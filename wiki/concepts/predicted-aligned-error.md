---
title: "Predicted Aligned Error (PAE)"
aliases: ["PAE", "Predicted Aligned Error"]
tags: [structural-biology, protein-structure-prediction, confidence-metrics, alphafold]
maturity: stable
key_papers: [alphafold-protein-structure-database-2024-providing]
first_introduced: "2021"
date_updated: 2026-04-30
related_concepts: []
---

## Definition

Predicted Aligned Error (PAE) is the AlphaFold confidence metric for the *relative* spatial position of two residues. For each pair of residues `(i, j)` in a predicted structure, PAE(i, j) is the model's expected error in Å for the position of residue `i` when the prediction is superposed on the true structure using residue `j` as the alignment frame. PAE is the per-domain / inter-domain confidence companion to the per-residue pLDDT score.

## Intuition

pLDDT tells you "how good is this single residue's local geometry"; PAE tells you "if I trust this residue's frame, how far off is that other residue?". Low PAE between two residues means their relative positioning is confident — i.e. they probably belong to the same rigid unit. High PAE between two regions with internally-low PAE means each region is a confident sub-domain but their *relative* orientation is uncertain — a textbook signature of a multi-domain protein with flexible inter-domain geometry.

## Formal notation

PAE(i, j) ≥ 0 is reported in Å. For a structure of length `L`, the full PAE is an `L × L` matrix. AlphaFold DB serves PAE as JSON; since 2022 the schema is:

```
{
  "predicted_aligned_error": <L-by-L 2D array of Å values>,
  "max_predicted_aligned_error": <upper-bound scalar>
}
```

(Pre-2022 the schema had a 1D `distances` field; the new compact form replaces it.)

## Variants

- **Per-pair PAE matrix** (full, L×L) — used for fine-grained domain reasoning.
- **Aggregate PAE statistics** (e.g. mean inter-domain PAE) — used as a global complex-quality signal in AlphaFold-Multimer downstream pipelines.

## Comparison

- **vs pLDDT**: pLDDT is per-residue local accuracy (lDDT-Cα target); PAE is pairwise relative-position accuracy. They are complementary and both released together.
- **vs lDDT**: lDDT is the experimental superposition-free comparison metric (Mariani et al. 2013); pLDDT predicts lDDT, PAE predicts pairwise alignment error. Different mathematical objects.

## When to use

- Inspecting whether two domains in a multi-domain prediction share a confident relative orientation (low off-diagonal PAE = yes).
- Scoring AlphaFold-Multimer / multi-chain predictions: low inter-chain PAE blocks indicate a confident interface.
- Filtering predictions for downstream analyses that depend on quaternary-structure confidence.

## Known limitations

- PAE is a *predicted* error metric — it can itself be miscalibrated, especially for sequences far from training distribution.
- Visualizing the L×L matrix scales poorly for very long sequences / large complexes.
- High inter-domain PAE is sometimes a true negative (the model genuinely doesn't know the relative orientation) and sometimes a false negative (training-data sparsity); the distinction is hard to make automatically.
- The non-consecutive-region highlighting limitation in pre-2024 PAE viewers was a UX bottleneck for inspecting multi-domain proteins; AFDB 2024 addressed it.

## Open problems

- Calibration of PAE on out-of-distribution sequences (de-novo designs, intrinsically disordered regions, viral proteins).
- Better aggregate PAE summaries that work across very different complex sizes.
- Joint use of PAE + pLDDT for principled confidence-weighted downstream inference.

## Key papers

- [[alphafold-protein-structure-database-2024-providing]] — operationalizes PAE as the standard inter-domain confidence metric in AFDB and improves the interactive PAE viewer (non-consecutive region highlighting + Mol* coupling).

## My understanding

PAE is the metric that turned AlphaFold predictions from "single-domain useful" into "multi-domain useful". Most of the practical engineering around AlphaFold-Multimer scoring, structurally-resolved PPI networks, and AFDB-cluster reasoning ultimately leans on PAE block structure. For [[medpredict]], any PPI-prediction pipeline that consumes AlphaFold complex predictions has to define a PAE-based interface-confidence score.
