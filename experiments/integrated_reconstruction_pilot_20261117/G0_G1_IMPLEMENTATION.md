# G0/G1 implementation plan and decisions

Spec: B2_CORE_READINESS_20261117.md and user G0/G1 request, 2026-11-17.
Goal: offline evidence for existing limits, then a separate document-set-v1 admission/permission interface. Python/jsonschema; no new dependencies or paid calls.

- [x] G0: add characterization tests for single/multiple scopes, native final audit and external complete pairs; inspect all six frozen Qwen candidates as validator_shadow. Record hashes before changes.
- [x] G1 RED: tests for input-only IR conversion, generic schema, identity/hash/provenance/output binding, pinned permissions, incomplete/pending holds, no-op candidates and unsupported reconstruction.
- [x] G1 GREEN: `document_set.py`, strict `document-set-v1.schema.json`, separate `ir_document_set_adapter.py`. No legacy executor changes. Core must not import IR or evaluator metadata.
- [x] Verify: Core unittest discovery and official evidence runner outside repository, integrity comparison, final diff review, scoped commit/push to existing PR #36.

Design: adapter accepts validated IR input objects only, never reads document paths. Common model preserves request/context, per-document role/authority/access/completeness/content/hash/provenance, output flags and pending questions. Generic Core validation rejects malformed input and inconsistent scope/provenance; admission never means semantic PASS or execution. Callers pin a canonical contract digest outside untrusted candidates before permission/candidate checking; a self-computed hash cannot authenticate source authority. Only unchanged format_only content is mechanically resolved here; every changed format_only candidate is REVIEW pending G3. Read-only changes and unauthorized destinations FAIL. Edit permission is eligibility, not semantic certification. External lookup/new document creation/application remain unsupported and need separate authorization design.

Ruling: retain the existing single-document runtime intact and expose an explicitly unsupported G2 entry point. This follows the requested separate-version expansion and avoids pretending G1 adds a reconstruction engine.
Ruling: IR v2 partial/unknown inputs retain their metadata but admission is held in REVIEW; original gaps also remain pending without blocking independent, explicitly granted edit permissions in complete v1 inputs.
Review focus: resealed permission escalation; duplicate source paths; omitted writable output scopes; candidate spoofed baseline/path/hash; unknown operations and malformed inputs. Tests must cover each.

Execution notes: initial G0 expectation that run_pipeline raises was corrected after reading its exception handler: low-level admission raises; the facade catches and returns STOPPED with no candidate. No production behavior/test criterion was weakened. New module import failure recorded in /tmp/logicwrite-g1-red.log; hardening tests then reproduced unhashable operation/version failures and conflated edit/output flags before their fixes.

Ruling: generic editable references may remain outside output_target; IR adapter still selects all writable documents required by IR delivery. This preserves the distinction between access and submission without granting extra outputs.

Verification: official runner PASS, 881 tests in 31 suites, 0 failures/errors/skips. Core 399, pilot 59. Existing 425 source/evaluation/pilot files unchanged; other 15 worktrees retain original Git status. Review found no material G0/G1 issues. Commit/push to existing PR #36 remains the final delivery step.
