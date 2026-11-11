"""Readonly diagnostics: no reference labels may enter runtime requests."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


class AdapterTests(unittest.TestCase):
    def test_reference_canary_is_rejected(self):
        import evaluate
        raw = evaluate.read(evaluate.INPUTS / 'SP-002.json')
        raw['user_final_judgment'] = 'CANARY_REFERENCE_LABEL'
        with self.assertRaises(ValueError):
            evaluate.predict(raw)

    def test_prediction_does_not_read_answers_or_gold(self):
        import evaluate
        from unittest.mock import patch
        raw = evaluate.read(evaluate.INPUTS / 'SP-006.json')
        original = Path.read_bytes
        def guarded(path):
            self.assertNotIn('answers', path.parts)
            self.assertNotIn('development-gold.json', path.parts)
            return original(path)
        with patch.object(Path, 'read_bytes', guarded):
            out = evaluate.predict(raw)
        self.assertIsNone(out['sp_prediction'])
        self.assertFalse(out['delivery_approved'])
        self.assertIn('LITERAL_DIFFERENCE_NEEDS_CONTEXT', out['witness_rule_ids'])
        self.assertFalse(any(w['status'] == 'violated' for w in out['witnesses']))

    def test_missing_destination_and_partial_result_are_unsupported(self):
        import evaluate
        for cid in ('SP-009', 'SP-012'):
            with self.subTest(cid=cid):
                result = evaluate.predict(evaluate.read(evaluate.INPUTS / (cid+'.json')))
                self.assertEqual(result['comparison_scope'], 'unsupported')
                self.assertIsNone(result['sp_prediction'])
                self.assertFalse(result['delivery_approved'])

    def test_unknown_approved_baseline_is_not_selected_by_version(self):
        import evaluate
        out = evaluate.predict(evaluate.read(evaluate.INPUTS / 'SP-010.json'))
        self.assertEqual(out['comparison_scope'], 'unsupported')
        self.assertIn('DOCUMENT_ID_SET_DIFFERS_NO_BASELINE_RESOLVER', out['limitations'])

    def test_references_must_match_prediction_input_hash(self):
        import evaluate
        predictions = evaluate.run_predictions()
        predictions['cases'][0]['input_sha256'] = '0'*64
        with self.assertRaises(ValueError):
            evaluate.compare(predictions)

    def test_diagnostic_witness_is_not_a_core_or_sp_gate(self):
        import evaluate
        out = evaluate.predict(evaluate.read(evaluate.INPUTS / 'SP-006.json'))
        self.assertEqual(out['comparison_scope'], 'native_literal_diagnostic_only')
        self.assertNotIn('gate_state', out)
        self.assertNotIn('accuracy', out)
        self.assertIsNone(out['sp_prediction'])

    def test_native_probes_enforce_expected_gates_and_termination(self):
        import evaluate
        result = evaluate.native_probes()
        for row in result['cases']:
            with self.subTest(case_id=row['case_id']):
                if 'expected_gate' in row:
                    self.assertEqual(row['actual_gate'], row['expected_gate'])
                if 'expected_termination' in row:
                    self.assertEqual(row['actual_termination'], row['expected_termination'])
                if 'expected_allows_move' in row:
                    self.assertEqual(row['actual']['allows_confirmed_move'], row['expected_allows_move'])
                self.assertFalse(row['delivery_approved'])
        all_descendants = next(r for r in result['cases'] if r['case_id']=='N-14-all-descendants-revalidated')
        attempt = all_descendants['evidence'][0]
        self.assertEqual(attempt['regenerated'], ['organization', 'expression', 'reconstruction'])
        self.assertIn('approval_report', attempt['invalidated'])
        self.assertIsNotNone(attempt['after_validation'])
        self.assertEqual(attempt['after_validation']['gate_state'], 'REVIEW')


if __name__ == '__main__':
    unittest.main()
