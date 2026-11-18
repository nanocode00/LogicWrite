"""Offline evidence must not relabel external candidates as Core generation."""
import unittest
import b2_g0_g1_offline as offline


class OfflineEvidenceTests(unittest.TestCase):
    def test_frozen_inputs_map_all_three_cases_and_six_candidates_without_generation(self):
        report,contracts=offline.build_evidence()
        self.assertEqual(set(contracts),{'IR-001','IR-002','IR-003'})
        self.assertEqual(len(report['source_hashes']),9)
        self.assertEqual(len(report['validator_shadow']),6)
        self.assertEqual(report['model_calls'],0)
        self.assertFalse(report['b2_reconstruction_success'])
        for probe in report['legacy_probes']:
            self.assertTrue(probe['single_scope_admitted'])
            self.assertFalse(probe['multiple_scope_admitted'])
            self.assertEqual(probe['integrated_status'],'STOPPED')
            self.assertFalse(probe['candidate_generated'])
        for row in report['validator_shadow']:
            self.assertEqual(row['mode'],'validator_shadow')
            self.assertFalse(row['b2_generated'])
            report=row['legacy_external_semantic_report']
            self.assertEqual(report['execution']['state'],'not_run')
            self.assertEqual(report['overall_judgment'],'unresolved')
            self.assertEqual(report['gate_state'],'REVIEW')
            self.assertFalse(report['lineage']['available'])
            self.assertFalse(report['delivery_approved'])
