#!/usr/bin/env python3
"""Local HTTP server for the OmegaWiki standalone frontend.

Serves (read):
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

Serves (write — Phase 4; loopback-only):
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
                                            open-questions, visualize}
                                       -> research_wiki.py rebuild-* /
                                          tools/visualize.py generate-*

  POST  /api/intent/{skill}           body context for command synthesis
                                       skill ∈ {ingest, ask, edit, check,
                                                ideate, discover, exp-design}
                                       -> {skill, command, doc_url, message}
                                       (returns guidance only — does not
                                       execute /skill; SPA has no LLM
                                       session)

Run:
  python tools/serve.py [--host 127.0.0.1] [--port 8765]

Phase 0+1+3+4 of docs/frontend-design.md. Stdlib only.
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

sys.path.insert(0, str(ROOT))
from runtime.loader import ENTITY_DIRS  # noqa: E402

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", re.DOTALL)
ENTITY_PATH_RE = re.compile(
    r"^/api/entities/([^/]+)(?:/([^/]+)(?:/(raw))?)?/?$"
)
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
        citations = self._read_jsonl(GRAPH_DIR / "citations.jsonl")
        self._send_json({"edges": edges, "citations": citations})

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
        from_claim = (body.get("from_claim") or "").strip()
        if from_claim:
            return {"command": f"/ideate --from-claim {from_claim}"}
        return {"command": "/ideate"}

    @staticmethod
    def _intent_discover(body: dict) -> dict:
        anchor = (body.get("anchor") or "").strip()
        if anchor:
            return {"command": f"/discover --anchor {anchor}"}
        return {
            "command": "/discover --anchor <arxiv-id-or-paper-slug>",
            "message": "Pass an arXiv ID (e.g. 1706.03762) or a paper slug.",
        }

    @staticmethod
    def _intent_exp_design(body: dict) -> dict:
        claim = (body.get("target_claim") or "").strip()
        if claim:
            return {"command": f"/exp-design --target-claim {claim}"}
        return {
            "command": "/exp-design --target-claim <claim-slug>",
            "message": "Run from a claim page or pass --target-claim explicitly.",
        }

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
