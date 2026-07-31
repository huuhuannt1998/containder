# CONTAINDER --- Experiment Pre-Registration (M5), v2 (IJCIP revision)

**Status:** Authored 2026-07-18. Supersedes v1. **There is no immutability evidence for this
document that predates 2026-07-30**; see "What this pre-registration does and does not prove"
below, which is the governing statement and overrides any stronger wording elsewhere.

**Pre-registration anchor (SHA-256 of `scenario_matrix.yaml`):**
`e95b174ca7ce43dab774afeef7c386d22e3900c68d9eedb8eefdcf6810e76262`

Recompute with `python3 experiments/validate_matrix.py`.

## What this pre-registration does and does not prove

Stated plainly, because the previous wording overclaimed.

**The version-control anchor postdates the pilot results.** The repository was placed under git
on **2026-07-30**. The initial commit capturing this document and `scenario_matrix.yaml` in the
state hashed above is `b65cd3b1cd2a993092ef7616f8e8bdf03c0398e8`, dated **2026-07-30 06:03:31
-0400**. Every pilot result reported in the manuscript's evaluation section was produced *before*
that commit (the result files carry modification times from 2026-07-18 to 2026-07-30). The
document header claims an authoring date of 2026-07-18, but **no artifact in this repository
independently corroborates that date.**

**Therefore:** the SHA-256 above is a *content* hash, not a *timestamp*. It was computed by the
same party who could have edited the file, so it establishes only that the matrix has not changed
since the hash was recorded --- it cannot establish *when* the matrix was fixed relative to seeing
outcomes. Any claim that the design "cannot be adjusted after seeing outcomes without leaving a
visible trace" is **false as applied to the pilot results** and must not appear in the manuscript.

**What would fix this,** and what the manuscript stages as a blocking pre-submission action: a
deposit of this document on OSF or Zenodo, whose independently issued timestamp and DOI convert
the claim into a verifiable one. That deposit is a PI action and **has not been made.** Once it
is, the DOI supersedes this section, and the guarantee applies from the deposit date forward ---
that is, to the confirmatory sweep, and *not* retroactively to the pilots.

**Consequently the pilot results in the manuscript are reported as exploratory, not
confirmatory,** and the manuscript says so.

## Why this exists

Writing the scenario matrix after seeing results is the most common way this genre of paper
loses credibility. This matrix is hashed and fixed for the **confirmatory** sweep, which has not
yet run. It was **not** fixed before the pilot runs, whose results the manuscript therefore
labels exploratory. Post-hoc scenarios go in a separate file and are labeled post-hoc in the
paper.

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
until this sweep runs. An earlier version of this document stated that the manuscript "reports
no numbers before then". That is not what the manuscript does: it reports pilot measurements in
its evaluation section, clearly labelled as exploratory pilot results and excluded from the
confirmatory tests. This document is corrected here to match the manuscript rather than to
contradict it.
