# Evaluation protocol

## Goal

Test whether validation-assisted revision improves **reader usefulness and consistency** without dropping necessary information. Shorter text is not automatically better.

## Corpus

Start with the synthetic fixtures in `tests/fixtures/cases.json`; they are intentionally small and illustrative. Expand to consented/public, permission-safe examples of:

- README or installation guides
- Pull request descriptions
- Release notes and changelogs
- Design documents and verification reports
- User-facing instructions

For each case annotate audience, purpose, document type, target register, required information, and expected issue/action. Include **negative examples** where long detail, apparent opposition, or mixed quoted speech is legitimate.

Keep a held-out split; avoid tuning rules on every case used for evaluation.

## Baselines

Compare three conditions using the same source facts and writing brief:

1. **B0 — direct generation:** writer alone.
2. **B1 — prompt-only:** writer prompted to be concise, coherent, and audience-aware.
3. **B2 — LogicWrite:** writer plus validation findings and bounded revision controller.

For existing drafts, use the same draft as input for all editing conditions. Record model, temperature/settings when available, contract, prompt, and tool versions. No quality results are claimed yet.

## Measures

| Metric | How to assess |
| --- | --- |
| Reader-task success | Can independent readers answer or act on the intended question? |
| Essential-information retention | Human-labeled required facts/conditions retained after edits |
| Irrelevant information | Human-labeled unnecessary spans left in final document |
| Contradiction detection | Precision/recall on labeled claim pairs; count false alarms |
| Register consistency | Violations per eligible Korean sentence, excluding quotes/code |
| Revision regression | New factual or logical errors introduced by editing |
| Reviewer time | Time to understand, verify, and approve the result |
| Length | Descriptive only; never the sole optimization target |

Report sample sizes, uncertainty, and per-document-type failures. Do not equate heuristic "AI-likeness" with writing quality.

## Annotation workflow

Two people independently label a subset when feasible. Each proposed issue includes a text span, rule, proposed action, and rationale; annotators mark `agree`, `disagree`, or `uncertain`. Resolve disagreements with a documented decision, not an arbitrary model vote.

A `FLAG` is a valid outcome when evidence cannot decide which assertion is true. Examples with uncertain ground truth should not be scored as definite contradiction failures.

## Guardrails

- Preserve provenance, numbers, constraints, and qualifiers unless source evidence authorizes change.
- Never treat a missing detected contradiction as proof none exists.
- Keep critical unresolved issues visible after the revision limit.
- Avoid using private documents without permission and appropriate redaction.

## Immediate next experiment

Run a small manual pilot on 10–20 examples, record B0/B1/B2 drafts, blind-review reader usefulness and retention, and inspect whether the validator's false alarms introduce more work than they save. Expand only if the pilot exposes a measurable benefit.
