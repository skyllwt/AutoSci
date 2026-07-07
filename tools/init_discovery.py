#!/usr/bin/env python3
"""Source preparation + discovery planner for /init.

Usage:
    python3 tools/init_discovery.py prepare --raw-root raw --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json
    python3 tools/init_discovery.py plan [--topic "efficient llm finetuning"] --prepared-manifest .checkpoints/init-prepare.json --output-plan .checkpoints/init-plan.json
    python3 tools/init_discovery.py fetch --raw-root raw --plan-json .checkpoints/init-plan.json --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json --id arxiv:2106.09685
    python3 tools/init_discovery.py handoff --sources-json .checkpoints/init-sources.json --mode serial --output-json .checkpoints/init-handoff.json
    python3 tools/init_discovery.py download --raw-root raw --arxiv-id 2106.09685 --title "Example Paper"
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
import tarfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import requests

from research_wiki import slugify

try:
    import fitz

    HAS_PYMUPDF = True
except ImportError:
    fitz = None
    HAS_PYMUPDF = False

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "in", "into", "is", "it", "of", "on", "or", "that",
    "the", "their", "this", "to", "we", "with", "you", "your",
}
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+/_-]*|[\u4e00-\u9fff]{2,}")
ARXIV_NEW_ID_PATTERN = re.compile(r"(?<!\d)(\d{4}\.\d{4,5}(?:v\d+)?)(?!\d)", re.IGNORECASE)
ARXIV_OLD_ID_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])([a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)(?!\d)",
    re.IGNORECASE,
)
CHINESE_CHAR_PATTERN = re.compile(r"[\u4e00-\u9fff]")
SURVEY_TERMS = {
    "survey", "review", "overview", "benchmark", "tutorial", "taxonomy",
    "roadmap", "empirical study",
}
ASSERTIVE_PATTERNS = (
    "beats", "improves", "outperforms", "is better", "reduces", "achieves",
    "should", "must", "can", "cannot", "fails", "works", "generalizes",
)
IDEA_PATTERNS = (
    "idea", "hypothesis", "we can", "we could", "maybe", "should try",
    "want to", "plan to", "explore", "test whether",
)
EXCLUSION_PATTERNS = (
    "avoid", "exclude", "do not want", "don't want", "not interested",
    "out of scope", "skip",
)
TEXT_SUFFIXES = {".md", ".txt", ".html", ".htm"}
PAPER_SUFFIXES = {".tex", ".pdf", ".zip"}
PREPARE_TEXT_SUFFIXES = {".md", ".txt", ".html", ".htm", ".tex"}
SHORTLIST_TARGET = 12
FINAL_TARGET_RANGE = [8, 10]
CURRENT_YEAR = datetime.now(timezone.utc).year
OLDER_PAPER_YEARS = 4
ROOMY_INTRODUCED_CAPACITY = 6
RANKING_WEIGHTS = {
    "relevance": 30,
    "freshness": 20,
    "anchor_bonus": 20,
    "survey_bonus": 15,
    "citation_centrality": 15,
}
EXCLUSION_PENALTY = 12
MAX_SOURCE_ARCHIVE_BYTES = 250_000_000


def _require_network() -> None:
    """Trigger the Codex sandbox gate only for commands that need network APIs."""
    import _sandbox  # noqa: F401


def _prepare_paper_source(path: Path, raw_root: Path, *, title: str = "", arxiv_id: str = "") -> dict[str, Any]:
    import prepare_paper_source as paper_source

    return paper_source.prepare_paper_source(path, raw_root, title=title, arxiv_id=arxiv_id)


def _s2_search(query: str, limit: int = 20) -> list[dict[str, Any]]:
    _require_network()
    from fetch_s2 import search

    return search(query, limit=limit)


def _s2_citations(arxiv_id: str, limit: int = 40) -> list[dict[str, Any]]:
    _require_network()
    from fetch_s2 import citations

    return citations(arxiv_id, limit=limit)


def _s2_references(arxiv_id: str, limit: int = 40) -> list[dict[str, Any]]:
    _require_network()
    from fetch_s2 import references

    return references(arxiv_id, limit=limit)


def _deepxiv_search(query: str, limit: int = 12) -> list[dict[str, Any]]:
    _require_network()
    from fetch_deepxiv import search

    return search(query, limit=limit)


def _paper_entry_match_key(entry: dict[str, Any]) -> tuple[str, str]:
    return (str(entry.get("arxiv_id") or ""), _normalize_text(str(entry.get("title") or "")))


def _paper_entry_source_key(entry: dict[str, Any]) -> str:
    source_path = Path(str(entry.get("source_path") or ""))
    name = source_path.name.lower()
    if name.endswith(".tar.gz"):
        base = source_path.name[:-7]
    else:
        base = source_path.stem
    return _normalize_text(base.replace("_", " ").replace("-", " "))


def _paper_entry_preference(entry: dict[str, Any]) -> tuple[int, int, int]:
    original_format = str(entry.get("original_format") or "")
    ingest_format = str(entry.get("ingest_format") or "")
    abstract_len = len(str(entry.get("abstract_excerpt") or ""))
    has_arxiv = 1 if entry.get("arxiv_id") else 0

    if original_format == "tex" and ingest_format == "tex":
        rank = 4
    elif original_format in {"archive", "directory"} and ingest_format in {"tex", "directory"}:
        rank = 3
    elif original_format == "pdf" and ingest_format == "directory":
        rank = 3  # fetched arXiv source for a PDF — equivalent to archive
    elif original_format == "pdf" and ingest_format == "tex":
        rank = 2
    elif ingest_format == "pdf":
        rank = 1
    else:
        rank = 0
    return (rank, has_arxiv, abstract_len)


def _project_root(raw_root: Path) -> Path:
    return raw_root.resolve().parent


def _relative_to_project(path: Path, raw_root: Path) -> str:
    return str(path.resolve().relative_to(_project_root(raw_root)))


def _resolve_project_path(raw_root: Path, rel_path: str) -> Path:
    return _project_root(raw_root) / rel_path


def _local_candidate_id(path: Path, raw_root: Path) -> str:
    return f"local:{_path_slug(path.relative_to(raw_root))}"


def _normalize_prepare_source_path(raw_root: Path, source_path: str) -> str:
    raw_source = str(source_path or "").strip()
    if not raw_source:
        return ""

    candidate = Path(raw_source)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        project_root = _project_root(raw_root)
        resolved = (project_root / raw_source).resolve()
        if not resolved.exists() and not raw_source.startswith("raw/"):
            resolved = (raw_root / raw_source).resolve()

    try:
        return _relative_to_project(resolved, raw_root)
    except ValueError:
        return ""


def _normalize_arxiv_id(arxiv_id: str) -> str:
    arxiv_id = str(arxiv_id or "").strip()
    if not arxiv_id:
        return ""
    return re.sub(r"v\d+$", "", arxiv_id, flags=re.IGNORECASE)


def _normalize_pdf_titles_map(
    raw_root: Path,
    pdf_titles: dict[str, Any] | None,
    warning_sink: list[str] | None = None,
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    normalized_payloads: dict[str, dict[str, str]] = {}
    original_keys: dict[str, str] = {}
    for raw_key, raw_title in (pdf_titles or {}).items():
        key = _normalize_prepare_source_path(raw_root, str(raw_key))
        if isinstance(raw_title, dict):
            title = " ".join(str(raw_title.get("title") or "").split())
            arxiv_id = _normalize_arxiv_id(str(raw_title.get("arxiv_id") or ""))
        else:
            title = " ".join(str(raw_title or "").split())
            arxiv_id = ""
        if not key:
            if warning_sink is not None:
                warning_sink.append(f"ignored invalid PDF title mapping: {raw_key}")
            continue
        if not title and not arxiv_id:
            continue
        normalized_payloads[key] = {"title": title, "arxiv_id": arxiv_id}
        original_keys[key] = str(raw_key)
    return normalized_payloads, original_keys


def _load_pdf_titles_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expected a JSON object mapping source paths to titles or {title, arxiv_id} records")
    return payload


def _read_text(path: Path, limit: int = 20000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _normalize_text(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff\s.+/_-]", " ", text.lower())
    return " ".join(text.split())


def _tokenize(text: str) -> list[str]:
    tokens = []
    for token in TOKEN_PATTERN.findall(_normalize_text(text)):
        token = token.strip("._/+ -")
        if not token:
            continue
        if re.fullmatch(r"[a-z0-9]+", token) and len(token) < 3:
            continue
        if token in STOP_WORDS:
            continue
        tokens.append(token)
    return tokens


def _top_terms(text: str, limit: int = 12) -> list[str]:
    counts = Counter(_tokenize(text))
    return [term for term, _ in counts.most_common(limit)]


def _extract_arxiv_id(text: str) -> str:
    for pattern in (ARXIV_NEW_ID_PATTERN, ARXIV_OLD_ID_PATTERN):
        match = pattern.search(text)
        if match:
            return _normalize_arxiv_id(match.group(1))
    return ""


def _recover_arxiv_id_by_title(title: str) -> str:
    """Try to recover an arXiv ID by searching Semantic Scholar with the paper title.

    Returns the bare arXiv ID (e.g. '2106.09685') or an empty string on failure.
    """
    if not title or len(title) < 8:
        return ""
    try:
        results = _s2_search(title, limit=5)
    except Exception:
        return ""
    normalized_title = _normalize_text(title)
    title_tokens = set(_tokenize(normalized_title))
    for result in results:
        result_title = _normalize_text(str(result.get("title") or ""))
        if not result_title:
            continue
        arxiv_id = (result.get("externalIds") or {}).get("ArXiv", "")
        if not arxiv_id:
            continue
        # Exact normalized match
        if result_title == normalized_title:
            return _normalize_arxiv_id(str(arxiv_id))
        # High token-overlap match (at least 80% of tokens in common)
        result_tokens = set(_tokenize(result_title))
        if result_tokens and title_tokens:
            overlap = len(result_tokens & title_tokens)
            min_len = min(len(result_tokens), len(title_tokens))
            if min_len > 0 and overlap / min_len >= 0.8:
                return _normalize_arxiv_id(str(arxiv_id))
    return ""


def _download_arxiv_source(arxiv_id: str, dest_dir: Path) -> dict[str, Any]:
    """Download arXiv TeX source tarball and extract to dest_dir.

    Returns a dict with keys:
        success (bool), format (str), error (str | None).
    """
    _require_network()
    headers = {"User-Agent": "OmegaWiki-init-discovery/1.0"}
    try:
        src_resp = requests.get(f"https://arxiv.org/e-print/{arxiv_id}", timeout=30, headers=headers)
        if src_resp.ok and src_resp.content:
            with NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
                tmp.write(src_resp.content)
                tmp_path = Path(tmp.name)
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                _safe_extract_tar(tmp_path, dest_dir)
                if not any(path.is_file() for path in dest_dir.rglob("*")):
                    raise ValueError("source archive extracted no files")
                return {"success": True, "format": "directory", "error": None}
            except (tarfile.TarError, OSError, ValueError) as exc:
                shutil.rmtree(dest_dir, ignore_errors=True)
                return {"success": False, "format": "", "error": str(exc)}
            finally:
                tmp_path.unlink(missing_ok=True)
    except requests.RequestException as exc:
        return {"success": False, "format": "", "error": str(exc)}
    return {"success": False, "format": "", "error": "empty response"}


def _extract_arxiv_id_from_pdf_metadata(path: Path) -> str:
    """Try to extract an arXiv ID from the PDF document info dict (metadata)."""
    if not HAS_PYMUPDF:
        return ""
    try:
        doc = fitz.open(path)
        meta = doc.metadata or {}
        doc.close()
        for key in ("subject", "keywords", "title"):
            text = str(meta.get(key) or "")
            arxiv_id = _extract_arxiv_id(text)
            if arxiv_id:
                return arxiv_id
    except Exception:
        pass
    return ""


def _extract_arxiv_source_metadata(source_dir: Path) -> dict[str, str]:
    """Extract title/abstract metadata from a fetched arXiv source dir."""
    tex_files = sorted(source_dir.rglob("*.tex"))
    if not tex_files:
        return {"source_title": "", "source_abstract": ""}

    # Find the .tex file that contains a title command — this is usually the main/master file.
    # Conference templates use \icmltitle{}, \cvprtitle{}, \neuripstitle{}, etc.
    source_text = ""
    for tf in tex_files:
        text = _read_text(tf, limit=15000)
        if text and re.search(r"\\[a-z]*title[a-z]*\{", text, re.IGNORECASE):
            source_text = text
            break
    if not source_text:
        return {"source_title": "", "source_abstract": ""}

    # Extract title from source (handle \title{}, \icmltitle{}, \icmltitlerunning{}, etc.)
    source_title = ""
    title_match = re.search(r"\\[a-z]*title[a-z]*\{", source_text, re.IGNORECASE)
    if title_match:
        start = title_match.end()
        depth = 1
        chars = []
        idx = start
        while idx < len(source_text) and depth > 0:
            ch = source_text[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            if depth > 0:
                chars.append(ch)
            idx += 1
        raw_title = "".join(chars)
        source_title = re.sub(r"\s+", " ", raw_title).strip()

    # Extract abstract from source
    source_abstract = ""
    m = re.search(r"\\begin\{abstract\}(.+?)\\end\{abstract\}", source_text, re.DOTALL | re.IGNORECASE)
    if m:
        source_abstract = re.sub(r"\s+", " ", m.group(1)).strip()

    return {
        "source_title": source_title,
        "source_abstract": source_abstract,
    }


def _guess_title_from_tex(text: str, fallback: str) -> str:
    match = re.search(r"\\title\{(.+?)\}", text, re.DOTALL)
    if match:
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        if title:
            return title
    return fallback


# Common PDF header/footer lines that should not be mistaken for paper titles.
_NON_TITLE_PATTERNS = (
    "published as a",
    "proceedings of",
    "conference",
    "arxiv preprint",
    "arxiv:",
    "copyright",
    "all rights reserved",
    "https://",
    "http://",
    "doi:",
    "ieee",
    "acm",
    "springer",
    "elsevier",
)


def _is_likely_title(line: str) -> bool:
    lower = line.lower()
    if lower in {"abstract", "introduction", "contents", "references"}:
        return False
    for pat in _NON_TITLE_PATTERNS:
        if pat in lower:
            return False
    # Skip lines that look like venue + year (e.g. "ICLR 2023")
    if re.search(r"\b20\d{2}\b", line) and len(line) < 50:
        return False
    return True


def _guess_title_from_text(text: str, fallback: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip().strip("#").strip()
        if len(line) < 8:
            continue
        if not _is_likely_title(line):
            continue
        return re.sub(r"\s+", " ", line)[:200]
    return fallback


def _guess_local_title(path: Path) -> str:
    fallback = path.stem.replace("_", " ").replace("-", " ").strip() or "Untitled"
    if path.suffix.lower() in {".md", ".txt", ".tex"}:
        text = _read_text(path, limit=4000)
        if path.suffix.lower() == ".tex":
            return _guess_title_from_tex(text, fallback)
        return _guess_title_from_text(text, fallback)
    return fallback


def _extract_abstract_excerpt(text: str, limit: int = 1200) -> str:
    if not text.strip():
        return ""
    match = re.search(
        r"(?is)(?:^|\n)\s*(?:abstract|摘要)\s*[:：]?\s*(.+?)(?:\n\s*(?:1\.?|i\.?|introduction|引言|keywords?|关键词)\b|\Z)",
        text,
    )
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()[:limit]
    first_paragraphs = re.split(r"\n\s*\n", text.strip())
    for paragraph in first_paragraphs:
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        if len(paragraph) >= 40:
            return paragraph[:limit]
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _scan_paper_dir(path: Path) -> Path | None:
    tex_files = sorted(path.rglob("*.tex"))
    if tex_files:
        return tex_files[0]
    pdf_files = sorted(path.rglob("*.pdf"))
    if pdf_files:
        return pdf_files[0]
    return None


def _is_archive(path: Path) -> bool:
    lower = path.name.lower()
    return lower.endswith(".tar.gz") or lower.endswith(".tgz") or path.suffix.lower() == ".zip"


def _safe_name(title: str) -> str:
    return slugify(title) or "paper"


def _path_slug(path: Path) -> str:
    return slugify("-".join(path.parts)) or "item"


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?。！？])\s+", text.replace("\n", " "))
    return [s.strip() for s in sentences if len(s.strip()) >= 20]


def _latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    result = []
    for ch in text:
        result.append(replacements.get(ch, ch))
    return "".join(result)


def _detect_language(text: str) -> str:
    chinese_count = len(CHINESE_CHAR_PATTERN.findall(text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    if chinese_count >= 8 and chinese_count >= latin_count / 2:
        return "zh"
    if latin_count >= 20:
        return "en"
    return "unknown"


def _record_issue(bucket: list[dict[str, str]], source: str, message: str) -> None:
    bucket.append({"source": source, "message": message})


def _safe_extract_tar(archive: Path, dest_dir: Path) -> None:
    dest_root = dest_dir.resolve()
    total_size = 0
    with tarfile.open(archive, mode="r:*") as tar:
        members = tar.getmembers()
        for member in members:
            if member.issym() or member.islnk():
                raise ValueError("archive contains link entries")
            target = (dest_root / member.name).resolve()
            if os.path.commonpath([str(dest_root), str(target)]) != str(dest_root):
                raise ValueError(f"archive entry escapes destination: {member.name}")
            total_size += max(member.size, 0)
            if total_size > MAX_SOURCE_ARCHIVE_BYTES:
                raise ValueError("archive exceeds extraction size limit")
        tar.extractall(dest_dir, members=members)


def _safe_extract_zip(archive: Path, dest_dir: Path) -> None:
    dest_root = dest_dir.resolve()
    total_size = 0
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            target = (dest_root / member.filename).resolve()
            if os.path.commonpath([str(dest_root), str(target)]) != str(dest_root):
                raise ValueError(f"archive entry escapes destination: {member.filename}")
            total_size += max(member.file_size, 0)
            if total_size > MAX_SOURCE_ARCHIVE_BYTES:
                raise ValueError("archive exceeds extraction size limit")
        zf.extractall(dest_dir)


def _extract_archive_to_tmp(source_path: Path, dest_dir: Path) -> list[str]:
    warnings: list[str] = []
    shutil.rmtree(dest_dir, ignore_errors=True)
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        if source_path.suffix.lower() == ".zip":
            _safe_extract_zip(source_path, dest_dir)
        else:
            _safe_extract_tar(source_path, dest_dir)
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        shutil.rmtree(dest_dir, ignore_errors=True)
        warnings.append(f"archive extraction failed: {exc}")
    return warnings


def _extract_pdf_text(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if not HAS_PYMUPDF:
        warnings.append("PyMuPDF unavailable; cannot decode PDF during prepare")
        return "", warnings
    try:
        doc = fitz.open(path)
        try:
            text_parts = [page.get_text("text") for page in doc]
        finally:
            doc.close()
        text = "\n".join(part.strip() for part in text_parts if part.strip()).strip()
        if not text:
            warnings.append("PDF decode produced empty text")
        return text[:120000], warnings
    except Exception as exc:
        warnings.append(f"PDF decode failed: {exc}")
        return "", warnings


def _build_synthetic_tex(title: str, text: str) -> str:
    abstract = _extract_abstract_excerpt(text, limit=1500)
    body = re.sub(r"\s+\n", "\n", text).strip()
    if not body:
        body = title
    title_line = _latex_escape(title or "Untitled")
    abstract_block = _latex_escape(abstract or body[:800])
    body_block = _latex_escape(body[:60000])
    return (
        "\\title{" + title_line + "}\n"
        "\\begin{document}\n"
        "\\maketitle\n\n"
        "\\begin{abstract}\n"
        + abstract_block
        + "\n\\end{abstract}\n\n"
        "\\section{Recovered Text}\n"
        + body_block
        + "\n\\end{document}\n"
    )


def _ingest_format_from_path(path_str: str) -> str:
    path = Path(path_str)
    if path.suffix.lower() == ".tex":
        return "tex"
    if path.suffix.lower() == ".pdf":
        return "pdf"
    return "directory"


def _prepare_text_entry(path: Path, raw_root: Path, kind: str) -> dict[str, Any] | None:
    text = _read_text(path, limit=120000)
    if not text.strip():
        return None
    source_rel = _relative_to_project(path, raw_root)
    title = _guess_title_from_text(text, path.stem)
    return {
        "entry_id": f"{kind}:{_path_slug(path.relative_to(raw_root))}",
        "source_kind": kind,
        "source_path": source_rel,
        "prepared_path": None,
        "canonical_ingest_path": source_rel,
        "canonical_read_path": source_rel,
        "original_format": path.suffix.lower().lstrip(".") or "text",
        "title": title,
        "abstract_excerpt": _extract_abstract_excerpt(text, limit=400),
        "warnings": [],
        "usable": True,
    }


def _prepare_paper_entry(path: Path, raw_root: Path, title: str = "", arxiv_id: str = "") -> dict[str, Any]:
    return _prepare_paper_source(path, raw_root, title=title, arxiv_id=arxiv_id)


def prepare_inputs(
    raw_root: Path,
    pdf_titles: dict[str, Any] | None = None,
    warning_sink: list[str] | None = None,
) -> dict[str, Any]:
    raw_root = raw_root.resolve()
    tmp_root = raw_root / "tmp"
    (tmp_root / "papers").mkdir(parents=True, exist_ok=True)
    paper_entries: list[dict[str, Any]] = []
    other_entries: list[dict[str, Any]] = []
    normalized_handoffs, original_title_keys = _normalize_pdf_titles_map(raw_root, pdf_titles, warning_sink=warning_sink)
    seen_title_keys: set[str] = set()

    papers_root = raw_root / "papers"
    if papers_root.exists():
        for entry in sorted(papers_root.iterdir()):
            if entry.name == ".gitkeep":
                continue
            source_rel = _relative_to_project(entry, raw_root)
            recovered = normalized_handoffs.get(source_rel, {})
            recovered_title = recovered.get("title", "")
            recovered_arxiv_id = recovered.get("arxiv_id", "")
            if recovered_title or recovered_arxiv_id:
                seen_title_keys.add(source_rel)
            paper_entries.append(
                _prepare_paper_entry(entry, raw_root, title=recovered_title, arxiv_id=recovered_arxiv_id)
            )

    deduped_papers: dict[str, dict[str, Any]] = {}
    for entry in paper_entries:
        arxiv_id, _title_key = _paper_entry_match_key(entry)
        key = f"arxiv:{arxiv_id}" if arxiv_id else entry["candidate_id"]

        existing = deduped_papers.get(key)
        if existing is None:
            deduped_papers[key] = entry
            continue

        if _paper_entry_preference(entry) > _paper_entry_preference(existing):
            kept, dropped = entry, existing
            deduped_papers[key] = entry
        else:
            kept, dropped = existing, entry
        kept["warnings"] = list(dict.fromkeys(
            list(kept.get("warnings", []))
            + list(dropped.get("warnings", []))
            + [f"duplicate local source skipped in favor of preferred source: {kept['source_path']}"]
        ))

    if warning_sink is not None:
        for source_rel, original_key in sorted(original_title_keys.items()):
            if source_rel not in seen_title_keys:
                warning_sink.append(f"ignored unknown PDF title mapping: {original_key}")

    for kind in ("notes", "web"):
        base = raw_root / kind
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_dir() or path.name == ".gitkeep" or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            record = _prepare_text_entry(path, raw_root, kind)
            if record:
                other_entries.append(record)

    return {
        "raw_root": _relative_to_project(raw_root, raw_root),
        "prepared_root": _relative_to_project(tmp_root, raw_root),
        "entries": list(deduped_papers.values()) + other_entries,
    }


def _load_prepare_manifest(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _prepared_paper_entries(prepared_manifest: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not prepared_manifest:
        return []
    return [
        entry
        for entry in prepared_manifest.get("entries", [])
        if entry.get("source_kind") == "paper" and entry.get("usable", True)
    ]


def _paper_match_key(candidate: dict[str, Any]) -> tuple[str, str]:
    return (str(candidate.get("arxiv_id") or ""), _normalize_text(str(candidate.get("title") or "")))


def _same_paper(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_arxiv, left_title = _paper_match_key(left)
    right_arxiv, right_title = _paper_match_key(right)
    if left_arxiv and right_arxiv:
        return left_arxiv == right_arxiv
    return bool(left_title and left_title == right_title)


def scan_local_papers(raw_root: Path, prepared_manifest: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if prepared_manifest:
        results: list[dict[str, Any]] = []
        for entry in _prepared_paper_entries(prepared_manifest):
            results.append({
                "candidate_id": entry["candidate_id"],
                "title": entry["title"],
                "arxiv_id": entry.get("arxiv_id", ""),
                "path": entry["canonical_ingest_path"],
                "source_path": entry["source_path"],
                "prepared_path": entry.get("prepared_path"),
                "resolved_source_path": entry.get("resolved_source_path"),
                "source_channels": ["local"],
                "user_owned": True,
                "source_type": entry.get("ingest_format", "file"),
                "year": None,
                "citation_count": 0,
                "abstract": entry.get("abstract_excerpt", ""),
                "cluster": "",
            })
        return results

    papers_root = raw_root / "papers"
    if not papers_root.exists():
        return []
    results: list[dict[str, Any]] = []
    for entry in sorted(papers_root.iterdir()):
        if entry.name == ".gitkeep":
            continue
        candidate_path = entry
        source_kind = "file"
        if entry.is_dir():
            chosen = _scan_paper_dir(entry)
            if chosen is None:
                continue
            candidate_path = chosen
            source_kind = "directory"
        elif entry.suffix.lower() not in PAPER_SUFFIXES and entry.name.lower() not in {"tar.gz", "tgz"}:
            if not entry.name.endswith(".tar.gz"):
                continue
        title = _guess_local_title(candidate_path)
        arxiv_id = _extract_arxiv_id(f"{entry.name} {title} {_read_text(candidate_path, 2000)}")
        results.append({
            "candidate_id": _local_candidate_id(entry, raw_root),
            "title": title,
            "arxiv_id": arxiv_id,
            "path": str(candidate_path.relative_to(raw_root.parent)),
            "source_path": str(entry.relative_to(raw_root.parent)),
            "prepared_path": None,
            "resolved_source_path": str(candidate_path.relative_to(raw_root.parent)),
            "source_channels": ["local"],
            "user_owned": True,
            "source_type": source_kind,
            "year": None,
            "citation_count": 0,
            "abstract": "",
            "cluster": "",
        })
    return results


def _iter_notes_web_sources(raw_root: Path, prepared_manifest: dict[str, Any] | None = None) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    if prepared_manifest:
        for entry in prepared_manifest.get("entries", []):
            if entry.get("source_kind") not in {"notes", "web"} or not entry.get("usable", True):
                continue
            source_path = str(entry.get("source_path") or "")
            if not source_path:
                continue
            sources.append({
                "path": source_path,
                "canonical_path": source_path,
                "kind": str(entry["source_kind"]),
            })
        return sources

    for sub in ("notes", "web"):
        base = raw_root / sub
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_dir() or path.name == ".gitkeep" or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            rel_path = str(path.relative_to(raw_root.parent))
            sources.append({
                "path": rel_path,
                "canonical_path": rel_path,
                "kind": sub,
            })
    return sources


def scan_notes_web(raw_root: Path, prepared_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    combined_text = ""
    for item in _iter_notes_web_sources(raw_root, prepared_manifest):
        text = _read_text(_resolve_project_path(raw_root, item["canonical_path"]), limit=120000)
        if not text.strip():
            continue
        files.append({
            "path": item["path"],
            "canonical_path": item["canonical_path"],
            "kind": item["kind"],
            "keywords": _top_terms(text, limit=8),
        })
        combined_text += "\n" + text

    sentences = _split_sentences(combined_text)
    exclusions = [s for s in sentences if any(p in s.lower() for p in EXCLUSION_PATTERNS)]
    assertions = [s for s in sentences if any(p in s.lower() for p in ASSERTIVE_PATTERNS)][:8]
    ideas = [s for s in sentences if any(p in s.lower() for p in IDEA_PATTERNS)][:8]
    keywords = _top_terms(combined_text, limit=16)
    return {
        "files": files,
        "keywords": keywords,
        "exclusions": exclusions[:8],
        "assertions": assertions,
        "ideas": ideas,
    }


def _notes_web_contains_chinese(raw_root: Path, prepared_manifest: dict[str, Any] | None = None) -> bool:
    for item in _iter_notes_web_sources(raw_root, prepared_manifest):
        text = _read_text(_resolve_project_path(raw_root, item["canonical_path"]), limit=120000)
        if text.strip() and _detect_language(text) == "zh":
            return True
    return False


def _title_key(title: str) -> str:
    return _normalize_text(title)


def _extract_external_arxiv_id(data: dict[str, Any]) -> str:
    if data.get("arxiv_id"):
        return str(data["arxiv_id"])
    external_ids = data.get("externalIds") or {}
    if isinstance(external_ids, dict):
        arxiv = external_ids.get("ArXiv") or external_ids.get("arXiv")
        if arxiv:
            return str(arxiv)
    return _extract_arxiv_id(json.dumps(data, ensure_ascii=False))


def _normalise_s2_result(data: dict[str, Any], channel: str, anchor: str = "") -> dict[str, Any]:
    title = str(data.get("title", "")).strip()
    if not title:
        return {}
    arxiv_id = _extract_external_arxiv_id(data)
    return {
        "candidate_id": f"arxiv:{arxiv_id}" if arxiv_id else f"title:{slugify(title)}",
        "title": title,
        "abstract": str(data.get("abstract", "") or ""),
        "authors": [a.get("name", "") for a in data.get("authors", []) if isinstance(a, dict)],
        "year": data.get("year"),
        "citation_count": int(data.get("citationCount") or 0),
        "venue": str(data.get("venue", "") or ""),
        "arxiv_id": arxiv_id,
        "source_channels": [channel],
        "anchor_sources": [anchor] if anchor else [],
        "deepxiv_relevance_score": None,
        "user_owned": False,
        "cluster": "",
    }


def _normalise_deepxiv_result(data: dict[str, Any], channel: str) -> dict[str, Any]:
    title = str(data.get("title", "")).strip()
    if not title:
        return {}
    arxiv_id = str(data.get("arxiv_id", "") or "")
    return {
        "candidate_id": f"arxiv:{arxiv_id}" if arxiv_id else f"title:{slugify(title)}",
        "title": title,
        "abstract": str(data.get("abstract", "") or ""),
        "authors": list(data.get("authors", []) or []),
        "year": data.get("year"),
        "citation_count": int(data.get("citation_count") or 0),
        "venue": "",
        "arxiv_id": arxiv_id,
        "source_channels": [channel],
        "anchor_sources": [],
        "deepxiv_relevance_score": float(data.get("relevance_score") or 0.0),
        "user_owned": False,
        "cluster": "",
    }


def _merge_candidate(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    for channel in incoming.get("source_channels", []):
        if channel not in existing["source_channels"]:
            existing["source_channels"].append(channel)
    for anchor in incoming.get("anchor_sources", []):
        if anchor not in existing["anchor_sources"]:
            existing["anchor_sources"].append(anchor)
    if not existing.get("abstract") and incoming.get("abstract"):
        existing["abstract"] = incoming["abstract"]
    if not existing.get("year") and incoming.get("year"):
        existing["year"] = incoming["year"]
    existing["citation_count"] = max(existing.get("citation_count", 0), incoming.get("citation_count", 0))
    if incoming.get("deepxiv_relevance_score") is not None:
        existing["deepxiv_relevance_score"] = max(
            float(existing.get("deepxiv_relevance_score") or 0.0),
            float(incoming["deepxiv_relevance_score"] or 0.0),
        )


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    title_index: dict[str, str] = {}
    for candidate in candidates:
        if not candidate:
            continue
        key = candidate["candidate_id"]
        title_key = _title_key(candidate["title"])
        if candidate.get("arxiv_id"):
            key = f"arxiv:{candidate['arxiv_id']}"
        elif title_key in title_index:
            key = title_index[title_key]
        if key in merged:
            _merge_candidate(merged[key], candidate)
        else:
            merged[key] = candidate
            title_index[title_key] = key
    return list(merged.values())


def _overlap_score(query_terms: list[str], text: str) -> tuple[float, list[str]]:
    if not query_terms:
        return 0.0, []
    text_terms = set(_tokenize(text))
    if not text_terms:
        return 0.0, []
    matched = [term for term in query_terms if term in text_terms]
    score = len(set(matched)) / max(len(set(query_terms)), 1)
    return min(score, 1.0), sorted(set(matched))


def _freshness_score(year: int | None) -> float:
    if not year:
        return 0.35
    age = max(CURRENT_YEAR - int(year), 0)
    if age <= 1:
        return 1.0
    if age <= 3:
        return 0.85
    if age <= 5:
        return 0.65
    if age <= 8:
        return 0.4
    return 0.15


def _is_older_paper(candidate: dict[str, Any]) -> bool:
    year = candidate.get("year")
    if not year:
        return False
    try:
        return CURRENT_YEAR - int(year) >= OLDER_PAPER_YEARS
    except (TypeError, ValueError):
        return False


def _is_older_external_non_survey(candidate: dict[str, Any]) -> bool:
    return (
        not candidate.get("user_owned")
        and not candidate.get("is_survey")
        and _is_older_paper(candidate)
    )


def _survey_score(title: str, abstract: str) -> float:
    haystack = f"{title} {abstract}".lower()
    for term in SURVEY_TERMS:
        if term in haystack:
            return 1.0 if term in title.lower() else 0.7
    return 0.0


def _citation_score(citation_count: int, max_citations: int) -> float:
    if citation_count <= 0 or max_citations <= 0:
        return 0.0
    return min(math.log1p(citation_count) / math.log1p(max_citations), 1.0)


def _combine_relevance_signals(lexical_rel: float, deepxiv_rel: float) -> float:
    if deepxiv_rel > 0:
        return min(1.0, 0.7 * deepxiv_rel + 0.3 * lexical_rel)
    return lexical_rel


def _cluster_label(candidate: dict[str, Any], query_terms: list[str]) -> str:
    text_terms = _tokenize(f"{candidate['title']} {candidate.get('abstract', '')}")
    for term in query_terms:
        if term in text_terms:
            return term
    return text_terms[0] if text_terms else "misc"


def _sort_search_candidates(candidates: list[dict[str, Any]], query_terms: list[str]) -> list[dict[str, Any]]:
    max_citations = max((c.get("citation_count", 0) for c in candidates), default=1)
    for candidate in candidates:
        rel, matches = _overlap_score(query_terms, f"{candidate['title']} {candidate.get('abstract', '')}")
        deepxiv_rel = float(candidate.get("deepxiv_relevance_score") or 0.0)
        relevance_feature = _combine_relevance_signals(rel, deepxiv_rel)
        candidate["_bootstrap_score"] = (
            0.6 * relevance_feature
            + 0.2 * _freshness_score(candidate.get("year"))
            + 0.1 * _survey_score(candidate["title"], candidate.get("abstract", ""))
            + 0.1 * _citation_score(candidate.get("citation_count", 0), max_citations)
        )
        candidate["_bootstrap_matches"] = matches
    return sorted(candidates, key=lambda c: c.get("_bootstrap_score", 0.0), reverse=True)


def _score_candidates(
    candidates: list[dict[str, Any]],
    mode: str,
    topic_terms: list[str],
    note_terms: list[str],
    local_terms: list[str],
    exclusion_terms: list[str],
) -> list[dict[str, Any]]:
    max_citations = max((c.get("citation_count", 0) for c in candidates), default=1)
    query_terms = list(dict.fromkeys(topic_terms + note_terms + local_terms))
    local_priority_terms = list(dict.fromkeys(local_terms + note_terms))
    for candidate in candidates:
        title_abstract = f"{candidate['title']} {candidate.get('abstract', '')}"
        lexical_rel, lexical_matches = _overlap_score(query_terms, title_abstract)
        deepxiv_rel = float(candidate.get("deepxiv_relevance_score") or 0.0)
        relevance_feature = _combine_relevance_signals(lexical_rel, deepxiv_rel)
        freshness_feature = _freshness_score(candidate.get("year"))
        if mode == "seeded":
            local_anchor, local_matches = _overlap_score(local_priority_terms or topic_terms, title_abstract)
            note_anchor, note_matches = _overlap_score(note_terms, title_abstract)
            connection_feature = min(len(candidate.get("anchor_sources", [])) / 3, 1.0)
            anchor_feature = min(
                1.0,
                0.60 * connection_feature + 0.25 * local_anchor + 0.15 * note_anchor,
            )
            matched_terms = sorted(set(lexical_matches + local_matches + note_matches))
        else:
            anchor_feature = min(1.0, max(len(candidate.get("anchor_sources", [])) / 2, 0.0))
            matched_terms = lexical_matches
        survey_feature = _survey_score(candidate["title"], candidate.get("abstract", ""))
        citation_feature = _citation_score(candidate.get("citation_count", 0), max_citations)
        exclusion_feature, excluded_matches = _overlap_score(exclusion_terms, title_abstract)
        total = (
            RANKING_WEIGHTS["relevance"] * relevance_feature
            + RANKING_WEIGHTS["freshness"] * freshness_feature
            + RANKING_WEIGHTS["anchor_bonus"] * anchor_feature
            + RANKING_WEIGHTS["survey_bonus"] * survey_feature
            + RANKING_WEIGHTS["citation_centrality"] * citation_feature
            - EXCLUSION_PENALTY * exclusion_feature
        )
        candidate["score_components"] = {
            "relevance": round(RANKING_WEIGHTS["relevance"] * relevance_feature, 3),
            "deepxiv_relevance": round(deepxiv_rel, 3),
            "lexical_relevance": round(lexical_rel, 3),
            "freshness": round(RANKING_WEIGHTS["freshness"] * freshness_feature, 3),
            "anchor_bonus": round(RANKING_WEIGHTS["anchor_bonus"] * anchor_feature, 3),
            "survey_bonus": round(RANKING_WEIGHTS["survey_bonus"] * survey_feature, 3),
            "citation_centrality": round(RANKING_WEIGHTS["citation_centrality"] * citation_feature, 3),
            "exclusion_penalty": round(-EXCLUSION_PENALTY * exclusion_feature, 3),
        }
        candidate["total_score"] = round(total, 3)
        candidate["matched_terms"] = matched_terms
        candidate["excluded_terms_matched"] = excluded_matches
        candidate["cluster"] = _cluster_label(candidate, query_terms)
        candidate["is_survey"] = survey_feature > 0
    return sorted(candidates, key=lambda c: c["total_score"], reverse=True)


def _selection_reason(candidate: dict[str, Any], penalized_score: float) -> str:
    reasons = []
    if candidate.get("user_owned"):
        reasons.append("user-owned local source")
    if candidate.get("is_survey"):
        reasons.append("survey/benchmark coverage")
    if float(candidate.get("deepxiv_relevance_score") or 0.0) > 0:
        reasons.append(f"DeepXiv relevance={round(float(candidate['deepxiv_relevance_score']), 2)}")
    if candidate.get("matched_terms"):
        reasons.append(f"matches: {', '.join(candidate['matched_terms'][:4])}")
    if candidate.get("anchor_sources"):
        reasons.append(f"connected to {len(candidate['anchor_sources'])} anchor source(s)")
    if candidate.get("excluded_terms_matched"):
        reasons.append(f"matches excluded terms: {', '.join(candidate['excluded_terms_matched'][:3])}")
    if candidate.get("year") and CURRENT_YEAR - int(candidate["year"]) <= 3:
        reasons.append("fresh recent paper")
    elif candidate.get("citation_count", 0) > 0:
        reasons.append("strong citation signal")
    reasons.append(f"penalized_score={round(penalized_score, 2)}")
    return "; ".join(reasons)


def _select_shortlist(
    candidates: list[dict[str, Any]],
    mode: str,
    local_count: int,
    allow_introduction: bool,
) -> list[dict[str, Any]]:
    if not allow_introduction:
        return [c for c in candidates if c.get("user_owned")]

    if local_count >= FINAL_TARGET_RANGE[1]:
        return [c for c in candidates if c.get("user_owned")]

    protected = [c for c in candidates if c.get("user_owned")]
    protected_ids = {c["candidate_id"] for c in protected}
    shortlist = list(protected)
    target = SHORTLIST_TARGET if mode == "bootstrap" else max(10, min(SHORTLIST_TARGET, local_count + 4))
    target = max(target, len(shortlist))
    introduced_capacity = max(FINAL_TARGET_RANGE[1] - local_count, 0)
    allow_old_anchor_promotion = mode == "bootstrap" or introduced_capacity >= ROOMY_INTRODUCED_CAPACITY
    scarce_seeded_mode = mode != "bootstrap" and introduced_capacity < ROOMY_INTRODUCED_CAPACITY

    survey_pool = [c for c in candidates if c.get("is_survey") and c["candidate_id"] not in protected_ids]
    if survey_pool and len(shortlist) < target:
        shortlist.append(survey_pool[0])
        protected_ids.add(survey_pool[0]["candidate_id"])

    anchor_added = False
    older_candidates = [
        c
        for c in candidates
        if c["candidate_id"] not in protected_ids and _is_older_external_non_survey(c)
    ]
    if allow_old_anchor_promotion and older_candidates and len(shortlist) < target:
        older = max(older_candidates, key=lambda c: (c["citation_count"], c["total_score"]))
        shortlist.append(older)
        protected_ids.add(older["candidate_id"])
        anchor_added = True

    cluster_counts: defaultdict[str, int] = defaultdict(int)
    for item in shortlist:
        cluster_counts[item["cluster"]] += 1
    older_external_selected = sum(1 for item in shortlist if _is_older_external_non_survey(item))

    for candidate in candidates:
        if candidate["candidate_id"] in protected_ids:
            continue
        if len(shortlist) >= target:
            break
        old_penalty = 0.0
        if _is_older_external_non_survey(candidate) and (anchor_added or scarce_seeded_mode):
            old_penalty = 12.0
        diversity_penalty = 12.0 * cluster_counts[candidate["cluster"]]
        penalized_score = candidate["total_score"] - diversity_penalty - old_penalty
        candidate["selection_reason"] = _selection_reason(candidate, penalized_score)
        candidate["_penalized_score"] = penalized_score

    remaining = sorted(
        [c for c in candidates if c["candidate_id"] not in protected_ids],
        key=lambda c: c.get("_penalized_score", c["total_score"]),
        reverse=True,
    )
    for candidate in remaining:
        if len(shortlist) >= target:
            break
        if _is_older_external_non_survey(candidate) and older_external_selected >= 1:
            continue
        shortlist.append(candidate)
        protected_ids.add(candidate["candidate_id"])
        cluster_counts[candidate["cluster"]] += 1
        if _is_older_external_non_survey(candidate):
            older_external_selected += 1

    return shortlist


def _notes_priority_query(topic: str, notes_web: dict[str, Any], local_papers: list[dict[str, Any]]) -> dict[str, list[str]]:
    topic_terms = _top_terms(topic, limit=8)
    idea_terms = _top_terms(" ".join(notes_web.get("ideas", [])), limit=6)
    assertion_terms = _top_terms(" ".join(notes_web.get("assertions", [])), limit=6)
    exclusion_terms = _top_terms(" ".join(notes_web.get("exclusions", [])), limit=6)
    note_terms = list(
        dict.fromkeys(notes_web.get("keywords", [])[:8] + idea_terms[:4] + assertion_terms[:4])
    )[:12]
    local_terms = []
    for paper in local_papers:
        local_terms.extend(_top_terms(paper["title"], limit=4))
    local_terms = list(dict.fromkeys(local_terms))[:8]
    return {
        "topic_terms": topic_terms,
        "note_terms": note_terms,
        "local_terms": local_terms,
        "exclusion_terms": exclusion_terms,
    }


def _build_discovery_query(topic: str, term_pack: dict[str, Any]) -> str:
    normalized_topic = " ".join(str(topic or "").split())
    extra_terms = list(term_pack.get("note_terms", [])[:4])
    if not normalized_topic:
        extra_terms = list(dict.fromkeys(extra_terms + list(term_pack.get("local_terms", [])[:4])))[:8]
    parts = [normalized_topic] if normalized_topic else []
    parts.extend(extra_terms)
    return " ".join(part for part in parts if part).strip()


def _select_seed_anchors(
    local_papers: list[dict[str, Any]],
    topic_terms: list[str],
    note_terms: list[str],
    limit: int = 3,
) -> list[dict[str, Any]]:
    priority_terms = list(dict.fromkeys(topic_terms + note_terms))
    if not priority_terms:
        return [paper for paper in local_papers if paper.get("arxiv_id")][:limit]
    ranked: list[tuple[float, int, str, dict[str, Any]]] = []
    for paper in local_papers:
        if not paper.get("arxiv_id"):
            continue
        score, matches = _overlap_score(priority_terms, paper["title"])
        ranked.append((score, len(matches), paper["title"], paper))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [paper for *_rest, paper in ranked[:limit]]


def _gather_external_candidates(
    mode: str,
    topic: str,
    local_papers: list[dict[str, Any]],
    term_pack: dict[str, list[str]],
    allow_introduction: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    if not allow_introduction:
        return [], [], []

    query = _build_discovery_query(topic, term_pack)
    candidates: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    if mode == "bootstrap":
        if not query:
            _record_issue(
                errors,
                "planner",
                "topic is required for bootstrap discovery unless notes/web or local inputs provide fallback keywords",
            )
            return [], warnings, errors
        try:
            candidates.extend(_normalise_s2_result(r, "search_s2") for r in _s2_search(query, 20))
        except Exception as exc:
            _record_issue(warnings, "search_s2", str(exc))
        try:
            candidates.extend(_normalise_deepxiv_result(r, "search_deepxiv") for r in _deepxiv_search(query, limit=12))
        except Exception as exc:
            _record_issue(warnings, "search_deepxiv", str(exc))
        seed_pool = _dedupe_candidates([c for c in candidates if c])
        sorted_seed = _sort_search_candidates(seed_pool, _top_terms(query, limit=10))
        anchors = [c for c in sorted_seed[:2] if c.get("arxiv_id")]
        for anchor in anchors:
            try:
                candidates.extend(
                    _normalise_s2_result(r, "citation", anchor=anchor["candidate_id"])
                    for r in _s2_citations(anchor["arxiv_id"], limit=40)
                )
            except Exception as exc:
                _record_issue(warnings, f"citation:{anchor['arxiv_id']}", str(exc))
            try:
                candidates.extend(
                    _normalise_s2_result(r, "reference", anchor=anchor["candidate_id"])
                    for r in _s2_references(anchor["arxiv_id"], limit=40)
                )
            except Exception as exc:
                _record_issue(warnings, f"reference:{anchor['arxiv_id']}", str(exc))
        if not candidates:
            _record_issue(errors, "planner", "no external candidates found during bootstrap discovery")
        return [c for c in candidates if c], warnings, errors

    anchor_limit = 3 if (term_pack["topic_terms"] or term_pack["note_terms"]) else min(5, len(local_papers))
    anchors = _select_seed_anchors(
        local_papers,
        term_pack["topic_terms"],
        term_pack["note_terms"],
        limit=max(anchor_limit, 1),
    )
    if not anchors and local_papers:
        _record_issue(
            warnings,
            "seeded_mode",
            "no local papers with arXiv IDs available for citation/reference expansion; falling back to search",
        )
    for anchor in anchors:
        try:
            candidates.extend(
                _normalise_s2_result(r, "citation", anchor=anchor["candidate_id"])
                for r in _s2_citations(anchor["arxiv_id"], limit=50)
            )
        except Exception as exc:
            _record_issue(warnings, f"citation:{anchor['arxiv_id']}", str(exc))
        try:
            candidates.extend(
                _normalise_s2_result(r, "reference", anchor=anchor["candidate_id"])
                for r in _s2_references(anchor["arxiv_id"], limit=50)
            )
        except Exception as exc:
            _record_issue(warnings, f"reference:{anchor['arxiv_id']}", str(exc))

    if len(candidates) < 12:
        if query:
            try:
                candidates.extend(_normalise_s2_result(r, "search_s2") for r in _s2_search(query, 20))
            except Exception as exc:
                _record_issue(warnings, "search_s2", str(exc))
            try:
                candidates.extend(_normalise_deepxiv_result(r, "search_deepxiv") for r in _deepxiv_search(query, limit=12))
            except Exception as exc:
                _record_issue(warnings, "search_deepxiv", str(exc))
        elif local_papers:
            _record_issue(
                warnings,
                "planner_query",
                "topic omitted and no fallback keywords were available for search; seeded discovery will rely on local-paper citation/reference expansion only",
            )
    if not candidates:
        if local_papers:
            _record_issue(
                warnings,
                "seeded_mode",
                "seeded discovery found no external candidates; proceeding with user-owned papers only",
            )
        else:
            _record_issue(errors, "planner", "no external candidates found during seeded discovery")
    return [c for c in candidates if c], warnings, errors


def build_plan(
    topic: str,
    raw_root: Path,
    wiki_root: Path,
    mode: str = "auto",
    allow_introduction: bool = True,
    prepared_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    topic = " ".join(str(topic or "").split())
    local_papers = scan_local_papers(raw_root, prepared_manifest=prepared_manifest)
    notes_web = scan_notes_web(raw_root, prepared_manifest=prepared_manifest)
    warnings: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    actual_mode = mode
    if mode == "auto":
        actual_mode = "seeded" if local_papers else "bootstrap"
    if allow_introduction and not os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip():
        _record_issue(
            warnings,
            "semantic_scholar",
            "SEMANTIC_SCHOLAR_API_KEY is unset; Semantic Scholar discovery will run with the slower public rate limit.",
        )
    if _notes_web_contains_chinese(raw_root, prepared_manifest=prepared_manifest):
        _record_issue(
            warnings,
            "notes_web_chinese",
            (
                "Chinese note or web content detected. Current note/web extraction and ranking may be "
                "less reliable for Chinese-heavy inputs, so treat rankings and provisional pages as "
                "lower-confidence."
            ),
        )

    term_pack = _notes_priority_query(topic, notes_web, local_papers)
    external, ext_warnings, ext_errors = _gather_external_candidates(
        actual_mode, topic, local_papers, term_pack, allow_introduction
    )
    warnings.extend(ext_warnings)
    errors.extend(ext_errors)
    external = [c for c in external if not any(_same_paper(c, local) for local in local_papers)]
    all_candidates = _dedupe_candidates(local_papers + external)
    scored = _score_candidates(
        all_candidates,
        actual_mode,
        term_pack["topic_terms"],
        term_pack["note_terms"],
        term_pack["local_terms"],
        term_pack["exclusion_terms"],
    )
    shortlist = _select_shortlist(scored, actual_mode, len(local_papers), allow_introduction)
    shortlist_ids = {item["candidate_id"] for item in shortlist}
    if not shortlist:
        _record_issue(errors, "planner", "shortlist is empty")

    for idx, candidate in enumerate(shortlist, start=1):
        candidate["shortlist_rank"] = idx
        if "selection_reason" not in candidate:
            candidate["selection_reason"] = _selection_reason(candidate, candidate["total_score"])

    for candidate in scored:
        candidate["selected_for_shortlist"] = candidate["candidate_id"] in shortlist_ids

    return {
        "topic": topic,
        "mode": actual_mode,
        "allow_introduction": allow_introduction,
        "target_final_range": FINAL_TARGET_RANGE,
        "shortlist_target": len(shortlist),
        "local_papers": local_papers,
        "notes_web": notes_web,
        "query_terms": term_pack,
        "shortlist": shortlist,
        "candidates": scored,
        "wiki_root": str(wiki_root),
        "raw_root": str(raw_root),
        "prepared_manifest": prepared_manifest.get("prepared_root") if prepared_manifest else None,
        "warnings": warnings,
        "errors": errors,
    }


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _download_source(candidate: dict[str, Any], raw_root: Path) -> dict[str, Any]:
    dest_root = raw_root / "discovered"
    dest_root.mkdir(parents=True, exist_ok=True)
    slug = _safe_name(candidate["title"])
    dest_dir = dest_root / slug
    dest_pdf = dest_root / f"{slug}.pdf"
    if dest_dir.exists() or dest_pdf.exists():
        existing = dest_dir if dest_dir.exists() else dest_pdf
        return {
            "candidate_id": candidate["candidate_id"],
            "status": "skipped_exists",
            "path": str(existing),
            "canonical_ingest_path": str(existing),
            "ingest_format": _ingest_format_from_path(str(existing)),
        }
    arxiv_id = candidate.get("arxiv_id", "")
    if not arxiv_id:
        return {"candidate_id": candidate["candidate_id"], "status": "skipped_no_arxiv", "path": ""}

    # Try TeX source first
    source_result = _download_arxiv_source(arxiv_id, dest_dir)
    if source_result["success"]:
        return {
            "candidate_id": candidate["candidate_id"],
            "status": "downloaded_source",
            "path": str(dest_dir),
            "canonical_ingest_path": str(dest_dir),
            "ingest_format": "directory",
        }

    # Fall back to PDF
    _require_network()
    headers = {"User-Agent": "OmegaWiki-init-discovery/1.0"}
    try:
        pdf_resp = requests.get(f"https://arxiv.org/pdf/{arxiv_id}", timeout=30, headers=headers)
        pdf_resp.raise_for_status()
        content_type = pdf_resp.headers.get("Content-Type", "").lower()
        if not pdf_resp.content or (
            "application/pdf" not in content_type and not pdf_resp.content.startswith(b"%PDF")
        ):
            raise requests.RequestException("empty pdf")
        _write_bytes(dest_pdf, pdf_resp.content)
        return {
            "candidate_id": candidate["candidate_id"],
            "status": "downloaded_pdf",
            "path": str(dest_pdf),
            "canonical_ingest_path": str(dest_pdf),
            "ingest_format": "pdf",
        }
    except requests.RequestException as exc:
        if dest_pdf.exists():
            dest_pdf.unlink()
        return {"candidate_id": candidate["candidate_id"], "status": "failed", "error": str(exc), "path": ""}


def _match_prepare_entry(candidate: dict[str, Any], prepare_entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    for entry in prepare_entries:
        if entry.get("candidate_id") == candidate.get("candidate_id"):
            return entry
    for entry in prepare_entries:
        if _same_paper(candidate, entry):
            return entry
    return None


def _build_source_manifest(
    raw_root: Path,
    plan: dict[str, Any],
    prepare_manifest: dict[str, Any] | None,
    fetch_results: list[dict[str, Any]],
) -> dict[str, Any]:
    shortlist_map = {item["candidate_id"]: item for item in plan.get("shortlist", [])}
    prepare_entries = _prepared_paper_entries(prepare_manifest)
    sources: list[dict[str, Any]] = []

    for candidate in plan.get("shortlist", []):
        if not candidate.get("user_owned"):
            continue
        entry = _match_prepare_entry(candidate, prepare_entries)
        if not entry:
            continue
        sources.append({
            "candidate_id": candidate["candidate_id"],
            "origin": "user_local",
            "canonical_ingest_path": entry["canonical_ingest_path"],
            "prepared_path": entry.get("prepared_path"),
            "discovered_path": None,
            "source_path": entry["source_path"],
            "ingest_format": entry.get("ingest_format") or _ingest_format_from_path(entry["canonical_ingest_path"]),
            "shortlist_rank": candidate.get("shortlist_rank"),
        })

    for result in fetch_results:
        candidate_id = result["candidate_id"]
        candidate = shortlist_map.get(candidate_id)
        if not candidate or result["status"] in {"failed", "missing_from_plan", "skipped_no_arxiv", "skipped_local_duplicate"}:
            continue
        if not result.get("path"):
            continue
        rel_path = _relative_to_project(Path(result["canonical_ingest_path"]), raw_root)
        discovered_rel = _relative_to_project(Path(result["path"]), raw_root)
        sources.append({
            "candidate_id": candidate_id,
            "origin": "introduced",
            "canonical_ingest_path": rel_path,
            "prepared_path": None,
            "discovered_path": discovered_rel,
            "source_path": None,
            "ingest_format": result.get("ingest_format") or _ingest_format_from_path(rel_path),
            "shortlist_rank": candidate.get("shortlist_rank"),
        })

    sources.sort(key=lambda item: (item.get("shortlist_rank") or 9999, item["candidate_id"]))
    return {
        "status": "ok",
        "sources": sources,
    }


def fetch_from_plan(
    raw_root: Path,
    plan_json: Path,
    candidate_ids: list[str],
    prepared_manifest_json: Path | None = None,
    output_sources: Path | None = None,
) -> dict[str, Any]:
    plan = json.loads(plan_json.read_text(encoding="utf-8"))
    prepare_manifest = _load_prepare_manifest(prepared_manifest_json)
    prepare_entries = _prepared_paper_entries(prepare_manifest)
    index = {c["candidate_id"]: c for c in plan.get("shortlist", []) + plan.get("candidates", [])}
    results = []
    for cid in candidate_ids:
        candidate = index.get(cid)
        if not candidate:
            results.append({"candidate_id": cid, "status": "missing_from_plan", "path": ""})
            continue
        if _match_prepare_entry(candidate, prepare_entries):
            local_entry = _match_prepare_entry(candidate, prepare_entries)
            results.append({
                "candidate_id": cid,
                "status": "skipped_local_duplicate",
                "path": local_entry["canonical_ingest_path"],
            })
            continue
        results.append(_download_source(candidate, raw_root))

    source_manifest = _build_source_manifest(raw_root, plan, prepare_manifest, results)
    if output_sources is not None:
        output_sources.parent.mkdir(parents=True, exist_ok=True)
        output_sources.write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "ok", "results": results, "source_manifest": source_manifest}


def _load_source_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"sources manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"sources manifest is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("sources manifest must be a JSON object")
    if not isinstance(data.get("sources"), list):
        raise ValueError("sources manifest must contain a 'sources' list")
    return data


def build_ingest_handoff(source_manifest: dict[str, Any], mode: str = "serial") -> dict[str, Any]:
    """Build ordered, runtime-neutral ingest handoff tasks for /init.

    The output is intentionally simple so an agent can execute the batch without
    re-interpreting the source manifest shape. It does not execute ingest.
    """
    if mode not in {"serial", "parallel"}:
        raise ValueError("mode must be 'serial' or 'parallel'")
    init_mode = "INIT MODE SERIAL" if mode == "serial" else "INIT MODE PARALLEL"
    sources = list(source_manifest.get("sources") or [])
    sources.sort(key=lambda item: (item.get("shortlist_rank") or 9999, item.get("candidate_id") or ""))

    tasks: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    for source in sources:
        path = str(source.get("canonical_ingest_path") or "").strip()
        candidate_id = str(source.get("candidate_id") or "").strip()
        if not path:
            warnings.append({
                "candidate_id": candidate_id,
                "warning": "missing canonical_ingest_path; skipped from handoff",
            })
            continue
        if Path(path).is_absolute():
            warnings.append({
                "candidate_id": candidate_id,
                "warning": "canonical_ingest_path is absolute; init handoff expects a project-relative path",
            })
        tasks.append({
            "order": len(tasks) + 1,
            "candidate_id": candidate_id,
            "origin": source.get("origin"),
            "canonical_ingest_path": path,
            "ingest_format": source.get("ingest_format"),
            "shortlist_rank": source.get("shortlist_rank"),
            "init_mode": init_mode,
            "commit_after_ingest": mode == "parallel",
            "active_ingest_skill": {
                "codex": ".agents/skills/ingest/SKILL.md",
                "claude_code": ".claude/skills/ingest/SKILL.md",
            },
            "instructions": (
                f"Load the active ingest skill, run ingest for exactly this relative path in {init_mode}, "
                "consume the canonical path verbatim, treat raw/ as read-only, skip per-paper citation/reference "
                "fetches, rebuilds, topic writes, visualization, and discovery follow-ups."
            ),
        })

    return {
        "status": "ok",
        "mode": mode,
        "init_mode": init_mode,
        "task_count": len(tasks),
        "tasks": tasks,
        "warnings": warnings,
    }


def download_to_discovered(
    raw_root: Path,
    arxiv_id: str,
    title: str,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    candidate = {
        "candidate_id": candidate_id or f"arxiv:{arxiv_id}",
        "arxiv_id": arxiv_id,
        "title": title,
    }
    return _download_source(candidate, raw_root)


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _parse_bool(text: str) -> bool:
    return text.lower() not in {"false", "0", "no"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="Prepare local raw inputs into raw/tmp/ and emit a manifest")
    p_prepare.add_argument("--raw-root", default="raw")
    p_prepare.add_argument("--pdf-titles-json")
    p_prepare.add_argument("--output-manifest", required=True)

    p_plan = sub.add_parser("plan", help="Build a deterministic discovery plan for /init")
    p_plan.add_argument("--topic", default="")
    p_plan.add_argument("--mode", default="auto", choices=["auto", "seeded", "bootstrap"])
    p_plan.add_argument("--raw-root", default="raw")
    p_plan.add_argument("--wiki-root", default="wiki")
    p_plan.add_argument("--prepared-manifest")
    p_plan.add_argument("--allow-introduction", default="true")
    p_plan.add_argument("--output-plan")

    p_fetch = sub.add_parser("fetch", help="Download selected shortlist papers into raw/discovered/ and write a source manifest")
    p_fetch.add_argument("--raw-root", default="raw")
    p_fetch.add_argument("--plan-json", required=True)
    p_fetch.add_argument("--prepared-manifest")
    p_fetch.add_argument("--output-sources")
    p_fetch.add_argument("--id", action="append", default=[])

    p_handoff = sub.add_parser("handoff", help="Build ordered ingest handoff tasks from init-sources.json")
    p_handoff.add_argument("--sources-json", required=True)
    p_handoff.add_argument("--mode", choices=["serial", "parallel"], default="serial")
    p_handoff.add_argument("--output-json")

    p_download = sub.add_parser("download", help="Download one arXiv paper into raw/discovered/")
    p_download.add_argument("--raw-root", default="raw")
    p_download.add_argument("--arxiv-id", required=True)
    p_download.add_argument("--title", required=True)
    p_download.add_argument("--candidate-id")

    args = parser.parse_args()

    if args.command == "prepare":
        pdf_titles = None
        if args.pdf_titles_json:
            try:
                pdf_titles = _load_pdf_titles_json(Path(args.pdf_titles_json))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                parser.error(f"--pdf-titles-json: {exc}")
        warnings: list[str] = []
        manifest = prepare_inputs(Path(args.raw_root), pdf_titles=pdf_titles, warning_sink=warnings)
        output_path = Path(args.output_manifest)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        _print_json(manifest)
        return

    if args.command == "plan":
        prepared_manifest = _load_prepare_manifest(Path(args.prepared_manifest)) if args.prepared_manifest else None
        plan = build_plan(
            args.topic,
            Path(args.raw_root),
            Path(args.wiki_root),
            mode=args.mode,
            allow_introduction=_parse_bool(args.allow_introduction),
            prepared_manifest=prepared_manifest,
        )
        if args.output_plan:
            output_path = Path(args.output_plan)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        _print_json(plan)
        return

    if args.command == "download":
        result = download_to_discovered(
            Path(args.raw_root),
            args.arxiv_id,
            args.title,
            candidate_id=args.candidate_id,
        )
        _print_json(result)
        return

    if args.command == "handoff":
        try:
            source_manifest = _load_source_manifest(Path(args.sources_json))
            handoff = build_ingest_handoff(source_manifest, mode=args.mode)
        except ValueError as exc:
            parser.error(str(exc))
        if args.output_json:
            output_path = Path(args.output_json)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")
        _print_json(handoff)
        return

    result = fetch_from_plan(
        Path(args.raw_root),
        Path(args.plan_json),
        args.id,
        prepared_manifest_json=Path(args.prepared_manifest) if args.prepared_manifest else None,
        output_sources=Path(args.output_sources) if args.output_sources else None,
    )
    _print_json(result)


if __name__ == "__main__":
    main()
