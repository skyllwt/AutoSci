#!/usr/bin/env python3
"""Semantic Scholar API wrapper.

Usage:
    python3 tools/fetch_s2.py search "low rank adaptation"
    python3 tools/fetch_s2.py paper 2106.09685
    python3 tools/fetch_s2.py citations 2106.09685
    python3 tools/fetch_s2.py references 2106.09685
    python3 tools/fetch_s2.py recommend 2106.09685
    python3 tools/fetch_s2.py recommend 2106.09685 2305.14314 --negative 1810.04805
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import _env  # noqa: F401 — load .env files for API keys

import requests

BASE_URL = "https://api.semanticscholar.org/graph/v1"
RECS_BASE_URL = "https://api.semanticscholar.org/recommendations/v1"

# Full rich field set. Accepted by `/paper/{id}` and `/paper/search` — both
# honor nested selectors like `authors.hIndex` and the `tldr` field. Extra
# keys are harmless to existing callers (they read specific keys), so the
# discovery flow picks up hIndex, influentialCitationCount, fieldsOfStudy,
# and tldr without a second round-trip.
FIELDS = (
    "paperId,title,abstract,authors.authorId,authors.name,authors.hIndex,"
    "authors.paperCount,year,citationCount,influentialCitationCount,venue,"
    "publicationTypes,fieldsOfStudy,tldr,externalIds,url"
)

# Flat field set for the endpoints that reject nested selectors and `tldr`:
# `/paper/{id}/citations`, `/paper/{id}/references`, and `/recommendations/*`.
# Authors come back as `{authorId, name}` only — h-index enrichment requires
# a follow-up `paper()` call per candidate if needed. (`/paper/search` does NOT
# share this restriction and still uses the full `FIELDS`.)
FLAT_FIELDS = (
    "paperId,title,abstract,authors,year,citationCount,influentialCitationCount,"
    "venue,publicationTypes,fieldsOfStudy,externalIds,url"
)

S2_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
RATE_LIMIT_DELAY = 1.0 if S2_API_KEY else 3.0  # faster with API key
MAX_RETRIES = 3

_HEADERS = {"x-api-key": S2_API_KEY} if S2_API_KEY else {}


def _bare_arxiv_id(arxiv_id: str) -> str:
    """Strip optional ARXIV:/arxiv: prefix so callers can pass either form."""
    return arxiv_id.removeprefix("ARXIV:").removeprefix("arxiv:")


def _request(method: str, url: str, *, params: dict | None = None, json_body: dict | None = None) -> dict | list:
    """Shared HTTP path with rate limit + 429 retry."""
    time.sleep(RATE_LIMIT_DELAY)
    for attempt in range(MAX_RETRIES):
        resp = requests.request(
            method,
            url,
            params=params or {},
            json=json_body,
            headers=_HEADERS,
            timeout=30,
        )
        if resp.status_code == 429:
            wait = 60 * (attempt + 1)  # 60s, 120s, 180s
            print(f"Rate limited, waiting {wait}s... (attempt {attempt+1}/{MAX_RETRIES})", file=sys.stderr)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"S2 API rate limited after {MAX_RETRIES} retries")


def _get(endpoint: str, params: dict | None = None) -> dict | list:
    return _request("GET", f"{BASE_URL}{endpoint}", params=params)


def _post(endpoint: str, params: dict | None = None, json_body: dict | None = None, base_url: str = BASE_URL) -> dict | list:
    return _request("POST", f"{base_url}{endpoint}", params=params, json_body=json_body)


def search(query: str, limit: int = 10) -> list[dict]:
    """Search papers by query string. Accepts the full rich FIELDS."""
    data = _get("/paper/search", {
        "query": query,
        "limit": limit,
        "fields": FIELDS,
    })
    return data.get("data", [])


def paper(arxiv_id: str) -> dict:
    """Get paper details by arXiv ID. This endpoint accepts the full rich FIELDS."""
    return _get(f"/paper/ARXIV:{_bare_arxiv_id(arxiv_id)}", {"fields": FIELDS})


def citations(arxiv_id: str, limit: int = 100) -> list[dict]:
    """Get papers that cite the given paper.

    Each returned paper dict carries `_is_influential_edge: bool`, lifted from
    the envelope's `isInfluential` field — S2's per-edge signal for whether this
    specific citation substantively built on the anchor (not just a name-check).
    The key is underscore-prefixed so existing key-based consumers
    (`init_discovery.py`, `/ingest`) ignore it without change.
    """
    data = _get(f"/paper/ARXIV:{_bare_arxiv_id(arxiv_id)}/citations", {
        "limit": limit,
        "fields": f"isInfluential,{FLAT_FIELDS}",
    })
    out: list[dict] = []
    for item in data.get("data", []):
        paper_obj = item.get("citingPaper") or {}
        if paper_obj:
            paper_obj["_is_influential_edge"] = bool(item.get("isInfluential"))
            out.append(paper_obj)
    return out


def references(arxiv_id: str, limit: int = 100) -> list[dict]:
    """Get papers referenced by the given paper.

    Each returned paper dict carries `_is_influential_edge: bool` — see `citations`.
    """
    data = _get(f"/paper/ARXIV:{_bare_arxiv_id(arxiv_id)}/references", {
        "limit": limit,
        "fields": f"isInfluential,{FLAT_FIELDS}",
    })
    out: list[dict] = []
    for item in data.get("data", []):
        paper_obj = item.get("citedPaper") or {}
        if paper_obj:
            paper_obj["_is_influential_edge"] = bool(item.get("isInfluential"))
            out.append(paper_obj)
    return out


def recommend(
    positive_ids: list[str],
    negative_ids: list[str] | None = None,
    limit: int = 50,
) -> list[dict]:
    """Recommend papers similar to the given anchors.

    Uses the lightweight forpaper GET endpoint when there is exactly one
    positive anchor and no negatives; otherwise uses the multi-anchor POST
    endpoint that supports negative examples.

    IDs accepted: bare arXiv IDs, "ARXIV:..." form, or S2 paperIds.
    """
    negative_ids = negative_ids or []
    if not positive_ids:
        raise ValueError("recommend() requires at least one positive_id")

    def _normalize(pid: str) -> str:
        # arXiv-style IDs need the ARXIV: prefix; S2 paperIds (40-char hex) pass through.
        if pid.startswith(("ARXIV:", "arxiv:")):
            return f"ARXIV:{_bare_arxiv_id(pid)}"
        if "/" in pid or len(pid) == 40 or pid.isdigit() and len(pid) > 12:
            return pid  # looks like an S2 paperId already
        # Heuristic: contains a dot and starts with a digit → arXiv-style (e.g. 2106.09685)
        if pid and pid[0].isdigit() and "." in pid:
            return f"ARXIV:{pid}"
        return pid

    positive = [_normalize(p) for p in positive_ids]
    negative = [_normalize(p) for p in negative_ids]

    if len(positive) == 1 and not negative:
        url = f"{RECS_BASE_URL}/papers/forpaper/{positive[0]}"
        data = _request("GET", url, params={"limit": limit, "fields": FLAT_FIELDS})
    else:
        data = _post(
            "/papers",
            params={"limit": limit, "fields": FLAT_FIELDS},
            json_body={"positivePaperIds": positive, "negativePaperIds": negative},
            base_url=RECS_BASE_URL,
        )

    # Both endpoints return {"recommendedPapers": [...]}.
    return data.get("recommendedPapers", [])


def main():
    parser = argparse.ArgumentParser(description="Semantic Scholar API wrapper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Search papers")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("n", nargs="?", type=int, default=10, help="Number of results")

    p_paper = sub.add_parser("paper", help="Get paper details")
    p_paper.add_argument("arxiv_id", help="arXiv ID (e.g., 2106.09685)")

    p_cite = sub.add_parser("citations", help="Get citations")
    p_cite.add_argument("arxiv_id", help="arXiv ID")

    p_refs = sub.add_parser("references", help="Get references")
    p_refs.add_argument("arxiv_id", help="arXiv ID")

    p_rec = sub.add_parser("recommend", help="Recommend papers similar to one or more anchors")
    p_rec.add_argument("positive_ids", nargs="+", help="One or more anchor paper IDs (arXiv or S2)")
    p_rec.add_argument(
        "--negative",
        action="append",
        default=[],
        metavar="ID",
        help="Paper ID to push recommendations away from (repeatable)",
    )
    p_rec.add_argument("--limit", type=int, default=50, help="Max recommendations to return (default 50)")

    args = parser.parse_args()

    if args.command == "search":
        result = search(args.query, args.n)
    elif args.command == "paper":
        result = paper(args.arxiv_id)
    elif args.command == "citations":
        result = citations(args.arxiv_id)
    elif args.command == "references":
        result = references(args.arxiv_id)
    elif args.command == "recommend":
        result = recommend(args.positive_ids, args.negative, args.limit)
    else:
        result = {}

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
