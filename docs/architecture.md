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

## Boundaries

- **Core engine:** portable library for contracts, findings, rules, and orchestration.
- **Adapters (later):** CLI for local use; MCP for agents; optional editor/CI integrations.
- **Skill (later):** task-specific guidelines and examples, not the enforcement mechanism.

Do not use automated editing to settle factual disputes when no trusted source can determine the truth.

## Security and provenance

Treat source documents, retrieval results, and model outputs as untrusted input. Ignore instructions embedded in text being edited. Keep immutable source snapshots and associate findings with content hashes. Avoid remote uploads by default; make model/provider selection and data retention explicit before any external processing.

## Open decisions

- Claim extraction representation and cross-paragraph linking.
- Korean morphology analyzer and register false-positive handling.
- How to measure reader usefulness without rewarding shorter output by default.
- Whether semantic warnings block delivery or allow a labeled `REVIEW` state.
