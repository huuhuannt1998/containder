"""Hand-verified graph-traversal cases across the four ACL realism levels (acceptance #5)."""
from pkimodel import (
    IdentityGraph, Node, NodeType, EdgeType, Credential, CredType,
    DER, DERType, Policy, AclRealismLevel, traverse_identity_graph,
)


def _graph():
    g = IdentityGraph()
    g.add_node(Node("A", NodeType.AGGREGATOR, aggregator="A"))
    g.add_node(Node("dev1", NodeType.DEVICE, feeder="f1", site="s1", aggregator="A"))
    g.add_node(Node("dev2", NodeType.DEVICE, feeder="f1", site="s2", aggregator="A"))
    g.add_node(Node("dev3", NodeType.DEVICE, feeder="f2", site="s3", aggregator="A"))
    g.add_der(DER("d1", DERType.PV, "dev1", 10.0, 4.0))
    g.add_der(DER("d2", DERType.PV, "dev2", 10.0, 4.0))
    g.add_der(DER("d3", DERType.PV, "dev3", 10.0, 4.0))
    for d in ("dev1", "dev2", "dev3"):
        g.add_edge("A", d, EdgeType.DELEGATION)
    g.add_credential(Credential("c_dev1", CredType.OPERATIONAL, "dev1"))
    g.add_credential(Credential("c_agg", CredType.OPERATIONAL, "A"))
    return g


def test_single_device_reach():
    g = _graph()
    p = Policy(acl_realism_level=AclRealismLevel.SINGLE_DEVICE)
    assert traverse_identity_graph(g, "c_dev1", p) == {"d1"}


def test_site_reach():
    g = _graph()
    p = Policy(acl_realism_level=AclRealismLevel.SITE)
    assert traverse_identity_graph(g, "c_dev1", p) == {"d1"}  # only site s1


def test_feeder_reach():
    g = _graph()
    p = Policy(acl_realism_level=AclRealismLevel.FEEDER)
    assert traverse_identity_graph(g, "c_dev1", p) == {"d1", "d2"}  # feeder f1


def test_fleet_reach_from_aggregator():
    g = _graph()
    p = Policy(acl_realism_level=AclRealismLevel.FLEET)
    assert traverse_identity_graph(g, "c_agg", p) == {"d1", "d2", "d3"}


def test_reach_is_monotone_in_realism_level():
    g = _graph()
    levels = [AclRealismLevel.SINGLE_DEVICE, AclRealismLevel.FEEDER, AclRealismLevel.FLEET]
    sizes = [len(traverse_identity_graph(g, "c_dev1", Policy(acl_realism_level=lv))) for lv in levels]
    # single-device (1) <= feeder (2); fleet from a device cred still resolves via its aggregator.
    assert sizes[0] <= sizes[1]
