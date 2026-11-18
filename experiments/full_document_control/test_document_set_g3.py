"""Regression tests for independent document-set verification."""
import copy
import importlib.util
import unittest

import document_set as core
import document_set_reconstruction as reconstruction
from document_set_final_validator import candidate_row
import test_document_set_reconstruction as fixtures


class IndependentTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('document_set_verification'),
                             'G3 independent verification entry point is missing')
        import document_set_verification
        self.g3 = document_set_verification
        self.fixture = fixtures.ReconstructionTests()
        self.fixture.setUp()

    def baseline(self, tasks=()):
        inputs = self.fixture.inputs(tasks)
        return inputs, reconstruction.reconstruct_document_set(**inputs)

    def check(self, inputs, result, *, obligations=(), mode='g2c', **overrides):
        requirements = dict(version='document-set-requirements-v1', obligations=list(obligations),
                            format_policies={})
        pins = dict(trusted_requirements_sha256=core.contract_digest(requirements),
                    trusted_candidate_sha256=core.contract_digest(result), mode=mode)
        pins.update(overrides)
        return self.g3.verify_document_set(result, requirements, **inputs, **pins)

    def replace(self, result, did, text):
        doc = next(d for d in self.fixture.contract['documents'] if d['document_id'] == did)
        row = candidate_row(doc, text)
        result['candidates'] = [d for d in result['candidates'] if d['document_id'] != did] + [row]

    def obligation(self, **extra):
        return dict(dict(check_id='local-limit', kind='exact_line', source_refs=[
            dict(document_id='guide', quote='Stop before 12 June if more than 60 samples arrive.')],
            document_ids=['notes'], task_ids=[], decision_owner='Sample owner',
            decision_needed='Confirm scope and required operating conditions'), **extra)

    def test_g2c_move_and_unchanged_formats_pass_with_review_boundary(self):
        inputs, result = self.baseline([self.fixture.task()])
        report = self.check(inputs, result)
        self.assertEqual(report['checks']['lineage']['status'], 'passed')
        self.assertEqual(report['checks']['authority:format']['status'], 'passed')
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertFalse(report['delivery_approved'])

    def test_read_only_output_and_missing_document(self):
        inputs, result = self.baseline()
        result['candidates'].pop(0)
        self.replace(result, 'policy', 'Unauthorized change.')
        report = self.check(inputs, result, mode='external_shadow')
        self.assertEqual(report['checks']['coverage']['status'], 'violated')
        self.assertEqual(report['checks']['authority:policy']['status'], 'violated')

    def test_format_word_change_and_undefined_whitespace(self):
        inputs, result = self.baseline()
        original = next(d['content'] for d in result['candidates'] if d['document_id'] == 'format')
        for text, expected in [(original + '\n', 'unresolved'),
                               (original.replace('attempt', 'success'), 'violated')]:
            with self.subTest(text=text):
                self.replace(result, 'format', text)
                report = self.check(inputs, result, mode='external_shadow')
                self.assertEqual(report['checks']['authority:format']['status'], expected)

    def test_edit_outside_plan_and_false_self_check(self):
        inputs, result = self.baseline()
        self.replace(result, 'guide', 'Unexpected rewrite')
        result['final_checks'] = {'within_authority': True}
        report = self.check(inputs, result, mode='external_shadow')
        self.assertEqual(report['checks']['authority:guide']['status'], 'violated')
        self.assertEqual(report['self_checks'][0]['status'], 'violated')

    def test_candidate_and_source_tampering_rejected(self):
        inputs, result = self.baseline()
        frozen = core.contract_digest(result)
        result['candidates'][0]['content'] += ' tampered'
        self.assertFalse(self.check(inputs, result, trusted_candidate_sha256=frozen)['accepted'])
        self.assertFalse(self.check(inputs, result)['accepted'])
        inputs['contract'] = copy.deepcopy(inputs['contract'])
        inputs['contract']['documents'][0]['content'] += ' tampered'
        self.assertFalse(self.check(inputs, result)['accepted'])

    def test_exact_target_requirement_detects_wrong_document_scope_and_negation(self):
        sentence = self.obligation()['source_refs'][0]['quote']
        self.fixture.update_text('guide', sentence + '\n')
        self.fixture.refresh()
        inputs, result = self.baseline()
        for replacement in ('', sentence.replace('12 June', '13 June'),
                            sentence.replace('60 samples', '60 crates'),
                            'Do not ' + sentence, 'Stop.\n' + sentence[5:]):
            with self.subTest(replacement=replacement):
                self.replace(result, 'notes', replacement)
                result['final_checks'] = {'completeness_verified': True}
                report = self.check(inputs, result, obligations=[self.obligation()], mode='external_shadow')
                item = report['checks']['local-limit']
                self.assertEqual(item['status'], 'violated')
                self.assertEqual(item['evidence'][0]['quote'], sentence)
                self.assertEqual(report['self_checks'][0]['status'], 'violated')

    def test_semantic_uncertainty_and_partial_hitl_propagation(self):
        self.fixture.update_text('guide', self.obligation()['source_refs'][0]['quote'] + '\n')
        self.fixture.refresh()
        task = self.fixture.place(name='place')
        harmless = self.fixture.task('KEEP', source='format', prefix='The', target='format', name='keep')
        dependent = self.fixture.task('KEEP', source='format', prefix='The', target='format',
                                      name='dependent', depends_on=['place'])
        inputs, result = self.baseline([task, harmless, dependent])
        policy = next(d for d in self.fixture.contract['documents'] if d['document_id'] == 'policy')
        refs = self.obligation()['source_refs'] + [dict(document_id='policy', quote=policy['content'].splitlines()[-1])]
        obligation = self.obligation(kind='policy_relation', task_ids=['place'], source_refs=refs)
        result['self_review'] = {'local-limit': 'passed'}
        report = self.check(inputs, result, obligations=[obligation])
        self.assertEqual(report['checks']['local-limit']['status'], 'unresolved')
        self.assertEqual(report['self_checks'][0]['status'], 'unresolved')
        question = next(q for q in report['hitl_questions'] if q['check_id'] == 'local-limit')
        self.assertEqual(question['held_task_ids'], ['dependent', 'place'])
        self.assertEqual(question['independent_task_ids'], ['keep'])

    def test_stale_report_cannot_be_reused(self):
        inputs, result = self.baseline()
        report = self.check(inputs, result)
        requirements = dict(version='document-set-requirements-v1', obligations=[], format_policies={})
        kwargs = dict(inputs, trusted_requirements_sha256=core.contract_digest(requirements),
                      trusted_candidate_sha256=core.contract_digest(result))
        self.assertTrue(self.g3.is_current_report(report, result, requirements, **kwargs))
        result['final_checks'] = {'within_authority': True}
        kwargs['trusted_candidate_sha256'] = core.contract_digest(result)
        self.assertFalse(self.g3.is_current_report(report, result, requirements, **kwargs))

    def test_review_is_pinned_to_current_exact_spans_and_cannot_override_mechanical_checks(self):
        self.fixture.update_text('guide', self.obligation()['source_refs'][0]['quote'] + '\n')
        self.fixture.refresh()
        inputs, result = self.baseline()
        obligation = self.obligation(kind='semantic')
        initial = self.check(inputs, result, obligations=[obligation])
        bindings = {k: v for k, v in initial['bindings'].items() if k != 'independent_review_sha256'}
        review = dict(bindings=bindings, reviewer_id='Independent fixture reviewer', reviews={
            'local-limit': dict(status='unresolved', reason='Scope is still uncertain',
                                evidence=initial['checks']['local-limit']['evidence'])})
        report = self.check(inputs, result, obligations=[obligation], independent_review=review,
                            trusted_review_sha256=core.contract_digest(review))
        self.assertEqual(report['execution']['semantic_review'], 'bound')
        self.assertEqual(report['checks']['local-limit']['status'], 'unresolved')
        review['reviews']['local-limit']['evidence'][0]['start'] += 1
        rejected = self.check(inputs, result, obligations=[obligation], independent_review=review,
                              trusted_review_sha256=core.contract_digest(review))
        self.assertEqual(rejected['reasons'], ['INVALID_REVIEW_CITATION'])

    def test_forged_native_trace_is_detected_independently_of_cached_structure(self):
        inputs, result = self.baseline([self.fixture.task()])
        result['trace'][0]['output']['start'] += 1
        report = self.check(inputs, result)
        self.assertEqual(result['structure']['status'], 'passed')
        self.assertEqual(report['checks']['lineage']['status'], 'violated')

    def test_pending_edit_is_held_and_unchanged_is_allowed(self):
        guide = next(d for d in self.fixture.contract['documents'] if d['document_id'] == 'guide')
        guide['authority'] = None
        self.fixture.refresh()
        inputs, result = self.baseline()
        self.assertEqual(self.check(inputs, result)['checks']['authority:guide']['status'], 'passed')
        self.replace(result, 'guide', 'A proposed edit.')
        report = self.check(inputs, result, mode='external_shadow')
        self.assertEqual(report['checks']['authority:guide']['reason'], 'PENDING_WRITE_AUTHORITY')
        self.assertTrue(any(q['check_id'] == 'authority:guide' for q in report['hitl_questions']))

    def test_human_record_requires_current_question_and_authenticated_owner(self):
        inputs, result = self.baseline()
        report = self.check(inputs, result)
        question = report['hitl_questions'][0]
        pin = report['report_sha256']
        record = dict(version='document-set-hitl-record-v1', record_id='decision-test',
                      report_sha256=pin, question_id=question['question_id'], actor='fixture-authorized',
                      decision='Supply a newly scoped request.')
        stored = dict(record=copy.deepcopy(record), actor_kind='human',
                      authorized_owner=question['decision_owner'], revoked=False)
        self.assertTrue(self.g3.bind_hitl_record(report, record, trusted_report_sha256=pin, lookup=lambda _: stored))
        stored['revoked'] = True
        self.assertFalse(self.g3.bind_hitl_record(report, record, trusted_report_sha256=pin, lookup=lambda _: stored))
        self.assertFalse(report['delivery_approved'])

    def test_independent_whitespace_policy_is_specific_to_exact_candidate(self):
        inputs, result = self.baseline()
        format_doc = next(d for d in self.fixture.contract['documents'] if d['document_id'] == 'format')
        original = format_doc['content']
        definition = dict(kind='reviewed_whitespace', source_sha256=format_doc['sha256'],
                          candidate_sha256=core._digest(original + '\n'),
                          basis='Fixture reviewer verified harmless terminal newline', issuer='Fixture owner')
        req = dict(version='document-set-requirements-v1', obligations=[], format_policies={'format': definition})
        for text, status in ((original + '\n', 'passed'), (original + '\n\n', 'unresolved')):
            self.replace(result, 'format', text)
            report = self.g3.verify_document_set(
                result, req, **inputs, mode='external_shadow', trusted_requirements_sha256=core.contract_digest(req),
                trusted_candidate_sha256=core.contract_digest(result))
            self.assertEqual(report['checks']['authority:format']['status'], status)

    def test_unrelated_trace_corruption_does_not_assert_move_unauthorized(self):
        inputs, result = self.baseline([self.fixture.task()])
        row = next(row for row in result['trace'] if row['output']['document_id'] == 'format')
        row['output']['start'] += 1
        report = self.check(inputs, result)
        self.assertEqual(report['checks']['lineage']['document_ids'], ['format'])
        self.assertEqual(report['checks']['authority:guide']['status'], 'passed')
        self.assertEqual(report['impact']['independent_task_ids'], ['task'])

    def test_definitive_omission_review_can_cite_verified_empty_target(self):
        self.fixture.update_text('guide', self.obligation()['source_refs'][0]['quote'] + '\n')
        self.fixture.refresh()
        inputs, result = self.baseline()
        self.replace(result, 'notes', '')
        obligations = [self.obligation(kind='semantic')]
        initial = self.check(inputs, result, obligations=obligations, mode='external_shadow')
        bindings = {k: v for k, v in initial['bindings'].items() if k != 'independent_review_sha256'}
        review = dict(bindings=bindings, reviewer_id='Independent fixture reviewer', reviews={
            'local-limit': dict(status='violated', reason='No operating conditions in the verified empty target',
                                evidence=initial['checks']['local-limit']['evidence'])})
        report = self.check(inputs, result, obligations=obligations, mode='external_shadow',
                            independent_review=review, trusted_review_sha256=core.contract_digest(review))
        self.assertEqual(report['checks']['local-limit']['status'], 'violated')

    def test_literal_inside_code_or_comment_does_not_verify_prose_exposure(self):
        sentence = self.obligation()['source_refs'][0]['quote']
        self.fixture.update_text('guide', sentence + '\n')
        self.fixture.refresh()
        inputs, result = self.baseline()
        for before, after in (('```text\n', '\n```\n'), ('<!--\n', '\n-->\n')):
            self.replace(result, 'notes', before + sentence + after)
            report = self.check(inputs, result, obligations=[self.obligation()], mode='external_shadow')
            self.assertEqual(report['checks']['local-limit']['status'], 'unresolved')

    def test_formatting_markup_around_same_words_needs_review(self):
        inputs, result = self.baseline()
        original = next(d['content'] for d in result['candidates'] if d['document_id'] == 'format')
        self.replace(result, 'format', original.replace('failed', '<em>failed</em>'))
        report = self.check(inputs, result, mode='external_shadow')
        self.assertEqual(report['checks']['authority:format']['status'], 'unresolved')

    def test_native_prerequisite_creates_question_without_blocking_independent_keep(self):
        self.fixture.contract['explicit_constraints'].append('Do not move paragraphs.')
        self.fixture.refresh()
        keep = self.fixture.task('KEEP', source='format', prefix='The', target='format', name='keep')
        inputs, result = self.baseline([self.fixture.task(), keep])
        report = self.check(inputs, result)
        self.assertEqual(report['impact']['held_task_ids'], ['task'])
        self.assertEqual(report['impact']['independent_task_ids'], ['keep'])
        question = next(q for q in report['hitl_questions'] if q['check_id'] == 'prerequisite:task')
        self.assertEqual(question['held_task_ids'], ['task'])
        self.assertTrue(question['evidence'])
