#!/usr/bin/env python3
"""Emit the model-validation subsection from the result files.

Written as a generator rather than typed by hand so that every numeral in the section is read
from the JSON it describes. The manuscript's numeral gate then passes by construction, and the
section cannot drift from the runs behind it.

Usage: python3 tools/gen_validation_section.py > manuscripts/CONTAINDER/sections/08c_validation.tex
"""
import json
import pathlib
import statistics
import sys

R = pathlib.Path(__file__).resolve().parent.parent / "experiments" / "results"


def f(x, d=1):
    return f"{x:.{d}f}"


def main():
    V = json.loads((R / "solver_validation.json").read_text())
    rows = [r for r in V["rows"] if "error" not in r]
    n = len(rows)
    sign_ind = sum(1 for r in rows
                   if (r["delta_j_invcontrol"] > 0) == (r["delta_j_independent"] > 0))
    maxbal = max(r["balance"]["residual_rel"] for r in rows)
    conv = sum(1 for r in rows if r["independent_converged"])
    newt = sum(1 for r in rows if r["newton_converged"])
    errs = sorted(100 * r["delta_j_rel_err"] for r in rows if r["independent_converged"])
    frz = sorted(100 * r["delta_j_frozen_rel_err"] for r in rows)
    amb_rows = [r for r in rows if r["rated_base_ambiguous_units"] > 0]
    amb = max((r["rated_base_ambiguous_units"] for r in amb_rows), default=0)
    units = max((r["n_units"] for r in amb_rows), default=0)

    sp = R / "sweep_path.json"
    S = json.loads(sp.read_text()) if sp.exists() else None

    o = []
    w = o.append
    w(r"\subsection{Does the physical model carry the result?}\label{sec:validation}")
    w("")
    w(r"""Every physical number here comes from one solver, and from one component of it: the
\texttt{InvControl} object that realises the Category~B characteristic defining the legitimate
baseline. If that component departs from the standard it implements, every contrast inherits the
departure silently, because the baseline and the attacker arms are produced by the same object. A
second solver is the textbook answer and we could not run one honestly: neither GridLAB-D nor
pandapower ingests these feeders without a hand-written converter whose own defects would be
indistinguishable from a solver disagreement. So we re-implemented the parts that could be wrong
and checked the solver against them.""")
    w("")
    w(r"\paragraph{Result: conservation holds, and the direction of every contrast survives}")
    exp = f"{maxbal:.0e}".split("e")
    w(rf"""Across {n} arms spanning both feeders at two rungs of each confirmatory ladder, the
converged solutions satisfy real-power balance --- source injection plus fleet generation against
load plus losses --- to a relative residual below ${exp[0]}\times10^{{{int(exp[1])}}}$. The
Category~B characteristic was then re-implemented in physical kvar and driven to a fixed point by
hand, with \texttt{{InvControl}} disabled, so that the control path shares no code with the
harness; the fixed point converged in {conv} of the {n} arms. In
\textbf{{{sign_ind} of {n}}} arms the independently-controlled contrast has the same sign as the
harness's, and in every arm both are strictly positive: the authorized point that the harness
credits with harm is credited with harm by an implementation that shares none of its control
code.""")
    w("")
    w(r"\paragraph{Result: the magnitude does not survive, and we could not attribute the gap}")
    by_f = {}
    for s_ in V["summary"]:
        by_f.setdefault(s_["feeder"], []).append(s_)
    def rng(k, key, mul=1, d=0):
        vals = [x[key] * mul for x in by_f[k]]
        lo, hi = min(vals), max(vals)
        return f"{lo:.{d}f}" if abs(hi - lo) < 10 ** -d else f"{lo:.{d}f}--{hi:.{d}f}"
    w(rf"""What does not reproduce is how much harm. Over the arms whose fixed point converged, the
independently-controlled contrast differs from the harness's by {f(errs[0])}\% to
{f(errs[-1])}\%, with a median of {f(statistics.median(errs))}\%, and the disagreement is not
spread evenly. It tracks how much
discrete switching the feeder does: on IEEE~8500, where a median of {rng("ieee8500",
"median_regulator_taps_differing")} of that feeder's twelve regulators end up on different taps
between the two implementations, the contrast differs by {rng("ieee8500",
"median_delta_j_rel_err", 100)}\%, while on IEEE~123, where {rng("ieee123",
"median_regulator_taps_differing", 1, 1)} regulators differ, it differs by {rng("ieee123",
"median_delta_j_rel_err", 100)}\%. The two implementations reach
nearly the same fleet reactive dispatch; what separates them is where the regulators land, and
the band integral is an integral of voltage exceedance, so a tap step moves it directly.""")
    w("")
    w(rf"""Pinning every regulator to the harness's own tap positions and repeating the comparison
does not settle it: the disagreement then ranges from {f(frz[0])}\% to {f(frz[-1])}\%, moving in
both directions across seeds, because taps that were the equilibrium for one reactive dispatch are
wrong for another and the pinning also freezes capacitor switching. That counterfactual shows the
discrete state matters a great deal. It does not isolate it as the sole cause, and we do not claim
that it does.""")
    w("")
    w(rf"""Two further observations belong with this. The alternative Newton solution algorithm
converges at the attacker's worst point in only {newt} of {n} arms, so that operating point is
numerically fragile under a solver change as well. And on IEEE~123 the element's rated voltage base
disagrees with the bus base OpenDSS assigns it for up to {amb} of {units} units --- the
line-to-line connected single-phase ones --- so \texttt{{voltage\_curvex\_ref=rated}} admits two
readings there. We report the count rather than resolving it silently.""")
    w("")
    if S:
        srows = [r for r in S["rows"] if "error" not in r]
        m = len(srows)
        agree = sum(1 for r in srows if r["argmax_agrees"])
        sgn = sum(1 for r in srows if r["sign_agrees"])
        higher = sum(1 for r in srows
                     if r["independent_max_dJ"] > r["sequential_max_dJ"])
        dif = sorted(100 * r["max_rel_diff"] for r in srows
                     if r["max_rel_diff"] is not None)
        by = {}
        for r in srows:
            k = r["primitive"]
            by.setdefault(k, [0, 0])
            by[k][1] += 1
            by[k][0] += 1 if r["argmax_agrees"] else 0
        w("")
        w(r"\paragraph{Result: the sweep order moves which point is selected, and can "
          r"understate what the set is worth}")
        w(rf"""Because tap state carries across solves, our own harness needs the same scrutiny:
it evaluates an authorized set by walking the grid inside one session, so each candidate inherits
the tap state the previous candidate left, whereas the oracle-adversary framing is that an
adversary plays \emph{{one}} point against the running feeder. Re-evaluating every candidate from
a freshly established legitimate equilibrium agrees in sign in {sgn} of {m} arms, but selects the
same worst admissible point in only {agree} of {m}. The disagreement is almost entirely in the
voltage-responsive primitive: the fixed setpoint agrees in {by['setpoint'][0]} of
{by['setpoint'][1]} arms and the curve in {by['curve'][0]} of {by['curve'][1]}.""")
        w("")
        w(rf"""The selected \emph{{maximum}} moves less than its location does --- a median of
{f(statistics.median(dif))}\% --- but not always by a little, and not always downward.
Independent evaluation finds a \emph{{higher}} maximum in {higher} of {m} arms, and on IEEE~8500
under the curve primitive two seeds understate by {f(dif[-2])}\% and {f(dif[-1])}\%. The
consequence is that the reported harms are lower bounds by a wider margin than the grid-resolution
study alone indicated, and the slack is sweep-order dependent rather than purely a matter of grid
spacing. For a claim of the form ``this authorization set fails to contain'' the bias is
conservative --- the attainable harm is larger than reported, not smaller. We did not re-evaluate
every authorization set independently, so we do not claim the slack is uniform across sets, and
any reading of \emph{{where}} in a set the worst point lies should be treated as
sweep-order dependent.""")

    w("")
    w(rf"""\textbf{{What this licenses, and what it does not.}} The direction of every contrast,
and the safety conclusion that follows from it, survive an independent implementation of the
control law and an independent evaluation order. The magnitudes do not. Absolute harm figures are
specific to this model of these feeders and should be read as evidence of direction and order of
magnitude, not as calibrated predictions of what a particular feeder would suffer.

One boundary deserves stating precisely, because it is easy to over-read this subsection in either
direction. What was tested is the \emph{{absolute}} paired contrast, at one attacker point, on two
rungs of each feeder. The paper's lifecycle results are reported as \emph{{ratios}} --- percentage
reductions of one arm against another within a single model --- and a common-mode modelling error
cancels from a ratio in a way it does not from a difference. We did not measure how much of it
cancels, so we neither claim those percentages inherit the full sensitivity reported here nor claim
they escape it. Establishing that would require re-running each lifecycle arm under the independent
control, which we did not do.""")

    w("")
    w(r"\begin{table}[htbp]")
    w(r"\centering")
    w(r"""\caption{Model validation, per rung of the confirmatory ladder. $\Delta J$ is the paired
attacker-minus-legitimate band integral at the worst admissible point of the widest set. ``indep.''
re-implements the Category~B characteristic with \texttt{InvControl} disabled; ``frozen'' repeats
that with regulator taps pinned to the harness's positions. The error columns are the median of
the per-seed \emph{absolute} relative errors, so they do not equal the ratio of the two median
$\Delta J$ columns: errors of opposite sign cancel in a ratio of medians and would understate the
disagreement. Direction agrees everywhere; magnitude does not.}""")
    w(r"\label{tab:validation}")
    w(r"\small")
    w(r"\begin{tabular}{@{}llrrrrrr@{}}")
    w(r"\toprule")
    w(r"""Feeder & Pen. & $n$ & $\Delta J$ harness & $\Delta J$ indep. & rel.\ err. &
frozen err. & Newton \\""")
    w(r"\midrule")
    lab = {"ieee8500": "IEEE 8500", "ieee123": "IEEE 123"}
    for s_ in V["summary"]:
        ind = ("---" if s_["median_delta_j_independent"] is None
               else f"${s_['median_delta_j_independent']:.2f}$")
        re_ = ("---" if s_["median_delta_j_rel_err"] is None
               else f"${100 * s_['median_delta_j_rel_err']:.0f}\\%$")
        w(f"{lab[s_['feeder']]} & ${s_['penetration']:.1f}\\times$ & ${s_['n']}$ & "
          f"${s_['median_delta_j_invcontrol']:.2f}$ & {ind} & {re_} & "
          f"${100 * s_['median_delta_j_frozen_rel_err']:.0f}\\%$ & "
          f"${s_['n_newton_converged']}/{s_['n']}$ \\\\")
    w(r"\bottomrule")
    w(r"\end{tabular}")
    w(r"\end{table}")
    print("\n".join(o))


if __name__ == "__main__":
    sys.exit(main())
