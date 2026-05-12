# Runtime Page Templates

> On-demand reference for full wiki page templates only. See `docs/runtime-support-files.en.md` for graph-derived files plus `index.md` and `log.md`.

<!-- bio-A1 (pilot merged 2026-05-11): page count grows from 9 to 10 — datasets/ is now a first-class entity. -->
## 10 Page Types

### papers/{slug}.md

```yaml
---
title: ""
slug: ""
arxiv: ""
# bio-A3 (minimal pilot merged 2026-05-11): bio-native identifiers, all optional.
# Bio papers often have DOI/PMID but no arXiv ID. The full A3 plan adds biorxiv, pdb_ids,
# uniprot_ids, nct_ids, gene_symbols, species — those are deferred until /ingest (C1) bio NER
# pre-pass can populate them at scale.
doi: ""                  # bio-A3: primary bio identifier
pmid: ""                 # bio-A3: PubMed ID
venue: ""
year:
tags: []
importance: 3           # 1-5
date_added: YYYY-MM-DD
source_type: tex         # tex | pdf
s2_id: ""
keywords: []
domain: ""               # NLP / CV / ML Systems / Robotics
code_url: ""
cited_by: []
---
```

Body sections: `## Problem` / `## Key idea` / `## Method` / `## Results` / `## Limitations` / `## Open questions` / `## My take` / `## Related`

### concepts/{concept-name}.md

```yaml
---
title: ""
aliases: []
tags: []
maturity: active         # stable | active | emerging | deprecated
key_papers: []
first_introduced: ""
date_updated: YYYY-MM-DD
related_concepts: []
# bio-A2 (light pilot merged 2026-05-11): optional protein-anchor fields. Populate ONLY when
# the concept IS a specific gene product (p53, CRBN, VHL, MDM2, …). Leave empty for process
# concepts (ubiquitylation), method concepts (alphafold-db), or class concepts
# (ubiquitin-ligase-e3). When ≥50 protein concepts accumulate, promote to a separate
# `proteins/` entity type (A2 heavy option, still drafted).
gene_symbol: ""          # bio-A2: HGNC symbol, e.g. "TP53"
uniprot_id: ""           # bio-A2: e.g. "P04637"
pdb_ids: []              # bio-A2: representative structures
species: []              # bio-A2: e.g. ["human"]
---
```

Body sections: `## Definition` / `## Intuition` / `## Formal notation` / `## Variants` / `## Comparison` / `## When to use` / `## Known limitations` / `## Open problems` / `## Key papers` / `## My understanding`

### topics/{topic-name}.md

```yaml
---
title: ""
tags: []
my_involvement: none     # none | reading | side-project | main-focus
sota_updated: YYYY-MM-DD
key_venues: []
related_topics: []
key_people: []
---
```

Body sections: `## Overview` / `## Timeline` / `## Seminal works` / `## SOTA tracker` / `## Open problems` / `## My position` / `## Research gaps` / `## Key people`

### people/{firstname-lastname}.md

```yaml
---
name: ""
affiliation: ""
tags: []
homepage: ""
scholar: ""
date_updated: YYYY-MM-DD
---
```

Body sections: `## Research areas` / `## Key papers` / `## Recent work` / `## Collaborators` / `## My notes`

### Summary/{area-name}.md

```yaml
---
title: ""
scope: ""
key_topics: []
paper_count:
date_updated: YYYY-MM-DD
---
```

Body sections: `## Overview` / `## Core areas` / `## Evolution` / `## Current frontiers` / `## Key references` / `## Related`

### foundations/{slug}.md

```yaml
---
title: ""
slug: ""
domain: ""
status: mainstream       # mainstream | historical
aliases: []
first_introduced: ""
date_updated: YYYY-MM-DD
source_url: ""
---
```

Body sections: `## Definition` / `## Intuition` / `## Formal notation` / `## Key variants` / `## Known limitations` / `## Open problems` / `## Relevance to active research`

Foundations have **no outward link fields**. Other pages may link to a foundation; foundations write no reverse link.

### ideas/{idea-slug}.md

```yaml
---
title: ""
slug: ""
status: proposed          # proposed | in_progress | tested | validated | failed
origin: ""
origin_gaps: []
tags: []
domain: ""
priority: 3               # 1-5
pilot_result: ""
failure_reason: ""
linked_experiments: []
date_proposed: YYYY-MM-DD
date_resolved: ""
# bio-A7 (pilot merged 2026-05-11): optional GRADE-style overall evidence grade for the idea.
# Coarser than per-edge grading (deferred). Useful for /novelty weighting and /paper-draft
# confidence framing. Omit when no evidence is yet available.
grade: ""                 # very-low | low | moderate | high (optional)
# bio-C3 (pilot merged 2026-05-12): optional scope object. Empty/absent scope means
# "universal" — for failed ideas, this is a universal banlist block (any candidate idea
# overlaps). For proposed/in_progress ideas, empty scope means the idea is not scoped to a
# specific bio subspace. Populate explicitly on failed ideas so future /ideate runs can
# distinguish "saturated subspace" from "blanket ban".
scope:
  species: []              # ["human"] | ["mouse", "human"] | ["plant"] | … (empty = universal)
  disease_area: []         # ["cancer"] | ["neurodegenerative"] | … (empty = disease-agnostic)
  data_regime: ""          # high_data | low_data | mixed (empty = data-regime-agnostic)
---
```

Body sections: `## Motivation` / `## Hypothesis` / `## Approach sketch` / `## Expected outcome` / `## Risks` / `## Pilot results` / `## Lessons learned`

### experiments/{experiment-slug}.md

```yaml
---
title: ""
slug: ""
status: planned           # planned | running | completed | abandoned
target_claim: ""
hypothesis: ""
tags: []
domain: ""
setup:
  model: ""
  dataset: ""
  hardware: ""
  framework: ""
  # bio-A5 full (pilot merged 2026-05-12): optional bio-shaped setup fields. Leave empty
  # for pure-ML designs — they remain valid. in_silico_or_wet drives /exp-design wet-lab
  # detection and /exp-run directory layout. force_field / solvent_model / simulation_length
  # are MD-specific. species / cell_line / assay_type cover wet-lab + cross-context.
  # weight_version captures multi-version ML models. random_seed_protocol records the
  # actual replication strategy (multi-seed alone often isn't enough for small bio n).
  in_silico_or_wet: ""         # in_silico | wet_lab | mixed
  species: []                  # ["human"] | ["mouse", "human"] | …
  cell_line: ""                # prefer Cellosaurus ID (e.g. CVCL_0023 for HEK293T)
  assay_type: ""               # MD | docking | scoring | Y2H | AP-MS | cryo-EM | NMR | binding_assay | …
  force_field: ""              # MD only (e.g. "AMBER ff14SB + phosaa14SB")
  solvent_model: ""            # MD only (explicit | implicit | vacuum)
  simulation_length: ""        # MD only (e.g. "50 ns")
  weight_version: ""           # multi-version ML models (e.g. "Boltz-2 Jan 2026 weights")
  random_seed_protocol: ""     # ranking-shuffle | bootstrap | stratified-k-fold | LOO-CV
metrics: []
baseline: ""
outcome: ""               # succeeded | failed | inconclusive
key_result: ""
linked_idea: ""
date_planned: YYYY-MM-DD
date_completed: ""
run_log: ""
started: ""
estimated_hours: 0           # bio-A6: legacy single-number budget — kept for backward compatibility
# bio-A6 (pilot merged 2026-05-11): structured cost block. All sub-fields optional and additive.
# Populate this on any new experiment that has a non-trivial mix of GPU / MD / wet-lab / FTE
# / dataset-access costs — single-number estimated_hours collapses too many constraints.
estimated_cost:
  gpu_hours: 0
  cpu_hours: 0
  md_wallclock_hours: 0
  wet_lab_usd: 0
  fte_weeks: 0
  dataset_access_lead_time_days: 0
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---
```

Body sections: `## Objective` / `## Setup` / `## Procedure` / `## Results` / `## Analysis` / `## Claim updates` / `## Follow-up`

### claims/{claim-slug}.md

```yaml
---
title: ""
slug: ""
status: proposed          # proposed | weakly_supported | supported | challenged | deprecated
confidence: 0.5           # 0.0-1.0
tags: []
domain: ""
source_papers: []
evidence:
  - source: ""
    type: supports        # supports | contradicts | tested_by | invalidates
    strength: moderate    # weak | moderate | strong
    detail: ""
conditions: ""
date_proposed: YYYY-MM-DD
date_updated: YYYY-MM-DD
---
```

Body sections: `## Statement` / `## Evidence summary` / `## Conditions and scope` / `## Counter-evidence` / `## Linked ideas` / `## Open questions`

<!-- bio-A1 (pilot merged 2026-05-11): datasets/ is the 10th first-class entity. Anchors
     reusable dataset references (TernaryDB, PROTAC-DB, AlphaFold-DB, dbPTM, PhosphoSitePlus,
     UniProt, PDB, …) so that experiments[*].setup.dataset and papers/* mentions can wikilink
     to a canonical page with version history and access tier. -->
### datasets/{slug}.md

```yaml
---
title: ""
slug: ""
aliases: []
tags: []
maturity: stable             # stable | active | emerging | deprecated
access: public               # public | registration | restricted | wet-lab-derived
# `versions` is a list of release records; downstream skills compare against
# `experiments[*].reproducibility.dataset_versions[*].version` to flag drift.
versions: []                 # list of {version, released, url, n_entries, notes}
canonical_url: ""
license: ""
key_papers: []               # backlink — populated by papers/ that cite the dataset
key_concepts: []
date_updated: YYYY-MM-DD
---
```

Body sections: `## Overview` / `## Versions` / `## Access and licensing` / `## Schema and entries` / `## Known caveats` / `## Used by experiments` / `## Key papers`
