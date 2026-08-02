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

import random
import statistics
from math import comb


def boot_ci(xs, n=10000, seed=20260801, stat=statistics.median, alpha=0.05):
    """Percentile bootstrap interval for ``stat`` over ``xs``."""
    if not xs:
        return (None, None)
    rng = random.Random(seed)
    k = len(xs)
    vals = sorted(stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    lo = vals[int((alpha / 2) * n)]
    hi = vals[int((1 - alpha / 2) * n) - 1]
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
