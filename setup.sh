#!/usr/bin/env bash
set -euo pipefail

LANG_CODE=en
while [ "$#" -gt 0 ]; do
  case "$1" in
    --lang) LANG_CODE="${2:-}"; shift 2 ;;
    --lang=*) LANG_CODE="${1#*=}"; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
case "$LANG_CODE" in en|zh) ;; *) echo "Language must be en or zh" >&2; exit 2 ;; esac
ROOT="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$ROOT/i18n/$LANG_CODE"
cd "$ROOT"
say() { printf '[AutoSci] %s\n' "$*"; }

command -v python3 >/dev/null || { echo "Python 3.9+ is required" >&2; exit 1; }
python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 9))'
if command -v opencode >/dev/null; then say "OpenCode found: $(opencode --version 2>/dev/null || echo installed)"
else say "WARNING: OpenCode was not found; setup will still prepare the project."; fi

[ -d .venv ] || python3 -m venv .venv
VENV_PYTHON="$ROOT/.venv/bin/python"
"$VENV_PYTHON" -m pip install -q -r requirements.txt -r mcp-servers/llm-review/requirements.txt
[ -f .env ] || cp .env.example .env

# The bilingual i18n tree is authoritative. Rebuild to remove stale skills.
rm -rf .opencode/skills
mkdir -p .opencode/skills/shared-references
cp -R "$SOURCE/skills/"* .opencode/skills/
cp "$SOURCE/shared-references/"*.md .opencode/skills/shared-references/
cp "$SOURCE/AGENTS.md" AGENTS.md
printf '%s\n' "$LANG_CODE" > .opencode/.current-lang

PYTHON_PATH=$("$VENV_PYTHON" -c 'import os,sys; print(os.path.abspath(sys.executable))')
SERVER_PATH="$ROOT/mcp-servers/llm-review/server.py"
"$VENV_PYTHON" - "$PYTHON_PATH" "$SERVER_PATH" > opencode.json <<'PY'
import json, sys
python_path, server_path = sys.argv[1:]
print(json.dumps({
  "$schema": "https://opencode.ai/config.json",
  "mcp": {"llm-review": {"type": "local", "command": [python_path, server_path], "enabled": True}},
  "permission": {"skill": "allow", "task": "allow", "question": "allow", "websearch": "allow", "webfetch": "allow", "read": "allow", "glob": "allow", "grep": "allow", "list": "allow", "edit": "ask", "bash": "ask"}
}, indent=2))
PY

"$VENV_PYTHON" -c 'import fitz, requests, feedparser, httpx'
"$VENV_PYTHON" -m py_compile mcp-servers/llm-review/server.py tools/daily_arxiv.py
say "Installed language=$LANG_CODE. Start with: opencode"
say "Use the init skill to initialize the research wiki."
