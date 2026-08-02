#!/usr/bin/env python3
"""Paired contrasts for the lifecycle experiment, with Holm correction within families.

Supersedes the marginal per-arm intervals in ``run_lifecycle_physical.py``'s own summary, which
bootstrapped each arm's median separately and reported the difference between them as a bare
percentage. Every contrast here is the paired difference against the long-lived baseline at the
same seed, which is both the declared procedure and the more powerful one.

Two hypothesis families are corrected separately, as pre-registered: the mechanism ablation
(S0-S3) and the response ladder (denial and its extensions).

**Arms whose paired differences are identically zero are reported as identical, not as null
results.** An arm that reproduces its baseline in every seed to machine precision has not been
measured to have no effect; it has executed the same trajectory. The distinction matters here
because three arms are in that position, and the manuscript's claim about them is an argument
about unspecified protocol semantics rather than a measurement.

Usage: python3 experiments/analyze_lifecycle.py
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments.stats import paired_contrast, holm

RES = Path(__file__).resolve().parent / "results"
OUT = RES / "lifecycle_contrasts.json"

MECHANISM = ["mech_S0", "mech_S1", "mech_S2", "mech_S3"]
RESPONSE = ["deny_denylist_d5", "deny_denylist+session_d5",
            "deny_denylist+session+cancel_d5",
            "deny_denylist_d15", "deny_denylist+session_d15",
            "deny_denylist+session+cancel_d15"]
LIFETIME = ["ttl_5", "ttl_10", "ttl_15", "ttl_25", "ttl_40", "ttl_55"]


def main():
    src = RES / "lifecycle_physical.json"
    if not src.exists():
        sys.exit(f"missing {src}")
    d = json.loads(src.read_text())
    rows = [r for r in d["rows"] if "error" not in r]
    report = {"source": src.name, "families": {}}

    for state in sorted({r["state"] for r in rows}):
        g = sorted([r for r in rows if r["state"] == state], key=lambda r: r["seed"])
        base = [r["arms"]["legacy"]["integral_dJ_band"] for r in g]
        fam = {}
        for name, arms in (("mechanism", MECHANISM), ("response", RESPONSE),
                           ("lifetime", LIFETIME)):
            recs = []
            for a in arms:
                if a not in g[0]["arms"]:
                    continue
                treat = [r["arms"][a]["integral_dJ_band"] for r in g]
                c = paired_contrast(treat, base, label=a)
                first = g[0]["arms"][a]
                c.update({"T_cred_min": first["T_cred_min"],
                          "T_sess_min": first["T_sess_min"],
                          "T_cmd_min": first["T_cmd_min"],
                          "n_commands_accepted": first["n_commands_accepted"],
                          "median_tap_ops": statistics.median(
                              [r["arms"][a]["tap_ops"] for r in g]),
                          "frac_recovered": round(sum(
                              1 for r in g if r["arms"][a]["recovered"]) / len(g), 3)})
                recs.append(c)
            holm(recs)
            fam[name] = recs
        report["families"][state] = fam

    OUT.write_text(json.dumps(report, indent=2))
    print(f"wrote {OUT}\n")

    for state, fam in report["families"].items():
        print(f"=== {state}")
        for name, recs in fam.items():
            print(f"  -- {name} family (Holm within family, m = "
                  f"{sum(1 for r in recs if not r['identical_to_base'])})")
            for r in recs:
                if r["identical_to_base"]:
                    print(f"    {r['label']:<32} IDENTICAL to baseline in all "
                          f"{r['n']} seeds (not a measured null)")
                else:
                    print("    %-32s %+9.2f [%9.2f,%9.2f]  %+7.1f%% [%+6.1f,%+6.1f]  "
                          "p=%.2g holm=%.2g %s  %2d/%d" %
                          (r["label"], r["median_paired_diff"], r["ci_lo"], r["ci_hi"],
                           r["median_rel_pct"], r["rel_ci_lo"], r["rel_ci_hi"],
                           r["p_sign"], r["p_holm"],
                           "*" if r["significant_holm"] else " ",
                           r["n_favouring_treat"], r["n"]))
        print()


if __name__ == "__main__":
    main()
