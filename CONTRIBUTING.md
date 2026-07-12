# Contributing

AutoSci supports OpenCode only. Keep changes focused, preserve user data, and never commit `.env`, `opencode.json`, `.opencode/`, raw sources, wiki content, checkpoints, or experiment artifacts.

Skill changes belong in both `i18n/en/skills/<name>` and `i18n/zh/skills/<name>`. Frontmatter supports only `name` and `description`; parameters belong in the body. Use OpenCode-native tool names (`websearch`, `webfetch`, `task`, `question`, `skill`) and relative reference paths. Do not edit generated `.opencode/skills`.

When a workflow writes the wiki, preserve writer policy, reverse links, human confirmation gates, and serial shared-file updates. Read `runtime/AGENTS.md` before changing schemas, policies, or templates.

Before opening a pull request, run the commands from README's Development section, including the OpenCode migration validator and `git diff --check`.
