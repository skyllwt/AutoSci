# /init Planner Policy

Use this reference when reading `.checkpoints/init-plan.json`, trimming the shortlist, or interpreting planner warnings and errors.

## Behavioral Policy

- In seeded mode, derive discovery and ranking cues from local paper titles/abstracts plus notes/web signals when `topic` is omitted.
- In bootstrap mode, if both `topic` and notes/web keywords are absent, surface a planner error instead of issuing an empty search.
- Favor relevance, freshness, connectivity, and survey coverage.
- Prefer one survey/overview when it improves coverage.
- In seeded mode with limited introduced capacity, freshness should dominate and older external non-survey papers should not pile up via citation advantage.
- In bootstrap mode or unusually roomy seeded cases, one older canonical anchor may be acceptable when it materially improves coverage.
- When Chinese note or web content is detected, keep a planner warning that extraction/ranking may be less reliable and treat provisional outputs as lower-confidence.
- If `SEMANTIC_SCHOLAR_API_KEY` is unset, continue anyway and preserve the slower public-rate-limit path as a planner warning.

## LLM Trim Expectations

- Read `.checkpoints/init-plan.json` and explicitly trim the over-picked shortlist before `fetch`.
- Do not skip the trim step even if the shortlist already looks reasonable.
- Emit a final selection artifact before `fetch` containing `shortlist_count`, `final_count`, and the final `candidate_id` list in shortlist order.
- If the final count is out of range, revise the selection before `fetch` unless a documented exception applies.

## Source Of Truth Boundary

- `tools/init_discovery.py` is the implementation authority for exact weights, thresholds, shortlist constants, and scoring math.
- `SKILL.md` and this reference describe orchestration and behavioral expectations only.
- Do not duplicate numeric planner constants here or override tool-owned policy during LLM reasoning.
