# IJCIP submission front-matter (Elsevier required elements)

Paste these into Editorial Manager at submission. `highlights.tex` is the authoritative copy of
the Highlights and is submitted as a separate file; the bullets below are a transcription of it
and `check_highlights.py` verifies the character limits against that file, not this one.

Length (IJCIP research-paper recommendation = 5,000-10,000 words incl. abstract, excl.
references, verified against the live guide-for-authors on 2026-07-31):

- Body prose incl. abstract, excluding float contents and headings: **~9,630 words. IN RANGE.**
- Same, counting figure/table captions and section headings: ~10,320.

The recommendation is a range, not a hard cap, and the count that most directly matches
"manuscript text" is the first. Reviewers who count captions will see a ~3% overage; if the
editor asks for a cut, Section 8's withdrawal material is the intended donor, since it documents
what earlier versions claimed rather than what this one measures.

---

## Highlights (3-5 bullets, each <= 85 characters)

- IEEE 2030.5 binds DER control authority to a long-lived, unrevocable identity
- CONTAINDER issues attested, short-lived, scope-bound operational credentials
- Non-renewal replaces revocation; sessions and command effects expire with it
- Bounding the volt-var curve contains a compromise; bounding a setpoint does not
- Withhold opModFixedVar: overriding the curve alone breaches the ANSI band

## Declaration of Competing Interest

The author declares that he has no known competing financial interests or personal relationships
that could have appeared to influence the work reported in this paper.

## Data Availability Statement

The analysis engine, the X.509/mutual-TLS credential service, the OpenDSS feeder experiment
scripts, the pre-registration document with its content hash, and all result files accompany this
submission as a single archive and will be deposited under a persistent identifier on acceptance.
Superseded result files are retained in `experiments/results/superseded/` with a README stating
what withdrew each. The IEEE 8500-node and IEEE 123-bus test feeders are publicly available from
the referenced OpenDSS distributions.

## CRediT author statement

Huan Bui: Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation,
Data curation, Writing - original draft, Writing - review and editing, Visualization.

---

## Build status (updated 2026-07-31)

`main.tex` is the primary build; `main.tex` (IEEEtran) is **broken** -- it still inputs
`sections/04_separation`, deleted in 37156d0 -- and is not needed for IJCIP.

- Build: `latexmk -pdf -interaction=nonstopmode main.tex`.
- Last clean build: 0 errors, 0 undefined references, 0 undefined citations, 0 overfull boxes,
  **48 pages** in the `review` (double-spaced, line-numbered) format Elsevier expects. Page count
  is a review-format artifact; IJCIP is word-count governed.
- `elsarticle.cls` is installed under `TEXMFHOME`; verify with `kpsewhich elsarticle.cls`. The
  vendored `els_build/elsarticle.zip` is a fallback and is not used by the recipe above.
- References use `elsarticle-num`. Zero `[n. d.]` entries. Two benign `.blg` warnings remain
  (`empty pages` for `ou2005mulval` and `smith2020letsrevoke`); USENIX Security and NDSS papers
  are unpaginated.

## Pre-submission gates

Run all three from the repository root:

```
python3 manuscripts/CONTAINDER/check_numbers.py      # every numeral traces to results/*.json
python3 manuscripts/CONTAINDER/check_highlights.py   # 3-5 bullets, <= 85 chars each
python3 experiments/validate_matrix.py               # pre-registration SHA-256 still matches
```

`check_numbers.py` scans the section files **and** `main.tex`, since the abstract carries the
headline numerals and was previously unchecked. It also tracks withdrawn numerals separately and
fails if one is used outside an explicit withdrawal. Regenerate derived statistics first with
`python3 experiments/derive_reported_stats.py` if any experiment has been re-run.

Full recipe, including the `refs.bib` DOI underscore escaping and the stale-`.bbl` trap, is in the
repository `README.md` under "Building the manuscript".
