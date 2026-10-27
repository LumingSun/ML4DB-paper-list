"""The gate.  If this module fails, no PR is opened.

Checks are deliberately mechanical: they encode the two historical
failures (PR #36: entry without venue/year; PR #37: stale base that
rewrites existing lines) as hard invariants.

Diffing is multiset-based rather than opcode-based on purpose: the README
contains identical lines (the 13 legacy duplicate titles), and opcode
alignment would report those as spurious edits.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .normalize import normalize_title
from .readme import parse_entries

# "[label](url)" and the repository's own "[[arXiv]](url)" are both fine;
# a bare "(venue year)" is not.
NEW_ENTRY_RE = re.compile(
    r"^\* (?P<title>.+?) \((?P<venue>[^()]+?) (?P<year>(?:19|20)\d{2})\) "
    r"(?P<link>\[.+?\]\(https?://[^)]+\))$"
)
EXTERNAL_ID_RE = re.compile(r"arxiv\.org/abs/(?P<arxiv>[\w.\-]+)|doi\.org/(?P<doi>10\.[^)\s]+)")


@dataclass
class Report:
    ok: bool
    errors: list[str]
    warnings: list[str]
    added: int = 0

    def raise_if_bad(self) -> None:
        if not self.ok:
            raise SystemExit("validation failed:\n- " + "\n- ".join(self.errors))


def _multiset_diff(a: list[str], b: list[str]) -> list[str]:
    return list((Counter(a) - Counter(b)).elements())


def added_lines(old: str, new: str) -> list[str]:
    return _multiset_diff(new.split("\n"), old.split("\n"))


def removed_lines(old: str, new: str) -> list[str]:
    return _multiset_diff(old.split("\n"), new.split("\n"))


def _headings(text: str) -> list[str]:
    return [l for l in text.split("\n") if l.startswith("#")]


def validate_additions(old: str, new: str) -> Report:
    errors: list[str] = []
    warnings: list[str] = []

    removed = [l for l in removed_lines(old, new) if l.strip()]
    for line in removed:
        errors.append(f"existing content modified or removed: {line[:120]}")

    if _headings(old) != _headings(new):
        errors.append("section headings or table of contents were modified")

    added = [l for l in added_lines(old, new) if l.strip()]
    new_entries = [l for l in added if l.startswith("* ")]
    for line in added:
        if not line.startswith("* "):
            errors.append(f"unexpected non-entry line added: {line[:120]}")

    if not new_entries:
        errors.append("no new entries")

    old_titles = {normalize_title(e.title) for e in parse_entries(old)}
    seen: set[str] = set()
    for line in new_entries:
        m = NEW_ENTRY_RE.match(line)
        if not m:
            errors.append(f"malformed entry (need title + (venue year) + link): {line[:120]}")
            continue
        if not EXTERNAL_ID_RE.search(line):
            errors.append(f"entry has no arXiv/DOI link: {line[:120]}")
        key = normalize_title(m.group("title"))
        if key in old_titles:
            errors.append(f"duplicates an existing entry: {m.group('title')[:100]}")
        if key in seen:
            errors.append(f"duplicate entry within this batch: {m.group('title')[:100]}")
        seen.add(key)

    return Report(ok=not errors, errors=errors, warnings=warnings, added=len(new_entries))


def duplicate_titles(text: str) -> dict[str, int]:
    counts = Counter(normalize_title(e.title) for e in parse_entries(text))
    return {t: n for t, n in counts.items() if n > 1}


def validate_cleanup(old: str, new: str, expected_removed: list[str]) -> Report:
    """Deleting exact duplicate lines is allowed -- nothing else is."""
    errors: list[str] = []
    added = [l for l in added_lines(old, new) if l.strip()]
    if added:
        errors.append(f"cleanup must not add lines: {added[:2]}")
    removed = [l for l in removed_lines(old, new) if l.strip()]
    if Counter(removed) != Counter(expected_removed):
        missing = list((Counter(expected_removed) - Counter(removed)).elements())
        extra = list((Counter(removed) - Counter(expected_removed)).elements())
        errors.append(f"removed lines do not match the manifest; missing={missing[:2]} extra={extra[:2]}")
    remaining = duplicate_titles(new)
    if remaining:
        errors.append(f"{len(remaining)} duplicate titles remain after cleanup")
    return Report(ok=not errors, errors=errors, warnings=[])
