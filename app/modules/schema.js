// Single source of truth for ΩmegaWiki entity-type schema constants.
//
// These mirror tools/visualize.py:ENTITY_DIRS and the 9 page types listed in
// CLAUDE.md / docs/runtime-page-templates.en.md. They are the project's
// schema, not user data — every user's wiki has the same 9 directory names.
//
// Future-proofing: if a new entity type is ever added (e.g. `protocols`),
// extend it here in one place and all views pick it up automatically.

// Canonical directory names, exact case (note: "Summary" is capitalized).
export const ENTITY_DIRS = Object.freeze([
  "papers", "concepts", "topics", "people",
  "ideas", "experiments", "claims", "Summary", "foundations",
]);

// Set form for fast `has()` checks (router uses this).
export const VALID_TYPES = new Set(ENTITY_DIRS);

// Priority order for resolving ambiguous wikilinks `[[slug]]` that match
// multiple entity types. Papers/concepts/topics rank highest because those
// are the most-referenced surfaces; foundations is terminal.
export const TYPE_PRECEDENCE = Object.freeze([
  "papers", "concepts", "topics", "claims", "people",
  "ideas", "experiments", "Summary", "foundations",
]);

// Human-readable display labels for the topnav, breadcrumb, and cards.
export const ENTITY_LABEL = Object.freeze({
  papers: "Papers",
  concepts: "Concepts",
  topics: "Topics",
  people: "People",
  ideas: "Ideas",
  experiments: "Experiments",
  claims: "Claims",
  Summary: "Summary",
  foundations: "Foundations",
});

// Edge-workflow color palette (used by Graph view to color edges by their
// semantic category). Mirrors tools/visualize.py:EDGE_WORKFLOW_COLORS.
export const EDGE_WORKFLOW_COLORS = Object.freeze({
  ingest: "#5B8BD9",
  claim_evidence: "#59C189",
  experiment: "#E6A23C",
  idea: "#F5A623",
  provenance: "#999999",
});

// Edge-type → workflow mapping. Mirrors tools/_schemas.py:EDGE_TYPE_SPECS
// (workflow field) plus the synthetic "cites" type for citations.jsonl.
export const EDGE_TYPE_WORKFLOW = Object.freeze({
  // ingest workflow (paper-paper + paper-concept)
  same_problem_as: "ingest",
  similar_method_to: "ingest",
  complementary_to: "ingest",
  builds_on: "ingest",
  compares_against: "ingest",
  improves_on: "ingest",
  challenges: "ingest",
  surveys: "ingest",
  introduces_concept: "ingest",
  uses_concept: "ingest",
  extends_concept: "ingest",
  critiques_concept: "ingest",
  cites: "ingest",
  // claim evidence
  supports: "claim_evidence",
  contradicts: "claim_evidence",
  // experiment
  tested_by: "experiment",
  invalidates: "experiment",
  // idea / gap
  addresses_gap: "idea",
  inspired_by: "idea",
  // provenance
  derived_from: "provenance",
});
