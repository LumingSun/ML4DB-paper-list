import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml4db import harvest as H  # noqa: E402
from ml4db.config import Candidate, load_config  # noqa: E402


def _cand(title="X"):
    return Candidate(title=title, venue="arXiv", year=2026, source="arxiv",
                     published="2026-10-01", arxiv_id="2610.00001")


def test_one_failing_source_does_not_kill_the_run(monkeypatch):
    cfg = load_config()
    monkeypatch.setattr(H, "harvest_arxiv", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(H, "harvest_crossref", lambda *a, **k: [_cand("From Crossref")])
    errors: list[str] = []
    items = H.harvest(cfg, date(2026, 9, 1), date(2026, 10, 27), errors=errors)
    assert [c.title for c in items] == ["From Crossref"]
    assert any("arxiv" in e for e in errors)


def test_all_sources_failing_raises(monkeypatch):
    cfg = load_config()
    monkeypatch.setattr(H, "harvest_arxiv", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("a")))
    monkeypatch.setattr(H, "harvest_crossref", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("c")))
    try:
        H.harvest(cfg, date(2026, 9, 1), date(2026, 10, 27))
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError")


def test_titles_are_markup_free():
    from ml4db.normalize import clean_title
    assert clean_title("Read &amp; Write") == "Read & Write"
    assert clean_title("<i>DBCooker</i> : A Harness") == "DBCooker: A Harness"
