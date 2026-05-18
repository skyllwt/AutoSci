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
import html
import json
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
    dag_path: Path,
    poster_path: Path,
    anonymous: bool = False,
    authors_override: Optional[str] = None,
) -> None:
    """Read root node from dag.json, replace <h1> and <div class='authors'>.

    Precedence for the authors string:
      1. `anonymous=True` always wins → "Anonymous"
      2. `authors_override` (e.g. from /poster --authors flag)
      3. dag.json root node's "content" field
      4. Fallback "Anonymous" if all of the above are empty
    """
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

    if anonymous:
        authors = "Anonymous"
    elif authors_override and authors_override.strip():
        authors = authors_override.strip()
    else:
        authors = str(root.get("content", "")).strip()

    if not title:
        raise ValueError("dag.json root node has empty 'name'")
    if not authors:
        authors = "Anonymous"

    html_content = poster_path.read_text(encoding="utf-8")

    if not TITLE_TAG_PATTERN.search(html_content):
        raise ValueError('Cannot find <h1 class="title">...</h1> in poster')
    if not AUTHORS_TAG_PATTERN.search(html_content):
        raise ValueError('Cannot find <div class="authors">...</div> in poster')

    # Escape — these strings come from dag.json / --authors / .author_display.txt
    # and could contain `<`, `&`, or markup that would otherwise be parsed as
    # HTML (or worse) when the poster is opened in a browser.
    title_safe = html.escape(title, quote=False)
    authors_safe = html.escape(authors, quote=False)

    html_content = TITLE_TAG_PATTERN.sub(
        lambda m: m.group(1) + title_safe + m.group(3), html_content, count=1
    )
    html_content = AUTHORS_TAG_PATTERN.sub(
        lambda m: m.group(1) + authors_safe + m.group(3), html_content, count=1
    )

    poster_path.write_text(html_content, encoding="utf-8")


# ----------------------------------------------------------------------------
# inject-header — venue text + affiliation/conference logos
# ----------------------------------------------------------------------------

LOGO_AFFILIATION_PATTERN = re.compile(
    r'(<div\s+class="logo-affiliation"[^>]*>)(.*?)(</div\s*>)',
    flags=re.IGNORECASE | re.DOTALL,
)

CONF_BLOCK_PATTERN = re.compile(
    r'(<div\s+class="conf"[^>]*>)(.*?)(</div\s*>\s*</header)',
    flags=re.IGNORECASE | re.DOTALL,
)

SUPPORTED_LAYOUTS = ("corners", "stacked")


def _copy_logo(source: Path, dest_dir: Path) -> str:
    """Copy a logo file into dest_dir/, converting PDF→PNG if needed.

    Returns the relative path used in the HTML (e.g. 'images/affiliation.png').
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".pdf":
        dest = dest_dir / (source.stem + ".png")
        _convert_pdf_to_png(source, dest)
    else:
        dest = dest_dir / source.name
        shutil.copyfile(source, dest)
    return f"images/{dest.name}"


def _affiliation_div_body(rel_path: Optional[str]) -> str:
    if not rel_path:
        return ""
    # Escape — a logo filename like `evil".onerror=alert(1).png` would
    # otherwise break out of the src attribute. quote=True turns " into
    # &quot; so it stays inside the attribute value.
    safe = html.escape(rel_path, quote=True)
    return f'<img src="{safe}" alt="Affiliation" />'


def _conf_block_body(
    layout: str,
    venue: Optional[str],
    affiliation_rel: Optional[str],
    conference_rel: Optional[str],
) -> str:
    """Build the inner HTML of <div class="conf"> based on layout."""
    parts: list[str] = []
    venue_html = html.escape(venue.strip()) if venue and venue.strip() else ""

    # Escape both relative paths the same way as _affiliation_div_body —
    # a quote character in a logo filename would otherwise break the
    # src attribute.
    aff_safe = (
        html.escape(affiliation_rel, quote=True) if affiliation_rel else None
    )
    conf_safe = (
        html.escape(conference_rel, quote=True) if conference_rel else None
    )

    if layout == "corners":
        # venue text on top, conference logo underneath; affiliation lives in
        # the title-block on the left.
        parts.append(f'<div class="venue">{venue_html}</div>')
        if conf_safe:
            parts.append(
                f'<div class="logo-conference"><img src="{conf_safe}" alt="Conference" /></div>'
            )
        else:
            parts.append('<div class="logo-conference"></div>')
    elif layout == "stacked":
        # both logos stacked in the conf area; title-block has no logo.
        parts.append(f'<div class="venue">{venue_html}</div>')
        if aff_safe:
            parts.append(
                f'<div class="logo-conference"><img src="{aff_safe}" alt="Affiliation" /></div>'
            )
        if conf_safe:
            parts.append(
                f'<div class="logo-conference"><img src="{conf_safe}" alt="Conference" /></div>'
            )
        if not aff_safe and not conf_safe:
            parts.append('<div class="logo-conference"></div>')
    else:
        raise ValueError(f"unsupported layout: {layout}")

    # Indent for readability inside the .conf wrapper
    return "\n      " + "\n      ".join(parts) + "\n    "


def inject_header(
    poster_path: Path,
    venue: Optional[str] = None,
    affiliation_logo: Optional[Path] = None,
    conference_logo: Optional[Path] = None,
    layout: str = "corners",
) -> dict:
    """Inject venue text and optional logos into the poster header.

    Logos are copied into <poster_dir>/images/ (PDF→PNG when needed). The
    final HTML stays self-contained as long as images/ is co-located.
    """
    if layout not in SUPPORTED_LAYOUTS:
        raise ValueError(
            f"unsupported layout '{layout}'; choose one of {SUPPORTED_LAYOUTS}"
        )
    if not poster_path.is_file():
        raise FileNotFoundError(f"poster not found: {poster_path}")

    poster_dir = poster_path.parent
    images_dest = poster_dir / "images"

    affiliation_rel: Optional[str] = None
    conference_rel: Optional[str] = None
    if affiliation_logo:
        if not affiliation_logo.is_file():
            raise FileNotFoundError(f"affiliation logo not found: {affiliation_logo}")
        affiliation_rel = _copy_logo(affiliation_logo, images_dest)
    if conference_logo:
        if not conference_logo.is_file():
            raise FileNotFoundError(f"conference logo not found: {conference_logo}")
        conference_rel = _copy_logo(conference_logo, images_dest)

    html_text = poster_path.read_text(encoding="utf-8")

    if not LOGO_AFFILIATION_PATTERN.search(html_text):
        raise ValueError(
            'cannot find <div class="logo-affiliation"> slot in poster — '
            'template out of date?'
        )
    if not CONF_BLOCK_PATTERN.search(html_text):
        raise ValueError(
            'cannot find <div class="conf"> slot in poster — template out of date?'
        )

    # 1) affiliation slot in title-block (corners layout only)
    aff_body_html = (
        _affiliation_div_body(affiliation_rel) if layout == "corners" else ""
    )
    html_text = LOGO_AFFILIATION_PATTERN.sub(
        lambda m: m.group(1) + aff_body_html + m.group(3), html_text, count=1
    )

    # 2) conf block — replace entire inner content
    conf_body = _conf_block_body(layout, venue, affiliation_rel, conference_rel)
    html_text = CONF_BLOCK_PATTERN.sub(
        lambda m: m.group(1) + conf_body + m.group(3), html_text, count=1
    )

    poster_path.write_text(html_text, encoding="utf-8")

    return {
        "layout": layout,
        "venue": venue or "",
        "affiliation_logo": affiliation_rel or "",
        "conference_logo": conference_rel or "",
    }


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

    # First try exact filename match at the top level
    exact = figures_dir / image_basename
    if exact.is_file():
        return exact

    # Then try by stem with common extensions at the top level
    for ext in (".pdf", ".png", ".jpg", ".jpeg", ".eps"):
        c = figures_dir / (stem + ext)
        if c.is_file():
            return c

    # Finally, fall back to a recursive search by stem so figures
    # placed in subdirs (e.g. `paper/figures/exp1/foo.pdf` referenced
    # in LaTeX as `\includegraphics{figures/exp1/foo}` and flattened to
    # `images/foo.png` by wiki2dag) still resolve. Walk paper/figures/**
    # once, prefer matches in the listed-extension priority order so a
    # PDF wins over a same-stem JPG sketch the author may have left
    # behind.
    matches: dict[str, Path] = {}
    for p in figures_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.stem != stem:
            continue
        ext = p.suffix.lower()
        if ext in (".pdf", ".png", ".jpg", ".jpeg", ".eps"):
            matches.setdefault(ext, p)
    for ext in (".pdf", ".png", ".jpg", ".jpeg", ".eps"):
        if ext in matches:
            return matches[ext]

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
# render — HTML → PNG via headless browser (Chrome/Edge/Chromium/Firefox)
# ----------------------------------------------------------------------------

POSTER_WIDTH_PATTERN = re.compile(
    r"--poster-width:\s*(\d+)\s*px", flags=re.IGNORECASE
)
POSTER_HEIGHT_PATTERN = re.compile(
    r"--poster-height:\s*(\d+)\s*px", flags=re.IGNORECASE
)


def _find_browser() -> tuple[Path, str]:
    """Locate a headless-capable browser. Returns (path, browser_type).

    Browser_type is "chromium" for any Chromium-based browser (Chrome,
    Edge, Chromium proper) or "firefox" for Mozilla Firefox. Chromium
    is preferred because we rely on `--force-device-scale-factor` (HiDPI)
    and `--virtual-time-budget` (sync wait for fonts/KaTeX/fit), neither
    of which Firefox supports — Firefox is a documented fallback.
    """
    # (path, browser_type) candidates in preference order
    candidates: list[tuple[str, str]] = [
        # macOS — Chromium family first
        ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "chromium"),
        ("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", "chromium"),
        ("/Applications/Chromium.app/Contents/MacOS/Chromium", "chromium"),
        # PATH lookups (Linux + portable macOS Homebrew) — Chromium family
        (shutil.which("google-chrome") or "", "chromium"),
        (shutil.which("microsoft-edge") or "", "chromium"),
        (shutil.which("microsoft-edge-stable") or "", "chromium"),
        (shutil.which("chromium") or "", "chromium"),
        (shutil.which("chromium-browser") or "", "chromium"),
        (shutil.which("chrome") or "", "chromium"),
        # Windows — Chromium family
        (r"C:\Program Files\Google\Chrome\Application\chrome.exe", "chromium"),
        (r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "chromium"),
        (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "chromium"),
        (r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", "chromium"),
        # Firefox fallback (Gecko) — lower-quality screenshots: no HiDPI
        # scaling, no virtual-time-budget. Better than nothing.
        ("/Applications/Firefox.app/Contents/MacOS/firefox", "firefox"),
        (shutil.which("firefox") or "", "firefox"),
        (r"C:\Program Files\Mozilla Firefox\firefox.exe", "firefox"),
        (r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe", "firefox"),
    ]
    for path_str, btype in candidates:
        if path_str and Path(path_str).is_file():
            return Path(path_str), btype
    raise FileNotFoundError(
        "No headless-capable browser found. Install one of (Chromium-based "
        "preferred for full HiDPI + sync-wait support):\n"
        "  macOS:    brew install --cask google-chrome   (recommended)\n"
        "            brew install --cask microsoft-edge\n"
        "            brew install --cask firefox          (fallback, 1x only)\n"
        "  Linux:    apt install chromium-browser        (or distro equivalent)\n"
        "            apt install microsoft-edge-stable\n"
        "            apt install firefox                   (fallback, 1x only)\n"
        "  Windows:  https://www.google.com/chrome/      (recommended)\n"
        "            Microsoft Edge is preinstalled on Windows 10+\n"
        "            https://www.mozilla.org/firefox/    (fallback, 1x only)"
    )


def _parse_dims(html_path: Path) -> tuple[int, int]:
    """Extract --poster-width / --poster-height from the HTML's inline CSS.

    Falls back to the default template's (1400, 900) if not found.
    """
    html = html_path.read_text(encoding="utf-8")
    mw = POSTER_WIDTH_PATTERN.search(html)
    mh = POSTER_HEIGHT_PATTERN.search(html)
    w = int(mw.group(1)) if mw else 1400
    h = int(mh.group(1)) if mh else 900
    return w, h


def _render_via_playwright(
    html_path: Path, output_path: Path, scale: int
) -> None:
    """Render via Playwright (Chromium) with PaperX-style event waits.

    Waits for: domcontentloaded, .poster + #flow attached, document.fonts.ready,
    all <img> in #flow loaded, and flow.scrollWidth stable for 10 consecutive
    animation frames (fit() converged). This is the same convergence criterion
    PaperX uses in their take_screenshot_poster, and is the only reliable way
    to capture a stabilized layout — Chrome's --virtual-time-budget is a
    wall-clock timeout that can race with slow CDN responses for fonts/KaTeX.
    """
    from playwright.sync_api import sync_playwright  # type: ignore[import]

    w, h = _parse_dims(html_path)
    html_uri = "file://" + str(html_path.resolve())
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, args=["--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": w, "height": h},
            device_scale_factor=scale,
        )
        page = context.new_page()
        page.goto(html_uri, wait_until="domcontentloaded")

        # Wait for structural attachment
        page.wait_for_selector(".poster", state="attached", timeout=30_000)
        page.wait_for_selector("#flow", state="attached", timeout=30_000)

        # Wait for fonts (best-effort — older browsers may not support it)
        try:
            page.evaluate(
                "() => document.fonts ? document.fonts.ready : Promise.resolve()"
            )
        except Exception:
            pass

        # Wait for every <img> inside #flow to fire load (or error)
        # Wait for EVERY <img> inside .poster (header logos included), not
        # just `#flow` images. Header logos load via inject-header and can
        # finish after #flow images — without this, the screenshot or
        # overflow probe may fire before logo bitmaps land and miss
        # header clipping or render blank logo slots.
        page.evaluate(r"""
        () => {
          const poster = document.querySelector(".poster");
          if (!poster) return Promise.resolve();
          const imgs = Array.from(poster.querySelectorAll("img"));
          if (imgs.length === 0) return Promise.resolve();
          return Promise.all(imgs.map(img => {
            if (img.complete) return Promise.resolve();
            return new Promise(res => {
              img.addEventListener("load",  res, { once: true });
              img.addEventListener("error", res, { once: true });
            });
          }));
        }
        """)

        # Wait for fit() convergence: scrollWidth stable for 10 consecutive
        # animation frames. Once fit() finishes its binary search and the
        # MutationObserver settles, this terminates cleanly.
        page.evaluate(r"""
        () => new Promise((resolve) => {
          const flow = document.getElementById("flow");
          if (!flow) return resolve();
          let last = -1;
          let stableCount = 0;
          function tick() {
            const cur = flow.scrollWidth;
            if (cur === last) stableCount += 1;
            else stableCount = 0;
            last = cur;
            if (stableCount >= 10) return resolve();
            requestAnimationFrame(tick);
          }
          tick();
        })
        """)

        # Before screenshotting, remove the .stage padding. The .stage uses
        # padding:24px to give the .poster visual breathing room when viewed
        # in a browser, but with viewport==W×H that padding shoves the
        # .poster's right + bottom borders past the visible viewport.
        # locator.screenshot() then silently clips them. Zeroing .stage's
        # padding parks .poster at (0,0) within the viewport, so its full
        # 1400×900 box (including all four 3px borders) is captured.
        # The template's CSS stays untouched — this override only applies
        # to the headless render.
        page.evaluate(
            "() => { const s = document.querySelector('.stage');"
            "if (s) { s.style.padding = '0'; s.style.minHeight = '0'; } }"
        )
        page.locator(".poster").screenshot(path=str(output_path))
        browser.close()


_STAGE_RESET_STYLE = (
    "<style>"
    ".stage{padding:0!important;min-height:0!important;display:block!important;}"
    "</style>"
)


def _materialize_render_html(html_path: Path) -> Path:
    """Return a path to an HTML file with `.stage{padding:0}` inlined.

    Subprocess render screenshots the whole viewport (no element-level
    selection like Playwright's `locator(".poster").screenshot()`), so
    the template's 24px `.stage` padding shoves `.poster`'s right and
    bottom borders past the visible viewport and Chrome silently clips
    them. The Playwright path zeros that padding via `page.evaluate(...)`
    before its element screenshot, but subprocess can't run mid-render
    JS — so we instead inline a high-specificity `<style>` override into
    a side-by-side temp HTML, point the browser at that copy, and leave
    the source file untouched.
    """
    src = html_path.read_text(encoding="utf-8")
    # Inject the override just before </head>; if no </head> exists, prepend
    # to the document. The override uses !important so it wins over any
    # earlier `.stage` rule in the template's <style> block.
    if "</head>" in src:
        patched = src.replace("</head>", _STAGE_RESET_STYLE + "</head>", 1)
    else:
        patched = _STAGE_RESET_STYLE + src
    tmp = html_path.with_name(f".{html_path.stem}.subprocess-render.html")
    tmp.write_text(patched, encoding="utf-8")
    return tmp


def _render_via_subprocess(
    html_path: Path, output_path: Path, scale: int
) -> tuple[str, int]:
    """Fallback: render via the system browser binary as a subprocess.

    Used when Playwright isn't installed or its Chromium isn't downloaded.
    Returns (browser_type, effective_scale). Firefox path clamps scale to 1.

    Writes a temp HTML copy with `.stage{padding:0}` inlined so the
    poster's right/bottom borders aren't clipped by the viewport edge
    (see _materialize_render_html). The temp file is cleaned up on
    success; left for debugging on failure.
    """
    browser, browser_type = _find_browser()
    w, h = _parse_dims(html_path)
    render_src = _materialize_render_html(html_path)
    html_uri = "file://" + str(render_src.resolve())

    effective_scale = scale
    if browser_type == "chromium":
        cmd = [
            str(browser),
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-sandbox",
            f"--screenshot={output_path}",
            f"--window-size={w},{h}",
            f"--force-device-scale-factor={scale}",
            # 5s wall-clock budget. Less reliable than Playwright's event
            # waits — used only as a fallback path.
            "--virtual-time-budget=5000",
            html_uri,
        ]
    elif browser_type == "firefox":
        effective_scale = 1
        if scale != 1:
            print(
                f"[warn] Firefox doesn't support HiDPI scaling; "
                f"rendering at 1x ({w}x{h}). Install Chrome/Edge for {scale}x.",
                file=sys.stderr,
            )
        print(
            "[warn] Using Firefox fallback: PNG may show pre-converged "
            "fit() state (no virtual-time-budget). Install Playwright + "
            "chromium for fully-stabilized layout.",
            file=sys.stderr,
        )
        cmd = [
            str(browser),
            "--headless",
            f"--screenshot={output_path}",
            f"--window-size={w},{h}",
            html_uri,
        ]
    else:
        raise ValueError(f"unknown browser_type: {browser_type}")

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        # Keep the temp file around so the caller can inspect what the
        # browser actually loaded; surface the path in the error.
        raise
    else:
        # On success, clean up the temp render HTML.
        try:
            render_src.unlink()
        except OSError:
            pass

    if not output_path.is_file():
        raise RuntimeError(
            f"{browser_type} ran but did not produce {output_path}. "
            f"Try running manually:\n  {' '.join(cmd)}"
        )
    return browser_type, effective_scale


def render_poster(
    html_path: Path,
    output_path: Optional[Path] = None,
    scale: int = 2,
) -> tuple[Path, str, int]:
    """Render an HTML poster to PNG.

    Prefers Playwright (event-based waits — matches PaperX). Falls back to
    a subprocess against a system browser (Chrome/Edge/Chromium/Firefox)
    when Playwright is unavailable. Returns (path, engine_label, scale).

    engine_label is one of "playwright-chromium" (recommended) or the
    underlying browser_type from `_find_browser` ("chromium" / "firefox").
    """
    if not html_path.is_file():
        raise FileNotFoundError(f"poster HTML not found: {html_path}")
    if scale not in (1, 2, 3):
        raise ValueError(f"scale must be 1, 2, or 3 (got {scale})")

    if output_path is None:
        output_path = html_path.with_suffix(".png")

    # Try Playwright first — strongly preferred because its event waits
    # eliminate the timing races that hit the subprocess --virtual-time-
    # budget path on slow networks.
    try:
        _render_via_playwright(html_path, output_path, scale)
        return output_path, "playwright-chromium", scale
    except ImportError:
        # playwright not installed at all — silently fall back
        pass
    except Exception as e:
        # playwright is there but something else failed (e.g. chromium browser
        # not downloaded via `python -m playwright install chromium`). Surface
        # a hint and fall back so the user still gets a PNG.
        msg = str(e)
        if (
            "Executable doesn" in msg
            or "playwright install" in msg
            or "BrowserType" in msg
        ):
            print(
                "[warn] Playwright installed but chromium browser missing. "
                "Run: python -m playwright install chromium  "
                "Falling back to system browser.",
                file=sys.stderr,
            )
        else:
            print(
                f"[warn] Playwright render failed ({e}); falling back to "
                "system browser.",
                file=sys.stderr,
            )

    # Subprocess fallback
    browser_type, eff_scale = _render_via_subprocess(
        html_path, output_path, scale
    )
    return output_path, browser_type, eff_scale


# ----------------------------------------------------------------------------
# check-overflow — programmatic clipping detector for Step 5.5
# ----------------------------------------------------------------------------

# JavaScript that walks the rendered DOM and returns a structured overflow
# report. Two probe groups:
#   1. Flow-content probes (sections, paragraphs, figures) — checked against
#      #flow's bounding rect. Strict: flags anything past flow.right/bottom
#      including content that bleeds into .main's padding zone.
#   2. Header-content probes (title, authors, venue, logos) — checked against
#      .poster's bounding rect. Catches header clipping like a long venue
#      string overflowing the .conf column.
# This is the ground truth that fit() / the LLM can both miss — DOM
# measurements don't lie about clipping.
_OVERFLOW_PROBE_JS = r"""
() => {
  const poster = document.querySelector(".poster");
  const flow = document.getElementById("flow");
  if (!poster || !flow) {
    return { ok: true, clipped: [], flow: null,
             error: "missing .poster or #flow element" };
  }
  const pr = poster.getBoundingClientRect();
  const fr = flow.getBoundingClientRect();
  const TOL = 1;
  const clipped = [];

  function record(el, refRect, region) {
    const r = el.getBoundingClientRect();
    const bot   = Math.round(r.bottom - refRect.bottom);
    const right = Math.round(r.right  - refRect.right);
    if (bot > TOL || right > TOL) {
      let preview = "";
      let title = "";
      if (el.tagName === "IMG") {
        preview = el.getAttribute("src") || el.getAttribute("alt") || "";
      } else {
        preview = (el.textContent || "").trim().slice(0, 80);
      }
      const sec = el.closest("section");
      if (sec) {
        const tEl = sec.querySelector(".section-bar");
        title = tEl ? tEl.textContent.trim() : "";
      }
      clipped.push({
        region,
        tag: el.tagName.toLowerCase(),
        section_title: title,
        preview,
        bottom_overflow_px: bot,
        right_overflow_px: right,
      });
    }
  }

  // 1) Flow content — strict bounds (catches content bleeding past columns).
  // table.poster-table is included so a too-tall booktabs table clipped
  // below the flow bottom shows up in the report; Step 5.5's refinement
  // LLM uses this to trim the corresponding section's prose or table.
  flow.querySelectorAll(
    ".section-bar, .section-body p, .img-section, .img-section img, .section-body table.poster-table"
  ).forEach((el) => record(el, fr, "flow"));

  // 2) Header content — checked against the outer .poster
  poster.querySelectorAll(
    ".title, .authors, .venue, .logo-affiliation img, .logo-conference img"
  ).forEach((el) => record(el, pr, "header"));

  return {
    ok: clipped.length === 0,
    clipped,
    flow: { width: Math.round(fr.width), height: Math.round(fr.height) },
    poster: { width: Math.round(pr.width), height: Math.round(pr.height) },
  };
}
"""


def check_overflow(
    html_path: Path,
    output_json_path: Optional[Path] = None,
) -> dict:
    """Query the rendered DOM for clipped content. Returns a structured
    report; optionally writes it as JSON alongside the HTML.

    Requires Playwright + Chromium for the DOM query. If Playwright is
    unavailable, returns a degraded report with a warning.

    Report schema:
      { ok: bool,
        clipped: [ { tag, section_title, preview,
                     bottom_overflow_px, right_overflow_px }, ... ],
        flow: { width, height } | null }
    """
    if not html_path.is_file():
        raise FileNotFoundError(f"poster HTML not found: {html_path}")

    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import]
    except ImportError:
        # No probe ran — explicitly NOT clean. Returning ok=True here would
        # let Step 5.5 declare convergence on a poster that may still have
        # clipping. Callers must treat `degraded: true` as "fall back to
        # LLM visual evaluation", not "everything's fine."
        report = {
            "ok": False,
            "degraded": True,
            "clipped": [],
            "flow": None,
            "error": (
                "Playwright not installed; overflow check could not run. "
                "Install with `pip install playwright && python -m "
                "playwright install chromium` to enable. /poster Step 5.5 "
                "should fall back to LLM-only visual evaluation."
            ),
        }
        if output_json_path:
            output_json_path.parent.mkdir(parents=True, exist_ok=True)
            output_json_path.write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
        return report

    w, h = _parse_dims(html_path)
    html_uri = "file://" + str(html_path.resolve())

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, args=["--disable-dev-shm-usage"]
        )
        # Use device_scale_factor=1 — the report is in CSS pixels regardless
        context = browser.new_context(
            viewport={"width": w, "height": h}, device_scale_factor=1
        )
        page = context.new_page()
        page.goto(html_uri, wait_until="domcontentloaded")
        page.wait_for_selector("#flow", state="attached", timeout=30_000)
        try:
            page.evaluate(
                "() => document.fonts ? document.fonts.ready : Promise.resolve()"
            )
        except Exception:
            pass
        # Wait for images, then fit-stable (same as render — must measure
        # the converged state, not a mid-fit intermediate)
        # Wait for EVERY <img> inside .poster (header logos included), not
        # just `#flow` images. Header logos load via inject-header and can
        # finish after #flow images — without this, the screenshot or
        # overflow probe may fire before logo bitmaps land and miss
        # header clipping or render blank logo slots.
        page.evaluate(r"""
        () => {
          const poster = document.querySelector(".poster");
          if (!poster) return Promise.resolve();
          const imgs = Array.from(poster.querySelectorAll("img"));
          if (imgs.length === 0) return Promise.resolve();
          return Promise.all(imgs.map(img => {
            if (img.complete) return Promise.resolve();
            return new Promise(res => {
              img.addEventListener("load",  res, { once: true });
              img.addEventListener("error", res, { once: true });
            });
          }));
        }
        """)
        page.evaluate(r"""
        () => new Promise((resolve) => {
          const flow = document.getElementById("flow");
          if (!flow) return resolve();
          let last = -1, stable = 0;
          function tick() {
            const cur = flow.scrollWidth;
            if (cur === last) stable += 1; else stable = 0;
            last = cur;
            if (stable >= 10) return resolve();
            requestAnimationFrame(tick);
          }
          tick();
        })
        """)
        report = page.evaluate(_OVERFLOW_PROBE_JS)
        browser.close()

    if output_json_path:
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
    return report


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
        authors_override=args.authors,
    )
    print(f"[ok] title + authors injected into {args.poster}")
    return 0


def cmd_inject_header(args) -> int:
    aff = Path(args.affiliation_logo).resolve() if args.affiliation_logo else None
    conf = Path(args.conference_logo).resolve() if args.conference_logo else None
    report = inject_header(
        Path(args.poster).resolve(),
        venue=args.venue,
        affiliation_logo=aff,
        conference_logo=conf,
        layout=args.layout,
    )
    print(f"[ok] header injected into {args.poster}")
    print(f"  layout:      {report['layout']}")
    print(f"  venue:       {report['venue'] or '(none)'}")
    print(f"  affiliation: {report['affiliation_logo'] or '(none)'}")
    print(f"  conference:  {report['conference_logo'] or '(none)'}")
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


def cmd_check_overflow(args) -> int:
    html = Path(args.html).resolve()
    json_path = (
        Path(args.output).resolve()
        if args.output
        else html.with_suffix(".overflow.json")
    )
    try:
        report = check_overflow(html, json_path)
    except FileNotFoundError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1
    if report.get("degraded"):
        # Probe could not run (e.g. Playwright not installed). Exit nonzero
        # so the calling pipeline does NOT treat absence of clipping as
        # convergence — Step 5.5 should fall back to LLM visual evaluation.
        print(f"[degraded] {json_path}")
        err = report.get("error") or report.get("warning") or "probe unavailable"
        print(f"[error] {err}", file=sys.stderr)
        return 2
    print(f"[{'ok' if report.get('ok') else 'fail'}] {json_path}")
    if not report.get("ok"):
        for item in report.get("clipped", []):
            region = item.get("region", "flow")
            print(
                f"  clipped [{region}]: {item['tag']:8s} "
                f"'{item['section_title'][:40]}' "
                f"bot+{item['bottom_overflow_px']}px "
                f"right+{item['right_overflow_px']}px "
                f"({item['preview'][:60]})",
                file=sys.stderr,
            )
        return 1
    if "warning" in report:
        print(f"[warn] {report['warning']}", file=sys.stderr)
    return 0


def cmd_render(args) -> int:
    html = Path(args.html).resolve()
    output = Path(args.output).resolve() if args.output else None
    try:
        out, browser_type, eff_scale = render_poster(
            html, output, scale=args.scale
        )
    except FileNotFoundError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else "(no stderr)"
        print(f"[error] browser exited with code {e.returncode}", file=sys.stderr)
        print(stderr, file=sys.stderr)
        return 1
    w, h = _parse_dims(html)
    print(f"[ok] poster rendered to {out}")
    print(
        f"  browser: {browser_type}\n"
        f"  dims: {w}x{h} CSS px, "
        f"{w * eff_scale}x{h * eff_scale} actual px (scale={eff_scale})"
    )
    return 0


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
    p_title.add_argument(
        "--authors",
        default=None,
        help="Override authors text (e.g. 'Morrow Yang, Co-Author'). "
        "Ignored when --anonymous is set.",
    )
    p_title.set_defaults(func=cmd_inject_title)

    p_header = sub.add_parser(
        "inject-header",
        help="Set venue text + optional affiliation/conference logos",
    )
    p_header.add_argument("poster", help="Path to poster.html (in-place edit)")
    p_header.add_argument(
        "--venue", default=None, help="Venue text (e.g. 'NeurIPS 2026'); omit for blank"
    )
    p_header.add_argument(
        "--affiliation-logo",
        default=None,
        help="Path to affiliation logo (PNG/JPG/PDF); copied to poster_dir/images/",
    )
    p_header.add_argument(
        "--conference-logo",
        default=None,
        help="Path to conference logo (PNG/JPG/PDF); copied to poster_dir/images/",
    )
    p_header.add_argument(
        "--layout",
        choices=SUPPORTED_LAYOUTS,
        default="corners",
        help="Header layout: 'corners' (affiliation left, conference right) "
        "or 'stacked' (both logos in conf area, venue text on top)",
    )
    p_header.set_defaults(func=cmd_inject_header)

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

    p_chk = sub.add_parser(
        "check-overflow",
        help="Query rendered DOM for clipped content (Playwright); "
        "writes a JSON report. Used by /poster Step 5.5.",
    )
    p_chk.add_argument("html", help="Path to poster.html")
    p_chk.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: <html>.overflow.json)",
    )
    p_chk.set_defaults(func=cmd_check_overflow)

    p_render = sub.add_parser(
        "render",
        help="Render HTML poster to PNG via headless Chrome",
    )
    p_render.add_argument("html", help="Path to poster.html")
    p_render.add_argument(
        "--output",
        default=None,
        help="Output PNG path (default: alongside HTML with .png extension)",
    )
    p_render.add_argument(
        "--scale",
        type=int,
        choices=(1, 2, 3),
        default=2,
        help="Device scale factor: 1=fast preview, 2=default (HiDPI), 3=print",
    )
    p_render.set_defaults(func=cmd_render)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
