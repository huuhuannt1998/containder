#!/usr/bin/env python3
"""Turn ``results/authz_shape.json`` into the declared contrasts, paired by seed.

Every contrast here is one of the pre-registered hypotheses, and every estimate carries a
bias-corrected percentile bootstrap CI at 10,000 resamples over the paired per-seed differences.
No contrast is reported as a median alone.

* **H1 shape, not width.** The exact matched-width pair is Q1 at ``c = 0.25 Qb`` (width
  ``0.50 Qb``) against Q2 at ``phi = 0.50 Qb`` (width ``0.50 Qb``). Both authorize a reactive
  interval of identical width; only one of them contains zero absorption. The secondary reading
  is the whole width profile: if shape rather than width is what contains, Q1's harm should not
  fall as its cap narrows, while Q2's should fall as its floor rises.
* **H2 reliance conditionality.** Harm against penetration and against the reactive absorption
  the fleet actually delivers under the conformant characteristic.
* **H3 primitive versus feasible set.** ``setpoint`` against ``curve`` at an identical bound.

**The pre-registered interpretation rule for H1 could not be applied as written, and the
substitution is disclosed here rather than made silently.** The rule required the Q2 arm's
reactive support deficit to stay below 25% of conformant demand. That threshold presumes the
metric reads near zero when the authorization is doing no harm, and it does not: the *legitimate,
unattacked* arm itself scores 0.53 to 0.999 across the ladder. The offset is a property of the
measurement, not of any authorization -- the reference reactive output is evaluated at a
per-unit voltage computed from the bus base, while the ``InvControl`` tracks its own rated-voltage
reference under damped iteration, so realised and prescribed output differ even under perfectly
legitimate operation.

The rule is therefore evaluated on the **excess over the paired legitimate arm at the same seed**,
``deficit_frac(attack) - deficit_frac(legitimate)``, with the 25-point threshold carried over. Two
things make the differential form trustworthy where the absolute form is not. The Q5 read-only
arm, which grants no remote reactive authority at all and must by construction cost nothing,
reads ``+0.001`` -- a null control the absolute metric could not have provided. And the ordering
across families is monotone in how much of the conformant characteristic each set gives away.

Usage: python3 experiments/analyze_shape.py
"""
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments.stats import boot_ci, sign_test_p, holm

RES = Path(__file__).resolve().parent / "results"
OUT = RES / "shape_contrasts.json"

DEFICIT_LIMIT = 0.25


def index(rows):
    """(feeder, penetration, set_label, primitive, seed) -> arm."""
    ix = {}
    for r in rows:
        if "error" in r:
            continue
        ix[(r["feeder"], r["penetration"], r["set_label"], r["primitive"], r["seed"])] = r
    return ix


def paired(ix, feeder, pen, prim, label_a, label_b, field=lambda r: r["worst"]["dJ_band"]):
    seeds = sorted({k[4] for k in ix
                    if k[0] == feeder and k[1] == pen and k[3] == prim and k[2] == label_a})
    out = []
    for s in seeds:
        a = ix.get((feeder, pen, label_a, prim, s))
        b = ix.get((feeder, pen, label_b, prim, s))
        if a and b:
            out.append((s, field(a), field(b)))
    return out


def main():
    src = RES / "authz_shape.json"
    if not src.exists():
        sys.exit(f"missing {src}")
    data = json.loads(src.read_text())
    rows = data["rows"]
    ix = index(rows)
    feeders = sorted({r["feeder"] for r in rows if "error" not in r})

    report = {"source": str(src.name), "deficit_limit": DEFICIT_LIMIT,
              "h1_matched_width": [], "h1_width_profile": [], "h2_reliance": [],
              "h3_primitive": []}

    Q1_NARROW = "Q1 cap |q|<=0.25Qb"
    Q2_MATCH = "Q2 floor q<=-0.50Qb"

    # ---- H1: matched-width Q1 vs Q2 ---------------------------------------------------------
    for f in feeders:
        for pen in sorted({r["penetration"] for r in rows
                           if "error" not in r and r["feeder"] == f}):
            for prim in ("setpoint", "curve"):
                pr = paired(ix, f, pen, prim, Q1_NARROW, Q2_MATCH)
                if len(pr) < 3:
                    continue
                diffs = [a - b for _, a, b in pr]
                q2rows = [ix[(f, pen, Q2_MATCH, prim, s)] for s, _, _ in pr]
                q2def = [r["worst"]["deficit_frac"] - r["base_deficit_frac"] for r in q2rows]
                q2abs = [r["worst"]["deficit_frac"] for r in q2rows]
                lo, hi = boot_ci(diffs)
                med_def = statistics.median(q2def)
                report["h1_matched_width"].append({
                    "feeder": f, "penetration": pen, "primitive": prim, "n": len(pr),
                    "set_a": Q1_NARROW, "set_b": Q2_MATCH,
                    "median_a": round(statistics.median([a for _, a, _ in pr]), 4),
                    "median_b": round(statistics.median([b for _, _, b in pr]), 4),
                    "median_paired_diff": round(statistics.median(diffs), 4),
                    "ci_lo": lo, "ci_hi": hi,
                    "sign_test_p": round(sign_test_p(diffs), 6),
                    "n_favouring_a": sum(1 for d in diffs if d > 0),
                    "q2_median_excess_deficit": round(med_def, 4),
                    "q2_median_absolute_deficit": round(statistics.median(q2abs), 4),
                    "legit_median_deficit": round(statistics.median(
                        [r["base_deficit_frac"] for r in q2rows]), 4),
                    "ci_excludes_zero": bool(lo is not None and lo > 0),
                    "h1_supported": bool(lo is not None and lo > 0
                                         and med_def < DEFICIT_LIMIT),
                })

    # ---- H1 secondary: does harm fall as each family narrows? -------------------------------
    for f in feeders:
        for pen in sorted({r["penetration"] for r in rows
                           if "error" not in r and r["feeder"] == f}):
            for prim in ("setpoint", "curve"):
                for fam in ("Q1", "Q2", "Q3"):
                    sub = [r for r in rows if "error" not in r and r["feeder"] == f
                           and r["penetration"] == pen and r["primitive"] == prim
                           and r["family"] == fam]
                    if not sub:
                        continue
                    by_w = {}
                    for r in sub:
                        by_w.setdefault(r["width_kvar"], []).append(r)
                    for w in sorted(by_w):
                        g = by_w[w]
                        dj = [x["worst"]["dJ_band"] for x in g]
                        lo, hi = boot_ci(dj)
                        report["h1_width_profile"].append({
                            "feeder": f, "penetration": pen, "primitive": prim, "family": fam,
                            "set_label": g[0]["set_label"], "width_kvar": w, "n": len(g),
                            "median_dJ_band": round(statistics.median(dj), 4),
                            "ci_lo": lo, "ci_hi": hi,
                            "median_argmax_q_frac_qb": round(statistics.median(
                                [x["argmax_q_frac_qb"] for x in g]), 4),
                            "frac_induced_screen": round(sum(
                                1 for x in g if x["worst"]["induced_screen"]) / len(g), 3),
                            "median_deficit_frac": round(statistics.median(
                                [x["worst"]["deficit_frac"] for x in g]), 4),
                            "median_excess_deficit": round(statistics.median(
                                [x["worst"]["deficit_frac"] - x["base_deficit_frac"]
                                 for x in g]), 4),
                        })

    # ---- H2: harm against penetration and against legitimate absorption ---------------------
    for f in feeders:
        for pen in sorted({r["penetration"] for r in rows
                           if "error" not in r and r["feeder"] == f}):
            sub = [r for r in rows if "error" not in r and r["feeder"] == f
                   and r["penetration"] == pen and r["family"] == "Q1"
                   and r["set_label"] == "Q1 cap |q|<=1.00Qb" and r["primitive"] == "curve"]
            if not sub:
                continue
            dj = [x["worst"]["dJ_band"] for x in sub]
            lo, hi = boot_ci(dj)
            # Legitimate fleet absorption at this rung: read from the conformant grid point of
            # the Q5 read-only arm, whose single admissible point is the conformant curve.
            q5 = [r for r in rows if "error" not in r and r["feeder"] == f
                  and r["penetration"] == pen and r["family"] == "Q5"]
            qfleet = statistics.median(
                [x["points"][0]["q_fleet_kvar"] for x in q5]) if q5 else None
            report["h2_reliance"].append({
                "feeder": f, "penetration": pen, "n": len(sub),
                "median_base_j_band": round(statistics.median(
                    [x["base_j_band"] for x in sub]), 4),
                "median_base_area_over": round(statistics.median(
                    [x["base_area_over"] for x in sub]), 4),
                "legit_compliant": bool(statistics.median(
                    [x["base_area_over"] for x in sub]) <= 0.10),
                "legit_q_fleet_kvar": round(qfleet, 2) if qfleet is not None else None,
                "median_dJ_band_widest_Q1": round(statistics.median(dj), 4),
                "ci_lo": lo, "ci_hi": hi,
                "frac_induced_screen": round(sum(
                    1 for x in sub if x["worst"]["induced_screen"]) / len(sub), 3),
            })

    # ---- H3: setpoint vs curve at an identical bound ----------------------------------------
    for f in feeders:
        for pen in sorted({r["penetration"] for r in rows
                           if "error" not in r and r["feeder"] == f}):
            for label in sorted({r["set_label"] for r in rows
                                 if "error" not in r and r["family"] in ("Q1", "Q2")}):
                seeds = sorted({k[4] for k in ix
                                if k[0] == f and k[1] == pen and k[2] == label})
                pr = []
                for s in seeds:
                    a = ix.get((f, pen, label, "setpoint", s))
                    b = ix.get((f, pen, label, "curve", s))
                    if a and b:
                        pr.append((a["worst"]["dJ_band"], b["worst"]["dJ_band"]))
                if len(pr) < 3:
                    continue
                diffs = [a - b for a, b in pr]
                lo, hi = boot_ci(diffs)
                report["h3_primitive"].append({
                    "feeder": f, "penetration": pen, "set_label": label, "n": len(pr),
                    "sign_test_p": round(sign_test_p(diffs), 6),
                    "identical_to_base": all(d == 0.0 for d in diffs),
                    "median_setpoint": round(statistics.median([a for a, _ in pr]), 4),
                    "median_curve": round(statistics.median([b for _, b in pr]), 4),
                    "median_paired_diff": round(statistics.median(diffs), 4),
                    "ci_lo": lo, "ci_hi": hi,
                    "ci_excludes_zero": bool(lo is not None and hi is not None
                                             and (lo > 0 or hi < 0)),
                })

    # Holm within each declared family, matching the methodology. H2 is descriptive (no test).
    holm(report["h1_matched_width"], key="sign_test_p")
    holm(report["h3_primitive"], key="sign_test_p")

    OUT.write_text(json.dumps(report, indent=2))
    print(f"wrote {OUT}\n")

    print("== H2: does the effect track compliance and reliance? (widest Q1, curve) ==")
    print("%-9s %6s %9s %9s %8s %12s %10s %8s" %
          ("feeder", "pen", "baseJband", "baseOver", "compl", "legitQ_kvar", "medDJ", "screen"))
    for r in report["h2_reliance"]:
        print("%-9s %6.2f %9.3f %9.3f %8s %12s %10.3f %8.2f" %
              (r["feeder"], r["penetration"], r["median_base_j_band"],
               r["median_base_area_over"], r["legit_compliant"],
               r["legit_q_fleet_kvar"], r["median_dJ_band_widest_Q1"],
               r["frac_induced_screen"]))

    print("\n== H1: matched-width Q1 (contains zero) vs Q2 (absorption floor) ==")
    print("%-9s %6s %-9s %3s %9s %9s %10s %-18s %7s %6s" %
          ("feeder", "pen", "primitive", "n", "medQ1", "medQ2", "medDiff", "95% CI",
           "Q2xsDef", "supp"))
    for r in report["h1_matched_width"]:
        print("%-9s %6.2f %-9s %3d %9.3f %9.3f %10.3f [%7.3f,%7.3f] %7.3f %6s" %
              (r["feeder"], r["penetration"], r["primitive"], r["n"], r["median_a"],
               r["median_b"], r["median_paired_diff"], r["ci_lo"], r["ci_hi"],
               r["q2_median_excess_deficit"], r["h1_supported"]))

    print("\n== H3: setpoint minus curve at an identical bound ==")
    sig = [r for r in report["h3_primitive"] if r["ci_excludes_zero"]]
    print(f"{len(sig)} of {len(report['h3_primitive'])} matched sets show a CI excluding zero")
    for r in report["h3_primitive"][:12]:
        print("  %-9s pen=%5.2f %-22s n=%2d set=%8.3f curve=%8.3f diff=%8.3f [%.3f,%.3f]%s" %
              (r["feeder"], r["penetration"], r["set_label"], r["n"], r["median_setpoint"],
               r["median_curve"], r["median_paired_diff"], r["ci_lo"], r["ci_hi"],
               "  *" if r["ci_excludes_zero"] else ""))


if __name__ == "__main__":
    main()
