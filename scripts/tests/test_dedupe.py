import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml4db.config import Candidate, load_config  # noqa: E402
from ml4db.filters import dedupe, find_duplicate, prefilter  # noqa: E402
from ml4db.readme import parse_entries  # noqa: E402

CORPUS = """## Query Optimization
* GLO: Towards Generalized Learned Query Optimization (ICDE 2024)
* Sample-Efficient Cardinality Estimation Using Geometric Deep Learning (VLDB 2024)
* Learning State Representations for Query Optimization with Deep Reinforcement Learning  (DEEM@SIGMOD2018)
* Learning State Representations for Query Optimization with Deep Reinforcement Learning  (DEEM@SIGMOD2018)
* The Case for Learned In-Memory Joins (arXiv 2021)
"""


def cfg():
    return load_config()


def cand(title, venue="arXiv", year=2026, **kw):
    return Candidate(title=title, venue=venue, year=year, source="arxiv",
                     published=f"{year}-01-01", **kw)


def test_exact_title_is_duplicate():
    entries = parse_entries(CORPUS)
    c = cand("GLO: Towards Generalized Learned Query Optimization")
    assert find_duplicate(c, entries, cfg()) is not None


def test_punctuation_and_case_variant_is_duplicate():
    entries = parse_entries(CORPUS)
    c = cand("The case for learned in-memory joins.")
    assert find_duplicate(c, entries, cfg()) is not None


def test_legacy_duplicate_does_not_break_matching():
    entries = parse_entries(CORPUS)
    assert len(entries) == 5  # the fixture really does hold a duplicate
    c = cand("Learning State Representations for Query Optimization with Deep Reinforcement Learning")
    assert find_duplicate(c, entries, cfg()) is not None


def test_new_title_passes():
    entries = parse_entries(CORPUS)
    c = cand("PilotScope: Steering Databases with Machine Learning Drivers")
    assert find_duplicate(c, entries, cfg()) is None


def test_within_batch_duplicate_dropped():
    entries = parse_entries(CORPUS)
    a = cand("Neo: A Learned Query Optimizer Revisited")
    b = cand("Neo: A Learned Query Optimizer Revisited", arxiv_id="2601.00001")
    kept, dropped = dedupe([a, b], entries, cfg())
    assert len(kept) == 1 and len(dropped) == 1


def test_arxiv_id_matches_even_without_title():
    entries = parse_entries(CORPUS)
    corpus = "## Text-to-SQL\n* Something (arXiv 2025) [[arXiv]](https://arxiv.org/abs/2501.12345)\n"
    e = parse_entries(corpus)
    c = cand("A Completely Different Title", arxiv_id="2501.12345")
    assert find_duplicate(c, e, cfg()) is not None


def test_prefilter_rejects_vector_and_rag():
    c = cfg()
    ok, why = prefilter([cand("Vector Database Search with Learned Indexes")], c)[0], None
    assert ok == []
    assert "excluded" in prefilter([cand("Vector Database Search with Learned Indexes")], c)[1][0]["reason"]


def test_prefilter_keeps_llm4db():
    c = cfg()
    kept, dropped = prefilter([cand("An LLM Agent for Database Knob Tuning")], c)
    assert len(kept) == 1 and not dropped


def test_short_ai_term_does_not_match_inside_words():
    """Regression: substring matching let 'ai' match 'domain'/'available'."""
    from ml4db.filters import relevance
    c = cand("A Resource-Centric Analysis of NoSQL Workloads",
             abstract="We detail the available domain options.")
    ok, why = relevance(c, cfg())
    assert not ok and why == "no AI term"


def test_full_version_variant_is_duplicate():
    """Publishers ship the same paper as "X" and "X [Full Version]"."""
    from ml4db.normalize import title_variant_key
    assert title_variant_key("BaCon: Counting Queries [Full Version]") == \
           title_variant_key("BaCon: Counting Queries")
    corpus = "## Query Optimization\n* BaCon: Counting Queries (VLDB 2026)\n"
    entries = parse_entries(corpus)
    assert find_duplicate(cand("BaCon: Counting Queries [Full Version]"), entries, cfg()) is not None
