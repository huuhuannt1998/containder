# CONTAINDER --- Experiment Pre-Registration (M5), v2 (IJCIP revision)

**Status:** FROZEN 2026-07-18, before any production sweep. Supersedes v1.
**Pre-registration anchor (SHA-256 of `scenario_matrix.yaml`):**
`e95b174ca7ce43dab774afeef7c386d22e3900c68d9eedb8eefdcf6810e76262`

Recompute with `python3 experiments/validate_matrix.py`. A private content hash proves
immutability only if paired with an independently verifiable timestamp, so this record is also
to be **deposited on a trusted timestamped repository (OSF or Zenodo)** before the sweep; the
git commit hash of this file is recorded alongside once under version control.

## Why this exists

Writing the scenario matrix after seeing results is the most common way this genre of paper
loses credibility. The matrix is frozen and hashed before the first run. Post-hoc scenarios go
in a separate file and are labeled post-hoc in the paper.

## Primary hypothesis

**H1 (compositional harm):** credential lifetime and authorization scope have a **non-additive
interaction** on the primary physical metric, voltage-violation area (fully crossed, 6 TTL x 4
scope = 24 cells). Secondaries H2--H8 cover capacity-time exposure, the B5-vs-{B3,B4} ablation,
post-expiry residual authority, locus dominance, safe-mode availability, fresh-key containment,
and renewal-latency safety margin. **Gate Three:** H2 and H3 must hold on at least one public
feeder, else raise a checkpoint and reframe.

## Baselines and mechanism ablations

B1 legacy-identity-as-authority, B2 legacy+narrow-ACL, B3 ephemeral-only, B4 attestation-only,
B5 full CONTAINDER, B6 safe-mode. Each baseline carries explicit **fresh-key / session-
enforcement / command-cleanup** columns, because the revision's central point is that short TTL
alone does not contain a copied key, an active session, or a persistent command. Mechanism
ablations A1--A8 remove one link of the containment chain each (fresh key, session termination,
command cancellation, scope narrowing, replay resistance, hardware key storage, fail-open,
fail-closed) to attribute the measured reduction.

## Statistics (frozen)

Experimental unit is the **complete paired scenario run**, not the per-timestep sample. Primary
model is mixed-effects: `log(1+VVA) ~ log(TTL) + Scope + log(TTL):Scope + (1|day) + (1|seed)`,
with robust / aligned-rank-transform / permutation fallbacks. Binary outcomes (protection trip)
use mixed-effects logistic regression; violating-node counts use a negative-binomial mixed model;
recovery time uses survival analysis. Effect sizes: median paired difference, ratio of geometric
means, paired rank-biserial, odds ratio, each with bootstrap CIs. Holm correction **within**
families (policy, attack-family, locus, availability); the primary interaction is not corrected
together with exploratory analyses.

## Power and seeds

Run a 5-seed-per-core-cell pilot, estimate between-seed and between-day variance, choose a
smallest meaningful effect for VVA, run simulation-based power analysis, then set the production
seed count (min 20, target 40) and record the rule before viewing final comparisons. The 40-seed
figure is provisional until the power analysis justifies it.

## Attacker models and missing runs

Every attack is run under an **oracle worst-case** attacker and an **operationally realistic**
attacker (telemetry-limited heuristic), so no result is only an omniscient upper bound. Solver
nonconvergence handling, a retry cap of 2, treating failure as an outcome, and never dropping
severe runs are all preregistered.

## Physical campaign scale

Policy comparison 3,840 + TTL-by-scope 3,200 + locus 1,280 + attestation/renewal 1,920 ~= 10,240
feeder runs before sensitivity and cross-solver subsets, on IEEE 8500 (primary) and PNNL 9500
(validation), OpenDSS with GridLAB-D cross-check over HELICS.

## Execution status

This document and the frozen matrix are the pre-registration deliverable. The production sweep
(the ~10,240 feeder runs, the credential-service functional and containment campaigns, the
microbenchmarks, availability, and scalability) requires the M3 attested-credential service on
real IEEE 2030.5 traffic and the M4 co-simulation, which need a testbed not present in the
authoring session. No sweep results exist yet; the manuscript marks all results sections pending
until this sweep runs, and reports no numbers before then.
