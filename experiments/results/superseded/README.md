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
