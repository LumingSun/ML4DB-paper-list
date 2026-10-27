import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from ml4db.normalize import normalize_title, parse_venue_year, token_set_ratio  # noqa: E402


@pytest.mark.parametrize(
    "a,b",
    [
        ("SageDB: A Learned Database System", "sagedb - a learned database system"),
        ("The Case for Learned In-Memory Joins", "The case for learned in-memory joins."),
        ("AStore: Uniformed Adaptive Learned Index and Cache for RDMA-enabled Key-Value Store",
         "AStore: Uniformed Adaptive Learned Index and Cache for RDMA-Enabled Key-Value Store"),
    ],
)
def test_same_paper_scores_high(a, b):
    assert token_set_ratio(a, b) >= 92


def test_distinct_papers_score_low():
    a = "Sample-Efficient Cardinality Estimation Using Geometric Deep Learning"
    b = "Robust Query Driven Cardinality Estimation under Changing Workloads"
    assert token_set_ratio(a, b) < 92


def test_normalize_strips_latex_and_punctuation():
    assert normalize_title(r"{\lambda}-Tune: Harnessing LLMs!") == "tune harnessing llms"


@pytest.mark.parametrize(
    "raw,venue,year",
    [
        ("SIGMOD 2021", "SIGMOD", 2021),
        ("DEEM@SIGMOD2018", "DEEM@SIGMOD", 2018),
        ("arXiv 2025", "arXiv", 2025),
        ("Proceedings of the ACM on Management of Data", "Proceedings of the ACM on Management of Data", None),
        ("CIDR2019", "CIDR", 2019),
    ],
)
def test_parse_venue_year(raw, venue, year):
    assert parse_venue_year(raw) == (venue, year)
