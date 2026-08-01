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


# Removed: fig_penetration, fig_exposure and fig_attack_families. They plotted the PV-penetration,
# capacity-time-exposure and attack-family sweeps, all of which were run on the superseded
# Generator-based harness against a no-DER counterfactual and are withdrawn in Section VIII ("Earlier
# sweeps, and why they are not reported as results"). Their inputs now live in
# experiments/results/superseded/ and their PDFs have been deleted, so nothing in the manuscript
# refers to them. The withdrawn runs remain in the archive under that directory's README, which is
# where the withdrawal can be checked; regenerating the plots would only invite the reader to treat
# them as findings.


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

    # Colour encodes the AUTHORIZED ENVELOPE, line style encodes CREDENTIAL LIFETIME. The two
    # arms sharing an envelope are bit-identical until expiry, which is the point of the figure,
    # so they must share a colour; encoding them as two different colours (as an earlier version
    # did, with B1 and B2 both #0072B2) hid the overlap and duplicated a colour across envelopes.
    # Arms are labelled by their commanded kvar because the artifact's "full"/"narrow" labels are
    # inverted: "full" commands 3.6 kvar, "narrow ACL" commands 5.28 kvar.
    fig, ax = plt.subplots(figsize=(3.4, 2.5))
    for pol, style, col, lab in [
            ("B2_acl_narrow_1547", "-", LIGHT, "5.28 kvar, long-lived (B2)"),
            ("B5_containder_1547", "--", "#8C5000", "5.28 kvar, bounded (B5)"),
            ("B1_legacy_full", "-", DARK, "3.60 kvar, long-lived (B1)"),
            ("A4_full_lifecycle", "--", "#00355A", "3.60 kvar, bounded (A4)")]:
        med, lo, hi = band(pol)
        ax.plot(t, med, style, color=col, lw=1.3, label=lab)
        ax.fill_between(t, lo, hi, color=col, alpha=0.13, lw=0)
    ax.axvline(ta + ttl, color="black", ls=":", lw=0.8)
    top = ax.get_ylim()[1]
    ax.text(ta + ttl - 1.2, top * 0.60, "credential expiry", fontsize=6, rotation=90,
            va="center", ha="right")
    ax.annotate("bounded and long-lived arms\ncoincide exactly until expiry",
                xy=(17, 0.60 * top), xytext=(6.5, 0.17 * top), fontsize=5.5,
                ha="left", va="center", color="#333333",
                arrowprops=dict(arrowstyle="->", lw=0.6, color="#333333",
                                shrinkA=0, shrinkB=2))
    ax.set_xlabel("time (min)")
    ax.set_ylabel("overvoltage area (p.u.-node)")
    ax.legend(loc="upper right", fontsize=5.2, ncol=1, handlelength=2.6)
    ax.grid(True, lw=0.3, alpha=0.5)
    fig.savefig(HERE / "fig_timeseries.pdf")
    plt.close(fig)


#: The two figures the manuscript includes, and the only two this script builds. Every input it
#: reads is a live file in experiments/results/, so a clean checkout reproduces both.
BUILT = (fig_containment_chain, fig_timeseries)

if __name__ == "__main__":
    for fn in BUILT:
        fn()
    print("wrote " + ", ".join(fn.__name__ for fn in BUILT))
