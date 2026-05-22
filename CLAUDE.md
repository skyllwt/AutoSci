# ΩmegaWiki — Runtime Contract

Edit `i18n/en/CLAUDE.md`, not the active copy at root. Run `./setup.sh --lang en` to sync.

## Repository Layout

- `wiki/` — product surface. `index.md` is the catalog; `log.md` is append-only; subdirs per entity kind; `wiki/graph/` is auto-generated.
- `runtime/` — contract source (schema + policy + templates). Read `runtime/CLAUDE.md` before changing any rule.
- `raw/` — user-owned `{papers,notes,web}/` (read-only) + skill-writable `discovered/`, `tmp/`.
- `tools/` — Python helpers (`research_wiki.py` is the wiki engine; `lint.py` is the validator).

Full tree: `docs/runtime-directory-structure.en.md`.

## Link Syntax

Wikilinks: `[[slug]]`. Slugs are lowercase, hyphen-separated, no spaces.

## Hard Rules

1. `raw/{papers,notes,web}` are user-owned, read-only. Skills append only to `raw/discovered/` or `raw/tmp/`.
2. `wiki/graph/` is derived. Modify only via `tools/research_wiki.py` (`add-edge`, `add-citation`, `rebuild-*`).
3. `wiki/log.md` is append-only. Never rewrite in place.
4. Forward link → write reverse simultaneously. Rules in `runtime/schema/xref.yaml`.
5. User-facing skill flags (those listed in a skill's `argument-hint`) are user-owned. Do not invent, flip, or drop them based on repo state. If the user omitted one, use a default only when the skill documents omission behavior; otherwise ask.

## Where to look

| Need | Source |
|---|---|
| Page frontmatter fields, enums, defaults, lifecycle | `runtime/schema/entities.yaml` |
| Page body section structure                          | `runtime/templates/{kind}.md.tmpl` |
| Edge types, attributes, direction, confidence       | `runtime/schema/edges.yaml` |
| Forward → reverse link rules                         | `runtime/schema/xref.yaml` |
| Slug rule, ownership, edge storage location          | `runtime/schema/conventions.yaml` |
| Field/edge write permissions per skill               | `runtime/policy/writers.yaml` |
| Changing the contract / regen                        | `runtime/CLAUDE.md` |

## Python Environment

Prefer in order: `.venv/bin/python` (`.venv/Scripts/python.exe` on Windows) → active conda env → `python3` (`python` on Windows). Tools auto-load API keys from `~/.env` and project-root `.env` via `tools/_env.py`.

---

## 语言策略（KnowledgeBase 强制）

无论用户用什么语言提问、原始论文用什么语言、上游 skill prompt 用什么语言，
**所有你生成的内容都必须用中文**：

- 给用户的回复：中文
- Wiki 页面正文（papers / concepts / methods / topics / ideas / experiments / Summary / foundations）：中文
- 生成的 LaTeX 论文、poster、survey：中文，除非用户在 runtime 明确要求英文
- 终端状态消息、面向用户的报告：中文
- 代码注释：遵循所在项目已有风格；若没有既有风格，优先英文

**保留英文原文的例外**（不强行翻译）：

- 学术术语：LoRA、attention、transformer、reinforcement learning、in-context learning、prompt、token、embedding 等
- 论文标题、作者姓名、机构名、会议名（NeurIPS / ICML / ACL ...）、URL、文献引用
- 代码标识符：变量名、函数名、类名、模块名
- 文件路径、命令行参数、环境变量、配置 key
- arXiv ID、DOI、commit hash 等技术标识符

写法：中文叙述 + 英文术语原样嵌入，例如 "本文提出基于 attention 的 LoRA 微调方法" 而不是 "本文提出基于注意力机制的低秩适配方法"。
