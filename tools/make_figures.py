#!/usr/bin/env python3
"""Generate publication figures from the real experiment results (JSON in experiments/results)."""
import json
import os
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "experiments" / "results"
#: Figures are written into the manuscript tree, which is not part of the public repository.
HERE = Path(os.environ.get("CONTAINDER_MANUSCRIPT",
                           ROOT / "manuscripts" / "CONTAINDER")).resolve() / "figures"

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


def fig_reliance():
    """Harm against the reactive support the feeder is actually drawing (RQ2, H2).

    The central conditional result: what an adversary gains by withdrawing reactive support is
    governed by how much support the fleet was delivering, not by PV penetration. Both feeders
    are plotted on the same axes because that is the claim -- the relationship holds across two
    feeders whose penetrations at comparable harm differ by an order of magnitude.

    Filled markers are the confirmatory rungs; open markers are the post-hoc resolution sweep
    (results/reliance_resolution.json), which tests no hypothesis and exists only to resolve a
    curve whose endpoints the confirmatory rungs had already fixed. The two are drawn
    differently so no reader mistakes one for the other.
    """
    conf = json.loads((RES / "shape_contrasts.json").read_text())["h2_reliance"]
    extra = json.loads((RES / "reliance_resolution.json").read_text())["summary"]

    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    for key, col, mark, lab in [("ieee8500", DARK, "o", "IEEE 8500-node"),
                                ("ieee123", LIGHT, "s", "IEEE 123-bus")]:
        pts = []
        for r in conf:
            if r["feeder"] == key:
                pts.append((abs(r["legit_q_fleet_kvar"] or 0) / 1000.0,
                            r["median_dJ_band_widest_Q1"], r["legit_compliant"], True,
                            r.get("ci_lo"), r.get("ci_hi")))
        for r in extra:
            if r["feeder"] == key:
                pts.append((abs(r["legit_q_fleet_kvar"] or 0) / 1000.0,
                            r["median_dJ_band"], r["legit_compliant"], False, None, None))
        pts.sort()
        ax.plot([p[0] for p in pts], [max(p[1], 1e-3) for p in pts], "-",
                color=col, lw=1.0, alpha=0.75, label=lab, zorder=2)
        # Intervals are drawn only where they exist: the confirmatory rungs carry bootstrap CIs,
        # the resolution rungs are single medians. Drawing nothing where there is nothing is why
        # the caption can state which points have intervals.
        cx = [p[0] for p in pts if p[4] is not None]
        cy = [max(p[1], 1e-3) for p in pts if p[4] is not None]
        clo = [max(1e-4, max(p[1], 1e-3) - p[4]) for p in pts if p[4] is not None]
        chi = [max(1e-4, p[5] - max(p[1], 1e-3)) for p in pts if p[4] is not None]
        if cx:
            ax.errorbar(cx, cy, yerr=[clo, chi], fmt="none", ecolor=col,
                        elinewidth=0.9, capsize=2.2, zorder=3)
        for x, y, compliant, is_conf, _lo, _hi in pts:
            y = max(y, 1e-3)
            ax.plot([x], [y], marker=mark, ms=5 if is_conf else 4.2,
                    mfc=col if is_conf else "white", mec=col,
                    mew=1.0, ls="none", zorder=4)
            if compliant:
                ax.plot([x], [y], marker="o", ms=10, mfc="none", mec=col,
                        mew=0.9, ls="none", zorder=3)

    ax.set_yscale("symlog", linthresh=0.1)
    ax.set_xlabel("legitimate fleet reactive absorption (Mvar)")
    ax.set_ylabel(r"induced $\Delta J_{\mathrm{band}}$ (p.u.-node)")
    ax.legend(loc="upper left", fontsize=6)
    ax.grid(True, lw=0.3, alpha=0.5)
    ax.text(0.97, 0.06, "filled: confirmatory   open: resolution sweep",
            transform=ax.transAxes, fontsize=5.2, ha="right", va="bottom", color="#333333")
    ax.text(0.97, 0.015, "large circle: legitimate operation compliant",
            transform=ax.transAxes, fontsize=5.2, ha="right", va="bottom", color="#333333")
    fig.savefig(HERE / "fig_reliance.pdf")
    plt.close(fig)


def fig_layers():
    """What each containment layer is worth (RQ3/RQ5/RQ6).

    The headline is the flat bar: denying the compromised identity removes no harm at all. The
    figure exists to make that comparable at a glance against the layers that do remove harm.
    """
    d = json.loads((RES / "lifecycle_physical.json").read_text())
    S = {(r["state"], r["arm"]): r for r in d["summary"]}
    st = "ieee8500_stress"
    arms = [("legacy", "long-lived baseline"),
            ("mech_S0", "expiry only"),
            ("mech_S2", "cleanup only"),
            ("mech_S1", "session only (S1)"),
            ("mech_S3", "session + cleanup (S3)"),
            ("deny_denylist_d5", "deny new sessions only"),
            ("deny_denylist+session_d5", "+ session termination"),
            ("deny_denylist+session+cancel_d5", "+ session + cancellation")]
    vals, los, his, labs = [], [], [], []
    for a, lab in arms:
        r = S.get((st, a))
        if not r:
            continue
        vals.append(r["median_integral"])
        los.append(r["median_integral"] - r["ci_lo"])
        his.append(r["ci_hi"] - r["median_integral"])
        labs.append(lab)
    base = vals[0]
    fig, ax = plt.subplots(figsize=(3.4, 2.7))
    ypos = list(range(len(vals)))[::-1]
    cols = [DARK if v >= base * 0.999 else LIGHT for v in vals]
    ax.barh(ypos, vals, xerr=[los, his], color=cols, height=0.62,
            error_kw=dict(elinewidth=0.7, capsize=2, ecolor="#333333"))
    ax.set_yticks(ypos)
    ax.set_yticklabels(labs, fontsize=6)
    ax.axvline(base, color="black", ls=":", lw=0.8)
    # Place each label clear of its own error bar, not at the bar end, or the two overlap.
    for y, v, h in zip(ypos, vals, his):
        ax.text(v + h + base * 0.045, y, f"{100*(v-base)/base:+.0f}%", va="center",
                fontsize=5.8, color="#333333")
    ax.set_xlabel("integrated harm (p.u.-node-min)")
    ax.set_xlim(0, base * 1.42)
    ax.grid(True, axis="x", lw=0.3, alpha=0.5)
    fig.savefig(HERE / "fig_layers.pdf")
    plt.close(fig)


#: The two figures the manuscript includes, and the only two this script builds. Every input it
#: reads is a live file in experiments/results/, so a clean checkout reproduces both.
BUILT = (fig_containment_chain, fig_reliance, fig_layers)

if __name__ == "__main__":
    for fn in BUILT:
        fn()
    print("wrote " + ", ".join(fn.__name__ for fn in BUILT))
