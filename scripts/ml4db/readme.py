"""README parsing and structural editing.

The README is the only state this project has: sections give the
taxonomy, entries give the corpus.  Nothing here reformats existing
content -- insertions append at the end of a section, deletions remove
exact lines, and both are checked by validate.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .normalize import ENTRY_RE, normalize_title, parse_venue_year

HEADING_RE = re.compile(r"^(#{2,4})\s+(.*?)\s*$")
ENTRY_START = "* "


@dataclass
class Section:
    level: int
    title: str
    path: str
    line_idx: int  # 0-based index of the heading line
    end_idx: int  # 0-based, exclusive end of the section body
    entries: list[int] = field(default_factory=list)  # line indices


@dataclass
class Entry:
    line_idx: int  # 0-based
    raw: str
    title: str
    venue: str
    year: int | None
    tail: str
    section_path: str
    has_link: bool

    @property
    def norm_title(self) -> str:
        return normalize_title(self.title)

    def render(self) -> str:
        """Canonical line: '* Title (Venue Year) [link]'."""
        year = "" if self.year is None else f" {self.year}"
        tail = f" {self.tail.strip()}" if self.tail and self.tail.strip() else ""
        return f"* {self.title} ({self.venue}{year}){tail}"


def _is_entry(line: str) -> bool:
    return line.startswith(ENTRY_START)


def parse_sections(text: str) -> list[Section]:
    lines = text.split("\n")
    headings = [(i, HEADING_RE.match(l)) for i, l in enumerate(lines)]
    headings = [(i, m) for i, m in headings if m]
    sections: list[Section] = []
    for pos, (idx, m) in enumerate(headings):
        level = len(m.group(1))
        title = m.group(2).strip()
        end = len(lines)
        for jdx, jm in headings[pos + 1 :]:
            if len(jm.group(1)) <= level:
                end = jdx
                break
        path = build_path(headings[: pos + 1])
        sections.append(Section(level, title, path, idx, end))
    return sections


def build_path(headings: list[tuple[int, re.Match]]) -> str:
    parts: list[tuple[int, str]] = []
    for _, m in headings:
        level = len(m.group(1))
        while parts and parts[-1][0] >= level:
            parts.pop()
        parts.append((level, m.group(2).strip()))
    return " > ".join(p[1] for p in parts)


def parse_entries(text: str) -> list[Entry]:
    lines = text.split("\n")
    sections = parse_sections(text)
    # line index -> section path (innermost section containing the line)
    by_line: dict[int, str] = {}
    for sec in sections:
        for i in range(sec.line_idx + 1, sec.end_idx):
            by_line[i] = sec.path
    entries: list[Entry] = []
    for i, line in enumerate(lines):
        if not _is_entry(line):
            continue
        m = ENTRY_RE.match(line)
        if not m:
            continue
        body = m.group("body").strip()
        venue_raw = m.group("venue")
        tail = m.group("tail") or ""
        venue, year = parse_venue_year(venue_raw)
        entries.append(
            Entry(
                line_idx=i,
                raw=line,
                title=body,
                venue=venue,
                year=year,
                tail=tail.strip(),
                section_path=by_line.get(i, ""),
                has_link=bool(re.search(r"\]\(https?://", tail)),
            )
        )
    return entries


def section_map(text: str) -> dict[str, Section]:
    return {s.path: s for s in parse_sections(text)}


def section_choices(text: str) -> list[tuple[str, str]]:
    """(path, one-line hint) for the sections that accept entries.

    Leaves out the TOC, the title and any section that holds no entry
    lines today -- the pipeline only appends to sections that already
    exist, so a section with zero entries is not a target.
    """
    lines = text.split("\n")
    sections = parse_sections(text)
    counts: dict[str, int] = {}
    for e in parse_entries(text):
        counts[e.section_path] = counts.get(e.section_path, 0) + 1
    out = []
    for s in sections:
        if s.level < 2:
            continue
        if counts.get(s.path, 0) == 0:
            continue
        head = lines[s.line_idx].lstrip("# ").strip()
        out.append((s.path, head))
    return out


def insert_entries(text: str, by_section: dict[str, list[str]]) -> str:
    """Append rendered entry lines to the end of each section's entry list.

    The insertion point is after the section's last entry line (skipping
    trailing blank lines belongs to the next section's heading), which
    keeps each section's list contiguous and leaves surrounding blank
    lines untouched.
    """
    lines = text.split("\n")
    sections = section_map(text)
    # Compute insertion index per section in the *original* coordinates.
    inserts: list[tuple[int, list[str]]] = []
    for path, new_lines in by_section.items():
        if not new_lines:
            continue
        sec = sections.get(path)
        if sec is None:
            raise KeyError(f"unknown section: {path!r}")
        # Stop at the first child heading: appending to the end of the whole
        # subtree drops the entry into the last subsection ("Data Access >
        # Materialized View" entries were landing under "Schema & Partition").
        body_end = sec.end_idx
        for i in range(sec.line_idx + 1, sec.end_idx):
            m = HEADING_RE.match(lines[i])
            if m and len(m.group(1)) > sec.level:
                body_end = i
                break
        last_entry = None
        for i in range(sec.line_idx + 1, body_end):
            if _is_entry(lines[i]):
                last_entry = i
        if last_entry is None:
            inserts.append((sec.line_idx + 1, new_lines))
            continue
        inserts.append((last_entry + 1, new_lines))
    for idx, new_lines in sorted(inserts, key=lambda t: t[0], reverse=True):
        lines[idx:idx] = new_lines
    return "\n".join(lines)


def delete_lines(text: str, line_indices: list[int]) -> str:
    lines = text.split("\n")
    for i in sorted(set(line_indices), reverse=True):
        del lines[i]
    return "\n".join(lines)
