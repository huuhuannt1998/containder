# Reusable Manuscript Revision Prompts

This file contains two prompts for the manuscript-review workflow:

1. **Initial manuscript presentation and writing review**
2. **Follow-up revision checking after a newer draft is uploaded**

The prompts are designed for research manuscripts in systems, security, AI, HCI, NLP, or related venues. They focus mainly on writing, presentation, structure, clarity, claim calibration, reviewer perception, and submission polish. They also ask the reviewer to flag technical issues only when they affect clarity, evidence, or credibility.

---

## Prompt 1: Initial Manuscript Presentation and Writing Review

```text
I have uploaded a manuscript. Please review it as a senior research-paper reviewer and manuscript editor. Focus mainly on presentation, writing, structure, clarity, claim calibration, reviewer perception, and submission readiness.

Do not primarily propose new technical ideas unless a technical issue directly affects clarity, evidence, claim strength, or reviewer trust. I want detailed, actionable comments that help me revise the paper before submission.

Please follow the workflow below.

0. Source, venue, and evidence discipline

Before giving comments, state your assumptions about:
- The target venue or venue family, if visible from the paper.
- The paper type, such as systems, security, AI, HCI, NLP, empirical study, or theory.
- The strongest evidence in the manuscript.
- The weakest or most fragile evidence in the manuscript.

Use a strict evidence rule: do not treat a claim as safe just because it sounds plausible. Check whether the manuscript itself supports it through experiments, citations, formal argument, or clear limitation text. If a claim is unsupported, ask for evidence or suggest softer wording.

When possible, point to exact sections, pages, paragraphs, figures, or tables. If the uploaded file supports citations or page references, cite them.

1. Overall assessment

Start with a concise but substantive assessment.

Comment on:
- Whether the central story is clear.
- Whether the title, abstract, introduction, contribution list, and results align.
- Whether the manuscript reads like a polished submission or an expanded technical report.
- Whether claims are appropriately calibrated.
- Whether the strongest evidence is placed in the right location.
- What the top 3 to 5 reviewer-facing risks are.

Be direct. If something is strong, say why. If something may trigger reviewer skepticism, identify it clearly.

2. Main revision priorities

Give a prioritized list of the most important revisions.

Focus on:
- Overclaiming or absolute wording.
- Confusing organization.
- Repetition.
- Inconsistent terminology.
- Inconsistent numbers across abstract, introduction, evaluation, tables, and conclusion.
- Claims that are plausible but not supported by the presented evidence.
- Results that should be emphasized more or framed more modestly.
- Negative or mixed results that should be acknowledged earlier.
- Parts that should move to the appendix, related work, discussion, or limitations.
- Places where the manuscript needs more transparent limitation language.

For each priority, explain:
- What the problem is.
- Why a reviewer may care.
- How to fix it.
- Where it appears.

3. Abstract review

Review the abstract for clarity, accuracy, and reviewer impact.

Check:
- Does the first sentence establish the problem clearly?
- Is the motivation specific rather than generic?
- Are the contributions described accurately without overclaiming?
- Are all numbers correct?
- Are ratios, percentage-point changes, and reductions mathematically correct?
- Are results too crowded?
- Is the strongest evidence the centerpiece?
- Are weaker or preliminary results framed honestly?
- Does the abstract avoid cherry-picking?
- Does it avoid hiding important negative or mixed results?

Then provide:
- Concrete abstract problems.
- A revised abstract draft that is shorter, clearer, and more credible.
- A brief explanation of why the revised version is better.

4. Introduction review

Evaluate whether the introduction creates a strong paper narrative.

Check:
- Opening motivation.
- Motivating example.
- Gap statement.
- Key insight.
- Why prior work is insufficient.
- Transition from problem to approach.
- Results paragraph.
- Contribution list.

Identify:
- Sentences that sound too broad, too absolute, or too promotional.
- Repetition.
- Missing transitions.
- Places where reviewer expectations are set too high.
- Places where the paper should distinguish architecture, implementation, benchmark, and evidence.

Then provide:
- A revised introduction outline.
- Suggested wording for the key insight paragraph.
- A shorter, more defensible contribution list.
- Specific sentences that should be softened or rewritten.

5. Claim calibration table

Create a table with three columns:

Original or likely claim | Problem | Safer revised wording

Include claims related to:
- Verification, guarantees, or completeness.
- Model generality.
- Robustness against adaptive or white-box adversaries.
- External benchmark generalization.
- Dominant defense or main mechanism claims.
- User study, usability, or task-success claims.
- Embedding, semantic matching, paraphrase, or classifier robustness.
- Policy-vs-mechanism conclusions.
- Any phrase such as "fundamental," "complete," "guaranteed," "verified," "model-agnostic," "dominant," or "eliminates."

The goal is not to weaken the paper. The goal is to make the claims precise, defensible, and reviewer-proof.

6. Structure and organization

Review the manuscript structure.

Comment on:
- Whether sections appear in a logical order.
- Whether background, threat model, design, implementation, evaluation, discussion, related work, and limitations are cleanly separated.
- Whether design, implementation, and evaluation configuration are mixed together.
- Whether the paper repeats the same point too many times.
- Whether limitations appear early enough.
- Whether the evaluation section is easy to follow.
- Whether the paper needs a clearer roadmap.

Provide:
- A proposed revised section outline.
- Specific movement suggestions, such as "move this table to appendix" or "move this limitation earlier."
- Suggestions for merging, shortening, or reordering sections.

7. Evaluation presentation

Review how the evaluation is presented, focusing on readability and credibility.

Check:
- Whether the evaluation story is easy to understand.
- Whether the main result is clearly identified.
- Whether the right benchmark is emphasized as the strongest evidence.
- Whether controlled benchmark, external benchmark, model-specific results, ablations, and preliminary tests are separated.
- Whether the number of trials is easy to verify.
- Whether table captions explain denominators clearly.
- Whether outcome categories are separated from defense mechanisms.
- Whether statistical claims are presented carefully.
- Whether repeated trials are treated appropriately.
- Whether limitations of each benchmark are stated.

Look for:
- Arithmetic errors.
- Confusing denominators.
- Ambiguous terms such as trial, scenario, attack evaluation, task success, safe tool call, blocked, and bypass.
- Positive results that should be framed as preliminary.
- Negative or mixed results that should be acknowledged more prominently.

Then provide:
- A clearer evaluation narrative.
- Caption improvements.
- A numerical consistency checklist the authors should run before submission.

8. Figures, tables, and layout

Review all important figures and tables.

For each important figure or table, comment on:
- Whether the title and caption are clear.
- Whether the visual is readable in two-column format.
- Whether it supports the main argument.
- Whether labels, legends, axes, fonts, and colors are clear.
- Whether the table duplicates information elsewhere.
- Whether it should be simplified, merged, or moved to the appendix.
- Whether it overstates the result.
- Whether a negative or mixed result is hidden in a dense table.

Also check layout issues:
- Overfull boxes or crowded tables.
- Tiny figure text.
- Page-limit pressure.
- Undefined references or citation placeholders.
- Captions that do not explain denominators.
- Figures that cannot be understood without reading the full text.

Provide:
- Better figure titles.
- Better table titles.
- Caption rewrites.
- Visual simplification suggestions.

9. Terminology and consistency

Identify terminology problems.

Check consistency in:
- System name.
- Title wording.
- Threat model terms.
- Attack category names.
- Evaluation metrics.
- Model names.
- Dataset and benchmark names.
- Policy names.
- Trust, provenance, security, or measurement labels.
- Tool names.
- Section, figure, table, and appendix references.

Provide a terminology normalization table:

Current variants | Recommended term | Notes

10. Writing style and anti-AI-tic audit

Review the prose for readability and style.

Flag:
- Overly long sentences.
- Dense paragraphs.
- Generic academic filler.
- Repeated phrases.
- Hype language.
- Ambiguous pronouns.
- Passive or vague wording.
- Paragraphs without clear topic sentences.
- Sentences that try to make too many points.
- AI-like transition patterns.
- Formulaic phrases such as "it is important to note," "in conclusion," "delve," "pivotal," "intricate," "showcase," "underscore," "facilitate," "utilize," "leverage," "comprehensive," "moreover," and "furthermore," unless genuinely needed.

Please also flag formatting artifacts or generated-text artifacts, such as raw citation placeholders, broken references, search-result IDs, or copied tool-output fragments.

Give at least 15 concrete sentence-level rewrite suggestions, grouped by section. Use a before/after format.

11. Reference and citation integrity

Review citation presentation from a writing and credibility perspective.

Check:
- Claims about prior work that need citations.
- Citations that are too broad or poorly placed.
- Sentences that cite a source but make a stronger claim than the source likely supports.
- Missing citations in background or related work.
- Related-work comparisons that may be unfair or not apples-to-apples.
- Any citation that looks hallucinated, incomplete, stale, or inconsistent.
- Whether the paper distinguishes the authors' results from prior reported numbers.

Do not invent citations. If a claim needs support, say what kind of citation is needed.

12. Venue fit

If the target venue is known, review venue fit.

Comment on:
- Whether the paper uses the expected tone.
- Whether the section order fits the venue.
- Whether limitation, ethics, reproducibility, artifact, or broader-impact sections are needed.
- Whether the contribution style matches the venue.
- Whether math, system detail, user study detail, or benchmark detail is too much or too little for that venue.

If the venue is unknown, list venue-dependent checks the authors should make.

13. Reviewer-risk analysis

List likely reviewer criticisms related to writing, presentation, structure, and evidence framing.

For each criticism, provide:
- Why a reviewer might raise it.
- How serious the risk is.
- How to preempt it.
- Suggested wording to add or revise.

Include risks such as:
- The paper overclaims.
- The baselines look weak or unfair.
- The strongest result is not emphasized.
- The abstract hides a mixed result.
- Evaluation numbers are hard to reconcile.
- The threat model is inconsistent with the attack taxonomy.
- The writing is repetitive.
- Figures or tables are too dense.
- Limitations appear too late.

14. Concrete rewrite package

Provide a focused rewrite package:
- Revised title options.
- Revised abstract.
- Revised key insight paragraph.
- Revised contribution list.
- Revised limitation paragraph.
- Revised evaluation-roadmap paragraph.
- Revised related-work positioning paragraph.

Keep these rewrites concise and submission-ready.

15. Final revision checklist

End with a practical checklist the authors can use before submission.

Include:
- Abstract consistency.
- Introduction story.
- Contribution list.
- Claim calibration.
- Threat model clarity.
- Evaluation denominator consistency.
- Statistical wording.
- Table and figure readability.
- Related-work fairness.
- Citation integrity.
- Limitations placement.
- Venue requirements.
- Anti-AI-tic style cleanup.
- Final proofreading.

Please be detailed, direct, and actionable. Avoid generic advice. Whenever possible, point to exact sections, pages, paragraphs, tables, or figures.
```

---

## Prompt 2: Follow-Up Revision Checking for a New Manuscript Version

```text
I previously uploaded an older version of this manuscript and received revision comments. I have now uploaded a newer version. Please review the newer version and compare it against the prior review direction.

Focus mainly on presentation, writing, structure, clarity, claim calibration, reviewer perception, and whether the revision actually fixed the earlier issues. Do not focus primarily on new technical ideas unless they affect credibility, evidence, or claim strength.

Please follow the workflow below.

0. Inputs and comparison setup

First identify:
- Which manuscript version appears to be the older version.
- Which manuscript version appears to be the newer version.
- What prior review comments or revision goals are being used as the baseline.
- Whether any information is missing for a fair comparison.

Then state whether you are doing:
- A full old-vs-new comparison.
- A new-version-only review guided by prior comments.
- A limited comparison because the old version or prior comments are incomplete.

1. Executive revision diagnosis

Start with a short diagnosis:
- Is the newer manuscript clearly better, somewhat better, unchanged, or worse?
- What are the most successful revisions?
- What earlier problems remain?
- Did the revision introduce any new problems?
- Does the paper now read closer to a polished submission?

Give a readiness judgment:
- Ready after minor editing.
- Needs another focused revision.
- Needs major restructuring.
- Not ready for submission.

2. Revision status tracker

Create a table with these columns:

Prior issue | Status | Evidence in new draft | Remaining problem | Recommended next edit

Use these status labels:
- Fixed.
- Mostly fixed.
- Partially fixed.
- Not fixed.
- Regressed.
- New issue.
- Cannot verify.

Track issues related to:
- Title accuracy.
- Abstract clarity and arithmetic.
- Claim calibration.
- Introduction story.
- Contribution list.
- Evaluation framing.
- Controlled benchmark vs external benchmark emphasis.
- Negative or mixed result disclosure.
- Table and figure readability.
- Terminology consistency.
- Limitation placement.
- Related-work positioning.
- Reference and citation integrity.
- Anti-AI-tic style.

3. Abstract revision check

Compare the newer abstract against the earlier problems.

Check:
- Did it correct arithmetic and ratios?
- Does it make the strongest evidence the centerpiece?
- Does it avoid overloading the reader with too many numbers?
- Does it avoid cherry-picking positive results?
- Does it mention major mixed or preliminary results honestly?
- Does it avoid unsupported guarantee language?
- Does it align with the evaluation tables?

Provide:
- Remaining abstract problems.
- A revised abstract.
- A one-paragraph explanation of what changed and why.

4. Title, framing, and contribution alignment

Check whether the title, framing, and contribution list now match the actual paper.

Evaluate:
- Whether the title overclaims.
- Whether the core phrase is accurate.
- Whether the contribution list is shorter and more defensible.
- Whether each contribution is backed by evidence in the paper.
- Whether the paper clearly separates design, implementation, benchmark, and evaluation contributions.

Provide a cleaned contribution list if needed.

5. Claim calibration audit

Create a table:

Claim in newer draft | Status | Risk | Suggested safer wording

Check for words or ideas such as:
- Verified.
- Complete.
- Guaranteed.
- Eliminates.
- Model-agnostic.
- Dominant.
- Fundamental.
- Robust to adaptive adversaries.
- Generalizes across benchmarks.
- Strongest possible adversary.
- Full recall.
- No false positives.

Flag any claim that is technically plausible but stronger than the evidence supports.

6. Introduction and story-flow check

Evaluate whether the newer introduction now tells a clearer story.

Check:
- Does it open with a concrete problem?
- Does the motivating example support the central claim?
- Does the gap statement avoid attacking prior work unfairly?
- Is the key insight easy to understand?
- Does the results paragraph match the evaluation section?
- Does the contribution list avoid becoming a second abstract?
- Is there too much repetition between abstract and introduction?

Provide:
- Remaining introduction issues.
- A revised introduction outline.
- Suggested rewrite for the key insight paragraph.

7. Evaluation-presentation check

Review whether the newer evaluation section is easier to follow than the older version.

Check:
- Are trial counts and denominators clear?
- Are model sets clearly separated?
- Are local-model, API-model, controlled-benchmark, external-benchmark, and preliminary-benchmark results separated?
- Are confidence intervals and statistical tests described without overstating independence?
- Are outcome categories separated from defense mechanisms?
- Are negative or mixed benchmark results acknowledged in the main text?
- Does the paper make clear which result is the main evidence for the key claim?

Provide:
- A corrected evaluation narrative.
- Any arithmetic or denominator inconsistencies.
- A table-caption improvement list.
- A final checklist of all numbers that must be cross-checked before submission.

8. Figures, tables, and layout comparison

Compare figures and tables against prior concerns.

Check:
- Were crowded figures simplified?
- Were captions improved?
- Are tables less duplicative?
- Are denominators visible?
- Are mixed results visible rather than hidden?
- Are important tables placed near the corresponding text?
- Are any figures still unreadable in two-column format?
- Are there signs of layout pressure?

Provide:
- Figure-by-figure and table-by-table comments.
- Which items should remain in the main paper.
- Which items should move to appendix.
- Suggested caption rewrites.

9. Terminology and consistency comparison

Check whether terminology is now consistent.

Create a table:

Term or phrase | Older issue | New status | Recommended final term

Check:
- System name.
- Paper title phrase.
- Threat model terms.
- Attack names.
- Benchmark names.
- Metric names.
- Model names.
- Policy names.
- Provenance labels.
- Section references.
- Figure and table references.

10. Writing and anti-AI-tic cleanup

Review whether the newer draft still sounds AI-generated, promotional, repetitive, or overly generic.

Flag:
- Formulaic transitions.
- Overused academic filler.
- Long stacked sentences.
- Repeated bridge sentences across sections.
- Overuse of phrases such as "fundamental," "key insight," "dominant," "robust," "comprehensive," "leverage," "utilize," "delve," "pivotal," "intricate," "underscore," "showcase," "moreover," and "furthermore."
- Formatting artifacts or generated-text artifacts.

Give at least 15 before/after sentence-level edits.

11. Reference and citation integrity check

Check whether the revision improved citation fairness and support.

Look for:
- Prior-work claims that still need citations.
- Numerical comparisons across papers that may not be apples-to-apples.
- Citation clusters that are too broad.
- Missing citations for benchmarks, systems, or datasets.
- Claims that require stronger source support.
- Any citation placeholder or broken reference.

Do not invent citations. State what type of source is needed.

12. Revision-comment classification

Classify remaining problems into four types:

R1. Factual or numerical correction.
R2. Style, clarity, repetition, or AI-tic issue.
R3. Cross-section inconsistency.
R4. Logical gap or unsupported claim.

For each remaining issue, give:
- Class.
- Severity.
- Location.
- Required action.
- Whether the author can fix it by editing text or needs more evidence.

13. Remaining reviewer risks

List the likely reviewer criticisms that still remain after revision.

For each one, provide:
- Why it may still arise.
- How severe it is.
- How to preempt it.
- Exact wording to add, soften, or move.

14. Final decision and action plan

End with:
- A one-paragraph final judgment.
- A prioritized action list.
- A submission-readiness checklist.
- A short list of changes that must be made before submission.
- A short list of changes that are optional but would strengthen the paper.

Please be detailed, direct, and actionable. Use exact locations when possible.
```

---

## Optional Mini-Prompt for a Fast Pass

```text
Please do a fast presentation-focused manuscript review. Focus on title, abstract, introduction, contribution list, claim calibration, evaluation presentation, figures/tables, terminology, and reviewer risks. Please identify the top 10 issues, give safer wording for overclaimed statements, check all visible arithmetic and denominators, and end with a submission checklist.
```

---

## Optional Add-On for Systems, Security, and AI-Agent Papers

Use this add-on when reviewing papers similar to PROVSAFE or other tool-using LLM agent security papers.

```text
Because this is a systems/security/AI-agent paper, pay special attention to:
- Whether the threat model is consistent with the attack taxonomy.
- Whether direct and indirect attacks are clearly separated.
- Whether the paper distinguishes design guarantees from implementation heuristics.
- Whether formal properties are conditional on assumptions that are stated clearly.
- Whether policy-only, filtering-only, taint-only, and full-system baselines are fairly framed.
- Whether evaluation outcomes are separated from defense mechanisms.
- Whether external benchmark results are adapted transparently.
- Whether controlled benchmark results are not oversold.
- Whether mixed results are acknowledged in the main text.
- Whether final claims distinguish architecture-level generality from empirical results on tested models.
- Whether confidentiality, integrity, availability, and usability claims are each supported by the right evidence.
```
