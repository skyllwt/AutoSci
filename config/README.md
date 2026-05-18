# Configuration Templates

This directory contains configuration templates. Copy them to the correct locations during setup.

## Files

### `daily-arxiv.yml.example`

Daily arXiv recommendation preferences. Copy to `config/daily-arxiv.yml`:

```bash
cp config/daily-arxiv.yml.example config/daily-arxiv.yml
```

This file stores non-secret settings such as mode, categories, recommendation
caps, schedule, and profile hints. Keep API keys and SMTP credentials in `.env`
or GitHub Actions secrets.

### `.env.example`

Environment variables for API keys. Copy to project root:

```bash
cp config/.env.example .env
```

Then edit `.env` to add your API keys. See comments in the file for detailed instructions on each key.

### `settings.local.json.example`

Claude Code permission settings. Copy to `.claude/`:

```bash
mkdir -p .claude
cp config/settings.local.json.example .claude/settings.local.json
```

**What the permissions do:**

| Permission | Why it's needed |
|-----------|-----------------|
| `Bash(*)` | Run any shell command — covers `python3 tools/*.py`, `pip install`, `latexmk` (paper compile), `nvidia-smi` (GPU check), `cp`, `mkdir`, `git`, and other commands used across skills |
| `Read(*)` | Read wiki pages, raw files, config, and experiment results |
| `Edit(*)` | Write wiki pages and update metadata |
| `WebSearch` | Search for papers during novelty checks, landscape scans, and daily-arxiv |
| `WebFetch(*)` | Fetch BibTeX from DBLP/CrossRef (used by `/paper-draft`, `/survey`) |
| `MCP(*)` | Call the llm-review MCP server for cross-model review |

`enableAllProjectMcpServers: true` auto-starts the `llm-review` server declared in `.mcp.json` without a first-run prompt.

These permissions grant broad access so that all skills work without interruption. Claude Code will **not** prompt for individual tool calls covered by this list.

**To restrict access:** If you prefer more manual control, you can replace `Bash(*)` with specific patterns (e.g., `Bash(python3:*)`, `Bash(latexmk:*)`) and remove permissions you don't need. Note that some skills may then require additional approval prompts. See [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code) for the full permissions format.

### `server.yaml.example`

Remote GPU server configuration for `/exp-run --env remote`. Copy to `config/`:

```bash
cp config/server.yaml.example config/server.yaml
```

Then edit `config/server.yaml` with your server's SSH details, GPU info, conda environment, and work directory. See comments in the file for each field.

**Only needed if you run experiments on a remote server.** Local-only users can skip this.

**Key fields:**

| Field | Required | Example |
|-------|----------|---------|
| `host` | Yes | `gpu1.cs.university.edu` |
| `user` | Yes | `researcher` |
| `work_dir` | Yes | `/home/researcher/experiments` |
| `conda.path` + `conda.env` | One of conda or env_setup | `/opt/conda` + `research` |
| `port` | No (default 22) | `2222` |
| `identity_file` | No | `~/.ssh/id_ed25519` |
| `proxy_jump` | No | `bastion.cs.edu` |

## All Done by `setup.sh`

If you ran `setup.sh`, `.env` and `.claude/settings.local.json` are already
copied to the right locations. `daily-arxiv.yml` and `server.yaml` are optional
and can be created later when you use those features.
