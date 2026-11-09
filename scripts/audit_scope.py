#!/usr/bin/env python3
"""Audit README entries against the AI4DB scope — local, high-accuracy, repeatable.

The weekly pipeline runs unattended, so it must be cheap, fast and
fail-closed.  This script is the opposite: it runs on a laptop, may take
minutes, spends a few cents, and is allowed to be pedantic.  It answers one
question per paper:

    is a DATABASE SYSTEM the object of this work?

Why that question and not "does it mention a database": the failure mode this
audits for is a paper that reads relational data, emits SQL and gets published
at VLDB/SIGMOD, while its actual contribution is a business answer, a
dashboard, an ontology, a semantic layer or a data pipeline.  Such papers are
LLM x data, not AI4DB.  Judging the object of study rather than the vocabulary
is what separates them, and no keyword filter can do it.

Usage
-----
    # papers added by the last two auto commits (the default question: "what
    # did the bot just add, and was it right?")
    python3 scripts/audit_scope.py --recent-commits 2

    # papers added since a given commit / branch
    python3 scripts/audit_scope.py --git-since d1f0578

    # one section, or the whole list
    python3 scripts/audit_scope.py --section "LLM4DB & Agent for DB"
    python3 scripts/audit_scope.py --all

    # narrow by title substring
    python3 scripts/audit_scope.py --match "Data.Readme"

Outputs a Markdown report plus a JSON dump under .ml4db/audit/ so a re-run is
cheap and two runs can be diffed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ml4db.config import REPO_ROOT  # noqa: E402
from ml4db.normalize import normalize_title, token_set_ratio  # noqa: E402
from ml4db.readme import Entry, parse_entries  # noqa: E402

# Bump when the rubric or the prompt changes: it invalidates the verdict cache,
# so an old judgement is never silently reused against a new definition.
RUBRIC_VERSION = "scope-3"

ARXIV_ID_RE = re.compile(r"arxiv\.org/abs/(?P<id>[\w.\-]+)")
DOI_RE = re.compile(r"doi\.org/(?P<doi>10\.[^)\s]+)")

ARXIV_API = "https://export.arxiv.org/api/query"
CROSSREF_API = "https://api.crossref.org/works"
OPENALEX_API = "https://api.openalex.org/works"
UA = "ML4DB-scope-audit/1.0 (local audit; https://github.com/LumingSun/ML4DB-paper-list)"

KEEP, REVIEW, DROP = "keep", "review", "drop"


# ---------------------------------------------------------------------------
# Scope definition — the single source of truth for this script.
# ---------------------------------------------------------------------------

RUBRIC = """\
You maintain a reading list for AI4DB / ML4DB: machine learning applied to database
systems, and LLM/agent systems that operate or build database systems. The audience is
database-systems researchers. The list's historical failure is admitting papers that
use SQL and relational tables while actually contributing something else - a business
answer, a dashboard, an ontology, a semantic layer, a data pipeline.

Judge the OBJECT OF STUDY, never the vocabulary. A DBMS must be what the paper builds,
changes, operates or measures.

Work through these steps and report each one.

STEP 1 - ARTIFACT. What does this paper build, change, operate or measure? Pick one:
  dbms_core       The DBMS itself: query optimizer, executor, plan or cost model,
                  cardinality estimation, storage or index structures, buffer pool,
                  transactions, catalog/schema, knobs, physical design, partitioning,
                  materialized views, workload management, learned DB components.
  dbms_interface  The layer turning a user request into DBMS operations: text-to-SQL /
                  NL2SQL / NL2Cypher / text2query, schema linking, SQL generation or
                  repair, query verification, database copilots, autonomous DBA agents
                  that diagnose / tune / migrate / repair a DBMS.
  dbms_eval       A benchmark, dataset or empirical study whose explicit subject is
                  database tasks or DBMS behaviour (e.g. "do LLMs understand MongoDB
                  queries", "do learned estimators generalise to a new IMDb snapshot").
  data_product    A BI or dashboard answer, analytics over enterprise data, semantic or
                  metric layer, data catalog, data discovery, data preparation or
                  cleaning, table/column annotation or documentation, ETL or
                  data-engineering pipeline, ontology or knowledge-graph construction.
  ml_method       A machine-learning method whose training or test data happens to live
                  in a database.
  other           None of the above.

STEP 2 - COUNTERFACTUAL. Would the contribution survive unchanged if the data were a
pile of CSV files or a managed warehouse? If yes, the DBMS is incidental.

STEP 3 - VENUE. Would this paper be equally at home at a BI, data-science, NLP,
knowledge-graph or software-engineering venue, with no change to its contribution? If
yes, the database is incidental.

STEP 4 - VERDICT.
  keep    ARTIFACT is dbms_core / dbms_interface / dbms_eval, the DBMS is essential, and
          STEPS 2-3 do not expose it as incidental.
  review  Genuinely in between: an agentic or data system where the DBMS is one component
          among several and database systems work is a substantial part of the
          contribution. Also use review when the abstract is too thin to decide.
  drop    ARTIFACT is data_product / ml_method / other; or the DBMS is incidental; or a
          hard exclusion applies.

HARD EXCLUSIONS (drop regardless of venue):
  vector database, vector search, ANN index as the contribution; RAG or GraphRAG as the
  contribution; knowledge-graph-only work; recommender systems; a DBMS paper that merely
  mentions AI as motivation; an AI paper that merely mentions databases as a data source.

Calibration notes:
  - "Agent that answers questions over enterprise tables" is data_product unless the
    paper's contribution is on the DBMS side (query planning, execution, schema, storage,
    correctness of the database interaction).
  - "LLM writes/repairs/optimises SQL, schema or engine code" is dbms_interface.
  - "Benchmark of LLMs/agents on database operations" is dbms_eval, even when the
    benchmark harness is generic.
  - Table annotation, column description, schema documentation for LLM consumption is
    data_product - the DBMS is unchanged and the work is metadata for a model.
  - An ontology or semantic layer is data_product even if stored in and queried from a
    database.
"""

VERDICT_SCHEMA = (
    'Return ONLY JSON, no prose, no code fences:\n'
    '{"artifact":"dbms_core|dbms_interface|dbms_eval|data_product|ml_method|other",'
    '"dbms_essential":true|false,'
    '"counterfactual_survives":true|false,'
    '"hard_exclusion":"none|vector|rag|kg_only|recsys|incidental_ml|incidental_db",'
    '"verdict":"keep|review|drop",'
    '"confidence":0.0-1.0,'
    '"reason":"<=30 words, name the object of study"}'
)


def build_prompt(entry: Entry, abstract: str) -> str:
    body = (
        f"TITLE: {entry.title}\n"
        f"VENUE: {entry.venue or 'unknown'} {entry.year or ''}\n"
        f"LIST SECTION: {entry.section_path or 'unknown'}\n"
        f"ABSTRACT: {abstract}\n"
    )
    if not abstract.strip():
        body += (
            "NOTE: no abstract is available. Judge from the title alone, and set "
            "confidence below 0.5; prefer verdict=review over guessing.\n"
        )
    return f"{RUBRIC}\n\nPAPER UNDER REVIEW\n{body}\n{VERDICT_SCHEMA}"


# Jev asks the same question as a typed decision, giving an independent second
# opinion.  Its probability is not calibration-grade (measured earlier on a
# 60-paper dev set), so it informs "review" rather than deciding alone.
JEV_ARTIFACTS = {
    "dbms_core": "The DBMS itself: optimizer, executor, cost/cardinality model, storage or "
                 "index structures, buffer pool, transactions, catalog, knobs, physical "
                 "design, workload management, learned DB components.",
    "dbms_interface": "Translating a request into DBMS operations: text-to-SQL/NL2SQL/"
                      "NL2Cypher, schema linking, SQL generation or repair, query "
                      "verification, database copilots, DBA agents that act on a DBMS.",
    "dbms_eval": "A benchmark or empirical study whose explicit subject is database tasks "
                 "or DBMS behaviour.",
    "data_product": "A BI/dashboard answer, analytics over enterprise data, semantic or "
                    "metric layer, data catalog, discovery, preparation, cleaning, table "
                    "annotation, ETL pipeline, ontology or knowledge-graph construction.",
    "ml_method": "A machine-learning method whose data happens to live in a database.",
    "other": "None of the above.",
}


def jev_questions() -> dict:
    return {
        "artifact": {
            "type": "choice",
            "instructions": (
                "What does this paper build, change, operate or measure? Judge the object "
                "of study, not whether relational data or SQL appears. Data or tables "
                "being relational is not sufficient for a database-system answer."
            ),
            "criteria": JEV_ARTIFACTS,
        },
        "dbms_essential": {
            "type": "noul",
            "instructions": (
                "Would the contribution survive unchanged if the data were a pile of CSV "
                "files or a managed warehouse? Answer true only if the contribution "
                "depends on the database system itself, so that a database-systems "
                "reading list on AI4DB / LLM4DB should collect this paper."
            ),
            "criteria": {
                "true": "The contribution depends on DBMS internals or on operating a DBMS.",
                "false": "The database is incidental: an LLM/data-science/BI paper that "
                         "happens to use SQL or relational tables.",
            },
        },
    }


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

DEFAULT_ENV_FILES = [
    "~/.config/ml4db/audit.env",
    "~/.config/ml4db/jev.env",
    ".ml4db/audit.env",
]


def load_env(paths: list[str], override: bool = False) -> list[str]:
    """Read `export KEY=value` / `KEY=value` files. First definition wins."""
    used: list[str] = []
    for raw in paths:
        p = Path(os.path.expanduser(raw))
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if not key:
                continue
            if override or not os.environ.get(key):
                os.environ[key] = value
        used.append(str(p))
    return used


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    return s


def _get_json(session: requests.Session, url: str, params: dict, tries: int = 3,
              timeout: int = 45) -> dict | None:
    delay = 2.0
    for attempt in range(tries):
        try:
            r = session.get(url, params=params, timeout=timeout)
        except requests.RequestException:
            time.sleep(delay)
            delay = min(delay * 2, 20)
            continue
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                return None
        if r.status_code in (429, 500, 502, 503, 504):
            wait = delay
            try:
                wait = float(r.headers.get("Retry-After") or delay)
            except ValueError:
                pass
            time.sleep(min(wait, 30))
            delay = min(delay * 2, 20)
            continue
        return None
    return None


# ---------------------------------------------------------------------------
# Selecting the papers to audit
# ---------------------------------------------------------------------------

def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                              capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def added_entry_lines(git_since: str) -> list[str]:
    """Entry lines that the range `git_since..HEAD` added to README.md."""
    out = _git("diff", "--unified=0", f"{git_since}..HEAD", "--", "README.md")
    added: list[str] = []
    for line in out.splitlines():
        if line.startswith("+* "):
            added.append(line[1:])
    return added


def recent_commit_bases(n: int) -> list[str]:
    """Commits (newest first) that touched README.md, as diff bases."""
    out = _git("log", f"-{n}", "--format=%H", "--", "README.md")
    return [h for h in out.split() if h]


def select_entries(all_entries: list[Entry], args) -> tuple[list[Entry], str]:
    entries = all_entries
    origin = "whole README"

    if args.match:
        needle = args.match.lower()
        entries = [e for e in entries if needle in e.title.lower()]
        origin = f"title contains {args.match!r}"

    if args.section:
        needle = args.section.lower()
        entries = [e for e in entries if needle in e.section_path.lower()]
        origin = f"section ~ {args.section!r}"

    bases: list[str] = []
    if args.git_since:
        bases = [args.git_since]
    elif args.recent_commits:
        # The N commits that touched README: diff from the oldest of them, so
        # exactly those N commits' additions are audited.
        commits = recent_commit_bases(args.recent_commits + 1)
        if len(commits) >= args.recent_commits + 1:
            bases = [commits[-1]]
        elif commits:
            bases = [f"{commits[-1]}~1"]
    if bases:
        lines = added_entry_lines(bases[0])
        wanted_norms = set()
        for line in lines:
            m = re.match(r"^\* (?P<title>.+?) \((?P<venue>[^()]*)\)", line)
            if m:
                wanted_norms.add(normalize_title(m.group("title")))
        entries = [e for e in entries if normalize_title(e.title) in wanted_norms]
        origin = f"added in {bases[0][:8]}..HEAD ({len(lines)} lines)"

    entries = _dedupe_entries(entries)
    if args.limit:
        entries = entries[: args.limit]
    return entries, origin


def _dedupe_entries(entries: list[Entry]) -> list[Entry]:
    seen: set[str] = set()
    out: list[Entry] = []
    for e in entries:
        key = normalize_title(e.title)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


# ---------------------------------------------------------------------------
# Abstracts: the judge is only as good as the text it reads.
# ---------------------------------------------------------------------------

class AbstractCache:
    def __init__(self, path: Path, refresh: bool = False):
        self.path = path
        self.refresh = refresh
        self.data: dict[str, dict] = {}
        self.lock = threading.Lock()
        if path.is_file() and not refresh:
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                self.data = {}

    def get(self, title: str) -> str | None:
        rec = self.data.get(normalize_title(title))
        return None if rec is None else rec.get("abstract", "")

    def put(self, title: str, abstract: str, source: str) -> None:
        with self.lock:
            self.data[normalize_title(title)] = {"abstract": abstract, "source": source}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1),
                             encoding="utf-8")


def _arxiv_ids(entry: Entry) -> str:
    m = ARXIV_ID_RE.search(entry.tail or "")
    return m.group("id") if m else ""


def _doi(entry: Entry) -> str:
    m = DOI_RE.search(entry.tail or "")
    return m.group("doi") if m else ""


def fetch_arxiv_abstracts(session, ids: list[str], verbose: bool = True) -> dict[str, str]:
    import xml.etree.ElementTree as ET

    atom = {"a": "http://www.w3.org/2005/Atom"}
    out: dict[str, str] = {}
    for start in range(0, len(ids), 40):
        chunk = ids[start:start + 40]
        for attempt in range(3):
            try:
                r = session.get(ARXIV_API, params={"id_list": ",".join(chunk),
                                                   "max_results": len(chunk)}, timeout=60)
            except requests.RequestException:
                time.sleep(3 * (attempt + 1))
                continue
            if r.status_code == 200:
                break
            time.sleep(3 * (attempt + 1))
        else:
            if verbose:
                print(f"[arxiv] gave up on {len(chunk)} ids", file=sys.stderr)
            continue
        try:
            root = ET.fromstring(r.text)
        except ET.ParseError:
            continue
        for e in root.findall("a:entry", atom):
            raw = e.find("a:id", atom).text.strip()
            aid = re.sub(r"v\d+$", "", raw.rsplit("/abs/", 1)[-1])
            summary = e.find("a:summary", atom)
            if summary is not None and summary.text:
                out[aid] = " ".join(summary.text.split())
        time.sleep(3)  # arXiv asks for 3s between API calls
    return out


def fetch_crossref_abstracts(session, dois: list[str], verbose: bool = True) -> dict[str, str]:
    out: dict[str, str] = {}
    for start in range(0, len(dois), 20):
        chunk = dois[start:start + 20]
        data = _get_json(session, CROSSREF_API, {
            "filter": ",".join(f"doi:{d}" for d in chunk),
            "rows": len(chunk),
            "select": "DOI,abstract",
        })
        if not data:
            if verbose:
                print(f"[crossref] gave up on {len(chunk)} dois", file=sys.stderr)
            continue
        for item in data.get("message", {}).get("items", []):
            abstract = _strip_markup(item.get("abstract") or "")
            if abstract and item.get("DOI"):
                out[item["DOI"].lower()] = abstract
    return out


_TAG = re.compile(r"<[^>]+>")


def _strip_markup(text: str) -> str:
    import html

    text = html.unescape(text or "")
    text = _TAG.sub(" ", text)
    return " ".join(text.split())


def fetch_crossref_by_title(session, entry: Entry) -> str:
    data = _get_json(session, CROSSREF_API, {
        "query.bibliographic": entry.title,
        "rows": 5,
        "select": "title,DOI,abstract",
    })
    if not data:
        return ""
    best, best_sim = "", 0.0
    for item in data.get("message", {}).get("items", []):
        titles = item.get("title") or []
        if not titles:
            continue
        sim = token_set_ratio(entry.title, titles[0])
        if sim >= 90 and sim > best_sim:
            abstract = _strip_markup(item.get("abstract") or "")
            if abstract:
                best, best_sim = abstract, sim
    return best


def fetch_openalex_by_title(session, entry: Entry, api_key: str = "") -> str:
    params = {
        "filter": f'title.search:"{entry.title}"',
        "per-page": 3,
        "select": "title,abstract_inverted_index",
    }
    if api_key:
        params["api_key"] = api_key
    data = _get_json(session, OPENALEX_API, params)
    if not data:
        return ""
    for work in data.get("results", []):
        sim = token_set_ratio(entry.title, work.get("title") or "")
        if sim < 88:
            continue
        inverted = work.get("abstract_inverted_index")
        if not inverted:
            continue
        positions: dict[int, str] = {}
        for token, idxs in inverted.items():
            for i in idxs:
                positions[i] = token
        text = " ".join(positions[i] for i in sorted(positions)).strip()
        if text:
            return text
    return ""


def resolve_abstracts(entries: list[Entry], cache: AbstractCache, args,
                      verbose: bool = True) -> None:
    session = _session()
    need = [e for e in entries if cache.get(e.title) is None]
    if verbose:
        print(f"[abstracts] {len(entries)} papers, {len(need)} need lookup "
              f"({len(entries) - len(need)} cached)", file=sys.stderr)

    # Phase 1: batch lookups by identifier, cheapest and most reliable.
    arxiv_map: dict[str, str] = {}
    ids = [i for i in {_arxiv_ids(e) for e in need} if i]
    if ids:
        arxiv_map = fetch_arxiv_abstracts(session, ids, verbose)
        for e in need:
            aid = _arxiv_ids(e)
            if aid and arxiv_map.get(aid):
                cache.put(e.title, arxiv_map[aid], "arxiv")

    doi_map: dict[str, str] = {}
    dois = [d for d in {_doi(e) for e in need if not cache.get(e.title)} if d]
    if dois:
        doi_map = fetch_crossref_abstracts(session, dois, verbose)
        for e in need:
            doi = _doi(e)
            if doi and not cache.get(e.title) and doi_map.get(doi.lower()):
                cache.put(e.title, doi_map[doi.lower()], "crossref-doi")

    # Phase 2: fall back to title search for whatever is still empty. This is
    # where the list's older entries (no link at all) get their abstract.
    missing = [e for e in need if not cache.get(e.title)]
    if verbose and missing:
        print(f"[abstracts] {len(missing)} still missing; title search", file=sys.stderr)

    def work(entry: Entry) -> tuple[Entry, str, str]:
        abstract = fetch_crossref_by_title(session, entry)
        if abstract:
            return entry, abstract, "crossref-title"
        abstract = fetch_openalex_by_title(session, entry, os.environ.get("OPENALEX_KEY", ""))
        if abstract:
            return entry, abstract, "openalex-title"
        return entry, "", "none"

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for entry, abstract, source in pool.map(work, missing):
            cache.put(entry.title, abstract, source)

    cache.save()


# ---------------------------------------------------------------------------
# Judging
# ---------------------------------------------------------------------------

def _loads_json(text: str) -> dict | None:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    for candidate in (text, text[text.find("{"): text.rfind("}") + 1]):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(data, dict):
            return data
    return None


def ask_deepseek(session: requests.Session, entry: Entry, abstract: str) -> dict | None:
    base = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    key = os.environ.get("LLM_API_KEY", "")
    if not key:
        raise RuntimeError("LLM_API_KEY is not set")
    prompt = build_prompt(entry, abstract[:4000])
    for attempt in range(3):
        try:
            r = session.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system",
                         "content": "You are a precise, sceptical reviewer of a database "
                                    "systems reading list. Output JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=120,
            )
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            data = _loads_json(r.json()["choices"][0]["message"]["content"])
            if data:
                return data
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
        except (KeyError, ValueError):
            time.sleep(1)
    return None


def ask_jev(session: requests.Session, entry: Entry, abstract: str) -> dict | None:
    key = os.environ.get("JEV_API_KEY", "")
    if not key:
        return None
    url = os.environ.get("JEV_URL", "https://api.defapi.org/api/v1/decisions")
    model = os.environ.get("JEV_MODEL", "typesafe/jev-1.14.0")
    state = {
        "title": entry.title,
        "venue": f"{entry.venue} {entry.year}" if entry.year else entry.venue,
        "section": entry.section_path,
        "abstract": abstract[:2500],
    }
    for attempt in range(3):
        try:
            r = session.post(url,
                             headers={"Authorization": f"Bearer {key}"},
                             json={"model": model, "state": state,
                                   "questions": jev_questions()},
                             timeout=180)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt * 2)
                continue
            r.raise_for_status()
            answers = r.json().get("answers", {})
            artifact = answers.get("artifact", {}).get("choice", "")
            essential = answers.get("dbms_essential", {})
            return {
                "artifact": artifact,
                "dbms_essential": float(essential.get("noul", 0.0)),
                "confidence": float(answers.get("artifact", {}).get("confidence", 0.0)),
            }
        except (requests.RequestException, ValueError, KeyError):
            time.sleep(2 ** attempt * 2)
    return None


IN_SCOPE_ARTIFACTS = {"dbms_core", "dbms_interface", "dbms_eval"}


def aggregate(votes: list[dict], jev: dict | None, has_abstract: bool,
              min_confidence: float) -> dict:
    """Combine DeepSeek passes and the Jev opinion into one auditable row.

    DeepSeek votes decide; a disagreement between passes, a Jev objection or a
    missing abstract can only soften a verdict (keep -> review), never harden
    it, because a wrong removal costs more than a wrong keep.
    """
    if not votes and jev:
        return _aggregate_jev_only(jev, has_abstract)
    if not votes:
        return {"verdict": REVIEW, "confidence": 0.0, "artifact": "",
                "agreement": "no deepseek answer",
                "notes": ["DeepSeek 调用失败，未判定"]}

    verdicts = Counter(v.get("verdict") for v in votes if v.get("verdict"))
    artifacts = Counter(v.get("artifact") for v in votes if v.get("artifact"))
    artifact, art_n = (artifacts.most_common(1)[0] if artifacts else ("", 0))
    verdict, ver_n = (verdicts.most_common(1)[0] if verdicts else (REVIEW, 0))
    unanimous = len(verdicts) == 1 and ver_n == len(votes)
    conf = sum(float(v.get("confidence") or 0) for v in votes) / max(1, len(votes))
    notes: list[str] = []

    if not unanimous:
        notes.append("多轮判定不一致：" + "，".join(f"{k}×{n}" for k, n in verdicts.items()))
        # Each pass is the same model on the same text: if it cannot agree with
        # itself, the paper is a judgement call by definition, and neither a
        # keep nor a removal should be asserted on a coin flip.
        verdict = REVIEW

    # Rubric consistency: an in-scope artifact with a drop verdict (or the
    # reverse) is a model inconsistency, not a finding — send it to review.
    if artifact in IN_SCOPE_ARTIFACTS and verdict == DROP:
        notes.append(f"判定自相矛盾：对象={artifact} 却给了 drop")
        verdict = REVIEW
    if artifact and artifact not in IN_SCOPE_ARTIFACTS and verdict == KEEP:
        notes.append(f"判定自相矛盾：对象={artifact} 却给了 keep")
        verdict = REVIEW

    exclusions = {v.get("hard_exclusion") for v in votes} - {"", "none", None}
    if exclusions:
        notes.append("命中硬性排除：" + "、".join(sorted(exclusions)))
        if verdict == KEEP:
            verdict = DROP

    if jev:
        p = jev.get("dbms_essential", 0.0)
        j_artifact = jev.get("artifact", "")
        if p < 0.35:
            notes.append(f"Jev 反对：DBMS 非关键（{p:.2f}），对象={j_artifact}")
            if verdict == KEEP:
                verdict = REVIEW
        elif j_artifact and j_artifact not in IN_SCOPE_ARTIFACTS and artifact in IN_SCOPE_ARTIFACTS:
            notes.append(f"Jev 对研究对象有异议（它判 {j_artifact}，DeepSeek 判 {artifact}）")
            if verdict == KEEP:
                verdict = REVIEW

    if not has_abstract:
        notes.append("无摘要，仅凭标题判断")
        if verdict == DROP:
            verdict = REVIEW

    if verdict == KEEP and conf < min_confidence:
        notes.append(f"置信度偏低（{conf:.2f}）")
        verdict = REVIEW

    reason = (votes[0].get("reason") or "").strip()
    return {
        "verdict": verdict,
        "confidence": round(conf, 2),
        "artifact": artifact,
        "agreement": "一致" if unanimous else "不一致",
        "reason": reason,
        "jev": jev or {},
        "notes": notes,
    }


JEV_ARTIFACT_REASONS = {
    "dbms_core": "改动的就是 DBMS 本身",
    "dbms_interface": "做的是自然语言/请求到 DBMS 操作的转换",
    "dbms_eval": "评测对象是数据库任务",
    "data_product": "对象是分析结论/元数据/数据产品，DBMS 未被改动",
    "ml_method": "贡献是 ML 方法，数据库只是数据来源",
    "other": "与数据库系统无关",
}


def _aggregate_jev_only(jev: dict, has_abstract: bool) -> dict:
    """Jev-only fallback: usable, but its probabilities are not calibrated.

    On the 60-paper dev set Jev's precision was 78% against DeepSeek's 97%, so
    a Jev-only run never asserts `drop` on a paper it is unsure about.
    """
    artifact = jev.get("artifact", "")
    p = float(jev.get("dbms_essential", 0.0))
    notes = []
    if artifact in IN_SCOPE_ARTIFACTS and p >= 0.5:
        verdict = KEEP
    elif artifact in IN_SCOPE_ARTIFACTS:
        verdict = REVIEW
        notes.append(f"对象在范围内，但 Jev 认为 DBMS 并非关键（{p:.2f}）")
    elif p < 0.25:
        verdict = DROP
    else:
        verdict = REVIEW
        notes.append(f"Jev 判 {artifact}，但把握不大（{p:.2f}）")
    if not has_abstract:
        notes.append("无摘要，仅凭标题判断")
        if verdict == DROP:
            verdict = REVIEW
    return {"verdict": verdict, "confidence": round(p, 2), "artifact": artifact,
            "agreement": "jev only",
            "reason": JEV_ARTIFACT_REASONS.get(artifact, ""),
            "jev": jev, "notes": notes}


def judge(entries: list[Entry], cache: AbstractCache, args, verbose: bool = True) -> dict:
    session = _session()
    have_llm = bool(os.environ.get("LLM_API_KEY"))
    have_jev = bool(os.environ.get("JEV_API_KEY")) and not args.no_jev

    if not have_llm and not have_jev:
        raise SystemExit(
            "Neither LLM_API_KEY nor JEV_API_KEY is set. Fill one into:\n  "
            + "\n  ".join(os.path.expanduser(p) for p in DEFAULT_ENV_FILES)
            + "\n(template: config/audit.env.example)"
        )
    if not have_llm:
        print("[warn] LLM_API_KEY not set: Jev-only run, weaker precision "
              "(78% vs 97% on the dev set)", file=sys.stderr)
    if not have_jev and not args.no_jev:
        print("[warn] JEV_API_KEY not set: running DeepSeek only", file=sys.stderr)

    results: dict[str, dict] = {}
    total = len(entries)

    def work(entry: Entry) -> tuple[Entry, list[dict], dict | None]:
        abstract = cache.get(entry.title) or ""
        votes = []
        if have_llm and not args.no_llm:
            for i in range(max(1, args.votes)):
                vote = ask_deepseek(session, entry, abstract)
                if vote:
                    votes.append(vote)
                if args.votes > 1 and i + 1 < args.votes:
                    time.sleep(0.3)
        jev = ask_jev(session, entry, abstract) if have_jev else None
        return entry, votes, jev

    done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(work, e) for e in entries]
        for fut in futures:
            entry, votes, jev = fut.result()
            done += 1
            abstract = cache.get(entry.title) or ""
            row = aggregate(votes, jev, bool(abstract.strip()), args.min_confidence)
            row.update({
                "title": entry.title,
                "venue": entry.venue,
                "year": entry.year,
                "section": entry.section_path,
                "line": entry.line_idx + 1,
                "link": (entry.tail or "").strip(),
                "has_abstract": bool(abstract.strip()),
                "votes": votes,
            })
            results[normalize_title(entry.title)] = row
            if verbose:
                flag = {"keep": "  ok ", "review": " ??  ", "drop": "DROP "}[row["verdict"]]
                print(f"[{done:>3}/{total}] {flag} {entry.title[:78]}", file=sys.stderr)
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def write_report(results: dict, entries: list[Entry], origin: str, out_md: Path,
                 out_json: Path, model_note: str) -> str:
    rows = list(results.values())
    counts = Counter(r["verdict"] for r in rows)
    drops = [r for r in rows if r["verdict"] == DROP]
    reviews = [r for r in rows if r["verdict"] == REVIEW]
    no_abs = [r for r in rows if not r["has_abstract"]]

    lines = [
        "# AI4DB 范畴审查报告",
        "",
        f"- 审查范围：{origin}",
        f"- 条目数：**{len(rows)}**",
        f"- 判定：保留 **{counts.get(KEEP, 0)}** ／ 复核 **{counts.get(REVIEW, 0)}** "
        f"／ 建议移除 **{counts.get(DROP, 0)}**",
        f"- 判定依据：{model_note}",
        f"- 无摘要（仅凭标题判断）：{len(no_abs)}",
        "",
        "判定标准：一篇论文只有当 **DBMS 是研究对象**（论文改动、操作、度量的是数据库系统本身）"
        "才算在范围内；只是读写关系型数据、生成 SQL 的不算。",
        "",
    ]
    if drops:
        lines += ["## 建议移除", "",
                  "| 行 | 标题 | 小节 | 对象 | 理由 |",
                  "| --- | --- | --- | --- | --- |"]
        for r in sorted(drops, key=lambda r: r["line"]):
            lines.append(f"| {r['line']} | {r['title'][:70]} | {_leaf(r['section'])} | "
                         f"{r['artifact']} | {_esc(r.get('reason') or _first_note(r))} |")
        lines.append("")
    if reviews:
        lines += ["## 需要人工复核", "",
                  "| 行 | 标题 | 小节 | 对象 | 置信度 | 说明 |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for r in sorted(reviews, key=lambda r: r["line"]):
            lines.append(f"| {r['line']} | {r['title'][:70]} | {_leaf(r['section'])} | "
                         f"{r['artifact']} | {r['confidence']:.2f} | "
                         f"{_esc('; '.join(r['notes']) or r.get('reason', ''))} |")
        lines.append("")
    kept = [r for r in rows if r["verdict"] == KEEP]
    if kept:
        lines += ["## 判定保留", "",
                  "| 行 | 标题 | 对象 | 理由 |",
                  "| --- | --- | --- | --- |"]
        for r in sorted(kept, key=lambda r: r["line"]):
            lines.append(f"| {r['line']} | {r['title'][:70]} | {r['artifact']} | "
                         f"{_esc(r.get('reason') or '')} |")
        lines.append("")
    if no_abs:
        lines += ["## 未取到摘要（结论仅供参考）", ""]
        lines += [f"- {r['title']}" for r in sorted(no_abs, key=lambda r: r["line"])]
        lines.append("")

    text = "\n".join(lines)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(text, encoding="utf-8")
    payload = {
        "rubric_version": RUBRIC_VERSION,
        "origin": origin,
        "counts": dict(counts),
        "results": sorted(rows, key=lambda r: r["line"]),
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return text


def _model_note(args) -> str:
    if args.no_llm:
        head = "Jev 独立判定（仅此一路）"
    elif args.no_jev:
        head = f"DeepSeek 判定 ×{args.votes}"
    else:
        head = f"DeepSeek 判定 ×{args.votes} + Jev 1.14 独立复核"
    return f"{head}，rubric {RUBRIC_VERSION}"


def _leaf(path: str) -> str:
    return (path or "").split(" > ")[-1]


def _esc(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _first_note(row: dict) -> str:
    notes = row.get("notes") or []
    return notes[0] if notes else ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(
        description="Audit README entries: is a database system the object of this work?")
    scope = p.add_mutually_exclusive_group()
    scope.add_argument("--all", action="store_true", help="audit every entry (default)")
    scope.add_argument("--git-since", help="audit entries added since this git ref")
    scope.add_argument("--recent-commits", type=int,
                       help="audit entries added by the last N README commits")
    p.add_argument("--section", help="only entries whose section path contains this")
    p.add_argument("--match", help="only entries whose title contains this")
    p.add_argument("--limit", type=int, help="stop after N papers (smoke test)")
    p.add_argument("--votes", type=int, default=3,
                   help="DeepSeek passes per paper; >1 makes disagreement visible (default 3)")
    p.add_argument("--min-confidence", type=float, default=0.6,
                   help="below this a 'keep' is softened to 'review' (default 0.6)")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--no-jev", action="store_true", help="DeepSeek only")
    p.add_argument("--no-llm", action="store_true", help="Jev only")
    p.add_argument("--cache-dir", default=".ml4db/audit")
    p.add_argument("--refresh", action="store_true", help="ignore cached abstracts")
    p.add_argument("--rejudge", action="store_true", help="ignore cached verdicts")
    p.add_argument("--env-file", action="append",
                   help="credentials file (repeatable); defaults to ~/.config/ml4db/*.env")
    p.add_argument("--out-md", default=".ml4db/audit/report.md")
    p.add_argument("--out-json", default=".ml4db/audit/report.json")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    used = load_env(args.env_file or DEFAULT_ENV_FILES)
    if used:
        print("[env] " + ", ".join(used), file=sys.stderr)

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    all_entries = parse_entries(readme)
    entries, origin = select_entries(all_entries, args)
    if not entries:
        print("no entries selected", file=sys.stderr)
        return 1

    cache_dir = Path(args.cache_dir)
    if not cache_dir.is_absolute():
        cache_dir = REPO_ROOT / cache_dir
    cache = AbstractCache(cache_dir / "abstracts.json", refresh=args.refresh)
    resolve_abstracts(entries, cache, args)

    verdict_file = cache_dir / "verdicts.json"
    results: dict = {}
    if verdict_file.is_file() and not args.rejudge:
        try:
            cached = json.loads(verdict_file.read_text(encoding="utf-8"))
        except ValueError:
            cached = {}
        if cached.get("rubric_version") == RUBRIC_VERSION:
            results = cached.get("results", {})

    todo = [e for e in entries if normalize_title(e.title) not in results]
    if todo:
        fresh = judge(todo, cache, args)
        results.update(fresh)
        verdict_file.parent.mkdir(parents=True, exist_ok=True)
        verdict_file.write_text(json.dumps(
            {"rubric_version": RUBRIC_VERSION, "results": results},
            ensure_ascii=False, indent=1), encoding="utf-8")
    elif results:
        print(f"[cache] all {len(entries)} verdicts reused (rubric {RUBRIC_VERSION})",
              file=sys.stderr)

    selected = [r for r in results.values()
                if any(normalize_title(e.title) == normalize_title(r["title"]) for e in entries)]
    note = _model_note(args)

    out_md = Path(args.out_md)
    out_json = Path(args.out_json)
    if not out_md.is_absolute():
        out_md = REPO_ROOT / out_md
    if not out_json.is_absolute():
        out_json = REPO_ROOT / out_json
    text = write_report({normalize_title(r["title"]): r for r in selected}, entries,
                        origin, out_md, out_json, note)

    counts = Counter(r["verdict"] for r in selected)
    print(f"\n{len(selected)} papers: keep {counts.get(KEEP, 0)}, "
          f"review {counts.get(REVIEW, 0)}, drop {counts.get(DROP, 0)}")
    print(f"report: {out_md}\njson:   {out_json}")
    for r in sorted(selected, key=lambda r: r["line"]):
        if r["verdict"] == DROP:
            print(f"  DROP  L{r['line']:<5} {r['title'][:70]}  [{r['artifact']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
