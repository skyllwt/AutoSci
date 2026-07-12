# AutoSci with OpenCode

OpenCode is the only supported terminal agent. Skills are generated into `.opencode/skills` by `setup.sh` or `setup.ps1`; bilingual sources under `i18n/<lang>` are authoritative. Use the `skill` tool to load a skill, including `init` for wiki initialization.

Treat `raw/`, `wiki/`, `.checkpoints/`, experiment outputs, and local configuration as user-owned data. Read them only as needed. Never publish, delete, reset, or overwrite them without explicit human confirmation. Skills may write only the paths declared in their Wiki Interaction section. Keep forward and reverse graph links synchronized according to `runtime/schema/xref.yaml`.

Use OpenCode-native tools: `websearch`, `webfetch`, `task`, `question`, and `skill`. Prefer the project Python retrieval tools when `websearch` is unavailable and label that result as degraded. Parallel tasks must not write the same files; shared-index and graph updates remain serial. Preserve all documented human confirmation gates, especially experiment execution, deployment, destructive reset, and external communication.

Repository contracts live in `runtime/schema`, `runtime/policy`, and `runtime/templates`. Read `runtime/AGENTS.md` before changing them. Run `python tools/lint.py --wiki-dir wiki` after wiki mutations. Never commit secrets, generated `.opencode`, `opencode.json`, user wiki content, raw sources, or experiment artifacts.
