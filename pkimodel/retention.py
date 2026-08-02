"""Retained-authority expectations, separated by compromise class.

Why this module exists
----------------------
The manuscript reported a single containment-latency figure of merit, ``T/p`` -- the credential
lifetime divided by the per-cycle attestation detection probability -- and applied it to every
compromise. That is wrong in two ways, and the errors run in opposite directions.

**It is too pessimistic for a copied key.** If an adversary copies the operational private key
but does not persist on the device, attestation has nothing to detect: the next renewal generates
a *fresh* key regardless, and the copied one is inert from that moment. Retention is bounded by
the remainder of the current epoch, whatever ``p`` is. Under a compromise arriving uniformly in
the epoch the expectation is ``T/2``, and the worst case is ``T``. Detection probability does not
appear.

**It is too optimistic for a persistent compromise arriving mid-epoch.** ``T/p`` is the
expectation only when the compromise lands immediately after an issuance, so that the adversary
holds a whole fresh epoch before the first detection opportunity. A compromise arriving uniformly
within the epoch has expectation ``T(1/p - 1/2)``, which is smaller.

Both closed forms are checked against Monte-Carlo simulation in ``tests/test_retention.py``.

The distinction matters for the design argument: fresh-key rotation contains a copied key without
any attestation at all, whereas containing an adversary who remains on the device and renews
successfully is exactly what attestation buys, and its value is governed by ``p``. Conflating the
two credits attestation with a guarantee that key rotation already provides, and simultaneously
overstates how long a mid-epoch persistent compromise survives.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class RetentionModel:
    """Expected and worst-case retained authority for one compromise class."""
    compromise_class: str
    expected: float
    worst_case: float
    formula: str
    depends_on_detection: bool
    note: str


def copied_key(ttl: float, *, arrival: str = "uniform") -> RetentionModel:
    """Adversary copies the operational key but does not persist on the device.

    Fresh-key rotation at the next epoch makes the copied key inert. Attestation is irrelevant
    to this class, because there is nothing on the device for it to measure.
    """
    if arrival == "uniform":
        exp, f = ttl / 2.0, "T/2"
    elif arrival == "immediate":
        exp, f = ttl, "T"
    else:
        raise ValueError(f"unknown arrival {arrival!r}")
    return RetentionModel(
        "copied operational key", exp, ttl, f, False,
        "Bounded by the remaining epoch. Independent of the attestation detection "
        "probability: renewal mints a fresh key whether or not anything is detected.")


def persistent_compromise(ttl: float, detect_prob: float, *,
                          arrival: str = "uniform") -> RetentionModel:
    """Adversary remains on the device and re-attests at each renewal.

    Each renewal independently detects the compromise with probability ``p``. The number of
    additional whole epochs survived after the current one is Geometric on {0, 1, 2, ...} with
    mean ``(1-p)/p``.

    * ``arrival='immediate'`` -- compromise just after an issuance, so the adversary holds a full
      epoch before the first detection opportunity: ``E = T + T(1-p)/p = T/p``.
    * ``arrival='uniform'`` -- compromise uniform within the epoch, so the expected remainder of
      the current epoch is ``T/2``: ``E = T/2 + T(1-p)/p = T(1/p - 1/2)``.
    """
    if not 0.0 < detect_prob <= 1.0:
        raise ValueError("detect_prob must be in (0, 1]")
    tail = ttl * (1.0 - detect_prob) / detect_prob
    if arrival == "immediate":
        exp, f = ttl + tail, "T/p"
    elif arrival == "uniform":
        exp, f = ttl / 2.0 + tail, "T(1/p - 1/2)"
    else:
        raise ValueError(f"unknown arrival {arrival!r}")
    return RetentionModel(
        "persistent compromise, attestation-gated renewal", exp, float("inf"), f, True,
        "Unbounded in the worst case: an adversary the reference values do not distinguish "
        "renews indefinitely. Attestation bounds this class only in expectation, and only for "
        "compromise that the evidence actually measures.")


def undetectable_compromise(ttl: float, horizon: float) -> RetentionModel:
    """Adversary persists and is not represented in the attestation evidence at all.

    Renewal succeeds every epoch. Neither lifetime nor attestation bounds this class; only
    authorization scope and the command-effect layer limit what it can do.
    """
    return RetentionModel(
        "persistent compromise outside the measurement", horizon, float("inf"),
        "unbounded (horizon-limited)", False,
        "Outside the design's guarantee. Named so that the attestation claim is not read as "
        "covering firmware states the evidence does not measure.")


def stolen_session(session_max_age: float, revalidation_interval: float,
                   forced_close: float = float("inf")) -> RetentionModel:
    """Adversary controls an established session; bounded by whichever check fires first."""
    exp = min(session_max_age, revalidation_interval, forced_close)
    return RetentionModel(
        "stolen active session", exp, exp,
        "min(T_session-age, T_revalidation, T_forced-close)", False,
        "Credential expiry alone does not bound this class unless the enforcement point "
        "revalidates the credential on the established session.")


def persistent_command(command_duration: float, cancel_latency: float,
                       safe_restore: float = float("inf")) -> RetentionModel:
    """An already-issued scheduled control; bounded by duration, cancellation or restoration."""
    exp = min(command_duration, cancel_latency, safe_restore)
    return RetentionModel(
        "persistent command effect", exp, exp,
        "min(T_command-duration, T_cancel, T_safe-restore)", False,
        "Survives both credential expiry and session closure unless something cancels it.")


# ------------------------------------------------------------------ verification by simulation

def simulate_persistent(ttl: float, detect_prob: float, *, arrival: str = "uniform",
                        n: int = 200_000, seed: int = 7) -> float:
    """Monte-Carlo mean retention for :func:`persistent_compromise`, for cross-checking."""
    rng = random.Random(seed)
    total = 0.0
    for _ in range(n):
        t = ttl if arrival == "immediate" else rng.random() * ttl
        # Detection opportunities occur at each subsequent renewal boundary.
        while rng.random() > detect_prob:
            t += ttl
        total += t
    return total / n


def simulate_copied(ttl: float, *, arrival: str = "uniform",
                    n: int = 200_000, seed: int = 7) -> float:
    """Monte-Carlo mean retention for :func:`copied_key`."""
    rng = random.Random(seed)
    if arrival == "immediate":
        return ttl
    return sum(rng.random() * ttl for _ in range(n)) / n
