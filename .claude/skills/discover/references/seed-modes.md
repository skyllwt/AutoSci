# /discover seed modes

Pick exactly one mode per invocation. The decision is based on what the user (or calling skill) actually said, not on what the wiki contains.

## Anchor mode (`from-anchors`)

Use when the user named one or more specific papers, or when this is a post-`/ingest` `--discover` follow-up.

Triggers:

- "find papers similar to LoRA"
- "what's related to this one I just ingested"
- one or more arXiv URLs / IDs / wiki paper slugs in the request
- `/ingest --discover` invocation (anchor = the just-ingested paper's arXiv ID)

Anchor mode is the strongest signal channel — Semantic Scholar's recommendations endpoint returns semantically similar papers based on its trained model, which is more useful than keyword search when the user has a concrete reference point.

If the user supplies negatives ("not these", "different from X"), pass them via `--negative`. The S2 recommendations endpoint pushes the result distribution away from negative anchors, which is useful when the user wants to escape a sub-area they already know.

## Topic mode (`from-topic`)

Use when the user gave a topic, direction, or set of keywords without naming specific papers.

Triggers:

- "find papers about diffusion model fine-tuning"
- "what's been written on retrieval augmented generation"
- a domain phrase with no anchors

Topic mode runs S2 search and (when available) DeepXiv search, then ranks. It is a lighter alternative to `/init`'s planner: useful for exploration but **not** a replacement for `/init`'s broader bootstrap workflow. If the user wants to seed a fresh wiki with a topic, route them to `/init` instead of bulking up `/discover`.

## Wiki mode (`from-wiki`)

Use when the user asked open-ended "what should I read next" with no anchor and no topic.

Triggers:

- "give me the next batch of papers to read"
- "what's a good follow-up to my current wiki"
- explicit `--from-wiki` flag

Wiki mode picks the wiki's most recently modified paper pages, extracts their arXiv IDs, and uses them as anchors. This implicitly biases discovery toward whatever the user has been working on lately — usually the desired behavior.

If `wiki/papers/` is empty or no papers carry an `arxiv` or `arxiv_id` frontmatter field, wiki mode cannot run. Tell the user the wiki is too sparse and suggest topic mode (or `/init`).

## Venue mode (`from-venue`)

Use when the user asked for papers from a specific conference or workshop and year.

Triggers:

- "show me NeurIPS 2024 papers relevant to my wiki"
- "what did ICML 2023 have on diffusion models"
- "any ICLR 2024 papers I should read"

Venue mode fetches the full paper list for that venue/year from Paper Copilot's public GitHub JSON source (`papercopilot/paperlists`), normalizes each record, and ranks them by relevance to the user's existing wiki content. It requires a non-sparse wiki — if the wiki is too empty, the tool fails clearly rather than returning an unpersonalized list.

Venue mode does **not** use Semantic Scholar or DeepXiv. It does not write to `wiki/` or `raw/`.

## What if the user gave both an anchor and a topic?

Prefer anchor mode. Anchors are a much stronger signal than a topic string. Mention the topic in the user-facing report so they know it was noted, but the discovery itself runs through `from-anchors`.

## What if the user gave both a venue and a topic?

Prefer venue mode if the user explicitly named a venue and year. The topic can be mentioned in the report, but venue mode's ranking is driven by wiki relevance, not by the topic string. If the wiki is too sparse for venue mode, stop with a clear sparse-wiki failure and suggest ingesting more papers or running a separate topic discovery; do not silently fall back to an unpersonalized venue ranking.
