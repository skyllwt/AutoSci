# Query Pack (general)

_Auto-generated compressed context. Do not edit._

## Open Gaps
_Auto-generated open questions. Do not edit._
- [paper/accurate-structure-prediction-biomolecular-interactions-alphafold] Can a generative structure predictor be coupled to an MSA-resampling or ensemble-sampling scheme to recover dynamical / multi-state behaviour rather than collapsing to a single PDB-like snapshot?
- [paper/accurate-structure-prediction-biomolecular-interactions-alphafold] How much of AF3's lift over specialised docking tools comes from joint training versus the diffusion formulation versus dataset scale? Ablations isolating each are not reported.
- [paper/accurate-structure-prediction-biomolecular-interactions-alphafold] What is the smallest training set (or which data slices) sufficient to match AF3 quality on a given complex class — i.e. how data-efficient is the unified framework relative to specialised predictors per class?
- [paper/accurate-structure-prediction-biomolecular-interactions-alphafold] Can the diffusion module's lack of equivariance be exploited (or replaced) to add cheap symmetry-aware prior, narrowing the chirality-violation gap?
- [paper/accurate-structure-prediction-biomolecular-interactions-alphafold] Does the same recipe transfer to membrane proteins, glycan-only structures, RNA-RNA tertiary contacts, or ribozyme catalysis intermediates that are under-represented in the PDB?
- [paper/alphafold-protein-structure-database-2024-providing] How should isoform-level structural coverage be represented and indexed? UniProt isoforms are curren
## Failed Ideas (avoid repeating)
- Chirality-aware noise schedule for the AF3 diffusion module (eliminated) — [filter] AF3 weights are restricted to a non-commercial license; fine-tuning the AF3 diffusion module is not feasible for an external research group. Replicating the diffusion-head architecture from scratch on Boltz-2 is a different (and much larger) project than the original idea framing.
- AlphaFold-derived PTM-site disorder predictor (eliminated) — [filter] saturated by SAPP (2025), PhosAF (2024), GraphPhos (2025), AstraPTM2 (2025), DeepPCT (2024), MTPrompt-PTM (2025) — 'AlphaFold structural features as input to PTM site predictor' is a published axis with at least five 2024-2025 entries. Adding pLDDT/IDR conditioning is incremental and unlikely to outperform any of these.
## Papers (11 total)
- [5] Accurate structure prediction of biomolecular interactions with AlphaFold 3
- [5] Highly accurate protein structure prediction with AlphaFold
- [4] AlphaFold Protein Structure Database in 2024: providing structure coverage for over 214 million protein sequences
- [4] Geometric deep learning on molecular representations
- [5] Towards a proteome-scale map of the human protein-protein interaction network
- [4] Towards a structurally resolved human protein interaction network
- [3] Drug design targeting active posttranslational modification protein isoforms
- [3] An integrated bioinformatics platform for investigating the human E3 ubiquitin ligase-substrate interaction network
- [4] Ubiquitin ligases in oncogenic transformation and cancer therapy
- [3] MusiteDeep: a deep-learning based webserver for protein post-translational modification site prediction and visualization
- [2] From Data to Cure: A Comprehensive Exploration of Multi-omics Data Analysis for Targeted Therapies
## Recent Relationships (84 total)
  experiments/calibrated-deltapternary-phospho-protac-ranking --tested_by--> ideas/ptm-protein-isoforms-enable-selective-drug
  experiments/ablation-uncalibrated-vs-calibrated-deltapternary --tested_by--> ideas/noise-floor-calibrated-deltapternary-improves-ranking
  experiments/ablation-boltz2-ptm-vs-md-relaxed-route --tested_by--> ideas/md-relaxed-phospho-route-comparable-to-native-ptm-tokens
  experiments/ablation-deepternary-vs-protac-stan-scorer --tested_by--> ideas/ptm-protein-isoforms-enable-selective-drug
  experiments/robustness-cross-ptm-type-ubiq-methyl --tested_by--> ideas/ptm-protein-isoforms-enable-selective-drug
  experiments/robustness-mutant-isoform-track-y220c-r175h --tested_by--> ideas/ptm-protein-isoforms-enable-selective-drug
  experiments/deepternary-baseline-ternarydb-crbn-vhl-reproduction --tested_by--> ideas/ptm-protein-isoforms-enable-selective-drug
  experiments/calibrated-deltapternary-phospho-protac-ranking --tested_by--> ideas/ptm-protein-isoforms-enable-se
