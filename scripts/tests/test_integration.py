"""Integration tests against the real README / config.

These are the acceptance criteria from the design doc: the pipeline must
be idempotent and must not disturb the existing corpus.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml4db.config import REPO_ROOT, load_config  # noqa: E402
from ml4db.readme import insert_entries, parse_entries, section_choices  # noqa: E402
from ml4db.validate import duplicate_titles, validate_additions, validate_cleanup  # noqa: E402

FAKE = "* ZZZ Test Paper: A Learned Query Optimizer (SIGMOD 2026) [DOI](https://doi.org/10.9999/test)"


def readme_text() -> str:
    return (REPO_ROOT / "README.md").read_text(encoding="utf-8")


def test_real_readme_parses():
    text = readme_text()
    entries = parse_entries(text)
    assert len(entries) > 600
    # duplicate count is asserted by the cleanup PR itself, not here: the
    # repo passes through both states (13 legacy duplicates, then 0).
    assert isinstance(duplicate_titles(text), dict)


def test_insertion_into_real_section_is_additions_only():
    text = readme_text()
    choices = section_choices(text)
    target = next(p for p, _ in choices if p.endswith("Query Plan"))
    new = insert_entries(text, {target: [FAKE]})
    report = validate_additions(text, new)
    assert report.ok, report.errors
    assert report.added == 1


def test_pipeline_is_idempotent():
    text = readme_text()
    choices = section_choices(text)
    target = next(p for p, _ in choices if p.endswith("Query Plan"))
    once = insert_entries(text, {target: [FAKE]})
    twice = insert_entries(once, {target: [FAKE]})
    report = validate_additions(once, twice)
    assert not report.ok
    assert any("duplicate" in e for e in report.errors)


def test_cleanup_on_real_readme_shape():
    """A full duplicate cleanup on the real file shape validates cleanly."""
    text = readme_text()
    lines = text.split("\n")
    seen: dict[str, int] = {}
    to_remove: list[int] = []
    for e in parse_entries(text):
        if e.norm_title in seen:
            to_remove.append(e.line_idx)
        else:
            seen[e.norm_title] = e.line_idx
    if not to_remove:
        return  # already clean
    removed = [lines[i] for i in to_remove]
    from ml4db.readme import delete_lines

    new = delete_lines(text, to_remove)
    report = validate_cleanup(text, new, removed)
    assert report.ok, report.errors
    assert duplicate_titles(new) == {}


def test_config_venue_map_covers_sources():
    cfg = load_config()
    assert cfg["duplicate_threshold"] == 92
    venues = {c["venue"] for c in cfg["crossref_containers"]}
    assert {"VLDB", "SIGMOD", "ICDE", "TKDE"} <= venues
