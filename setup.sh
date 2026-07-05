#!/usr/bin/env bash
# ============================================================================
# AutoSci — One-Click Setup
# ============================================================================
# Usage:
#   chmod +x setup.sh && ./setup.sh            # English (default)
#   chmod +x setup.sh && ./setup.sh --lang zh  # Chinese / 中文
#
# What it does:
#   1. Checks prerequisites (Python, pip, Claude Code or Codex)
#   2. Creates virtual environment and installs dependencies
#   3. Copies configuration templates
#   4. Verifies the installation
#
# API key configuration (Semantic Scholar, DeepXiv, Review LLM) is handled
# interactively by your coding agent — run /setup in Claude Code or $setup in Codex.
# ============================================================================

set -e

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $1"; }

# Cross-platform sed -i (macOS BSD sed vs GNU sed)
_sed_i() {
  if [[ "$OSTYPE" == darwin* ]]; then
    sed -i '' "$@"
  else
    sed -i "$@"
  fi
}

# ── Language selection ──────────────────────────────────────────────
LANG_CODE="en"
_ARGS=("$@")
for i in "${!_ARGS[@]}"; do
  case "${_ARGS[$i]}" in
    --lang=*) LANG_CODE="${_ARGS[$i]#*=}" ;;
    --lang)   LANG_CODE="${_ARGS[$((i+1))]}" ;;
  esac
done
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
[[ "$LANG_CODE" == "en" || "$LANG_CODE" == "zh" ]] || { fail "Unknown lang: $LANG_CODE (use 'en' or 'zh')"; exit 1; }
I18N_DIR="$PROJECT_ROOT/i18n/$LANG_CODE"
[ -d "$I18N_DIR" ] || { fail "i18n/$LANG_CODE not found — run from the project root"; exit 1; }
cd "$PROJECT_ROOT"

echo ""
echo "============================================"
echo "  AutoSci — Setup"
echo "============================================"
echo ""

# ── Step 1: Check prerequisites ─────────────────────────────────────────

info "Checking prerequisites..."

# Python
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 9 ]; then
        ok "Python $PY_VERSION"
    else
        fail "Python >= 3.9 required, found $PY_VERSION"
        exit 1
    fi
else
    fail "Python3 not found. Install Python 3.9+ first."
    exit 1
fi

# pip
if "$PYTHON_CMD" -m pip --version &>/dev/null; then
    ok "pip available"
else
    fail "pip not found. Install with: $PYTHON_CMD -m ensurepip"
    exit 1
fi

# Coding agent runtime
HAVE_CLAUDE=0
HAVE_CODEX=0
if command -v claude &>/dev/null; then
    HAVE_CLAUDE=1
    ok "Claude Code installed"
else
    warn "Claude Code not found."
fi

if command -v codex &>/dev/null; then
    HAVE_CODEX=1
    ok "Codex installed"
else
    warn "Codex not found."
fi

if [ "$HAVE_CLAUDE" -eq 0 ] && [ "$HAVE_CODEX" -eq 0 ]; then
    echo ""
    echo "  Install at least one coding-agent runtime to use AutoSci skills:"
    echo "    npm install -g @anthropic-ai/claude-code"
    echo "    # or install Codex from your OpenAI/Codex setup path"
    echo ""
    read -p "  Continue setup without a coding agent? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "  Install Claude Code or Codex first, then re-run setup.sh"
        exit 1
    fi
fi

# ── Step 2: Python environment + dependencies ───────────────────────────

echo ""
info "Setting up Python environment..."

if [ -n "$VIRTUAL_ENV" ] || { [ -n "$CONDA_DEFAULT_ENV" ] && [ "$CONDA_DEFAULT_ENV" != "base" ]; }; then
    warn "Active environment detected; setup always installs AutoSci into .venv"
fi

if [ -d ".venv" ]; then
    warn ".venv already exists, using it"
else
    "$PYTHON_CMD" -m venv .venv
    ok "Created .venv"
fi

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
    fail "Expected $VENV_PYTHON but it does not exist"
    exit 1
fi
ok "Using $VENV_PYTHON"

info "Installing dependencies into .venv..."
"$VENV_PYTHON" -m pip install -r requirements.txt -q
ok "Dependencies installed into .venv"

# ── Step 3: Configuration files ─────────────────────────────────────────

echo ""
info "Setting up configuration..."

# .env
if [ -f ".env" ]; then
    warn ".env already exists, not overwriting"
else
    cp .env.example .env
    ok "Created .env from template"
fi

# Claude Code settings
mkdir -p .claude
if [ -f ".claude/settings.local.json" ]; then
    warn ".claude/settings.local.json already exists, not overwriting"
else
    cp config/settings.local.json.example .claude/settings.local.json
    ok "Created .claude/settings.local.json"
fi

# ── Step 3b: Activate language files ───────────────────────────────
echo ""
info "Activating language: $LANG_CODE"
cp "$I18N_DIR/CLAUDE.md" CLAUDE.md
if [ -f "$I18N_DIR/AGENTS.md" ]; then
    cp "$I18N_DIR/AGENTS.md" AGENTS.md
fi
for agent_skills_dir in ".claude/skills" ".agents/skills"; do
    mkdir -p "$agent_skills_dir"
    for skill_dir in "$I18N_DIR/skills"/*; do
        [ -d "$skill_dir" ] || continue
        name=$(basename "$skill_dir")
        mkdir -p "$agent_skills_dir/$name"
        cp -R "$skill_dir"/. "$agent_skills_dir/$name/"
    done
    mkdir -p "$agent_skills_dir/shared-references"
    cp "$I18N_DIR/shared-references"/*.md "$agent_skills_dir/shared-references/"
done
echo "$LANG_CODE" > .claude/.current-lang
mkdir -p .agents
echo "$LANG_CODE" > .agents/.current-lang
ok "Language files activated for Claude Code and Codex ($LANG_CODE)"

# ── Step 4: Verify installation ─────────────────────────────────────────

echo ""
info "Verifying installation..."

ERRORS=0
WARNINGS=0

check_python_snippet() {
    local label="$1"
    local snippet="$2"
    if "$VENV_PYTHON" -c "$snippet" >/dev/null 2>&1; then
        ok "$label"
    else
        fail "$label missing"
        ERRORS=$((ERRORS+1))
    fi
}

check_tool_import() {
    local label="$1"
    local import_stmt="$2"
    if (cd tools && "$VENV_PYTHON" -c "$import_stmt") >/dev/null 2>&1; then
        ok "$label"
    else
        fail "$label import error"
        ERRORS=$((ERRORS+1))
    fi
}

# Check real runtime dependencies first.
check_python_snippet "PyMuPDF (fitz)" "import fitz"
check_python_snippet "requests" "import requests"
check_python_snippet "feedparser" "import feedparser"

# Then check the current-stage tools with the same interpreter.
check_tool_import "tools/init_discovery.py" "from init_discovery import prepare_inputs"
check_tool_import "tools/fetch_s2.py" "from fetch_s2 import search"
check_tool_import "tools/fetch_arxiv.py" "from fetch_arxiv import fetch_recent"
check_tool_import "tools/research_wiki.py" "from research_wiki import slugify"
check_tool_import "tools/lint.py" "from lint import check_missing_fields"
check_tool_import "tools/wiki2dag.py" "from wiki2dag import build_dag"
check_tool_import "tools/poster.py" "from poster import build_poster"

# DeepXiv is optional; surface it as a warning-only diagnostic.
if "$VENV_PYTHON" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1; then
    if "$VENV_PYTHON" -c "import deepxiv_sdk" >/dev/null 2>&1; then
        ok "deepxiv-sdk (optional)"
    else
        warn "deepxiv-sdk unavailable; DeepXiv features will degrade but setup can continue"
        WARNINGS=$((WARNINGS+1))
    fi
else
    warn "Python < 3.10 detected inside .venv; deepxiv-sdk may be unavailable, so DeepXiv features may degrade"
    WARNINGS=$((WARNINGS+1))
fi

# ── Done ────────────────────────────────────────────────────────────────

echo ""
echo "============================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "  ${GREEN}Setup complete!${NC}"
elif [ $ERRORS -eq 0 ]; then
    echo -e "  ${YELLOW}Setup complete with $WARNINGS warning(s)${NC}"
else
    echo -e "  ${YELLOW}Setup complete with $ERRORS error(s) and $WARNINGS warning(s)${NC}"
fi
echo "============================================"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Authenticate your coding agent (if not already):"
echo "     claude login"
echo "     codex"
echo ""
echo "  2. Optional: activate .venv for manual Python tool use:"
echo "     source .venv/bin/activate"
echo "     setup.sh does not activate your current shell permanently."
echo "     /init will use .venv/bin/python automatically when it exists."
echo ""
echo "  3. Start an agent:"
echo "     claude"
echo "     codex"
echo ""
echo "  4. Complete API key configuration (guided):"
echo "     Claude Code: /setup"
echo "     Codex:       \$setup"
echo "     The agent will walk you through Semantic Scholar,"
echo "     DeepXiv, and Review LLM — skip any you don't have yet."
echo ""
echo "  5. Then initialize your wiki:"
echo "     Claude Code: /init [your-research-topic]"
echo "     Codex:       \$init [your-research-topic]"
echo ""
echo "  For more, see README.md"
echo ""
