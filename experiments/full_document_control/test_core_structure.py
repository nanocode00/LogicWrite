"""Synthetic structural regressions, independent of evaluation answers."""
import copy
import unittest

import expression
import integration
import organization
import pipeline
import final_validator
import test_integration as fixtures
import reconstruction


class CoreStructureTests(unittest.TestCase):
    def fixture(self, move=False):
        fixture = fixtures.ReconstructionTests()
        fixture.setUp()
        if move:
            fixture.setup_move()
        return fixture

    def test_integrated_multidocument_contract_still_stops_at_analysis(self):
        fixture = self.fixture(move=True)
        result = integration.run_pipeline(fixture.bundle, analysis=fixture.analysis,
                                          destination_snapshots=fixture.snaps)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertIsNone(result['organization_plan'])
        self.assertIn('INVALID_ARTIFACT', {f['rule_id'] for f in result['analysis_report']['findings']})
        self.assertFalse(result['delivery_approved'])

    def test_generated_move_declares_append_without_invented_section(self):
        fixture = self.fixture(move=True)
        for placement in fixture.org['placements'][1:]:
            self.assertEqual(placement['targets'][0]['section_path'], [])

    def test_explicit_move_placement_is_held(self):
        for request in ({'section_path': ['목적지']},
                        {'section_path': [], 'anchor_unit_id': 'destination-unit',
                         'anchor_relative_position': 'before'}):
            with self.subTest(request=request):
                fixture = self.fixture(move=True)
                fixture.org['placements'][1]['targets'][0].update(request)
                expression.seal(fixture.org, 'plan_sha256')
                fixture.regenerate()
                result = fixture.candidate()
                self.assertEqual(result['delivery_state'], 'preview')
                self.assertEqual(result['output_snapshots'], [])
                self.assertIn('MOVE_PLACEMENT_UNSUPPORTED', {f['rule_id'] for f in result['findings']})
                self.assertEqual(fixture.report(result)['gate_state'], 'REVIEW')

    def test_final_validator_rejects_ignored_move_placement(self):
        fixture = self.fixture(move=True)
        result = fixture.candidate()
        fixture.org['placements'][1]['targets'][0]['section_path'] = ['目的地']
        expression.seal(fixture.org, 'plan_sha256')
        fixture.regenerate()
        # Rebind the old append-only output to the changed intent. Hashes alone
        # must not make this output an execution of the new section request.
        docs = {s['document_id']: s for s in [fixture.bundle['document_snapshot']] + fixture.snaps}
        result.update(reconstruction.references(fixture.bundle, fixture.analysis,
                         fixture.org, fixture.preview, docs))
        result['organization_ref'] = copy.deepcopy(fixture.preview['organization_ref'])
        result['expression_plan'] = copy.deepcopy(fixture.preview['expression_plan'])
        expression.seal(result, 'revision_sha256')
        report = fixture.report(result)
        self.assertIn('MOVE_PLACEMENT_UNSUPPORTED', {f['rule_id'] for f in report['findings']})
        self.assertEqual(report['checks']['ORGANIZATION_FIDELITY'], 'violated')

    def test_mixed_failures_invalidate_from_earliest_module(self):
        for rules, owner, retained in (
            (['MOVE_SEVERS_REQUIRED_CONDITION', 'ANALYSIS_INPUT_INVALID', 'TERM_VIOLATION'],
             'information_extraction_analysis', set()),
            (['TERM_VIOLATION', 'ACTUAL_PLACEMENT_MISMATCH'],
             'information_organization', {'analysis'})):
            with self.subTest(rules=rules):
                artifacts = dict.fromkeys(['analysis', 'organization', 'expression', 'reconstruction',
                    'final_report', 'final_semantic_report', 'final_audit', 'approval_request', 'approval_report'], {})
                decision = integration.RevisionController(artifacts).stop(
                    [{'rule_id': r, 'severity': 'ERROR'} for r in rules])
                self.assertEqual(decision['responsible_module'], owner)
                self.assertEqual(set(artifacts), retained)
                self.assertFalse(decision['stage_transition_allowed'])

    def observation(self, result, uid):
        self.assertIn('execution_observations', result, 'Missing separate decision/output diagnostics')
        observations = result['execution_observations']
        self.assertTrue(observations['advisory_only'])
        return next(row for row in observations['units'] if row['unit_id'] == uid)

    def test_decision_and_unchanged_output_are_distinct(self):
        fixture = self.fixture()
        uid = fixture.uid('기본 기본')
        result = fixture.candidate()
        row = self.observation(result, uid)
        self.assertEqual(row['decision']['placement']['action'], 'KEEP')
        self.assertEqual(row['decision']['expression_operation'], 'REVISE')
        self.assertEqual(row['observation']['treatments'], ['KEEP'])
        self.assertFalse(row['observation']['text_changed'])
        self.assertEqual(row['observation']['state'], 'observed')
        self.assertEqual(row['observation']['output_spans'], next(
            t['output_spans'] for t in result['trace'] if t['unit_refs'] == [uid]))
        self.assertTrue(organization.verify_self_digest(result, 'revision_sha256')[0])

    def test_compression_and_held_semantic_rewrite_report_actual_text(self):
        fixture = self.fixture()
        uid = fixture.uid('기본 기본')
        fixture.regenerate(operations={uid: 'COMPRESS'})
        compressed = self.observation(fixture.candidate(), uid)
        self.assertTrue(compressed['observation']['text_changed'])
        self.assertEqual(compressed['decision']['expression_operation'], 'COMPRESS')
        fixture.regenerate(generator=lambda r: {'text': '요청의 기본 제한은 30초다.' if r['unit_id'] == uid else r['before']})
        held = self.observation(fixture.candidate(), uid)
        self.assertFalse(held['observation']['text_changed'])
        self.assertEqual(held['observation']['treatments'], ['KEEP'])

    def test_move_and_consolidation_observations_use_actual_ledger(self):
        fixture = self.fixture(move=True)
        uid = fixture.analysis['units'][1]['id']
        row = self.observation(fixture.candidate(), uid)
        self.assertEqual(row['decision']['placement']['action'], 'MOVE')
        self.assertEqual(row['observation']['treatments'], ['MOVE'])
        self.assertEqual(row['observation']['output_spans'][0]['document_id'], 'doc-dest')
        self.assertFalse(row['observation']['text_changed'])
        fixture = self.fixture()
        uids = fixture.setup_consolidation()
        row = self.observation(fixture.candidate(), uids[1])
        self.assertEqual(row['decision']['placement']['action'], 'CONSOLIDATE')
        self.assertEqual(row['observation']['treatments'], ['CONSOLIDATE'])

    def test_remove_and_unsupported_placement_do_not_claim_observed_output(self):
        for action in ('REMOVE', 'MOVE'):
            with self.subTest(action=action):
                fixture = self.fixture(move=action == 'MOVE')
                uid = fixture.analysis['units'][1]['id']
                if action == 'REMOVE':
                    fixture.org = organization.generate_organization_plan(fixture.bundle, fixture.analysis,
                        candidate_actions={uid: {'action': 'REMOVE'}})
                else:
                    fixture.org['placements'][1]['targets'][0]['section_path'] = ['missing']
                    expression.seal(fixture.org, 'plan_sha256')
                fixture.regenerate()
                result = fixture.candidate()
                row = self.observation(result, uid)
                self.assertEqual(row['decision']['placement']['action'], action)
                self.assertEqual(row['observation'], {'state': 'not_materialized',
                    'output_spans': [], 'treatments': [], 'text_changed': None})
                self.assertEqual(result['output_snapshots'], [])
                self.assertFalse(result['delivery_approved'])
