"""Deterministic gates between harvesting and the model."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache

from .config import Candidate
from .readme import Entry
from .normalize import normalize_title, title_tokens, title_variant_key, token_set_ratio


@lru_cache(maxsize=512)
def _term_pattern(term: str) -> re.Pattern:
    """Whole-word match, tolerating a plural 's'.

    Substring matching on short terms is a trap: "ai" hits "domain",
    "available", "explain", letting anything through.
    """
    escaped = re.escape(term.strip())
    return re.compile(rf"(?<![a-z0-9]){escaped}s?(?![a-z0-9])")


def _hit(term: str, blob: str) -> bool:
    return bool(_term_pattern(term).search(blob))


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").lower()


def relevance(c: Candidate, cfg: dict) -> tuple[bool, str]:
    """Lexical in-scope test: one DB term AND one AI term, no excluded topic."""
    blob = _fold(f"{c.title} {c.abstract}")
    for term in cfg["exclude_terms"]:
        if _hit(term, blob):
            return False, f"excluded topic: {term}"
    if not any(_hit(t, blob) for t in cfg["db_terms"]):
        return False, "no database term"
    if not any(_hit(t, blob) for t in cfg["ai_terms"]):
        return False, "no AI term"
    return True, ""


def prefilter(cands: list[Candidate], cfg: dict) -> tuple[list[Candidate], list[dict]]:
    kept, dropped = [], []
    for c in cands:
        ok, why = relevance(c, cfg)
        if ok:
            kept.append(c)
        else:
            dropped.append({"title": c.title, "reason": why})
    return kept, dropped


class DupeIndex:
    """Duplicate detection over the ~660 existing titles.

    Exact title lookups are O(1); fuzzy matching is narrowed by a token
    inverted index, so a 1,600-candidate run does not perform a million
    difflib comparisons.
    """

    def __init__(self, entries: list[Entry], cfg: dict):
        self.entries = entries
        self.cfg = cfg
        self.threshold = cfg["duplicate_threshold"]
        self.by_key: dict[str, Entry] = {}
        self.by_token: dict[str, list[int]] = defaultdict(list)
        self.tokens: list[set[str]] = []
        for i, e in enumerate(entries):
            self.by_key.setdefault(e.norm_title, e)
            self.by_key.setdefault(title_variant_key(e.title), e)
            toks = set(title_tokens(e.title))
            self.tokens.append(toks)
            for t in toks:
                self.by_token[t].append(i)

    def exact(self, c: Candidate) -> Entry | None:
        if c.arxiv_id:
            for e in self.entries:
                if c.arxiv_id in e.raw:
                    return e
        if c.doi:
            for e in self.entries:
                if c.doi in e.raw:
                    return e
        return (self.by_key.get(normalize_title(c.title))
                or self.by_key.get(title_variant_key(c.title)))

    def match(self, c: Candidate) -> Entry | None:
        hit = self.exact(c)
        if hit is not None:
            return hit
        cand_tokens = set(title_tokens(c.title))
        if not cand_tokens:
            return None
        overlaps: Counter[int] = Counter()
        for t in cand_tokens:
            for i in self.by_token.get(t, ()):
                overlaps[i] += 1
        if not overlaps:
            return None
        best, best_score = None, 0.0
        for i, shared in overlaps.most_common(25):
            entry_tokens = self.tokens[i]
            denom = min(len(cand_tokens), len(entry_tokens)) or 1
            if shared / denom < 0.5:
                continue
            score = token_set_ratio(c.title, self.entries[i].title)
            if score > best_score:
                best, best_score = self.entries[i], score
        return best if best_score >= self.threshold else None


def find_duplicate(c: Candidate, entries: list[Entry], cfg: dict) -> Entry | None:
    return DupeIndex(entries, cfg).match(c)


def dedupe(cands: list[Candidate], entries: list[Entry], cfg: dict) -> tuple[list[Candidate], list[dict]]:
    index = DupeIndex(entries, cfg)
    kept, dropped = [], []
    kept_keys: set[str] = set()
    kept_titles: list[str] = []
    for c in cands:
        hit = index.match(c)
        if hit is not None:
            dropped.append({"title": c.title, "reason": f"duplicate of existing: {hit.title}"})
            continue
        key = title_variant_key(c.title)
        if key in kept_keys:
            dropped.append({"title": c.title, "reason": "duplicate within batch (exact)"})
            continue
        clash = next(
            (t for t in kept_titles if token_set_ratio(c.title, t) >= cfg["duplicate_threshold"]),
            None,
        )
        if clash is not None:
            dropped.append({"title": c.title, "reason": f"duplicate within batch: {clash}"})
            continue
        kept.append(c)
        kept_keys.add(key)
        kept_titles.append(c.title)
    return kept, dropped


def upgrade_candidates(dropped: list[dict], entries: list[Entry]) -> list[dict]:
    """Preprints already listed as (arXiv ...) that now have a venue version.

    Reported in the PR body only: the pipeline never rewrites existing rows.
    """
    return [d for d in dropped if d.get("reason", "").startswith("duplicate of existing")]
