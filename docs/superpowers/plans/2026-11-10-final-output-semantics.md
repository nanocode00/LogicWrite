# 2-A Full Output Semantic Validation Plan

Goal: independently review actual full output snapshots without granting delivery or stage approval.
Architecture: retain the existing eight-check structural report unchanged; append a separate, versioned final semantic report and a sealed combined audit. Model-independent callback review is optional and bound to complete snapshots and current upstream artifact bodies. No write-back, retries, RAG or stage approval.

- [x] Add adversarial tests for literal changes, contextual movement, full-document coverage, callback failures, stale results and approval forgery; run them before implementation.
- [x] Implement `final_semantic_validator.validate_final_semantics(bundle, analysis, org, preview, result, *, destination_snapshots=None, reviewer=None, max_review_chars=48000, timeout_seconds=30)` and process-local receipt verification. Reuse token extraction only; never reinterpret analysis judgments as output review.
- [x] Add combined audit and integration/controller invalidation while preserving structural report APIs and checks. Expose the final-stage wrapper from pipeline.py.
- [x] Document actual callback/report schemas, execution evidence limits and the remaining 2-B boundary; preserve milestones and evaluation claims.
- [x] Run all four regression suites and diff checks and review the diff.

Publication: commit this scoped change and open a Draft PR without merging.

Review focus: complete destination context, duplicate occurrence provenance, semantically equal rewrites, model truncation/timeouts, rehashed report forgery. Execution uses the current clean checkout on a separate feature branch based on refreshed main.
