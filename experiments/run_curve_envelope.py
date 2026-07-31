#!/usr/bin/env python3
"""M12: does a *bounded volt-var curve* authorization contain, where a bounded setpoint does not?

Why this experiment exists
--------------------------
``run_scope_envelope.py`` sweeps the authorized reactive envelope by calling
``feeder8500v2.dispatch()``, which unconditionally issues ``Edit InvControl.der1547 enabled=no``
before writing a fixed (P, Q). Every arm of that sweep therefore contains a *function
suppression* term -- the autonomous IEEE 1547 volt-var response is switched off -- that the
envelope parameter does not gate. At the q = 0 point the envelope authorizes no injection at
all and the entire measured harm is that suppression. A sweep in which no arm constrains the
dominant term cannot show that narrowing fails to contain: it is forced.

This script evaluates the authorization model the earlier one could not express. The volt-var
controller stays **enabled** throughout, the PV stays on its legitimate schedule, and the
adversary's authority is a bound on the *characteristic itself*: how far the reactive setpoint
at the top of the voltage range may be moved away from the conformant Category B value of
-0.44 p.u. (absorption). That is what an operator who narrows a volt-var authorization actually
grants, and unlike the setpoint envelope it is a bound the adversary cannot step outside.

Two arms are run at each point so the decomposition is visible:
  ``curve``    -- controller enabled, characteristic rewritten within the authorized band.
  ``override`` -- controller disabled and a fixed Q commanded, i.e. the model
                  ``run_scope_envelope.py`` uses, retained for comparison at equal |Q|.

Interpretation rule, fixed before running: if there exists a non-degenerate band of authorized
curve values over which dJ_V <= 0 and no seed trips, then a bounded *curve* authorization
contains and the manuscript's "no reactive envelope contains" claim is false as stated. If no
such band exists, the negative result is earned rather than assumed.

Usage: python3 experiments/run_curve_envelope.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from power import feeder8500v2 as f

N_PV = 600
STATES = {"light_load": 0.30, "normal": 1.00}

#: Reactive setpoint at the top of the voltage range, in p.u. of nameplate apparent power.
#: -0.44 is the conformant IEEE 1547-2018 Category B value (full absorption at high voltage).
#: Moving toward 0 withdraws the service; positive values inject into an already-high voltage.
Q_HIGH_V = [-0.44, -0.33, -0.22, -0.11, 0.0, 0.11, 0.22, 0.33, 0.44]


def arm_curve(seed: int, lm: float, q_high: float) -> dict:
    """Controller ENABLED; adversary rewrites the characteristic within its authorized band."""
    with f.Session(seed=seed, n_pv=N_PV, load_mult=lm) as s:
        f.dispatch_legitimate(s.names)
        f.solve()
        base = f.voltage_stats()
        base_pr = f.protection_state()
        base_taps = f.tap_positions()

        f.distort_voltvar_curve(q_high)
        f.solve()
        st, pr = f.voltage_stats(), f.protection_state()
        taps = f.count_tap_operations(base_taps, f.tap_positions())
    return {"dJ_V": round(st["area"] - base["area"], 4), "J_V": round(st["area"], 4),
            "base_J_V": round(base["area"], 4), "base_n_over": base["n_over"],
            "base_vmax": base["vmax"], "base_trip": base_pr["trip"],
            "n_over": st["n_over"], "vmax": st["vmax"], "trip": pr["trip"],
            "induced_trip": bool(pr["trip"] and not base_pr["trip"]), "tap_ops": taps}


def arm_override(seed: int, lm: float, q_high: float) -> dict:
    """Controller DISABLED and a fixed Q commanded -- the run_scope_envelope.py model."""
    kvar = q_high * f.KVA_PV
    with f.Session(seed=seed, n_pv=N_PV, load_mult=lm) as s:
        f.dispatch_legitimate(s.names)
        f.solve()
        base = f.voltage_stats()
        base_pr = f.protection_state()
        base_taps = f.tap_positions()

        f.dispatch(s.names, f.P_PV_KW, kvar)   # disables InvControl internally
        f.solve()
        st, pr = f.voltage_stats(), f.protection_state()
        taps = f.count_tap_operations(base_taps, f.tap_positions())
    return {"dJ_V": round(st["area"] - base["area"], 4), "J_V": round(st["area"], 4),
            "base_J_V": round(base["area"], 4), "base_n_over": base["n_over"],
            "base_vmax": base["vmax"], "base_trip": base_pr["trip"],
            "kvar_commanded": round(kvar, 4),
            "n_over": st["n_over"], "vmax": st["vmax"], "trip": pr["trip"],
            "induced_trip": bool(pr["trip"] and not base_pr["trip"]), "tap_ops": taps}


def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    seeds = list(range(1000, 1000 + n_seeds))
    f.chdir_feeder()

    rows = {}
    total = len(STATES) * len(Q_HIGH_V) * 2 * n_seeds
    i = 0
    for st, lm in STATES.items():
        for q in Q_HIGH_V:
            for mode, fn in (("curve", arm_curve), ("override", arm_override)):
                for sd in seeds:
                    rows[f"{st}|{mode}|{q}|{sd}"] = fn(sd, lm, q)
                    i += 1
                print(f"  .. {st} {mode} q_high={q} done ({i}/{total})", flush=True)

    agg = {}
    for st in STATES:
        for mode in ("curve", "override"):
            for q in Q_HIGH_V:
                xs = [rows[f"{st}|{mode}|{q}|{s}"]["dJ_V"] for s in seeds]
                tr = [rows[f"{st}|{mode}|{q}|{s}"]["trip"] for s in seeds]
                itr = [rows[f"{st}|{mode}|{q}|{s}"]["induced_trip"] for s in seeds]
                btr = [rows[f"{st}|{mode}|{q}|{s}"]["base_trip"] for s in seeds]
                bj = [rows[f"{st}|{mode}|{q}|{s}"]["base_J_V"] for s in seeds]
                bn = [rows[f"{st}|{mode}|{q}|{s}"]["base_n_over"] for s in seeds]
                agg[f"{st}|{mode}|{q}"] = {
                    "dJV_median": round(statistics.median(xs), 3),
                    "dJV_min": round(min(xs), 3), "dJV_max": round(max(xs), 3),
                    "trip_frac": round(sum(tr) / len(tr), 3),
                    "induced_trip_frac": round(sum(itr) / len(itr), 3),
                    "base_trip_frac": round(sum(btr) / len(btr), 3),
                    "base_JV_median": round(statistics.median(bj), 3),
                    "base_n_over_median": statistics.median(bn), "n": len(xs)}

    # Containment band: authorized curve values at which the attack does not raise overvoltage
    # area and induces no trip in any seed.
    bands = {}
    for st in STATES:
        for mode in ("curve", "override"):
            ok = [q for q in Q_HIGH_V
                  if agg[f"{st}|{mode}|{q}"]["dJV_median"] <= 0.0
                  and agg[f"{st}|{mode}|{q}"]["induced_trip_frac"] == 0.0]
            bands[f"{st}|{mode}"] = {"contained_q_high_values": ok,
                                     "contains_beyond_conformant_point": [q for q in ok
                                                                          if q != -0.44]}

    print("\n== bounded-curve vs setpoint-override authorization, IEEE 8500, "
          f"n={n_seeds} paired seeds ==")
    for st in STATES:
        for mode in ("curve", "override"):
            print(f"\n-- {st} / {mode} --   (base dJ_V reference: "
                  f"{agg[f'{st}|{mode}|0.0']['base_JV_median']:.1f} p.u.-node, "
                  f"{agg[f'{st}|{mode}|0.0']['base_n_over_median']:.0f} nodes over 1.05)")
            print(f"{'q_high':>7} {'dJV med':>9} {'min':>9} {'max':>9} {'trip':>6} {'induced':>8}")
            for q in Q_HIGH_V:
                A = agg[f"{st}|{mode}|{q}"]
                print(f"{q:>7.2f} {A['dJV_median']:>9.2f} {A['dJV_min']:>9.2f} "
                      f"{A['dJV_max']:>9.2f} {A['trip_frac']:>6.2f} "
                      f"{A['induced_trip_frac']:>8.2f}")
            print(f"   contained at: {bands[f'{st}|{mode}']['contained_q_high_values']}")

    out = {"agg": agg, "bands": bands, "rows": rows,
           "params": {"n_seeds": n_seeds, "n_pv": N_PV, "states": STATES,
                      "q_high_v_grid": Q_HIGH_V, "conformant_q_high_v": -f.Q_1547_FRAC,
                      "kva_pv": f.KVA_PV, "p_pv_kw": f.P_PV_KW,
                      "pv_capacity_mw": round(N_PV * f.P_PV_KW / 1000, 3)},
           "note": "Two authorization models at equal reactive magnitude. 'curve' leaves the "
                   "IEEE 1547 volt-var controller ENABLED and bounds how far the adversary may "
                   "move the characteristic's high-voltage reactive setpoint from the conformant "
                   "-0.44 p.u.; 'override' disables the controller and commands a fixed Q, which "
                   "is the model run_scope_envelope.py uses and in which the envelope cannot "
                   "gate the loss of the autonomous response. dJ_V is measured against "
                   "legitimate scheduled PV under the conformant Cat B curve at the same load "
                   "state. induced_trip counts only seeds where the base case did NOT already "
                   "trip, since the legitimate base at light load sits close to the OV1 screen."}
    (Path(__file__).resolve().parent / "results" / "curve_envelope.json").write_text(
        json.dumps(out, indent=2))
    print("\nSaved -> experiments/results/curve_envelope.json")


if __name__ == "__main__":
    main()
