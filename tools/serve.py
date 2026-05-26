#!/usr/bin/env python3
"""Local HTTP server for the OmegaWiki standalone frontend.

ThreadingHTTPServer (stdlib only, no pip dependency). Binds to 127.0.0.1.
Serves the SPA in `app/` plus a JSON API + SSE live-reload stream.

Read endpoints (Cache-Control: no-store):
  /                              -> app/index.html
  /<file>                        -> app/<file>          (static)
  GET   /api/health              -> hello-world JSON
  GET   /api/stats               -> research_wiki.py stats --json
  GET   /api/maturity            -> research_wiki.py maturity --json
  GET   /api/entities/{type}     -> array of full frontmatter
  GET   /api/entities/{type}/{slug} -> {frontmatter_yaml, body}
  GET   /api/entities/{type}/{slug}/raw -> raw markdown
  GET   /api/graph               -> {edges, citations}
  GET   /api/open-questions      -> raw markdown of wiki/graph/open_questions.md
  GET   /api/log?tail=N          -> parsed entries from wiki/log.md
  GET   /api/events              -> SSE stream of `change` events (see below)

Write endpoints (loopback-only; every successful write appends a
"## [date] frontend | <verb> <subject>" line to wiki/log.md so /check
and other skills can distinguish SPA-originated edits):
  PATCH /api/entities/{type}/{slug}   body {field, value, append?}
                                       -> research_wiki.py set-meta
  POST  /api/edges                    body {from, to, type, evidence?,
                                            confidence?, symmetric?}
                                       -> research_wiki.py add-edge
  POST  /api/citations                body {from, to, source?}
                                       -> research_wiki.py add-citation
  POST  /api/log                      body {message}
                                       -> research_wiki.py log
  POST  /api/regenerate/{kind}        kind ∈ {index, context-brief,
                                              open-questions}
                                       -> research_wiki.py rebuild-*

  POST  /api/intent/{skill}           body context for command synthesis
                                       skill ∈ {ingest, ask, edit, check,
                                                ideate, discover, exp-design}
                                       -> {skill, command, doc_url, message}

Skill-intent boundary
---------------------
The SPA cannot run /skill X — slash-commands need a Claude Code LLM
session. Naive UX would silently call a different code path and produce
results that diverge from /skill X's actual behavior. So every UI button
that wants a skill posts to /api/intent/{skill}; the backend assembles
the right "/skill ..." command (filling in slug/arxiv-id/etc. from page
context) and returns it. The SPA opens a copy-to-clipboard modal with the
command. The user pastes it into Claude Code. The boundary is explicit
in the API surface itself — no silent skill faking.

Live reload (SSE)
-----------------
A background thread polls every file under wiki/ for mtime changes every
1.5s. On any change, broadcasts `event: change\\ndata: {paths: [...]}`
to all connected /api/events clients. The SPA's EventSource listener
refetches data and re-renders the current view. A 2.5s grace window
after each SPA-initiated write suppresses redundant re-renders triggered
by the SPA's own write — state.lastWriteAt is consulted before
re-rendering. External edits (Obsidian, Claude Code editing wiki/* during
a running ingest, manual research_wiki.py invocations) all reflect in the
SPA within ~1.5 seconds with no manual refresh.

Run:
  python tools/serve.py [--host 127.0.0.1] [--port 8765]

Smoke test:
  curl http://127.0.0.1:8765/api/health    -> {"status":"ok","phase":4}
  curl http://127.0.0.1:8765/api/stats     -> entity counts (must match
                                              `python tools/research_wiki.py
                                              stats wiki/ --json`)
  Browser: open /, navigate to #/reader/papers/<slug>, #/graph,
           #/dashboard. Edit a tag in Reader -> `git diff wiki/...` shows
           the change -> wiki/log.md has a new "frontend | PATCH..." line.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = ROOT / "app"
WIKI_ROOT = ROOT / "wiki"
GRAPH_DIR = WIKI_ROOT / "graph"
CHECKPOINTS_DIR = ROOT / ".checkpoints"

sys.path.insert(0, str(ROOT))
from runtime.loader import ENTITY_DIRS, EDGE_TYPE_SPECS  # noqa: E402
from tools import research_wiki as _research_wiki  # noqa: E402  for graph projection

try:
    import json as _json_for_config
    _VISUALIZE_CFG = _json_for_config.loads(
        (ROOT / "config" / "visualize.json").read_text(encoding="utf-8")
    )
except (OSError, ValueError):
    _VISUALIZE_CFG = {}

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", re.DOTALL)
ENTITY_PATH_RE = re.compile(
    r"^/api/entities/([^/]+)(?:/([^/]+)(?:/(raw))?)?/?$"
)
# /api/checkpoints/discover               -> list
# /api/checkpoints/discover/<name>        -> read one
# `name` must match the discover-* prefix; further validated against the
# filesystem so we never read anything outside .checkpoints/.
CHECKPOINT_NAME_RE = re.compile(r"^discover-[A-Za-z0-9._-]+\.json$")
LOG_ENTRY_RE = re.compile(
    r"^##\s*\[(\d{4}-\d{2}-\d{2})\]\s+([^|]+?)\s*\|\s*(.*)$"
)


def _python_bin() -> str:
    venv_unix = ROOT / ".venv" / "bin" / "python"
    venv_win = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_unix.exists():
        return str(venv_unix)
    if venv_win.exists():
        return str(venv_win)
    return sys.executable


def _run_research_wiki(*args: str) -> str:
    cmd = [_python_bin(), str(ROOT / "tools" / "research_wiki.py"), *args]
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        cmd, capture_output=True, text=True, env=env, encoding="utf-8"
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"research_wiki.py {' '.join(args)} failed "
            f"(exit {result.returncode}):\n{result.stderr}"
        )
    return result.stdout


def _audit_log(message: str) -> None:
    """Append an audit entry to wiki/log.md. Best-effort — failures
    here must not break the underlying write that prompted the audit."""
    try:
        _run_research_wiki("log", str(WIKI_ROOT), f"frontend | {message}")
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"[audit-log] failed: {exc}\n")


def _run_visualize(*args: str) -> str:
    cmd = [_python_bin(), str(ROOT / "tools" / "visualize.py"), *args]
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        cmd, capture_output=True, text=True, env=env, encoding="utf-8"
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"visualize.py {' '.join(args)} failed "
            f"(exit {result.returncode}):\n{result.stderr}"
        )
    return result.stdout


def _run_lint(*args: str) -> str:
    """Run tools/lint.py and return its stdout. lint.py exits non-zero when
    issues are found, so callers should always pass `--json` and parse the
    result instead of relying on exit code."""
    cmd = [_python_bin(), str(ROOT / "tools" / "lint.py"), *args]
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        cmd, capture_output=True, text=True, env=env, encoding="utf-8"
    )
    # Don't treat non-zero exit as error — lint signals "issues found" that way.
    # The JSON output is what callers actually care about. We surface stderr
    # only if there's no parseable stdout.
    if not result.stdout.strip() and result.stderr.strip():
        raise RuntimeError(
            f"lint.py {' '.join(args)} produced no output "
            f"(exit {result.returncode}):\n{result.stderr}"
        )
    return result.stdout


# ---------------------------------------------------------------------------
# Live-reload via SSE (Server-Sent Events).
#
# A background thread polls wiki/ mtimes every WATCH_INTERVAL seconds and
# broadcasts a "change" event to every connected /api/events client. The
# SPA subscribes via EventSource and re-fetches its boot state on event.
#
# Stdlib only: uses threading + queue + os.walk + os.stat. No watchdog
# or platform-specific inotify/FSEvents — same code path on every OS.
# ---------------------------------------------------------------------------

WATCH_INTERVAL = 1.5  # seconds between scans
SSE_KEEPALIVE = 15.0  # seconds between keepalive comments per client

_watch_clients: set[queue.Queue] = set()
_watch_lock = threading.Lock()
_watch_started = False


def _snapshot_wiki() -> dict[str, float]:
    """Build a {abs_path: mtime} map of every regular file under wiki/.

    Skips dotted directories (.checkpoints, .obsidian) — those churn
    on visualize regen and would spam SSE events on every interaction.
    """
    snap = {}
    for root, dirs, files in os.walk(WIKI_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            p = os.path.join(root, fname)
            try:
                snap[p] = os.path.getmtime(p)
            except OSError:
                pass
    return snap


def _diff_snapshots(old: dict, new: dict) -> list[str]:
    changed = []
    for p, mt in new.items():
        if p not in old or old[p] != mt:
            changed.append(p)
    for p in old:
        if p not in new:
            changed.append(p)
    return changed


def _watch_loop() -> None:
    """Poll wiki/ forever; broadcast change events to SSE clients."""
    snapshot = _snapshot_wiki()
    while True:
        try:
            time.sleep(WATCH_INTERVAL)
            new_snap = _snapshot_wiki()
            changed = _diff_snapshots(snapshot, new_snap)
            if changed:
                # cap path list at 20 so payload is small
                payload = json.dumps({
                    "type": "wiki-change",
                    "count": len(changed),
                    "paths": [
                        os.path.relpath(p, ROOT).replace("\\", "/")
                        for p in changed[:20]
                    ],
                    "ts": int(time.time() * 1000),
                })
                with _watch_lock:
                    targets = list(_watch_clients)
                for q in targets:
                    try:
                        q.put_nowait(payload)
                    except queue.Full:
                        # slow client; drop event silently
                        pass
            snapshot = new_snap
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[watch] error: {exc}\n")
            time.sleep(WATCH_INTERVAL)


def _ensure_watcher() -> None:
    global _watch_started
    with _watch_lock:
        if _watch_started:
            return
        _watch_started = True
    t = threading.Thread(target=_watch_loop, daemon=True, name="wiki-watch")
    t.start()


class WikiHandler(SimpleHTTPRequestHandler):
    """Serves app/ as static, plus /api/ endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_ROOT), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(
            f"[{self.log_date_time_string()}] {fmt % args}\n"
        )

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self._dispatch_api_get(path)
            return
        super().do_GET()

    def end_headers(self) -> None:
        # Force browsers to revalidate every static request (SPA modules,
        # CSS, HTML). ES modules are normally aggressively cached by URL,
        # which silently breaks the page after a frontend edit if some
        # modules are fresh and some are stale. `/api/*` responses set
        # their own no-store via _send_json / _send_raw, and the SSE
        # handler sets no-cache,no-store explicitly — those paths reach
        # this method with the header already present, so adding it once
        # more is harmless (or already handled).
        # The check here only fires on the static-file path (super().do_GET()).
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    # --- Phase 4 write methods ----------------------------------------------

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            self._send_json({"error": "POST only on /api/*"}, status=405)
            return
        body = self._read_json_body()
        if "_parse_error" in body:
            self._send_json({"error": f"bad JSON body: {body['_parse_error']}"}, status=400)
            return
        if path == "/api/edges":
            self._handle_post_edge(body)
            return
        if path == "/api/citations":
            self._handle_post_citation(body)
            return
        if path == "/api/log":
            self._handle_post_log(body)
            return
        if path.startswith("/api/regenerate/"):
            kind = path[len("/api/regenerate/"):]
            self._handle_regenerate(kind)
            return
        if path == "/api/lint/fix":
            dry_run = bool(body.get("dry_run", False))
            self._handle_lint(fix=True, dry_run=dry_run)
            return
        if path.startswith("/api/intent/"):
            skill = path[len("/api/intent/"):]
            self._handle_intent(skill, body)
            return
        self._send_json({"error": f"unknown POST endpoint: {path}"}, status=404)

    def do_PATCH(self) -> None:
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            self._send_json({"error": "PATCH only on /api/*"}, status=405)
            return
        body = self._read_json_body()
        if "_parse_error" in body:
            self._send_json({"error": f"bad JSON body: {body['_parse_error']}"}, status=400)
            return
        m = ENTITY_PATH_RE.match(path)
        # Refuse PATCH on .../raw — those are read-only
        if m and not m.group(3):
            self._handle_patch_entity(m.group(1), m.group(2), body)
            return
        self._send_json({"error": f"unknown PATCH endpoint: {path}"}, status=404)

    def _read_json_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except ValueError:
            length = 0
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        if not raw.strip():
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            return {"_parse_error": str(exc)}
        if not isinstance(data, dict):
            return {"_parse_error": "JSON body must be an object"}
        return data

    def _dispatch_api_get(self, path: str) -> None:
        if path == "/api/events":
            self._handle_sse()
            return
        if path == "/api/health":
            self._send_json({"status": "ok", "phase": 4})
            return
        if path == "/api/stats":
            try:
                stdout = _run_research_wiki("stats", str(WIKI_ROOT), "--json")
                self._send_raw(
                    stdout, content_type="application/json; charset=utf-8"
                )
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return
        if path == "/api/maturity":
            try:
                stdout = _run_research_wiki("maturity", str(WIKI_ROOT), "--json")
                self._send_raw(
                    stdout, content_type="application/json; charset=utf-8"
                )
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return
        if path == "/api/lint":
            self._handle_lint(fix=False)
            return
        if path == "/api/checkpoints/discover":
            self._handle_checkpoints_list()
            return
        if path.startswith("/api/checkpoints/discover/"):
            name = path[len("/api/checkpoints/discover/"):]
            self._handle_checkpoint_read(name)
            return
        if path == "/api/graph":
            self._handle_graph()
            return
        if path == "/api/open-questions":
            self._handle_open_questions()
            return
        if path == "/api/log":
            tail = self._query_int("tail", default=200, max_value=2000)
            self._handle_log(tail=tail)
            return
        m = ENTITY_PATH_RE.match(path)
        if m:
            etype, slug, raw = m.group(1), m.group(2), m.group(3)
            self._handle_entities(etype, slug, raw == "raw")
            return
        self._send_json(
            {"error": f"unknown endpoint: {path}"}, status=404
        )

    # --- query-string helper -------------------------------------------------

    def _query_int(self, key: str, default: int, max_value: int) -> int:
        from urllib.parse import parse_qs
        qs = parse_qs(urlparse(self.path).query)
        raw = qs.get(key, [None])[0]
        if raw is None:
            return default
        try:
            v = int(raw)
        except ValueError:
            return default
        return max(1, min(v, max_value))

    # --- entity endpoints ----------------------------------------------------

    def _handle_entities(
        self, etype: str, slug: str | None, want_raw: bool
    ) -> None:
        if etype not in ENTITY_DIRS:
            self._send_json(
                {"error": f"unknown entity type: {etype}"}, status=400
            )
            return
        if slug is None:
            # GET /api/entities/{type}
            try:
                stdout = _run_research_wiki("find", str(WIKI_ROOT), etype)
                self._send_raw(
                    stdout, content_type="application/json; charset=utf-8"
                )
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return
        # GET /api/entities/{type}/{slug}[/raw]
        if not SLUG_RE.match(slug):
            self._send_json({"error": f"invalid slug: {slug}"}, status=400)
            return
        path = WIKI_ROOT / etype / f"{slug}.md"
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._send_json(
                {"error": f"not found: {etype}/{slug}"}, status=404
            )
            return
        except OSError as exc:
            self._send_json({"error": str(exc)}, status=500)
            return
        if want_raw:
            self._send_raw(
                text, content_type="text/markdown; charset=utf-8"
            )
            return
        m = FRONTMATTER_RE.match(text)
        if m:
            fm_yaml, body = m.group(1), m.group(2)
        else:
            fm_yaml, body = "", text
        self._send_json(
            {"slug": slug, "type": etype, "frontmatter_yaml": fm_yaml, "body": body}
        )

    # --- graph endpoint ------------------------------------------------------

    def _handle_graph(self) -> None:
        edges = self._read_jsonl(GRAPH_DIR / "edges.jsonl")
        for e in edges:
            # Stash whatever "source" might already mean per-row (rare on
            # edges.jsonl today, but reserved for future) so we can label
            # provenance buckets unambiguously.
            if "source" in e:
                e.setdefault("source_attr", e["source"])
            e["source"] = "edges.jsonl"
        citations = self._read_jsonl(GRAPH_DIR / "citations.jsonl")
        for c in citations:
            # citations.jsonl rows carry source: semantic_scholar|parsed_bib|manual
            # which is the *citation provenance*, not the payload bucket. Move it
            # aside so the unified `source` field cleanly labels the bucket.
            if "source" in c:
                c["cite_source"] = c.pop("source")
            c["source"] = "citations.jsonl"
            c.setdefault("type", "cites")
        try:
            projected = _research_wiki.project_frontmatter_edges(WIKI_ROOT)
        except Exception as exc:  # noqa: BLE001 — projection must never fail the graph endpoint
            print(f"WARN: frontmatter projection failed: {exc}", file=sys.stderr)
            projected = []
        self._send_json({
            "edges": edges + projected,
            "citations": citations,
            "schema": self._emit_minimal_schema(),
        })

    @staticmethod
    def _emit_minimal_schema() -> dict:
        """Edge metadata the frontend needs to render arrows / groups without
        hardcoding a parallel copy of runtime/schema/edges.yaml."""
        edge_types = {
            et: {"direction": spec.get("direction"),
                 "workflow":  spec.get("workflow")}
            for et, spec in EDGE_TYPE_SPECS.items()
        }
        # `cites` is excluded from EDGE_TYPE_SPECS per loader convention; add it.
        edge_types["cites"] = {"direction": "directed", "workflow": "citation"}
        return {
            "edge_types": edge_types,
            "edge_workflow_colors": _VISUALIZE_CFG.get("edge_workflow_colors", {}),
            "edge_category_groups": _VISUALIZE_CFG.get("edge_category_groups", {}),
            "entity_colors": {
                k: v.get("hex") for k, v in
                _VISUALIZE_CFG.get("entity_colors", {}).items()
            },
        }

    @staticmethod
    def _read_jsonl(path: Path) -> list:
        if not path.exists():
            return []
        rows = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    # skip malformed; do not fail the whole endpoint
                    continue
        return rows

    # --- /api/open-questions -------------------------------------------------

    def _handle_open_questions(self) -> None:
        path = GRAPH_DIR / "open_questions.md"
        if not path.exists():
            self._send_raw("# Gap Map\n\n_(no open_questions.md yet)_\n",
                           content_type="text/markdown; charset=utf-8")
            return
        try:
            self._send_raw(
                path.read_text(encoding="utf-8"),
                content_type="text/markdown; charset=utf-8",
            )
        except OSError as exc:
            self._send_json({"error": str(exc)}, status=500)

    # --- /api/entities/{type}/{slug} PATCH (set-meta) ------------------------

    def _handle_patch_entity(self, etype: str, slug: str, body: dict) -> None:
        if etype not in ENTITY_DIRS:
            self._send_json({"error": f"unknown entity type: {etype}"}, status=400)
            return
        if not SLUG_RE.match(slug):
            self._send_json({"error": f"invalid slug: {slug}"}, status=400)
            return
        path = WIKI_ROOT / etype / f"{slug}.md"
        if not path.exists():
            self._send_json({"error": f"not found: {etype}/{slug}"}, status=404)
            return
        field = body.get("field")
        value = body.get("value")
        append = bool(body.get("append", False))
        if not field or not isinstance(field, str):
            self._send_json({"error": "missing string `field`"}, status=400)
            return
        if value is None:
            self._send_json({"error": "missing `value`"}, status=400)
            return
        # Coerce non-string scalars to string for set-meta CLI. Lists with
        # --append are applied one item at a time; lists without --append
        # are not supported (set-meta is single-value).
        if isinstance(value, list):
            if not append:
                self._send_json(
                    {"error": "list value requires append=true (single set-meta call is single-value)"},
                    status=400,
                )
                return
            applied = []
            errors = []
            for item in value:
                v = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                try:
                    out = _run_research_wiki("set-meta", str(path), field, v, "--append")
                    applied.append({"value": v, "stdout": out.strip()})
                except RuntimeError as exc:
                    errors.append({"value": v, "error": str(exc)})
            if applied:
                _audit_log(
                    f"PATCH set-meta {etype}/{slug} {field}+={','.join(a['value'] for a in applied)}"
                )
            self._send_json({"applied": applied, "errors": errors},
                            status=200 if not errors else 207)
            return
        v = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        args = ["set-meta", str(path), field, v]
        if append:
            args.append("--append")
        try:
            out = _run_research_wiki(*args)
            verb = "+=" if append else "="
            _audit_log(f"PATCH set-meta {etype}/{slug} {field}{verb}{v}")
            self._send_raw(out, content_type="application/json; charset=utf-8")
        except RuntimeError as exc:
            self._send_json({"error": str(exc)}, status=500)

    # --- /api/edges POST (add-edge) ------------------------------------------

    def _handle_post_edge(self, body: dict) -> None:
        f = body.get("from"); t = body.get("to"); etype = body.get("type")
        if not (f and t and etype):
            self._send_json({"error": "missing one of {from, to, type}"}, status=400)
            return
        args = ["add-edge", str(WIKI_ROOT),
                "--from", str(f), "--to", str(t), "--type", str(etype)]
        if body.get("evidence"):
            args += ["--evidence", str(body["evidence"])]
        if body.get("confidence"):
            args += ["--confidence", str(body["confidence"])]
        if body.get("symmetric"):
            args += ["--symmetric"]
        try:
            out = _run_research_wiki(*args)
            _audit_log(f"POST add-edge {f} --{etype}--> {t}")
            self._send_raw(out, content_type="application/json; charset=utf-8")
        except RuntimeError as exc:
            self._send_json({"error": str(exc)}, status=500)

    # --- /api/citations POST (add-citation) ----------------------------------

    def _handle_post_citation(self, body: dict) -> None:
        f = body.get("from"); t = body.get("to")
        if not (f and t):
            self._send_json({"error": "missing one of {from, to}"}, status=400)
            return
        args = ["add-citation", str(WIKI_ROOT), "--from", str(f), "--to", str(t)]
        src = body.get("source")
        if src:
            args += ["--source", str(src)]
        try:
            out = _run_research_wiki(*args)
            _audit_log(f"POST add-citation {f} --cites--> {t}" + (f" (source={src})" if src else ""))
            self._send_raw(out, content_type="application/json; charset=utf-8")
        except RuntimeError as exc:
            self._send_json({"error": str(exc)}, status=500)

    # --- /api/log POST (log) -------------------------------------------------

    def _handle_post_log(self, body: dict) -> None:
        msg = body.get("message")
        if not msg or not isinstance(msg, str):
            self._send_json({"error": "missing string `message`"}, status=400)
            return
        try:
            out = _run_research_wiki("log", str(WIKI_ROOT), msg)
            self._send_raw(out, content_type="application/json; charset=utf-8")
        except RuntimeError as exc:
            self._send_json({"error": str(exc)}, status=500)

    # --- /api/regenerate/{kind} POST ----------------------------------------

    REGENERATE_KINDS = {
        "index":              ("research_wiki", ["rebuild-index"]),
        "context-brief":      ("research_wiki", ["rebuild-context-brief"]),
        "open-questions":     ("research_wiki", ["rebuild-open-questions"]),
        "visualize":          ("visualize",     ["generate-obsidian-config",
                                                 "generate-canvas"]),
    }

    def _handle_regenerate(self, kind: str) -> None:
        spec = self.REGENERATE_KINDS.get(kind)
        if not spec:
            self._send_json(
                {"error": f"unknown regenerate kind: {kind}",
                 "valid": sorted(self.REGENERATE_KINDS.keys())},
                status=400,
            )
            return
        tool, subcmds = spec
        results = []
        for sub in subcmds:
            try:
                if tool == "research_wiki":
                    out = _run_research_wiki(sub, str(WIKI_ROOT))
                else:
                    out = _run_visualize(sub, str(WIKI_ROOT))
                results.append({"step": sub, "ok": True, "stdout": out.strip()})
            except RuntimeError as exc:
                results.append({"step": sub, "ok": False, "error": str(exc)})
        all_ok = all(r["ok"] for r in results)
        if all_ok:
            _audit_log(f"POST regenerate {kind}")
        self._send_json({"kind": kind, "ok": all_ok, "steps": results},
                        status=200 if all_ok else 500)

    # --- /api/events (SSE live-reload) --------------------------------------

    def _handle_sse(self) -> None:
        _ensure_watcher()
        q: queue.Queue = queue.Queue(maxsize=64)
        with _watch_lock:
            _watch_clients.add(q)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.send_header("Connection", "keep-alive")
            # Disable proxy buffering (in case anyone fronts this server later)
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            self._sse_write(": connected\n\n")
            while True:
                try:
                    payload = q.get(timeout=SSE_KEEPALIVE)
                except queue.Empty:
                    self._sse_write(": keepalive\n\n")
                    continue
                self._sse_write(f"event: change\ndata: {payload}\n\n")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # client disconnected; cleanup happens in finally
        finally:
            with _watch_lock:
                _watch_clients.discard(q)

    def _sse_write(self, s: str) -> None:
        self.wfile.write(s.encode("utf-8"))
        self.wfile.flush()

    # --- /api/intent/{skill} POST -------------------------------------------
    #
    # These return ready-to-paste `/skill ...` command strings. They do NOT
    # execute the skill (the SPA has no LLM session). The frontend shows
    # the command in a copy-to-clipboard modal; user pastes into Claude Code.

    INTENT_DEFAULT_MESSAGE = (
        "Run this in Claude Code. The SPA cannot orchestrate /skill — "
        "skills require an LLM session."
    )

    def _handle_intent(self, skill: str, body: dict) -> None:
        builders = {
            "ingest":     self._intent_ingest,
            "ask":        self._intent_ask,
            "edit":       self._intent_edit,
            "check":      self._intent_check,
            "ideate":     self._intent_ideate,
            "discover":   self._intent_discover,
            "exp-design": self._intent_exp_design,
        }
        b = builders.get(skill)
        if not b:
            self._send_json(
                {"error": f"unknown skill intent: {skill}",
                 "valid": sorted(builders.keys())},
                status=400,
            )
            return
        out = b(body)
        out.setdefault("skill", skill)
        out.setdefault("doc_url", f".claude/skills/{skill}/SKILL.md")
        out.setdefault("message", self.INTENT_DEFAULT_MESSAGE)
        self._send_json(out)

    @staticmethod
    def _intent_ingest(body: dict) -> dict:
        path = (body.get("path") or "").strip()
        if path:
            return {"command": f"/ingest {path}"}
        return {
            "command": "/ingest <local-path-or-arXiv-URL>",
            "message": ("Replace <local-path-or-arXiv-URL> with a "
                        ".pdf path, .tex path, or arXiv link, then run in "
                        "Claude Code."),
        }

    @staticmethod
    def _intent_ask(body: dict) -> dict:
        q = (body.get("question") or "").strip()
        if q:
            return {"command": f"/ask {q}"}
        return {"command": "/ask <your-question>"}

    @staticmethod
    def _intent_edit(body: dict) -> dict:
        intent = (body.get("intent") or "").strip()
        slug = (body.get("slug") or "").strip()
        etype = (body.get("type") or "").strip()
        if intent:
            return {"command": f"/edit {intent}"}
        if etype and slug:
            return {
                "command": f"/edit <natural-language-edit-for-{etype}/{slug}>",
                "message": ("Replace the placeholder with what you want to "
                            f"change on {etype}/{slug} in plain English."),
            }
        return {"command": "/edit <natural-language-intent>"}

    @staticmethod
    def _intent_check(body: dict) -> dict:
        return {"command": "/check"}

    @staticmethod
    def _intent_ideate(body: dict) -> dict:
        # Concept and topic pages can seed an ideate run by passing the slug
        # under the matching key. Only one is honoured per call.
        from_concept = (body.get("from_concept") or "").strip()
        if from_concept:
            return {"command": f"/ideate --from-concept {from_concept}"}
        from_topic = (body.get("from_topic") or "").strip()
        if from_topic:
            return {"command": f"/ideate --from-topic {from_topic}"}
        return {"command": "/ideate"}

    @staticmethod
    def _intent_discover(body: dict) -> dict:
        # /discover has four seed modes (see .claude/skills/discover/SKILL.md).
        # Priority when multiple fields are present: anchor > topic > venue/year
        # > from-wiki. `--limit` is universal and tacks on at the end.
        anchor = (body.get("anchor") or "").strip()
        topic = (body.get("topic") or "").strip()
        venue = (body.get("venue") or "").strip()
        year = (body.get("year") or "").strip()
        limit = (body.get("limit") or "").strip()

        def _limit_suffix() -> str:
            if not limit:
                return ""
            try:
                int(limit)
            except ValueError:
                return ""
            return f" --limit {limit}"

        if anchor:
            return {"command": f"/discover --anchor {anchor}{_limit_suffix()}"}
        if topic:
            # Quote the topic so multi-word phrases survive shell tokenisation.
            return {"command": f'/discover --topic "{topic}"{_limit_suffix()}'}
        if venue and year:
            return {"command": f"/discover --venue {venue} --year {year}{_limit_suffix()}"}
        if venue or year:
            return {
                "command": "/discover --venue <slug> --year <int>",
                "message": "Venue mode needs both --venue and --year.",
            }
        # Nothing supplied → derive from current wiki state.
        return {
            "command": f"/discover --from-wiki{_limit_suffix()}",
            "message": ("from-wiki mode mines your current papers/concepts/"
                        "open-questions to suggest what to read next — good "
                        "default when you don't have a specific anchor."),
        }

    @staticmethod
    def _intent_exp_design(body: dict) -> dict:
        idea = (body.get("linked_idea") or "").strip()
        if idea:
            return {"command": f"/exp-design --linked-idea {idea}"}
        return {
            "command": "/exp-design --linked-idea <idea-slug>",
            "message": "Run from an idea page or pass --linked-idea explicitly.",
        }

    # --- /api/lint and /api/lint/fix ----------------------------------------
    #
    # `tools/lint.py` is the deterministic core of `/check`. It already
    # supports `--json` and `--fix` (with `--dry-run` for preview). Exposing
    # it here lets the SPA show lint results inline without going through
    # the intent → copy → paste → Claude Code round trip.

    def _handle_lint(self, fix: bool, dry_run: bool = False) -> None:
        args = ["--wiki-dir", str(WIKI_ROOT), "--json"]
        if fix:
            args.append("--fix")
            if dry_run:
                args.append("--dry-run")
        try:
            stdout = _run_lint(*args)
        except RuntimeError as exc:
            self._send_json({"error": str(exc)}, status=500)
            return
        # lint.py emits JSON; we forward it raw. Audit only when a real fix
        # (non-dry-run) was applied, mirroring the regenerate write-endpoints.
        if fix and not dry_run:
            _audit_log("POST lint --fix")
        self._send_raw(stdout, content_type="application/json; charset=utf-8")

    # --- /api/checkpoints/discover ------------------------------------------
    #
    # `/discover` writes `.checkpoints/discover-{seed}-{date}.json`. The SPA
    # cannot re-run `/discover` (LLM-bound), but it CAN browse already-written
    # checkpoints so the user can pick which candidates to ingest. List +
    # read are both safe read-only operations on a local-only directory.

    CHECKPOINT_MAX_BYTES = 2 * 1024 * 1024  # 2 MB cap on individual reads

    def _handle_checkpoints_list(self) -> None:
        if not CHECKPOINTS_DIR.is_dir():
            self._send_json({"checkpoints": []})
            return
        items = []
        for p in CHECKPOINTS_DIR.glob("discover-*.json"):
            try:
                st = p.stat()
            except OSError:
                continue
            items.append({
                "name": p.name,
                "size": st.st_size,
                "mtime": st.st_mtime,
            })
        items.sort(key=lambda x: x["mtime"], reverse=True)
        self._send_json({"checkpoints": items})

    def _handle_checkpoint_read(self, name: str) -> None:
        if not CHECKPOINT_NAME_RE.match(name):
            self._send_json(
                {"error": f"invalid checkpoint name: {name!r} "
                          "(must match discover-*.json)"},
                status=400,
            )
            return
        # Resolve and confirm the path stays inside CHECKPOINTS_DIR — defends
        # against any future regex weakness.
        path = (CHECKPOINTS_DIR / name).resolve()
        try:
            path.relative_to(CHECKPOINTS_DIR.resolve())
        except ValueError:
            self._send_json({"error": "path traversal rejected"}, status=400)
            return
        if not path.is_file():
            self._send_json({"error": f"checkpoint not found: {name}"}, status=404)
            return
        try:
            size = path.stat().st_size
        except OSError as exc:
            self._send_json({"error": str(exc)}, status=500)
            return
        if size > self.CHECKPOINT_MAX_BYTES:
            self._send_json(
                {"error": f"checkpoint too large ({size} bytes; cap "
                          f"{self.CHECKPOINT_MAX_BYTES})"},
                status=413,
            )
            return
        try:
            data = path.read_text(encoding="utf-8")
        except OSError as exc:
            self._send_json({"error": str(exc)}, status=500)
            return
        self._send_raw(data, content_type="application/json; charset=utf-8")

    # --- /api/log ------------------------------------------------------------

    def _handle_log(self, tail: int) -> None:
        """Return last `tail` parsed log entries as JSON.

        Entry format: ## [YYYY-MM-DD] skill | details
        """
        path = WIKI_ROOT / "log.md"
        if not path.exists():
            self._send_json({"entries": []})
            return
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            self._send_json({"error": str(exc)}, status=500)
            return
        entries = []
        for line in text.splitlines():
            m = LOG_ENTRY_RE.match(line)
            if m:
                entries.append({
                    "date": m.group(1),
                    "skill": m.group(2).strip(),
                    "details": m.group(3).strip(),
                })
        if tail and tail < len(entries):
            entries = entries[-tail:]
        self._send_json({"entries": entries, "total": len(entries)})

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_raw(
        self, body_str: str, content_type: str, status: int = 200
    ) -> None:
        body = body_str.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OmegaWiki local frontend server (Phase 1)"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if not APP_ROOT.exists():
        print(f"ERROR: app/ directory missing at {APP_ROOT}", file=sys.stderr)
        return 1

    server = ThreadingHTTPServer((args.host, args.port), WikiHandler)
    server.daemon_threads = True
    _ensure_watcher()
    base = f"http://{args.host}:{args.port}"
    print(f"OmegaWiki frontend serving at {base}")
    print(f"  static root  : {APP_ROOT}")
    print(f"  api/health   : {base}/api/health")
    print(f"  api/stats    : {base}/api/stats")
    print(f"  api/entities : {base}/api/entities/<type>[/<slug>[/raw]]")
    print(f"  api/graph    : {base}/api/graph")
    print(f"  api/events   : {base}/api/events  (SSE live-reload)")
    print(f"  watch        : {WIKI_ROOT}  (interval {WATCH_INTERVAL}s)")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    return 0


if __name__ == "__main__":
    sys.exit(main())
