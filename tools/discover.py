#!/usr/bin/env python3
"""Discovery tool — assemble a ranked shortlist of candidate papers.

This is the deterministic core behind the /discover skill. It produces a
recommendation shortlist from one of four seed modes:

    from-anchors  — given one or more anchor paper IDs (post-/ingest case)
    from-topic    — given a topic/query string (lighter alternative to /init)
    from-wiki     — derive anchors from the wiki's most recent papers
    from-venue    — papers from a specific venue/year, ranked by wiki relevance

Output is a JSON shortlist on stdout (and optionally a checkpoint file).
Dedupes against papers already in wiki/. Ranking is *not* the same as
init_discovery.py — discovery does not favor surveys; it weights anchor
similarity, influential citations, author h-index, and freshness.

Usage:
    python3 tools/discover.py from-anchors --id 2106.09685 [--id 2305.14314] \\
        [--negative 1810.04805] [--wiki-root wiki/] [--limit 10]
    python3 tools/discover.py from-topic "diffusion model fine-tuning" \\
        [--wiki-root wiki/] [--limit 10]
    python3 tools/discover.py from-wiki --wiki-root wiki/ [--limit 10]
    python3 tools/discover.py from-venue --venue neurips --year 2024 \\
        [--wiki-root wiki/] [--limit 10]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

import _env  # noqa: F401 — load .env files

import fetch_s2

# DeepXiv is optional; degrade silently if unavailable.
try:
    import fetch_deepxiv  # type: ignore
except Exception:  # pragma: no cover — defensive
    fetch_deepxiv = None  # type: ignore


# ---------- candidate normalization ----------------------------------------

def _arxiv_id_from_external(external_ids: dict[str, Any] | None) -> str:
    if not external_ids:
        return ""
    for key in ("ArXiv", "arXiv", "ARXIV"):
        if external_ids.get(key):
            return str(external_ids[key])
    return ""


def _normalize_candidate(raw: dict[str, Any], *, source: str, anchor: str = "") -> dict[str, Any]:
    """Flatten an S2/DeepXiv paper record into the discover shortlist schema."""
    if not raw:
        return {}
    external_ids = raw.get("externalIds") or {}
    arxiv_id = raw.get("arxiv_id") or _arxiv_id_from_external(external_ids)
    authors = raw.get("authors") or []
    h_indexes = [a.get("hIndex") for a in authors if isinstance(a, dict) and a.get("hIndex")]
    tldr = raw.get("tldr")
    tldr_text = tldr.get("text") if isinstance(tldr, dict) else (tldr or "")
    return {
        "paperId": raw.get("paperId") or raw.get("s2_id") or "",
        "arxiv_id": arxiv_id,
        "title": raw.get("title") or "",
        "abstract": raw.get("abstract") or "",
        "tldr": tldr_text,
        "year": raw.get("year"),
        "venue": raw.get("venue") or "",
        "authors": [a.get("name", "") for a in authors if isinstance(a, dict)],
        "max_h_index": max(h_indexes) if h_indexes else 0,
        "citation_count": raw.get("citationCount") or 0,
        "influential_citation_count": raw.get("influentialCitationCount") or 0,
        "fields_of_study": raw.get("fieldsOfStudy") or [],
        "publication_types": raw.get("publicationTypes") or [],
        "url": raw.get("url") or "",
        # True when S2's per-edge `isInfluential` flag fired on the anchor↔candidate
        # citation/reference. Stronger signal than the aggregate `influentialCitationCount`:
        # it means the candidate specifically matters to (or was built on by) the anchor,
        # not just that it has many influential citers in general.
        "is_influential_edge": bool(raw.get("_is_influential_edge")),
        "_sources": [source],
        "_anchors": [anchor] if anchor else [],
    }


def _candidate_key(c: dict[str, Any]) -> str:
    """Stable dedup key — prefer arxiv_id, fall back to paperId, then title."""
    if c.get("arxiv_id"):
        return f"arxiv:{c['arxiv_id']}"
    if c.get("paperId"):
        return f"s2:{c['paperId']}"
    title = re.sub(r"\s+", " ", (c.get("title") or "").strip().lower())
    return f"title:{title}" if title else ""


def _merge_candidate(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    """Union sources/anchors; keep richer field values from either side."""
    for src in incoming.get("_sources", []):
        if src not in existing["_sources"]:
            existing["_sources"].append(src)
    for anchor in incoming.get("_anchors", []):
        if anchor and anchor not in existing["_anchors"]:
            existing["_anchors"].append(anchor)
    for key in (
        "abstract",
        "tldr",
        "venue",
        "url",
        "openreview",
        "site",
        "pdf",
        "project",
        "github",
        "review",
        "metareview",
        "_papercopilot_id",
        "_track",
        "_primary_area",
        "_topic",
        "_status",
    ):
        if not existing.get(key) and incoming.get(key):
            existing[key] = incoming[key]
    if not existing.get("authors") and incoming.get("authors"):
        existing["authors"] = incoming["authors"]
    for key in ("fields_of_study", "keywords"):
        if incoming.get(key):
            merged = list(existing.get(key) or [])
            seen = {_title_key(str(value)) for value in merged}
            for value in incoming.get(key) or []:
                marker = _title_key(str(value))
                if marker and marker not in seen:
                    seen.add(marker)
                    merged.append(value)
            existing[key] = merged
    # Numeric fields: prefer the larger reading (S2 is authoritative; DeepXiv often lacks them).
    for key in ("max_h_index", "citation_count", "influential_citation_count"):
        existing[key] = max(existing.get(key) or 0, incoming.get(key) or 0)
    if "_papercopilot_review_count" in existing or "_papercopilot_review_count" in incoming:
        existing["_papercopilot_review_count"] = max(
            existing.get("_papercopilot_review_count") or 0,
            incoming.get("_papercopilot_review_count") or 0,
        )
    if "_papercopilot_rating" in existing or "_papercopilot_rating" in incoming:
        existing["_papercopilot_rating"] = max(
            float(existing.get("_papercopilot_rating") or 0),
            float(incoming.get("_papercopilot_rating") or 0),
        )
    if "_papercopilot_replies_avg" in existing or "_papercopilot_replies_avg" in incoming:
        existing["_papercopilot_replies_avg"] = max(
            float(existing.get("_papercopilot_replies_avg") or 0),
            float(incoming.get("_papercopilot_replies_avg") or 0),
        )
    if "_wiki_relevance" in existing or "_wiki_relevance" in incoming:
        if float(incoming.get("_wiki_relevance") or 0) > float(existing.get("_wiki_relevance") or 0):
            existing["_wiki_relevance"] = incoming.get("_wiki_relevance")
            existing["_wiki_matched_terms"] = incoming.get("_wiki_matched_terms") or []
    # Influential-edge is a union: if any anchor↔candidate edge was flagged influential,
    # the candidate keeps the flag even when other channels surfaced it without the flag.
    existing["is_influential_edge"] = bool(existing.get("is_influential_edge") or incoming.get("is_influential_edge"))
    if not existing.get("year") and incoming.get("year"):
        existing["year"] = incoming["year"]


def _dedupe(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for c in candidates:
        key = _candidate_key(c)
        if not key:
            continue
        if key in out:
            _merge_candidate(out[key], c)
        else:
            out[key] = c
    return list(out.values())


# ---------- paper copilot source -------------------------------------------

_PAPER_COPILOT_ALIASES: dict[str, str] = {
    "neurips": "nips",
}
_PAPER_COPILOT_BASE_URL = (
    "https://raw.githubusercontent.com/papercopilot/paperlists/main"
)
_ARXIV_ID_RE = re.compile(
    r"(?:arxiv:|arxiv\.org/(?:abs|pdf)/)?"
    r"([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?|[a-z\-]+(?:\.[A-Z]{2})?/[0-9]{7}(?:v[0-9]+)?)",
    re.IGNORECASE,
)


def _papercopilot_url(venue: str, year: int) -> str:
    canonical = _PAPER_COPILOT_ALIASES.get(venue.lower(), venue.lower())
    return f"{_PAPER_COPILOT_BASE_URL}/{canonical}/{canonical}{year}.json"


def _fetch_papercopilot(venue: str, year: int) -> list[dict[str, Any]]:
    """Download the venue/year JSON from Paper Copilot's public GitHub repo."""
    url = _papercopilot_url(venue, year)
    data: Any = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
                data = json.loads(resp.read().decode("utf-8"))
            break
        except Exception as exc:
            if attempt == 0:
                time.sleep(1.0)
                continue
            raise RuntimeError(f"Paper Copilot fetch failed for {venue} {year}: {exc}") from exc
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected Paper Copilot response shape for {venue} {year}: expected list, got {type(data).__name__}")
    return data


def _first_text(raw: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = raw.get(key)
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_url_text(value: Any) -> str:
    if value is None or isinstance(value, (dict, list)):
        return ""
    text = str(value).strip()
    if not text or text in {";", ";;"}:
        return ""
    if text.lower().startswith("www."):
        text = f"https://{text}"
    parsed = urllib.parse.urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return text


def _first_url(raw: dict[str, Any], *keys: str) -> str:
    for key in keys:
        text = _normalize_url_text(raw.get(key))
        if text:
            return text
    return ""


def _first_url_containing(raw: dict[str, Any], needle: str, *keys: str) -> str:
    needle = needle.lower()
    for key in keys:
        text = _normalize_url_text(raw.get(key))
        if text and needle in text.lower():
            return text
    return ""


def _split_text_values(value: Any, *, separators: str = r"[;,]") -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = _first_text(item, "name", "full_name", "value", "text")
            else:
                text = str(item).strip()
            if text:
                out.append(text)
        return out
    return [part.strip() for part in re.split(separators, str(value)) if part.strip()]


def _parse_int(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))
    text = str(value).replace(",", "").strip()
    if not text:
        return 0
    try:
        return max(0, int(float(text)))
    except ValueError:
        return 0


def _parse_rating(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, list) and value:
        return _parse_rating(value[0])
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, float(value))
    text = str(value).strip()
    if not text:
        return 0.0
    try:
        return max(0.0, float(text))
    except ValueError:
        return 0.0


def _unique_text_values(*values: Any, separators: str = r"[;,]") -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        for text in _split_text_values(value, separators=separators):
            key = _title_key(text)
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(text)
    return out


def _extract_arxiv_id_from_record(raw: dict[str, Any]) -> str:
    external_ids = raw.get("externalIds") or raw.get("external_ids") or {}
    if isinstance(external_ids, dict):
        aid = _arxiv_id_from_external(external_ids)
        if aid:
            return aid
    for key in ("arxiv_id", "arxivId", "arxiv", "arxiv_url", "url", "pdf"):
        value = raw.get(key)
        if not value:
            continue
        match = _ARXIV_ID_RE.search(str(value))
        if match:
            return match.group(1)
    return ""


def _normalize_papercopilot_record(raw: dict[str, Any], *, venue: str, year: int) -> dict[str, Any]:
    """Flatten a Paper Copilot record into the discover shortlist schema."""
    if not raw:
        return {}
    title = str(raw.get("title") or "").strip()
    if not title:
        return {}
    authors = _split_text_values(raw.get("authors") or raw.get("author"), separators=r";")
    keyword_list = _unique_text_values(
        raw.get("keywords"),
        raw.get("keyword"),
        raw.get("primary_area"),
        raw.get("primaryArea"),
        raw.get("topic"),
        raw.get("topics"),
    )
    pc_id = str(raw.get("id") or "").strip()
    arxiv_id = _extract_arxiv_id_from_record(raw)
    s2_id = _first_text(raw, "paperId", "s2_id", "s2Id", "semantic_scholar_id")
    openreview = _first_url_containing(raw, "openreview.net", "openreview", "openreview_url", "site", "url")
    site = _first_url(raw, "site")
    pdf = _first_url(raw, "pdf", "pdf_url")
    url = _first_url(raw, "url")
    project = _first_url(raw, "project")
    github = _first_url(raw, "github")
    site = site or project
    url = url or site or openreview or pdf
    citation_count = _parse_int(
        raw.get("gs_citation")
        or raw.get("citation_count")
        or raw.get("citationCount")
        or raw.get("citations")
    )
    review_count = _parse_int(raw.get("review_count") or raw.get("reviews_count") or raw.get("num_reviews"))
    replies_avg = _parse_rating(raw.get("replies_avg") or raw.get("reply_avg"))
    rating_avg = _parse_rating(raw.get("rating_avg") or raw.get("rating"))
    record_year = _parse_int(raw.get("year")) or year
    return {
        "paperId": s2_id or pc_id,
        "arxiv_id": arxiv_id,
        "title": title,
        "abstract": str(raw.get("abstract") or "").strip(),
        "tldr": _first_text(raw, "tldr", "tl_dr", "summary"),
        "year": record_year,
        "venue": str(raw.get("venue") or venue).strip(),
        "authors": authors,
        "max_h_index": 0,
        "citation_count": citation_count,
        "influential_citation_count": 0,
        "fields_of_study": keyword_list,
        "keywords": keyword_list,
        "publication_types": [],
        "url": url,
        "openreview": openreview,
        "site": site,
        "pdf": pdf,
        "project": project,
        "github": github,
        "review": _first_url(raw, "review"),
        "metareview": _first_url(raw, "metareview", "meta_review"),
        "is_influential_edge": False,
        "_sources": ["papercopilot"],
        "_anchors": [],
        # Venue-mode specific signals (prefixed to avoid collision).
        "_papercopilot_id": pc_id,
        "_papercopilot_rating": rating_avg,
        "_papercopilot_review_count": review_count,
        "_papercopilot_replies_avg": replies_avg,
        "_track": str(raw.get("track") or "").strip(),
        "_primary_area": str(raw.get("primary_area") or raw.get("primaryArea") or "").strip(),
        "_topic": str(raw.get("topic") or raw.get("topics") or "").strip(),
        "_status": str(raw.get("status") or raw.get("decision") or "").strip(),
    }


# ---------- wiki dedup -----------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_ARXIV_LINE_RE = re.compile(r"^arxiv(?:_id)?\s*:\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.MULTILINE)
_TITLE_LINE_RE = re.compile(r"^title\s*:\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.MULTILINE)


def _extract_arxiv_id_from_paper(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return ""
    fm = m.group(1)
    am = _ARXIV_LINE_RE.search(fm)
    return (am.group(1).strip() if am else "")


def _wiki_known_arxiv_ids(wiki_root: Path | None) -> set[str]:
    """Scan wiki/papers/*.md for arxiv/arxiv_id frontmatter values."""
    if not wiki_root or not wiki_root.exists():
        return set()
    papers_dir = wiki_root / "papers"
    if not papers_dir.exists():
        return set()
    seen: set[str] = set()
    for path in papers_dir.glob("*.md"):
        aid = _extract_arxiv_id_from_paper(path)
        if aid:
            # Strip arXiv prefixes for match consistency.
            bare = aid.removeprefix("arXiv:").removeprefix("ARXIV:").removeprefix("arxiv:").strip()
            seen.add(re.sub(r"v[0-9]+$", "", bare, flags=re.IGNORECASE))
    return seen


def _title_key(title: str) -> str:
    title = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", (title or "").lower())
    return " ".join(title.split())


def _extract_title_from_paper(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    m = _FRONTMATTER_RE.match(text)
    if m:
        tm = _TITLE_LINE_RE.search(m.group(1))
        if tm:
            return tm.group(1).strip()
    hm = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if hm:
        return hm.group(1).strip()
    return path.stem.replace("-", " ").replace("_", " ")


def _wiki_known_title_keys(wiki_root: Path | None) -> set[str]:
    """Scan wiki/papers/*.md for normalized title keys."""
    if not wiki_root or not wiki_root.exists():
        return set()
    papers_dir = wiki_root / "papers"
    if not papers_dir.exists():
        return set()
    seen: set[str] = set()
    for path in papers_dir.glob("*.md"):
        key = _title_key(_extract_title_from_paper(path))
        if key:
            seen.add(key)
    return seen


def _filter_against_wiki(
    candidates: list[dict[str, Any]],
    known_arxiv_ids: set[str],
    *,
    known_title_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not known_arxiv_ids and not known_title_keys:
        return candidates
    out: list[dict[str, Any]] = []
    known_title_keys = known_title_keys or set()
    for c in candidates:
        arxiv_id = c.get("arxiv_id", "").strip()
        if arxiv_id:
            arxiv_id = arxiv_id.removeprefix("arXiv:").removeprefix("ARXIV:").removeprefix("arxiv:").strip()
            arxiv_id = re.sub(r"v[0-9]+$", "", arxiv_id, flags=re.IGNORECASE)
        if arxiv_id and arxiv_id in known_arxiv_ids:
            continue
        title_key = _title_key(c.get("title") or "")
        if known_title_keys and title_key and title_key in known_title_keys:
            continue
        out.append(c)
    return out


# ---------- wiki relevance corpus ------------------------------------------

_WIKI_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "in", "into", "is", "it", "of", "on", "or", "that",
    "the", "their", "this", "to", "we", "with", "you", "your",
}
_WIKI_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+/_-]*|[\u4e00-\u9fff]{1,}")


def _tokenize(text: str) -> list[str]:
    """Extract meaningful tokens from text for deterministic local ranking."""
    tokens: list[str] = []
    for token in _WIKI_TOKEN_RE.findall(text.lower()):
        token = token.strip("._/+ -")
        if not token:
            continue
        if re.fullmatch(r"[a-z0-9]+", token) and len(token) < 2:
            continue
        if token in _WIKI_STOP_WORDS:
            continue
        tokens.append(token)
    return tokens


def _add_weighted_terms(counts: Counter[str], text: str, weight: float) -> None:
    for token in _tokenize(text):
        counts[token] += weight


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    parts = text.split("---", 2)
    if len(parts) >= 3:
        return parts[1], parts[2]
    return "", text


def _extract_wiki_relevance_corpus(wiki_root: Path) -> dict[str, Any]:
    """Build a deterministic BM25-style corpus from existing wiki documents."""
    if not wiki_root or not wiki_root.exists():
        return {"docs": [], "postings": {}, "df": Counter(), "terms": set(), "avg_len": 0.0}

    dirs_to_scan: list[Path] = []
    for sub in ("papers", "concepts", "topics"):
        d = wiki_root / sub
        if d.exists():
            dirs_to_scan.append(d)
    if not dirs_to_scan:
        # Fallback: scan everything under wiki/
        dirs_to_scan.append(wiki_root)

    docs: list[dict[str, Any]] = []
    postings: dict[str, list[tuple[int, float]]] = {}
    df: Counter[str] = Counter()
    terms: set[str] = set()
    for d in dirs_to_scan:
        for path in d.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            fm, body = _split_frontmatter(text)
            title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
            frontmatter_title = ""
            title_line = _TITLE_LINE_RE.search(fm)
            if title_line:
                frontmatter_title = title_line.group(1).strip()
            title = title_match.group(1).strip() if title_match else frontmatter_title
            if not title:
                title = path.stem.replace("-", " ").replace("_", " ")

            counts: Counter[str] = Counter()
            _add_weighted_terms(counts, title, 4.0)
            _add_weighted_terms(counts, fm, 1.5)
            _add_weighted_terms(counts, body, 1.0)
            if not counts:
                continue
            doc_idx = len(docs)
            length = float(sum(counts.values()))
            docs.append({
                "path": str(path),
                "kind": path.parent.name,
                "length": length,
            })
            for term, tf in counts.items():
                postings.setdefault(term, []).append((doc_idx, float(tf)))
            doc_terms = set(counts)
            df.update(doc_terms)
            terms.update(doc_terms)

    avg_len = sum(float(doc["length"]) for doc in docs) / len(docs) if docs else 0.0
    return {"docs": docs, "postings": postings, "df": df, "terms": terms, "avg_len": avg_len}


def _candidate_relevance_terms(candidate: dict[str, Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    _add_weighted_terms(counts, candidate.get("title", ""), 4.0)
    _add_weighted_terms(counts, candidate.get("abstract", ""), 1.0)
    _add_weighted_terms(counts, candidate.get("tldr", ""), 1.5)
    keyword_terms: list[str] = []
    seen_keywords: set[str] = set()
    for value in list(candidate.get("fields_of_study") or []) + list(candidate.get("keywords") or []):
        marker = _title_key(str(value))
        if marker and marker not in seen_keywords:
            seen_keywords.add(marker)
            keyword_terms.append(str(value))
    _add_weighted_terms(counts, " ".join(keyword_terms), 2.0)
    _add_weighted_terms(counts, str(candidate.get("_track") or ""), 1.2)
    _add_weighted_terms(counts, str(candidate.get("_primary_area") or ""), 1.5)
    _add_weighted_terms(counts, str(candidate.get("_topic") or ""), 1.5)
    return counts


def _wiki_relevance_score(candidate: dict[str, Any], corpus: dict[str, Any]) -> tuple[float, list[str]]:
    """Score a candidate against the wiki with weighted local BM25 signals."""
    query_terms = _candidate_relevance_terms(candidate)
    docs = corpus.get("docs") or []
    postings = corpus.get("postings") or {}
    df = corpus.get("df") or Counter()
    avg_len = float(corpus.get("avg_len") or 0.0)
    if not query_terms or not docs or avg_len <= 0:
        return 0.0, []

    n_docs = len(docs)
    k1 = 1.2
    b = 0.75
    doc_scores: Counter[int] = Counter()
    matched_weights: dict[str, float] = {}
    for term, q_weight in query_terms.items():
        term_postings = postings.get(term)
        if not term_postings:
            continue
        term_df = int(df.get(term, 0))
        idf = math.log(1.0 + (n_docs - term_df + 0.5) / (term_df + 0.5))
        weighted_query = min(3.0, 1.0 + math.log1p(float(q_weight)))
        matched_weights[term] = weighted_query * idf
        for doc_idx, tf in term_postings:
            doc_len = float(docs[doc_idx]["length"])
            norm = tf + k1 * (1.0 - b + b * doc_len / avg_len)
            doc_scores[doc_idx] += weighted_query * idf * ((tf * (k1 + 1.0)) / norm)

    if not doc_scores:
        return 0.0, []
    top_scores = sorted(doc_scores.values(), reverse=True)[:3]
    aggregate = sum(score * (0.5 ** idx) for idx, score in enumerate(top_scores))
    score = 1.0 - math.exp(-aggregate / 8.0)
    matched = [
        term
        for term, _ in sorted(matched_weights.items(), key=lambda item: (-item[1], item[0]))[:12]
    ]
    return min(score, 1.0), matched


# ---------- ranking --------------------------------------------------------

def _influence_score(infl: int, total: int) -> float:
    """Reward influential citations more than raw count.

    Uses log scaling to keep mega-cited papers from saturating.
    """
    infl = max(0, int(infl or 0))
    total = max(0, int(total or 0))
    return 0.7 * math.log1p(infl) / math.log1p(50) + 0.3 * math.log1p(total) / math.log1p(1000)


def _hindex_score(h: int) -> float:
    """Mild bonus from author credibility — cap so it can't dominate."""
    h = max(0, int(h or 0))
    return min(1.0, h / 60.0)


def _freshness_score(year: int | None) -> float:
    if not year:
        return 0.4
    now = _dt.date.today().year
    age = max(0, now - int(year))
    if age <= 1:
        return 1.0
    if age <= 3:
        return 0.85
    if age <= 6:
        return 0.6
    if age <= 10:
        return 0.4
    return 0.25


def _anchor_overlap_score(c: dict[str, Any]) -> float:
    """How many anchors surfaced this candidate (more anchors = stronger signal)."""
    n = len(c.get("_anchors") or [])
    if n == 0:
        return 0.0
    return min(1.0, 0.5 + 0.25 * (n - 1))


def _channel_diversity_score(c: dict[str, Any]) -> float:
    """Bonus when the same candidate was surfaced by multiple channels.

    A paper appearing from recommend + references + citations is a
    stronger signal than one appearing only from recommend — it means
    the paper is semantically similar AND part of the citation graph.
    """
    return min(1.0, 0.4 * len(set(c.get("_sources") or [])))


def _anchor_influence_edge_score(c: dict[str, Any]) -> float:
    """S2's per-edge `isInfluential` flag for this anchor↔candidate citation.

    When True, S2's citation-analysis model judged that the anchor substantively
    built on this candidate (references channel) or this candidate substantively
    built on the anchor (citations channel). That is a much sharper "this matters
    to the anchor" signal than the aggregate `influential_citation_count`, which
    reflects the candidate's influence in general.
    """
    return 1.0 if c.get("is_influential_edge") else 0.0


def _score(c: dict[str, Any], *, anchor_mode: bool) -> float:
    influence = _influence_score(c.get("influential_citation_count", 0), c.get("citation_count", 0))
    h = _hindex_score(c.get("max_h_index", 0))
    fresh = _freshness_score(c.get("year"))
    diversity = _channel_diversity_score(c)
    if anchor_mode:
        # With three channels plus the per-edge isInfluential flag:
        #   - influence: aggregate prestige (candidate's general importance)
        #   - anchor_influence_edge: specific anchor↔candidate significance (sharp, often 0)
        #   - anchor overlap: how many anchors surfaced the candidate
        #   - channel diversity: how many channels surfaced the candidate
        #   - freshness + h-index: supporting signals
        anchor = _anchor_overlap_score(c)
        edge = _anchor_influence_edge_score(c)
        return (
            0.25 * influence
            + 0.20 * edge
            + 0.15 * anchor
            + 0.15 * diversity
            + 0.15 * fresh
            + 0.10 * h
        )
    # Topic / wiki mode: no anchor signal — lean harder on influence and freshness.
    # `is_influential_edge` is always False here (no anchor edge exists), so skip it.
    return 0.45 * influence + 0.25 * fresh + 0.15 * h + 0.15 * diversity


def _rationale(c: dict[str, Any], *, anchor_mode: bool) -> str:
    bits: list[str] = []
    if anchor_mode and c.get("is_influential_edge"):
        # Lead with this — it is the sharpest signal we have.
        bits.append("influential edge with anchor")
    if anchor_mode and c.get("_anchors"):
        bits.append(f"from {len(c['_anchors'])} anchor(s)")
    if c.get("influential_citation_count"):
        bits.append(f"{c['influential_citation_count']} influential citations")
    elif c.get("citation_count"):
        bits.append(f"{c['citation_count']} citations")
    if c.get("max_h_index"):
        bits.append(f"top author h-index {c['max_h_index']}")
    if c.get("year"):
        bits.append(str(c["year"]))
    return "; ".join(bits) if bits else "candidate"


def _rating_score(rating: float) -> float:
    """Normalize Paper Copilot average rating (typically 0–10) to 0–1."""
    return min(1.0, max(0.0, float(rating or 0)) / 10.0)


def _status_score(status: str) -> float:
    """Use Paper Copilot decision/status as a small venue-mode tie-breaker."""
    text = (status or "").lower()
    if not text:
        return 0.5
    if any(marker in text for marker in ("reject", "withdraw", "desk")):
        return 0.0
    if "workshop" in text:
        return 0.65
    if any(marker in text for marker in ("oral", "spotlight")):
        return 1.0
    if any(marker in text for marker in ("accept", "poster", "main")):
        return 0.85
    return 0.5


def _score_venue(c: dict[str, Any]) -> float:
    """Rank venue-mode candidates by wiki relevance + secondary signals."""
    rel = float(c.get("_wiki_relevance", 0.0))
    influence = _influence_score(0, c.get("citation_count", 0))
    fresh = _freshness_score(c.get("year"))
    rating = _rating_score(c.get("_papercopilot_rating", 0))
    status = _status_score(str(c.get("_status") or ""))
    return (
        0.50 * rel
        + 0.20 * influence
        + 0.15 * fresh
        + 0.10 * rating
        + 0.05 * status
    )


def _rationale_venue(c: dict[str, Any]) -> str:
    bits: list[str] = []
    matched = c.get("_wiki_matched_terms")
    if matched:
        bits.append(f"wiki relevance {len(matched)} term(s)")
    if c.get("citation_count"):
        bits.append(f"{c['citation_count']} citations")
    if c.get("year"):
        bits.append(str(c["year"]))
    rating = c.get("_papercopilot_rating")
    if rating:
        bits.append(f"rating {round(float(rating), 1)}")
    status = c.get("_status")
    if status:
        bits.append(status)
    track = c.get("_track")
    if track:
        bits.append(track)
    return "; ".join(bits) if bits else "candidate"


# ---------- candidate gathering --------------------------------------------

def _gather_from_anchors(
    positive: list[str],
    negative: list[str],
    per_anchor_limit: int,
    *,
    citation_expand: bool = True,
    citation_limit: int = 30,
) -> list[dict[str, Any]]:
    """Three-channel anchor gather: recommend + references + citations.

    Each channel fills a different gap:
      - recommend:  semantic neighbors (S2 tends toward recent work)
      - references: what the anchor cites — surfaces older canonical work
      - citations:  what cites the anchor — surfaces high-impact follow-ups

    Without references/citations, anchor mode collapses into "recent papers
    near the topic", which overlaps with /daily-arxiv. With them, anchor mode
    becomes a genuine literature-graph walk from the anchor.
    """
    candidates: list[dict[str, Any]] = []
    # One call-set per anchor preserves which anchor surfaced which candidate;
    # this matters for the anchor-overlap signal in ranking.
    for anchor in positive:
        # Channel 1: semantic recommendations
        try:
            recs = fetch_s2.recommend([anchor], negative_ids=negative, limit=per_anchor_limit)
        except Exception as exc:
            print(f"warn: S2 recommend failed for {anchor}: {exc}", file=sys.stderr)
            recs = []
        for raw in recs:
            norm = _normalize_candidate(raw, source="s2_recommend", anchor=anchor)
            if norm:
                candidates.append(norm)

        if not citation_expand:
            continue

        # Channel 2: what the anchor cites (older canonical work)
        try:
            refs = fetch_s2.references(anchor, limit=citation_limit)
        except Exception as exc:
            print(f"warn: S2 references failed for {anchor}: {exc}", file=sys.stderr)
            refs = []
        for raw in refs:
            norm = _normalize_candidate(raw, source="s2_reference", anchor=anchor)
            if norm:
                candidates.append(norm)

        # Channel 3: what cites the anchor (high-impact follow-ups). S2 returns
        # citations in reverse-chronological order, so capping at citation_limit
        # keeps costs bounded without losing the most recent impactful work.
        try:
            cits = fetch_s2.citations(anchor, limit=citation_limit)
        except Exception as exc:
            print(f"warn: S2 citations failed for {anchor}: {exc}", file=sys.stderr)
            cits = []
        for raw in cits:
            norm = _normalize_candidate(raw, source="s2_citation", anchor=anchor)
            if norm:
                candidates.append(norm)
    return candidates


def _gather_from_topic(topic: str, limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    try:
        s2_results = fetch_s2.search(topic, limit=limit)
    except Exception as exc:
        print(f"warn: S2 search failed for {topic!r}: {exc}", file=sys.stderr)
        s2_results = []
    for raw in s2_results:
        norm = _normalize_candidate(raw, source="s2_search")
        if norm:
            candidates.append(norm)

    if fetch_deepxiv is not None:
        try:
            dx_results = fetch_deepxiv.search(topic, limit=limit)
        except Exception:
            dx_results = []
        for raw in dx_results or []:
            norm = _normalize_candidate(raw, source="deepxiv_search")
            if norm:
                candidates.append(norm)
    return candidates


def _wiki_recent_anchors(wiki_root: Path, k: int) -> list[str]:
    """Pick the K most recently modified paper pages and return their arxiv IDs."""
    papers_dir = wiki_root / "papers"
    if not papers_dir.exists():
        return []
    paths = sorted(papers_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    anchors: list[str] = []
    for path in paths:
        aid = _extract_arxiv_id_from_paper(path)
        if aid:
            anchors.append(aid.removeprefix("arXiv:").removeprefix("ARXIV:").removeprefix("arxiv:").strip())
            if len(anchors) >= k:
                break
    return anchors


def _gather_from_venue(venue: str, year: int) -> list[dict[str, Any]]:
    """Fetch and normalize Paper Copilot records for a venue/year."""
    raw_records = _fetch_papercopilot(venue, year)
    candidates: list[dict[str, Any]] = []
    for raw in raw_records:
        norm = _normalize_papercopilot_record(raw, venue=venue, year=year)
        if norm:
            candidates.append(norm)
    return candidates


# ---------- shortlist assembly ---------------------------------------------

def build_shortlist(
    *,
    mode: str,
    positive_ids: list[str] | None = None,
    negative_ids: list[str] | None = None,
    topic: str = "",
    venue: str = "",
    year: int | None = None,
    wiki_root: Path | None = None,
    limit: int = 10,
    per_anchor_limit: int = 50,
    citation_expand: bool = True,
    citation_limit: int = 30,
) -> dict[str, Any]:
    """Run the discovery pipeline and return a structured shortlist payload."""
    positive_ids = positive_ids or []
    negative_ids = negative_ids or []
    anchor_mode = mode in ("anchors", "wiki")

    if mode == "anchors":
        if not positive_ids:
            raise ValueError("from-anchors requires at least one --id")
        candidates = _gather_from_anchors(
            positive_ids,
            negative_ids,
            per_anchor_limit,
            citation_expand=citation_expand,
            citation_limit=citation_limit,
        )
        seed_summary = {
            "mode": "anchors",
            "positive_ids": positive_ids,
            "negative_ids": negative_ids,
            "citation_expand": citation_expand,
        }
    elif mode == "topic":
        if not topic:
            raise ValueError("from-topic requires a query string")
        candidates = _gather_from_topic(topic, max(20, limit * 4))
        seed_summary = {"mode": "topic", "topic": topic}
    elif mode == "wiki":
        if not wiki_root:
            raise ValueError("from-wiki requires --wiki-root")
        derived = _wiki_recent_anchors(wiki_root, k=3)
        if not derived:
            raise ValueError("from-wiki found no anchorable papers under wiki/papers/")
        candidates = _gather_from_anchors(
            derived,
            negative_ids,
            per_anchor_limit,
            citation_expand=citation_expand,
            citation_limit=citation_limit,
        )
        seed_summary = {
            "mode": "wiki",
            "derived_anchors": derived,
            "citation_expand": citation_expand,
        }
    elif mode == "venue":
        if not venue:
            raise ValueError("from-venue requires --venue")
        if year is None:
            raise ValueError("from-venue requires --year")
        if not wiki_root:
            raise ValueError("from-venue requires --wiki-root for relevance scoring")
        wiki_corpus = _extract_wiki_relevance_corpus(wiki_root)
        if len(wiki_corpus.get("terms") or set()) < 20:
            raise ValueError(
                "Wiki too sparse to compute relevance for venue mode. "
                "Ingest some papers or use topic mode."
            )
        candidates = _gather_from_venue(venue, year)
        if not candidates:
            raise ValueError(f"Paper Copilot returned no records for venue mode: {venue} {year}")
        seed_summary = {"mode": "venue", "venue": venue, "year": year}
        # Pre-compute relevance so we can score/rank later.
        for c in candidates:
            rel, matched = _wiki_relevance_score(c, wiki_corpus)
            c["_wiki_relevance"] = rel
            c["_wiki_matched_terms"] = matched
    else:
        raise ValueError(f"unknown mode: {mode}")

    candidates = _dedupe(candidates)
    known = _wiki_known_arxiv_ids(wiki_root) if wiki_root else set()
    known_titles = _wiki_known_title_keys(wiki_root) if wiki_root and mode == "venue" else set()
    before_wiki_filter_count = len(candidates)
    candidates = _filter_against_wiki(candidates, known, known_title_keys=known_titles)
    wiki_dedup_count = before_wiki_filter_count - len(candidates)

    if mode == "venue":
        candidates = [c for c in candidates if float(c.get("_wiki_relevance", 0.0)) > 0]
        if not candidates:
            raise ValueError(
                "No venue candidates matched the existing wiki relevance corpus after filtering existing wiki papers. "
                "Expand the wiki or use topic mode."
            )
        for c in candidates:
            c["_score"] = round(_score_venue(c), 4)
            c["_rationale"] = _rationale_venue(c)
    else:
        for c in candidates:
            c["_score"] = round(_score(c, anchor_mode=anchor_mode), 4)
            c["_rationale"] = _rationale(c, anchor_mode=anchor_mode)

    candidates.sort(key=lambda c: c["_score"], reverse=True)
    shortlist = candidates[:limit]

    return {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "seed": seed_summary,
        "wiki_dedup_count": wiki_dedup_count,
        "candidates_total": len(candidates),
        "shortlist_count": len(shortlist),
        "shortlist": shortlist,
    }


# ---------- output formatting ---------------------------------------------

def _format_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    seed = payload.get("seed") or {}
    mode = seed.get("mode", "?")
    if mode == "anchors":
        seed_desc = f"anchors: {', '.join(seed.get('positive_ids', []))}"
        if seed.get("negative_ids"):
            seed_desc += f" | negatives: {', '.join(seed['negative_ids'])}"
    elif mode == "topic":
        seed_desc = f'topic: "{seed.get("topic", "")}"'
    elif mode == "wiki":
        seed_desc = f"derived from wiki anchors: {', '.join(seed.get('derived_anchors', []))}"
    elif mode == "venue":
        seed_desc = f"venue: {seed.get('venue', '')} {seed.get('year', '')}"
    else:
        seed_desc = mode

    lines.append(f"# Discover shortlist ({mode})")
    lines.append(f"_Seed_: {seed_desc}")
    lines.append(
        f"_Stats_: {payload.get('shortlist_count', 0)} shown / "
        f"{payload.get('candidates_total', 0)} candidates / "
        f"{payload.get('wiki_dedup_count', 0)} already in wiki"
    )
    lines.append("")
    for i, c in enumerate(payload.get("shortlist") or [], start=1):
        title = c.get("title") or "(untitled)"
        aid = c.get("arxiv_id") or c.get("paperId") or ""
        rationale = c.get("_rationale") or ""
        score = c.get("_score", 0)
        lines.append(f"{i}. **{title}**  ")
        lines.append(f"   `{aid}` — score {score} — {rationale}")
        if c.get("tldr"):
            lines.append(f"   > {c['tldr']}")
        lines.append("")
    return "\n".join(lines)


# ---------- CLI ------------------------------------------------------------

def _slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return text[:48] or "discover"


def _resolve_output_checkpoint_path(raw_path: str | Path, seed_slug: str) -> Path:
    """Resolve --output-checkpoint as either a file path or directory target."""
    raw_text = str(raw_path)
    out_path = Path(raw_text)
    if out_path.is_dir() or raw_text.endswith(("/", "\\")):
        today = _dt.date.today().isoformat()
        return out_path / f"discover-{seed_slug}-{today}.json"
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="OmegaWiki discovery shortlist builder")
    sub = parser.add_subparsers(dest="command", required=True)

    common_args: list[tuple[str, dict[str, Any]]] = [
        ("--wiki-root", {"type": Path, "default": None, "help": "Wiki root for dedup against existing papers"}),
        ("--limit", {"type": int, "default": 10, "help": "Max shortlist size (default 10)"}),
        ("--output-checkpoint", {"default": None, "help": "Also write JSON to this file or directory path"}),
        ("--markdown", {"action": "store_true", "help": "Print human-readable markdown instead of JSON"}),
    ]
    anchor_common_args: list[tuple[str, dict[str, Any]]] = [
        ("--per-anchor-limit", {"type": int, "default": 50, "help": "Recs requested per anchor (default 50)"}),
    ]

    # Citation-expansion flags apply only to anchor and wiki modes.
    anchor_expand_args: list[tuple[str, dict[str, Any]]] = [
        ("--no-citation-expand", {"dest": "citation_expand", "action": "store_false", "help": "Skip references/citations fan-out (recommend channel only; faster but narrower)"}),
        ("--citation-limit", {"type": int, "default": 30, "help": "Per-anchor cap for references and citations channels (default 30 each)"}),
    ]

    p_anchors = sub.add_parser("from-anchors", help="Recommend from one or more anchor papers")
    p_anchors.add_argument("--id", dest="positive_ids", action="append", default=[], required=True, help="Anchor paper ID (repeatable)")
    p_anchors.add_argument("--negative", dest="negative_ids", action="append", default=[], help="Push recommendations away from this ID (repeatable)")
    for flag, kwargs in common_args:
        p_anchors.add_argument(flag, **kwargs)
    for flag, kwargs in anchor_common_args:
        p_anchors.add_argument(flag, **kwargs)
    for flag, kwargs in anchor_expand_args:
        p_anchors.add_argument(flag, **kwargs)

    p_topic = sub.add_parser("from-topic", help="Recommend from a topic / query string")
    p_topic.add_argument("topic", help="Topic or query string")
    for flag, kwargs in common_args:
        p_topic.add_argument(flag, **kwargs)
    # Preserve the previous no-op flag acceptance for topic mode without showing
    # an anchor-only option in help.
    p_topic.add_argument("--per-anchor-limit", type=int, default=50, help=argparse.SUPPRESS)

    p_wiki = sub.add_parser("from-wiki", help="Derive seeds from the wiki's recent papers")
    for flag, kwargs in common_args:
        p_wiki.add_argument(flag, **kwargs)
    for flag, kwargs in anchor_common_args:
        p_wiki.add_argument(flag, **kwargs)
    for flag, kwargs in anchor_expand_args:
        p_wiki.add_argument(flag, **kwargs)

    p_venue = sub.add_parser("from-venue", help="Recommend papers from a venue/year ranked by wiki relevance")
    p_venue.add_argument("--venue", required=True, help="Venue slug (e.g. neurips, icml, iclr)")
    p_venue.add_argument("--year", type=int, required=True, help="Year (e.g. 2024)")
    for flag, kwargs in common_args:
        p_venue.add_argument(flag, **kwargs)

    args = parser.parse_args()

    if args.command == "from-anchors":
        payload = build_shortlist(
            mode="anchors",
            positive_ids=args.positive_ids,
            negative_ids=args.negative_ids,
            wiki_root=args.wiki_root,
            limit=args.limit,
            per_anchor_limit=args.per_anchor_limit,
            citation_expand=args.citation_expand,
            citation_limit=args.citation_limit,
        )
        seed_slug = _slugify("-".join(args.positive_ids[:2]))
    elif args.command == "from-topic":
        payload = build_shortlist(
            mode="topic",
            topic=args.topic,
            wiki_root=args.wiki_root,
            limit=args.limit,
        )
        seed_slug = _slugify(args.topic)
    elif args.command == "from-wiki":
        if not args.wiki_root:
            parser.error("from-wiki requires --wiki-root")
        payload = build_shortlist(
            mode="wiki",
            wiki_root=args.wiki_root,
            limit=args.limit,
            per_anchor_limit=args.per_anchor_limit,
            citation_expand=args.citation_expand,
            citation_limit=args.citation_limit,
        )
        seed_slug = "wiki"
    elif args.command == "from-venue":
        if not args.wiki_root:
            parser.error("from-venue requires --wiki-root")
        try:
            payload = build_shortlist(
                mode="venue",
                venue=args.venue,
                year=args.year,
                wiki_root=args.wiki_root,
                limit=args.limit,
            )
        except (RuntimeError, ValueError) as exc:
            parser.error(str(exc))
        seed_slug = _slugify(f"{args.venue}-{args.year}")
    else:
        parser.error(f"unknown command: {args.command}")
        return

    if args.output_checkpoint:
        out_path = _resolve_output_checkpoint_path(args.output_checkpoint, seed_slug)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"checkpoint written: {out_path}", file=sys.stderr)

    if args.markdown:
        print(_format_markdown(payload))
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
