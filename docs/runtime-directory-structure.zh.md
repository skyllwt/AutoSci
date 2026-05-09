# 运行时目录图

> 按需读取的仓库布局参考。主 `CLAUDE.md` 只保留需要常驻上下文的 schema 与约束。

```text
wiki/
├── CLAUDE.md          ← runtime schema
├── index.md           ← 内容目录（YAML）
├── log.md             ← 时序日志（append-only）
├── papers/            ← 论文结构化摘要
├── concepts/          ← 技术概念综述
├── topics/            ← 研究方向地图
├── people/            ← 研究者追踪
├── ideas/             ← 研究想法（带生命周期状态）
├── experiments/       ← 实验记录（wiki 页面）
├── methods/           ← 跨论文可复用的方法实体
├── Summary/           ← 领域全景综述
├── foundations/       ← 领域基础知识（终端：只接受入链，不写出链）
├── outputs/           ← 生成物（Related Work、论文草稿）
└── graph/             ← 自动生成（勿手动编辑）
    ├── edges.jsonl
    ├── citations.jsonl
    ├── context_brief.md
    └── open_questions.md

raw/
├── papers/            ← 用户自有 .tex / .pdf 来源
├── discovered/        ← /init 与 /daily-arxiv 抓取的外部论文
├── tmp/               ← /init 与直接本地 /ingest 生成的本地预处理来源
├── notes/             ← 用户自有 .md 笔记
└── web/               ← 用户自有 HTML / Markdown

config/
├── server.yaml        ← 远程 GPU 服务器配置（可选，/exp-run --env remote 时需要）
├── server.yaml.example
├── .env.example
└── settings.local.json.example
```

## 快速提醒

- `raw/papers/`、`raw/notes/`、`raw/web/` 是用户自有输入。
- `raw/discovered/` 用于外部抓取论文，不是用户随手放文件的目录。
- `raw/tmp/` 是 `/init` 与直接本地 `/ingest` 的生成型中间状态。
- `graph/` 是派生目录，只能通过 `tools/research_wiki.py` 维护。
