# Proposed architecture

> Design proposal. None of the components below is implemented yet.

## Pipeline

```text
Client / agent / CLI
      |
      v
Contract Resolver ----> normalized Writing Contract
      |                         |
      +-----------+-------------+
                  |
                  v
            Draft / Input
                  |
                  v
        Validation Coordinator
            /            \
           v              v
    Rule Validators    Semantic Reviewer
    (deterministic)    (model-assisted)
           \              /
            +------+-----+
                   v
           Finding Aggregator
                   |
                   v
            Validation Gate
              |         |
        PASS/REVIEW    revise
              |         |
        report/output  Revision Controller
                          |
                    revised document
                          |
                     re-validate
```

## Editorial workflow

Within the validation and revision orchestration above, editorial processing follows six logical stages before a revised document passes the gate:

```text
Audience & purpose determination
  -> Per-information relevance & importance assessment
  -> Action decision (KEEP / COMPRESS / REVISE / MOVE / REMOVE / ADD / FLAG)
  -> Regroup per destination & merge duplicates (preserving conditions, facts, provenance)
  -> Order by reader task, prerequisites, & importance
  -> Whole-document validation
```

| Stage | Input | Output |
| --- | --- | --- |
| 1. Audience & purpose determination | Source draft, writing contract, user context | Normalized audience, purpose, scope, and recorded assumptions |
| 2. Relevance & importance assessment | Information units, target document context (audience, purpose, existing content) | Context-dependent relevance and importance judgment per unit |
| 3. Action decision | Assessed units, source and candidate destination contexts | Per-unit action (`KEEP`, `COMPRESS`, `REVISE`, `MOVE`, `REMOVE`, `ADD`, `FLAG`) and target destination |
| 4. Regroup & merge duplicates | Units grouped by destination, existing destination content | Consolidated units preserving conditions, qualifiers, facts, and provenance |
| 5. Order within destination | Regrouped units, reader tasks, prerequisites, relative importance | Ordered document plan and revised draft |
| 6. Whole-document validation | Complete revised document, contract, protected facts/qualifiers | Deterministic and semantic findings; gate state (`PASS`, `REVIEW`, `FAIL`, `STOPPED`) |

### Editorial invariants

- **Context-dependent value:** An information unit's relevance and importance depend on the target document's audience, purpose, and existing content rather than intrinsic length or detail.
- **Destination review before cross-document move:** A cross-document `MOVE` (or redundancy-based `REMOVE`) requires reviewing the destination document's context first so information is not dropped or misrouted.
- **Low source relevance is not deletion permission:** Low relevance to the current document alone does not justify `REMOVE` when the unit carries valuable architectural, operational, or historical context belonging elsewhere (`MOVE` or `FLAG`).
- **`KEEP` does not freeze placement:** `KEEP` preserves content that is relevant and important for the document, while its section and relative order remain subject to regrouping and reader-oriented ordering.
- **Content action vs. placement:** `MOVE` transfers information to another document. Section and order changes within the same document are recorded separately as `placement`, so `KEEP` can accompany a placement change.
- **Bounded fallback on ambiguity:** When a destination is undecided, destination context is unavailable, or claims conflict without authoritative resolution, the workflow returns to prior assessment or yields `FLAG` / `REVIEW` under the bounded `Revision Controller`.

### Caveat retention and exposure

Ask: **If this caveat is omitted, will readers misunderstand a claim in this document or make a different decision?** Distinguish preserving information in the corpus from exposing it in each document.

| Effect of omission in the current document | Treatment |
| --- | --- |
| Changes the meaning of a claim or materially affects the reader's decision | Retain the minimum necessary condition near that claim |
| Matters to a subset of readers but is not needed to interpret the main text | Preserve details in an appropriate document and link where useful |
| Needed for provenance or later reuse, without affecting the current reader's decision | Preserve in the evidence record; omit from the current text |
| The same condition is already adequately stated | Consolidate the duplication |

Adjust claims and caveats together: narrow an overbroad claim or move the claim and its supporting detail together rather than deleting only its limitation. A link cannot replace a condition necessary to interpret the visible claim. Verify destination preservation before removing duplicated detail; unknown preservation yields `FLAG` / `REVIEW`. These decisions depend on the claims retained in the revised document, so reassess after editing.

## Module responsibilities

### Contract Resolver

Validate required fields; normalize document type, target Korean register, required information, and evidence sources. Assumptions must be recorded when a user did not explicitly supply context.

### Rule Validators (deterministic)

JSON schema validation, required sections/terms, explicit forbidden phrases, stable terminology, and checkable invariants (for example, retained identifiers or literal numbers). Pattern-based Korean register checks are heuristic unless disambiguated; quotes, code fences, headings, and other exceptions must be considered.

### Semantic Reviewer (model-assisted)

Analyze whether a span contributes to the reader's goal, belongs in this document, needs a qualifier, or conflicts with another claim. Contradiction checks must compare subject, scope, condition, time, quantifiers, and attribution rather than merely opposite words.

**No semantic verdict is unconditionally deterministic:** even if the reviewer outputs valid JSON, it can misunderstand meaning. `FLAG` and `REVIEW` remain valid outputs.

### Findings and gate

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

Offsets refer to the unchanged draft. Versioning and exact offset convention must be fixed before implementation (recommend Unicode code-point offsets plus document hash).

Gate states:

| State | Meaning |
| --- | --- |
| `PASS` | All configured hard checks passed; no blocking findings remain |
| `REVIEW` | No confirmed hard failure, but unresolved semantic concerns need a decision |
| `FAIL` | Confirmed hard check or blocking requirement failed |
| `STOPPED` | Revision limit reached, no progress, or execution error; report outstanding issues |

A reviewer can raise a potential contradiction, but an unverified model judgment alone must not silently rewrite authoritative facts.

### Revision Controller

1. Receive findings and a protected list of facts/qualifiers.
2. Produce minimal, targeted edits; prefer patches over full rewrites.
3. Re-run all relevant checks on the **whole** revised document.
4. Compare required content and prior findings; reject regression.
5. Stop on pass, human-review requirement, repeated state, or attempt limit (default proposal: three).
6. Return the final draft **and** unresolved findings, never a falsely clean status.

The controller enforces the loop externally. A skill or prompt may guide the model, but cannot by itself guarantee calls or a final gate.

## Future design: vector-assisted routing

> **Status: unimplemented future design.** Vector-assisted routing is neither implemented nor evaluated. No embedding providers, runtime dependencies, numeric importance scales, similarity thresholds, or executable schemas are fixed.

When routing information across multiple documents or large drafts, vector retrieval can assist candidate discovery before editorial review:

1. **Profile and unit embeddings:** Compute embeddings for target document profiles (capturing audience, purpose, and scope) and extracted source information units.
2. **Candidate retrieval via cosine similarity:** Use cosine similarity to retrieve candidate destination documents (unit-to-profile) and potentially overlapping or related existing units (unit-to-unit).
3. **Contextual review and assembly:** A semantic/editorial review step inspects the retrieved destination context, verifies scope, conditions, and qualifiers, determines context-dependent relevance, importance, and action (`KEEP`, `COMPRESS`, `REVISE`, `MOVE`, `REMOVE`, `ADD`, `FLAG`), integrates new and existing material while preserving facts and provenance, and hands the result to intra-document ordering and whole-document validation.

### Guardrails and boundaries

- **Document affinity vs. intra-document ordering:** Vector similarity estimates which document a unit may belong to (document affinity). Position within a document is decided separately by reader task flow, prerequisites, and importance.
- **Similarity is not importance, truth, or deletion license:** Cosine similarity does not measure editorial importance, establish factual truth, or justify `REMOVE`.
- **No blind merging:** Overlapping or contradictory units surfaced by similarity must not be merged automatically; scope, conditions, quantifiers, and provenance must be checked first.
- **Provisional missing destinations:** If a suitable target document does not exist or cannot be confirmed, the destination remains provisional (`FLAG` / `REVIEW`). The system must not automatically create or publish new documents.
- **Retrieval/routing vs. RAG:** Using similarity search alone to shortlist candidate destinations or related passages is **retrieval/routing**. Supplying retrieved destination passages to a model during draft synthesis or revision constitutes **RAG (Retrieval-Augmented Generation)**.

## Boundaries

- **Core engine:** portable library for contracts, findings, rules, and orchestration.
- **Adapters (later):** CLI for local use; MCP for agents; optional editor/CI integrations.
- **Skill (later):** task-specific guidelines and examples, not the enforcement mechanism.

Do not use automated editing to settle factual disputes when no trusted source can determine the truth.

## Security and provenance

Treat source documents, retrieval results, and model outputs as untrusted input. Ignore instructions embedded in text being edited. Keep immutable source snapshots and associate findings with content hashes. Avoid remote uploads by default; make model/provider selection and data retention explicit before any external processing.

## Open decisions

- Claim extraction representation and cross-paragraph linking.
- Information unit granularity for segmentation and routing (clause, sentence, claim, or paragraph).
- Document profile representation for audience, purpose, and scope embeddings.
- Evaluation protocol for candidate retrieval quality and cross-document misrouting risks.
- Calibration between vector similarity signals and editorial relevance/importance judgments.
- Korean morphology analyzer and register false-positive handling.
- How to measure reader usefulness without rewarding shorter output by default.
- Whether semantic warnings block delivery or allow a labeled `REVIEW` state.
