# CONTAINDER — Manuscript Outline (ratified under PI delegation, 2026-07-18)

**Working title:** CONTAINDER: A Four-Radius Blast-Radius Model and Attested Ephemeral
Credentials for Containing Authorization Compromise in IEEE 2030.5 DER Ecosystems

**Venue (provisional):** Q1 security journal; IEEEtran double-column, ~12 pp incl. refs/bios
(target IEEE TDSC; final venue decided at submission). Framing: **security-led** —
credential lifecycle and containment lead; feeder consequence supports (dec_01KXT26ZN6XNQTVWX53NJDPHTJ).

**Iron-Law status of each section** — R = real/complete now; P = pre-registered protocol +
marked result placeholders (no measured numbers exist yet, no testbed in the authoring session).

| # | Section | Status | Primary RKA anchors |
|---|---------|--------|---------------------|
| 1 | Abstract | R (claims scoped to what exists) | manifest |
| 2 | Introduction & Contributions | R | jrn_01KXT490ZD (defs), dec RQ1-RQ5 |
| 3 | Background & Threat Model | R | jrn_01KXT490ZD, jrn_01KXT3JP (SAND §4.1), lit Passos, lit SAND |
| 4 | Four-Radius Blast-Radius Formalism | R | jrn_01KXT490ZD, jrn_01KXT49DN (separation+counterexample), dec_01KXT4C6 (BR_phys unit) |
| 5 | Separation from Attack-Graph Reachability | R | jrn_01KXT49DN, jrn_01KXT3PV (mapping table), dec_01KXT4C1 (Gate One) |
| 6 | CONTAINDER Design (attested ephemeral scope-bound creds; non-renewal containment) | R (design) / P (prototype) | dec_01KXT28WT (novelty), dec RQ4, jrn_01KXT3JP (SAND constraints) |
| 7 | Cyber-Side Analysis Engine (pkimodel) | **R (implemented, 14/14 tests)** | M2 report, code |
| 8 | Feeder Co-Simulation Methodology | R (design) / P (results) | M4 spec, dec_01KXT27V (testbed) |
| 9 | Evaluation Protocol (pre-registered) | P | jrn_01KXTQR7 (pre-registration, SHA-256), scenario_matrix.yaml |
| 10 | Related Work | R | jrn_01KXT4CF (Passos differentiation), jrn_01KXT3PV, dec_01KXT28WT |
| 11 | Ethics & Responsible Disclosure | R | M3 scope boundary (synthetic keys only) |
| 12 | Limitations & Conclusion | R | this outline's status column |

**Non-negotiables (honesty contract):**
- Sections 6(prototype), 8(results), 9 carry a visible "results pending sweep" marker; no
  fabricated tables/figures. Placeholders reference the pre-registered matrix by its SHA-256.
- Related Work differentiates from Passos et al. 2025 on three axes (no redesign / no feeder
  quantification / no blast-radius formalism) per jrn_01KXT4CF.
- Every `\cite` resolves to a verified refs.bib entry; unverified sources sit in REFS_TODO.md
  until validated, never cited.

**Framing choice (ratified):** motivation-led intro (DER attack surface + the 2030.5
identity/credential conflation), because the contribution is a system/architecture
dependability result, not a standalone crypto result (TDSC scope constraint,
jrn_01KXT4NN8Z).
