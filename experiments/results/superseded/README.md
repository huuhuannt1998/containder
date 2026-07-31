# Superseded result files

Files here are retained for provenance and are **not** part of the released evidence base. They
are deliberately outside `experiments/results/`, which
`manuscripts/CONTAINDER/check_numbers.py` globs as the set of live artifacts: leaving a
superseded file in that directory lets a stale numeral in the manuscript match a number that no
longer corresponds to any current experiment, and the freeze gate returns a false PASS.

## `timeseries.json`

Superseded by `../timeseries2.json`. Three defects, all fixed in
`experiments/run_timeseries2.py`:

1. **Solver-state leak.** `run_timeseries.py::run_one()` called `compile_base()` once per seed
   and then iterated policies against the same live circuit. OpenDSS warm-starts each solution
   from the previous converged voltage vector and from the current regulator tap and capacitor
   switch positions, so every arm after the first inherited the previous arm's excursion.
2. **Non-conformant "narrow" envelope.** The narrow scope was 0.6 kvar, about 5% of a 12 kW
   unit's nameplate and 11% of the IEEE 1547-2018 Category B reactive range. It is physically
   inert on this feeder, so any lifecycle multiplied by it read as containment.
3. **n = 3, unpaired.** Contrasts were medians of independent integrals at three seeds, with no
   paired inference and a single operating state.

Numbers that appear only in this file and nowhere in the live results — notably the integrals
6956, 7030, 3196 and 3.8 — are stale and must not appear in the manuscript.

## `legitimate_utility.json`

Superseded and **contradicts the manuscript's central finding**, which is why it must not sit in
the live results directory. It records `S2_voltvar` as
`{legit_voltvar_authorized: true, malicious_export_authorized: false,
malicious_overvoltage_area: 0.042}` with the note "S2 (bounded volt-var) preserves legitimate
support control while denying export" — i.e. that a bounded volt-var scope both delivers the
service and contains. The manuscript's scope-envelope result says the opposite.

The apparent containment is an artifact of the superseded harness: it was produced with
`power/feeder8500.py` (`Generator` objects, no inverter, no volt-var curve) against a
counterfactual feeder carrying no DER, and its "bounded volt-var" scope is the same
non-conformant 0.6 kvar envelope that `results/scope_envelope.json` shows is physically inert.
It is cited nowhere in the manuscript.

## `feeder.json`

Early IEEE 13/123-bus scaffolding run, superseded by `../feeder123.json`. Cited nowhere.

## Files that remain live despite using the superseded harness

`feeder8500.json`, `full_sweep.json`, `attack_families.json`, `penetration.json` and
`feeder123.json` were also produced with `power/feeder8500.py` and the zero-DER counterfactual.
They stay in `results/` because the manuscript still reports numbers from them — the
legacy-baseline halves, which do not depend on the narrow-scope arm — and moving them would
break the traceability the freeze gate checks. Section VI names the two harnesses and states
which results come from which, and Section VIII attaches the provenance to each figure and
table that uses them.
