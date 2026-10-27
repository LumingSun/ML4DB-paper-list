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

SCOPE = """You are curating a paper list for AI4DB / ML4DB research — the intersection of
machine learning and database systems.

IN SCOPE: learned query optimization, learned cardinality/cost estimation, learned
indexes, knob/configuration tuning with ML, learned query execution and scheduling,
workload forecasting and diagnosis, text-to-SQL, LLM/agent-for-DB (database copilots,
LLM-assisted tuning, LLM4DB), learned storage/partitioning/materialized views.

OUT OF SCOPE (reject without hesitation): vector databases / vector search / ANN
indexes, RAG, GraphRAG, knowledge-graph-only work, recommender systems, and papers
that mention a database but contribute nothing about ML applied to database systems
or DB systems supporting ML.

QUALITY BAR: a paper must plausibly be a systems or algorithms contribution that
belongs in a database-systems reading list. Benchmarks, surveys and position papers
are acceptable only if directly about the above topics.

Pick the single best section for each accepted paper from the EXACT section list
provided. Never invent a section name. If nothing fits, reject the paper.
"""


def _section_block(sections: list[tuple[str, str]]) -> str:
    return "\n".join(f"- {path}" for path, _ in sections)


def build_prompt(batch: list[Candidate], sections: list[tuple[str, str]]) -> str:
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
        + _section_block(sections)
        + "\n\nCANDIDATES:\n"
        + json.dumps(payload, ensure_ascii=False, indent=1)
        + '\n\nReturn ONLY JSON: {"results":[{"id":"...","decision":"accept"|"reject",'
          '"section":"<exact path, accept only>","reason":"<max 20 words>"}]}'
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
                            {"role": "user", "content": build_prompt(batch, sections)},
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
JEV_MODEL = "typesafe/jev-1.13"


def _jev_questions(sections: list[tuple[str, str]]) -> dict:
    return {
        "in_scope": {
            "type": "noul",
            "instructions": (
                "Given the paper title, venue and abstract, is this paper about machine "
                "learning applied to database systems, or about LLM/agent systems for "
                "databases, in the way a database-systems reading list would collect it?"
            ),
            "criteria": {
                "true": "Learned query optimization, cardinality/cost estimation, learned "
                        "indexes, knob tuning, learned execution/scheduling, text-to-SQL, "
                        "LLM4DB / agent-for-DB, learned physical design.",
                "false": "Vector search or RAG, GraphRAG, knowledge-graph-only, recommender "
                         "systems, or a database systems paper that applies no ML.",
            },
        },
        "section": {
            "type": "choice",
            "instructions": "Which existing section of the paper list does this paper belong to?",
            "criteria": {path: desc for path, desc in sections},
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
            section = answers.get("section", {}).get("choice", "")
            conf = float(answers.get("section", {}).get("confidence", 0.0))
            cand.section = section if section in allowed else ""
            cand.notable = notable >= 0.5
            cand.decision = ACCEPT if (in_scope >= 0.5 and cand.section) else REJECT
            cand.reason = f"p_in={in_scope:.2f} p_notable={notable:.2f} sec_conf={conf:.2f}"
            return {
                "id": cand.uid, "decision": cand.decision,
                "section": cand.section, "notable": cand.notable,
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
    questions = _jev_questions(sections)
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
