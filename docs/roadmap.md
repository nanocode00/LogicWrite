# Roadmap

This is a proposed sequence, not a delivery promise. A milestone advances only when its exit criteria are met.

> **Current status:** M0 is in progress. Only design documents, 12 synthetic seed fixtures (`tests/fixtures/cases.json`), and 20 provisional real-world candidate records (`tests/fixtures/real-world-candidates.json`, summarized in [`docs/real-world-candidates.md`](real-world-candidates.md)) exist today. No validator, module pipeline, CLI, MCP server, or baseline experiment has been implemented or executed.

## M0 — Evidence and evaluation foundation (in progress)

- [x] Establish public repository and initial design documents
- [x] Define synthetic, labeled examples in `tests/fixtures/cases.json`
- [x] Collect 20 permission-safe provisional candidate samples from 5 public repositories (12 non-`KEEP` action candidates and 8 `KEEP` preservation candidates) in `tests/fixtures/real-world-candidates.json`
- [ ] Have an independent human reviewer confirm audience, purpose, preservation/placement judgment, and expected action for each candidate (provisional labels are not gold data)
- [ ] Freeze fixture schema v1 and reserve held-out cases
- [ ] Document the B0/B1/B2 comparison protocol and prompt-only pilot; defer executable B2 runs until the validator and controller exist in M3

**Exit:** reproducible, human-reviewed labeled corpus with positive and negative examples and a locked held-out split; reviewer disagreements recorded instead of overwritten.

## M1 — Contract resolver and deterministic validation gate

- [ ] Define versioned `Writing Contract` and finding schemas (preserving compatibility with existing fixture labels)
- [ ] Implement `Contract Resolver` (required-field checks and assumption recording); reserve semantic intent/purpose alignment checks for M2
- [ ] Implement deterministic `Rule Validators` for protected facts/numbers and explicit terminology invariants; label pattern-based Korean register checks as heuristic
- [ ] Handle Markdown code blocks, quotations, headings, and contextual exceptions
- [ ] Provide CLI that returns machine-readable findings and gate status (`PASS`, `REVIEW`, `FAIL`, `STOPPED`)
- [ ] Add unit tests and CI

**Exit:** stable results for equal inputs; no false `PASS` for missing required contract fields or dropped deterministic invariants.

## M2 — Modular extraction, analysis, and organization checks

- [ ] Implement `Information Extraction & Analysis` checks: segment information units, link claims/conditions/numbers/provenance, assess audience/purpose fit and importance, and detect/recover purpose misidentification
- [ ] Implement `Information Organization` checks: verify cross-document `MOVE` destination context, duplicate consolidation without caveat/number loss, and intra-document `placement` (grouping and reader-task ordering)
- [ ] Detect potential conflicting claims across scope, time, quantifiers, and conditions, while respecting legitimate exceptions and attributed opinions
- [ ] Capture supporting spans and label uncertainty (`FLAG` / `REVIEW`) when evidence or destination context is incomplete
- [ ] Evaluate module-level checks on held-out data (including optional future evaluation of vector-assisted candidate retrieval once core checks are measured)

**Exit:** per-module and whole-document semantic evaluation on held-out data; false positives, false negatives, and unresolved `FLAG` rates reported explicitly.

## M3 — Expression refinement and revision controller

- [ ] Implement `Expression Refinement` proposals (`REVISE`, `COMPRESS`, register/terminology normalization) constrained by protected facts, numbers, and conditions
- [ ] Implement `Revision Controller` routing findings to the responsible module (`Information Extraction & Analysis`, `Information Organization`, or `Expression Refinement`)
- [ ] Enforce downstream invalidation and whole-document revalidation across affected source and destination documents after each edit
- [ ] Limit iterations and stop on `PASS`, ambiguity/human-review blockers (`FLAG` / `REVIEW`), repeated states, or attempt limits (`STOPPED`) with a full audit trail

**Exit:** bounded, module-routed edit and revalidation workflow demonstrable on fixtures, including preservation of required caveats/numbers and clean stops on unresolved cases.

## M4 — Agent integrations

- [ ] Provide an MCP interface to the modular validator and revision controller
- [ ] Add an optional Skill describing appropriate use of contracts, module findings, and review gates
- [ ] Offer opt-in editor or PR workflow integration
- [ ] Publish measured `B0` / `B1` / `B2` comparisons on held-out cases

**Exit:** usable integration without suggesting that a plugin can universally intercept or guarantee every agent output.

## Long-term direction — conversational agent responses

> **Future exploration only.** This is not an M0–M4 deliverable or an implemented capability. The first target remains durable technical documents, while the core information-processing and validation concepts should be reusable for other kinds of agent-generated text.

**Common principle:** A response, like a document, should convey the right information to its intended reader for the current purpose—neither dropping necessary qualifiers nor exposing irrelevant detail. Reuse the shared `Writing Contract`, the three modules, and independent validation rather than creating a separate writing-quality engine.

| Module | Future conversational-response adaptation |
| --- | --- |
| **Information Extraction & Analysis** | Identify the user's actual question, relevant conversation/tool context, required facts and conditions, and details not needed for the current turn. Distinguish omission from destruction of source knowledge. |
| **Information Organization** | Group and order facts **within the response** according to the question and decision/action needs. There is normally no destination document and no cross-document `MOVE`; response-level `placement` handles reordering, while omitting nonessential information from this answer does not delete its source. |
| **Expression Refinement** | Adjust register, terminology, level of detail, and response length to the dialogue rather than imposing a fixed document template. Retain scope, attribution, important safety caveats, and uncertainty. |
| **Validation Gate & Revision Controller** | Check answer coverage, relevance, contradictions, preservation of essential qualifications, and avoidable verbosity. Support pre-generation information planning and post-generation review, without promising error-free semantics. |

**Future design and evaluation questions:**
- Define an optional *output profile* for a conversational response versus a durable document; do not retroactively modify the current contract or fixture schemas.
- Compare direct response, prompt-only revision, and validation-assisted response using question satisfaction, information retention, clarity, over-answering, and latency—not word count alone.
- Account for streaming and tool execution: withholding a final answer for verification can increase latency, while post-stream corrections cannot retract already displayed text. Decide when checking is feasible and how unresolved concerns are disclosed.
- Enforcement requires control over the response-generation pipeline or an explicit invocation point. An optional Skill or MCP tool cannot universally intercept every ChatGPT or agent response.

This direction must not make conversational adapters, response interception, vector databases, or online integrations prerequisites for the first document-oriented MVP.

## Prioritization rule

Do not optimize for length or AI-detector scores at the expense of factual meaning. Prefer a small engine that reliably catches documented contract, boundary, and consistency problems to a broad evaluator with unmeasured confidence.
