# pkimodel — CONTAINDER cyber-side blast-radius engine (M2)

`pkimodel` turns the CONTAINDER four-radius formalism (M1) into executable code. It computes
the **cyber-side** blast radii for a compromise locus in an IEEE 2030.5 / CSIP DER
authorization graph:

- **`BR_reach`** — DERs a compromised credential can *address* (topological reach).
- **`BR_cap`** — aggregate commandable authority (kW, kVAr) under the credential's
  function-set *scope*.
- **`BR_time`** — retained-capability *duration distribution* under the credential lifecycle.

`BR_phys` (feeder-level physical consequence) is deliberately out of scope — it is owned by
the M4 co-simulation pipeline; this engine produces the commandable-capacity input `BR_phys`
consumes.

## Why reach and scope are separate

The central modeling choice: a credential's **reach** (which DER nodes it can address) is
independent of its **scope** (which CSIP function sets it may invoke at each DER). This is
what lets two compromises share an addressable set — *identical topological reach* — yet
differ by orders of magnitude in capacity and persistence. That is the M1 separation
argument, and it is enforced as a regression test in `tests/test_counterexample.py`.

## Layout

```
pkimodel/
  der.py           DER model + CSIP function-set -> commandable-capacity kernel
  cert_graph.py    identity/delegation graph (nodes, typed edges, credentials)
  policy_scope.py  parameterized policy engine (4 ACL realism levels)
  lifecycle_sim.py credential-lifecycle / persistence estimation (distribution)
  blast_radius.py  the engine: reach, capacity, persistence
  scenario.py      YAML/JSON scenario loader + deterministic synthetic generator
scenarios/
  counterexample.{json,yaml}   the committed M1 counterexample
tests/             unit tests incl. the M1 counterexample regression
```

## Usage

```python
from pkimodel import analyze
from pkimodel.scenario import load_scenario   # or build_scenario(spec_dict)

sc = load_scenario("scenarios/counterexample.json")
br = analyze(sc.graph, "cred_beta", sc.policy, seed=1)
print(br.reach, br.cap_kw, br.cap_kvar, br.persistence.mean_hours)
```

## Function-set fidelity

Control modes follow base IEEE 2030.5-2018 / CSIP `DERControlBase`
(`opModMaxLimW`, `opModFixedW`, `opModFixedVar`, `opModVoltVar`, `opModVoltWatt`,
`opModFreqWatt`, `opModConnect`, `opModEnergize`). `opModExpLimW` is intentionally **not**
modeled as a base mode — it is a CSIP-AUS (AS/NZS 4777.2) extension.

## Tests

```
python3 -m pytest -q
```

The authorization model is deliberately parameterized (four ACL realism levels spanning
single-device through whole-aggregator-fleet scope); a hardcoded permissive ACL would
overstate what a stolen certificate can do. Vary `Policy.acl_realism_level` in ablation.
