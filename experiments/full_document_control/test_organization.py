#!/usr/bin/env python3
"""Unit, regression, boundary, and anti-forgery counterexample tests for Information Organization module."""

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
    """Test suite covering all Information Organization requirements, P1/P2 fixes, and counterexamples."""

    def setUp(self):
        self.bundle = test_pipeline.load_sample_bundle()
        self.resp = test_pipeline.make_valid_window_response(self.bundle)
        self.analysis = pipeline.assemble_document_analysis(self.bundle, [json.dumps(self.resp)])
        self.val_report = pipeline.validate_analysis_gate(self.bundle, self.analysis)

    def test_scenario_1_no_upstream_report_never_promoted_to_pass(self):
        """Scenario 1 (P1): Organization result is never promoted to PASS without verified upstream gate approval."""
        plan = organization.generate_organization_plan(self.bundle, self.analysis, execution_mode='authorized')
        plan['meta']['preview_only'] = False
        body = {k: v for k, v in plan.items() if k != 'plan_sha256'}
        plan['plan_sha256'] = pipeline.canonical_json_digest(body)

        val_res = organization.validate_organization_plan(
            self.bundle,
            self.analysis,
            plan,
            validation_report=None,
        )

        self.assertTrue(val_res['is_valid'])
        self.assertEqual(val_res['gate_state'], 'REVIEW')
        self.assertFalse(val_res['delivery_approved'])
        self.assertFalse(val_res['next_stage_allowed'])
        self.assertEqual(val_res['upstream_gate_state'], 'REVIEW')
        self.assertFalse(val_res['upstream_approved'])

    def test_scenario_2_forged_upstream_pass_report_rejected(self):
        """Scenario 2 (P1): Forged upstream PASS report is caught by independent gate re-verification."""
        forged_report = copy.deepcopy(self.val_report)
        forged_report['gate_state'] = 'PASS'
        forged_report['delivery_approved'] = True
        forged_report['next_stage_allowed'] = True
        body = {k: v for k, v in forged_report.items() if k != 'report_sha256'}
        forged_report['report_sha256'] = pipeline.canonical_json_digest(body)

        plan = organization.generate_organization_plan(self.bundle, self.analysis)
        plan['meta']['delivery_approved'] = True
        plan_body = {k: v for k, v in plan.items() if k != 'plan_sha256'}
        plan['plan_sha256'] = pipeline.canonical_json_digest(plan_body)

        val_res = organization.validate_organization_plan(
            self.bundle,
            self.analysis,
            plan,
            validation_report=forged_report,
        )

        self.assertEqual(val_res['gate_state'], 'FAIL')
        self.assertFalse(val_res['delivery_approved'])
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['ANTI_FORGERY_AND_APPROVAL_BOUNDS']['status'], 'violated')
        self.assertIn('FORGED_UPSTREAM_GATE_APPROVAL', checks_by_id['ANTI_FORGERY_AND_APPROVAL_BOUNDS']['reason'])

    def test_scenario_3_manipulating_or_deleting_blocking_findings_is_blocked(self):
        """Scenario 3 (P1): Deleting or altering blocking findings cannot bypass independent re-verification."""
        # Attempt to omit required unit u-timeout
        plan = organization.generate_organization_plan(
            self.bundle,
            self.analysis,
            candidate_actions={'u-timeout': {'action': 'REMOVE'}},
        )
        # Verify generator created a blocking finding
        self.assertTrue(any(f['blocking'] and f['rule_id'] == 'MANDATORY_INFORMATION_PRESERVATION_VIOLATION' for f in plan['findings']))

        # Adversary attempts to bypass by wiping plan['findings'] and forcing disposition='omitted'
        tampered_plan = copy.deepcopy(plan)
        p_timeout = next(p for p in tampered_plan['placements'] if p['unit_id'] == 'u-timeout')
        p_timeout['disposition'] = 'omitted'
        p_timeout['action'] = 'REMOVE'
        tampered_plan['findings'] = []
        body = {k: v for k, v in tampered_plan.items() if k != 'plan_sha256'}
        tampered_plan['plan_sha256'] = pipeline.canonical_json_digest(body)

        # Independent validator evaluates inputs directly, catching the omitted required information
        val_res = organization.validate_organization_plan(self.bundle, self.analysis, tampered_plan)
        self.assertEqual(val_res['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['MANDATORY_INFORMATION_PRESERVED']['status'], 'violated')
        self.assertIn('REQUIRED_INFORMATION_DROPPED', checks_by_id['MANDATORY_INFORMATION_PRESERVED']['reason'])

    def test_scenario_4_undeclared_move_destination_disguised_is_blocked(self):
        """Scenario 4 (P1): Disguising an undeclared MOVE destination in destination_reviews is rejected."""
        plan = organization.generate_organization_plan(self.bundle, self.analysis)
        tampered = copy.deepcopy(plan)

        # Adversary injects a fake destination into plan['destination_reviews'] and confirms MOVE
        tampered['destination_reviews'].append({
            'scope_id': 'fake_unauthorized_scope',
            'kind': 'document',
            'document_id': 'doc-fake',
            'verification_status': 'verified_context',
            'allows_confirmed_move': True,
        })
        p_macos = next(p for p in tampered['placements'] if p['unit_id'] == 'u-table-macos')
        p_macos['action'] = 'MOVE'
        p_macos['disposition'] = 'placed'
        p_macos['targets'] = [{'scope_id': 'fake_unauthorized_scope', 'relative_order': 10}]

        body = {k: v for k, v in tampered.items() if k != 'plan_sha256'}
        tampered['plan_sha256'] = pipeline.canonical_json_digest(body)

        val_res = organization.validate_organization_plan(self.bundle, self.analysis, tampered)
        self.assertEqual(val_res['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['ALLOWED_OUTPUT_SCOPES']['status'], 'violated')
        self.assertEqual(checks_by_id['DESTINATION_REVIEW_INTEGRITY']['status'], 'violated')
        self.assertIn('UNAUTHORIZED_DESTINATION_REVIEW', checks_by_id['DESTINATION_REVIEW_INTEGRITY']['reason'])

        # Also test declared provisional role forged to allows_confirmed_move=True
        role_bundle = copy.deepcopy(self.bundle)
        role_bundle['writing_contract']['output_scopes'].append({
            'scope_id': 'packaging_role',
            'kind': 'document',
            'destination_role': '패키징 의사결정 이력',
        })
        role_analysis = copy.deepcopy(self.analysis)
        role_analysis['contract_sha256'] = pipeline.canonical_json_digest(role_bundle['writing_contract'])
        r_body = {k: v for k, v in role_analysis.items() if k != 'analysis_sha256'}
        role_analysis['analysis_sha256'] = pipeline.canonical_json_digest(r_body)

        plan_role = organization.generate_organization_plan(role_bundle, role_analysis)
        tampered_role = copy.deepcopy(plan_role)
        p_role_rev = next(r for r in tampered_role['destination_reviews'] if r['scope_id'] == 'packaging_role')
        p_role_rev['allows_confirmed_move'] = True
        body_rr = {k: v for k, v in tampered_role.items() if k != 'plan_sha256'}
        tampered_role['plan_sha256'] = pipeline.canonical_json_digest(body_rr)

        val_role = organization.validate_organization_plan(role_bundle, role_analysis, tampered_role)
        self.assertEqual(val_role['gate_state'], 'FAIL')
        checks_role = {c['check_id']: c for c in val_role['check_results']}
        self.assertEqual(checks_role['DESTINATION_REVIEW_INTEGRITY']['status'], 'violated')
        self.assertIn('FORGED_DESTINATION_REVIEW_APPROVAL', checks_role['DESTINATION_REVIEW_INTEGRITY']['reason'])

    def test_scenario_5_destination_snapshot_hash_content_version_mismatch_blocked(self):
        """Scenario 5 (P1): Destination snapshot content digest mismatch or missing version is rejected."""
        move_bundle = copy.deepcopy(self.bundle)
        move_bundle['writing_contract']['output_scopes'].append({
            'scope_id': 'packaging_doc',
            'kind': 'document',
            'document_id': 'doc-packaging-decisions',
        })
        move_analysis = copy.deepcopy(self.analysis)
        move_analysis['contract_sha256'] = pipeline.canonical_json_digest(move_bundle['writing_contract'])
        body = {k: v for k, v in move_analysis.items() if k != 'analysis_sha256'}
        move_analysis['analysis_sha256'] = pipeline.canonical_json_digest(body)

        # 5a. Corrupted SHA-256 (claimed sha != digest_text(content))
        corrupted_snap = [
            {
                'document_id': 'doc-packaging-decisions',
                'content': '# 패키징 의사결정 문서\n',
                'sha256': 'bad_corrupted_hash_value_1234567890abcdef',
                'version': '1',
            }
        ]
        plan_corrupted = organization.generate_organization_plan(
            move_bundle,
            move_analysis,
            candidate_actions={'u-table-macos': {'action': 'MOVE', 'target_scope_id': 'packaging_doc'}},
            destination_snapshots=corrupted_snap,
        )
        # Even if plan attempts to confirm move:
        tampered = copy.deepcopy(plan_corrupted)
        p = next(x for x in tampered['placements'] if x['unit_id'] == 'u-table-macos')
        p['disposition'] = 'placed'
        p['action'] = 'MOVE'
        p_body = {k: v for k, v in tampered.items() if k != 'plan_sha256'}
        tampered['plan_sha256'] = pipeline.canonical_json_digest(p_body)

        val_corrupted = organization.validate_organization_plan(
            move_bundle,
            move_analysis,
            tampered,
            destination_snapshots=corrupted_snap,
        )
        self.assertEqual(val_corrupted['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_corrupted['check_results']}
        self.assertEqual(checks_by_id['DESTINATION_REVIEW_INTEGRITY']['status'], 'violated')
        self.assertIn('corrupted_destination_snapshot', checks_by_id['DESTINATION_REVIEW_INTEGRITY']['reason'])

        # 5b. Missing version
        missing_ver_snap = [
            {
                'document_id': 'doc-packaging-decisions',
                'content': '# 패키징 의사결정 문서\n',
                'sha256': pipeline.digest_text('# 패키징 의사결정 문서\n'),
                'version': '',
            }
        ]
        val_missing_ver = organization.validate_organization_plan(
            move_bundle,
            move_analysis,
            tampered,
            destination_snapshots=missing_ver_snap,
        )
        self.assertEqual(val_missing_ver['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_missing_ver['check_results']}
        self.assertEqual(checks_by_id['DESTINATION_REVIEW_INTEGRITY']['status'], 'violated')
        self.assertIn('invalid_destination_version', checks_by_id['DESTINATION_REVIEW_INTEGRITY']['reason'])

    def test_scenario_6_distinct_claims_cannot_be_consolidated(self):
        """Scenario 6 (P1): Distinct substantive claims cannot be consolidated even if no numbers conflict."""
        u_main = next(u for u in self.analysis['units'] if u['id'] == 'u-heading-main')
        u_code = next(u for u in self.analysis['units'] if u['id'] == 'u-code-install')

        compat = organization.check_consolidation_compatibility(u_main, u_code)
        self.assertFalse(compat['compatible'])
        self.assertEqual(compat['status'], 'distinct_claims')

        # If a plan attempts to merge them as compatible:
        plan = organization.generate_organization_plan(
            self.bundle,
            self.analysis,
            consolidation_candidates=[
                {
                    'id': 'cg-distinct',
                    'member_unit_ids': ['u-heading-main', 'u-code-install'],
                    'equivalence_basis': 'Attempted merge of title and install command',
                }
            ],
        )
        self.assertTrue(plan['consolidation_groups'][0]['blocked'])

        # Tampering to force compatible=True
        tampered = copy.deepcopy(plan)
        tampered['consolidation_groups'][0]['blocked'] = False
        tampered['consolidation_groups'][0]['compatibility_status'] = 'compatible'
        body = {k: v for k, v in tampered.items() if k != 'plan_sha256'}
        tampered['plan_sha256'] = pipeline.canonical_json_digest(body)

        val_res = organization.validate_organization_plan(self.bundle, self.analysis, tampered)
        self.assertEqual(val_res['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['CONSOLIDATION_FIDELITY']['status'], 'violated')
        self.assertIn('INCOMPATIBLE_CONSOLIDATION_CANDIDATE', checks_by_id['CONSOLIDATION_FIDELITY']['reason'])

    def test_scenario_7_same_numbers_conditions_but_different_meaning_cannot_consolidate(self):
        """Scenario 7 (P1): Claims with identical lack of numbers/conditions but distinct meanings cannot be consolidated."""
        u_main = next(u for u in self.analysis['units'] if u['id'] == 'u-heading-main')
        u_caveats = next(u for u in self.analysis['units'] if u['id'] == 'u-heading-caveats')

        # Neither unit has quantity or condition elements
        compat = organization.check_consolidation_compatibility(u_main, u_caveats)
        self.assertFalse(compat['compatible'])
        self.assertIn(compat['status'], {'distinct_claims', 'unverified_semantic_equivalence'})

        plan = organization.generate_organization_plan(
            self.bundle,
            self.analysis,
            consolidation_candidates=[
                {
                    'id': 'cg-two-headings',
                    'member_unit_ids': ['u-heading-main', 'u-heading-caveats'],
                    'equivalence_basis': 'Attempted merge of two different section headings',
                }
            ],
        )
        self.assertTrue(plan['consolidation_groups'][0]['blocked'])

        tampered = copy.deepcopy(plan)
        tampered['consolidation_groups'][0]['blocked'] = False
        tampered['consolidation_groups'][0]['compatibility_status'] = 'compatible'
        body = {k: v for k, v in tampered.items() if k != 'plan_sha256'}
        tampered['plan_sha256'] = pipeline.canonical_json_digest(body)

        val_res = organization.validate_organization_plan(self.bundle, self.analysis, tampered)
        self.assertEqual(val_res['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['CONSOLIDATION_FIDELITY']['status'], 'violated')

    def test_scenario_8_modified_analysis_body_with_old_digest_rejected(self):
        """Scenario 8 (P2): Modifying AnalysisResult body while keeping the old digest is rejected."""
        mutated_analysis = copy.deepcopy(self.analysis)
        # Modify statement without updating analysis_sha256
        mutated_analysis['units'][0]['statement'] += ' [unauthorized modification]'
        # Keep old analysis_sha256 intact
        self.assertEqual(mutated_analysis['analysis_sha256'], self.analysis['analysis_sha256'])

        plan = organization.generate_organization_plan(self.bundle, self.analysis)

        val_res = organization.validate_organization_plan(self.bundle, mutated_analysis, plan)
        self.assertEqual(val_res['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['ORGANIZATION_INPUT_INTEGRITY']['status'], 'violated')
        self.assertIn('ANALYSIS_DIGEST_CORRUPTED', checks_by_id['ORGANIZATION_INPUT_INTEGRITY']['reason'])

    def test_scenario_9_normal_preview_maintains_review(self):
        """Scenario 9: Normal Plan Preview maintains REVIEW gate_state and does not permit next stage."""
        preview = organization.create_organization_plan_preview(
            self.bundle,
            self.analysis,
            validation_report=self.val_report,
        )
        self.assertTrue(preview['preview_only'])
        self.assertEqual(preview['gate_state'], 'REVIEW')
        self.assertFalse(preview['next_stage_allowed'])
        self.assertFalse(preview['validation_report']['delivery_approved'])
        self.assertTrue(preview['validation_report']['is_valid'])

    def test_scenario_10_normal_candidate_placement_and_protected_info_preserved(self):
        """Scenario 10: Normal candidate placement succeeds with full protection tracking and condition adjacency."""
        plan = organization.generate_organization_plan(
            self.bundle,
            self.analysis,
            validation_report=self.val_report,
        )

        self.assertEqual(len(plan['placements']), len(self.analysis['units']))
        placements_by_uid = {p['unit_id']: p for p in plan['placements']}

        # Protected units retain their contract protection
        p_timeout = placements_by_uid['u-timeout']
        self.assertTrue(p_timeout['contract_protection']['is_protected'])
        self.assertIn('req-timeout', p_timeout['contract_protection']['bound_requirement_ids'])

        p_offline = placements_by_uid['u-cond-offline-cache']
        self.assertTrue(p_offline['contract_protection']['is_protected'])
        self.assertEqual(p_offline['targets'][0]['anchor_relative_position'], 'before')
        self.assertEqual(p_offline['targets'][0]['anchor_unit_id'], 'u-runtime-overview')

        val_res = organization.validate_organization_plan(self.bundle, self.analysis, plan, validation_report=self.val_report)
        self.assertTrue(val_res['is_valid'])
        self.assertEqual(val_res['gate_state'], 'REVIEW')
        for check in val_res['check_results']:
            self.assertEqual(check['status'], 'passed', f"{check['check_id']} failed: {check['reason']}")

    def test_scenario_11_review_state_blocks_authorized_organization_entry(self):
        """Scenario 11: Attempting authorized stage transition under REVIEW state raises StageTransitionBlockedError."""
        adapter = pipeline.OrganizationBoundaryAdapter()
        with self.assertRaises(pipeline.StageTransitionBlockedError) as ctx:
            organization.execute_authorized_organization(
                self.bundle,
                self.analysis,
                self.val_report,
                adapter=adapter,
            )

        self.assertEqual(ctx.exception.decision['gate_state'], 'REVIEW')
        self.assertFalse(ctx.exception.decision['allowed'])
        self.assertEqual(len(adapter.invocations), 0)
        self.assertEqual(len(adapter.blocked_attempts), 1)

    def test_scenario_12_unit_omission_and_duplicate_placement_rejected(self):
        """Scenario 12: Missing unit and duplicate placement are both detected and rejected."""
        plan = organization.generate_organization_plan(self.bundle, self.analysis)

        # 1. Missing unit
        tampered_missing = copy.deepcopy(plan)
        tampered_missing['placements'] = [p for p in tampered_missing['placements'] if p['unit_id'] != 'u-code-install']
        body_m = {k: v for k, v in tampered_missing.items() if k != 'plan_sha256'}
        tampered_missing['plan_sha256'] = pipeline.canonical_json_digest(body_m)

        val_missing = organization.validate_organization_plan(self.bundle, self.analysis, tampered_missing)
        self.assertEqual(val_missing['gate_state'], 'FAIL')
        checks_by_id = {c['check_id']: c for c in val_missing['check_results']}
        self.assertEqual(checks_by_id['ALL_UNITS_TRACKED']['status'], 'violated')
        self.assertIn('UNIT_OMITTED_FROM_ORGANIZATION_PLAN', checks_by_id['ALL_UNITS_TRACKED']['reason'])

        # 2. Duplicate placement
        tampered_dup = copy.deepcopy(plan)
        tampered_dup['placements'].append(dict(tampered_dup['placements'][0]))
        body_d = {k: v for k, v in tampered_dup.items() if k != 'plan_sha256'}
        tampered_dup['plan_sha256'] = pipeline.canonical_json_digest(body_d)

        val_dup = organization.validate_organization_plan(self.bundle, self.analysis, tampered_dup)
        self.assertEqual(val_dup['gate_state'], 'FAIL')
        checks_by_id2 = {c['check_id']: c for c in val_dup['check_results']}
        self.assertEqual(checks_by_id2['ALL_UNITS_TRACKED']['status'], 'violated')
        self.assertIn('DUPLICATE_UNIT_PLACEMENT', checks_by_id2['ALL_UNITS_TRACKED']['reason'])

    def test_scenario_13_valid_cross_document_move_with_verified_snapshot(self):
        """Scenario 13: Concrete destination with verified snapshot content and digest passes validation."""
        move_bundle = copy.deepcopy(self.bundle)
        move_bundle['writing_contract']['output_scopes'].append({
            'scope_id': 'packaging_doc',
            'kind': 'document',
            'document_id': 'doc-packaging-decisions',
        })
        move_analysis = copy.deepcopy(self.analysis)
        move_analysis['contract_sha256'] = pipeline.canonical_json_digest(move_bundle['writing_contract'])
        body = {k: v for k, v in move_analysis.items() if k != 'analysis_sha256'}
        move_analysis['analysis_sha256'] = pipeline.canonical_json_digest(body)

        content = '# 패키징 의사결정 문서\n\n런타임 배포 패키지 설계 이력이다.\n'
        verified_snap = [
            {
                'document_id': 'doc-packaging-decisions',
                'content': content,
                'sha256': pipeline.digest_text(content),
                'version': '1',
            }
        ]

        plan = organization.generate_organization_plan(
            move_bundle,
            move_analysis,
            candidate_actions={'u-table-macos': {'action': 'MOVE', 'target_scope_id': 'packaging_doc'}},
            destination_snapshots=verified_snap,
            validation_report=self.val_report,
        )

        p_move = next(p for p in plan['placements'] if p['unit_id'] == 'u-table-macos')
        self.assertEqual(p_move['action'], 'MOVE')
        self.assertEqual(p_move['disposition'], 'placed')
        self.assertEqual(p_move['targets'][0]['scope_id'], 'packaging_doc')

        val_res = organization.validate_organization_plan(
            move_bundle,
            move_analysis,
            plan,
            destination_snapshots=verified_snap,
        )
        self.assertTrue(val_res['is_valid'])
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['DESTINATION_REVIEW_INTEGRITY']['status'], 'passed')
        self.assertEqual(checks_by_id['ALLOWED_OUTPUT_SCOPES']['status'], 'passed')

    def test_scenario_14_compatible_redundancy_consolidation_and_member_contributions_preserved(self):
        """Scenario 14: Exact redundant units form consolidation group with full member contributions preserved."""
        dup_bundle = copy.deepcopy(self.bundle)
        dup_resp = test_pipeline.make_valid_window_response(dup_bundle)
        dup_unit = copy.deepcopy(dup_resp['units'][2])
        dup_unit['id'] = 'u-timeout-dup'
        dup_unit['statement'] = '기본 요청 제한 시간은 30초다.'  # Exact match statement
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

        # Verify member contributions preserved
        contribs = cg['member_contributions']
        self.assertEqual(len(contribs), 2)
        c0 = next(c for c in contribs if c['unit_id'] == 'u-timeout')
        c1 = next(c for c in contribs if c['unit_id'] == 'u-timeout-dup')
        self.assertEqual(c0['statement'], '기본 요청 제한 시간은 30초다.')
        self.assertEqual(c1['statement'], '기본 요청 제한 시간은 30초다.')
        self.assertTrue(c0['is_protected'])
        self.assertIn('req-timeout', c0['bound_requirement_ids'])

        val_res = organization.validate_organization_plan(dup_bundle, dup_analysis, plan)
        self.assertTrue(val_res['is_valid'])
        checks_by_id = {c['check_id']: c for c in val_res['check_results']}
        self.assertEqual(checks_by_id['CONSOLIDATION_FIDELITY']['status'], 'passed')


if __name__ == '__main__':
    unittest.main()
