---
title: "Chirality-aware noise schedule for the AF3 diffusion module (eliminated)"
slug: "chirality-aware-af3-diffusion"
status: failed
origin: "ideate: gap 'Can the diffusion module's lack of equivariance be exploited (or replaced) to add cheap symmetry-aware prior, narrowing the chirality-violation gap?'"
origin_gaps: []
tags: [alphafold3, diffusion, chirality, equivariance, eliminated]
domain: "Computational Biology / ML for Science"
priority: 1
pilot_result: ""
failure_reason: "[filter] AF3 weights are restricted to a non-commercial license; fine-tuning the AF3 diffusion module is not feasible for an external research group. Replicating the diffusion-head architecture from scratch on Boltz-2 is a different (and much larger) project than the original idea framing."
linked_experiments: []
date_proposed: 2026-04-30
date_resolved: 2026-04-30
# bio-C3 (pilot merged 2026-05-12): the failure here is licensing/feasibility, not subspace
# saturation — AF3 weights are non-commercial. The block applies wherever AF3 fine-tuning is
# the proposed approach, regardless of species / disease / data regime. Empty scope = universal
# block (any future idea proposing "fine-tune AF3 diffusion head" should match this entry).
# A Boltz-2-based replacement is a distinct project — that ideation should not match the
# failure_reason text directly; the matching is on AF3-specific approach, not on the broader
# chirality / diffusion / equivariance theme.
scope:
  species: []
  disease_area: []
  data_regime: ""
---

## Motivation

[[accurate-structure-prediction-biomolecular-interactions-alphafold]] reports occasional chirality and clash failures from its [[diffusion-based-structure-prediction]] head; the paper itself flags symmetry-aware noise as a possible fix. Replacing the isotropic noise schedule with a chirality-aware one would in principle preserve the cost advantages of [[diffusion-based-structure-prediction]] while narrowing the chirality-violation gap that motivates [[invariant-point-attention]] and other equivariant alternatives.

## Hypothesis

A chirality-penalizing noise schedule on AF3's diffusion module reduces the chirality violation rate without measurable accuracy regression on a chirality-pathological subset.

## Approach sketch

Replace AF3's isotropic diffusion noise with a chirality-aware schedule (penalize mirror flips on Cα frames). Fine-tune on a chirality-pathological subset. Compare violation rate against vanilla AF3.

## Expected outcome

Eliminated — see `failure_reason`.

## Risks

AF3 weights are non-commercial; the fine-tune step is gated. Re-implementing the diffusion head on Boltz-2 is a different project (a full diffusion-architecture replacement, not a noise-schedule tweak), and ports the question to a model that already has different chirality behavior.

## Pilot results

(none — eliminated at Phase-3 filter, before any experiment)

## Lessons learned

When a research idea depends on fine-tuning a closed-weights model, the idea is not actionable for an external group regardless of its scientific merit. Future ideate runs should auto-eliminate proposals that require fine-tuning AF3 or other restricted-license models.
