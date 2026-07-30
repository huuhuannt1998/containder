"""Parameterized authorization policy engine (M2 T2.2 / T2.3).

Every permissiveness knob is a parameter, never a constant (mission constraint): the ACL
realism level, the credential-lifetime model, the attestation detection probability, and
the revocation model. A hardcoded permissive ACL would let a reviewer dismiss the paper as
overstating what a stolen certificate can do, so all of it is config-driven and varied in
ablation.

``resolve_addressable_ders`` is the ResolveAuthorizedDERs primitive: the set of DER nodes a
compromised credential can ADDRESS under a policy. Function-set SCOPE (what is authorized
at each addressed DER) is a separate credential attribute, so two credentials can share an
addressable set (identical reach) yet differ in capacity.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .cert_graph import IdentityGraph, Credential, NodeType


class AclRealismLevel(str, Enum):
    """Four ACL realism levels spanning single-device through whole-aggregator-fleet scope."""

    SINGLE_DEVICE = "single_device"   # only DERs hosted by the bound device
    SITE = "site"                     # DERs at the same site / premises
    FEEDER = "feeder"                 # DERs in the same feeder FSA group
    FLEET = "fleet"                   # all DERs under the credential's aggregator


@dataclass
class Policy:
    """``pi = (L, Att, A)``. Scope ``A`` is carried per-credential; ``L`` / ``Att`` here."""

    acl_realism_level: AclRealismLevel = AclRealismLevel.FEEDER
    # lifetime model L: default TTLs by cred-type value (seconds); None = indefinite.
    default_ttl_seconds: "dict[str, float | None] | None" = None
    # attestation detection probability per renewal cycle (Att); 0.0 = never denies renewal.
    attestation_detect_prob: float = 0.0
    # revocation model for non-attestation-gated credentials.
    revocation_enabled: bool = False                 # baseline 2030.5 forbids revocation.
    revocation_latency_seconds: "float | None" = None
    # cap standing in for 'indefinite' lifetime when integrating persistence.
    analysis_horizon_seconds: float = 2 * 365 * 24 * 3600.0
    # session-expiry enforcement (T_sess): close sessions at/near credential expiry.
    enforce_session: bool = True
    session_max_age_seconds: "float | None" = None
    unmanaged_session_overhang_seconds: float = 3600.0
    # command-effect cleanup (T_cmd): bound the duration of adversary-issued controls.
    enforce_command_cleanup: bool = True
    command_max_duration_seconds: "float | None" = None
    unmanaged_command_overhang_seconds: float = 4 * 3600.0


def resolve_addressable_ders(
    graph: IdentityGraph, cred: Credential, policy: Policy
) -> "set[str]":
    """ResolveAuthorizedDERs: DER set a compromised credential can address under ``policy``.

    Reach expands from the credential's bound node according to the ACL realism level. This
    is topological reach only; the returned set is NOT filtered by function-set scope.
    """
    node = graph.nodes.get(cred.bound_node)
    if node is None:
        return set()

    level = policy.acl_realism_level

    if level == AclRealismLevel.SINGLE_DEVICE:
        return graph.ders_of_device(cred.bound_node)

    if level == AclRealismLevel.SITE:
        if node.site is not None:
            return graph.ders_in_site(node.site)
        return graph.ders_of_device(cred.bound_node)

    if level == AclRealismLevel.FEEDER:
        if node.feeder is not None:
            return graph.ders_in_feeder(node.feeder)
        return graph.ders_of_device(cred.bound_node)

    if level == AclRealismLevel.FLEET:
        agg = node.aggregator
        if agg is None and node.node_type == NodeType.AGGREGATOR:
            agg = cred.bound_node
        reachable: "set[str]" = set()
        if agg is not None:
            reachable |= graph.ders_in_fleet(agg)
        # an aggregator/gateway credential also reaches DERs on devices it delegates to.
        for dev in graph.devices_behind(cred.bound_node):
            reachable |= graph.ders_of_device(dev)
        reachable |= graph.ders_of_device(cred.bound_node)
        return reachable

    return set()
