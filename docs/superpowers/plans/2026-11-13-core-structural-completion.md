# Core structural completion implementation plan

**Goal:** Audit actual Core boundaries and fix reproducible structural defects without evaluation-data changes or approval-policy changes.
**Basis:** User request authorizes independently verifiable P0 fixes without another approval round. Base `879d15b8fa267010217d9310b72d1066fda74f99` (origin/main fetched 2026-11-13).
**Architecture:** Preserve the existing Python candidate pipeline and independent validators. Hold unsupported edits as REVIEW; keep diagnostics advisory.
**Constraints:** No evaluation changes, no semantic-answer tuning, no approval issuance or PASS relaxation, no automatic merge.

## Design choices

- Reuse existing Organization/Reconstruction/RepairLoop rather than adding executors.
- Preserve the single-scope gate. Investigation showed multi-document contracts stop before Organization; destination forwarding alone is insufficient, so defer coordinated multi-document support.
- Describe generated MOVE as append (`section_path=[]`); explicitly hold requested destination section/anchor placement rather than implementing a new multi-document layout engine. Independent final validation must also detect unsupported placement on forged candidates.
- Route mixed failures to the earliest responsible module before invalidating descendants.
- Add advisory per-unit D/Q observations to sealed reconstruction artifacts, derived from actual trace and ledger, including held/no-output states. These are not semantic-quality scores or validation evidence.

## Tasks (each uses RED -> implementation -> GREEN)

- [x] Integration: pin existing multi-document rejection at Analysis; record missing destination forwarding as follow-up rather than changing the input/approval contract.
- [x] MOVE bounds: generator emits no invented section. Explicit section/before/after anchor requests produce preview + warning; forged candidate independently violates Organization fidelity. Existing append/atomic-condition tests remain green.
- [x] Controller: combined Analysis/Organization/Expression failures select Analysis; combined Organization/Expression select Organization, invalidate all descendants/reports and preserve upstream artifacts.
- [x] D/Q: test unchanged, deterministic compression, held semantic rewrite, MOVE, CONSOLIDATE, REMOVE and unsupported placement. Assert intended decisions remain distinct from actual spans/treatments and incomplete results report no observation.
- [x] Audit: module input/output/validation/boundaries table, structural versus semantic gaps, ranked follow-up work and actual test evidence in `experiments/full_document_control/CORE_STATUS.md`.
- [x] Verify all four experiment unittest suites, executable offline examples, diff/evaluation isolation; review complete diff, push feature branch and open PR without merging.

## Review focus

Complete versus partial destination snapshots; default append versus explicit placement; mixed-module errors; no candidate versus unchanged candidate; unknown semantic rewrites. Existing approval and repair trust/receipt tests remain mandatory.
