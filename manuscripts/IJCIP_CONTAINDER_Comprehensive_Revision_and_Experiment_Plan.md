# IJCIP Review and Revision Plan for CONTAINDER

**Manuscript reviewed:** `main(51).pdf`  
**Target journal:** *International Journal of Critical Infrastructure Protection (IJCIP)*  
**Current manuscript title:** *CONTAINDER: Bounding Credential-Compromise Impact in IEEE 2030.5 DER Systems*  
**Purpose:** Provide a complete, actionable review and revision plan for preparing the manuscript for IJCIP submission.

---

# 1. Executive Verdict

## 1.1 Overall assessment

This version is substantially stronger than the previous manuscript. It has progressed from a design proposal with a planned evaluation to a preliminary end-to-end systems paper that includes:

- a four-dimensional authorization-compromise impact model;
- a narrower and more defensible argument about the limitations of reachability-only measurement;
- fresh-key binding;
- credential, session, and command-effect persistence;
- a safe-mode authorization policy;
- a working X.509 and mutual-TLS credential service;
- preliminary IEEE 8500-node feeder results;
- attack-family and penetration sensitivity experiments;
- a preregistered plan for broader evaluation.

These changes directly address many of the original conceptual and experimental weaknesses.

However, the paper should not yet be submitted to IJCIP. The manuscript now has real publication potential, but several scientific inconsistencies, unfinished claims, and incomplete experiments remain. The central problem is no longer that the paper has no results. The current problem is that the evaluation largely demonstrates the benefit of authorization-scope narrowing, while the paper claims an integrated benefit from:

- attestation;
- ephemeral credentials;
- fresh-key rotation;
- session enforcement;
- command-effect cleanup;
- least-privilege authorization;
- feeder-level containment.

The paper needs one additional complete experimental and consistency pass before it will be a credible IJCIP submission.

## 1.2 Reviewer-style recommendation

**Current recommendation: Reject, with encouragement to resubmit after major experimental revision.**

This is a significantly stronger position than the previous version. The paper's topic, architecture, and preliminary evidence are promising. The remaining issues are fixable, but they are substantive enough that submitting now would expose the manuscript to straightforward reviewer objections.

## 1.3 Assessment summary

| Dimension | Assessment |
|---|---:|
| Fit to IJCIP | 9/10 |
| Importance of the problem | 8/10 |
| Novelty potential | 7/10 |
| Technical completeness | 6/10 |
| Experimental strength | 4/10 |
| Writing and organization | 7/10 |
| Submission readiness | 4/10 |

## 1.4 Central path to acceptance

The final paper must independently demonstrate three claims:

1. **Authorization-scope narrowing limits the instantaneous physical attack envelope.**
2. **Fresh attestation, fresh-key rotation, session enforcement, and command cleanup bound how long adversarial authority remains effective.**
3. **The combined reduction is measured directly in a time-series feeder simulation without imposing unacceptable availability costs.**

The current paper preliminarily demonstrates the first claim. The second and third claims are partially modeled or tested in isolation but are not yet integrated into a complete confirmatory evaluation.

---

# 2. Major Improvements in the Current Version

## 2.1 The theoretical claim is now narrower and more defensible

The revised manuscript explicitly avoids claiming that every graph-based security model is incapable of representing time or physical state. Instead, it argues that:

> Static, unweighted reachability is insufficient to compare DER credential-containment policies.

This is a strong improvement. It reduces the risk of a reviewer dismissing the work as a straw-man critique of attack graphs. The paper now treats the four dimensions as a measurement framework for cyber-physical authorization compromise rather than as a universal impossibility result.

The three propositions are also better structured:

- scope separation;
- temporal separation;
- physical-state separation.

Linking each proposition to a regression test in the analysis engine is a good design decision.

## 2.2 The impact model is substantially more rigorous

The revised model correctly recognizes that the four quantities do not have the same mathematical type. The paper now distinguishes:

- `BRreach`: cyber reach;
- `BRflex`: state-dependent commandable flexibility;
- `BRauth`: retained authority;
- `BRphys`: physical feeder consequence;
- `BRexp`: accumulated exposure.

Important improvements include:

- replacing nameplate capacity with state-dependent feasible command sets;
- separating credential persistence from session persistence and command-effect persistence;
- introducing capacity-time exposure;
- defining physical consequence over an attacker action trajectory;
- distinguishing a worst-case attacker from a telemetry-limited attacker;
- defining a voltage-violation objective.

These changes make the model much more credible for a cyber-physical infrastructure journal.

## 2.3 The containment architecture addresses real credential-lifecycle gaps

The containment chain is one of the strongest parts of the manuscript:

\[
\text{fresh attestation}
\rightarrow
\text{fresh bound key}
\rightarrow
\text{short scoped credential}
\rightarrow
\text{bounded session}
\rightarrow
\text{bounded command}
\rightarrow
\text{measured recovery}
\]

The fresh-key requirement is especially important. A healthy device may continue to pass attestation even when an attacker retains a copied operational key. Therefore, attestation alone is insufficient unless the newly issued credential is bound to a new, attested public key.

The manuscript also correctly recognizes that:

- certificate expiry does not automatically terminate an established TLS session;
- an already-issued DER command may remain active after the credential expires;
- session and command-effect persistence must be measured independently.

These are meaningful technical improvements.

## 2.4 The paper now includes preliminary end-to-end evidence

The manuscript reports:

- real X.509/ECDSA certificates;
- mutual TLS;
- replay rejection;
- fresh-key rotation;
- per-command expiration enforcement;
- workstation latency measurements;
- a public IEEE 8500-node feeder benchmark;
- multiple load states;
- multiple attack families;
- PV-penetration sensitivity;
- preliminary baseline comparisons.

This makes the manuscript much more credible than the prior version. The system is no longer purely architectural.

---

# 3. Critical Submission Blockers

## 3.1 The IEEE 2030.5 standards foundation is unfinished

Table I explicitly contains entries such as:

- “pending 2023 clause”;
- “confirm 2023”;
- “pending direct verification.”

These placeholders cannot remain in a submitted manuscript because the title, motivation, and threat model depend on these exact claims.

The manuscript must resolve whether each claim applies to:

- IEEE 2030.5-2018;
- IEEE 2030.5-2023;
- IEEE 2030.5-2023 with the 2024 corrigendum;
- a Common Smart Inverter Profile version;
- a deployment-specific profile;
- a common operational practice rather than the base standard itself.

### Required standards table

Replace the current verification-status table with a completed evidence table:

| Claim | Edition/profile | Exact clause | Normative wording | Interpretation used in paper |
|---|---|---:|---|---|
| Device certificate lifetime | Applicable version | Clause | SHALL/MAY/explanatory | Exact supported statement |
| CRL behavior | Applicable version | Clause | Exact text | Scope of prohibition |
| OCSP behavior | Applicable version | Clause | Exact text | Scope of prohibition |
| Local deny list | Applicable version | Clause | Exact text | Existing local containment |
| Re-enrollment/rekey | Applicable version | Clause | Exact text | What the standard already supports |
| LFDI/SFDI derivation | Applicable version | Clause | Exact text | Identity impact of rotation |
| FunctionSetAssignments | Applicable version | Clause | Exact text | Authorization semantics |
| Scheduled controls | Applicable version | Clause | Exact text | Post-credential persistence |

### Why this matters

The current abstract says that IEEE 2030.5:

> forbids online certificate revocation.

That statement may be correct in the intended profile or edition, but it must be supported precisely. If the claim is profile-specific, the title and abstract must say so.

### Required manuscript changes

- Remove all “pending” and “confirm” language.
- Name the exact standard/profile in the abstract.
- Explain what local deny-list or server-side authorization mechanisms already exist.
- Distinguish cryptographic revocation from local identity denial and re-enrollment.
- Verify whether operational certificate rotation changes LFDI/SFDI identity.
- Verify how scheduled DER controls behave after the issuing credential expires.

## 3.2 The manuscript still describes the main evaluation as future work

The paper repeatedly characterizes the current study as:

- preliminary;
- reduced scale;
- one feeder;
- one solver;
- workstation only;
- fixed attacker;
- incomplete full sweep.

The conclusion says that the full evaluation remains to be completed. Table IX also includes a footnote implying that prototype and feeder results will be reported after the sweep, even though Section IX already reports them.

This makes the paper read like an extended pilot rather than a finished journal article.

### Preferred solution

Complete the full production evaluation and integrate it into the paper.

### Minimum defensible solution

If time or computational resources prevent the originally planned large sweep, redefine the current paper as a complete bounded study and add the minimum missing evidence:

- a second public feeder;
- cross-solver validation;
- real failure injection;
- constrained or hardware-backed credential measurements;
- statistical confidence intervals;
- direct time-series credential-to-feeder experiments;
- interoperability evidence.

Then remove language promising a future, larger paper.

### Required wording change

Do not state:

> The full evaluation will be reported later.

Instead, the submitted paper should state:

> We evaluate the design under the following declared scope and limitations.

A journal article can be bounded. It should not present its core validation as unfinished.

---

# 4. Central Scientific Problem: Scope Narrowing Is Confounded with CONTAINDER

## 4.1 Current physical comparison

The primary physical comparison is approximately:

- B1: legacy credential with full authorization;
- B5: CONTAINDER with narrow authorization.

Under B1, the attacker has high-impact active and reactive controls. Under B5, those controls are largely removed. Therefore, the physical benefit is expected.

Table VII also shows that B2—legacy credentials with a narrow ACL—has approximately zero exposure, similar to B5.

This creates the most obvious reviewer objection:

> If narrow ACLs already remove the physical consequence, what additional benefit comes from attestation, ephemeral credentials, fresh keys, session enforcement, and command cleanup?

The answer should be temporal containment, but the current feeder evaluation does not measure that directly.

## 4.2 Required equal-scope comparisons

Run matched comparisons in which scope is held constant:

| Comparison | Scope condition | Mechanism isolated |
|---|---|---|
| B1 vs B3 | Same broad scope | Short credential lifetime |
| B2 vs B5 | Same narrow scope | Attestation, fresh keys, session/command containment |
| B3 vs B5 | Same short lifetime where possible | Scope and attestation |
| B4 vs B5 | Same attestation policy | Lifetime, fresh keys, session and command enforcement |
| B5 vs A2 | Identical except session enforcement | Session persistence |
| B5 vs A3 | Identical except command cleanup | Command-effect persistence |
| B5 vs A1 | Identical except fresh-key rotation | Copied-key containment |
| B5 vs A4 | Identical except scope narrowing | Physical attack envelope |

## 4.3 Avoid trivial read-only scopes

If B5's narrow scope effectively removes all attack-relevant write operations, then the physical result may be equivalent to changing the compromised credential into a read-only credential.

A more meaningful least-privilege design should preserve legitimate operational utility.

For each scope, report:

- legitimate functions retained;
- functions denied;
- legitimate dispatch success rate;
- malicious action set;
- active-power flexibility;
- reactive-power flexibility;
- physical impact;
- availability impact.

## 4.4 Recommended scope designs

### Scope S1 — Read-only

- telemetry access only;
- no control.

This is the strongest containment baseline but may be operationally unrealistic.

### Scope S2 — Bounded support control

Allow:

- bounded volt-var response;
- bounded curtailment;
- no arbitrary fixed real-power export;
- no unrestricted battery charge/discharge;
- no connect/disconnect.

### Scope S3 — Program-specific operational scope

Allow the controls needed for one DER program but not the complete DERControl surface.

This is the most valuable comparison because it shows whether CONTAINDER can preserve useful operations while reducing attack consequence.

---

# 5. Fundamental Metric Inconsistency

## 5.1 `BRexp` is defined one way and evaluated another way

The model defines:

\[
BR_{\mathrm{exp}}
=
\int BR_{\mathrm{flex}}(t)
\mathbf{1}[\text{adversarial authority is effective at }t]dt
\]

This is a capacity-time or flexibility-time quantity with units such as:

- kWh;
- kVArh;
- a declared active/reactive composite.

However, the evaluation computes:

\[
BR_{\mathrm{exp}} \approx \Delta J_V \times BR_{\mathrm{auth}}
\]

This is not capacity-time exposure. It is a physical-impact-times-duration quantity with different units.

The paper currently labels this quantity as capacity-time exposure, creating a mathematical and unit inconsistency.

## 5.2 Recommended correction: retain two separate metrics

### Cyber-physical authority exposure

Define:

\[
BR_{\mathrm{exp}}
=
\int_{t_0}^{t_{\mathrm{end}}}
BR_{\mathrm{flex}}(t)
I_{\mathrm{authority}}(t)\,dt
\]

Report:

- active-power exposure in kWh;
- reactive-power exposure in kVArh;
- a composite only if the weights are explicitly justified.

### Physical violation accumulation

Define a separate quantity:

\[
BR_{\mathrm{phys-time}}
=
\int_{t_0}^{t_{\mathrm{end}}}
J_V(t)\,dt
\]

or use the voltage-violation area itself as the primary integrated physical metric.

Do not call `J_V × duration` capacity-time exposure.

## 5.3 Best experimental approach

Do not multiply a static feeder result by a modeled credential duration.

Instead, run a true time-series experiment:

1. Start from a clean feeder state.
2. Authenticate the compromised credential.
3. Begin issuing malicious commands.
4. Allow commands while the credential/session remains valid.
5. Trigger:
   - expiration;
   - failed attestation;
   - scope narrowing;
   - session termination;
   - command cancellation.
6. Continue feeder simulation through recovery.
7. Integrate:
   - actual commandable flexibility over time;
   - actual accepted adversarial commands;
   - actual voltage violations;
   - actual recovery time.

This directly measures the lifetime-by-scope interaction and avoids combining one measured factor with one modeled factor.

---

# 6. Physical-Metric Problems

## 6.1 The declared primary endpoint differs from the reported endpoint

The formal model defines a two-sided voltage-violation area that includes:

- overvoltage;
- undervoltage.

The preliminary evaluation reports only attack-induced overvoltage because the feeder base case has native undervoltage.

That may be a reasonable secondary analysis, but it contradicts the declaration that the two-sided quantity is the primary endpoint.

### Required correction

Report both:

#### Primary system-level endpoint

\[
J_V^{two-sided}
\]

Total two-sided voltage-violation area.

#### Attack-specific endpoint

\[
\Delta J_V^{over}
=
J_{V,\mathrm{over}}^{attack}
-
J_{V,\mathrm{over}}^{clean}
\]

Attack-induced overvoltage relative to the paired clean baseline.

State whether the attack-specific endpoint was selected:

- before the pilot;
- after observing benchmark undervoltage;
- as an exploratory endpoint.

## 6.2 Investigate the feeder base case

Determine whether the native undervoltage is:

- an expected property of the reference feeder;
- caused by modifications;
- caused by DER placement;
- caused by solver settings;
- caused by a conversion issue.

Report:

- clean minimum voltage;
- number of undervoltage nodes;
- voltage profile before attack;
- any regulator/control changes.

## 6.3 A violation area cannot be negative

Table VIII reports a B5 value of `-0.01`.

A raw violation area cannot be negative. A negative number is only meaningful if it represents a difference relative to a baseline.

Rename the quantity:

\[
\Delta J_V
=
J_V^{attack}
-
J_V^{clean}
\]

Then report raw and differential values:

| Policy | Clean violation area | Attack violation area | Difference |
|---|---:|---:|---:|

## 6.4 The reported feeder outcome is not the formal worst-case `BRphys`

The model defines:

\[
BR_{\mathrm{phys}}
=
\max_{a_{0:H}\in\mathcal{A}} J(F,u,a)
\]

The preliminary evaluation uses a fixed attacker and explicitly says that it is not optimized for each state.

Therefore, the reported result is not the formal maximum. It is a feasible observed attack consequence.

### Options

- Implement the optimizer; or
- define `BRphys_observed` and `BRphys_worst` separately.

## 6.5 Proposition 3 needs a physically validated counterexample

Replace the questionable curtailment/reverse-power example with a validated case such as:

- battery discharge under low-load versus high-load conditions;
- fixed active-power export under different load states;
- reactive injection under different baseline voltages;
- volt-var distortion under different regulator states;
- battery charge/discharge with different state of charge and feeder direction.

The counterexample should be reproducible and released.

---

# 7. Credential and Attestation Evaluation Issues

## 7.1 “Attested issuance costs 0.2 ms” is too broad

Decompose the result into:

- operational key generation;
- evidence generation;
- evidence signing;
- token serialization;
- transport;
- token verification;
- endorsement/reference-value lookup;
- policy evaluation;
- certificate request creation;
- certificate signing;
- certificate installation;
- database/logging;
- network round trip.

If there is no TPM, TEE, or secure element in the measured path, do not call the result hardware-backed.

Use wording such as:

> In the software-based workstation prototype, local issuance processing has a median latency of 0.2 ms, excluding hardware-attestation and network costs.

## 7.2 Throughput is projected rather than measured

The 4,900 issuances/s and 100,000-device result should be treated as projections unless measured under concurrency.

Required load testing:

- multiple request rates;
- multiple client concurrency levels;
- queueing;
- verifier and issuer contention;
- storage/logging overhead;
- renewal bursts.

Report median, p95, p99, CPU, memory, error rate, queue length, and saturation.

## 7.3 The ten invariants should be tabulated

Use a table:

| ID | Security invariant | Test procedure | Expected result | Observed result |
|---|---|---|---|---|
| I1 | Bootstrap identity cannot authorize DER control | Attempt direct control | Rejected | Pass/fail |
| I2 | Fresh attestation is required | Reuse stale evidence | Rejected | Pass/fail |
| I3 | Credential binds fresh public key | Substitute key | Rejected | Pass/fail |
| I4 | Replay is rejected | Replay nonce/token | Rejected | Pass/fail |
| I5 | Expired credential cannot issue command | Submit after expiry | Rejected | Pass/fail |
| I6 | Scope is enforced per command | Invoke out-of-scope operation | Rejected | Pass/fail |
| I7 | Bad measurement receives degraded/denied scope | Tamper measurement | Narrow/deny | Pass/fail |
| I8 | Prior epoch cannot self-renew | Renew using old cert only | Rejected | Pass/fail |
| I9 | Copied prior key fails after rotation | Use old key | Rejected | Pass/fail |
| I10 | Active command/session is bounded | Maintain past expiry | Stopped | Pass/fail |

## 7.4 Expiration timing needs clearer reporting

Report:

- command attempt frequency;
- credential expiration time;
- last accepted attempt time;
- first rejected attempt time;
- maximum post-expiry acceptance;
- number of trials;
- confidence interval.

Recommended wording:

> Across \(N\) trials at a 2 Hz command rate, no post-expiry command was accepted. The first post-expiry attempt was rejected within 0–0.5 seconds, determined by the command interval.

---

# 8. Availability Evaluation Issues

## 8.1 Outage behavior is modeled, not experimentally measured

Before submission, perform fault injection for:

- verifier outage;
- issuer outage;
- network partition;
- packet loss;
- latency;
- clock skew;
- false rejection;
- renewal storm;
- database failure;
- partial recovery.

Metrics:

- legitimate command success;
- safe-mode duration;
- expired credential count;
- renewal failures;
- p99 latency;
- recovery time;
- physical impact caused by defensive denial;
- fail-open authority duration.

---

# 9. Preregistration Chronology Must Be Clarified

Use a credible chronology:

1. preliminary pilot experiments;
2. design refinement;
3. production preregistration;
4. pilot data excluded from confirmatory testing;
5. production execution.

Recommended wording:

> The preliminary experiments served as pilot studies. After the pilot, we froze and deposited the confirmatory scenario matrix and statistical plan. Pilot observations are not included in confirmatory tests.

---

# 10. Internal Contradictions

## 10.1 Backward compatibility is overclaimed

Replace “backward compatible” with:

> designed for incremental deployment through native and gateway-proxy tiers.

Only restore the stronger claim after interoperability tests.

## 10.2 B6 is missing from the main results

Add B6 or change the claim that all six baselines are shown.

## 10.3 Implementation-status statements conflict

Add a status table distinguishing:

- implemented and measured;
- implemented but not fully measured;
- planned;
- not implemented.

## 10.4 Table IX contradicts the evaluation section

Revise the footnote to acknowledge that preliminary prototype and IEEE 8500-node results are already reported.

---

# 11. Related Work Is Still a Submission Blocker

Remove all placeholders such as:

- `[cite pending validation, REFS TODO]`;
- `[cite pending]`.

Expand related work across:

- IEEE 2030.5 and CSIP security;
- DER and smart-inverter attacks;
- distribution-grid cyber-physical impact;
- PKI lifecycle and short-lived credentials;
- device identity and hardware-bound keys;
- remote attestation;
- temporal and cyber-physical attack graphs;
- co-simulation;
- DER authorization.

Aim for roughly 30–50 relevant references and compare named works rather than broad categories.

---

# 12. Figure and Table Problems

## 12.1 Figure 1

Retain the containment-chain diagram. Distinguish:

- architectural mechanisms;
- implemented components;
- evaluated components;
- pending components.

## 12.2 Figure 2

Do not plot zero on a log scale. Use:

- linear;
- symlog;
- a declared plotting floor;
- a separate zero category.

Add units.

## 12.3 Figures 3 and 4

Add:

- individual seed points;
- confidence intervals;
- exact \(N\);
- units.

## 12.4 Figure 4

Separate curtailment-spam voltage variability from overvoltage-area attacks.

## 12.5 Tables VII and VIII

Use consistent units and report:

- clean value;
- attack value;
- paired difference;
- median;
- confidence interval;
- seed count.

---

# 13. Minimum Experiments Required Before Submission

## 13.1 Equal-scope mechanism evaluation

Compare B1/B3, B2/B5, B4/B5, and B5 against mechanism ablations.

## 13.2 Direct time-series credential-to-feeder containment

Measure credential expiry, session termination, command cleanup, and feeder recovery in one run.

## 13.3 Hardware or constrained attestation

Evaluate at least one constrained or hardware-backed platform.

## 13.4 Real failure injection

Inject verifier/issuer outages, partitions, clock skew, false rejection, and renewal storms.

## 13.5 Second feeder and cross-solver validation

Use another public feeder and validate a preregistered subset across OpenDSS and GridLAB-D.

## 13.6 Interoperability

Test unmodified endpoints, proxy deployment, and mixed legacy/native tiers.

---

# 14. Statistical Analysis Requirements

## 14.1 Experimental unit

Use the complete scenario run, not each timestep.

## 14.2 Pairing

Keep feeder, day, placement, attack, and seed fixed across policy comparisons.

## 14.3 Primary model

Use a mixed-effects model for the TTL-by-scope interaction.

## 14.4 Outcome-specific models

- mixed-effects regression for voltage area;
- logistic mixed model for trips;
- negative-binomial model for counts;
- survival analysis for recovery;
- bootstrap intervals for latency.

## 14.5 Power analysis

Use pilot variance to justify the production seed count.

## 14.6 Failed runs

Preregister retry, timeout, convergence, exclusion, and missing-data rules.

---

# 15. Section-by-Section Revision Plan

## 15.1 Title

Keep the current title unless the standards claim is profile-specific.

## 15.2 Abstract

Remove unsupported backward compatibility, qualify the 0.2 ms result, and report final numerical findings after the production evaluation.

## 15.3 Introduction

Lead with infrastructure risk, then measurement gap, system, and measured results.

## 15.4 Background

Add complete clause-level standards analysis.

## 15.5 Threat model

Clarify each compromise locus and expected defense.

## 15.6 Model

Fix `BRexp`, observed/worst-case physical consequence, units, and Proposition 3.

## 15.7 Design

Add certificate fields, EAT profile, nonce flow, session enforcement, command cleanup, safe mode, and audit design.

## 15.8 Implementation

Report exact software, libraries, crypto parameters, platforms, and versions.

## 15.9 Evaluation methodology

Separate completed methodology from future work.

## 15.10 Results

Organize by research question.

## 15.11 Discussion

Explain scope versus lifetime, fresh keys, sessions, commands, safe mode, issuer trust, and generalization.

## 15.12 Related work

Complete and expand.

## 15.13 Limitations

Do not list unfinished core evaluation in the submitted version.

## 15.14 Conclusion

Report measured findings only.

---

# 16. Required Tables

1. Standards claim and clause table.
2. Threat model by compromise locus.
3. Four dimensions, units, and computation.
4. Baseline and ablation mechanism table.
5. Security-invariant results.
6. Equal-scope containment results.
7. Credential/session/command timing.
8. Hardware and software overhead.
9. Cyber blast-radius results.
10. Feeder consequence results.
11. Availability failure results.
12. Cross-solver agreement.
13. Interoperability matrix.
14. Related-work comparison.

---

# 17. Required Figures

1. Baseline versus CONTAINDER architecture.
2. Containment chain.
3. Credential/session/command timeline.
4. Fresh-key attestation sequence.
5. End-to-end testbed.
6. Equal-scope exposure comparison.
7. TTL-by-scope interaction.
8. Time-series feeder containment.
9. Capacity-time exposure.
10. Voltage-violation area.
11. Attack-family results with uncertainty.
12. Penetration sensitivity.
13. Renewal latency and throughput.
14. Availability-security tradeoff.
15. Cross-solver agreement.
16. Migration-tier interoperability.

---

# 18. Priority Order

## Must fix immediately

1. Complete IEEE 2030.5 clause verification.
2. Remove citation placeholders.
3. Correct `BRexp`.
4. Distinguish observed from worst-case `BRphys`.
5. Resolve endpoint inconsistency.
6. Remove unsupported backward compatibility.
7. Clarify preregistration chronology.
8. Correct B6 and Table IX contradictions.
9. Fix negative violation-area presentation.
10. Replace the questionable physical counterexample.

## Must add before submission

1. Equal-scope B2 versus B5.
2. Direct time-series credential-to-feeder experiment.
3. Fresh-key, session, and command-cleanup ablations.
4. Real failure injection.
5. Constrained or hardware-backed measurements.
6. Second feeder and cross-solver validation.
7. Interoperability test.
8. Confirmatory statistics and confidence intervals.

## Presentation fixes

1. Fix zero values on log axes.
2. Add uncertainty.
3. Add units.
4. Replace “real feeder” with “public benchmark feeder model.”
5. Separate unlike attack metrics.
6. Remove argumentative wording.

---

# 19. Final Submission Checklist

## Standards

- [ ] Exact IEEE 2030.5 edition/profile named.
- [ ] All claims have exact clauses.
- [ ] CRL/OCSP claim scoped correctly.
- [ ] Local deny-list mechanisms discussed.
- [ ] Re-enrollment and key replacement discussed.
- [ ] LFDI/SFDI continuity resolved.
- [ ] Scheduled-control persistence resolved.
- [ ] No pending placeholders remain.

## Model

- [ ] `BRreach` precise.
- [ ] `BRflex` state dependent.
- [ ] `BRauth` separates credential/session/command.
- [ ] `BRexp` consistent.
- [ ] `BRphys` observed/worst-case distinction.
- [ ] Endpoints consistent.
- [ ] Proposition 3 validated.
- [ ] Regression tests released.

## Architecture

- [ ] Fresh key per epoch.
- [ ] Key bound to fresh evidence.
- [ ] Replay prevented.
- [ ] Session bounded.
- [ ] Command effect bounded.
- [ ] Safe mode precise.
- [ ] Issuer boundary explicit.
- [ ] Audit logs included.

## Evaluation

- [ ] B1–B6 reported.
- [ ] Equal-scope comparisons complete.
- [ ] Mechanism ablations complete.
- [ ] Time-series containment measured.
- [ ] Availability faults injected.
- [ ] Constrained/hardware platform tested.
- [ ] Second feeder evaluated.
- [ ] Cross-solver subset reported.
- [ ] Interoperability tested.
- [ ] Statistical power justified.
- [ ] Confidence intervals reported.
- [ ] Failed runs documented.
- [ ] Pilot and confirmatory data separated.

## Writing

- [ ] Abstract contains final numerical results.
- [ ] Unsupported compatibility claim removed.
- [ ] No future-work promise for core validation.
- [ ] No citation placeholders.
- [ ] Related work complete.
- [ ] Figure axes and units correct.
- [ ] Zero values not misused on log scale.
- [ ] Raw and differential metrics reported.
- [ ] Conclusion reports evidence.
- [ ] Limitations do not include unfinished core evaluation.

## Artifact

- [ ] Code deposited.
- [ ] Scenario matrix deposited.
- [ ] Preregistration timestamped.
- [ ] Seeds released.
- [ ] Feeder modifications documented.
- [ ] Analysis scripts released.
- [ ] Figure scripts released.
- [ ] Data-availability statement includes a repository/DOI.
- [ ] Security-sensitive exclusions explained.

---

# 20. Final Candid Recommendation

This version is a meaningful advance and is much closer to an IJCIP-quality paper. The architecture is coherent, the model is substantially improved, and the preliminary feeder results show that the system can produce a serious contribution.

The paper should not yet be submitted because the current evaluation does not cleanly separate:

- least-privilege scope;
- credential lifetime;
- attestation;
- fresh-key rotation;
- session enforcement;
- command cleanup.

The most important next experiment is a true time-series end-to-end run in which a compromised credential controls the feeder, then expires or fails attestation, after which the system terminates the session, cancels or bounds outstanding commands, and measures feeder recovery.

The strongest final result would establish:

1. narrow scope reduces the instantaneous attack envelope;
2. fresh-key rotation prevents copied-key persistence across epochs;
3. session enforcement prevents post-expiry command acceptance;
4. command cleanup bounds residual physical effect;
5. the combined mechanism reduces actual integrated feeder consequence;
6. safe mode preserves acceptable legitimate control availability;
7. these results hold beyond one feeder and one workstation.

After those revisions, IJCIP is a strong and credible target for CONTAINDER.