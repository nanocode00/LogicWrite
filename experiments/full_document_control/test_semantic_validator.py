#!/usr/bin/env python3
"""Unit, regression, tamper-resistance, and end-to-end tests for the Semantic Fidelity Validator."""

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

_EVAL_SPEC = importlib.util.spec_from_file_location('semantic_eval_cases', HERE / 'semantic_eval_cases.py')
eval_cases = importlib.util.module_from_spec(_EVAL_SPEC)
_EVAL_SPEC.loader.exec_module(eval_cases)


class SemanticFidelityValidatorTests(unittest.TestCase):
    """Comprehensive tests for Semantic Fidelity Validator, Validation Gate integration, and ExecutionController."""

    def setUp(self):
        self.fd001_bundle = eval_cases.load_fd001_bundle()
        self.fd001_resp = eval_cases.make_fd001_faithful_window_response(self.fd001_bundle)
        self.fd001_analysis = pipeline.assemble_document_analysis(
            self.fd001_bundle, [json.dumps(self.fd001_resp)]
        )

        self.rw001_bundle = eval_cases.build_rw001_full_doc_bundle()
        self.rw001_resp = eval_cases.make_rw001_faithful_window_response(self.rw001_bundle)
        self.rw001_analysis = pipeline.assemble_document_analysis(
            self.rw001_bundle, [json.dumps(self.rw001_resp)]
        )

    def _check_status(self, gate_report, check_id):
        return next(c['status'] for c in gate_report['check_results'] if c['check_id'] == check_id)

    # ------------------------------------------------------------------
    # 1. Faithful Preservation & First-Implementation Auto-PASS Prohibition
    # ------------------------------------------------------------------
    def test_faithful_fd001_and_rw001_produce_supported_judgment_but_remain_review_at_gate(self):
        for bundle, analysis in (
            (self.fd001_bundle, self.fd001_analysis),
            (self.rw001_bundle, self.rw001_analysis),
        ):
            def stub_responder(w_idx, _sw, _prompt, _att, b=bundle, a=analysis):
                return pipeline.build_stub_semantic_response_from_audit(b, a, window_index=w_idx)

            gate_report = pipeline.validate_analysis_gate(
                bundle,
                analysis,
                semantic_responder=stub_responder,
                run_semantic_validation=True,
            )
            sem_report = gate_report['semantic_report']
            self.assertEqual(sem_report['overall_judgment'], 'supported')
            self.assertEqual(sem_report['findings'], [])
            self.assertTrue(sem_report['coverage_summary']['is_complete'])
            self.assertEqual(sem_report['coverage_summary']['unreviewed_unit_ids'], [])
            self.assertEqual(sem_report['coverage_summary']['unreviewed_block_ids'], [])

            # First implementation invariant: all-supported judgment NEVER auto-passes the gate
            self.assertEqual(self._check_status(gate_report, 'SEMANTIC_FIDELITY'), 'unresolved')
            self.assertEqual(gate_report['gate_state'], 'REVIEW')
            self.assertFalse(gate_report['delivery_approved'])
            self.assertFalse(pipeline.can_advance_to_organization(bundle, analysis, gate_report)['allowed'])
            codes = {f['rule_id'] for f in gate_report['findings']}
            self.assertIn('SEMANTIC_SUPPORTED_AWAITING_APPROVAL', codes)

    # ------------------------------------------------------------------
    # 2. Eight Required Semantic Error Categories & RW-001 Regressions
    # ------------------------------------------------------------------
    def test_category_1_claim_overstatement_rw001_a1_a2_regression(self):
        """RW-001 A/B regression (E-REQ-A1 / E-REQ-A2): installation requirements escalated to factual package behavior."""
        # Case A2: statement turns 'needs to install...' into 'The macOS package installs...'
        resp_a2 = copy.deepcopy(self.rw001_resp)
        for u in resp_a2['units']:
            if u['id'] == 'u-install-reqs':
                u['statement'] = (
                    'The macOS package installs a menu bar runtime under Applications, '
                    'bundles Node/cloudflared helpers, and runs a non-blocking post-install Doctor.'
                )
                u['assessment']['reason'] = (
                    'These factual package behaviors are the primary technical justification for why PKG is a better fit than DMG.'
                )
        analysis_a2 = pipeline.assemble_document_analysis(self.rw001_bundle, [json.dumps(resp_a2)])
        gate_report = pipeline.validate_analysis_gate(
            self.rw001_bundle, analysis_a2, run_semantic_validation=True
        )
        sem_report = gate_report['semantic_report']
        self.assertEqual(sem_report['overall_judgment'], 'overstated')
        self.assertEqual(self._check_status(gate_report, 'SEMANTIC_FIDELITY'), 'violated')
        self.assertEqual(gate_report['gate_state'], 'FAIL')

        paths = {f['field_path']: f for f in sem_report['findings']}
        self.assertIn('/units/2/statement', paths)
        self.assertEqual(paths['/units/2/statement']['error_category'], 'CLAIM_OVERSTATEMENT')
        self.assertEqual(paths['/units/2/statement']['semantic_judgment'], 'overstated')
        self.assertEqual(paths['/units/2/statement']['return_to_stage'], 'information_extraction_analysis')
        self.assertIn('/units/2/assessment/reason', paths)
        self.assertEqual(paths['/units/2/assessment/reason']['error_category'], 'ASSESSMENT_RATIONALE_DISTORTION')

        # Case A1: 'the fact that the macOS PKG installs...'
        resp_a1 = copy.deepcopy(self.rw001_resp)
        for u in resp_a1['units']:
            if u['id'] == 'u-install-reqs':
                u['assessment']['exposure'] = (
                    'Surface directly in the decision rationale alongside the PKG recommendation; '
                    'do not omit the fact that the macOS PKG installs a menu bar runtime under Applications, '
                    'bundles Node/cloudflared helpers, and runs a non-blocking post-install Doctor.'
                )
        analysis_a1 = pipeline.assemble_document_analysis(self.rw001_bundle, [json.dumps(resp_a1)])
        sem_a1 = pipeline.validate_semantic_fidelity(self.rw001_bundle, analysis_a1)
        self.assertEqual(sem_a1['overall_judgment'], 'overstated')
        a1_paths = {f['field_path']: f for f in sem_a1['findings']}
        self.assertIn('/units/2/assessment/exposure', a1_paths)

    def test_category_2_polarity_reversal_korean_and_english(self):
        """Polarity reversal: affirmative <-> negative, non-blocking <-> blocking."""
        # Korean polarity reversal on FD-001 B015
        resp_ko = copy.deepcopy(self.fd001_resp)
        for u in resp_ko['units']:
            if u['id'] == 'u-cond-macos-manual':
                u['statement'] = 'macOS 패키지는 초기 실험 빌드이지만 자동 업데이트를 지원하며 수동 재설치 없이 갱신된다.'
        analysis_ko = pipeline.assemble_document_analysis(self.fd001_bundle, [json.dumps(resp_ko)])
        gate_ko = pipeline.validate_analysis_gate(
            self.fd001_bundle, analysis_ko, run_semantic_validation=True
        )
        self.assertEqual(gate_ko['semantic_report']['overall_judgment'], 'contradicted')
        self.assertEqual(gate_ko['gate_state'], 'FAIL')
        cats_ko = {f['error_category'] for f in gate_ko['semantic_report']['findings']}
        self.assertIn('POLARITY_REVERSAL', cats_ko)

        # English polarity reversal on RW-001 ('non-blocking post-install Doctor' -> 'blocking post-install Doctor')
        resp_en = copy.deepcopy(self.rw001_resp)
        for u in resp_en['units']:
            if u['id'] == 'u-install-reqs':
                u['statement'] = (
                    'A DMG is nicer for drag-and-drop apps, but this app needs to install a menu bar runtime under '
                    'Applications, bundle Node/cloudflared helpers, and run a blocking post-install Doctor.'
                )
        analysis_en = pipeline.assemble_document_analysis(self.rw001_bundle, [json.dumps(resp_en)])
        sem_en = pipeline.validate_semantic_fidelity(self.rw001_bundle, analysis_en)
        self.assertEqual(sem_en['overall_judgment'], 'contradicted')
        self.assertTrue(any(
            f['error_category'] == 'POLARITY_REVERSAL' and f['field_path'] == '/units/2/statement'
            for f in sem_en['findings']
        ))

    def test_category_3_condition_loss_and_unjustified_omit_candidate(self):
        """Condition loss: generalizing release-scoped or cache-conditional claims, or omitting a qualifying unit."""
        # 3A: Generalizing 'For this release' to 'In all releases, PKG is permanently superior'
        resp_cond = copy.deepcopy(self.rw001_resp)
        for u in resp_cond['units']:
            if u['id'] == 'u-pkg-fit-release':
                u['statement'] = 'In all releases, PKG is permanently superior and always the only installer over DMG.'
        analysis_cond = pipeline.assemble_document_analysis(self.rw001_bundle, [json.dumps(resp_cond)])
        sem_cond = pipeline.validate_semantic_fidelity(self.rw001_bundle, analysis_cond)
        self.assertEqual(sem_cond['overall_judgment'], 'overstated')
        self.assertTrue(any(
            f['error_category'] == 'CONDITION_LOSS' and f['field_path'] == '/units/1/statement'
            for f in sem_cond['findings']
        ))

        # 3B: Marking a qualifying condition unit ('u-dmg-later-option') as 'omit_candidate' while target is 'retain_current'
        resp_omit = copy.deepcopy(self.rw001_resp)
        for u in resp_omit['units']:
            if u['id'] == 'u-dmg-later-option':
                u['assessment']['preservation'] = 'omit_candidate'
        analysis_omit = pipeline.assemble_document_analysis(self.rw001_bundle, [json.dumps(resp_omit)])
        sem_omit = pipeline.validate_semantic_fidelity(self.rw001_bundle, analysis_omit)
        self.assertEqual(sem_omit['overall_judgment'], 'contradicted')
        self.assertTrue(any(
            f['error_category'] == 'CONDITION_LOSS' and f['field_path'] == '/units/4/assessment/preservation'
            for f in sem_omit['findings']
        ))

    def test_category_4_quantity_unit_version_port_and_scope_distortion(self):
        """Quantity, unit, version, port, and platform scope distortions."""
        # 4A: 30초 -> 30분
        resp_unit = copy.deepcopy(self.fd001_resp)
        for u in resp_unit['units']:
            if u['id'] == 'u-timeout':
                u['statement'] = '기본 요청 제한 시간은 30분이다.'
        analysis_unit = pipeline.assemble_document_analysis(self.fd001_bundle, [json.dumps(resp_unit)])
        sem_unit = pipeline.validate_semantic_fidelity(self.fd001_bundle, analysis_unit)
        self.assertEqual(sem_unit['overall_judgment'], 'contradicted')
        self.assertTrue(any(
            f['error_category'] == 'QUANTITY_OR_SCOPE_DISTORTION' and f['field_path'] == '/units/2/statement'
            for f in sem_unit['findings']
        ))

        # 4B: Version & port distortion + platform swap (Ubuntu -> macOS)
        resp_scope = copy.deepcopy(self.fd001_resp)
        for u in resp_scope['units']:
            if u['id'] == 'u-table-ubuntu':
                u['statement'] = 'macOS 최소 지원 버전은 24.04 LTS이며 설치 패키지는 runtime-linux-x64.tar.gz다.'
            if u['id'] == 'u-code-install':
                u['statement'] = 'tar -xzf runtime-linux-x64.tar.gz 명령으로 압축을 해제한 뒤 ./install.sh --port 9090 명령으로 설치한다.'
        analysis_scope = pipeline.assemble_document_analysis(self.fd001_bundle, [json.dumps(resp_scope)])
        sem_scope = pipeline.validate_semantic_fidelity(self.fd001_bundle, analysis_scope)
        self.assertEqual(sem_scope['overall_judgment'], 'contradicted')
        paths = {f['field_path'] for f in sem_scope['findings'] if f['error_category'] == 'QUANTITY_OR_SCOPE_DISTORTION'}
        self.assertIn('/units/4/statement', paths)
        self.assertIn('/units/6/statement', paths)

    def test_category_5_unsupported_addition(self):
        """Unsupported addition of unstated encryption, daemon, or quantitative performance claims."""
        resp_add = copy.deepcopy(self.fd001_resp)
        for u in resp_add['units']:
            if u['id'] == 'u-runtime-overview':
                u['statement'] = (
                    '로컬 에이전트 런타임 v0.4.0은 외부 클라우드 업로드 없이 작업 폴더 안에서 파일 검색과 테스트 실행을 수행하며, '
                    'AES-256 암호화와 systemd 자동 복구 데몬을 통해 지연 시간을 50% 감소시킨다.'
                )
        analysis_add = pipeline.assemble_document_analysis(self.fd001_bundle, [json.dumps(resp_add)])
        sem_add = pipeline.validate_semantic_fidelity(self.fd001_bundle, analysis_add)
        self.assertEqual(sem_add['overall_judgment'], 'contradicted')
        self.assertTrue(any(
            f['error_category'] == 'UNSUPPORTED_ADDITION' and f['field_path'] == '/units/1/statement'
            for f in sem_add['findings']
        ))

    def test_category_6_critical_omission_backward_source_to_analysis_check(self):
        """Backward check (DocumentSnapshot -> AnalysisResult) detects omitted caveat clause in B015."""
        bundle = copy.deepcopy(self.fd001_bundle)
        bundle['writing_contract']['required_information'] = [
            req for req in bundle['writing_contract']['required_information']
            if req['id'] != 'req-macos-manual-update'
        ]
        resp_omit = eval_cases.make_fd001_faithful_window_response(bundle)
        resp_omit['units'] = [u for u in resp_omit['units'] if u['id'] != 'u-cond-macos-manual']
        for cov in resp_omit['block_coverage']:
            if cov['block_id'] == 'B015':
                cov['unit_ids'] = ['u-cond-offline-cache']
        analysis_omit = pipeline.assemble_document_analysis(bundle, [json.dumps(resp_omit)])
        gate_report = pipeline.validate_analysis_gate(bundle, analysis_omit, run_semantic_validation=True)

        # Even though block_coverage and protected traceability pass, SEMANTIC_FIDELITY catches the omitted B015 clause!
        self.assertEqual(self._check_status(gate_report, 'BLOCK_COVERAGE'), 'passed')
        self.assertEqual(self._check_status(gate_report, 'PROTECTED_TRACEABILITY'), 'passed')
        self.assertEqual(self._check_status(gate_report, 'SEMANTIC_FIDELITY'), 'violated')
        self.assertEqual(gate_report['gate_state'], 'FAIL')

        sem_findings = gate_report['semantic_report']['findings']
        self.assertTrue(any(
            f['error_category'] == 'CRITICAL_OMISSION'
            and f['check_direction'] == 'source_to_analysis'
            and f['field_path'] == '/blocks/6'
            and any('자동 업데이트를 지원하지 않으며' in s['quote'] for s in f['source_spans'])
            for f in sem_findings
        ))

    def test_category_7_relation_distortion_rw001_e_rel_a1_a2_regression(self):
        """Relation distortion: inverted supports direction (RW-001 E-REL-A1/A2) and inverted qualifies direction."""
        resp_rel = copy.deepcopy(self.rw001_resp)
        for u in resp_rel['units']:
            if u['id'] == 'u-install-reqs':
                u['relations'] = []
            if u['id'] == 'u-beginner-open-path':
                u['relations'] = []
            if u['id'] == 'u-pkg-fit-release':
                # Reproduce E-REL-A1 and E-REL-A2-REQUIREMENT / E-REL-A2-USABILITY
                u['relations'] = [
                    {
                        'kind': 'supports',
                        'target_unit_id': 'u-install-reqs',
                        'reason': (
                            'The choice of PKG for this release is justified by the technical installation '
                            'requirements described in u2 (installing the menu bar runtime in Applications, '
                            'bundling Node/cloudflared helpers, running Doctor).'
                        ),
                    },
                    {
                        'kind': 'supports',
                        'target_unit_id': 'u-beginner-open-path',
                        'reason': (
                            'u3 provides the user-experience rationale (a clearer install and open path for beginners) '
                            'that explains why PKG is the better fit in u1.'
                        ),
                    },
                ]
        analysis_rel = pipeline.assemble_document_analysis(self.rw001_bundle, [json.dumps(resp_rel)])
        sem_rel = pipeline.validate_semantic_fidelity(self.rw001_bundle, analysis_rel)
        self.assertEqual(sem_rel['overall_judgment'], 'contradicted')
        rel_paths = {
            f['field_path'] for f in sem_rel['findings'] if f['error_category'] == 'RELATION_DISTORTION'
        }
        self.assertIn('/units/1/relations/0/reason', rel_paths)
        self.assertIn('/units/1/relations/1/reason', rel_paths)

    def test_category_8_assessment_only_distortion_rw001_b2_regression(self):
        """RW-001 E-REQ-B2-EXPOSURE / E-REQ-B2-REASON: statement is faithful, distortion is ONLY in assessment."""
        resp_b2 = copy.deepcopy(self.rw001_resp)
        for u in resp_b2['units']:
            if u['id'] == 'u-install-reqs':
                # Keep statement 100% faithful ("needs to install...")
                u['assessment']['exposure'] = (
                    'Retain in the current note as the concrete technical justification for choosing PKG, '
                    'keeping the embedded facts about what gets installed and executed.'
                )
                u['assessment']['reason'] = (
                    'For a technical collaborator, knowing that the macOS package places the menu bar runtime in '
                    'Applications, bundles Node and cloudflared helpers, and triggers a non-blocking post-install '
                    'Doctor check is essential to understanding why a simple drag-and-drop DMG is insufficient.'
                )
        analysis_b2 = pipeline.assemble_document_analysis(self.rw001_bundle, [json.dumps(resp_b2)])
        gate_b2 = pipeline.validate_analysis_gate(self.rw001_bundle, analysis_b2, run_semantic_validation=True)
        sem_b2 = gate_b2['semantic_report']

        self.assertEqual(sem_b2['overall_judgment'], 'overstated')
        self.assertEqual(self._check_status(gate_b2, 'SEMANTIC_FIDELITY'), 'violated')
        self.assertEqual(gate_b2['gate_state'], 'FAIL')

        # Verify unit statement itself was judged 'supported', while assessment.exposure and assessment.reason failed!
        by_path = {j['field_path']: j for j in sem_b2['item_judgments']}
        self.assertEqual(by_path['/units/2/statement']['semantic_judgment'], 'supported')
        self.assertEqual(by_path['/units/2/assessment/exposure']['semantic_judgment'], 'overstated')
        self.assertEqual(by_path['/units/2/assessment/exposure']['error_category'], 'ASSESSMENT_RATIONALE_DISTORTION')
        self.assertEqual(by_path['/units/2/assessment/reason']['semantic_judgment'], 'overstated')
        self.assertEqual(by_path['/units/2/assessment/reason']['error_category'], 'ASSESSMENT_RATIONALE_DISTORTION')

    # ------------------------------------------------------------------
    # 3. Independent Evaluator Boundary, Code Quote Re-Verification & Self-Approval Rejection
    # ------------------------------------------------------------------
    def test_evaluator_fabricated_quote_and_missing_evidence_downgraded_to_unresolved_review(self):
        """Model evaluator quotes are re-verified against DocumentSnapshot; bad or empty quotes become unresolved."""
        def bad_quote_responder(w_idx, _sw, _prompt, _att):
            resp = pipeline.build_stub_semantic_response_from_audit(
                self.rw001_bundle, self.rw001_analysis, window_index=w_idx
            )
            for ur in resp['unit_reviews']:
                if ur['unit_id'] == 'u-pkg-fit-release':
                    for fj in ur['field_judgments']:
                        if fj['field_path'] == '/units/1/statement':
                            # Fabricated quote not in B003
                            fj['evidence_quotes'] = [
                                {'block_id': 'B003', 'quote': 'Fabricated quote not in source document.', 'occurrence': 0}
                            ]
                if ur['unit_id'] == 'u-install-reqs':
                    for fj in ur['field_judgments']:
                        if fj['field_path'] == '/units/2/statement':
                            # Empty evidence_quotes on a 'supported' claim
                            fj['evidence_quotes'] = []
            return resp

        gate_report = pipeline.validate_analysis_gate(
            self.rw001_bundle,
            self.rw001_analysis,
            semantic_responder=bad_quote_responder,
            run_semantic_validation=True,
        )
        sem_report = gate_report['semantic_report']
        self.assertEqual(sem_report['overall_judgment'], 'unresolved')
        self.assertEqual(self._check_status(gate_report, 'SEMANTIC_FIDELITY'), 'unresolved')
        self.assertEqual(gate_report['gate_state'], 'REVIEW')

        cats_by_path = {f['field_path']: f['error_category'] for f in sem_report['findings']}
        self.assertEqual(cats_by_path.get('/units/1/statement'), 'UNVERIFIED_EVALUATOR_QUOTE')
        self.assertEqual(cats_by_path.get('/units/2/statement'), 'AMBIGUOUS_SOURCE_EVIDENCE')

    def test_evaluator_self_approval_fields_rejected_and_blocked(self):
        """Model evaluator outputting passed=True, delivery_approved=True, or gate_state='PASS' is rejected."""
        for forbidden_payload in (
            {'passed': True},
            {'delivery_approved': True},
            {'gate_state': 'PASS'},
        ):
            def self_approving_responder(w_idx, _sw, _prompt, _att, extra=forbidden_payload):
                resp = pipeline.build_stub_semantic_response_from_audit(
                    self.rw001_bundle, self.rw001_analysis, window_index=w_idx
                )
                resp.update(extra)
                return resp

            gate_report = pipeline.validate_analysis_gate(
                self.rw001_bundle,
                self.rw001_analysis,
                semantic_responder=self_approving_responder,
                run_semantic_validation=True,
            )
            sem_report = gate_report['semantic_report']
            self.assertEqual(sem_report['overall_judgment'], 'contradicted')
            self.assertEqual(self._check_status(gate_report, 'SEMANTIC_FIDELITY'), 'violated')
            self.assertEqual(gate_report['gate_state'], 'FAIL')
            self.assertFalse(gate_report['delivery_approved'])
            self.assertTrue(any(
                f['error_category'] == 'UNAUTHORIZED_EVALUATOR_APPROVAL_CLAIM'
                for f in sem_report['findings']
            ))

    def test_multi_evaluator_judgment_conflict_held_as_unresolved_review(self):
        """Conflicting judgments between two model evaluators produce EVALUATOR_JUDGMENT_CONFLICT -> unresolved."""
        def pass_0(w_idx, _sw, _prompt, _att):
            return pipeline.build_stub_semantic_response_from_audit(
                self.rw001_bundle, self.rw001_analysis, window_index=w_idx
            )

        def pass_1(w_idx, _sw, _prompt, _att):
            resp = pipeline.build_stub_semantic_response_from_audit(
                self.rw001_bundle, self.rw001_analysis, window_index=w_idx
            )
            for ur in resp['unit_reviews']:
                if ur['unit_id'] == 'u-install-reqs':
                    for fj in ur['field_judgments']:
                        if fj['field_path'] == '/units/2/statement':
                            fj['semantic_judgment'] = 'overstated'
                            fj['error_category'] = 'CLAIM_OVERSTATEMENT'
                            fj['rationale'] = 'Second evaluator considers the statement overstated.'
            return resp

        gate_report = pipeline.validate_analysis_gate(
            self.rw001_bundle,
            self.rw001_analysis,
            semantic_responder=[pass_0, pass_1],
            run_semantic_validation=True,
        )
        sem_report = gate_report['semantic_report']
        self.assertEqual(sem_report['overall_judgment'], 'unresolved')
        self.assertEqual(self._check_status(gate_report, 'SEMANTIC_FIDELITY'), 'unresolved')
        self.assertEqual(gate_report['gate_state'], 'REVIEW')
        self.assertTrue(any(
            f['error_category'] == 'EVALUATOR_JUDGMENT_CONFLICT' and f['field_path'] == '/units/2/statement'
            for f in sem_report['findings']
        ))

    def test_multi_window_prompt_budget_and_partial_coverage_tracking(self):
        """Small max_prompt_chars splits semantic review into multiple windows and records unreviewed units if incomplete."""
        tight_budget = 6500
        windows = pipeline.plan_semantic_review_windows(
            self.fd001_bundle, self.fd001_analysis, max_prompt_chars=tight_budget
        )
        self.assertGreater(len(windows), 1)
        for sw in windows:
            self.assertLessEqual(len(sw['prompt_text']), tight_budget)

        # Responder reviews all units in SW001 but omits unit_reviews in subsequent windows (partial review)
        def partial_window_responder(w_idx, _sw, _prompt, _att):
            resp = pipeline.build_stub_semantic_response_from_audit(
                self.fd001_bundle,
                self.fd001_analysis,
                window_index=w_idx,
                max_prompt_chars=tight_budget,
            )
            if w_idx >= 1:
                resp['unit_reviews'] = []
            return resp

        gate_report = pipeline.validate_analysis_gate(
            self.fd001_bundle,
            self.fd001_analysis,
            semantic_responder=partial_window_responder,
            run_semantic_validation=True,
            max_prompt_chars=tight_budget,
        )
        sem_report = gate_report['semantic_report']
        self.assertFalse(sem_report['coverage_summary']['is_complete'])
        self.assertGreater(len(sem_report['coverage_summary']['unreviewed_unit_ids']), 0)
        self.assertEqual(sem_report['overall_judgment'], 'unresolved')
        self.assertEqual(self._check_status(gate_report, 'SEMANTIC_FIDELITY'), 'unresolved')
        self.assertEqual(gate_report['gate_state'], 'REVIEW')
        self.assertTrue(any(
            f['error_category'] == 'INCOMPLETE_SEMANTIC_COVERAGE' for f in sem_report['findings']
        ))

    def test_retry_bound_and_provider_error_redaction_in_semantic_validator(self):
        """Semantic evaluator retries up to max_attempts, records redacted failure history, and holds at REVIEW."""
        calls = {'count': 0}

        def failing_responder(_w_idx, _sw, _prompt, _att):
            calls['count'] += 1
            raise pipeline.ProviderCallError(
                'Semantic evaluator timeout with token sk-secret-9876543210abcdef',
                kind='provider_timeout',
                timed_out=True,
            )

        gate_report = pipeline.validate_analysis_gate(
            self.rw001_bundle,
            self.rw001_analysis,
            semantic_responder=failing_responder,
            run_semantic_validation=True,
            max_semantic_attempts=2,
        )
        self.assertEqual(calls['count'], 2)
        sem_report = gate_report['semantic_report']
        self.assertEqual(sem_report['overall_judgment'], 'unresolved')
        self.assertEqual(self._check_status(gate_report, 'SEMANTIC_FIDELITY'), 'unresolved')
        self.assertEqual(gate_report['gate_state'], 'REVIEW')
        self.assertEqual(len(sem_report['window_records']), 2)
        for att_rec in sem_report['window_records']:
            self.assertEqual(att_rec['status'], 'failed')
            self.assertNotIn('sk-secret-9876543210abcdef', att_rec['error_message'])
            self.assertIn('[REDACTED_TOKEN]', att_rec['error_message'])

    # ------------------------------------------------------------------
    # 4. Tamper Resistance & Upstream Artifact Invalidation
    # ------------------------------------------------------------------
    def test_tampering_with_semantic_report_or_upstream_artifacts_is_rejected(self):
        """Forging semantic_report, recomputing digests, or mutating upstream artifacts cannot bypass the gate."""
        def stub_responder(w_idx, _sw, _prompt, _att):
            return pipeline.build_stub_semantic_response_from_audit(
                self.rw001_bundle, self.rw001_analysis, window_index=w_idx
            )

        gate_report = pipeline.validate_analysis_gate(
            self.rw001_bundle,
            self.rw001_analysis,
            semantic_responder=stub_responder,
            run_semantic_validation=True,
        )
        self.assertTrue(
            pipeline.verify_semantic_report_integrity(
                self.rw001_bundle, self.rw001_analysis, gate_report['semantic_report']
            )['valid']
        )

        # 4A: Mutating DocumentSnapshot invalidates semantic_report
        mutated_bundle = copy.deepcopy(self.rw001_bundle)
        mutated_bundle['document_snapshot']['content'] += '\nExtra sentence.\n'
        mutated_bundle['document_snapshot']['sha256'] = pipeline.digest_text(
            mutated_bundle['document_snapshot']['content']
        )
        self.assertFalse(
            pipeline.verify_semantic_report_integrity(
                mutated_bundle, self.rw001_analysis, gate_report['semantic_report']
            )['valid']
        )
        revalidated_snap = pipeline.validate_analysis_gate(
            mutated_bundle,
            self.rw001_analysis,
            semantic_report=gate_report['semantic_report'],
            run_semantic_validation=True,
        )
        self.assertEqual(revalidated_snap['gate_state'], 'FAIL')

        # 4B: Mutating WritingContract invalidates semantic_report
        mutated_contract_bundle = copy.deepcopy(self.rw001_bundle)
        mutated_contract_bundle['writing_contract']['purpose'] = 'Changed contract purpose'
        self.assertFalse(
            pipeline.verify_semantic_report_integrity(
                mutated_contract_bundle, self.rw001_analysis, gate_report['semantic_report']
            )['valid']
        )

        # 4C: Mutating AnalysisResult invalidates semantic_report
        mutated_analysis = copy.deepcopy(self.rw001_analysis)
        mutated_analysis['units'][1]['statement'] = 'Modified statement after semantic review.'
        self.assertFalse(
            pipeline.verify_semantic_report_integrity(
                self.rw001_bundle, mutated_analysis, gate_report['semantic_report']
            )['valid']
        )

        # 4D: Forging a 'supported' semantic_report with recomputed sha256 on an overstated analysis is caught!
        resp_over = copy.deepcopy(self.rw001_resp)
        for u in resp_over['units']:
            if u['id'] == 'u-install-reqs':
                u['statement'] = (
                    'The macOS package installs a menu bar runtime under Applications, '
                    'bundles Node/cloudflared helpers, and runs a non-blocking post-install Doctor.'
                )
        analysis_over = pipeline.assemble_document_analysis(self.rw001_bundle, [json.dumps(resp_over)])
        real_sem = pipeline.validate_semantic_fidelity(self.rw001_bundle, analysis_over)
        self.assertEqual(real_sem['overall_judgment'], 'overstated')

        forged_sem = copy.deepcopy(real_sem)
        forged_sem['overall_judgment'] = 'supported'
        forged_sem['findings'] = []
        for ij in forged_sem['item_judgments']:
            ij['semantic_judgment'] = 'supported'
            ij['error_category'] = None
        forged_body = {k: v for k, v in forged_sem.items() if k != 'semantic_report_sha256'}
        forged_sem['semantic_report_sha256'] = pipeline.canonical_json_digest(forged_body)

        self.assertFalse(
            pipeline.verify_semantic_report_integrity(self.rw001_bundle, analysis_over, forged_sem)['valid']
        )
        gate_forged = pipeline.validate_analysis_gate(
            self.rw001_bundle, analysis_over, semantic_report=forged_sem, run_semantic_validation=True
        )
        self.assertEqual(self._check_status(gate_forged, 'SEMANTIC_FIDELITY'), 'violated')
        self.assertEqual(gate_forged['gate_state'], 'FAIL')
        self.assertFalse(pipeline.can_advance_to_organization(self.rw001_bundle, analysis_over, gate_forged)['allowed'])

    # ------------------------------------------------------------------
    # 5. ExecutionController End-to-End Flow & Retry on Semantic FAIL
    # ------------------------------------------------------------------
    def test_execution_controller_retries_on_semantic_fail_and_blocks_organization_on_review(self):
        """End-to-end flow: DocumentSnapshot -> AnalysisResult -> Semantic Review -> Validation Gate -> Organization blocked."""
        overstated_resp = copy.deepcopy(self.rw001_resp)
        for u in overstated_resp['units']:
            if u['id'] == 'u-install-reqs':
                u['statement'] = (
                    'The macOS package installs a menu bar runtime under Applications, '
                    'bundles Node/cloudflared helpers, and runs a non-blocking post-install Doctor.'
                )
        faithful_resp = copy.deepcopy(self.rw001_resp)

        extraction_calls = {'count': 0}

        def extraction_responder(_w_idx, _win, _prompt, _att):
            extraction_calls['count'] += 1
            if extraction_calls['count'] == 1:
                return json.dumps(overstated_resp)
            return json.dumps(faithful_resp)

        def semantic_responder(w_idx, sw, _prompt, _att):
            # Dynamically build candidate semantic response for whichever analysis attempt is being evaluated
            current_analysis = pipeline.assemble_document_analysis(
                self.rw001_bundle,
                [json.dumps(overstated_resp if extraction_calls['count'] == 1 else faithful_resp)],
            )
            resp = pipeline.build_stub_semantic_response_from_audit(
                self.rw001_bundle, current_analysis, window_index=w_idx
            )
            resp['analysis_sha256'] = sw['analysis_sha256']
            return resp

        controller = pipeline.ExecutionController(max_attempts=2)
        run_state = controller.run(
            self.rw001_bundle,
            extraction_responder,
            semantic_responder=semantic_responder,
            enable_semantic_validation=True,
            max_semantic_attempts=1,
        )

        # Attempt 1 failed SEMANTIC_FIDELITY ('overstated' -> 'FAIL') and triggered retry of extraction;
        # Attempt 2 succeeded with 'supported' semantic judgment and held at ValidationGate ('REVIEW')!
        self.assertEqual(extraction_calls['count'], 2)
        self.assertEqual(len(run_state['attempt_history']), 2)
        self.assertEqual(run_state['attempt_history'][0]['gate_state'], 'FAIL')
        self.assertEqual(run_state['attempt_history'][1]['gate_state'], 'REVIEW')
        self.assertEqual(run_state['gate_state'], 'REVIEW')
        self.assertEqual(run_state['return_to_stage'], 'human_or_semantic_review')
        self.assertFalse(run_state['next_stage_allowed'])
        self.assertFalse(run_state['next_stage_invoked'])
        self.assertFalse(run_state['delivery_approved'])
        self.assertIsNotNone(run_state['semantic_report'])
        self.assertEqual(run_state['semantic_report']['overall_judgment'], 'supported')

        # Markdown report includes Semantic Fidelity Summary
        md_report = pipeline.render_markdown_report(run_state)
        self.assertIn('## 독립 의미 충실도 검증 결과(semantic_report)', md_report)
        self.assertIn('"overall_judgment": "supported"', md_report)

    # ------------------------------------------------------------------
    # 6. Fixed Evaluation Benchmark (14 Cases: TP, TN, FP, FN, Disagreements)
    # ------------------------------------------------------------------
    def test_fixed_semantic_benchmark_metrics_and_disagreement_tracking(self):
        det_res = eval_cases.evaluate_semantic_benchmark(mode='deterministic_only')
        comb_res = eval_cases.evaluate_semantic_benchmark(mode='combined_stub')

        self.assertEqual(det_res['total_cases'], 14)
        self.assertEqual(
            det_res['metrics'],
            {
                'true_positives': 8,
                'true_negatives': 3,
                'false_positives': 0,
                'false_negatives': 1,
                'unresolved_holds': 1,
            },
        )
        self.assertEqual(
            comb_res['metrics'],
            {
                'true_positives': 9,
                'true_negatives': 3,
                'false_positives': 0,
                'false_negatives': 0,
                'unresolved_holds': 2,
            },
        )
        disagreement_ids = {d['eval_case_id'] for d in comb_res['disagreements']}
        self.assertIn('EVAL-12-BOUNDARY-SUBTLE-SEQUENTIAL-SHIFT-FN', disagreement_ids)
        self.assertIn('EVAL-13-BOUNDARY-CONTRAST-CLAUSE-IN-REASON-FP', disagreement_ids)
        self.assertIn('EVAL-14-INTER-EVALUATOR-CONFLICT-HOLD', disagreement_ids)

    # ------------------------------------------------------------------
    # 7. Defense against Forgery / Concealment of Model-Only Errors
    # ------------------------------------------------------------------
    def test_defense_against_forged_report_omitting_model_only_errors(self):
        """Minimal counterexample: Model finds subtle sequential shift (EVAL-12), attacker strips it and recomputes digest.
        Integrity verifier must detect tampering via raw execution record or reject unverified model reports.
        """
        eval_cases_list = eval_cases.build_semantic_evaluation_cases()
        eval12 = next(c for c in eval_cases_list if c['eval_case_id'] == 'EVAL-12-BOUNDARY-SUBTLE-SEQUENTIAL-SHIFT-FN')
        b12 = eval12['input_bundle']
        a12 = eval12['analysis_result']

        # 1. Deterministic audit alone passes because sequential shift is outside keyword rules
        det_audit = pipeline.run_deterministic_semantic_audit(b12, a12)
        det_non_sup = [it for it in det_audit['item_judgments'] if it['semantic_judgment'] != 'supported']
        self.assertEqual(det_non_sup, [])

        # 2. Legitimate run with model evaluator detects the error
        stub_eval12 = eval_cases.make_stub_model_responder_for_eval_case(eval12)
        real_report = pipeline.validate_semantic_fidelity(
            b12,
            a12,
            semantic_responder=stub_eval12,
        )
        self.assertEqual(real_report['overall_judgment'], 'overstated')
        self.assertEqual(len(real_report['findings']), 1)
        self.assertEqual(real_report['findings'][0]['error_category'], 'CLAIM_OVERSTATEMENT')
        self.assertEqual(real_report['findings'][0]['field_path'], '/units/1/statement')
        self.assertTrue(pipeline.verify_semantic_report_integrity(b12, a12, real_report)['valid'])

        # 3. Forgery Attempt A: Strip finding, set overall_judgment='supported', recompute sha256 (leaving evaluator_records)
        forged_report_a = copy.deepcopy(real_report)
        forged_report_a['overall_judgment'] = 'supported'
        forged_report_a['findings'] = []
        for ij in forged_report_a['item_judgments']:
            if ij['field_path'] == '/units/1/statement':
                ij['semantic_judgment'] = 'supported'
                ij['error_category'] = None
        forged_body_a = {k: v for k, v in forged_report_a.items() if k != 'semantic_report_sha256'}
        forged_report_a['semantic_report_sha256'] = pipeline.canonical_json_digest(forged_body_a)

        # Self-digest passes, but reconstruction from raw execution records reveals the stripped error!
        check_a = pipeline.verify_semantic_report_integrity(b12, a12, forged_report_a)
        self.assertFalse(check_a['valid'])
        self.assertEqual(check_a['code'], 'FORGED_OR_OMITTED_SEMANTIC_FINDINGS')

        # 4. Forgery Attempt B: Strip finding AND delete evaluator_records to conceal raw response
        forged_report_b = copy.deepcopy(forged_report_a)
        del forged_report_b['evaluator_records']
        forged_body_b = {k: v for k, v in forged_report_b.items() if k != 'semantic_report_sha256'}
        forged_report_b['semantic_report_sha256'] = pipeline.canonical_json_digest(forged_body_b)

        # Without trusted execution records, report with model evaluator claims cannot be approved!
        check_b = pipeline.verify_semantic_report_integrity(b12, a12, forged_report_b)
        self.assertFalse(check_b['valid'])
        self.assertEqual(check_b['code'], 'UNVERIFIED_MODEL_EXECUTION_RECORD')

        # 5. Forgery Attempt C: Tamper with raw_response payload in evaluator_records
        forged_report_c = copy.deepcopy(real_report)
        forged_report_c['evaluator_records'][0]['raw_response'] = '{"tampered": true}'
        forged_body_c = {k: v for k, v in forged_report_c.items() if k != 'semantic_report_sha256'}
        forged_report_c['semantic_report_sha256'] = pipeline.canonical_json_digest(forged_body_c)

        check_c = pipeline.verify_semantic_report_integrity(b12, a12, forged_report_c)
        self.assertFalse(check_c['valid'])
        self.assertEqual(check_c['code'], 'SEMANTIC_RESPONSE_DIGEST_MISMATCH')

    # ------------------------------------------------------------------
    # 8. Accurate Semantic Review Coverage Tracking & Partial Omission
    # ------------------------------------------------------------------
    def test_accurate_field_path_coverage_tracking_and_incomplete_coverage_review(self):
        """When model evaluator only reviews statement and omits assessment/elements/relations,
        coverage tracker flags INCOMPLETE_SEMANTIC_COVERAGE and holds at unresolved (REVIEW).
        """
        def partial_fields_responder(w_idx, _sw, _prompt, _att):
            full_resp = pipeline.build_stub_semantic_response_from_audit(
                self.rw001_bundle, self.rw001_analysis, window_index=w_idx
            )
            # Deliberately prune all field judgments except statement
            for ur in full_resp['unit_reviews']:
                ur['field_judgments'] = [
                    fj for fj in ur['field_judgments'] if fj['field_path'].endswith('/statement')
                ]
            return full_resp

        gate_report = pipeline.validate_analysis_gate(
            self.rw001_bundle,
            self.rw001_analysis,
            semantic_responder=partial_fields_responder,
            run_semantic_validation=True,
        )
        sem_report = gate_report['semantic_report']
        cov = sem_report['coverage_summary']

        self.assertFalse(cov['is_complete'])
        self.assertFalse(cov['forward_analysis_to_source_complete'])
        self.assertGreater(cov['unreviewed_field_count'], 0)
        self.assertTrue(any(p.endswith('/assessment/reason') for p in cov['unreviewed_field_paths']))
        self.assertTrue(any(p.endswith('/assessment/exposure') for p in cov['unreviewed_field_paths']))

        # Must record INCOMPLETE_SEMANTIC_COVERAGE finding and hold at unresolved (REVIEW)
        error_cats = {f['error_category'] for f in sem_report['findings']}
        self.assertIn('INCOMPLETE_SEMANTIC_COVERAGE', error_cats)
        self.assertEqual(sem_report['overall_judgment'], 'unresolved')
        self.assertEqual(gate_report['gate_state'], 'REVIEW')
        self.assertFalse(gate_report['delivery_approved'])

    def test_rw001_assessment_distortion_cannot_claim_supported_with_partial_coverage(self):
        """Statement is accurate but assessment.reason escalates to factual package behavior (RW-001).
        If only statement is evaluated, system CANNOT claim supported or complete coverage.
        """
        # Build RW-001 analysis where statement is faithful but assessment.reason overstates
        rw_bundle = self.rw001_bundle
        rw_resp = copy.deepcopy(self.rw001_resp)
        for u in rw_resp['units']:
            if u['id'] == 'u-install-reqs':
                # Statement preserves modality
                u['statement'] = 'The macOS package needs to install a menu bar runtime and bundle Node/cloudflared helpers.'
                # But assessment.reason escalates to verified package behavior!
                u['assessment']['reason'] = (
                    'Knowing that the macOS package actually installs a menu bar runtime under Applications '
                    'is essential factual package behavior for downstream configuration.'
                )
        rw_analysis = pipeline.assemble_document_analysis(rw_bundle, [json.dumps(rw_resp)])

        # If a responder only evaluates statement (marking it supported):
        def statement_only_responder(w_idx, _sw, _prompt, _att):
            resp = pipeline.build_stub_semantic_response_from_audit(rw_bundle, rw_analysis, window_index=w_idx)
            for ur in resp['unit_reviews']:
                ur['field_judgments'] = [
                    fj for fj in ur['field_judgments'] if fj['field_path'].endswith('/statement')
                ]
            return resp

        # Test model-only partial review (without deterministic auditor overriding the omitted field):
        partial_model_only = pipeline.validate_semantic_fidelity(
            rw_bundle,
            rw_analysis,
            semantic_responder=statement_only_responder,
            combine_with_deterministic_audit=False,
            max_prompt_chars=4000,
        )
        self.assertFalse(partial_model_only['coverage_summary']['is_complete'])
        self.assertNotEqual(partial_model_only['overall_judgment'], 'supported')
        self.assertIn('INCOMPLETE_SEMANTIC_COVERAGE', {f['error_category'] for f in partial_model_only['findings']})

        # When combined with deterministic audit, deterministic audit catches the distortion in assessment.reason
        # AND coverage tracker flags the incomplete model coverage:
        partial_gate = pipeline.validate_analysis_gate(
            rw_bundle,
            rw_analysis,
            semantic_responder=statement_only_responder,
            run_semantic_validation=True,
        )
        partial_sem = partial_gate['semantic_report']
        self.assertFalse(partial_sem['coverage_summary']['is_complete'])
        self.assertEqual(partial_sem['overall_judgment'], 'overstated')
        self.assertEqual(partial_gate['gate_state'], 'FAIL')
        finding_cats = {f['error_category'] for f in partial_sem['findings']}
        self.assertIn('ASSESSMENT_RATIONALE_DISTORTION', finding_cats)
        self.assertIn('INCOMPLETE_SEMANTIC_COVERAGE', finding_cats)

    # ------------------------------------------------------------------
    # 9. Concessive Contrast Clause (EVAL-13 Fix & True Negative Preservation)
    # ------------------------------------------------------------------
    def test_concessive_contrast_clause_distinction(self):
        """Concessive contrast clauses in explanations must not be falsely flagged as polarity reversals,
        while definite polarity reversals must still be caught (no false negatives).
        """
        source = 'macOS 패키지는 초기 실험 빌드이므로 자동 업데이트를 지원하지 않으며 수동으로 재설치해야 한다.'

        # 1. Normal concessive contrast explanation: contrasts general case while preserving negative fact
        faithful_explanation = (
            '일반적인 정식 패키지가 자동 업데이트를 지원한다 하더라도 이 macOS 초기 실험 빌드는 지원하지 않으므로 수동 재설치가 필요하다.'
        )
        check_faithful = pipeline._semantic_validator._check_polarity_reversal(source, faithful_explanation)
        self.assertIsNone(check_faithful)

        # 2. Definite polarity reversal: directly claims auto-update is supported
        contradicted_claim = 'macOS 패키지는 자동 업데이트를 지원하며 최신 런타임을 자동으로 유지한다.'
        check_contradicted = pipeline._semantic_validator._check_polarity_reversal(source, contradicted_claim)
        self.assertIsNotNone(check_contradicted)
        self.assertEqual(check_contradicted[0], 'contradicted')
        self.assertEqual(check_contradicted[1], 'POLARITY_REVERSAL')

        # 3. Ambiguous hypothetical framing downgrades to unresolved rather than hard contradicted
        hypothetical_claim = '자동 업데이트를 지원한다고 가정할 때의 동작 방식을 고려한다.'
        check_hypothetical = pipeline._semantic_validator._check_polarity_reversal(source, hypothetical_claim)
        self.assertIsNotNone(check_hypothetical)
        self.assertEqual(check_hypothetical[0], 'unresolved')
        self.assertEqual(check_hypothetical[1], 'AMBIGUOUS_SOURCE_EVIDENCE')

    # ------------------------------------------------------------------
    # 10. Required Field Coverage, Targeted Retry & Schema Stabilization
    # ------------------------------------------------------------------
    def test_model_omits_preservation_field_and_recovers_via_targeted_retry(self):
        """When a model evaluator omits /units/0/assessment/preservation on first response,
        the validator prompts specifically for the missing field, merges the response without
        shrinking coverage or overwriting prior valid judgments, and achieves full coverage.
        """
        initial_called = []
        retry_called = []

        def omitting_responder(w_idx, sw, prompt_text, att):
            # Check if this is a missing-fields retry prompt
            if 'missing_field_paths' in prompt_text or 'FOLLOW-UP SEMANTIC REVIEW' in prompt_text:
                retry_called.append((w_idx, att))
                # Provide judgment ONLY for the missing preservation field
                return {
                    'input_sha256': sw.get('input_sha256') or pipeline.canonical_json_digest(self.rw001_bundle),
                    'snapshot_id': self.rw001_bundle['document_snapshot']['snapshot_id'],
                    'snapshot_sha256': self.rw001_bundle['document_snapshot']['sha256'],
                    'analysis_sha256': self.rw001_analysis['analysis_sha256'],
                    'semantic_window_id': sw['semantic_window_id'],
                    'unit_reviews': [
                        {
                            'unit_id': 'u-rw-heading',
                            'field_judgments': [
                                {
                                    'field_path': '/units/0/assessment/preservation',
                                    'semantic_judgment': 'supported',
                                    'error_category': None,
                                    'evidence_quotes': [
                                        {'block_id': 'B001', 'quote': '### Why PKG Instead Of DMG?', 'occurrence': 0}
                                    ],
                                    'rationale': 'Preservation choice retain_current is faithful to document heading.',
                                }
                            ],
                        }
                    ],
                    'block_omission_reviews': [],
                }

            initial_called.append((w_idx, att))
            base_resp = pipeline.build_stub_semantic_response_from_audit(
                self.rw001_bundle, self.rw001_analysis, window_index=w_idx
            )
            # Omit /units/0/assessment/preservation
            for ur in base_resp['unit_reviews']:
                ur['field_judgments'] = [
                    fj for fj in ur['field_judgments']
                    if fj['field_path'] != '/units/0/assessment/preservation'
                ]
            return base_resp

        report = pipeline.validate_semantic_fidelity(
            self.rw001_bundle,
            self.rw001_analysis,
            semantic_responder=omitting_responder,
            combine_with_deterministic_audit=False,
            max_attempts=2,
        )
        self.assertTrue(len(retry_called) > 0, 'Targeted missing-field retry must be called')
        self.assertTrue(report['coverage_summary']['is_complete'])
        self.assertEqual(report['coverage_summary']['unreviewed_field_paths'], [])
        self.assertEqual(report['overall_judgment'], 'supported')

    def test_model_omits_fields_and_exhausts_retries_leaves_incomplete_coverage_review(self):
        """When a model evaluator omits a required field and still omits it on retry,
        it is flagged as INCOMPLETE_SEMANTIC_COVERAGE and held as unresolved (REVIEW).
        """
        def persistent_omitting_responder(w_idx, sw, prompt_text, att):
            base_resp = pipeline.build_stub_semantic_response_from_audit(
                self.rw001_bundle, self.rw001_analysis, window_index=w_idx
            )
            for ur in base_resp['unit_reviews']:
                ur['field_judgments'] = [
                    fj for fj in ur['field_judgments']
                    if fj['field_path'] != '/units/0/assessment/preservation'
                ]
            return base_resp

        report = pipeline.validate_semantic_fidelity(
            self.rw001_bundle,
            self.rw001_analysis,
            semantic_responder=persistent_omitting_responder,
            combine_with_deterministic_audit=False,
            max_attempts=2,
        )
        self.assertFalse(report['coverage_summary']['is_complete'])
        self.assertIn('/units/0/assessment/preservation', report['coverage_summary']['unreviewed_field_paths'])
        self.assertEqual(report['overall_judgment'], 'unresolved')
        incomplete_findings = [f for f in report['findings'] if f['error_category'] == 'INCOMPLETE_SEMANTIC_COVERAGE']
        self.assertTrue(len(incomplete_findings) > 0)

    def test_error_category_alias_normalization_and_unmapped_category_handling(self):
        """Error category aliases ('overstatement') are normalized to standard categories ('CLAIM_OVERSTATEMENT').
        Unrecognized categories are treated as schema parse errors (retryable) rather than confirmed document failures.
        """
        # 1. Alias normalization
        norm = pipeline._semantic_validator.normalize_semantic_error_category('overstatement')
        self.assertEqual(norm, 'CLAIM_OVERSTATEMENT')
        self.assertEqual(
            pipeline._semantic_validator.normalize_semantic_error_category('polarity_reversal'),
            'POLARITY_REVERSAL',
        )

        def alias_responder(w_idx, _sw, _prompt, _att):
            resp = pipeline.build_stub_semantic_response_from_audit(
                self.rw001_bundle, self.rw001_analysis, window_index=w_idx
            )
            for ur in resp['unit_reviews']:
                if ur['unit_id'] == 'u-install-reqs':
                    for fj in ur['field_judgments']:
                        if fj['field_path'] == '/units/2/statement':
                            fj['semantic_judgment'] = 'overstated'
                            fj['error_category'] = 'overstatement'  # alias!
            return resp

        report = pipeline.validate_semantic_fidelity(
            self.rw001_bundle,
            self.rw001_analysis,
            semantic_responder=alias_responder,
            combine_with_deterministic_audit=False,
        )
        self.assertEqual(report['overall_judgment'], 'overstated')
        overstated_findings = [f for f in report['findings'] if f['error_category'] == 'CLAIM_OVERSTATEMENT']
        self.assertTrue(len(overstated_findings) > 0)

    # ------------------------------------------------------------------
    # 11. Trust Boundary Enforcement (Evidence vs Report Discrepancy & Tampering)
    # ------------------------------------------------------------------
    def test_tampering_both_report_and_embedded_records_rejected_against_trusted_evidence(self):
        """Counterexample: An attacker manipulates BOTH the semantic report and its embedded evaluator_records
        to remove a model-detected error.
        - When verified against gate's trusted execution evidence, it is rejected with DISCREPANT_EXECUTION_RECORD.
        - When an external report is presented without trusted execution evidence, it is held at UNVERIFIED_MODEL_EXECUTION_RECORD.
        """
        cases = eval_cases.build_semantic_evaluation_cases()
        eval12 = next(c for c in cases if c['eval_case_id'] == 'EVAL-12-BOUNDARY-SUBTLE-SEQUENTIAL-SHIFT-FN')
        b12, a12 = eval12['input_bundle'], eval12['analysis_result']
        stub_eval12 = eval_cases.make_stub_model_responder_for_eval_case(eval12)

        # 1. Legitimate execution produces report and trusted evidence
        legit_report, trusted_evidence = pipeline.validate_semantic_fidelity_with_evidence(
            b12,
            a12,
            semantic_responder=stub_eval12,
        )
        self.assertEqual(legit_report['overall_judgment'], 'overstated')

        # Gate verification with trusted evidence succeeds in identifying the error and passing integrity
        integ_legit = pipeline.verify_semantic_report_integrity(
            b12, a12, legit_report, trusted_execution_evidence=trusted_evidence
        )
        self.assertTrue(integ_legit['valid'])

        # 2. Attacker forges BOTH report AND embedded evaluator_records
        forged_report = copy.deepcopy(legit_report)
        forged_report['overall_judgment'] = 'supported'
        forged_report['findings'] = []
        for ij in forged_report['item_judgments']:
            if ij['field_path'] == '/units/1/statement':
                ij['semantic_judgment'] = 'supported'
                ij['error_category'] = None

        # Attacker also tampers raw_response inside evaluator_records to match forged claims
        if 'evaluator_records' in forged_report:
            for rec in forged_report['evaluator_records']:
                rec_json = json.loads(rec['raw_response'])
                for ur in rec_json.get('unit_reviews', []):
                    for fj in ur.get('field_judgments', []):
                        if fj.get('field_path') == '/units/1/statement':
                            fj['semantic_judgment'] = 'supported'
                            fj['error_category'] = None
                tampered_bytes = json.dumps(rec_json, ensure_ascii=False).encode('utf-8')
                rec['raw_response'] = tampered_bytes.decode('utf-8')
                rec['response_sha256'] = pipeline.digest_bytes(tampered_bytes)

        forged_body = {k: v for k, v in forged_report.items() if k != 'semantic_report_sha256'}
        forged_report['semantic_report_sha256'] = pipeline.canonical_json_digest(forged_body)

        # A: Verifying against gate's trusted execution evidence catches discrepancy!
        integ_check = pipeline.verify_semantic_report_integrity(
            b12, a12, forged_report, trusted_execution_evidence=trusted_evidence
        )
        self.assertFalse(integ_check['valid'])
        self.assertEqual(integ_check['code'], 'DISCREPANT_EXECUTION_RECORD')

        # B: Verifying without trusted execution evidence refuses to trust embedded records!
        integ_no_evidence = pipeline.verify_semantic_report_integrity(
            b12, a12, forged_report, trusted_execution_evidence=None
        )
        self.assertFalse(integ_no_evidence['valid'])
        self.assertEqual(integ_no_evidence['code'], 'UNVERIFIED_MODEL_EXECUTION_RECORD')

    def test_corrupted_trusted_execution_record_rejected(self):
        """When trusted execution evidence has mismatched artifact binding or corrupted digests,
        verification rejects with CORRUPTED_EXECUTION_RECORD.
        """
        cases = eval_cases.build_semantic_evaluation_cases()
        eval12 = next(c for c in cases if c['eval_case_id'] == 'EVAL-12-BOUNDARY-SUBTLE-SEQUENTIAL-SHIFT-FN')
        b12, a12 = eval12['input_bundle'], eval12['analysis_result']
        stub_eval12 = eval_cases.make_stub_model_responder_for_eval_case(eval12)

        legit_report, trusted_evidence = pipeline.validate_semantic_fidelity_with_evidence(
            b12,
            a12,
            semantic_responder=stub_eval12,
        )

        corrupted_evidence = copy.deepcopy(trusted_evidence)
        corrupted_evidence['input_sha256'] = '0' * 64

        integ_check = pipeline.verify_semantic_report_integrity(
            b12, a12, legit_report, trusted_execution_evidence=corrupted_evidence
        )
        self.assertFalse(integ_check['valid'])
        self.assertEqual(integ_check['code'], 'CORRUPTED_EXECUTION_RECORD')

    def test_multi_evaluator_live_conflict_protocol_holds_at_review(self):
        """When two independent evaluators conflict on a judgment, the validator records
        EVALUATOR_JUDGMENT_CONFLICT and holds as unresolved (REVIEW).
        """
        cases = eval_cases.build_semantic_evaluation_cases()
        eval14 = next(c for c in cases if c['eval_case_id'] == 'EVAL-14-INTER-EVALUATOR-CONFLICT-HOLD')
        b14, a14 = eval14['input_bundle'], eval14['analysis_result']
        responders = eval_cases.make_stub_model_responder_for_eval_case(eval14)

        report = pipeline.validate_semantic_fidelity(
            b14,
            a14,
            semantic_responder=responders,
            combine_with_deterministic_audit=False,
        )
        self.assertEqual(report['overall_judgment'], 'unresolved')
        finding_cats = {f['error_category'] for f in report['findings']}
        self.assertIn('EVALUATOR_JUDGMENT_CONFLICT', finding_cats)


if __name__ == '__main__':
    unittest.main()
