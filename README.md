# AutoSci

AutoSci is a bilingual, file-backed research assistant for OpenCode. It turns papers and notes into a linked research wiki and supports discovery, ideas, experiments, academic writing, visualization, and recommendation-only daily arXiv digests.

OpenCode is the only supported terminal agent. Python research tools remain usable directly and are independent of the agent runtime.

## Install

Requirements: Python 3.9+ and OpenCode.

```bash
git clone <repository-url> AutoSci
cd AutoSci
./setup.sh --lang en       # or: --lang zh
opencode
```

On Windows run `.\setup.ps1 -Lang en`, then `opencode`.

Setup creates `.venv`, installs main and `llm-review` dependencies, cleanly rebuilds `.opencode/skills` from `i18n/<lang>`, activates root `AGENTS.md`, and generates machine-local `opencode.json` with the absolute `.venv` Python command for the review MCP server. Generated OpenCode files are gitignored.

Use the `init` skill to bootstrap a wiki. Skill parameters are documented in each skill body and can be supplied in natural language.

## Data and safety

Inputs under `raw/`, knowledge under `wiki/`, checkpoints, experiment outputs, `.env`, and local OpenCode configuration remain local. AutoSci preserves confirmation gates for destructive actions, experiment execution/deployment, and external communication. Shared graph and index updates remain serial.

## Optional APIs

Use `.env.example` or the `setup` skill. Semantic Scholar and DeepXiv improve retrieval. `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` enable independent review and unattended recommendations through a compatible Chat Completions API.

Daily arXiv is notification-only. Local runs use `prepare → recommendation judgment → finalize`; GitHub Actions uses the independent API, deterministic fallback, optional best-effort SMTP, and always uploads artifacts. It never runs OpenCode in CI or ingests papers. See [deployment documentation](docs/daily-arxiv-deployment.md).

## Development

The bilingual trees under `i18n/en` and `i18n/zh` are authoritative; `.opencode/skills` is generated. Runtime contracts live under `runtime/`.

```bash
python -m unittest discover -s tests -v
python tools/validate_opencode_migration.py
python tools/lint.py --wiki-dir wiki
git diff --check
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [configuration](config/README.md).
