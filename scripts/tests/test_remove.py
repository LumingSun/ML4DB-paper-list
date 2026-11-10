"""Tests for `ml4db remove`, which deletes entries planned by a scope audit."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml4db import config as cfgmod  # noqa: E402
from ml4db.main import main  # noqa: E402

README = (
    "# Title\n\n"
    "## Data Access\n"
    "* Keep Me (VLDB 2020) [DOI](https://doi.org/10.1/a)\n"
    "* Dashboard Agent (arXiv 2026) [[arXiv]](https://arxiv.org/abs/2610.00001)\n"
    "* Ontology Layer (arXiv 2026) [[arXiv]](https://arxiv.org/abs/2610.00002)\n"
)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text(README, encoding="utf-8")
    monkeypatch.setattr(cfgmod, "README", readme)
    monkeypatch.setenv("ML4DB_WORKDIR", str(tmp_path / "work"))
    return tmp_path


def plan(tmp_path, titles, name="plan.json"):
    p = tmp_path / name
    p.write_text(json.dumps(
        {"removals": [{"title": t, "artifact": "data_product", "reason": "r"} for t in titles]}),
        encoding="utf-8")
    return str(p)


def test_remove_deletes_planned_titles_only(repo, capsys):
    p = plan(repo, ["Dashboard Agent", "Ontology Layer"])
    out = repo / "out.md"
    main(["remove", "--plan", p, "--dry-run", "--out", str(out)])
    text = out.read_text(encoding="utf-8")
    assert "Keep Me" in text
    assert "Dashboard Agent" not in text and "Ontology Layer" not in text


def test_remove_fails_when_a_title_is_missing(repo):
    p = plan(repo, ["No Such Paper"])
    with pytest.raises(SystemExit) as exc:
        main(["remove", "--plan", p, "--dry-run", "--out", str(repo / "o.md")])
    assert "not found" in str(exc.value)


def test_remove_refuses_an_ambiguous_title(repo):
    readme = cfgmod.README
    readme.write_text(README + "* Keep Me (VLDB 2022) [DOI](https://doi.org/10.1/c)\n",
                      encoding="utf-8")
    p = plan(repo, ["Keep Me"])
    with pytest.raises(SystemExit) as exc:
        main(["remove", "--plan", p, "--dry-run", "--out", str(repo / "o.md")])
    assert "matches" in str(exc.value)


def test_remove_accepts_a_bare_list_plan(repo):
    p = repo / "list.json"
    p.write_text(json.dumps([{"title": "Ontology Layer"}]), encoding="utf-8")
    out = repo / "out.md"
    main(["remove", "--plan", str(p), "--dry-run", "--out", str(out)])
    assert "Ontology Layer" not in out.read_text(encoding="utf-8")
