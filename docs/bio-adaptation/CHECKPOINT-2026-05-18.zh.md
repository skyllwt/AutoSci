# 生信适配会话 Checkpoint —— 2026-05-18

> 智源 Agent for Science 大赛报名后第一次工作会话。主线：把 bio-adaptation 模块从"README demo case"重新定位为"比赛 case study"，落地三轴 framing + P0 优化产出 + Obsidian Linux 安装。**全部已 commit；尚未 push**。下次会话用户手调 canvas 布局后截图九，然后视情况启 P1。

## 1. 分支当前状态

- **分支**：`feat/qwt-ptm-degrader-ideate`
- **HEAD commit**：`8137ffb` —— `docs(bio-adaptation): P0-1..P0-4 — Bio Quick Tour + 3 example outputs`
- **工作树**：clean tracked；2 个 untracked 调试截图（`assets/屏幕截图 2026-05-18 18{2111,3746}.png`，可删）；本地 canvas 改动**不进 git**（`wiki/canvases/`、`wiki/.obsidian/` 都被 `.gitignore` 屏蔽 —— 见 `.gitignore:38`）
- **Ahead of main**：28 commits（27 来自 2026-05-11/12 两次会话 + 1 本会话新 commit。前一 checkpoint 报 25 是因为还差 1 commit `605d172`；本会话又加 2 个，累计 28）
- **Push target**：仍未定（`origin/dev` 已删；项目规范 `branch-from-dev → PR-to-dev` 当前不适用）
- **Lint**：`0 🔴 / 0 🟡 / 11 🔵` (base) + `0 🔴 / 0 🟡 / 0 🔵` (bio) —— 与会话开始完全一致，未引入回退

## 2. 本次会话的 2 个 commit

```
8137ffb docs(bio-adaptation): P0-1..P0-4 — Bio Quick Tour + 3 example outputs
dc2da52 docs(bio-adaptation): 智源 Agent for Science 大赛作战备忘 + DEMO_GUIDE §0
```

## 3. 完成的工作（按时间顺序）

### 3.1 比赛 framing 落地（commit `dc2da52`）

**触发**：用户通报团队报名第八届北京智源大会 · Agent for Science 创意大赛（征集截止 2026-05-30）；用户分工是 **Head of Bio Applications**。

**新增**：`docs/bio-adaptation/COMPETITION_NOTES.zh.md`（218 行，10 节）：
1. 比赛事实卡（一屏看清关键日期 / 五项交付 / 评审 / 奖项）
2. 主线三轴 × 生物锚点 framing（Self-evolving / Multi-agent / 能复现 每轴 4-5 个 bio 实证）
3. 五项交付物 × OmegaWiki 现状 × 生物可贡献清单
4. 视频里的生物视觉锤 TOP-8 清单（识别度 × 拍摄成本权衡）
5. 12 天内的 P0/P1/P2 优化清单（0-拆台铁则 + 估时 + 演示用途 + 谁做）
6. 视频脚本骨架 30s 主线版 + 90s 详版（含 40-60s bio reveal 段）
7. 给团队的 5 句话接口（PM / 写论文 / 拍视频 / poster 同事问 bio 时直接抄）
8. 我的近期 todo（按 2026-05-18 → 05-30 时间排序）
9. 关键风险与缓解
10. 链接索引

**修改**：`docs/bio-adaptation/DEMO_GUIDE.zh.md`
- 加 §0 比赛上下文段（把 8 张静态图重新定位为多用途素材：README + Poster + Video + Paper §4）
- §1 图清单加 **用途** 列（README / Poster / Video / Paper §4 标记）
- §3 图 7 路径修正 —— 把原"SPA tooltip 悬停"主路径降级为后备，把 **JSONL `grep` 终端截图**升为主路径（已经在前次会话验证 SPA 不显示边 metadata，证据：`app/modules/graph.js:146-160` 边映射只透传 `id/source/target/label/workflow/symmetric`，metadata 被丢弃；无 edge tap/hover handler）

### 3.2 P0 工作（commit `8137ffb`）

| Pilot | 文件 | 字数 | 演示用途 |
|---|---|---|---|
| **P0-1** | `README.md` 加 "Bio Quick Tour" 段（11 行能力表）+ 修旧数 `63/66 → 65/80` | +47 行 | 第一印象 / poster / paper §4 抄稿 |
| **P0-2** | `examples/output/bio-novelty-report.md`（`/novelty` 5 通道输出，bio-C9 PubMed 信号触发 4→3 降分演示）| 163 行 | 视频锤 #3 (PubMed multi-source) |
| **P0-3a** | `examples/output/bio-ideate-banlist.md`（C3 scope-overlap accept/reject 双例：Arabidopsis low-data 通过 / human high-data 拒绝）| 127 行 | 视频锤 #5 |
| **P0-3b** | `examples/output/bio-exp-design-dose-response.md`（4 bio tag 组合 + 5 ID reproducibility + 失败 taxonomy 预注册）| 156 行 | 视频锤 #6 |
| **P0-4** | **redirected** —— 原 wiki/index.md 是 `tools/research_wiki.py:1628` 自动 rebuild 的，手写内容下次 rebuild-index 被擦；改投 P0-1 README 同段 | 同 P0-1 | poster 数据 |
| **P0-5** | _pending_，留给用户手调 canvas 布局 + 截图 | — | 图 9 / poster panel |

### 3.3 Obsidian Linux 安装（解决 WSL ↔ Obsidian 同步）

**问题**：Obsidian Windows 端通过 `\\wsl.localhost\` UNC 路径打开 vault 报 "加载 obsidian 时发生错误"——已知 Obsidian file watcher 不兼容 WSL 的 9P 协议。

**方案**：WSL 端原生跑 Obsidian Linux（WSLg 推 GUI 窗口到 Windows 桌面，inotify 在 ext4 上原生工作，live sync 通了）。

**步骤**：
1. 验证 WSLg 就绪：`DISPLAY=:0` + `WAYLAND_DISPLAY=wayland-0` + `/mnt/wslg/` ✓
2. 安装 GUI 运行时 6 个库：`libfuse2 libnss3 libnotify-bin libgtk-3-0 libasound2t64 libsecret-1-0`（用户在 WSL 终端 `sudo apt`；中间遇到 Ubuntu 24.04 Noble 的 `t64` 改名 `libasound2 → libasound2t64`，typo `libscret`→`libsecret`，分 3 次跑通）
3. 下载 Obsidian 1.12.7 AppImage（直连 GitHub release-assets CDN 失败，走 `gh-proxy.com` 镜像 1.8 MB/s，119 MB 1 分钟到手）
4. `chmod +x ~/bin/Obsidian.AppImage`；`ln -s` 短链 `~/bin/obsidian`；`~/.bashrc` 加 PATH
5. 写 `~/.local/share/applications/obsidian.desktop` —— Windows 开始菜单可搜到"Obsidian"
6. 测试启动：`Obsidian.AppImage --no-sandbox /home/yukino/OmegaWiki/wiki` GPU 报错（WSLg + Electron 已知，自动回退 CPU 渲染），主进程 PID 276955 起来，窗口在 Win 桌面弹出 ✓

### 3.4 Canvas 布局迭代（两版）

**Version 1：同心圆**
- PTM idea 居中（480×340），ring1 R=1100 / ring2 R=1750
- 5 experiments 下半圈 + 5 close-ideas 上半圈对称（内圈），5 papers + 5 concepts + 2 outer-ideas 交错环绕（外圈，与内圈 15° 错位）
- 用户反馈：箭头汇聚到单一焦点，**label 严重叠在中心**

**Version 2：5 行流水线（当前 disk 状态）**
- 同类型同行：ROW 1 papers / ROW 2 concepts / ROW 3 close-ideas / ROW 4 outer + FOCUS / ROW 5 experiments
- 列对齐：drug-design paper ↓ PTM-inspired-drug-design concept ↓ ptm-protein-isoforms anchor 同 col
- `ptm-protein-isoforms` 放 row 3 col 2（不在正中央）—— 5 experiments tested_by → 它，扇形上来不穿过 focus
- 边的 fromSide/toSide 用 ratio rule（`|dy| > 0.55 × |dx| && |dy| > 80` → 走 top/bottom；其余走 left/right）—— 跨行边大多走垂直，同行边走横向
- 画布 2750 × 1900
- **用户表示稍后手动微调**

## 4. 数据快照

```
五项必交付物 × 当前状态：
  ① 基础信息          ✅ README + Bio Quick Tour 段（本会话补）
  ② 技术报告 ≤9p     ❌ 未开始（P1-4 待 Claude 出 §4 草稿 1.5 页）
  ③ Poster 海报      ❌ 未开始（等 8 PNG + canvas 出图）
  ④ 公开仓库          ✅ 已开源；28 commits ahead of main 未 push
  ⑤ Demo 视频        ❌ 未拍摄（剧本已就绪：30s + 90s 双版见 COMPETITION_NOTES §6）

视觉锤就绪度（COMPETITION_NOTES §4 表）：
  锤 1: SPA 14 bio edge labels live           ✅ SPA 跑着，截图待
  锤 2: 5 ID reproducibility 同屏             ✅ wiki/experiments/deepternary-baseline-... 在位
  锤 3: /novelty PubMed multi-source          ✅ examples/output/bio-novelty-report.md（本会话）
  锤 4: typed metadata grep 输出              ✅ edges.jsonl 第 79 行 + grep 命令在 DEMO_GUIDE §3
  锤 5: /ideate banlist scope accept/reject   ✅ examples/output/bio-ideate-banlist.md（本会话）
  锤 6: /exp-design dose_response 输出         ✅ examples/output/bio-exp-design-dose-response.md（本会话）
  锤 7: datasets/ternarydb versions 表        ✅ wiki/datasets/ternarydb.md
  锤 8: lint_bio cross-check 通过日志          ⏸ 等 P1-1 加 cellosaurus check

wiki 实体（与 2026-05-12 一致 —— 本会话未动 wiki 内容）：
  papers 11 / concepts 25 / topics 1 / people 16 / ideas 22（11 validated / 2 failed / 9 其他）
  experiments 8 (8/8 in_silico) / methods 0 / datasets 1 / summaries 1 / foundations 0
  graph edges: 80（含 7 条 bio relation live / 4 条 typed metadata live）
  bio lint: 0 🔴 / 0 🟡 / 0 🔵
  base lint: 0 🔴 / 0 🟡 / 11 🔵
```

## 5. 待决 / 未决事项

| 决策 | 选项 | 谁决 |
|---|---|---|
| Push target | 重建 `origin/dev`？直 PR 到 main？维持不 push？ | 用户 + 团队 |
| Canvas 手调后是否 commit | wiki/canvases/ 被 .gitignore 屏蔽，**手调改动不进 git**；只有截图 `demo-09-canvas.png` 会进 commit | 用户 |
| COMPETITION_NOTES / CHECKPOINT en 镜像 | memory 规则要求双语，但临时作战文档可豁免；最终论文 §4 会是英文，可暂缓 | 用户 |
| 启动 P1 时机 | Claude 待命；用户拍板"开 P1"即启（~7h 工作量散到 3-5 天） | 用户 |
| 删除调试截图 | `assets/屏幕截图 2026-05-18 18{2111,3746}.png` 是 canvas 迭代中间产物，可删 | 用户 |

## 6. 新对话恢复指令

```
读 docs/bio-adaptation/CHECKPOINT-2026-05-18.zh.md 与
docs/bio-adaptation/COMPETITION_NOTES.zh.md。分支 feat/qwt-ptm-degrader-ideate @ 8137ffb；
lint 0/0/11 + 0/0/0；28 commits ahead of main；0 push。

报名第八届北京智源大会 Agent for Science 创意大赛，征集截止 2026-05-30。
User = Head of Bio Applications；bio 是 case study 不是分赛道；主线 self-evolving × multi-agent
由 PM/Lead 主导，bio 在视频中段 20s reveal、poster 占 1 panel、论文 §4 占 1.5–2 页。

本次会话目标按用户当前优先级：
  1. 用户手调 canvas（5 行流水线 baseline 已写盘，wiki/canvases/.../...canvas）
     - Obsidian 启动：~/bin/obsidian   （或 Win 开始菜单搜 Obsidian）
     - 微调后截 assets/demo-09-canvas.png
  2. 按 DEMO_GUIDE §3 截剩下 7 张 PNG（图 1-8）
  3. 决定要不要启 P1（清单见 COMPETITION_NOTES §5）

可启 P1 工作（用户拍板后 Claude 接手）：
  P1-1  tools/lint_bio.py 加 cellosaurus CVCL_[A-Z0-9]{4} 格式 check (~1.5h)
  P1-2  wiki/graph/edges.jsonl 加 3 条 live bio 边（lenalidomide-crbn 等）(~1h)
  P1-3  demo/run-demo-bio.sh + examples/output/bio-demo-output.md (~1.5h)
  P1-4  9 页论文 §4 Domain Adaptation 草稿 1.5 页英文 (~3h)

需要用户做的：
  - Obsidian 内手调 canvas + 截图九
  - Snipping Tool 截图 1-8（DEMO_GUIDE §3 操作逐图说明）
  - 决定 push target

未决事项见 §5。
```

## 7. 文件清单速查

| 类别 | 路径 | 备注 |
|---|---|---|
| **本 checkpoint** | `docs/bio-adaptation/CHECKPOINT-2026-05-18.zh.md` | 本文件（即将 commit） |
| 上次 checkpoint | `docs/bio-adaptation/CHECKPOINT-2026-05-12.zh.md` | A+B+C+D backlog 完结快照 |
| **比赛作战备忘** | `docs/bio-adaptation/COMPETITION_NOTES.zh.md` | 本会话新建（dc2da52）|
| Demo 制作指南 | `docs/bio-adaptation/DEMO_GUIDE.zh.md` | 本会话加 §0 + 用途列（dc2da52）|
| 整体 report | `docs/bio-adaptation/REPORT.zh.md` | 未动 |
| 累计 changelog | `docs/bio-adaptation/CHANGELOG.zh.md` | 未动（39 entries 截至 2026-05-12）|
| Backlog 原档 | `docs/bioinformatics-adaptation-backlog.zh.md` | 未动 |
| README | `README.md` | Bio Quick Tour 段 + 数字修正（8137ffb）|
| Bio 示例输出 | `examples/output/bio-novelty-report.md` | 本会话新建（8137ffb）|
| 同上 | `examples/output/bio-ideate-banlist.md` | 本会话新建（8137ffb）|
| 同上 | `examples/output/bio-exp-design-dose-response.md` | 本会话新建（8137ffb）|
| Canvas 文件 | `wiki/canvases/focus-ideas-ptm-aware-degrader-target-nomination.canvas` | 5 行流水线布局，**.gitignored，本地 only** |
| Canvas 文件 2 | `wiki/canvases/knowledge-map.canvas` | 老的全图 canvas，未动 |
| Demo 脚本 | `demo/run-demo.sh` + `demo/sample-feed.json` | 未动 |
| Demo 预渲染输出 | `examples/output/digest-sample.md` | 未动 |
| Obsidian AppImage | `~/bin/Obsidian.AppImage`（119 MB，1.12.7）| WSL 用户家目录，**不在 repo 内** |
| Obsidian .desktop | `~/.local/share/applications/obsidian.desktop` | Windows 开始菜单条目 |
| 调试截图（可删） | `assets/屏幕截图 2026-05-18 18{2111,3746}.png` | canvas 迭代中间产物，untracked |
| SPA 后台进程 | `tools/serve.py` PID 退出（用户关 Obsidian 时连带退出？）| 需要时重启 `.venv/bin/python tools/serve.py` |

## 8. 给下次自己的备注

- canvas 手调时，Obsidian 是 live sync 的 —— 用户在 Obsidian 里拖完，wiki/canvases/*.canvas 文件已经同步写盘，**无需手动保存**
- 用户**拖出来的布局不会进 git**（.gitignore），但**截图会进**（assets/demo-09-canvas.png）—— 这是 by design：源 canvas 是工作产物，截图是交付物
- P1-2 加 live bio 边时要注意 `concepts/lenalidomide` 等可能不存在；要么先 `/ingest` 相关 paper 让 concept 自动生成，要么手工建 concept 页面（不建议，破坏 wiki write-only-by-skill 约定）
- P1-4 论文 §4 草稿是英文 ICLR 模板，Overleaf URL: https://www.overleaf.com/read/bvsdjzdttszt#4023ef
- bio 5 句话接口（COMPETITION_NOTES §7）是给团队其他人的，**不是给评委的**——评委看的是 paper + poster + 视频，5 句话是内部沟通用
