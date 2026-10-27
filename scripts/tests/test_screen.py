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
