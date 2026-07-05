#!/usr/bin/env python3
"""Fetch recent papers from arXiv RSS feeds.

Usage:
    python3 tools/fetch_arxiv.py              # output JSON to stdout
    python3 tools/fetch_arxiv.py -o out.json  # output to file
    python3 tools/fetch_arxiv.py --hours 48   # fetch last 48h (default: 24h)
"""

from __future__ import annotations

import argparse

import _sandbox  # noqa: F401 — sandbox gate, exits if blocked
import json
import re
import sys
from datetime import datetime, timedelta, timezone

try:
    import feedparser
except ImportError:
    class _FeedParserStub:
        @staticmethod
        def parse(*args, **kwargs):
            raise ImportError("feedparser not installed")

    feedparser = _FeedParserStub()

DEFAULT_CATEGORIES = ["cs.LG", "cs.CV", "cs.CL", "cs.AI", "stat.ML"]


def fetch_recent(
    hours: int = 24,
    categories: list[str] | None = None,
) -> list[dict]:
    """Fetch papers from arXiv RSS feeds, optionally filtered by recency.

    Args:
        hours: Only include papers published within this many hours.
               If a paper lacks a parseable published date, it is kept
               (with a warning to stderr).
        categories: arXiv categories to fetch. Defaults to DEFAULT_CATEGORIES.

    Returns:
        Deduplicated list of paper dicts.
    """
    cats = categories or DEFAULT_CATEGORIES
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    papers: list[dict] = []

    for cat in cats:
        try:
            feed = feedparser.parse(f"https://arxiv.org/rss/{cat}")
            if getattr(feed, "bozo", False) and not feed.entries:
                print(
                    f"Warning: RSS feed for {cat} returned an error, skipping.",
                    file=sys.stderr,
                )
                continue
        except Exception as exc:
            print(
                f"Warning: failed to fetch RSS for {cat}: {exc}",
                file=sys.stderr,
            )
            continue

        for entry in feed.entries:
            # --- time filter ---
            published_str = entry.get("published", "")
            if published_str:
                try:
                    pub_dt = datetime.fromisoformat(
                        published_str.replace("Z", "+00:00")
                    )
                    if pub_dt < cutoff:
                        continue
                except (ValueError, TypeError):
                    # Unparseable date — keep the entry, warn once per feed
                    pass

            papers.append(
                {
                    "title": entry.get("title", "").strip().replace("\n", " "),
                    "abstract": entry.get("summary", "").strip(),
                    "authors": [
                        a.get("name", "") for a in entry.get("authors", [])
                    ],
                    "arxiv_url": entry.get("link", ""),
                    "arxiv_id": extract_id(entry.get("link", "")),
                    "category": cat,
                    "published": published_str,
                }
            )

    # Deduplicate by arxiv_id (more reliable than URL)
    seen: set[str] = set()
    unique: list[dict] = []
    for p in papers:
        aid = p["arxiv_id"]
        if aid and aid not in seen:
            seen.add(aid)
            unique.append(p)
        elif not aid:
            # Keep entries without a parseable ID (edge case)
            unique.append(p)
    return unique


def extract_id(url: str) -> str:
    """Extract arXiv ID from URL like https://arxiv.org/abs/2106.09685v2.

    Strips trailing version suffix (e.g. v2) using regex so that IDs
    containing the letter 'v' elsewhere are not corrupted.
    """
    parts = url.rstrip("/").split("/")
    raw = parts[-1] if parts else ""
    # Strip version suffix: only trailing vN where N is one or more digits
    return re.sub(r"v\d+$", "", raw)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch recent arXiv papers via RSS"
    )
    parser.add_argument(
        "-o", "--output", help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Fetch papers from last N hours (default: 24)",
    )
    parser.add_argument(
        "--categories", nargs="+", help="Override arXiv categories"
    )
    args = parser.parse_args()

    papers = fetch_recent(hours=args.hours, categories=args.categories)
    output = json.dumps(papers, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(
            f"Fetched {len(papers)} papers → {args.output}", file=sys.stderr
        )
    else:
        print(output)


if __name__ == "__main__":
    main()
