"""Read-only real Markdown E2E and adversarial full reconstruction tests."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import expression
import organization
import pipeline
import reconstruction
import final_validator
import integration

DOC = "# 안내\n\n기본 기본 제한 시간은 30초다.\n\n## 설치\n\n설치를 수행한다.\n\n```sh\n./install.sh --port 8765\n```\n\n| 환경 | 버전 |\n| --- | --- |\n| Linux | 1.0 |\n\n> 원문 인용\n\n마지막 단락이다.\n"

def contract():
    return {'contract_id': 'integration-contract', 'version': '1', 'document_type': 'guide',
            'audience': '개발자', 'purpose': '설치 안내', 'language': 'ko', 'register': '한다체',
            'output_scopes': [{'scope_id': 'guide', 'document_id': 'doc-guide'}],
            'required_information': [], 'constraints': []}


class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.bundle = integration.markdown_bundle(DOC, contract())
        self.analysis = integration.analyze_source(self.bundle)
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.preview = expression.generate_revision_result(self.bundle, self.analysis, self.org)
        self.snaps = []

    def seal(self, value, field='revision_sha256'):
        expression.seal(value, field)

    def candidate(self, **kwargs):
        return reconstruction.reconstruct_documents(self.bundle, self.analysis, self.org, self.preview,
                                                     destination_snapshots=self.snaps, **kwargs)

    def report(self, result):
        return final_validator.validate_final_result(self.bundle, self.analysis, self.org, self.preview, result,
                                                     destination_snapshots=self.snaps)

    def uid(self, text):
        return next(u['id'] for u in self.analysis['units'] if text in u['statement'])

    def regenerate(self, **kwargs):
        self.preview = expression.generate_revision_result(self.bundle, self.analysis, self.org,
                                                           destination_snapshots=self.snaps, **kwargs)

    def test_full_source_preserved(self):
        result = self.candidate()
        self.assertEqual(result['delivery_state'], 'candidate')
        self.assertEqual(result['preview_fragments'], [])
        self.assertEqual(result['output_snapshots'][0]['content'], DOC)
        report = self.report(result)
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertEqual(report['checks']['FULL_COVERAGE'], 'passed')
        self.assertFalse(report['delivery_approved'])

    def test_one_span_compress_rest_of_document_exact(self):
        uid = self.uid('기본 기본')
        self.regenerate(operations={uid: 'COMPRESS'})
        result = self.candidate()
        self.assertEqual(result['output_snapshots'][0]['content'], DOC.replace('기본 기본', '기본'))
        self.assertEqual(self.report(result)['gate_state'], 'REVIEW')

    def test_safe_register_transform(self):
        self.bundle['writing_contract']['register'] = '합니다체'
        self.analysis = integration.analyze_source(self.bundle)
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.regenerate()
        result = self.candidate()
        self.assertIn('30초입니다.', result['output_snapshots'][0]['content'])
        self.assertEqual(self.report(result)['gate_state'], 'REVIEW')

    def test_unknown_semantic_rewrite_held(self):
        uid = self.uid('기본 기본')
        self.regenerate(generator=lambda r: {'text': '요청의 기본 제한은 30초다.' if r['unit_id'] == uid else r['before']})
        result = self.candidate()
        self.assertEqual(result['output_snapshots'][0]['content'], DOC)
        self.assertIn('EXPRESSION_CHANGE_HELD', {f['rule_id'] for f in result['findings']})

    def test_protected_syntax_preserved(self):
        result = self.candidate()
        output = result['output_snapshots'][0]['content']
        for block in pipeline.parse_markdown_blocks(self.bundle['document_snapshot']):
            if block['kind'] in {'heading', 'code_block', 'table', 'blockquote'}:
                self.assertIn(block['text'], output)

    def test_number_loss_blocks_candidate(self):
        uid = self.uid('기본 기본')
        self.regenerate(generator=lambda r: {'text': r['before'].replace('30초', '60초') if r['unit_id'] == uid else r['before']})
        result = self.candidate()
        self.assertEqual(result['delivery_state'], 'preview')
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def test_shared_exact_span_not_duplicated(self):
        dup = copy.deepcopy(self.analysis['units'][1])
        dup['id'] = 'shared'
        for e in dup['elements']:
            e['id'] += '-dup'
        self.analysis['units'].append(dup)
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.regenerate()
        result = self.candidate()
        self.assertEqual(result['output_snapshots'][0]['content'], DOC)
        self.assertEqual(len(result['trace']), len(self.analysis['units']))

    def test_conflicting_shared_edits_block(self):
        dup = copy.deepcopy(self.analysis['units'][1])
        dup['id'] = 'shared'
        self.analysis['units'].append(dup)
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.regenerate(operations={self.analysis['units'][1]['id']: 'COMPRESS'})
        result = self.candidate()
        self.assertEqual(result['delivery_state'], 'preview')
        self.assertIn('OVERLAPPING_REVISIONS', {f['rule_id'] for f in result['findings']})

    def test_whole_block_reorder_and_trace(self):
        moving, anchor = self.uid('마지막 단락'), self.uid('설치를 수행')
        plc = next(p for p in self.org['placements'] if p['unit_id'] == moving)
        plc['targets'][0].update(anchor_unit_id=anchor, anchor_relative_position='before')
        self.seal(self.org, 'plan_sha256')
        self.regenerate()
        result = self.candidate()
        output = result['output_snapshots'][0]['content']
        self.assertLess(output.index('마지막 단락'), output.index('설치를 수행'))
        self.assertEqual(self.report(result)['checks']['BIDIRECTIONAL_TRACE'], 'passed')

    def setup_move(self, condition=True):
        text = '# 원본\n\n로컬 실행이 가능하다.\n\n캐시가 있을 때만 동작한다.\n'
        self.bundle = integration.markdown_bundle(text, contract())
        self.analysis = integration.analyze_source(self.bundle)
        claim, cond = self.analysis['units'][1:]
        cond['relations'] = [{'kind': 'qualifies', 'target_unit_id': claim['id'], 'reason': '필수 캐시 조건'}]
        self.bundle['writing_contract']['output_scopes'].append({'scope_id': 'dest', 'document_id': 'doc-dest'})
        self.analysis['contract_sha256'] = pipeline.canonical_json_digest(self.bundle['writing_contract'])
        self.analysis['input_sha256'] = pipeline.canonical_json_digest(self.bundle)
        self.seal(self.analysis, 'analysis_sha256')
        content = '# 목적지\n\n기존 문서 내용이다.\n'
        self.snaps = [{'snapshot_id': 'dest-v1', 'document_id': 'doc-dest', 'version': '1',
                       'content': content, 'sha256': pipeline.digest_text(content), 'coverage': 'complete', 'media_type': 'text/markdown'}]
        moved = [claim['id'], cond['id']] if condition else [claim['id']]
        self.org = organization.generate_organization_plan(self.bundle, self.analysis,
                    candidate_actions={uid: {'action': 'MOVE', 'target_scope_id': 'dest'} for uid in moved},
                    destination_snapshots=self.snaps)
        if condition:
            self.regenerate()

    def test_atomic_move_full_source_and_destination(self):
        self.setup_move()
        result = self.candidate()
        self.assertEqual(result['delivery_state'], 'candidate')
        docs = {s['document_id']: s['content'] for s in result['output_snapshots']}
        self.assertNotIn('로컬 실행', docs['doc-guide'])
        self.assertIn('로컬 실행', docs['doc-dest'])
        self.assertIn('캐시가 있을 때만', docs['doc-dest'])
        self.assertIn('기존 문서 내용', docs['doc-dest'])
        self.assertEqual(self.report(result)['gate_state'], 'REVIEW')

    def test_condition_split_blocked(self):
        self.setup_move(condition=False)
        with self.assertRaises(ValueError):
            self.regenerate()

    def test_stale_destination_rejected(self):
        self.setup_move()
        result = self.candidate()
        self.snaps[0]['content'] += 'changed'
        self.snaps[0]['sha256'] = pipeline.digest_text(self.snaps[0]['content'])
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def test_partial_output_documents_blocked(self):
        self.setup_move()
        result = self.candidate()
        result['output_snapshots'].pop()
        self.seal(result)
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def test_forged_snapshot_digest_and_claim(self):
        result = self.candidate()
        result['output_snapshots'][0]['content'] += '\n암호화가 항상 보장된다.\n'
        self.seal(result)
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def test_rehashed_new_claim_blocked(self):
        result = self.candidate()
        snap = result['output_snapshots'][0]
        snap['content'] += '\n근거 없는 주장이다.\n'
        snap['sha256'] = pipeline.digest_text(snap['content'])
        self.seal(result)
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def test_missing_unit_trace_blocked(self):
        result = self.candidate()
        result['trace'].pop()
        self.seal(result)
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def test_forged_pass_blocked(self):
        result = self.candidate()
        result['delivery_approved'] = True
        result['gate_state'] = 'PASS'
        self.seal(result)
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def test_report_missing_mandatory_check_rejected(self):
        result = self.candidate()
        report = self.report(result)
        report['checks'].pop('PROTECTED_INFORMATION')
        self.seal(report, 'report_sha256')
        self.assertFalse(final_validator.verify_final_report(self.bundle, self.analysis, self.org, self.preview, result, report)['valid'])

    def test_stale_organization_plan_rejected(self):
        result = self.candidate()
        self.org['placements'][1]['targets'][0]['relative_order'] += 1
        self.seal(self.org, 'plan_sha256')
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def test_stale_analysis_rejected(self):
        result = self.candidate()
        self.analysis['units'][1]['statement'] += ' changed'
        self.seal(self.analysis, 'analysis_sha256')
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def rebuild_forged_layout(self, result):
        docs = {snap['document_id']: snap for snap in result['output_snapshots']}
        for doc, snap in docs.items():
            content = ''
            for row in result['block_ledger']:
                if row['output_document_id'] != doc or row.get('alias'):
                    continue
                row['output_start'], row['output_end'] = len(content), len(content) + len(row['text'])
                content += row['text']
            sha = pipeline.digest_text(content)
            snap.update(content=content, sha256=sha, snapshot_id=doc + ':candidate:' + sha[:12],
                        version='1.candidate.' + sha[:12])
        for trace in result['trace']:
            for source, out in zip(trace['source_spans'], trace['output_spans']):
                row = next(r for r in result['block_ledger'] if r['source_document_id'] == 'doc-guide'
                           and r['start'] <= source['start'] < source['end'] <= r['end'])
                start = row['output_start'] + source['start'] - row['start']
                doc = row['output_document_id']
                out.update(document_id=doc, snapshot_sha256=docs[doc]['sha256'], start=start,
                           end=start + len(source['quote']), quote=source['quote'])
        result['change_set'] = copy.deepcopy(result['block_ledger'])
        self.seal(result)

    def test_arbitrary_document_reorder_rejected(self):
        result = self.candidate()
        result['block_ledger'].reverse()
        self.rebuild_forged_layout(result)
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def test_destination_existing_content_cannot_be_moved_back(self):
        self.setup_move()
        result = self.candidate()
        row = next(r for r in result['block_ledger'] if r['source_document_id'] == 'doc-dest')
        row['output_document_id'] = 'doc-guide'
        self.rebuild_forged_layout(result)
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def setup_consolidation(self):
        self.bundle = integration.markdown_bundle('# 문서\n\n중복 문장이다.\n\n중복 문장이다.\n\n중복 문장이다.\n', contract())
        self.analysis = integration.analyze_source(self.bundle)
        uids = [u['id'] for u in self.analysis['units'][1:]]
        self.org = organization.generate_organization_plan(self.bundle, self.analysis,
                    consolidation_candidates=[{'id': 'cg', 'member_unit_ids': uids[:2], 'equivalence_basis': 'Exact standalone duplicate'}])
        self.regenerate()
        return uids

    def test_exact_duplicate_consolidation(self):
        self.setup_consolidation()
        result = self.candidate()
        self.assertEqual(result['delivery_state'], 'candidate')
        self.assertEqual(result['output_snapshots'][0]['content'].count('중복 문장이다.'), 2)
        self.assertEqual(self.report(result)['gate_state'], 'REVIEW')

    def test_unrelated_consolidation_cannot_remove_keep_occurrence(self):
        uids = self.setup_consolidation()
        result = self.candidate()
        last_span = self.analysis['units'][-1]['source_spans'][0]
        alias = next(r for r in result['block_ledger'] if r.get('alias'))
        row = next(r for r in result['block_ledger'] if r['start'] == last_span['start'])
        row.update(alias=True, treatment='CONSOLIDATE', group_id='cg',
                   output_start=alias['output_start'], output_end=alias['output_start']+len(row['text']))
        self.rebuild_forged_layout(result)
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def test_existing_section_heading_placement(self):
        uid = self.uid('기본 기본')
        plc = next(p for p in self.org['placements'] if p['unit_id'] == uid)
        plc['targets'][0]['section_path'] = ['설치']
        self.seal(self.org, 'plan_sha256')
        self.regenerate()
        result = self.candidate()
        output = result['output_snapshots'][0]['content']
        self.assertGreater(output.index('기본 기본'), output.index('## 설치'))
        self.assertEqual(self.report(result)['gate_state'], 'REVIEW')

    def test_unapproved_whitespace_cannot_change_markdown_structure(self):
        result = self.candidate()
        result['block_ledger'].insert(0, {'source_document_id': None, 'start': None, 'end': None,
             'text': '    ', 'treatment': 'SEPARATOR', 'output_document_id': 'doc-guide',
             'output_start': 0, 'output_end': 4, 'alias': False})
        self.rebuild_forged_layout(result)
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def test_wrong_duplicate_occurrence_trace_rejected(self):
        self.bundle = integration.markdown_bundle('# 문서\n\n중복 문장이다.\n\n중복 문장이다.\n', contract())
        self.analysis = integration.analyze_source(self.bundle)
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.regenerate()
        result = self.candidate()
        source = self.bundle['document_snapshot']['content']
        result['block_ledger'] = [{'source_document_id': 'doc-guide', 'start': 0, 'end': len(source),
             'text': source, 'treatment': 'KEEP', 'output_document_id': 'doc-guide',
             'output_start': 0, 'output_end': len(source), 'alias': False}]
        result['trace'][2]['output_spans'] = copy.deepcopy(result['trace'][1]['output_spans'])
        result['change_set'] = copy.deepcopy(result['block_ledger'])
        self.seal(result)
        self.assertEqual(self.report(result)['gate_state'], 'FAIL')

    def test_partial_overlapping_source_changes_blocked(self):
        original = self.analysis['units'][1]
        dup = copy.deepcopy(original)
        dup['id'] = 'partial-overlap'
        dup['quotes'][0]['quote'] = '기본 기본'
        blocks = {b['block_id']: b for b in self.analysis['blocks']}
        dup['source_spans'] = pipeline.resolve_block_quotes(dup['quotes'], blocks, self.bundle['document_snapshot'])
        dup['elements'][0]['quotes'] = copy.deepcopy(dup['quotes'])
        dup['elements'][0]['source_spans'] = copy.deepcopy(dup['source_spans'])
        self.analysis['units'].append(dup)
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.regenerate(operations={original['id']: 'COMPRESS'})
        result = self.candidate()
        self.assertEqual(result['delivery_state'], 'preview')
        self.assertIn('OVERLAPPING_REVISIONS', {f['rule_id'] for f in result['findings']})

    def test_condition_loss_blocks_full_candidate(self):
        self.setup_move()
        uid = self.uid('때만')
        self.regenerate(generator=lambda r: {'text': r['before'].replace('때만', '때도') if r['unit_id'] == uid else r['before']})
        self.assertEqual(self.report(self.candidate())['gate_state'], 'FAIL')

    def test_negation_loss_blocks_full_candidate(self):
        self.bundle = integration.markdown_bundle('# 안내\n\n추가 비용은 없다.\n', contract())
        self.analysis = integration.analyze_source(self.bundle)
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.regenerate(generator=lambda r: {'text': r['before'].replace('없다', '있다')})
        self.assertEqual(self.report(self.candidate())['gate_state'], 'FAIL')

    def test_cyclic_placement_is_held(self):
        first, second = self.uid('기본 기본'), self.uid('마지막 단락')
        for uid, anchor in ((first, second), (second, first)):
            plc = next(p for p in self.org['placements'] if p['unit_id'] == uid)
            plc['targets'][0].update(anchor_unit_id=anchor, anchor_relative_position='before')
        self.seal(self.org, 'plan_sha256')
        self.regenerate()
        self.assertEqual(self.candidate()['delivery_state'], 'preview')

    def test_rehashed_final_report_cannot_claim_pass(self):
        result = self.candidate()
        report = self.report(result)
        report['gate_state'] = 'PASS'
        report['delivery_approved'] = True
        self.seal(report, 'report_sha256')
        self.assertFalse(final_validator.verify_final_report(self.bundle, self.analysis, self.org, self.preview, result, report)['valid'])

    def test_nested_unchanged_spans_preserve_exact_trace(self):
        original = self.analysis['units'][1]
        dup = copy.deepcopy(original)
        dup['id'] = 'nested'
        dup['statement'] = '기본 기본'
        dup['quotes'][0]['quote'] = dup['statement']
        dup['source_spans'] = pipeline.resolve_block_quotes(dup['quotes'],
                 {b['block_id']: b for b in self.analysis['blocks']}, self.bundle['document_snapshot'])
        dup['elements'][0].update(value=dup['statement'], quotes=copy.deepcopy(dup['quotes']), source_spans=copy.deepcopy(dup['source_spans']))
        self.analysis['units'].append(dup)
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.regenerate()
        result = self.candidate()
        self.assertEqual(self.report(result)['checks']['BIDIRECTIONAL_TRACE'], 'passed')

    def test_move_into_unclosed_destination_fence_held(self):
        self.setup_move()
        self.snaps[0]['content'] = '# 목적지\n\n```sh\necho existing\n'
        self.snaps[0]['sha256'] = pipeline.digest_text(self.snaps[0]['content'])
        moved = [u['id'] for u in self.analysis['units'][1:]]
        self.org = organization.generate_organization_plan(self.bundle, self.analysis,
                candidate_actions={uid: {'action': 'MOVE', 'target_scope_id': 'dest'} for uid in moved},
                destination_snapshots=self.snaps)
        self.regenerate()
        result = self.candidate()
        self.assertEqual(result['delivery_state'], 'preview')
        self.assertEqual(self.report(result)['gate_state'], 'REVIEW')

    def test_move_with_bounded_style_change_has_exact_output_trace(self):
        self.setup_move()
        self.bundle['writing_contract']['register'] = '합니다체'
        self.analysis['contract_sha256'] = pipeline.canonical_json_digest(self.bundle['writing_contract'])
        self.analysis['input_sha256'] = pipeline.canonical_json_digest(self.bundle)
        self.seal(self.analysis, 'analysis_sha256')
        moved = [u['id'] for u in self.analysis['units'][1:]]
        self.org = organization.generate_organization_plan(self.bundle, self.analysis,
                candidate_actions={uid: {'action': 'MOVE', 'target_scope_id': 'dest'} for uid in moved},
                destination_snapshots=self.snaps)
        self.regenerate()
        result = self.candidate()
        self.assertEqual(self.report(result)['gate_state'], 'REVIEW')
        self.assertIn('동작합니다.', result['output_snapshots'][1]['content'])

    def test_destination_without_complete_coverage_is_held(self):
        self.setup_move()
        self.snaps[0].pop('coverage')
        result = self.candidate()
        self.assertEqual(result['delivery_state'], 'preview')
        self.assertEqual(self.report(result)['gate_state'], 'REVIEW')

    def test_incomplete_context_does_not_hide_approval_forgery(self):
        self.setup_move()
        result = self.candidate()
        result.update(delivery_state='preview', output_snapshots=[], delivery_approved=True)
        self.seal(result)
        self.snaps[0].pop('coverage')
        report = self.report(result)
        self.assertEqual(report['gate_state'], 'FAIL')
        self.assertIn('UNAUTHORIZED_FINAL_APPROVAL', {f['rule_id'] for f in report['findings']})


class EndToEndTests(unittest.TestCase):
    def test_real_markdown_file_cli_and_no_write(self):
        with tempfile.TemporaryDirectory() as directory:
            document, config = Path(directory) / 'guide.md', Path(directory) / 'contract.json'
            document.write_text(DOC)
            config.write_text(json.dumps(contract()))
            before = {p.name: p.read_bytes() for p in (document, config)}
            proc = subprocess.run([sys.executable, str(HERE / 'integration.py'), str(document), str(config)],
                                  capture_output=True, text=True, check=True)
            result = json.loads(proc.stdout)
            self.assertEqual(result['revision_result']['delivery_state'], 'candidate')
            self.assertEqual(result['final_report']['gate_state'], 'REVIEW')
            self.assertEqual(before, {p.name: p.read_bytes() for p in (document, config)})
            self.assertEqual(len(list(Path(directory).iterdir())), 2)

    def test_repeat_execution_has_identical_document_candidates(self):
        bundle = integration.markdown_bundle(DOC, contract())
        first, second = integration.run_pipeline(bundle), integration.run_pipeline(bundle)
        self.assertEqual(first['revision_result']['output_snapshots'], second['revision_result']['output_snapshots'])
        self.assertEqual(first['final_report']['checks'], second['final_report']['checks'])
        self.assertFalse(first['stage_transition_allowed'])

    def test_invalid_analysis_stops_without_generating(self):
        bundle = integration.markdown_bundle(DOC, contract())
        analysis = integration.analyze_source(bundle)
        analysis['snapshot_sha256'] = 'stale'
        result = integration.run_pipeline(bundle, analysis=analysis)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertEqual(result['controller']['responsible_module'], 'information_extraction_analysis')
        self.assertIsNone(result['revision_result'])

    def test_controller_routes_and_invalidates(self):
        controller = integration.RevisionController()
        result = controller.stop([{'rule_id': 'MOVE_SEVERS_REQUIRED_CONDITION', 'severity': 'ERROR'}])
        self.assertEqual(result['responsible_module'], 'information_organization')
        self.assertIn('expression', result['invalidated_artifacts'])
        self.assertEqual(result['retry_count'], 0)

    def test_controller_invalidates_stored_descendants(self):
        artifacts = {'analysis': {'id': 'keep'}, 'organization': {}, 'expression': {},
                     'reconstruction': {}, 'final_report': {}}
        controller = integration.RevisionController(artifacts)
        decision = controller.stop([{'rule_id': 'MOVE_SEVERS_REQUIRED_CONDITION', 'severity': 'ERROR'}])
        self.assertEqual(set(artifacts), {'analysis'})
        self.assertEqual(decision['last_gate_state'], 'FAIL')

    def test_controller_revalidates_current_artifacts(self):
        bundle = integration.markdown_bundle(DOC, contract())
        outcome = integration.run_pipeline(bundle)
        result = outcome['revision_result']
        result['delivery_approved'] = True
        expression.seal(result, 'revision_sha256')
        decision = integration.RevisionController().revalidate(bundle, outcome['analysis'],
                         outcome['organization_plan'], outcome['expression_preview'], result)
        self.assertEqual(decision['report']['gate_state'], 'FAIL')
        self.assertEqual(decision['controller']['state'], 'STOPPED')

    def test_generation_execution_error_stops_without_retry(self):
        bundle = integration.markdown_bundle(DOC, contract())
        def broken(request):
            raise RuntimeError('private generator failure')
        result = integration.run_pipeline(bundle, generator=broken)
        self.assertEqual(result['status'], 'STOPPED')
        self.assertEqual(result['controller']['responsible_module'], 'expression_refinement')
        self.assertEqual(result['controller']['retry_count'], 0)
        self.assertEqual(result['final_report']['gate_state'], 'REVIEW')
        self.assertIn('GENERATION_ERROR', {f['rule_id'] for f in result['final_report']['findings']})


if __name__ == '__main__':
    unittest.main()
