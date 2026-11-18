"""Red/green coverage for the pinned document-set candidate boundary."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import document_set as core
import document_set_analysis as analysis
import document_set_planning as planning
import document_set_reconstruction as execution
from ir_document_set_adapter import from_ir_input
from test_document_set_g2 import synthetic


class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.contract = synthetic()
        self.update_text('guide', '# Guide\n\nCollect the samples.\n')
        self.update_text('notes', '# Notes\n\nInstall the package.\n\nRecord the label.\n')
        self.refresh()

    def update_text(self, doc, text):
        row = next(d for d in self.contract['documents'] if d['document_id'] == doc)
        row.update(content=text, sha256=core._digest(text))
        row['provenance']['snapshot_sha256'] = row['sha256']

    def refresh(self):
        self.pin = core.contract_digest(self.contract)
        self.analysis = analysis.analyze_document_set(self.contract, trusted_contract_sha256=self.pin)

    def unit(self, doc, prefix=''):
        return next(u['unit_id'] for u in self.analysis['units']
                    if u['document_id'] == doc and u['kind'] == 'paragraph' and u['quote'].startswith(prefix))

    def task(self, action='MOVE', source='notes', prefix='Install', target='guide', name='task', **attrs):
        uid = self.unit(source, prefix)
        task = dict(task_id=name, action=action, unit_ids=[uid], target_document_id=target,
                    reason='Explicit test proposal', evidence_unit_ids=[uid], depends_on=[],
                    parameters={'placement': 'append'} if action == 'MOVE' else {})
        task.update(attrs)
        return task

    def place(self, **attrs):
        return self.task('PLACE', target='notes', parameters={
            'anchor_unit_id': self.unit('notes', 'Record'), 'position': 'after'}, **attrs)

    def inputs(self, tasks=(), *, allowed=None, documents=None):
        request = planning.make_request(list(tasks))
        request_pin = core.contract_digest(request)
        plan = planning.plan_document_set(self.contract, self.analysis, request,
                                          trusted_contract_sha256=self.pin, trusted_request_sha256=request_pin)
        self.assertEqual(plan['gate_state'], 'REVIEW', plan['reasons'])
        grant = execution.make_candidate_request(
            plan, task_ids=[t['task_id'] for t in plan['tasks']] if allowed is None else allowed,
            document_ids=[d['document_id'] for d in self.contract['documents'] if d['output_target']]
            if documents is None else documents)
        return dict(contract=self.contract, analysis=self.analysis, plan=plan, plan_request=request,
                    candidate_request=grant, trusted_contract_sha256=self.pin,
                    trusted_request_sha256=request_pin, trusted_candidate_request_sha256=core.contract_digest(grant))

    def assert_candidate(self, result):
        self.assertEqual(result['gate_state'], 'REVIEW', result)
        self.assertEqual(result['structure']['status'], 'passed')
        self.assertFalse(result['delivery_approved'])
        self.assertFalse(result['request_complete'])
        return {d['document_id']: d['content'] for d in result['candidates']}

    def test_single_keep_and_multiple_noop(self):
        for single in (False, True):
            if single:
                self.contract['documents'] = self.contract['documents'][2:3]
                self.contract['output_scopes'] = [dict(scope_id='notes', document_id='notes')]
                self.refresh()
            result = execution.reconstruct_document_set(**self.inputs())
            actual = self.assert_candidate(result)
            self.assertEqual(actual, {d['document_id']: d['content'] for d in self.contract['documents'] if d['output_target']})
            self.assertEqual(result['executed'], [])
            self.assertTrue(result['held'])

    def test_place_reorders_full_paragraphs(self):
        result = execution.reconstruct_document_set(**self.inputs([self.place()]))
        self.assertEqual(self.assert_candidate(result)['notes'], '# Notes\n\n\nRecord the label.\n\nInstall the package.\n')
        self.assertEqual(result['executed'], ['task'])

    def test_move_full_snapshots_and_trace(self):
        kwargs = self.inputs([self.task()])
        result = execution.reconstruct_document_set(**kwargs)
        texts = self.assert_candidate(result)
        self.assertEqual(result['executed'], ['task'])
        self.assertNotIn('Install the package.', texts['notes'])
        self.assertTrue(texts['guide'].endswith('\n\nInstall the package.\n'))
        self.assertEqual(execution.validate_candidate_result(result, **kwargs)['status'], 'passed')
        moved = next(r for r in result['trace'] if r['treatment'] == 'MOVE')
        self.assertEqual(moved['source']['document_id'], 'notes')
        self.assertEqual(moved['output']['document_id'], 'guide')
        for side, docs in (('source', self.contract['documents']), ('output', result['candidates'])):
            span = moved[side]
            doc = next(d for d in docs if d['document_id'] == span['document_id'])
            self.assertEqual(doc['sha256'], span['sha256'])
            self.assertEqual(doc['content'].encode()[span['byte_start']:span['byte_end']].decode(), moved['text'])

    def test_partial_hitl_leaves_condition_in_original(self):
        self.update_text('guide', '# Guide\n\nIf the alarm sounds, wait.\n')
        # Keep the held task disjoint from the placement and its evidence.
        self.contract['documents'][3]['access'] = 'edit'
        self.refresh()
        task = self.task(source='guide', prefix='If', target='format', name='conditional')
        result = execution.reconstruct_document_set(**self.inputs([task, self.place()]))
        self.assertIn('If the alarm sounds, wait.', self.assert_candidate(result)['guide'])
        self.assertEqual(result['executed'], ['task'])
        self.assertEqual(result['held'], ['conditional'])
        self.assertEqual(result['execution_state'], 'partial_candidate')

    def test_permissions_and_unimplemented(self):
        tasks = [
            self.task(target='policy', name='readonly'),
            self.task('REVISE', 'format', 'The attempt', 'format', 'format-revision',
                      parameters={'operation': 'REVISE', 'constraints': {'terminology': {'failed': 'worked'}}}),
            self.task('REMOVE', 'guide', 'Collect', 'guide', 'remove'),
            self.task('CONSOLIDATE', name='paraphrase', parameters={'summary': 'Some rewrite'}),
            self.task(target='new', name='new-document'),
        ]
        result = execution.reconstruct_document_set(**self.inputs(tasks))
        self.assert_candidate(result)
        self.assertEqual(result['executed'], [])
        self.assertEqual(set(result['denied']), {'readonly', 'format-revision', 'new-document'})
        self.assertEqual(set(result['unsupported']), {'remove', 'paraphrase'})

    def test_ungranted_task_and_document(self):
        for kwargs in (self.inputs([self.task()], allowed=[]), self.inputs([self.task()], documents=['notes'])):
            result = execution.reconstruct_document_set(**kwargs)
            self.assert_candidate(result)
            self.assertEqual(result['denied'], ['task'])
            self.assertEqual(result['executed'], [])

    def test_missing_or_unpinned_candidate_request(self):
        for change in (dict(candidate_request=None), dict(trusted_candidate_request_sha256=None)):
            kwargs = self.inputs([self.task()])
            kwargs.update(change)
            result = execution.reconstruct_document_set(**kwargs)
            self.assertEqual(result['gate_state'], 'FAIL')
            self.assertEqual(result['candidates'], [])

    def test_conflicts_and_cycle(self):
        for tasks in ([self.task(), self.place(name='other')],
                      [self.task(depends_on=['other']), self.task('KEEP', 'format', 'The attempt', 'format',
                                                                 'other', depends_on=['task'])]):
            result = execution.reconstruct_document_set(**self.inputs(tasks))
            self.assert_candidate(result)
            self.assertEqual(result['executed'], [])
            self.assertIn('task', result['held'])

    def test_competing_appends_are_held(self):
        other = self.task(prefix='Record', name='other')
        result = execution.reconstruct_document_set(**self.inputs([self.task(), other]))
        self.assert_candidate(result)
        self.assertEqual(result['held'], ['task', 'other'])
        self.assertEqual(result['executed'], [])

    def test_disjoint_structural_tasks_materialize_together(self):
        self.update_text('format', '# Minutes\n\nSort envelopes.\n\nFile receipts.\n')
        self.contract['documents'][3]['access'] = 'edit'
        self.refresh()
        other = self.task('PLACE', 'format', 'Sort', 'format', 'other', parameters={
            'anchor_unit_id': self.unit('format', 'File'), 'position': 'after'})
        result = execution.reconstruct_document_set(**self.inputs([self.task(), other]))
        texts = self.assert_candidate(result)
        self.assertEqual(result['executed'], ['task', 'other'])
        self.assertIn('Install the package.', texts['guide'])
        self.assertLess(texts['format'].index('File receipts.'), texts['format'].index('Sort envelopes.'))

    def test_original_and_destination_hash_mismatch(self):
        for index in (0, 2):
            kwargs = self.inputs([self.task()])
            kwargs['contract'] = copy.deepcopy(self.contract)
            kwargs['contract']['documents'][index]['sha256'] = '0' * 64
            result = execution.reconstruct_document_set(**kwargs)
            self.assertEqual(result['gate_state'], 'FAIL')
            self.assertEqual(result['candidates'], [])

    def test_stale_artifacts_and_resealed_plan(self):
        kwargs = self.inputs([self.task()])
        stale = copy.deepcopy(kwargs)
        self.update_text('guide', '# Guide\n\nCollect the sealed samples.\n')
        self.refresh()
        kwargs = self.inputs([self.task()])
        forged = copy.deepcopy(kwargs['plan'])
        forged['tasks'][0]['target_document_id'] = 'format'
        forged['plan_sha256'] = core.contract_digest({k: v for k, v in forged.items() if k != 'plan_sha256'})
        for changed in (dict(analysis=stale['analysis']), dict(plan=stale['plan']), dict(plan=forged),
                        dict(candidate_request=stale['candidate_request'],
                             trusted_candidate_request_sha256=stale['trusted_candidate_request_sha256'])):
            result = execution.reconstruct_document_set(**dict(kwargs, **changed))
            self.assertEqual(result['gate_state'], 'FAIL')
            self.assertEqual(result['candidates'], [])

    def test_old_plan_request_is_rejected_for_current_contract_and_analysis(self):
        old = self.inputs([self.task()])
        current = self.inputs([self.task(reason='Changed grounded instructions')])
        changed = dict(current, plan=old['plan'], plan_request=old['plan_request'])
        result = execution.reconstruct_document_set(**changed)
        self.assertEqual(result['gate_state'], 'FAIL')
        self.assertIn('UPSTREAM_BINDING_REJECTED:TRUSTED_REQUEST_MISMATCH', result['reasons'])

    def test_independent_validator_rejects_missing_duplicate_and_forged_output(self):
        kwargs = self.inputs([self.task()])
        result = execution.reconstruct_document_set(**kwargs)
        self.assert_candidate(result)
        def rewrite(result, doc, transform):
            row = next(d for d in result['candidates'] if d['document_id'] == doc)
            row['content'] = transform(row['content'])
            row['sha256'] = core._digest(row['content'])
        for mutate in (
            lambda r: r['candidates'].pop(),
            lambda r: r['trace'].append(r['trace'][0]),
            lambda r: r['executed'].append('other'),
            lambda r: r.update(delivery_approved=True),
            lambda r: r['structure'].update(delivery_approved=True, stage_transition_allowed=True),
            lambda r: r['output_scopes'][0].update(scope_id='forged-scope'),
            lambda r: r['trace'][0]['source'].update(start=False),
            lambda r: r['change_ledger']['notes'].clear(),
            lambda r: rewrite(r, 'guide', lambda t: t.replace('Install the package.\n', '')),
            lambda r: rewrite(r, 'guide', lambda t: t + 'Install the package.\n'),
            lambda r: rewrite(r, 'format', lambda t: t.replace('failed', 'worked')),
            lambda r: r['candidates'].append(dict(document_id='policy', source_path='policy.md',
                                                 source_sha256='a'*64, content='Forged', sha256=core._digest('Forged'))),
        ):
            changed = copy.deepcopy(result)
            mutate(changed)
            self.assertEqual(execution.validate_candidate_result(changed, **kwargs)['status'], 'failed')

    def test_render_failure_leaves_no_partial_outputs_or_input_mutation(self):
        kwargs = self.inputs([self.task()])
        frozen = copy.deepcopy(kwargs)
        with patch.object(execution, '_render_document', side_effect=[{'partial': True}, ValueError('test')]):
            result = execution.reconstruct_document_set(**kwargs)
        self.assertEqual(result['execution_state'], 'failed')
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['trace'], [])
        self.assertEqual(result['change_ledger'], {})
        self.assertEqual(result['executed'], [])
        self.assertEqual(kwargs, frozen)

    def test_source_and_destination_context_hold(self):
        for doc, text in (
            ('notes', '# Notes\n\nInstall the package.\n\nUse the previous procedure.\n'),
            ('notes', '# Notes\n\n## Internal\n\nInstall the package.\n'),
            ('guide', '# Guide\n\nUnless cleared, wait.\n'),
            ('guide', '# Guide\n\nCollect the samples.\n\nInstall the package.\n'),
        ):
            with self.subTest(doc=doc, text=text):
                self.setUp()
                self.update_text(doc, text)
                self.refresh()
                result = execution.reconstruct_document_set(**self.inputs([self.task()]))
                self.assert_candidate(result)
                self.assertEqual(result['held'], ['task'])
                self.assertEqual(result['executed'], [])

    def test_move_holds_polarity_conflict_and_explicit_structure_prohibition(self):
        self.update_text('guide', '# Guide\n\nDo not install the package.\n')
        self.refresh()
        result = execution.reconstruct_document_set(**self.inputs([self.task()]))
        self.assert_candidate(result)
        self.assertEqual(result['held'], ['task'])
        self.setUp()
        self.contract['documents'][2]['explicit_constraints'] = ['Do not move the installation paragraph.']
        self.refresh()
        result = execution.reconstruct_document_set(**self.inputs([self.task()]))
        self.assert_candidate(result)
        self.assertEqual(result['held'], ['task'])

    def test_explicit_english_and_korean_order_constraints_hold(self):
        for constraint in ('문단을 이동하지 마세요.', 'Keep the original paragraph order.',
                           '기존 문단 순서를 유지하세요.'):
            with self.subTest(constraint=constraint):
                self.contract['documents'][2]['explicit_constraints'] = [constraint]
                self.refresh()
                result = execution.reconstruct_document_set(**self.inputs([self.task()]))
                self.assert_candidate(result)
                self.assertEqual(result['held'], ['task'])

    def test_destination_plain_prohibition_holds_move(self):
        self.update_text('guide', '# Guide\n\nNo photography in storage.\n')
        self.refresh()
        result = execution.reconstruct_document_set(**self.inputs([self.task()]))
        self.assert_candidate(result)
        self.assertEqual(result['held'], ['task'])

    def test_unresolved_condition_reference_and_bom_hold(self):
        for paragraph in ('설치 완료 시 실행합니다.', '장비 준비 여부에 따라 실행합니다.',
                          'See the related procedure.', '\ufeffInstall the package.'):
            with self.subTest(paragraph=paragraph):
                self.update_text('notes', paragraph + '\n\nRecord the label.\n')
                self.refresh()
                task = self.task(prefix=paragraph)
                result = execution.reconstruct_document_set(**self.inputs([task]))
                self.assert_candidate(result)
                self.assertEqual(result['held'], ['task'])

    def test_unrelated_document_question_does_not_revoke_local_write_scope(self):
        self.contract['documents'][1]['pending_questions'] = ['Which source is current?']
        self.refresh()
        result = execution.reconstruct_document_set(**self.inputs([self.place()]))
        self.assert_candidate(result)
        self.assertEqual(result['executed'], ['task'])
        self.assertEqual(len(result['hitl_questions']), 1)
        self.assertEqual(result['execution_state'], 'partial_candidate')

    def test_place_rejects_cross_section_missing_and_identical_anchors(self):
        self.update_text('notes', '# Notes\n\nInstall the package.\n\n## Other\n\nRecord the label.\n')
        self.refresh()
        for task in (self.place(), self.task('PLACE', target='notes', parameters={
                'anchor_unit_id': 'missing', 'position': 'before'})):
            result = execution.reconstruct_document_set(**self.inputs([task]))
            self.assert_candidate(result)
            self.assertEqual(result['held'], ['task'])
        self.update_text('notes', '# Notes\n\nInstall the package.\n\nInstall the package.\n')
        self.refresh()
        paragraphs = [u['unit_id'] for u in self.analysis['units']
                      if u['document_id'] == 'notes' and u['kind'] == 'paragraph']
        task = self.task('PLACE', target='notes', parameters={'anchor_unit_id': paragraphs[1], 'position': 'after'})
        result = execution.reconstruct_document_set(**self.inputs([task]))
        self.assert_candidate(result)
        self.assertEqual(result['executed'], [])
        self.assertEqual(result['held'], ['task'])

    def test_missing_trailing_newline_and_crlf_keep_original_bytes(self):
        self.update_text('notes', '# Notes\r\n\r\nRecord the label.\r\n\r\n물품 목록을 작성한다.')
        self.refresh()
        result = execution.reconstruct_document_set(**self.inputs([self.task(prefix='물품')]))
        actual = self.assert_candidate(result)
        self.assertEqual(actual['notes'], '# Notes\r\n\r\nRecord the label.\r\n\r\n')
        self.assertTrue(actual['guide'].endswith('\n\n물품 목록을 작성한다.'))
        row = next(r for r in result['trace'] if r['treatment'] == 'MOVE')
        self.assertGreater(row['output']['byte_end'], row['output']['end'])

    def test_g2c_held_dependency_cannot_authorize_an_independent_write(self):
        parent = self.task('REVISE', 'guide', 'Collect', 'guide', 'parent',
                           parameters={'operation': 'REVISE', 'constraints': {'terminology': {'Collect': 'Gather'}}})
        child = self.place(depends_on=['parent'])
        result = execution.reconstruct_document_set(**self.inputs([parent, child]))
        self.assert_candidate(result)
        self.assertEqual(result['unsupported'], ['parent'])
        self.assertEqual(result['held'], ['task'])

    def test_candidate_scope_request_cannot_be_extended_with_a_self_hash(self):
        kwargs = self.inputs([self.task()], documents=['notes'])
        changed = copy.deepcopy(kwargs)
        changed['candidate_request']['document_ids'].append('guide')
        changed['candidate_request']['candidate_request_sha256'] = core.contract_digest(changed['candidate_request'])
        self.assertEqual(execution.reconstruct_document_set(**changed)['gate_state'], 'FAIL')

    def test_validation_failure_rolls_back_and_records_failed_work(self):
        kwargs = self.inputs([self.task()])
        with patch.object(execution, '_layouts', return_value={}):
            result = execution.reconstruct_document_set(**kwargs)
        self.assertEqual(result['execution_state'], 'failed')
        self.assertEqual(result['structure']['status'], 'failed')
        self.assertEqual(result['failed'], ['task'])
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['trace'], [])
        self.assertEqual(result['change_ledger'], {})

    def test_ir_outputs_preserve_scope_and_remain_review(self):
        root = Path(__file__).resolve().parents[2] / 'evaluation/integrated_reconstruction/inputs'
        for index, count in [(1, 2), (2, 2), (3, 1)]:
            with self.subTest(case=index):
                self.contract = from_ir_input(json.loads((root / f'IR-{index:03}.json').read_text()))
                self.refresh()
                result = execution.reconstruct_document_set(**self.inputs())
                actual = self.assert_candidate(result)
                self.assertEqual(len(actual), count)
                self.assertEqual(actual, {d['document_id']: d['content'] for d in self.contract['documents'] if d['output_target']})
                self.assertEqual(result['executed'], [])
                self.assertEqual(result['held'], ['request-decomposition'])
