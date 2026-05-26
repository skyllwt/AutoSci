---
description: Generate a Related Work section for a paper from wiki knowledge — thematic grouping → narrative structure → LaTeX output, following citation-verification and academic-writing
argument-hint: <research-question-or-idea-slugs> [--format latex|markdown] [--max-papers 30]
---

# /survey

> Generate a Related Work section ready for direct use in a paper, based on existing wiki knowledge.
> Draw material from wiki/papers/, concepts/, topics/; group by research direction (not paper-by-paper listing).
> End each group with a statement of how it differs from this work. Citations follow citation-verification.md;
> writing follows academic-writing.md Related Work rules.
> Supports LaTeX and Markdown output formats.

## Inputs

- `query`: one of:
  - research question description (free text, e.g. "parameter-efficient fine-tuning for LLMs")
  - list of idea slugs (from wiki/ideas/, used to organize related work around specific ideas)
  - path to PAPER_PLAN.md (extract Related Work section definition from it)
- `--format` (optional, default `latex`): output format
  - `latex`: `\cite{key}` citations, embeddable directly in a paper
  - `markdown`: `[[slug]]` wikilink citations, for wiki archiving
- `--max-papers` (optional, default 30): maximum number of papers to cite

## Outputs

- `wiki/outputs/related-work-{slug}-{date}.md` — Related Work text (archived)
- `wiki/graph/edges.jsonl` — derived_from edges (if a new output is created)
- `wiki/log.md` — appended log entry
- **Terminal output** — Related Work body text (for direct copy-paste)

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — Problem & Context, Key idea, Experiment & Results, Related, My take
- `wiki/concepts/*.md` — Definition, Variants, Comparison, Known limitations
- `wiki/topics/*.md` — Overview, Timeline, Open problems, Seminal works
- `wiki/ideas/*.md` — Hypothesis, Motivation, origin_gaps (if input is idea slugs)
- `wiki/methods/*.md` — Mechanism, Procedure, source_papers (when ideas reference methods)
- `wiki/index.md` — content catalog, filtered by importance
- `wiki/graph/context_brief.md` — global context
- `wiki/graph/edges.jsonl` — inter-paper semantic relationships (same_problem_as, similar_method_to, builds_on, challenges)
- `.claude/skills/shared-references/academic-writing.md` — Related Work writing rules
- `.claude/skills/shared-references/citation-verification.md` — citation discipline

### Writes
- `wiki/outputs/related-work-{slug}-{date}.md` — archived file
- `wiki/graph/edges.jsonl` — derived_from edges
- `wiki/log.md` — appended operation log

### Graph edges created
- `derived_from`: related-work output → source papers

## Workflow

**Precondition**: confirm the working directory is the wiki project root (the directory containing `wiki/`, `raw/`, `tools/`).

### Step 1: Locate Relevant Knowledge

1. **Parse input**:
   - If free text: extract keywords; match against tags and titles in wiki/index.md
   - If idea slugs: read each idea's `origin_gaps` (concepts/topics) and walk to `concepts.key_papers` and topic seminal works to collect related papers; also read methods linked from the idea's `## Approach sketch` and pull their `source_papers`
   - If PAPER_PLAN path: read the Related Work section's groupings and citations
2. **Read wiki/graph/context_brief.md** for global context
3. **Read wiki/graph/edges.jsonl**: extract inter-paper semantic relationships (same_problem_as, similar_method_to, builds_on, challenges)
4. **Build candidate paper list**:
   - Sort by importance descending from index.md
   - Rank by tags and domain match
   - Cap at `--max-papers` papers
5. **If candidate papers < 5**: warn "insufficient related papers; consider /ingest of more papers first"

### Step 2: Deep-Read Related Pages

For each paper in the candidate list:

1. Read `wiki/papers/{slug}.md`: focus on Problem & Context, Key idea, Experiment & Results, My take
2. Read linked `wiki/concepts/*.md`: focus on Definition, Variants, Comparison
3. Read related `wiki/topics/*.md`: focus on Timeline, Open problems

Record for each paper:
- core contribution (one sentence)
- method category (which research direction it belongs to)
- relationship to this work (same problem / similar method / builds on / challenges)
- limitations (extracted from Limitations or My take)

### Step 3: Thematic Grouping

Following the Related Work rules in `shared-references/academic-writing.md`:

1. **Group by research direction** (not paper-by-paper listing):
   - Extract natural groupings from wiki/topics/ and concepts/ classifications
   - 3–8 papers per group
   - Group headings describe research directions (e.g. "Parameter-Efficient Fine-Tuning"), not individual papers
2. **Determine group order**:
   - Broad to specific (major direction → sub-direction → most related methods)
   - Or chronological (foundational → development → recent)
3. **Determine within-group order**:
   - Ascending by year (show progression)
   - Important papers: 2–3 sentences; secondary papers: 1 sentence
4. **Annotate each group's relationship to this work**:
   - End each group with one sentence: "Unlike these approaches, our method..." or "We build upon X by..."

### Step 4: Generate Paragraphs

Following `shared-references/academic-writing.md`:

1. **One or two paragraphs per group**:
   - Opening: background and importance of the direction
   - Body: expand on each paper's contribution in within-group order
   - Closing: positioning relative to this work (required)

2. **Citation format**:
   - `--format latex`: `\cite{key}`, key generated from citation-verification.md naming rules
   - `--format markdown`: `[[slug]]`

3. **Writing standards**:
   - No flat lists ("X did Y. Z did W.")
   - Each paragraph has a topic sentence
   - Use contrastive connectives ("While X focuses on..., Y addresses...")
   - No AI-signature vocabulary (see de-AI list in academic-writing.md)

4. **De-AI polish**:
   - Scan and replace AI-signature vocabulary
   - Vary sentence openings
   - Remove filler sentences

### Step 5: BibTeX Preparation (--format latex only)

If output format is LaTeX, following `shared-references/citation-verification.md`:

1. Collect all `\cite{key}` citations
2. For each key, attempt to fetch BibTeX: DBLP → CrossRef → S2
3. Verified: record BibTeX
4. Unverified: mark `[UNCONFIRMED]`
5. Output list of BibTeX entries (can be appended to paper/references.bib)
6. Report citation coverage

### Step 6: Archive

1. **Generate slug**:
   ```bash
   python3 tools/research_wiki.py slug "<query-keywords>"
   ```

2. **Write archive file**:
   Create `wiki/outputs/related-work-{slug}-{date}.md`:
   ```yaml
   ---
   title: "Related Work: {topic}"
   type: related-work
   format: {latex|markdown}
   paper_count: {N}
   date_generated: YYYY-MM-DD
   ---
   ```
   Body is the complete Related Work text.
   If latex format: append BibTeX entries as an appendix.

3. **Add graph edges**:
   ```bash
   # output → each cited paper
   python3 tools/research_wiki.py add-edge wiki/ \
     --from "outputs/related-work-{slug}-{date}" --to "papers/{paper-slug}" \
     --type derived_from --evidence "Cited in related work section"
   ```

4. **Append log**:
   ```bash
   python3 tools/research_wiki.py log wiki/ \
     "survey | {topic} | {N} papers, {G} groups, format: {format}"
   ```

5. **Terminal output**: complete Related Work body text + citation coverage statistics

## Constraints

- **Only cite papers already in the wiki**: do not fabricate citations; every `\cite{}` or `[[slug]]` must correspond to a page in wiki/papers/
- **Group by theme, not as a flat list**: each paragraph covers a research direction, not "Paper A did X. Paper B did Y."
- **Every group must have a positioning sentence**: state the relationship to this work (at the end — difference or inheritance)
- **Warn when candidate papers < 5**: prompt user to /ingest more papers first
- **BibTeX follows citation-verification.md**: do not generate from LLM memory (--format latex only)
- **De-AI polish is mandatory**: a polish pass must be applied after generation
- **Archive to outputs/**: do not directly modify wiki papers/concepts/topics pages
- **Graph edges via tools/research_wiki.py**: do not manually edit edges.jsonl

## Error Handling

- **Fewer than 3 wiki papers**: error; suggest /ingest of enough papers first
- **No matching papers**: broaden search scope (relax tag matching); if still none, error
- **All BibTeX fetches failed** (latex format): use [UNCONFIRMED] placeholders; report count
- **PAPER_PLAN format mismatch**: ignore plan's grouping suggestions; use automatic grouping
- **Slug conflict**: append date suffix

## Dependencies

### Tools（via Bash）
- `python3 tools/research_wiki.py slug "<title>"` — generate slug
- `python3 tools/research_wiki.py add-edge wiki/ ...` — add graph edge
- `python3 tools/research_wiki.py log wiki/ "<message>"` — append log
- `python3 tools/fetch_s2.py search "<title>"` — BibTeX fallback (S2 search)

### MCP Servers
- None (survey does not require Review LLM; use /review --focus writing for separate review)

### Claude Code Native
- `Read` — read wiki pages
- `Glob` — find ideas, methods, concepts, topics, papers
- `WebFetch` — DBLP / CrossRef BibTeX fetch (--format latex only)

### Shared References
- `.claude/skills/shared-references/academic-writing.md` — Related Work writing rules + de-AI polish
- `.claude/skills/shared-references/citation-verification.md` — BibTeX fetch and [UNCONFIRMED] protocol

### Called by
- `/paper-draft` Step 3 (Related Work section can be delegated to this skill)
- Manual user invocation
