"""Time-varying load and irradiance profiles for the horizon experiments.

Why this exists
---------------
The pilot's time-series experiment held load and irradiance constant across its sixty-minute
horizon. Under a static operating point the attacked and unattacked solutions are each a single
fixed power flow, so integrated harm is exactly (accrual rate) x (minutes the control is
honoured) and the ratio between two lifetime policies is pinned to the ratio of their exposure
windows. The pilot reported this honestly -- it observed that its "2.16x reduction" was
arithmetic rather than a measured effect -- but the underlying limitation is the static profile,
not the metric.

Varying load and irradiance over the horizon makes the accrual rate genuinely time-dependent, so
integrated harm is an integral rather than a product, and post-expiry recovery becomes a real
question: whether a regulator or capacitor left in an excursion-driven position holds voltage up
after the adversarial control stops is only observable when the underlying state is moving.

Profiles are deterministic functions of the step index so that every arm at a given seed sees an
identical exogenous trajectory; the only difference between arms is the credential lifecycle.
"""
from __future__ import annotations

import math


def midday_pv(step: int, n_steps: int, *, peak: float = 1.0, floor: float = 0.55) -> float:
    """Irradiance over the horizon: a smooth midday arc.

    The horizon is taken to straddle solar noon, so irradiance rises to ``peak`` near the middle
    and falls away symmetrically, bottoming at ``floor``. This is the state in which volt-var
    support is most load-bearing and therefore in which withdrawing it matters most.
    """
    if n_steps <= 1:
        return peak
    x = (step / (n_steps - 1)) * 2.0 - 1.0          # -1 .. +1
    return floor + (peak - floor) * math.cos(x * math.pi / 2.0) ** 2


def cloud_transient(step: int, n_steps: int, *, depth: float = 0.35,
                    start_frac: float = 0.62, width_frac: float = 0.10) -> float:
    """Multiplicative irradiance dip modelling a passing cloud.

    Placed after the midpoint so that it falls inside the post-expiry window of the shorter
    credential lifetimes, which is where a spurious "recovery" would otherwise be easiest to
    claim: a feeder whose irradiance happens to fall at expiry recovers for reasons that have
    nothing to do with the credential.
    """
    if n_steps <= 1:
        return 1.0
    s0 = start_frac * n_steps
    w = max(1.0, width_frac * n_steps)
    x = (step - s0) / w
    if abs(x) > 1.0:
        return 1.0
    return 1.0 - depth * math.cos(x * math.pi / 2.0) ** 2


def evening_load(step: int, n_steps: int, *, base: float = 1.0, rise: float = 0.22) -> float:
    """Load multiplier scale over the horizon: a gentle rise toward the evening peak."""
    if n_steps <= 1:
        return base
    x = step / (n_steps - 1)
    return base + rise * x


def horizon_profile(n_steps: int, *, load_mult: float, clouds: bool = True) -> "list[dict]":
    """Full exogenous trajectory: per-step irradiance and load multiplier.

    ``load_mult`` is the nominal multiplier for the operating tier; the profile modulates it.
    """
    out = []
    for k in range(n_steps):
        irr = midday_pv(k, n_steps)
        if clouds:
            irr *= cloud_transient(k, n_steps)
        out.append({"step": k,
                    "irradiance": round(irr, 6),
                    "load_mult": round(load_mult * evening_load(k, n_steps), 6)})
    return out
