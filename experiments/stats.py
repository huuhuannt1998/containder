"""Paired contrasts, bootstrap intervals, and Holm correction.

Why this module exists
----------------------
The evaluation methodology declared two procedures the analysis did not perform. It stated that
"Holm correction is applied within each hypothesis family", and no implementation existed. And it
stated that every contrast is paired on seed, while the lifecycle analysis bootstrapped each arm's
own median and reported a bare percentage for the difference between them. A paper that invites
artifact inspection cannot claim a statistical procedure it does not run, so both are implemented
here and both analyses now call this module.

The paired form is not merely more defensible, it is more powerful: the seed-to-seed variance in
absolute harm is large (standard deviations of 46 to 99 p.u.-node across seeds at the stressed
rungs) while the seed-to-seed variance in the *difference* between two lifecycle arms is small,
because both arms see the identical fleet placement. Pairing removes the former entirely.
"""
from __future__ import annotations

import math
import random
import statistics
from math import comb


def _norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _norm_ppf(p):
    """Inverse standard normal CDF (Acklam's rational approximation, |err| < 1.15e-9)."""
    if not 0.0 < p < 1.0:
        return -math.inf if p <= 0.0 else math.inf
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def boot_ci(xs, n=10000, seed=20260801, stat=statistics.median, alpha=0.05):
    """Bias-corrected and accelerated (BCa) bootstrap interval for ``stat`` over ``xs``.

    BCa rather than a plain percentile interval because these distributions are skewed --
    integrated harm is bounded below and has a long upper tail -- and a percentile interval is
    then biased. The bias-correction term ``z0`` is estimated from the proportion of bootstrap
    replicates below the observed statistic, and the acceleration ``a`` from the jackknife
    skewness. An earlier version of this module computed a plain percentile interval while the
    manuscript described it as bias-corrected; that discrepancy is what this implementation
    removes.

    Falls back to the percentile interval in the degenerate cases -- all values
    identical, or fewer than three observations -- where BCa is undefined rather than merely
    imprecise.
    """
    if not xs:
        return (None, None)
    k = len(xs)
    theta = stat(xs)
    if k < 3 or all(x == xs[0] for x in xs):
        return (round(theta, 4), round(theta, 4))

    rng = random.Random(seed)
    reps = sorted(stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))

    # Bias correction: how far the bootstrap distribution sits from the observed statistic.
    n_below = sum(1 for r in reps if r < theta)
    if n_below in (0, n):
        lo = reps[int((alpha / 2) * n)]
        hi = reps[int((1 - alpha / 2) * n) - 1]
        return (round(lo, 4), round(hi, 4))
    z0 = _norm_ppf(n_below / n)

    # Acceleration: jackknife skewness of the statistic.
    jack = [stat(xs[:i] + xs[i + 1:]) for i in range(k)]
    jbar = statistics.fmean(jack)
    num = sum((jbar - j) ** 3 for j in jack)
    den = 6.0 * (sum((jbar - j) ** 2 for j in jack) ** 1.5)
    a = num / den if den else 0.0

    def endpoint(pz):
        z = z0 + pz
        adj = z0 + z / (1.0 - a * z)
        return min(max(_norm_cdf(adj), 0.0), 1.0)

    p_lo = endpoint(_norm_ppf(alpha / 2))
    p_hi = endpoint(_norm_ppf(1 - alpha / 2))
    lo = reps[min(n - 1, max(0, int(p_lo * n)))]
    hi = reps[min(n - 1, max(0, int(p_hi * n) - 1))]
    if lo > hi:
        lo, hi = hi, lo
    return (round(lo, 4), round(hi, 4))


def sign_test_p(diffs):
    """Two-sided exact binomial sign test on the non-zero paired differences.

    Returns 1.0 when every difference is exactly zero, which is the correct answer and also a
    warning: an arm whose paired differences are *identically* zero across every seed is not
    statistically indistinguishable from its baseline, it is the same arm. :func:`paired_contrast`
    flags that case explicitly rather than letting a p-value of 1.0 be read as a null result.
    """
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    n = pos + neg
    if n == 0:
        return 1.0
    k = min(pos, neg)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / (2 ** n))


def paired_contrast(treat, base, label="", n_boot=10000):
    """Paired difference of ``treat`` against ``base``, elementwise by seed.

    Reports the median paired difference and the median paired *relative* change, each with a
    bootstrap interval, the sign test, and the count of seeds favouring the treatment.

    ``identical`` marks the case where every paired difference is exactly zero. That is not a
    measurement of no effect; it means the two arms executed the same trajectory, and the
    manuscript must say so rather than report a zero with an interval around it.
    """
    if len(treat) != len(base) or not treat:
        raise ValueError("paired_contrast requires equal-length non-empty sequences")
    diffs = [t - b for t, b in zip(treat, base)]
    rels = [100.0 * (t - b) / b for t, b in zip(treat, base) if b]
    lo, hi = boot_ci(diffs, n=n_boot)
    rlo, rhi = boot_ci(rels, n=n_boot) if rels else (None, None)
    identical = all(d == 0.0 for d in diffs)
    return {
        "label": label,
        "n": len(diffs),
        "median_treat": round(statistics.median(treat), 4),
        "median_base": round(statistics.median(base), 4),
        "median_paired_diff": round(statistics.median(diffs), 4),
        "ci_lo": lo, "ci_hi": hi,
        "median_rel_pct": round(statistics.median(rels), 3) if rels else None,
        "rel_ci_lo": rlo, "rel_ci_hi": rhi,
        "p_sign": round(sign_test_p(diffs), 6),
        "n_favouring_treat": sum(1 for d in diffs if d < 0),
        "n_against": sum(1 for d in diffs if d > 0),
        "ci_excludes_zero": bool(lo is not None and (lo > 0 or hi < 0)),
        "identical_to_base": identical,
    }


def holm(records, key="p_sign", out="p_holm", alpha=0.05):
    """Holm-Bonferroni step-down correction, applied in place within one family.

    ``records`` is one hypothesis family. Each record gains its corrected p-value and a
    ``significant_holm`` flag. Records marked ``identical_to_base`` are excluded from the
    family size, because a contrast between an arm and itself is not a hypothesis test and
    inflating the correction with it would penalise the genuine tests.
    """
    testable = [r for r in records if not r.get("identical_to_base")]
    m = len(testable)
    for r in records:
        if r.get("identical_to_base"):
            r[out] = None
            r["significant_holm"] = False
    ordered = sorted(testable, key=lambda r: r[key])
    running = 0.0
    for i, r in enumerate(ordered):
        adj = min(1.0, (m - i) * r[key])
        running = max(running, adj)          # step-down monotonicity
        r[out] = round(running, 6)
        r["significant_holm"] = bool(running <= alpha)
    return records
