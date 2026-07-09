# AutoSci Codex Preview

AutoSci now has an official Codex Preview on the `migrate-codex` branch.
The stable `main` branch remains the Claude Code version while the Codex path
is validated with real users.

## Try It

```bash
git clone -b migrate-codex https://github.com/skyllwt/AutoSci.git
cd AutoSci
./setup.sh --lang en
codex
# Then invoke: $init [your-research-topic]
```

## What Works

- Repo-scoped Codex skills are available under `.agents/skills`.
- Skills are invoked in Codex with `$setup`, `$init`, `$ingest`, `$research`,
  and the other skill names listed in the README.
- Claude Code compatibility is preserved under `.claude/skills`.
- English and Chinese skill sources remain centralized in `i18n/<lang>/skills`;
  setup regenerates both active skill trees.
- Local Codex workflows have smoke coverage for setup, init, ingest, discover,
  ask/check, experiment helpers, writing helpers, visualization, and paper tools.
- Daily arXiv CI `inform` recommendations can use Codex CLI credentials.

## Known Boundaries

- GitHub Actions `daily-arxiv --mode auto-ingest` still uses the legacy Claude
  Code Action path until unattended Codex ingest and push writeback are verified.
- Some networked tools require Codex sandbox escalation, as documented in
  `AGENTS.md`.
- Review LLM support through the Codex MCP server may require restarting Codex
  after MCP configuration changes.
- `main` is not yet switched to Codex-first defaults; clone this preview branch
  explicitly when testing Codex.

## Feedback

Please open issues or PRs against the preview branch and include:

- your OS and Python version
- Codex CLI version
- the skill you ran, for example `$init` or `$ingest`
- whether the failure happened in local use or GitHub Actions
- relevant logs with secrets removed

## Suggested GitHub Release Text

Title:

```text
AutoSci Codex Preview
```

Body:

~~~markdown
AutoSci now has a Codex-compatible preview branch.

Try it:

```bash
git clone -b migrate-codex https://github.com/skyllwt/AutoSci.git
cd AutoSci
./setup.sh --lang en
codex
# $init your-topic
```

Status:

- Local Codex skills are available under `.agents/skills`.
- Claude Code compatibility is preserved under `.claude/skills`.
- Shared skill sources remain under `i18n/<lang>/skills`.
- Daily arXiv CI `inform` recommendations can use Codex.
- CI `auto-ingest` still uses the legacy Claude Code Action path until
  unattended Codex writeback is verified.
~~~
