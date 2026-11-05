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
| Essential-information retention | Proportion of human-labeled required facts, numbers, conditions, and provenance retained across affected documents |
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
| **Information Organization** | Destination review before `MOVE`; source/destination retention; grouping, duplicate consolidation, reader-task ordering, and independent `placement` of `KEEP` units | Misrouting, lost caveats or provenance, remaining duplication, prerequisite-order violations, and unnecessary reorganization |
| **Vector candidate retrieval (future, within Organization)** | Recall of human-labeled related units, destinations, and contradiction pairs within a declared candidate budget; review of retrieved context before decisions | Missed candidates, irrelevant candidates, and any importance/truth/deletion decision made from similarity alone; retrieval quality is separate from downstream editorial accuracy |
| **Expression Refinement** | Meaning-preserving `REVISE`/`COMPRESS`, terminology, Korean register, clarity, and readability; human usefulness ratings with required-content checks | Changed numbers, lost qualifiers or attribution, unsupported additions, edits in excluded quotes/code, or unauthorized routing/deletion |
| **Validation Gate & Revision Controller** | Independent boundary and whole-document checks, routing by defect origin, downstream invalidation, and bounded stopping | Missed regressions, unnecessary retries, stale artifacts after upstream changes, incorrect target module, nontermination, or falsely clean `PASS` |

Report sample sizes, uncertainty, and per-document-type breakdowns. Do not equate heuristic "AI-likeness" scores with writing quality.

## Annotation workflow and guardrails

- **Independent human review:** Two people independently label a subset when feasible, marking each proposed finding, preservation judgment, and `placement` proposal as `agree`, `disagree`, or `uncertain`. Disagreements are resolved with a documented rationale rather than an automated model vote.
- **Uncertainty is first-class:** `FLAG` is a valid outcome when source evidence cannot settle a factual conflict, when user intent vs. draft purpose requires clarification, or when a cross-document `MOVE` destination is not yet confirmed.
- **No invented targets or silent relabeling:** Evaluators and tools must not fabricate destination file paths, invent source evidence, or silently overwrite existing fixture annotations.
- **Guardrails:**
  - Preserve provenance, literal numbers, constraints, and qualifiers unless authoritative source evidence authorizes change.
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
