# Query Pack (general)

_Auto-generated compressed context. Do not edit._

## Claims (17 total)
- [weakly_supported] PTM protein isoforms enable selective drug design beyond wild-type targets (conf: 0.6)
- [supported] AlphaFold2 enables large-scale structural modeling of human PPI network (conf: 0.75)
- [weakly_supported] Diffusion-based atom-coordinate generation eliminates the need for equivariant frame-based structure modules (conf: 0.55)
- [supported] E3 ligase deregulation in cancer alters substrate stability and is therapeutically exploitable in a context-dependent manner (conf: 0.85)
- [supported] MSA depth bounds the achievable accuracy of MSA-conditioned protein structure predictors (conf: 0.85)
- [proposed] Noise-floor-calibrated ΔpTernary improves PTM-isoform degrader ranking precision over uncalibrated raw ΔpTernary (conf: 0.3)
- [weakly_supported] Deep-learning ensembles with sequence-only input outperform feature-engineered classical ML for PTM site prediction across most PTM types (conf: 0.6)
- [supported] Deep learning can predict protein structure at near-experimental atomic accuracy from sequence alone (conf: 0.92)
- [supported] Heterogeneous biological evidence integrated by naive Bayes predicts human E3-substrate interactions at proteome scale (conf: 0.75)
- [supported] Equivariant 3D neural networks reliably outperform 2D-graph baselines for quantum-chemistry targets but not consistently for drug-discovery property prediction (conf: 0.7)
- [supported] Geometric priors (equivariance / invariance) systematically improve neural-network modelling of molecular systems (conf: 0.75)
- [supported] Stringent high-throughput Y2H recovers many novel disease-associated human PPIs at low inspection bias (conf: 0.8)
- [proposed] MD-relaxed phospho-structure fallback yields ΔpTernary signal comparable to native CCD-PTM-token Boltz-2 prediction (conf: 0.3)
- [weakly_supported] Integrating multi-omics data with machine learning and network-pharmacology models enables identification of multi-target therapeutic strategies that single-omics analysis cannot re
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
- [5] Accurate structure prediction of biomolecular interactions with AlphaFold 3 (Computational Biology / ML for Science)
- [5] Highly accurate protein structure prediction with AlphaFold (Structural Biology / ML for Science)
- [4] AlphaFold Protein Structure Database in 2024: providing structure coverage for over 214 million protein sequences (Structural Bioinformatics)
- [4] Geometric deep learning on molecular representations (ML for Molecules)
- [5] Towards a proteome-scale map of the human protein-protein interaction network (Computational Biology)
- [4] Towards a structurally resolved human protein interaction network (Computational Biology)
- [3] Drug design targeting active posttranslational modification protein isoforms (Computational Drug Design / Chemical Biology)
- [3] An integrated bioinformatics platform for investigating the human E3 ubiquitin ligase-substrate interaction network (computational biology)
- [4] Ubiquitin ligases in oncogenic transformation and cancer therapy (Cancer biology / Molecular oncology)
- [2] From Data to Cure: A Comprehensive Exploration of Multi-omics Data Analysis for Targeted Therapies (Computational Biology)
- [3] MusiteDeep: a deep-learning based webserver for protein post-translational modification site prediction and visualization (Bioinformatics)
## Recent Relationships (65 total)
  papers/accurate-structure-prediction-biomolecular-interactions-alphafold --improves_on--> papers/highly-accurate-protein-structure-prediction-alphafold
  ideas/ptm-aware-degrader-target-nomination --addresses_gap--> claims/ptm-protein-isoforms-enable-selective-drug
  ideas/ptm-aware-degrader-target-nomination --addresses_gap--> claims/e3-ligase-deregulation-cancer-alters-substrate
  ideas/ptm-aware-degrader-target-nomination --inspired_by--> papers/drug-design-targeting-active-posttranslational-modification
  ideas/ptm-aware-degrader-target-nomination --inspired_by--> papers/integrated-bioinformatics-platform-investigating-human-e3
  ideas/ptm-aware-degrader-target-nomination --inspired_by--> papers/accurate-structure-prediction-biomolecular-interactions-alphafold
  ideas/ptm-conditioned-ensemble-prediction --addresses_gap--> claims/diffusion-based-generation-eliminates-need-equivariant
  ideas/ptm-conditioned-ensemble-prediction --addresses_gap--> claims/msa-depth-bounds-structure-p
