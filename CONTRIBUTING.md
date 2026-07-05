# Contributing to AutoSci

Thank you for your interest in contributing to AutoSci. This guide covers the essentials.

## Reporting Bugs & Requesting Features

Use [GitHub Issues](../../issues):

- **Bugs**: Use the "Bug Report" template. Include which `/skill` triggered the issue and any error logs.
- **Features**: Use the "Feature Request" template.

## Submitting Pull Requests

1. **Fork** the repository and create a feature branch from `main`.
2. **Implement** your changes (see guidelines below).
3. **Test**: `python -m pytest tests/ -v` must pass with no failures.
4. **Submit** a PR using the pull request template.

## Adding a New Skill

Follow the checklist in [`docs/extending.md`](docs/extending.md) before creating any new skill.

Key points:

- Create the skill directory as `kebab-case/SKILL.md`.
- Skills are **orchestrators** that use LLM reasoning and multi-step decisions.
- Skills call tools via `Bash: python3 tools/X.py` -- they do not contain deterministic logic themselves.
- Every skill must read from and/or write back to the wiki.
- **Bilingual + dual-agent requirement**: create both `i18n/en/skills/<name>/SKILL.md` and `i18n/zh/skills/<name>/SKILL.md`, include `name` and `description` in frontmatter, then run `./setup.sh` to sync active `.claude/skills` and `.agents/skills` files.
- Add tests in `tests/test_skill_validation.py`.

## Adding a New Tool

Tools live in `tools/` and are **deterministic Python helpers** (no LLM reasoning).

- File naming: `snake_case.py`
- Add corresponding tests in `tests/test_<module>.py`.
- Do **NOT** create a `src/` Python package. This is an agent-skill project, not a pip-installable library.

## Testing

Testing is mandatory for every module or skill change.

```bash
python -m pytest tests/ -v
```

- Python tools: `tests/test_<module>.py` with pytest
- Skills: `tests/test_skill_validation.py` checks structure, required sections, cross-references
- MCP servers: test tool registration and basic request/response

## Bilingual (i18n)

AutoSci ships in English and Chinese. English is canonical.

When modifying any `SKILL.md`, `CLAUDE.md`, `AGENTS.md`, or shared-references file:

1. Edit `i18n/en/<path>` first.
2. Apply the equivalent change to `i18n/zh/<path>`.
3. Run `./setup.sh --lang $(cat .claude/.current-lang 2>/dev/null || echo en)` to sync.
4. Confirm both `.claude/skills` and `.agents/skills` received the change.
5. Run tests.

## Active Skill Copies

The active skill trees under `.claude/skills` and `.agents/skills` are committed
so Claude Code and Codex work immediately after checkout. Treat them as generated
copies: do not edit them directly. Make workflow changes in `i18n/<lang>/skills`
or `i18n/<lang>/shared-references`, run setup to regenerate the active copies,
and commit the source plus regenerated output together.

## Code Style

| What | Convention |
|------|-----------|
| Python files | `snake_case.py` |
| Skill directories | `kebab-case/SKILL.md` |
| Wiki pages | `kebab-case.md` with YAML frontmatter |
| Test files | `test_<module_name>.py` |
| Edge types | `snake_case` |

## Architecture Reminders

- The **wiki is the central hub**. Every skill reads from and writes back to it.
- **Skills** = orchestrators (LLM reasoning). **Tools** = executors (deterministic).
- Do **NOT** create `src/` packages.
- Do **NOT** edit files under `graph/` directly -- they are auto-generated.
