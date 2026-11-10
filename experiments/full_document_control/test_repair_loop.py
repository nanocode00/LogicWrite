"""Repair regression and executable offline integration examples (no gold data)."""
import copy
import time
import unittest
from unittest.mock import patch

import expression
import integration
import repair_loop as repair
from test_integration import DOC, contract


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.bundle = integration.markdown_bundle(DOC, contract())
        outcome = integration.run_pipeline(self.bundle)
        self.artifacts = dict(zip(repair.STAGES, (outcome['analysis'], outcome['organization_plan'],
                                                 outcome['expression_preview'], outcome['revision_result'])))

    def run_loop(self, adapter=None, **kwargs):
        return repair.RepairLoop(**kwargs).run(self.bundle, self.artifacts,
            adapters={'expression': adapter or repair.DeterministicExpressionRepair()})

    def break_expression(self):
        def broken(request):
            raise RuntimeError('private error')
        initial = integration.run_pipeline(self.bundle, generator=broken)
        self.artifacts['expression'] = initial['expression_preview']
        self.artifacts['reconstruction'] = initial['revision_result']

    def test_actual_generation_error_repair_reconstruct_validate(self):
        self.break_expression()
        result = self.run_loop()
        self.assertEqual(result['termination_reason'], 'CANDIDATE_VALIDATED')
        self.assertEqual(len(result['attempts']), 1)
        row = result['attempts'][0]
        self.assertIn('GENERATION_ERROR', {f['rule_id'] for f in row['before_validation']['structural_report']['findings']})
        self.assertEqual(row['regenerated'], ['reconstruction'])
        self.assertIn('approval_report', row['invalidated'])
        self.assertEqual(result['artifacts']['reconstruction']['output_snapshots'][0]['content'], DOC)
        self.assertEqual(result['status'], 'REVIEW')
        self.assertFalse(result['delivery_approved'])

    def test_unfinished_semantics_remains_review(self):
        result = self.run_loop()
        self.assertEqual(result['status'], 'REVIEW')
        self.assertTrue(repair.unresolved(result['final_audit']))
        self.assertEqual(result['attempts'], [])

    def test_unchanged_rejected(self):
        self.break_expression()
        result = self.run_loop(lambda r: {'candidate': r['artifacts']['expression']})
        self.assertEqual(result['termination_reason'], 'REPEATED_STATE')

    def test_claims_and_hidden_report_rejected(self):
        self.break_expression()
        for field in ('fixed', 'success', 'approved', 'final_audit'):
            with self.subTest(field=field):
                result = self.run_loop(lambda r: {'candidate': r['artifacts']['expression'], field: True})
                self.assertEqual(result['termination_reason'], 'INVALID_ADAPTER_RESPONSE')

    def test_adapter_error_and_timeout(self):
        self.break_expression()
        def fail(_):
            raise RuntimeError('secret')
        self.assertEqual(self.run_loop(fail)['termination_reason'], 'ADAPTER_ERROR')
        def slow(_):
            time.sleep(.1)
            return {}
        self.assertEqual(self.run_loop(slow, adapter_timeout=.01)['termination_reason'], 'ADAPTER_TIMEOUT')

    def test_changed_source_or_contract_discards_audit(self):
        self.break_expression()
        for key in ('document_snapshot', 'writing_contract'):
            original = copy.deepcopy(self.bundle)
            def mutate(r):
                self.bundle[key]['version'] = 'changed'
                return repair.DeterministicExpressionRepair()(r)
            result = self.run_loop(mutate)
            self.assertEqual(result['termination_reason'], 'INPUT_CHANGED')
            self.assertIsNone(result['final_audit'])
            self.bundle = original

    def test_max_attempts_and_budget(self):
        self.break_expression()
        self.assertEqual(self.run_loop(max_attempts=0)['termination_reason'], 'MAX_ATTEMPTS')
        self.assertEqual(self.run_loop(budget_seconds=.000001)['termination_reason'], 'BUDGET_EXHAUSTED')

    def test_stale_approval_and_reports_discarded(self):
        self.artifacts.update(approval_report={'approved': True}, approval_request={'token': 'old'}, final_audit={'gate_state': 'PASS'})
        result = self.run_loop()
        self.assertNotIn('approval_report', result['artifacts'])
        self.assertNotIn('approval_request', result['artifacts'])
        self.assertFalse(result['stage_transition_allowed'])

    def test_trust_and_unknown_ownership_stop(self):
        for rule in ('STALE_FINAL_INPUT', 'REVISION_DIGEST_MISMATCH', 'UNAUTHORIZED_FINAL_APPROVAL', 'UNKNOWN'):
            self.assertIsNone(repair.diagnose([{'rule_id': rule, 'severity': 'ERROR'}]))

    def test_highest_valid_stage_and_trust_precedence(self):
        findings = [{'rule_id': r, 'severity': 'ERROR'} for r in ('UNIT_TRACE_INVALID', 'GENERATION_ERROR', 'ACTUAL_PLACEMENT_MISMATCH')]
        self.assertEqual(repair.diagnose(findings), 'organization')
        findings.append({'rule_id': 'STALE_FINAL_INPUT', 'severity': 'ERROR'})
        self.assertIsNone(repair.diagnose(findings))

    def test_new_violation_is_not_progress(self):
        self.break_expression()
        original = repair.pipeline.validate_final_output
        calls = []
        def validate(*args, **kwargs):
            audit = original(*args, **kwargs)
            calls.append(1)
            if len(calls) > 1:
                audit['semantic_report']['findings'].append({'check_id': 'MEANING', 'rule_id': 'NEW_MEANING_LOSS', 'severity': 'ERROR', 'evidence': []})
            return audit
        with patch.object(repair.pipeline, 'validate_final_output', side_effect=validate):
            result = self.run_loop()
        self.assertEqual(result['termination_reason'], 'WORSENED')
        self.assertEqual(result['status'], 'FAIL')

    def test_provider_independent_integrated_entry(self):
        result = repair.run_repair_pipeline(self.bundle, generator=lambda _: (_ for _ in ()).throw(ValueError()),
            adapters={'expression': repair.DeterministicExpressionRepair()})
        self.assertEqual(result['status'], 'REVIEW')
        self.assertEqual(len(result['attempts']), 1)

    def test_analysis_repair_invalidates_all_descendants(self):
        good = copy.deepcopy(self.artifacts['analysis'])
        self.artifacts['analysis']['units'][0]['statement'] = ''
        expression.seal(self.artifacts['analysis'], 'analysis_sha256')
        result = repair.RepairLoop().run(self.bundle, self.artifacts,
            adapters={'analysis': lambda r: {'candidate': good}})
        self.assertEqual(result['termination_reason'], 'CANDIDATE_VALIDATED')
        self.assertEqual(result['attempts'][0]['regenerated'], ['organization', 'expression', 'reconstruction'])
        self.assertEqual(result['attempts'][0]['target_module'], 'analysis')

    def test_no_adapter_stops(self):
        self.break_expression()
        result = repair.RepairLoop().run(self.bundle, self.artifacts)
        self.assertEqual(result['termination_reason'], 'ADAPTER_UNAVAILABLE')

    def test_reconstruction_adapter_is_independently_validated(self):
        original = copy.deepcopy(self.artifacts['reconstruction'])
        self.artifacts['reconstruction']['trace'][0]['unit_refs'] = ['unknown']
        expression.seal(self.artifacts['reconstruction'], 'revision_sha256')
        result = repair.RepairLoop().run(self.bundle, self.artifacts,
            adapters={'reconstruction': lambda r: {'candidate': original}})
        self.assertEqual(result['termination_reason'], 'CANDIDATE_VALIDATED')
        self.assertEqual(result['attempts'][0]['regenerated'], [])

    def test_synthetic_multiple_steps_and_cycle_policy(self):
        # Policy-only audit seam: real integration is exercised separately above.
        original = repair.pipeline.validate_final_output
        good = copy.deepcopy(self.artifacts['reconstruction'])
        def run(cycle, limit=3):
            calls = []
            def validate(*args, **kwargs):
                audit = original(self.bundle, *(self.artifacts[k] for k in repair.STAGES))
                n = len(calls)
                calls.append(n)
                audit['structural_report']['findings'] = [
                    {'rule_id': 'UNIT_TRACE_INVALID', 'check_id': str(i), 'severity': 'ERROR'}
                    for i in range(max(0, 2-n))]
                return audit
            def adapter(r):
                candidate = copy.deepcopy(good)
                if not cycle or r['attempt'] == 1:
                    candidate['trace'][0]['justification'] = 'policy-' + str(r['attempt'])
                return {'candidate': candidate}
            with patch.object(repair.pipeline, 'validate_final_output', side_effect=validate):
                return repair.RepairLoop(max_attempts=limit).run(self.bundle, self.artifacts,
                    adapters={'reconstruction': adapter})
        result = run(False)
        self.assertEqual(len(result['attempts']), 2)
        self.assertEqual(result['termination_reason'], 'CANDIDATE_VALIDATED')
        limited = run(False, 1)
        self.assertEqual(limited['termination_reason'], 'MAX_ATTEMPTS')
        self.assertEqual(len(limited['attempts']), 1)
        result = run(True)
        self.assertEqual(len(result['attempts']), 2)
        self.assertEqual(result['termination_reason'], 'REPEATED_STATE')

    def test_organization_boundary_regenerates_expression_and_reconstruction(self):
        original = repair.pipeline.validate_final_output
        calls = []
        def validate(*args, **kwargs):
            audit = original(*args, **kwargs)
            if not calls:
                audit['structural_report']['findings'].append({
                    'rule_id': 'ACTUAL_PLACEMENT_MISMATCH', 'severity': 'ERROR'})
            calls.append(1)
            return audit
        # An independently grounded organization finding is represented at the audit seam.
        with patch.object(repair.pipeline, 'validate_final_output', side_effect=validate):
            result = repair.RepairLoop().run(self.bundle, self.artifacts,
                adapters={'organization': lambda r: {'candidate': r['artifacts']['organization']}})
        # Identical effective state must stop even when a callback claims it fixed the plan.
        self.assertEqual(result['termination_reason'], 'REPEATED_STATE')
        self.assertEqual(result['attempts'][0]['regenerated'], ['expression', 'reconstruction'])

    def test_missing_generation_receipt_is_trust_stop(self):
        for fragment in self.artifacts['expression']['preview_fragments']:
            fragment['generation']['receipt_id'] = 'missing'
        expression.seal(self.artifacts['expression'], 'revision_sha256')
        result = self.run_loop()
        self.assertNotEqual(result['termination_reason'], 'CANDIDATE_VALIDATED')
        self.assertEqual(result['attempts'], [])

    def test_invalid_repair_cannot_export_old_audit(self):
        self.artifacts['analysis']['units'][0]['statement'] = ''
        expression.seal(self.artifacts['analysis'], 'analysis_sha256')
        result = repair.RepairLoop().run(self.bundle, self.artifacts,
            adapters={'analysis': lambda _: {'candidate': {}}})
        self.assertEqual(result['termination_reason'], 'INVALID_ANALYSIS_CANDIDATE')
        self.assertIsNone(result['final_audit'])
        self.assertIsNone(result['attempts'][0]['after_validation'])

    def test_initial_integration_is_bounded(self):
        def slow(_):
            time.sleep(.1)
            return {'text': 'late'}
        result = repair.run_repair_pipeline(self.bundle, generator=slow, adapter_timeout=.01)
        self.assertEqual(result['termination_reason'], 'INITIAL_TIMEOUT')
        self.assertIsNone(result['final_audit'])

    def test_bad_limits(self):
        for config in ({'max_attempts': True}, {'max_attempts': -1}, {'budget_seconds': float('nan')}, {'adapter_timeout': 0}):
            with self.assertRaises(ValueError):
                repair.RepairLoop(**config)


if __name__ == '__main__':
    unittest.main()
