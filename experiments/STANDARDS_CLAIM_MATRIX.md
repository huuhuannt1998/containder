# Standards claim matrix

Every load-bearing standards claim in the manuscript, the free source of record for it, the
verbatim text that supports it, and what remains unverified. "Free source" means a document a
reader can check without purchase.

**Editions.** IEEE 2030.5-2018 is the edition the accessible sources quote. IEEE 2030.5-2023
(published December 2024) supersedes it and **could not be obtained**: it is paywalled at roughly
US$255 and is not in the IEEE GET free-standards programme. Every row below is therefore
evidenced against the 2018 edition and its profile, and the final column states the exposure.

**Sources.**

- **SAND** — Sandia National Laboratories, *Recommendations for Trust and Encryption in DER
  Interoperability Standards*, SAND2019-1490, February 2019. DOI 10.2172/1761841. Full text
  freely available from OSTI. Quotations below are verbatim from the OSTI PDF.
- **CSIP** — SunSpec Common Smart Inverter Profile Implementation Guide v2.1, March 2018.
- **COG** — Cogito Group, "IEEE 2030.5 CA Types", a PKI vendor's public description of the
  Manufacturing PKI, used only as an independent second witness where it agrees with SAND.
- **VEND** — vendor and test-house descriptions of the 2023 revision's scope, used only for the
  edition-delta row and never for a load-bearing claim.

---

## S1 — A device certificate's lifetime is indefinite

**Supported.** SAND §4.1, verbatim:

> "The IEEE 2030.5/CSIP PKI is different than other PKI's in the use of non-expiring certificates
> and the explicit prohibition of CRL and OCSP. Once issued, a device certificate has an
> indefinite lifetime, so it is always valid."

SAND §6.4 additionally quotes the management statements directly:

> "'IEEE 2030.5 Cert — Indef.' is meant to convey that Manufacturing PKI certificates are
> indefinitely valid and the check is limited solely to a check of the signatures on the
> certificate chain."

Second witness, COG: "As the certificates in the Manufacturing PKI are indefinitely valid, a
check for validity is limited to only a check of the signatures on the certificate chain."

*Residual risk:* 2023 clause unread. Low — two independent sources agree on the 2018 position.

---

## S2/S3 — CRL and OCSP are prohibited **for IEEE 2030.5 certificates**

**Supported, with a qualification the manuscript previously omitted.** SAND §4.1, verbatim:

> "In fact, IEEE 2030.5 prohibits their use. This means that Certificate Authorities (CA) shall
> not maintain CRLs or run OSCP servers, and clients and servers shall not check for CRLs or OCSP
> servers to verify certificate validity."

The qualification is in SAND §6.4, quoting the standard's own wording:

> "The phrase 'Optional OCSP' means that the server device (and optionally, the client device) may
> utilize Online Certificate Status Protocol as an additional mechanism to determine if a
> certificate has been revoked. **OCSP may only be used to verify non-IEEE 2030.5 certificates.**"

So OCSP is not absent from the protocol; it is scoped away from the certificates that carry DER
control identity. **The manuscript must say "prohibited for IEEE 2030.5 certificates", not
"prohibited".** The earlier unqualified wording is an overstatement that a reviewer holding the
standard would catch.

*Residual risk:* 2023 clause unread.

---

## S4 — Local allow/deny listing is available, and is the sanctioned substitute

**Supported.** SAND §4.1:

> "This does not preclude servers or clients from maintaining or obtaining their own list of
> blacklisted or whitelisted devices if the operator prefers."

SAND §4.1.2 describes enrollment as whitelist insertion:

> "The utility will enroll a device (i.e. add to the utility server whitelist) after entering a
> contractual relationship with the end user."

**It is permitted, not required**, and SAND is explicit that it is a weaker instrument than
revocation:

> "A blacklist is essentially a local CRL but without the process, rigor and verification behind
> its issuance."

> "With fragmented blacklists and policies, it is possible for a stolen device certificate that
> was disallowed in one region to be used in a different region to gain access because it was only
> locally blacklisted."

This is the row that governs the manuscript's motivation, and it must be stated precisely: local
denial exists and can refuse future authorization. What it does not do is bound the end-to-end
time to termination of all effective physical authority — it is local, unsynchronised, and says
nothing about an already-open session or an already-issued control. That gap, not the absence of
a denial mechanism, is what CONTAINDER addresses.

---

## S5 — A short-lived operational credential is **permitted**

**Supported, and this row is stronger than the manuscript previously claimed.** The earlier
version recorded S5 (certificate replacement / re-enrollment) as "unsupported by any source". It
is in fact addressed directly. SAND §6.4:

> "Inverter manufacturers strictly following these guidelines are **not required to limit the life
> of a device certificate** or to validate IEEE 2030.5 certificates using OCSP or CRLs."

"Not required to limit" is permissive, not prohibitive. SAND §6.4 also sets out the mechanics of
certificate maintenance as ordinary practice and names one year as the usual renewal interval:

> "(1 year certificate life is the usual recommended renewal interval). This requires that a key
> pair be generated for each device prior to expiration, a Certificate Signing Request (CSR)
> issued to the CA, and the CA then returning the signed certificate to the device for secure
> placement."

Two consequences for the manuscript, both of which narrow it in the right direction:

1. CONTAINDER's short-lived operational credential is **compatible with the standard's guidance
   rather than a departure from it**. The contribution is not the idea of a short-lived
   certificate, which SAND already recommends; it is the enforcement of expiry across the
   session and command-effect layers, which nothing in the accessible material addresses.
2. The difference between CONTAINDER and the recommended practice is **quantitative** — hours
   against a year — and must be presented as such.

---

## S6 — Identity derives from the certificate (LFDI/SFDI)

**Supported**, SAND §3.1.1 and CSIP §5.2.1.2 independently. *Residual risk:* low.

---

## S7 — FunctionSetAssignments scopes which operations an identity may invoke

**Supported for function-level scoping** (CSIP §5.2.3.1). **Not supported for numeric value
constraints.** No accessible source establishes that IEEE 2030.5 or CSIP can express a bound of
the form "reactive power must remain at or below −φ kvar" as an authorization attached to an
identity.

This is the row on which the manuscript's design framing turns, and the honest position is:

> CONTAINDER's value-constrained authorization is a **layer above** FunctionSetAssignments,
> enforced by the DERMS or the gateway proxy, not a native IEEE 2030.5 capability. Messages
> crossing the downstream interface remain protocol-conformant; the constraint is applied before
> forwarding.

The manuscript states this explicitly rather than implying native expressiveness.

---

## S8 — Scheduled DER controls persist for their stated duration

**Supported for 2018** (CSIP §4.4.2, §6.1.8.2). **Most exposed row to edition drift.** Multiple
vendor and test-house descriptions of the 2023 revision state that it

> "maintains backward compatibility with IEEE Std 2030.5-2018, except for elimination of the
> requirements for mandatory DERControl modes, while providing an expanded feature set."

Eliminating *mandatory* modes is a conformance change, not necessarily a change to the persistence
semantics of a scheduled control. But it is in S8's territory, it is unread, and the manuscript
says so.

---

## S9 — The adversary model is the one the standard's own analysis names

**Supported.** SAND §6.4 states the threat CONTAINDER is built against, in the standard analysis's
own words:

> "If a manufacturer decides not to implement certificate revocation and replacement, for a
> critical period an adversary could potentially extract a private key from a device and
> masquerade as the legitimate device without other nodes being aware of the device compromise."

---

## What no accessible source establishes

Named so that absence is not mistaken for evidence:

1. Whether an **active mutual-TLS session** must be revalidated or closed when the credential
   authorizing it expires. Nothing in SAND or CSIP addresses it. CONTAINDER treats it as
   unspecified and supplies enforcement.
2. Whether **already-issued DERControls are cancelled** when an identity is denied or its
   credential expires. Likewise unaddressed.
3. Whether **numeric bounds** are expressible in FunctionSetAssignments (S7 above).
4. Any **clause-level text of IEEE 2030.5-2023**.

Items 1 and 2 are precisely the two layers the manuscript's mechanism ablation measures, and the
fact that the accessible standards material is silent on both is the motivation for measuring
them.
