# 运行时页面模板

> 仅按需读取的 wiki 页面模板。graph 派生文件以及 `index.md`、`log.md` 请看 `docs/runtime-support-files.zh.md`。

<!-- bio-A1（2026-05-11 pilot merge）：页面类型从 9 类扩为 10 类——datasets/ 成为一等实体。 -->
## 10 类页面

### papers/{slug}.md

```yaml
---
title: ""
slug: ""
arxiv: ""
# bio-A3（2026-05-11 minimal pilot merge）：生信原生标识符，全部可选。
# 生信论文常有 DOI / PMID 但无 arXiv ID。完整 A3 方案还有 biorxiv、pdb_ids、uniprot_ids、
# nct_ids、gene_symbols、species —— 这些字段延后到 /ingest（C1）的 bio NER 预扫能批量填充时。
doi: ""                  # bio-A3：主生信标识符
pmid: ""                 # bio-A3：PubMed ID
venue: ""
year:
tags: []
importance: 3           # 1-5
date_added: YYYY-MM-DD
source_type: tex         # tex | pdf
s2_id: ""
keywords: []
domain: ""
code_url: ""
cited_by: []
---
```

正文：`## Problem` / `## Key idea` / `## Method` / `## Results` / `## Limitations` / `## Open questions` / `## My take` / `## Related`

### concepts/{concept-name}.md

```yaml
---
title: ""
aliases: []
tags: []
maturity: active         # stable | active | emerging | deprecated
key_papers: []
first_introduced: ""
date_updated: YYYY-MM-DD
related_concepts: []
# bio-A2（2026-05-11 light pilot merge）：可选的蛋白质锚点字段。仅当概念本身是具体基因产物
# （p53、CRBN、VHL、MDM2、…）时填充。过程概念（ubiquitylation）、方法概念（alphafold-db）、
# 类概念（ubiquitin-ligase-e3）请留空。蛋白概念累积到 ≥50 个时，提升为独立 `proteins/`
# 实体类型（A2 heavy 选项，仍 drafted）。
gene_symbol: ""          # bio-A2：HGNC 符号，例如 "TP53"
uniprot_id: ""           # bio-A2：例如 "P04637"
pdb_ids: []              # bio-A2：代表性结构
species: []              # bio-A2：例如 ["human"]
---
```

正文：`## Definition` / `## Intuition` / `## Formal notation` / `## Variants` / `## Comparison` / `## When to use` / `## Known limitations` / `## Open problems` / `## Key papers` / `## My understanding`

### topics/{topic-name}.md

```yaml
---
title: ""
tags: []
my_involvement: none     # none | reading | side-project | main-focus
sota_updated: YYYY-MM-DD
key_venues: []
related_topics: []
key_people: []
---
```

正文：`## Overview` / `## Timeline` / `## Seminal works` / `## SOTA tracker` / `## Open problems` / `## My position` / `## Research gaps` / `## Key people`

### people/{firstname-lastname}.md

```yaml
---
name: ""
affiliation: ""
tags: []
homepage: ""
scholar: ""
date_updated: YYYY-MM-DD
---
```

正文：`## Research areas` / `## Key papers` / `## Recent work` / `## Collaborators` / `## My notes`

### Summary/{area-name}.md

```yaml
---
title: ""
scope: ""
key_topics: []
paper_count:
date_updated: YYYY-MM-DD
---
```

正文：`## Overview` / `## Core areas` / `## Evolution` / `## Current frontiers` / `## Key references` / `## Related`

### foundations/{slug}.md

```yaml
---
title: ""
slug: ""
domain: ""
status: mainstream       # mainstream | historical
aliases: []
first_introduced: ""
date_updated: YYYY-MM-DD
source_url: ""
---
```

正文：`## Definition` / `## Intuition` / `## Formal notation` / `## Key variants` / `## Known limitations` / `## Open problems` / `## Relevance to active research`

Foundations **没有外向链接字段**。其他页面可链接到 foundation；foundation 不写反向链接。

### ideas/{idea-slug}.md

```yaml
---
title: ""
slug: ""
status: proposed          # proposed | in_progress | tested | validated | failed
origin: ""
origin_gaps: []
tags: []
domain: ""
priority: 3               # 1-5
pilot_result: ""
failure_reason: ""
linked_experiments: []
date_proposed: YYYY-MM-DD
date_resolved: ""
# bio-A7（2026-05-11 pilot merge）：可选的 GRADE 风格整体证据等级。
# 比 per-edge 分级（延后）粗，但对 /novelty 权重和 /paper-draft 置信度叙述立即有用。
# 没有证据时留空即可。
grade: ""                 # very-low | low | moderate | high（可选）
# bio-C3（2026-05-12 pilot merge）：可选 scope 对象。空 / 缺失视为 "universal" ——
# failed ideas 上意味着 universal banlist block（任何候选 idea 都 overlap）;proposed /
# in_progress ideas 上意味着 idea 不限定具体 bio 子空间。在 failed ideas 上显式填充,
# 这样未来 /ideate 运行可区分 "饱和子空间" 与 "全面禁令"。
scope:
  species: []              # ["human"] | ["mouse", "human"] | ["plant"] | …（空 = universal）
  disease_area: []         # ["cancer"] | ["neurodegenerative"] | …（空 = disease-agnostic）
  data_regime: ""          # high_data | low_data | mixed（空 = data-regime-agnostic）
---
```

正文：`## Motivation` / `## Hypothesis` / `## Approach sketch` / `## Expected outcome` / `## Risks` / `## Pilot results` / `## Lessons learned`

### experiments/{experiment-slug}.md

```yaml
---
title: ""
slug: ""
status: planned           # planned | running | completed | abandoned
target_claim: ""
hypothesis: ""
tags: []
domain: ""
setup:
  model: ""
  dataset: ""
  hardware: ""
  framework: ""
  # bio-A5 full（2026-05-12 pilot merge）：可选的 bio 形态 setup 字段。纯 ML 设计留空仍合法。
  # in_silico_or_wet 驱动 /exp-design 湿实验探测与 /exp-run 目录布局。force_field /
  # solvent_model / simulation_length 仅 MD 流水线。species / cell_line / assay_type
  # 覆盖湿实验与 cross_context。weight_version 捕获多版本 ML 模型。random_seed_protocol
  # 记录实际复制策略（多 seed 对小样本 bio n 通常不够）。
  in_silico_or_wet: ""         # in_silico | wet_lab | mixed
  species: []                  # ["human"] | ["mouse", "human"] | …
  cell_line: ""                # 优先 Cellosaurus ID（如 HEK293T 是 CVCL_0023）
  assay_type: ""               # MD | docking | scoring | Y2H | AP-MS | cryo-EM | NMR | binding_assay | …
  force_field: ""              # 仅 MD（如 "AMBER ff14SB + phosaa14SB"）
  solvent_model: ""            # 仅 MD（explicit | implicit | vacuum）
  simulation_length: ""        # 仅 MD（如 "50 ns"）
  weight_version: ""           # 多版本 ML 模型（如 "Boltz-2 Jan 2026 weights"）
  random_seed_protocol: ""     # ranking-shuffle | bootstrap | stratified-k-fold | LOO-CV
metrics: []
baseline: ""
outcome: ""               # succeeded | failed | inconclusive
key_result: ""
linked_idea: ""
date_planned: YYYY-MM-DD
date_completed: ""
run_log: ""
started: ""
estimated_hours: 0           # bio-A6：legacy 单数字预算，向后兼容保留
# bio-A6（2026-05-11 pilot merge）：结构化成本块。子字段全部可选、加性。
# 新实验在 GPU / MD / 湿实验 / FTE / 数据访问成本组成非平凡时应填充此块——
# 单数字 estimated_hours 会把这些约束压扁成一个数。
estimated_cost:
  gpu_hours: 0
  cpu_hours: 0
  md_wallclock_hours: 0
  wet_lab_usd: 0
  fte_weeks: 0
  dataset_access_lead_time_days: 0
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---
```

正文：`## Objective` / `## Setup` / `## Procedure` / `## Results` / `## Analysis` / `## Claim updates` / `## Follow-up`

### claims/{claim-slug}.md

```yaml
---
title: ""
slug: ""
status: proposed          # proposed | weakly_supported | supported | challenged | deprecated
confidence: 0.5           # 0.0-1.0
tags: []
domain: ""
source_papers: []
evidence:
  - source: ""
    type: supports        # supports | contradicts | tested_by | invalidates
    strength: moderate    # weak | moderate | strong
    detail: ""
conditions: ""
date_proposed: YYYY-MM-DD
date_updated: YYYY-MM-DD
---
```

正文：`## Statement` / `## Evidence summary` / `## Conditions and scope` / `## Counter-evidence` / `## Linked ideas` / `## Open questions`

<!-- bio-A1（2026-05-11 pilot merge）：datasets/ 是第 10 种一等实体。锚定可复用的数据集引用
     （TernaryDB、PROTAC-DB、AlphaFold-DB、dbPTM、PhosphoSitePlus、UniProt、PDB、…），
     使 experiments[*].setup.dataset 和 papers/* 中的引用可以 wikilink 到带版本历史与
     access tier 的规范页面。 -->
### datasets/{slug}.md

```yaml
---
title: ""
slug: ""
aliases: []
tags: []
maturity: stable             # stable | active | emerging | deprecated
access: public               # public | registration | restricted | wet-lab-derived
# versions 是 release 记录列表；下游 skill 会拿它与
# experiments[*].reproducibility.dataset_versions[*].version 对比检测漂移。
versions: []                 # 列表元素: {version, released, url, n_entries, notes}
canonical_url: ""
license: ""
key_papers: []               # 反向链接 —— 由引用该数据集的 papers/ 写入
key_concepts: []
date_updated: YYYY-MM-DD
---
```

正文：`## Overview` / `## Versions` / `## Access and licensing` / `## Schema and entries` / `## Known caveats` / `## Used by experiments` / `## Key papers`
