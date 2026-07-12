#!/usr/bin/env python3
"""Prepare one local paper source for ingest.

Usage:
    python3 tools/prepare_paper_source.py --raw-root raw --source raw/papers/example.pdf
    python3 tools/prepare_paper_source.py --raw-root raw --source raw/papers/example.pdf --title "Recovered Paper Title"
    python3 tools/prepare_paper_source.py --raw-root raw --source raw/papers/example.pdf --title "Recovered Paper Title" --arxiv-id 2401.00001
"""
from __future__ import annotations


import argparse
import json
import os
import re
import shutil
import tarfile
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import requests

from fetch_s2 import search as s2_search
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
MAX_SOURCE_ARCHIVE_BYTES = 250_000_000
LATEX_UNWRAP_COMMANDS = (
    "emph",
    "textbf",
    "textit",
    "textsc",
    "textrm",
    "textsf",
    "texttt",
    "underline",
    "mbox",
    "mathbf",
    "mathit",
    "mathrm",
    "mathsf",
    "mathtt",
    "Large",
    "LARGE",
    "huge",
    "Huge",
    "large",
    "normalsize",
)
LATEX_DROP_WITH_ARG_COMMANDS = (
    "vspace",
    "hspace",
    "vskip",
    "hskip",
    "thanks",
    "footnote",
    "footnotemark",
    "footnotetext",
    "label",
    "rule",
    "raisebox",
)
LATEX_DROP_SIMPLE_COMMANDS = (
    "newline",
    "linebreak",
    "pagebreak",
    "smallskip",
    "medskip",
    "bigskip",
    "noindent",
    "centering",
    "raggedright",
    "raggedleft",
    "hfill",
    "vfill",
    "quad",
    "qquad",
)


def _project_root(raw_root: Path) -> Path:
    return raw_root.resolve().parent


def _relative_to_project(path: Path, raw_root: Path) -> str:
    return str(path.resolve().relative_to(_project_root(raw_root)))


def _resolve_project_path(raw_root: Path, rel_path: str) -> Path:
    return _project_root(raw_root) / rel_path


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


def _normalize_space(text: str) -> str:
    return " ".join(str(text or "").split())


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


def _normalize_arxiv_id(arxiv_id: str) -> str:
    arxiv_id = str(arxiv_id or "").strip()
    if not arxiv_id:
        return ""
    return re.sub(r"v\d+$", "", arxiv_id, flags=re.IGNORECASE)


def _extract_arxiv_id(text: str) -> str:
    for pattern in (ARXIV_NEW_ID_PATTERN, ARXIV_OLD_ID_PATTERN):
        match = pattern.search(text)
        if match:
            return _normalize_arxiv_id(match.group(1))
    return ""


def _recover_arxiv_id_by_title(title: str) -> str:
    """Try to recover an arXiv ID by searching Semantic Scholar with a title."""
    if not title or len(title) < 8:
        return ""
    try:
        results = s2_search(title, limit=5)
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
        if result_title == normalized_title:
            return _normalize_arxiv_id(str(arxiv_id))
        result_tokens = set(_tokenize(result_title))
        if result_tokens and title_tokens:
            overlap = len(result_tokens & title_tokens)
            min_len = min(len(result_tokens), len(title_tokens))
            if min_len > 0 and overlap / min_len >= 0.8:
                return _normalize_arxiv_id(str(arxiv_id))
    return ""


def _download_arxiv_source(arxiv_id: str, dest_dir: Path) -> dict[str, Any]:
    arxiv_id = _normalize_arxiv_id(arxiv_id)
    headers = {"User-Agent": "OmegaWiki-prepare-paper-source/1.0"}
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


def _extract_pdf_metadata(path: Path) -> dict[str, str]:
    if not HAS_PYMUPDF:
        return {}
    try:
        doc = fitz.open(path)
        meta = doc.metadata or {}
        doc.close()
        return {key: str(meta.get(key) or "") for key in ("subject", "keywords", "title")}
    except Exception:
        return {}


def _extract_pdf_metadata_title(path: Path) -> str:
    meta = _extract_pdf_metadata(path)
    title = _normalize_space(meta.get("title", ""))
    if title and not _extract_arxiv_id(title):
        return title[:300]
    return ""


def _strip_latex_comments(text: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def _sanitize_latex_fragment(text: str, *, strip_edge_punctuation: bool = False) -> str:
    cleaned = str(text or "")
    if not cleaned:
        return ""
    cleaned = _strip_latex_comments(cleaned)
    cleaned = cleaned.replace("\\\\", " ")
    cleaned = cleaned.replace("~", " ")
    cleaned = cleaned.replace("$", "")
    cleaned = cleaned.replace(r"\&", "&")
    cleaned = cleaned.replace(r"\%", "%")
    cleaned = cleaned.replace(r"\_", "_")
    cleaned = cleaned.replace(r"\#", "#")

    unwrap_pattern = re.compile(
        rf"\\(?:{'|'.join(LATEX_UNWRAP_COMMANDS)})\*?(?:\[[^\]]*\])?\{{([^{{}}]*)\}}"
    )
    drop_with_arg_pattern = re.compile(
        rf"\\(?:{'|'.join(LATEX_DROP_WITH_ARG_COMMANDS)})\*?(?:\[[^\]]*\])?\{{[^{{}}]*\}}"
    )
    previous = None
    while cleaned != previous:
        previous = cleaned
        cleaned = unwrap_pattern.sub(r"\1", cleaned)
        cleaned = drop_with_arg_pattern.sub(" ", cleaned)

    cleaned = re.sub(
        rf"\\(?:{'|'.join(LATEX_DROP_SIMPLE_COMMANDS)})\b",
        " ",
        cleaned,
    )
    cleaned = cleaned.replace(r"\LaTeX", "LaTeX").replace(r"\TeX", "TeX")
    cleaned = re.sub(r"\\[A-Za-z@]+", " ", cleaned)
    cleaned = cleaned.replace("\\", " ")
    cleaned = cleaned.replace("{", " ").replace("}", " ")
    cleaned = _normalize_space(cleaned)
    if strip_edge_punctuation:
        cleaned = cleaned.strip(" -,:;")
    return cleaned


def _is_usable_pdf_title(title: str) -> bool:
    normalized = _normalize_space(title)
    if len(normalized) < 8:
        return False
    if not re.search(r"[A-Za-z\u4e00-\u9fff]{4}", normalized):
        return False
    if normalized.endswith((":", "-", "/", "|")):
        return False
    return True


def _sanitize_source_title(text: str) -> str:
    cleaned = _sanitize_latex_fragment(text, strip_edge_punctuation=True)
    if not _is_usable_pdf_title(cleaned):
        return ""
    return cleaned[:300]


def _sanitize_source_abstract(text: str) -> str:
    return _sanitize_latex_fragment(text)[:1200]


def _find_tex_file_with_title(source_dir: Path) -> tuple[Path | None, str]:
    for tex_file in sorted(source_dir.rglob("*.tex")):
        try:
            text = tex_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if text and re.search(r"\\[a-z]*title[a-z]*\{", text, re.IGNORECASE):
            return tex_file, text
    return None, ""


def _extract_arxiv_source_metadata(source_dir: Path) -> dict[str, str]:
    _tex_file, source_text = _find_tex_file_with_title(source_dir)
    if not source_text:
        return {"source_title": "", "source_abstract": ""}

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
        source_title = _sanitize_source_title("".join(chars))

    source_abstract = ""
    match = re.search(r"\\begin\{abstract\}(.+?)\\end\{abstract\}", source_text, re.DOTALL | re.IGNORECASE)
    if match:
        source_abstract = _sanitize_source_abstract(match.group(1))

    return {"source_title": source_title, "source_abstract": source_abstract}


def _guess_title_from_tex(text: str, fallback: str) -> str:
    match = re.search(r"\\title\{(.+?)\}", text, re.DOTALL)
    if match:
        title = _sanitize_source_title(match.group(1))
        if title:
            return title
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


def _path_slug(path: Path) -> str:
    return slugify("-".join(path.parts)) or "item"


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
    return "".join(replacements.get(ch, ch) for ch in text)


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


def _base_title_from_path(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").strip() or "Untitled"


def _local_candidate_id(path: Path, raw_root: Path) -> str:
    return f"local:{_path_slug(path.relative_to(raw_root))}"


def _metadata_path_for(path: Path, raw_root: Path) -> Path:
    return raw_root / "tmp" / "papers" / f"{_path_slug(path.relative_to(raw_root))}.prepare.json"


def _load_prepare_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    if payload.get("arxiv_id"):
        payload["arxiv_id"] = _normalize_arxiv_id(str(payload["arxiv_id"]))
    if payload.get("title"):
        payload["title"] = _normalize_space(str(payload["title"]))
    return payload


def _write_prepare_metadata(path: Path, arxiv_id: str, title: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"arxiv_id": _normalize_arxiv_id(arxiv_id)}
    if title:
        payload["title"] = _normalize_space(title)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _replace_tex_title(tex_text: str, title: str) -> str:
    replacement = "\\" + "title" + "{" + _latex_escape(title or "Untitled") + "}"
    match = re.search(r"\\([A-Za-z@]*title[A-Za-z@]*)\{", tex_text, re.IGNORECASE)
    if not match:
        return replacement + "\n" + tex_text.lstrip()

    command = match.group(1)
    open_brace = match.end() - 1
    depth = 1
    idx = open_brace + 1
    while idx < len(tex_text) and depth > 0:
        ch = tex_text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        idx += 1
    if depth != 0:
        return replacement + "\n" + tex_text.lstrip()

    replacement = "\\" + command + "{" + _latex_escape(title or "Untitled") + "}"
    return tex_text[:match.start()] + replacement + tex_text[idx:]


def _rewrite_source_dir_title(source_dir: Path, title: str) -> None:
    if not title:
        return
    tex_file, tex_text = _find_tex_file_with_title(source_dir)
    if tex_file is None or not tex_text:
        return
    rewritten = _replace_tex_title(tex_text, title)
    if rewritten != tex_text:
        _write_text(tex_file, rewritten)


def _refresh_synthetic_tex(path: Path, title: str, pdf_text: str) -> None:
    if pdf_text:
        _write_text(path, _build_synthetic_tex(title, pdf_text))
        return
    if path.exists():
        existing = _read_text(path, limit=120000)
        if existing:
            _write_text(path, _replace_tex_title(existing, title))


def prepare_paper_source(path: Path, raw_root: Path, title: str = "", arxiv_id: str = "") -> dict[str, Any]:
    raw_root = raw_root.resolve()
    path = path.resolve()
    warnings: list[str] = []
    source_rel = _relative_to_project(path, raw_root)
    working_entry = path
    original_format = "directory" if path.is_dir() else path.suffix.lower().lstrip(".")
    prepared_path = ""
    canonical_path = ""
    resolved_source_path = source_rel
    title = re.sub(r"\s+", " ", title).strip()
    arxiv_id = _normalize_arxiv_id(arxiv_id)
    authoritative_title = ""
    abstract_excerpt = ""
    usable = True
    candidate_id = _local_candidate_id(path, raw_root)
    metadata_path = _metadata_path_for(path, raw_root)
    prepared_metadata = _load_prepare_metadata(metadata_path)

    if path.is_file() and _is_archive(path):
        extract_dir = raw_root / "tmp" / "papers" / f"{_path_slug(path.relative_to(raw_root))}-src"
        warnings.extend(_extract_archive_to_tmp(path, extract_dir))
        if extract_dir.exists():
            working_entry = extract_dir
            prepared_path = _relative_to_project(extract_dir, raw_root)
            original_format = "archive"

    candidate_path = _scan_paper_dir(working_entry) if working_entry.is_dir() else working_entry

    if candidate_path is None:
        usable = False
        fallback_title = title or _base_title_from_path(path)
        warnings.append("no parseable .tex or .pdf found for local paper source")
        return {
            "entry_id": candidate_id,
            "candidate_id": candidate_id,
            "source_kind": "paper",
            "source_path": source_rel,
            "resolved_source_path": source_rel,
            "prepared_path": prepared_path or None,
            "canonical_ingest_path": source_rel,
            "original_format": original_format,
            "ingest_format": _ingest_format_from_path(source_rel),
            "title": fallback_title,
            "abstract_excerpt": "",
            "arxiv_id": "",
            "warnings": warnings,
            "usable": usable,
        }

    resolved_source_path = _relative_to_project(candidate_path, raw_root)
    path_slug = _path_slug(path.relative_to(raw_root))
    source_dir = raw_root / "tmp" / "papers" / f"{path_slug}-arxiv-src"
    out_path = raw_root / "tmp" / "papers" / f"{path_slug}.tex"

    if candidate_path.suffix.lower() == ".pdf":
        text, pdf_warnings = _extract_pdf_text(candidate_path)
        warnings.extend(pdf_warnings)
        metadata_title = _extract_pdf_metadata_title(candidate_path)
        stored_authoritative_title = _normalize_space(str(prepared_metadata.get("title") or ""))
        authoritative_title = title or stored_authoritative_title
        provisional_title = authoritative_title or metadata_title or _base_title_from_path(candidate_path)
        abstract_excerpt = _extract_abstract_excerpt(text) if text else ""
        stored_arxiv_id = _normalize_arxiv_id(str(prepared_metadata.get("arxiv_id") or ""))
        arxiv_id = arxiv_id or _extract_arxiv_id(f"{path.name} {source_rel}")
        if not arxiv_id and authoritative_title:
            arxiv_id = _recover_arxiv_id_by_title(authoritative_title)
        if not arxiv_id:
            arxiv_id = stored_arxiv_id

        if source_dir.exists() and any(source_dir.rglob("*")):
            _rewrite_source_dir_title(source_dir, authoritative_title)
            source_meta = _extract_arxiv_source_metadata(source_dir)
            title = authoritative_title or source_meta["source_title"] or provisional_title
            if source_meta["source_abstract"]:
                abstract_excerpt = source_meta["source_abstract"][:1200]
            prepared_path = _relative_to_project(source_dir, raw_root)
            canonical_path = prepared_path
        elif arxiv_id:
            dl_result = _download_arxiv_source(arxiv_id, source_dir)
            if dl_result["success"]:
                _rewrite_source_dir_title(source_dir, authoritative_title)
                source_meta = _extract_arxiv_source_metadata(source_dir)
                title = authoritative_title or source_meta["source_title"] or provisional_title
                if source_meta["source_abstract"]:
                    abstract_excerpt = source_meta["source_abstract"][:1200]
                prepared_path = _relative_to_project(source_dir, raw_root)
                canonical_path = prepared_path
                warnings.append(f"recovered arXiv ID {arxiv_id}; using fetched TeX source")
            else:
                if text or out_path.exists():
                    if authoritative_title or not out_path.exists():
                        _refresh_synthetic_tex(out_path, authoritative_title or provisional_title, text)
                    if out_path.exists():
                        prepared_path = _relative_to_project(out_path, raw_root)
                        canonical_path = prepared_path
                        title = authoritative_title or provisional_title
                        if not abstract_excerpt:
                            abstract_excerpt = _extract_abstract_excerpt(_read_text(out_path, limit=120000))
                    else:
                        canonical_path = resolved_source_path
                        title = authoritative_title or provisional_title
                else:
                    canonical_path = resolved_source_path
                    title = authoritative_title or provisional_title
                warnings.append(
                    f"recovered arXiv ID {arxiv_id} but TeX source download failed; "
                    f"falling back to synthetic tex ({dl_result.get('error', 'unknown error')})"
                )
        else:
            if text or out_path.exists():
                if authoritative_title or not out_path.exists():
                    _refresh_synthetic_tex(out_path, authoritative_title or provisional_title, text)
                if out_path.exists():
                    prepared_path = _relative_to_project(out_path, raw_root)
                    canonical_path = prepared_path
                    title = authoritative_title or provisional_title
                    if not abstract_excerpt:
                        abstract_excerpt = _extract_abstract_excerpt(_read_text(out_path, limit=120000))
                else:
                    canonical_path = resolved_source_path
                    title = authoritative_title or provisional_title
            else:
                canonical_path = resolved_source_path
                title = authoritative_title or provisional_title
    else:
        text = _read_text(candidate_path, limit=120000)
        fallback_title = _base_title_from_path(candidate_path)
        if working_entry.is_dir():
            title = _guess_title_from_tex(text, fallback_title)
        elif candidate_path.suffix.lower() == ".tex":
            title = _guess_title_from_tex(text, fallback_title)
        else:
            title = fallback_title
        arxiv_id = arxiv_id or _extract_arxiv_id(f"{candidate_path.name} {title} {text[:2000]}")
        abstract_excerpt = _extract_abstract_excerpt(text)
        canonical_path = resolved_source_path

    if not arxiv_id:
        arxiv_id = _extract_arxiv_id(f"{path.name} {title} {abstract_excerpt}")
    if candidate_path.suffix.lower() == ".pdf" and prepared_path:
        _write_prepare_metadata(metadata_path, arxiv_id, title=authoritative_title)
    return {
        "entry_id": candidate_id,
        "candidate_id": candidate_id,
        "source_kind": "paper",
        "source_path": source_rel,
        "resolved_source_path": resolved_source_path,
        "prepared_path": prepared_path or None,
        "canonical_ingest_path": canonical_path,
        "original_format": original_format or candidate_path.suffix.lower().lstrip(".") or "file",
        "ingest_format": _ingest_format_from_path(canonical_path),
        "title": title,
        "abstract_excerpt": abstract_excerpt,
        "arxiv_id": arxiv_id,
        "warnings": warnings,
        "usable": usable,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--arxiv-id", default="")
    args = parser.parse_args()

    raw_root = Path(args.raw_root)
    source = Path(args.source)
    if not source.is_absolute():
        source = _resolve_project_path(raw_root, args.source)

    result = prepare_paper_source(source, raw_root, title=args.title, arxiv_id=args.arxiv_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
