# Final IJCIP Revision and Ready-to-Submit Plan for CONTAINDER

**Manuscript reviewed:** `main (8).pdf`  
**Title:** *CONTAINDER: Bounding Credential-Compromise Impact in IEEE 2030.5 DER Systems*  
**Target venue:** *International Journal of Critical Infrastructure Protection (IJCIP)*  
**Review objective:** Produce a complete revision, framing, and experimental plan that can turn the current pilot manuscript into a ready-to-submit journal article.

---

# 1. Executive Decision

## Current recommendation

> **Do not submit the current version yet. Complete the work below and then submit to IJCIP.**

The revised manuscript is substantially more credible than the earlier version. It corrects important modeling errors, withdraws invalid claims, distinguishes exploratory from confirmatory evidence, acknowledges close prior systems such as SPIFFE/SPIRE and IEC 62351, and develops a more interesting empirical result: **authorization safety depends on the shape of the permitted control set, not merely its width**.

The paper is still not ready for IJCIP because its strongest claims remain limited by six blocking issues:

1. The standards premise has not been verified against IEEE 2030.5-2023.
2. The central feeder result is demonstrated primarily at a light-load/high-PV point where the legitimate feeder is already outside the ANSI voltage band.
3. It is not yet established that the proposed reactive absorption floor is expressible and enforceable through IEEE 2030.5/CSIP authorization.
4. The most relevant attacker for the lifetime argument—a stealth-constrained attacker—has not been evaluated.
5. Real IEEE 2030.5 interoperability, session expiration, and command-effect cleanup remain untested end to end.
6. The physical evaluation is still a one-feeder, one-solver pilot rather than a confirmatory journal evaluation.

These are solvable. Since all experiments and implementation work can now be completed, the paper should be revised as a finished journal study rather than submitted as an exploratory pilot.

## Expected decision if submitted now

A likely decision is:

> **Reject with encouragement to resubmit**

The paper is likely to be judged positively on topic, transparency, and potential contribution, but negatively on standards validity, external validity, deployability, and experimental completeness.

## Expected decision after completing this plan

After completing the mandatory work, the paper should become:

> **A strong IJCIP candidate, likely to receive major revision rather than rejection, with a realistic path to acceptance.**

---

# 2. What the Final Paper Should Be About

The paper currently contains several possible stories. The final article should have one primary story and three supporting contributions.

## 2.1 Recommended primary story

> **Credential containment for DER control requires controlling both the shape of authorized physical actions and the duration for which compromised authority remains effective.**

This story has two parts:

1. **Scope shape controls instantaneous physical leverage.**  
   A numerically narrow authorization may remain unsafe if it includes a harmful control point, such as withdrawal of reactive absorption. Therefore, least privilege must constrain the feasible physical action set, not merely reduce a nominal magnitude cap or grant fewer protocol functions.

2. **Credential, session, and command lifetime control exposure duration.**  
   When the operationally necessary authorization envelope still permits harmful behavior, short-lived credentials only provide containment if expiration is enforced at the credential, active-session, and persistent-command layers.

This is a stronger and more precise story than:

- “reachability is insufficient,”
- “short-lived credentials are better,”
- or “narrow authorization contains attacks.”

## 2.2 Recommended supporting contributions

### Contribution A — DER-specific credential architecture

CONTAINDER separates:

- bootstrap identity,
- operational credential,
- and numeric/function authorization.

It combines:

- attestation-gated issuance,
- fresh operational keys,
- short credential lifetime,
- per-command authorization,
- session-age enforcement,
- persistent-command cleanup,
- and safe degradation.

### Contribution B — Authorization-set-shape result

The final paper should show, across multiple feeders and compliant operating states, that:

- a symmetric reactive magnitude cap that includes zero may fail to contain withdrawal-of-support attacks;
- an authorization that preserves a minimum required absorption can contain those attacks;
- this result follows from the feasible authorization set, not automatically from whether the command uses `opModFixedVar` or `opModVoltVar`.

### Contribution C — Exposure-duration result

At a fixed authorized physical envelope:

- the instantaneous attack trajectory is unchanged before expiration;
- bounded lifetime truncates, rather than attenuates, the attack;
- the resulting integrated harm depends on the measured harm-accrual rate and the chosen enforcement lifetime;
- the operational benefit must be evaluated jointly with regulator wear, availability, curtailment, and recovery behavior.

### Contribution D — Deployable gateway-proxy path

The gateway tier should become the practical deployment contribution:

- hardware-backed key and attestation at the gateway;
- trusted time and session enforcement at the gateway;
- compatibility with downstream legacy DER devices;
- numeric authorization enforcement before forwarding controls;
- explicit mapping from upstream operational credential to downstream IEEE 2030.5 identities and controls.

This contribution requires an actual implementation and interoperability evaluation.

---

# 3. Claims the Final Paper May and May Not Make

A claims matrix should govern the final rewrite.

## 3.1 Claims that can become primary claims after completion

| Claim | Evidence required |
|---|---|
| CONTAINDER bounds copied operational-key authority by the next credential epoch | Fresh-key renewal experiment with real key rotation and expired-key rejection |
| CONTAINDER bounds active-session authority | Real mTLS session experiment with expiry and forced closure/revalidation |
| CONTAINDER bounds persistent DERControl effects | Real or protocol-faithful scheduled-control experiment with cleanup |
| Authorization-set shape matters more than nominal width for reactive containment | Matched feasible-set experiments on at least two feeders and compliant states |
| A reactive authorization including zero absorption can remain unsafe | Replicated results with legitimate compliant baselines and two-sided safety metrics |
| An absorption-floor policy can preserve volt-var support while containing withdrawal attacks | Service-quality and safety evaluation, not only one-sided overvoltage reduction |
| Lifetime truncates physical exposure rather than attenuating instantaneous harm | Direct time-series experiments at fixed scope over multiple TTL values |
| The gateway tier is incrementally deployable | Interoperability with an unmodified or minimally modified IEEE 2030.5 endpoint |
| Non-renewal is practical under realistic gateway conditions | Hardware-backed attestation and networked renewal measurements |

## 3.2 Claims that must be narrowed

### Current overclaim

> IEEE 2030.5 provides no online mechanism to withdraw a compromised credential.

### Replace with

> The accessible IEEE 2030.5-2018 and CSIP materials do not provide standardized CRL/OCSP revocation. Local identity denial can refuse future authorization, but it does not by itself establish a bounded end-to-end containment time across new sessions, active sessions, cached authorization, and already-issued DER controls.

This wording must be updated after reading IEEE 2030.5-2023.

### Current overclaim

> Attested issuance costs 0.23 ms.

### Replace until hardware is evaluated

> The software-emulated EAT/X.509 issuance path costs 0.23 ms on the evaluation workstation.

After hardware-backed evaluation, report separate numbers for:

- evidence generation,
- quote or attestation operation,
- verification,
- key generation,
- certificate signing,
- and end-to-end renewal.

### Current overclaim

> Every seed trips.

### Replace unless a stateful protection model is implemented

> Every seed crosses the modeled IEEE 1547 Category II overvoltage trip threshold.

Use “trip” only when the model includes:

- persistence timers,
- disconnect behavior,
- and state updates after disconnection.

### Current overclaim

> The absorption-floor authorization still delivers volt-var.

This is not established solely by a fixed absorbing setpoint or by avoiding overvoltage. The final paper must measure:

- curve-tracking error,
- voltage-support utility,
- undervoltage effects,
- reactive energy,
- and legitimate-service success.

## 3.3 Claims to remove entirely

Remove or avoid:

- novelty claims for short-lived certificates;
- novelty claims for non-renewal instead of revocation;
- novelty claims for the four-dimension accounting;
- statements that static attack graphs generally cannot represent time or physical impact;
- claims that both session enforcement and command cleanup are empirically necessary unless the ablations are actually implemented;
- conclusions from the superseded Generator-based harness;
- the old 1,700× exposure comparison;
- “neither half alone suffices” unless demonstrated with valid, independent mechanism ablations;
- statements that a narrow function list automatically preserves useful control while containing the attack.

---

# 4. Mandatory Standards Work

This is the highest-priority non-experimental task.

## 4.1 Obtain IEEE 2030.5-2023

The final paper cannot say that the edition in force was unavailable. Obtain it through:

- the university library;
- an IEEE institutional subscription;
- interlibrary loan;
- an advisor or collaborator;
- a standards-working-group contact;
- or purchase.

The paper is specifically about IEEE 2030.5. Reviewers will not accept an unresolved standards premise when the standard can be obtained.

## 4.2 Build a clause-level standards matrix

Replace the current residual-risk table with a verified matrix.

| Topic | IEEE 2030.5-2018 | IEEE 2030.5-2023 | CSIP version in scope | Final interpretation |
|---|---|---|---|---|
| Certificate validity period | Exact clause | Exact clause | Profile clause | Whether indefinite/long validity is permitted |
| CRL behavior | Exact clause | Exact clause | Profile clause | Whether CRLs are prohibited, unsupported, or optional |
| OCSP behavior | Exact clause | Exact clause | Profile clause | Whether status checking is prohibited, unsupported, or optional |
| Local allow/deny list | Exact clause | Exact clause | Profile clause | Whether it is permitted, required, and where enforced |
| Re-enrollment/re-provisioning | Exact clause | Exact clause | Profile clause | Whether a compromised identity can be replaced |
| LFDI/SFDI derivation | Exact clause | Exact clause | Profile clause | Identity and certificate binding |
| FunctionSetAssignments | Exact clause | Exact clause | Profile clause | Function-level scope |
| Numeric value constraints | Exact clause or “not defined” | Exact clause or “not defined” | Profile clause | Whether bounds such as an absorption floor are expressible |
| DERProgram membership | Exact clause | Exact clause | Profile clause | Program-level authorization |
| Scheduled DERControl behavior | Exact clause | Exact clause | Profile clause | Duration, supersession, cancellation |
| Active-session behavior after certificate expiry | Standard or implementation-specific | Same | Profile effect | Whether reauthentication is required |
| Control cancellation on identity denial | Exact behavior or unspecified | Same | Profile effect | Residual command authority |
| Gateway/proxy allowance | Exact clause or external architecture | Same | Profile effect | Compatibility basis |

## 4.3 Separate six authority-withdrawal mechanisms

The background must distinguish:

1. **PKI revocation:** CRL or OCSP.
2. **Local identity denial:** server refuses the certificate-derived identity.
3. **Authorization removal:** FunctionSetAssignments or DERProgram membership changes.
4. **Session termination:** existing authenticated channel is closed or revalidated.
5. **Command cancellation:** scheduled or latched DERControl is withdrawn or superseded.
6. **Identity replacement:** device is re-enrolled or re-keyed.

The final motivation should be:

> The standard may support local administrative denial, but the end-to-end time from compromise response to termination of all effective physical authority is not automatically bounded.

That is the problem CONTAINDER addresses.

## 4.4 Resolve numeric authorization expressiveness

The authorization-shape result is only actionable if the system can express and enforce the proposed set.

Determine whether the standard or profile can represent:

- `q <= -q_min` when negative means absorption;
- `q in [q_low, q_high]`;
- a bounded deviation from a reference volt-var curve;
- a fixed setpoint range;
- a maximum active-power fraction;
- and a maximum command duration.

For each bound, document:

- where it is stored;
- which protocol resource carries it;
- which component enforces it;
- whether it is native to IEEE 2030.5;
- whether it requires a gateway policy extension;
- and whether messages remain protocol-conformant.

If FunctionSetAssignments only grants access to a function and does not constrain values, frame CONTAINDER as:

> A value-constrained authorization layer placed above FunctionSetAssignments and enforced by the DERMS or gateway proxy.

This is acceptable, but it must be explicit.

---

# 5. Correct the Threat and Containment Model

## 5.1 Separate compromise classes

The current threat model combines attacks that have different containment behavior. Use the following table.

| Compromise class | Attacker persistence | Primary defense | Residual bound |
|---|---|---|---|
| Copied operational key | External attacker possesses current epoch key only | Fresh key every epoch + short credential | At most remaining epoch |
| Stolen active session | Attacker controls established session | Session-age enforcement + per-command revalidation | Session/revalidation interval |
| Persistent command | Attacker has already issued scheduled/latched control | Command-duration cap + cancellation/safe restoration | Command cleanup bound |
| Compromised firmware detectable by attestation | Attacker remains on device | Attestation-gated renewal | Detection-probability dependent |
| Compromised firmware not represented in measurement | Attacker remains and renews successfully | Not defeated by attestation | Outside guarantee; scope/lifetime limit only |
| Stolen bootstrap key | Attacker can attempt enrollment | Hardware binding, enrollment policy, audit | Depends on enrollment controls |
| Compromised gateway | Attacker controls proxy and downstream mapping | Gateway attestation, recovery, issuer policy | Not bounded by downstream device key rotation |
| Compromised aggregator/DERMS | Broad legitimate authority | Scope separation, dual control, governance | Partially addressed |
| Compromised issuer | Can issue arbitrary credentials | Governance/HSM/audit | Protection boundary |

## 5.2 Correct expected-retention formulas

The current `T/p` statement should not be used for every compromise.

### Copied operational key

If a key is copied at a uniformly random point during a credential epoch of length `T`:

\[
E[T_{\text{retained}}] = T/2
\]

and the worst case is:

\[
T_{\text{retained}} \leq T.
\]

This case does not require attestation to detect the theft. Fresh-key renewal makes the old key unusable after the epoch.

### Persistent compromise detected at renewal

If the attacker remains on the device and each renewal independently detects compromise with probability `p`:

- compromise immediately after issuance gives expected retention approximately:

\[
T/p;
\]

- compromise uniformly distributed within the current epoch gives:

\[
E[T_{\text{retained}}]
= T/2 + \frac{1-p}{p}T
= T\left(\frac{1}{p}-\frac{1}{2}\right).
\]

State the timing assumption explicitly.

### Stolen session

Retained authority is bounded by:

\[
\min(T_{\text{session-age}}, T_{\text{revalidation}}, T_{\text{forced-close}})
\]

depending on the implementation.

### Persistent command

Retained physical effect is bounded by:

\[
T_{\text{cmd}} =
\min(T_{\text{command-duration}}, T_{\text{cancel}}, T_{\text{safe-restore}}).
\]

## 5.3 Replace one `BRauth` number with a vector

The final results should report:

\[
BR_{\text{auth}} =
(T_{\text{cred}}, T_{\text{sess}}, T_{\text{cmd}})
\]

before optionally summarizing with a maximum.

A single maximum hides which containment layer failed.

---

# 6. Final System Architecture and Implementation Work

## 6.1 Make the gateway tier the implemented deployment path

The manuscript already recognizes that the gateway tier is the practical path. Implement it and make it central.

### Required components

1. **Upstream operational-credential client**
   - obtains short-lived credential;
   - presents attestation evidence;
   - rotates key every epoch.

2. **Attestation verifier**
   - validates nonce freshness;
   - validates hardware quote or evidence;
   - checks reference values;
   - returns explicit pass/fail/degraded result.

3. **Credential issuer**
   - signs operational certificate;
   - embeds or references role/site/scope;
   - enforces TTL;
   - rejects reused keys and replayed evidence.

4. **Gateway policy enforcement point**
   - terminates upstream mTLS;
   - validates credential and session age;
   - maps credential identity to downstream DER identities;
   - checks function-level and numeric authorization;
   - caps command duration;
   - records audit events.

5. **Command-lifecycle controller**
   - tracks scheduled commands;
   - cancels or supersedes commands on expiration/denial;
   - restores a safe autonomous profile.

6. **Downstream IEEE 2030.5 interface**
   - communicates with an existing endpoint;
   - preserves valid IEEE 2030.5 messages;
   - documents where proxy behavior extends the authorization model.

## 6.2 Add a real architecture figure

The final figure should show:

- DER device;
- legacy DER;
- gateway proxy;
- attester;
- verifier;
- issuer;
- authorization service;
- DERMS/aggregator;
- OpenDSS or grid model;
- bootstrap key;
- operational key;
- evidence;
- certificate;
- session;
- DERControl;
- trust boundaries;
- and failure boundaries.

Use different arrow styles for:

- enrollment;
- renewal;
- control traffic;
- and cancellation.

## 6.3 Implement real IEEE 2030.5 interoperability

Use an existing IEEE 2030.5 implementation where possible, including the EPRI client/server if available.

### Required interoperability sequence

1. Client enrollment.
2. Certificate-derived identity processing.
3. FunctionSetAssignments retrieval.
4. DERProgram binding.
5. Valid DERControl submission.
6. Scope-conforming command acceptance.
7. Out-of-scope command rejection.
8. Credential renewal with a fresh key.
9. Credential expiration during an open session.
10. Command attempt after expiration.
11. Long-duration command extending beyond expiration.
12. Cancellation or safe restoration.
13. Local denylist update.
14. Session and command behavior after denylisting.
15. Mixed legacy/native operation through the gateway.

### Evidence to collect

- packet capture;
- client logs;
- server logs;
- gateway logs;
- certificate chain;
- credential issuance events;
- session events;
- authorization decisions;
- command cancellation events;
- and timestamps aligned across components.

## 6.4 Implement hardware-backed key and attestation

The gateway is the right hardware target because it is the proposed deployment path.

### Suggested implementation

- Linux gateway or mini-PC;
- TPM 2.0;
- TPM-backed non-exportable operational key;
- TPM quote or measured-boot evidence;
- EAT claim set carrying nonce, measurement, and public-key digest;
- verifier reference values;
- real X.509 issuance.

### Measure

- TPM key generation;
- evidence generation;
- quote generation;
- verifier processing;
- certificate issuance;
- end-to-end renewal;
- mTLS handshake;
- CPU utilization;
- memory;
- network bytes;
- p50/p95/p99 latency;
- throughput under concurrent renewal.

### Security tests

- old operational key replay;
- reused nonce;
- stale evidence;
- modified evidence;
- wrong key digest;
- bad measurement;
- old firmware reference;
- copied certificate without key;
- copied key from previous epoch;
- verifier unavailable;
- issuer unavailable.

---

# 7. Complete Experimental Program

The final evaluation should be organized by research question rather than by development history.

## RQ1 — What authority can each compromise locus obtain?

### Goal

Measure the cyber reach and feasible physical control set under realistic scope policies.

### Factors

- compromise locus:
  - device;
  - gateway;
  - aggregator;
  - issuer as boundary;
- authorization granularity:
  - device;
  - site;
  - feeder segment;
  - fleet;
- function scope:
  - read-only;
  - fixed P;
  - fixed Q;
  - volt-var;
  - volt-watt;
  - connect/disconnect;
- numeric bounds:
  - active-power fraction;
  - reactive symmetric cap;
  - reactive absorption floor;
  - curve-deviation bound;
- operating state:
  - irradiance;
  - state of charge;
  - availability.

### Metrics

- reachable devices;
- reachable sites;
- reachable feeders;
- active-power flexibility interval;
- reactive-power flexibility interval;
- feasible-region area;
- command duration;
- and authorization-path length.

### Improvement over current engine

The current synthetic four-level ACL model is useful but too stylized. Add:

- multiple fleet sizes;
- uneven site sizes;
- multiple feeders;
- heterogeneous DER types;
- hierarchical aggregators;
- shared gateways;
- and misconfiguration rates.

Report sensitivity rather than one 200-device example.

---

## RQ2 — How does authorization-set shape affect physical safety?

This should be the central physical experiment.

### 7.2.1 First establish compliant legitimate operating points

The current 222% PV/light-load point is already noncompliant under legitimate operation. Do not use it as the primary state.

For each feeder:

1. Run the legitimate IEEE 1547 Category B volt-var controller.
2. Sweep PV penetration and load multiplier.
3. Determine the highest penetration at which:
   - all voltages remain within the declared ANSI band, or
   - the chosen baseline violation criterion is satisfied;
   - no trip threshold is crossed;
   - regulator/capacitor behavior converges.
4. Define operating tiers relative to the compliant hosting limit:
   - 80%;
   - 90%;
   - 95%;
   - 100%;
   - 105%;
   - plus the current extreme stress case.

Use the compliant 90–100% tiers for primary claims. Keep 105% and 222% as stress tests.

### 7.2.2 Reactive authorization sets

Evaluate matched feasible sets, not mismatched labels.

#### Set family Q1 — symmetric magnitude cap

\[
Q \in [-q_{\max}, +q_{\max}]
\]

This always contains zero.

#### Set family Q2 — absorption-only band

\[
Q \in [-q_{\max}, -q_{\min}],
\quad q_{\min}>0.
\]

This excludes zero absorption.

#### Set family Q3 — reference-curve tube

\[
|Q(V)-Q_{\text{ref}}(V)| \leq \epsilon
\]

with additional minimum-support constraints where necessary.

#### Set family Q4 — rate-limited curve change

Bound:

- maximum movement of breakpoints;
- maximum slope change;
- maximum change per time interval.

#### Set family Q5 — read-only/autonomous fallback

No remote reactive rewrite; local autonomous curve remains active.

### 7.2.3 Match the fixed-setpoint and curve experiments

To determine whether the protocol primitive matters:

- give `opModFixedVar` and `opModVoltVar` the same feasible physical set;
- compare them under identical bounds;
- keep all other variables fixed.

Do not compare:

- a two-sided setpoint cap,
- against a one-sided curve floor,

and interpret the result as a primitive difference.

### 7.2.4 Active-power authorization sets

Evaluate:

\[
P \in [0, \sigma P_{\max}]
\]

for multiple `σ`.

But do not interpret negative overvoltage deltas as safety without pricing curtailment.

Measure:

- curtailed energy;
- service/revenue loss;
- voltage effect;
- and availability impact.

### 7.2.5 Physical metrics

Primary metrics should include:

1. overvoltage area;
2. undervoltage area;
3. two-sided ANSI violation area;
4. maximum voltage;
5. minimum voltage;
6. nodes outside band;
7. threshold-screen events;
8. actual protection operations if modeled;
9. regulator tap operations;
10. capacitor changes;
11. reverse-power events;
12. curtailment energy;
13. reactive-energy deviation;
14. legitimate volt-var service error;
15. recovery time.

### 7.2.6 Acceptance criterion for the absorption-floor claim

The claim is supported only if, across multiple feeders and compliant operating states:

- symmetric sets containing zero produce materially greater physical harm;
- an absorption-floor set prevents the attack;
- the result holds with confidence intervals;
- the policy does not produce unacceptable undervoltage;
- legitimate volt-var service remains within a declared error bound;
- and the bound is implementable in the system.

---

## RQ3 — How does retained-authority duration affect integrated harm?

### Goal

Measure the physical harm-accrual rate and the truncation effect of credential/session/command expiration.

### TTL values

Use a logarithmically and operationally meaningful range, for example:

- 5 min;
- 15 min;
- 30 min;
- 1 h;
- 3 h;
- 6 h;
- 12 h;
- 24 h.

The exact values should reflect the gateway deployment model and renewal reliability.

### Policies

At identical scope:

1. long-lived legacy;
2. short credential without session closure;
3. short credential with session closure only;
4. short credential with command cleanup only;
5. full CONTAINDER;
6. local denylist response;
7. denylist + session close;
8. denylist + session close + command cancellation.

### Required result

Show separately:

- pre-expiry instantaneous harm;
- credential acceptance after expiry;
- session command acceptance after expiry;
- persistent command effect after expiry;
- feeder recovery;
- post-expiry tail;
- and operational transition cost.

### Do not report the lifetime ratio as a measured effect size

The physical mechanism does not attenuate the command before expiration. Therefore report:

- measured harm-accrual rate;
- measured recovery tail;
- selected TTL;
- and resulting integrated harm.

State that the TTL is an operator-controlled parameter.

---

## RQ4 — How does a stealth-constrained attacker change the value of lifetime containment?

This is mandatory.

### Why this matters

The current loud attack would likely be detected through:

- AMI voltage readings;
- regulator activity;
- customer complaints;
- and feeder alarms.

If operational detection is faster than credential expiration, the lifetime mechanism is not the binding response.

### Attacker models

#### A1 — Oracle maximum-impact attacker

Has complete feeder state and maximizes immediate physical consequence.

#### A2 — Telemetry-limited attacker

Uses only information available through the compromised identity.

#### A3 — Stealth-constrained attacker

Optimizes cumulative harm subject to constraints such as:

- no voltage above the selected alarm/trip threshold;
- limited number of nodes outside ANSI band;
- bounded command changes;
- no abrupt fleet-wide transition;
- bounded tap-operation anomaly;
- or action only during high-PV windows.

#### A4 — Wear attacker

Maximizes:

- tap operations;
- capacitor operations;
- or reactive cycling,

while remaining below obvious voltage alarms.

#### A5 — Curtailment attacker

Maximizes lost generation or economic impact while maintaining voltage compliance.

### Metrics

- cumulative voltage violation;
- time below detection threshold;
- tap/capacitor operations;
- curtailed energy;
- detection delay;
- credential-lifetime benefit;
- and physical recovery.

### Core analysis

Compare whether containment is bound by:

- credential lifetime;
- utility detection time;
- local denylist response;
- or command cleanup.

This directly supports the practical value of short-lived authority.

---

## RQ5 — How does local denial compare with non-renewal?

This baseline is essential.

### Baselines

1. legacy, no response;
2. local identity deny only;
3. authorization removal only;
4. deny + session termination;
5. deny + command cancellation;
6. complete legacy incident response;
7. CONTAINDER non-renewal;
8. CONTAINDER plus emergency deny.

### Detection-delay values

Use a range such as:

- immediate;
- 1 min;
- 5 min;
- 15 min;
- 1 h;
- 6 h.

### Metrics

- new-session rejection;
- active-session survival;
- command survival;
- physical-effect survival;
- administrator action required;
- containment latency;
- availability impact;
- and auditability.

### Final framing

CONTAINDER should not be presented as replacing every local deny mechanism. It provides:

- an automatic upper bound when detection or administration is absent;
- while local deny can provide faster emergency response when compromise is detected.

The strongest system combines both.

---

## RQ6 — Are session and command cleanup independently necessary?

The current feeder harness did not identify these mechanisms. Implement a real ablation.

### Test sequence

1. Establish mTLS session with valid operational certificate.
2. Issue a command whose duration exceeds certificate expiry.
3. Expire the certificate.
4. Continue sending commands over the existing session.
5. Observe scheduled/latched command state.

### Four mechanism arms

| Arm | Session enforcement | Command cleanup |
|---|---:|---:|
| S0 | No | No |
| S1 | Yes | No |
| S2 | No | Yes |
| S3 | Yes | Yes |

### Measure

- `Tcred`;
- `Tsess`;
- `Tcmd`;
- last accepted command;
- last effective command;
- feeder recovery;
- and safe-profile restoration.

### Required evidence

The physical time series should show different outcomes across S0–S3. Unit tests alone are insufficient for the systems claim.

---

## RQ7 — Does the result generalize across feeders and solvers?

### Feeders

At minimum use:

1. IEEE 8500-node feeder;
2. IEEE 123-bus feeder rebuilt with the corrected `PVSystem + InvControl` methodology.

The PNNL 9500 case may remain an explained failure if it cannot be fixed, but it cannot serve as the second feeder.

A third feeder would strengthen the paper but is not mandatory if the first two differ meaningfully in:

- voltage level;
- regulator structure;
- topology;
- stiffness;
- and DER hosting characteristics.

### Cross-solver validation

Use OpenDSS and GridLAB-D for selected cases:

- legitimate base case;
- symmetric reactive cap attack;
- absorption-floor policy;
- active-power attack;
- lifetime expiration case.

### Compare

- voltage distribution;
- maximum/minimum voltage;
- total P and Q;
- regulator states;
- capacitor states;
- violation area;
- and direction of treatment effect.

Predefine conversion tolerances before seeing final results. Report both numerical differences and whether conclusions agree.

### If model conversion is imperfect

Do not demand identical values. Require:

- same sign of the key contrast;
- similar affected regions;
- and no contradiction of the principal safety conclusion.

---

## RQ8 — What are the reliability and availability costs?

### Networked fault injection

Replace in-process-only outages with networked experiments using:

- latency injection;
- packet loss;
- disconnection;
- DNS or endpoint failure;
- verifier failure;
- issuer failure.

### Conditions

- 50 ms, 100 ms, 250 ms, 500 ms, 1 s latency;
- 0%, 1%, 5%, 10% loss;
- outage durations from minutes to longer than TTL;
- correlated fleet renewal;
- clock skew;
- gateway reboot;
- verifier recovery.

### Renewal-storm scenarios

Test synchronized renewal for:

- 1,000;
- 10,000;
- 100,000 simulated credentials.

Then test randomized renewal jitter.

### Policies

- fail closed;
- bounded grace;
- degraded autonomous control;
- previous low-risk scope;
- emergency credential.

### Metrics

- legitimate command availability;
- renewal success;
- p50/p95/p99 latency;
- issuer queue;
- CPU and memory;
- stale authority duration;
- fleet fraction without control;
- voltage consequence during outage;
- and recovery time.

### Operational cost

Report:

- regulator taps;
- capacitor changes;
- curtailment;
- and control discontinuities caused by expiration.

---

## RQ9 — Does hardware-backed deployment remain practical?

### Platform

Use the gateway-proxy hardware implementation.

### Experiments

1. single renewal latency;
2. concurrent renewal;
3. periodic renewal for 24–72 hours;
4. key rotation under load;
5. attestation failure;
6. verifier outage;
7. issuer outage;
8. gateway reboot;
9. clock-skew injection;
10. network partition.

### Report

- end-to-end latency;
- cryptographic subcomponents;
- p95/p99;
- throughput;
- CPU;
- memory;
- network traffic;
- and failure recovery.

Do not extrapolate constrained-device performance solely from workstation ECDSA throughput.

---

## RQ10 — How do different DER technologies affect the result?

The final confirmatory study should not be PV-only if practical.

Include:

- PV inverter;
- battery storage;
- mixed PV/storage.

For storage, evaluate:

- active charging;
- active discharging;
- reactive support;
- state-of-charge constraints;
- and duration-limited flexibility.

This demonstrates that `BRflex` is genuinely state dependent rather than a static capacity label.

---

# 8. Recommended Experimental Matrix

A full factorial across every factor may be too large. Use a staged design.

## 8.1 Stage A — Correctness and mechanism experiments

Purpose: establish system behavior.

- 2 IEEE 2030.5 endpoints or endpoint/proxy configurations;
- 4 session/cleanup arms;
- 5 compromise classes;
- 3 TTLs;
- 3 denial policies;
- 30–50 repetitions for latency/security paths.

Outputs:

- correctness table;
- containment timeline;
- protocol traces;
- hardware timing.

## 8.2 Stage B — Authorization-shape confirmatory experiment

- 2 feeders;
- 2 solvers for selected cases;
- 5 operating tiers relative to hosting capacity;
- 2 load/season profiles minimum;
- 2 control representations:
  - fixed setpoint;
  - curve;
- 4 authorization-set families;
- 5–9 parameter values per set;
- 20–30 paired seeds based on power analysis.

Primary contrasts:

1. includes zero vs excludes zero;
2. matched setpoint vs curve feasible set;
3. compliant vs overstressed base state;
4. feeder interaction.

## 8.3 Stage C — Lifetime and attacker experiment

- 2 feeders;
- 2–3 operating states;
- 6–8 TTLs;
- 4 attacker models;
- 4 lifecycle mechanisms;
- 20–30 paired seeds.

Primary contrasts:

- lifetime slope at fixed scope;
- loud vs stealth attacker;
- local deny vs non-renewal;
- session/cleanup ablations.

## 8.4 Stage D — Availability and deployment experiment

- hardware gateway;
- 5 network-latency levels;
- 4 outage durations;
- 3 safe-mode policies;
- 3 fleet scales;
- 20–50 repetitions per condition.

---

# 9. Statistical Analysis Plan

## 9.1 Pre-register the confirmatory study properly

Before executing the new confirmatory runs:

1. freeze hypotheses;
2. freeze scenario matrix;
3. freeze exclusions and retry policy;
4. freeze primary endpoint;
5. freeze statistical models;
6. deposit to a trusted timestamped repository;
7. record DOI or immutable timestamp;
8. then run the new experiments.

The existing pilot remains exploratory.

Rename the current Section 7 until this is done:

> **Planned Confirmatory Evaluation**

After proper registration, the final paper may use:

> **Confirmatory Evaluation Protocol**

## 9.2 Experimental unit

The experimental unit is the complete scenario/seed run, not each timestep or node.

Do not inflate sample size using:

- nodes;
- minutes;
- or commands

as independent observations.

## 9.3 Primary endpoint

Use a two-sided physical-safety endpoint for the primary system-level analysis:

\[
J_{\text{band}}
=
\sum_{n,t}
\left[
\max(0,V_n(t)-V_{\max})
+
\max(0,V_{\min}-V_n(t))
\right]\Delta t.
\]

Use one-sided overvoltage only as an attack-specific secondary endpoint.

## 9.4 Primary hypotheses

### H1 — Authorization shape

An authorization set excluding withdrawal of required reactive support produces lower two-sided violation area and fewer threshold events than a matched-width set containing zero.

### H2 — Primitive versus feasible set

At matched feasible physical sets, fixed-setpoint and curve-based controls do not materially differ on the primary safety endpoint.

### H3 — Lifetime truncation

At fixed scope, integrated harm increases with retained-authority duration; the instantaneous pre-expiry trajectory is unchanged.

### H4 — Mechanism decomposition

Session enforcement and command cleanup independently reduce `Tsess` and `Tcmd`.

### H5 — Stealth interaction

The relative value of short-lived authority is greater when detection delay exceeds TTL, particularly for stealth-constrained attacks.

### H6 — Operational tradeoff

Containment reduces attack exposure but may increase regulator operations, curtailment, or availability loss.

## 9.5 Models

Possible models:

- mixed-effects model for log-transformed violation area;
- negative-binomial model for violating-node or operation counts;
- mixed-effects logistic model for threshold/protection events;
- survival model for recovery time;
- linear or segmented regression for lifetime versus integrated harm;
- hierarchical model with feeder and operating profile effects.

Include random effects for:

- seed;
- day/profile;
- feeder where appropriate.

## 9.6 Report

For every primary contrast:

- estimate;
- 95% confidence interval;
- paired effect;
- raw distribution;
- sample size;
- convergence/exclusion count;
- and multiplicity correction within hypothesis families.

Do not report only medians.

## 9.7 Non-convergence

Predefine:

- retry count;
- iteration limits;
- whether unsettled runs remain;
- how they are flagged;
- sensitivity analysis excluding them;
- and whether non-convergence is itself an outcome.

The current transparent handling is good and should be retained in a concise form.

---

# 10. Writing and Framing Revision

The current paper is approximately 48 pages and about 14,800 extracted words. The abstract is approximately 466 words. The official IJCIP guide requires an abstract no longer than 250 words.

The final manuscript should be substantially shorter and should read as a finished study rather than a rebuttal, correction log, or research diary.

## 10.1 Recommended title

The current title is acceptable. Stronger alternatives include:

1. **CONTAINDER: Scope- and Lifetime-Bounded Credential Containment for IEEE 2030.5 DER Control**
2. **CONTAINDER: Containing Credential Compromise in IEEE 2030.5 DER Systems**
3. **Bounding Credential Authority and Physical Impact in IEEE 2030.5 DER Systems**

The first is the most precise because it foregrounds the two key controls.

## 10.2 Abstract

### Requirements

- no more than 250 words;
- no citations;
- no development history;
- no “pilot” framing after confirmatory work is complete;
- one problem;
- one design;
- one evaluation scale;
- two or three results;
- one practical implication.

### Final abstract template

Do not use unverified numbers. Replace bracketed fields after the final study.

> IEEE 2030.5 authenticates distributed energy resources using certificate-derived identities, but local credential denial does not necessarily terminate active sessions or retract previously issued controls. We present CONTAINDER, a gateway-deployable architecture that separates bootstrap identity from short-lived operational authority and enforces expiration across credential, session, and command-effect layers. CONTAINDER also adds value-constrained authorization for DER functions. We evaluate the design using a hardware-backed credential service, an IEEE 2030.5 gateway prototype, and time-series power-flow experiments on [FEEDERS] under [OPERATING STATES] and [ATTACK MODELS]. The results show that authorization safety depends on the feasible control set rather than nominal scope width: reactive bounds that admit withdrawal of required absorption remain harmful, whereas bounds preserving at least [THRESHOLD] of legitimate support reduce [PRIMARY ENDPOINT] by [EFFECT, CI] without violating [SERVICE CRITERION]. At fixed scope, short-lived credentials do not attenuate pre-expiry behavior but truncate exposure; session and command cleanup reduce residual authority from [BASELINE] to [BOUND]. A stealth-constrained attacker demonstrates when credential lifetime, rather than operational detection, is the binding containment mechanism. Hardware-backed renewal has [P99] latency, while safe-mode policies expose a measurable tradeoff between stale authority, legitimate control availability, and regulator operations. These findings show that practical DER credential containment requires both physically meaningful authorization sets and end-to-end lifetime enforcement.

Keep the final abstract around 200–240 words.

## 10.3 Introduction

### Keep

- critical-infrastructure importance;
- credential-compromise problem;
- distinction between action magnitude and duration;
- CONTAINDER overview;
- three or four contributions.

### Remove or compress

- long attack-graph objection;
- repeated statements that the model is not novel;
- development-history corrections;
- detailed pilot caveats;
- paragraphs explaining what earlier versions got wrong.

### Recommended flow

1. DER control credentials authorize physical actions.
2. Existing response mechanisms may reject identity but do not necessarily bound all residual authority.
3. Containment has two independent dimensions:
   - feasible physical action set;
   - effective authority duration.
4. CONTAINDER addresses both.
5. Evaluation and results.
6. Contributions.

### Recommended contributions

Use four concise bullets:

1. DER-specific credential and enforcement architecture.
2. Authorization-set-shape finding.
3. End-to-end lifetime/mechanism evaluation.
4. Gateway implementation and multi-feeder evaluation/artifact.

Do not include long results narratives in the contribution bullets.

## 10.4 Background and standards section

### Required changes

- replace the paywall narrative with verified 2023 clauses;
- distinguish revocation, denylisting, session termination, and command cancellation;
- move the full clause matrix to an appendix if lengthy;
- retain only the clauses needed for the design motivation in the main paper.

### Avoid

- “no online mechanism can withdraw it”;
- “indefinite” unless the current clause directly supports it;
- treating local denial as irrelevant.

## 10.5 Threat model

Organize by:

- assets;
- trust anchors;
- compromise classes;
- attacker knowledge;
- attacker persistence;
- protection boundary;
- security goals;
- non-goals.

Add the attack-mechanism coverage table.

Explicitly state that attestation only detects measurements included in the evidence and reference-value policy.

## 10.6 Impact accounting section

Compress this section to approximately 1–2 pages.

Keep:

- `BRreach`;
- `BRflex`;
- `(Tcred, Tsess, Tcmd)`;
- direct physical consequence.

Remove or minimize:

- proposition-style separation language;
- repeated defense of why it is not a contribution;
- extensive attack-graph discussion.

Frame it as:

> Evaluation dimensions and notation.

## 10.7 Design section

Organize around the actual enforcement path:

1. enrollment;
2. attestation and fresh-key binding;
3. credential issuance;
4. numeric/function authorization;
5. session enforcement;
6. command cleanup;
7. safe mode;
8. gateway deployment.

Add a security-claims table:

| Claim | Mechanism | Assumption | Test |
|---|---|---|---|

Correct the copied-key and persistent-compromise retention analysis.

## 10.8 Cyber-side engine section

The current engine section is somewhat disconnected from the strongest paper story.

Either:

- expand its evaluation across compromise loci and heterogeneous graphs;
- or compress it into the methodology and artifact sections.

Do not keep a large engine section based on one synthetic 200-device example if the main contribution is the physical and lifecycle result.

## 10.9 Feeder methodology section

The final main paper should describe only the corrected harness.

Move to supplementary provenance:

- the superseded Generator model;
- warm-start contamination;
- old withdrawn integrals;
- inverted labels;
- prior script names;
- correction history.

A concise main-text statement is enough:

> All reported confirmatory results use independently compiled PVSystem/InvControl cases and legitimate DER operation as the paired counterfactual. Superseded pilot outputs are retained in the artifact but excluded from analysis.

## 10.10 Evaluation protocol section

After completing the study:

- rename to “Evaluation Methodology”;
- state that confirmatory hypotheses were timestamped before execution;
- place the full statistical plan in the supplement;
- do not devote pages to explaining why an old hash was not a timestamp.

The current honesty is correct, but the history should not dominate the final article.

## 10.11 Results section

Organize by research questions:

1. RQ1: system and credential correctness;
2. RQ2: authorization-set shape;
3. RQ3: lifetime and residual authority;
4. RQ4: stealth attacker and detection;
5. RQ5: reliability/availability cost;
6. RQ6: generalization and deployment overhead.

Each subsection should follow:

- question;
- setup;
- result;
- interpretation;
- limitation.

## 10.12 Related work

The prose is now much better, especially the discussion of:

- SPIFFE/SPIRE;
- short-lived Web PKI certificates;
- IEC 62351-8/9;
- and DER guidance.

Replace the current broad Table 7 with concrete systems.

### Recommended columns

| Work/system | DER/2030.5 | Short-lived credential | Attestation | Numeric scope | Session expiry | Command cleanup | Physical evaluation |
|---|---:|---:|---:|---:|---:|---:|---:|

Rows should include:

- SPIFFE/SPIRE;
- BRSKI;
- CA/B Forum short-lived subscriber certificates;
- IEC 62351-8;
- IEC 62351-9;
- IEEE 2030.5/CSIP baseline;
- CONTAINDER.

Avoid comparing the system to entire categories such as “attack graphs.”

## 10.13 Ethics

Keep concise:

- synthetic/lab credentials;
- no production fleet;
- no vendor exploit;
- simulated control only;
- release/disclosure policy.

Remove argumentative language unless a concrete disclosure issue emerges.

## 10.14 Limitations

Use one consolidated limitations section. Do not repeat the same caveats in:

- abstract;
- introduction;
- methodology;
- results;
- and conclusion.

After completing the plan, remaining limitations may include:

- public rather than utility-private feeders;
- synthetic authorization graphs;
- gateway trust concentration;
- limited hardware platforms;
- no field deployment;
- and standards-profile variability.

## 10.15 Conclusion

The conclusion should contain:

1. the problem;
2. the authorization-shape result;
3. the lifetime-enforcement result;
4. the deployment implication;
5. no new limitations narrative.

Do not restate the correction history.

---

# 11. Language and Tone Corrections

The current manuscript repeatedly uses phrases such as:

- “we state plainly”;
- “we do not minimise it”;
- “the honest counter-arm”;
- “what its ratio is not”;
- “rather than let a reader find it”;
- “read the rows, not the columns”;
- “a pre-registration that overstates its own guarantee is worse than none”;
- “we withdraw”;
- “the predecessor”;
- “an earlier version.”

These phrases demonstrate honesty, but their repetition makes the article sound defensive and rebuttal-like.

## Recommended replacement style

### Instead of

> We state plainly that the second solver is absent.

Use:

> The evaluation uses OpenDSS; selected cases are independently validated in GridLAB-D.

### Instead of

> The honest counter-arm, and the cost.

Use:

> Operational cost when scope is already restrictive.

### Instead of

> Read the rows, not the columns.

Use:

> The primary contrast is between authorization sets that include and exclude zero absorption.

### Instead of

> We withdraw the earlier claim.

In the final paper, simply omit the earlier claim. Put correction provenance in the artifact documentation.

---

# 12. Figures and Tables

## 12.1 Figure 1 — containment chain

Keep, but add a separate system architecture figure.

## 12.2 Current Figure 2

The plot is readable, but it plots total overvoltage area while the text analyzes attack-induced excess.

Improve it using either:

### Option A — two panels

- Panel A: total violation area;
- Panel B: attack-induced excess over the paired legitimate baseline.

### Option B — one consistent endpoint

Plot only the attack-induced quantity that is integrated and statistically analyzed.

Also:

- reduce annotation density;
- put the expiry marker outside the traces if possible;
- show confidence interval rather than min–max as the primary band;
- identify the baseline clearly;
- report `n` in the caption;
- do not use the figure to narrate prior errors.

## 12.3 Reactive authorization figure

The reactive-scope result deserves a main figure, not only a table near the end.

Plot:

- x-axis: authorized reactive set or absorption floor;
- y-axis: two-sided violation area;
- separate curves for fixed setpoint and volt-var curve;
- threshold-event rate in a second panel;
- compliant versus stressed states;
- confidence intervals.

Mark:

- zero absorption;
- conformant reference point;
- estimated safe threshold.

## 12.4 Lifetime figure

Plot:

- TTL on x-axis;
- integrated physical harm on y-axis;
- separate attacker models;
- separate scope shapes;
- confidence intervals;
- expected linear reference line.

A second panel should show:

- tap operations;
- availability;
- or command recovery.

## 12.5 Session/command timeline

Create a timeline figure showing:

- certificate expiry;
- last accepted new session;
- last accepted command;
- command cancellation;
- feeder recovery.

Show the four ablation arms.

## 12.6 Table placement

Current central Tables 5 and 6 appear at pages 47–48, far from their discussion. This must be fixed.

Place central result tables immediately after first reference.

Move to supplement:

- full parameter grids;
- diagnostic tables;
- run inventory;
- correction history;
- raw per-seed results.

## 12.7 Captions

Current table captions are too long and argumentative.

Captions should state:

- what is shown;
- units;
- sample size;
- essential definitions.

Interpretation belongs in the body.

## 12.8 Replace Table 7

The current table is too broad and understates the concrete related-work analysis. Use the concrete-system comparison described above.

---

# 13. Artifact and Reproducibility

The artifact direction is already strong. Preserve it, but restructure it for external review.

## 13.1 Required repository structure

```text
artifact/
  README.md
  environment/
    versions.txt
    containers/
  standards/
    claim_matrix.md
  credential_service/
  gateway_proxy/
  attestation/
  ieee2030_5/
  cyber_model/
  feeders/
    ieee8500/
    ieee123/
    gridlabd/
  experiments/
    rq1_scope/
    rq2_shape/
    rq3_lifetime/
    rq4_stealth/
    rq5_availability/
  preregistration/
  results/
    raw/
    processed/
    figures/
  scripts/
    reproduce_all.sh
    check_numbers.py
  superseded/
    README.md
```

## 13.2 One-command reproduction

Provide commands for:

- environment build;
- unit tests;
- credential tests;
- one smoke feeder run;
- complete figure/table reproduction;
- manuscript-number verification.

## 13.3 Provenance

Retain superseded outputs for auditability, but do not mix them with current results.

Each result should record:

- git commit;
- script;
- solver version;
- feeder hash;
- configuration;
- seed;
- timestamp;
- convergence status;
- and output hash.

## 13.4 Persistent identifier

Deposit:

- code;
- configuration;
- preregistration;
- and result archive

under a persistent identifier at submission if permitted, or in an anonymized archive for review.

## 13.5 Number verification

The current `check_numbers.py` idea is excellent.

Extend it to check:

- abstract;
- highlights;
- tables;
- captions;
- main text;
- supplement.

Fail the build if:

- a reported value has no source;
- units disagree;
- sample sizes disagree;
- or a superseded result is referenced.

---

# 14. IJCIP Submission Compliance

Verify all requirements again at submission time against the official guide.

## Mandatory current item

- Abstract must not exceed 250 words.

## Prepare

- title page;
- author affiliation;
- corresponding-author details;
- concise abstract;
- keywords;
- highlights if requested by the submission system;
- CRediT statement;
- competing-interest declaration;
- funding statement;
- data availability statement;
- generative-AI declaration consistent with actual use;
- supplementary material;
- anonymized artifact if review policy requires;
- cover letter.

## AI declaration

The current declaration is generally appropriate, but ensure it exactly matches actual use.

Do not say “grammar checking only” if the tool also assisted with:

- LaTeX formatting;
- code comments;
- or copy editing.

Do not claim that no generated text was incorporated if any tool-assisted wording remains. Use the publisher’s current required wording.

---

# 15. Proposed Final Paper Structure

1. **Introduction**
2. **IEEE 2030.5 Credential and Control Lifecycle**
3. **Threat Model and Security Goals**
4. **CONTAINDER Architecture**
5. **Authorization and Exposure Metrics**
6. **Implementation**
   - gateway proxy;
   - IEEE 2030.5 integration;
   - hardware attestation;
   - command lifecycle.
7. **Evaluation Methodology**
   - feeders and compliant states;
   - attackers;
   - baselines;
   - metrics;
   - statistics.
8. **Results**
   - system correctness;
   - authorization-set shape;
   - lifetime and mechanism decomposition;
   - stealth attacker;
   - availability and cost;
   - cross-feeder/cross-solver validation.
9. **Deployment and Operational Implications**
10. **Related Work**
11. **Limitations**
12. **Conclusion**

Move to supplement:

- standards claim matrix;
- complete scenario matrix;
- full per-seed tables;
- solver diagnostics;
- failed PNNL case;
- superseded-run provenance;
- detailed statistical diagnostics;
- all secondary plots.

---

# 16. Prioritized Work Plan

## Priority 0 — Submission blockers

Complete all of these:

- [ ] Obtain and analyze IEEE 2030.5-2023.
- [ ] Resolve local denylist, re-enrollment, session, and DERControl semantics.
- [ ] Determine how numeric authorization bounds are represented and enforced.
- [ ] Correct the copied-key versus attestation-detection model.
- [ ] Implement a compliant-baseline hosting-capacity sweep.
- [ ] Repeat authorization-shape experiments at compliant operating points.
- [ ] Add a stealth-constrained attacker.
- [ ] Add the corrected IEEE 123 feeder.
- [ ] Perform selected GridLAB-D cross-checks.
- [ ] Implement local-denylist baselines.
- [ ] Implement real session/command cleanup ablations.
- [ ] Reduce abstract to 250 words.
- [ ] Remove planned/future framing from the final article.

## Priority 1 — Strong system evidence

- [ ] Implement gateway proxy.
- [ ] Integrate a real IEEE 2030.5 endpoint.
- [ ] Implement TPM/TEE-backed attestation.
- [ ] Run networked outage and renewal-storm tests.
- [ ] Add stateful command cancellation.
- [ ] Add stateful protection or consistently call the outcome a threshold screen.
- [ ] Measure legitimate volt-var service and two-sided safety.

## Priority 2 — Generalization and quality

- [ ] Add mixed DER technology.
- [ ] Expand compromise-locus evaluation.
- [ ] Add heterogeneous synthetic authorization graphs.
- [ ] Add economic/availability metrics.
- [ ] Replace related-work table.
- [ ] Improve figures.
- [ ] Shorten main paper by approximately 25–35%.
- [ ] Move correction history to artifact documentation.

## Priority 3 — Final polish

- [ ] Check every claim against result files.
- [ ] Check every unit.
- [ ] Check every sample size.
- [ ] Check all figure/table references.
- [ ] Check bibliography and DOI metadata.
- [ ] Verify IJCIP formatting and declarations.
- [ ] Prepare cover letter.
- [ ] Run a final independent internal review.

---

# 17. Go/No-Go Criteria Before Submission

Do not submit until every “No-Go” item is resolved.

| Item | No-Go condition | Go condition |
|---|---|---|
| IEEE 2030.5-2023 | Unread/unverified | All load-bearing claims have exact clauses |
| Motivation | Claims no withdrawal mechanism despite denylist | Precisely distinguishes all containment layers |
| Authorization floor | Not known to be enforceable | Native or gateway enforcement demonstrated |
| Base case | Primary result relies on already noncompliant feeder | Primary result replicated at compliant states |
| Attacker | Only loud fixed attacker | Stealth and telemetry-limited attackers included |
| Feeder generality | One feeder | At least two corrected feeders |
| Solver validity | One solver only | Selected independent cross-check completed |
| Session/command | Unit-test-only | End-to-end ablation completed |
| Protocol | “2030.5-style” only | Real endpoint/proxy interoperability demonstrated |
| Attestation | Software-emulated only | Hardware-backed gateway result or claims narrowed |
| Statistics | Pilot medians | Confirmatory estimates with confidence intervals |
| Abstract | 466 words | ≤250 words |
| Manuscript style | Correction/rebuttal narrative | Clean archival presentation |
| Results status | Exploratory pilot | Properly registered confirmatory evaluation complete |

---

# 18. Final Reviewer Assessment After Planned Revision

The paper can become a strong IJCIP submission because it has:

- an important critical-infrastructure problem;
- a technically coherent system;
- a practical migration path;
- a distinctive authorization-shape result;
- a meaningful security–reliability tradeoff;
- and unusually strong artifact discipline.

The final acceptance case will depend on demonstrating that the result is not an artifact of:

- an overstressed feeder;
- one solver;
- a mismatched authorization-set comparison;
- a one-sided voltage metric;
- or an abstract policy that IEEE 2030.5 cannot enforce.

The strongest final framing is:

> **CONTAINDER is not a new certificate primitive. It is an end-to-end DER authority-containment architecture that binds short-lived operational identity to physically meaningful control sets and ensures that expiration actually terminates sessions and persistent control effects.**

After the mandatory standards, interoperability, compliant-state, stealth-attacker, mechanism-ablation, and multi-feeder experiments are complete, the manuscript should be ready for IJCIP submission.
