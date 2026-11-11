"""Prediction/reference separation and honest evaluated-case denominators."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


class RunnerTests(unittest.TestCase):
    @staticmethod
    def protocol_reviewer(request):
        """Synthetic transport fixture, deliberately no semantic inference or gold access."""
        evidence = [dict(side=side, document_id=s['document_id'], snapshot_sha256=s['sha256'],
                         start=0, end=len(s['content']), quote=s['content'])
                    for side, key in [('source','source_snapshots'), ('output','output_snapshots')]
                    for s in request[key] if s['content']]
        return {'request_sha256': request['request_sha256'], 'reviews': [
            {'check_id': check, 'judgment': 'supported', 'reason': 'Synthetic protocol test only',
             'reviewed_refs': request['snapshot_refs'], 'evidence': evidence}
            for check in request['required_checks']]}

    def test_predictions_never_load_references(self):
        import run
        original = Path.read_bytes
        def guarded(path):
            self.assertNotIn('answers', path.parts)
            self.assertNotEqual(path.name, 'development-gold.json')
            return original(path)
        with patch.object(Path, 'read_bytes', guarded):
            out = run.predict(['SP-005', 'SP-006', 'SP-007', 'SP-008'])
        self.assertFalse(out['reference_labels_loaded'])
        self.assertTrue(all(not r['result']['evaluated'] for r in out['cases']))

    def test_no_accuracy_from_unevaluated_cases(self):
        import run
        report = run.compare(run.predict(['SP-005', 'SP-006', 'SP-007', 'SP-008']))
        self.assertEqual(report['evaluated_count'], 0)
        self.assertIsNone(report['accuracy'])
        self.assertEqual(len(report['excluded']), 4)

    def test_mixed_violation_is_visible_but_excluded_from_accuracy(self):
        import run
        def mixed(request):
            response = self.protocol_reviewer(request)
            response['reviews'][0]['judgment'] = 'contradicted'
            response['reviews'][1]['judgment'] = 'unresolved'
            return response
        predictions = run.predict(['SP-006'], reviewer=mixed)
        report = run.compare(predictions)
        self.assertEqual(report['evaluated_count'], 0)
        self.assertIsNone(report['accuracy'])
        self.assertEqual(report['reviewed_case_count'], 1)
        self.assertEqual(report['confirmed_violation_count'], 1)
        self.assertTrue(report['cases'][0]['violation_confirmed'])
        self.assertEqual(report['cases'][0]['observed_classification'], 'VIOLATION')
        self.assertFalse(report['cases'][0]['included_in_metric'])
        self.assertFalse(report['evidence_trust']['model_execution_authenticated'])

    def test_excluded_mixed_report_is_still_checked_for_forged_binding(self):
        import run
        def mixed(request):
            response = self.protocol_reviewer(request)
            response['reviews'][0]['judgment'] = 'contradicted'
            response['reviews'][1]['judgment'] = 'unresolved'
            return response
        predictions = run.predict(['SP-006'], reviewer=mixed)
        report = predictions['cases'][0]['result']['semantic_report']
        report['execution']['request_sha256'] = '0'*64
        report.pop('report_sha256');run.semantic.expression.seal(report, 'report_sha256')
        predictions.pop('record_sha256');run.seal(predictions)
        with self.assertRaises(ValueError):
            run.compare(predictions)

    def test_only_full_cited_evaluation_enters_denominator(self):
        import run
        predictions = run.predict(['SP-006', 'SP-009'], reviewer=self.protocol_reviewer)
        report = run.compare(predictions)
        self.assertEqual(report['evaluated_count'], 1)
        self.assertEqual(report['candidate_count'], 2)
        self.assertEqual([r['case_id'] for r in report['excluded']], ['SP-009'])
        self.assertIn(report['accuracy'], (0.0, 1.0))

    def test_legacy_definitive_record_without_additive_fields_still_compares(self):
        import run
        predictions = run.predict(['SP-006'], reviewer=self.protocol_reviewer)
        result = predictions['cases'][0]['result']
        for key in ('all_checks_reviewed', 'all_judgments_definitive', 'violation_confirmed',
                    'model_execution_state', 'evidence_trust'):
            result.pop(key)
        report = result['semantic_report']
        for key in ('all_checks_reviewed', 'all_judgments_definitive'):
            report['coverage'].pop(key)
        report.pop('violation_confirmed');report.pop('evidence_trust')
        report.pop('report_sha256');run.semantic.expression.seal(report, 'report_sha256')
        predictions.pop('evidence_trust')
        predictions.pop('record_sha256');run.seal(predictions)
        compared = run.compare(predictions)
        self.assertEqual(compared['evaluated_count'], 1)
        self.assertFalse(compared['evidence_trust']['model_execution_authenticated'])

    def test_boolean_evaluated_flag_alone_is_not_valid_model_coverage(self):
        import run
        predictions = run.predict(['SP-006'])
        predictions['cases'][0]['result'].update(evaluated=True, semantic_judgment='supported')
        predictions.pop('record_sha256');run.seal(predictions)
        with self.assertRaises(ValueError):
            run.compare(predictions)

    def test_cited_review_verdict_cannot_be_relabeled_after_evaluation(self):
        import run
        predictions = run.predict(['SP-006'], reviewer=self.protocol_reviewer)
        report = predictions['cases'][0]['result']['semantic_report']
        report['checks']['CLAIM_FACTS']['model_review']['judgment'] = 'contradicted'
        report.pop('report_sha256');run.semantic.expression.seal(report, 'report_sha256')
        predictions.pop('record_sha256');run.seal(predictions)
        with self.assertRaises(ValueError):
            run.compare(predictions)

    def test_resealed_request_hash_cannot_replace_actual_input_request(self):
        import run
        predictions = run.predict(['SP-006'], reviewer=self.protocol_reviewer)
        report = predictions['cases'][0]['result']['semantic_report']
        report['execution']['request_sha256'] = '0'*64
        report.pop('report_sha256');run.semantic.expression.seal(report, 'report_sha256')
        predictions.pop('record_sha256');run.seal(predictions)
        with self.assertRaises(ValueError):
            run.compare(predictions)

    def test_nested_approval_claim_or_wrong_namespace_is_rejected(self):
        import run
        for field, value in [('delivery_approved', True), ('stage_transition_allowed', True),
                             ('version', 'final-output-semantic-validation-v1')]:
            predictions = run.predict(['SP-006'], reviewer=self.protocol_reviewer)
            report = predictions['cases'][0]['result']['semantic_report']
            report[field] = value
            report.pop('report_sha256');run.semantic.expression.seal(report, 'report_sha256')
            predictions.pop('record_sha256');run.seal(predictions)
            with self.subTest(field=field), self.assertRaises(ValueError):
                run.compare(predictions)

    def test_provisional_cases_not_in_g3_runner(self):
        import run
        for cid in ('GC-001', 'SP-013'):
            with self.assertRaises(ValueError):
                run.predict([cid])

    def test_tampered_input_binding_rejected(self):
        import run
        out = run.predict(['SP-006'])
        out['cases'][0]['input_sha256'] = '0'*64
        with self.assertRaises(ValueError):
            run.compare(out)

    def test_duplicate_case_ids_rejected(self):
        import run
        with self.assertRaises(ValueError):
            run.predict(['SP-006', 'SP-006'])

    def test_case_result_is_not_core_approval(self):
        import run
        out = run.predict(['SP-006'])
        result = out['cases'][0]['result']
        self.assertFalse(result['delivery_approved'])
        self.assertFalse(result['stage_transition_allowed'])
        self.assertEqual(result['gate_state'], 'REVIEW')

    def test_provider_failure_stops_later_calls_without_false_execution(self):
        import run
        reviewer = run.CliReviewer('fixture-only', 'test-model', max_calls=1)
        observation = {'stdout': b'', 'stderr': b'RESOURCE_EXHAUSTED 429 quota',
                       'returncode': 3, 'timed_out': False, 'seconds': 0.01}
        with patch.object(run.pipeline, 'call_cli_provider', return_value=observation) as call:
            out = run.predict(['SP-006', 'SP-007'], reviewer=reviewer)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(reviewer.attempts[0]['error_class'], 'quota_exhausted')
        second = out['cases'][1]['result']
        self.assertEqual(second['semantic_report']['execution']['state'], 'not_run')
        self.assertIn('PROVIDER_NOT_ATTEMPTED_CALL_BUDGET_OR_PREVIOUS_FAILURE', second['reasons'])


if __name__ == '__main__':
    unittest.main()
