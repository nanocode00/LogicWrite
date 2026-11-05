# Proposed architecture

> Design proposal. None of the components below is implemented yet.

## System overview and pipeline

LogicWrite separates editorial processing into **three explicit core modules** coordinated by **shared contract, validation, and revision infrastructure**:

1. **Information Extraction & Analysis** — segments drafts into information units, analyzes claims/conditions/quantities/provenance, evaluates audience/purpose fit and importance, and detects or recovers from document-purpose misidentification.
2. **Information Organization** — determines cross-document destinations (`MOVE`), consolidates duplicates across or within documents, and establishes intra-document grouping and reader-task ordering (`placement`), optionally assisted in the future by vector candidate retrieval.
3. **Expression Refinement** — rewrites sentences and paragraphs (`REVISE`), enforces target Korean register and terminology consistency, and performs meaning-preserving compression (`COMPRESS`) and readability improvements.

Shared infrastructure surrounds the three modules:
- **Writing Contract & Contract Resolver** — normalizes actual user intent, audience, purpose, required information, constraints, and authoritative sources.
- **Validation Gate** — executes deterministic rule validators and model-assisted semantic checks at module boundaries and across complete affected documents.
- **Revision Controller** — routes validation findings back to the responsible module in a bounded loop with downstream invalidation and revalidation.

```text
Client / agent / CLI
      |
      v
Contract Resolver ----> Shared Writing Contract
      |                 (user intent > inferred doc purpose; surface conflicts)
      v
Draft / Source & Candidate Destination Contexts
      |
      v
+-------------------------------------------------------------------+
| 1. Information Extraction & Analysis                              |
|    unit extraction, claim/condition/number analysis,              |
|    audience/purpose fit & importance, purpose recovery            |
+-------------------------------------------------------------------+
      |  (boundary check: extracted units, contract alignment, protected facts)
      v
+-------------------------------------------------------------------+
| 2. Information Organization                                       |
|    cross-document routing (MOVE), duplicate consolidation,        |
|    intra-document grouping & ordering (placement),                |
|    [future] vector-assisted candidate search                      |
+-------------------------------------------------------------------+
      |  (boundary check: source + destination preservation, caveat proximity)
      v
+-------------------------------------------------------------------+
| 3. Expression Refinement                                          |
|    sentence/paragraph rewrite (REVISE), style/register/terms,     |
|    meaning-preserving compression (COMPRESS), clarity             |
+-------------------------------------------------------------------+
      |
      v
Validation Gate (Deterministic Rules + Semantic Reviewer)
      |                                   |
  PASS / REVIEW                         revise
      |                                   |
report & audit trail            Revision Controller
                                (route to Module 1, 2, or 3;
                                 invalidate & revalidate downstream;
                                 stop on ambiguity / no progress / limit)
```

## Shared infrastructure

### Writing Contract and Contract Resolver

The `Contract Resolver` validates required fields and normalizes the contract under the [intent precedence and conflict rules](requirements.md#intent-precedence-and-conflict-handling). User intent takes precedence over purpose inferred from an existing draft. `Information Extraction & Analysis` can return an evidence-backed purpose correction to the resolver; the resolver records its basis and contract version before downstream work resumes. Unresolved ambiguity yields `FLAG` / `REVIEW`. Contract changes invalidate dependent assessments, organization plans, and expression edits rather than silently reusing them.

### Validation Gate

The gate owns check execution and verdicts independently of editorial proposals: a module cannot pass its own output by declaration. This is a responsibility boundary, not a requirement for another model vendor.

The gate combines deterministic **Rule Validators** and a model-assisted **Semantic Reviewer** to verify both **inter-module boundaries** and **entire affected documents** (including both source and destination documents when content is moved or consolidated):

- **Rule Validators (deterministic):** JSON schema validation, contract completeness, required sections/terms, explicit forbidden phrases, terminology invariants, and checkable protected items (such as literal numbers, identifiers, or required citations). Pattern-based Korean register checks are treated as heuristic unless context (quotes, code fences, headings, tables) is disambiguated.
- **Semantic Reviewer (model-assisted):** Evaluates whether information units serve the contract's audience and purpose, whether claims conflict across subject/scope/condition/time/quantifiers/attribution, whether caveats remain attached to the claims they qualify, and whether rewrites or compressions altered meaning. **No semantic verdict is unconditionally deterministic;** `FLAG` and `REVIEW` remain valid outcomes when evidence is insufficient.

Proposed finding envelope (subject to change):

```json
{
  "rule_id": "CLAIM_CONTRADICTION",
  "severity": "WARNING",
  "action": "FLAG",
  "spans": [{"start": 0, "end": 28}, {"start": 100, "end": 144}],
  "evidence": "The two claims appear to apply to the same requests.",
  "reason": "A universal rule conflicts with an exception unless its scope is narrowed.",
  "confidence": "medium",
  "requires_human_review": true
}
```

Offsets refer to the evaluated draft snapshot. Exact conventions and versioning must be fixed before implementation (recommended: Unicode code-point offsets plus document content hash). Cross-document findings must identify the document snapshot for each span; this illustrative envelope is not a frozen schema.

Gate states:

| State | Meaning |
| --- | --- |
| `PASS` | All configured hard checks passed; no blocking findings remain across affected documents |
| `REVIEW` | No confirmed hard failure, but unresolved semantic concerns, purpose conflicts, or provisional destinations need human decision |
| `FAIL` | Confirmed hard check or blocking requirement failed |
| `STOPPED` | Revision limit reached, no progress, or execution error; report outstanding issues |

### Revision Controller

The `Revision Controller` enforces the validation loop externally rather than relying on a prompt asking the writer to self-police:

1. **Route by module ownership:** Inspect each finding and dispatch it to the responsible module:
   - Purpose mismatch, omitted source units, incorrect preservation judgments, or unresolved claim/evidence relationships → `Information Extraction & Analysis`.
   - Misrouted cross-document `MOVE`, unverified destination context, duplicate merge loss, detached caveats, or poor section/task ordering → `Information Organization`.
   - Register violations, terminology drift, wordiness, local clarity defects, or meaning lost during rewriting → `Expression Refinement`.
   - Route dropped facts or unsupported claims to the module that introduced them. If the cause is unclear, return to analysis before generating another edit; a severity or action label alone does not determine ownership.
2. **Invalidate and revalidate downstream:** Any revision in an upstream module invalidates dependent downstream artifacts:
   - Changes in `Information Extraction & Analysis` (e.g., recovering document purpose or changing unit preservation) require re-running `Information Organization` and `Expression Refinement` on affected units.
   - Changes in `Information Organization` (e.g., regrouping, merging duplicates, or changing `placement`) require re-running `Expression Refinement` on modified sections.
   - Every revision cycle concludes with a full **Validation Gate** check over the **entire** affected source and destination documents.
3. **Reject regressions and bound execution:** Compare protected facts, numbers, conditions, and prior findings after each attempt. Stop on `PASS`, a human-review blocker (`FLAG` / `REVIEW`), a repeated/non-improving state, or the attempt limit (default proposal: three), returning the latest draft and all unresolved findings.

## Core modules

### 1. Information Extraction & Analysis

- **Responsibilities:**
  - Segment source drafts and supplied reference texts into discrete information units.
  - Extract and link claims, supporting evidence, conditions/qualifiers, literal numbers/metrics, time/scope bounds, and provenance.
  - Assess each unit's relevance and importance relative to the contract's audience, purpose, and existing document context.
  - Detect and recover from **purpose misidentification**—for example, when an inferred purpose reflects how a draft was originally written (an agent's activity log or an omnibus master file) rather than what the user's contract requires, or when a draft mixes multiple document roles.
- **Inputs:** Source draft(s), normalized `Writing Contract`, user context, and optional authoritative `source_material` or candidate overlap pairs.
- **Outputs:**
  - Structured inventory of information units with extracted claims, conditions, numbers, and provenance links.
  - Contract-alignment report (confirming audience/purpose fit or surfacing purpose conflicts/ambiguities for recovery or clarification).
  - Per-unit preservation and boundary judgment (`KEEP`, `REMOVE`, `ADD`, `FLAG`, or candidate for cross-document `MOVE`) with audience/purpose rationale.
- **Boundary and gate checks:**
  - Every extracted unit maps to traceable source spans and provenance hashes; proposed additions retain their evidence reference and are marked missing when no source supports them.
  - Contract-required facts, numbers, and conditions are accounted for (`REQUIRED_INFORMATION_MISSING` triggers `ADD` or `FLAG`; never invent unsupported facts).
  - Purpose conflicts between user intent and draft content are explicitly surfaced rather than silently resolved by overwriting the contract or deleting high-value material.
  - Low relevance to the current document alone cannot produce `REMOVE` if the unit carries architectural, operational, or historical value belonging in another document (`MOVE` or `FLAG`).

### 2. Information Organization

- **Responsibilities:**
  - Determine cross-document destinations and execute `MOVE` decisions only after reviewing destination document context (audience, purpose, and existing content).
  - Group information units by destination document and section, consolidating duplicates while preserving all qualifying conditions, numbers, facts, and provenance.
  - Order units within each document (`placement`) according to reader task flow, prerequisites, and relative importance.
  - Utilize optional vector-assisted candidate search (future design) to locate candidate target documents, related/overlapping units, and potential cross-paragraph or cross-document contradictions.
- **Inputs:** Analyzed information units and preservation judgments from Module 1, source and candidate destination document contexts, and optional vector retrieval candidates.
- **Outputs:**
  - Document-level and section-level organization plan (`placement`: target document, target section, relative position, and ordering rationale).
  - Consolidated unit groups with provenance and required caveats attached to the claims they qualify.
  - Flagged routing ambiguities (`FLAG` / `REVIEW`) when a suitable destination document does not exist or cannot be verified.
- **Boundary and gate checks:**
  - **Source and destination validation:** A cross-document `MOVE` or redundancy-based `REMOVE` is blocked unless the destination context is inspected and both the source document (after removal) and destination document (after integration) preserve required claims, conditions, and numbers.
  - **Caveat attachment:** Conditions required to interpret a retained claim remain adjacent to that claim; they cannot be stripped into a bare link or lost during duplicate merging.
  - **`KEEP` vs. `placement` separation:** `KEEP` preserves the unit's information in the current document, while intra-document section and order remain adjustable via `placement`.

### 3. Expression Refinement

- **Responsibilities:**
  - Rewrite sentences and paragraphs (`REVISE`) to fix grammar, awkward phrasing, or structural transitions after reorganization.
  - Enforce target Korean speech level/register (e.g., `해요체`, `합니다체`, `한다체`) and consistent domain terminology while respecting quotations, code blocks, and headings.
  - Condense verbose phrasing or local repetition (`COMPRESS`) without altering semantic scope, conditions, or numbers.
- **Inputs:** Organized document plan and consolidated units from Module 2, target register and terminology constraints from the `Writing Contract`, and the protected list of facts, numbers, and qualifiers.
- **Outputs:**
  - Revised document text(s) with span-level change tracking mapped back to the organized units.
- **Boundary and gate checks:**
  - **Meaning and fact invariance:** `REVISE` and `COMPRESS` must not drop contract-required facts, alter quantities/metrics, broaden claim scope by dropping qualifiers, or introduce unsupported assertions (`UNSUPPORTED_CLAIM`).
  - **Style and register compliance:** Target register and terminology rules pass deterministic and contextual checks across eligible narration sentences.
  - **Scope restraint:** Module 3 cannot delete substantive information units or reroute content across documents; if rewriting exposes a deeper structural or factual problem, the `Revision Controller` routes the issue back to Module 1 or Module 2.

## Separating preservation, expression, and placement

A single passage often requires independent decisions across three conceptual dimensions:

| Dimension | Owning module | Question answered |
| --- | --- | --- |
| **Preservation judgment** | Information Extraction & Analysis | Should this unit's information be retained here, moved elsewhere, supplemented, removed, or flagged for confirmation? |
| **Placement decision** | Information Organization | Which document (`MOVE`) and which section/relative order (`placement`) best serve the reader's prerequisites and task flow? |
| **Expression edit** | Expression Refinement | How should the retained or merged unit be phrased, condensed (`COMPRESS`), or normalized (`REVISE`) for register, terminology, and clarity? |

**Compatibility with the seven action labels:**
LogicWrite retains the seven action names—`KEEP`, `COMPRESS`, `REVISE`, `MOVE`, `REMOVE`, `ADD`, and `FLAG`—for human readability and backward compatibility with existing fixtures (`tests/fixtures/cases.json` and `tests/fixtures/real-world-candidates.json`). These single labels record the **primary editorial disposition** of a finding rather than forcing one label to encode all three dimensions simultaneously:
- `KEEP` means the information is relevant and important to preserve in the current document; it **does not freeze wording or current position**. A `KEEP` unit may still be reordered within the document (`placement`) by `Information Organization` or polished for style/conciseness by `Expression Refinement`.
- `MOVE` denotes cross-document transfer to a document better suited to the unit's audience and purpose. Reordering or moving a passage to another section **within the same document** is recorded as `placement`, not `MOVE`.
- `COMPRESS` and `REVISE` describe expression-level or redundancy edits on retained information without revoking its preservation status.

## Editorial workflow

Within the modular architecture above, editorial processing follows six logical stages before a revised document passes the gate. Each stage maps explicitly to the core modules and shared infrastructure, making unit extraction and expression refinement explicit where earlier summaries left them implicit:

```text
1. Audience & purpose determination            [Contract Resolver + Extraction & Analysis]
  -> 2. Unit extraction, relevance & importance [Information Extraction & Analysis]
  -> 3. Action & boundary decision             [Extraction & Analysis -> Organization]
  -> 4. Regroup per destination & merge        [Information Organization]
  -> 5. Order within destination & refine      [Information Organization -> Expression Refinement]
  -> 6. Whole-document validation              [Validation Gate + Revision Controller]
```

| Stage | Owning module / component | Input | Output |
| --- | --- | --- | --- |
| 1. Audience & purpose determination | `Contract Resolver` + `Information Extraction & Analysis` | Source draft, `Writing Contract`, user context | Normalized audience, purpose, scope, recorded assumptions, and recovery/surfacing of any purpose misidentification |
| 2. Relevance & importance assessment *(includes explicit unit & claim extraction)* | `Information Extraction & Analysis` | Source drafts, contract, and target document context | Extracted unit inventory plus context-dependent relevance and importance judgment per unit |
| 3. Action decision | `Information Extraction & Analysis` (preservation/boundary) & `Information Organization` (destination viability) | Assessed units, source and candidate destination contexts | Primary compatibility action, preservation judgment, and candidate destination; expression proposals are realized and checked in Module 3 |
| 4. Regroup & merge duplicates | `Information Organization` | Units grouped by destination, existing destination content, candidate overlaps | Consolidated units across/within documents preserving conditions, qualifiers, facts, numbers, and provenance |
| 5. Order within destination *(followed by explicit expression refinement)* | `Information Organization` (`placement`) → `Expression Refinement` (rewrite/compress/style) | Regrouped units, reader tasks, prerequisites, relative importance, register/term constraints | Ordered document plan (`placement`) and expression-refined revised draft(s) (`REVISE`, `COMPRESS`, register/term normalization) |
| 6. Whole-document validation | `Validation Gate` + `Revision Controller` | Complete revised source and destination document(s), contract, protected facts/qualifiers | Deterministic and semantic findings; gate state (`PASS`, `REVIEW`, `FAIL`, `STOPPED`) or targeted module re-routing |

### Editorial invariants

The [module boundaries](#core-modules) and [decision dimensions](#separating-preservation-expression-and-placement) apply throughout all six stages: relevance is contextual, low relevance alone cannot justify deleting valuable information, and unresolved purpose/destination/claim questions yield `FLAG` / `REVIEW`. Neither regrouping nor polishing overrides the protected facts, conditions, numbers, or provenance.

### Caveat retention and exposure

Ask: **If this caveat is omitted, will readers misunderstand a claim in this document or make a different decision?** Distinguish preserving information in the corpus from exposing it in each document.

| Effect of omission in the current document | Treatment |
| --- | --- |
| Changes the meaning of a claim or materially affects the reader's decision | Retain the minimum necessary condition near that claim |
| Matters to a subset of readers but is not needed to interpret the main text | Preserve details in an appropriate document and link where useful |
| Needed for provenance or later reuse, without affecting the current reader's decision | Preserve in the evidence record; omit from the current text |
| The same condition is already adequately stated | Consolidate the duplication |

Adjust claims and caveats together: narrow an overbroad claim or move the claim and its supporting detail together rather than deleting only its limitation. A link cannot replace a condition necessary to interpret the visible claim. Verify destination preservation before removing duplicated detail; unknown preservation yields `FLAG` / `REVIEW`. Because `Information Organization` and `Expression Refinement` can alter which claims appear in a document and how they are grouped, the `Validation Gate` reassesses caveat exposure on the complete revised source and destination documents after editing.

## Future design: vector-assisted routing

> **Status: unimplemented future design.** Vector-assisted routing is neither implemented nor evaluated. No embedding providers, runtime dependencies, numeric importance scales, similarity thresholds, or executable schemas are fixed.

Within **Information Organization** (and feeding candidate contradiction pairs to **Information Extraction & Analysis**), vector retrieval can assist candidate discovery across multi-document repositories before editorial judgment:

1. **Profile and unit embeddings:** Compute embeddings for target document profiles (capturing audience, purpose, and scope) and extracted source information units from `Information Extraction & Analysis`.
2. **Candidate retrieval via cosine similarity:** Use cosine similarity to retrieve:
   - Candidate destination documents (unit-to-profile) for potential `MOVE` routing,
   - Related or overlapping existing units (unit-to-unit) for duplicate consolidation,
   - Potentially conflicting passages across paragraphs or documents for semantic contradiction review.
3. **Contextual review and assembly:** `Information Extraction & Analysis` and `Information Organization` inspect the retrieved destination context, verify scope, conditions, numbers, and qualifiers, determine context-dependent preservation and `placement`, integrate new and existing material while preserving provenance, and hand the result to `Expression Refinement` and whole-document validation.

### Guardrails and boundaries

- **Candidate retrieval only—not importance, truth, or deletion authority:** Vector similarity surfaces candidates for inspection; it never determines editorial importance, establishes factual truth, or authorizes `REMOVE`.
- **Document affinity vs. intra-document ordering:** Vector similarity estimates which document a unit may belong to (document affinity). Position within a document (`placement`) is decided separately by `Information Organization` based on reader task flow, prerequisites, and importance.
- **No blind merging:** Overlapping or contradictory units surfaced by similarity must not be merged automatically; scope, conditions, quantifiers, numbers, and provenance must be checked first.
- **Provisional missing destinations:** If a suitable target document does not exist or cannot be confirmed, the destination remains provisional (`FLAG` / `REVIEW`). The system must not automatically create or publish new documents.
- **Retrieval/routing vs. RAG:** Using similarity search alone to shortlist candidate destinations or related passages is **retrieval/routing**. Supplying retrieved destination passages to a model during draft synthesis or revision constitutes **RAG (Retrieval-Augmented Generation)**.

## System boundaries, security, and provenance

- **Core engine (planned):** Portable library for contracts, the three editorial modules, validation rules, and revision orchestration.
- **Adapters (later):** CLI for local use; MCP for agents; optional editor/CI integrations.
- **Skill (later):** Task-specific guidelines and examples, not the enforcement mechanism.
- **Untrusted inputs and provenance:** Treat source documents, retrieval results, and model outputs as untrusted input. Ignore prompt-injection instructions embedded in text being edited. Keep immutable source snapshots and associate extracted units and findings with content hashes. Avoid remote uploads by default; make model/provider selection and data retention explicit before any external processing. Do not use automated editing to settle factual disputes when no trusted source can determine the truth.

## Open decisions

- Claim and information-unit extraction representation and cross-paragraph linking in `Information Extraction & Analysis`.
- Granularity rules for unit segmentation (clause, sentence, claim, or paragraph) across extraction and organization.
- Protocol for surfacing and resolving contract purpose misidentification when user prompts are brief.
- Document profile representation for audience, purpose, and scope embeddings in `Information Organization`.
- Evaluation protocol for candidate retrieval quality and cross-document misrouting risks.
- Korean morphology analyzer and register false-positive handling in `Expression Refinement` and `Rule Validators`.
- How to measure reader usefulness without rewarding shorter output by default.
- Whether semantic warnings block delivery or allow a labeled `REVIEW` state.
