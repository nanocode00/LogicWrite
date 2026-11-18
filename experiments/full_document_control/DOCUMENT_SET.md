# Core document-set contract v1 (G1)

`document_set.py` and `document-set-v1.schema.json` are a separate input and permission foundation. The existing `pipeline.validate_input_bundle`, single-document executor, final audit and approval interfaces are unchanged. `prepare_reconstruction` retains its G1 admission-only response. The separate G2-C entry point binds a G2-B plan and a pinned candidate request. See [G2-C execution and examples](../integrated_reconstruction_pilot_20261117/g2-c-offline-20261118/REPORT.md).

| Interface | Meaning |
|---|---|
| `validate_contract(contract, expected_sha256=None)` | Strict schema and document/scope/path/hash/provenance checks. `structural_input_valid` is admission only; incomplete/unknown inputs remain REVIEW with `ready_for_planning=false`. Unpinned admission cannot authorize operations. |
| `contract_digest(contract)` | Canonical JSON UTF-8 SHA-256, distinct from the original input file byte hash and each document's UTF-8 content hash. Caller must pin the baseline outside model/candidate data before use. |
| `check_operation(contract, document_id, operation, trusted_contract_sha256=pin)` | Eligibility for `reference`, `edit_content`, or `format` against a pinned contract. Returns eligible/denied/held/unsupported; **execution_allowed is always false in G1**. Eligibility does not interpret natural-language constraints or certify a specific edit. |
| `validate_candidates(contract, rows, trusted_contract_sha256=pin)` | Exact full output set; candidate SHA, source path and source SHA; declared access. Input-only references cannot be output targets. Does not generate documents or evaluate semantic quality. |
| `ir_document_set_adapter.from_ir_input(raw)` | Separate strict IR v1/v2 input-only bridge. No source paths are opened. Unknown fields, including evaluator/gold fields, reject. Only the two input schemas are read, never answers, criteria, reference outputs or reviews. |

The common model carries request/context/audience/purpose, constraints and pending questions; each document carries ID/role/audience/purpose/authority/access/completeness/source_scope/content/SHA, source provenance, output_target, constraints and pending questions. Unknown audience/purpose remain null, with supplied request/context/role preserved rather than inferred. A document's `access` and `output_target` are separate: an editable reference may stay outside output scope. Every declared output target must appear in `output_scopes`, exactly once; read_only/pending can never be an output target. IR delivery requires every edit/format_only document, so its adapter selects all of them.

`provenance` identifies a supplied snapshot: source_id, relative path, content SHA. The adapter records the canonical source input hash under `origin` and uses it as the shared source ID. No external/public origin authentication is claimed. A source path/hash/access/authority change after pinning is rejected even when an attacker recomputes internal hashes. A new contract supplied with its own new pin is a new caller assertion, **not** evidence of a real grant: authenticating the initial user authorization remains the caller's responsibility. Do not obtain a trusted pin from a candidate or ask a model to reissue it.

| Boundary | G1 behavior |
|---|---|
| edit | Content/structure operations eligible only for declared output targets; explicit constraints and semantic quality need later independent review. |
| format_only | A format operation is eligible in principle. Exact no-op candidates clear the declared access check. **Every changed byte sequence remains REVIEW**, including whitespace and known word changes. No changed candidate gains formatting permission automatically; G3 must define/audit transforms or obtain explicit review. |
| read_only | Reference only; cannot be promoted by a candidate or changed as output. Evidence remains in the pinned input. |
| pending / incomplete / unknown document context | Validly represented but held; no execution authority. Excerpts retain their provided source_scope and hashes without claiming missing original text. |
| Global pending questions | Preserved as unresolved context, never answered or treated as approval. They do not automatically revoke independently explicit complete-document access grants; G2 must bind task-specific uncertain actions before execution. Per-document pending questions hold the document-set planning eligibility in this conservative G1 foundation. |
| External lookup / new documents / applying files | `not_granted`, schema-locked. Separate authorization and implementation are required; unsupported even if document edit eligibility exists. |

Every result keeps `semantic_judgment=unresolved`, `delivery_approved=false`, `stage_transition_allowed=false`, and `b2_reconstruction_success=false`. `permission_status=within_declared_access` means only the checked access category, full-set and snapshot bindings; it does not mean all natural-language constraints or meaning passed. No-op candidates are allowed.

## Example for G2 consumers

Run from `experiments/full_document_control` (or add it to the import path):

```python
import json
import document_set as core
from ir_document_set_adapter import from_ir_input

raw = json.loads(input_path.read_text())  # trusted, input-only IR file
contract = from_ir_input(raw)
pin = core.contract_digest(contract)    # retain separately before model execution
admission = core.validate_contract(contract, expected_sha256=pin)

# Example external/no-op candidate rows; this is not a generator invocation.
rows = [{"document_id": d["document_id"],
         "source_path": d["provenance"]["path"], "source_sha256": d["sha256"],
         "content": d["content"], "sha256": d["sha256"]}
        for d in contract["documents"] if d["output_target"]]
report = core.validate_candidates(contract, rows, trusted_contract_sha256=pin)
# report: gate_state=REVIEW, permission_status=within_declared_access,
# semantic_judgment=unresolved, execution_state=not_run, b2_reconstruction_success=false
unsupported = core.prepare_reconstruction(contract, trusted_contract_sha256=pin)
# status=unsupported; reason=DOCUMENT_SET_RECONSTRUCTION_NOT_IMPLEMENTED
```

Complete IR-001~003 contract JSON and actual admission/shadow reports are in [g0-g1-offline-20261117](../integrated_reconstruction_pilot_20261117/g0-g1-offline-20261117/). These are converted input examples and validator results, not reconstructed documents.

G2-C provides source-preserving KEEP, bounded PLACE and append MOVE with scoped HITL and a complete candidate trace. G3 must independently assess format changes, meaning and local reader requirements. G4 requires separate model-run authorization, budget/receipt controls and an independently reviewed complete pipeline. None is implemented by G1.
