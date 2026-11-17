# Integrated reconstruction pilot execution plan

Goal: establish executable B0/B1/B2 boundaries without changing protected assets.
Architecture: input-only HTTP harness plus separate evaluator records; no Core changes.
Spec: ../../evaluation/integrated_reconstruction/DESIGN.md and user request dated 2026-11-17.
Execution: directly in this session; no delegated agents.

- [x] Verify live PR branch and preserve clean existing worktree; fast-forward to 82180fb.
- [x] Inspect development manifest, design, project proposal, roadmap, interfaces and Core code.
- [x] Check model environment without extracting credentials; distinguish CLI login from API readiness.
- [x] Document B2 incompatibilities and reject semantic/authority-changing adapters.
- [x] Prepare identical evaluation inputs for B0/B1, configuration and opt-in reproducible runner.
- [x] Record all unobserved/unevaluated D/Q/F/HITL criteria and case statuses.
- [x] Test evidence boundaries, existing evaluation regression, gold integrity and preservation.
- [x] Prepare comparison report and proposals; leave human judgments unset.
- [ ] Real model execution: blocked by missing dedicated API environment; B2 integration unsupported.

Live execution remains outstanding and is explicitly not a completion claim for model evaluation.
Commit/push scope is only this experiment directory on the existing PR #36 branch.
