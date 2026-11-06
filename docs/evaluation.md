# Evaluation protocol

## Goal

Test whether modular, validation-assisted revision improves **reader usefulness, structural organization, and consistency** without dropping necessary information, numbers, or conditions. Shorter text is not automatically better, and **no benchmark or baseline experiment has been executed yet**.

## Corpus and current status

1. **Synthetic seed fixtures (`tests/fixtures/cases.json`):** 12 small, illustrative cases (`LW-001`..`LW-012`) covering audience irrelevance, redundancy, Korean register inconsistency, claim contradictions, scoped exceptions, attributed opinions, missing required information, and unsupported claims.
2. **Provisional real-world candidates (`tests/fixtures/real-world-candidates.json`, documented in [`docs/real-world-candidates.md`](real-world-candidates.md)):** **20 provisional entries** collected from 5 public repositories—**12 non-`KEEP` action candidates** (`MOVE`, `COMPRESS`, `REVISE`, `FLAG`) and **8 `KEEP` information-preservation candidates** (where intra-document `placement` is evaluated separately from content retention).

**Current status constraints:**
- Independent human review, reviewer agreement resolution, held-out split assignment, and `B0` / `B1` / `B2` baseline runs are **not done**.
- Provisional candidates are marked `provisional_candidates_not_gold` and must not be reported as a validated gold benchmark.
- Existing fixture files (`tests/fixtures/cases.json` and `tests/fixtures/real-world-candidates.json`) remain unchanged at `schema_version: "0.1.0"`, with **no invented target documents and no retroactive relabeling**.

Across the corpus, cases span:
- README and installation guides
- Pull request descriptions
- Release notes and changelogs
- Design documents, verification gates, and work/experience reports
- Negative controls where long technical safeguards, scoped exceptions, or attributed disagreements should be preserved (`KEEP`)

### Agreed scope for the planned diagnostic gold set

The user agreed to the following evaluation scope for the 20 real-world cases. This settles the task definition only: per-case input bundles, accepted judgments, review records and the freeze version are still to be agreed. Existing fixtures remain provisional and unchanged.

| Evaluate | Evidence of a satisfactory judgment |
| --- | --- |
| Purpose and information extraction | Interpret the reader task correctly; distinguish explicit intent from assumptions and identify units with their necessary conditions and provenance. |
| Preservation and organization | Justify what belongs in each document and where other information must be preserved; distinguish local exposure, internal placement and cross-document transfer. |
| Expression decisions and alternatives | Separate required corrections from optional improvements and recognize defensible alternatives rather than demanding one layout or wording. |
| Uncertainty and evidence limits | Identify unsupported claims, ambiguous intent or unverified destinations and recommend `FLAG` / `REVIEW` where warranted; never report unverified behavior as confirmed. |

This is a **development/regression set for diagnosis and editorial decisions**, not a test requiring a completed rewritten document, an executed transfer, or independent proof of every source's runtime/performance claim. Exact replacement-text matching is outside this task. These exclusions do not excuse wrong attribution, meaning distortion or unsupported assertions in the diagnosis or any suggested text. A working validation engine is not a prerequisite for freezing these diagnostic annotations.

The cases have already informed the editorial criteria and must not be represented as an unseen holdout. A separate future set is needed for that purpose. This scope decision neither approves all annotations as gold nor records independent human agreement; those remain separate steps.

### Agreed input composition and answer separation

The model-facing input will contain the following fixed material. This agreement defines what may be supplied, not a completed export, adopted schema or frozen set of case inputs.

| Input component | Inclusion and boundary |
| --- | --- |
| Source identity and text | Fixed excerpt with source kind, exact text and original range; Git commit/blob and content digest where applicable. A PR body requires its captured text and observation time, not just a head SHA. |
| Necessary surrounding context | Source passages needed to interpret role, prerequisites, measurements, attribution or conflicts. Pin their snapshots and ranges as well; do not require the model to reconstruct our conversation or silently fetch changing live context. |
| Reader task and user requirements | Self-contained audience, intended purpose and applicable constraints, including purpose changes agreed in this conversation. Distinguish explicit user requirements from historical document role and labeled assumptions. State the desired outcome without embedding our recommended editorial actions. |
| Destination context or availability | Supplied destination text and role when verified, or a factual statement that destination context is unavailable/unverified. Availability is input evidence; our proposed MOVE or REVIEW verdict is an answer and must not be included here. |
| Supplied check observations | Relevant recorded evidence such as dated HTTP observations, with method, scope and limits. A source's claim that tests passed is still a source assertion; no runtime verification is implied. |

Keep existing action labels, annotation rationales, gold information-unit segmentation, preservation/placement/expression judgments, acceptable-answer alternatives and reassessment conclusions in a separate answer area. Do not pass the candidate fixture or review record wholesale to the evaluated model: their source/context fields and the resolved task must be selected explicitly. Ordinary source headings and statements remain source data, even when they discuss verification or limitations; answer separation must not strip necessary interpretation context.

All evaluation arms must receive the same selected facts and contract. Preparing the bundles requires checking the selected context and snapshot references case by case; agreement on this composition does not assert that all 20 bundles are already complete or approved. Their serialization, final expected judgments and freeze approval remain later steps.

## Baselines

After M0 human review, prepare comparisons using identical source facts, draft snapshots, and writing contracts. Execute B2 only when the validator and revision controller exist:

1. **B0 — direct generation / unassisted draft:** writer alone.
2. **B1 — prompt-only:** writer prompted to be concise, coherent, and audience-aware.
3. **B2 — LogicWrite:** modular pipeline (`Information Extraction & Analysis` → `Information Organization` → `Expression Refinement`) governed by the `Validation Gate` and bounded `Revision Controller`.

For existing drafts, every editing condition receives the same unchanged draft; do not compare a newly generated B0 document with an edited B2 document as if their inputs were equal. Record model identifiers, temperature/settings when available, contract, prompt, and validator versions.

## Overall and per-module evaluation checks

### 1. End-to-end document measures

| Metric | How to assess |
| --- | --- |
| Reader-task success | Can independent readers answer or act on the intended question using the revised document? |
| Essential-information retention | Proportion of human-labeled required facts, numbers, conditions, and provenance retained across affected documents, with separately checked local exposure for claims that remain visible; see the [contextual rubric](#contextual-judgment-rubric) |
| Irrelevant information | Human-labeled out-of-scope spans left in the final document without appropriate `MOVE` or `REMOVE` |
| Contradiction detection | Precision/recall on labeled claim pairs (counting false alarms on legitimate exceptions or attributed quotes) |
| Register & term consistency | Violations per eligible Korean narration sentence, excluding quotations, code blocks, and headings |
| Revision regression | New factual errors, dropped caveats, altered numbers, or broken transitions introduced during editing |
| Reviewer time | Human time required to inspect findings, verify moves/edits, and approve the result |
| Length | Descriptive statistic only; never an optimization target by itself |

### 2. Per-module evaluation checks

To isolate where failures occur in the [three-module architecture](architecture.md), evaluate each module and the controller independently against human annotations:

| Module / component | What to verify | Failure evidence to record |
| --- | --- | --- |
| **Information Extraction & Analysis** | Unit/claim extraction and condition, number, evidence links; audience/purpose fit and preservation judgments; recovery of purpose misidentification from user context | Missing or incorrectly linked units; disagreement with human annotations; silent purpose overwrite; unsupported recovery or unnecessary changes when the purpose already fits |
| **Information Organization** | Destination review before `MOVE`; source/destination retention; grouping, duplicate consolidation, reader-task ordering, and independent `placement` of `KEEP` units | Misrouting, lost caveats or provenance, remaining duplication, prerequisite-order violations, and unjustified reorganization; a different valid placement alone is not a failure under the [contextual rubric](#contextual-judgment-rubric) |
| **Vector candidate retrieval (future, within Organization)** | Recall of human-labeled related units, destinations, and contradiction pairs within a declared candidate budget; review of retrieved context before decisions | Missed candidates, irrelevant candidates, and any importance/truth/deletion decision made from similarity alone; retrieval quality is separate from downstream editorial accuracy |
| **Expression Refinement** | Meaning-preserving `REVISE`/`COMPRESS`, terminology, Korean register, clarity, and readability; human usefulness ratings with required-content checks | Changed numbers, lost qualifiers or attribution, unsupported additions, edits in excluded quotes/code, or unauthorized routing/deletion |
| **Validation Gate & Revision Controller** | Independent boundary and whole-document checks, routing by defect origin, downstream invalidation, and bounded stopping | Missed regressions, unnecessary retries, stale artifacts after upstream changes, incorrect target module, nontermination, or falsely clean `PASS` |

Report sample sizes, uncertainty, and per-document-type breakdowns. Do not equate heuristic "AI-likeness" scores with writing quality.

### Contextual judgment rubric

Apply the [purpose-first decision procedure](architecture.md#purpose-first-decision-procedure) before comparing actions or surface wording. This is guidance for future human annotation and evaluation, not an executed benchmark, adopted scoring schema or new gold labels. The [20-case reassessment](reviews/real-world-20-reassessment.md) supplies illustrative reasoning and scoped user feedback; it does not establish universal document policies.

| Criterion | Evidence to examine | Failure to distinguish from an acceptable alternative |
| --- | --- | --- |
| Desired purpose and reader task | Explicit user context, fixture assumptions, historical document role, and the task of each output scope | Preserving a historical management role against an explicit master-career display goal is a purpose error (RW-009). Do not assume every README must display a resume. |
| Information function and selection | Source context, unit/condition boundaries, why that information belongs here rather than merely being useful somewhere | Installer-selection rationale is not an installation instruction (RW-001/002). Detailed maintenance procedures can belong in a guide even when README readers might use them (RW-018). |
| Preservation versus local exposure | Full affected evidence set, proposed current claims, destination context, protected elements and their scope-specific exposure | Narrowing a resume to actual evaluation work can allow detailed metrics and limits to stay in evidence (RW-012). Keeping only favorable numbers while hiding regression or falsely claiming implementation credit is not equivalent. |
| Organization and alternatives | Destination fit, existing overlap, retained unique information, actual anchor/order and reader task | Accept multiple defensible placements when the same contract is satisfied (RW-003); reject missing prerequisites, lost information, or unverified transfers, not a choice merely different from the suggested layout. |
| Expression and edit necessity | Meaning of the actual before/after text, style constraints, readability, exclusions and substantive versus decorative content | Decorative emoji cleanup may be a reasonable REVISE proposal without an earlier instruction (RW-014). Do not demand it universally, remove meaningful symbols, or report it as evidence that a support claim is false. |
| Evidence boundary and unresolved work | Source assertion, captured snapshot, current observation, independent human judgment, actual execution and complete output coverage | Reading a release note, a PR body or a destination document does not verify runtime behavior, diff invariance or completed preservation. Optional editorial alternatives do not themselves establish a missing fact. |

For each proposed decision, describe the supporting purpose/evidence, preservation scope, required local exposure, placement and expression separately, using the existing review records where possible. State whether the edit addresses a demonstrated requirement/meaning failure, offers an optional improvement, or awaits evidence/intent clarification. These are review explanations, not new fixture fields or gate verdicts. Rejecting an optional placement or style suggestion does not by itself make a contract-compliant output incorrect; competing placements need not block delivery if all required checks are satisfied. Leaving an already suitable passage unchanged is valid; do not reward edit count or unmotivated churn. Unverified destinations and missing required checks still prevent `PASS` under the existing gate policy.

Compare candidates under the same contract and source facts. A supported change of purpose creates a separate contract condition; do not score old and new judgments as disagreement under identical inputs. Preserve a predecessor record and rationale for a correction. Exact action-label or text match is insufficient for contextual judgments: assess whether the actual decision and output satisfy the task and preservation/exposure obligations. Deterministic constraints such as protected literals and valid references remain exact checks where applicable.

Keep the agreed preservation obligations and retention denominator fixed across evaluation arms. Moving detail or narrowing a visible claim does not lower the denominator, authorize loss of evidence or permit changing required facts to improve a score. Check local exposure against the claims actually retained as well as corpus-wide preservation. Style improvements do not establish factual correctness, and semantic correctness cannot be replaced by counting shorter text or matching one reference layout. No weights, thresholds, scores or agreement results are established here.

## Annotation workflow and guardrails

- **Independent human review:** Two people independently label a subset when feasible, marking each proposed finding, preservation judgment, and `placement` proposal as `agree`, `disagree`, or `uncertain`. Disagreements are resolved with a documented rationale rather than an automated model vote.
- **Uncertainty is first-class:** `FLAG` is a valid outcome when source evidence cannot settle a factual conflict, when user intent vs. draft purpose requires clarification, or when a cross-document `MOVE` destination is not yet confirmed.
- **Acceptable alternatives and necessity:** Reviewers record justified alternatives and distinguish a blocking contract/meaning problem from an optional editorial preference using the [contextual rubric](#contextual-judgment-rubric). Scoped user feedback can resolve an intended purpose or preference; it does not constitute independent annotation of the whole corpus or a gold freeze.
- **No invented targets or silent relabeling:** Evaluators and tools must not fabricate destination file paths, invent source evidence, or silently overwrite existing fixture annotations.
- **Guardrails:**
  - Preserve provenance, literal numbers, constraints, and qualifiers across authorized affected scopes; separately check the [necessary local exposure](architecture.md#caveat-retention-and-exposure) of retained claims. Source correction needs authoritative evidence, while relocation needs verified preservation rather than forced repetition in every document.
  - Validate both source and destination contexts when evaluating cross-document moves or duplicate consolidation.
  - Never treat a missing detected contradiction as proof none exists.
  - Keep critical unresolved issues visible after the revision limit reaches `STOPPED` or `REVIEW`.
  - Use permission-safe public or consented examples; do not introduce private documents without permission and appropriate redaction.

## Proposed schema extensions (proposal only — not adopted)

> **Status: design proposal only.** The fields below are **not adopted**, **not implemented**, **not migrated** into `tests/fixtures/cases.json` or `tests/fixtures/real-world-candidates.json`, and **not** a gold-standard annotation format. Both existing JSON fixture files remain byte-identical at `schema_version: "0.1.0"` and continue to use the seven primary compatibility action labels (`KEEP`, `COMPRESS`, `REVISE`, `MOVE`, `REMOVE`, `ADD`, `FLAG`).

Consider these additions separately before any schema freeze or migration:

| Proposed addition | Purpose and compatibility question |
| --- | --- |
| Per-unit preservation, expression, and placement decisions | Represent independent decisions without replacing existing `action` / `expected_action` labels; define span/unit linkage and handling of multiple edits |
| Contract intent provenance and purpose conflict/recovery record | Distinguish explicit user context from inferred assumptions and retain the evidence for recovery |
| Responsible module and editorial stage | Audit where a defect originated and where the controller routed it, separately from its primary action |
| Protected-element references and verification evidence | Track facts, numbers, conditions, citations, and source/destination checks using snapshot references, rather than unsupported boolean success claims |

Existing candidate annotations already contain `placement` and, in some cases, scoped additional actions. Review reuse of those fields before adding alternatives; define backward mapping, versioning, and human approval before adoption. No new fields, labels, thresholds, or migrated records are established by this proposal.

## Immediate next step

Complete M0 human review on the 20 provisional real-world candidates, retain reviewer decisions and disagreement rationales in review records, and reserve a held-out split before tuning. Prepare a small B0/B1 pilot and the B2 protocol; run the executable B2 comparison after M3 provides validation and bounded revision. Expand only if reader usefulness and information retention justify it.
