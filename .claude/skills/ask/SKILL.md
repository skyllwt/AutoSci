---
description: Ask the wiki a question, retrieve and synthesize relevant pages, optionally crystallize the answer back into the wiki
argument-hint: <question>
---

# /ask

> Ask a question to the wiki knowledge base. The LLM reads context_brief.md for global context,
> retrieves relevant pages, synthesizes an answer with citations. Good answers can be
> crystallized back into the wiki — written to outputs/, as new concept pages, or appended
> to an existing idea/method/output note — so exploration compounds like ingestion does.

## Inputs

- `question`: natural-language question (e.g. "What is the core difference between LoRA and Adapter?")
- `--crystallize` (optional): if specified, crystallize the answer back into the wiki (default: answer only, no write)
- `--format` (optional): output format, default `markdown`, options: `table` / `timeline` / `bullets`

## Outputs

- **Always**: terminal output of synthesized answer (with `[[slug]]` citations)
- **If crystallize**:
  - `wiki/outputs/{query-slug}.md` — query result page (default crystallize target)
  - or `wiki/concepts/{slug}.md` — if the answer reveals a new cross-paper concept
  - or appended to an existing `wiki/ideas/{slug}.md` / `wiki/methods/{slug}.md` / `wiki/outputs/{slug}.md` — if the answer adds a finding to an existing entity
  - updated `wiki/graph/edges.jsonl` (relationships produced by crystallize)
  - updated `wiki/index.md` and `wiki/log.md`

## Wiki Interaction

### Reads
- `wiki/graph/context_brief.md` — global compressed context (ideas, gaps, failed ideas, papers, edges)
- `wiki/index.md` — page catalog for locating relevant pages
- `wiki/graph/open_questions.md` — open questions, helps identify whether the question touches known gaps
- `wiki/papers/*.md` — paper pages relevant to the question
- `wiki/concepts/*.md` — concept pages relevant to the question
- `wiki/methods/*.md` — method pages relevant to the question
- `wiki/topics/*.md` — topic pages relevant to the question
- `wiki/people/*.md` — if the question involves specific researchers
- `wiki/ideas/*.md` — if the question involves research ideas or failed ideas
- `wiki/experiments/*.md` — if the question involves experiment results
- `wiki/Summary/*.md` — if the question involves domain-wide landscape

### Writes (crystallize mode only)
- `wiki/outputs/{query-slug}.md` — CREATE (query result page)
- `wiki/concepts/{slug}.md` — CREATE (newly discovered concept) or EDIT (supplement existing concept)
- `wiki/ideas/{slug}.md` / `wiki/methods/{slug}.md` / `wiki/outputs/{slug}.md` — EDIT (append finding to existing page)
- `wiki/graph/edges.jsonl` — APPEND (relationships produced by crystallize)
- `wiki/graph/context_brief.md` — REBUILD (if crystallize created new pages)
- `wiki/graph/open_questions.md` — REBUILD (if crystallize created new pages)
- `wiki/index.md` — EDIT (if crystallize created new pages)
- `wiki/log.md` — APPEND

### Graph edges created (crystallize only)
- `output → paper`: `derived_from` (papers cited in the answer)
- `output → concept`: `derived_from` (concepts cited in the answer)
- `output → idea` / `output → method`: `derived_from` (ideas or methods cited in the answer)
- `concept → paper`: `supports` (if a new concept is generalized from papers)

## Workflow

**Precondition**: confirm working directory is the wiki project root (containing `wiki/`, `raw/`, `tools/`).
Set `WIKI_ROOT=wiki/`.

### Step 1: Load Global Context

1. Read `wiki/graph/context_brief.md` — get compressed snapshot of wiki's current knowledge (ideas, gaps, papers, edges)
2. Read `wiki/graph/open_questions.md` — understand known open questions and knowledge gaps
3. If both are missing, rebuild first:
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

### Step 2: Retrieve Relevant Pages

1. Read `wiki/index.md`, match relevant slugs against question keywords
2. Extract ideas, methods, and papers semantically related to the question from context_brief.md
3. Sort by relevance, select top-K pages (K ≤ 15 to avoid exceeding context window)
4. Read full content of selected pages
5. If the question involves relationships (e.g. "difference between X and Y"), additionally read edges connecting X and Y from `wiki/graph/edges.jsonl`

### Step 3: Synthesize Answer

1. Synthesize an answer to the user's question based on collected page content
2. Answer requirements:
   - **Cited**: every key statement must include a `[[slug]]` wikilink pointing to its source page
   - **Structured**: organize output according to `--format` parameter (markdown / table / timeline / bullets)
   - **Acknowledge uncertainty**: clearly flag "insufficient evidence in wiki" for parts with weak support
   - **Flag knowledge gaps**: if the question touches a known gap in open_questions.md, call it out explicitly
   - **Cite idea status**: when referencing ideas, note their `status` and `novelty_score`
3. If the question exceeds the wiki's current knowledge, honestly say so and suggest:
   - which papers to ingest to fill the gap
   - possible search directions (arXiv keywords, Semantic Scholar queries)

### Step 4: Assess Crystallize Value

1. Judge whether the answer is worth writing back to the wiki (make a recommendation even if `--crystallize` was not specified)
2. Signals that crystallize is worthwhile:
   - The answer synthesizes information from multiple papers, forming a new cross-paper insight
   - The answer reveals a concept not yet explicitly recorded in the wiki
   - The answer adds a finding that strengthens an existing idea, method, or output note
   - The answer addresses a known gap in open_questions.md
3. Signals that crystallize is not worthwhile:
   - The answer merely restates the content of a single page
   - The question is a simple factual lookup (e.g. "What year was LoRA published?")
   - The answer relies primarily on inference rather than wiki evidence
4. Append a crystallize recommendation at the end of the answer:
   ```
   💡 Crystallize recommendation: [worthwhile / not needed] — [reason]
   ```

### Step 5: Crystallize Back to Wiki (if user confirms or --crystallize was specified)

Choose the crystallize target based on answer content:

**Case A — Write to outputs/ (default):**
1. Generate slug: `python3 tools/research_wiki.py slug "<query-summary>"`
2. Create `wiki/outputs/{query-slug}.md`:
   ```yaml
   ---
   title: ""
   slug: ""
   query: ""           # original question
   source_pages: []    # slugs of all pages cited in the answer
   date_created: YYYY-MM-DD
   ---
   ```
   Body is the answer content (preserve wikilinks)
3. Add a graph edge for each cited source page:
   ```bash
   python3 tools/research_wiki.py add-edge wiki/ --from outputs/<slug> --to papers/<source-slug> --type derived_from --evidence "query answer"
   ```

**Case B — Create new concept:**
1. If the answer reveals a new concept: create `wiki/concepts/{slug}.md` using the CLAUDE.md concept template
2. maturity: emerging
3. key_papers: extracted from answer citations
4. Add graph edges (concept → papers)
5. Append reverse links to relevant paper pages under `## Related`

**Case C — Append finding to an existing idea, method, or output note:**
1. If the answer extends a finding tied to an existing entity, append a short paragraph (with `[[slug]]` citations) to the appropriate section:
   - `wiki/ideas/{slug}.md` → `## Lessons learned` or `## Pilot results`
   - `wiki/methods/{slug}.md` → `## Limitations` or `## Tradeoff profile`
   - `wiki/outputs/{slug}.md` → end of the body
2. Add graph edges from the touched page to the cited papers/concepts/methods (`derived_from`)
3. Do not create a new entity; this case only enriches an existing one

### Step 6: Update Navigation and Graph (crystallize only)

1. **index.md**: append new page entries under the appropriate category
2. **log.md**:
   ```bash
   python3 tools/research_wiki.py log wiki/ "ask | <question-summary> | crystallized: <target-path>"
   ```
   If not crystallized:
   ```bash
   python3 tools/research_wiki.py log wiki/ "ask | <question-summary> | answer-only"
   ```
3. **Rebuild derived graph files** (only if crystallize created new pages):
   ```bash
   python3 tools/research_wiki.py rebuild-context-brief wiki/
   python3 tools/research_wiki.py rebuild-open-questions wiki/
   ```

### Step 7: Report to User

Output a summary including:
- Number and list of retrieved pages
- Answer (with citations and formatting)
- Knowledge gap annotations (if any)
- Crystallize recommendation or execution result
- Follow-up suggestions (papers recommended for ingestion, related open questions)

## Constraints

- **No fabrication**: answers must be grounded in actual wiki content; do not invent from LLM pre-training knowledge
- **Citations must exist**: every `[[slug]]` must point to a page that actually exists in the wiki
- **raw/ is read-only**: do not modify files under `raw/`
- **graph/ only via tools**: do not hand-edit files under `graph/`
- **Crystallize requires confirmation**: unless the user explicitly specifies `--crystallize`, only recommend but do not write
- **Context limit**: retrieve at most 15 pages to stay within context window
- **Cite idea status**: when referencing ideas, always note their `status` and `novelty_score`
- **Flag gaps**: if the question touches a known gap in open_questions.md, explicitly call it out
- **outputs/ frontmatter must include query and source_pages**: ensures traceability

## Error Handling

- **context_brief.md missing**: run `python3 tools/research_wiki.py rebuild-context-brief wiki/` to rebuild, then retry
- **wiki is empty**: inform the user to first run `/init` or `/ingest` to build the knowledge base
- **no matching pages**: honestly report that no relevant content exists in the wiki, suggest search and ingest directions
- **crystallize slug conflict**: append a numeric suffix (e.g. `query-result-2`)
- **index.md missing**: run `python3 tools/research_wiki.py init wiki/` to initialize, then retry

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py slug "<title>"` — slug generation
- `python3 tools/research_wiki.py add-edge wiki/ --from <id> --to <id> --type <type> --evidence "<text>"` — add graph edge
- `python3 tools/research_wiki.py rebuild-context-brief wiki/` — rebuild compressed context
- `python3 tools/research_wiki.py rebuild-open-questions wiki/` — rebuild knowledge gap map
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log entry
- `python3 tools/research_wiki.py init wiki/` — initialize wiki (fallback)

### Skills（via Skill tool）
- `/ingest` — referenced when suggesting the user supplement knowledge

### Shared References
- `.claude/skills/shared-references/citation-verification.md` (created in Phase 3)
