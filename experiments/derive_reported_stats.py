#!/usr/bin/env python3
"""Recompute every derived statistic quoted in the manuscript, from the primary result files.

The freeze gate (``manuscripts/CONTAINDER/check_numbers.py``) matches each numeral in the
manuscript against literals present in ``experiments/results/*.json``. Medians, maxima and
spreads computed *across* seeds are legitimately reported in the text but are not stored by the
primary runners, so they would fail that gate even though they are fully reproducible. Rather
than whitelist them -- which would silence the gate -- this script recomputes each one from the
released primary files and writes ``results/derived_reported.json``, so every derived numeral has
a named, re-runnable origin.

Each key is named for the sentence it supports. Nothing here is a new measurement.

Usage: python3 experiments/derive_reported_stats.py
"""
import json
import statistics
import sys
from pathlib import Path

RES = Path(__file__).resolve().parent / "results"


def load(name):
    return json.loads((RES / name).read_text())


def main():
    out = {"_note": "Derived statistics quoted in the manuscript, recomputed from the primary "
                    "result files in this directory. Regenerate with "
                    "experiments/derive_reported_stats.py. No new measurement is performed here.",
           "_sources": {}}

    # ---- IEEE 8500 snapshot sweep: how loud the attack is (Sec. VIII, 'this attack is loud') ---
    f8500 = load("feeder8500.json")
    rows = [r for r in f8500["rows"] if r["state"] == "light_load" and r["policy"] == "B1_full"]
    nov = [r["n_over"] for r in rows]
    vmx = [r["vmax"] for r in rows]
    out["attack_loudness_light_load_B1"] = {
        "n_seeds": len(rows),
        "n_over_median": statistics.median(nov),
        "n_over_min": min(nov), "n_over_max": max(nov),
        "n_over_median_pct_of_8531": round(100 * statistics.median(nov) / 8531, 1),
        "vmax_median": round(statistics.median(vmx), 4), "vmax_max": round(max(vmx), 4)}
    out["_sources"]["attack_loudness_light_load_B1"] = "feeder8500.json rows"

    # ---- corrected time series: accrual rate, ratio ceiling, recovery, tap cost ---------------
    ts = load("timeseries2.json")
    P, R = ts["params"], ts["runs"]
    TA, TTL, H, n = P["t_attack"], P["ttl"], P["horizon"], P["n_seeds"]
    seeds = range(1000, 1000 + n)

    def excess(st, seed, pol):
        r = R[f"{st}|{seed}|{pol}"]
        b = r["baseline_area"]
        return [max(0.0, v - b) for v in r["series"]]

    ARMS = {"q44_conformant": ("B2_acl_narrow_1547", "B5_containder_1547"),
            "q30_partial": ("B1_legacy_full", "A4_full_lifecycle"),
            "q5_inert": ("B2b_acl_narrow_5pct", "B5b_containder_5pct")}

    ts_out = {"exposure_window_min": H - TA, "ttl_min": TTL,
              "arithmetic_ratio_ceiling": round((H - TA) / TTL, 4)}
    for st in P["states"]:
        for label, (legacy, lifecycle) in ARMS.items():
            rate_l = [statistics.mean(excess(st, s, lifecycle)[TA:TA + TTL]) for s in seeds]
            rate_g = [statistics.mean(excess(st, s, legacy)[TA:TA + TTL]) for s in seeds]
            ratios = [sum(excess(st, s, legacy)) / sum(excess(st, s, lifecycle))
                      for s in seeds if sum(excess(st, s, lifecycle)) > 1e-9]
            tails = [sum(excess(st, s, lifecycle)[TA + TTL:]) for s in seeds]
            ints = [sum(excess(st, s, lifecycle)) for s in seeds]
            settled = [statistics.median(excess(st, s, lifecycle)[TA + TTL + 2:]) for s in seeds]
            rec = [R[f"{st}|{s}|{lifecycle}"]["recovery_min"] for s in seeds]
            got = [x for x in rec if x is not None]
            ts_out[f"{st}|{label}"] = {
                "accrual_rate_mean": round(statistics.mean(rate_l), 4),
                "accrual_rate_sd": round(statistics.pstdev(rate_l), 4),
                "accrual_rate_max_abs_diff_lifecycle_vs_legacy":
                    round(max(abs(a - b) for a, b in zip(rate_l, rate_g)), 12),
                "integral_ratio_mean": round(statistics.mean(ratios), 4) if ratios else None,
                "integral_ratio_max": round(max(ratios), 4) if ratios else None,
                "post_expiry_tail_pct_of_integral":
                    round(100 * statistics.mean(tails) / statistics.mean(ints), 2)
                    if statistics.mean(ints) > 1e-9 else None,
                "settled_post_expiry_excess_median": round(statistics.median(settled), 4),
                "n_recovered_by_criterion": len(got), "n_seeds": n,
                "recovery_min_median": statistics.median(got) if got else None,
                "tap_ops_median_legacy": ts["agg"][f"{st}|{legacy}"]["tap_ops_median"],
                "tap_ops_median_lifecycle": ts["agg"][f"{st}|{lifecycle}"]["tap_ops_median"],
                "tap_ops_increase_pct": round(
                    100 * (ts["agg"][f"{st}|{lifecycle}"]["tap_ops_median"]
                           / ts["agg"][f"{st}|{legacy}"]["tap_ops_median"] - 1), 1)}
    # cross-envelope accrual-rate contrast quoted in the text
    r44 = ts_out["light_load|q44_conformant"]["accrual_rate_mean"]
    r30 = ts_out["light_load|q30_partial"]["accrual_rate_mean"]
    ts_out["light_load_accrual_rate_ratio_q44_over_q30"] = round(r44 / r30, 4)
    ts_out["light_load_accrual_rate_pct_higher_q44_vs_q30"] = round(100 * (r44 / r30 - 1), 1)
    out["timeseries_derived"] = ts_out
    out["_sources"]["timeseries_derived"] = "timeseries2.json runs + agg"

    # ---- arm-identity audit: which labelled arms are the same arm ----------------------------
    import hashlib
    ident = {}
    for st in P["states"]:
        sig = {}
        for pol in ts["agg"]:
            if not pol.startswith(st + "|"):
                continue
            name = pol.split("|", 1)[1]
            h = hashlib.sha256(json.dumps(
                [R[f"{st}|{s}|{name}"]["series"] for s in seeds]).encode()).hexdigest()[:16]
            sig.setdefault(h, []).append(name)
        ident[st] = [v for v in sig.values() if len(v) > 1]
    out["arm_identity_classes"] = ident
    out["_sources"]["arm_identity_classes"] = (
        "SHA-256 over the full n=20 output series of each labelled arm in timeseries2.json; "
        "classes with more than one member are distinct labels for a single arm")

    # ---- scope-envelope sweep: medians per envelope -------------------------------------------
    sc = load("scope_envelope.json")
    by = {}
    for row in sc["rows"]:
        lv = row["kvar"] if row["axis"] == "reactive" else row["sigma"]
        by.setdefault((row["axis"], row["state"], lv), []).append(row)
    scope_out = {}
    for (ax, st, lv), rs in by.items():
        dj = [r["dJ_V"] for r in rs]
        scope_out[f"{ax}|{st}|{lv}"] = {
            "dJV_median": round(statistics.median(dj), 2),
            "dJV_min": round(min(dj), 2), "dJV_max": round(max(dj), 2),
            "trip_frac": round(sum(1 for r in rs if r["trip"]) / len(rs), 2),
            "vmax_max": round(max(r["vmax"] for r in rs), 4), "n": len(rs)}
    out["scope_envelope_derived"] = scope_out
    out["_sources"]["scope_envelope_derived"] = "scope_envelope.json rows"

    # ---- lifetime dose-response, if the sweep has been run ------------------------------------
    if (RES / "ttl_sweep.json").exists():
        tsw = load("ttl_sweep.json")
        out["ttl_sweep_fits"] = tsw["fits"]
        out["_sources"]["ttl_sweep_fits"] = "ttl_sweep.json fits (OLS integral ~ ttl)"

    (RES / "derived_reported.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out["timeseries_derived"]["light_load|q44_conformant"], indent=1))
    print("\narm identity classes:", json.dumps(out["arm_identity_classes"]))
    print("\nSaved -> experiments/results/derived_reported.json")


if __name__ == "__main__":
    main()
