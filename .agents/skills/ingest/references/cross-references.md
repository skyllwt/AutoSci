# /ingest Cross-References

Open this reference when you are writing a link on any wiki page. Every forward link has a reverse obligation (except to foundations). The table below is the contract.

## Forward → reverse obligation

Mirrors the matrix in the root `CLAUDE.md` ("Cross-Reference Rules"), trimmed to the edges `/ingest` actually writes:

| Forward action (what you write on page A) | Required reverse action (what you also write on page B in the same turn) |
|-------------------------------------------|--------------------------------------------------------------------------|
| `papers/P` writes `Related: [[concept-K]]` | `concepts/K` appends `P` to `key_papers` |
| `papers/P` writes `[[person-R]]` (any body section) | `people/R` appends `[[P]]` to `## Recent work` |
| `concepts/K` writes `key_papers: [[paper-P]]` | `papers/P` appends `K` to `## Related` |
| `methods/M` writes `source_papers: [[paper-P]]` | `papers/P` appends `M` to `## Related` |
| `methods/M` writes `parent_methods: [[method-N]]` | `methods/N` appends `M` to `child_methods` (and vice versa) |
| any page writes `[[foundation-X]]` | **no reverse link** — foundations are terminal |

Writing a forward link without its reverse is the most common way `/check` surfaces `missing-field` errors. Doing both together eliminates the class entirely.

## Foundations are terminal

Never modify a foundation page from `/ingest`. No `key_papers` field, no back-reference of any kind. A paper linking to a foundation leaves a trace only in two places:

- the paper page's `## Related` contains `[[foundation-slug]]`
- `wiki/graph/edges.jsonl` contains the `paper → foundation` edge with type `derived_from`

Foundations are created only by `/prefill`. `/ingest` never creates foundations, even when a concept candidate looks foundational and has no match. In that case, route the candidate through the ordinary concept path (possibly creating a new concept page), and let the user seed a foundation later if they want to.

## Paper-to-concept semantic edges

Papers relate to concepts by using, introducing, extending, or critiquing
them. Every paper-to-concept semantic edge must include `--confidence high|medium|low`.

Edge-type selection:

- **`introduces_concept`** — strict novelty only: the paper explicitly proposes, coins, defines, or names the concept as a contribution.
- **`uses_concept`** — default for an existing concept that the paper relies on without materially changing it.
- **`extends_concept`** — the paper modifies, generalizes, specializes, or formalizes an existing concept.
- **`critiques_concept`** — the paper argues that a concept has limitations, failure modes, or invalid assumptions.

When uncertain between `introduces_concept` and `uses_concept`, choose
`uses_concept`. When uncertain between `uses_concept` and `extends_concept`,
choose `uses_concept`. Do not emit `paper → concept` edges of type `supports` or
plain `extends`.
The tool rejects missing confidence/evidence and legacy paper-to-concept edge
types on new writes.

## Paper-to-paper edges

The bibliographic layer is separate from the semantic layer:

- always write `graph/citations.jsonl` with `type: cites` when a reference resolves to an existing `wiki/papers/{slug}.md`
- write `graph/edges.jsonl` only when the paper text gives a clear semantic cue
- do not force every citation into a semantic edge

Paper-to-paper semantic edges are intentionally sparse. They require a concrete
relationship between the papers' contributions, not just shared topic,
modality, architecture family, benchmark family, or high-level method words. If
the same statement would be true for dozens of papers in the wiki, skip the
paper-to-paper edge and rely on topic/concept links plus citations instead.

Semantic edge-type selection:

- **`same_problem_as`** — symmetric; both papers attack the same concrete task, research question, or problem formulation, so their proposed answers are directly comparable. Do not use this for broad areas like "attention", "video generation", or "LLM evaluation". Also use this when one of the papers is "complementary" in the sense of attacking the same problem from a different angle.
- **`similar_method_to`** — symmetric; both papers share a distinctive mechanism, formulation, training strategy, or algorithmic design. Do not use this for generic families like "uses transformers", "uses diffusion", or "uses RL".
- **`builds_on`** — directional; this paper directly depends on, adapts, or extends the other paper's specific method, formulation, dataset, result, or system. Includes the "improves on" case — write `builds_on` when this paper claims improved quality / efficiency / scope over the prior work. Do not use this for vague inspiration.
- **`challenges`** — directional; this paper disputes, weakens, or presents counter-evidence against the other paper's result, assumption, or framing.

Note: `compares_against` / `improves_on` / `surveys` / `complementary_to` have been removed.
Comparison baselines belong in `cites`; "improves on" is a subset of `builds_on`;
survey relationships are derived from `papers.contribution_type` containing `survey`.

All paper-to-paper semantic edges must include `--confidence high|medium|low`.
For symmetric types, `tools/research_wiki.py add-edge` canonicalizes the
endpoint order and writes `symmetric: true`.
The tool rejects missing confidence/evidence and legacy paper-paper edge types
on new writes.

- **none / skip** — if none of the above cleanly fits, skip the edge. Graph noise is worse than a missing edge.

When in doubt, skip. Paper-paper semantic edges are for high-signal local
relationships, not clustering by field.

## Writing both sides atomically

For every link `/ingest` writes, the reverse should land in the same turn. In practice that means:

1. Decide on the link.
2. Write the forward entry on the originating page.
3. Write the reverse entry on the target page.
4. If the link also corresponds to a semantic graph edge (paper↔concept, paper↔paper, paper→foundation), emit it via `tools/research_wiki.py add-edge`.
5. If a paper reference resolves to an existing paper page, emit the bibliographic row via `tools/research_wiki.py add-citation`.

This pattern keeps `/check` from flagging half-written links in its next run. It also makes rollbacks straightforward: if a paper ingest is aborted, you can undo both sides together by reverting the paper's edits.

## What `/ingest` does not check here

`/ingest` writes forward and reverse links as it goes, but it does not verify that every pre-existing link in the wiki still has its reverse. That is a full-graph audit and belongs to `/check`. Do not read the entire `wiki/` to look for broken back-references during ingest — the time and token cost is large and the work is redundant with `/check`.
