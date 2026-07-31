#!/usr/bin/env python3
"""M3: scope-envelope sweep on IEEE 8500 -- how narrow must authorization be before it contains?

The original evaluation fixed two envelopes by fiat -- legacy full ``(12.0 kW, 3.6 kvar)`` and
"narrow" ``(0.0 kW, 0.6 kvar)`` -- and reported the resulting collapse in violation area as if it
were an emergent property of scope narrowing. It is not: it is the arithmetic consequence of the
chosen pair. This script sweeps the authorized envelope continuously and locates the *breach
threshold*: the envelope at which an adversary confined to that scope first does net harm relative
to legitimate operation, and first drives a node past an IEEE 1547 overvoltage trip threshold.

Two axes are swept, because IEEE 2030.5 ``FunctionSetAssignments`` narrowing acts on the function
set, not on a scalar:

* **Active-power axis.** The adversary holds ``DERControl`` and commands ``sigma`` x nameplate
  active power with the legacy 0.3 power-factor-equivalent reactive component.
* **Reactive axis (volt-var scope).** The adversary is confined to the volt-var function set --
  the narrowest scope that still delivers the service CSIP volt-var programs procure. Active
  power stays at its *legitimate* schedule (the PV keeps generating; the adversary has no need to
  touch it) and only Q is manipulated, up to the IEEE 1547-2018 Category B capability of 44% of
  nameplate active power rating.

The reactive axis is the operationally binding one. IEEE 1547-2018 Cl. 5.2 requires Category B
DER to supply +/- 44% of nameplate; the manuscript's original "narrow" envelope of 0.6 kvar is
about 5% of a 12 kW unit's nameplate, i.e. roughly 11% of the mandated range, and therefore does
not deliver volt-var at all.

Usage: python3 experiments/run_scope_envelope.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from power import feeder8500v2 as f

N_PV = 600
STATES = {"light_load": 0.30, "normal": 1.00}
SIGMA_P = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
Q_KVAR = [0.0, 0.6, 1.2, 1.8, 2.4, 3.0, 3.6, 4.2, 4.8, 5.28]


def arm(seed, lm, kw, kvar, legit_p):
    """One fully isolated arm. Returns (dJ_V, stats, protection, tap_ops)."""
    with f.Session(seed=seed, n_pv=N_PV, load_mult=lm) as s:
        f.solve()
        base = f.voltage_stats()
        base_taps = f.tap_positions()
        p_cmd = f.P_PV_KW if legit_p else kw
        f.dispatch(s.names, p_cmd, kvar)
        f.solve()
        st = f.voltage_stats()
        pr = f.protection_state()
        taps = f.count_tap_operations(base_taps, f.tap_positions())
    return st["area"] - base["area"], st, pr, taps, base["area"]


def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    f.chdir_feeder()
    rows = []
    for seed in range(1000, 1000 + n_seeds):
        for st_name, lm in STATES.items():
            for sig in SIGMA_P:
                d, s_, pr, taps, b = arm(seed, lm, sig * f.P_PV_KW, 0.3 * sig * f.P_PV_KW, False)
                rows.append({"axis": "active", "seed": seed, "state": st_name, "sigma": sig,
                             "kw": round(sig * f.P_PV_KW, 3), "kvar": round(0.3 * sig * f.P_PV_KW, 3),
                             "dJ_V": round(d, 4), "J_V": round(s_["area"], 4), "base_J_V": round(b, 4),
                             "n_over": s_["n_over"], "vmax": s_["vmax"], "trip": pr["trip"],
                             "trip_class": pr["trip_class"], "tap_ops": taps})
            for q in Q_KVAR:
                d, s_, pr, taps, b = arm(seed, lm, 0.0, q, True)
                rows.append({"axis": "reactive", "seed": seed, "state": st_name,
                             "q_frac_nameplate": round(q / f.P_PV_KW, 4),
                             "q_frac_1547": round(q / f.Q_1547_KVAR, 4),
                             "kw": f.P_PV_KW, "kvar": q,
                             "dJ_V": round(d, 4), "J_V": round(s_["area"], 4), "base_J_V": round(b, 4),
                             "n_over": s_["n_over"], "vmax": s_["vmax"], "trip": pr["trip"],
                             "trip_class": pr["trip_class"], "tap_ops": taps})

    def med(axis, state, key, val):
        xs = [r["dJ_V"] for r in rows if r["axis"] == axis and r["state"] == state and r[key] == val]
        return statistics.median(xs) if xs else float("nan")

    def trip_rate(axis, state, key, val):
        xs = [r["trip"] for r in rows if r["axis"] == axis and r["state"] == state and r[key] == val]
        return sum(xs) / len(xs) if xs else float("nan")

    thresholds = {}
    for state in STATES:
        for axis, key, grid in (("active", "sigma", SIGMA_P), ("reactive", "kvar", Q_KVAR)):
            breach = next((v for v in grid if med(axis, state, key, v) > 0.0), None)
            triple = next((v for v in grid if trip_rate(axis, state, key, v) >= 0.5), None)
            thresholds[f"{axis}|{state}"] = {"breach_dJV_positive": breach, "breach_trip": triple}

    print(f"== M3 scope-envelope sweep, IEEE 8500, {n_seeds} paired seeds ==")
    print(f"   IEEE 1547-2018 Cat B reactive capability = {f.Q_1547_KVAR} kvar "
          f"({f.Q_1547_FRAC:.0%} of {f.P_PV_KW} kW nameplate); inverter {f.KVA_PV} kVA\n")
    for state in STATES:
        print(f"-- {state} : ACTIVE-POWER axis (adversary holds DERControl) --")
        print(f"{'sigma':>7} {'kW':>7} {'median dJ_V':>12} {'trip rate':>10} {'med taps':>9}")
        for v in SIGMA_P:
            tp = [r["tap_ops"] for r in rows if r["axis"] == "active" and r["state"] == state and r["sigma"] == v]
            print(f"{v:>7.2f} {v * f.P_PV_KW:>7.2f} {med('active', state, 'sigma', v):>12.3f} "
                  f"{trip_rate('active', state, 'sigma', v):>10.2f} {statistics.median(tp):>9.1f}")
        print(f"-- {state} : REACTIVE axis (volt-var scope; legitimate P retained) --")
        print(f"{'kvar':>7} {'/1547':>7} {'median dJ_V':>12} {'trip rate':>10} {'med taps':>9}")
        for v in Q_KVAR:
            tp = [r["tap_ops"] for r in rows if r["axis"] == "reactive" and r["state"] == state and r["kvar"] == v]
            print(f"{v:>7.2f} {v / f.Q_1547_KVAR:>7.2f} {med('reactive', state, 'kvar', v):>12.3f} "
                  f"{trip_rate('reactive', state, 'kvar', v):>10.2f} {statistics.median(tp):>9.1f}")
        print()
    print("breach thresholds (first grid point with median dJ_V>0 / trip rate>=0.5):")
    for k, v in thresholds.items():
        print(f"   {k:22} {v}")

    out = {"rows": rows, "n_seeds": n_seeds, "n_pv": N_PV,
           "q_1547_kvar": f.Q_1547_KVAR, "q_1547_frac": f.Q_1547_FRAC,
           "p_pv_kw": f.P_PV_KW, "kva_pv": f.KVA_PV,
           "legacy_narrow_kvar": 0.05 * f.P_PV_KW,
           "legacy_narrow_frac_of_1547": round(0.05 * f.P_PV_KW / f.Q_1547_KVAR, 4),
           "thresholds": thresholds,
           "note": "Scope-envelope sweep with PVSystem+InvControl (IEEE 1547-2018 Cat B volt-var) "
                   "and a legitimate-PV counterfactual. dJ_V is measured against legitimate "
                   "scheduled operation, not against a zero-DER feeder."}
    (Path(__file__).resolve().parent / "results" / "scope_envelope.json").write_text(
        json.dumps(out, indent=2))
    print("\nSaved -> experiments/results/scope_envelope.json")


if __name__ == "__main__":
    main()
