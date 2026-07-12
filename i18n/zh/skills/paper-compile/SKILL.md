---
name: paper-compile
description: LaTeX 编译 → PDF：latexmk 编译 + 自动修复 + 页数/匿名/字体/[UNCONFIRMED] 检查 + 提交清单
---

# paper-compile

> 编译 LaTeX 论文为 PDF，自动修复常见错误，验证提交要求。
> 输入 paper/ 目录（由 paper-draft 生成），执行 latexmk 编译，
> 解析错误并尝试自动修复（缺失包、引用未定义、figure 路径），
> 验证页数限制、匿名合规、字体嵌入、[UNCONFIRMED] 标记清除。
> 生成提交清单。

## Inputs

- `paper_dir`（可选，默认 `paper/`）：LaTeX 项目目录，包含 `main.tex`
- `--fix`（可选）：启用自动修复模式（自动安装缺失包、修正路径）
- `--checklist`（可选）：生成详细提交清单（不编译，只检查）

## Outputs

- `paper/main.pdf` — 编译后的 PDF
- **COMPILE_REPORT**（输出到终端）— 编译状态、检查结果、提交清单
- 若 `--fix`：修改的 .tex 文件（自动修复）

## Wiki Interaction

### Reads
- `wiki/outputs/paper-plan-*.md` — 获取 venue 信息（页数限制、匿名要求）
- `shared-references/citation-verification.md` — [UNCONFIRMED] 标记检查规则

### Writes
- `paper/main.pdf` — 编译输出
- `wiki/log.md` — 追加编译日志

### Graph edges created
- 无

## Workflow

**前置**：确认 `paper/main.tex` 存在。确认 `latexmk` 已安装（`which latexmk`）。

### Step 1: 编译（Compile）

1. **首次编译**：
   ```bash
   cd paper/ && latexmk -pdf -interaction=nonstopmode main.tex 2>&1
   ```

2. **解析编译输出**：
   - 收集所有 errors（`! ...`）
   - 收集所有 warnings（`Warning:` / `Overfull` / `Underfull`）
   - 分类：
     - **Missing package**：`! LaTeX Error: File 'xxx.sty' not found`
     - **Undefined reference**：`LaTeX Warning: Reference 'xxx' on page N undefined`
     - **Undefined citation**：`LaTeX Warning: Citation 'xxx' on page N undefined`
     - **Missing figure**：`! LaTeX Error: File 'figures/xxx' not found`
     - **Syntax error**：其他 `!` 开头的错误
     - **Overfull/Underfull**：排版警告（非阻塞）

3. **若编译成功**（main.pdf 生成）：进入 Step 3
4. **若编译失败**：进入 Step 2

### Step 2: 自动修复（Auto-Fix）

若 `--fix` 启用，尝试自动修复每种错误类型：

**2a. Missing package**：
```bash
# 检查是否为 TeX Live 可安装包
tlmgr info {package-name} 2>/dev/null
# 若可安装且用户确认：
tlmgr install {package-name}
```
若无法安装：注释掉 `\usepackage{xxx}` 行并标注 `% TODO: install package {xxx}`

**2b. Undefined reference/citation**：
- Undefined reference：检查对应 `\label{}` 是否存在，若不存在则添加占位 label
- Undefined citation：检查 `references.bib` 是否包含该 key
  - 若不包含：尝试从 wiki papers 匹配并添加 [UNCONFIRMED] 条目
  - 若包含但 bibtex 未运行：重新运行 `latexmk`（通常 latexmk 自动处理）

**2c. Missing figure**：
- 检查 `paper/figures/` 中是否存在不同扩展名的文件（.pdf vs .png vs .eps）
- 若找到：修正 `\includegraphics` 路径
- 若找不到：替换为占位符 `\missingfigure{xxx}`（需要 `todonotes` 包）

**2d. Syntax error**：
- 常见修复：未闭合的 `{}`、`\begin{}`/`\end{}` 不匹配、非法字符
- 尝试定位错误行号，提供具体修复建议
- 若无法自动修复：报告错误位置和建议

**修复后重新编译**（最多 3 轮 fix-compile 循环）：
```bash
cd paper/ && latexmk -pdf -interaction=nonstopmode main.tex 2>&1
```

### Step 3: 验证检查（Verify）

编译成功后执行以下检查：

**3a. 页数检查**：
```bash
# 获取 PDF 页数
python3 -c "
import subprocess
result = subprocess.run(['pdfinfo', 'paper/main.pdf'], capture_output=True, text=True)
for line in result.stdout.splitlines():
    if line.startswith('Pages:'):
        print(line.split(':')[1].strip())
"
```
与 venue 页数限制对比（从 PAPER_PLAN 的 venue 或 academic-writing.md 的 venue 表获取）。
- 超限：报告超出页数，建议压缩或移至 appendix
- 不足：报告剩余空间，建议补充内容

**3b. 匿名检查**：
扫描所有 .tex 文件：
- 搜索作者姓名（若 `\author{}` 非空 → 警告）
- 搜索机构名（university, lab, institute → 警告）
- 搜索 GitHub/GitLab 链接（可能泄露身份 → 警告）
- 搜索 "our previous work" / "we previously" → 应使用第三人称引用
- 搜索 `\thanks{}` / `\acknowledgments` → 匿名提交应移除

**3c. [UNCONFIRMED] 标记检查**：
```bash
# 扫描 references.bib 和所有 .tex 文件
grep -rn "VERIFY" paper/
```
- 若存在 [UNCONFIRMED] 标记：列出每个，标注为 **提交阻塞项**
- 参照 citation-verification.md：[UNCONFIRMED] 是提交的硬阻塞

**3d. 字体嵌入检查**：
```bash
pdffonts paper/main.pdf
```
- 检查 "emb" 列：所有字体应为 "yes"
- 未嵌入字体：报告字体名，建议在编译选项中添加字体嵌入

**3e. 内容完整性检查**：
- 搜索 `TODO`、`FIXME`、`XXX` 标记
- 搜索 `\missingfigure`、空 section（`\section{X}` 后无内容）
- 搜索未引用的 figures/tables（`\includegraphics` 存在但无 `\ref`）
- 检查 abstract 是否存在且非空

### Step 4: 生成提交清单和报告

```markdown
# Compile Report

## Compilation
- Status: {SUCCESS / FAILED}
- Compiler: latexmk + pdflatex
- Rounds: {N} (including auto-fix rounds)
- Errors: {N} (fixed: {M}, remaining: {K})
- Warnings: {N} (overfull: {O}, underfull: {U}, other: {W})

## Verification Results

| Check | Status | Details |
|-------|--------|---------|
| Page count | {PASS/FAIL} | {N} pages (limit: {L}) |
| Anonymous | {PASS/WARN} | {details} |
| [UNCONFIRMED] citations | {PASS/FAIL} | {N} remaining |
| Fonts embedded | {PASS/FAIL} | {details} |
| No TODOs | {PASS/WARN} | {N} remaining |
| Figures referenced | {PASS/WARN} | {details} |
| Abstract present | {PASS/FAIL} | {details} |

## Submission Checklist

- [ ] PDF compiles without errors
- [ ] Page count within venue limit ({L} pages)
- [ ] All [UNCONFIRMED] citations resolved
- [ ] Anonymous submission (no author info)
- [ ] All fonts embedded
- [ ] No TODO/FIXME markers
- [ ] All figures referenced in text
- [ ] Abstract present and complete
- [ ] Supplementary material prepared (if applicable)
- [ ] Paper title matches submission system

## Blocking Issues
{list of FAIL items that must be resolved before submission}

## Warnings (non-blocking)
{list of WARN items for consideration}

## Next Steps
- {specific actions to resolve blocking issues}
- Run `refine paper/main.tex --focus writing` for final polish
- Manual review of anonymous compliance
```

追加日志：
```bash
python3 tools/research_wiki.py log wiki/ \
  "paper-compile | {SUCCESS/FAILED} | {pages} pages, {errors} errors, {verify_count} [UNCONFIRMED], {checks_passed}/{checks_total} checks passed"
```

## Constraints

- **不修改 wiki 内容**：只操作 paper/ 目录和 wiki/log.md
- **自动修复需 --fix 启用**：默认只报告错误不修复
- **[UNCONFIRMED] 是硬阻塞**：submission checklist 中 [UNCONFIRMED] 存在 = 不可提交
- **最多 3 轮 fix-compile**：防止无限修复循环
- **不删除用户内容**：auto-fix 只添加或修正，不删除用户手写的内容
- **pdfinfo/pdffonts 依赖**：若未安装，跳过对应检查并标注「tool not available」
- **匿名检查是启发式的**：可能有 false positive，标注为 WARN 而非 FAIL

## Error Handling

- **main.tex 不存在**：报错，建议先运行 paper-draft
- **latexmk 未安装**：报错，提供安装命令（`sudo apt install texlive-full` 或 `brew install --cask mactex`）
- **编译失败且无法自动修复**：输出完整错误日志 + 定位到具体 .tex 文件和行号
- **pdfinfo/pdffonts 未安装**：跳过页数/字体检查，在报告中标注
- **PAPER_PLAN 找不到**：跳过 venue 信息提取，使用默认限制（10 pages），警告用户
- **权限问题**（tlmgr 需要 sudo）：报告需要手动安装的包列表

## Dependencies

### Tools（via bash）
- `latexmk` — LaTeX 编译
- `pdfinfo` — PDF 页数检查（poppler-utils）
- `pdffonts` — 字体嵌入检查（poppler-utils）
- `python3 tools/research_wiki.py log wiki/ "<message>"` — 追加日志

### MCP Servers
- 无

### Agent Runtime Capabilities
- `Read` — 读取 .tex 文件和编译日志
- `Edit` — 自动修复 .tex 文件（--fix 模式）
- `bash` — 执行编译和检查命令
- `grep` — 搜索 [UNCONFIRMED]、TODO、匿名违规

### Shared References
- `shared-references/citation-verification.md` — [UNCONFIRMED] 标记检查规则
- `shared-references/academic-writing.md` — venue 页数限制参考

### Called by
- `research` Stage 5（论文编译阶段）
- 用户手动调用
