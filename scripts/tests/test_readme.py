import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml4db.readme import (delete_lines, insert_entries, parse_entries,  # noqa: E402
                          parse_sections, section_choices)

FIXTURE = """# Title

Table of Contents
=================
- [Data Access](#data-access)

## Data Access
### Configuration Tuning
* Alpha: Tuning with Machine Learning (SIGMOD 2020)
* Beta: Another Tuning Paper (VLDB 2021)

### Physical Design
* Gamma: Learned Index (ICDE 2022)

## Query Optimization
### Cardinality Estimation
* Delta: Learned Cardinality (TKDE 2023)
"""


def test_parse_sections_paths():
    sections = {s.path for s in parse_sections(FIXTURE)}
    assert "Data Access > Configuration Tuning" in sections
    assert "Query Optimization > Cardinality Estimation" in sections


def test_parse_entries_fields():
    entries = parse_entries(FIXTURE)
    assert len(entries) == 4
    first = entries[0]
    assert first.title == "Alpha: Tuning with Machine Learning"
    assert (first.venue, first.year) == ("SIGMOD", 2020)
    assert first.section_path == "Data Access > Configuration Tuning"
    assert not first.has_link


def test_insert_appends_after_last_entry_of_section():
    new = insert_entries(FIXTURE, {
        "Data Access > Configuration Tuning": ["* Epsilon: New Tuner (SIGMOD 2026) [DOI](https://doi.org/10.1/x)"],
    })
    lines = new.split("\n")
    eps = next(i for i, l in enumerate(lines) if "Epsilon" in l)
    gamma = next(i for i, l in enumerate(lines) if "Gamma" in l)
    assert eps < gamma  # stayed inside Configuration Tuning
    assert lines[eps - 1].startswith("* Beta")


def test_insert_unknown_section_raises():
    try:
        insert_entries(FIXTURE, {"Nope > Nothing": ["* X (Y 2020)"]})
    except KeyError:
        return
    raise AssertionError("expected KeyError")


def test_delete_lines_removes_exact_index():
    lines = FIXTURE.split("\n")
    idx = next(i for i, l in enumerate(lines) if "Beta" in l)
    out = delete_lines(FIXTURE, [idx])
    assert "Beta" not in out
    assert len(out.split("\n")) == len(lines) - 1


def test_section_choices_excludes_empty_sections():
    choices = dict(section_choices(FIXTURE))
    assert "Data Access > Configuration Tuning" in choices
    assert not any(p.startswith("Table of Contents") for p in choices)
