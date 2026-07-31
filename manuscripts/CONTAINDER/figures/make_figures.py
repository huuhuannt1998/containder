#!/usr/bin/env python3
"""Generate publication figures from the real experiment results (JSON in experiments/results)."""
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RES = ROOT / "experiments" / "results"

plt.rcParams.update({"font.size": 8, "axes.linewidth": 0.6, "figure.dpi": 300,
                     "savefig.bbox": "tight", "legend.frameon": False})
DARK, LIGHT = "#0072B2", "#E69F00"   # colorblind-safe; distinguished also by marker/hatch


def fig_penetration():
    d = json.loads((RES / "penetration.json").read_text())
    x = [int(v * 100) for v in d["levels"]]
    fig, ax = plt.subplots(figsize=(3.3, 2.1))
    ax.plot(x, d["B1_full"], "o-", color=DARK, label="legacy full (B1)", lw=1.3, ms=4)
    ax.plot(x, d["B5_narrow"], "s--", color=LIGHT, label="CONTAINDER (B5)", lw=1.3, ms=4)
    ax.set_xlabel("PV penetration (%)")
    ax.set_ylabel("induced overvoltage area")
    ax.set_xticks(x)
    ax.grid(True, lw=0.3, alpha=0.5)
    ax.legend(loc="upper left")
    fig.savefig(HERE / "fig_penetration.pdf")
    plt.close(fig)


def fig_exposure():
    d = json.loads((RES / "full_sweep.json").read_text())
    jv, ba = d["jv_by_scope"], d["br_auth_hours"]
    baselines = [("B1", "full", "legacy_long"), ("B2", "narrow", "legacy_long"),
                 ("B3", "full", "ephemeral"), ("B4", "reference", "attest_long"),
                 ("B5", "narrow", "containder")]
    labels, vals = [], []
    for name, scope, regime in baselines:
        exp = jv[f"{scope}|light_load"] * ba[regime]
        labels.append(name)
        vals.append(max(exp, 1.0))   # floor for log display
    fig, ax = plt.subplots(figsize=(3.3, 2.1))
    bars = ax.bar(labels, vals, color=[DARK, LIGHT, DARK, "#56B4E9", LIGHT], edgecolor="k", lw=0.5)
    bars[1].set_hatch("//"); bars[4].set_hatch("//")
    ax.set_yscale("log")
    ax.set_ylabel(r"capacity-time exposure  $J_V\times BR_{auth}$")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.3, ("$\\approx$0" if v <= 1.0 else f"{v:.0e}"),
                ha="center", va="bottom", fontsize=6)
    ax.set_ylim(0.5, max(vals) * 8)
    fig.savefig(HERE / "fig_exposure.pdf")
    plt.close(fig)


def fig_attack_families():
    d = json.loads((RES / "attack_families.json").read_text())["overvoltage_families"]
    fams = ["export_limit", "volt_var", "volt_watt"]
    legacy = [d[f]["full"] for f in fams]
    cont = [d[f]["narrow"] for f in fams]
    x = range(len(fams))
    w = 0.38
    fig, ax = plt.subplots(figsize=(3.3, 2.1))
    ax.bar([i - w / 2 for i in x], legacy, w, color=DARK, edgecolor="k", lw=0.5, label="legacy full")
    ax.bar([i + w / 2 for i in x], cont, w, color=LIGHT, edgecolor="k", lw=0.5, hatch="//",
           label="CONTAINDER")
    ax.set_xticks(list(x))
    ax.set_xticklabels(["export", "volt-var", "volt-watt"])
    ax.set_ylabel("induced overvoltage area")
    ax.legend(loc="upper right")
    ax.grid(True, axis="y", lw=0.3, alpha=0.5)
    fig.savefig(HERE / "fig_attack_families.pdf")
    plt.close(fig)


def fig_containment_chain():
    steps = [("fresh\nattestation", "gate issuance"),
             ("fresh bound\nkey", "copied key"),
             ("short scoped\ncredential", "scope, T_cred"),
             ("bounded\nsession", "T_sess"),
             ("bounded\ncommand", "T_cmd"),
             ("measured\nrecovery", "BR_phys")]
    fig, ax = plt.subplots(figsize=(7.0, 1.45))
    ax.set_xlim(0, len(steps)); ax.set_ylim(0, 1); ax.axis("off")
    for i, (top, bot) in enumerate(steps):
        ax.add_patch(FancyBboxPatch((i + 0.08, 0.34), 0.84, 0.52, boxstyle="round,pad=0.02",
                                    fc="#EAF2FB", ec=DARK, lw=1.1))
        ax.text(i + 0.5, 0.60, top, ha="center", va="center", fontsize=8.5)
        ax.text(i + 0.5, 0.15, bot, ha="center", va="center", fontsize=6.5, color="#555555")
        if i < len(steps) - 1:
            ax.annotate("", xy=(i + 1.07, 0.6), xytext=(i + 0.93, 0.6),
                        arrowprops=dict(arrowstyle="-|>", color="black", lw=1.1))
    fig.savefig(HERE / "fig_chain.pdf")
    plt.close(fig)


def fig_timeseries():
    """Corrected time series: median across all seeds with a min-max band (reviewer minor 5).

    Reads timeseries2.json (per-arm recompile, legitimate-PV counterfactual, IEEE 1547 scope),
    not the superseded timeseries.json.
    """
    d = json.loads((RES / "timeseries2.json").read_text())
    P = d["params"]
    H, ttl, ta, n = P["horizon"], P["ttl"], P["t_attack"], P["n_seeds"]
    seeds = list(range(1000, 1000 + n))
    t = list(range(H))

    def band(pol, state="light_load"):
        S = [d["runs"][f"{state}|{s}|{pol}"]["series"] for s in seeds]
        med = [statistics.median(x[i] for x in S) for i in range(H)]
        lo = [min(x[i] for x in S) for i in range(H)]
        hi = [max(x[i] for x in S) for i in range(H)]
        return med, lo, hi

    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    for pol, style, col, lab in [
            ("B1_legacy_full", "-", DARK, "legacy full (B1)"),
            ("B2_acl_narrow_1547", ":", "#0072B2", "legacy + narrow ACL (B2)"),
            ("A4_full_lifecycle", "--", "#D55E00", "broad scope + lifecycle (A4)"),
            ("B5_containder_1547", "-.", LIGHT, "CONTAINDER (B5)")]:
        med, lo, hi = band(pol)
        ax.plot(t, med, style, color=col, lw=1.4, label=lab)
        ax.fill_between(t, lo, hi, color=col, alpha=0.15, lw=0)
    ax.axvline(ta + ttl, color="black", ls=":", lw=0.8)
    ax.text(ta + ttl - 1, ax.get_ylim()[1] * 0.55, "credential expiry", fontsize=6, rotation=90,
            va="center", ha="right")
    ax.set_xlabel("time (min)")
    ax.set_ylabel("overvoltage area (p.u.-node)")
    ax.legend(loc="upper right", fontsize=5.5)
    ax.grid(True, lw=0.3, alpha=0.5)
    fig.savefig(HERE / "fig_timeseries.pdf")
    plt.close(fig)


if __name__ == "__main__":
    fig_penetration()
    fig_exposure()
    fig_attack_families()
    fig_containment_chain()
    fig_timeseries()
    print("wrote fig_penetration, fig_exposure, fig_attack_families, fig_chain, fig_timeseries")
