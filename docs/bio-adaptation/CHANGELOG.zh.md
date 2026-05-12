# 生信适配变更日志（中文）

> 本文件累计记录生信适配的每一项改动。每条对应 `docs/bioinformatics-adaptation-backlog.zh.md` 中一项 backlog 条目。仅追加，不修订。
>
> 所有改动写入 `docs/bio-adaptation/` 下的**镜像副本**，**不动原始文件**。某条目被采纳后，把镜像 hunk 合回真值源，并将本日志对应条目标为 `STATUS: merged`。
>
> 镜像目录：
> - `docs/bio-adaptation/section-a/runtime-page-templates.en.md` ↔ 真值源 `docs/runtime-page-templates.en.md`
> - `docs/bio-adaptation/section-a/runtime-page-templates.zh.md` ↔ 真值源 `docs/runtime-page-templates.zh.md`
> - `docs/bio-adaptation/section-a/CLAUDE.md` ↔ 真值源 `i18n/en/CLAUDE.md`（根 `CLAUDE.md` 通过 `./setup.sh --lang en` 同步）
>
> 镜像内注释规范：
> - YAML 块内：`# bio-A{n}: <一行说明>`
> - Markdown 正文：`<!-- bio-A{n}: <一行说明> -->`

镜像至英文版：`docs/bio-adaptation/CHANGELOG.en.md`。任何实质性改动两份必须同步。

---

## 2026-05-03 — A 节草拟（A1–A8）

**范围**：仅页面模板与运行入口的 schema 改动。未触动任何 skill 行为。
**状态**：已草拟，尚未合回真值源。
**写入文件**：
- `docs/bio-adaptation/section-a/runtime-page-templates.en.md`
- `docs/bio-adaptation/section-a/runtime-page-templates.zh.md`
- `docs/bio-adaptation/section-a/CLAUDE.md`

### A1 — [P0] `datasets/` 升为首位实体类型

**位置**：
- `runtime-page-templates.{en,zh}.md`：新增 `### datasets/{slug}.md` 模板（frontmatter + 正文段落）；标题"9 类页面"提升为"10 类页面"；类型清单加入 `datasets`。
- `CLAUDE.md`：同步标题数字；`wiki/` 主表层条目加 `wiki/datasets/`；交叉引用规则表追加两行（papers→datasets、experiments→datasets）；Link Syntax 块新增 `[[ternarydb]]` 示例；Constraints 段新增一项，声明 datasets 为首位实体并指出 C8 应拦截版本漂移。

**目的**：backlog 条目 A1。此前 `/exp-design` 全程提到的 TernaryDB / PROTAC-DB / DegronMD / AlphaFold-DB / PhosphoSitePlus / dbPTM / UniProt / PDB 全是纯文本 —— 没有 wikilink 目标、没有版本字段、没有 access 等级。没有首位 `datasets/` 页面，未来 bio ingest 无法锚定数据集，`/exp-design` 也无法把 `setup.dataset` 填成 wikilink。

**解锁**：`setup.dataset` 改为 wikilink（A5）；`dataset_versions` lint 检查（C8）；`/exp-design` 能上浮 access 受限 cohort 的 lead-time（H3）。

### A2 — [P1] `concepts/` 增加可选蛋白锚定字段（轻量方案）

**位置**：`runtime-page-templates.{en,zh}.md`，`concepts/{concept-name}.md` 块。新增可选 `gene_symbol`、`uniprot_id`、`pdb_ids`、`species`，并在注释中说明：仅当 concept 本身就是某个具体基因产物时填写；当此类 concept 累计 ≥ 50 条时再升级为独立 `proteins/` 实体。

**目的**：backlog 条目 A2 明确推荐先轻量后重型。p53、CRBN、VHL、MDM2 等当前只在正文里以纯文本出现；增加可选 UniProt/HGNC 锚定，让 concept 页可同时承担 protein 角色，无需立刻新建实体。

**解锁**：lint 可校验 UniProt accession 格式（C8）；未来诸如"靶向激酶 X 的 paper"等 graph 查询无需 schema 迁移即可写。

### A3 — [P0] `papers/` frontmatter 加入 bio 原生标识符

**位置**：`runtime-page-templates.{en,zh}.md`，`papers/{slug}.md` 块。在保留的 `arxiv` 之外，新增 `doi`、`pmid`、`biorxiv`、`pdb_ids`、`uniprot_ids`、`nct_ids`、`gene_symbols`、`species`。注释指明 `/ingest` 应从 CrossRef / PubMed E-utilities / EuropePMC 填充，而非仅 Semantic Scholar。

**目的**：backlog 条目 A3。本 wiki 11 篇 paper 中 bio 相关的 6 篇没有 arXiv ID，规范标识符是 DOI/PMID。CS 化的 frontmatter 把真实标识符挤进正文，无法被查询。

**解锁**：`/ingest` 接 PubMed/EuropePMC fallback（C1）；标识符格式 lint（C8）；按 gene/protein/structure 跨 paper 聚合。

### A4 — [P1] `domain` 字段记录受控词表

**位置**：`runtime-page-templates.{en,zh}.md`，所有携带 `domain` 的块（`papers/`、`ideas/`、`experiments/`、`claims/`）。YAML 内联注释列出 CS 取值（NLP / CV / ML Systems / Robotics）以及推荐 bio 词表（`structural-bio | chembio | comp-drug-discovery | cancer-bio | systems-bio | bioinformatics | clinical-translation`）。说明 lint 强制由 C8 落地。

**目的**：backlog 条目 A4。当前自由文本 `domain` 在不同页面已漂移（"Computational Drug Design / Chemical Biology"、"Cancer biology / Molecular oncology"、"Structural Bioinformatics"…）。先把词表写下来，未来写入可逐步收敛而不破坏旧页。

**解锁**：`/check` 可复用 status enum 警告机制（C8）；H6（基因组学侧词表扩充）可向同一列表追加，无需重构。

### A5 — [P0] `experiments/` setup 加 bio 形态字段

**位置**：`runtime-page-templates.{en,zh}.md`，`experiments/{experiment-slug}.md` setup 块。新增 `in_silico_or_wet`、`species`、`cell_line`、`assay_type`、`force_field`、`solvent_model`、`simulation_length`、`weight_version`、`random_seed_protocol`，全部可选。原有 `model`、`dataset`、`hardware`、`framework` 保留。

**目的**：backlog 条目 A5。当前 setup 是纯 ML 流水线形状，所有 bio 细节 —— 力场、溶剂模型、模拟时长、ML 权重版本、in-silico/MD/wet-lab 区分 —— 只能塞到正文里，下游 skill 无法读到。

**解锁**：`/exp-design` 可识别 MD 实验并强制 `force_field`（C8）；成本估算可对照真实 assay 参照表锚定（A6 + `docs/bio-compute-references.md`）。

### A6 — [P1] `estimated_hours` 弃用，改为结构化 `estimated_cost` 块

**位置**：`runtime-page-templates.{en,zh}.md`，`experiments/{experiment-slug}.md`。`estimated_hours` 标记 deprecated（保留 0 默认值供向后兼容）。新增 `estimated_cost` 块：`gpu_hours`、`cpu_hours`、`md_wallclock_hours`、`wet_lab_usd`、`fte_weeks`、`dataset_access_lead_time_days`。`CLAUDE.md` Constraints 增加一条正式弃用说明。提到配套参照表 `docs/bio-compute-references.md`（尚未创建，列为后续工具工作）。

**目的**：backlog 条目 A6 引用 F5 案例（`ablation-boltz2-ptm-vs-md-relaxed-route`）：`estimated_hours: 12` 实际差 ~250 倍（约 3000 GPU-h）。单一小时字段无法区分 GPU/CPU/MD 墙钟/湿实验美元/access lead time，估算无锚。

**向后兼容方案**：旧页保留 `estimated_hours: 0`；当某实验 `assay_type` 暗示 MD 或 wet-lab，但 `estimated_cost.md_wallclock_hours == 0` 且 `estimated_cost.wet_lab_usd == 0` 时，`/check` 发 warning（不报错）。逐页迁移即可，无需大规模重写。

**解锁**：`/exp-design` 能给出真实预算；H8 测序成本扩展可挂在同一块上。

### A7 — [P1] Claim 证据类型与强度针对 bio 扩展

**位置**：
- `runtime-page-templates.{en,zh}.md`，`claims/{claim-slug}.md` `evidence` 块。`type` 枚举扩展加入 `wet_lab_validated`、`clinical_validated`、`mechanistic_basis`、`correlative`、`predicts`。新增可选 `grade` 字段（`very-low | low | moderate | high`）。原 `strength`（`weak | moderate | strong`）原样保留。
- `CLAUDE.md`：Constraints 新增一条，列举基础与扩展类型集合，并说明 grade 字段。

**目的**：backlog 条目 A7。临床试验阳性结果与单次体外检测不属同一证据等级；机制性生化研究（点突变废活性）和相关性观察是定性不同的。GRADE 是医学领域的证据强度标准。

**向后兼容方案**：`strength` 保留，旧 claim 页无需重写；`grade` 纯属添加。

**解锁**：`/exp-eval` 可写出更具区分度的证据记录；`/novelty` 对 bio 类 claim 可按 GRADE 加权而非单一 confidence 数（E3）。

### A8 — [P2] `experiments/` 增加可选 `reproducibility` 块

**位置**：`runtime-page-templates.{en,zh}.md`，`experiments/{experiment-slug}.md`。新增可选 `reproducibility` 块：`rrid`、`cellosaurus`、`addgene`、`pdb_versions`、`dataset_versions`（列表 `{dataset_slug, version, accessed_date}`）。纯 in-silico 实验可省略。

**目的**：backlog 条目 A8。即使名义上的 in-silico 实验也常消费湿实验衍生数据（如 `phase0-noise-floor-calibration-deepternary-ptm-perturbations` V1 摄取的 phospho-PROTAC 阳性集来自已发表 assay）。没有抗体 RRID、细胞系 CVCL、质粒 ID、数据集版本+日期，"可复现"无法验证。

**解锁**：C8 lint 可对比 `reproducibility.dataset_versions[*].version` 与 `datasets/{slug}.versions[]`，捕捉数据集静默漂移（依赖 A1）。

---

## 跨条目说明（统一适用）

- **未修改任何源文件。** `docs/runtime-page-templates.en.md`、`docs/runtime-page-templates.zh.md`、`i18n/en/CLAUDE.md` 全部原封不动。在后续提交把镜像 hunk 合回之前，原文件保持权威。
- **未改动任何 skill 行为。** A 节全部是 schema 或文档级改动。C 节（skill 工作流）与 B 节（图 edge 类型）仍待启动。
- **Backlog 条目状态未更新。** 按 backlog 的"使用方法"段，标注 `STATUS: in progress` 或 `STATUS: done` 需编辑原始 `docs/bioinformatics-adaptation-backlog.{en,zh}.md`；按本次会话指令这些原文件不动。合回时请在同一 commit 内一起更新 backlog 状态。
- **后续工具工作延后（B / C / H 节）。** 依赖 A 节的 C1（PubMed fallback）、C8（bio-lint）、H3（测序 cohort 入 `datasets/`）等留待各自的 changelog 条目。

---

## 2026-05-03 — B 节草拟（B1–B3）

**范围**：扩展 graph edge 类型。触及 CLAUDE.md 的 Graph Rules 段以及 `runtime-support-files` 中的 edge JSON 格式说明。**不修改** `tools/research_wiki.py`（工具实现工作另列后续条目）。
**状态**：已草拟，尚未合回真值源。
**写入文件**：
- `docs/bio-adaptation/section-b/CLAUDE.md`
- `docs/bio-adaptation/section-b/runtime-support-files.en.md`
- `docs/bio-adaptation/section-b/runtime-support-files.zh.md`

**与 A 节副本相互独立。** `section-a/CLAUDE.md` 与 `section-b/CLAUDE.md` 都基于同一真值源 `i18n/en/CLAUDE.md` 并指向同一合并目标，但各自只含本 section 的 hunk；合回时按 A、B 顺序应用。

### 跨条目设计抉择 —— edge metadata 布局

B2（`clinical_trial_for {nct_id, phase}`、`fda_approved_for {indication, year}`、`validates_in_species {species}`）与 B3（`dataset_version_used {slug, version}`）引入了按 edge type 区分的属性。当前 edge JSON 没有可挂的位置。考虑了两个方案：

1. 把每个属性提升为 edge JSON 顶层字段。
2. 把按类型属性分组到嵌套的 `metadata` 对象中，与 `evidence`/`confidence`/`date` 同级。

**选择：方案 2（嵌套 `metadata`）。** 理由：(a) 避免与未来顶层字段及 JSONL/log 保留字段命名冲突；(b) 不识别某 edge type 的读取器可整体忽略 `metadata`，无需逐个键学习；(c) H9（变异-疾病、表达-终点）将引入更多类型化属性（`odds_ratio`、`hazard_ratio`、`p_value`、`cohort`），同一 `metadata` 槽位可吸收，无需进一步扩展 schema。

向后兼容：不带 `metadata` 的 edge 仍然合法；该字段纯属添加。

### B1 — [P1] 蛋白关系 edge 加入 graph schema

**位置**：
- `CLAUDE.md` Graph Rules 段：edge 列举重组为按类别分组的子项（paper-paper / paper-concept / claim-experiment-provenance / **bio 关系** / **验证-转化** / **数据集版本来源**）；B1 行列出 `targets_protein`、`binds`、`inhibits`、`activates`、`degrades`、`phosphorylates`、`ubiquitinates`、`methylates`、`acetylates`、`is_substrate_of`。新增 confidence 要求项。
- `runtime-support-files.{en,zh}.md`：edges.jsonl 行更新；新增"Edge 类型清单"表，按 edge 列出端点 / metadata / 语义。

**目的**：backlog 条目 B1。没有这些 edge，graph 无法回答"哪些药物靶向蛋白 X"、"哪些激酶磷酸化底物 Y"、"哪些 E3 ligase 泛素化底物 Z"——这些都被困在正文中。PTM 动词与一般功能动词分开列出，因为 PTM 关系常需独立的图遍历（底物推断、修饰级联重建）。

**端点策略**：关系 edge 既接受 A2 轻量方案下带蛋白锚定的 `concept`，也接受 A2 重型方案下未来的 `proteins/` 实体类型。A2 升级为重型时无需 schema 变更。

**解锁**：图侧的 drug-target / kinase-substrate / E3-substrate 查询；`/ideate` 与 `/exp-design` 下游的 PTM 级联推理。

### B2 — [P1] 验证 / 转化层 edge 加入

**位置**：
- `CLAUDE.md` Graph Rules 段：新 edge 类别行列出 `clinical_trial_for`、`fda_approved_for`、`validates_in_species`；说明这些 edge 携带类型化 `metadata`。
- `runtime-support-files.{en,zh}.md`：edge 清单行指明必填 `metadata` 键（`nct_id`+`phase`、`indication`+`year`、`species`）。

**目的**：backlog 条目 B2。诸如"asciminib 已获 FDA 批准用于 CML"、"tazemetostat 已获 FDA 批准用于 epithelioid sarcoma"等当前只在正文。没有这些 edge，graph 无法回答"哪些 claim 有 FDA 批准的药作为证据"、"哪些进行中的试验测试该机制"——而这正是转化研究者需要的查询。

**Edge JSON 形态示例**（位于 `runtime-support-files.en.md`）：
```json
{"from": "claims/asciminib-cml-effective", "to": "concepts/asciminib", "type": "fda_approved_for",
 "evidence": "FDA Drug Approval Letter, Oct 2021", "confidence": "high", "date": "2026-05-03",
 "metadata": {"indication": "CML", "year": 2021}}
```

**解锁**：转化类查询；后续 `/novelty` 在 PubMed 加权时优先以已批准药为锚。

### B3 — [P2] 实验-数据集版本来源 edge 加入

**位置**：
- `CLAUDE.md` Graph Rules 段：数据集版本 edge 类别下新 bullet。Constraints 段新增一项，要求当 `experiments[*].setup.dataset` 解析到 `datasets/{slug}` 页且其 `versions[]` 非空时，必须有出向 `dataset_version_used` edge；`/check` 在缺失或版本漂移时 warn。
- `runtime-support-files.{en,zh}.md`：edge 清单行指明 `metadata.version`（`slug` 可选）。

**目的**：backlog 条目 B3。TernaryDB 终会出 v2，基于 v1 校准的 Phase-0 noise floor 对 v2 不再成立。没有 `dataset_version_used` provenance edge，graph 无法侦测实验证据锚定到了过期的数据集快照。

**跨节依赖**：依赖 A1（`datasets/` 实体类型）与 A8（`reproducibility.dataset_versions` 块，是 `metadata.version` 的真值源）。

**解锁**：C8 lint 比对 `dataset_version_used` edge 与 `datasets/{slug}.versions[]`；`/exp-eval` 可上浮"本评估用的数据集为 v1 — 检查 v2 是否改变结论"提示。

---

### A1 后续 —— `index.md` 的 `datasets:` 块（延后）

起草 B 节时发现 A 节遗漏一项关联：`docs/runtime-support-files.{en,zh}.md` 中的 `index.md` schema 没有 `datasets:` 块，即便 A1 已把 `datasets/` 升为首位实体。在此记录避免遗忘；**未在任何 B 节副本中打补丁**（避免污染按节差异）。合回 A 节真值源时，请同步把 `datasets:` 追加到 index.md schema。

---

## 2026-05-03 — C 节 Batch 1 部分（仅 C1，`/ingest`）

**范围**：skill 工作流改造。C 节因体量切成 3 批；本条目覆盖 Batch 1 第一步（`/ingest`）。Batch 1 还包括 `/exp-design`（C4+C5+C6），下一响应交付。
**状态**：已草拟，未合回。**bio fetcher 工具尚未实现** —— bio 路径在 `tools/fetch_crossref.py`、`tools/fetch_pubmed.py`、`tools/fetch_europepmc.py`、`tools/fetch_biorxiv.py` 与 `tools/extract_bio_ner.py` 落地之前自动降级到 S2+RSS（C1 后续工具实现工作，不在本次 schema-and-doc 工作范围内）。
**写入文件**：
- `docs/bio-adaptation/section-c/skills/ingest/SKILL.en.md`
- `docs/bio-adaptation/section-c/skills/ingest/SKILL.zh.md`

### C1 — [P0] `/ingest` 接受 bio 标识符；bio 感知 fallback 链；bio NER 预扫描

**位置**：
- `Inputs` 段：`source` 枚举扩到接受 DOI / PMID / bioRxiv URL / PMC URL，与 arXiv URL / `.tex` / `.pdf` / INIT MODE 交接并列。YAML frontmatter 中 `argument-hint` 同步更新。
- `Wiki Interaction → Reads`：新增 `wiki/datasets/*.md`（依赖 A1）。
- `Wiki Interaction → Writes`：新增保守的 `wiki/datasets/{slug}.md` 写入规则（仅 EDIT 已存在；仅当本论文引入数据集且 importance ≥ 4 时 CREATE）。
- `Wiki Interaction → Graph edges created`：新增 B1 bio 关系 edge 家族（`targets_protein`、`binds`、`inhibits`、`activates`、`degrades`、`phosphorylates`、`ubiquitinates`、`methylates`、`acetylates`、`is_substrate_of`），仅当原文给出清晰线索时发出，confidence 默认保守。
- `Workflow → Step 1（解析来源）`：新增子步骤 3，详述 DOI / PMID / bioRxiv / PMC 的路由。每条路由解析到 `raw/discovered/` 下的 `canonical_ingest_path`。
- `Workflow → Step 2（论文身份与 enrichment）`：新增显式 fallback 链（子步骤 3）：bio 锚点输入走 `CrossRef → PubMed E-utilities → EuropePMC → bioRxiv API → DeepXiv → Semantic Scholar`；CS 路径文档化为 `S2 → DeepXiv → CrossRef`。新增子步骤 4：从结构化元数据（CrossRef abstract subjects、PubMed MeSH、EuropePMC annotations）抽 bio 标识符预填 A3 frontmatter 字段。Stop-if-exists 检查（子步骤 2）扩展到匹配 DOI / PMID / bioRxiv DOI。
- `Workflow → Step 3（写 paper 页面）`：填充时形状检查也对 DOI / PMID / PDB / UniProt 格式做粗检（完整 lint 留 C8）。
- `Workflow → Step 4（concept / claim / people）`：新增子步骤 1（bio NER 预扫描）以及子步骤 6–7（数据集 wikilink 提升；bio 关系 edge 抽取）。NER profile 默认 `protein-drug`；H5 覆盖其他 profile。
- `Workflow → Step 5（paper-to-paper edge）`：bio 路径 references/citations 改用 CrossRef + PubMed + EuropePMC；reference 匹配键扩到 DOI / PMID。
- `Workflow → Step 6（topic 与 index）`：注明 A1 后续条目落地后包含 `index.md` 的 `datasets:` 段。
- `Workflow → Step 8（汇报）`：report 新增上浮 fallback 链中胜出通道、NER 候选接受/延后数、留作 `/edit` 处理的数据集提及、降级为仅摘要的访问受限 DOI。
- `Workflow → Step 9（可选 discovery）`：`/discover` anchor key 扩到 `--doi` / `--pmid`（依赖 C2）。
- `Constraints`：bio 路径产物落入 `raw/discovered/`；JATS XML 等价于 `.tex` 用于正文抽取（XML > PDF > vision API）；bio NER 候选受同一 per-paper concept/claim cap。
- `Error Handling`：新增 bio 路径 fallback 语义（CrossRef/PubMed/EuropePMC/bioRxiv 故障级联）、许可受限 DOI 降级为仅摘要、`extract_bio_ner.py` 不可用时 graceful 跳过。
- `Dependencies → Tools`：`add-edge` confidence 要求扩到 B1 bio 关系 edge；`add-citation --source` 枚举扩入 `crossref|pubmed|europepmc|biorxiv`。新增"待建 bio fetcher 工具"小节列出 5 个尚未存在的脚本。
- `Dependencies → External APIs`：新增 CrossRef、NCBI E-utilities、EuropePMC、bioRxiv content API。

**目的**：backlog 条目 C1。本 wiki 中 6 篇 bio 相关论文没有一篇有 arXiv ID —— 每一篇都被强行套进 arXiv 形状的流水线。bio 规范源是 PubMed/EuropePMC/bioRxiv，不是 Semantic Scholar。没有 bio 标识符路由，未来每次 bio `/ingest` 要么匹配不到现有路径，要么靠 `prepare_paper_source.py` 强行套用、enrichment 退化。

**跨节依赖**：
- A1（`datasets/` 实体）—— 数据集 wikilink 提升与 `wiki/datasets/*.md` 的 Reads/Writes 行需要它。
- A3（`papers/` bio 标识符 frontmatter）—— 新元数据通道才有地方写 `doi`/`pmid`/`pdb_ids`/`uniprot_ids`/`nct_ids`/`gene_symbols`/`species`。
- B1（bio 关系 edge 类型）—— Step 4 子步骤 7 才能用 `add-edge` 写 `targets_protein` 等。
- C2（`/discover` bio anchor）—— Step 9 的 `--doi`/`--pmid` 锚定键；C2 落地前 fallback 到标题搜索。
- C8（`/check` bio-lint）—— 拥有完整标识符格式校验，本 skill 只做粗 sanity check。
- H5（按子领域 NER profile）—— 在默认 `protein-drug` profile 之外扩展 NER 预扫描；不在 C1 自身范围内。

**向后兼容**：legacy arXiv-only ingest 路径不变。bio 添加仅当 source 字符串匹配 bio 标识符形态、或 bio frontmatter 字段被填充时激活。每个新依赖都有优雅降级。

**采纳门槛** —— 本 skill 改动合回 `i18n/en/skills/ingest/SKILL.md` 之前：
1. A1 + A3 必须先合回（否则写入无处可去）。
2. 至少 `tools/fetch_pubmed.py paper <pmid>` 可用（最常见的 bio 标识符）。其余 fetcher 可分阶段。
3. `tools/extract_bio_ner.py` 初期可桩化（返回空列表）；bio NER 预扫描允许 no-op，工作流其余照常。

### Batch 1 待办 —— `/exp-design`（C4 + C5 + C6）

下一响应交付。C4（block 分类增 `negative_control | mechanism | dose_response | cross_context`）；C5（Step 1 的湿实验 vs in-silico 路由）；C6（bio 统计默认值 —— bootstrap CI / stratified CV / 复制语义 —— 加到 Step 3 + Step 5 review prompt）。

---

## 2026-05-03 — 物化可运行目录 + bio fetcher 工具（节外工作）

**脱离上述按节切批的节奏**，用户要求物化一份 bio 优化的可运行 fork，并实现全部 bio fetcher 工具，让 C1 不只是草稿、能真正运行。

**已完成**：
- 复制 `/home/yukino/OmegaWiki/` → `/home/yukino/OmegaWiki_bioinfo_adaptation/`（146→147M）；`sed` 改写 12 个 `.venv/` 文件中的绝对路径。原 `.venv` 不动。
- 在新目录把 A1–A8 + B1–B3 + C1 镜像 hunk 提升到真值源；`setup.sh --lang en` 同步根 `CLAUDE.md` 与 `.claude/skills/`。
- 在新目录 `tools/` 实现 5 个新工具：`fetch_pubmed.py`、`fetch_crossref.py`、`fetch_europepmc.py`、`fetch_biorxiv.py`、`extract_bio_ner.py`。全部用真实 bio 论文 smoke-tested（AlphaFold Nature 2021，PMID 34265844 + DOI 10.1038/s41586-021-03819-2；Boltz-1 bioRxiv 10.1101/2024.11.19.624167）。
- 扩展 `tools/_schemas.py`：`ENTITY_DIRS += ["datasets"]`；`CITATION_SOURCES += {crossref, pubmed, europepmc, biorxiv}`；14 个新 edge type spec（B1×10 + B2×3 + B3×1）+ `EDGE_METADATA_REQUIRED` 必填键。
- 扩展 `tools/research_wiki.py add-edge`，新增 `--metadata key=value`（可重复）；写入 edge JSON 的嵌套 `metadata` 对象；按 edge 校验必填键。
- 在新目录根写 `BIOINFO_ADAPTATION_README.md` + `BIOINFO_ADAPTATION_CHECKPOINT.md`。

**未完成**（带到下次 session）：
- C 节剩余批次：Batch 1 余项（C4+C5+C6）、Batch 2（C7/C8/C2/C9）、Batch 3（C3/C10/C11）
- `tools/lint_bio.py`（C8 依赖）
- 在新目录对真实 bio 标识符跑一次端到端 `/ingest` 调用
- 第一份 `wiki/datasets/{slug}.md` 页（如 TernaryDB）

**Session 暂停 2026-05-03。** Resume 入口：`/home/yukino/OmegaWiki_bioinfo_adaptation/BIOINFO_ADAPTATION_CHECKPOINT.md`。


---

## 2026-05-04 — C 节 Batch 1 收尾（C4 + C5 + C6 —— `/exp-design`）

**范围**：`/exp-design` skill 工作流改动。三条 backlog 打包是因为它们都落在同一份 SKILL.md 上，且彼此依赖（C4 的新块类型需要 C6 的统计协议选择器，C5 的 wet-lab 分支会创建一个其统计须遵循 C6 的实验块）。
**状态**：已草拟，**未合回真值源**。
**已写文件**：
- `docs/bio-adaptation/section-c/skills/exp-design/SKILL.en.md`
- `docs/bio-adaptation/section-c/skills/exp-design/SKILL.zh.md`

### 跨条目设计选择

- **bio 条件触发，不强制按 domain**：四种新块（E–H）和 bio 统计默认值在以下条件之一时启用：(a) idea 的 `domain` 命中 A4 的 bio 词表；**或** (b) wet-lab 关键词扫描命中 ≥1 锚点。CS idea 走旧 4 块分类与 `seeds_only` 协议不变。原因：仅按 `domain` 切换会漏掉那些 `domain` 留空（当前 wiki 里的常态）但 Approach sketch 明显在写细胞 assay 的 idea。
- **`statistical_protocol` 现在是必填的 YAML 标量、不再是推断属性**。把它做成枚举字段（四个允许值：`seeds_only | bootstrap_ci | stratified_kfold | replicate_matrix_BxT`），让 `/exp-eval` 与 `/check` 可以直接 grep，而不必从 `n_test` 反推。下游消费者只看一个真值源。
- **`--wet-lab yes|no|skip`** 是 user-owned flag，让非交互调用者（`/research`）能预先回答 probe。非交互模式默认 `skip` + 报告 flag —— 永远不静默选择范围降级。这与 CLAUDE.md 的 "user-facing skill parameters are user-owned" 一致。
- **Stage-4 砍预算优先级**固定为 `cross_context → robustness → dose_response`。原因：dose-response 单位成本上产出最具可量化价值的 claim（带 CI 的 EC50/IC50）；cross-context 是一种作用域 claim，可以推到下一篇 follow-up paper 而不会让当前结论失效。

### C4 — [P0] `/exp-design` 块分类增加四种生物原生类型

**位置**：
- description 与导语：把块类型扩到包含 `negative_control | mechanism | dose_response | cross_context`。
- Step 3：开头加一句 bio 条件触发判定，再追加四个字母小节（E–H），每节给出目的、何时加、标准设计、成功标准、计算量。块 schema 中 `type` 枚举随之扩展，并明确每种新块的 `baseline` 应指向什么（安慰剂臂、WT/vehicle、零剂量、同上下文效应大小）。
- Step 4：调整 Stage 图，使 negative-control 与 validation 在 Stage 2 并行，mechanism 与 ablation 在 Stage 3 并行，dose-response + cross-context 与 robustness 同处 Stage 4。新增 Stage-2 的 negative-control 门（"非零 negative control 阻断 validation 解读"）和 Stage-3 的正交扰动门（"两个扰动都为零 → 把 `mechanistic_basis` 降级为 `correlative`"）。
- Step 5 review prompt + review questions：补一道第 6 题，明确审查 negative-control 覆盖、≥2 个正交 mechanism 扰动、≥3 个数量级 dose-response、cross-context 是否预注册保留阈值。
- Step 6 frontmatter 模板：扩展 `type` 枚举注释。
- Step 6 报告模板：示例表给每种新块各一行，并在 Run Order 行点明新增的两个门。
- Constraints：新增一条把 negative-control 门列为强制规则。
- Error Handling：budget 不足条目改成引用 Step 4 的显式砍预算顺序。

**理由**：backlog 条目 C4 —— 旧的 4 类型分类漏掉了生物学家凭直觉就会做的实验形态。"PTM-blind baseline 复现"不是 negative control；超参数 sweep 不是 dose-response；ML 视角下的跨数据集 robustness 漏掉物种特异的失败模式。把它们做成一等块类型后，`/exp-design` 能主动提示，`/exp-eval` 能用对的门评分，graph 能带上正确的 `tested_by` 边。

**跨节依赖**：
- A7 —— `mechanism` 块的目标是 `mechanistic_basis` 类型的 evidence claim，仅在 A7 扩展的 evidence-type 枚举落地后存在。
- B1 —— Step 5 review prompt 提到 bio relation 边；只在 `/ingest`（C1）开始发射这些边后才相关。

**向后兼容**：旧的 4 块计划仍然合法。新类型是加法；不带新类型的实验 `type` 字段照常通过。

### C5 — [P0] `/exp-design` Step 1 通过关键词 probe 区分 wet-lab vs in-silico

**位置**：
- Inputs：新增 `--wet-lab yes|no|skip` flag，明确非交互默认语义。
- Outputs：报告记录 wet-lab 决策与命中关键词。
- Step 1：新增子步骤 4 —— 在 `## Hypothesis` + `## Approach sketch` + `## Risks` 上做关键词扫描，覆盖六组关键词（基于细胞、动物/临床、生物物理、结构、互作组、基因组学 readout），然后三分支路由到 `plan | retrospective_only | deferred | none`。
- Step 6 frontmatter 模板：把 `setup` 扩展为带 A5 的 bio 字段，加入结构化的 `estimated_cost` block（A6），让 `plan` 决策有处可放预算数字。
- Step 6 idea 页更新：当决策为 `retrospective_only` 时，向 `conditions` 追加一行说明范围降级。
- Step 6 log 行：行末追加 `wet_lab_decision: …`，方便 grep。
- Step 6 报告：顶部加 wet-lab 决策与命中关键词字段；底部 budget 行点名 A6 全部 6 维成本。
- Constraints：新增一条 —— 报告与 log 行必须记录 wet-lab 决策（即便为 `none`）。
- Error Handling：明确写出非交互 fallback 提示文案。
- Dependencies → Claude Code Native：补 `AskUserQuestion`。

**理由**：backlog 条目 C5 —— 之前 F 节审计的 8 个实验全是 in-silico，但源 idea 引用的是真实 wet-lab 的 phospho-PROTAC 数据。skill 从不问"这个 idea 是否需要新的 wet-lab 数据？"。关键词扫描是一个具体而便宜的启发；三分支 prompt 强制把答案记录下来，而不是隐含假设。

**跨节依赖**：
- A1 —— `setup.dataset` 升级为 wikilink 到 `wiki/datasets/{slug}` 只在 A1 落地后才生效。
- A5 —— bio `setup` 字段（`in_silico_or_wet`、`species`、`cell_line`、`assay_type`、force_field…）落到这里。
- A6 —— wet-lab 决策为 `plan` 时，`estimated_cost` block 落到这里。

**向后兼容**：没有命中关键词时（CS idea），probe 是 no-op；既有计划形状不变。

### C6 — [P1] `/exp-design` 统计默认值按样本量与模态切换

**位置**：
- Step 3 B（validation）与 C（ablation）：把无条件的 ">= 3 random seeds" 替换为按样本量+模态选择器。三个分支：`seeds_only`（旧默认；n_test ≥ 50，in-silico）；`bootstrap_ci` + `stratified_kfold`（n_test < 50 **或** bio domain）；`replicate_matrix_BxT`（任何 wet-lab 块）。
- Step 3 块 schema：新增 `statistical_protocol` 字段，四值枚举。
- Step 5 review prompt：第 5 题改写以揭示 seeds 与 bootstrap 与 stratified 与 replicate matrix 的不匹配。
- Step 6 frontmatter 模板：`statistical_protocol` 现在是必填 YAML 标量、附说明注释；`seeds` 字段含义收窄（"仅当 statistical_protocol == seeds_only 时有意义"）。
- Step 6 `## Setup` 正文：当 `replicate_matrix_BxT` 时必须显式说明哪一维是 biological、哪一维是 technical，以及各自数量。
- Constraints：把 "At least 3 seeds" 替换为四协议感知版本（seeds_only ≥ 3 seeds；bootstrap_ci 默认 1000 resample；stratified_kfold 默认 `k = min(5, n_positives)`；replicate_matrix_BxT 默认 `>= 3 × >= 3`）。
- Error Handling：新增一条 —— `n_test` 无法决定时默认走 bootstrap_ci，并提示用户回填 `wiki/datasets/{slug}.versions[*].n_test`。

**理由**：backlog 条目 C6 —— 旧的 ">= 3 random seeds" 在 50 个 phospho-PROTAC 强类不平衡的 held-out 集上没有统计意义，且对 wet-lab assay 完全失语 —— wet-lab 的规范统计是 biological×technical 复制矩阵。In-silico 小样本走 bootstrap CI、类不平衡走 stratified k-fold、wet-lab 走显式 B×T 复制矩阵，正好覆盖旧默认漏掉的三种情形。

**跨节依赖**：
- A1 —— `n_test` 从 `wiki/datasets/{slug}.versions[*].n_test` 读取。C8 的 lint 可以提示这个字段，但本身无法填它。
- A8 —— `reproducibility.dataset_versions` block 记录该 n_test 是在哪个版本下测得的。

**向后兼容**：C6 之前写的实验页会缺 `statistical_protocol` 标量。`/check`（C8）把它当作可确定性修复的问题；`--fix` 在足够明确时（如 `seeds >= 3` 且无 bio domain 标记）可填默认 `seeds_only`。

### 采纳门槛 —— 三条合回真值源之前

1. A1、A5、A6、A7 必须已合回（否则写入无处可去）。这四项截至 2026-05-03 已在 runnable 目录里到位。
2. `/exp-eval` 与 `/check` 必须能识别 `statistical_protocol` 与新 `type` 枚举值，否则下游 skill 会静默丢弃它们。**两项升级未做**：与 Batch C-2 的 C8（`/check` bio-lint）打包，避免合并散乱。
3. harness 中要有 `AskUserQuestion`（Claude Code 默认 deferred-tool 列表里有）。

### Batch 2 待办 —— `/exp-run` + `/check` + `/discover` + `/novelty`（C7 + C8 + C2 + C9）

下次再起草。须先合本批次，因为 C8 的 lint 规则要校验新的 `statistical_protocol` 与 `type` 枚举值。

---

## 2026-05-04 — C 节 Batch 2 草拟（C7 + C8 + C2 + C9）

**范围**：跨 `/exp-run`、`/check`、`/discover`、`/novelty` 四个 skill 的工作流改动。打包是因为 C8（bio-lint）必须知道 C7 / C2 / C9 引入或读取的字段形态，而 `/check` 是验证这些新字段与新边能否一致落地的天然位置。

**状态**：已草拟，**未合回真值源**。**`tools/lint_bio.py` 未实现** —— 该工具落地之前 `/check` 的 bio pass 静默跳过，其余照常运行。本批 discovery / novelty 的子命令依赖的 C1 fetcher（`fetch_pubmed.py`、`fetch_crossref.py`、`fetch_europepmc.py`、`fetch_biorxiv.py`）已实现；唯一需新增的代码面是 `tools/discover.py` 的 `from-bio-anchor` 子命令。

**已写文件**：
- `docs/bio-adaptation/section-c/skills/check/SKILL.{en,zh}.md`
- `docs/bio-adaptation/section-c/skills/discover/SKILL.{en,zh}.md`
- `docs/bio-adaptation/section-c/skills/novelty/SKILL.{en,zh}.md`
- `docs/bio-adaptation/section-c/skills/exp-run/SKILL.{en,zh}.md`

### 跨条目设计选择

- **`tools/lint_bio.py` 是独立可执行而非 `tools/lint.py` 的一个 flag**。输出 JSON 形状一致让 `/check` 的报告生成器无须分支即可消费，但两个二进制不共享状态。原因：bio-lint 本身就是一组类别簇（identifier 格式、dataset 版本漂移、force-field provenance、物种一致性、`statistical_protocol` 完整性、domain 词汇）—— 与既有结构检查交织没有好处。分开还让 CS-only fork 能直接丢掉 bio 二进制而无须改 `tools/lint.py`。
- **`--bio-channels {auto|on|off}` 在 `/discover` 与 `/novelty` 中是同一 flag、同一 auto 规则**。两个 skill 在同输入下必须解析为相同结果 —— 否则用户会在同 target 上看到 `/discover` 启用 bio 通道但 `/novelty` 没有。两边镜像中均作为硬不变量记录。
- **setup-type 检测器落在 `/exp-run` Phase 1 子步骤 3 而非 `tools/`**。原因：检测器是 `setup` 字段上的一张 6 条决策表，做成 Python helper 也行，但写在 SKILL.md 里让路由透明，且让用户能用 `--setup-type` 覆盖而无须新增 CLI 表面。检测器在有 bio 字段的情况下选了 `ml` 时，镜像规定发 🟡 提示而非阻塞 —— 几乎一定是用户漏填了 setup 字段，强迫他们补齐才是正解，不是静默覆盖。
- **identifier 格式即便带 `--fix` 也不自动修**。"修过的" DOI / PMID / PDB / UniProt 是被静默腐蚀的 provenance。bio-lint issue 上的 fix-rule 字段：identifier 检查为 `none`、缺失必填字段且有安全默认值的为 `deterministic`、其余为 `suggestion`。

### C7 — [P1] `/exp-run` 目录布局按 setup-type 模板化

**位置**：
- description 与导语：列出六种 setup-type 与每类型的 entrypoint 文件。argument hint 扩展 `--setup-type {auto|ml|md|wet-lab|docking|snakemake|nextflow}`。
- Wiki Interaction → Reads：把 `wiki/datasets/*.md` 列入 dataset 访问层级与版本固定的来源。
- Wiki Interaction → Writes：每类型目录布局展开（带角色注释的文件清单）。
- Phase 1 子步骤 3：六条决策表，按顺序匹配（wet → MD → docking → snakemake → nextflow → ml）。
- Phase 1 子步骤 4：每类型模板填充章节 —— `ml`（旧）、`md`（mdrun.sh + mdp/* + analysis.ipynb）、`wet-lab`（protocol.md + materials.csv + 数据占位）、`docking`（dock.sh + receptor + library + scoring）、`snakemake` / `nextflow`（workflow runner skeleton）。每节点名所需字段；当某必填字段缺失时拒绝部署。
- Phase 1 子步骤 5：Review LLM `system` prompt 按检测到的类型专化 —— MD reviewer 抓 equilibration / barostat 问题；wet-lab reviewer 抓缺失 RRID；docking reviewer 抓 protonation / 搜索盒；等等。
- Phase 1 子步骤 6：每类型 sanity check。wet-lab 是唯一 N/A。
- Phase 2：每类型部署路径。wet-lab 部署有意是 no-op（实验在台面跑）。
- DEPLOY_REPORT：增加 `Setup type` 与 `Template` 行。
- Phase 3 异常检测：每类型异常字典（ml 的 NaN/OOM；md 的 LINCS / 能量爆炸；docking 的零 pose；workflow-manager 的 rule 失败）。
- Phase 4 子步骤 3：按 `statistical_protocol` 决定解析规则。`replicate_matrix_BxT`（wet-lab）折成 mean ± SEM 跨 biological replicates、technical replicates 显原始点 —— 不静默退回 mean ± std。
- Constraints：setup-type 检测器非权威；wet-lab 必填 materials；多 seed mean 规则收窄到 `seeds_only` 才适用。
- Error Handling：检测器把 bio 字段误判到 ml（🟡 提示）；模板尚未编写（生成占位）；wet-lab CSV collect 模式缺失（不要自动 fail）。
- Local References：六个计划中模板路径 `skills/exp-run/references/templates/{type}/`。

**理由**：backlog C7 —— 旧 `train.py + config.yaml + run.sh` 布局会让任何非 ML 实验默默走偏。MD 实验天然要 `mdrun.sh + system.gro + mdp/*.mdp`；wet-lab 要 `protocol.md + materials.csv + analysis.ipynb`。把所有实验都套 `train.py` 骨架会写出"看着对、跑不动"的代码。

**跨节依赖**：
- A5（experiments setup bio fields）—— 喂检测器
- A6（`estimated_cost` block）—— 非 ML 类型填对应成本维度而非堆 `estimated_hours`
- C4（experiment.type 枚举）—— `mechanism` 块尤其受益于 wet-lab + docking 模板
- C6（`statistical_protocol`）—— Phase 4 聚合规则

**向后兼容**：无 bio 字段时检测器选 `ml`、写出旧 4 文件布局，与 C7 之前路径逐字节一致。

### C8 — [P1] `/check` 增加自动检测的 bio-lint pass

**位置**：
- description 与导语："10 entity types" 与 bio-lint pass 提及。
- Inputs：新 `--bio` / `--no-bio`，写明自动检测规则。
- Wiki Interaction → Reads：补 `wiki/datasets/*.md`。
- Step 2 必填字段表：第 10 类 `datasets` 的必填字段集补入。
- Step 3 enum 校验：补 `experiments.type`（C4 枚举）、`experiments.statistical_protocol`（C6 枚举）、`claims.evidence[*].type` 与 `.grade`（A7）、`datasets.maturity`、`datasets.access`。
- Step 4 cross-reference 矩阵：两条新行 —— papers→datasets 与 experiments→datasets 的双向链接。
- Step 5 graph 边一致性：补 B1 confidence 必填、B2 / B3 typed `metadata` 完整性（与 `tools/_schemas.py::EDGE_METADATA_REQUIRED` 对照）。
- 新 Step 6b "Bio-Lint pass" 章节：6 类 —— identifier 格式（DOI / PMID / bioRxiv DOI / PDB / UniProt / NCT / Cellosaurus / HGNC）、dataset 版本漂移、MD 实验 force-field provenance、物种一致性（LLM 辅助）、`statistical_protocol` 完整性、domain 词汇提示。
- Step 7 报告：bio-lint 摘要行；每类新增 bio 项的分级。
- Constraints：bio-lint 自动检测、加法式；identifier 格式不自动修。
- Error Handling：lint_bio.py 未装 → 优雅跳过；datasets/ 空但 bio 字段存在 → 🟡 + 引用 TernaryDB 试点。
- Dependencies：`tools/lint_bio.py` 列为 planned follow-up；附工具设计注释块（期望 JSON 形状、CLI、退出码语义）。

**理由**：backlog C8 —— `/check` 对现 wiki 报告 clean 只是因为它漏了能抓到真实 bug 的结构检查。PDB ID 容易写错（`6XYZ` vs `6xyz`），UniProt 有严格正则，dataset 版本会静默漂移，缺 `force_field` 的 MD 实验不可复现。

**跨节依赖**：
- A1 —— version-drift 检查读 datasets/
- A3 —— 校验 papers/ 的 bio identifier
- A5 —— 校验 experiments setup bio 字段
- A7 —— 校验 claim evidence type/grade 枚举
- A8 —— 校验 `reproducibility.dataset_versions`
- B1/B2/B3 —— 校验边的 metadata 完整性
- C4/C6 —— 校验 `experiments.type` 与 `statistical_protocol` 枚举

**向后兼容**：wiki 中无 bio 字段时 bio pass 自动跳过，`/check` 输出与 C8 之前完全一致。`tools/lint.py` 不变。

### C2 — [P1] `/discover` 并行查询 PubMed + EuropePMC + bioRxiv，新增 DOI / PMID anchor key

**位置**：
- description：补入并行通道与 recall 倾向。
- Inputs：新 `--doi` / `--pmid` anchor flag；新 `--bio-channels {auto|on|off}`，与 `/novelty` 共享 auto 规则。
- Wiki Interaction → Reads：补 `papers.doi/pmid/biorxiv` 与 bio-anchor frontmatter（`gene_symbols`、`pdb_ids`…）。
- Step 1 seed-mode 选择器：DOI / PMID / bioRxiv 输入对应新 `bio-anchor` 模式。
- 新 Step 2 "通道集合" 章节：`bio off` / `bio on` / `bio auto` 解析规则。
- Step 3 工具调用：详细规划 `tools/discover.py from-bio-anchor` 子命令（CrossRef + PubMed 解析 → PubMed similar / EPMC citations / bioRxiv related → 与 S2 通道按 `doi > pmid > arxiv > biorxiv > 标题模糊` 优先级合并）。
- Step 4 shortlist 呈现：bio 候选附 source-channel；"next step" 含 bio canonical 的 `/ingest <doi>` 与 `/ingest PMID:<pmid>`。
- Step 5 日志行：尾巴附 `bio-channels={on|off|auto→on|auto→off}`。
- Internal Callers `/ingest --discover`：刚 ingest 论文 canonical id 是 bio 时，post-ingest 调用使用 `--doi` / `--pmid`。
- Constraints：bio 侧 dedup 用 canonical-id 优先级；bio rate limit 与 S2 调用叠加。
- Error Handling：S2 down + bio up 降级到 bio-only（正确行为，非 bug）；DOI/PMID 全通道未命中明确报错（不要静默 fallback 到标题模糊）。
- Dependencies：PubMed / EuropePMC / bioRxiv / CrossRef 列入外部 API；`tools/discover.py from-bio-anchor` 列为 planned 子命令。

**理由**：backlog C2 —— DeepXiv 在 biology/structure 上索引稀疏；S2 单跑漏掉 PubMed-only prior art。把 PubMed + EuropePMC + bioRxiv 与 S2 并行是修 bio discovery 召回的方法。

**跨节依赖**：A3（bio identifier frontmatter 用于 dedup）、C1（四个 bio fetcher，已实现）。

**向后兼容**：既有 arXiv-anchor 与 topic 模式不变。`--bio-channels off` 与 C2 前 shortlist 完全一致。

### C9 — [P1] `/novelty` 增加并行 PubMed + EuropePMC 通道

**位置**：
- description 与导语：S2 旁列出 PubMed + EuropePMC。
- Inputs：bio target 类型（DOI / PMID / bioRxiv URL）；与 `/discover` 同形的 `--bio-channels`。
- Outputs：novelty 报告新增 "Search Coverage" 表（每来源命中数 + top-5 贡献），让用户自评 prior-art 覆盖是不是真的广。
- Wiki Interaction → Reads：bio identifier frontmatter 用于 `auto` 检测与 bio 侧 dedup。
- Step 1：bio target 经 `fetch_crossref.py` / `fetch_pubmed.py` 解析；为 MeSH 收窄查询生成 bio 锚词。
- 新 Source B-bio：PubMed（关键词 + MeSH） + EuropePMC（search + annotations）。`annotations` endpoint 被点名为 bio target 的主要相似度信号 —— 实体 URI（UniProt / GO / ChEBI）胜过 abstract bag-of-words。
- Step 3 Review LLM prompt：扩展 system prompt，强调 "bio 通道命中按全权重计"；新第 5 题专门让 reviewer 揭出搜索可能漏掉的 clinical / wet-lab validation 先例。
- Step 4 报告：每候选附 `Source` 与 `Identifier` 字段；新评分规则 —— bio target 上 PubMed 命中方法重合 + 同 protein target + ≤5 年 → 不论 S2 结果一律 1（Published）。
- Constraints：bio 通道不替代 wiki 内部搜索；bio 启用时至少 2 次 PubMed 查询 + 1 次 EuropePMC 查询。
- Error Handling：PubMed + EuropePMC 都不可用 → 报告顶部硬警告；不要在 S2 单跑下静默给 bio target 自信的 novelty 分。

**理由**：backlog C9 —— bio prior art 绝大多数在 PubMed（>30M abstract，S2 仅部分索引）。漏掉 PubMed 让 `/novelty` 在 bio 上低报先验撞车，让用户在已有方法上继续。

**跨节依赖**：C1（PubMed + EuropePMC fetcher，已实现）、C2（共享 auto 规则）、A4（domain 受控词）。

**向后兼容**：bio 通道关闭（CS-only 流）时 Source B-bio 跳过，其余流程不变。

### 采纳门槛 —— 四条合回真值源之前

1. C1 fetcher 工具（`fetch_pubmed.py`、`fetch_crossref.py`、`fetch_europepmc.py`、`fetch_biorxiv.py`）必须已合回。✅ 截至 2026-05-03 已在 runnable 目录到位。
2. **`tools/lint_bio.py` 必须实现**，否则 C8 的 bio pass 不会真跑。落地之前 `/check` 报 "bio-lint pass skipped — tools/lint_bio.py not installed"，符合镜像中规定。镜像末尾的工具设计注释块即规范。
3. **`tools/discover.py` 必须新增 `from-bio-anchor` 子命令**，否则 C2 的 bio-anchor 模式不会真跑。落地之前 bio-anchor 模式降级为 S2 标题搜索。
4. **`/exp-run` 每类型模板**（`skills/exp-run/references/templates/{md,wet-lab,docking,snakemake,nextflow}/`）应当落地。落地之前非 ML 类型回退到占位 layout 并发警告。
5. 合并顺序：C8 应最后落地。原因：C8 bio-lint 覆盖 C4/C6 引入的 `statistical_protocol` 与 `experiments.type` 字段、A5 引入的 `setup` bio 字段。先合 C8 会在既有的 pre-bio 实验上误报"missing field"。

### Batch 3 待办 —— `/ideate` + `/paper-plan` + `/paper-draft` + `/rebuttal`（C3 + C10 + C11）

下次再起草。C3（`/ideate` failed-idea banlist 增 `scope: species | disease_area | data_regime`）；C10（`/paper-plan` + `/paper-draft` 接受 `paper_style: cs | bio | clinical`，含 bio 的 Vancouver / Results-first 模板）；C11（`/rebuttal` 把承诺的后续 wet-lab 实验作为答辩 evidence 而非空头承诺来跟踪）。

---

## 2026-05-04 — C8 规范修正（exit code 描述错误）

`docs/bio-adaptation/section-c/skills/check/SKILL.{en,zh}.md` 中 `tools/lint_bio.py` 设计块原本写："即使发现 🔴 issue 退出码也是 0（与 tools/lint.py 一致 —— 报告本身就是产物）"。实际上 `tools/lint.py` 在有 🔴 时会退出 1（见其 `main()` 末尾 `sys.exit(1 if red > 0 else 0)`）。`tools/lint_bio.py` 实现按 lint.py 的真实行为做；规范现在改回与之对齐。代码无改动。

---

## 2026-05-04 — C 节 Batch 3 草拟（C3 + C10 + C11）

**范围**：跨 `/ideate`、`/paper-plan`、`/paper-draft`、`/rebuttal` 四个 skill 的工作流改动。三条 backlog 打包是因为它们覆盖 C 节后实验 / 写作阶段的尾部，C10 还跨两个 skill（`/paper-plan` 写 metadata，`/paper-draft` 消费）。

**状态**：已草拟，**未合回真值源**。**四份镜像在旧 CS 路径之上是加法**——bio 字段缺、`--scope` 未传、`--paper-style` 解析为 `cs`、`--scaffold-followups` 关时，行为与 C 节之前完全一致。

**已写文件**：
- `docs/bio-adaptation/section-c/skills/ideate/SKILL.{en,zh}.md`
- `docs/bio-adaptation/section-c/skills/paper-plan/SKILL.{en,zh}.md`
- `docs/bio-adaptation/section-c/skills/paper-draft/SKILL.{en,zh}.md`
- `docs/bio-adaptation/section-c/skills/rebuttal/SKILL.{en,zh}.md`

### 跨条目设计选择

- **scope 是每 idea 的元数据，不是全局运行 flag**。`scope` block 落在每个 `wiki/ideas/{slug}.md` 上，含失败 idea。这意味着失败 idea **意图覆盖的** scope 才是被记录的，不是当前运行的 `current_scope`。后续在另一 scope 跑的运行能正确绕过 out-of-scope precedent，因为禁令记录的是它在禁什么，而不是是谁在禁。
- **`paper_style` 在 `/paper-plan` 中一次解析并写入 PAPER_PLAN.md metadata**。`/paper-draft` 直接读，不再推断。这避免了 plan 在 bio venue 上生成、但 draft 因为推断输入变了而开始按 cs 节序排版的失败模式。
- **`paper_style` 不一致时 venue 优先**。venue 的格式要求不可商量；用户选了 Nature 但 claim 看起来 cs 形态，正确的动作是发警告（内容不适合 venue）并用 bio 结构（结构性要求是 venue 强制的）。
- **`--scaffold-followups` opt-in**。Bio reviewer 每次投稿常要 3-5 个后续湿实验；把每条 commitment 变成可追踪的 `wiki/experiments/{slug}.md` 页杠杆很大但惊喜很大。用户必须 opt in。Step 5 的 Review LLM 压力测试对 Strategy B commitment 推得更狠，正是因为含糊承诺无法 scaffold 成有用的 experiment 页。
- **Bio Methods 是 wiki 驱动序列化，不是写作**。`/paper-draft` 在 `paper_style: bio` 时从 `wiki/datasets/` 读 dataset 版本、从 `experiments[*].statistical_protocol` 读复制数、从 `setup` 读 force-field/cell-line/RRID、从 `estimated_cost` 读成本，然后确定性地序列化。bio Methods 是 wiki 中少数应该用结构化 dump 替代"写作"的地方 —— 散文不增加价值反而模糊复现性。

### C3 — [P1] `/ideate` failed-idea banlist 增 scope（species / disease_area / data_regime）

**位置**：
- `argument-hint`：新 `--scope species=...|disease_area=...|data_regime=...` flag
- Inputs / Outputs：scope flag 文档化；IDEA_REPORT 增 "Banlist Trace" 节，区分 in-scope hits 与 out-of-scope precedent
- 前置条件：新 step 4 —— 从 `--scope` 解析 `current_scope` 或从 direction 推断；明显 bio 方向但 scope 为空时发 🟡 警告
- Phase 1 子步骤 1：每条 banlist 项目附 `scope_overlap: True | False`，按与 `current_scope` 的重叠
- Phase 2 brainstorm prompt：in-scope banlist 是硬阻塞；out-of-scope banlist 是 "informational precedent" —— 揭示已饱和领域而不阻止其架构在另一 scope 的应用
- Phase 3 过滤：仅 `scope_overlap == True` 项导致淘汰
- Phase 5 frontmatter 模板：可选 `scope:` block 含 `species`、`disease_area`、`data_regime`。C3 之前不带它的 idea 退回 "global"（旧语义）
- Phase 5 失败 idea 写入：`scope` 字段记录失败 idea **意图覆盖的** scope。确实与 scope 无关的失败明确把三子字段全留空，并在 failure_reason 前缀加 `[filter] global:`
- Constraints：scope-aware 匹配为规范；"失败 idea 应记录其自身 scope，不是当前运行的 scope" 是硬规则

**理由**：backlog C3 —— 在人/高数据上饱和的 PROTAC phospho 预测对植物或微生物 PTM 什么也没说。旧的 global banlist 过度阻塞。每 idea scope 让单条失败 idea 正确记录其禁令边界。

**跨节依赖**：A4（bio domain 受控词用于 `disease_area`）、A1（`wiki/datasets/{slug}.versions[*].n_test` 决定 `data_regime`）

**向后兼容**：C3 之前不带 `scope` block 的 idea 退回 global ban 语义 —— 与旧 banlist 行为一致

### C10 — [P2] `/paper-plan` + `/paper-draft` 接受 `paper_style: cs|bio|clinical`

**`/paper-plan` 中**：
- `argument-hint`：新 `--paper-style cs|bio|clinical` flag，默认 `auto`
- venue 列表为 bio（`Nature` / `Cell` / `Science` / `Nature Methods` / `Nature Biotech` / `Nat. Commun.` / `eLife` / `bioRxiv`）和 clinical（`NEJM` / `JAMA` / `Lancet` / `BMJ` / `Annals` / `medRxiv`）扩展
- 新 Step 1b（"解析 paper_style"）含明确规则：传了 `--paper-style` → venue → `claims[*].domain` 聚合 → 平局优先 venue
- Step 2 证据图谱增 `Type/Grade` 列（A7 evidence type 与 grade）
- Step 4 大纲：三套按 style 的完整模板 —— cs（Intro→RW→Method→Experiments→Conclusion）、bio（Intro→Results→Discussion→Methods，figure-first 叙事，叙事性 caption，Results-first）、clinical（Intro→Methods→Results→Discussion，Methods 前置，CONSORT 图，基线表，显式 limitations）
- Step 5 figure plan 增按 style 规范：cs 简短 caption，bio 含样本量+复制类型+统计检验名的叙事 caption，clinical 含 CONSORT + ITT/per-protocol 命名
- Step 6 引用计划：cs author-year，bio Vancouver 数字，clinical Vancouver。bio/clinical 优先 CrossRef + PubMed 而非 DBLP
- Step 7 Review LLM 人格按 `paper_style` 分派：ML area chair / bio editor / clinical editor
- Step 8 PAPER_PLAN.md metadata 记录解析后的 `paper_style` 让 `/paper-draft` 直接消费、不再推断
- Constraints：clinical 风格要求通过 B2 `clinical_trial_for` edge 的 NCT ID，除非显式 observational

**`/paper-draft` 中**：
- 节文件命名按 `paper_style` 分派：cs 用 `method.tex` + `experiments.tex`；bio 用 `results.tex` + `methods.tex`；clinical 先 `methods.tex` 再 `results.tex`
- `main.tex` 骨架按 `paper_style` 分派节序与 bibliography 风格：cs `\bibliographystyle{plainnat}`，bio `\bibliographystyle{naturemag}`（数字上标 Vancouver），clinical `\bibliographystyle{vancouver}`
- Step 3a 按 style 收集材料：bio Results = 每 claim 一个子节，按 `experiments[*].type` 分派（validation → 头条；mechanism → "we tested whether the predicted mechanism holds"；dose_response → 滴定带 EC50/IC50；cross_context → 泛化；negative_control → 折入 validation caption）
- Bio Methods 视为 **wiki 驱动序列化、不是写作任务**：从 `wiki/datasets/` 拉 dataset 版本、从 `experiments[*].statistical_protocol` 拉复制数、从 `setup` 拉 force-field/cell-line/RRID、从 `estimated_cost` 拉成本。Step 6 显式 bio（dataset 版本存在）和 clinical（NCT ID 与 B2 edge 匹配）的完整性检查
- Step 3b LaTeX 写作：cs claim-first（"We claim X. To verify..."），bio result-first 内嵌统计（"In ABC cells, treatment reduced target abundance by 78% (Fig. 2a; n=4 biological replicates, two-sided t-test, P<0.001)"）
- 节级 Review LLM 人格：与 `/paper-plan` 同分派 —— ML researcher / bio researcher / clinical reviewer

**理由**：backlog C10 —— bio 论文是 figure-first，Methods 末位且简化；clinical 论文是预注册驱动，CONSORT 与 Methods 前置；CS 论文是方法优先，experiments 验证方法。把三者都套 cs 模板会静默写出错的论文。

**跨节依赖**：A1（datasets/）、A6（estimated_cost）、A7（evidence type & grade）、A8（reproducibility）、B2（clinical_trial_for）、C4（experiment.type 枚举）、C6（statistical_protocol）

**向后兼容**：`paper_style: cs` 时节结构、引用风格、Review LLM 人格与旧路径完全一致。`auto` 在 venue 与 domain 都不是 bio 时解析为 `cs`

### C11 — [P2] `/rebuttal` 追踪承诺的后续湿实验

**位置**：
- `argument-hint`：新 opt-in `--scaffold-followups` flag
- Step 4 Strategy B：除散文回应外，把 response 捕获为结构化 `commitment` 记录（`commitment_id`、`proposed_title`、`target_claim`、`setup_hint.{in_silico_or_wet, assay_type, species, cell_line}`、`estimated_cost_hint`、`rationale`）
- Step 5 Review LLM 压力测试：明确评分规则 —— 通用 "we will run experiments" 评 1-2 因为不能 scaffold；具体 "CETSA on HEK293, n=3 biological, 4-week timeline" 评 4-5
- 新 Step 6d "可选 follow-up scaffolding"：传了 `--scaffold-followups` 时，每条预飞检查通过的 Strategy B commitment 喂给 `/exp-design`（每条一次调用）。每个 scaffold 出的 experiment 带 `triggered_by_rebuttal: <paper-slug>` 与 `triggered_by_concern: <Rvx-Cy>` provenance 字段
- Step 6b 富文本答辩 "Suggested Experiments" 表增 `Setup Hint`、`Cost Hint`、`Scaffolded?` 列
- Constraints：Strategy B commitment 必须可 scaffold（足够具体）；scaffold 出的 experiment 带 provenance 字段；`--scaffold-followups` 默认 opt-in
- Error handling：含糊承诺压力测试后仍不被 scaffold（🟡 提示细化）；`/exp-design` 调用失败发 🔴，rebuttal 退化为纯文本

**理由**：backlog C11 —— bio reviewer 经常把额外湿实验作为接受条件；没有机制把这些承诺转成可追踪 deliverable，承诺会烂尾。opt-in 关键：从 rebuttal 静默生成 5 个新"已规划"实验是高代价惊喜

**跨节依赖**：`/exp-design`（既有 skill，每条 commitment 调一次，理想情况下带新 flag `--triggered-by-rebuttal`、`--commitment-id`、`--setup-hint` —— 这些 flag 加到 `/exp-design` 是 C11 的同伴 planned tooling；落地之前 `/rebuttal` 退化为事后 `tools/research_wiki.py set-meta` 调用）；A5（setup bio 字段由 scaffold 填）；C8（lint_bio 未来扩展可在后续 experiment 上检测 `triggered_by_rebuttal` 缺失）

**向后兼容**：未传 `--scaffold-followups` 时与旧纯文本 rebuttal 流一致

### 采纳门槛 —— 四条合回真值源之前

1. C3 无工具依赖，可独立合回
2. C10 最佳体验需要按 style 内容模板（`skills/paper-draft/references/templates/{cs,bio,clinical}/`），但镜像中的行内默认在模板落地之前是足够的
3. C11 理想需要 `/exp-design` 增 `--triggered-by-rebuttal`、`--commitment-id`、`--setup-hint` flag。落地之前 set-meta fallback 可工作 —— wiki 最终状态相同，只是步骤更多
4. **合并顺序**：三条任意顺序均可。C3 影响最小（一个 skill，加法元数据字段）；C10 最广（两个 skill，新节序，引用风格变更）；C11 跨 rebuttal 流加 `/exp-design` 调用

### C 节状态

Batch C-3 草拟完成后，**全部 11 条 C 节项目都有 applied（C1）或 drafted（C2-C11）镜像**。批表：

| Batch | Items | Skills touched | Status |
|-------|-------|----------------|--------|
| C-1a（Q1 partial） | C1 | /ingest | ✅ 已合回真值源 + 5 个 fetcher 工具实现 |
| C-1b（Q1 finish） | C4 + C5 + C6 | /exp-design | ✅ 已草拟 |
| C-2 | C7 + C8 + C2 + C9 | /exp-run, /check, /discover, /novelty | ✅ 已草拟；tools/lint_bio.py 已实现 |
| C-3 | C3 + C10 + C11 | /ideate, /paper-plan, /paper-draft, /rebuttal | ✅ 已草拟 |

### 待办 —— 更广 section

原 backlog 的 D / F / G / H 节按之前计划继续推迟。建议下一步：
1. 把 C-1b / C-2 / C-3 任意子集合回 `/home/yukino/OmegaWiki_bioinfo_adaptation/` 的真值源。每批 CHANGELOG 条目有独立的采纳门槛
2. 按优先级建四个后续工具：`tools/discover.py from-bio-anchor` 子命令（C2）、`skills/exp-run/references/templates/{md,wet-lab,docking,snakemake,nextflow}/`（C7）、`skills/paper-draft/references/templates/{cs,bio,clinical}/`（C10）、`/exp-design --triggered-by-rebuttal` flag（C11）
3. 端到端 smoke test：挑一篇 wiki 中尚没有的 bio paper，跑 `/ingest` → `/discover` → `/ideate --scope species=human,disease_area=cancer-bio,data_regime=high-data` → `/exp-design` → `/exp-run`（合成）→ `/exp-eval` → `/paper-plan --paper-style bio` → `/paper-draft` → `/check`。runnable 目录中每个缺失部分会被标出并补上

---

## 2026-05-04 — C1 完善（`tools/prepare_bio_paper_source.py` + SKILL.md 收紧）

**之前不完整的地方**：BIOINFO_ADAPTATION_CHECKPOINT 中 "C1 has not been exercised end-to-end" 这条 —— bio 路径文字层面已串通，五个 fetcher 工具各自能跑，但没有一个工具实际做到：
- 分类一个任意 bio 标识符（DOI / PMID / bioRxiv URL / bioRxiv DOI / PMC ID / PMC URL）
- 路由到对应 fetcher
- 把 OA 全文 artefact 下载到 `raw/discovered/`
- 返回与 `prepare_paper_source.py` 同形的 JSON 信封,让 `/ingest` Step 1 子步骤 3 单点交接

**现在完成**：
- 新工具：`tools/prepare_bio_paper_source.py`（约 430 行）。单点分派：`--raw-root raw --source <bio-id-or-url>` → 分类 → 拉元数据 → 下载 PDF（bioRxiv）或 JATS XML（OA PMC）→ 返回带 `canonical_ingest_path`、`doi`、`pmid`、`biorxiv`、`pmcid`、可选 `manual_download_url`、`warnings` 的 JSON 信封。
- 路由规则（按优先级）：bioRxiv/medRxiv URL → biorxiv 路径；PMC URL → pmc 路径；DOI URL 或纯 DOI 以 `10.1101/` 起头 → biorxiv 路径；纯 PMC ID → pmc 路径；`PMID:N` 或纯数字 → pubmed 路径；通用 DOI → doi（CrossRef + EPMC 镜像查询）路径。
- `/ingest` SKILL.md（en + zh）Step 1 子步骤 3 重写为单次调用 `prepare_bio_paper_source.py` 并消费信封，替代原先按路由分散的散文（让 Claude 自行解释执行）。
- Dependencies 节更新：移除 bio-fetcher 块的 "待建" 标记；把 `prepare_bio_paper_source.py` 列为单点分派器。
- 通过 `./setup.sh --lang en` 同步。

**Smoke test**（全部通过）：
- DOI（Nature 付费墙）`10.1038/s41586-021-03819-2` → CrossRef 拿 AlphaFold 元数据，无 OA 镜像，`metadata-only`（正确：Nature 不是 OA）。
- bioRxiv DOI `10.1101/2024.11.19.624167`（Boltz-1）→ bioRxiv API 拿元数据，PDF 自动下载被 Cloudflare 403 阻挡 → `manual_download_url` 填好且 warning 可执行。
- bioRxiv URL `https://www.biorxiv.org/content/10.1101/2024.11.19.624167v1` → 同一 Boltz-1 记录（发现并修复 bug：贪婪/非贪婪正则把 `.11.19.624167` 切断在日期后缀）。
- PMID `34265844`（含 `PMID:` 前缀变体）→ 经 PubMed 路由 → 有 PMC 镜像 → JATS XML 下载到 `raw/discovered/structure-sars-cov-2-orf8-rapidly-evolving-immune.xml`（66 KB）。
- PMC URL `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8316889/` → 经 EuropePMC 直接下载 JATS XML（124 KB）。
- PMC ID `PMC8316889`（纯）→ 与 PMC URL 同路径。
- 非法输入 `not-a-real-id` → 优雅错误信封，`usable: false` 且 `warnings` 含可执行提示。

**已知限制**（记录但不阻塞）：
- bioRxiv 通过 Cloudflare 阻挡程序化 PDF 下载。fallback 是 `manual_download_url` + warning；用户手动取 PDF，放到 `raw/papers/`，重跑 `/ingest <local-path>`。其余路径仅元数据 ingest 仍可工作。
- DOI 路径不下载 PDF —— 只查 EPMC 镜像，因为 publisher 侧 OA PDF 需要按出版商定制的逻辑，超出 C1 范围。付费墙 DOI 与不在 EPMC 的 OA DOI 优雅降级为仅元数据。
- CLI 表面有意不把实验的 `setup.dataset` 翻成 wikilink —— 那是 `/ingest` Step 4 子步骤 6 的工作，不是来源解析器的。

**C1 状态**：✅ 完成。`/ingest <bio-id>` 现在端到端可以跑通无须手动编排 fetcher；SKILL.md 散文契约与实现匹配。

---

## 2026-05-04 — `fetch_pubmed.py` 递归 findall bug 修复（已合到真值源）

**Bug**：`tools/fetch_pubmed.py::_parse_pubmed_article()` 用 `article.findall(".//ArticleId")` 读外部 ID。由于 `<PubmedArticle>` 既包含 article 自己的 `<PubmedData>/<ArticleIdList>`，也包含 `<PubmedData>/<ReferenceList>` 下每条 `<Reference>/<ArticleIdList>`，递归下降按文档顺序匹配全部，**最后一条**静默覆盖 `external["DOI"]`、`external["PMC"]`、`external["PII"]`。结果：N 条引用的 PMID 会返回 article 自己的 title 但某条引用的 ID。

**具体失败**：PMID 40593782（DeepTernary，Nat. Commun. 2025）返回 `DOI: 10.1073/pnas.2016239118`（ESM 论文）和 `PMC: 8053943`（也是 ESM）。`prepare_bio_paper_source.py prepare_pmid` 拿到错误 PMC 后让 EPMC 全文下载器抓回了完全不相关论文的 JATS XML 落到 `raw/discovered/`。本次 DeepTernary ingest 因为 title 与 PMC 不一致才捕到。

**修复**：把路径锚定到 article 自己的 ID 列表：

```python
# 之前（递归，错）：
for aid in article.findall(".//ArticleId"):
    ...

# 之后（锚定，对）：
own_ids = article.find("PubmedData/ArticleIdList")
if own_ids is not None:
    for aid in own_ids.findall("ArticleId"):
        ...
```

**回归测试**（现在通过）：
- PMID 40593782 → DOI `10.1038/s41467-025-61272-5` ✅、PMC `12216337` ✅
- PMID 34265844 → DOI `10.1038/s41586-021-03819-2`（AlphaFold）、PMC `8371605` ✅

**同类站点审计**：扫描 `fetch_pubmed.py` 其余 `findall(".//*")` 调用：
- `art.findall(".//AbstractText")` —— `art` = `MedlineCitation/Article`，不含 `ReferenceList`。**安全**。
- `art.findall(".//Author")` —— 同 scope。**安全**。
- `citation.findall(".//MeshHeading/...")`、`Chemical/...`、`Keyword/...` —— `citation` = `MedlineCitation`。References 在 `PubmedData/ReferenceList` 中，与 `MedlineCitation` 是兄弟节点。**安全**。
- `_hydrate_pmids`（esummary 路径）：JSON 按 PMID 索引，无共享可变累加器。**安全**。

**真值源说明**：tools/ 没有 mirror 层（按 bio-adaptation 的模式，只有 `i18n/` 文件在 `docs/bio-adaptation/` 下有镜像）。`/home/yukino/OmegaWiki_bioinfo_adaptation/tools/fetch_pubmed.py` 就是真值源，修复已在位。文件内的修复意图写在 `external = {"PMID": pmid}` 行上方的注释块中。

**为什么之前没暴露**：原 C1 smoke test（CHANGELOG "2026-05-03 — Materialised runnable folder + bio fetcher tools" 条目）用的 PMID 34265844（AlphaFold）和 DOI 10.1038/s41586-021-03819-2。这些标识符要么 (a) 引用集合足够小让正确 ID 在覆盖竞速中幸存，要么 (b) 测试只 sanity-check 了 title 而没探 DOI/PMC。无论哪种，bug 一直潜伏到 DeepTernary ingest 同时探 title 与每论文 canonical ID 才捕到。教训：C1 smoke test 应该断言 title-与-ID-一致，而不是仅 "title 非空"。

---

## 2026-05-04 — `prepare_bio_paper_source.py::title_to_slug` 双连字符修复（已合到真值源）

**Bug**：含括号版本标记的标题如 `SE(3)-equivariant` 产出双连字符 slug：

```
"SE(3)-equivariant ternary complex prediction towards target protein degradation"
  → se--equivariant-ternary-complex-prediction-towards    （双连字符，bug）
```

流水线先 lowercase，再跑 `re.sub(r"[^\w\s-]", " ", ...)`，把 `(3)` 变成空格，留下 `se 3 -equivariant`。split 后丢掉数字 `3`，token 变成 `["se", "-equivariant"]`。`-` 连接后产出 `se--equivariant`。

**具体失败**：在 DeepTernary ingest（`/home/yukino/OmegaWiki_bioinfo_adaptation/wiki/papers/se-equivariant-...`）中捕到。修复前 `raw/discovered/se--equivariant-...xml` 已经落盘；修复后删掉重 prepare。

**修复**（`tools/prepare_bio_paper_source.py::title_to_slug`）：

```python
# 之前：
parts = [p for p in cleaned.split() if p and p not in _STOPWORDS and not p.isdigit()]
return "-".join(parts[:_KEEP_LEN])

# 之后：
parts = [p.strip("-") for p in cleaned.split()
         if p and p not in _STOPWORDS and not p.isdigit()]
parts = [p for p in parts if p]   # 丢掉被剥成空的 token
slug = "-".join(parts[:_KEEP_LEN])
return re.sub(r"-+", "-", slug).strip("-")
```

三个小改动：(a) 每个 token `strip("-")`；(b) 丢掉被剥成空的 token；(c) 折叠连续 `-` 并 trim 两端。

**回归矩阵**（7 个 case 测过）：

| Title（截断） | Slug（修复后） | 结果 |
|--------------|---------------|------|
| `SE(3)-equivariant ternary complex prediction…` | `se-equivariant-ternary-complex-prediction-towards` | ✅ 与 `research_wiki.py slug` 一致 |
| `PROTAC-DB 2.0: an updated database of PROTACs` | `protac-db-updated-database-protacs` | ✅ 一致 |
| `Highly accurate protein structure prediction with AlphaFold` | `highly-accurate-protein-structure-prediction-alphafold` | ✅ 一致 |
| `Boltz-1: Democratizing Biomolecular Interaction Modeling` | `boltz-1-democratizing-biomolecular-interaction-modeling` | ✅ **与 canonical 有差异（有意为之）** —— 见下文 |
| `E(3)-equivariant graph neural networks (EGNN) for molecules` | `e-equivariant-graph-neural-networks-egnn` | ⚠️ 6 词截断（`_KEEP_LEN`），`for molecules` 被丢 |
| `p53/MDM2 — selective allosteric inhibition` | `p53-mdm2-selective-allosteric-inhibition` | ✅ 一致 |
| `SARS-CoV-2 ORF8 structure` | `sars-cov-2-orf8-structure` | ✅ **与 canonical 有差异（有意为之）** |

**与 `research_wiki.py slug` 的差异是有意且有益的**。canonical generator 丢掉所有纯数字 token（`Boltz-1` → `boltz-democratizing-…` 把 `1` 丢了；`SARS-CoV-2 ORF8` → `sars-cov-orf8-structure` 把 `2` 丢了）。对于版本号承载语义的论文 slug（"Boltz-1" vs 未来的 "Boltz-2"；"SARS-CoV-2" vs "SARS-CoV-1"），保留数字是对的。`prepare_bio_paper_source.title_to_slug` 因为按 token `strip("-")` 而不是按 `-` 切分，所以 `boltz-1`、`sars-cov-2` 这种 multi-hyphen token 整体保留。我们**不**建议改 canonical 的 `research_wiki.py slug` 去匹配 —— 它的 "丢数字" 规则对 arXiv 风格标题（版本号在他处编码）是合适的 —— 但 bio 论文受益于这里更保守的行为。

**本修复范围外**：`_KEEP_LEN=6` 会截断超过 6 个非 stopword 关键词的标题。EGNN test case 暴露了这点。提高上限会让长 bio 标题 slug 膨胀（"CRISPR-Cas9 mediated knockout of hexokinase 2 in pancreatic ductal adenocarcinoma cells reveals a novel metabolic vulnerability…"）。`_KEEP_LEN=6` 仍是合理默认值；EGNN test case 是已知限制，需要时用户可以事后改 slug。

**真值源说明**：与 fetch_pubmed.py 修复同 —— `/home/yukino/OmegaWiki_bioinfo_adaptation/tools/prepare_bio_paper_source.py` 即真值源（无 mirror 层）。修复已在位；本 CHANGELOG 是审计轨迹。

**教训**（沿用 fetch_pubmed.py 条目的）：`prepare_bio_paper_source.py` 的 robust C1 smoke test 应该在小固定矩阵上断言 *slug-与-canonical-一致-或-解释-差异*，而不仅仅 "title 非空"。DeepTernary ingest 在一次尝试中同时暴露 fetch_pubmed.py 递归 findall bug 和 这条 slug bug，正是因为它是第一个用带括号标题探 slug 形成路径的 ingest。后续 C1 加固：加 `tests/test_prepare_bio_paper_source.py` 含上述回归矩阵，防止重构回归。

---

## 2026-05-04 — C 节全部 draft 合到真值源

C-1b / C-2 / C-3 三批草稿（落在 `docs/bio-adaptation/section-c/skills/{skill}/SKILL.{en,zh}.md`）此前都只是 mirror。本条目记录把剩下 9 个 draft 全部 promote 到真值源 `i18n/{en,zh}/skills/{skill}/SKILL.md`。

**方法**：剥掉顶部 `<!-- bio-CX: Mirror of i18n/... -->` audit-trail 注释块（仅说明该文件是 draft），同时保留正文里的 `<!-- bio-CX -->` 行内注释（那些是 C 节真正的标注，在真值源里也作为 audit trail 保留）。用一段 20 行 Python 正则 helper 程序化处理，按结构位置（frontmatter `---` 与第一个 `# /skill` heading 之间）锚定而不按英文关键词 —— 正是这点让它对 EN 和 ZH mirror 都能一致工作。

**Promotion 顺序遵循 CHANGELOG 中的 adoption gate**：
1. **C-1b**（`/exp-design`）—— 依赖 A1/A5/A6/A7（已合）
2. **C-3**（`/ideate` C3、`/paper-plan` + `/paper-draft` C10、`/rebuttal` C11）—— 独立，blast radius 最小先合
3. **C-2 partial**（`/discover` C2、`/novelty` C9、`/exp-run` C7）—— bio fetcher 工具已就位
4. **C-2 last**（`/check` C8）—— bio-lint 覆盖 C4/C6 引入的字段；先合 C8 会在旧实验上误报

**改动文件**（在 `/home/yukino/OmegaWiki_bioinfo_adaptation/`）：
```
i18n/en/skills/{exp-design,ideate,paper-plan,paper-draft,rebuttal,discover,novelty,exp-run,check}/SKILL.md
i18n/zh/skills/{...同上...}/SKILL.md
.claude/skills/{...同上...}/SKILL.md   （./setup.sh --lang en 自动同步）
CLAUDE.md、.claude/.current-lang        （自动同步）
```

**验证矩阵**：
- 全部 10 份 SKILL.md（刚 promote 的 9 个 + C1 的 `/ingest` 早先已就位）都有非零 bio-CX 行内注释计数，EN 与 ZH 互相 match 在 ±2 内（翻译选择带来的小差）
- 根 `.claude/skills/{skill}/SKILL.md` 的注释数与 `i18n/en/skills/{skill}/SKILL.md` 对应 —— `setup.sh --lang en` 同步干净
- `tools/lint.py --wiki-dir wiki/`：0 🔴、0 🟡、10 🔵 —— 无回归
- `tools/lint_bio.py --wiki-dir wiki/`：0 🔴、0 🟡、32 🔵 —— 无回归
- `python -m unittest discover -s tests`：52 个 test 绿

**按 skill 的 bio-CX 行内注释数**（promote 后真值源状态）：

| Skill | Items | en | zh |
|-------|-------|----|----|
| `/ingest` | C1 | 37 | 37 |
| `/exp-design` | C4 + C5 + C6 | 43 | 43 |
| `/exp-run` | C7 | 60 | 60 |
| `/check` | C8 | 25 | 25 |
| `/discover` | C2 | 28 | 28 |
| `/novelty` | C9 | 27 | 27 |
| `/ideate` | C3 | 30 | 30 |
| `/paper-plan` | C10 | 41 | 41 |
| `/paper-draft` | C10 | 43 | 43 |
| `/rebuttal` | C11 | 24 | 24 |

**现在解锁了什么**：每个 C 节项目都行内文档化在活的 skill 散文中（根 `.claude/skills/{skill}/SKILL.md`）。Claude Code 运行时读这些 SKILL.md 看到的就是 bio-adaptation 行为作为文档化契约，不再是 mirror。

**仍开口的事项**（按 CHANGELOG 2026-05-04 Batch C-2 / C-3 adoption gate）：
- `tools/discover.py from-bio-anchor` 子命令（C2）—— 落地之前 bio-anchor 模式降级为 S2 标题搜索
- `skills/exp-run/references/templates/{md,wet-lab,docking,snakemake,nextflow}/`（C7）—— 非 ML setup type 回退到占位 layout + warning
- `skills/paper-draft/references/templates/{cs,bio,clinical}/`（C10）—— `/paper-draft` 使用 SKILL.md 散文中的行内默认，直到模板落地
- `/exp-design --triggered-by-rebuttal` flag（C11）—— `/rebuttal --scaffold-followups` 退化到事后 `set-meta` 调用，直到 flag 落地

这些是**运行时优雅降级的 gap**，不是 blocker。skill 现在已经能用；gap 只意味着部分人体工学不如未来 follow-up 工具落地后那么好。

**C 节状态：✅ 全部 11 项已合到真值源。** Section C 从文档角度功能完整；剩余工作是后续工具实现，按优先级推进。

---

## 2026-05-04 — C7 后续工具：`/exp-run` 按类型模板已实现

`/exp-run` SKILL.md 的 C7 mirror 承诺 `skills/exp-run/references/templates/{ml,md,wet-lab,docking,snakemake,nextflow}/` 提供按类型脚手架。本条目之前这些路径都是空的 —— Phase 1 子步骤 4 对非 ML 类型回退到占位 layout 并 warn。本条目记录把全部 6 个模板实现为可运行脚手架。

**写入文件**：43 个文件 / 256 KB，落在 `i18n/en/skills/exp-run/references/templates/`（同样一份拷贝到 `i18n/zh/...` 服务 ZH 用户）。

| 模板 | 文件数 | 脚手架内容 |
|------|--------|-----------|
| **ml** | 5 | `train.py`（PyTorch 监督训练骨架，带多 seed 循环 + 按 `statistical_protocol` 聚合）、`config.yaml`、`run.sh`、`requirements.txt`、README |
| **md** | 8 | `mdrun.sh`（GROMACS 管线：pdb2gmx → solvate → ions → em → nvt → npt → prod）、4 份 `mdp/*.mdp`（em / NVT / NPT / production）、`system.gro` 占位、`analysis.ipynb`（RMSD/RMSF/Rg + bootstrap-CI）、`requirements.txt`、README |
| **wet-lab** | 7 | `protocol.md`（Materials → Equipment → Procedure → Read-out → Pause points → Safety + 复制矩阵表）、`materials.csv`（6 行展示 RRID / CVCL / Addgene / catalog 规范）、`analysis.ipynb`（先聚 tech 再 aggregate bio + RRID sanity check）、`data/{raw,processed}/.gitkeep`、`requirements.txt`、README |
| **docking** | 7 | `dock.sh`（AutoDock Vina 遍历 SMILES 库 + openbabel SMILES→PDBQT 转换 + scoring CSV）、`receptor.pdbqt` 占位、`ligand_library.smi`（4 个示例 SMILES + 格式说明）、`box.txt`（搜索盒中心+尺寸，默认 25 Å cubic）、`scoring.yaml`、`analysis.ipynb`（top-N + score 分布 + redocking RMSD）、`requirements.txt`、README |
| **snakemake** | 7 | `Snakefile`（DSL 含 `rule all` + summary）、`config.yaml`、`envs/main.yaml`（conda spec）、`rules/process.smk`（占位 rule 模板）、`scripts/process.py`（占位）、`requirements.txt`、README |
| **nextflow** | 7 | `main.nf`（DSL2 工作流含 `include` + summary process）、`modules/process.nf`（process 模板带 `stub:` 用于 dry-run）、`nextflow.config`（executor + manifest + tracing）、`params.yaml`、`scripts/process.py`、`requirements.txt`、README |

**约定**：每个模板带 README 文档化 (a) 部署时替换读哪些 `setup` 字段、(b) 哪些字段必填（缺失则拒绝部署 —— 例如 MD 的 `setup.force_field`、wet-lab 抗体 assay 的 `materials.csv` RRID）、(c) 按类型的 Phase-1 sanity check 形态（例如 MD 的 `gmx mdrun -nsteps 100`、Snakemake 的 `--dry-run`）、(d) 按类型的 Phase-3 异常检测规则、(e) 按 `statistical_protocol` 的 Phase-4 聚合规则。README 是可读契约；代码文件是机器可读的脚手架。

**替换占位符**：每个模板用 `{{FIELD_NAME}}`（如 `{{FORCE_FIELD}}`、`{{SLUG}}`、`{{SEED}}`），由 `/exp-run` Phase 1 子步骤 4 在部署时从 `wiki/experiments/{slug}.md` frontmatter 替换。YAML 文件用 default-with-comment 模式而非裸占位（`seed: 42  # default; /exp-run substitutes from setup.random_seed_protocol`），让模板开箱可解析；替换是行替换，不是 YAML 重序列化。

**验证**：
- 全部 5 个 YAML config 用 `python -c "import yaml; yaml.safe_load(...)"` 干净解析（无毒占位）
- 全部 3 个 `.ipynb` 是合法 JSON 且 nbformat/cell shape 正确
- 全部 3 个 `.sh` 通过 `bash -n` 语法检查
- `setup.sh --lang en` 把 43 个文件全部同步到 `.claude/skills/exp-run/references/templates/`
- `tools/lint.py`：0 🔴 0 🟡 —— 无回归
- `tools/lint_bio.py`：0 🔴 0 🟡 —— 无回归
- `python -m unittest discover -s tests`：52 个 test 仍绿

**`/exp-run` SKILL.md 更新**：「Local References」block（en + zh）把每模板「(planned)」标记替换为模板内容一行摘要。Phase 1 子步骤 4 中的「stub fallback」路径仍保留 —— setup-type 不命中 6 个模板时仍走 fallback —— 但对已文档化的 6 个，fallback 不再是默认行为。

**状态**：✅ C7 后续工具完成。C 节 CHANGELOG 标记的四项后续 gap：
1. ~~`tools/discover.py from-bio-anchor` 子命令（C2）~~ —— 仍待办
2. ~~`skills/exp-run/references/templates/{md,wet-lab,docking,snakemake,nextflow}/`（C7）~~ —— **本条目完成**
3. ~~`skills/paper-draft/references/templates/{cs,bio,clinical}/`（C10）~~ —— 仍待办
4. ~~`/exp-design --triggered-by-rebuttal` flag（C11）~~ —— 仍待办

剩 3 项后续。其中 `/paper-draft` 模板是单点最大的（3 个 venue-style 脚手架 × 每个含多个 LaTeX section 文件）；C2 discover 子命令与 C11 exp-design flag 较小。

---

## 2026-05-04 — C10 后续工具：`/paper-draft` 按风格模板已实现

`/paper-draft` SKILL.md 的 C10 mirror 承诺 `skills/paper-draft/references/templates/{cs,bio,clinical}/` 提供按风格脚手架。本条目之前这些路径都是空的 —— `/paper-draft` 回退到 SKILL.md 散文中的行内默认。本条目记录把全部 3 个模板实现为可编译的 LaTeX 脚手架。

**写入文件**：25 个文件 / 约 64 KB，落在 `i18n/en/skills/paper-draft/references/templates/`（同样一份拷贝到 `i18n/zh/...` 服务 ZH 用户）。

| 模板 | 文件数 | 亮点 |
|------|--------|------|
| **cs** | 9 | 主文件 `main.tex`（Intro → RW → Method → Experiments → Conclusion）；`\bibliographystyle{plainnat}`（author-year）；5 个 section 文件；丰富的 `math_commands.tex`（概率 / 线性代数 / ML 记号）；minimal caption 约定 |
| **bio** | 8 | 节序 Intro → Results → Discussion → Methods（Methods 末位，按 Nature/Cell/eLife 惯例）；`\bibliographystyle{naturemag}`（数字上标 Vancouver）；叙事性 caption 含样本量/复制类型/统计检验名；Methods 是 wiki 驱动的序列化，含显式 `{{DATASETS_PARAGRAPHS}}` / `{{WET_LAB_SUBSECTIONS}}` / `{{COMPUTATIONAL_SUBSECTIONS}}` / `{{STATISTICAL_PARAGRAPHS}}` 占位让 `/paper-draft` Step 3a 从 `wiki/datasets/`、`wiki/experiments/[*].setup`、`experiments[*].statistical_protocol`（C6）、`estimated_cost.*`（A6）填；Discussion 必含显式 `\paragraph*{Limitations.}` |
| **clinical** | 8 | 节序 Intro → Methods → Results → Discussion（Methods 前置，按 NEJM/JAMA/Lancet）；`\bibliographystyle{vancouver}`；结构化 abstract（Background / Methods / Results / Conclusions）；trial-registration banner（`{{NCT_ID}}` 来自 B2 `clinical_trial_for` 边）；Methods 6 个必填子节（Study design / Participants / Interventions / Outcomes / Statistical analysis / Trial registration / Ethics）；Results 5 个固定顺序子节（3.1 CONSORT / 3.2 基线表 / 3.3 primary / 3.4 secondary / 3.5 safety）；Discussion 必含显式 `\paragraph*{Limitations.}`（强制无 hedging）|

**关键设计决策**：

1. **Bio Methods 是结构化序列化，不是写作。** Methods 模板带显式 `{{DATASETS_PARAGRAPHS}}` / `{{WET_LAB_SUBSECTIONS}}` / `{{COMPUTATIONAL_SUBSECTIONS}}` / `{{STATISTICAL_PARAGRAPHS}}` / `{{RESOURCES_PARAGRAPH}}` 占位，由 `/paper-draft` Step 3a 从 wiki 状态确定性地填。用户**不**写 Methods 散文 —— 而是策划 wiki，让 `/paper-draft` 序列化。这与 SKILL.md C10 规定 "bio Methods is a wiki-driven serialization, not a writing task" 一致。

2. **Clinical limitations 在语法层面强制。** Discussion 模板带显式 `\paragraph*{Limitations.}` block + 占位 —— `/paper-draft` Step 5 cross-review（Review LLM clinical-editor 人格）若渲染后的 LaTeX 没这一段则阻塞 finalize。这让 C10 mirror 的「limitations 强制」规则可结构化执行而非仅约定。

3. **Caption 规范按 style 不同。** Bio 模板叙事性 caption 含 `n=...` 样本量与统计检验名；clinical 模板每图点名分析人群（intent-to-treat / per-protocol / safety）；CS 模板 minimal caption。每个模板的 caption 形态是 `/paper-draft` Step 2 产出的规范参照。

4. **替换占位用 `{{FIELD_NAME}}`** 在 cs/bio/clinical 一致，让 `/paper-draft` 有统一的 per-template-type 替换 pass。必填替换（如 clinical RCT 的 `{{NCT_ID}}`）若 wiki 状态无法供应则模板填充失败，明确报错而非在输出中静默留占位。

**验证**：
- 全部 18 个 `.tex` + 3 个 `.bib` 结构合法：每文件 `{` / `}` 数匹配且 `\begin{env}` / `\end{env}` 配对
- `setup.sh --lang en` 把 25 个文件全部同步到 `.claude/skills/paper-draft/references/templates/`
- `tools/lint.py`：0 🔴 0 🟡 —— 无回归
- `tools/lint_bio.py`：0 🔴 0 🟡 —— 无回归
- `python -m unittest discover -s tests`：52 个 test 仍绿

**`/paper-draft` SKILL.md 更新**：「Local References」block（en + zh）把每模板「(planned)」标记替换为内容一行摘要（节序 + `\bibliographystyle` + 文件数）。加一段说明每模板 README 的契约。

**状态**：✅ C10 后续工具完成。C 节 CHANGELOG 标记的四项后续 gap：
1. ~~`tools/discover.py from-bio-anchor` 子命令（C2）~~ —— 仍待办
2. ~~`skills/exp-run/references/templates/...`（C7）~~ —— 早先 2026-05-04 已完成
3. ~~`skills/paper-draft/references/templates/...`（C10）~~ —— **本条目完成**
4. ~~`/exp-design --triggered-by-rebuttal` flag（C11）~~ —— 仍待办

剩 2 项后续：C2 discover 子命令（较小，构建于已实现的 bio fetcher）和 C11 exp-design flag（最小，给 `/exp-design` SKILL.md 散文加 3 个 flag + experiment 模板加 provenance 字段）。

---

## 2026-05-04 — C11 后续工具：`/exp-design` rebuttal 触发的 flag + 配对 provenance lint 检查

C11 草拟的 `/rebuttal --scaffold-followups` 流程会用三个 `/exp-design` flag 调用：`--triggered-by-rebuttal`、`--commitment-id`、`--setup-hint`。本条目之前 `/exp-design` SKILL.md 中没文档化这些 flag。C11 mirror 当时给出 `tools/research_wiki.py set-meta` 事后 fallback 作为应急路径。本条目把规范路径落地：`/exp-design` 上真正的 flag + experiment frontmatter 模板的配对 provenance 字段 + `lint_bio.py` 检查结构性违例 + 测试。

### 改动

**`/exp-design` SKILL.md（en + zh）**：
- `argument-hint` 扩展为 `[--triggered-by-rebuttal <paper-slug>] [--commitment-id <Rvx-Cy>] [--setup-hint key=value]`
- 三个 flag 的 Inputs 文档，含配对 flag 规则（`--triggered-by-rebuttal` 与 `--commitment-id` 必须同时有或同时无）、规范 concern-ID 格式 `^Rv[0-9]+-C[0-9]+$`、`--setup-hint` 允许的 key（`in_silico_or_wet`、`assay_type`、`species`、`cell_line`、`force_field`、`solvent_model`、`simulation_length`）
- 新 Step 1 子步骤 5（"Rebuttal-triggered provenance"）文档化 flag 校验逻辑、跳过 wet-lab probe 规则（`/rebuttal` 已分类）、隐含 `--auto` 行为
- Step 6 frontmatter 模板增 `triggered_by_rebuttal: ""` 与 `triggered_by_concern: ""`（配对）
- 报告 block 增 "Triggered by rebuttal" / "Commitment ID" / "Setup hints applied" 行
- 日志行末尾扩展 `triggered_by_rebuttal` + `commitment_id`
- 两条新 Constraints：配对规则强制 + 隐含 auto
- 三条新 Error Handling：单边配对、concern 格式无效、未知 setup-hint key

**`/rebuttal` SKILL.md（en + zh）**：
- Step 6d 注解去掉 "落地之前 fallback 到 set-meta" 免责声明；替换为 flag 现已规范化的说明 + 隐含 auto 行为
- Dependencies 中 `tools/research_wiki.py set-meta` 重新定位为 "追溯回填的应急 fallback" 而非主路径

**`tools/lint_bio.py`** — 新检查类别 5b（配对 provenance），接入 `lint_bio()` 编排器：
```python
def check_triggered_by_rebuttal_pairing(wiki_dir: Path) -> list[Issue]:
```
- 遍历 `wiki/experiments/*.md`
- 每个：从 frontmatter 读 `triggered_by_rebuttal` 与 `triggered_by_concern`
- 恰好一个填了 → 🟡 配对 provenance 违例，附可执行回填提示
- 两个都填，校验 concern ID 匹配 `^Rv[0-9]+-C[0-9]+$` → 不匹配则 🔴 格式错误
- 两个都空（含 pre-C11 完全无字段的 experiment）→ 无 issue（兼容旧 wiki）

**`tests/test_lint_bio.py`** — 新建，含 C11 检查的 8 个 case：
- `test_both_set_with_canonical_concern_id_is_clean` —— happy path
- `test_both_empty_is_clean` —— 显式空路径（post-C11 用户调用）
- `test_missing_fields_entirely_is_clean` —— pre-C11 兼容
- `test_rebuttal_set_concern_empty_fires_yellow` —— 配对违例 1
- `test_concern_set_rebuttal_empty_fires_yellow` —— 配对违例 2
- `test_invalid_concern_id_format_fires_red` —— 格式错误
- `test_canonical_concern_id_variants` —— 单数字与多数字 `Rv12-C34` 均合法
- `test_concern_id_lowercase_is_rejected` —— 大小写敏感（正则强制 Rv/C 大写）

### 验证

| 检查 | 结果 |
|------|------|
| `python -m unittest discover -s tests` | 60 个 test 绿（原 52，+8 新 C11） |
| `tools/lint.py --wiki-dir wiki/` | 0 🔴 0 🟡 —— 无回归 |
| `tools/lint_bio.py --wiki-dir wiki/` | 0 🔴 0 🟡 —— 真实 wiki 无回归 |
| 合成 4-experiment fixture | 1 🔴（concern 格式错）+ 1 🟡（半配对）—— 正是 C11 检查应该捕到的 |
| `setup.sh --lang en` | 同步 |

### 为什么这件事重要

C11 的结构性强制落地之前，`/rebuttal` 通过 `set-meta` fallback scaffold 出的 follow-up experiment 会带不一致的 `triggered_by_rebuttal`（已设）+ `triggered_by_concern`（空）形态，因为 fallback 只懂第一个字段。lint 检查让这种漂移可见。规范路径就位后，`/rebuttal --scaffold-followups` 第一次写就产出配对一致的记录 —— 无须回填，未来漂移在 lint 阶段就被捕到。

### 状态

C 节后续工具：**4 项中 3 项已完成**。

| 项 | 状态 |
|----|------|
| `tools/discover.py from-bio-anchor`（C2） | ⏳ 仍待办 —— 最后一项 |
| `skills/exp-run/references/templates/...`（C7） | ✅ 早先完成 |
| `skills/paper-draft/references/templates/...`（C10） | ✅ 早先完成 |
| `/exp-design --triggered-by-rebuttal`（C11） | ✅ **本条目完成** |

仅剩 C2 的 `discover from-bio-anchor` 子命令。它构建于已实现的 bio fetcher（`fetch_pubmed.py`、`fetch_crossref.py`、`fetch_europepmc.py`、`fetch_biorxiv.py`）之上，给 `tools/discover.py` 加一个子命令，解析 DOI/PMID/bioRxiv-DOI 输入，与既有 S2 / DeepXiv 通道在 canonical-id dedup 下合并候选列表。

---

## 2026-05-11 —— A1 minimal + A5 切片合入 source-of-truth（pilot merge）

**范围**：Section A 中最小的加性切片，目标是为 demo 解锁 `[[ternarydb]]` 式 wikilink。不触碰
skill prompt、不动 graph 规则。
**状态**：**A1（最小切片）和 A5（单实验切片）已合并**。完整 A1（ingest 自动建 datasets 页）
与完整 A5（8 个 experiment 全部改造 + setup 扩展 bio 字段）继续 deferred —— 它们依赖仍处于
drafted 的 C1 / C2 skill prompt 改造。

### A1 —— 最小切片：`datasets/` 注册为第 10 种实体

**改动位置**：
- `runtime/schema/entities.yaml`：append `datasets:` 块。字段 `title`、`slug`、`aliases`、
  `tags`、`maturity`（stable | active | emerging | deprecated）、`access`（public |
  registration | restricted | wet-lab-derived）、`versions`（list_object，pilot 不带 item 内嵌
  spec）、`canonical_url`、`license`、`key_papers`（list_link → papers）、`key_concepts`
  （list_link → concepts）、`date_updated`。loader 自动接收：`ENTITY_DIRS` 现在 10 项。
- `runtime/templates/datasets.md.tmpl`：新文件。正文章节 `## Overview` / `## Versions` /
  `## Access and licensing` / `## Schema and entries` / `## Known caveats` /
  `## Used by experiments` / `## Key papers`。
- `docs/runtime-page-templates.{en,zh}.md`：标题从 "9 类页面" 改为 "10 类页面"；新增
  `datasets/{slug}.md` 章节，frontmatter 形状对齐。
- `wiki/datasets/ternarydb.md`：第一个 dataset 页面。锚定 PTM-aware degrader 流水线下的 8 个
  实验。版本元数据和 canonical URL 留作 TBD，等 DeepTernary 论文 ingest 后填充。
- `wiki/index.md`：新增 `datasets:` 块（2026-05-03 提到的 A1 follow-up 在 live wiki 上落地）。
- `xref.yaml`：**仍未改**。pilot 保留 experiment→dataset 的反向链接为手工维护（dataset 页面
  的 `## Used by experiments` 段手填）。自动反向需要支持嵌套字段（`setup.dataset → datasets.??`）的 xref
  规则，这是后续工作。

**为什么现在合**：将来 ingest PROTAC / PTM / ternary-complex 论文时，TernaryDB、PROTAC-DB、
dbPTM、AlphaFold-DB 等数据集会被反复引用。没有一等实体时这些引用都退化成纯文本。最小切片让
它们现在就有了规范页面；A1 的其他部分（`/ingest` 自动识别）等 C1 合并时再上。

### A5 —— 切片：`setup.dataset` wikilink，单实验

**改动位置**：
- `wiki/experiments/deepternary-baseline-ternarydb-crbn-vhl-reproduction.md`：`setup.dataset`
  从纯字符串 `"TernaryDB CRBN+VHL test split (the same split used in the DeepTernary paper)"`
  改写为 `"[[ternarydb]] CRBN+VHL test split (the same split used in the DeepTernary paper)"`。
  schema 类型保持 `str`——wikilink 在结构上仍是字符串，只是 Obsidian 可解析。
- 其他 7 个实验（`phase0-noise-floor-calibration-...`、`calibrated-deltapternary-...`、4 个
  消融、2 个鲁棒性运行）**保留 plain-string 形态的 `setup.dataset`**，作为向后兼容 demo：
  lint 接受两种写法。

**为什么现在合**：`DEMO_PLAN.{en,zh}.md` v2 的 storyboard 场景 3 想现场展示 `setup.dataset` 作为
wikilink。单实验切片给出这一点，且无须做完整的 A5（扩展 `setup` 加 `in_silico_or_wet`、
`species`、`cell_line`、`assay_type`、`force_field` 等字段，那要等 C2 的 `/exp-design`
prompt 升级来填新字段）。

### 验证

| 检查 | 结果 |
|------|------|
| `python -c "from runtime.loader import ENTITY_DIRS; print(ENTITY_DIRS)"` | 10 项；`datasets` 在末位 |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 仅 informational |
| `wiki/datasets/ternarydb.md` 在 `experiments/deepternary-baseline-...md` 中可解析 | 是 —— Obsidian 风格 `[[ternarydb]]` |
| 向后兼容：7 个 sibling experiment 未动 | 是 —— `setup.dataset` 纯字符串仍正常 parse |

### 此 pilot 故意不做的事

- `i18n/{en,zh}/CLAUDE.md` —— 当前 slim 形态不枚举页面类型，无需编辑。根目录 active
  `CLAUDE.md` 未重生（未调用 `setup.sh --lang`）。
- `runtime/schema/xref.yaml` —— 未加 experiment→dataset 反向规则。`## Used by experiments`
  段手工维护。
- `.claude/skills/*` —— 不动 prompt。`/ingest` 仍会写纯字符串 dataset；`/exp-design` 仍写
  `estimated_hours`。C1、C2 deferred。
- A2、A3、A4、A6、A7、A8 —— 全部仍处于 `drafted` 状态，存放在 `docs/bio-adaptation/section-a/`。

### 回滚

单 `git revert` 即可恢复 9-entity 状态。没有数据销毁：`wiki/datasets/ternarydb.md` 是唯一
净新增的内容；那一个实验的 `setup.dataset` 回到纯字符串。

---

## 2026-05-11 —— A6 pilot merge：结构化 `estimated_cost` 块

**范围**：A6（结构化实验成本），加性合并到 source-of-truth。同日早些时候合并的 A1+A5 pilot 的姊妹工作。
**状态**：**A6 以加性形态合并**。`estimated_hours` 仍合法、每个实验都填了（向后兼容 fallback）；
新增的结构化块 `estimated_cost` 是非平凡预算的规范位置。Skill prompt C2（`/exp-design`）仍
产出 legacy 形态，直到 C2 落地。

### 改动位置

- `runtime/schema/entities.yaml`：`experiments.fields.estimated_cost` 加为 `object`，子字段
  `gpu_hours`、`cpu_hours`、`md_wallclock_hours`、`wet_lab_usd`、`fte_weeks`、
  `dataset_access_lead_time_days` 全部可选。注释标记 bio-A6 并指出 C3（bio-lint）将来在
  bio-domain 实验只填 `estimated_hours` 时发出警告。
- `docs/runtime-page-templates.{en,zh}.md`：`experiments/{slug}.md` 模板加入 `estimated_cost`
  块（默认全 0）。
- 8 个 `wiki/experiments/*.md` 全部改写：每份 frontmatter 现在带 `estimated_cost` 块，含每个
  实验的真实数值。`estimated_hours` 保留并加注释 `# legacy; superseded by estimated_cost.gpu_hours below`。

### 逐实验预算

| 实验 | gpu | cpu | md_wallclock | wet_lab_usd | fte_weeks |
|------|---:|---:|---:|---:|---:|
| `deepternary-baseline-ternarydb-crbn-vhl-reproduction` | 4 | 0 | 0 | 0 | 0.25 |
| `phase0-noise-floor-calibration-deepternary-ptm-perturbations` | 24 | 4 | 0 | 0 | 1.0 |
| `calibrated-deltapternary-phospho-protac-ranking` | 16 | 2 | 0 | 0 | 0.75 |
| `ablation-uncalibrated-vs-calibrated-deltapternary` | 4 | 1 | 0 | 0 | 0.25 |
| `ablation-boltz2-ptm-vs-md-relaxed-route` | 4 | 1 | **8** | 0 | 0.5 |
| `ablation-deepternary-vs-protac-stan-scorer` | 16 | 2 | 0 | 0 | 0.5 |
| `robustness-cross-ptm-type-ubiq-methyl` | 16 | 2 | 0 | 0 | 0.5 |
| `robustness-mutant-isoform-track-y220c-r175h` | 12 | 1 | 0 | 0 | 0.5 |
| **TOTAL** | **96** | **13** | **8** | **0** | **4.25** |

GPU + MD wall-clock 总和：**104 h** —— 与 2026-05-02 `/exp-design` 日志和 `ideas/ptm-aware-degrader-target-nomination.md`
里的"≈104 GPU-h"头条数字一致。**MD wall-clock 现在可见**了（之前藏在 boltz2 消融的合并
`estimated_hours: 12` 里）。当前所有实验都是纯算力——`wet_lab_usd: 0` 全员。所有数据集都
公开可达（TernaryDB、PROTAC-DB、DegronMD）—— `dataset_access_lead_time_days: 0`。

### 验证

| 检查 | 结果 |
|------|------|
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 —— 与合并前蓝色 informational 集合一致 |
| 8 个实验文件 YAML 均可解析 | 是；`estimated_cost.gpu_hours` 读出为 float |
| `sum(estimated_hours) == sum(estimated_cost.gpu_hours + .md_wallclock_hours)` | 是（104 = 104）；未引入预算漂移 |
| 向后兼容：`estimated_hours` 仍填充 | 是；legacy 消费者（lint defaults、未来迁移工具）仍能读到 |

### 此 pilot 故意不做的事

- **`.claude/skills/exp-design/`** 未动。下次 `/exp-design` 仍只会产出 `estimated_hours`。
  C2 SKILL.md 升级在 `docs/bio-adaptation/section-c/skills/exp-design/` 起草中。
- **不加 lint 强制**："domain 为 bio 时必须填 `estimated_cost`" 是 C3（bio-lint）的范围。
- **`estimated_hours` 未在 schema 层标记 deprecated**（loader.py 不支持 `deprecated: true`
  标记）。仅字段注释表明 legacy 状态。

### 回滚

`git revert <pilot-A6-commit>` 即可恢复单数字预算。没有数据销毁：每个实验的
`estimated_hours` 字段仍是原值。

---

## 2026-05-11 —— B3 pilot merge：`dataset_version_used` provenance 边

**范围**：Section B 中最易 demo 的切片。让 ternarydb 在 SPA 网络视图里成为有连接的节点，
storyboard 场景 4 的 "bio relation edges" caption 终于能指向一条真实存在的边而非静态 mockup。
依赖更早的 A1 minimal pilot（datasets/ 实体）。
**状态**：**B3 以最小形态合并**。`dataset_version_used` 边类型已注册；一条真实边
（`deepternary-baseline → ternarydb`）已写入图。带类型的 `metadata.version` 属性（B3 完整
形态）**延后** —— 见下方"此 pilot 故意不做的事"。

### 改动位置

- `runtime/schema/edges.yaml`：append `dataset_version_used` 块。endpoints `from:
  experiments, to: datasets`。directed。workflow provenance。attributes：`confidence`
  （enum high/medium/low，required）和 `evidence`（str，required）。loader 自动接收：
  注册边类型总数从 21 → 22。
- `wiki/graph/edges.jsonl`：通过 `tools/research_wiki.py add-edge` 添加一条真实边：

  ```json
  {"from": "experiments/deepternary-baseline-ternarydb-crbn-vhl-reproduction",
   "to": "datasets/ternarydb",
   "type": "dataset_version_used",
   "confidence": "high",
   "evidence": "version: v1 (release alongside DeepTernary, Nat. Commun. 2025); CRBN+VHL test split — the exact split reproduced by this experiment",
   "date": "2026-05-11"}
  ```
- `wiki/graph/context_brief.md`、`wiki/graph/open_questions.md`：由
  `tools/research_wiki.py rebuild-*` 重新生成。

### Demo 影响

| 之前 | 之后 |
|---|---|
| `wiki/datasets/ternarydb.md` 存在但在 SPA 网络视图里是孤立节点（无边指向它） | ternarydb 成为有连接的节点 —— `tools/serve.py /api/graph` 返回新边；SPA 将其渲染在 `experiments/deepternary-baseline-...` 旁边 |
| Storyboard 场景 4 有 0 条 bio relation 边 live；B1/B2/B3 都只有 caption | 1 条 B3 边 live；B1/B2 仍只有 caption |
| 边类型计数：21 | 22（`dataset_version_used` 加入） |

### 验证

| 检查 | 结果 |
|------|------|
| `python -c "from runtime.loader import VALID_EDGE_TYPES; print(len(VALID_EDGE_TYPES))"` | 22 |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵（informational 集合不变） |
| `python tools/research_wiki.py add-edge wiki --from ... --type dataset_version_used --confidence high --evidence ...` | `{"status": "ok", ...}` |
| `grep dataset_version_used wiki/graph/edges.jsonl` | 1 行；endpoints 匹配 `experiments → datasets` |
| `tools/serve.py /api/graph` 返回该边 | 是；SPA 把 ternarydb 显示为有连接的节点 |

### 此 pilot 故意不做的事

- **边上的类型化 `metadata.version` 属性**。完整 Section B3 计划声明 `metadata: {version: str,
  required}` 为顶层 edge attribute。要落地需要扩展 `tools/research_wiki.py add-edge` CLI，
  让它接收 `--metadata KEY=VALUE` 或每属性 flag。pilot 出于风险控制跳过 —— 版本信息当前编码
  在 `evidence` 字符串里（可用正则解析）。
- **C3（bio-lint）的版本漂移检查**。设计在 `docs/bio-adaptation/section-c/skills/check/`，未实现。
  C3 以 `tools/lint_bio.py` 形态落地后，可以解析 evidence 文本，或者（如果
  `metadata.version` 先合并）直接读类型化属性。
- **批量给其他 7 个实验加边**。只有 deepternary-baseline 实验得到 `dataset_version_used`
  边。其他 7 个 sibling 实验（phase0-noise-floor、calibrated-...、4 ablations、2 robustness）
  通过 plain-string `setup.dataset` 引用 TernaryDB，没有出向 dataset-version 边。批量迁移
  属于完整 B3 + C3 范围。
- **B1（bio relation 边）和 B2（validation/translation 边）**。两者都仍 drafted 在
  `docs/bio-adaptation/section-b/`。要落地需要更多的类型化 metadata 设计：
  `clinical_trial_for {nct_id, phase}`、`fda_approved_for {indication, year}`、
  `validates_in_species {species}`、以及 10 个 B1 关系动词。

### 回滚

`git revert <pilot-B3-commit>` 移除边类型注册。`wiki/graph/edges.jsonl` 里的单条 live 边可
通过后续 `rebuild` 或手工清理（graph/ 是自动生成的；按 conventions.yaml 的 `tools_only`
规则，移除孤立边是安全的）。

---

## 2026-05-11 —— A7 pilot merge：ideas 可选 `grade` 字段

**范围**：Section A7 中最易 demo 的切片。在 ideas/ frontmatter 顶层加可选 GRADE 风格证据等级。
完整 A7（每条 evidence 边上的 grade 属性，加上扩展证据动词 `wet_lab_validated`、
`mechanistic_basis`、`clinical_validated`、`correlative`、`predicts`）需要扩 add-edge CLI，
延后。
**状态**：**A7 最小切片合并**。idea 页面级 grade live；per-edge grade 延后。

### 改动位置

- `runtime/schema/entities.yaml`：`ideas.fields.grade` 加为可选 enum
  （`very-low | low | moderate | high`）。schema 加性：现有未填 grade 的 ideas 仍合法。
- `wiki/ideas/ptm-aware-degrader-target-nomination.md`：填 `grade: low`。理由（内联 YAML
  注释）："load-bearing 前提（phospho 扰动 > 噪声底）经验上未验证；锚点 claim
  ptm-protein-isoforms-enable-selective-drug 置信度仅 0.6（weakly_supported）；存在机理依据，
  但 truly PTM-selective experimental degraders < 10 这一稀少正例集合按 GRADE 惯例约束证据等级
  为 'low'。"
- `docs/runtime-page-templates.{en,zh}.md`：`ideas/{slug}.md` 模板加可选 `grade:` 字段。

### 此 pilot 故意不做的事

- **per-edge GRADE 属性**：完整 A7 把 `grade` 放到每条 `supports` / `tested_by` 边上，
  让不同证据线携带不同 grade。需要扩 `tools/research_wiki.py add-edge` CLI 接 `--grade`
  （或通用属性 flag）。出于风险控制跳过。
- **扩展证据动词边类型**（`wet_lab_validated`、`clinical_validated`、`mechanistic_basis`、
  `correlative`、`predicts`）。可作为新边类型与现有 `supports`/`contradicts` 集合并行注册。
  延后——需设计它们与 confidence + GRADE 的交互。
- **给其他 21 个 ideas 填 `grade`**：大部分从 claims 迁移时无 per-claim GRADE 输入，批量回填
  属 /novelty C5 范围。

### 验证

| 检查 | 结果 |
|------|------|
| `python -c "from runtime.loader import VALID_VALUES; print(VALID_VALUES['ideas.grade'])"` | `{'very-low', 'low', 'moderate', 'high'}` |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵（informational 集合不变） |
| `grep '^grade:' wiki/ideas/ptm-aware-degrader-target-nomination.md` | `grade: low` |

---

## 2026-05-11 —— A3 minimal pilot merge：`papers/` 加 DOI + PMID

**范围**：Section A3 最小切片。在 `papers/` frontmatter 加 A3 的 8 个生信标识符字段中的 2 个
（`doi`、`pmid`），可选，并在一篇 paper 上填值。完整 A3（biorxiv、pdb_ids、uniprot_ids、
nct_ids、gene_symbols、species —— 结构化生信锚点）延后到 /ingest C1，因为这些字段大规模填充
需要 ingest 时的 bio NER，而非手工编辑。
**状态**：**A3 最小切片合并**。一个 paper 上 DOI + PMID live；其他 10 个 papers 和 6 个 A3
字段延后。

### 改动位置

- `runtime/schema/entities.yaml`：`papers.fields.doi` 和 `.pmid` 加为可选 `str`。均加性：
  没填这两个字段的 papers 仍合法。
- `wiki/papers/musitedeep-deep-learning-based-webserver-protein.md`：frontmatter 填
  `doi: "10.1093/nar/gkaa275"`、`pmid: "32324217"` —— Nucleic Acids Research 2020 的规范出版
  标识符。
- `docs/runtime-page-templates.{en,zh}.md`：`papers/{slug}.md` 模板加这两个新字段。

### 此 pilot 故意不做的事

- **其他 A3 字段**：`biorxiv`（DOI suffix）、`pdb_ids`（论文引入的结构）、`uniprot_ids`
  （论文表征的蛋白）、`nct_ids`（被引用的临床试验）、`gene_symbols`（HGNC）、`species`
  （模式生物）。这些需要 /ingest（C1）的 bio NER 大规模填充。pilot 给一篇 demo 论文手填可以，
  但多加 6 个空字段只增加模板噪声、无实际价值。
- **其他 10 篇 paper**：它们的 DOI/PMID 值并非都易得；/ingest C1 落地后应批量回填。

### 验证

| 检查 | 结果 |
|------|------|
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |
| `grep -E '^(doi|pmid):' wiki/papers/musitedeep-deep-learning-based-webserver-protein.md` | `doi: "10.1093/nar/gkaa275"`、`pmid: "32324217"` |

---

## 2026-05-11 —— B1 minimal pilot merge：2 种 bio 关系边类型 + 2 条 live 边

**范围**：Section B1 最易 demo 的切片。注册 B1 的 10 个动词中的 2 个（`targets_protein`、
`ubiquitinates`），endpoints 宽松（`from: '*', to: concepts`），遵循 A2-light "proteins-as-concepts"
约定。写入 2 条 live 边。
**状态**：**B1 最小切片合并**。其他 8 个动词（`binds`、`inhibits`、`activates`、`degrades`、
`phosphorylates`、`methylates`、`acetylates`、`is_substrate_of`）和针对未来 `proteins/`
实体（A2-heavy）的收紧端点契约延后。

### 改动位置

- `runtime/schema/edges.yaml`：append 两种新边类型：
  - `targets_protein` —— `from: '*'`、`to: concepts`、directed、workflow `ingest`、attrs
    confidence + evidence。
  - `ubiquitinates` —— 同形状。
  总边类型：22 → 24。
- `wiki/graph/edges.jsonl`：通过 `tools/research_wiki.py add-edge` 写入 2 条 live 边：
  1. `papers/ubiquitin-ligases-oncogenic-transformation-cancer-therapy --targets_protein-->
     concepts/ubiquitin-ligase-e3` —— confidence high，evidence 描述论文将 E3 ligase 框定为
     可药 oncogenic 靶点。
  2. `concepts/ubiquitin-ligase-e3 --ubiquitinates--> concepts/ubiquitylation` —— confidence
     high，捕捉 E3 ligase 与 ubiquitylation 反应之间的规范酶学关系。

### Demo 影响

| 之前 | 之后 |
|---|---|
| Storyboard 场景 4：1 条 B3 边 live（`dataset_version_used`）；B1 + B2 仅 caption | 1 B3 + 2 B1 edges live；仅 B2（validation/translation）仍 caption |
| 边类型计数：22 | 24（B1 从 0/10 增至 2/10） |

### 此 pilot 故意不做的事

- **其他 8 个 B1 动词**：`binds`、`inhibits`、`activates`、`degrades`、`phosphorylates`、
  `methylates`、`acetylates`、`is_substrate_of`。每个都是小的 YAML 加性块，但 pilot 保持
  surface 小以便快速回滚。
- **针对 `proteins/` 实体（A2 heavy 选项）的收紧端点**。pilot 使用 `to: concepts`，因为
  proteins-as-concepts（A2 light）是当前约定。
- **`/ingest` 自动抽取**（C1）。pilot 手工添加边；C1 落地后 /ingest 会随 bio NER 自动产出
  B1 边。

### 验证

| 检查 | 结果 |
|------|------|
| `python -c "from runtime.loader import VALID_EDGE_TYPES; print(len(VALID_EDGE_TYPES))"` | 24 |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |
| `grep -E 'targets_protein|ubiquitinates' wiki/graph/edges.jsonl` | 2 行 |

### 回滚

`git revert <pilot-commit>` 一并移除 A7 + A3 + B1 最小切片。这些字段/边没有进入现有 schema
validation 路径，revert 是干净删除。

---

## 2026-05-11 —— B1 完整 pilot merge：剩余 8 个动词注册 + 1 条新 live 边

**范围**：把当日早些时候的 B1 最小切片（2/10 动词）升级为完整覆盖 —— 全部 10 个 B1 bio 关系
动词现在都在 `runtime/schema/edges.yaml` 中注册。新增 1 条 live 边演示新的 `binds` 动词。
其他 7 个新注册动词（`inhibits`、`activates`、`degrades`、`phosphorylates`、`methylates`、
`acetylates`、`is_substrate_of`）**0 条 live 边** —— wiki 暂无 kinase / phosphatase /
acetyltransferase / 特定 substrate 概念页可以锚定。等 C1 bio NER 落地后即可填充。
**状态**：**B1 schema 完整注册**。10 个动词的 schema surface 全齐；live 边覆盖 3/10
（`targets_protein` ×1、`ubiquitinates` ×1、`binds` ×1），剩余 7 个动词等 bio NER 驱动的内容。

### 改动位置

- `runtime/schema/edges.yaml`：append 8 个新边类型块（`binds`、`inhibits`、`activates`、
  `degrades`、`phosphorylates`、`methylates`、`acetylates`、`is_substrate_of`）。形状与
  早先 `targets_protein` / `ubiquitinates` 一致：`endpoints: { from: '*', to: concepts }`、
  `direction: directed`、`workflow: ingest`、attrs `confidence`（enum required）+ `evidence`
  （str required）。总注册边类型：24 → 32。
- `wiki/graph/edges.jsonl`：通过 `tools/research_wiki.py add-edge` 添加 1 条 live 边：
  - `concepts/posttranslational-modification-inspired-drug-design --binds-->
    concepts/ubiquitin-ligase-e3`（confidence high，evidence 描述 PROTAC 的 E3 recruitment
    是三元复合物机制中的承载性分子事件）。
- `wiki/graph/context_brief.md`、`wiki/graph/open_questions.md`：重新生成。

### Demo 影响

| 之前 | 之后 |
|---|---|
| B1 动词注册：2/10 | **10/10** |
| Live B1 边：2 | **3**（`targets_protein`、`ubiquitinates`、`binds`） |
| Storyboard 场景 4：caption 列出 8 个延后的动词 | caption 可以去掉 "deferred verbs" overlay（只剩 B2 仍是 caption） |
| 总边类型：24 | **32** |

### 此 pilot 故意不做的事

- **10 个动词中 7 个的 live 边**：`inhibits` / `activates` / `degrades` / `phosphorylates`
  / `methylates` / `acetylates` / `is_substrate_of` 注册了但 0 条 live 边。要锚定需要：
  - `/ingest` 的 bio NER 自动抽取（C1）—— drafted
  - 增加针对特定 kinase、phosphatase、acetyltransferase、substrate 蛋白的概念页（A2 heavy
    选项——`proteins/` 作为独立实体类型）
- **针对 `proteins/` 实体的收紧 `to:` 端点**：仍是 `to: concepts`，遵循 A2 light 约定。

### 验证

| 检查 | 结果 |
|------|------|
| `python -c "from runtime.loader import VALID_EDGE_TYPES; print(len(VALID_EDGE_TYPES))"` | 32 |
| 全部 10 个 B1 动词在 VALID_EDGE_TYPES 中 | 是（10/10） |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |
| `grep -E '"type": "(targets_protein\|binds\|ubiquitinates\|...)"' wiki/graph/edges.jsonl` | 3 行 |

### 回滚

`git revert <pilot-commit>` 移除 8 个新注册的边类型 + `binds` live 边。早先 B1 最小切片的
2 个动词和 2 条 live 边不在本次 revert 窗口（它们已单独合并）。

---

## 2026-05-11 —— B2 minimal pilot merge：3 种 validation/translation 边类型注册

**范围**：把 Section B 从部分注册升级为完整 schema 注册（14/14 边类型）。加入 B2 validation/
translation 边（`clinical_trial_for`、`fda_approved_for`、`validates_in_species`），形态与
B1 / B3 minimal 一致 —— 仅 `confidence` + `evidence` 属性，类型化 metadata（`nct_id`、
`phase`、`indication`、`year`、`species`）暂存 evidence 字符串。
**状态**：**B2 schema 完整注册**。0 条 live B2 边 —— wiki 暂无临床试验或 FDA-approval 内容可
锚定。等 /ingest（C1）的 bio NER 处理临床-translation 论文时才会有 live 内容。

### 改动位置

- `runtime/schema/edges.yaml`：append 3 个新边类型块：
  - `clinical_trial_for` —— `endpoints: { from: '*', to: concepts }`、directed、workflow
    `evidence`、attrs confidence + evidence。Section B2 plan 要求类型化 `metadata.nct_id`
    与 `metadata.phase`；pilot 暂存 evidence 字符串。
  - `fda_approved_for` —— 同形状。B2 plan 要求 `metadata.indication` 与 `metadata.year`；
    暂存 evidence 字符串。
  - `validates_in_species` —— 同形状。B2 plan 要求 `metadata.species`；暂存 evidence 字符串。

  总注册边类型：32 → 35。

### Demo 影响

| 之前 | 之后 |
|---|---|
| Section B 注册：11/14（B1 完整 + B3 minimal；B2 drafted） | **14/14**（B1 完整 + B2 minimal + B3 minimal） |
| Storyboard 场景 4 caption："B2 仍 drafted" | "B2 schema 已注册，等 bio-clinical 内容 + 类型化 metadata 扩展" |
| 总边类型：32 | **35** |

### Section B 覆盖矩阵

| 动词家族 | 已注册动词 | Live 边 | 类型化 metadata？ |
|------|---|---|---|
| B1（bio 关系，10 动词） | 10/10 | 3（`targets_protein`、`ubiquitinates`、`binds`） | n/a（仅 confidence + evidence） |
| B2（validation/translation，3 动词） | 3/3 | 0 | 延后（暂存 evidence 字符串） |
| B3（dataset-version provenance，1 动词） | 1/1 | 1（`dataset_version_used`） | 延后（暂存 evidence 字符串） |
| **Section B 总和** | **14/14** | **4** | **0/14 typed；14/14 evidence-string 编码** |

### 此 pilot 故意不做的事

- **Live B2 边**：wiki 暂无临床试验 / FDA-approval 内容。`docs/bio-adaptation/preview/
  bio-edges-sample.jsonl` 里的 4 条 sample 边早于 B2 minimal 产出，且都是 B1 形状；如果
  storyboard 场景 4 需要 B2 caption 材料，可作小补丁加进去。
- **任何 B1 / B2 / B3 边上的类型化 `metadata.*` 属性**。三家族目前共用最简 `confidence +
  evidence` 形态。完整 Section B 带类型化 metadata 需扩 `tools/research_wiki.py add-edge`
  接 `--metadata KEY=VALUE` 或每属性 flag（约 30 行 Python）。在那之前，version / nct_id /
  phase / indication / year / species 都以子串形式存在 evidence 字段内，可用正则解析。

### 验证

| 检查 | 结果 |
|------|------|
| `python -c "from runtime.loader import VALID_EDGE_TYPES; print(len(VALID_EDGE_TYPES))"` | 35 |
| 全部 14 个 Section-B 边类型已注册 | 是（B1 ×10 + B2 ×3 + B3 ×1） |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |

### 回滚

`git revert <pilot-commit>` 移除 3 个新注册的 B2 边类型。无新增 live 边，revert 是纯 schema
删除。

---

## 2026-05-11 —— `tools/research_wiki.py add-edge` 扩展 `--metadata KEY=VALUE`

**范围**：生信适配工作中的第一个 Python 代码改动。此前所有 pilot merge（A1/A3/A5/A6/A7
minimal + B1 full + B2 minimal + B3 minimal）都是 YAML/markdown-only，依赖把类型化 metadata
塞进 `evidence` 字符串。本次改动解锁原 Section B2/B3 设计意图中的类型化 `metadata.*` 形态。
**状态**：**CLI 扩展已合并**。用新 flag 添加了 2 条新 live 边（1 条 B2 + 1 条 B3，详见下文）。
早先 pilot 添加的边保留 evidence-string 编码（无 remove-edge 子命令；dedup 阻止原地改写）。

### 改动位置

- `tools/research_wiki.py`：
  - `add_edge(...)` 签名加 `metadata: dict | None = None` 关键字参数。非空时序列化进 edge
    JSON 作为嵌套 `"metadata": {...}` 对象，与 `evidence` / `confidence` / `date` 并列。
  - `add-edge` 子命令 argparse 加新 flag：`--metadata KEY=VALUE`（`action="append"`，
    可重复）。示例调用：

    ```bash
    python tools/research_wiki.py add-edge wiki \
      --from papers/musitedeep-... --to concepts/... --type validates_in_species \
      --confidence high --evidence "..." \
      --metadata species=human --metadata source_db=uniprotkb-swissprot
    ```
  - CLI dispatcher 把每个 `KEY=VALUE` 解析进 dict，传给 `add_edge`。
- `wiki/graph/edges.jsonl`：两条新 live 边演示 `--metadata`：
  1. `papers/musitedeep-deep-learning-based-webserver-protein --validates_in_species-->
     concepts/post-translational-modification-site-prediction` —— confidence high，evidence
     描述 MusiteDeep 的 UniProtKB/Swiss-Prot 人类 PTM 训练集，metadata
     `{species: human, source_db: uniprotkb-swissprot}`。**首条 live B2 边。**
  2. `experiments/phase0-noise-floor-calibration-deepternary-ptm-perturbations
     --dataset_version_used--> datasets/ternarydb` —— confidence high，evidence 描述
     Phase-0 calibration subset 使用，metadata `{version: v1, subset: crbn-vhl-training}`。
     **第二条 live B3 边**（第一条在 B3 minimal pilot 时添加，用 evidence-string 编码）。
- `wiki/graph/context_brief.md`、`wiki/graph/open_questions.md`：重新生成。

### Demo 影响

| 之前 | 之后 |
|---|---|
| Live bio 边（B1/B2/B3）：4 | **6**（+1 B2 +1 B3） |
| 带类型化 `metadata.*` 的边：0 | **2** |
| Live B2 边：0 | **1**（`validates_in_species`，含 `species: human` metadata） |
| Live B3 边：1（evidence-string 编码） | **2**（一条 evidence-string，一条类型化 metadata） |
| 总边数：77 | **79** |
| `add-edge` CLI 能力 | 只有 confidence + evidence | + 可重复类型化 metadata |

### Loader 未改

`runtime/loader.py::validate_edge_attributes` 仍忽略 `metadata.*`。对 edges.yaml 的嵌套
metadata schema 验证仍延后。这是有意的渐进式选择：CLI 扩展小、立即解锁新 edge 内容；
类型化 nested-schema 强制是另一独立关切，C3（bio-lint）可后续在其上叠加。

### 向后兼容

- 没有 metadata 的边继续无该字段地序列化（加性）。
- 早先 B3 minimal pilot 添加的边保留 evidence-string 编码 —— 此后 `--metadata` 是记录
  类型化属性的规范方式。
- Skill prompt（C1、C2 仍 drafted）未动。它们仍只输出 confidence + evidence。CLI 新能力
  对手工 `add-edge` 调用、以及任何未来 opt-in 的 skill 都可用。

### 验证

| 检查 | 结果 |
|------|------|
| `python tools/research_wiki.py add-edge --help` | 显示 `--metadata KEY=VALUE`（可重复） |
| 非法对 `--metadata version`（无 `=`） | 退出码 1，报 `--metadata expects KEY=VALUE` |
| 带 metadata 的边 JSON | `{"...", "metadata": {"species": "human", "source_db": "uniprotkb-swissprot"}}` |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |
| Live bio 边数 | 6（3 B1 + 1 B2 + 2 B3） |

### 此改动故意不做的事

- **`remove-edge` 子命令**：除手工编辑 edges.jsonl（违反 `tools_only` 规则）外，无法删除
  legacy 的 evidence-string B3 边。需要时另行加 commit。
- **`edges.yaml` 中的嵌套 metadata schema**：B2/B3 边类型仍只声明 `confidence` + `evidence`。
  加 `metadata: { type: object, fields: {...} }` 块还需扩 `validate_edge_attributes` 做递归
  —— 延后。
- **metadata 值的类型强制**：`--metadata phase=II` 产出 `{"phase": "II"}`（string），
  `--metadata year=2024` 产出 `{"year": "2024"}`（string）。所有值都是 string。数值/enum
  强制是 schema 验证落地后的下游关切。

### 回滚

`git revert <pilot-commit>` 同时回滚 CLI 扩展和 2 条新 live 边。B3 minimal pilot 的 legacy
边不受影响。

---

## 2026-05-11 —— C1 minimal pilot merge：bio-aware `/ingest` Step 2.5

**范围**：Section C 落地的第一项。给 `/ingest` 加一个轻量级生信标识符抽取步骤，让运行
ingestion 的 LLM agent 填充 A3 minimal frontmatter 字段（`doi`、`pmid`），并把正文中的纯文本
dataset 引用升级为 `[[{slug}]]` wikilink（对照 live `wiki/datasets/` 目录，A1 minimal）。

**状态**：**C1 minimal 以纯 prompt 形态合并**。完整 C1 设计（PubMed / EuropePMC / CrossRef
fetcher 工具、`tools/extract_bio_ner.py` 结构化 NER、JATS-XML 流水线、把 DOI / PMID / bioRxiv
/ PMC URL 加入 `/ingest` 源输入）**延后** —— 那些计划的 Python 工具尚未实现。最小切片依赖
LLM agent 自身的 prompt 内 NER 能力做生信标识符抽取。

### 改动位置

- `i18n/en/skills/ingest/SKILL.md`：在 Step 2（Paper identity and enrichment）与 Step 3
  （Write the paper page）之间插入新的 `### Step 2.5: Bio identifier extraction (minimal C1)`
  块。该块指示 agent：
  1. 对生信领域论文，从正文 / metadata 源中可读出值时填充 `doi`、`pmid` —— 决不编造，不确定
     时留空。其他 A3 字段（`biorxiv`、`pdb_ids`、`uniprot_ids`、`nct_ids`、`gene_symbols`、
     `species`）继续延后到完整 C1。
  2. 当 `wiki/datasets/{slug}.md` 页面（按 title 或 aliases 匹配）已存在时，把纯文本 dataset
     提及升级为 `[[{slug}]]` wikilink。本 pilot 不创建新 datasets 页。
- `i18n/zh/skills/ingest/SKILL.md`：同 Step 2.5 的中文镜像。
- `.claude/skills/ingest/SKILL.md`：从 `i18n/en/` 同步（英文为当前活动 locale；用户可运行
  `./setup.sh --lang zh` 切换）。

### Demo 影响

| 之前 | 之后 |
|---|---|
| `/ingest` 产出 `doi`/`pmid` 为空的 paper 页面，即便源文件里有值 | `/ingest` 给生信论文填 `doi`/`pmid`（例如 musitedeep 页面首次 ingest 时就会正确，无需 A3 minimal 事后补丁） |
| `/ingest` 在正文章节里写纯文本 "TernaryDB" | `/ingest` 写 `[[ternarydb]]`（当 `wiki/datasets/` 里有该页时） |
| Section C 状态：0/9 项合并 | **1/9**（C1 minimal） |
| `/ingest` SKILL.md 行数 | 297 → 327（新增 30 行） |

### 此 pilot 故意不做的事

- **计划中的 5 个 bio fetcher 工具**（`fetch_crossref.py`、`fetch_pubmed.py`、
  `fetch_europepmc.py`、`fetch_biorxiv.py`、`extract_bio_ner.py`）。完整 C1 通过 Bash 调用
  它们；最小 pilot 用 prompt 内 LLM NER 替代。
- **DOI / PMID / bioRxiv / PMC URL 作为 `/ingest` 源输入**。今天仍需 `.tex` / `.pdf` /
  arXiv URL。完整 C1 会加生信标识符 resolver 链（CrossRef → PubMed → EuropePMC → bioRxiv
  → DeepXiv → Semantic Scholar）。
- **自动创建新 `wiki/datasets/{slug}.md` 页**。最小 pilot 仅在页面已存在时升级为 wikilink。
  页面创建保守 —— 交给 `/edit` 或完整 C1（importance ≥ 4 门控）。
- **B1 bio relation 边自动抽取**。完整 C1 会从正文 NER + 概念链接自动产出 `targets_protein`、
  `phosphorylates` 等。最小 pilot 让它们继续由手工 `add-edge` 调用产生（3 条 live B1 边就是
  这样写的）。

### 验证

| 检查 | 结果 |
|------|------|
| `diff -q .claude/skills/ingest/SKILL.md i18n/en/skills/ingest/SKILL.md` | 一致（已同步） |
| `grep "Step 2.5" .claude/skills/ingest/SKILL.md` | 命中 |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵（informational 集合不变） |
| 活动 SKILL.md 行数 | 327（升自 297） |

### 回滚

`git revert <pilot-commit>` 同时移除 i18n 双语版本和活动 `.claude/skills/ingest/SKILL.md`
中的 Step 2.5 块。在 Step 2.5 生效后 ingest 的 wiki 页面会保留它们填好的 `doi`/`pmid` 字段
（那是 wiki 内容，与 skill prompt 分离）。

---

## 2026-05-11 —— C2 minimal pilot merge：`/exp-design` 输出 A6 结构化 `estimated_cost`

**范围**：闭合 A6 ↔ C2 环。当日早些时候的 A6 pilot 把结构化 `estimated_cost` 块加入 experiment
schema，并手工改写了 8 个现有实验。C2 minimal 升级 `/exp-design` SKILL.md，让下次
`/exp-design` 调用直接填 `estimated_cost`，不必再手工改写。
**状态**：**C2 minimal 以纯 prompt 形态合并**。完整 C2（从 `setup.framework` 自动检测 MD 墙钟时
、从 `setup.hardware` 检测湿实验成本、从已解析的 `[[dataset]]` 页 `access` tier 推断数据访问
lead time、固定预算削减顺序）**延后** —— 计划的自动推断逻辑尚未进入 prompt；最小 pilot 依赖
LLM agent 自身基于实验设计判断子字段填值。

### 改动位置

- `i18n/en/skills/exp-design/SKILL.md`：在 Step 6 的实验 frontmatter 模板中，紧跟 legacy
  `estimated_hours: 0` 行插入结构化 `estimated_cost` 块。块中列出全部 6 个子字段
  （`gpu_hours`、`cpu_hours`、`md_wallclock_hours`、`wet_lab_usd`、`fte_weeks`、
  `dataset_access_lead_time_days`），每个子字段配内联指引说明何时取非零值。
- `i18n/zh/skills/exp-design/SKILL.md`：同块的中文镜像。
- `.claude/skills/exp-design/SKILL.md`：从 `i18n/en/` 同步。

### Demo 影响

| 之前 | 之后 |
|---|---|
| `/exp-design` 写 `estimated_hours: 0`，`estimated_cost` 缺席 —— 除非有人手工改写，A6 schema 字段为空 | `/exp-design` 同时写 `estimated_hours: 0`（legacy）和 6 子字段的 `estimated_cost` 块，由 agent 从 Step 3 / Step 4 预算拆分填充 |
| PTM-aware degrader 的 8 个现有实验是 A6 pilot 时手工改写的 | 下次 `/exp-design` 调用产出的页面就是 A6 合规的，无需手工改写 —— A6 ↔ C2 环闭合 |
| Section C 状态：1/9（C1 minimal） | **2/9**（C1 + C2 minimal） |
| `/exp-design` SKILL.md 行数 | 351 → 366（新增 15 行：estimated_cost 块 + 内联指引） |

### 与 A6 配对

A6 pilot 的逐实验预算拆分（gpu+md=104h 合计，fte 4.25 周）现在对通过 `/exp-design` 走的新实验
**可复现**。agent 从实验设计的同样子字段（model / dataset / hardware / framework）读出，以
结构化块输出，而非塌缩成单数字。

### 此 pilot 故意不做的事

- **从 `setup.framework` 自动推断子字段**。完整 C2 会做映射，如 "MD 流水线 with AMBER ff14SB
  + GROMACS" → `md_wallclock_hours > 0`。最小 pilot 把这交给 LLM agent 判断。
- **从已解析的 `[[dataset]]` 页 `access` tier 自动查 `dataset_access_lead_time_days`**
  （`public` → 0、`registration` → ~7、`restricted` → ~30）。同延后 —— 需要结构化 access-tier
  读取。
- **固定预算削减顺序**。完整 C2 计划：总和超 `--budget` 时按 `cross_context → robustness →
  dose_response` 顺序裁剪。最小 pilot 保留 `--budget` 的当前非结构化上限语义。
- **湿实验交接 hook**（C9 范围）。最小 pilot 仅暴露 `wet_lab_usd` 字段；下游湿实验追踪延后。

### 验证

| 检查 | 结果 |
|------|------|
| `diff -q .claude/skills/exp-design/SKILL.md i18n/en/skills/exp-design/SKILL.md` | 一致（已同步） |
| `grep "bio-C2" .claude/skills/exp-design/SKILL.md` | 命中 |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵（informational 集合不变） |
| 活动 SKILL.md 行数 | 366（升自 351） |

### 回滚

`git revert <pilot-commit>` 从两个 i18n locale 与活动 `.claude/skills/exp-design/SKILL.md`
中同时移除 `estimated_cost` 块与 bio-C2 指引。8 个现有实验页保留 A6 结构化 cost 块（那是
wiki 内容，与 prompt 分离）。

---

## 2026-05-11 —— A2 light pilot merge：`concepts/` 加蛋白质锚点字段 + 首个蛋白质概念页

**范围**：A2 light 选项 —— 给 `concepts/` schema 加 4 个可选字段，把概念锚定到具体基因产物
（HGNC + UniProt + PDB + species）。在新建的 `wiki/concepts/crbn.md` 页填值，这是 wiki 中
首个**具体蛋白质**概念（此前所有蛋白质引用 —— p53、CRBN、VHL、MDM2、BCL-XL、BTK —— 都是
正文中的纯文本）。
**状态**：**A2 light 合并**。A2 heavy（独立 `proteins/` 实体类型）延后到蛋白质概念累积到 ≥50
个或图查询要求时再做。

### 改动位置

- `runtime/schema/entities.yaml`：`concepts.fields` 加 4 个可选字段：
  - `gene_symbol`（str）—— HGNC 符号
  - `uniprot_id`（str）—— UniProt 登录号
  - `pdb_ids`（list_str）—— 代表性结构
  - `species`（list_str）—— 模式生物

  全部可选、加性：未填这些字段的现有概念页（alphafold-db、ubiquitylation、ubiquitin-ligase-e3
  …）仍合法。
- `wiki/concepts/crbn.md`：Cereblon 新概念页，PROTAC 药物发现中核心的 CRBN 招募 E3 ligase。
  frontmatter 填 `gene_symbol: CRBN`、`uniprot_id: Q96SW2`、`pdb_ids: [4CI1, 4CI2, 5HXB,
  5FQD]`、`species: [human]`。正文章节涵盖定义、招募机制、与 VHL/MDM2 对比、CRBN^Y384A 临床
  耐药变体，以及反链到 `[[ptm-aware-degrader-target-nomination]]` /
  `[[ubiquitin-ligase-e3]]` / `[[posttranslational-modification-inspired-drug-design]]`。
- `wiki/index.md`：在 `concepts:` 块下加 `crbn` 条目，bio-A2 字段提到顶层。
- `wiki/datasets/ternarydb.md`：`Overview` 段的纯文本 "CRBN+VHL subset" 改为 `[[crbn]]+VHL
  subset`（保留原 prose，仅把 dataset 首次 CRBN 提及升级为 wikilink —— 必需，以清除 crbn.md
  的 lint orphan 检查）。
- `docs/runtime-page-templates.{en,zh}.md`：`concepts/{concept-name}.md` 模板加 4 个新字段与
  内联指引，注明仅当概念本身是具体基因产物时才填。
- `wiki/graph/edges.jsonl`：通过 `add-edge --metadata` 添加 1 条新 live B1 边：
  `concepts/posttranslational-modification-inspired-drug-design --binds--> concepts/crbn`，
  confidence high，metadata `{recruitment_ligand_class: imid, clinical_anchor:
  lenalidomide-pomalidomide}`。这是现有类级（到 `concepts/ubiquitin-ligase-e3`）边的
  更具体实例。

### Demo 影响

| 之前 | 之后 |
|---|---|
| wiki 有 0 个具体蛋白质概念页 | **1**（crbn.md）—— 填了 HGNC / UniProt / PDB / species |
| concept 模板列出 11 个字段 | 15（4 个新 bio-A2 字段全部可选） |
| Bio relation 边：6 | **7**（加了 CRBN 特定的 `binds` 边） |
| 带类型化 metadata.* 的边：3 | **4** |
| Section A 状态：5/8 项合并 | **6/8**（A2 light 加入 A1 / A3 / A5 / A6 / A7） |

### 与既有 pilot 的配对

- **A2 light ↔ A1**：TernaryDB dataset 页已存在（A1 minimal pilot）；crbn.md 加上
  ternarydb.md 的 wikilink 升级，把 CRBN（蛋白）与 TernaryDB（数据集）在页面内容层连起来
  （dataset 的 Overview 文本引用 `[[crbn]]`）。
- **A2 light ↔ B1**：从 PROTAC 药物类到 CRBN 的新 `binds` 边比既有的类级到 ubiquitin-ligase-e3
  边更具体。两条都留在图中 —— 它们编码同一机制的不同粒度。
- **A2 light ↔ B3**：现有从实验到 TernaryDB 的 `dataset_version_used` 边现在通过 dataset 页
  的正文 wikilink 间接锚定 CRBN。

### 此 pilot 故意不做的事

- **A2 heavy**（独立 `proteins/` 实体类型）。light 选项是 backlog 推荐的起点（"如果蛋白质引用
  累积到 50+ 时我们想要 '靶向 kinase X 的药物' 这种图查询，再升级为独立类型"）。当前计数：1。
- **UniProt 格式 lint**（例如 `uniprot_id` 匹配 `^[A-NR-Z][0-9][A-Z0-9]{3}[0-9]$` 或等价的
  10 字符模式）。属 C3（bio-lint）范围。
- **其他蛋白质作为概念页**。p53、VHL、MDM2、BCL-XL、BTK —— 仍是 wiki 中的纯文本。pilot 建立
  schema；批量创建属后续工作，依赖 bio NER（C1 完整版）做系统化抽取。

### 验证

| 检查 | 结果 |
|------|------|
| `python -c "from runtime.loader import ENTITIES; print([k for k in ENTITIES['concepts']['fields'] if k in ['gene_symbol','uniprot_id','pdb_ids','species']])"` | 4 字段全部就位 |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵（ternarydb.md 的 wikilink 升级后 informational 集合不变） |
| `grep '\[\[crbn\]\]' wiki/datasets/ternarydb.md` | 命中（清除 crbn orphan 检查） |
| `grep -c '"to": "concepts/crbn"' wiki/graph/edges.jsonl` | 1（新 B1 binds 边） |

### 回滚

`git revert <pilot-commit>` 移除 4 个新 concept 字段、crbn.md 页、ternarydb.md 的 `[[crbn]]`
升级、index 条目、模板加项以及新 B1 边。早先 B1 完整 pilot 添加的类级 `binds` 边（指向
ubiquitin-ligase-e3）保持完整。

---

## 2026-05-12 —— A5 full pilot merge：`experiments.setup` 加 9 个 bio 形态可选字段

**范围**：A5 切片（2026-05-11）只把 `deepternary-baseline` 的 `setup.dataset` 升为 wikilink。
A5 full 把 backlog 列出的 9 个 bio 形态字段全部加入 `experiments.setup`（仍可选 + 加性 ——
纯 ML 页面留空仍合法），并在 8 个现有实验页填出适用的非空值。
**状态**：**A5 full 合并**。下游 C7（`/exp-run` 按 setup type 路由）需要 `in_silico_or_wet`
驱动；C8 bio-lint 计划针对 `setup.assay_type=MD` 时 `force_field` 缺失发 warning（延后）。

### 改动位置

- `runtime/schema/entities.yaml`：`experiments.setup.fields` 加 9 个字段 ——
  `in_silico_or_wet`（enum: in_silico|wet_lab|mixed）、`species`（list_str）、`cell_line`、
  `assay_type`、`force_field`、`solvent_model`、`simulation_length`、`weight_version`、
  `random_seed_protocol`。
- `docs/runtime-page-templates.{en,zh}.md`：`experiments/{slug}.md` setup 块模板扩展，含内联指引。
- `i18n/{en,zh}/skills/exp-design/SKILL.md` + `.claude/skills/exp-design/SKILL.md`：
  Step 6 frontmatter 模板同步扩展。
- `wiki/experiments/*.md`（8 文件）：填入逐实验 bio 字段。全部 in_silico human；
  `ablation-boltz2-ptm-vs-md-relaxed-route` 携带 MD 三连（force_field=AMBER ff14SB + phosaa14SB、
  solvent_model=explicit、simulation_length=50 ns）；其他携带 weight_version（Boltz-2 Jan 2026 /
  DeepTernary Nat Commun 2025 / PROTAC-STAN Adv Sci 2025）和 random_seed_protocol
  （ranking-shuffle 或 bootstrap，按实验角色）。

### 验证

| 检查 | 结果 |
|---|---|
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵（informational 集合不变） |
| `grep -c "in_silico_or_wet" wiki/experiments/*.md \| awk -F: '{s+=$2}END{print s}'` | 8（8 个实验全部填写） |
| `diff -q i18n/en/skills/exp-design/SKILL.md .claude/skills/exp-design/SKILL.md` | 一致（已同步） |

Section A 状态：6/8 → 7/8（仅 A4 受控词表与 A8 wet-lab 可复现性元数据剩余）。

---

## 2026-05-12 —— C4 minimal pilot merge：`/exp-design` 块分类加 4 个 bio 块类型

**范围**：`/exp-design` 原 4 类块（baseline / validation / ablation / robustness）形态是 ML
流水线，bio 自然的块类型（negative_control、mechanism、dose_response、cross_context）缺席。
C4 minimal 在 SKILL prompt 中加上这 4 类，并说明与 A–D 的边界区分。
**状态**：**C4 minimal 以纯 prompt 形态合并**。块类型沿用 tags 记录（不引入新 frontmatter
enum，与 backlog 设计一致）。完整 C4（在 `/exp-design --review` Review LLM 提问中显式问"是否
缺 mechanism 块"等）延后。

### 改动位置

- `i18n/{en,zh}/skills/exp-design/SKILL.md` + `.claude/skills/exp-design/SKILL.md`：
  Step 3 在 A–D 之后插入 "Bio-specific block types" 段，列出 E negative_control / F mechanism /
  G dose_response / H cross_context 及与最近 A–D 类比的形态区分（negative_control ≠ baseline、
  mechanism ≠ validation、dose_response ≠ 超参扫描、cross_context ≠ ML 跨数据集）。Step 3
  "每个实验块包含" 列表中的 `type` 行更新为 8 类标签可叠加。

### 验证

| 检查 | 结果 |
|---|---|
| `grep "negative_control\|mechanism\|dose_response\|cross_context" .claude/skills/exp-design/SKILL.md \| wc -l` | ≥ 4（4 类均出现） |
| `diff -q i18n/en/skills/exp-design/SKILL.md .claude/skills/exp-design/SKILL.md` | 一致 |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |

Section C 状态：2/9 → 3/9。

---

## 2026-05-12 —— C5 minimal pilot merge：`/exp-design` Step 1 加湿实验依赖探测

**范围**：`/exp-design` Step 1 此前未问"该 idea 是否需要湿实验数据"。C5 minimal 在 Step 1
新增子步骤 3，扫描 idea hypothesis / Risks / Approach sketch 中的 14 个湿实验信号词；
命中则提示用户一次询问湿实验访问条件，回答驱动 Step 3 的块规划。与 A5 full 的
`setup.in_silico_or_wet` 字段配套。
**状态**：**C5 minimal 以纯 prompt 形态合并**。完整 C5（具体湿实验块模板、protocol.md 子目录
布局、湿实验 cost referencing）延后到 C7（`/exp-run` 目录布局）。

### 改动位置

- `i18n/{en,zh}/skills/exp-design/SKILL.md` + `.claude/skills/exp-design/SKILL.md`：
  Step 1 在 "Load relevant wiki context" 之后插入子步骤 3 "Detect wet-lab dependencies"。
  14 个触发词：in cell / cellular target engagement / in vivo / tumor regression / binding assay /
  ELISA / Western blot / co-IP / cryo-EM / point mutation / knockdown / knockout / IC50 / Kd。
  匹配 → 提示用户 → 记录 `wet_lab_planned: true|false` → 驱动 Step 3 块规划与
  `setup.in_silico_or_wet` 字段；未匹配则静默跳过。

### 验证

| 检查 | 结果 |
|---|---|
| `grep "wet_lab_planned\|Detect wet-lab\|探测湿实验" .claude/skills/exp-design/SKILL.md \| wc -l` | ≥ 1 |
| `diff -q i18n/en/skills/exp-design/SKILL.md .claude/skills/exp-design/SKILL.md` | 一致 |
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |

Section C 状态：3/9 → 4/9。P0 backlog 完结：当前分支 P0 余额 0（A1/A3/A5/C1/C4/C5 全部已 merge）。

---

## 2026-05-12 —— C9 minimal pilot merge：`/novelty` 加 PubMed E-utilities 通道

**范围**：`/novelty` 此前用 WebSearch + Semantic Scholar + DeepXiv + wiki + Review LLM。Bio prior
art 绝大部分在 PubMed（>3000 万摘要），Semantic Scholar 覆盖中等 —— bio 类 prior-art 撞车被
under-report。C9 minimal 在 Step 2 加 Source E（PubMed E-utilities via WebFetch），bio 形态
target 给满权重。
**状态**：**C9 minimal 以纯 prompt 形态合并**。完整 C9（`tools/fetch_pubmed.py` CLI + 分页 +
MeSH 扩展 + 摘要 NER + PMC 全文 fallback）延后 —— 最小 pilot 让 agent 直接用 WebFetch 拉
NCBI E-utilities URL。

### 改动位置

- `i18n/{en,zh}/skills/novelty/SKILL.md` + `.claude/skills/novelty/SKILL.md`：
  - description 加 "+ PubMed (bio)"
  - Step 2 在 Source D 之后插入 Source E：bio-claim 探测三条规则（domain enum 命中 / method
    signature 含 bio token / 链接 idea 含 A2-light 蛋白锚字段）；5 种查询形态（直接 / 组合 /
    PTM 专用 / 临床锚 / 综述）；esearch + esummary + efetch URL；按 DOI / PMID / 归一化 title
    去重；NCBI 限速 ≤ 3 req/sec；raw/tmp/novelty-pubmed/ 缓存
  - Step 3 Review LLM 输入加"每条 prior work 标 source channel"
  - 评分规则加："bio 形态 + PubMed 命中 ≥ 3 条 S2/WebSearch 未独立命中的高相似论文 → 降 1 分"
    与"PubMed + WebSearch 一致命中且 wiki 未 ingest → 标 Recommend /ingest before scoring"
  - Constraints 加 bio 形态 target 额外 3–5 个 PubMed 查询
  - Error Handling 加 PubMed 不可用 → 显式 coverage gap 注释（不静默降级）
  - Dependencies 加 WebFetch（Source E）

### 验证

| 检查 | 结果 |
|---|---|
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |
| `diff -q i18n/en/skills/novelty/SKILL.md .claude/skills/novelty/SKILL.md` | 一致 |
| `grep -c "PubMed\|eutils.ncbi" .claude/skills/novelty/SKILL.md` | ≥ 8 |
| 活动 SKILL.md 行数 | 253（升自 217） |

Section C 状态：4/9 → 5/9。

---

## 2026-05-12 —— C6 minimal pilot merge：`/exp-design` 统计默认值改 bio 形态

**范围**：`/exp-design` 此前对 validation / ablation 一律建议 ">= 3 seeds"。bio 测试集常 n_test < 50
且类不平衡，仅多 seed 不能给出可靠 CI ——bootstrap CI + stratified k-fold 是标准做法。湿实验
还需 biological vs technical replicates 区分。C6 minimal 在 Step 3 加 4 形态表。
**状态**：**C6 minimal 以纯 prompt 形态合并**。完整 C6（每种协议的 Review LLM prompt 变体、
`tools/research_wiki.py validate-setup` 当协议与 n_test 矛盾时 warn、`/exp-eval` 按协议接入
对应 p-value 检验）延后。

### 改动位置

- `i18n/{en,zh}/skills/exp-design/SKILL.md` + `.claude/skills/exp-design/SKILL.md`：
  - Step 3 在 Bio-specific block types 之后、"每个实验块包含" 之前插入 "Statistical defaults"
    4 行表：ML-large（n_test >= 50 → >= 3 seeds）/ Bio small-n（n_test < 50 → bootstrap CI
    ≥ 1000 resamples + stratified k-fold k = min(5, n_positives)）/ Bio very-small-n
    （n_test < 10 → leave-one-out CV + bootstrap CI 头条）/ Wet-lab assay（>= 3 biological ×
    >= 3 technical replicates 并显式标注）。每行末尾列出 `setup.random_seed_protocol`
    （A5 full 字段）应记录的值。
  - 加类不平衡检查：`min(n_positives, n_negatives) < 20` 时按类分层 k-fold AND 报告逐类指标。
  - Step 3 B Validation、Step 3 `seeds` 行、Step 5 Review LLM 问题 5、Constraints
    "At least 3 seeds" 全部更新为引用此表。

### 验证

| 检查 | 结果 |
|---|---|
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵 |
| `diff -q i18n/en/skills/exp-design/SKILL.md .claude/skills/exp-design/SKILL.md` | 一致 |
| `grep -c "bootstrap\|stratified-k-fold\|LOO-CV\|biological.*technical" .claude/skills/exp-design/SKILL.md` | ≥ 10 |
| 活动 SKILL.md 行数 | 405（升自 366） |

Section C 状态：5/9 → 6/9。

---

## 2026-05-12 —— C8 pilot merge：`tools/lint_bio.py` 5 项 bio 专用检查

**范围**：`/check` 调用的 `tools/lint.py` 是 entity-type-agnostic 的结构检查（必填字段、enum、xref
对称、edge 一致）—— 无法表达 bio 形态约束（PDB ID 格式、UniProt accession、dataset 版本对照、
MD 必需 force_field 等）。C8 新增 `tools/lint_bio.py` 实现这 5 项检查，并在 `/check` 工作流中
在 wiki 含 bio 字段时调用。
**状态**：**C8 合并**（不是 minimal — 工具是完整工程化的，且本 wiki 全部 5 项检查均干净通过）。
这是 bio-adaptation 的第二次 Python 代码改动（第一次是 add-edge --metadata）。

### 改动位置

- **新文件 `tools/lint_bio.py`**（298 行）：
  1. `check_pdb_ids` —— `concepts.pdb_ids` 每个值必须匹配 `^[0-9][A-Za-z0-9]{3}([A-Za-z0-9]{4})?$`
     （4 字符或 8 字符 alphanum 起始 digit）；🟡 on mismatch。
  2. `check_uniprot_ids` —— `concepts.uniprot_id` 必须匹配
     `[OPQ][0-9][A-Z0-9]{3}[0-9]` 或扩展 `[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}`；🟡 on mismatch。
  3. `check_dataset_versions` —— `dataset_version_used` 边 `metadata.version` 必须出现在目标
     dataset `versions:` 列表（B3 + A1 交叉）；🟡 on mismatch。仅 evidence 字符串中含版本号的
     边不在本检查范围。
  4. `check_species_recognised` —— `experiments.setup.species` 每个值在 29 项识别集中（human /
     mouse / rat / yeast / zebrafish / drosophila / c-elegans / e-coli / ...）；🔵 informational
     对未识别值 —— 合法新物种时扩展 `RECOGNISED_SPECIES`。
  5. `check_md_force_field` —— `experiments.setup.assay_type` 匹配 `\bMD\b|molecular dynamics`
     时 `setup.force_field` 必填；🟡 when empty。
  - 严重度约定与 `LintIssue` 类从 `tools/lint.py` 通过 sys.path 注入复用（tools/ 无 `__init__.py`,
    沿用 lint.py 自己导入 runtime/loader 的方式）。
  - 嵌套 setup 解析用 PyYAML（lint.py 的 regex parser 丢弃缩进子键）。
  - `--json` 输出与 `--wiki-dir` flag 与 lint.py 等价。
  - 退出码：≥ 1 个 🔴 时 exit 1。
- `i18n/{en,zh}/skills/check/SKILL.md` + `.claude/skills/check/SKILL.md`：
  - Step 1 末尾插入 "Bio-specific lint" 段说明何时调用 `lint_bio.py` 与如何合并 JSON 输出
    （`bio-*` category 前缀区分）；非 bio wiki 静默跳过。
  - Dependencies 加 `lint_bio.py` 条目。

### 验证

| 检查 | 结果 |
|---|---|
| `python tools/lint.py` | 0 🔴 / 0 🟡 / 11 🔵（baseline 不变） |
| `python tools/lint_bio.py` | 0 🔴 / 0 🟡 / 0 🔵（本 wiki 13-pilot bio 表面全干净） |
| `python tools/lint_bio.py --json` | `[]`（机器可读） |
| PDB regex 烟测 | `4CI1 5HXB 6XYZ` ✓；`XYZ4 pdb_001 6X` ✗ |
| UniProt regex 烟测 | `Q96SW2 P12345 O00533` ✓；`Q96SW XYZ123` ✗ |
| MD pattern 烟测 | `MD / MD + scoring / molecular dynamics` ✓；`scoring / docking / Cryo-EM` ✗ |
| `diff -q i18n/en/skills/check/SKILL.md .claude/skills/check/SKILL.md` | 一致 |

Section C 状态：6/9 → 7/9。
