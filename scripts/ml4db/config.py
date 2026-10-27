"""Configuration loading and the Candidate record.

The Candidate is the *only* carrier of facts.  The model never sees a
mutable copy of it and never produces title/venue/year/link: it only
picks a section for, or rejects, a candidate id.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"
CONFIG_PATH = REPO_ROOT / "config" / "lexicon.yaml"


@dataclass
class Candidate:
    title: str
    venue: str
    year: int | None
    source: str  # "arxiv" | "crossref"
    published: str  # ISO date
    abstract: str = ""
    arxiv_id: str = ""
    doi: str = ""
    section: str = ""  # filled in by the screener
    decision: str = ""  # "accept" | "reject" | ""
    notable: bool = False  # system / benchmark / paradigm, not an incremental variant
    ai_core: bool = False  # ML/LLM is the contribution, not just motivation
    reason: str = ""
    uid: str = ""  # stable id for verdict matching

    def __post_init__(self) -> None:
        if not self.uid:
            self.uid = self.arxiv_id or self.doi or self.title

    @property
    def link(self) -> str:
        if self.arxiv_id:
            return f"[[arXiv]](https://arxiv.org/abs/{self.arxiv_id})"
        if self.doi:
            return f"[DOI](https://doi.org/{self.doi})"
        return ""

    def entry_line(self, link_mode: str = "always") -> str:
        year = "" if self.year is None else f" {self.year}"
        line = f"* {self.title} ({self.venue}{year})"
        if link_mode == "always" and self.link:
            line += f" {self.link}"
        return line

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Candidate":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def load_config(path: Path | None = None) -> dict:
    with open(path or CONFIG_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def today() -> date:
    return date.today()


def iso(d: date) -> str:
    return d.isoformat()


def parse_iso(s: str) -> date:
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def data_dir() -> Path:
    """Scratch space; outside the repo so no run artefacts get committed."""
    d = Path(os.environ.get("ML4DB_WORKDIR", "/tmp/ml4db"))
    d.mkdir(parents=True, exist_ok=True)
    return d
