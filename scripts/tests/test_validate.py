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


def test_double_bracket_arxiv_link_is_valid():
    entry = "* X: A Paper (arXiv 2026) [[arXiv]](https://arxiv.org/abs/2610.00001)"
    new = insert_entries(BASE, {"Data Access > Configuration Tuning": [entry]})
    report = validate_additions(BASE, new)
    assert report.ok, report.errors


def test_restructure_allows_pure_moves():
    from ml4db.validate import validate_restructure

    old = BASE
    moved = "* Alpha: Tuning with Machine Learning (SIGMOD 2020)"
    new = BASE.replace(moved + "\n", "")
    new = new.replace("## Data Access", "## New Section\n" + moved + "\n\n## Data Access")
    report = validate_restructure(old, new, ["## New Section"])
    assert report.ok, report.errors


def test_restructure_rejects_edited_entry():
    from ml4db.validate import validate_restructure

    old = BASE
    moved = "* Alpha: Tuning with Machine Learning (SIGMOD 2020)"
    new = BASE.replace(moved + "\n", "")
    new = new.replace("## Data Access", "## New Section\n" + moved.replace("2020", "2021") + "\n\n## Data Access")
    report = validate_restructure(old, new, ["## New Section"])
    assert not report.ok


# --- validate_removal: deleting out-of-scope entries ----------------------

def test_removal_of_planned_lines_is_ok():
    from ml4db.validate import validate_removal
    old = ("## A\n"
           "* Keep Me (VLDB 2020) [DOI](https://doi.org/10.1/a)\n"
           "* Drop Me (VLDB 2021) [DOI](https://doi.org/10.1/b)\n")
    new = ("## A\n"
           "* Keep Me (VLDB 2020) [DOI](https://doi.org/10.1/a)\n")
    report = validate_removal(old, new, ["* Drop Me (VLDB 2021) [DOI](https://doi.org/10.1/b)"])
    assert report.ok, report.errors
    assert report.added == 1


def test_removal_rejects_an_unplanned_deletion():
    from ml4db.validate import validate_removal
    old = ("## A\n"
           "* Keep Me (VLDB 2020) [DOI](https://doi.org/10.1/a)\n"
           "* Also Keep (VLDB 2021) [DOI](https://doi.org/10.1/b)\n")
    new = "## A\n* Keep Me (VLDB 2020) [DOI](https://doi.org/10.1/a)\n"
    report = validate_removal(old, new, [])  # plan says remove nothing
    assert not report.ok


def test_removal_rejects_added_lines():
    from ml4db.validate import validate_removal
    old = "## A\n* A Paper (VLDB 2020) [DOI](https://doi.org/10.1/a)\n"
    new = ("## A\n* A Paper (VLDB 2020) [DOI](https://doi.org/10.1/a)\n"
           "* Sneaky (VLDB 2021) [DOI](https://doi.org/10.1/b)\n")
    report = validate_removal(old, new, [])
    assert not report.ok
    assert any("must not add" in e for e in report.errors)


def test_removal_rejects_heading_changes():
    from ml4db.validate import validate_removal
    old = "## A\n* A Paper (VLDB 2020) [DOI](https://doi.org/10.1/a)\n"
    new = "## A Renamed\n* A Paper (VLDB 2020) [DOI](https://doi.org/10.1/a)\n"
    report = validate_removal(old, new, [])
    assert not report.ok
    assert any("heading" in e for e in report.errors)


def test_removal_rejects_an_edited_entry():
    from ml4db.validate import validate_removal
    old = ("## A\n* A Paper (VLDB 2020) [DOI](https://doi.org/10.1/a)\n"
           "* Other (VLDB 2021) [DOI](https://doi.org/10.1/b)\n")
    # the surviving entry was silently reworded
    new = "## A\n* A Paper (VLDB 2099) [DOI](https://doi.org/10.1/a)\n"
    report = validate_removal(old, new, ["* Other (VLDB 2021) [DOI](https://doi.org/10.1/b)"])
    assert not report.ok
