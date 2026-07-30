# CONTAINDER — artifact repository

Three installable packages plus the experiment drivers behind the manuscript:

| Package | Role |
|---|---|
| `pkimodel` | cyber-side impact-dimension analysis engine (M2) |
| `credsvc` | attested X.509 / mutual-TLS credential service |
| `power` | OpenDSS feeder pipeline and test feeders |

Install everything in one editable install; no `PYTHONPATH` is required:

```
python3 -m pip install -e .
```

## pkimodel — cyber-side impact-dimension engine (M2)

`pkimodel` turns the CONTAINDER four-impact-dimension model (M1) into executable code. It
computes the **cyber-side** dimensions for a compromise locus in an IEEE 2030.5 / CSIP DER
authorization graph. The `BR_` prefix is retained in code and notation for continuity; the
manuscript calls these *dimensions*, not *radii*, because the four quantities have different
mathematical types.

- **`BR_reach`** — DERs a compromised credential can *address* (topological reach).
- **`BR_flex`** — aggregate state-dependent commandable flexibility (kW, kVAr) under the
  credential's function-set *scope* (exposed as `cap_kw` / `cap_kvar`).
- **`BR_auth`** — retained authority: the retained-capability *duration distribution* under the
  credential lifecycle (exposed as `persistence` / `br_auth_hours`).

`BR_phys` (feeder-level physical consequence) is deliberately out of scope for this package — it
is owned by the M4 feeder pipeline under `power/`; this engine produces the commandable-capacity
input `BR_phys` consumes.

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

## Building the manuscript

The manuscript lives in `manuscripts/CONTAINDER/`. Two builds are maintained:

| Target | Class | Status |
|---|---|---|
| `main_els.tex` -> `main_els.pdf` | `elsarticle` | **primary** (IJCIP, Elsevier) |
| `main.tex` -> `main.pdf` | `IEEEtran` | contingency only |

`elsarticle.cls` is installed system-wide under `TEXMFHOME`
(`~/Library/texmf/tex/latex/elsarticle/`), so the primary build needs no special path:

```
cd manuscripts/CONTAINDER
latexmk -pdf -interaction=nonstopmode main_els.tex     # primary
latexmk -pdf -interaction=nonstopmode main.tex         # contingency
```

Confirm the class is visible before building; if this prints nothing, install it with
`tlmgr --usermode install elsarticle` against a TeX Live 2025 repository:

```
kpsewhich elsarticle.cls
```

`manuscripts/CONTAINDER/els_build/elsarticle.zip` is a vendored copy kept only as a fallback for
machines without the `TEXMFHOME` install. It is **not** used by the recipe above; unzip it into
the manuscript directory only if `kpsewhich` comes back empty and `tlmgr` is unavailable.

Two DOIs in `refs.bib` contain underscores and are escaped as `{\_}`
(`10.1007/0-387-24230-9{\_}9`, `10.1007/978-3-540-70567-3{\_}22`). The escape survives BibTeX and
is required: unescaped, the `elsarticle` build raises eight LaTeX errors. If you regenerate
`refs.bib`, delete the stale `main_els.bbl` before rebuilding, or the errors will appear to
persist.

Acceptance for either build is zero LaTeX errors, zero undefined references, and zero undefined
citations.

The authorization model is deliberately parameterized (four ACL realism levels spanning
single-device through whole-aggregator-fleet scope); a hardcoded permissive ACL would
overstate what a stolen certificate can do. Vary `Policy.acl_realism_level` in ablation.
