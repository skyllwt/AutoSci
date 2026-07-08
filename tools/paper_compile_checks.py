#!/usr/bin/env python3
"""Codex-safe local checks for paper-compile.

This helper intentionally avoids invoking TeX. It validates the paper/ source
tree invariants that are useful before and after latexmk runs: referenced files
exist, citations resolve to references.bib, hard blocker markers are absent,
and anonymous-submission heuristics are surfaced as warnings.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


INPUT_PATTERN = re.compile(r"\\input\{([^}]+)\}")
INCLUDE_GRAPHICS_PATTERN = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
CITE_PATTERN = re.compile(r"\\cite[a-z]*(?:\[[^\]]*\])*\{([^}]+)\}")
BIB_KEY_PATTERN = re.compile(r"@\w+\{([^,\s]+)\s*,")
LABEL_PATTERN = re.compile(r"\\label\{([^}]+)\}")
REF_PATTERN = re.compile(r"\\(?:autoref|cref|Cref|ref)\{([^}]+)\}")
ABSTRACT_PATTERN = re.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", re.S)
AUTHOR_PATTERN = re.compile(r"\\author\{(.*?)\}", re.S)
COMMENT_PATTERN = re.compile(r"(?<!\\)%.*?$", re.M)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _strip_comments(text: str) -> str:
    return COMMENT_PATTERN.sub("", text)


def _resolve_tex_input(paper_dir: Path, value: str) -> Path | None:
    candidate = paper_dir / value
    if candidate.is_file():
        return candidate
    with_tex = paper_dir / f"{value}.tex"
    if with_tex.is_file():
        return with_tex
    return None


def _resolve_figure(paper_dir: Path, value: str) -> Path | None:
    candidate = paper_dir / value
    if candidate.is_file():
        return candidate
    for ext in (".pdf", ".png", ".jpg", ".jpeg", ".eps"):
        with_ext = paper_dir / f"{value}{ext}"
        if with_ext.is_file():
            return with_ext
    return None


def _collect_tex_files(paper_dir: Path, main_tex: Path) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []

    def visit(path: Path) -> None:
        path = path.resolve()
        if path in seen or not path.is_file():
            return
        seen.add(path)
        ordered.append(path)
        text = _strip_comments(_read(path))
        for value in INPUT_PATTERN.findall(text):
            target = _resolve_tex_input(paper_dir, value.strip())
            if target is not None:
                visit(target)

    visit(main_tex)
    return ordered


def _line_hits(files: list[Path], pattern: re.Pattern[str], label: str) -> list[dict]:
    hits: list[dict] = []
    for path in files:
        for lineno, line in enumerate(_read(path).splitlines(), start=1):
            if pattern.search(line):
                hits.append({"file": str(path), "line": lineno, "kind": label, "text": line.strip()})
    return hits


def run_checks(paper_dir: Path) -> dict:
    paper_dir = paper_dir.resolve()
    main_tex = paper_dir / "main.tex"
    blockers: list[dict] = []
    warnings: list[dict] = []
    details: dict = {"paper_dir": str(paper_dir)}

    if not main_tex.is_file():
        blockers.append({"check": "main_tex", "message": f"main.tex not found: {main_tex}"})
        return {"ok": False, "blockers": blockers, "warnings": warnings, "details": details}

    tex_files = _collect_tex_files(paper_dir, main_tex)
    details["tex_files"] = [str(path) for path in tex_files]
    joined_tex = "\n".join(_strip_comments(_read(path)) for path in tex_files)

    missing_inputs = []
    for path in tex_files:
        for value in INPUT_PATTERN.findall(_strip_comments(_read(path))):
            if _resolve_tex_input(paper_dir, value.strip()) is None:
                missing_inputs.append({"file": str(path), "target": value.strip()})
    if missing_inputs:
        blockers.append({"check": "inputs", "message": "missing LaTeX input files", "items": missing_inputs})

    figure_refs = []
    missing_figures = []
    for value in INCLUDE_GRAPHICS_PATTERN.findall(joined_tex):
        value = value.strip()
        figure_refs.append(value)
        if _resolve_figure(paper_dir, value) is None:
            missing_figures.append(value)
    details["figure_refs"] = figure_refs
    if missing_figures:
        blockers.append({"check": "figures", "message": "missing figure files", "items": missing_figures})

    citation_keys = {
        key.strip()
        for group in CITE_PATTERN.findall(joined_tex)
        for key in group.split(",")
        if key.strip()
    }
    bib_path = paper_dir / "references.bib"
    bib_text = _read(bib_path) if bib_path.is_file() else ""
    bib_keys = set(BIB_KEY_PATTERN.findall(bib_text))
    details["citation_keys"] = sorted(citation_keys)
    details["bib_keys"] = sorted(bib_keys)
    if citation_keys and not bib_path.is_file():
        blockers.append({"check": "bibliography", "message": "citations exist but references.bib is missing"})
    missing_citations = sorted(citation_keys - bib_keys)
    if missing_citations:
        blockers.append({"check": "citations", "message": "citation keys missing from references.bib", "items": missing_citations})

    unconfirmed_hits = _line_hits(tex_files + ([bib_path] if bib_path.is_file() else []), re.compile(r"\[UNCONFIRMED\]|UNCONFIRMED_"), "unconfirmed")
    if unconfirmed_hits:
        blockers.append({"check": "unconfirmed", "message": "[UNCONFIRMED] citations remain", "items": unconfirmed_hits})

    if re.search(r"\\nocite\{\s*\*\s*\}", joined_tex):
        blockers.append({"check": "nocite", "message": r"\nocite{*} is forbidden"})

    refs = set(REF_PATTERN.findall(joined_tex))
    labels = set(LABEL_PATTERN.findall(joined_tex))
    details["refs"] = sorted(refs)
    details["labels"] = sorted(labels)
    missing_labels = sorted(refs - labels)
    if missing_labels:
        blockers.append({"check": "references", "message": "references without matching labels", "items": missing_labels})

    main_clean = _strip_comments(_read(main_tex))
    abstract = ABSTRACT_PATTERN.search(main_clean)
    if abstract is None or not abstract.group(1).strip():
        blockers.append({"check": "abstract", "message": "abstract missing or empty"})

    todo_hits = _line_hits(tex_files + ([bib_path] if bib_path.is_file() else []), re.compile(r"\b(?:TODO|FIXME|XXX)\b|\\missingfigure\b"), "todo")
    if todo_hits:
        warnings.append({"check": "todo", "message": "TODO/FIXME/XXX or missingfigure markers remain", "items": todo_hits})

    author_match = AUTHOR_PATTERN.search(main_clean)
    author_text = author_match.group(1).strip() if author_match else ""
    if author_text:
        warnings.append({"check": "anonymous", "message": r"\author{} is non-empty", "items": [author_text]})
    identity_hits = _line_hits(tex_files, re.compile(r"\b(?:university|institute|laboratory|github\.com|gitlab\.com|our previous work|we previously)\b", re.I), "identity")
    if identity_hits:
        warnings.append({"check": "anonymous", "message": "possible anonymous-submission identity leak", "items": identity_hits})

    return {
        "ok": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "details": details,
    }


def _print_text(report: dict) -> None:
    status = "PASS" if report["ok"] else "FAIL"
    print(f"paper-compile checks: {status}")
    for group_name in ("blockers", "warnings"):
        items = report[group_name]
        if not items:
            continue
        print(f"\n{group_name.title()}:")
        for item in items:
            print(f"- {item['check']}: {item['message']}")
            for sub in item.get("items", []):
                print(f"  - {sub}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local paper-compile checklist checks.")
    parser.add_argument("paper_dir", help="Path to paper/ directory")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args(argv)

    report = run_checks(Path(args.paper_dir))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_text(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
