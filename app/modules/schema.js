// Single source of truth for ΩmegaWiki entity-type schema constants.
//
// These mirror tools/visualize.py:ENTITY_DIRS and the page types declared in
// runtime/schema/entities.yaml (the SSOT). They are the project's schema, not
// user data — every user's wiki has the same set of directory names.
//
// Future-proofing: if a new entity type is ever added (e.g. `protocols`),
// extend it here in one place and all views pick it up automatically.

// Canonical directory names, exact case. Mirrors runtime/schema/entities.yaml.
export const ENTITY_DIRS = Object.freeze([
  "papers", "concepts", "topics", "people",
  "ideas", "experiments", "methods", "foundations",
  "manuscripts", "reviews",
]);

// Set form for fast `has()` checks (router uses this).
export const VALID_TYPES = new Set(ENTITY_DIRS);

// Priority order for resolving ambiguous wikilinks `[[slug]]` that match
// multiple entity types. Papers/concepts/topics rank highest because those
// are the most-referenced surfaces.
export const TYPE_PRECEDENCE = Object.freeze([
  "papers", "concepts", "topics", "methods", "people",
  "ideas", "experiments", "foundations", "manuscripts", "reviews",
]);

// Human-readable display labels for the topnav, breadcrumb, and cards.
export const ENTITY_LABEL = Object.freeze({
  papers: "Papers",
  concepts: "Concepts",
  topics: "Topics",
  people: "People",
  ideas: "Ideas",
  experiments: "Experiments",
  methods: "Methods",
  foundations: "Foundations",
  manuscripts: "Manuscripts",
  reviews: "Reviews",
});

// Edge-workflow color palette (used by Graph view to color edges by their
// semantic category). Self-contained; the corresponding workflow groups are
// declared per-edge in runtime/schema/edges.yaml::workflow. Fallback only —
// the live colors come from /api/graph payload.schema.edge_workflow_colors
// (sourced from config/visualize.json::edge_workflow_colors).
export const EDGE_WORKFLOW_COLORS = Object.freeze({
  ingest: "#5B8BD9",
  evidence: "#59C189",
  experiment: "#E6A23C",
  idea: "#F5A623",
  citation: "#7B8AB8",
  provenance: "#999999",
  frontmatter: "#B8B8C8",
});

// Fallback category-group mapping when the API payload's schema is missing.
// Authoritative copy lives in config/visualize.json::edge_category_groups.
// Frontmatter-projected edges use `fm_<kind>_<field>` so two entities with
// the same field name (concepts.key_papers vs topics.key_papers) don't
// collide.
export const EDGE_CATEGORY_GROUPS = Object.freeze({
  "Citations": ["cites"],
  "Paper relations": [
    "same_problem_as", "similar_method_to",
    "builds_on", "challenges",
  ],
  "Paper ↔ Concept": [
    "introduces_concept", "uses_concept",
    "extends_concept", "critiques_concept",
    "fm_concepts_key_papers", "fm_concepts_related_concepts",
    "fm_concepts_linked_ideas", "fm_concepts_parent_topics",
  ],
  "Paper ↔ Method": [
    "proposes_method", "applies_method", "extends_method",
  ],
  "Method genealogy": [
    "fm_methods_source_papers", "fm_methods_parent_methods",
    "fm_methods_child_methods", "fm_methods_realizes_concepts",
  ],
  "Foundation grounding": [
    "fm_concepts_grounded_in", "fm_methods_grounded_in",
    "contributes_to_foundation",
  ],
  "Topic membership": [
    "fm_topics_key_papers", "fm_topics_key_people",
    "fm_topics_key_foundations", "fm_topics_key_concepts",
    "fm_topics_key_methods", "fm_topics_related_topics",
    "fm_topics_parent_topics", "fm_topics_linked_ideas",
    "fm_papers_parent_topics", "fm_foundations_parent_topics",
    "fm_concepts_parent_topics", "fm_methods_parent_topics",
    "fm_people_parent_topics",
  ],
  "People contributions": [
    "fm_people_key_papers", "fm_people_contributed_methods",
    "fm_people_contributed_foundations",
  ],
  "Concept relations": [
    "shares_mechanism_with", "shares_assumption_with",
    "related_problem_formulation", "contrasts_with_concept",
  ],
  "Active research": [
    "fm_reviews_linked_manuscript",
  ],
  "Workflow (ideas / experiments)": [
    "fm_experiments_linked_idea", "fm_experiments_evaluates_methods",
    "fm_ideas_origin_gaps", "fm_ideas_linked_experiments",
    "supports", "contradicts", "tested_by",
    "invalidates", "addresses_gap",
    "derived_from", "inspired_by",
  ],
});

// Preset views: each maps to the categories to show. Buttons are additive —
// clicking one TOGGLES that category in the visible set.
export const EDGE_PRESETS = Object.freeze({
  "Citations":      ["Citations"],
  "Methods":        ["Method genealogy", "Paper ↔ Method", "Paper ↔ Concept"],
  "Ideas":          ["Workflow (ideas / experiments)"],
  "People":         ["Topic membership", "People contributions"],
  "Concepts":       ["Paper ↔ Concept", "Concept relations"],
  "Foundations":    ["Foundation grounding"],
  "Active":         ["Active research"],
  "All":            ["Citations", "Paper relations", "Paper ↔ Concept",
                     "Paper ↔ Method", "Method genealogy", "Foundation grounding",
                     "Topic membership", "People contributions", "Concept relations",
                     "Active research", "Workflow (ideas / experiments)"],
});

// Edge-type → workflow mapping. Mirrors runtime/schema/edges.yaml (each
// edge's `workflow` field) plus the synthetic "cites" type for citations.jsonl.
export const EDGE_TYPE_WORKFLOW = Object.freeze({
  // ingest workflow (paper-paper + paper-concept). Only 4 paper↔paper
  // semantic types are retained — removed: improves_on / compares_against /
  // surveys / complementary_to (see runtime/schema/edges.yaml).
  same_problem_as: "ingest",
  similar_method_to: "ingest",
  builds_on: "ingest",
  challenges: "ingest",
  introduces_concept: "ingest",
  uses_concept: "ingest",
  extends_concept: "ingest",
  critiques_concept: "ingest",
  proposes_method: "ingest",
  applies_method: "ingest",
  extends_method: "ingest",
  contributes_to_foundation: "ingest",
  shares_mechanism_with: "ingest",
  shares_assumption_with: "ingest",
  related_problem_formulation: "ingest",
  contrasts_with_concept: "ingest",
  cites: "citation",
  // evidence — supports/contradicts now travel between ideas, methods, and papers
  // (the legacy standalone claim entity was retired in the schema refactor).
  supports: "evidence",
  contradicts: "evidence",
  // experiment
  tested_by: "experiment",
  invalidates: "experiment",
  // idea / gap
  addresses_gap: "idea",
  inspired_by: "idea",
  // provenance
  derived_from: "provenance",
});

// Best-effort: any unknown edge type starting with `fm_` is a frontmatter
// projection. Frontends can call this instead of a direct map lookup.
export function workflowFor(edgeType) {
  if (EDGE_TYPE_WORKFLOW[edgeType]) return EDGE_TYPE_WORKFLOW[edgeType];
  if (typeof edgeType === "string" && edgeType.startsWith("fm_")) return "frontmatter";
  return "provenance";
}
