# Evidence boundary design and implementation plan

User-authorized scope: separate immutable Golden Set evidence from current Core; do not edit any existing evidence, Core implementation, #33 or #34; produce a separate Draft PR.

## Design

Historical trust root: full Git commit `879d15b8fa267010217d9310b72d1066fda74f99`, tree `b9d324aac007ddb663984151bb1a5081a22001cf`. Existing manifests, validators, tests, consumers, input/answer/judgment/approval/execution records remain byte-for-byte unchanged.

Use a new execution layer, not manifest exclusions/resealing or changes to historical validators:

1. Read every pinned Git blob. Validate all existing evaluation files and test fixtures against those objects in the current evidence store. Verify all source/environment/documentation blobs in the historical checkout against the same tree.
2. Run every historical evaluation test unchanged in a temporary local Git checkout of that revision. Historical validators may retain their original current-tree preservation semantics inside that historical tree. Keep Git ancestry available for validators using historical `git show`.
3. Run current experiment regressions and new boundary tests in the actual current checkout. New evaluation version packages run in the current checkout, rather than silently inheriting the historical test environment.
4. Reuse existing active-v3 consumers: generate offline predictions with current Core, then compare in the validated historical checkout. This keeps label loading after prediction and preserves all original input binding/metric/approval checks. Expose this through the new execution layer; do not monkeypatch frozen validation functions.
5. Report history revision, current revision/source hashes, Python/dependency versions, individual commands, test counts/failures and prediction-comparison provenance separately. Original exact dependency lock was not recorded; do not invent one.

Alternatives rejected: excluding Core paths from old manifests loses evidence; modifying frozen validators/consumers breaks nested hashes; running everything against an archive without Git loses historical provenance checks. Bare old historical test commands remain snapshot-specific and are not the new whole-repository command.

## RED -> GREEN tasks

- [x] Integrity API: synthetic current Core mutation is allowed, input/judgment/approval/manifest/validator/fixture tampering and missing Git history fail. Snapshot/source/requirements tampering fails. Pin substitution fails.
- [x] Execution: verify separate suite roots and all original tests executed, current failing Core test causes nonzero result, real #33 combined tests pass. Historical execution failure cannot become success.
- [x] Consumer adapter: current Core offline prediction -> historical comparator, no label reads before predictions; wrong input binding fails; current source identity reported.
- [ ] Full runs: standalone latest-main branch and temporary combined #33 tree, diff check and unchanged old blobs, Draft PR only.

## Review focus

No stale/cached integrity verdicts; no symlink/path escape; missing/corrupt Git objects; all historical tests preserved; no current failure hidden by historical success. Current evidence must be rechecked after execution. Exact historical environment equality is not asserted.
