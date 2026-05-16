"""Build a PaperX-compatible dag.json from an OmegaWiki paper directory.

Reads `paper/main.tex` + `paper/sections/*.tex` + `paper/figures/` and
produces the same dag.json schema that PaperX's DAG2poster pipeline expects.

dag.json schema:
{
  "nodes": [
    { "name": <title|section name|"![](images/foo.png)">,
      "content": <authors|section text|caption>,
      "edge": [<section names in root order>],   # root only
      "level": 0|1|2,
      "visual_node": [<image markdown refs>],     # sections only
      "resolution": "WxH",                         # visuals only
      "wide": true|false                           # visuals only; aspect >= WIDE_ASPECT_THRESHOLD
    }, ...
  ]
}

This bridge is LaTeX-only. Wiki entity enrichment happens in the /poster
SKILL.md, where Claude can read PAPER_PLAN and linked wiki/ideas/*.md to
inform per-section distillation prompts.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Optional dependency: Pillow for raster image dimensions
try:
    from PIL import Image  # type: ignore
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


# Aspect ratio at/above which a figure is flagged "wide" — wide figures get
# rendered as a column-spanning sibling block in the poster instead of being
# squeezed into a single column. Also flags very tall figures (1/threshold).
WIDE_ASPECT_THRESHOLD = 2.0


def _is_wide(resolution: str) -> bool:
    """Return True if the figure's aspect ratio crosses the wide threshold
    in either direction (very wide or very tall). Empty/malformed → False."""
    if not resolution:
        return False
    try:
        w_str, h_str = resolution.lower().split("x", 1)
        w, h = int(w_str), int(h_str)
        if w <= 0 or h <= 0:
            return False
        aspect = w / h
        return aspect >= WIDE_ASPECT_THRESHOLD or aspect <= 1.0 / WIDE_ASPECT_THRESHOLD
    except (ValueError, ZeroDivisionError):
        return False


SECTION_NAME_PATTERN = re.compile(r"\\section\*?\{([^}]*)\}")
INCLUDE_GRAPHICS_PATTERN = re.compile(
    r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}"
)
TITLE_PATTERN = re.compile(r"\\title\{(.*?)\}", re.DOTALL)
AUTHOR_PATTERN = re.compile(r"\\author\{(.*?)\}", re.DOTALL)
INPUT_PATTERN = re.compile(r"\\input\{([^}]+)\}")
CAPTION_PATTERN = re.compile(
    r"\\caption\{((?:[^{}]|\{[^{}]*\})*)\}", re.DOTALL
)
FIGURE_ENV_PATTERN = re.compile(
    r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", re.DOTALL
)
COMMENT_PATTERN = re.compile(r"(?<!\\)%.*?$", re.MULTILINE)


def _replace_citations(text: str, cite_map: Optional[dict] = None) -> str:
    """Replace `\\cite*{key1, key2}` with `[1, 2]` using a bibkey → ordinal map.

    Handles all \\cite-family commands (\\cite, \\citep, \\citet, \\citeauthor, ...).
    Unknown keys are dropped. If cite_map is None, citations strip to empty
    (preserves legacy behavior).
    """
    def _sub(m):
        if cite_map is None:
            return ""
        keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
        nums = [str(cite_map[k]) for k in keys if k in cite_map]
        return f"[{', '.join(nums)}]" if nums else ""
    return re.sub(r"\\cite[a-z]*\{([^}]+)\}", _sub, text)


def _extract_table_captions(text: str) -> str:
    """Replace each `\\begin{table}…\\end{table}` env with `[Table: <caption>]`.

    Preserves the table's information as a flat paragraph so the LLM
    distilling can mention key results. Tabular data itself is dropped —
    no room for a real table on a 1400×900 poster.
    """
    def _sub(m):
        body = m.group(0)
        cap = CAPTION_PATTERN.search(body)
        if not cap:
            return ""
        cap_text = cap.group(1)
        cap_text = re.sub(r"\\label\{[^}]*\}", "", cap_text)
        cap_text = re.sub(r"\\ref\{[^}]*\}", "", cap_text)
        cap_text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", cap_text)
        cap_text = re.sub(r"\\emph\{([^}]*)\}", r"\1", cap_text)
        cap_text = re.sub(r"\s+", " ", cap_text).strip()
        return f"\n\n[Table: {cap_text}]\n\n"
    return re.sub(
        r"\\begin\{table\*?\}.*?\\end\{table\*?\}",
        _sub,
        text,
        flags=re.DOTALL,
    )


def _strip_latex_text(
    text: str,
    cite_map: Optional[dict] = None,
    math_macros: Optional[dict] = None,
) -> str:
    """Best-effort LaTeX → plain text.

    Preserves math ($…$, $$…$$, \\(…\\), \\[…\\]) intact for downstream KaTeX
    rendering in the poster HTML. Expands custom math macros (parsed from
    `math_commands.tex`) so KaTeX can render them. Replaces \\cite*{} via
    cite_map. Extracts table captions before stripping the tabular envs.
    Drops figure envs (their captions are pulled separately by
    `_find_caption_for_figure`).
    """
    text = COMMENT_PATTERN.sub("", text)
    text = re.sub(r"\\section\*?\{[^}]*\}", "", text)
    text = re.sub(r"\\subsection\*?\{[^}]*\}", "", text)
    text = re.sub(r"\\paragraph\{[^}]*\}", "", text)
    text = re.sub(r"\\label\{[^}]*\}", "", text)
    text = re.sub(r"\\ref\{[^}]*\}", "", text)
    text = _replace_citations(text, cite_map)
    text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\emph\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\textit\{([^}]*)\}", r"\1", text)
    # Expand custom math macros so KaTeX sees standard commands
    text = _expand_math_macros(text, math_macros or {})
    # Extract table captions first, before they're swallowed by the env regex
    text = _extract_table_captions(text)
    # Strip figure environments — captions pulled separately
    text = re.sub(
        r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}", "", text, flags=re.DOTALL
    )
    # Collapse whitespace (math survives — $…$ tokens are not touched)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _parse_math_macros(paper_dir: Path) -> dict:
    """Parse zero-arg `\\newcommand{\\name}{def}` from `math_commands.tex`.

    Returns {macro_name_with_backslash: definition_string}. Only handles the
    common LaTeX pattern of simple aliases used in math (e.g. `\\drationeg`
    → `\\depthratio^{-}`). Macros with `[n]` argument counts are skipped.
    """
    path = paper_dir / "math_commands.tex"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    text = COMMENT_PATTERN.sub("", text)
    macros: dict[str, str] = {}
    for m in re.finditer(
        r"\\newcommand\{(\\[A-Za-z]+)\}\{((?:[^{}]|\{[^{}]*\})*)\}",
        text,
    ):
        macros[m.group(1)] = m.group(2)
    return macros


def _expand_math_macros(text: str, macros: dict) -> str:
    """Iteratively expand `\\macroname` tokens to their definitions.

    Iterates up to 4 times to resolve transitive references (e.g.
    `\\dratiopos` → `\\depthratio^{+}` → `\\rho^{+}`). Stops when no
    further changes happen. Uses `(?![A-Za-z])` to avoid matching prefixes
    of longer command names. Replacement is done via a lambda so that
    backslashes in the definition (e.g. `\\rho`, `\\depthratio`) are NOT
    interpreted as regex back-reference escapes.
    """
    if not macros:
        return text
    for _ in range(4):
        prev = text
        for name, defn in macros.items():
            text = re.sub(
                re.escape(name) + r"(?![A-Za-z])",
                lambda m, d=defn: d,
                text,
            )
        if text == prev:
            break
    return text


def _build_citation_map(paper_dir: Path) -> dict:
    """Build {bibkey: ordinal} by scanning section .tex files in input order.

    Citations are numbered by first appearance, walking the paper top-to-bottom
    via the `\\input{sections/…}` order in main.tex. Multi-key citations like
    `\\citep{a,b}` register both keys with consecutive ordinals.
    """
    main_tex_path = paper_dir / "main.tex"
    if not main_tex_path.is_file():
        return {}
    main_tex = main_tex_path.read_text(encoding="utf-8")
    main_tex_clean = COMMENT_PATTERN.sub("", main_tex)
    section_order = _extract_section_order(main_tex_clean)

    keymap: dict[str, int] = {}
    next_n = 1
    sections_dir = paper_dir / "sections"
    for sec_name in section_order:
        sec_file = sections_dir / f"{sec_name}.tex"
        if not sec_file.is_file():
            continue
        sec_text = sec_file.read_text(encoding="utf-8")
        sec_text = COMMENT_PATTERN.sub("", sec_text)
        for m in re.finditer(r"\\cite[a-z]*\{([^}]+)\}", sec_text):
            keys = [k.strip() for k in m.group(1).split(",")]
            for k in keys:
                if k and k not in keymap:
                    keymap[k] = next_n
                    next_n += 1
    return keymap


def _extract_title(main_tex: str) -> str:
    m = TITLE_PATTERN.search(main_tex)
    if not m:
        return "Untitled"
    title = m.group(1)
    # Remove \\ line breaks and clean
    title = re.sub(r"\\\\", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title or "Untitled"


def _extract_authors(main_tex: str) -> str:
    m = AUTHOR_PATTERN.search(main_tex)
    if not m:
        return "Anonymous"
    authors = m.group(1).strip()
    # Strip trailing % comment markers and inline comments
    authors = re.sub(r"%.*$", "", authors, flags=re.MULTILINE).strip()
    if not authors:
        return "Anonymous"
    # Clean LaTeX commands like \and, \\
    authors = re.sub(r"\\and\b", ",", authors)
    authors = re.sub(r"\\\\", " ", authors)
    authors = re.sub(r"\s+", " ", authors).strip()
    return authors or "Anonymous"


def _extract_section_order(main_tex: str) -> list[str]:
    """Return ordered list of section filenames referenced by \\input{sections/...}.

    Stops at the first \\appendix marker — appendix content is excluded from
    the poster source since it's typically supplementary."""
    # Truncate at \appendix if present
    appendix_idx = main_tex.find(r"\appendix")
    if appendix_idx >= 0:
        main_tex = main_tex[:appendix_idx]

    matches = INPUT_PATTERN.findall(main_tex)
    order = []
    for path in matches:
        # e.g. "sections/introduction" or "sections/introduction.tex"
        if path.startswith("sections/"):
            name = Path(path).stem
            order.append(name)
    return order


def _read_section_file(
    path: Path,
    cite_map: Optional[dict] = None,
    math_macros: Optional[dict] = None,
) -> tuple[str, str, list[str]]:
    """Read a section .tex file. Returns (display_name, content_text, figure_refs).

    figure_refs are basenames as they appear in \\includegraphics{...}, e.g.
    "figures/layer_curves.pdf" or "figures/layer_curves" (extension may be missing).
    """
    raw = path.read_text(encoding="utf-8")

    # Display name: first \section{...}, fallback to capitalized filename
    sec_match = SECTION_NAME_PATTERN.search(raw)
    if sec_match:
        display_name = sec_match.group(1).strip()
    else:
        display_name = path.stem.replace("_", " ").title()

    figure_refs = INCLUDE_GRAPHICS_PATTERN.findall(raw)

    content = _strip_latex_text(raw, cite_map, math_macros)
    return display_name, content, figure_refs


def _resolve_figure_path(ref: str, paper_dir: Path) -> Optional[Path]:
    """Given a LaTeX reference like 'figures/foo' or 'figures/foo.pdf',
    return the actual file path on disk, trying common extensions."""
    candidate = paper_dir / ref
    if candidate.is_file():
        return candidate
    # Extension missing — try common ones
    for ext in (".pdf", ".png", ".jpg", ".jpeg", ".eps"):
        c = paper_dir / (ref + ext)
        if c.is_file():
            return c
    return None


def _get_resolution(path: Path) -> str:
    """Return 'WxH' string for an image file. Empty string on failure."""
    ext = path.suffix.lower()

    if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"):
        if _HAS_PIL:
            try:
                with Image.open(path) as img:
                    return f"{img.width}x{img.height}"
            except Exception as e:
                print(
                    f"[warn] PIL failed on {path}: {e}", file=sys.stderr
                )
                return ""
        else:
            print(
                f"[warn] PIL not installed; cannot get resolution for {path}",
                file=sys.stderr,
            )
            return ""

    if ext == ".pdf":
        # Use pdfinfo to read page size in points, convert to pixels @ 200 DPI
        try:
            out = subprocess.run(
                ["pdfinfo", str(path)],
                capture_output=True,
                text=True,
                check=True,
            )
            m = re.search(
                r"Page size:\s+([\d.]+)\s*x\s*([\d.]+)\s*pts", out.stdout
            )
            if m:
                pts_w = float(m.group(1))
                pts_h = float(m.group(2))
                dpi = 200
                px_w = int(pts_w * dpi / 72)
                px_h = int(pts_h * dpi / 72)
                return f"{px_w}x{px_h}"
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(
                f"[warn] pdfinfo failed on {path}: {e}", file=sys.stderr
            )
        return ""

    return ""


def _destination_image_name(source_path: Path) -> str:
    """Map a source figure to its destination image filename in the poster.

    PDF figures will be converted to PNG by `tools/poster.py inject-figures`,
    so we name them with .png up front for schema consistency. Other formats
    keep their extension.
    """
    ext = source_path.suffix.lower()
    if ext == ".pdf":
        return f"images/{source_path.stem}.png"
    return f"images/{source_path.name}"


def _find_caption_for_figure(
    section_text: str, figure_ref: str, cite_map: Optional[dict] = None
) -> str:
    """Locate a \\caption{...} associated with the figure environment that
    contains \\includegraphics{figure_ref}. Returns empty string if none."""
    figure_basename = Path(figure_ref).stem
    for fig_env_match in FIGURE_ENV_PATTERN.finditer(section_text):
        env_body = fig_env_match.group(1)
        if figure_basename in env_body:
            cap_match = CAPTION_PATTERN.search(env_body)
            if cap_match:
                caption = cap_match.group(1)
                # Strip inner LaTeX
                caption = re.sub(r"\\label\{[^}]*\}", "", caption)
                caption = _replace_citations(caption, cite_map)
                caption = re.sub(r"\\textbf\{([^}]*)\}", r"\1", caption)
                caption = re.sub(r"\\emph\{([^}]*)\}", r"\1", caption)
                caption = re.sub(r"\s+", " ", caption).strip()
                return caption
    return ""


def build_dag(paper_dir: Path, output_path: Path, anonymous: bool = False) -> dict:
    """Build dag.json from paper directory. Writes to output_path and returns the dict."""
    main_tex_path = paper_dir / "main.tex"
    if not main_tex_path.is_file():
        raise FileNotFoundError(f"main.tex not found: {main_tex_path}")

    main_tex = main_tex_path.read_text(encoding="utf-8")
    main_tex_clean = COMMENT_PATTERN.sub("", main_tex)

    title = _extract_title(main_tex_clean)
    authors = "Anonymous" if anonymous else _extract_authors(main_tex_clean)
    section_order = _extract_section_order(main_tex_clean)
    cite_map = _build_citation_map(paper_dir)
    math_macros = _parse_math_macros(paper_dir)

    # Build section nodes
    section_nodes = []
    section_names_in_order: list[str] = []
    # Track visuals across all sections (deduplicated by destination path)
    visual_seen: dict[str, dict] = {}

    sections_dir = paper_dir / "sections"
    for sec_basename in section_order:
        sec_path = sections_dir / f"{sec_basename}.tex"
        if not sec_path.is_file():
            print(
                f"[warn] section file not found: {sec_path}", file=sys.stderr
            )
            continue

        sec_raw = sec_path.read_text(encoding="utf-8")
        display_name, content_text, figure_refs = _read_section_file(
            sec_path, cite_map, math_macros
        )

        if not display_name or display_name.lower() == "abstract":
            # Abstract has no \section{}; use the filename as display
            display_name = sec_basename.replace("_", " ").title()

        section_names_in_order.append(display_name)

        # Map figure refs → destination paths + collect visual nodes
        visual_node_refs: list[str] = []
        for ref in figure_refs:
            resolved = _resolve_figure_path(ref, paper_dir)
            if resolved is None:
                print(
                    f"[warn] figure not found on disk: {ref}", file=sys.stderr
                )
                continue
            dest_name = _destination_image_name(resolved)
            md_ref = f"![]({dest_name})"

            if dest_name not in visual_seen:
                caption = _find_caption_for_figure(sec_raw, ref, cite_map)
                resolution = _get_resolution(resolved)
                visual_seen[dest_name] = {
                    "name": md_ref,
                    "content": caption,
                    "edge": [],
                    "level": 2,
                    "visual_node": [],
                    "resolution": resolution,
                    "wide": _is_wide(resolution),
                    "_source_path": str(resolved),  # private, removed before write
                }

            if md_ref not in visual_node_refs:
                visual_node_refs.append(md_ref)

        section_nodes.append({
            "name": display_name,
            "content": content_text,
            "edge": [],
            "level": 1,
            "visual_node": visual_node_refs,
            "resolution": "",
        })

    # Visual nodes — drop the private _source_path before writing (kept strict PaperX-compatible)
    visual_nodes = []
    for node in visual_seen.values():
        node.pop("_source_path", None)
        visual_nodes.append(node)

    # Root node
    root_node = {
        "name": title,
        "content": authors,
        "edge": section_names_in_order,
        "level": 0,
        "visual_node": [],
        "resolution": "",
    }

    dag = {"nodes": [root_node] + section_nodes + visual_nodes}

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(dag, f, ensure_ascii=False, indent=2)

    return dag


def cmd_build(args) -> int:
    paper_dir = Path(args.paper_dir).resolve()
    output_path = Path(args.output).resolve()

    if not paper_dir.is_dir():
        print(f"[error] paper directory not found: {paper_dir}", file=sys.stderr)
        return 1

    dag = build_dag(paper_dir, output_path, anonymous=args.anonymous)

    n_sections = sum(1 for n in dag["nodes"] if n.get("level") == 1)
    n_visuals = sum(1 for n in dag["nodes"] if n.get("level") == 2)
    print(f"[ok] wrote {output_path}")
    print(f"  root: '{dag['nodes'][0]['name']}'")
    print(f"  sections: {n_sections}")
    print(f"  visuals: {n_visuals}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a PaperX-compatible dag.json from a LaTeX paper directory."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser(
        "build", help="Build dag.json from paper/main.tex + sections + figures"
    )
    p_build.add_argument(
        "--paper-dir",
        required=True,
        help="Path to the LaTeX paper directory (must contain main.tex)",
    )
    p_build.add_argument(
        "--output", required=True, help="Output path for dag.json"
    )
    p_build.add_argument(
        "--anonymous",
        action="store_true",
        help="Force authors='Anonymous' regardless of \\author{} content",
    )
    p_build.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
