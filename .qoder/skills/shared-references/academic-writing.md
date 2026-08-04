# Academic Writing Principles

> Shared reference for all skills that produce written output: /paper-draft, /paper-plan, /survey.
> These principles ensure publication-quality writing that reads as expert-authored, not AI-generated.

---

## 1. Narrative Structure

### The Hourglass Shape

Every well-structured paper follows an hourglass:

```
BROAD:   Introduction — why this matters to the field
NARROW:  Method — exactly what we did
NARROW:  Experiments — exactly what happened
BROAD:   Discussion — what this means for the field
```

### Section-Level Rules

- **Introduction**: Start with the problem (not the solution). The reader must feel the gap before you fill it.
  - Paragraph 1: broad context and importance
  - Paragraph 2: specific problem and why existing approaches fall short
  - Paragraph 3: "In this work, we..." — your contribution
  - Paragraph 4: summary of results and paper structure

- **Related Work**: Organize by theme, not by paper. Each paragraph covers a research direction, not a single citation.
  - End each paragraph with how your work differs from that direction
  - Never write a flat list of "X did Y. Z did W."

- **Method**: Lead with intuition before formalism. A reader should understand *why* before *how*.
  - One figure showing the overall architecture (mandatory)
  - Notation introduced before first use
  - Each subsection = one design decision

- **Experiments**: Claim-first structure. Each subsection begins with the claim it validates.
  - "We claim X. To verify, we..." (not "We ran experiment A. Results show...")
  - Tables before discussion (readers scan tables first)
  - Error bars or confidence intervals mandatory

- **Conclusion**: New insight, not summary. What should the reader remember tomorrow?

## 2. Clarity Rules

### Sentence Level

- **One idea per sentence.** If a sentence has "and" + "which" + "that", split it.
- **Active voice by default.** "We train the model" not "The model is trained."
- **Specific > vague.** "Reduces latency by 40%" not "significantly improves performance."
- **Define before use.** Every acronym spelled out on first use. Every symbol defined before first equation.

### Paragraph Level

- **Topic sentence first.** Every paragraph starts with its main claim.
- **One point per paragraph.** If you find yourself writing "Additionally" mid-paragraph, start a new one.
- **Transitions between paragraphs.** The last sentence of paragraph N should connect to the first sentence of paragraph N+1.

### Notation Consistency

- Define a `math_commands.tex` file for shared notation
- Same symbol = same meaning throughout the paper
- Bold lowercase for vectors (**x**), bold uppercase for matrices (**W**), calligraphic for sets
- Never redefine a symbol mid-paper

## 3. Figure and Table Design

### Figures

- **Every figure must be referenced in text** and discussed (not just displayed)
- **Colorblind-safe palettes**: use distinguishable patterns + colors (never rely on color alone)
- **Font size >= 8pt** in all labels, legends, axis ticks
- **Vector format preferred** (PDF/SVG for line plots, PNG only for photos/screenshots)
- **Caption is self-contained**: a reader should understand the figure from its caption alone
- **Consistent style**: all figures use the same font, line width, color scheme

### Tables

- **Horizontal rules only** (no vertical lines, no full grid): `\toprule`, `\midrule`, `\bottomrule`
- **Best result in bold**, second-best underlined
- **Units in column header**, not in every cell
- **Align decimal points** in numeric columns
- **Caption above table** (convention in most ML venues)

## 4. De-AI Polish Rules

AI-generated text has recognizable patterns. These must be eliminated before submission.

### Words and Phrases to Remove or Replace

| AI Pattern | Replace With |
|------------|-------------|
| "delve into" | "examine" / "analyze" / remove entirely |
| "it is worth noting that" | remove (just state the thing) |
| "it is important to note" | remove |
| "in the realm of" | "in" |
| "leverage" (as verb) | "use" / "exploit" / "apply" |
| "utilize" | "use" |
| "facilitate" | "enable" / "allow" / remove |
| "comprehensive" (without evidence) | remove or quantify |
| "crucial" / "pivotal" | "important" / "key" / remove |
| "Furthermore" at paragraph start | vary: "Moreover" / "In addition" / restructure |
| "In conclusion" (exact phrase) | "To summarize" / restructure without filler |
| "a myriad of" | "many" / "various" / specific number |
| "shed light on" | "reveal" / "clarify" / "show" |
| "pave the way for" | "enable" / remove |
| "cutting-edge" / "state-of-the-art" (as filler) | only use SOTA when citing specific benchmarks |
| "robust" (without robustness experiments) | remove or qualify |
| "novel" (overuse) | use once in abstract + once in intro, no more |

### Structural Patterns to Fix

- **Excessive hedging**: "It could potentially be argued that X might..." → "X is likely because..."
- **Redundant topic shifts**: "Having discussed X, we now turn to Y" → just start Y
- **Enumeration addiction**: "First... Second... Third..." in every paragraph → vary structure
- **Superlative inflation**: "groundbreaking", "revolutionary" → let results speak
- **Repetitive sentence openings**: vary subject-verb patterns across consecutive sentences

### The Polish Pass

After drafting, run this mental checklist on every paragraph:

1. Could a reviewer guess this was AI-generated? If yes, rewrite.
2. Does every adjective earn its place? Remove unearned superlatives.
3. Is there a shorter way to say this? Use it.
4. Does this paragraph add information, or just fill space? Cut filler.
5. Read aloud: does it sound like a human expert wrote it?

## 5. Venue-Specific Formatting

### Page Limits (typical)

| Venue | Main | References | Appendix |
|-------|------|-----------|----------|
| ICLR | 10 pages | unlimited | unlimited |
| NeurIPS | 9 pages | unlimited | unlimited |
| ICML | 8 pages | unlimited | unlimited |
| ACL | 8 pages (long) | unlimited | unlimited |
| CVPR | 8 pages | +2 pages | — |
| IEEE TPAMI | ~20 pages | included | — |

### Anonymity Rules

- No author names, affiliations, or acknowledgments in submission
- No "our previous work [1]" — use "Smith et al. [1]" (third person)
- No GitHub links to identifiable repos
- No institution-specific cluster names

## What NOT To Do

- **Never submit without de-AI polish** — reviewers increasingly check for AI patterns
- **Never use filler paragraphs** — every paragraph must advance the argument
- **Never present results without context** — "95% accuracy" means nothing without baseline comparison
- **Never mix tenses** — Method in present tense, experiments in past tense, results in present
- **Never cite without discussing** — every \cite must be accompanied by how it relates to your work
