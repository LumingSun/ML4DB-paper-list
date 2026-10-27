"""CLI entry point.

    python -m ml4db harvest --since 2026-04-21 --out cands.json
    python -m ml4db filter  --in cands.json --out pending.json
    python -m ml4db batches --in pending.json --size 25 --dir batches/
    python -m ml4db apply   --in accepted.json --dry-run
    python -m ml4db apply   --in accepted.json --pr
    python -m ml4db cleanup --manifest cleanup.json --pr
    python -m ml4db screen  --in pending.json --out accepted.json   # needs LLM_API_KEY
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from . import config as cfgmod
from .config import Candidate, data_dir
from .filters import dedupe, prefilter, find_duplicate
from .harvest import harvest
from .pr import open_pr
from .readme import (delete_lines, insert_entries, parse_entries, parse_sections,
                     section_choices)
from .normalize import normalize_title
from .validate import (duplicate_titles, removed_lines, validate_additions,
                       validate_cleanup)


def _load(path: str) -> list[Candidate]:
    return [Candidate.from_dict(d) for d in json.loads(Path(path).read_text(encoding="utf-8"))]


def _dump(path: str, items: list) -> None:
    payload = [c.to_dict() if isinstance(c, Candidate) else c for c in items]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_harvest(args) -> None:
    cfg = cfgmod.load_config()
    from datetime import date
    since = cfgmod.parse_iso(args.since)
    until = cfgmod.parse_iso(args.until) if args.until else date.today()
    sources = tuple(args.source.split(",")) if args.source else ("arxiv", "crossref")
    items = harvest(cfg, since, until, sources)
    _dump(args.out, items)
    print(f"harvested {len(items)} candidates ({since} .. {until}) -> {args.out}")


def cmd_filter(args) -> None:
    cfg = cfgmod.load_config()
    cands = _load(args.in_)
    readme_text = cfgmod.README.read_text(encoding="utf-8")
    entries = parse_entries(readme_text)
    in_scope, lex_dropped = prefilter(cands, cfg)
    kept, dedup_dropped = dedupe(in_scope, entries, cfg)
    _dump(args.out, [c.to_dict() for c in kept])
    _dump(args.dropped, lex_dropped + dedup_dropped)
    print(f"harvested {len(cands)} -> lexical {len(in_scope)} -> new {len(kept)}")
    print(f"dropped: {len(lex_dropped)} out-of-scope, {len(dedup_dropped)} duplicates")


def cmd_batches(args) -> None:
    cands = _load(args.in_)
    sections = section_choices(cfgmod.README.read_text(encoding="utf-8"))
    outdir = Path(args.dir)
    outdir.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(cands), args.size):
        batch = cands[i:i + args.size]
        payload = {
            "sections": [p for p, _ in sections],
            "candidates": [
                {"id": c.uid, "title": c.title, "venue": f"{c.venue} {c.year}",
                 "abstract": (c.abstract or "")[:1200]}
                for c in batch
            ],
        }
        (outdir / f"batch_{i // args.size:03d}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {(len(cands) + args.size - 1) // args.size} batches to {outdir}")


def cmd_screen(args) -> None:
    from .screen import screen_api, screen_jev
    cfg = cfgmod.load_config()
    cands = _load(args.in_)
    sections = section_choices(cfgmod.README.read_text(encoding="utf-8"))
    if args.screener == "jev":
        kept, dropped = screen_jev(cands, sections, cfg)
    else:
        kept, dropped = screen_api(cands, sections, cfg)
    _dump(args.out, [c.to_dict() for c in kept])
    _dump(args.dropped, dropped)
    print(f"screened {len(cands)} -> accepted {len(kept)}")


def cmd_verdicts(args) -> None:
    from .screen import screen_verdicts
    cands = _load(args.in_)
    sections = section_choices(cfgmod.README.read_text(encoding="utf-8"))
    verdicts: list[dict] = []
    for path in args.verdicts:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        verdicts += data.get("results", data) if isinstance(data, dict) else data
    kept, dropped = screen_verdicts(cands, sections, verdicts)
    _dump(args.out, [c.to_dict() for c in kept])
    _dump(args.dropped, dropped)
    print(f"{len(cands)} candidates, {len(verdicts)} verdicts -> accepted {len(kept)}, rejected {len(dropped)}")


def cmd_select(args) -> None:
    """Cap how many unrefereed (arXiv) entries a section may gain.

    A backfill can otherwise swamp a section with preprints: the list
    privileges peer-reviewed papers, and arXiv entries are a garnish.
    """
    cands = _load(args.in_)
    by_section: dict[str, list[Candidate]] = {}
    for c in cands:
        by_section.setdefault(c.section, []).append(c)
    kept: list[Candidate] = []
    for section, items in sorted(by_section.items()):
        published = [c for c in items if c.venue != "arXiv"]
        arxiv = sorted((c for c in items if c.venue == "arXiv"),
                       key=lambda c: (c.year or 0), reverse=True)
        if args.require_notable:
            arxiv = [c for c in arxiv if c.notable]
        kept += published
        kept += arxiv[: args.arxiv_per_section]
    if args.arxiv_total is not None:
        pub = [c for c in kept if c.venue != "arXiv"]
        arx = [c for c in kept if c.venue == "arXiv"][: args.arxiv_total]
        kept = pub + arx
    _dump(args.out, [c.to_dict() for c in kept])
    print(f"{len(cands)} accepted -> kept {len(kept)} "
          f"({sum(1 for c in kept if c.venue != 'arXiv')} published, "
          f"{sum(1 for c in kept if c.venue == 'arXiv')} arXiv)")


def cmd_apply(args) -> None:
    cfg = cfgmod.load_config()
    accepted = _load(args.in_)
    if not accepted:
        raise SystemExit("nothing accepted; refusing to open an empty PR")
    readme_text = cfgmod.README.read_text(encoding="utf-8")
    sections = {p: s for p, s in section_choices(readme_text)}
    by_section: dict[str, list[str]] = {}
    for c in accepted:
        if c.section not in sections:
            raise SystemExit(f"unknown section {c.section!r} for {c.title!r}")
        by_section.setdefault(c.section, []).append(c.entry_line())

    new_text = insert_entries(readme_text, by_section)
    report = validate_additions(readme_text, new_text)
    counts = Counter(c.section.split(" > ")[-1] for c in accepted)
    report.raise_if_bad()

    body = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else _pr_body(accepted, counts, report, readme_text)
    if args.dry_run or not args.pr:
        out = Path(args.out) if args.out else data_dir() / "README.candidate.md"
        out.write_text(new_text, encoding="utf-8")
        print(f"validation ok: {report.added} entries; wrote {out}")
        print(body)
        return
    branch = f"auto/papers-{args.slug}"
    url = open_pr(branch, {Path("README.md"): new_text}, args.title, body,
                  labels=["auto-update"])
    print(f"opened {url}")


def _pr_body(accepted: list[Candidate], counts: Counter, report, old_text: str) -> str:
    lines = [
        "## 新增论文",
        "",
        "| 小节 | 新增 |",
        "| --- | --- |",
    ]
    for sec, n in counts.most_common():
        lines.append(f"| {sec} | {n} |")
    lines += [
        "",
        f"合计 **{report.added}** 条。",
        "",
        "## 校验",
        "",
        "- [x] 每条都是 `标题 (会议/期刊 年份) [arXiv/DOI 链接]` 四要素齐全",
        "- [x] 每条链接都能解析到 arXiv ID 或 DOI",
        "- [x] 未引入与现有条目重复的标题",
        "- [x] diff 只有新增行，未改动任何已有内容",
        "- [x] 章节标题与目录未变",
        "",
        "## 来源",
        "",
        "arXiv API + Crossref（PVLDB / PACMMOD / TKDE / VLDBJ / ICDE）。"
        "条目元数据直接来自接口返回，模型只负责判断是否收录与归入哪个小节。",
    ]
    return "\n".join(lines)


def cmd_cleanup(args) -> None:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    readme_text = cfgmod.README.read_text(encoding="utf-8")
    lines = readme_text.split("\n")
    remove_idx, expected = [], []
    for item in manifest["removals"]:
        idx = item["line"] - 1
        actual = lines[idx]
        if normalize_title(_title_of(actual)) != normalize_title(_title_of(lines[item["keep_line"] - 1])):
            raise SystemExit(f"manifest sanity check failed at line {item['line']}: {actual[:80]}")
        remove_idx.append(idx)
        expected.append(actual)
    new_text = delete_lines(readme_text, remove_idx)
    report = validate_cleanup(readme_text, new_text, expected)
    report.raise_if_bad()
    remaining = duplicate_titles(new_text)
    body = "\n".join([
        "## 清理存量重复条目",
        "",
        f"README 里有 {len(manifest['removals'])} 组同名论文被判重，本 PR 每组保留一条、删除多余的那条，"
        f"共删除 {len(expected)} 行。",
        "",
        "| 删除行 | 保留行 | 标题 |",
        "| --- | --- | --- |",
        *[f"| {r['line']} | {r['keep_line']} | {_title_of(expected[i])[:70]} |"
          for i, r in enumerate(manifest["removals"])],
        "",
        "除此之外没有任何改动：不新增、不改格式、不调整分类。",
        f"清理后剩余重复标题：**{len(remaining)}** 组。",
    ])
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    if args.dry_run or not args.pr:
        out = Path(args.out) if args.out else data_dir() / "README.cleaned.md"
        out.write_text(new_text, encoding="utf-8")
        print(f"cleanup validation ok: removed {len(expected)} lines; wrote {out}")
        print(body)
        return
    url = open_pr(f"auto/dedupe-{args.slug}", {Path("README.md"): new_text},
                  args.title, body, labels=["cleanup"])
    print(f"opened {url}")


def _title_of(line: str) -> str:
    from .normalize import ENTRY_RE
    m = ENTRY_RE.match(line)
    return m.group("body") if m else line


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="ml4db")
    sub = p.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("harvest")
    h.add_argument("--since", required=True)
    h.add_argument("--until")
    h.add_argument("--out", required=True)
    h.add_argument("--source", help="arxiv,crossref (default: both)")
    h.set_defaults(func=cmd_harvest)

    f = sub.add_parser("filter")
    f.add_argument("--in", dest="in_", required=True)
    f.add_argument("--out", required=True)
    f.add_argument("--dropped", default=str(data_dir() / "dropped.json"))
    f.set_defaults(func=cmd_filter)

    b = sub.add_parser("batches")
    b.add_argument("--in", dest="in_", required=True)
    b.add_argument("--dir", required=True)
    b.add_argument("--size", type=int, default=25)
    b.set_defaults(func=cmd_batches)

    s = sub.add_parser("screen")
    s.add_argument("--in", dest="in_", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--dropped", default=str(data_dir() / "screen_dropped.json"))
    s.add_argument("--screener", choices=["llm", "jev"], default="llm")
    s.set_defaults(func=cmd_screen)

    v = sub.add_parser("verdicts")
    v.add_argument("--in", dest="in_", required=True)
    v.add_argument("--verdicts", nargs="+", required=True)
    v.add_argument("--out", required=True)
    v.add_argument("--dropped", default=str(data_dir() / "screen_dropped.json"))
    v.set_defaults(func=cmd_verdicts)

    sel = sub.add_parser("select")
    sel.add_argument("--in", dest="in_", required=True)
    sel.add_argument("--out", required=True)
    sel.add_argument("--arxiv-per-section", type=int, default=6)
    sel.add_argument("--arxiv-total", type=int, default=None)
    sel.add_argument("--require-notable", action="store_true", default=True)
    sel.set_defaults(func=cmd_select)

    a = sub.add_parser("apply")
    a.add_argument("--in", dest="in_", required=True)
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--pr", action="store_true")
    a.add_argument("--out")
    a.add_argument("--slug", default="run")
    a.add_argument("--title", default="[Auto] 新增 AI4DB 论文")
    a.add_argument("--body-file", help="use this markdown as the PR body")
    a.set_defaults(func=cmd_apply)

    c = sub.add_parser("cleanup")
    c.add_argument("--manifest", required=True)
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--pr", action="store_true")
    c.add_argument("--out")
    c.add_argument("--slug", default="run")
    c.add_argument("--title", default="[Cleanup] 清理 README 中的重复条目")
    c.add_argument("--body-file", help="use this markdown as the PR body")
    c.set_defaults(func=cmd_cleanup)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
