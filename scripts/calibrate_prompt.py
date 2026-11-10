#!/usr/bin/env python3
"""Measure the screener's scope prompt against hand-labelled papers.

The weekly pipeline's SCOPE prompt decides what enters the list, so changing it
without measuring it is how a list drifts.  This harness replays the prompt over
`docs/scope-calibration.md` (hand-labelled: reject / keep / borderline) and
reports precision and recall on the "should reject" class, which is the class
that matters: a wrong entry costs the maintainer a manual deletion.

    # measure the production prompt with DeepSeek
    python3 scripts/calibrate_prompt.py

    # swap in a candidate prompt without editing screen.py
    python3 scripts/calibrate_prompt.py --prompt-file /tmp/new_scope.txt

    # add a few repeats: an unstable prompt is worse than an inaccurate one
    python3 scripts/calibrate_prompt.py --repeats 3

It reports, per paper, what the prompt decided and what a human said, plus a
confusion matrix.  No network call happens for the labels.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ml4db.config import REPO_ROOT  # noqa: E402
from ml4db.readme import section_choices  # noqa: E402
from ml4db.screen import SCOPE, build_prompt, screen_api  # noqa: E402
from ml4db.config import Candidate  # noqa: E402

CALIBRATION = REPO_ROOT / "docs" / "scope-calibration.md"

# Which hand labels mean "the pipeline should refuse this paper".
REJECT_LABELS = {"应当拒绝"}
KEEP_LABELS = {"应当保留"}
BORDER_LABELS = {"边界"}


def parse_calibration(path: Path = CALIBRATION) -> list[dict]:
    """Read the markdown table into [{title, label, why}]."""
    rows: list[dict] = []
    label = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            head = line[3:].strip()
            label = next((lab for lab in REJECT_LABELS | KEEP_LABELS | BORDER_LABELS
                          if head.startswith(lab)), "")
            continue
        if not label or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("论文", "---") or set(cells[0]) <= set("-: "):
            continue
        rows.append({"title": cells[0], "label": label, "why": cells[1]})
    return rows


def expected_decision(label: str) -> str:
    if label in REJECT_LABELS:
        return "reject"
    if label in KEEP_LABELS:
        return "accept"
    return "either"


def make_candidate(row: dict) -> Candidate:
    return Candidate(title=row["title"], venue="arXiv", year=2026, source="arxiv",
                     published="2026-01-01", abstract=row.get("abstract", ""),
                     uid=row["title"])


def title_matches(short: str, full: str) -> bool:
    """True when `short` is an abbreviation of `full`.

    The calibration file abbreviates titles, either by truncating them
    ("Logos: Certified Order-Sensitive SQL Rewrites") or by eliding a middle
    part with "...".  Comparing tokens as an ordered subsequence handles both,
    and is far safer than a similarity threshold: an abbreviated title scores
    67-80 while an unrelated paper scores 31, so any cut-off wide enough to
    catch abbreviations also starts matching genuinely different papers.
    """
    import re as _re

    from ml4db.normalize import normalize_title

    def toks(text: str) -> list[str]:
        return normalize_title(text).split()

    parts = [toks(p) for p in _re.split(r"\.\.\.", short) if toks(p)]
    if not parts:
        return False
    full_toks = toks(full)
    pos = 0
    for part in parts:
        # find `part` as a contiguous run inside full_toks, at or after pos
        n = len(part)
        found = -1
        for i in range(pos, len(full_toks) - n + 1):
            if full_toks[i:i + n] == part:
                found = i
                break
        if found < 0:
            return False
        pos = found + n
    return True


def _fuzzy_lookup(key: str, table: dict, full_titles: dict | None = None) -> dict | None:
    """Exact key first, then abbreviation matching."""
    if key in table:
        return table[key]
    for cand_key, rec in table.items():
        if title_matches(key, cand_key) or title_matches(cand_key, key):
            return rec
    return None


def strip_abstract_fetch(rows: list[dict], cache_dir: Path) -> None:
    """Attach cached abstracts when available; the prompt still works without."""
    path = cache_dir / "abstracts.json"
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return
    from ml4db.normalize import normalize_title
    for row in rows:
        rec = _fuzzy_lookup(normalize_title(row["title"]), data)
        if rec:
            row["abstract"] = rec.get("abstract", "")


def attach_abstracts(rows: list[dict], cache_dir: Path, verbose: bool = True) -> None:
    """Reuse the audit's abstract cache; fetch what is missing, quietly."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "audit_scope", REPO_ROOT / "scripts" / "audit_scope.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    from ml4db.readme import parse_entries

    strip_abstract_fetch(rows, cache_dir)
    missing = [r for r in rows if not r.get("abstract")]
    if not missing:
        return
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    by_title = {e.title: e for e in parse_entries(readme)}
    from ml4db.normalize import normalize_title
    by_norm = {normalize_title(e.title): e for e in parse_entries(readme)}
    cache = audit.AbstractCache(cache_dir / "abstracts.json")
    entries = []
    for row in missing:
        e = by_title.get(row["title"]) or by_norm.get(normalize_title(row["title"]))
        if e is None:
            for cand in by_norm.values():
                if title_matches(row["title"], cand.title):
                    e = cand
                    break
        if e is not None:
            entries.append(e)
    if entries:
        if verbose:
            print(f"[abstracts] resolving {len(entries)} of {len(missing)} missing",
                  file=sys.stderr)
        args = argparse.Namespace(workers=4)
        audit.resolve_abstracts(entries, cache, args, verbose=verbose)
        strip_abstract_fetch(rows, cache_dir)


def run(prompt: str, rows: list[dict], sections, repeats: int, verbose: bool = True) -> list[dict]:
    """Screen every calibration paper with `prompt`, `repeats` times."""
    from ml4db import screen as screen_mod

    original = screen_mod.SCOPE
    screen_mod.SCOPE = prompt
    try:
        out = []
        for i, row in enumerate(rows):
            cands = [make_candidate(row)]
            decisions = []
            for _ in range(repeats):
                kept, dropped = screen_api(cands, sections, {})
                decisions.append("accept" if kept else "reject")
            vote = Counter(decisions).most_common(1)[0][0]
            out.append({**row, "decisions": decisions, "decision": vote,
                        "stable": len(set(decisions)) == 1})
            if verbose:
                mark = "ok" if _matches(expected_decision(row["label"]), vote) else "XX"
                print(f"[{i + 1:>2}/{len(rows)}] {mark} {row['label']:<5} "
                      f"→ {vote:<6} {row['title'][:60]}", file=sys.stderr)
        return out
    finally:
        screen_mod.SCOPE = original


def _matches(expected: str, actual: str) -> bool:
    return expected == "either" or expected == actual


def summarise(rows: list[dict]) -> dict:
    decidable = [r for r in rows if expected_decision(r["label"]) != "either"]
    correct = [r for r in decidable if _matches(expected_decision(r["label"]), r["decision"])]

    reject_rows = [r for r in rows if expected_decision(r["label"]) == "reject"]
    keep_rows = [r for r in rows if expected_decision(r["label"]) == "accept"]
    refused = [r for r in reject_rows if r["decision"] == "reject"]
    admitted = [r for r in keep_rows if r["decision"] == "accept"]
    leaked = [r for r in reject_rows if r["decision"] == "accept"]
    lost = [r for r in keep_rows if r["decision"] == "reject"]

    precision = len(refused) / max(1, sum(1 for r in rows if r["decision"] == "reject"))
    recall = len(refused) / max(1, len(reject_rows))
    return {
        "n": len(rows),
        "accuracy": len(correct) / max(1, len(decidable)),
        "reject_precision": precision,
        "reject_recall": recall,
        "keep_recall": len(admitted) / max(1, len(keep_rows)),
        "leaked": [r["title"] for r in leaked],
        "lost": [r["title"] for r in lost],
        "unstable": [r["title"] for r in rows if not r["stable"]],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prompt-file", help="use this text instead of screen.SCOPE")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--cache-dir", default=".ml4db/audit")
    p.add_argument("--out", default=".ml4db/audit/calibration.json")
    p.add_argument("--calibration", default=str(CALIBRATION))
    args = p.parse_args(argv)

    from ml4db.config import load_config

    env_paths = ["~/.config/ml4db/audit.env", "~/.config/ml4db/jev.env"]
    for raw in env_paths:
        path = Path(os.path.expanduser(raw))
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            line = line[len("export "):] if line.startswith("export ") else line
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))

    if not os.environ.get("LLM_API_KEY"):
        raise SystemExit("LLM_API_KEY is not set; calibration measures the SCOPE prompt, "
                         "which needs the chat endpoint. Fill ~/.config/ml4db/audit.env.")

    prompt = Path(args.prompt_file).read_text(encoding="utf-8") if args.prompt_file else SCOPE
    rows = parse_calibration(Path(args.calibration))
    if not rows:
        raise SystemExit(f"no labelled rows found in {args.calibration}")

    cache_dir = Path(args.cache_dir)
    if not cache_dir.is_absolute():
        cache_dir = REPO_ROOT / cache_dir
    attach_abstracts(rows, cache_dir)

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    sections = section_choices(readme)
    results = run(prompt, rows, sections, args.repeats)
    stats = summarise(results)

    print(f"\n{stats['n']} labelled papers  accuracy {stats['accuracy']:.0%}")
    print(f"reject precision {stats['reject_precision']:.0%}  "
          f"reject recall {stats['reject_recall']:.0%}  "
          f"keep recall {stats['keep_recall']:.0%}")
    if stats["leaked"]:
        print("\n泄漏（该拒却收）：")
        for t in stats["leaked"]:
            print(f"  - {t}")
    if stats["lost"]:
        print("\n误杀（该收却拒）：")
        for t in stats["lost"]:
            print(f"  - {t}")
    if stats["unstable"]:
        print(f"\n判定不稳定（{args.repeats} 次结果不一致）：{len(stats['unstable'])} 篇")
        for t in stats["unstable"]:
            print(f"  - {t}")

    payload = {"prompt_sha": _sha(prompt), "stats": stats, "rows": results}
    out = Path(args.out)
    if not out.is_absolute():
        out = REPO_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


def _sha(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


if __name__ == "__main__":
    raise SystemExit(main())
