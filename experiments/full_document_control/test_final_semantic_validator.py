"""Whole-output semantics, complete-context review and untrusted receipt boundaries."""
import copy
import json
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import expression
import integration
import organization
import pipeline
import reconstruction
import final_semantic_validator as semantic
import test_integration as fixtures
from test_integration import contract


def supported(request):
    """Synthetic callback, never an actual LLM evaluation."""
    refs = request['snapshot_refs']
    evidence = []
    for side in ('source', 'output'):
        for snap in request[side + '_snapshots']:
            if snap['content']:
                evidence.append({'side': side, 'document_id': snap['document_id'],
                    'snapshot_sha256': snap['sha256'], 'start': 0, 'end': len(snap['content']), 'quote': snap['content']})
    return {'request_sha256': request['request_sha256'], 'reviews': [
        {'check_id': check, 'judgment': 'supported', 'reason': 'Synthetic full-context review',
         'reviewed_refs': copy.deepcopy(refs), 'evidence': copy.deepcopy(evidence)}
        for check in request['required_checks']]}


class FinalSemanticTests(unittest.TestCase):
    def setup_text(self, text):
        self.bundle = integration.markdown_bundle(text, contract())
        self.analysis = integration.analyze_source(self.bundle)
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.preview = expression.generate_revision_result(self.bundle, self.analysis, self.org)
        self.result = reconstruction.reconstruct_documents(self.bundle, self.analysis, self.org, self.preview)
        self.destinations = []

    def setUp(self):
        self.setup_text('# 안내\n\n제한 시간은 30초다.\n\n자동 업데이트를 지원하지 않음.\n\n캐시가 있을 때만 실행 가능하다.\n\n주의: 실행 전에 백업해야 한다.\n')

    def validate(self, **kwargs):
        return semantic.validate_final_semantics(self.bundle, self.analysis, self.org, self.preview,
            self.result, destination_snapshots=self.destinations, **kwargs)

    def mutate(self, before, after):
        snap = self.result['output_snapshots'][0]
        snap['content'] = snap['content'].replace(before, after)
        snap['sha256'] = pipeline.digest_text(snap['content'])
        # Keep the forged ledger physically aligned, so lexical checks see the
        # intended pair rather than a stale slice into the next paragraph.
        cursor = 0
        for row in self.result['block_ledger']:
            if row.get('alias'):
                continue
            row['text'] = row['text'].replace(before, after)
            row['output_start'], row['output_end'] = cursor, cursor + len(row['text'])
            cursor = row['output_end']
        expression.seal(self.result, 'revision_sha256')

    def test_default_is_unresolved_with_complete_snapshot_refs(self):
        report = self.validate()
        self.assertEqual(report['overall_judgment'], 'unresolved')
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertEqual(len(report['snapshot_refs']), 2)
        self.assertFalse(report['coverage']['complete'])
        self.assertFalse(report['delivery_approved'])

    def test_quantity_and_unit_change_confirmed(self):
        self.mutate('30초', '30분')
        report = self.validate(reviewer=supported)
        self.assertEqual(report['checks']['QUANTITY_SCOPE']['status'], 'violated')
        self.assertEqual(report['gate_state'], 'FAIL')
        self.assertTrue(report['checks']['QUANTITY_SCOPE']['evidence'])

    def test_polarity_flip_confirmed(self):
        self.mutate('지원하지 않음', '지원함')
        self.assertEqual(self.validate()['checks']['POLARITY_CONDITIONS']['status'], 'violated')

    def test_condition_to_always_confirmed(self):
        self.mutate('캐시가 있을 때만 실행 가능하다.', '항상 실행 가능하다.')
        report = self.validate()
        self.assertEqual(report['checks']['POLARITY_CONDITIONS']['status'], 'violated')

    def test_omission_and_addition_do_not_become_supported(self):
        for before, after in [('주의: 실행 전에 백업해야 한다.', ''),
                              ('제한 시간은 30초다.', '제한 시간은 30초다. SOC 2 인증 및 성능 10배 향상을 보장한다.')]:
            with self.subTest(after=after):
                self.setUp()
                self.mutate(before, after)
                report = self.validate()
                self.assertNotEqual(report['overall_judgment'], 'supported')
                audit = semantic.validate_final_audit(self.bundle, self.analysis, self.org, self.preview, self.result)
                self.assertEqual(audit['gate_state'], 'FAIL')

    def test_supported_never_grants_final_approval(self):
        report = self.validate(reviewer=supported)
        self.assertEqual(report['overall_judgment'], 'supported')
        self.assertTrue(report['coverage']['complete'])
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertFalse(report['stage_transition_allowed'])
        self.assertTrue(semantic.verify_final_semantic_report(self.bundle, self.analysis, self.org,
            self.preview, self.result, report)['valid'])

    def test_partial_or_missing_check_is_unresolved(self):
        for change in ('check', 'refs', 'quote', 'judgment', 'binding', 'duplicate'):
            def partial(request):
                response = supported(request)
                if change == 'check': response['reviews'].pop()
                if change == 'refs': response['reviews'][0]['reviewed_refs'].pop()
                if change == 'quote': response['reviews'][0]['evidence'][0]['quote'] = 'invented'
                if change == 'judgment': response['reviews'][0]['judgment'] = 'PASS'
                if change == 'binding': response['request_sha256'] = 'old'
                if change == 'duplicate': response['reviews'].append(response['reviews'][0])
                return response
            with self.subTest(change=change):
                report = self.validate(reviewer=partial)
                self.assertFalse(report['coverage']['complete'])
                self.assertNotEqual(report['overall_judgment'], 'supported')

    def test_model_failure_timeout_and_budget(self):
        def fail(request): raise RuntimeError('secret provider failure')
        def slow(request): time.sleep(.05); return supported(request)
        for kwargs, state in [({'reviewer': fail}, 'error'),
                              ({'reviewer': slow, 'timeout_seconds': .001}, 'timeout'),
                              ({'reviewer': supported, 'max_review_chars': 10}, 'budget_exceeded')]:
            with self.subTest(state=state):
                report = self.validate(**kwargs)
                self.assertEqual(report['execution']['state'], state)
                self.assertFalse(report['coverage']['complete'])
                self.assertEqual(report['gate_state'], 'REVIEW')
                self.assertNotIn('secret provider', json.dumps(report))

    def test_receipt_rejects_other_document_version_contract_or_rehash(self):
        report = self.validate(reviewer=supported)
        def verified(candidate=report):
            return semantic.verify_final_semantic_report(self.bundle, self.analysis, self.org,
                self.preview, self.result, candidate)['valid']
        forged = copy.deepcopy(report)
        forged['delivery_approved'] = True
        expression.seal(forged, 'report_sha256')
        self.assertFalse(verified(forged))
        for artifact, key in [(self.bundle['document_snapshot'], 'version'),
                              (self.bundle['document_snapshot'], 'document_id'),
                              (self.bundle['writing_contract'], 'version'), (self.result, 'revision_sha256')]:
            old = artifact[key]
            artifact[key] = 'different'
            self.assertFalse(verified())
            artifact[key] = old
        self.assertTrue(verified())

    def test_model_approval_claim_is_violation(self):
        def forged(request):
            response = supported(request)
            response['meta'] = {'delivery_approved': True}
            return response
        self.assertEqual(self.validate(reviewer=forged)['gate_state'], 'FAIL')

    def test_equivalent_register_and_reorder_not_violations(self):
        self.bundle['writing_contract']['register'] = '합니다체'
        self.analysis = integration.analyze_source(self.bundle)
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        units = self.analysis['units']
        plc = next(p for p in self.org['placements'] if p['unit_id'] == units[-1]['id'])
        plc['targets'][0].update(anchor_unit_id=units[1]['id'], anchor_relative_position='before')
        expression.seal(self.org, 'plan_sha256')
        self.preview = expression.generate_revision_result(self.bundle, self.analysis, self.org)
        self.result = reconstruction.reconstruct_documents(self.bundle, self.analysis, self.org, self.preview)
        self.assertEqual(self.validate(reviewer=supported)['overall_judgment'], 'supported')

    def test_pipeline_contains_structural_and_semantic_audit(self):
        outcome = integration.run_pipeline(self.bundle, final_semantic_reviewer=supported)
        self.assertEqual(outcome['final_semantic_report']['overall_judgment'], 'supported')
        self.assertEqual(outcome['final_report']['semantic_fidelity'], 'not_run')
        self.assertEqual(outcome['final_audit']['gate_state'], 'REVIEW')
        self.assertFalse(outcome['delivery_approved'])

    def test_move_reviews_all_original_destination_and_outputs(self):
        fixture = fixtures.ReconstructionTests()
        fixture.setUp()
        fixture.setup_move()
        self.bundle, self.analysis, self.org, self.preview = fixture.bundle, fixture.analysis, fixture.org, fixture.preview
        self.destinations = fixture.snaps
        self.result = fixture.candidate()
        def review(request):
            self.assertEqual(len(request['source_snapshots']), 2)
            self.assertEqual(len(request['output_snapshots']), 2)
            self.assertIn('기존 문서 내용', request['source_snapshots'][1]['content'])
            return supported(request)
        self.assertEqual(self.validate(reviewer=review)['overall_judgment'], 'supported')
        # Retain relation-linked condition at the source, detach the moved claim.
        condition = next(t for t in self.result['trace'] if '캐시' in t['output_spans'][0]['quote'])
        condition['output_spans'][0]['document_id'] = self.bundle['document_snapshot']['document_id']
        self.assertEqual(self.validate()['checks']['MOVE_CONSOLIDATION']['status'], 'violated')

    def test_structural_fail_cannot_be_overridden(self):
        self.mutate('30초', '30분')
        audit = semantic.validate_final_audit(self.bundle, self.analysis, self.org, self.preview,
            self.result, reviewer=supported)
        self.assertEqual(audit['gate_state'], 'FAIL')
        self.assertFalse(audit['delivery_approved'])

    def test_malformed_model_data_is_review_not_a_document_violation(self):
        for response in [None, [], {'reviews': []}, {'request_sha256': 'unused', 'reviews': [None]}]:
            with self.subTest(response=response):
                report = self.validate(reviewer=lambda request: response)
                self.assertEqual(report['gate_state'], 'REVIEW')
                self.assertFalse(report['coverage']['complete'])
        def unhashable(request):
            response = supported(request)
            response['reviews'][0]['check_id'] = []
            return response
        self.assertEqual(self.validate(reviewer=unhashable)['gate_state'], 'REVIEW')

    def test_every_document_requires_valid_model_citations_not_just_claimed_refs(self):
        fixture = fixtures.ReconstructionTests()
        fixture.setUp()
        fixture.setup_move()
        self.bundle, self.analysis, self.org, self.preview = fixture.bundle, fixture.analysis, fixture.org, fixture.preview
        self.destinations, self.result = fixture.snaps, fixture.candidate()
        def missing_destination(request):
            response = supported(request)
            for review in response['reviews']:
                review['evidence'] = [span for span in review['evidence'] if span['document_id'] != 'doc-dest']
            return response
        report = self.validate(reviewer=missing_destination)
        self.assertEqual(report['overall_judgment'], 'unresolved')
        self.assertFalse(report['coverage']['complete'])

    def test_model_contradiction_has_real_source_and_output_witnesses(self):
        self.setup_text('# 안내\n\n로컬 실행을 지원한다.\n\n로컬 실행을 지원하지 않는다.\n')
        def contradiction(request):
            response = supported(request)
            review = next(r for r in response['reviews'] if r['check_id'] == 'CONTRADICTIONS')
            review.update(judgment='contradicted', reason='Same local execution claim has opposing polarity')
            return response
        report = self.validate(reviewer=contradiction)
        self.assertEqual(report['checks']['CONTRADICTIONS']['status'], 'violated')
        self.assertEqual(report['gate_state'], 'FAIL')

    def test_json_response_and_forged_location_rejection(self):
        self.assertEqual(self.validate(reviewer=lambda r: json.dumps(supported(r)))['overall_judgment'], 'supported')
        for key, value in [('document_id', 'other'), ('snapshot_sha256', 'old'), ('start', True), ('end', 999999)]:
            def forged(request):
                response = supported(request)
                response['reviews'][0]['evidence'][0][key] = value
                return response
            with self.subTest(key=key):
                self.assertEqual(self.validate(reviewer=forged)['overall_judgment'], 'unresolved')

    def test_combined_audit_and_receipt_tampering(self):
        audit = pipeline.validate_final_output(self.bundle, self.analysis, self.org, self.preview,
                                              self.result, reviewer=supported)
        self.assertTrue(pipeline.verify_final_output_report(self.bundle, self.analysis, self.org,
            self.preview, self.result, audit)['valid'])
        for field in ('gate_state', 'delivery_approved', 'stage_transition_allowed'):
            forged = copy.deepcopy(audit)
            forged[field] = 'PASS' if field == 'gate_state' else True
            expression.seal(forged, 'report_sha256')
            self.assertFalse(pipeline.verify_final_output_report(self.bundle, self.analysis, self.org,
                self.preview, self.result, forged)['valid'])
        forged = copy.deepcopy(audit)
        forged['semantic_report']['checks'].pop('CONTRADICTIONS')
        expression.seal(forged['semantic_report'], 'report_sha256')
        expression.seal(forged, 'report_sha256')
        self.assertFalse(pipeline.verify_final_output_report(self.bundle, self.analysis, self.org,
            self.preview, self.result, forged)['valid'])

    def test_version_change_witness(self):
        self.setup_text('# 사양\n\n버전 v1.2는 제한 시간 30초를 사용한다.\n')
        self.mutate('v1.2', 'v1.3')
        self.assertEqual(self.validate()['checks']['QUANTITY_SCOPE']['status'], 'violated')

    def test_consolidation_attribution_loss_and_new_security_claim_fail_audit(self):
        for text, before, after in [
            ('# 결과\n\n팀 A에 따르면 지연 시간은 30초다.\n', '팀 A에 따르면 ', ''),
            ('# 결과\n\n보안 검토가 필요하다.\n', '보안 검토가 필요하다.', 'SOC 2 보안 인증을 획득했다.')]:
            with self.subTest(after=after):
                self.setup_text(text)
                self.mutate(before, after)
                audit = semantic.validate_final_audit(self.bundle, self.analysis, self.org,
                    self.preview, self.result, reviewer=supported)
                self.assertEqual(audit['gate_state'], 'FAIL')

    def test_current_body_change_without_self_digest_update_invalidates_receipt(self):
        report = self.validate(reviewer=supported)
        self.org['placements'][0]['action'] = 'MOVE'
        self.assertFalse(semantic.verify_final_semantic_report(self.bundle, self.analysis, self.org,
            self.preview, self.result, report)['valid'])

    def test_preview_is_not_reviewed_as_full_output(self):
        self.result.update(delivery_state='preview', output_snapshots=[])
        expression.seal(self.result, 'revision_sha256')
        calls = []
        report = self.validate(reviewer=lambda r: calls.append(r))
        self.assertFalse(calls)
        self.assertFalse(report['coverage']['complete'])
        self.assertEqual(report['overall_judgment'], 'unresolved')

    def test_equal_duration_conversion_is_not_confirmed_violation(self):
        self.assertEqual(semantic._literal_tokens('60초'), semantic._literal_tokens('1분'))
        self.assertEqual(semantic._literal_tokens('1시간'), semantic._literal_tokens('60 minutes'))
        self.assertNotEqual(semantic._literal_tokens('30초'), semantic._literal_tokens('30분'))

    def test_actual_alias_cannot_lose_attribution(self):
        self.setup_text('# 결과\n\n팀 A에 따르면 지연 시간은 30초다.\n\n팀 A에 따르면 지연 시간은 30초다.\n')
        ids = [u['id'] for u in self.analysis['units'][1:]]
        self.org = organization.generate_organization_plan(self.bundle, self.analysis,
            consolidation_candidates=[{'id': 'cg', 'member_unit_ids': ids,
                                       'equivalence_basis': 'Exact attributed duplicates'}])
        self.preview = expression.generate_revision_result(self.bundle, self.analysis, self.org)
        self.result = reconstruction.reconstruct_documents(self.bundle, self.analysis, self.org, self.preview)
        self.assertTrue(any(r.get('alias') for r in self.result['block_ledger']))
        self.assertEqual(self.validate(reviewer=supported)['overall_judgment'], 'supported')
        self.mutate('팀 A에 따르면 ', '')
        self.assertNotIn('팀 A', self.result['output_snapshots'][0]['content'])
        self.assertIn('30초', self.result['output_snapshots'][0]['content'])
        self.assertEqual(self.validate(reviewer=supported)['gate_state'], 'FAIL')

    def test_malformed_nested_model_fields_remain_unresolved(self):
        for field in ('judgment', 'side', 'document_id'):
            def malformed(request):
                response = supported(request)
                review = response['reviews'][0]
                if field == 'judgment': review[field] = []
                else: review['evidence'][0][field] = []
                return response
            with self.subTest(field=field):
                report = self.validate(reviewer=malformed)
                self.assertEqual(report['gate_state'], 'REVIEW')
                self.assertFalse(report['coverage']['complete'])

    def test_equivalent_multi_sentence_negation_is_not_literal_reversal(self):
        self.setup_text('# 설명\n\n아래는 기능 설명이다. 자동 업데이트를 지원하지 않음.\n')
        self.mutate('자동 업데이트를 지원하지 않음.', '자동 업데이트는 미지원이다.')
        row = next(r for r in self.result['block_ledger'] if '자동 업데이트' in r['text'])
        row['text'] = row['text'].replace('자동 업데이트를 지원하지 않음.', '자동 업데이트는 미지원이다.')
        row['output_end'] = row['output_start'] + len(row['text'])
        expression.seal(self.result, 'revision_sha256')
        self.assertNotEqual(self.validate()['checks']['POLARITY_CONDITIONS']['status'], 'violated')

    def test_condition_preserving_negated_explanation_not_expansion(self):
        self.mutate('캐시가 있을 때만 실행 가능하다.',
                    '항상 실행 가능하다는 뜻은 아니다. 캐시가 있을 때만 실행 가능하다.')
        self.assertNotEqual(self.validate()['checks']['POLARITY_CONDITIONS']['status'], 'violated')

    def test_literal_comparisons_and_unresolved_reasons_are_inspectable(self):
        report = self.validate()
        self.assertTrue(report['deterministic_audit']['literal_pairs'])
        pair = report['deterministic_audit']['literal_pairs'][0]
        self.assertTrue(pair['literal_text_equal'])
        self.assertEqual(pair['source']['quote'], pair['output']['quote'])
        self.assertTrue(all(check['unresolved_reason'] for check in report['checks'].values()))

    def test_inputs_changed_during_callback_cannot_claim_matching_evidence(self):
        def changing(request):
            self.bundle['writing_contract']['purpose'] = 'Changed during review'
            return supported(request)
        report = self.validate(reviewer=changing)
        self.assertFalse(report['execution_evidence_matches_current_inputs'])
        self.assertEqual(report['gate_state'], 'FAIL')
        self.assertFalse(report['coverage']['complete'])

    def test_values_cannot_be_swapped_between_unchanged_targets(self):
        for before, after in [
            ('A의 제한은 30초이고 B의 제한은 60초다.', 'A의 제한은 60초이고 B의 제한은 30초다.'),
            ('A는 v1.2이고 B는 v1.3이다.', 'A는 v1.3이고 B는 v1.2이다.')]:
            with self.subTest(before=before):
                self.setup_text('# 사양\n\n' + before + '\n')
                self.mutate(before, after)
                self.assertEqual(self.validate()['checks']['QUANTITY_SCOPE']['status'], 'violated')

    def test_structural_failure_never_sends_abnormal_output_to_reviewer(self):
        self.mutate('30초', '30분')
        calls = []
        def reviewer(request):
            calls.append(request)
            return supported(request)
        audit = semantic.validate_final_audit(self.bundle, self.analysis, self.org, self.preview,
                                             self.result, reviewer=reviewer)
        report = audit['semantic_report']
        self.assertEqual(calls, [])
        self.assertEqual(audit['structural_report']['gate_state'], 'FAIL')
        self.assertEqual(audit['gate_state'], 'FAIL')
        self.assertEqual(report['gate_state'], 'FAIL')
        self.assertEqual(report['execution']['state'], 'blocked_structural_failure')
        self.assertIsNone(report['execution']['response_sha256'])
        self.assertEqual(report['coverage']['reviewed_checks'], [])
        self.assertFalse(report['coverage']['complete'])
        structural_errors = {f['rule_id'] for f in audit['structural_report']['findings'] if f['severity'] == 'ERROR'}
        self.assertTrue(structural_errors)
        self.assertTrue(structural_errors.issubset({f['rule_id'] for f in report['findings']}))
        for check in report['checks'].values():
            self.assertNotEqual(check['status'], 'supported')
            self.assertNotIn('model_review', check)
            if check['status'] == 'unresolved':
                self.assertEqual(check['unresolved_reason'], 'SEMANTIC_REVIEW_BLOCKED_STRUCTURAL_FAILURE')
        self.assertFalse(report['delivery_approved'])
        self.assertFalse(report['stage_transition_allowed'])

    def test_detected_input_change_stays_invalid_after_input_restoration(self):
        original = self.bundle['writing_contract']['purpose']
        def changing(request):
            self.bundle['writing_contract']['purpose'] = 'Changed during review'
            return supported(request)
        report = self.validate(reviewer=changing)
        self.assertFalse(report['execution_evidence_matches_current_inputs'])
        self.assertEqual(report['gate_state'], 'FAIL')
        self.bundle['writing_contract']['purpose'] = original
        verification = semantic.verify_final_semantic_report(self.bundle, self.analysis, self.org,
            self.preview, self.result, report)
        self.assertFalse(verification['valid'])
        self.assertFalse(verification['execution_evidence_matches_current_inputs'])
        self.assertEqual(verification['gate_state'], 'FAIL')
        forged = copy.deepcopy(report)
        forged['execution_evidence_matches_current_inputs'] = True
        expression.seal(forged, 'report_sha256')
        self.assertFalse(semantic.verify_final_semantic_report(self.bundle, self.analysis, self.org,
            self.preview, self.result, forged)['valid'])
        # A fresh execution on the restored input is allowed to produce REVIEW evidence.
        fresh = self.validate(reviewer=supported)
        self.assertEqual(fresh['gate_state'], 'REVIEW')
        self.assertTrue(semantic.verify_final_semantic_report(self.bundle, self.analysis, self.org,
            self.preview, self.result, fresh)['valid'])


if __name__ == '__main__': unittest.main()
