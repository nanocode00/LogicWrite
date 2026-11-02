# Roadmap

This is a proposed sequence, not a delivery promise. A milestone advances only when its exit criteria are met.

## M0 — Evidence and evaluation foundation (now)

- [x] Establish public repository and initial design documents
- [x] Define synthetic, labeled examples in `tests/fixtures/cases.json`
- [ ] Collect 10–20 permission-safe samples from real README, PR, release, and report writing
- [ ] Have a human reviewer confirm audience, purpose, and expected action for each example
- [ ] Freeze fixture schema v1 and reserve held-out cases
- [ ] Document baseline prompt-only evaluation

**Exit:** reproducible labeled corpus with positive and negative examples; disagreements recorded instead of overwritten.

## M1 — Deterministic rule engine

- [ ] Define versioned Writing Contract and finding schemas
- [ ] Implement contract parser and deterministic validators
- [ ] Handle Markdown code blocks, quotations, headings, and exceptions
- [ ] Provide CLI that returns machine-readable findings and exit status
- [ ] Add unit tests and CI

**Exit:** stable results for equal inputs; no false PASS for missing required contract fields.

## M2 — Semantic checks

- [ ] Evaluate relevance and information location against audience/purpose
- [ ] Detect potential conflicting claims, including quantifiers, time, and scope
- [ ] Capture supporting spans and label uncertainty
- [ ] Test negative examples (legitimate exceptions and attributed disagreements)
- [ ] Add human-review path for unresolved factual claims

**Exit:** evaluation on held-out data; false positives and false negatives reported explicitly.

## M3 — Revision controller

- [ ] Targeted edit proposals: KEEP / COMPRESS / MOVE / REMOVE / ADD / FLAG
- [ ] Protect required information and source attribution
- [ ] Revalidate the entire document after each edit
- [ ] Limit iterations; detect repeated/no-progress states
- [ ] Return PASS / REVIEW / FAIL / STOPPED with an audit trail

**Exit:** bounded edit/recheck workflow demonstrable on fixtures, including an unresolved-case stop.

## M4 — Agent integrations

- [ ] Provide an MCP interface to the validator
- [ ] Add an optional Skill describing appropriate use
- [ ] Offer opt-in editor or PR workflow integration
- [ ] Publish measured comparison to an unassisted writer and prompt-only revision

**Exit:** usable integration without suggesting that a plugin can universally intercept or guarantee every agent output.

## Prioritization rule

Do not optimize for length or AI-detector scores at the expense of factual meaning. Prefer a small engine that reliably catches a few documented problems to a broad evaluator with unmeasured confidence.
