"""Credential lifecycle / persistence estimation (M2 T2.5).

``estimate_persistence`` returns BR_time as an expected-duration DISTRIBUTION, not a point
estimate (mission constraint). Two regimes:

  * **attestation-gated ephemeral credential** — retention ends at the first renewal cycle
    where attestation detects compromise; retention ~ ``TTL * Geometric(detect_prob)``.
  * **non-attestation-gated credential** — retention ends at revocation. Under baseline
    IEEE 2030.5 revocation is forbidden (``revocation_enabled=False``) and the TTL may be
    indefinite, so retention is bounded only by the TTL or the analysis horizon
    (SAND2019-1490 4.1: CRL/OCSP prohibited, indefinite-lifetime certs).
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

from .cert_graph import Credential
from .policy_scope import Policy


@dataclass
class PersistenceDistribution:
    """Monte-Carlo samples of retained-capability duration (seconds)."""

    samples: "list[float]"

    @property
    def mean_seconds(self) -> float:
        return statistics.fmean(self.samples)

    @property
    def median_seconds(self) -> float:
        return statistics.median(self.samples)

    @property
    def mean_hours(self) -> float:
        return self.mean_seconds / 3600.0

    def quantile(self, q: float) -> float:
        s = sorted(self.samples)
        idx = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
        return s[idx]


def _ttl_for(cred: Credential, policy: Policy) -> "float | None":
    if cred.ttl_seconds is not None:
        return cred.ttl_seconds
    if policy.default_ttl_seconds:
        return policy.default_ttl_seconds.get(cred.cred_type.value)
    return None


def estimate_persistence(
    cred: Credential,
    policy: Policy,
    *,
    n_samples: int = 2000,
    seed: int = 0,
) -> PersistenceDistribution:
    """EstimatePersistence: BR_time as a retained-duration distribution."""
    rng = random.Random(seed)
    horizon = policy.analysis_horizon_seconds
    ttl = _ttl_for(cred, policy)
    samples: "list[float]" = []

    for _ in range(n_samples):
        if cred.attestation_gated:
            cycle = ttl if ttl is not None else horizon
            p = policy.attestation_detect_prob
            if p <= 0.0:
                # attestation never catches the compromise -> renews to the horizon.
                samples.append(horizon)
                continue
            # first renewal is at t=cycle; number of surviving cycles ~ Geometric(p), k>=1.
            k = 1
            while rng.random() > p:
                k += 1
                if k * cycle >= horizon:
                    break
            samples.append(min(horizon, k * cycle))
        else:
            if policy.revocation_enabled and policy.revocation_latency_seconds is not None:
                retention = policy.revocation_latency_seconds
            else:
                retention = ttl if ttl is not None else horizon
            samples.append(min(horizon, retention))

    return PersistenceDistribution(samples)


@dataclass
class RetainedAuthority:
    """Three-part retained authority: BR_auth = max(T_cred, T_sess, T_cmd) (seconds)."""

    t_cred_seconds: float   # until the stolen credential is refused for a NEW session
    t_sess_seconds: float   # until existing sessions can no longer issue commands
    t_cmd_seconds: float    # until queued/scheduled/latched controls stop affecting the DER

    @property
    def br_auth_seconds(self) -> float:
        return max(self.t_cred_seconds, self.t_sess_seconds, self.t_cmd_seconds)

    @property
    def br_auth_hours(self) -> float:
        return self.br_auth_seconds / 3600.0


def decompose_persistence(cred: Credential, policy: Policy, *, seed: int = 0) -> RetainedAuthority:
    """Decompose persistence into credential, session, and command-effect components.

    Certificate expiry alone bounds only T_cred. Without session enforcement an open session
    outlives the credential; without command-effect cleanup an already-issued long-duration
    control outlives it too. This is why shortening TTL without enforcing T_sess and T_cmd does
    not bound exposure (the paper's point, and the basis of the A2/A3 ablations).
    """
    t_cred = estimate_persistence(cred, policy, seed=seed).mean_seconds

    if policy.enforce_session:
        t_sess = min(t_cred, policy.session_max_age_seconds) if policy.session_max_age_seconds \
            else t_cred
    else:
        t_sess = t_cred + policy.unmanaged_session_overhang_seconds

    if policy.enforce_command_cleanup:
        t_cmd = policy.command_max_duration_seconds if policy.command_max_duration_seconds \
            else 300.0
    else:
        t_cmd = t_cred + policy.unmanaged_command_overhang_seconds

    return RetainedAuthority(t_cred, t_sess, t_cmd)
