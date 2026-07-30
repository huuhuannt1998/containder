"""Blast-radius analysis engine: reach, flexibility, retained authority, exposure.

Computes the cyber-side impact dimensions from the model for a compromise locus under a policy:

  * BR_reach = DERs the compromised credential can address (topological reach),
  * BR_flex  = aggregate state-dependent commandable flexibility (active/reactive intervals),
  * BR_auth  = retained authority max(T_cred, T_sess, T_cmd), and BR_exp = capacity-time exposure.

BR_phys (feeder-level physical consequence) is owned by the M4 co-simulation; this engine
produces the flexibility and exposure inputs it consumes. Capacity (nameplate) is retained as a
state-free special case for backward compatibility with the counterexample regression test.
"""
from __future__ import annotations

from dataclasses import dataclass

from .cert_graph import IdentityGraph
from .der import (
    Capability,
    ZERO_CAPABILITY,
    commandable_capacity,
    FlexInterval,
    ZERO_FLEX,
    DeviceState,
    commandable_flexibility,
)
from .lifecycle_sim import (
    PersistenceDistribution,
    estimate_persistence,
    RetainedAuthority,
    decompose_persistence,
)
from .policy_scope import Policy, resolve_addressable_ders


@dataclass
class BlastRadius:
    locus_cred: str
    reachable_ders: "frozenset[str]"
    reach: int                              # BR_reach
    capacity: Capability                    # nameplate special case of flexibility
    persistence: PersistenceDistribution    # T_cred distribution
    flexibility: FlexInterval = ZERO_FLEX   # BR_flex (state dependent)
    retained: "RetainedAuthority | None" = None   # BR_auth = max(T_cred,T_sess,T_cmd)

    @property
    def cap_kw(self) -> float:
        return self.capacity.controllable_kw

    @property
    def cap_kvar(self) -> float:
        return self.capacity.controllable_kvar

    @property
    def persistence_hours(self) -> float:
        return self.persistence.mean_hours

    @property
    def flex_p_swing(self) -> float:
        return self.flexibility.p_swing

    @property
    def flex_q_swing(self) -> float:
        return self.flexibility.q_swing

    def flex_scalar(self, w_P: float = 1.0, w_Q: float = 1.0) -> float:
        return self.flexibility.scalar(w_P, w_Q)

    @property
    def br_auth_hours(self) -> float:
        return self.retained.br_auth_hours if self.retained else self.persistence.mean_hours

    @property
    def exposure_kwh(self) -> float:
        """Capacity-time exposure BR_exp, first-order rectangular: BR_flex_scalar * BR_auth."""
        if self.retained is None:
            return 0.0
        return self.flex_scalar() * self.retained.br_auth_hours


def traverse_identity_graph(graph: IdentityGraph, cred_id: str, policy: Policy) -> "set[str]":
    """TraverseIdentityGraph -> reachable DER set for a compromised credential."""
    return resolve_addressable_ders(graph, graph.creds[cred_id], policy)


def sum_der_capability(graph: IdentityGraph, cred_id: str, reachable: "set[str]") -> Capability:
    """SumDERCapability -> aggregate nameplate controllable kW/kVAr under the credential scope."""
    cred = graph.creds[cred_id]
    total = ZERO_CAPABILITY
    for der_id in reachable:
        total = total + commandable_capacity(graph.ders[der_id], cred.scope_for(der_id))
    return total


def sum_der_flexibility(
    graph: IdentityGraph, cred_id: str, reachable: "set[str]",
    states: "dict[str, DeviceState] | None" = None,
) -> FlexInterval:
    """Aggregate state-dependent BR_flex over the reachable DERs under the credential scope."""
    cred = graph.creds[cred_id]
    states = states or {}
    total = ZERO_FLEX
    for der_id in reachable:
        total = total + commandable_flexibility(
            graph.ders[der_id], cred.scope_for(der_id), states.get(der_id))
    return total


def analyze(
    graph: IdentityGraph, cred_id: str, policy: Policy, *,
    seed: int = 0, states: "dict[str, DeviceState] | None" = None,
) -> BlastRadius:
    """Compute the cyber-side blast radius for a compromised credential under a policy."""
    reachable = traverse_identity_graph(graph, cred_id, policy)
    capacity = sum_der_capability(graph, cred_id, reachable)
    flexibility = sum_der_flexibility(graph, cred_id, reachable, states)
    persistence = estimate_persistence(graph.creds[cred_id], policy, seed=seed)
    retained = decompose_persistence(graph.creds[cred_id], policy, seed=seed)
    return BlastRadius(
        locus_cred=cred_id,
        reachable_ders=frozenset(reachable),
        reach=len(reachable),
        capacity=capacity,
        persistence=persistence,
        flexibility=flexibility,
        retained=retained,
    )
