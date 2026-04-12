#!/usr/bin/env python3
"""Semantic dedup tool -- Token Jaccard similarity search across wiki pages.

Finds pages whose title/body are similar to a free-text query, useful for
detecting near-duplicates before creating new pages and for discovering
related content across entity types.

Usage:
    python3 tools/find_similar.py <wiki_root> "attention mechanism"
    python3 tools/find_similar.py <wiki_root> "transformer architecture" --type concepts
    python3 tools/find_similar.py <wiki_root> "failed experiment" --threshold 0.5

Python 3.9+, no external dependencies.
"""

from __future__ import annotations

import argparse
import io
import re
import string
import sys
from pathlib import Path

from _schemas import ENTITY_DIRS

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

THRESHOLD_POTENTIAL = 0.35
THRESHOLD_LIKELY = 0.65

# English top-100 stopwords (hardcoded, no nltk)
STOPWORDS: set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "get", "got", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isn't",
    "it", "its", "itself", "just", "let", "me", "might", "more", "most",
    "must", "my", "myself", "no", "nor", "not", "now", "of", "off", "on",
    "once", "only", "or", "other", "our", "ours", "ourselves", "out",
    "over", "own", "s", "same", "she", "should", "shouldn't", "so", "some",
    "such", "t", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "were", "weren't", "what", "when", "where", "which",
    "while", "who", "whom", "why", "will", "with", "won't", "would",
    "wouldn't", "you", "your", "yours", "yourself", "yourselves",
}

# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def tokenize(text: str) -> set[str]:
    """Lowercase, strip punctuation, remove stopwords, return token set."""
    words = text.lower().translate(_PUNCT_TABLE).split()
    return {w for w in words if w and w not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# Page loader
# ---------------------------------------------------------------------------


def _parse_yaml_frontmatter(content: str) -> dict[str, str]:
    """Extract simple key: value pairs from YAML frontmatter."""
    fm: dict[str, str] = {}
    if not content.startswith("---"):
        return fm
    end = content.find("\n---", 3)
    if end == -1:
        return fm
    block = content[3:end]
    for line in block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm


def _first_paragraph(content: str) -> str:
    """Return first non-frontmatter, non-heading paragraph text."""
    text = content
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if lines:
                break
            continue
        if stripped.startswith("#"):
            if lines:
                break
            continue
        lines.append(stripped)
    return " ".join(lines)


def load_wiki_pages(wiki_root: Path,
                    entity_filter: str | None = None) -> list[tuple[str, str, str]]:
    """Walk wiki entity directories, extract title + first paragraph.

    Returns (label, title, body) triples.
    """
    entries: list[tuple[str, str, str]] = []
    dirs_to_scan = [entity_filter] if entity_filter else ENTITY_DIRS

    for subdir_name in dirs_to_scan:
        subdir = wiki_root / subdir_name
        if not subdir.is_dir():
            continue
        for md_file in sorted(subdir.rglob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue
            fm = _parse_yaml_frontmatter(content)
            title = fm.get("title", "") or fm.get("name", "")
            if not title:
                title = md_file.stem.replace("-", " ").replace("_", " ").title()
            first_para = _first_paragraph(content)
            rel = md_file.relative_to(wiki_root)
            label = str(rel).replace("\\", "/")
            entries.append((label, title, first_para))
    return entries


# ---------------------------------------------------------------------------
# Search + display
# ---------------------------------------------------------------------------


def score_entry(query_tokens: set[str], title: str, body: str) -> float:
    """Score an entry against query tokens.

    Uses weighted Jaccard: best of title-only Jaccard and an asymmetric
    Jaccard against full entry that compensates for length mismatch.
    """
    title_tokens = tokenize(title)
    all_tokens = tokenize(f"{title} {body}")

    s1 = jaccard(query_tokens, title_tokens)

    intersection = len(query_tokens & all_tokens)
    if not query_tokens or not all_tokens:
        s2 = 0.0
    else:
        excess = max(0, len(all_tokens) - len(query_tokens))
        denominator = len(query_tokens) + excess * 0.05
        s2 = intersection / denominator if denominator else 0.0

    return max(s1, s2)


def search(query: str, wiki_root: Path, entity_filter: str | None = None,
           top_n: int = 15, threshold: float = THRESHOLD_POTENTIAL
           ) -> list[tuple[float, str, str]]:
    """Return ranked (score, label, snippet) list."""
    entries = load_wiki_pages(wiki_root, entity_filter)
    if not entries:
        print(f"No pages found in {wiki_root}", file=sys.stderr)
        return []
    query_tokens = tokenize(query)
    if not query_tokens:
        print("ERROR: query produced no tokens after stopword removal", file=sys.stderr)
        sys.exit(1)

    results: list[tuple[float, str, str]] = []
    for label, title, body in entries:
        score = score_entry(query_tokens, title, body)
        if score >= threshold:
            snippet = f"{title}"
            body_start = body[:60].replace("\n", " ").strip()
            if body_start:
                snippet += f" -- {body_start}"
                if len(body) > 60:
                    snippet += "..."
            results.append((score, label, snippet))

    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_n]


def format_results(results: list[tuple[float, str, str]],
                   likely: float = THRESHOLD_LIKELY) -> str:
    if not results:
        return "  No matches above threshold"
    lines: list[str] = []
    for score, label, snippet in results:
        pct = int(score * 100)
        tag = "[LIKELY DUP]" if score >= likely else "[POTENTIAL] "
        lines.append(f"  {pct:3d}% {tag} {label} -- \"{snippet}\"")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find similar wiki pages using Token Jaccard similarity."
    )
    parser.add_argument("wiki_root", help="Path to the wiki/ directory")
    parser.add_argument(
        "query", nargs="+",
        help="Free-text query to match against"
    )
    parser.add_argument(
        "--type", default=None, choices=ENTITY_DIRS,
        help="Restrict search to a single entity directory"
    )
    parser.add_argument(
        "--top", type=int, default=15,
        help="Max results to show (default: 15)"
    )
    parser.add_argument(
        "--threshold", type=float, default=None,
        help="Minimum similarity (0.0-1.0). Default: 0.35"
    )
    args = parser.parse_args()

    threshold = args.threshold if args.threshold is not None else THRESHOLD_POTENTIAL
    query_str = " ".join(args.query)
    wiki_root = Path(args.wiki_root).resolve()

    results = search(query_str, wiki_root, args.type, args.top, threshold)
    print(format_results(results))


if __name__ == "__main__":
    main()
