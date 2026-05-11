"""Render an academic HTML poster from a dag.json + outline + template.

Ports the mechanical bits of PaperX's DAG2poster.py into OmegaWiki:
  build         — inject outline section blocks into the template
  inject-title  — set <h1 class="title"> and <div class="authors"> from dag.json
  inject-figures — copy referenced figures into the poster's images/ dir
                   (PDF → PNG conversion via pdftoppm when needed)
  validate      — sanity checks on the final HTML

Claude (in the /poster SKILL.md workflow) writes the outline HTML — this
tool only handles mechanical injection, copying, and validation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


# ----------------------------------------------------------------------------
# build — inject outline blocks into the template
# ----------------------------------------------------------------------------

FLOW_BLOCK_PRIMARY = re.compile(
    r'(<main\s+class="main"\s*>\s*'
    r'<div\s+class="flow"\s+id="flow"\s*>\s*)'
    r'(.*?)'
    r'(\s*</div>\s*</main>)',
    flags=re.DOTALL | re.IGNORECASE,
)

FLOW_BLOCK_FALLBACK = re.compile(
    r'(<div\s+class="flow"\s+id="flow"\s*>\s*)'
    r'(.*?)'
    r'(\s*</div>)',
    flags=re.DOTALL | re.IGNORECASE,
)


def _infer_indent(prefix_start_idx: int, full_html: str) -> str:
    line_start = full_html.rfind("\n", 0, prefix_start_idx) + 1
    line = full_html[line_start:prefix_start_idx]
    m = re.match(r"[ \t]*", line)
    return m.group(0) if m else ""


def _indent_block(text: str, indent: str) -> str:
    if not text:
        return ""
    out = []
    for ln in text.split("\n"):
        out.append("" if ln.strip() == "" else indent + ln)
    return "\n".join(out) + ("\n" if not text.endswith("\n") else "")


def _collapse_blank_lines(html: str, max_blank: int = 2) -> str:
    html = re.sub(r"[ \t]+\n", "\n", html)
    html = re.sub(
        r"\n{" + str(max_blank + 2) + r",}", "\n" * (max_blank + 1), html
    )
    return html


def build_poster(
    template_path: Path, outline_path: Path, output_path: Path
) -> Path:
    """Copy template to output_path and inject outline HTML into the flow div."""
    if not template_path.is_file():
        raise FileNotFoundError(f"template not found: {template_path}")
    if not outline_path.is_file():
        raise FileNotFoundError(f"outline not found: {outline_path}")
    if output_path.suffix.lower() != ".html":
        raise ValueError(f"output must be .html: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template_path, output_path)

    outline_raw = outline_path.read_text(encoding="utf-8")
    outline_raw = (
        outline_raw.replace("﻿", "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .strip()
    )
    if outline_raw:
        outline_raw += "\n"

    html = output_path.read_text(encoding="utf-8")
    html = html.replace("﻿", "").replace("\r\n", "\n").replace("\r", "\n")

    m = FLOW_BLOCK_PRIMARY.search(html) or FLOW_BLOCK_FALLBACK.search(html)
    if not m:
        raise ValueError(
            'Cannot find <div class="flow" id="flow">...</div> in template'
        )

    prefix, _, suffix = m.group(1), m.group(2), m.group(3)
    base_indent = _infer_indent(m.start(1), html)
    formatted = _indent_block(outline_raw, base_indent + "  ")
    new_block = prefix + "\n" + formatted + suffix
    html = html[: m.start()] + new_block + html[m.end():]

    html = _collapse_blank_lines(html)
    output_path.write_text(html, encoding="utf-8", newline="\n")
    return output_path


# ----------------------------------------------------------------------------
# inject-title — set <h1 class="title"> and <div class="authors">
# ----------------------------------------------------------------------------

TITLE_TAG_PATTERN = re.compile(
    r'(<h1\s+class="title"\s*>)(.*?)(</h1\s*>)',
    flags=re.IGNORECASE | re.DOTALL,
)

AUTHORS_TAG_PATTERN = re.compile(
    r'(<div\s+class="authors"\s*>)(.*?)(</div\s*>)',
    flags=re.IGNORECASE | re.DOTALL,
)


def inject_title(
    dag_path: Path, poster_path: Path, anonymous: bool = False
) -> None:
    """Read root node from dag.json, replace <h1> and <div class='authors'>."""
    if not dag_path.is_file():
        raise FileNotFoundError(f"dag.json not found: {dag_path}")
    if not poster_path.is_file():
        raise FileNotFoundError(f"poster.html not found: {poster_path}")

    dag = json.loads(dag_path.read_text(encoding="utf-8"))
    nodes = dag.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("Invalid dag.json: 'nodes' list empty or missing")

    root = nodes[0]
    title = str(root.get("name", "")).strip()
    authors = "Anonymous" if anonymous else str(root.get("content", "")).strip()

    if not title:
        raise ValueError("dag.json root node has empty 'name'")
    if not authors:
        authors = "Anonymous"

    html = poster_path.read_text(encoding="utf-8")

    if not TITLE_TAG_PATTERN.search(html):
        raise ValueError('Cannot find <h1 class="title">...</h1> in poster')
    if not AUTHORS_TAG_PATTERN.search(html):
        raise ValueError('Cannot find <div class="authors">...</div> in poster')

    html = TITLE_TAG_PATTERN.sub(
        lambda m: m.group(1) + title + m.group(3), html, count=1
    )
    html = AUTHORS_TAG_PATTERN.sub(
        lambda m: m.group(1) + authors + m.group(3), html, count=1
    )

    poster_path.write_text(html, encoding="utf-8")


# ----------------------------------------------------------------------------
# inject-figures — copy figures, PDF→PNG conversion
# ----------------------------------------------------------------------------

IMG_MD_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def _resolve_source_figure(
    image_basename: str, paper_dir: Path
) -> Optional[Path]:
    """Given an image basename like 'layer_curves.png', find the source file
    in paper_dir/figures/, trying .pdf, .png, .jpg, .jpeg as fallbacks."""
    stem = Path(image_basename).stem
    figures_dir = paper_dir / "figures"
    if not figures_dir.is_dir():
        return None

    # First try exact filename match
    exact = figures_dir / image_basename
    if exact.is_file():
        return exact

    # Then try by stem with common extensions
    for ext in (".pdf", ".png", ".jpg", ".jpeg", ".eps"):
        c = figures_dir / (stem + ext)
        if c.is_file():
            return c

    return None


def _convert_pdf_to_png(source_pdf: Path, dest_png: Path, dpi: int = 200) -> None:
    """Convert a PDF to PNG using pdftoppm. Output is single-page rasterization."""
    dest_png.parent.mkdir(parents=True, exist_ok=True)
    # pdftoppm writes to <prefix>-1.png by default; use -singlefile to drop the suffix
    # Trim the .png to use as the prefix
    prefix = str(dest_png.with_suffix(""))
    subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-r",
            str(dpi),
            "-singlefile",
            str(source_pdf),
            prefix,
        ],
        check=True,
        capture_output=True,
    )


def inject_figures(
    dag_path: Path, paper_dir: Path, poster_dir: Path
) -> dict:
    """Walk visual_node entries in dag.json, copy/convert figures to
    poster_dir/images/. Returns a report dict."""
    if not dag_path.is_file():
        raise FileNotFoundError(f"dag.json not found: {dag_path}")
    if not paper_dir.is_dir():
        raise FileNotFoundError(f"paper dir not found: {paper_dir}")

    images_dest = poster_dir / "images"
    images_dest.mkdir(parents=True, exist_ok=True)

    dag = json.loads(dag_path.read_text(encoding="utf-8"))
    visual_nodes = [n for n in dag.get("nodes", []) if n.get("level") == 2]

    copied = []
    converted = []
    missing = []

    for vn in visual_nodes:
        md_ref = vn.get("name", "")
        m = IMG_MD_PATTERN.search(md_ref)
        if not m:
            continue
        rel_path = m.group(1)  # e.g. "images/layer_curves.png"
        basename = Path(rel_path).name

        source = _resolve_source_figure(basename, paper_dir)
        if source is None:
            missing.append(basename)
            print(f"[warn] no source figure found for {basename}", file=sys.stderr)
            continue

        dest = images_dest / basename
        if source.suffix.lower() == ".pdf" and dest.suffix.lower() == ".png":
            try:
                _convert_pdf_to_png(source, dest)
                converted.append((str(source), str(dest)))
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                missing.append(basename)
                print(
                    f"[warn] PDF→PNG conversion failed for {source}: {e}",
                    file=sys.stderr,
                )
        else:
            shutil.copyfile(source, dest)
            copied.append((str(source), str(dest)))

    return {
        "copied": copied,
        "converted": converted,
        "missing": missing,
        "total_visuals": len(visual_nodes),
    }


# ----------------------------------------------------------------------------
# validate — sanity checks
# ----------------------------------------------------------------------------

IMG_SRC_PATTERN = re.compile(
    r'<img[^>]*\ssrc="([^"]+)"', flags=re.IGNORECASE
)
SECTION_PATTERN = re.compile(
    r'<section\s+class="section"', flags=re.IGNORECASE
)


def validate_poster(poster_path: Path, min_sections: int = 3) -> tuple[bool, list[str]]:
    """Run sanity checks. Returns (passed, issues)."""
    if not poster_path.is_file():
        return False, [f"poster file not found: {poster_path}"]

    html = poster_path.read_text(encoding="utf-8")
    issues: list[str] = []

    # 1. Title non-empty
    tm = TITLE_TAG_PATTERN.search(html)
    if not tm:
        issues.append('missing <h1 class="title">')
    elif not tm.group(2).strip() or tm.group(2).strip() == "Paper Title":
        issues.append('title is empty or unchanged from template placeholder')

    # 2. At least N sections
    sections = SECTION_PATTERN.findall(html)
    if len(sections) < min_sections:
        issues.append(
            f"only {len(sections)} sections found, expected ≥ {min_sections}"
        )

    # 3. All image references resolve
    img_srcs = IMG_SRC_PATTERN.findall(html)
    poster_dir = poster_path.parent
    for src in img_srcs:
        target = poster_dir / src
        if not target.is_file():
            issues.append(f"broken image reference: {src}")

    # 4. No leftover blockers
    for marker in ("TODO", "FIXME", "[UNCONFIRMED]"):
        if marker in html:
            issues.append(f"contains '{marker}' marker — submission blocker")

    return len(issues) == 0, issues


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def cmd_build(args) -> int:
    out = build_poster(
        Path(args.template).resolve(),
        Path(args.outline).resolve(),
        Path(args.output).resolve(),
    )
    print(f"[ok] poster written to {out}")
    return 0


def cmd_inject_title(args) -> int:
    inject_title(
        Path(args.dag).resolve(),
        Path(args.poster).resolve(),
        anonymous=args.anonymous,
    )
    print(f"[ok] title + authors injected into {args.poster}")
    return 0


def cmd_inject_figures(args) -> int:
    report = inject_figures(
        Path(args.dag).resolve(),
        Path(args.paper_dir).resolve(),
        Path(args.poster_dir).resolve(),
    )
    print(f"[ok] figures processed:")
    print(f"  copied:    {len(report['copied'])}")
    print(f"  converted: {len(report['converted'])} (PDF→PNG)")
    print(f"  missing:   {len(report['missing'])}")
    if report["missing"]:
        for m in report["missing"]:
            print(f"    - {m}")
    return 0 if not report["missing"] else 1


def cmd_validate(args) -> int:
    passed, issues = validate_poster(Path(args.poster).resolve())
    if passed:
        print(f"[ok] {args.poster} passes validation")
        return 0
    print(f"[fail] {args.poster} has {len(issues)} issue(s):", file=sys.stderr)
    for issue in issues:
        print(f"  - {issue}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render an academic HTML poster from dag.json + outline + template."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Inject outline into template")
    p_build.add_argument("--template", required=True)
    p_build.add_argument("--outline", required=True)
    p_build.add_argument("--output", required=True)
    p_build.set_defaults(func=cmd_build)

    p_title = sub.add_parser(
        "inject-title", help="Set <h1>/<div class='authors'> from dag.json"
    )
    p_title.add_argument("--dag", required=True)
    p_title.add_argument("poster", help="Path to poster.html (in-place edit)")
    p_title.add_argument(
        "--anonymous", action="store_true", help="Override authors to 'Anonymous'"
    )
    p_title.set_defaults(func=cmd_inject_title)

    p_figs = sub.add_parser(
        "inject-figures",
        help="Copy/convert figures from paper_dir/figures/ to poster_dir/images/",
    )
    p_figs.add_argument("--dag", required=True)
    p_figs.add_argument("--paper-dir", required=True)
    p_figs.add_argument("--poster-dir", required=True)
    p_figs.set_defaults(func=cmd_inject_figures)

    p_val = sub.add_parser("validate", help="Sanity checks on the poster HTML")
    p_val.add_argument("poster", help="Path to poster.html")
    p_val.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
