#!/usr/bin/env python3
"""Deterministic helpers for the /daily-arxiv recommendation pipeline.

The slash skill is the policy and LLM judgment layer. This helper keeps the
repeatable parts in one place: config resolution, arXiv feed handling, wiki
profile extraction, optional external enrichment, and digest formatting.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import _env  # noqa: F401 - load .env files when present
except Exception:  # pragma: no cover - defensive for unusual invocation paths
    pass

try:
    import fetch_arxiv
except Exception:  # pragma: no cover - reported when fetch is requested
    fetch_arxiv = None  # type: ignore

try:
    import fetch_s2
except Exception:  # pragma: no cover - Semantic Scholar is optional
    fetch_s2 = None  # type: ignore

try:
    import fetch_deepxiv
except Exception:  # pragma: no cover - DeepXiv is optional
    fetch_deepxiv = None  # type: ignore

try:
    import requests
except Exception:  # pragma: no cover - reported when third-party LLM is used
    requests = None  # type: ignore


ARXIV_ID_RE = re.compile(r"(?<![\w./-])(\d{4}\.\d{4,5})(?:v\d+)?(?![\w.-])")
ARXIV_URL_RE = re.compile(
    r"https?://arxiv\.org/(?:abs|pdf)/([A-Za-z0-9./-]+)", re.IGNORECASE
)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
STOPWORDS = {
    "about",
    "after",
    "also",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "its",
    "new",
    "of",
    "on",
    "or",
    "our",
    "paper",
    "that",
    "the",
    "their",
    "this",
    "to",
    "using",
    "via",
    "we",
    "with",
}

DEFAULT_CATEGORIES = ["cs.LG", "cs.CV", "cs.CL", "cs.AI", "stat.ML"]
DEFAULT_CONFIG: dict[str, Any] = {
    "mode": "inform",
    "hours": 24,
    "categories": DEFAULT_CATEGORIES,
    "max_recommendations": 10,
    "max_auto_ingest": 1,
    "email": {"enabled": True},
    "schedule": {"enabled": True, "cron": "17 0 * * *"},
    "profile": {
        "derive_from_wiki": True,
        "positive_topics": [],
        "negative_topics": [],
        "positive_papers": [],
        "negative_papers": [],
    },
    "enrichment": {
        "semantic_scholar": True,
        "deepxiv": True,
        "s2_anchor_limit": 5,
        "s2_candidate_limit": 12,
        "s2_recommendation_limit": 50,
        "deepxiv_brief_limit": 8,
        "deepxiv_trending_days": 7,
        "deepxiv_trending_limit": 50,
    },
}


# ---------------------------------------------------------------------------
# Lightweight config loading
# ---------------------------------------------------------------------------


def _in_quotes(line: str) -> bool:
    in_single = False
    in_double = False
    for ch in line:
        if ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == "#" and not in_single and not in_double:
            return False
    return True


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value or value in {'""', "''"}:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.lower() in {"true", "yes", "on"}:
        return True
    if value.lower() in {"false", "no", "off"}:
        return False
    if value.lower() in {"null", "none"}:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _parse_inline_list(value: str) -> list[Any]:
    inner = value.strip()[1:-1]
    return [_parse_scalar(part.strip()) for part in inner.split(",") if part.strip()]


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by config/daily-arxiv.yml.

    Supports scalars, inline lists, block lists, nested dicts, and comments.
    This avoids adding PyYAML only for one config file.
    """
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(-1, result)]
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.split("#")[0].rstrip() if "#" in raw and not _in_quotes(raw) else raw.rstrip()
        i += 1
        if not stripped or stripped.lstrip().startswith("#"):
            continue

        indent = len(stripped) - len(stripped.lstrip())
        item = stripped.lstrip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            stack = [(-1, result)]
        parent = stack[-1][1]

        if item.startswith("- "):
            if isinstance(parent, list):
                parent.append(_parse_scalar(item[2:].strip()))
            continue

        if ":" not in item or not isinstance(parent, dict):
            continue
        key, rest = item.split(":", 1)
        key = key.strip().strip('"').strip("'")
        rest = rest.strip()

        if not rest:
            j = i
            next_item = ""
            while j < len(lines):
                nxt = lines[j]
                candidate = nxt.split("#")[0].rstrip() if "#" in nxt and not _in_quotes(nxt) else nxt.rstrip()
                if candidate.strip():
                    next_item = candidate.lstrip()
                    break
                j += 1
            child: dict[str, Any] | list[Any] = [] if next_item.startswith("- ") else {}
            parent[key] = child
            stack.append((indent, child))
        elif rest.startswith("[") and rest.endswith("]"):
            parent[key] = _parse_inline_list(rest)
        elif rest.startswith("{") and rest.endswith("}"):
            inline: dict[str, Any] = {}
            inner = rest[1:-1].strip()
            for pair in [p.strip() for p in inner.split(",") if p.strip()]:
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    inline[k.strip().strip('"').strip("'")] = _parse_scalar(v)
            parent[key] = inline
        else:
            parent[key] = _parse_scalar(rest)
    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        elif value is not None:
            merged[key] = value
    return merged


def _split_categories(value: Any) -> list[str]:
    if value is None:
        return []
    parts: list[str] = []
    values = value if isinstance(value, list) else [value]
    for raw in values:
        parts.extend(re.split(r"[\s,]+", str(raw).strip()))
    return [part for part in parts if part]


def _as_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def _coerce_int(value: Any, default: int, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, parsed)


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_config(path: Path | None, overrides: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    cfg = deepcopy(DEFAULT_CONFIG)
    config_found = False

    if path and path.exists():
        raw = path.read_text(encoding="utf-8")
        parsed = _parse_simple_yaml(raw)
        cfg = _deep_merge(cfg, parsed)
        config_found = True
    elif path:
        notes.append(f"No config found at {path}; using inferred defaults.")

    if not config_found:
        env_categories = _split_categories(os.environ.get("ARXIV_CATEGORIES"))
        if env_categories:
            cfg["categories"] = env_categories
            notes.append("Using ARXIV_CATEGORIES from the environment.")

    overrides = overrides or {}
    if overrides:
        cfg = _deep_merge(cfg, overrides)

    cfg["mode"] = str(cfg.get("mode") or "inform")
    if cfg["mode"] not in {"inform", "auto-ingest"}:
        notes.append(f"Unknown mode {cfg['mode']!r}; falling back to inform.")
        cfg["mode"] = "inform"

    categories = _split_categories(cfg.get("categories"))
    cfg["categories"] = categories or DEFAULT_CATEGORIES
    cfg["hours"] = _coerce_int(cfg.get("hours"), 24, 1)
    cfg["max_recommendations"] = _coerce_int(cfg.get("max_recommendations"), 10, 0)
    cfg["max_auto_ingest"] = _coerce_int(cfg.get("max_auto_ingest"), 1, 0)
    cfg.setdefault("email", {})
    cfg["email"]["enabled"] = _coerce_bool(cfg["email"].get("enabled"), True)
    cfg.setdefault("schedule", {})
    cfg["schedule"]["enabled"] = _coerce_bool(cfg["schedule"].get("enabled"), True)
    cfg["schedule"]["cron"] = str(cfg["schedule"].get("cron") or "17 0 * * *")

    profile = cfg.setdefault("profile", {})
    profile["derive_from_wiki"] = _coerce_bool(profile.get("derive_from_wiki"), True)
    for key in ("positive_topics", "negative_topics", "positive_papers", "negative_papers"):
        profile[key] = _as_text_list(profile.get(key))

    enrichment = cfg.setdefault("enrichment", {})
    enrichment["semantic_scholar"] = _coerce_bool(enrichment.get("semantic_scholar"), True)
    enrichment["deepxiv"] = _coerce_bool(enrichment.get("deepxiv"), True)
    for key, default in (
        ("s2_anchor_limit", 5),
        ("s2_candidate_limit", 12),
        ("s2_recommendation_limit", 50),
        ("deepxiv_brief_limit", 8),
        ("deepxiv_trending_days", 7),
        ("deepxiv_trending_limit", 50),
    ):
        enrichment[key] = _coerce_int(enrichment.get(key), default, 0)

    cfg["_config_path"] = str(path) if path else ""
    cfg["_config_found"] = config_found
    return cfg, notes


# ---------------------------------------------------------------------------
# arXiv and wiki normalization
# ---------------------------------------------------------------------------


def _normalize_arxiv_id(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    url_match = ARXIV_URL_RE.search(text)
    if url_match:
        text = url_match.group(1)
    text = text.removesuffix(".pdf").rstrip("/")
    text = re.sub(r"^arxiv:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"v\d+$", "", text)
    return text


def _extract_arxiv_ids(text: str) -> set[str]:
    ids = {_normalize_arxiv_id(match.group(1)) for match in ARXIV_ID_RE.finditer(text)}
    ids.update(_normalize_arxiv_id(match.group(1)) for match in ARXIV_URL_RE.finditer(text))
    return {aid for aid in ids if aid}


def _known_arxiv_ids(wiki_root: Path) -> set[str]:
    known: set[str] = set()
    if not wiki_root.exists():
        return known

    index_path = wiki_root / "index.md"
    if index_path.exists():
        known.update(_extract_arxiv_ids(index_path.read_text(encoding="utf-8", errors="ignore")))

    papers_dir = wiki_root / "papers"
    if papers_dir.exists():
        for path in papers_dir.glob("*.md"):
            known.update(_extract_arxiv_ids(path.read_text(encoding="utf-8", errors="ignore")))
    return known


def _load_feed(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"expected a list of papers in {path}")
    return [item for item in data if isinstance(item, dict)]


def _fetch_feed(cfg: dict[str, Any], out_path: Path | None = None) -> list[dict[str, Any]]:
    if fetch_arxiv is None:
        raise RuntimeError("tools/fetch_arxiv.py could not be imported")
    papers = fetch_arxiv.fetch_recent(
        hours=int(cfg["hours"]),
        categories=list(cfg["categories"]),
    )
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(papers, indent=2, ensure_ascii=False), encoding="utf-8")
    return papers


def _paper_url(paper: dict[str, Any], arxiv_id: str) -> str:
    url = str(paper.get("arxiv_url") or paper.get("url") or "").strip()
    if url:
        return url
    return f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""


def _abstract_preview(text: str, limit: int = 360) -> str:
    compact = re.sub(r"\s+", " ", (text or "").strip())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def _normalize_authors(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for item in value:
        if isinstance(item, str):
            name = item.strip()
        elif isinstance(item, dict):
            name = str(item.get("name") or "").strip()
        else:
            name = ""
        if name:
            authors.append(name)
    return authors


def _title_from_markdown(text: str, fallback: str) -> str:
    match = TITLE_RE.search(text)
    if match:
        return re.sub(r"\s+", " ", match.group(1).strip())
    return fallback


def _frontmatter_value(text: str, key: str) -> str:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return ""
    pattern = re.compile(rf"^{re.escape(key)}\s*:\s*[\"']?([^\"'\n]+)", re.MULTILINE)
    found = pattern.search(match.group(1))
    return found.group(1).strip() if found else ""


def _read_markdown_cards(directory: Path, limit: int = 12) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    paths = sorted(directory.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    cards: list[dict[str, Any]] = []
    for path in paths[:limit]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        cards.append(
            {
                "path": str(path),
                "title": _title_from_markdown(text, path.stem.replace("-", " ")),
                "arxiv_id": _normalize_arxiv_id(_frontmatter_value(text, "arxiv") or _frontmatter_value(text, "arxiv_id")),
                "preview": _abstract_preview(re.sub(FRONTMATTER_RE, "", text), 500),
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
            }
        )
    return cards


def _extract_open_questions(cards: list[dict[str, Any]], log_text: str) -> list[str]:
    questions: list[str] = []
    for source in [log_text] + [card.get("preview", "") for card in cards]:
        for line in source.splitlines():
            compact = re.sub(r"\s+", " ", line.strip(" -#\t"))
            lower = compact.lower()
            if compact and ("?" in compact or "open question" in lower or "gap" in lower):
                questions.append(compact[:240])
            if len(questions) >= 10:
                return questions
    return questions


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower())
        if token not in STOPWORDS and not token.isdigit()
    ]


def build_wiki_profile(wiki_root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    papers = _read_markdown_cards(wiki_root / "papers", limit=12)
    topics = _read_markdown_cards(wiki_root / "topics", limit=12)
    concepts = _read_markdown_cards(wiki_root / "concepts", limit=12)
    methods = _read_markdown_cards(wiki_root / "methods", limit=8)
    ideas = _read_markdown_cards(wiki_root / "ideas", limit=8)
    log_path = wiki_root / "log.md"
    log_text = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""
    recent_log = "\n".join(log_text.splitlines()[-20:])

    profile_cfg = cfg.get("profile", {})
    text_parts = []
    if profile_cfg.get("derive_from_wiki", True):
        for collection in (papers, topics, concepts, methods, ideas):
            text_parts.extend(f"{card.get('title', '')} {card.get('preview', '')}" for card in collection)
        text_parts.append(recent_log)
    text_parts.extend(profile_cfg.get("positive_topics") or [])
    text_parts.extend(profile_cfg.get("positive_papers") or [])

    token_counts = Counter(_tokenize("\n".join(text_parts)))
    negative_tokens = set(_tokenize(" ".join(profile_cfg.get("negative_topics") or [])))
    keywords = [token for token, _ in token_counts.most_common(40) if token not in negative_tokens]

    anchors = [
        {"arxiv_id": card["arxiv_id"], "title": card["title"], "path": card["path"]}
        for card in papers
        if card.get("arxiv_id")
    ]
    all_cards = papers + topics + concepts + methods + ideas
    return {
        "wiki_root": str(wiki_root),
        "is_sparse": not bool(papers or topics or concepts or methods or ideas),
        "anchors": anchors,
        "keywords": keywords,
        "positive_preferences": profile_cfg.get("positive_topics") or [],
        "negative_preferences": profile_cfg.get("negative_topics") or [],
        "papers": papers,
        "topics": topics,
        "concepts": concepts,
        "methods": methods,
        "ideas": ideas,
        "open_questions": _extract_open_questions(all_cards, recent_log),
        "recent_log": recent_log,
    }


def _candidate_record(paper: dict[str, Any], known_ids: set[str]) -> dict[str, Any]:
    arxiv_id = _normalize_arxiv_id(str(paper.get("arxiv_id") or paper.get("arxiv_url") or ""))
    title = re.sub(r"\s+", " ", str(paper.get("title") or "").strip())
    category = str(paper.get("category") or "").strip()
    abstract = re.sub(r"\s+", " ", str(paper.get("abstract") or paper.get("summary") or "").strip())
    known = bool(arxiv_id and arxiv_id in known_ids)
    return {
        "arxiv_id": arxiv_id,
        "title": title or "(untitled)",
        "authors": _normalize_authors(paper.get("authors")),
        "arxiv_url": _paper_url(paper, arxiv_id),
        "category": category,
        "published": str(paper.get("published") or "").strip(),
        "abstract": abstract,
        "abstract_preview": _abstract_preview(abstract),
        "is_known": known,
        "decision": "already_in_wiki" if known else "unjudged",
        "confidence": None,
        "score": None,
        "rationale": "Already represented in the wiki." if known else "",
        "wiki_connections": [],
        "signals_used": [],
        "tool_rank_score": 0.0,
        "signals": {
            "arxiv_rss": True,
            "semantic_scholar": None,
            "deepxiv": None,
            "llm": None,
        },
    }


# ---------------------------------------------------------------------------
# Enrichment and ranking
# ---------------------------------------------------------------------------


def _arxiv_from_external_ids(raw: dict[str, Any]) -> str:
    external = raw.get("externalIds") or {}
    for key in ("ArXiv", "arXiv", "ARXIV"):
        if external.get(key):
            return _normalize_arxiv_id(str(external[key]))
    return _normalize_arxiv_id(str(raw.get("arxiv_id") or ""))


def _safe_title_key(title: str) -> str:
    return re.sub(r"\W+", " ", title.lower()).strip()


def _semantic_scholar_enrich(candidates: list[dict[str, Any]], wiki_profile: dict[str, Any], cfg: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    enrichment_cfg = cfg.get("enrichment", {})
    if not enrichment_cfg.get("semantic_scholar", True):
        return ["Semantic Scholar enrichment disabled by config."]
    if fetch_s2 is None:
        return ["Semantic Scholar enrichment unavailable: tools/fetch_s2.py could not be imported."]

    anchors = [anchor["arxiv_id"] for anchor in wiki_profile.get("anchors", []) if anchor.get("arxiv_id")]
    anchors = anchors[: enrichment_cfg.get("s2_anchor_limit", 5)]
    recommendation_ids: set[str] = set()
    recommendation_titles: set[str] = set()
    if anchors:
        try:
            recommendations = fetch_s2.recommend(
                anchors,
                limit=enrichment_cfg.get("s2_recommendation_limit", 50),
            )
            for item in recommendations:
                aid = _arxiv_from_external_ids(item)
                if aid:
                    recommendation_ids.add(aid)
                if item.get("title"):
                    recommendation_titles.add(_safe_title_key(str(item["title"])))
        except Exception as exc:
            notes.append(f"Semantic Scholar recommendations degraded: {exc}")
    else:
        notes.append("Semantic Scholar recommendations skipped: no wiki arXiv anchors found.")

    limit = min(len(candidates), enrichment_cfg.get("s2_candidate_limit", 12))
    for candidate in candidates[:limit]:
        if candidate.get("is_known") or not candidate.get("arxiv_id"):
            continue
        signal: dict[str, Any] = {
            "recommended_from_wiki_anchors": candidate["arxiv_id"] in recommendation_ids
            or _safe_title_key(candidate["title"]) in recommendation_titles,
        }
        try:
            detail = fetch_s2.paper(candidate["arxiv_id"])
            signal.update(
                {
                    "paperId": detail.get("paperId", ""),
                    "year": detail.get("year"),
                    "citation_count": detail.get("citationCount", 0),
                    "influential_citation_count": detail.get("influentialCitationCount", 0),
                    "fields_of_study": detail.get("fieldsOfStudy") or [],
                    "venue": detail.get("venue") or "",
                    "tldr": (detail.get("tldr") or {}).get("text", "")
                    if isinstance(detail.get("tldr"), dict)
                    else (detail.get("tldr") or ""),
                }
            )
        except Exception as exc:
            signal["error"] = str(exc)
            notes.append(f"S2 metadata degraded for {candidate['arxiv_id']}: {exc}")
        candidate["signals"]["semantic_scholar"] = signal
    return notes


def _deepxiv_enrich(candidates: list[dict[str, Any]], cfg: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    enrichment_cfg = cfg.get("enrichment", {})
    if not enrichment_cfg.get("deepxiv", True):
        return ["DeepXiv enrichment disabled by config."]
    if fetch_deepxiv is None:
        return ["DeepXiv enrichment unavailable: tools/fetch_deepxiv.py could not be imported."]

    trending_by_id: dict[str, dict[str, Any]] = {}
    try:
        trending = fetch_deepxiv.trending(
            days=enrichment_cfg.get("deepxiv_trending_days", 7),
            limit=enrichment_cfg.get("deepxiv_trending_limit", 50),
        )
        trending_by_id = {
            _normalize_arxiv_id(str(item.get("arxiv_id") or "")): item
            for item in trending
            if item.get("arxiv_id")
        }
    except Exception as exc:
        notes.append(f"DeepXiv trending degraded: {exc}")

    limit = min(len(candidates), enrichment_cfg.get("deepxiv_brief_limit", 8))
    for candidate in candidates[:limit]:
        if candidate.get("is_known") or not candidate.get("arxiv_id"):
            continue
        aid = candidate["arxiv_id"]
        signal: dict[str, Any] = {}
        if aid in trending_by_id:
            trend = trending_by_id[aid]
            signal["trending_rank"] = trend.get("rank")
            signal["social_impact"] = trend.get("social_impact") or {}
        try:
            brief = fetch_deepxiv.brief(aid)
            signal.update(
                {
                    "tldr": brief.get("tldr", ""),
                    "keywords": brief.get("keywords") or [],
                    "citations": brief.get("citations", 0),
                    "github_url": brief.get("github_url"),
                }
            )
        except Exception as exc:
            signal["error"] = str(exc)
            notes.append(f"DeepXiv brief degraded for {aid}: {exc}")
        candidate["signals"]["deepxiv"] = signal
    return notes


def _score_candidates(candidates: list[dict[str, Any]], wiki_profile: dict[str, Any]) -> None:
    keywords = set(wiki_profile.get("keywords") or [])
    sparse = wiki_profile.get("is_sparse", True)
    for candidate in candidates:
        if candidate.get("is_known"):
            continue
        text = " ".join([candidate.get("title", ""), candidate.get("abstract", "")])
        tokens = set(_tokenize(text))
        overlap = sorted(tokens & keywords)
        if overlap:
            candidate["wiki_connections"] = overlap[:8]

        score = 0.0
        if sparse:
            score += 0.15
        if keywords:
            score += min(0.35, len(overlap) / max(8, len(keywords)) * 1.5)
        if candidate.get("category") in DEFAULT_CATEGORIES:
            score += 0.08

        s2 = candidate["signals"].get("semantic_scholar") or {}
        if s2.get("recommended_from_wiki_anchors"):
            score += 0.25
        score += min(0.12, float(s2.get("influential_citation_count") or 0) / 50)
        score += min(0.08, float(s2.get("citation_count") or 0) / 500)

        deepxiv = candidate["signals"].get("deepxiv") or {}
        if deepxiv.get("trending_rank"):
            try:
                rank = int(deepxiv["trending_rank"])
                score += max(0.0, 0.15 - (rank - 1) * 0.003)
            except (TypeError, ValueError):
                pass
        if deepxiv.get("tldr") or s2.get("tldr"):
            score += 0.05

        candidate["tool_rank_score"] = round(min(1.0, score), 3)
        used = ["arxiv"]
        if s2:
            used.append("semantic_scholar")
        if deepxiv:
            used.append("deepxiv")
        if overlap:
            used.append("wiki_profile")
        candidate["signals_used"] = used


def build_recommendation_context(
    *,
    feed: list[dict[str, Any]],
    feed_path: Path | None,
    wiki_root: Path,
    cfg: dict[str, Any],
    config_notes: list[str],
    enrich: bool = True,
) -> dict[str, Any]:
    known_ids = _known_arxiv_ids(wiki_root)
    candidates = [_candidate_record(paper, known_ids) for paper in feed]
    new_candidates = [candidate for candidate in candidates if not candidate["is_known"]]
    category_counts = Counter(candidate["category"] or "unknown" for candidate in new_candidates)
    wiki_profile = build_wiki_profile(wiki_root, cfg)

    notes = list(config_notes)
    if enrich:
        notes.extend(_semantic_scholar_enrich(new_candidates, wiki_profile, cfg))
        notes.extend(_deepxiv_enrich(new_candidates, cfg))
    else:
        notes.append("External enrichment skipped by command-line option.")
    _score_candidates(new_candidates, wiki_profile)
    new_candidates.sort(key=lambda item: item.get("tool_rank_score", 0), reverse=True)

    all_candidates = [*new_candidates, *[candidate for candidate in candidates if candidate["is_known"]]]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": cfg["mode"],
        "recommendation_enabled": True,
        "auto_ingest_enabled": cfg["mode"] == "auto-ingest",
        "llm_decision_required": True,
        "config": {
            key: value
            for key, value in cfg.items()
            if key not in {"_config_path", "_config_found"}
        },
        "config_path": cfg.get("_config_path", ""),
        "config_found": bool(cfg.get("_config_found")),
        "feed_path": str(feed_path) if feed_path else "",
        "wiki_root": str(wiki_root),
        "wiki_profile": wiki_profile,
        "counts": {
            "feed_total": len(candidates),
            "already_in_wiki": len(candidates) - len(new_candidates),
            "new_candidates": len(new_candidates),
            "listed": min(len(new_candidates), int(cfg["max_recommendations"])),
        },
        "category_counts": dict(sorted(category_counts.items())),
        "candidates": all_candidates,
        "candidate_order": [candidate.get("arxiv_id") or candidate.get("title") for candidate in new_candidates],
        "notes": [note for note in notes if note],
    }


# ---------------------------------------------------------------------------
# Finalization and markdown formatting
# ---------------------------------------------------------------------------


VALID_DECISIONS = {"strong_recommend", "maybe", "skip", "ingest"}
VALID_CONFIDENCE = {"high", "medium", "low"}


def _candidate_key(candidate: dict[str, Any]) -> str:
    return candidate.get("arxiv_id") or _safe_title_key(candidate.get("title", ""))


def _load_decisions(path: Path | None) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if not path or not path.exists():
        return {}, ["LLM decisions were not provided; using tool-ranked fallback digest."]
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict) and isinstance(data.get("decisions"), list):
        raw_items = data["decisions"]
    elif isinstance(data, dict):
        raw_items = []
        for key, value in data.items():
            if isinstance(value, dict):
                item = dict(value)
                item.setdefault("arxiv_id", key)
                raw_items.append(item)
    else:
        raise ValueError(f"Unsupported decisions payload in {path}")

    decisions: dict[str, dict[str, Any]] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        key = _normalize_arxiv_id(str(item.get("arxiv_id") or "")) or _safe_title_key(str(item.get("title") or ""))
        if key:
            decisions[key] = item
    return decisions, []


def _merge_decision(candidate: dict[str, Any], decision: dict[str, Any] | None, llm_available: bool) -> dict[str, Any]:
    out = deepcopy(candidate)
    if out.get("is_known"):
        return out

    if not decision:
        out["decision"] = "maybe"
        out["confidence"] = "low"
        out["score"] = out.get("tool_rank_score")
        out["rationale"] = "LLM decisions were not available; this candidate is shown from the deterministic evidence ranking."
        out["signals"]["llm"] = False
        return out

    normalized = str(decision.get("decision") or "maybe").strip()
    if normalized not in VALID_DECISIONS:
        normalized = "maybe"
    confidence = str(decision.get("confidence") or "medium").strip()
    if confidence not in VALID_CONFIDENCE:
        confidence = "medium"

    out["decision"] = normalized
    out["confidence"] = confidence
    decision_score = decision.get("score")
    out["score"] = decision_score if isinstance(decision_score, (int, float)) else out.get("tool_rank_score")
    out["rationale"] = str(decision.get("rationale") or out.get("rationale") or "").strip()
    out["wiki_connections"] = decision.get("wiki_connections") or out.get("wiki_connections") or []
    out["signals_used"] = decision.get("signals_used") or out.get("signals_used") or []
    if decision.get("ingest_status"):
        out["ingest_status"] = decision["ingest_status"]
    if decision.get("ingest_error"):
        out["ingest_error"] = decision["ingest_error"]
    out["signals"]["llm"] = llm_available
    return out


def finalize_payload(context: dict[str, Any], decisions_path: Path | None = None) -> dict[str, Any]:
    decisions, notes = _load_decisions(decisions_path)
    llm_available = bool(decisions)
    cfg = context.get("config") or {}
    mode = context.get("mode") or cfg.get("mode") or "inform"
    max_auto = _coerce_int(cfg.get("max_auto_ingest"), 1, 0)

    finalized: list[dict[str, Any]] = []
    for candidate in context.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        key = _candidate_key(candidate)
        decision = decisions.get(key)
        finalized.append(_merge_decision(candidate, decision, llm_available))

    new_candidates = [candidate for candidate in finalized if not candidate.get("is_known")]
    ordered = sorted(
        new_candidates,
        key=lambda item: (
            1 if item.get("decision") == "ingest" else 0,
            1 if item.get("decision") == "strong_recommend" else 0,
            item.get("score") if isinstance(item.get("score"), (int, float)) else item.get("tool_rank_score", 0),
        ),
        reverse=True,
    )
    selected = [
        candidate
        for candidate in ordered
        if mode == "auto-ingest"
        and candidate.get("decision") == "ingest"
        and candidate.get("confidence") == "high"
    ][:max_auto]
    selected_keys = {_candidate_key(candidate) for candidate in selected}
    for candidate in finalized:
        if candidate.get("decision") == "ingest" and _candidate_key(candidate) not in selected_keys:
            candidate["auto_ingest_blocked"] = (
                "not selected because mode/cap/confidence guard did not permit ingestion"
            )

    payload = deepcopy(context)
    payload["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload["llm_decision_available"] = llm_available
    payload["candidates"] = finalized
    payload["listed_candidates"] = ordered[: _coerce_int(cfg.get("max_recommendations"), 10, 0)]
    payload["auto_ingest"] = {
        "enabled": mode == "auto-ingest",
        "cap": max_auto,
        "selected": [
            {
                "arxiv_id": candidate.get("arxiv_id"),
                "title": candidate.get("title"),
                "arxiv_url": candidate.get("arxiv_url"),
                "confidence": candidate.get("confidence"),
            }
            for candidate in selected
        ],
        "requires_ingest_skill": True,
    }
    payload["notes"] = [*(context.get("notes") or []), *notes]
    return payload


def _format_authors(authors: list[str], limit: int = 3) -> str:
    if not authors:
        return "unknown authors"
    shown = authors[:limit]
    suffix = " et al." if len(authors) > limit else ""
    return ", ".join(shown) + suffix


def _format_signal_summary(candidate: dict[str, Any]) -> str:
    bits: list[str] = []
    s2 = candidate.get("signals", {}).get("semantic_scholar") or {}
    if s2.get("recommended_from_wiki_anchors"):
        bits.append("S2 wiki-anchor match")
    if s2.get("citation_count"):
        bits.append(f"{s2['citation_count']} citations")
    if s2.get("influential_citation_count"):
        bits.append(f"{s2['influential_citation_count']} influential")
    deepxiv = candidate.get("signals", {}).get("deepxiv") or {}
    if deepxiv.get("trending_rank"):
        bits.append(f"DeepXiv trend #{deepxiv['trending_rank']}")
    if candidate.get("wiki_connections"):
        bits.append("wiki: " + ", ".join(map(str, candidate["wiki_connections"][:4])))
    return "; ".join(bits)


def _format_candidate(lines: list[str], index: int, paper: dict[str, Any]) -> None:
    title = paper["title"]
    url = paper["arxiv_url"]
    arxiv_id = paper["arxiv_id"] or "unknown-id"
    category = paper["category"] or "unknown"
    authors = _format_authors(paper.get("authors") or [])
    score = paper.get("score")
    if score is None:
        score = paper.get("tool_rank_score")
    lines.append(f"{index}. **{title}**")
    lines.append(f"   - arXiv: [{arxiv_id}]({url})")
    lines.append(f"   - Category: `{category}`")
    lines.append(f"   - Authors: {authors}")
    lines.append(f"   - Decision: `{paper.get('decision')}` / confidence `{paper.get('confidence')}` / score `{score}`")
    if paper.get("published"):
        lines.append(f"   - Published: {paper['published']}")
    signal_summary = _format_signal_summary(paper)
    if signal_summary:
        lines.append(f"   - Signals: {signal_summary}")
    if paper.get("rationale"):
        lines.append(f"   - Rationale: {paper['rationale']}")
    if paper.get("abstract_preview"):
        lines.append(f"   - Abstract: {paper['abstract_preview']}")
    if paper.get("ingest_status"):
        lines.append(f"   - Ingest: {paper['ingest_status']}")
    if paper.get("ingest_error"):
        lines.append(f"   - Ingest error: {paper['ingest_error']}")
    lines.append("")


def format_markdown(payload: dict[str, Any]) -> str:
    counts = payload["counts"]
    mode = payload.get("mode", "inform")
    lines = [
        "# Daily arXiv Recommendations",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Feed papers scanned: {counts['feed_total']}",
        f"- Already in wiki: {counts['already_in_wiki']}",
        f"- New candidates: {counts['new_candidates']}",
        f"- Listed in this digest: {counts['listed']}",
        f"- Mode: `{mode}`",
        f"- LLM decisions: {'available' if payload.get('llm_decision_available') else 'not available; tool-ranked fallback'}",
        "",
    ]

    auto_ingest = payload.get("auto_ingest") or {}
    if auto_ingest:
        lines.extend(["## Auto-Ingest", ""])
        if not auto_ingest.get("enabled"):
            lines.append("Auto-ingest is disabled for this run.")
        elif not auto_ingest.get("selected"):
            lines.append("Auto-ingest is enabled, but no high-confidence candidates passed the guard.")
        else:
            lines.append(f"Selected for `/ingest` (cap {auto_ingest.get('cap', 0)}):")
            for item in auto_ingest["selected"]:
                lines.append(f"- [{item.get('arxiv_id')}]({item.get('arxiv_url')}) — {item.get('title')}")
        lines.append("")

    listed = payload.get("listed_candidates") or []
    strong = [paper for paper in listed if paper.get("decision") in {"ingest", "strong_recommend"}]
    maybe = [paper for paper in listed if paper.get("decision") == "maybe"]
    skipped = [paper for paper in listed if paper.get("decision") == "skip"]
    unjudged = [paper for paper in listed if paper.get("decision") == "unjudged"]

    for heading, papers in (
        ("Strong Recommendations", strong),
        ("Maybe Interesting", maybe),
        ("Tool-Ranked / Unjudged Candidates", unjudged),
        ("Skipped by Recommender", skipped),
    ):
        lines.extend([f"## {heading}", ""])
        if not papers:
            lines.append("None.")
            lines.append("")
            continue
        for index, paper in enumerate(papers, start=1):
            _format_candidate(lines, index, paper)

    known = [paper for paper in payload.get("candidates", []) if paper.get("is_known")]
    if known:
        lines.extend(["## Skipped Duplicates", ""])
        for paper in known[:10]:
            lines.append(f"- `{paper.get('arxiv_id') or 'unknown-id'}` — {paper.get('title')}")
        lines.append("")

    if payload.get("category_counts"):
        lines.extend(["## New Candidates by Category", ""])
        for category, count in payload["category_counts"].items():
            lines.append(f"- `{category}`: {count}")
        lines.append("")

    notes = payload.get("notes") or []
    if notes:
        lines.extend(["## Notes", ""])
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# OpenAI-compatible LLM recommendation for inform mode
# ---------------------------------------------------------------------------


def _llm_env() -> dict[str, str]:
    return {
        "api_key": os.environ.get("LLM_API_KEY", "").strip(),
        "base_url": os.environ.get("LLM_BASE_URL", "").strip().rstrip("/"),
        "model": os.environ.get("LLM_MODEL", "").strip(),
        "fallback_model": os.environ.get("LLM_FALLBACK_MODEL", "").strip(),
    }


def _require_llm_env() -> dict[str, str]:
    env = _llm_env()
    missing = [name for name, key in (("LLM_API_KEY", "api_key"), ("LLM_BASE_URL", "base_url"), ("LLM_MODEL", "model")) if not env[key]]
    if missing:
        raise RuntimeError("third-party LLM unavailable; missing " + ", ".join(missing))
    if requests is None:
        raise RuntimeError("third-party LLM unavailable; requests is not installed")
    return env


def _llm_signal_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    s2 = candidate.get("signals", {}).get("semantic_scholar") or {}
    deepxiv = candidate.get("signals", {}).get("deepxiv") or {}
    return {
        "tool_rank_score": candidate.get("tool_rank_score"),
        "wiki_connections": candidate.get("wiki_connections") or [],
        "semantic_scholar": {
            key: s2.get(key)
            for key in (
                "recommended_from_wiki_anchors",
                "year",
                "citation_count",
                "influential_citation_count",
                "fields_of_study",
                "venue",
                "tldr",
            )
            if s2.get(key) not in (None, "", [])
        },
        "deepxiv": {
            key: deepxiv.get(key)
            for key in ("trending_rank", "social_impact", "tldr", "keywords", "citations", "github_url")
            if deepxiv.get(key) not in (None, "", [])
        },
    }


def _compact_llm_context(context: dict[str, Any], limit: int | None = None) -> dict[str, Any]:
    cfg = context.get("config") or {}
    recommendation_limit = _coerce_int(limit, _coerce_int(cfg.get("max_recommendations"), 10, 0), 0)
    candidates = [
        candidate
        for candidate in context.get("candidates", [])
        if isinstance(candidate, dict) and not candidate.get("is_known")
    ]
    candidates = sorted(candidates, key=lambda item: item.get("tool_rank_score", 0), reverse=True)
    if recommendation_limit:
        candidates = candidates[:recommendation_limit]

    wiki_profile = context.get("wiki_profile") or {}
    compact_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        compact_candidates.append(
            {
                "arxiv_id": candidate.get("arxiv_id"),
                "title": candidate.get("title"),
                "authors": candidate.get("authors") or [],
                "category": candidate.get("category"),
                "published": candidate.get("published"),
                "arxiv_url": candidate.get("arxiv_url"),
                "abstract": candidate.get("abstract") or candidate.get("abstract_preview"),
                "signals": _llm_signal_summary(candidate),
            }
        )

    return {
        "mode": context.get("mode"),
        "generated_at": context.get("generated_at"),
        "config": {
            "max_recommendations": cfg.get("max_recommendations"),
            "categories": cfg.get("categories"),
            "profile": cfg.get("profile"),
        },
        "wiki_profile": {
            "is_sparse": wiki_profile.get("is_sparse"),
            "keywords": (wiki_profile.get("keywords") or [])[:40],
            "positive_preferences": wiki_profile.get("positive_preferences") or [],
            "negative_preferences": wiki_profile.get("negative_preferences") or [],
            "open_questions": (wiki_profile.get("open_questions") or [])[:10],
            "anchors": (wiki_profile.get("anchors") or [])[:8],
            "papers": (wiki_profile.get("papers") or [])[:6],
            "topics": (wiki_profile.get("topics") or [])[:8],
            "concepts": (wiki_profile.get("concepts") or [])[:8],
            "ideas": (wiki_profile.get("ideas") or [])[:6],
            "methods": (wiki_profile.get("methods") or [])[:6],
            "recent_log": wiki_profile.get("recent_log", ""),
        },
        "candidates": compact_candidates,
        "degraded_notes": context.get("notes") or [],
    }


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end < start:
            raise
        data = json.loads(stripped[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("LLM response JSON must be an object")
    return data


def _normalize_llm_decisions(payload: dict[str, Any], allowed_ids: set[str], provider: str, model: str) -> dict[str, Any]:
    raw = payload.get("decisions")
    if not isinstance(raw, list):
        raise ValueError("LLM response must contain a decisions list")

    decisions: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        arxiv_id = _normalize_arxiv_id(str(item.get("arxiv_id") or ""))
        if not arxiv_id or arxiv_id not in allowed_ids:
            continue
        decision = str(item.get("decision") or "maybe").strip()
        if decision == "ingest":
            decision = "strong_recommend"
        if decision not in {"strong_recommend", "maybe", "skip"}:
            decision = "maybe"
        confidence = str(item.get("confidence") or "medium").strip()
        if confidence not in VALID_CONFIDENCE:
            confidence = "medium"
        score = item.get("score")
        if not isinstance(score, (int, float)):
            score = None
        decisions.append(
            {
                "arxiv_id": arxiv_id,
                "decision": decision,
                "confidence": confidence,
                "score": score,
                "rationale": str(item.get("rationale") or "").strip(),
                "wiki_connections": item.get("wiki_connections") if isinstance(item.get("wiki_connections"), list) else [],
                "signals_used": item.get("signals_used") if isinstance(item.get("signals_used"), list) else [],
            }
        )

    return {
        "provider": "openai-compatible",
        "base_url": provider,
        "model": model,
        "mode": "inform",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "decisions": decisions,
        "notes": [
            "Generated by a third-party OpenAI-compatible LLM in inform mode.",
            "The `ingest` decision is intentionally unavailable in this path.",
        ],
    }


def _call_openai_compatible(
    *,
    compact_context: dict[str, Any],
    env: dict[str, str],
    timeout: int,
    temperature: float,
) -> dict[str, Any]:
    assert requests is not None
    url = f"{env['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {env['api_key']}",
        "Content-Type": "application/json",
    }
    system = (
        "You are OmegaWiki's daily arXiv recommendation judge. "
        "Use only the provided evidence. Return strict JSON only. "
        "This is inform mode: never select or request ingestion."
    )
    user = (
        "Rank fresh arXiv candidates for this user's research wiki. "
        "For each candidate, choose decision strong_recommend, maybe, or skip; "
        "confidence high, medium, or low; a numeric score from 0 to 1; "
        "a concise evidence-grounded rationale; wiki_connections; and signals_used. "
        "Return exactly {\"decisions\": [...]}.\n\n"
        + json.dumps(compact_context, ensure_ascii=False)
    )

    models = [env["model"]]
    if env.get("fallback_model") and env["fallback_model"] not in models:
        models.append(env["fallback_model"])
    last_error: Exception | None = None
    for model in models:
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        try:
            response = requests.post(url, headers=headers, json=body, timeout=timeout)
            if response.status_code >= 400 and body.get("response_format"):
                body.pop("response_format", None)
                response = requests.post(url, headers=headers, json=body, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = _extract_json_object(content)
            parsed["_model_used"] = model
            return parsed
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(f"third-party LLM recommendation failed: {last_error}")


def run_third_party_recommendation(
    *,
    context: dict[str, Any],
    limit: int | None = None,
    timeout: int = 90,
    temperature: float = 0.1,
) -> dict[str, Any]:
    if context.get("mode") != "inform":
        raise RuntimeError("third-party LLM recommendation is inform-mode only; auto-ingest requires Claude Code runtime")
    env = _require_llm_env()
    compact = _compact_llm_context(context, limit)
    allowed_ids = {
        _normalize_arxiv_id(str(candidate.get("arxiv_id") or ""))
        for candidate in compact.get("candidates", [])
        if candidate.get("arxiv_id")
    }
    if not allowed_ids:
        return {
            "provider": "openai-compatible",
            "base_url": env["base_url"],
            "model": env["model"],
            "mode": "inform",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "decisions": [],
            "notes": ["No new candidates were available for third-party LLM recommendation."],
        }
    raw = _call_openai_compatible(
        compact_context=compact,
        env=env,
        timeout=timeout,
        temperature=temperature,
    )
    model_used = str(raw.pop("_model_used", env["model"]))
    return _normalize_llm_decisions(raw, allowed_ids, env["base_url"], model_used)


# ---------------------------------------------------------------------------
# Backward-compatible scaffold digest
# ---------------------------------------------------------------------------


def build_digest(feed_path: Path, wiki_root: Path, max_items: int) -> dict[str, Any]:
    papers = _load_feed(feed_path)
    known_ids = _known_arxiv_ids(wiki_root)
    candidates = [_candidate_record(paper, known_ids) for paper in papers]
    new_candidates = [paper for paper in candidates if not paper["is_known"]]
    category_counts = Counter(paper["category"] or "unknown" for paper in new_candidates)
    listed = new_candidates[: max(0, max_items)]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "inform",
        "recommendation_enabled": False,
        "auto_ingest_enabled": False,
        "feed_path": str(feed_path),
        "wiki_root": str(wiki_root),
        "counts": {
            "feed_total": len(candidates),
            "already_in_wiki": len(candidates) - len(new_candidates),
            "new_candidates": len(new_candidates),
            "listed": len(listed),
        },
        "category_counts": dict(sorted(category_counts.items())),
        "candidates": candidates,
        "listed_candidates": listed,
        "auto_ingest": {"enabled": False, "cap": 0, "selected": []},
        "llm_decision_available": False,
        "notes": [
            "Compatibility digest only: run `prepare` + LLM decisions + `finalize` for real recommendations.",
            "This fallback does not score, download, ingest, or mutate the wiki.",
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _overrides_from_args(args: argparse.Namespace) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for key in ("mode", "hours", "max_recommendations", "max_auto_ingest"):
        value = getattr(args, key, None)
        if value is not None:
            overrides[key] = value
    categories = _split_categories(getattr(args, "categories", None))
    if categories:
        overrides["categories"] = categories
    send_email = getattr(args, "send_email", None)
    if send_email is not None:
        overrides.setdefault("email", {})["enabled"] = _coerce_bool(send_email)
    return overrides


def cmd_config(args: argparse.Namespace) -> None:
    cfg, notes = load_config(args.config, _overrides_from_args(args))
    payload = {"config": cfg, "notes": notes}
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def cmd_prepare(args: argparse.Namespace) -> None:
    cfg, notes = load_config(args.config, _overrides_from_args(args))
    if args.feed:
        feed = _load_feed(args.feed)
        feed_path = args.feed
    else:
        feed = _fetch_feed(cfg, args.out_feed)
        feed_path = args.out_feed

    payload = build_recommendation_context(
        feed=feed,
        feed_path=feed_path,
        wiki_root=args.wiki_root,
        cfg=cfg,
        config_notes=notes,
        enrich=not args.no_external,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        "daily-arxiv prepare: "
        f"{payload['counts']['new_candidates']} new / "
        f"{payload['counts']['feed_total']} scanned -> {args.out}"
    )


def cmd_finalize(args: argparse.Namespace) -> None:
    context = json.loads(args.context.read_text(encoding="utf-8"))
    payload = finalize_payload(context, args.decisions)
    markdown = format_markdown(payload)

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(markdown, encoding="utf-8")
    args.out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        "daily-arxiv finalize: "
        f"{len(payload.get('listed_candidates', []))} listed -> {args.out_md}"
    )


def cmd_recommend_llm(args: argparse.Namespace) -> None:
    context = json.loads(args.context.read_text(encoding="utf-8"))
    payload = run_third_party_recommendation(
        context=context,
        limit=args.limit,
        timeout=args.timeout,
        temperature=args.temperature,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        "daily-arxiv recommend-llm: "
        f"{len(payload.get('decisions', []))} decisions via {payload.get('model')} -> {args.out}"
    )


def cmd_digest(args: argparse.Namespace) -> None:
    payload = build_digest(args.feed, args.wiki_root, args.max_items)
    markdown = format_markdown(payload)

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(markdown, encoding="utf-8")
    args.out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        "daily-arxiv digest: "
        f"{payload['counts']['new_candidates']} new / "
        f"{payload['counts']['feed_total']} scanned -> {args.out_md}"
    )


def _add_config_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, default=Path("config/daily-arxiv.yml"), help="Daily arXiv config path")
    parser.add_argument("--mode", choices=["inform", "auto-ingest"], help="Override action mode")
    parser.add_argument("--hours", type=int, help="Override lookback window")
    parser.add_argument("--categories", nargs="*", help="Override arXiv categories")
    parser.add_argument("--max-recommendations", type=int, help="Override digest recommendation cap")
    parser.add_argument("--max-auto-ingest", type=int, help="Override auto-ingest cap")
    parser.add_argument("--send-email", help="Override e-mail enabled flag")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OmegaWiki daily arXiv helpers")
    sub = parser.add_subparsers(dest="command", required=True)

    config = sub.add_parser("config", help="Resolve daily arXiv config")
    _add_config_args(config)
    config.add_argument("--out", type=Path, help="Write resolved config JSON")
    config.set_defaults(func=cmd_config)

    prepare = sub.add_parser("prepare", help="Build LLM recommendation context")
    _add_config_args(prepare)
    prepare.add_argument("--feed", type=Path, help="JSON feed from tools/fetch_arxiv.py")
    prepare.add_argument("--out-feed", type=Path, help="When fetching, also write feed JSON here")
    prepare.add_argument("--wiki-root", type=Path, default=Path("wiki"), help="Wiki root for deduplication and profile")
    prepare.add_argument("--out", type=Path, required=True, help="Recommendation context JSON output")
    prepare.add_argument("--no-external", action="store_true", help="Skip S2 and DeepXiv enrichment")
    prepare.set_defaults(func=cmd_prepare)

    finalize = sub.add_parser("finalize", help="Merge LLM decisions and build digest")
    finalize.add_argument("--context", type=Path, required=True, help="Recommendation context JSON from prepare")
    finalize.add_argument("--decisions", type=Path, help="LLM decisions JSON")
    finalize.add_argument("--out-md", type=Path, required=True, help="Markdown digest output path")
    finalize.add_argument("--out-json", type=Path, required=True, help="Machine-readable digest output path")
    finalize.set_defaults(func=cmd_finalize)

    recommend_llm = sub.add_parser(
        "recommend-llm",
        help="Use an OpenAI-compatible LLM to write inform-mode recommendation decisions",
    )
    recommend_llm.add_argument("--context", type=Path, required=True, help="Recommendation context JSON from prepare")
    recommend_llm.add_argument("--out", type=Path, required=True, help="LLM decisions JSON output")
    recommend_llm.add_argument("--limit", type=int, help="Candidate limit sent to the LLM")
    recommend_llm.add_argument("--timeout", type=int, default=90, help="HTTP timeout in seconds")
    recommend_llm.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    recommend_llm.set_defaults(func=cmd_recommend_llm)

    digest = sub.add_parser("digest", help="Build a compatibility inform-only digest")
    digest.add_argument("--feed", type=Path, required=True, help="JSON feed from tools/fetch_arxiv.py")
    digest.add_argument("--wiki-root", type=Path, default=Path("wiki"), help="Wiki root for deduplication")
    digest.add_argument("--out-md", type=Path, required=True, help="Markdown digest output path")
    digest.add_argument("--out-json", type=Path, required=True, help="Machine-readable digest output path")
    digest.add_argument("--max-items", type=int, default=20, help="Maximum new candidates to list")
    digest.set_defaults(func=cmd_digest)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(f"daily-arxiv error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
