import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml4db.config import Candidate  # noqa: E402
from ml4db.screen import ACCEPT, REJECT, _jev_one, _jev_questions, _parse  # noqa: E402

SECTIONS = [
    ("Data Access > Configuration Tuning", "Configuration Tuning"),
    ("Query Optimization > Query Plan", "Query Plan"),
    ("Text-to-SQL", "Text-to-SQL"),
]


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return FakeResponse(self.payload)


def cand(title="An LLM Agent for Database Knob Tuning"):
    return Candidate(title=title, venue="arXiv", year=2026, source="arxiv",
                     published="2026-01-01", abstract="We tune DBMS knobs with an LLM agent.")


def test_questions_cover_sections_and_types():
    q = _jev_questions(SECTIONS)
    assert q["section"]["type"] == "choice"
    assert set(q["section"]["criteria"]) == {p for p, _ in SECTIONS}
    assert q["in_scope"]["type"] == "noul"
    assert q["notable"]["type"] == "noul"


def test_accept_path_maps_section_and_notable():
    payload = {"answers": {
        "in_scope": {"type": "noul", "noul": 0.93},
        "section": {"type": "choice", "choice": "Data Access > Configuration Tuning",
                    "confidence": 0.81},
        "notable": {"type": "noul", "noul": 0.7},
    }, "consumed": "0.00001"}
    session = FakeSession(payload)
    c = cand()
    verdict = _jev_one(session, "https://example.test", "k", "m", c,
                       _jev_questions(SECTIONS), {p for p, _ in SECTIONS})
    assert verdict["decision"] == ACCEPT
    assert c.section == "Data Access > Configuration Tuning"
    assert c.notable is True
    assert session.calls[0]["headers"]["Authorization"] == "Bearer k"


def test_hallucinated_section_is_dropped():
    payload = {"answers": {
        "in_scope": {"type": "noul", "noul": 0.9},
        "section": {"type": "choice", "choice": "A Section That Does Not Exist", "confidence": 0.9},
        "notable": {"type": "noul", "noul": 0.9},
    }}
    c = cand()
    verdict = _jev_one(FakeSession(payload), "u", "k", "m", c,
                       _jev_questions(SECTIONS), {p for p, _ in SECTIONS})
    assert verdict["decision"] == REJECT
    assert c.section == ""


def test_out_of_scope_is_rejected_even_with_section():
    payload = {"answers": {
        "in_scope": {"type": "noul", "noul": 0.1},
        "section": {"type": "choice", "choice": "Text-to-SQL", "confidence": 0.4},
        "notable": {"type": "noul", "noul": 0.2},
    }}
    c = cand("Vector Search with Learned Indexes")
    verdict = _jev_one(FakeSession(payload), "u", "k", "m", c,
                       _jev_questions(SECTIONS), {p for p, _ in SECTIONS})
    assert verdict["decision"] == REJECT


def test_parse_tolerates_code_fences():
    text = '```json\n{"results":[{"id":"a","decision":"accept","reason":"x"}]}\n```'
    out = _parse(text)
    assert out and out[0]["id"] == "a"


def _verdict(uid, decision="accept", section="Text-to-SQL", ai_core=True, notable=True):
    return {"id": uid, "decision": decision, "section": section,
            "ai_core": ai_core, "notable": notable}


def test_combine_requires_unanimous_accept():
    from ml4db.screen import combine

    cands = [cand("A"), cand("B"), cand("C"), cand("D")]
    for i, c in enumerate(cands):
        c.uid = f"id{i}"
    allowed = {"Text-to-SQL"}
    llm = [_verdict("id0"), _verdict("id1"), _verdict("id2", decision="reject"), _verdict("id3")]
    jev = [_verdict("id0"), _verdict("id1", decision="reject"), _verdict("id2"), _verdict("id3")]
    kept, dropped, stats = combine(llm, jev, cands, allowed)
    assert [c.uid for c in kept] == ["id0", "id3"]
    assert stats["only_llm"] == 1 and stats["only_jev"] == 1


def test_combine_drops_when_ml_only_motivation():
    from ml4db.screen import combine

    c = cand("How Much Can RocksDB Chew?")
    c.uid = "rocks"
    kept, dropped, stats = combine(
        [_verdict("rocks", section="Text-to-SQL", ai_core=False)],
        [_verdict("rocks", section="Text-to-SQL", ai_core=False)], [c], {"Text-to-SQL"})
    assert kept == [] and stats["ai_core_conflict"] == 1


def test_combine_rejects_invented_section():
    from ml4db.screen import combine

    c = cand("X")
    c.uid = "x"
    kept, _, _ = combine([_verdict("x", section="Nowhere")], [_verdict("x", section="Nowhere")],
                         [c], {"Text-to-SQL"})
    assert kept == []


def test_ai_core_policy_both_vs_llm():
    from ml4db.screen import combine

    c = cand("Learned Index Under Concurrent Inserts")
    c.uid = "li"
    llm_v = [_verdict("li", ai_core=True)]
    jev_v = [_verdict("li", ai_core=False)]
    kept_llm, _, _ = combine(llm_v, jev_v, [c], {"Text-to-SQL"}, ai_core_policy="llm")
    kept_both, _, _ = combine(llm_v, jev_v, [c], {"Text-to-SQL"}, ai_core_policy="both")
    assert len(kept_llm) == 1 and kept_both == []
