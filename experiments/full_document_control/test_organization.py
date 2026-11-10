#!/usr/bin/env python3
"""Unit, regression, boundary, and anti-forgery tests for Information Organization module."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

_PIPE_SPEC = importlib.util.spec_from_file_location('full_document_control_pipeline', HERE / 'pipeline.py')
pipeline = importlib.util.module_from_spec(_PIPE_SPEC)
_PIPE_SPEC.loader.exec_module(pipeline)

_ORG_SPEC = importlib.util.spec_from_file_location('organization', HERE / 'organization.py')
organization = importlib.util.module_from_spec(_ORG_SPEC)
_ORG_SPEC.loader.exec_module(organization)

_TEST_PIPE_SPEC = importlib.util.spec_from_file_location('test_pipeline', HERE / 'test_pipeline.py')
test_pipeline = importlib.util.module_from_spec(_TEST_PIPE_SPEC)
_TEST_PIPE_SPEC.loader.exec_module(test_pipeline)


class InformationOrganizationTests(unittest.TestCase):
    """Test suite covering all Information Organization requirements and invariants."""

    def setUp(self):
        self.bundle = test_pipeline.load_sample_bundle()
        self.resp = test_pipeline.make_valid_window_response(self.bundle)
        self.analysis = pipeline.assemble_document_analysis(self.bundle, [json.dumps(self.resp)])
        self.val_report = pipeline.validate_analysis_gate(self.bundle, self.analysis)

    def test_scenario_1_normal_in_document_placement(self):
        """Scenario 1: Normal InformationUnits are placed in-document with topic sections and condition adjacency."""
        plan = organization.generate_organization_plan(
            self.bundle,
            self.analysis,
            validation_report=self.val_report,
        )

        self.assertEqual(plan['version'], organization.ORGANIZATION_PLAN_VERSION)
        self.assertEqual(len(plan['placements']), len(self.analysis['units']))
        self.assertTrue(plan['meta']['preview_only'])
        self.assertFalse(plan['meta']['delivery_approved'])

        # Check sections and relative orders
        placements_by_uid = {p['unit_id']: p for p in plan['placements']}
        self.assertIn('u-heading-main', placements_by_uid)
        self.assertIn('u-timeout', placements_by_uid)
        self.assertIn('u-cond-offline-cache', placements_by_uid)

        # Overview heading comes before installation commands
        p_title = placements_by_uid['u-heading-main']
        p_install = placements_by_uid['u-code-install']
        self.assertLess(
            p_title['targets'][0]['relative_order'],
            p_install['targets'][0]['relative_order'],
        )

        # Condition unit for offline cache is marked with anchor relation to qualified claim (u-runtime-overview)
        p_cond = placements_by_uid['u-cond-offline-cache']
        self.assertEqual(p_cond['targets'][0]['anchor_relative_position'], 'before')
        self.assertEqual(p_cond['targets'][0]['anchor_unit_id'], 'u-runtime-overview')

        # Independent validation
        val_res = organization.validate_organization_plan(
            self.bundle,
            self.analysis,
            plan,
            validation_report=self.val_report,
        )
        self.assertTrue(val_res['is_valid'])
        self.assertEqual(val_res['gate_state'], 'REVIEW')  # Because upstream gate is in REVIEW
        self.assertFalse(val_res['delivery_approved'])

    def test_scenario_2_redundancy_consolidation_compatible(self):
        """Scenario 2: Semantically redundant units with compatible conditions and elements form a consolidation group."""
        # Create an analysis with duplicate runtime units
        dup_bundle = copy.deepcopy(self.bundle)
        dup_resp = test_pipeline.make_valid_window_response(dup_bundle)
        # Duplicate u-timeout with identical values
        dup_unit = copy.deepcopy(dup_resp['units'][2])
        dup_unit['id'] = 'u-timeout-dup'
        dup_unit['statement'] = '기본 요청 제한 시간 수치는 30초다.'
        dup_resp['units'].append(dup_unit)
        dup_resp['block_coverage'][1]['unit_ids'].append('u-timeout-dup')

        dup_analysis = pipeline.assemble_document_analysis(dup_bundle, [json.dumps(dup_resp)])

        plan = organization.generate_organization_plan(
            dup_bundle,
            dup_analysis,
            consolidation_candidates=[
                {
                    'id': 'cg-timeout',
                    'member_unit_ids': ['u-timeout', 'u-timeout-dup'],
                    'equivalence_basis': 'Identical timeout limit specification across blocks',
                }
            ],
            validation_report=self.val_report,
        )

        self.assertEqual(len(plan['consolidation_groups']), 1)
        cg = plan['consolidation_groups'][0]
        self.assertEqual(cg['compatibility_status'], 'compatible')
        self.assertFalse(cg['blocked'])
        self.assertEqual(cg['member_unit_ids'], ['u-timeout', 'u-timeout-dup'])

        # Secondary unit is marked CONSOLIDATE
        placements_by_uid = {p['unit_id']: p for p in plan['placements']}
        p_dup = placements_by_uid['u-timeout-dup']
        self.assertEqual(p_dup['action'], 'CONSOLIDATE')
        self.assertEqual(p_dup['consolidated_into'], 'u-timeout')

        # Independent validation passes
        val_res = organization.validate_organization_plan(dup_bundle, dup_analysis, plan)
        self.assertTrue(val_res['is_valid'])
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['CONSOLIDATION_FIDELITY']['status'], 'passed')

    def test_scenario_3_differing_conditions_or_versions_block_consolidation(self):
        """Scenario 3: Units with differing conditions, versions, quantities, or platforms cannot be consolidated."""
        # 1. Condition divergence: u-runtime-overview (unconditional) vs u-cond-offline-cache (cache condition)
        # 2. Platform & package divergence: u-table-ubuntu (Linux) vs u-table-macos (macOS)
        # 3. Quantity conflict: duplicate u-timeout and alter element quantity value in analysis
        analysis_with_qty = copy.deepcopy(self.analysis)
        unit_60s = copy.deepcopy(analysis_with_qty['units'][2])
        unit_60s['id'] = 'u-timeout-60s'
        unit_60s['statement'] = '기본 요청 제한 시간 수치는 60초다.'
        unit_60s['elements'][0]['id'] = 'el-timeout-60s'
        unit_60s['elements'][0]['value'] = '60초'
        analysis_with_qty['units'].append(unit_60s)
        body = {k: v for k, v in analysis_with_qty.items() if k != 'analysis_sha256'}
        analysis_with_qty['analysis_sha256'] = pipeline.canonical_json_digest(body)

        plan = organization.generate_organization_plan(
            self.bundle,
            analysis_with_qty,
            consolidation_candidates=[
                {
                    'id': 'cg-qty-conflict',
                    'member_unit_ids': ['u-timeout', 'u-timeout-60s'],
                    'equivalence_basis': 'Attempted merge of conflicting timeouts (30s vs 60s)',
                },
                {
                    'id': 'cg-platform-conflict',
                    'member_unit_ids': ['u-table-ubuntu', 'u-table-macos'],
                    'equivalence_basis': 'Attempted merge of Linux and macOS packages',
                },
                {
                    'id': 'cg-condition-conflict',
                    'member_unit_ids': ['u-runtime-overview', 'u-cond-offline-cache'],
                    'equivalence_basis': 'Attempted merge of unconditional claim and condition constraint',
                },
            ],
            validation_report=self.val_report,
        )

        self.assertEqual(len(plan['consolidation_groups']), 3)

        cg_qty = plan['consolidation_groups'][0]
        self.assertEqual(cg_qty['compatibility_status'], 'conflicting_quantities')
        self.assertTrue(cg_qty['blocked'])

        cg_plat = plan['consolidation_groups'][1]
        self.assertTrue(cg_plat['blocked'])
        self.assertIn(cg_plat['compatibility_status'], {'conflicting_platforms', 'conflicting_versions'})

        cg_cond = plan['consolidation_groups'][2]
        self.assertEqual(cg_cond['compatibility_status'], 'conflicting_conditions')
        self.assertTrue(cg_cond['blocked'])

        # Units remain separate placements (not merged)
        placements_by_uid = {p['unit_id']: p for p in plan['placements']}
        self.assertEqual(placements_by_uid['u-timeout-60s']['action'], 'KEEP')
        self.assertEqual(placements_by_uid['u-table-ubuntu']['action'], 'KEEP')
        self.assertEqual(placements_by_uid['u-runtime-overview']['action'], 'KEEP')

        # If an adversary creates a tampered plan claiming they were compatible and not blocked:
        tampered_plan = copy.deepcopy(plan)
        tampered_plan['consolidation_groups'][0]['blocked'] = False
        tampered_plan['consolidation_groups'][0]['compatibility_status'] = 'compatible'
        tampered_body = {k: v for k, v in tampered_plan.items() if k != 'plan_sha256'}
        tampered_plan['plan_sha256'] = pipeline.canonical_json_digest(tampered_body)

        tampered_val = organization.validate_organization_plan(self.bundle, analysis_with_qty, tampered_plan)
        self.assertEqual(tampered_val['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in tampered_val['check_results']}
        self.assertEqual(checks_by_id['CONSOLIDATION_FIDELITY']['status'], 'violated')
        self.assertIn('INCOMPATIBLE_CONSOLIDATION_CANDIDATE', checks_by_id['CONSOLIDATION_FIDELITY']['reason'])

    def test_scenario_4_valid_cross_document_move_candidate(self):
        """Scenario 4: Valid MOVE candidate targeting a declared, verified external document scope."""
        move_bundle = copy.deepcopy(self.bundle)
        # Add a concrete external document scope to contract
        move_bundle['writing_contract']['output_scopes'].append({
            'scope_id': 'packaging_doc',
            'kind': 'document',
            'document_id': 'doc-packaging-decisions',
        })
        move_analysis = copy.deepcopy(self.analysis)
        move_analysis['contract_sha256'] = pipeline.canonical_json_digest(move_bundle['writing_contract'])
        body = {k: v for k, v in move_analysis.items() if k != 'analysis_sha256'}
        move_analysis['analysis_sha256'] = pipeline.canonical_json_digest(body)

        dest_snapshots = [
            {
                'document_id': 'doc-packaging-decisions',
                'content': '# 패키징 의사결정 문서\n\n런타임 배포 패키지 설계 이력이다.\n',
                'sha256': pipeline.digest_text('# 패키징 의사결정 문서\n\n런타임 배포 패키지 설계 이력이다.\n'),
            }
        ]

        plan = organization.generate_organization_plan(
            move_bundle,
            move_analysis,
            candidate_actions={
                'u-table-macos': {'action': 'MOVE', 'target_scope_id': 'packaging_doc'},
            },
            destination_snapshots=dest_snapshots,
            validation_report=self.val_report,
        )

        p_move = next(p for p in plan['placements'] if p['unit_id'] == 'u-table-macos')
        self.assertEqual(p_move['action'], 'MOVE')
        self.assertEqual(p_move['disposition'], 'placed')
        self.assertEqual(p_move['targets'][0]['scope_id'], 'packaging_doc')
        self.assertTrue(p_move['transfer_peer_ids'])

        # Check affected documents
        affected_scopes = {d['scope_id'] for d in plan['affected_documents']}
        self.assertIn('install_guide', affected_scopes)
        self.assertIn('packaging_doc', affected_scopes)

        # Independent validation passes
        val_res = organization.validate_organization_plan(move_bundle, move_analysis, plan)
        self.assertTrue(val_res['is_valid'])
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['DESTINATION_REVIEW_INTEGRITY']['status'], 'passed')
        self.assertEqual(checks_by_id['ALLOWED_OUTPUT_SCOPES']['status'], 'passed')

    def test_scenario_5_invalid_and_unauthorized_and_role_only_move_blocked(self):
        """Scenario 5: MOVE to undeclared scope or unverified destination_role is blocked."""
        # 1. Undeclared scope
        plan_undeclared = organization.generate_organization_plan(
            self.bundle,
            self.analysis,
            candidate_actions={
                'u-table-macos': {'action': 'MOVE', 'target_scope_id': 'completely_invented_scope'},
            },
        )
        p_blocked = next(p for p in plan_undeclared['placements'] if p['unit_id'] == 'u-table-macos')
        self.assertEqual(p_blocked['disposition'], 'blocked')
        self.assertEqual(p_blocked['action'], 'FLAG')
        self.assertTrue(any(f['rule_id'] == 'UNAUTHORIZED_DESTINATION_SCOPE' for f in plan_undeclared['findings']))

        # If a tampered plan claims placement into undeclared scope was successful:
        forged_undeclared = copy.deepcopy(plan_undeclared)
        forged_p = next(p for p in forged_undeclared['placements'] if p['unit_id'] == 'u-table-macos')
        forged_p['disposition'] = 'placed'
        forged_p['action'] = 'MOVE'
        forged_p['targets'] = [{'scope_id': 'completely_invented_scope', 'relative_order': 10}]
        body = {k: v for k, v in forged_undeclared.items() if k != 'plan_sha256'}
        forged_undeclared['plan_sha256'] = pipeline.canonical_json_digest(body)

        val_undeclared = organization.validate_organization_plan(self.bundle, self.analysis, forged_undeclared)
        self.assertEqual(val_undeclared['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_undeclared['check_results']}
        self.assertEqual(checks_by_id['ALLOWED_OUTPUT_SCOPES']['status'], 'violated')

        # 2. Provisional role-only scope (destination_role without concrete snapshot)
        role_bundle = copy.deepcopy(self.bundle)
        role_bundle['writing_contract']['output_scopes'].append({
            'scope_id': 'packaging_role',
            'kind': 'document',
            'destination_role': '패키징 의사결정·설계 이력 문서',
        })
        role_analysis = copy.deepcopy(self.analysis)
        role_analysis['contract_sha256'] = pipeline.canonical_json_digest(role_bundle['writing_contract'])
        body_r = {k: v for k, v in role_analysis.items() if k != 'analysis_sha256'}
        role_analysis['analysis_sha256'] = pipeline.canonical_json_digest(body_r)

        plan_role = organization.generate_organization_plan(
            role_bundle,
            role_analysis,
            candidate_actions={
                'u-table-macos': {'action': 'MOVE', 'target_scope_id': 'packaging_role'},
            },
        )
        p_role = next(p for p in plan_role['placements'] if p['unit_id'] == 'u-table-macos')
        # Role target must be held as proposal / blocked, not confirmed placed
        self.assertEqual(p_role['disposition'], 'blocked')
        self.assertTrue(any(f['rule_id'] == 'UNVERIFIED_DESTINATION_CONTEXT' for f in plan_role['findings']))

        # If adversary marks it as confirmed 'placed' in role-only destination:
        forged_role = copy.deepcopy(plan_role)
        forged_role_p = next(p for p in forged_role['placements'] if p['unit_id'] == 'u-table-macos')
        forged_role_p['disposition'] = 'placed'
        forged_role_p['action'] = 'MOVE'
        body_role = {k: v for k, v in forged_role.items() if k != 'plan_sha256'}
        forged_role['plan_sha256'] = pipeline.canonical_json_digest(body_role)

        val_role = organization.validate_organization_plan(role_bundle, role_analysis, forged_role)
        self.assertEqual(val_role['gate_state'], 'FAIL')
        checks_by_id_role = {c['check_id']: c for c in val_role['check_results']}
        self.assertEqual(checks_by_id_role['DESTINATION_REVIEW_INTEGRITY']['status'], 'violated')
        self.assertIn('UNVERIFIED_DESTINATION_CONFIRMED_MOVE', checks_by_id_role['DESTINATION_REVIEW_INTEGRITY']['reason'])

    def test_scenario_6_missing_mandatory_information_and_protected_condition_loss_blocked(self):
        """Scenario 6: Attempting to omit mandatory information or linked conditions is blocked."""
        # u-timeout is bound to req-timeout; u-cond-offline-cache is bound to req-offline-cache-condition
        plan = organization.generate_organization_plan(
            self.bundle,
            self.analysis,
            candidate_actions={
                'u-timeout': {'action': 'REMOVE'},
                'u-cond-offline-cache': {'action': 'REMOVE'},
            },
        )

        p_timeout = next(p for p in plan['placements'] if p['unit_id'] == 'u-timeout')
        p_cond = next(p for p in plan['placements'] if p['unit_id'] == 'u-cond-offline-cache')

        # Generator must block both omissions
        self.assertEqual(p_timeout['disposition'], 'blocked')
        self.assertEqual(p_cond['disposition'], 'blocked')
        self.assertTrue(p_timeout['contract_protection']['is_protected'])
        self.assertTrue(p_cond['contract_protection']['is_protected'])

        # If a forged plan sets disposition='omitted' on a required unit:
        tampered_plan = copy.deepcopy(plan)
        t_timeout = next(p for p in tampered_plan['placements'] if p['unit_id'] == 'u-timeout')
        t_timeout['disposition'] = 'omitted'
        t_timeout['action'] = 'REMOVE'
        body = {k: v for k, v in tampered_plan.items() if k != 'plan_sha256'}
        tampered_plan['plan_sha256'] = pipeline.canonical_json_digest(body)

        val_res = organization.validate_organization_plan(self.bundle, self.analysis, tampered_plan)
        self.assertEqual(val_res['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['MANDATORY_INFORMATION_PRESERVED']['status'], 'violated')
        self.assertIn('REQUIRED_INFORMATION_DROPPED', checks_by_id['MANDATORY_INFORMATION_PRESERVED']['reason'])

    def test_scenario_7_omitted_unit_from_plan_detected(self):
        """Scenario 7: Plan omitting any InformationUnit fails ALL_UNITS_TRACKED check."""
        plan = organization.generate_organization_plan(self.bundle, self.analysis)
        tampered = copy.deepcopy(plan)
        # Drop unit u-code-install from placements
        tampered['placements'] = [p for p in tampered['placements'] if p['unit_id'] != 'u-code-install']
        body = {k: v for k, v in tampered.items() if k != 'plan_sha256'}
        tampered['plan_sha256'] = pipeline.canonical_json_digest(body)

        val_res = organization.validate_organization_plan(self.bundle, self.analysis, tampered)
        self.assertEqual(val_res['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['ALL_UNITS_TRACKED']['status'], 'violated')
        self.assertIn('u-code-install', checks_by_id['ALL_UNITS_TRACKED']['reason'])

    def test_scenario_8_stale_analysis_invalidates_plan_reuse(self):
        """Scenario 8: Reusing a plan after upstream AnalysisResult changes is rejected."""
        plan = organization.generate_organization_plan(self.bundle, self.analysis)

        # Mutate analysis by changing statement or digest
        mutated_analysis = copy.deepcopy(self.analysis)
        mutated_analysis['units'][0]['statement'] += ' (mutated)'
        mutated_analysis['analysis_sha256'] = pipeline.digest_text('new_tampered_analysis')

        val_res = organization.validate_organization_plan(self.bundle, mutated_analysis, plan)
        self.assertEqual(val_res['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['ORGANIZATION_INPUT_INTEGRITY']['status'], 'violated')
        self.assertIn('STALE_ANALYSIS_PLAN_INVALIDATED', checks_by_id['ORGANIZATION_INPUT_INTEGRITY']['reason'])

    def test_scenario_9_model_forged_approval_claims_rejected(self):
        """Scenario 9: Plan claiming delivery_approved or stage_transition_allowed without gate pass is rejected."""
        plan = organization.generate_organization_plan(self.bundle, self.analysis)
        forged = copy.deepcopy(plan)
        forged['meta']['delivery_approved'] = True
        forged['meta']['stage_transition_allowed'] = True
        body = {k: v for k, v in forged.items() if k != 'plan_sha256'}
        forged['plan_sha256'] = pipeline.canonical_json_digest(body)

        # 1. Validated with unapproved validation report (gate_state: REVIEW)
        val_res = organization.validate_organization_plan(
            self.bundle,
            self.analysis,
            forged,
            validation_report=self.val_report,
        )
        self.assertEqual(val_res['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['ANTI_FORGERY_AND_APPROVAL_BOUNDS']['status'], 'violated')
        self.assertIn('UNAUTHORIZED_ORGANIZATION_APPROVAL_CLAIM', checks_by_id['ANTI_FORGERY_AND_APPROVAL_BOUNDS']['reason'])

        # 2. Validated without any validation report supplied
        val_no_report = organization.validate_organization_plan(
            self.bundle,
            self.analysis,
            forged,
            validation_report=None,
        )
        self.assertEqual(val_no_report['gate_state'], 'FAIL')
        checks_by_id2 = {c['check_id']: c for c in val_no_report['check_results']}
        self.assertEqual(checks_by_id2['ANTI_FORGERY_AND_APPROVAL_BOUNDS']['status'], 'violated')

    def test_scenario_10_review_state_blocks_organization_stage_entry(self):
        """Scenario 10: In REVIEW state, actual Organization stage entry is strictly blocked; preview remains safe."""
        # 1. Preview mode creation works and stays safe
        preview = organization.create_organization_plan_preview(
            self.bundle,
            self.analysis,
            validation_report=self.val_report,
        )
        self.assertTrue(preview['preview_only'])
        self.assertFalse(preview['next_stage_allowed'])
        self.assertEqual(preview['gate_state'], 'REVIEW')
        self.assertEqual(preview['plan']['meta']['execution_mode'], 'preview')

        # 2. Attempt to execute authorized transition directly with the REVIEW report must raise StageTransitionBlockedError
        adapter = pipeline.OrganizationBoundaryAdapter()
        with self.assertRaises(pipeline.StageTransitionBlockedError) as ctx:
            organization.execute_authorized_organization(
                self.bundle,
                self.analysis,
                self.val_report,
                adapter=adapter,
                organization_plan=preview['plan'],
            )

        self.assertEqual(ctx.exception.decision['gate_state'], 'REVIEW')
        self.assertFalse(ctx.exception.decision['allowed'])
        self.assertEqual(len(adapter.invocations), 0)
        self.assertEqual(len(adapter.blocked_attempts), 1)
        self.assertEqual(adapter.blocked_attempts[0]['gate_state'], 'REVIEW')

    def test_edge_case_duplicate_placement_of_same_unit_rejected(self):
        """Edge case: Duplicating a placement entry in the plan fails ALL_UNITS_TRACKED."""
        plan = organization.generate_organization_plan(self.bundle, self.analysis)
        dup_plan = copy.deepcopy(plan)
        dup_plan['placements'].append(dict(dup_plan['placements'][0]))
        body = {k: v for k, v in dup_plan.items() if k != 'plan_sha256'}
        dup_plan['plan_sha256'] = pipeline.canonical_json_digest(body)

        val_res = organization.validate_organization_plan(self.bundle, self.analysis, dup_plan)
        self.assertEqual(val_res['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['ALL_UNITS_TRACKED']['status'], 'violated')
        self.assertIn('DUPLICATE_UNIT_PLACEMENT', checks_by_id['ALL_UNITS_TRACKED']['reason'])


if __name__ == '__main__':
    unittest.main()
