import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml4db.readme import delete_lines, insert_entries  # noqa: E402
from ml4db.validate import (duplicate_titles, validate_additions,  # noqa: E402
                            validate_cleanup)

BASE = """## Data Access
### Configuration Tuning
* Alpha: Tuning with Machine Learning (SIGMOD 2020)
* Beta: Another Tuning Paper (VLDB 2021)

## Query Optimization
* GLO: Towards Generalized Learned Query Optimization (ICDE 2024)
"""

GOOD = "* Epsilon: New Tuner (SIGMOD 2026) [DOI](https://doi.org/10.1145/123.456)"


def test_valid_addition_passes():
    new = insert_entries(BASE, {"Data Access > Configuration Tuning": [GOOD]})
    report = validate_additions(BASE, new)
    assert report.ok, report.errors
    assert report.added == 1


def test_pr36_style_entry_without_venue_and_year_fails():
    # exactly the PR #36 failure: title only, no (venue year), no link
    new = insert_entries(BASE, {"Data Access > Configuration Tuning": ["* Epsilon: New Tuner"]})
    report = validate_additions(BASE, new)
    assert not report.ok
    assert any("malformed" in e for e in report.errors)


def test_entry_without_link_fails():
    new = insert_entries(BASE, {"Data Access > Configuration Tuning": [
        "* Epsilon: New Tuner (SIGMOD 2026)"]})
    report = validate_additions(BASE, new)
    assert not report.ok
    assert any("malformed" in e for e in report.errors)


def test_deleting_existing_line_fails():
    lines = BASE.split("\n")
    idx = next(i for i, l in enumerate(lines) if "Beta" in l)
    new = insert_entries(delete_lines(BASE, [idx]),
                         {"Data Access > Configuration Tuning": [GOOD]})
    report = validate_additions(BASE, new)
    assert not report.ok
    assert any("modified or removed" in e for e in report.errors)


def test_refomartting_fails():
    new = BASE.replace("(SIGMOD 2020)", "(SIGMOD  2020)")
    new = insert_entries(new, {"Data Access > Configuration Tuning": [GOOD]})
    report = validate_additions(BASE, new)
    assert not report.ok


def test_preexisting_duplicates_are_grandfathered():
    legacy = BASE + "* GLO: Towards Generalized Learned Query Optimization (ICDE 2024)\n"
    assert duplicate_titles(legacy)
    new = insert_entries(legacy, {"Data Access > Configuration Tuning": [GOOD]})
    report = validate_additions(legacy, new)
    assert report.ok, report.errors


def test_duplicate_of_existing_entry_fails():
    dup = "* Alpha: Tuning with Machine Learning (SIGMOD 2024) [DOI](https://doi.org/10.1/x)"
    new = insert_entries(BASE, {"Data Access > Configuration Tuning": [dup]})
    report = validate_additions(BASE, new)
    assert not report.ok
    assert any("duplicates an existing entry" in e for e in report.errors)


def test_duplicate_within_batch_fails():
    new = insert_entries(BASE, {"Data Access > Configuration Tuning": [GOOD,
        "* Epsilon: New Tuner (VLDB 2026) [DOI](https://doi.org/10.1/y)"]})
    report = validate_additions(BASE, new)
    assert not report.ok
    assert any("within this batch" in e for e in report.errors)


def test_cleanup_validator_accepts_exact_removal():
    lines = BASE.split("\n")
    idx = next(i for i, l in enumerate(lines) if "Beta" in l)
    new = delete_lines(BASE, [idx])
    report = validate_cleanup(BASE, new, [lines[idx]])
    assert report.ok, report.errors


def test_cleanup_validator_rejects_extra_change():
    lines = BASE.split("\n")
    idx = next(i for i, l in enumerate(lines) if "Beta" in l)
    new = delete_lines(BASE, [idx]).replace("(SIGMOD 2020)", "(SIGMOD 2021)")
    report = validate_cleanup(BASE, new, [lines[idx]])
    assert not report.ok
