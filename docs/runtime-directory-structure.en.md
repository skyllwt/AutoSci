# Runtime Directory Chart

> On-demand reference for the repo layout. The main `CLAUDE.md` keeps only the schema and rules that should stay in immediate context.

```text
wiki/
├── CLAUDE.md          ← runtime schema
├── index.md           ← content catalog (YAML)
├── log.md             ← chronological log (append-only)
├── papers/            ← structured paper summaries
├── concepts/          ← cross-paper technical concepts
├── topics/            ← research direction maps
├── people/            ← researcher profiles
├── ideas/             ← research ideas (with lifecycle status)
├── experiments/       ← experiment records (wiki pages)
├── methods/           ← cross-paper reusable method entities
├── Summary/           ← domain-wide surveys
├── foundations/       ← background knowledge (terminal: receives inward links, writes none)
├── outputs/           ← generated artifacts (Related Work, paper drafts)
└── graph/             ← auto-generated (do not edit)
    ├── edges.jsonl
    ├── citations.jsonl
    ├── context_brief.md
    └── open_questions.md

raw/
├── papers/            ← user-owned .tex / .pdf sources
├── discovered/        ← externally fetched papers from /init and /daily-arxiv
├── tmp/               ← generated prepared local sources for /init and direct local /ingest
├── notes/             ← user-owned .md notes
└── web/               ← user-owned HTML / Markdown

config/
├── server.yaml        ← remote GPU server config (optional, needed for /exp-run --env remote)
├── server.yaml.example
├── .env.example
└── settings.local.json.example
```

## Fast Reminders

- `raw/papers/`, `raw/notes/`, and `raw/web/` are user-owned inputs.
- `raw/discovered/` is for fetched external papers, not user drop-ins.
- `raw/tmp/` is generated intermediate state for `/init` and direct local `/ingest`.
- `graph/` is derived and should be maintained only through `tools/research_wiki.py`.
