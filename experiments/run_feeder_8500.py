#!/usr/bin/env python3
"""Feeder-consequence sweep on the REAL IEEE 8500-node feeder (OpenDSS, real power flow).

Seeded rooftop-PV placement (paired across policies), malicious dispatch under legacy-full (B1)
vs CONTAINDER-narrowed (B5) authorization, across load operating states. Reports the
attack-INDUCED voltage-violation area dJ_V = J_V(attack) - J_V(base) at the same operating
state (the 8500 base has some native undervoltage, so induced harm is the honest metric).

Single solver (OpenDSS); GridLAB-D cross-check and constrained hardware remain. Usage:
  python3 experiments/run_feeder_8500.py [n_seeds]
"""
import json
import os
import random
import statistics
import sys
from pathlib import Path

import opendssdirect as dss

ROOT = Path(__file__).resolve().parent.parent
FEEDER = ROOT / "power" / "feeders" / "ieee8500"
RESULTS = ROOT / "experiments" / "results"

N_PV = 600
P_PV_KW = 12.0
STATES = {"light_load": 0.30, "normal": 1.00, "heavy_load": 1.50}
POLICIES = {"B1_full": (P_PV_KW, 0.3 * P_PV_KW), "B5_narrow": (0.0, 0.05 * P_PV_KW)}


def compile_base():
    dss.Command("Compile Master.dss")
    dss.Command("Set controlmode=static")
    dss.Command("Set maxcontroliter=100")
    dss.Command("Set maxiterations=100")


def load_buses():
    buses = []
    i = dss.Loads.First()
    while i:
        name = dss.Loads.Name()
        dss.Circuit.SetActiveElement("Load." + name)
        buses.append((dss.CktElement.BusNames()[0], dss.CktElement.NumPhases(), dss.Loads.kV()))
        i = dss.Loads.Next()
    return buses


def place_pv(buses, n, seed):
    rng = random.Random(seed)
    chosen = rng.sample(buses, min(n, len(buses)))
    names = []
    for j, (busfull, ph, kv) in enumerate(chosen):
        nm = f"pvatk_{j}"
        dss.Command(f"New Generator.{nm} bus1={busfull} phases={ph} kv={kv} kw=0 kvar=0 model=1")
        names.append(nm)
    return names


def dispatch(names, kw, kvar):
    for nm in names:
        dss.Command(f"Edit Generator.{nm} kw={kw} kvar={kvar}")


def jv():
    # This is an export/overvoltage attack, so the harm metric is the OVERVOLTAGE-violation
    # area (>=0). Reporting total two-sided area would credit the attack for raising the
    # feeder's native undervoltage nodes under heavy load, which is not the harm it targets.
    v = [x for x in dss.Circuit.AllBusMagPu() if x > 0.01]
    over_area = sum(max(0.0, x - 1.05) for x in v)
    return over_area, sum(1 for x in v if x > 1.05), round(max(v), 4)


def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    os.chdir(FEEDER)
    rows = []
    for seed in range(1000, 1000 + n_seeds):
        compile_base()
        names = place_pv(load_buses(), N_PV, seed)
        for sname, lm in STATES.items():
            dss.Command(f"Set LoadMult={lm}")
            dispatch(names, 0.0, 0.0)
            dss.Solution.Solve()
            base_area, _, base_vmax = jv()
            for pol, (kw, kvar) in POLICIES.items():
                dispatch(names, kw, kvar)
                dss.Solution.Solve()
                area, nover, vmax = jv()
                rows.append({"seed": seed, "state": sname, "policy": pol,
                             "dJ_V": round(area - base_area, 4), "J_V": round(area, 4),
                             "vmax": vmax, "n_over": nover, "conv": bool(dss.Solution.Converged())})

    # aggregate: median induced dJ_V per (state, policy) + paired B1-B5
    agg = {}
    for st in STATES:
        for pol in POLICIES:
            xs = [r["dJ_V"] for r in rows if r["state"] == st and r["policy"] == pol]
            agg[(st, pol)] = (round(statistics.median(xs), 4), round(min(xs), 4), round(max(xs), 4))

    print(f"== IEEE 8500-node feeder sweep, {n_seeds} seeds, real OpenDSS power flow ==")
    print(f"PV: {N_PV} units x {P_PV_KW} kW placed at seeded load buses (paired across policies)\n")
    print(f"{'state':12} {'policy':10} {'median dJ_V':>12} {'[min':>9} {'max]':>9}")
    for st in STATES:
        for pol in POLICIES:
            m, lo, hi = agg[(st, pol)]
            print(f"{st:12} {pol:10} {m:>12.3f} {lo:>9.3f} {hi:>9.3f}")
    print("\n(dJ_V = attack-induced OVERVOLTAGE-violation area vs base at same load; B5 narrows scope)")

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "feeder8500.json").write_text(json.dumps(
        {"rows": rows, "n_seeds": n_seeds, "n_pv": N_PV, "p_pv_kw": P_PV_KW,
         "note": "Real IEEE 8500-node feeder, OpenDSS single solver. GridLAB-D cross-check, "
                 "constrained hardware, and seasonal time series remain."}, indent=2))
    print(f"\nSaved -> experiments/results/feeder8500.json")


if __name__ == "__main__":
    main()
