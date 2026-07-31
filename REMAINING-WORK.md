# CONTAINDER — Remaining Work

**HEAD:** `311b9f7` · **Venue:** IJCIP (Elsevier) — Q2
**Manuscript:** `manuscripts/CONTAINDER/main_els.pdf` ← **this is the correct build**
**State:** Revision in flight. **The 20-seed re-run completed and strengthened the
paper** — the headline separation is real (2.1×, 20/20 seeds). Main remaining work
is rebuilding tables from the new data and rewriting §VII/§VIII around the finding.

---

## ✅ THE 20-SEED RE-RUN FINISHED — and it changes the story in your favour

`experiments/results/timeseries2.json` (453 KB, completed 2026-07-31 04:06,
`n_seeds: 20`, both load states). **The "B2 ties B5" problem is not what the data
says.** The tie was an artifact of conflating two different fallback scopes.

### The actual result

| State | Contrast | Ratio (95% CI) | Seeds favouring CONTAINDER |
|---|---|---|---|
| light_load | **B5 vs B2 @ IEEE 1547 scope** | **2.159** [2.131, 2.183] | **20 / 20** |
| normal | **B5 vs B2 @ IEEE 1547 scope** | **2.095** [2.019, 2.151] | **20 / 20** |
| light_load | B5b vs B2b @ 5% scope | 0.622 [0.455, 0.781] | 0 / 20 |
| normal | B5b vs B2b @ 5% scope | 0.083 [0.041, 0.131] | 0 / 20 |

**At the IEEE 1547 default scope CONTAINDER halves excess overvoltage area — 2.1×,
every one of 20 seeds, tight CIs. At an aggressively narrowed 5% scope the ACL
alone wins and CONTAINDER is unnecessary.**

### Why this is a better paper than the one you had

The finding is **scope-conditional, and the condition is the one that matters in
deployment.** IEEE 1547 is the default an operator actually gets; the 5% scope
requires the operator to already know how to narrow the ACL correctly. So the
honest headline is:

> CONTAINDER's benefit is large precisely where operators are today (1547
> default), and vanishes where they have already solved the problem by other
> means (hand-narrowed ACL). The mechanism is a substitute for expertise the
> operator may not have.

That is a real contribution with a clear deployment implication, it is fully
supported by 20 paired seeds, **and it is not a tie.** Rewrite §VII/§VIII around
this rather than around the reframing options I had drafted before the run landed.

**Report both arms.** The 5% loss is not a weakness to bury — it is what makes
the scope-conditionality credible and it pre-empts the obvious reviewer question.

### Backup before touching `experiments/`
```bash
cp -r experiments/results experiments/results.bak-$(date +%F)
```
Results are written in place; a re-run without a backup destroys this baseline.

---

## 1. ~~Known code defect~~ — FIXED by this run ✅

The `compile_base()` warm-start leak in `run_timeseries.py::run_one()`
(compiled once per seed rather than between policies) **is fixed in
`run_timeseries2.py`.** From the results file's own note:

> *"Every (state, seed, policy) arm is an independent compile of the IEEE 8500
> feeder with a fresh PV fleet and fresh regulator/capacitor state, fixing the
> warm-start leak in run_timeseries.py."*

Non-convergence handling is also sound: 24 solves flagged, 48 retried,
retry cap 2 with 4× control budget, **unsettled solves retained and flagged,
never dropped.** Say this in the paper — it is the kind of discipline reviewers
credit.

**Consequence:** any table still built from `timeseries.json` (Jul 20) is stale
and carries the leak. Rebuild every affected table from `timeseries2.json`.

## 3. Pre-registration date is inconsistent ⚠️
`experiments/PREREGISTRATION.md` claims **FROZEN 2026-07-18**, but the git anchor
it cites (`b65cd3b`) is dated **2026-07-30**. A reviewer who checks will read this
as a backdated pre-registration — the worst possible inference.

**Fix:** correct the document to state the true freeze date and the commit that
actually corresponds to it. If the freeze genuinely happened on the 18th, cite
the commit from that date. If it didn't, say so — an honestly-dated late
pre-registration is fine; a backdated one is misconduct-adjacent.

## 4. Text asserts infrastructure that was never built
- §VII asserts a HELICS/GridLAB-D co-simulation that **does not exist**
- §VIII-A claims a pre-registration **deposit** that never happened

Both are text-only fixes: cut the claims, or build the thing. Cutting is correct
unless you want the co-simulation for a later paper.

---

## What's solid — don't re-audit

Code runs, **18/18 tests pass**, OpenDSS reproduces to the digit, **zero
untraceable numbers**. The earlier fear that this project's results were unsound
was refuted. The problems above are framing and hygiene, not validity.

---

## PI-only

- [ ] Decide the framing (#1)
- [ ] OSF/Zenodo pre-registration deposit — deliberately **not** done autonomously
- [ ] Paywalled IEEE 2030.5-2023 certificate-management text (needs your access)
- [ ] RQ5-pivot ratification
- [ ] Re-verify live IJCIP author guidance

---

## Traps

- **`main_els.pdf` is correct, `main.pdf` is not.** IJCIP is Elsevier. TDSC and
  C&S are *reach* venues conditioned on the full empirical evaluation completing —
  that condition is not met, so don't build for them.
- ΔJ_V units: an earlier sweep mislabelled time-axis-free snapshots as
  `p.u.-node-min`. Check units are right per-figure, not globally.
- Back up `experiments/results/*.json` before any re-run. Said twice on purpose.
