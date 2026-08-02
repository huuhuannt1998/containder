# CONTAINDER — Confirmatory Evaluation Pre-Registration (v3)

**Supersedes** `PREREGISTRATION.md` (v2) for the confirmatory study. v2 remains in the artifact
as the record of what governed the exploratory pilot.

## 0. What this document proves, and what it does not

Stated first, because the previous version overstated it and the correction is load-bearing.

This document is committed to version control **before any confirmatory treatment arm is run.**
The ordering is therefore checkable in `git log`: the commit introducing this file precedes the
commit introducing `results/confirmatory_*.json`. That is a genuine ordering guarantee within
the repository, and it is stronger than v2's position, under which every pilot result predated
the repository itself.

It is still **not** an independent timestamp. The commit is authored by the same party who could
rewrite history, so it establishes ordering to a reader who trusts the repository, not to one who
does not. Converting it into an independent guarantee requires a deposit on OSF or Zenodo whose
timestamp is issued by a third party. **That deposit has not been made**; it is a PI action, and
until it is made this document claims repository-internal ordering only.

### What was seen before this document was frozen

Full disclosure, because it bears on which hypotheses below are genuinely blind.

1. **Calibration (§3) had been run.** Hosting-capacity characterisation under *legitimate*
   operation only. No treatment, no attacker, no policy contrast.
2. **Three exploratory probes had been run**, each at a single seed:
   - a comparison of the pilot harness's two "matched magnitude" primitives, which is what
     exposed Defect 1 in §1;
   - a check of whether a withdrawal-of-absorption attack moves the band at a compliant
     operating point on either feeder;
   - a 26-point scan of legitimate fleet reactive absorption against the harm from withdrawing
     it, across both feeders and four load multipliers.

   The second and third probes returned a near-zero effect at *every* compliant state on *both*
   feeders, and an effect growing with the reactive absorption the feeder was drawing once
   legitimate operation was already out of band. **Hypothesis H2 below was reformulated after
   seeing this and is not blind.** It is reported as a confirmatory test of an exploratory
   observation, which is weaker than a blind test, and the manuscript says so. The operating
   ladder in §3 was also chosen after these probes, to span the transition they revealed rather
   than to sit on one side of it. H1, H3, H4, H5 and H6 were fixed without a corresponding
   observation.

## 1. Harness corrections that motivated the re-run

The confirmatory study does not re-analyse the pilot data; it re-measures, because two defects in
the pilot harness invalidate the comparison the pilot's central claim rests on. Both are fixed in
`power/confirmatory.py` and both are checkable against the pilot harness that remains in the
artifact.

**Defect 1 — the two "matched magnitude" primitives were not matched.** The curve arm writes its
setpoint into an `XYCurve` read by an `InvControl` declared `RefReactivePower=VARMAX`, so its Y
axis is per unit of `kvarmax` (5.28 kvar). The setpoint arm multiplies by the apparent-power
rating (13.11 kVA). At the nominally identical point `q_high = -0.44` the curve arm delivers
**-2.15 kvar** per DER and the setpoint arm **-5.28 kvar**, a factor of 2.46. Every row-wise
comparison of the two columns in the pilot's reactive table compares two different physical
absorptions.

**Defect 2 — the legitimate counterfactual under-delivers volt-var.** The conformant Category B
characteristic absorbs 44% of nameplate at V4 = 1.08 p.u., i.e. 5.28 kvar, which against a
`VARMAX` reference of 5.28 kvar is `y = -1.0`. The pilot harness writes `y = -0.44` and absorbs
2.15 kvar. The baseline against which every induced quantity was differenced was a *degraded*
volt-var service; correcting it lowers the light-load legitimate overvoltage area from 57.1 to
46.1 p.u.-node at seed 1001.

Both are corrected by carrying every reactive quantity in **physical kvar per DER** and
converting at a single site (`Session.apply`). A third change is not a defect but a
methodological necessity: penetration is swept through **per-unit rating**, not fleet count,
because IEEE 123 has 91 load buses and saturates above that fleet size.

## 2. Endpoints

**Primary (declared, system-level).** Two-sided ANSI C84.1 Range A violation area

    J_band = sum_n [ max(0, V_n - 1.05) + max(0, 0.95 - V_n) ]

in per-unit nodes, and its paired induced form ΔJ_band = J_band(attack) − J_band(legitimate) at
the same seed, state and feeder. Two-sided because a one-sided overvoltage endpoint credits an
attack for lifting sagging nodes and cannot price the undervoltage that forced over-absorption
causes — which is exactly the quantity an absorption-floor authorization must be shown not to
incur.

**Secondary, attack-specific.** The one-sided overvoltage term, retained for continuity with the
pilot and reported alongside, never instead.

**Safety screen.** Count of nodes crossing the IEEE 1547-2018 Table 16 Category II overvoltage
thresholds. Reported as a **screen**, not a trip: the model has no persistence timer, no
disconnection and no post-disconnection state update. The word "trip" does not appear in the
confirmatory results.

**Service quality.** Reactive support deficit — the shortfall of realised reactive output against
what the conformant characteristic prescribes at each unit's *observed* terminal voltage, in kvar
and as a fraction of conformant demand. An authorization that contains the attack while
destroying volt-var support is not a usable authorization, and this is the endpoint that decides
it.

**Operational cost.** Regulator tap operations, capacitor switching operations, curtailed
active energy.

## 3. Operating tiers (calibration-derived)

Tiers are derived from `results/hosting_capacity.json` by a rule fixed here, not chosen after
seeing treatment outcomes.

Compliance criterion, declared before the calibration ran: legitimate operation adds no more than
**TAU = 0.10 p.u.-node** of overvoltage area above the same feeder's own zero-PV base case, in
every seed. The tolerance is relative because the IEEE 8500 base case is itself marginally out of
band with no PV present (9 of 8531 nodes above 1.05 p.u. at light load), so an absolute criterion
would report zero hosting capacity there for reasons unrelated to PV.

The calibration returned:

| Feeder | load multiplier | compliant penetration limit |
|---|---|---|
| IEEE 8500 | 0.30 / 0.50 / 0.75 / 1.00 | 0.20 / 0.50 / 0.50 / 0.60 |
| IEEE 123 | any tested | **> 12.0 (right-censored)** — no upper-band violation at any penetration tested |

A tier ladder defined as fractions of `L` is therefore not usable: on IEEE 123 `L` is censored at
the top of the grid, because that feeder is electrically stiff enough to hold the band at 1200%
penetration with the volt-var function still inside its deadband. The confirmatory ladder is
instead an **explicit penetration ladder per feeder, chosen to straddle each feeder's compliance
transition**, with the calibrated limit reported as a marker rather than used as a scale:

| Feeder | load multiplier | penetration ladder | compliant at |
|---|---|---|---|
| IEEE 8500 | 0.50 | 0.50, 1.00, 1.50, 2.00 | 0.50 |
| IEEE 123 | 1.00 | 2.00, 6.00, 10.00, 14.00 | 2.00, 6.00 |

**Primary claims are made at the compliant rungs** of each ladder. The non-compliant rungs are
the overstressed cases, and the pilot's 222%-penetration point is retained as a stress case that
is never the sole support for a claim.

### Amendment A1 (recorded before any shape result was seen)

The ladders above originally carried a fourth rung each — IEEE 8500 at 2.00 and IEEE 123 at
14.00 — and the attacker searched a 9-point grid. At those rungs the strong-injection admissible
points exhaust the retry ladder of §7 (500 → 1500 → 4500 control iterations, roughly 60 s per
arm), and the sweep projected about 4.5 hours. The top rung of each ladder was removed and the
grid reduced to 7 points.

The run was stopped and restarted under the amended design; **no result of the original run was
inspected**, and its partial output was discarded rather than merged. Both removed rungs sit well
beyond their feeder's compliance transition and support no primary claim; the 20-seed count and
the retry policy are unchanged. This paragraph is the record of the change.

### Amendment A2 (recorded **after** seeing the first shape results — a defect correction)

Unlike A1, this change was made with results in hand, and it is disclosed as such.

The IEEE 123 fleet was set to 91, which is exactly that feeder's load-bus count. `place_pv` draws
`rng.sample(buses, min(n, len(buses)))`, so at n = 91 every seed selects *the same 91 buses* and
merely permutes their order. All twenty IEEE 123 seeds were therefore the identical circuit: the
first run's IEEE 123 arms return **one distinct value across twenty seeds** at every rung
(standard deviation exactly 0), and their bootstrap intervals are degenerate — `[0.004, 0.004]`
and the like. The nominal n = 20 was an n = 1. IEEE 8500, whose fleet of 600 is drawn from 1177
load buses, shows genuine variation (20 distinct values per rung, standard deviations 1.9 to 99).

This is the same class of error the pilot made in its withdrawn ablations — reporting replication
where the harness produced none — and it is corrected the same way: the IEEE 123 fleet is reduced
to 46, half its load-bus population, so placement genuinely varies with the seed. **The IEEE 123
arms are re-run and the first run's IEEE 123 arms are discarded.** The IEEE 8500 arms are
unaffected by the fleet change and are retained.

No hypothesis, endpoint, ladder, set family, interpretation rule or seed count changed. The change
is confined to a sampling parameter that had silently disabled replication on one feeder, and the
inferences drawn from the discarded arms were void for that reason rather than unfavourable.

The ladder is the independent variable in place of a compliant/non-compliant dichotomy, because
the calibration showed the governing quantity to be continuous: how much reactive absorption the
fleet is actually delivering under the conformant characteristic. That quantity is reported for
every rung, since a feeder can sit at high penetration and still draw no volt-var support if its
voltages stay inside the curve's deadband — which is exactly what IEEE 123 does.

## 4. Authorization sets

An authorization is a **set**, not a setpoint; an adversary plays the worst admissible point in
it. All bounds are physical kvar per DER, positive = injection, `Qb` = Category B capability.

| Family | Definition | Contains zero absorption? |
|---|---|---|
| Q1(c) symmetric cap | q ∈ [−c, +c], c ∈ {Qb, 0.75Qb, 0.50Qb, 0.25Qb} | yes, at every width |
| Q2(φ) absorption floor | q ∈ [−Qb, −φ], φ ∈ {0.25Qb, 0.50Qb, 0.75Qb, Qb} | no |
| Q3(ε) curve tube | \|q(V) − q_ref(V)\| ≤ ε, ε ∈ {0.25Qb, 0.50Qb} | only if ε large |
| Q5 read-only | no remote reactive authority | n/a |

Each set is evaluated under **both** primitives — `setpoint` (`opModFixedVar` semantics) and
`curve` (`opModVoltVar` semantics) — receiving the identical physical bound. This is the matched
feasible-set comparison the pilot did not perform.

## 5. Attacker models

- **A1 oracle** — full feeder state; plays the admissible point maximising ΔJ_band.
- **A2 telemetry-limited** — sees only what the compromised identity is authorized to read;
  plays the extreme of the authorized set in the injection direction.
- **A3 stealth-constrained** — maximises ΔJ_band subject to crossing no screen threshold and
  keeping the count of out-of-band nodes at or below the legitimate baseline count.
- **A4 wear** — maximises regulator tap operations subject to the A3 stealth constraint.
- **A5 curtailment** — maximises curtailed active energy subject to the A3 stealth constraint.

The attacker searches its set on a fixed grid of 9 points declared in code before running.

## 6. Hypotheses

**H1 (shape, not width).** At a fixed operating tier, ΔJ_band under the worst admissible point of
a Q1 symmetric cap exceeds that under a Q2 absorption floor of the same *width*, and the Q1
excess does not diminish as the cap narrows. *Blind.*

**H2 (reliance conditionality).** The magnitude of the withdrawal-of-absorption effect is
governed by the reactive absorption the fleet delivers under the conformant characteristic, not
by penetration as such; it is not materially different from zero at every rung where legitimate
operation is compliant, on both feeders. *Not blind — reformulated after the probes described in
§0.* The confirmatory test is whether this survives 20 paired seeds, both primitives and all four
authorization families, which the probes did not examine.

**H3 (primitive versus feasible set).** At matched feasible sets, `setpoint` and `curve` do not
differ materially on the primary endpoint. *Blind.*

**H4 (lifetime truncation).** At fixed scope, integrated harm is linear in retained-authority
duration with a slope equal to the measured harm-accrual rate; the pre-expiry trajectory is
unchanged by lifetime. *Blind.*

**H5 (stealth interaction).** The advantage of bounded lifetime over detection-driven response is
larger for A3 than for A1, because A3's detection delay exceeds A1's. *Blind.*

**H6 (operational cost).** Containment increases regulator tap operations relative to an
uncontained compromise at the same scope. *Blind.*

## 7. Statistical analysis

**Experimental unit** is the complete paired scenario run — (feeder, tier, set, primitive,
attacker, seed) — never a node, a timestep or a command.

**Pairing.** Every contrast is paired on seed: the same seeded fleet placement is used for the
legitimate baseline and every treatment arm at that seed, and each arm is an independent compile
so no solver state leaks between arms.

**Estimates.** Median paired difference and ratio of geometric means, each with a
bias-corrected-accelerated bootstrap 95% CI at 10,000 resamples. Counts (screen crossings, tap
operations) additionally by paired sign test. No result is reported as a median alone.

**Seeds.** 20 paired seeds for every primary contrast; 10 for exploratory sweeps, labelled as
such.

**Multiplicity.** Holm correction within each hypothesis family (shape, primitive, lifetime,
attacker, cost) separately; the primary contrast is not pooled with exploratory analyses.

**Non-convergence.** Retry cap 2, control-iteration budget tripling 500 → 1500 → 4500. Unsettled
solves are **retained and flagged**, never dropped; every reported aggregate is accompanied by
its flagged count, and any contrast whose flagged runs fall disproportionately in one arm is
reported with and without them.

**Interpretation rule for H1, fixed here.** H1 is supported only if the Q1-minus-Q2 paired
difference in ΔJ_band is positive with a CI excluding zero **and** the Q2 arm's reactive support
deficit stays below 25% of conformant demand. An authorization that contains by destroying the
service does not count as containment.

### Amendment A3 (recorded after seeing results — analysis corrections and two additions)

Four changes were made once the confirmatory results were in hand. All are disclosed here and all
are visible in the manuscript.

1. **Holm correction was declared in §7 and had not been implemented.** It now is
   (`experiments/stats.py`), applied within the mechanism, response and lifetime families
   separately. Every contrast that was reported as significant survives it.

2. **The lifecycle contrasts were not paired.** §7 declares pairing, but the lifecycle analysis
   bootstrapped each arm's own median and reported the difference between them as a bare
   percentage. They are now paired per seed with bootstrap intervals, which is both the declared
   procedure and the more powerful one; the estimates move (S3 from −11.1% to −15.2%) because a
   median of differences is not a difference of medians.

3. **Arms whose paired differences are identically zero are no longer reported as measured
   nulls.** Three arms — credential expiry alone, command cleanup alone, and identity denial —
   reproduce the baseline exactly in all twenty seeds. That is a consequence of the reach the
   lifecycle model assigns each response, not a measurement, and the manuscript now says so and
   argues the reach assignment from the standards material instead.

4. **A second detector was added to the attacker analysis**, declared post-hoc: generation
   telemetry flagging any attack withholding more than 10% of available active power. The
   confirmatory analysis declared only a voltage detector, against which the curtailment attackers
   are invisible. Under the generation detector they are flagged in every seed, which materially
   weakens the stealth claim, and the manuscript reports the weakened form.

A **post-hoc resolution sweep** (`run_reliance_resolution.py`) adds four intermediate rungs per
feeder to the reliance curve. It evaluates one arm, tests no hypothesis, is excluded from every
confirmatory contrast, and is plotted with open markers.

## 8. What is out of scope for this study

Named so that absence is not read as omission: no constrained-hardware or TPM attestation
measurement; no third-party IEEE 2030.5 endpoint interoperability; no second power-flow solver;
no field deployment; and no clause-level analysis of IEEE 2030.5-2023, which could not be
obtained. §11 of the manuscript states which claims each absence bounds.
