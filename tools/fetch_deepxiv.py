#!/usr/bin/env python3
"""DeepXiv API wrapper — semantic search, progressive reading, trending papers.

Usage:
    python3 tools/fetch_deepxiv.py search "low rank adaptation" --limit 10
    python3 tools/fetch_deepxiv.py brief 2106.09685
    python3 tools/fetch_deepxiv.py head 2106.09685
    python3 tools/fetch_deepxiv.py section 2106.09685 Introduction
    python3 tools/fetch_deepxiv.py raw 2106.09685
    python3 tools/fetch_deepxiv.py trending --days 7
    python3 tools/fetch_deepxiv.py social 2106.09685

Requires: pip install deepxiv-sdk
Token: reads DEEPXIV_TOKEN env var. If absent, SDK auto-registers on first use.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import _env  # noqa: F401 — load .env files for API keys

try:
    from deepxiv_sdk import Reader
    from deepxiv_sdk.reader import (
        APIError,
        AuthenticationError,
        NotFoundError,
        RateLimitError,
    )

    HAS_DEEPXIV = True
except ImportError:
    HAS_DEEPXIV = False

    class Reader:  # pragma: no cover - only used when SDK is absent
        def __init__(self, *args, **kwargs):
            raise ImportError("deepxiv-sdk not installed")

    # Dummy exception classes so except clauses don't raise NameError
    class APIError(Exception): pass            # noqa: E303,E701
    class AuthenticationError(Exception): pass  # noqa: E701
    class NotFoundError(Exception): pass        # noqa: E701
    class RateLimitError(Exception): pass       # noqa: E701

DEEPXIV_TOKEN = os.environ.get("DEEPXIV_TOKEN", "")


def _get_reader() -> "Reader":
    """Create a Reader instance with token from env."""
    kwargs: dict = {}
    if DEEPXIV_TOKEN:
        kwargs["token"] = DEEPXIV_TOKEN
    return Reader(**kwargs)


def _error_exit(msg: str, code: int = 1) -> None:
    """Print error to stderr and exit."""
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def search(
    query: str,
    mode: str = "hybrid",
    limit: int = 10,
    categories: list[str] | None = None,
    min_citation: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Search papers with hybrid BM25+vector search.

    Returns a list of paper dicts with normalised fields.
    """
    reader = _get_reader()
    data = reader.search(
        query=query,
        size=limit,
        search_mode=mode,
        categories=categories,
        min_citation=min_citation,
        date_from=date_from,
        date_to=date_to,
    )
    results = data.get("results")
    if results is None:
        # DeepXiv SDK/API versions around the retrieval-service update use
        # `result`; keep the older `results` spelling for compatibility.
        results = data.get("result", [])
    # Normalise output to a consistent shape
    papers = []
    for r in results:
        authors_raw = r.get("authors", [])
        if authors_raw and isinstance(authors_raw[0], dict):
            authors = [a.get("name", "") for a in authors_raw]
        else:
            authors = list(authors_raw)
        papers.append(
            {
                "arxiv_id": r.get("arxiv_id", ""),
                "title": r.get("title", ""),
                "abstract": r.get("abstract", ""),
                "authors": authors,
                "categories": r.get("categories", []),
                "year": r.get("year", None),
                "citation_count": r.get("citation_count", r.get("citation", 0)),
                "relevance_score": r.get("score", 0.0),
                "published": r.get("publish_at", ""),
            }
        )
    return papers


def brief(arxiv_id: str) -> dict:
    """Get brief summary (TLDR, keywords, citations)."""
    reader = _get_reader()
    data = reader.brief(arxiv_id)
    return {
        "arxiv_id": data.get("arxiv_id", arxiv_id),
        "title": data.get("title", ""),
        "tldr": data.get("tldr", ""),
        "keywords": data.get("keywords", []),
        "citations": data.get("citations", 0),
        "published": data.get("publish_at", ""),
        "src_url": data.get("src_url", ""),
        "github_url": data.get("github_url", None),
    }


def head(arxiv_id: str) -> dict:
    """Get paper metadata and section structure."""
    reader = _get_reader()
    data = reader.head(arxiv_id)
    sections_raw = data.get("sections", {})
    # Normalise sections to list of {name, tldr, token_count}
    sections = []
    if isinstance(sections_raw, dict):
        for name, info in sections_raw.items():
            if isinstance(info, dict):
                sections.append(
                    {
                        "name": name,
                        "tldr": info.get("tldr", ""),
                        "token_count": info.get("token_count", 0),
                    }
                )
            else:
                sections.append({"name": name, "tldr": "", "token_count": 0})
    elif isinstance(sections_raw, list):
        for item in sections_raw:
            if isinstance(item, dict):
                sections.append(
                    {
                        "name": item.get("name", ""),
                        "tldr": item.get("tldr", ""),
                        "token_count": item.get("token_count", 0),
                    }
                )

    authors_raw = data.get("authors", [])
    if authors_raw and isinstance(authors_raw[0], dict):
        authors = [a.get("name", "") for a in authors_raw]
    else:
        authors = list(authors_raw) if authors_raw else []

    return {
        "arxiv_id": data.get("arxiv_id", arxiv_id),
        "title": data.get("title", ""),
        "abstract": data.get("abstract", ""),
        "authors": authors,
        "categories": data.get("categories", []),
        "published": data.get("publish_at", ""),
        "token_count": data.get("token_count", 0),
        "sections": sections,
    }


def section(arxiv_id: str, section_name: str) -> dict:
    """Read a specific section of a paper."""
    reader = _get_reader()
    content = reader.section(arxiv_id, section_name)
    return {
        "arxiv_id": arxiv_id,
        "section_name": section_name,
        "content": content if isinstance(content, str) else str(content),
    }


def raw(arxiv_id: str) -> dict:
    """Get full paper content in markdown."""
    reader = _get_reader()
    content = reader.raw(arxiv_id)
    return {
        "arxiv_id": arxiv_id,
        "content": content if isinstance(content, str) else str(content),
    }


def trending(days: int = 7, limit: int = 30) -> list[dict]:
    """Get trending papers by social impact."""
    reader = _get_reader()
    data = reader.trending(days=days, limit=limit)
    papers = []
    for p in data.get("papers", []):
        papers.append(
            {
                "arxiv_id": p.get("arxiv_id", ""),
                "title": p.get("title", ""),
                "rank": p.get("rank", 0),
                "social_impact": p.get("stats", {}),
                "categories": p.get("categories", []),
            }
        )
    return papers


def social(arxiv_id: str) -> dict:
    """Get social media impact metrics for a paper."""
    reader = _get_reader()
    data = reader.social_impact(arxiv_id)
    if data is None:
        return {
            "arxiv_id": arxiv_id,
            "tweets": 0,
            "views": 0,
            "likes": 0,
            "replies": 0,
        }
    return {
        "arxiv_id": data.get("arxiv_id", arxiv_id),
        "tweets": data.get("total_tweets", 0),
        "views": data.get("total_views", 0),
        "likes": data.get("total_likes", 0),
        "replies": data.get("total_replies", 0),
        "first_seen": data.get("first_seen_date", ""),
        "last_seen": data.get("last_seen_date", ""),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DeepXiv API: semantic search + progressive reading"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="Hybrid search for papers")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument(
        "--mode",
        choices=["hybrid", "bm25", "vector"],
        default="hybrid",
        help="Search mode (default: hybrid)",
    )
    p_search.add_argument(
        "--limit", type=int, default=10, help="Max results (1-100)"
    )
    p_search.add_argument(
        "--categories", nargs="+", help="arXiv categories filter"
    )
    p_search.add_argument(
        "--min-citation", type=int, help="Minimum citation count"
    )
    p_search.add_argument("--date-from", help="From date (YYYY-MM-DD)")
    p_search.add_argument("--date-to", help="To date (YYYY-MM-DD)")

    # brief
    p_brief = sub.add_parser("brief", help="Quick paper summary (TLDR)")
    p_brief.add_argument("arxiv_id", help="arXiv ID (e.g. 2106.09685)")

    # head
    p_head = sub.add_parser("head", help="Paper metadata + section structure")
    p_head.add_argument("arxiv_id", help="arXiv ID")

    # section
    p_section = sub.add_parser("section", help="Read a specific section")
    p_section.add_argument("arxiv_id", help="arXiv ID")
    p_section.add_argument("section_name", help="Section name (case-insensitive)")

    # raw
    p_raw = sub.add_parser("raw", help="Full paper in markdown")
    p_raw.add_argument("arxiv_id", help="arXiv ID")

    # trending
    p_trend = sub.add_parser("trending", help="Trending papers")
    p_trend.add_argument(
        "--days",
        type=int,
        choices=[7, 14, 30],
        default=7,
        help="Lookback window (default: 7)",
    )
    p_trend.add_argument(
        "--limit", type=int, default=30, help="Max results (1-100)"
    )

    # social
    p_social = sub.add_parser("social", help="Social impact metrics")
    p_social.add_argument("arxiv_id", help="arXiv ID")

    args = parser.parse_args()

    if not HAS_DEEPXIV:
        _error_exit(
            "deepxiv-sdk not installed. Run: pip install deepxiv-sdk"
        )

    try:
        if args.command == "search":
            result = search(
                args.query,
                mode=args.mode,
                limit=args.limit,
                categories=args.categories,
                min_citation=args.min_citation,
                date_from=args.date_from,
                date_to=args.date_to,
            )
        elif args.command == "brief":
            result = brief(args.arxiv_id)
        elif args.command == "head":
            result = head(args.arxiv_id)
        elif args.command == "section":
            result = section(args.arxiv_id, args.section_name)
        elif args.command == "raw":
            result = raw(args.arxiv_id)
        elif args.command == "trending":
            result = trending(days=args.days, limit=args.limit)
        elif args.command == "social":
            result = social(args.arxiv_id)
        else:
            result = {}

        print(json.dumps(result, indent=2, ensure_ascii=False))

    except (APIError, AuthenticationError, RateLimitError, NotFoundError) as exc:
        _error_exit(f"DeepXiv API error: {exc}")
    except ConnectionError as exc:
        _error_exit(f"Connection error: {exc}")
    except ValueError as exc:
        _error_exit(f"Invalid input: {exc}")


if __name__ == "__main__":
    main()
