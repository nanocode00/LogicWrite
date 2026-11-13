# Capability pilot implementation plan

Spec: `docs/golden-set-expansion-design.md`, merged PR #32 at `879d15b`.

Goal: prepare separated evaluation-only D/Q candidates and one human review package;
never alter the active v3, Core, policies or consumers. All cases remain provisional.

Implementation calls: start with six cases per type; add simple-axis T2/T9 cases (57 total) to cover the five/six required
subscenarios; calibration is the first case per type, a subset, not nine extra samples.
Prioritize pinned permissively licensed public documents, with explicitly labeled
controlled edits and Korean synthetic boundary cases. All published material is exposed
development data. No holdout is collected or claimed. Source-family counts are separate
from task counts. AI counterreview is input-only and never a human judgment.

- [x] 1. Capture pinned sources/license notices and build input/answer/review schemas.
- [x] 2. Write rejection tests first, then implement a read-only integrity validator.
- [x] 3. Build nine calibration tasks; inspect ambiguity and revise the form before expansion.
- [x] 4. Expand to at least 54 candidates; validate references, complete alternatives and coverage.
- [x] 5. Obtain independent input-only AI counterexamples; preserve raw reviews and reconcile.
- [x] 6. Prepare input-first batch review, empty human responses, coverage and regression report;
      open a Draft PR without merging.

Review focus: unavailable evidence versus missing input; alternative bundles versus
forbidden outcomes; source family inflation; answer leakage; preservation of human edits
on validator failure. Tests corrupt copies and verify validator is read-only. Semantic
consistency is an explicit AI/human review task, not a claim from structural checks.

Shared interfaces: schemas define JSON records consumed by validator and review package;
input SHA binds answer and review; source registry binds snapshots and license bytes.

Implementation complete: 57 provisional tasks; 9 calibration subset; 36 public originals and 21 synthetic tasks. No human review/freeze/holdout completion claim. Independent code review found two Important issues; both were reproduced RED then fixed GREEN. Historical input binding received an additional RED/GREEN regression.
