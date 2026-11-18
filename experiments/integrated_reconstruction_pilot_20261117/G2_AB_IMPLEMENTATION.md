# G2-A/B design and implementation plan — 2026-11-18

Spec: user G2-A/B request; B2_CORE_READINESS_20261117.md, G0_G1_IMPLEMENTATION.md and DOCUMENT_SET.md.
Goal: source-bound shared analysis and per-task organization eligibility only.
Architecture: separate generic document_set_analysis.py and document_set_planning.py; reuse pipeline.parse_markdown_blocks/verify_block_partition, not single-document executors. JSON-compatible deterministic artifacts, no new dependencies. Preserve G1 and all legacy execution/approval behavior.

## Contract and trust decisions

Caller pins the G1 contract outside untrusted input. Analysis is reproducible from that contract; planner regenerates and compares the entire artifact, rejecting omissions, stale results and resealed forgeries. The contract pin asserts supplied identity, not genuine external authority. No evaluator imports, IR IDs, answer strings, model callbacks, file-path reads or network calls in generic modules.

Analysis units are full Markdown blocks with exact quote, codepoint/UTF-8 byte/line ranges, document/source hashes and metadata. Blocks partition every provided byte, including explicitly excluded whitespace. Literal observations (numbers, conditional/exception/status cues, identifiers) retain exact spans and are not semantic extraction claims. Shared exact-text and explicit-link indexes span the whole set; cooccurrence and shared literal candidates stay unresolved. No general semantic contradiction detector is claimed. Unsupported/partial material is explicitly incomplete; complete literal coverage is distinct from completed semantic analysis.

Planner accepts separately pinned explicit task proposals (whole-block sources, target/anchor, action, rationale/evidence, dependencies). No supplied proposals means KEEP coverage plus a held request-decomposition task: the natural-language request is never fabricated into a finished organization plan. Caller may provide input-only scoped issues with quoted evidence and accountable decision owner, pinned with proposals; they remain caller assertions, not analyzer-discovered semantic truths. Every global pending question holds changed tasks unless caller binds its scope. Unknown dependency/scope/cycles, overlapping writes, unit conditions, destination context and permissions are checked. Source constraints remain explicit obligations; eligibility is conditional planning, never an assertion that prose constraints or meaning have passed.

KEEP is reference/preservation. PLACE: one paragraph before/after a same-document paragraph. MOVE: one paragraph to another declared editable document, append only. CONSOLIDATE: two exact full paragraphs within the same document, retaining all provenance and local obligations; context/conditions still require review. REVISE: bounded existing expression operation settings, semantic review required. REMOVE/new documents/general rewrite/internal destination placement unsupported. Changed format_only denied; undefined formatting held. Read-only and non-output changes denied; pending authority held. No candidate/output documents produced and prepare_reconstruction stays unsupported.

## Tasks and checks

- [x] 1. RED: generic and IR input-only coverage/integrity tests. GREEN: shared block graph and deterministic analysis replay.
- [x] 2. RED: all four statuses, permission/format/uncertainty/partial HITL/dependency/unsupported/mutation/no-execution tests. GREEN: scoped planner and request pin validation.
- [x] 3. Add independent synthetic variants; offline input-only IR-001–003 artifact runner and examples. Verify no semantic conflict invented, all 14 documents covered.
- [x] 4. Review branch diff and preservation hashes, full Core discovery and official evidence runner to new /tmp report. Freeze files while runner executes. Record results, scope-only commit/push existing branch; no new PR/merge/G2-C.

Review focus: forged analysis with recomputed digest; omitted uncertainty bindings; mutation of read-only destination; malformed/cyclic task requests; exact duplicate claims with differing local constraints; unsupported Markdown/partial snapshots; write overlap through placement anchors. Tests include counterexamples and renamed/reworded synthetic sets. Existing tracked source/evaluation/pilot files pinned externally before edits; other worktree Git states preserved.

Execution notes: 32 generic/IR tests plus 4 offline-runner tests. First RED was missing analysis module; later REDs covered missing output-coverage field, malformed URL, reserved question IDs, indirect reference question bindings, ancestor/destination conditions, Korean conditional cues, and read/write dependencies between proposals. All fixed without relaxing prior assertions. Initial tamper fixture assigned edit to an already-edit unit; corrected to an actual value change. Scoped REVISE test now supplies a supported operation shape. Positive MOVE fixture now has a condition-free destination; separate negatives assert both source and destination condition holds.

Review: separate read-only reviewer identified 3 dependency/context issues; reproduced with failing tests and fixed. Final own review found a task could change another task's read evidence without a hold; added failing test then read/write dependency conflict detection. The first official run passed 916 tests before this additional fix; final official run uses a new path. Source code and artifacts frozen while each runner executes.

Final verification: PASS 917 tests / 31 suites, 0 failures/errors/skips/expected failures/unexpected successes. Core 431, pilot 63. Existing 1,072 tracked files unchanged; other 15 worktree states unchanged. Evidence source identity refers to frozen validation snapshot; final report/result-copy additions are documentation of that run. G2-C not started.
