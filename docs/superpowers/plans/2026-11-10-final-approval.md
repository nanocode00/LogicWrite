# Core 2-B final approval implementation plan

**Goal:** Explicit, evidence-bound human approval policy without enabling real approval issuance.

**Architecture:** Preserve structural/semantic reports and live receipts. Build a versioned request over actual artifact bodies, verify a separate human decision against an independently configured test evidence source, and always hold delivery in REVIEW (FAIL for confirmed validation failures).

**Spec:** User's Core 2-B requirements and approved test-only trust boundary; details in `docs/final-approval-policy.md`.

**Tech stack:** Python standard library, unittest; no external authentication/storage dependencies.

## Constraints and review focus

- No actual file application, automatic repair, RAG/LangGraph or golden-set promotion.
- JSON, self-digests and model judgments do not authenticate a human.
- Failed/stale/restarted validation, malformed authority output, mutation during lookup, and all destination/version changes must fail closed.
- Human judgments must cover every semantic check, even model `supported`, and other structural warnings. Confirmed violations cannot be waived.
- Production issuance remains disabled; only host-configured `test_only` authority adapters are supported.

## Tasks

1. Add `test_final_approval.py` covering bound requests, explicit synthetic human approval, forged/rehash/reused/stale decisions, unsupported sources, resolutions, expiry/revocation and missing receipts. Observe failure before implementation.
2. Add `final_approval.py`: `build_approval_request(...)` and `evaluate_final_approval(...)`. Rebuild and independently verify audit/current inputs, bind hashes and snapshot scope, compare independent record and human identity, validate bounded lifetime and evidenced human resolutions. Return sealed audit with decision/reason/unresolved items, never delivery authorization.
3. Add pipeline wrappers and optional integration approval inputs; invalidate approval artifacts on controller stop. Add integration/adversarial tests, run existing regressions and document support limits. Create a separate Draft PR; do not merge.

## Execution notes

- User approved test-only implementation direction. Execute inline on separate feature branch; preserve existing gold-pilot worktree.
- Baseline: full_document_control unittest suite, 272 tests passed.
- Antigravity documentation draft failed with RESOURCE_EXHAUSTED; author documents locally and obtain independent final code review.

## Verification and decisions

- Tasks 1–3 implemented. Full Core suite: 303 passed, including 31 new approval tests; minimal gate 31, extraction analysis 27, extraction AB 17 passed (378 total).
- Independent reviewer found no demonstrated bypass; separately checked receipt age boundary at 900 seconds, negative age, missing receipt and mutation during lookup.
- Conservative policy choices: max decision lifetime 24 hours; live validation receipt age strictly less than 15 minutes. These require fresh validation and a new decision after expiry, rather than refreshing old evidence.
- Branch remains based on PR #18 main. Publication is a separate Draft PR, with no merge.
