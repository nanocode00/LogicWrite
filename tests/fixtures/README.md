# Annotated fixture set

`cases.json` contains **synthetic examples**, not a benchmark result or tested implementation.

Each case specifies:
- `id`, `description`, `document_type`
- `contract`: intended audience, purpose, register, and required information
- `input`: the unedited text
- `expected_findings`: expected rule, action, evidence span(s), and reason

An empty `expected_findings` array means **no issue should be raised for the targeted concern**. It does not certify flawless prose.

## Rules in this seed set

- `AUDIENCE_IRRELEVANCE`: detail does not help intended reader.
- `CONTENT_REDUNDANCY`: repeated content adds no meaningful distinction.
- `REGISTER_INCONSISTENCY`: narration violates an explicitly selected Korean register.
- `CLAIM_CONTRADICTION`: incompatible assertions under the same subject/time/scope.
- `REQUIRED_INFORMATION_MISSING`: a contract-required fact is absent.
- `UNSUPPORTED_CLAIM`: an assertion demands evidence unavailable in supplied sources.

Actions are `KEEP`, `COMPRESS`, `REVISE`, `MOVE`, `REMOVE`, `ADD`, or `FLAG`. `REVISE` preserves information while correcting wording, register, or terminology; `COMPRESS` addresses verbosity or repetition. The labels represent *human-designed expected judgments*, not deterministic truth for every linguistic context.

## Important negative controls

Cases with valid policy exceptions, attributed opposing opinions, or necessary implementation detail should not be flagged simply because they contain contrasting claims or long explanations.

## Next step

Add IDs and independent human review to real, permission-safe samples. Before implementing automated scoring, freeze fixture structure and write a JSON Schema with precise field and offset conventions.
