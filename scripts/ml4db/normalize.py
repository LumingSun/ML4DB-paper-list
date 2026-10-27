"""Title / venue normalisation and similarity helpers.

Everything here is pure and deterministic: no network, no model.  The
dedupe layer trusts these functions, so they carry the burden of
"never introduce a duplicate".
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# LaTeX-ish decorations people put in paper titles.
_LATEX = re.compile(r"\\[a-zA-Z]+\*?|\$[^$]*\$")
_NON_WORD = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")


def normalize_title(title: str) -> str:
    """Lowercase, strip LaTeX/punctuation, collapse whitespace.

    Two titles that differ only in capitalisation, hyphens, quotes or
    LaTeX escapes normalise to the same key.
    """
    t = unicodedata.normalize("NFKC", title or "")
    t = _LATEX.sub(" ", t)
    t = t.lower()
    t = _NON_WORD.sub(" ", t)
    return " ".join(t.split())


def title_tokens(title: str) -> list[str]:
    return normalize_title(title).split()


def token_set_ratio(a: str, b: str) -> float:
    """Fuzzy similarity in [0, 100] over normalised token sets.

    difflib over sorted tokens: order-insensitive enough for titles and
    dependency-free (Actions runners do not need rapidfuzz).
    """
    ta, tb = title_tokens(a), title_tokens(b)
    if not ta or not tb:
        return 0.0
    if ta == tb:
        return 100.0
    sa, sb = " ".join(sorted(ta)), " ".join(sorted(tb))
    return SequenceMatcher(None, sa, sb).ratio() * 100.0


YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
# trailing "(venue year [trailing junk])" -- venue may itself contain dots,
# ampersands, dashes, commas, e.g. "DEEM@SIGMOD2018", "Proceedings of the
# ACM on Management of Data", "aiDM@SIGMOD 2019".
ENTRY_RE = re.compile(r"^\*\s+(?P<body>.+?)\s*[（(](?P<venue>[^（()）]*)[）)]\s*(?P<tail>\[.*)?$")


def parse_venue_year(venue_raw: str) -> tuple[str, int | None]:
    """Split "SIGMOD 2021" into ("SIGMOD", 2021).

    Years glued to the venue ("DEEM@SIGMOD2018", "CIDR2019") are split
    off.  A missing year yields None -- callers decide whether that is
    fatal (new entries: yes) or tolerable (existing entries: yes).
    """
    raw = (venue_raw or "").strip()
    m = YEAR_RE.search(raw)
    if not m:
        return raw.strip(), None
    year = int(m.group(1))
    venue = (raw[: m.start()] + raw[m.end():]).strip(" ,;:-")
    return venue, year


def normalize_venue(venue: str) -> str:
    v = unicodedata.normalize("NFKC", venue or "").strip()
    v = re.sub(r"\s+", " ", v)
    return v


def fold_for_compare(s: str) -> str:
    """Aggressive fold used only for duplicate detection."""
    return normalize_title(s)
