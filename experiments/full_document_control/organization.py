"""Information Organization module for LogicWrite full-document control prototype.

Implements OrganizationPlan generation, in-document placement, redundancy consolidation,
cross-document MOVE candidate review, mandatory information preservation,
and independent deterministic organization validation.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

try:
    from . import pipeline
except (ImportError, ValueError):
    try:
        import pipeline
    except ImportError:
        try:
            import experiments.full_document_control.pipeline as pipeline
        except ImportError:
            _pipe_spec = importlib.util.spec_from_file_location('pipeline', _HERE / 'pipeline.py')
            pipeline = importlib.util.module_from_spec(_pipe_spec)
            _pipe_spec.loader.exec_module(pipeline)

ORGANIZATION_VERSION = 'information-organization-prototype-v1'
ORGANIZATION_PLAN_VERSION = 'org-plan-v1'
ORGANIZATION_REPORT_VERSION = 'org-validation-report-v1'

DISPOSITIONS = {'placed', 'omitted', 'blocked', 'flagged'}
ACTIONS = {'KEEP', 'MOVE', 'REMOVE', 'FLAG', 'CONSOLIDATE'}
DESTINATION_STATUSES = {'verified_context', 'unverified_role', 'unauthorized', 'nonexistent'}
COMPATIBILITY_STATUSES = {
    'compatible',
    'conflicting_conditions',
    'conflicting_quantities',
    'conflicting_versions',
    'conflicting_platforms',
    'incompatible_scopes',
}

ORGANIZATION_GATE_CHECKS = (
    ('ORGANIZATION_INPUT_INTEGRITY', '1', 'deterministic'),
    ('ALL_UNITS_TRACKED', '1', 'deterministic'),
    ('MANDATORY_INFORMATION_PRESERVED', '1', 'deterministic'),
    ('ALLOWED_OUTPUT_SCOPES', '1', 'deterministic'),
    ('DESTINATION_REVIEW_INTEGRITY', '1', 'deterministic'),
    ('CONSOLIDATION_FIDELITY', '1', 'deterministic'),
    ('ANTI_FORGERY_AND_APPROVAL_BOUNDS', '1', 'deterministic'),
)


# ============================================================================
# Digest and Validation Utilities
# ============================================================================

def canonical_json_bytes(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode('ascii')


def canonical_json_digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def digest_text(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def verify_self_digest(artifact, digest_field):
    if not isinstance(artifact, dict):
        return False, None
    claimed = artifact.get(digest_field)
    if not isinstance(claimed, str) or not claimed.strip():
        return False, None
    body = {k: v for k, v in artifact.items() if k != digest_field}
    actual = canonical_json_digest(body)
    return claimed == actual, actual


# ============================================================================
# Scope and Finding Helpers
# ============================================================================

def parse_output_scope_entry(scope_entry):
    """Normalize output scope entry into a standard descriptor."""
    if not isinstance(scope_entry, dict):
        return None
    scope_id = scope_entry.get('scope_id')
    if not scope_id or not isinstance(scope_id, str):
        return None

    kind = scope_entry.get('kind', 'document')
    target = scope_entry.get('target')

    doc_id = None
    dest_role = None

    if isinstance(target, dict):
        doc_id = target.get('document_id')
        dest_role = target.get('destination_role')
    else:
        doc_id = scope_entry.get('document_id')
        dest_role = scope_entry.get('destination_role')

    return {
        'scope_id': scope_id,
        'kind': kind,
        'document_id': doc_id,
        'destination_role': dest_role,
        'audience': scope_entry.get('audience'),
        'purpose': scope_entry.get('purpose'),
        'raw_entry': dict(scope_entry),
    }


def make_organization_finding(
    rule_id,
    severity,
    message,
    *,
    responsible_component='information_organization',
    origin_ref=None,
    unit_ids=None,
    scope_id=None,
    action='FLAG',
    requires_human_review=True,
    blocking=False,
    evidence=None,
):
    """Create a structured organization finding record."""
    return {
        'rule_id': rule_id,
        'severity': severity,
        'message': message,
        'responsible_component': responsible_component,
        'origin_ref': origin_ref,
        'unit_ids': list(unit_ids or []),
        'scope_id': scope_id,
        'action': action,
        'requires_human_review': requires_human_review,
        'blocking': blocking,
        'evidence': list(evidence or []),
    }


# ============================================================================
# Destination Scope Evaluation
# ============================================================================

def evaluate_destination_scope(scope_entry, input_bundle, *, destination_snapshots=None):
    """Evaluate destination scope for verified context vs unverified provisional role."""
    parsed = parse_output_scope_entry(scope_entry)
    if not parsed:
        return {
            'scope_id': 'invalid_scope',
            'kind': 'document',
            'document_id': None,
            'destination_role': None,
            'verification_status': 'unauthorized',
            'audience_alignment': 'misaligned',
            'purpose_alignment': 'misaligned',
            'allows_confirmed_move': False,
            'prerequisites': 'Valid scope declaration in WritingContract.output_scopes',
            'notes': 'Invalid or unparseable scope entry',
            'evidence': [],
        }

    scope_id = parsed['scope_id']
    doc_id = parsed['document_id']
    dest_role = parsed['destination_role']

    # Check against DocumentSnapshot in input_bundle
    snap = input_bundle.get('document_snapshot', {})
    is_current_source = bool(doc_id and snap.get('document_id') == doc_id)

    # Check if there is verified source material or destination snapshot for another concrete document
    dest_snaps = list(destination_snapshots or [])
    if isinstance(input_bundle.get('source_material'), list):
        dest_snaps.extend(input_bundle['source_material'])

    has_known_target_content = False
    for sm in dest_snaps:
        if isinstance(sm, dict) and sm.get('document_id') == doc_id and sm.get('content'):
            has_known_target_content = True
            break

    if is_current_source:
        verification_status = 'verified_context'
        allows_confirmed_move = True
        notes = 'Primary source document scope with verified snapshot context.'
    elif doc_id and has_known_target_content:
        verification_status = 'verified_context'
        allows_confirmed_move = True
        notes = f'Verified external document context for destination {doc_id}.'
    elif doc_id:
        verification_status = 'unverified_context'
        allows_confirmed_move = False
        notes = f'Concrete destination document {doc_id} declared, but target snapshot context is not loaded.'
    elif dest_role:
        verification_status = 'unverified_role'
        allows_confirmed_move = False
        notes = f'Provisional destination role "{dest_role}". Cannot confirm completed MOVE without concrete document snapshot.'
    else:
        verification_status = 'unauthorized'
        allows_confirmed_move = False
        notes = 'Output scope lacks both concrete document_id and destination_role.'

    return {
        'scope_id': scope_id,
        'kind': parsed['kind'],
        'document_id': doc_id,
        'destination_role': dest_role,
        'verification_status': verification_status,
        'audience_alignment': 'aligned' if is_current_source else 'unverified',
        'purpose_alignment': 'aligned' if is_current_source else 'unverified',
        'allows_confirmed_move': allows_confirmed_move,
        'prerequisites': 'Requires verified concrete document context before publishing moves' if not allows_confirmed_move else 'None',
        'notes': notes,
        'evidence': [{'scope_id': scope_id, 'document_id': doc_id, 'destination_role': dest_role}],
    }


# ============================================================================
# Semantic Consolidation Compatibility Check
# ============================================================================

def _extract_element_signatures(unit):
    """Extract quantities, versions, conditions, and platform identifiers from unit elements."""
    quantities = {}
    versions = set()
    platforms = set()
    conditions = []

    for el in unit.get('elements', []):
        kind = el.get('kind')
        val = str(el.get('value', '')).strip()
        if kind == 'quantity':
            quantities[val] = el
        elif kind == 'identifier':
            if re.search(r'v\d+\.\d+(?:\.\d+)?', val):
                versions.add(val)
            if any(p in val.lower() for p in ('linux', 'ubuntu', 'macos', 'darwin', 'windows')):
                platforms.add(val.lower())
        elif kind == 'condition':
            conditions.append(val)
        elif kind == 'claim':
            if any(p in val.lower() for p in ('linux', 'ubuntu', 'macos', 'darwin', 'windows')):
                platforms.add(val.lower())

    return {
        'quantities': quantities,
        'versions': versions,
        'platforms': platforms,
        'conditions': conditions,
    }


def check_consolidation_compatibility(unit_a, unit_b):
    """Determine whether two InformationUnits can be consolidated without semantic/condition loss.

    Strictly forbids consolidation when members carry differing conditions, quantities,
    version identifiers, or platform scopes.
    """
    sig_a = _extract_element_signatures(unit_a)
    sig_b = _extract_element_signatures(unit_b)

    # 1. Version incompatibility
    if sig_a['versions'] and sig_b['versions'] and sig_a['versions'] != sig_b['versions']:
        return {
            'compatible': False,
            'status': 'conflicting_versions',
            'reason': f"Conflicting versions between units: {sig_a['versions']} vs {sig_b['versions']}",
            'conflicting_elements': list(sig_a['versions'] | sig_b['versions']),
        }

    # 2. Platform target divergence
    if sig_a['platforms'] and sig_b['platforms'] and sig_a['platforms'] != sig_b['platforms']:
        return {
            'compatible': False,
            'status': 'conflicting_platforms',
            'reason': f"Conflicting platform targets between units: {sig_a['platforms']} vs {sig_b['platforms']}",
            'conflicting_elements': list(sig_a['platforms'] | sig_b['platforms']),
        }

    # 3. Differing quantities
    if sig_a['quantities'] and sig_b['quantities']:
        vals_a = set(sig_a['quantities'].keys())
        vals_b = set(sig_b['quantities'].keys())
        if vals_a != vals_b:
            return {
                'compatible': False,
                'status': 'conflicting_quantities',
                'reason': f"Conflicting quantity specifications: {vals_a} vs {vals_b}",
                'conflicting_elements': list(vals_a | vals_b),
            }

    # 4. Differing conditions (one has conditions that the other lacks or contradicts)
    conds_a = set(sig_a['conditions'])
    conds_b = set(sig_b['conditions'])
    if conds_a != conds_b and (conds_a or conds_b):
        # If one unit has an explicit operational constraint/condition that the other does not express,
        # consolidating them poses a severe risk of dropping the qualifier.
        return {
            'compatible': False,
            'status': 'conflicting_conditions',
            'reason': f"Differing conditions between candidate units: {conds_a} vs {conds_b}",
            'conflicting_elements': list(conds_a ^ conds_b),
        }

    # Merge elements preserving distinct element identities
    merged_elements = list(unit_a.get('elements', []))
    existing_ids = {e.get('id') for e in merged_elements}
    existing_vals = {(e.get('kind'), str(e.get('value')).strip()) for e in merged_elements}

    for el in unit_b.get('elements', []):
        pair = (el.get('kind'), str(el.get('value')).strip())
        if el.get('id') not in existing_ids and pair not in existing_vals:
            merged_elements.append(dict(el))
            existing_ids.add(el.get('id'))
            existing_vals.add(pair)

    return {
        'compatible': True,
        'status': 'compatible',
        'reason': 'Units express equivalent information with compatible conditions, quantities, and versions.',
        'merged_elements': merged_elements,
    }


# ============================================================================
# Section Placement & Topic Ordering
# ============================================================================

def _determine_section_and_order(unit, units_by_id):
    """Determine document section path and relative ordering respecting condition adjacency."""
    origin_blocks = unit.get('origin_block_ids', [])
    statement = unit.get('statement', '')

    # Analyze relations to preserve condition adjacency
    qualifying_targets = []
    for rel in unit.get('relations', []):
        if rel.get('kind') in {'qualifies', 'depends_on'}:
            tgt_id = rel.get('target_unit_id')
            if tgt_id in units_by_id:
                qualifying_targets.append(tgt_id)

    # Heading-based or keyword-based topic classification
    first_block = origin_blocks[0] if origin_blocks else ''
    if first_block in {'B001'}:
        section_path = ['Title and Overview']
        base_order = 10
    elif first_block in {'B003'}:
        section_path = ['Title and Overview', 'Runtime Summary']
        base_order = 20
    elif first_block in {'B005', 'B007', 'B009'}:
        section_path = ['Installation and Environments']
        base_order = 50
    elif first_block in {'B013', 'B015'}:
        section_path = ['Operational Constraints and Cautions']
        base_order = 80
    else:
        # Fallback by content
        if any(w in statement for w in ('설치', '패키지', 'tar', 'install')):
            section_path = ['Installation and Environments']
            base_order = 50
        elif any(w in statement for w in ('제약', '오프라인', '캐시', '주의', '업데이트')):
            section_path = ['Operational Constraints and Cautions']
            base_order = 80
        else:
            section_path = ['General Content']
            base_order = 60

    anchor_uid = qualifying_targets[0] if qualifying_targets else None
    anchor_rel = 'before' if anchor_uid else 'within'

    return section_path, base_order, anchor_uid, anchor_rel


# ============================================================================
# OrganizationPlan Generator
# ============================================================================

def generate_organization_plan(
    input_bundle,
    analysis_result,
    *,
    candidate_actions=None,
    consolidation_candidates=None,
    destination_snapshots=None,
    execution_mode='preview',
    run_id='org-run-preview',
    validation_report=None,
):
    """Generate a structured OrganizationPlan from an AnalysisResult.

    Tracks all units, protects mandatory information, evaluates consolidation candidates,
    inspects destination scopes, and ensures preview/authorized boundary integrity.
    """
    if not isinstance(input_bundle, dict):
        raise pipeline.InvalidArtifactError('input_bundle must be an object', code='INVALID_INPUT_BUNDLE')
    if not isinstance(analysis_result, dict):
        raise pipeline.InvalidArtifactError('analysis_result must be an object', code='INVALID_ANALYSIS_RESULT')

    contract = input_bundle.get('writing_contract', {})
    snapshot = input_bundle.get('document_snapshot', {})
    case_id = input_bundle.get('case_id', 'UNKNOWN_CASE')

    # Digest verification of analysis binding
    expected_snap_sha = snapshot.get('sha256')
    expected_contract_sha = pipeline.canonical_json_digest(contract)
    ok_analysis_self, actual_analysis_sha = verify_self_digest(analysis_result, 'analysis_sha256')

    if not ok_analysis_self or analysis_result.get('analysis_sha256') != actual_analysis_sha:
        raise pipeline.InvalidArtifactError(
            f'AnalysisResult digest mismatch: claimed {analysis_result.get("analysis_sha256")} != actual {actual_analysis_sha}',
            code='CORRUPTED_ANALYSIS_DIGEST',
        )

    if analysis_result.get('snapshot_sha256') != expected_snap_sha:
        raise pipeline.InvalidArtifactError(
            'AnalysisResult snapshot_sha256 does not match input_bundle DocumentSnapshot',
            code='STALE_SNAPSHOT_BINDING',
        )

    if analysis_result.get('contract_sha256') != expected_contract_sha:
        raise pipeline.InvalidArtifactError(
            'AnalysisResult contract_sha256 does not match input_bundle WritingContract',
            code='STALE_CONTRACT_BINDING',
        )

    # Parse declared output scopes
    declared_scopes = contract.get('output_scopes', [])
    if not isinstance(declared_scopes, list) or not declared_scopes:
        raise pipeline.InvalidArtifactError('WritingContract output_scopes must be a nonempty list', code='EMPTY_OUTPUT_SCOPES')

    declared_scopes_by_id = {}
    destination_reviews = []
    for sc in declared_scopes:
        rev = evaluate_destination_scope(sc, input_bundle, destination_snapshots=destination_snapshots)
        declared_scopes_by_id[rev['scope_id']] = rev
        destination_reviews.append(rev)

    # Determine primary source scope ID
    primary_source_scope = None
    for rev in destination_reviews:
        if rev.get('document_id') == snapshot.get('document_id'):
            primary_source_scope = rev['scope_id']
            break
    if not primary_source_scope and destination_reviews:
        primary_source_scope = destination_reviews[0]['scope_id']

    # Map requirement bindings and protected information
    req_bindings = analysis_result.get('requirement_bindings', [])
    protected_unit_ids = set()
    bound_requirements_by_unit = {}
    verified_condition_units = set()

    for binding in req_bindings:
        if isinstance(binding, dict) and binding.get('satisfied'):
            req_id = binding.get('requirement_id')
            uids = binding.get('unit_ids', [])
            for uid in uids:
                protected_unit_ids.add(uid)
                bound_requirements_by_unit.setdefault(uid, []).append(req_id)
            for link in binding.get('verified_condition_links', []):
                cond_uid = link.get('condition_unit_id')
                if cond_uid:
                    protected_unit_ids.add(cond_uid)
                    verified_condition_units.add(cond_uid)
                    bound_requirements_by_unit.setdefault(cond_uid, []).append(f'{req_id}:condition_link')

    units = analysis_result.get('units', [])
    units_by_id = {u['id']: u for u in units}
    candidate_actions = candidate_actions or {}
    consolidation_candidates = consolidation_candidates or []

    findings = []
    placements = []
    consolidation_groups = []
    affected_document_map = {
        primary_source_scope: {
            'scope_id': primary_source_scope,
            'document_id': snapshot.get('document_id'),
            'role': 'source',
            'status': 'source_retained',
            'snapshot_sha256': snapshot.get('sha256'),
            'unit_count': 0,
        }
    }

    # Process consolidation candidates first
    consolidated_secondary_units = {}
    for idx, cand in enumerate(consolidation_candidates):
        cand_uids = cand.get('member_unit_ids', [])
        if len(cand_uids) < 2:
            continue
        missing_m = [uid for uid in cand_uids if uid not in units_by_id]
        if missing_m:
            findings.append(make_organization_finding(
                'UNKNOWN_CONSOLIDATION_MEMBER',
                'ERROR',
                f'Consolidation candidate references unknown unit IDs: {missing_m}',
                unit_ids=missing_m,
                action='BLOCK',
                blocking=True,
            ))
            continue

        member_units = [units_by_id[uid] for uid in cand_uids]
        compat_result = {'compatible': True, 'merged_elements': []}
        for i in range(len(member_units)):
            for j in range(i + 1, len(member_units)):
                pair_res = check_consolidation_compatibility(member_units[i], member_units[j])
                if not pair_res['compatible']:
                    compat_result = pair_res
                    break
            if not compat_result['compatible']:
                break

        primary_uid = cand_uids[0]
        group_id = cand.get('id') or f'cg-{idx + 1:03d}'
        if not compat_result['compatible']:
            # Blocked consolidation: preserve as blocked candidate, do NOT merge
            cg_entry = {
                'id': group_id,
                'member_unit_ids': cand_uids,
                'equivalence_basis': cand.get('equivalence_basis', 'Proposed duplicate consolidation'),
                'compatibility_status': compat_result['status'],
                'retained_elements': [e['id'] for e in member_units[0].get('elements', [])],
                'member_contributions': [
                    {'unit_id': u['id'], 'contributed_element_ids': [e['id'] for e in u.get('elements', [])]}
                    for u in member_units
                ],
                'target': {'scope_id': primary_source_scope, 'primary_unit_id': primary_uid},
                'rationale': {
                    'reason': compat_result['reason'],
                    'evidence_ids': [],
                },
                'blocked': True,
                'block_reason': compat_result['reason'],
            }
            consolidation_groups.append(cg_entry)
            findings.append(make_organization_finding(
                'INCOMPATIBLE_CONSOLIDATION_CANDIDATE',
                'WARNING',
                f'Consolidation blocked between {cand_uids}: {compat_result["reason"]}',
                unit_ids=cand_uids,
                action='BLOCK',
                blocking=False,
            ))
        else:
            # Compatible consolidation
            all_retained_elements = compat_result.get('merged_elements', member_units[0].get('elements', []))
            cg_entry = {
                'id': group_id,
                'member_unit_ids': cand_uids,
                'equivalence_basis': cand.get('equivalence_basis', 'Verified semantic redundancy with compatible elements'),
                'compatibility_status': 'compatible',
                'retained_elements': [e['id'] for e in all_retained_elements],
                'member_contributions': [
                    {'unit_id': u['id'], 'contributed_element_ids': [e['id'] for e in u.get('elements', [])]}
                    for u in member_units
                ],
                'target': {'scope_id': primary_source_scope, 'primary_unit_id': primary_uid},
                'rationale': {
                    'reason': 'Consolidated semantically redundant units while preserving all constituent elements and conditions.',
                    'evidence_ids': [],
                },
                'blocked': False,
                'block_reason': None,
            }
            consolidation_groups.append(cg_entry)
            for sec_uid in cand_uids[1:]:
                consolidated_secondary_units[sec_uid] = {
                    'primary_unit_id': primary_uid,
                    'group_id': group_id,
                }

    # Generate placements for all units
    for unit in units:
        uid = unit['id']
        assessment = unit.get('assessment', {})
        preservation = assessment.get('preservation', 'retain_current')
        is_protected = uid in protected_unit_ids
        bound_reqs = bound_requirements_by_unit.get(uid, [])

        custom_action = candidate_actions.get(uid, {})
        action_desire = custom_action.get('action')
        target_scope_desire = custom_action.get('target_scope_id')

        # Determine target section and ordering
        sec_path, base_order, anchor_uid, anchor_rel = _determine_section_and_order(unit, units_by_id)

        # Handling Consolidated Secondary Units
        if uid in consolidated_secondary_units:
            cons_info = consolidated_secondary_units[uid]
            placements.append({
                'id': f'plc-{uid}',
                'unit_id': uid,
                'scope_id': primary_source_scope,
                'disposition': 'placed',
                'action': 'CONSOLIDATE',
                'consolidated_into': cons_info['primary_unit_id'],
                'consolidation_group_id': cons_info['group_id'],
                'targets': [
                    {
                        'scope_id': primary_source_scope,
                        'document_id': snapshot.get('document_id'),
                        'destination_role': None,
                        'section_path': sec_path,
                        'relative_order': base_order,
                        'anchor_relative_position': 'within',
                        'anchor_unit_id': cons_info['primary_unit_id'],
                        'exposure': 'consolidated_in_primary',
                        'retained_elements': [e['id'] for e in unit.get('elements', [])],
                    }
                ],
                'transfer_peer_ids': [],
                'source_origin_blocks': unit.get('origin_block_ids', []),
                'contract_protection': {
                    'is_protected': is_protected,
                    'bound_requirement_ids': bound_reqs,
                    'protected_elements': [e['id'] for e in unit.get('elements', [])] if is_protected else [],
                },
                'rationale': {
                    'reason': f"Consolidated into primary unit {cons_info['primary_unit_id']} under group {cons_info['group_id']}",
                    'evidence_ids': [],
                    'uncertainty': assessment.get('uncertainty', 'Verified deterministic consolidation'),
                    'assumptions': [],
                },
                'review_required': False,
            })
            affected_document_map[primary_source_scope]['unit_count'] += 1
            continue

        # Handling Omission / Removal Request
        if action_desire == 'REMOVE' or preservation == 'omit_candidate':
            if is_protected:
                # OMISSION BLOCKED!
                findings.append(make_organization_finding(
                    'MANDATORY_INFORMATION_PRESERVATION_VIOLATION',
                    'ERROR',
                    f"Unit {uid} is bound to contract-required information ({', '.join(bound_reqs)}) and cannot be omitted",
                    unit_ids=[uid],
                    scope_id=primary_source_scope,
                    action='BLOCK',
                    blocking=True,
                ))
                placements.append({
                    'id': f'plc-{uid}',
                    'unit_id': uid,
                    'scope_id': primary_source_scope,
                    'disposition': 'blocked',
                    'action': 'FLAG',
                    'targets': [
                        {
                            'scope_id': primary_source_scope,
                            'document_id': snapshot.get('document_id'),
                            'destination_role': None,
                            'section_path': sec_path,
                            'relative_order': base_order,
                            'anchor_relative_position': anchor_rel,
                            'anchor_unit_id': anchor_uid,
                            'exposure': assessment.get('exposure', 'direct'),
                            'retained_elements': [e['id'] for e in unit.get('elements', [])],
                        }
                    ],
                    'transfer_peer_ids': [],
                    'source_origin_blocks': unit.get('origin_block_ids', []),
                    'contract_protection': {
                        'is_protected': True,
                        'bound_requirement_ids': bound_reqs,
                        'protected_elements': [e['id'] for e in unit.get('elements', [])],
                    },
                    'rationale': {
                        'reason': 'Omission attempt blocked because unit carries contract-required information.',
                        'evidence_ids': [],
                        'uncertainty': 'Omission blocked by contract policy',
                        'assumptions': [],
                    },
                    'review_required': True,
                })
            else:
                placements.append({
                    'id': f'plc-{uid}',
                    'unit_id': uid,
                    'scope_id': primary_source_scope,
                    'disposition': 'omitted',
                    'action': 'REMOVE',
                    'targets': [],
                    'transfer_peer_ids': [],
                    'source_origin_blocks': unit.get('origin_block_ids', []),
                    'contract_protection': {
                        'is_protected': False,
                        'bound_requirement_ids': [],
                        'protected_elements': [],
                    },
                    'rationale': {
                        'reason': assessment.get('reason', 'Omitted as candidate non-essential detail with no protection obligation.'),
                        'evidence_ids': [],
                        'uncertainty': assessment.get('uncertainty', 'Standard candidate omission'),
                        'assumptions': [],
                    },
                    'review_required': False,
                })
            continue

        # Handling Cross-Document MOVE
        if action_desire == 'MOVE' or preservation == 'preserve_elsewhere_candidate':
            target_scope_id = target_scope_desire or custom_action.get('scope_id') or 'packaging_record'
            dest_review = declared_scopes_by_id.get(target_scope_id)

            if not dest_review:
                # Target scope is NOT declared in WritingContract.output_scopes!
                findings.append(make_organization_finding(
                    'UNAUTHORIZED_DESTINATION_SCOPE',
                    'ERROR',
                    f'Unit {uid} targeted for MOVE to undeclared scope "{target_scope_id}"',
                    unit_ids=[uid],
                    scope_id=target_scope_id,
                    action='BLOCK',
                    blocking=True,
                ))
                placements.append({
                    'id': f'plc-{uid}',
                    'unit_id': uid,
                    'scope_id': primary_source_scope,
                    'disposition': 'blocked',
                    'action': 'FLAG',
                    'targets': [],
                    'transfer_peer_ids': [],
                    'source_origin_blocks': unit.get('origin_block_ids', []),
                    'contract_protection': {
                        'is_protected': is_protected,
                        'bound_requirement_ids': bound_reqs,
                        'protected_elements': [e['id'] for e in unit.get('elements', [])] if is_protected else [],
                    },
                    'rationale': {
                        'reason': f'MOVE blocked because destination scope "{target_scope_id}" is not declared in WritingContract.',
                        'evidence_ids': [],
                        'uncertainty': 'Undeclared destination scope',
                        'assumptions': [],
                    },
                    'review_required': True,
                })
                continue

            # Target scope is declared, check if verified vs role-only
            if not dest_review['allows_confirmed_move']:
                # Unverified context or destination_role provisional target
                findings.append(make_organization_finding(
                    'UNVERIFIED_DESTINATION_CONTEXT',
                    'WARNING',
                    f'Unit {uid} proposed for MOVE to provisional or unverified role "{target_scope_id}" ({dest_review.get("destination_role")}). Held as proposal; confirmed transfer blocked.',
                    unit_ids=[uid],
                    scope_id=target_scope_id,
                    action='FLAG',
                    requires_human_review=True,
                    blocking=False,
                ))
                placements.append({
                    'id': f'plc-{uid}',
                    'unit_id': uid,
                    'scope_id': primary_source_scope,
                    'disposition': 'blocked',
                    'action': 'FLAG',
                    'targets': [
                        {
                            'scope_id': target_scope_id,
                            'document_id': dest_review.get('document_id'),
                            'destination_role': dest_review.get('destination_role'),
                            'section_path': ['Provisional Move Target'],
                            'relative_order': 10,
                            'anchor_relative_position': 'within',
                            'anchor_unit_id': None,
                            'exposure': 'proposal_only',
                            'retained_elements': [e['id'] for e in unit.get('elements', [])],
                        }
                    ],
                    'transfer_peer_ids': [],
                    'source_origin_blocks': unit.get('origin_block_ids', []),
                    'contract_protection': {
                        'is_protected': is_protected,
                        'bound_requirement_ids': bound_reqs,
                        'protected_elements': [e['id'] for e in unit.get('elements', [])] if is_protected else [],
                    },
                    'rationale': {
                        'reason': f'MOVE held as provisional proposal because destination scope "{target_scope_id}" lacks verified concrete snapshot context.',
                        'evidence_ids': [],
                        'uncertainty': 'Destination role lacks verified snapshot context',
                        'assumptions': [],
                    },
                    'review_required': True,
                })
                affected_document_map.setdefault(target_scope_id, {
                    'scope_id': target_scope_id,
                    'document_id': dest_review.get('document_id') or f'role:{dest_review.get("destination_role")}',
                    'role': 'destination',
                    'status': 'unverified_target',
                    'snapshot_sha256': None,
                    'unit_count': 0,
                })['unit_count'] += 1
                continue

            # Verified concrete destination scope
            placements.append({
                'id': f'plc-{uid}',
                'unit_id': uid,
                'scope_id': primary_source_scope,
                'disposition': 'placed',
                'action': 'MOVE',
                'targets': [
                    {
                        'scope_id': target_scope_id,
                        'document_id': dest_review.get('document_id'),
                        'destination_role': None,
                        'section_path': ['Transferred Information'],
                        'relative_order': 10,
                        'anchor_relative_position': 'within',
                        'anchor_unit_id': None,
                        'exposure': assessment.get('exposure', 'direct'),
                        'retained_elements': [e['id'] for e in unit.get('elements', [])],
                    }
                ],
                'transfer_peer_ids': [f'peer-plc-{uid}'],
                'source_origin_blocks': unit.get('origin_block_ids', []),
                'contract_protection': {
                    'is_protected': is_protected,
                    'bound_requirement_ids': bound_reqs,
                    'protected_elements': [e['id'] for e in unit.get('elements', [])] if is_protected else [],
                },
                'rationale': {
                    'reason': f'Candidate information verified for transfer to concrete destination {target_scope_id}.',
                    'evidence_ids': [],
                    'uncertainty': assessment.get('uncertainty', 'Verified concrete destination'),
                    'assumptions': [],
                },
                'review_required': False,
            })
            affected_document_map.setdefault(target_scope_id, {
                'scope_id': target_scope_id,
                'document_id': dest_review.get('document_id'),
                'role': 'destination',
                'status': 'candidate_destination',
                'snapshot_sha256': None,
                'unit_count': 0,
            })['unit_count'] += 1
            continue

        # Standard in-document KEEP placement
        placements.append({
            'id': f'plc-{uid}',
            'unit_id': uid,
            'scope_id': primary_source_scope,
            'disposition': 'placed',
            'action': 'KEEP',
            'targets': [
                {
                    'scope_id': primary_source_scope,
                    'document_id': snapshot.get('document_id'),
                    'destination_role': None,
                    'section_path': sec_path,
                    'relative_order': base_order,
                    'anchor_relative_position': anchor_rel,
                    'anchor_unit_id': anchor_uid,
                    'exposure': assessment.get('exposure', 'direct'),
                    'retained_elements': [e['id'] for e in unit.get('elements', [])],
                }
            ],
            'transfer_peer_ids': [],
            'source_origin_blocks': unit.get('origin_block_ids', []),
            'contract_protection': {
                'is_protected': is_protected,
                'bound_requirement_ids': bound_reqs,
                'protected_elements': [e['id'] for e in unit.get('elements', [])] if is_protected else [],
            },
            'rationale': {
                'reason': assessment.get('reason', 'Retained in source document with structured topic placement.'),
                'evidence_ids': [],
                'uncertainty': assessment.get('uncertainty', 'Normal placement'),
                'assumptions': [],
            },
            'review_required': False,
        })
        affected_document_map[primary_source_scope]['unit_count'] += 1

    # Sort placements by relative order
    placements.sort(key=lambda p: (
        p['targets'][0]['relative_order'] if p.get('targets') and p['targets'] else 999,
        p['id'],
    ))

    # Add execution mode tracking finding
    is_preview = (execution_mode == 'preview')
    gate_state = validation_report.get('gate_state') if isinstance(validation_report, dict) else 'UNVALIDATED'

    if is_preview:
        findings.append(make_organization_finding(
            'PLAN_PREVIEW_ONLY',
            'INFO',
            f'OrganizationPlan generated in isolated preview mode (upstream gate_state: {gate_state}). Pipeline stage progression is not authorized.',
            action='REVIEW',
            requires_human_review=True,
            blocking=False,
        ))

    affected_documents = sorted(affected_document_map.values(), key=lambda d: d['scope_id'])

    plan = {
        'version': ORGANIZATION_PLAN_VERSION,
        'producer': ORGANIZATION_VERSION,
        'meta': {
            'execution_mode': execution_mode,
            'preview_only': is_preview,
            'delivery_approved': False,
            'stage_transition_allowed': False,
            'run_id': run_id,
            'gate_state_at_generation': gate_state,
        },
        'analysis_ref': {
            'case_id': case_id,
            'analysis_sha256': analysis_result['analysis_sha256'],
            'snapshot_id': snapshot.get('snapshot_id'),
            'snapshot_sha256': snapshot.get('sha256'),
            'contract_id': contract.get('contract_id'),
            'contract_sha256': expected_contract_sha,
        },
        'placements': placements,
        'consolidation_groups': consolidation_groups,
        'destination_reviews': destination_reviews,
        'affected_documents': affected_documents,
        'findings': findings,
    }

    plan['plan_sha256'] = canonical_json_digest(plan)
    return plan


# ============================================================================
# Independent Deterministic Organization Plan Validator
# ============================================================================

def validate_organization_plan(
    input_bundle,
    analysis_result,
    plan,
    *,
    validation_report=None,
):
    """Independently validate an OrganizationPlan against deterministic invariants.

    Checks:
    1. Input and analysis artifact binding integrity
    2. Complete coverage and tracking of all InformationUnits
    3. Mandatory information and protected condition preservation
    4. Strict confinement to declared output scopes
    5. Destination review and MOVE proposal integrity
    6. Semantic consolidation fidelity without condition/quantity loss
    7. Anti-forgery defenses against unauthenticated self-approval claims
    """
    diagnostics = []
    check_results = []
    blocking_violations = []

    # 1. ORGANIZATION_INPUT_INTEGRITY
    input_ok = True
    input_reasons = []

    if not isinstance(input_bundle, dict) or not isinstance(analysis_result, dict) or not isinstance(plan, dict):
        input_ok = False
        input_reasons.append('INVALID_ARGUMENT_TYPES: input_bundle, analysis_result, and plan must be dictionaries')
    else:
        # Check plan self-digest
        plan_self_ok, actual_plan_sha = verify_self_digest(plan, 'plan_sha256')
        if not plan_self_ok or plan.get('plan_sha256') != actual_plan_sha:
            input_ok = False
            input_reasons.append(f'PLAN_DIGEST_CORRUPTED: claimed {plan.get("plan_sha256")} != actual {actual_plan_sha}')

        # Check analysis_ref binding
        analysis_ref = plan.get('analysis_ref', {})
        if analysis_ref.get('analysis_sha256') != analysis_result.get('analysis_sha256'):
            input_ok = False
            input_reasons.append('STALE_ANALYSIS_PLAN_INVALIDATED: plan.analysis_ref does not match current analysis_sha256')

        snap = input_bundle.get('document_snapshot', {})
        if analysis_ref.get('snapshot_sha256') != snap.get('sha256'):
            input_ok = False
            input_reasons.append('STALE_SNAPSHOT_BINDING: plan.analysis_ref snapshot_sha256 does not match input_bundle')

        contract = input_bundle.get('writing_contract', {})
        if analysis_ref.get('contract_sha256') != canonical_json_digest(contract):
            input_ok = False
            input_reasons.append('STALE_CONTRACT_BINDING: plan.analysis_ref contract_sha256 does not match writing_contract')

    check_results.append({
        'check_id': 'ORGANIZATION_INPUT_INTEGRITY',
        'status': 'passed' if input_ok else 'violated',
        'reason': '; '.join(input_reasons) if not input_ok else 'Input artifacts and plan digest independently verified',
    })
    if not input_ok:
        blocking_violations.extend(input_reasons)

    # 2. ALL_UNITS_TRACKED
    units_ok = True
    units_reasons = []
    raw_units = analysis_result.get('units', []) if isinstance(analysis_result, dict) else []
    expected_unit_ids = [u.get('id') for u in raw_units if isinstance(u, dict) and u.get('id')]
    placements = plan.get('placements', []) if isinstance(plan, dict) else []

    placement_unit_ids = []
    for plc in placements:
        if isinstance(plc, dict):
            uid = plc.get('unit_id')
            if uid:
                placement_unit_ids.append(uid)

    missing_from_plan = set(expected_unit_ids) - set(placement_unit_ids)
    if missing_from_plan:
        units_ok = False
        units_reasons.append(f'UNIT_OMITTED_FROM_ORGANIZATION_PLAN: units {sorted(missing_from_plan)} are not tracked in placements')

    # Duplicate placements of the same unit
    seen_uids = set()
    dup_uids = set()
    for uid in placement_unit_ids:
        if uid in seen_uids:
            dup_uids.add(uid)
        seen_uids.add(uid)
    if dup_uids:
        units_ok = False
        units_reasons.append(f'DUPLICATE_UNIT_PLACEMENT: units {sorted(dup_uids)} placed multiple times')

    check_results.append({
        'check_id': 'ALL_UNITS_TRACKED',
        'status': 'passed' if units_ok else 'violated',
        'reason': '; '.join(units_reasons) if not units_ok else f'All {len(expected_unit_ids)} InformationUnits tracked without duplicates',
    })
    if not units_ok:
        blocking_violations.extend(units_reasons)

    # 3. MANDATORY_INFORMATION_PRESERVED
    mandatory_ok = True
    mandatory_reasons = []
    placements_by_uid = {plc.get('unit_id'): plc for plc in placements if isinstance(plc, dict)}

    req_bindings = analysis_result.get('requirement_bindings', []) if isinstance(analysis_result, dict) else []
    for binding in req_bindings:
        if isinstance(binding, dict) and binding.get('satisfied'):
            req_id = binding.get('requirement_id')
            for uid in binding.get('unit_ids', []):
                plc = placements_by_uid.get(uid)
                if not plc:
                    continue
                if plc.get('disposition') == 'omitted' or plc.get('action') == 'REMOVE':
                    mandatory_ok = False
                    mandatory_reasons.append(f'REQUIRED_INFORMATION_DROPPED: Unit {uid} bound to {req_id} marked as omitted/removed')

            # Linked conditions preservation
            for link in binding.get('verified_condition_links', []):
                cond_uid = link.get('condition_unit_id')
                cond_plc = placements_by_uid.get(cond_uid)
                if cond_plc and (cond_plc.get('disposition') == 'omitted' or cond_plc.get('action') == 'REMOVE'):
                    mandatory_ok = False
                    mandatory_reasons.append(f'REQUIRED_CONDITION_DROPPED: Condition unit {cond_uid} qualifying {req_id} marked as omitted/removed')

    check_results.append({
        'check_id': 'MANDATORY_INFORMATION_PRESERVED',
        'status': 'passed' if mandatory_ok else 'violated',
        'reason': '; '.join(mandatory_reasons) if not mandatory_ok else 'All contract-required information and linked conditions preserved',
    })
    if not mandatory_ok:
        blocking_violations.extend(mandatory_reasons)

    # 4. ALLOWED_OUTPUT_SCOPES
    scopes_ok = True
    scopes_reasons = []
    contract = input_bundle.get('writing_contract', {}) if isinstance(input_bundle, dict) else {}
    declared_scopes = contract.get('output_scopes', []) if isinstance(contract, dict) else []
    declared_scope_ids = set()
    for sc in declared_scopes:
        parsed = parse_output_scope_entry(sc)
        if parsed:
            declared_scope_ids.add(parsed['scope_id'])

    for plc in placements:
        if not isinstance(plc, dict):
            continue
        scope_id = plc.get('scope_id')
        if scope_id and scope_id not in declared_scope_ids:
            scopes_ok = False
            scopes_reasons.append(f'UNAUTHORIZED_OUTPUT_SCOPE: Placement {plc.get("id")} references undeclared scope "{scope_id}"')
        for tgt in plc.get('targets', []):
            tgt_scope = tgt.get('scope_id')
            if tgt_scope and tgt_scope not in declared_scope_ids:
                scopes_ok = False
                scopes_reasons.append(f'UNAUTHORIZED_DESTINATION_SCOPE: Target in placement {plc.get("id")} references undeclared scope "{tgt_scope}"')

    check_results.append({
        'check_id': 'ALLOWED_OUTPUT_SCOPES',
        'status': 'passed' if scopes_ok else 'violated',
        'reason': '; '.join(scopes_reasons) if not scopes_ok else f'All placements strictly confined to {len(declared_scope_ids)} declared scopes',
    })
    if not scopes_ok:
        blocking_violations.extend(scopes_reasons)

    # 5. DESTINATION_REVIEW_INTEGRITY
    dest_ok = True
    dest_reasons = []
    dest_reviews = plan.get('destination_reviews', []) if isinstance(plan, dict) else []
    dest_reviews_by_scope = {r.get('scope_id'): r for r in dest_reviews if isinstance(r, dict)}

    for plc in placements:
        if not isinstance(plc, dict):
            continue
        if plc.get('action') == 'MOVE' and plc.get('disposition') == 'placed':
            for tgt in plc.get('targets', []):
                t_scope = tgt.get('scope_id')
                rev = dest_reviews_by_scope.get(t_scope)
                if not rev or not rev.get('allows_confirmed_move'):
                    dest_ok = False
                    dest_reasons.append(
                        f'UNVERIFIED_DESTINATION_CONFIRMED_MOVE: Unit {plc.get("unit_id")} confirmed placed into unverified or role-only destination "{t_scope}"'
                    )

    check_results.append({
        'check_id': 'DESTINATION_REVIEW_INTEGRITY',
        'status': 'passed' if dest_ok else 'violated',
        'reason': '; '.join(dest_reasons) if not dest_ok else 'All MOVE candidates adhere to destination verification bounds',
    })
    if not dest_ok:
        blocking_violations.extend(dest_reasons)

    # 6. CONSOLIDATION_FIDELITY
    cons_ok = True
    cons_reasons = []
    units_by_id = {u['id']: u for u in raw_units if isinstance(u, dict) and u.get('id')}
    groups = plan.get('consolidation_groups', []) if isinstance(plan, dict) else []

    for grp in groups:
        if not isinstance(grp, dict):
            continue
        m_uids = grp.get('member_unit_ids', [])
        is_blocked = grp.get('blocked', False)
        status = grp.get('compatibility_status')

        # Check member units exist
        m_units = [units_by_id[uid] for uid in m_uids if uid in units_by_id]
        if len(m_units) != len(m_uids):
            cons_ok = False
            cons_reasons.append(f'CONSOLIDATION_UNKNOWN_MEMBER: Group {grp.get("id")} contains nonexistent units')
            continue

        # Re-check compatibility independently
        for i in range(len(m_units)):
            for j in range(i + 1, len(m_units)):
                compat = check_consolidation_compatibility(m_units[i], m_units[j])
                if not compat['compatible']:
                    if not is_blocked or status == 'compatible':
                        cons_ok = False
                        cons_reasons.append(
                            f'INCOMPATIBLE_CONSOLIDATION_CANDIDATE: Group {grp.get("id")} merged incompatible units ({compat["reason"]})'
                        )
                        break
            if not cons_ok:
                break

    check_results.append({
        'check_id': 'CONSOLIDATION_FIDELITY',
        'status': 'passed' if cons_ok else 'violated',
        'reason': '; '.join(cons_reasons) if not cons_ok else 'Consolidation candidates preserve all conditions, quantities, and versions',
    })
    if not cons_ok:
        blocking_violations.extend(cons_reasons)

    # 7. ANTI_FORGERY_AND_APPROVAL_BOUNDS
    sec_ok = True
    sec_reasons = []
    meta = plan.get('meta', {}) if isinstance(plan, dict) else {}

    # Reject model or plan claiming execution authorization on its own
    if meta.get('delivery_approved') is True or meta.get('stage_transition_allowed') is True:
        # Only allowed if validation_report is supplied and independently PASS
        if not validation_report or validation_report.get('gate_state') != 'PASS' or not validation_report.get('delivery_approved'):
            sec_ok = False
            sec_reasons.append('UNAUTHORIZED_ORGANIZATION_APPROVAL_CLAIM: Plan claims delivery_approved or stage_transition_allowed without valid Validation Gate approval')

    # If Validation Gate is REVIEW, plan MUST be preview_only
    if validation_report and validation_report.get('gate_state') == 'REVIEW':
        if not meta.get('preview_only'):
            sec_ok = False
            sec_reasons.append('UNAUTHORIZED_STAGE_EXECUTION: Validation Gate is REVIEW; OrganizationPlan must be marked preview_only=True')

    check_results.append({
        'check_id': 'ANTI_FORGERY_AND_APPROVAL_BOUNDS',
        'status': 'passed' if sec_ok else 'violated',
        'reason': '; '.join(sec_reasons) if not sec_ok else 'Plan respects trust boundary and does not forge approval claims',
    })
    if not sec_ok:
        blocking_violations.extend(sec_reasons)

    # Determine overall organization gate state
    all_passed = all(r['status'] == 'passed' for r in check_results)
    any_violated = any(r['status'] == 'violated' for r in check_results)

    if any_violated:
        org_gate_state = 'FAIL'
    elif validation_report and validation_report.get('gate_state') == 'REVIEW':
        # Upstream gate is in REVIEW, organization outcome remains in REVIEW
        org_gate_state = 'REVIEW'
    elif not all_passed:
        org_gate_state = 'REVIEW'
    else:
        org_gate_state = 'PASS'

    diagnostics.extend(blocking_violations)

    report = {
        'version': ORGANIZATION_REPORT_VERSION,
        'producer': ORGANIZATION_VERSION,
        'gate_state': org_gate_state,
        'is_valid': (org_gate_state != 'FAIL'),
        'delivery_approved': (org_gate_state == 'PASS' and not meta.get('preview_only')),
        'next_stage_allowed': (org_gate_state == 'PASS' and not meta.get('preview_only')),
        'plan_sha256': plan.get('plan_sha256') if isinstance(plan, dict) else None,
        'analysis_sha256': analysis_result.get('analysis_sha256') if isinstance(analysis_result, dict) else None,
        'check_results': check_results,
        'diagnostics': diagnostics,
        'findings': plan.get('findings', []) if isinstance(plan, dict) else [],
    }

    report['report_sha256'] = canonical_json_digest(report)
    return report


# ============================================================================
# Boundary & Execution Controller Integration
# ============================================================================

def create_organization_plan_preview(
    input_bundle,
    analysis_result,
    *,
    validation_report=None,
    candidate_actions=None,
    consolidation_candidates=None,
):
    """Generate an isolated, safe candidate plan preview.

    Does not approve stage transition or pipeline progression.
    Displays current input status and unresolved items clearly.
    """
    plan = generate_organization_plan(
        input_bundle,
        analysis_result,
        candidate_actions=candidate_actions,
        consolidation_candidates=consolidation_candidates,
        execution_mode='preview',
        validation_report=validation_report,
    )
    report = validate_organization_plan(
        input_bundle,
        analysis_result,
        plan,
        validation_report=validation_report,
    )
    return {
        'plan': plan,
        'validation_report': report,
        'preview_only': True,
        'gate_state': report['gate_state'],
        'next_stage_allowed': False,
    }


def execute_authorized_organization(
    input_bundle,
    analysis_result,
    validation_report,
    *,
    adapter=None,
    validation_plan=None,
    organization_plan=None,
):
    """Attempt authorized stage execution into Information Organization.

    Enforces that actual stage transition is strictly governed by the independent Validation Gate.
    When the Validation Gate is in REVIEW, entry is strictly BLOCKED.
    """
    adapter = adapter or pipeline.OrganizationBoundaryAdapter()
    decision = pipeline.can_advance_to_organization(
        input_bundle,
        analysis_result,
        validation_report,
        plan=validation_plan,
    )

    if not decision['allowed']:
        # Boundary adapter will record blocked attempt and raise StageTransitionBlockedError
        return adapter.enter_organization_stage(
            input_bundle,
            analysis_result,
            validation_report,
            plan=validation_plan,
        )

    # If allowed (authorized path)
    invocation = adapter.enter_organization_stage(
        input_bundle,
        analysis_result,
        validation_report,
        plan=validation_plan,
    )
    return {
        'status': 'executed',
        'invocation': invocation,
        'decision': decision,
        'organization_plan': organization_plan,
    }
