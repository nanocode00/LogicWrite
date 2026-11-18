"""G0 characterization only: legacy generation is distinct from pair evaluation."""
import copy
import unittest

import expression
import final_semantic_validator as semantic
import final_validator
import integration
import organization
import pipeline
import reconstruction
from test_integration import contract
from test_source_candidate_adapter import review


class ExistingBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.bundle = integration.markdown_bundle('# Source\n\n조건을 보존한다.\n', contract())

    def test_single_scope_analysis_and_candidate_are_unapproved(self):
        pipeline.validate_input_bundle(self.bundle)
        analysis = integration.analyze_source(self.bundle)
        org = organization.generate_organization_plan(self.bundle, analysis)
        preview = expression.generate_revision_result(self.bundle, analysis, org)
        candidate = reconstruction.reconstruct_documents(self.bundle, analysis, org, preview)
        report = final_validator.validate_final_result(self.bundle, analysis, org, preview, candidate)
        self.assertEqual(candidate['output_snapshots'][0]['content'], self.bundle['document_snapshot']['content'])
        self.assertEqual(report['semantic_fidelity'], 'not_run')
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertFalse(report['delivery_approved'])

    def test_multiple_scope_admission_rejected_before_analysis(self):
        self.bundle['writing_contract']['output_scopes'].append({'scope_id':'second', 'document_id':'second'})
        for call in (pipeline.validate_input_bundle, integration.analyze_source):
            with self.subTest(call=call.__name__), self.assertRaisesRegex(ValueError, 'exactly one concrete output_scope'):
                call(self.bundle)
        result = integration.run_pipeline(self.bundle)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertIsNone(result['revision_result'])
        self.assertFalse(result['delivery_approved'])

    def pair(self):
        sources = [dict(self.bundle['document_snapshot'])]
        sources.append(dict(sources[0], document_id='second', snapshot_id='second:1'))
        return sources, copy.deepcopy(sources), {'output_document_ids':['doc-guide','second'],
            'required_information':[], 'constraints':[]}

    def test_external_pair_without_review_never_succeeds_or_creates_receipt(self):
        before = copy.deepcopy(semantic._RECEIPTS)
        report = semantic.evaluate_snapshot_pair(*self.pair())
        self.assertEqual(report['execution']['state'], 'not_run')
        self.assertEqual(report['overall_judgment'], 'unresolved')
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertFalse(report['coverage']['complete'])
        self.assertEqual(before, semantic._RECEIPTS)

    def test_full_synthetic_review_is_advisory_without_generation(self):
        report = semantic.evaluate_snapshot_pair(*self.pair(), reviewer=review)
        self.assertTrue(report['coverage']['complete'])
        self.assertEqual(report['overall_judgment'], 'supported')
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertFalse(report['lineage']['available'])
        self.assertFalse(report['stage_transition_allowed'])
        self.assertNotIn(report['report_sha256'], semantic._RECEIPTS)

    def test_invalid_incomplete_unresolved_and_unsupported_review_stay_review(self):
        sources, outputs, wc = self.pair()
        for mutate in (lambda s,o: o[0].update(sha256='0'*64),
                       lambda s,o: o.pop(), lambda s,o: s[0].update(coverage='partial')):
            s,o = copy.deepcopy((sources,outputs)); mutate(s,o)
            report = semantic.evaluate_snapshot_pair(s,o,wc)
            self.assertEqual(report['execution']['state'], 'invalid_input')
            self.assertFalse(report['coverage']['complete'])
            self.assertEqual(report['gate_state'], 'REVIEW')
        for reviewer in (lambda r: review(r,'unresolved'), lambda r: {'unsupported':True}):
            report = semantic.evaluate_snapshot_pair(sources,outputs,wc,reviewer=reviewer)
            self.assertFalse(report['coverage']['complete'])
            self.assertEqual(report['gate_state'], 'REVIEW')
