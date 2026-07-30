"""Scenario specs + synthetic generator (M2 T2.6).

A scenario spec is a plain dict (loadable from YAML or JSON) describing nodes, DERs, edges,
credentials, and a policy. ``build_scenario`` materializes it into an
:class:`~pkimodel.cert_graph.IdentityGraph` plus a :class:`~pkimodel.policy_scope.Policy`.

``generate_spec`` is the deterministic, seedable synthetic generator: real utility
authorization graphs are not public, so this releasable generator stands in for them,
varying fleet size, aggregator centrality, feeder/site scope, and tenant separation.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from .cert_graph import (
    IdentityGraph,
    Node,
    NodeType,
    EdgeType,
    Credential,
    CredType,
)
from .der import DER, DERType, FunctionSet
from .policy_scope import Policy, AclRealismLevel

_DEFAULT_HORIZON = 2 * 365 * 24 * 3600.0


@dataclass
class Scenario:
    graph: IdentityGraph
    policy: Policy
    cred_ids: "list[str]" = field(default_factory=list)


def _parse_scope(scope: "dict | None") -> "dict[str, frozenset[FunctionSet]]":
    out: "dict[str, frozenset[FunctionSet]]" = {}
    for der_id, fs_list in (scope or {}).items():
        out[der_id] = frozenset(FunctionSet(v) for v in fs_list)
    return out


def build_scenario(spec: dict) -> Scenario:
    """Materialize a scenario spec dict into a graph + policy."""
    g = IdentityGraph()

    for n in spec.get("nodes", []):
        g.add_node(Node(
            node_id=n["id"],
            node_type=NodeType(n["type"]),
            feeder=n.get("feeder"),
            site=n.get("site"),
            aggregator=n.get("aggregator"),
        ))

    for d in spec.get("ders", []):
        g.add_der(DER(
            der_id=d["id"],
            der_type=DERType(d["type"]),
            host_node=d["host_node"],
            nameplate_kw=float(d.get("nameplate_kw", 0.0)),
            nameplate_kvar=float(d.get("nameplate_kvar", 0.0)),
            max_charge_kw=float(d.get("max_charge_kw", 0.0)),
            max_discharge_kw=float(d.get("max_discharge_kw", 0.0)),
        ))

    for e in spec.get("edges", []):
        g.add_edge(e["src"], e["dst"], EdgeType(e["type"]))

    cred_ids: "list[str]" = []
    for c in spec.get("credentials", []):
        g.add_credential(Credential(
            cred_id=c["id"],
            cred_type=CredType(c["cred_type"]),
            bound_node=c["bound_node"],
            issuer=c.get("issuer"),
            ttl_seconds=c.get("ttl_seconds"),
            attestation_gated=bool(c.get("attestation_gated", False)),
            scope=_parse_scope(c.get("scope")),
        ))
        cred_ids.append(c["id"])

    p = spec.get("policy", {}) or {}
    policy = Policy(
        acl_realism_level=AclRealismLevel(p.get("acl_realism_level", "feeder")),
        default_ttl_seconds=p.get("default_ttl_seconds"),
        attestation_detect_prob=float(p.get("attestation_detect_prob", 0.0)),
        revocation_enabled=bool(p.get("revocation_enabled", False)),
        revocation_latency_seconds=p.get("revocation_latency_seconds"),
        analysis_horizon_seconds=float(p.get("analysis_horizon_seconds", _DEFAULT_HORIZON)),
    )
    return Scenario(graph=g, policy=policy, cred_ids=cred_ids)


def load_spec(path: "str | Path") -> dict:
    """Load a scenario spec from a .yaml/.yml (needs PyYAML) or .json file."""
    path = Path(path)
    text = path.read_text()
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # optional dependency
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "PyYAML is required to load .yaml specs; install pkimodel[yaml] or use the .json spec"
            ) from exc
        return yaml.safe_load(text)
    return json.loads(text)


def load_scenario(path: "str | Path") -> Scenario:
    return build_scenario(load_spec(path))


def generate_spec(
    *,
    seed: int = 0,
    fleet_size: int = 50,
    n_feeders: int = 3,
    aggregator_centrality: float = 1.0,
    n_tenants: int = 1,
    bess_fraction: float = 0.1,
    acl_realism_level: str = "feeder",
) -> dict:
    """Deterministic synthetic identity/delegation scenario (T2.6).

    Parameters (all knobs, no constants):
      * ``fleet_size`` — number of DER-hosting devices.
      * ``aggregator_centrality`` in [0,1] — fraction of devices under one central aggregator;
        the remainder are split across secondary (per-tenant) aggregators.
      * ``n_feeders`` — devices are round-robined across this many feeders.
      * ``n_tenants`` — credential/aggregator isolation groups.
      * ``bess_fraction`` — probability a device hosts a BESS (else PV).

    Fully determined by ``seed`` (only the PV/BESS draw is randomized).
    """
    rng = random.Random(seed)
    nodes: "list[dict]" = []
    ders: "list[dict]" = []
    edges: "list[dict]" = []

    n_central = max(1, int(round(fleet_size * aggregator_centrality)))
    agg_ids = ["agg_central"] + [f"agg_t{t}" for t in range(1, max(1, n_tenants))]
    for a in agg_ids:
        nodes.append({"id": a, "type": "aggregator", "aggregator": a})

    for i in range(fleet_size):
        feeder = f"f{i % n_feeders}"
        site = f"s{i}"
        tenant = i % max(1, n_tenants)
        agg = agg_ids[0] if i < n_central else agg_ids[min(tenant, len(agg_ids) - 1)]
        dev = f"dev{i}"
        nodes.append({
            "id": dev, "type": "device",
            "feeder": feeder, "site": site, "aggregator": agg,
        })
        edges.append({"src": agg, "dst": dev, "type": "delegation"})
        if rng.random() < bess_fraction:
            ders.append({
                "id": f"der{i}", "type": "bess", "host_node": dev,
                "nameplate_kw": 5000.0, "nameplate_kvar": 2000.0,
                "max_charge_kw": 5000.0, "max_discharge_kw": 5000.0,
            })
        else:
            ders.append({
                "id": f"der{i}", "type": "pv", "host_node": dev,
                "nameplate_kw": 8.0, "nameplate_kvar": 3.0,
            })

    # Representative compromised credential, bound to a DEVICE (dev0) so that all four ACL
    # realism levels resolve to a meaningful reach (a feeder/site-scoped policy on a
    # feeder-less aggregator would resolve to nothing). Bind to an aggregator explicitly
    # via a hand-written spec when modelling an aggregator/DERMS compromise at fleet scope.
    probe_node = "dev0" if fleet_size > 0 else agg_ids[0]
    creds = [{
        "id": "cred_probe", "cred_type": "operational", "bound_node": probe_node,
        "ttl_seconds": 21600, "attestation_gated": True,
        "scope": {"*": ["opModVoltVar", "opModMaxLimW"]},
    }]

    return {
        "nodes": nodes, "ders": ders, "edges": edges, "credentials": creds,
        "policy": {
            "acl_realism_level": acl_realism_level,
            "attestation_detect_prob": 0.5,
            "revocation_enabled": False,
        },
    }
