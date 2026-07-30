#!/usr/bin/env python3
"""PV-penetration sweep on real IEEE 8500: induced overvoltage vs penetration, B1 vs B5.

One compile per seed; penetration level activates the first n of a fixed PV set. Light load.
Usage: python3 experiments/run_penetration.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from power import feeder8500 as f

P = 12.0
N_MAX = 1000
LEVELS = [0.2, 0.5, 0.8, 1.0]
STATE_LM = 0.30
FULL = (P, 0.3 * P)      # B1 authorization envelope
NARROW = (0.0, 0.05 * P)  # B5 authorization envelope


def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    f.chdir_feeder()
    acc = {lv: {"B1_full": [], "B5_narrow": []} for lv in LEVELS}
    for seed in range(1000, 1000 + n_seeds):
        f.compile_base()
        names = f.place_pv(f.load_buses(), N_MAX, seed)
        f.set_load_mult(STATE_LM)
        f.dispatch(names, 0.0, 0.0); f.solve(); base = f.overvoltage_area()
        for lv in LEVELS:
            n = int(lv * len(names))
            active, off = names[:n], names[n:]
            for pol, env in (("B1_full", FULL), ("B5_narrow", NARROW)):
                f.dispatch(active, *env)
                f.dispatch(off, 0.0, 0.0)
                f.solve()
                acc[lv][pol].append(max(0.0, f.overvoltage_area() - base))
    out = {"levels": LEVELS, "n_seeds": n_seeds,
           "B1_full": [round(statistics.median(acc[lv]["B1_full"]), 3) for lv in LEVELS],
           "B5_narrow": [round(statistics.median(acc[lv]["B5_narrow"]), 3) for lv in LEVELS]}
    print("== IEEE 8500 penetration sweep (induced overvoltage area, light load) ==")
    print(f"{'penetration':12} {'B1_full':>10} {'B5_narrow':>10}")
    for i, lv in enumerate(LEVELS):
        print(f"{int(lv*100):>10}% {out['B1_full'][i]:>10.2f} {out['B5_narrow'][i]:>10.3f}")
    (Path(__file__).resolve().parent / "results" / "penetration.json").write_text(json.dumps(out, indent=2))
    print("\nSaved -> experiments/results/penetration.json")


if __name__ == "__main__":
    main()
