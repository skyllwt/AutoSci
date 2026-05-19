# ΩmegaWiki Bio Case Study — 端到端 Demo

ΩmegaWiki 把生信文献组织成 typed graph + typed metadata 的可推理知识库。这里用 **PTM-aware PROTAC degrader nomination** 这个 case 串起 9 张实拍截图，覆盖**论文 → idea → 实验 → 知识图谱 → 每日推荐 → 策展可视化**的完整数据流。

---

## 1 · 论文从 PDF 到 typed 实体

![](../../assets/demo-01-paper.png)

MusiteDeep（Nucleic Acids Research 2020）的 wiki 页 frontmatter——DOI、PubMed ID、领域归一化 slug、tags、keywords 都从 PDF 自动提取。后续所有推理的入口。

## 2 · Idea + 证据强度评级

![](../../assets/demo-02-idea-main.png)

`ptm-aware-degrader-target-nomination` —— `status: in_progress` · GRADE 评级 **low**（系统主动承认证据不足，不是 LLM 自吹）· 8 个 cascaded experiments（baseline → noise-floor → headline → 3 ablations → 2 robustness）从这一页派生。

## 3 · 失败也是产物

![](../../assets/demo-03-idea-failed.png)

状态 `failed` 的 idea 同样持久化。`failure_reason` 列出 6 个已发表的同领域工具（SAPP / PhosAF / GraphPhos / AstraPTM2 / DeepPCT / MTPrompt-PTM），`scope:` 块明确标出"已 saturated 的子空间"（species=human/mouse, data_regime=high_data）。未来跑 ideate 同领域会自动避开；走植物、低数据迁移、跨物种则放行。

## 4 · 实验全字段

![](../../assets/demo-04-experiment.png)

DeepTernary baseline 实验页。`setup` 13 字段（含 `in_silico_or_wet` / `species` / `assay_type` / `random_seed_protocol`）+ `estimated_cost` 6 字段（GPU-hours、MD wall-clock、人力 FTE-weeks 分开计费）+ `reproducibility.dataset_versions` 与下文图 5 的 dataset 页双向 cross-check。CS 默认的"model + dataset + hardware"三字段在 bio 远远不够。

## 5 · Dataset 作为一等公民

![](../../assets/demo-05-dataset.png)

TernaryDB 数据集页面：`versions` 表 · `access: public` · `aliases`（同一数据集在不同论文里 3 种叫法归一）。下游实验引用 `version=v1`，由 `tools/lint_bio.py` 与本页 `versions[].version` 闭环校验。

## 6 · Live 知识图谱

![](../../assets/demo-06-spa-graph.png)

浏览器渲染的 PTM-aware-degrader 邻域（BFS depth=2）：**4 papers + 5 concepts + 5 ideas + 5 experiments** 用 14 类 bio 边类型连接（`tested_by` / `addresses_gap` / `inspired_by` / `introduces_concept`...）。每条边都是一次自动化产出——`/ingest` 加 paper 边、`/ideate` 加 idea 边、`/exp-design` 加 experiment 边。84 条边累计是多个 skill 在同一 wiki 上协作的轨迹。

## 7 · 边的 typed metadata

![](../../assets/demo-07-spa-metadata.png)

一条 `dataset_version_used` 边的完整 JSON——`metadata: {"version": "v1", "subset": "crbn-vhl-training"}` 由 closed-set schema 强制：必需 key 缺失 → error，未声明 key → warning，类型不匹配 → 拒绝。这是和 RAG 的根本差别：**边是结构化数据，不是 free-text 注释**。

## 8 · daily-arxiv 端到端

![](../../assets/demo-08-digest.png)

一条命令 `bash demo/run-demo.sh && head -25 examples/output/digest.md` 跑通 3 步流水线：**prepare**（9 篇候选去重打分）→ **recommend-llm via DeepSeek v4-flash**（4 decisions, score + rationale）→ **finalize digest**（5 篇落盘 markdown + 机读 JSON）。缺 LLM key 时自动退化为 tool-signals-only ranking，依然产出 digest——系统不靠 LLM 也能跑。

## 9 · 策展知识地图

![](../../assets/demo-09-canvas.png)

Obsidian Canvas 把 PTM 邻域排成 5 行流水线（papers / concepts / close-ideas / FOCUS / experiments）。与图 6 同源——都从 `edges.jsonl` 派生——但视角不同：SPA 是机器视角的全图，Canvas 是人手挑选的故事版。两者实时同步。

---

## 本地 5 分钟复现

```bash
git clone https://github.com/skyllwt/OmegaWiki.git && cd OmegaWiki

# 图 6 SPA 知识图谱
.venv/bin/python tools/serve.py
# 访问 http://localhost:8765/，搜 ptm-aware-degrader-target-nomination

# 图 8 daily-arxiv（需 .env 配 LLM_API_KEY + LLM_BASE_URL + LLM_MODEL）
bash demo/run-demo.sh && head -25 examples/output/digest.md

# 图 7 typed metadata 直接 grep
grep -F dataset_version_used wiki/graph/edges.jsonl | python3 -m json.tool

# 9 张截图直链
ls assets/demo-0*.png
```

`examples/output/digest-sample.md` 是预渲染输出，无需 API key 即可看 LLM 排序后的 digest 长什么样。

---

## 同一份 idea graph 的另一种输出

把上述 9 张图依赖的同一 idea graph 喂给 `/paper-plan` + `/paper-draft`，可以生成完整 ICLR 8 页论文：

- 论文 LaTeX 源码：[`paper/main.tex`](../../paper/main.tex)
- 论文规划：[`wiki/outputs/paper-plan-ptm-aware-degrader-target-nomination-2026-05-19.md`](../../wiki/outputs/paper-plan-ptm-aware-degrader-target-nomination-2026-05-19.md)

视觉 demo 与论文是**同源双输出**——前者面向人快速理解，后者面向同行评审。
