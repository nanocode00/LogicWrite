# Capability pilot implementation review

Reviewer: Codex AI, separate implementation review. This is not an input-only case review, human judgment, or gold approval. Earlier raw input-only reviews remain unchanged.

Scope: `validate.py`, `test_integrity.py`, all three `*.schema.json`, `PLAN.md`, and `docs/golden-set-expansion-design.md`. No code or candidate data was modified. Mutation probes used disposable copies outside the repository. Only this report was written.

Validation evidence: `python3 -B -m unittest discover -s evaluation/capability_pilot -p test_integrity.py` completed with **15 tests passed**. Additional mutation probes below passed the validator when they should have been rejected. They used `validate_package(copy_root, require_reviews=False)` because review linkage was still pending in the package at inspection time. This option permits absent records; a present record still traverses the exact same validation and counting branch.

## Important 1: an empty non-independent record counts as an independent AI review

Locations: `validate.py:177-196`; `review.schema.json:23` validates only the reference envelope, not the raw review record. In particular, `validate.py:194` uses substring membership, so `'' in document_content` succeeds, and line 195 only requires a nonempty evidence array. The raw record need not have an assessment or any counterexample analysis. Its top-level reviewer/method declarations are ignored.

Reproduction in an isolated package copy:

1. Create `raw_reviews/probe.json` with `reviewer: "author AI, not independent"`, `method: "answers read; not input-only"`, and `cases: [{case_id: "CP-T1-01", input_sha256: <current input hash>, evidence: [{document_id: "draft", quote: ""}]}]`. Do not provide assessment, preservation judgments, alternatives, counterexample, unresolved conditions, or input defects.
2. Point `reviews/CP-T1-01.json.independent_ai_counterreview` to that file and `/cases/0`, using its actual raw SHA256, the current input hash, and `superseded_input: false`.
3. Run the validator on the copy with pending AI records allowed.

Observed result: **ACCEPTED**, `independent_ai_reviews: 1`. This is not a request for a machine to prove reviewer independence: the file explicitly declares the opposite method, has no review content, and cites no nonempty text. The current structural validator can and should distinguish this from a completed review. Under the default mode the same branch counts it, with only other missing reviews determining whether the package completes.

Impact: the reported review-completion count can advance without an actual input-only counterreview, undermining PLAN's independent-review step and raw-review evidence boundary. Input SHA and raw-file SHA remain valid, so those checks do not catch the omission.

Suggested correction: add a raw counterreview schema with required case assessment fields and nonempty strings/quotes; validate it before resolving/counting its case; reject an explicitly incompatible method/exposure declaration and keep method metadata distinct from externally established independence. Add rejection tests for empty quote, missing assessment, and non-input-only declaration. Continue to state that schema conformity cannot prove the review's substantive quality or historical independence.

## Important 2: duplicate decision IDs silently collapse the fixed metric denominator

Locations: `validate.py:115-117,129-130`; `answer.schema.json:122-151,204-233`. The decision arrays do not require unique IDs, and the validator compares sets of IDs rather than checking uniqueness before comparing maps. The effect maps are unique-key objects; the arrays can contain multiple different obligations with the same ID.

Reproduction in an isolated package copy:

1. Load `answers/CP-T1-01.json`.
2. Deep-copy `D.required_decisions[0]`, retain its `id` and valid evidence references, replace its `criterion` with a second distinct requirement, and append the copy to `D.required_decisions`.
3. Leave `required_effects`, every alternative bundle, and the recall denominator unchanged.
4. Validate the copy.

Observed result: **ACCEPTED**, with `len(required_decisions) == 3`, `len(required_effects) == 2`, and `required_decision_recall.denominator == 2`. The analogous set comparison exists for forbidden outcomes. No semantic reading is required to identify the ID collision and loss of one-to-one correspondence.

Impact: a third required criterion can disappear from the fixed effect/alternative/denominator representation. This defeats the intended structural consistency of complete alternative bundles and explicit fixed denominators, even though semantic evaluation remains a later review task.

Suggested correction: reject duplicate IDs in required decisions and forbidden outcomes before set comparison; apply appropriate namespace uniqueness checks to the other ID-bearing lists as well. Add tests with same-ID/different-criterion entries and confirm rejection without rewriting records. `uniqueItems: true` alone is insufficient because the two objects have different criterion strings.

## Other reviewed boundaries

No Critical finding was reproduced. No additional Minor item is necessary to the requested scope.

The implementation correctly labels its output as structural integrity rather than semantic D/Q proof (`validate.py:2,213`, PLAN's final review paragraph). Existing tests cover stale input bindings, answer-only field rejection, provided-document hashes, source snapshot hashes, evidence spans, forbidden-effect contradiction, fake gold approval, scope/read-only role conflicts, partial-output abstention distinction, and preservation of human response bytes/mtime on failure. These passing checks do not establish semantic coverage, actual reviewer independence, upstream authenticity beyond the supplied pinned registry, or human approval. The proposed corrections above retain that distinction.
