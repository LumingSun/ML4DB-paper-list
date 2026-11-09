"""Tests for the local scope auditor (scripts/audit_scope.py).

The auditor spends money and makes judgement calls, so the parts worth
pinning down are the ones that can silently mislead: the aggregation rules
that decide whether a paper is flagged, the credential/env plumbing, and the
selection of what to audit.

The load-bearing rule is that evidence can only soften a verdict
(keep -> review), never harden it, because deleting a right entry costs the
maintainer more trust than missing a wrong one.
"""
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ml4db.readme import Entry  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "audit_scope", REPO_ROOT / "scripts" / "audit_scope.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

DROP = audit.DROP
KEEP = audit.KEEP
REVIEW = audit.REVIEW


def vote(verdict, artifact="dbms_core", confidence=0.9, exclusion="none"):
    return {"verdict": verdict, "artifact": artifact, "confidence": confidence,
            "dbms_essential": True, "hard_exclusion": exclusion,
            "counterfactual_survives": False, "reason": "because"}


def jev(artifact="dbms_core", p=0.9):
    return {"artifact": artifact, "dbms_essential": p, "confidence": 0.9}


def entry(title="An LLM Agent for Database Knob Tuning", section="LLM4DB & Agent for DB"):
    return Entry(line_idx=10, raw=f"* {title} (VLDB 2026)",
                 title=title, venue="VLDB", year=2026,
                 tail="[DOI](https://doi.org/10.1/x)", section_path=section, has_link=True)


# --- aggregation: agreement ------------------------------------------------

def test_unanimous_keep_is_keep():
    row = audit.aggregate([vote(KEEP)] * 3, jev(), True, 0.6)
    assert row["verdict"] == KEEP
    assert row["agreement"] == "一致"
    assert row["artifact"] == "dbms_core"


def test_unanimous_drop_is_drop():
    row = audit.aggregate([vote(DROP, artifact="data_product")] * 3, None, True, 0.6)
    assert row["verdict"] == DROP


def test_disagreement_softens_to_review():
    row = audit.aggregate([vote(KEEP), vote(KEEP), vote(DROP, artifact="data_product")],
                          None, True, 0.6)
    assert row["verdict"] == REVIEW
    assert row["agreement"] == "不一致"


def test_jev_objection_softens_keep_but_never_flips_to_drop():
    row = audit.aggregate([vote(KEEP)] * 3, jev(artifact="data_product", p=0.05), True, 0.6)
    assert row["verdict"] == REVIEW
    assert any("Jev" in n for n in row["notes"])


def test_jev_agreement_keeps_keep():
    row = audit.aggregate([vote(KEEP)] * 3, jev(p=0.95), True, 0.6)
    assert row["verdict"] == KEEP


# --- aggregation: consistency and exclusions ------------------------------

def test_in_scope_artifact_with_drop_verdict_becomes_review():
    """A model that calls something dbms_core and then drops it is confused."""
    row = audit.aggregate([vote(DROP, artifact="dbms_core")] * 3, None, True, 0.6)
    assert row["verdict"] == REVIEW


def test_out_of_scope_artifact_with_keep_verdict_becomes_review():
    row = audit.aggregate([vote(KEEP, artifact="data_product")] * 3, None, True, 0.6)
    assert row["verdict"] == REVIEW


def test_hard_exclusion_downgrades_keep():
    row = audit.aggregate([vote(KEEP, exclusion="rag")] * 3, None, True, 0.6)
    assert row["verdict"] == DROP


def test_low_confidence_keep_becomes_review():
    row = audit.aggregate([vote(KEEP, confidence=0.3)] * 3, None, True, 0.6)
    assert row["verdict"] == REVIEW


def test_missing_abstract_never_allows_drop():
    row = audit.aggregate([vote(DROP, artifact="data_product")] * 3, None, False, 0.6)
    assert row["verdict"] == REVIEW
    assert any("无摘要" in n for n in row["notes"])


def test_no_votes_and_no_jev_is_review_not_drop():
    row = audit.aggregate([], None, True, 0.6)
    assert row["verdict"] == REVIEW


# --- aggregation: jev-only fallback --------------------------------------

def test_jev_only_keeps_in_scope_high_probability():
    row = audit.aggregate([], jev("dbms_eval", 0.8), True, 0.6)
    assert row["verdict"] == KEEP
    assert row["agreement"] == "jev only"


def test_jev_only_escalates_in_scope_low_probability():
    row = audit.aggregate([], jev("dbms_interface", 0.2), True, 0.6)
    assert row["verdict"] == REVIEW


def test_jev_only_drops_confident_data_product():
    row = audit.aggregate([], jev("data_product", 0.05), True, 0.6)
    assert row["verdict"] == DROP
    assert row["reason"]


def test_jev_only_escalates_borderline_data_product():
    row = audit.aggregate([], jev("data_product", 0.45), True, 0.6)
    assert row["verdict"] == REVIEW


# --- prompt / rubric ------------------------------------------------------

def test_rubric_judges_object_of_study_and_names_the_llm_data_failure():
    text = audit.RUBRIC
    assert "OBJECT OF STUDY" in text
    assert "data_product" in text
    assert "CSV" in text  # the counterfactual test
    for artifact in ("dbms_core", "dbms_interface", "dbms_eval",
                     "data_product", "ml_method", "other"):
        assert artifact in text


def test_prompt_carries_title_venue_section_and_abstract():
    p = audit.build_prompt(entry(), "We tune knobs with an LLM agent.")
    assert "An LLM Agent for Database Knob Tuning" in p
    assert "VLDB" in p
    assert "LLM4DB & Agent for DB" in p
    assert "We tune knobs" in p
    assert '"verdict":"keep|review|drop"' in p


def test_prompt_warns_when_abstract_missing():
    p = audit.build_prompt(entry(), "")
    assert "no abstract is available" in p
    assert "confidence below 0.5" in p


def test_jev_questions_offer_every_artifact_and_a_binary_essential_test():
    q = audit.jev_questions()
    assert q["artifact"]["type"] == "choice"
    assert set(q["artifact"]["criteria"]) == set(audit.JEV_ARTIFACTS)
    assert q["dbms_essential"]["type"] == "noul"


def test_rubric_version_is_set_so_cached_verdicts_cannot_outlive_a_rubric_change():
    assert audit.RUBRIC_VERSION


# --- json parsing robustness ---------------------------------------------

def test_loads_json_handles_fences_and_trailing_prose():
    assert audit._loads_json('```json\n{"verdict":"keep"}\n```')["verdict"] == "keep"
    assert audit._loads_json('ok: {"verdict":"drop"} hope that helps')["verdict"] == "drop"
    assert audit._loads_json("not json at all") is None


# --- credentials ----------------------------------------------------------

def test_load_env_reads_export_and_plain_forms(tmp_path, monkeypatch):
    f = tmp_path / "audit.env"
    f.write_text("# comment\nexport AAA=1\nBBB='two words'\nCCC=\"3\"\n", encoding="utf-8")
    monkeypatch.delenv("AAA", raising=False)
    monkeypatch.delenv("BBB", raising=False)
    monkeypatch.delenv("CCC", raising=False)
    used = audit.load_env([str(f)])
    assert used and used[0].endswith("audit.env")
    import os
    assert os.environ["AAA"] == "1"
    assert os.environ["BBB"] == "two words"
    assert os.environ["CCC"] == "3"


def test_load_env_does_not_override_an_existing_variable(tmp_path, monkeypatch):
    f = tmp_path / "audit.env"
    f.write_text("export KEEPME=from_file\n", encoding="utf-8")
    monkeypatch.setenv("KEEPME", "from_shell")
    audit.load_env([str(f)])
    import os
    assert os.environ["KEEPME"] == "from_shell"


def test_load_env_override_when_asked(tmp_path, monkeypatch):
    f = tmp_path / "audit.env"
    f.write_text("export OVERRIDEME=from_file\n", encoding="utf-8")
    monkeypatch.setenv("OVERRIDEME", "from_shell")
    audit.load_env([str(f)], override=True)
    import os
    assert os.environ["OVERRIDEME"] == "from_file"


def test_missing_env_file_is_ignored(tmp_path):
    assert audit.load_env([str(tmp_path / "nope.env")]) == []


# --- selection ------------------------------------------------------------

def test_select_by_section_and_match():
    entries = [entry("A Database Copilot", "LLM4DB & Agent for DB"),
               entry("A Dashboard Agent", "LLM4DB & Agent for DB"),
               entry("Learned Index", "Data Access > Physical Design")]
    args = audit.parse_args(["--section", "LLM4DB"])
    sel, origin = audit.select_entries(entries, args)
    assert len(sel) == 2 and "LLM4DB" in origin

    args = audit.parse_args(["--match", "dashboard"])
    sel, _ = audit.select_entries(entries, args)
    assert [e.title for e in sel] == ["A Dashboard Agent"]


def test_select_dedupes_by_normalised_title():
    entries = [entry("Learned Index"), entry("learned  index")]
    args = audit.parse_args(["--all"])
    sel, _ = audit.select_entries(entries, args)
    assert len(sel) == 1


def test_limit_caps_the_batch():
    entries = [entry(f"Paper {i}") for i in range(10)]
    args = audit.parse_args(["--all", "--limit", "3"])
    sel, _ = audit.select_entries(entries, args)
    assert len(sel) == 3


# --- abstract cache -------------------------------------------------------

def test_abstract_cache_roundtrip(tmp_path):
    path = tmp_path / "abstracts.json"
    cache = audit.AbstractCache(path)
    assert cache.get("A Paper") is None
    cache.put("A Paper", "text", "arxiv")
    cache.save()

    again = audit.AbstractCache(path)
    assert again.get("A Paper") == "text"
    assert again.get("a  paper") == "text"  # normalised lookup


def test_abstract_cache_empty_abstract_is_remembered_as_attempted(tmp_path):
    """An abstract we failed to find must not be retried from the search loop."""
    path = tmp_path / "abstracts.json"
    cache = audit.AbstractCache(path)
    cache.put("Missing Paper", "", "none")
    cache.save()
    again = audit.AbstractCache(path)
    assert again.get("Missing Paper") == ""


def test_arxiv_and_doi_extraction_from_entry_tail():
    e = entry()
    assert audit._doi(e) == "10.1/x"
    ax = Entry(line_idx=1, raw="x", title="t", venue="arXiv", year=2026,
               tail="[[arXiv]](https://arxiv.org/abs/2610.33817)", section_path="S",
               has_link=True)
    assert audit._arxiv_ids(ax) == "2610.33817"


# --- report ---------------------------------------------------------------

def test_report_lists_drops_reviews_and_keeps(tmp_path):
    rows = {
        "a": {"verdict": DROP, "title": "Ontology Agent", "section": "LLM4DB & Agent for DB",
              "line": 3, "artifact": "data_product", "confidence": 0.9,
              "reason": "对象是数据产品", "notes": [], "has_abstract": True},
        "b": {"verdict": REVIEW, "title": "Borderline", "section": "LLM4DB & Agent for DB",
              "line": 4, "artifact": "dbms_interface", "confidence": 0.4,
              "reason": "", "notes": ["Jev 反对"], "has_abstract": True},
        "c": {"verdict": KEEP, "title": "MongoBench", "section": "LLM4DB & Agent for DB",
              "line": 5, "artifact": "dbms_eval", "confidence": 0.9,
              "reason": "评测数据库任务", "notes": [], "has_abstract": True},
    }
    md = tmp_path / "report.md"
    js = tmp_path / "report.json"
    text = audit.write_report(rows, [], "test origin", md, js, "DeepSeek ×3")
    assert "Ontology Agent" in text and "MongoBench" in text
    assert "## 建议移除" in text and "## 需要人工复核" in text
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["rubric_version"] == audit.RUBRIC_VERSION
    assert data["counts"][DROP] == 1


def test_report_escapes_pipes_so_tables_stay_valid(tmp_path):
    rows = {"a": {"verdict": DROP, "title": "T", "section": "S", "line": 1,
                  "artifact": "other", "confidence": 0.9,
                  "reason": "a | b", "notes": [], "has_abstract": True}}
    text = audit.write_report(rows, [], "o", tmp_path / "r.md", tmp_path / "r.json", "n")
    assert "a \\| b" in text
