# Tables and figures plan (IJCIP revision §22-§23)

Each required table/figure, its RQ, data source, and status. "in draft" = present in the compiled
manuscript now; "pending sweep" = needs the M3-M5 testbed run (not fabricated).

## Tables
| # | Content | RQ | Source | Status |
|---|---------|----|--------|--------|
| 1 | Standards claims (clause-level) | premise | IEEE 2030.5-2023 (paywalled) | in draft (skeleton; clause rows pending) |
| 2 | Threat model (asset/compromise/gain/exclusion/goal) | premise | sec 02 | in draft (prose; tabularize optional) |
| 3 | Four impact dimensions (type/unit/computation) | RQ1 | sec 03 | **in draft** |
| 4 | Baselines (mechanism columns) | all | scenario_matrix v2 | **in draft** |
| 5 | Experimental factors/levels | all | scenario_matrix v2 | in draft (in yaml; tabularize) |
| 6 | Prototype overhead (latency/CPU/mem/throughput) | RQ5 | Campaign 3 | pending sweep |
| 7 | Containment (block/terminate/effect/exposure) | RQ2 | Campaign 2 | pending sweep |
| 8 | Cyber blast radius (reach/flex/persistence/exposure) | RQ1 | Campaign 4 (pkimodel) | partial: engine ready, matrix pending |
| 9 | Physical results (VVA/deviation/trips/curtailment/recovery) | RQ3 | Campaign 5 | pending sweep |
| 10 | Availability (success/degraded/risk/recovery) | RQ4 | Campaign 6 | pending sweep |
| 11 | Cross-solver agreement (OpenDSS vs GridLAB-D) | RQ3 | Campaign 5 | pending sweep |
| 12 | Interoperability / migration | RQ6 | Campaign 0 | pending sweep |
| -- | Related-work positioning | -- | sec 09 | **in draft** |

## Figures
| # | Content | RQ | Status |
|---|---------|----|--------|
| 1 | Baseline vs CONTAINDER trust architecture | design | pending (draw) |
| 2 | Enrollment/renewal sequence diagram | design | pending (draw) |
| 3 | Fresh-key attestation binding | design | pending (draw) |
| 4 | Credential/session/command persistence timeline | RQ2 | pending (draw) |
| 5 | Four-dimensional impact model | RQ1 | pending (draw) |
| 6 | Testbed + HELICS federation | method | pending (draw) |
| 7 | TTL x scope interaction plot | RQ1/H1 | pending sweep |
| 8 | Capacity-time exposure by policy | RQ2 | pending sweep |
| 9 | Voltage-violation area by policy and attack | RQ3 | pending sweep |
| 10 | Feeder voltage heat map / time series | RQ3 | pending sweep |
| 11 | Renewal latency / service throughput | RQ5 | pending sweep |
| 12 | Availability-security tradeoff (deny vs safe mode) | RQ4 | pending sweep |
| 13 | Cross-solver agreement | RQ3 | pending sweep |
| 14 | Migration-tier compatibility | RQ6 | pending sweep |

Figures 1-6 are architecture/method diagrams that can be drawn now (no measured data); 7-14
depend on the sweep. Draw 1-6 with TikZ/matplotlib in `figures/` before submission.
