"""Harvesting: arXiv API and Crossref.  Deterministic, no model involved."""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import requests

from .config import Candidate, iso

ARXIV_API = "https://export.arxiv.org/api/query"
CROSSREF_API = "https://api.crossref.org/works"
ATOM = {"a": "http://www.w3.org/2005/Atom"}
OS = "{http://a9.com/-/spec/opensearch/1.1/}totalResults"
UA = "ML4DB-paper-list-bot/1.0 (https://github.com/LumingSun/ML4DB-paper-list)"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    return s


def _clean(text: str) -> str:
    return " ".join((text or "").split())


def _get(session: requests.Session, url: str, params: dict, tries: int = 6) -> requests.Response:
    """GET with backoff.  arXiv rate-limits aggressively (429) and both APIs
    occasionally return 5xx; a run that gives up would silently lose a week."""
    delay = 10.0
    last_exc: Exception | None = None
    for attempt in range(tries):
        try:
            r = session.get(url, params=params, timeout=180)
        except requests.RequestException as exc:  # timeouts, proxy hiccups
            last_exc = exc
            time.sleep(delay)
            delay = min(delay * 1.8, 90)
            continue
        if r.status_code == 200:
            return r
        if r.status_code in (429, 500, 502, 503, 504):
            wait = float(r.headers.get("Retry-After") or delay)
            time.sleep(min(wait, 90))
            delay = min(delay * 1.8, 90)
            continue
        r.raise_for_status()
    if last_exc is not None:
        raise last_exc
    return r


def harvest_arxiv(queries: list[str], since: date, until: date, cfg: dict,
                  max_per_query: int = 300) -> list[Candidate]:
    window = f"submittedDate:[{since:%Y%m%d}0000 TO {until:%Y%m%d}2359]"
    session = _session()
    out: list[Candidate] = []
    for q in queries:
        start = 0
        while start < max_per_query:
            params = {
                "search_query": f"({q}) AND {window}",
                "start": start,
                "max_results": 100,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            r = _get(session, ARXIV_API, params)
            if r.status_code != 200:
                break
            root = ET.fromstring(r.text)
            entries = root.findall("a:entry", ATOM)
            if not entries:
                break
            for e in entries:
                raw_id = e.find("a:id", ATOM).text.strip()
                arxiv_id = re.sub(r"v\d+$", "", raw_id.rsplit("/abs/", 1)[-1])
                title = _clean(e.find("a:title", ATOM).text)
                published = e.find("a:published", ATOM).text[:10]
                summary = _clean(e.find("a:summary", ATOM).text)
                cats = [c.get("term") for c in e.findall("{http://www.w3.org/2005/Atom}category")]
                out.append(
                    Candidate(
                        title=title,
                        venue="arXiv",
                        year=date.fromisoformat(published).year,
                        source="arxiv",
                        published=published,
                        abstract=summary,
                        arxiv_id=arxiv_id,
                    )
                )
            start += 100
            time.sleep(3)  # arXiv asks for 3s between API calls
        time.sleep(3)
    return _dedupe_by_id(out)


def _dedupe_by_id(items: list[Candidate]) -> list[Candidate]:
    seen: dict[str, Candidate] = {}
    for c in items:
        key = c.arxiv_id or c.doi or c.title
        seen.setdefault(key, c)
    return list(seen.values())


def _crossref_year(item: dict) -> int | None:
    for key in ("published-print", "published-online", "issued", "published"):
        parts = item.get(key, {}).get("date-parts")
        if parts and parts[0] and parts[0][0]:
            return int(parts[0][0])
    return None


def _strip_jats(abstract: str) -> str:
    text = re.sub(r"<[^>]+>", " ", abstract or "")
    return _clean(text)


def harvest_crossref(containers: list[dict], since: date, cfg: dict,
                     rows_per_page: int = 200, max_total: int = 2000) -> list[Candidate]:
    session = _session()
    out: list[Candidate] = []
    for spec in containers:
        cursor = "*"
        seen = 0
        while seen < max_total:
            params = {
                "filter": f"container-title:{spec['match']},from-pub-date:{iso(since)}",
                "rows": rows_per_page,
                "cursor": cursor,
                "select": "title,container-title,published-print,published-online,issued,DOI,abstract,type",
                "mailto": "noreply@example.com",
            }
            r = _get(session, CROSSREF_API, params)
            if r.status_code != 200:
                break
            msg = r.json()["message"]
            items = msg.get("items", [])
            if not items:
                break
            for item in items:
                titles = item.get("title") or []
                if not titles:
                    continue
                year = _crossref_year(item)
                if year is None:
                    continue
                out.append(
                    Candidate(
                        title=_clean(titles[0]),
                        venue=spec["venue"],
                        year=year,
                        source="crossref",
                        published=f"{year}-01-01",
                        abstract=_strip_jats(item.get("abstract", "")),
                        doi=item.get("DOI", ""),
                    )
                )
            seen += len(items)
            cursor = msg.get("next-cursor")
            if not cursor:
                break
            time.sleep(1)
    return _dedupe_by_id(out)


def harvest(cfg: dict, since: date, until: date,
            sources: tuple[str, ...] = ("arxiv", "crossref")) -> list[Candidate]:
    items: list[Candidate] = []
    if "arxiv" in sources:
        items += harvest_arxiv(cfg["arxiv_queries"], since, until, cfg)
    if "crossref" in sources:
        items += harvest_crossref(cfg["crossref_containers"], since, cfg)
    # one paper may arrive as both preprint and published version: keep the
    # published one (it carries a venue and a DOI), drop the arXiv duplicate.
    by_title: dict[str, Candidate] = {}
    for c in items:
        key = c.title.lower()
        cur = by_title.get(key)
        if cur is None or (cur.venue == "arXiv" and c.venue != "arXiv"):
            by_title[key] = c
    return list(by_title.values())


def default_since(cfg: dict) -> date:
    from datetime import datetime
    return date.today() - timedelta(days=max(cfg["arxiv_lookback_days"], cfg["crossref_lookback_days"]))
