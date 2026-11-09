"""The only place a model is involved.

Contract: the model sees candidate ids, titles, abstracts and the list of
existing sections.  It answers {id, decision, section?, reason}.  It has
no field in which to invent a title, venue, year or link, and any id or
section it returns that we did not offer is discarded.
"""
from __future__ import annotations

import json
import os
import time

import requests

from .config import Candidate

ACCEPT, REJECT = "accept", "reject"

SCOPE = """You are curating a paper list for AI4DB / ML4DB: machine learning applied to
database systems, and LLM/agent systems that operate or build database systems.

DECIDE BY THE OBJECT OF STUDY, NOT BY THE DATA.
A paper is in scope only if a DATABASE SYSTEM (DBMS) is what the paper changes,
operates, builds or measures: its query engine, optimizer, storage and index
structures, transactions, catalog and schema, knobs, workload, physical design,
or the act of running and maintaining a DBMS. Working "on tables" or "on data"
is NOT sufficient. A paper whose real object is a business question, a dashboard,
a data pipeline, an ontology, a semantic layer or an analytics answer is out of
scope even when it reads relational data, writes SQL, and is published at
VLDB/SIGMOD.

IN SCOPE (each must still pass the object-of-study test above):
- Learned DB components: cardinality/cost estimation, learned indexes and filters,
  learned query optimization or rewriting, learned query execution and scheduling,
  knob/configuration tuning, physical design, partitioning, materialized views,
  buffer pool and caching, workload forecasting and diagnosis, learned storage.
- Text-to-SQL / NL2SQL / NL2Cypher / NL2Query: mapping a natural-language question
  to a database query language, plus its schema linking, benchmarks, verification
  and error analysis.
- LLM/agent for DBMS: database copilots, autonomous DBA agents, agents that
  diagnose, tune, migrate or repair a DBMS, generate or repair SQL/schema/engine
  code, and benchmarks that evaluate an LLM or agent ON database tasks.

OUT OF SCOPE (reject even when the paper mentions SQL, tables or a database):
- LLM/agent answering business or analytical questions over data while the DBMS is
  not the object: BI and dashboard agents, "chat with your data", metric or
  semantic layers, data catalogs, data discovery, data preparation and cleaning,
  table/column annotation or documentation, ETL and data-engineering pipelines,
  knowledge-graph or ontology construction, spreadsheet or document analytics.
- Vector databases / vector search / ANN indexes, RAG, GraphRAG,
  knowledge-graph-only work, recommender systems.
- Incidental ML: a database systems paper that only mentions AI as motivation, or
  an AI paper that only mentions databases as a convenient data source.

QUALITY BAR: the paper must plausibly be a systems or algorithms contribution that
belongs in a database-systems reading list. Benchmarks, surveys and position
papers count only when they are about the above topics.

FINAL TEST before accepting: would a database-systems researcher recognise this
contribution as work on a database system? If the honest answer is "this is really
an LLM/data-science paper that happens to use SQL", reject it.

Pick the single best section for each accepted paper from the EXACT section list
provided. Never invent a section name. If nothing fits, reject the paper.

AI CORE: also decide whether machine learning / LLMs are the paper's *contribution*
(the method that does the work) rather than mere motivation or a passing mention.
A storage paper that says "realtime AI serving" in its motivation is NOT AI-core.
"""


def _section_block(sections: list[tuple[str, str]], hints: dict | None = None) -> str:
    hints = hints or {}
    return "\n".join(f"- {path}" + (f" :: {hints[path]}" if path in hints else "")
                     for path, _ in sections)


def build_prompt(batch: list[Candidate], sections: list[tuple[str, str]],
                 hints: dict | None = None) -> str:
    payload = [
        {
            "id": c.uid,
            "title": c.title,
            "venue": f"{c.venue} {c.year}",
            "abstract": (c.abstract or "")[:700],
        }
        for c in batch
    ]
    return (
        SCOPE
        + "\n\nEXACT SECTION LIST (paths are ' > '-separated heading titles):\n"
        + _section_block(sections, hints)
        + "\n\nCANDIDATES:\n"
        + json.dumps(payload, ensure_ascii=False, indent=1)
        + '\n\nReturn ONLY JSON: {"results":[{"id":"...","decision":"accept"|"reject",'
          '"section":"<exact path, accept only>","ai_core":true|false,"notable":true|false,'
          '"reason":"<max 20 words>"}]}'
    )


def _apply(verdicts: list[dict], batch: list[Candidate],
           allowed: set[str]) -> tuple[list[Candidate], list[dict]]:
    by_id = {c.uid: c for c in batch}
    kept, dropped = [], []
    for v in verdicts:
        c = by_id.get(v.get("id", ""))
        if c is None:
            dropped.append({"title": "?", "reason": f"unknown id {v.get('id')!r}"})
            continue
        if v.get("decision") == ACCEPT and v.get("section") in allowed:
            c.decision, c.section = ACCEPT, v["section"]
            c.notable = bool(v.get("notable"))
            c.ai_core = bool(v.get("ai_core"))
            c.reason = str(v.get("reason", ""))[:200]
            kept.append(c)
        else:
            c.decision = REJECT
            c.reason = str(v.get("reason", ""))[:200]
            dropped.append({"title": c.title, "reason": f"model rejected: {c.reason}"})
    return kept, dropped


def _parse(text: str) -> list[dict] | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end < 0:
            return None
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    results = data.get("results") if isinstance(data, dict) else data
    if not isinstance(results, list):
        return None
    return results


def screen_api(cands: list[Candidate], sections: list[tuple[str, str]], cfg: dict,
               batch_size: int = 10, retries: int = 2) -> tuple[list[Candidate], list[dict]]:
    """Screen through an OpenAI-compatible chat completions endpoint.

    Fails closed: a batch that cannot be parsed after retries is dropped
    rather than guessed at.
    """
    base = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    key = os.environ.get("LLM_API_KEY", "")
    if not key:
        raise RuntimeError("LLM_API_KEY is not set; refusing to guess paper relevance")
    url = f"{base}/chat/completions"
    allowed = {p for p, _ in sections}
    kept: list[Candidate] = []
    dropped: list[dict] = []
    for i in range(0, len(cands), batch_size):
        batch = cands[i:i + batch_size]
        verdicts = None
        for attempt in range(retries + 1):
            try:
                r = requests.post(
                    url,
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": model,
                        "temperature": 0,
                        "messages": [
                            {"role": "system", "content": "You are a precise paper classifier. Output JSON only."},
                            {"role": "user", "content": build_prompt(batch, sections, cfg.get("section_hints"))},
                        ],
                    },
                    timeout=120,
                )
                r.raise_for_status()
                verdicts = _parse(r.json()["choices"][0]["message"]["content"])
            except Exception:  # noqa: BLE001 - retried below, then dropped
                verdicts = None
            if verdicts is not None:
                break
            time.sleep(2 * (attempt + 1))
        if verdicts is None:
            dropped += [{"title": c.title, "reason": "screener failed (batch dropped)"} for c in batch]
            continue
        k, d = _apply(verdicts, batch, allowed)
        kept += k
        dropped += d
        time.sleep(1)
    return kept, dropped


def screen_verdicts(cands: list[Candidate], sections: list[tuple[str, str]],
                    verdicts: list[dict]) -> tuple[list[Candidate], list[dict]]:
    """Apply pre-computed verdicts (agent-reviewed batch, offline runs)."""
    return _apply(verdicts, cands, {p for p, _ in sections})


def batches(cands: list[Candidate], size: int) -> list[list[Candidate]]:
    return [cands[i:i + size] for i in range(0, len(cands), size)]


# --------------------------------------------------------------------------
# Jev (TypeSafe decision model) screener: one request per paper, typed
# questions, returns a probability for "in scope", a probability-weighted
# choice for the section, and a probability for "notable".
# --------------------------------------------------------------------------

JEV_URL = "https://api.defapi.org/api/v1/decisions"
JEV_MODEL = "typesafe/jev-1.14.0"


JEV_SCOPE_IN = (
    "A database system is the object of the work: it changes, operates, builds or "
    "measures a DBMS. Learned DB components (cardinality/cost estimation, learned "
    "indexes or filters, learned query optimization/rewriting/execution, knob tuning, "
    "physical design, materialized views, buffer pool, workload diagnosis); text-to-SQL "
    "and other natural-language-to-query-language translation with its schema linking, "
    "benchmarks and verification; LLM or agent systems acting ON a DBMS (copilots, "
    "autonomous DBA agents, agents that diagnose/tune/migrate/repair a DBMS or generate "
    "and repair SQL, schema or engine code); benchmarks evaluating LLMs or agents on "
    "database tasks."
)
JEV_SCOPE_OUT = (
    "The database is only a source of data and the real object is something else: BI or "
    "dashboard agents, 'chat with your data', semantic or metric layers, data catalogs, "
    "data discovery, data preparation/cleaning/annotation, ETL and data-engineering "
    "pipelines, ontology or knowledge-graph construction, document or spreadsheet "
    "analytics. Also out: vector databases/vector search/ANN, RAG, GraphRAG, "
    "knowledge-graph-only work, recommender systems, and papers where ML is only "
    "motivation or the database is only a convenience."
)


def _jev_questions(sections: list[tuple[str, str]], hints: dict | None = None) -> dict:
    return {
        "in_scope": {
            "type": "noul",
            "instructions": (
                "Is a DATABASE SYSTEM the object of this work, so that a database-systems "
                "reading list on AI4DB / LLM4DB should collect it? Judge the object of "
                "study, not whether relational data or SQL appears. If the honest answer "
                "is 'this is an LLM or data-science paper that happens to use SQL', the "
                "answer is false."
            ),
            "criteria": {"true": JEV_SCOPE_IN, "false": JEV_SCOPE_OUT},
        },
        "section": {
            "type": "choice",
            "instructions": "Which existing section of the paper list does this paper belong to?",
            "criteria": {path: (hints or {}).get(path, desc) for path, desc in sections},
        },
        "ai_core": {
            "type": "noul",
            "instructions": (
                "Are machine learning or LLMs the paper's contribution (the method that does the "
                "work), rather than just motivation or a passing mention?"
            ),
            "criteria": {
                "true": "The ML/LLM component is the contribution (learned model, LLM agent, semantic operator).",
                "false": "ML appears only as motivation, background, or a downstream user.",
            },
        },
        "notable": {
            "type": "noul",
            "instructions": (
                "Does this paper contribute a system, a benchmark or dataset, a survey, or a "
                "new paradigm - as opposed to an incremental method variant?"
            ),
            "criteria": {
                "true": "System / benchmark / dataset / survey / new paradigm.",
                "false": "Incremental variant, prompt tweak, or single-dataset accuracy bump.",
            },
        },
    }


def _jev_one(session: requests.Session, url: str, key: str, model: str,
             cand: Candidate, questions: dict, allowed: set[str]) -> dict | None:
    state = {"title": cand.title, "venue": f"{cand.venue} {cand.year}",
             "abstract": (cand.abstract or "")[:1500]}
    for attempt in range(3):
        try:
            r = session.post(
                url,
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "state": state, "questions": questions},
                timeout=60,
            )
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            body = r.json()
            answers = body.get("answers", {})
            in_scope = float(answers.get("in_scope", {}).get("noul", 0.0))
            notable = float(answers.get("notable", {}).get("noul", 0.0))
            ai_core = float(answers.get("ai_core", {}).get("noul", 0.0))
            section = answers.get("section", {}).get("choice", "")
            conf = float(answers.get("section", {}).get("confidence", 0.0))
            cand.section = section if section in allowed else ""
            cand.notable = notable >= 0.5
            cand.ai_core = ai_core >= 0.5
            cand.decision = ACCEPT if (in_scope >= 0.5 and cand.section) else REJECT
            cand.reason = (f"p_in={in_scope:.2f} p_notable={notable:.2f} p_ai_core={ai_core:.2f} sec_conf={conf:.2f} "
                           f"cost={body.get('consumed') or 0}")
            return {
                "id": cand.uid, "decision": cand.decision,
                "section": cand.section, "notable": cand.notable, "ai_core": cand.ai_core,
                "reason": cand.reason, "cost": body.get("consumed"),
            }
        except Exception:  # noqa: BLE001 - retried, then dropped
            time.sleep(2 ** attempt)
    return None


def screen_jev(cands: list[Candidate], sections: list[tuple[str, str]], cfg: dict,
               workers: int = 6) -> tuple[list[Candidate], list[dict]]:
    """Screen with Jev-1.13 via the Decisions API (one request per paper)."""
    from concurrent.futures import ThreadPoolExecutor

    key = os.environ.get("JEV_API_KEY", "")
    if not key:
        raise RuntimeError("JEV_API_KEY is not set; refusing to guess paper relevance")
    url = os.environ.get("JEV_URL", JEV_URL)
    model = os.environ.get("JEV_MODEL", JEV_MODEL)
    questions = _jev_questions(sections, cfg.get("section_hints"))
    allowed = {p for p, _ in sections}
    kept: list[Candidate] = []
    dropped: list[dict] = []
    session = requests.Session()

    def work(c: Candidate):
        return c, _jev_one(session, url, key, model, c, questions, allowed)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for c, verdict in pool.map(work, cands):
            if verdict is None:
                dropped.append({"title": c.title, "reason": "jev request failed"})
            elif c.decision == ACCEPT:
                kept.append(c)
            else:
                dropped.append({"title": c.title, "reason": f"jev rejected: {c.reason}"})
    return kept, dropped


# --------------------------------------------------------------------------
# Two-layer confirmation: DeepSeek (or agent) + Jev must both accept, and
# both must find the ML component central.  Precision is what this list
# needs: a wrong entry costs the maintainer a manual deletion, a missed
# one is recoverable next week.
# --------------------------------------------------------------------------

def _as_map(verdicts: list[dict]) -> dict[str, dict]:
    return {v["id"]: v for v in verdicts if isinstance(v, dict) and v.get("id")}


def combine(llm: list[dict], jev: list[dict], cands: list[Candidate],
            allowed: set[str], ai_core_policy: str = "llm"
            ) -> tuple[list[Candidate], list[dict], dict]:
    lmap, jmap = _as_map(llm), _as_map(jev)
    kept: list[Candidate] = []
    dropped: list[dict] = []
    stats = {"both_accept": 0, "only_llm": 0, "only_jev": 0, "neither": 0,
             "ai_core_conflict": 0, "section_conflict": 0}
    for c in cands:
        l, j = lmap.get(c.uid), jmap.get(c.uid)
        l_ok = bool(l) and l.get("decision") == ACCEPT and l.get("section") in allowed
        j_ok = bool(j) and j.get("decision") == ACCEPT and j.get("section") in allowed
        if l_ok and j_ok:
            stats["both_accept"] += 1
            if ai_core_policy == "both":
                core_ok = bool(l.get("ai_core")) and bool(j.get("ai_core"))
            elif ai_core_policy == "any":
                core_ok = bool(l.get("ai_core")) or bool(j.get("ai_core"))
            else:  # "llm": the more accurate judge decides the ML-core question
                core_ok = bool(l.get("ai_core"))
            if not core_ok:
                stats["ai_core_conflict"] += 1
                dropped.append({"title": c.title, "reason": "ML component not central (two-layer)"})
                continue
            c.decision, c.ai_core = ACCEPT, True
            c.section = l["section"]
            if j["section"] != l["section"]:
                stats["section_conflict"] += 1
            c.notable = bool(l.get("notable"))
            kept.append(c)
        else:
            stats["only_llm" if l_ok else "only_jev" if j_ok else "neither"] += 1
            dropped.append({"title": c.title,
                            "reason": "two-layer: " + ("llm accepted only" if l_ok else
                                                       "jev accepted only" if j_ok else "both rejected")})
    return kept, dropped, stats


def screen_double(cands: list[Candidate], sections: list[tuple[str, str]], cfg: dict):
    """Run both backends; require unanimity on acceptance and on AI-coredness."""
    allowed = {p for p, _ in sections}
    jev_kept, _ = screen_jev(cands, sections, cfg)
    llm_kept, _ = screen_api(cands, sections, cfg)
    jev_verdicts = [{"id": c.uid, "decision": c.decision, "section": c.section,
                     "ai_core": c.ai_core, "notable": c.notable} for c in jev_kept]
    llm_verdicts = [{"id": c.uid, "decision": c.decision, "section": c.section,
                     "ai_core": c.ai_core, "notable": c.notable} for c in llm_kept]
    return combine(llm_verdicts, jev_verdicts, cands, allowed)
