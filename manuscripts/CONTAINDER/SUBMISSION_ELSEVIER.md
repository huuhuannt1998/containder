# IJCIP submission front-matter (Elsevier required elements)

Paste these into Editorial Manager at submission. They are separate portal
fields for Elsevier; when the manuscript is converted to `elsarticle` for the
revision stage they also go in the `.tex` (`\begin{highlights}`, front matter,
`\section*{CRediT ...}`, etc.).

Length check (IJCIP research-paper rule = 5,000-10,000 words incl. abstract,
excl. references): manuscript body ~7,900 words. WITHIN RANGE. No page limit
applies (Elsevier is word-count governed, not page-count).

---

## Highlights (3-5 bullets, each <= 85 characters)

- Four-dimensional DER compromise-impact model beyond reachability alone
- Reachability-only impact omits scope, persistence, and feeder-state effects
- CONTAINDER: attested short-lived scope-bound credentials, non-renewal containment
- Real X.509/mTLS prototype with OpenDSS IEEE 8500- and 123-bus evaluation
- Least-privilege scope keeps legitimate volt-var utility while denying export

## Declaration of Competing Interest

The author declares that he has no known competing financial interests or
personal relationships that could have appeared to influence the work reported
in this paper.

## Data Availability Statement

The analysis engine, the X.509/mutual-TLS credential service, the OpenDSS feeder
experiment scripts, the pre-registration document with its content hash, and all
result files will be released in a public repository upon publication. The
IEEE 8500-node and IEEE 123-bus test feeders used in the evaluation are publicly
available from the referenced OpenDSS distributions.

## CRediT author statement

Huan Bui: Conceptualization, Methodology, Software, Validation, Formal analysis,
Investigation, Data curation, Writing - original draft, Writing - review and
editing, Visualization.

---

## Build status (updated 2026-07-30)

The elsarticle conversion is **done**, not a remaining task. `main_els.tex` is the primary
build and `main.tex` (IEEEtran) is kept only as a contingency.

- `elsarticle.cls` is installed under `TEXMFHOME`; verify with `kpsewhich elsarticle.cls`.
- Build: `latexmk -pdf -interaction=nonstopmode main_els.tex`.
- Last clean build: 0 LaTeX errors, 0 undefined references, 0 undefined citations, 38 pages
  in the `review` (double-spaced, line-numbered) format Elsevier expects. Page count is a
  review-format artifact and is not the submission length criterion; IJCIP is word-count
  governed.
- References already use `elsarticle-num`.
- The vendored `els_build/elsarticle.zip` is a fallback for machines without the `TEXMFHOME`
  install and is not used by the recipe above.

Full recipe, including the `refs.bib` DOI underscore escaping and the stale-`.bbl` trap, is in
the repository `README.md` under "Building the manuscript".
