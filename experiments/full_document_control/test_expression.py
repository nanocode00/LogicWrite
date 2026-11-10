"""Source-bound Expression previews and independent anti-forgery counterexamples."""
import copy
from contextlib import redirect_stdout, redirect_stderr
import io
import logging
from unittest.mock import patch
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent

def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

expression = load('expression')
validator = load('expression_validator')
test_org = load('test_organization')
pipeline = test_org.pipeline
organization = test_org.organization


class ExpressionTests(unittest.TestCase):
    def setUp(self):
        base = test_org.InformationOrganizationTests()
        base.setUp()
        self.bundle, self.analysis = base.bundle, base.analysis
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)

    def result(self, generator=None, operations=None):
        return expression.generate_revision_result(
            self.bundle, self.analysis, self.org, generator=generator, operations=operations)

    def validate(self, result):
        return validator.validate_expression_result(self.bundle, self.analysis, self.org, result)

    def rewrite(self, uid, text):
        return self.result(generator=lambda request: {'text': text if request['unit_id'] == uid else request['before']})

    def seal(self, obj, field='revision_sha256'):
        obj[field] = pipeline.canonical_json_digest({k: v for k, v in obj.items() if k != field})

    def alter_text(self, result, uid, text):
        fragment = next(f for f in result['preview_fragments'] if f['unit_id'] == uid)
        fragment.update(content=text, sha256=pipeline.digest_text(text))
        for change in result['change_set']:
            if change['fragment_id'] == fragment['fragment_id']:
                change.update(after=text, after_sha256=fragment['sha256'],
                              operation='KEEP' if change['before'] == text else 'REVISE')
                change['output_span']['end'] = len(text)
        for trace in result['trace']:
            if trace['output_spans'][0]['fragment_id'] == fragment['fragment_id']:
                trace['output_spans'][0].update(end=len(text), snapshot_sha256=fragment['sha256'])
                trace['treatment'] = 'KEEP' if trace['source_spans'][0]['quote'] == text else 'REVISE'
        self.seal(result)

    def assert_code(self, result, code, state='FAIL'):
        report = self.validate(result)
        self.assertEqual(report['gate_state'], state, report)
        self.assertIn(code, {f['rule_id'] for f in report['findings']}, report)
        self.assertFalse(report['delivery_approved'])
        self.assertFalse(report['next_stage_allowed'])

    def test_real_register_rewrite(self):
        self.bundle['writing_contract']['register'] = '합니다체'
        self.analysis['contract_sha256'] = pipeline.canonical_json_digest(self.bundle['writing_contract'])
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        result = self.result()
        timeout = next(f for f in result['preview_fragments'] if f['unit_id'] == 'u-timeout')
        self.assertEqual(timeout['content'], '기본 요청 제한 시간은 30초입니다.')
        self.assertNotEqual(timeout['content'], timeout['source_span']['quote'])
        self.assertEqual(self.validate(result)['gate_state'], 'REVIEW')

    def test_compress_is_real_edit(self):
        self.assertEqual(expression.DeterministicGenerator().generate({
            'before': '설치 설치 절차를 확인한다.', 'operation': 'COMPRESS',
            'constraints': {'register': '한다체', 'terminology': {}}, 'excluded': False})['text'],
            '설치 절차를 확인한다.')

    def test_natural_rewrite_stays_semantic_review(self):
        result = self.rewrite('u-timeout', '요청의 기본 제한 시간은 30초다.')
        report = self.validate(result)
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertIn('SEMANTIC_EQUIVALENCE_UNVERIFIED', {f['rule_id'] for f in report['findings']})

    def test_quantity_unit_and_version_distortion(self):
        for uid, text in [('u-timeout', '기본 요청 제한 시간은 30분이다.'),
                          ('u-timeout', '기본 요청 제한 시간은 60초다.'),
                          ('u-runtime-overview', '런타임 v9.0.0은 로컬 실행을 지원한다.')]:
            with self.subTest(text=text):
                self.assert_code(self.rewrite(uid, text), 'PROTECTED_INFORMATION_LOSS')

    def test_negation_loss(self):
        self.assert_code(self.rewrite('u-cond-macos-manual',
            '- macOS 패키지는 초기 실험 빌드이므로 자동 업데이트를 지원하며 수동으로 재설치해야 한다.'),
            'PROTECTED_INFORMATION_LOSS')

    def test_condition_loss(self):
        self.assert_code(self.rewrite('u-cond-offline-cache', '- 오프라인 모드는 동작한다.'),
                         'PROTECTED_INFORMATION_LOSS')

    def test_scope_overstatement(self):
        self.assert_code(self.rewrite('u-cond-macos-manual',
            '- macOS 패키지는 모든 환경에서 자동 업데이트를 완벽하게 지원한다.'),
            'PROTECTED_INFORMATION_LOSS')

    def test_command_is_excluded(self):
        self.assert_code(self.rewrite('u-code-install', 'rm -rf /tmp/runtime'), 'EXCLUDED_CONTEXT_MODIFIED')

    def test_identifiers_preserved(self):
        self.assert_code(self.rewrite('u-table-ubuntu', '| Ubuntu | 22.04 | other.tar.gz |'),
                         'EXCLUDED_CONTEXT_MODIFIED')

    def test_unsupported_new_assertion(self):
        result = self.rewrite('u-timeout', '기본 요청 제한 시간은 30초다. AES-256 암호화를 지원한다.')
        self.assert_code(result, 'UNSUPPORTED_CLAIM')

    def test_unrecognized_addition_review(self):
        result = self.rewrite('u-timeout', '기본 요청 제한 시간은 30초다. 고양이가 설정을 관리한다.')
        self.assert_code(result, 'SEMANTIC_EQUIVALENCE_UNVERIFIED', state='REVIEW')

    def test_stale_analysis(self):
        result = self.result()
        self.analysis['units'][2]['statement'] += ' changed'
        self.seal(self.analysis, 'analysis_sha256')
        self.assert_code(result, 'STALE_EXPRESSION_INPUT')

    def test_stale_organization(self):
        result = self.result()
        self.org['placements'][0]['targets'][0]['relative_order'] += 1
        self.seal(self.org, 'plan_sha256')
        self.assert_code(result, 'STALE_EXPRESSION_INPUT')

    def test_missing_unit(self):
        result = self.result()
        result['preview_fragments'].pop()
        self.seal(result)
        self.assert_code(result, 'EXPRESSION_COVERAGE_MISMATCH')

    def test_forged_pass_and_delivery(self):
        for field in ('gate_state', 'delivery_approved', 'next_stage_allowed'):
            with self.subTest(field=field):
                result = self.result()
                result[field] = 'PASS' if field == 'gate_state' else True
                self.seal(result)
                self.assert_code(result, 'UNAUTHORIZED_EXPRESSION_APPROVAL')

    def test_rehashed_preview_cannot_become_candidate(self):
        result = self.result()
        result['delivery_state'] = 'candidate'
        self.seal(result)
        self.assert_code(result, 'UNSUPPORTED_DELIVERY_STATE')

    def test_rehashed_output_is_independently_audited(self):
        result = self.result()
        self.alter_text(result, 'u-timeout', '기본 요청 제한 시간은 60초다.')
        self.assert_code(result, 'PROTECTED_INFORMATION_LOSS')

    def test_rehashed_expression_plan_cannot_move(self):
        result = self.result()
        result['expression_plan']['entries'][0]['placement']['targets'][0]['document_id'] = 'evil'
        self.seal(result['expression_plan'], 'plan_sha256')
        self.seal(result)
        self.assert_code(result, 'UNAUTHORIZED_ORGANIZATION_CHANGE')

    def test_expression_cannot_remove_or_add(self):
        for operation in ('REMOVE', 'MOVE', 'ADD', 'CONSOLIDATE'):
            with self.subTest(operation=operation):
                with self.assertRaises(ValueError):
                    self.result(operations={'u-timeout': operation})

    def test_preview_under_upstream_review(self):
        preview = expression.create_expression_preview(self.bundle, self.analysis, self.org)
        self.assertEqual(preview['revision_result']['delivery_state'], 'preview')
        self.assertEqual(preview['revision_result']['output_snapshots'], [])
        self.assertEqual(preview['validation_report']['gate_state'], 'REVIEW')
        self.assertFalse(preview['next_stage_allowed'])

    def test_authorized_path_not_implemented(self):
        decision = expression.execute_authorized_expression(self.bundle, self.analysis, self.org)
        self.assertEqual(decision['status'], 'NOT_IMPLEMENTED')
        self.assertFalse(decision['next_stage_allowed'])

    def test_adapter_cannot_mutate_inputs_or_self_approve(self):
        before = copy.deepcopy((self.bundle, self.analysis, self.org))
        def hostile(request):
            request['before'] = 'tampered'
            request['constraints'].clear()
            return {'text': '기본 요청 제한 시간은 30초다.', 'gate_state': 'PASS'}
        result = self.result(hostile)
        self.assertEqual((self.bundle, self.analysis, self.org), before)
        self.assert_code(result, 'GENERATOR_APPROVAL_CLAIM')

    def test_generator_error_preserves_original(self):
        def broken(request):
            raise RuntimeError('unavailable')
        result = self.result(broken)
        self.assertTrue(all(c['before'] == c['after'] for c in result['change_set']))
        self.assert_code(result, 'GENERATION_ERROR', state='REVIEW')

    def test_trace_binds_actual_source_and_output(self):
        result = self.result()
        snapshot = self.bundle['document_snapshot']
        fragments = {f['fragment_id']: f for f in result['preview_fragments']}
        for trace in result['trace']:
            source, out = trace['source_spans'][0], trace['output_spans'][0]
            self.assertEqual(snapshot['content'][source['start']:source['end']], source['quote'])
            self.assertEqual(fragments[out['fragment_id']]['content'][out['start']:out['end']],
                             fragments[out['fragment_id']]['content'])

    def test_tampered_source_trace_rejected(self):
        result = self.result()
        result['trace'][0]['source_spans'][0]['start'] += 1
        self.seal(result)
        self.assert_code(result, 'EXPRESSION_TRACE_MISMATCH')

    def test_forged_clean_findings_do_not_hide_loss(self):
        result = self.rewrite('u-timeout', '기본 요청 제한 시간은 60초다.')
        result['findings'] = []
        self.seal(result)
        self.assert_code(result, 'PROTECTED_INFORMATION_LOSS')

    def test_explicit_terms_and_forbidden_terms(self):
        self.bundle['writing_contract']['constraints'] += ['TERM: 런타임 => Runtime', 'FORBID: 완벽']
        self.analysis['contract_sha256'] = pipeline.canonical_json_digest(self.bundle['writing_contract'])
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        result = self.result()
        text = next(f['content'] for f in result['preview_fragments'] if f['unit_id'] == 'u-runtime-overview')
        self.assertIn('Runtime', text)
        self.assert_code(self.rewrite('u-timeout', '기본 요청 제한 시간은 30초다. 완벽하다.'),
                         'CONTRACT_TERM_VIOLATION')

    def test_register_violation(self):
        self.assert_code(self.rewrite('u-timeout', '기본 요청 제한 시간은 30초입니다.'),
                         'CONTRACT_REGISTER_VIOLATION')

    def test_unhashed_output_corruption(self):
        result = self.result()
        result['preview_fragments'][0]['content'] = 'changed'
        self.assert_code(result, 'REVISION_DIGEST_MISMATCH')

    def test_plan_preserves_units_and_constraints(self):
        result = self.result()
        plan = result['expression_plan']
        self.assertEqual({e['unit_id'] for e in plan['entries']}, {u['id'] for u in self.analysis['units']})
        self.assertEqual(plan['constraints']['register'], self.bundle['writing_contract']['register'])
        self.assertEqual(plan['organization_ref']['plan_sha256'], self.org['plan_sha256'])
        self.assertTrue(all(e['source_spans'] and e['protected_elements'] for e in plan['entries']))

    def reset_source(self, old, new):
        self.bundle['document_snapshot']['content'] = self.bundle['document_snapshot']['content'].replace(old, new)
        self.bundle['document_snapshot']['sha256'] = pipeline.digest_text(self.bundle['document_snapshot']['content'])
        response = test_org.test_pipeline.make_valid_window_response(self.bundle)
        def replace(value):
            if isinstance(value, str):
                return value.replace(old, new)
            if isinstance(value, list):
                return [replace(v) for v in value]
            if isinstance(value, dict):
                return {k: replace(v) for k, v in value.items()}
            return value
        response = replace(response)
        self.analysis = pipeline.assemble_document_analysis(self.bundle, [json.dumps(response)])
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)

    def test_compress_end_to_end(self):
        self.reset_source('기본 요청 제한 시간은 30초다.', '기본 기본 요청 제한 시간은 30초다.')
        result = self.result(operations={'u-timeout': 'COMPRESS'})
        fragment = next(f for f in result['preview_fragments'] if f['unit_id'] == 'u-timeout')
        self.assertEqual(fragment['content'], '기본 요청 제한 시간은 30초다.')
        self.assertEqual(self.validate(result)['gate_state'], 'REVIEW')

    def test_inline_quote_immutable(self):
        self.reset_source('기본 요청 제한 시간은 30초다.', '기본 요청 제한 시간은 30초다. "원문 인용"')
        self.assert_code(self.rewrite('u-timeout', '기본 요청 제한 시간은 30초다. "변경 인용"'),
                         'EXCLUDED_CONTEXT_MODIFIED')

    def test_url_immutable(self):
        self.reset_source('기본 요청 제한 시간은 30초다.', '기본 요청 제한 시간은 30초다. https://example.org/a')
        self.assert_code(self.rewrite('u-timeout', '기본 요청 제한 시간은 30초다. https://example.org/b'),
                         'EXCLUDED_CONTEXT_MODIFIED')

    def test_partial_inline_context_is_excluded(self):
        self.reset_source('기본 요청 제한 시간은 30초다.', '"기본 요청 제한 시간은 30초다."')
        # Restrict the unit to the interior of the quoted text; context still protects it.
        unit = next(u for u in self.analysis['units'] if u['id'] == 'u-timeout')
        unit['quotes'][0]['quote'] = '기본 요청 제한 시간은 30초다.'
        blocks = {b['block_id']: b for b in self.analysis['blocks']}
        unit['source_spans'] = pipeline.resolve_block_quotes(unit['quotes'], blocks, self.bundle['document_snapshot'])
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.assert_code(self.rewrite('u-timeout', '기본 요청 제한 시간은 30초입니다.'),
                         'EXCLUDED_CONTEXT_MODIFIED')

    def test_explicit_preserve_literal(self):
        self.bundle['writing_contract']['constraints'].append('PRESERVE: 기본 요청 제한 시간')
        self.analysis['contract_sha256'] = pipeline.canonical_json_digest(self.bundle['writing_contract'])
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.assert_code(self.rewrite('u-timeout', '요청의 기본 제한 시간은 30초다.'),
                         'EXCLUDED_CONTEXT_MODIFIED')

    def test_unknown_operation_unit_rejected(self):
        with self.assertRaises(ValueError):
            self.result(operations={'unknown': 'REVISE'})

    def test_duplicate_fragment(self):
        result = self.result()
        result['preview_fragments'].append(copy.deepcopy(result['preview_fragments'][0]))
        self.seal(result)
        self.assert_code(result, 'EXPRESSION_COVERAGE_MISMATCH')

    def test_invented_unit(self):
        result = self.result()
        result['expression_plan']['entries'][0]['unit_id'] = 'invented'
        self.seal(result['expression_plan'], 'plan_sha256')
        self.seal(result)
        self.assert_code(result, 'EXPRESSION_COVERAGE_MISMATCH')

    def test_invalid_upstream_never_calls_generator(self):
        self.org['placements'][0]['action'] = 'REMOVE'
        self.seal(self.org, 'plan_sha256')
        calls = []
        with self.assertRaises(ValueError):
            self.result(generator=lambda request: calls.append(request))
        self.assertEqual(calls, [])

    def test_forged_upstream_report_rejected(self):
        result = self.result()
        upstream = pipeline.validate_analysis_gate(self.bundle, self.analysis)
        upstream.update(gate_state='PASS', delivery_approved=True, next_stage_allowed=True)
        self.seal(upstream, 'report_sha256')
        report = validator.validate_expression_result(self.bundle, self.analysis, self.org, result,
                                                       validation_report=upstream)
        self.assertEqual(report['gate_state'], 'FAIL')
        self.assertFalse(report['next_stage_allowed'])

    def test_rehashed_contract_constraint_override(self):
        result = self.result()
        result['expression_plan']['constraints']['register'] = '해요체'
        self.seal(result['expression_plan'], 'plan_sha256')
        self.seal(result)
        self.assert_code(result, 'CONTRACT_CONSTRAINT_MISMATCH')

    def test_malformed_result_fails_closed(self):
        for value in (None, {}, [], {'expression_plan': None}):
            with self.subTest(value=value):
                self.assertEqual(self.validate(value)['gate_state'], 'FAIL')

    def test_multi_span_units_all_tracked(self):
        unit = next(u for u in self.analysis['units'] if u['id'] == 'u-runtime-overview')
        other = next(u for u in self.analysis['units'] if u['id'] == 'u-timeout')
        unit['quotes'].extend(copy.deepcopy(other['quotes']))
        unit['source_spans'].extend(copy.deepcopy(other['source_spans']))
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        result = self.result()
        self.assertEqual(len(result['preview_fragments']), len(self.analysis['units']) + 1)
        self.assertEqual(self.validate(result)['gate_state'], 'REVIEW')

    def test_plan_protected_element_cannot_be_deleted(self):
        result = self.result()
        result['expression_plan']['entries'][2]['protected_elements'] = []
        self.seal(result['expression_plan'], 'plan_sha256')
        self.seal(result)
        self.assert_code(result, 'EXPRESSION_TRACE_MISMATCH')

    def test_stale_snapshot_and_contract(self):
        result = self.result()
        self.bundle['writing_contract']['purpose'] += ' changed'
        self.assert_code(result, 'STALE_EXPRESSION_INPUT')

    def test_cli_preview_without_overwriting_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, obj in [('bundle', self.bundle), ('analysis', self.analysis), ('organization', self.org)]:
                path = Path(directory) / (name + '.json')
                path.write_text(json.dumps(obj, ensure_ascii=False))
                paths.append(path)
            originals = [p.read_bytes() for p in paths]
            proc = subprocess.run(['python3', str(HERE / 'expression.py'), *map(str, paths)],
                                  capture_output=True, text=True, check=True)
            preview = json.loads(proc.stdout)
            self.assertEqual(preview['revision_result']['delivery_state'], 'preview')
            self.assertFalse(preview['next_stage_allowed'])
            self.assertEqual([p.read_bytes() for p in paths], originals)

    def test_negative_ending_style_change_is_not_information_loss(self):
        self.reset_source('기본 요청 제한 시간은 30초다.', '기본 요청 제한 시간은 30초이며 예외는 없다.')
        self.bundle['writing_contract']['register'] = '합니다체'
        self.analysis['contract_sha256'] = pipeline.canonical_json_digest(self.bundle['writing_contract'])
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        result = self.result()
        self.assertTrue(any('없습니다.' in f['content'] for f in result['preview_fragments']))
        self.assertEqual(self.validate(result)['gate_state'], 'REVIEW')

    def test_hangul_adjacent_new_number_is_detected(self):
        self.assert_code(self.rewrite('u-timeout', '기본 요청 제한 시간은 30초다. 최대60초다.'),
                         'PROTECTED_INFORMATION_LOSS')

    def test_canonical_term_may_contain_alias(self):
        self.bundle['writing_contract']['constraints'].append('TERM: 런타임 => 런타임 환경')
        self.analysis['contract_sha256'] = pipeline.canonical_json_digest(self.bundle['writing_contract'])
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        result = self.result()
        self.assertEqual(self.validate(result)['gate_state'], 'REVIEW')
        request = {'before': '런타임 환경을 설치한다.', 'operation': 'REVISE', 'excluded': False,
                   'constraints': {'register': '한다체', 'terminology': {'런타임': '런타임 환경'}}}
        self.assertEqual(expression.DeterministicGenerator().generate(request)['text'], request['before'])

    def test_style_violation_in_nonfinal_sentence(self):
        self.assert_code(self.rewrite('u-timeout', '기본 요청 제한 시간은 30초입니다. 설정을 확인한다.'),
                         'CONTRACT_REGISTER_VIOLATION')

    def test_generator_passed_true_is_self_approval(self):
        result = self.result(generator=lambda request: {'text': request['before'], 'passed': True})
        self.assert_code(result, 'GENERATOR_APPROVAL_CLAIM')

    def test_approval_claim_inside_fragment_or_context(self):
        for nested in (False, True):
            with self.subTest(nested=nested):
                result = self.result()
                fragment = result['preview_fragments'][0]
                if nested:
                    fragment['context']['gate_state'] = 'PASS'
                else:
                    fragment['delivery_approved'] = True
                self.seal(result)
                self.assert_code(result, 'UNAUTHORIZED_EXPRESSION_APPROVAL')

    def test_generator_metadata_is_not_retained(self):
        marker = 'PRIVATE_METADATA_SENTINEL'
        result = self.result(generator=lambda r: {'text': r['before'], 'api_key': marker,
                              'internal_logs': [marker], 'metadata': {'token': marker}})
        encoded = json.dumps(result)
        self.assertNotIn(marker, encoded)
        for fragment in result['preview_fragments']:
            record = fragment['generation']
            self.assertEqual(set(record), {'status', 'approval_claim_detected', 'error_code', 'receipt_id'})
            self.assertNotIn('response', record)
            self.assertNotIn('text', record)
        self.assertNotIn(marker, json.dumps(self.validate(result)))

    def test_ignored_nonserializable_metadata_does_not_fail_generation(self):
        result = self.result(generator=lambda r: {'text': r['before'], 'unneeded': object()})
        self.assertTrue(all(f['generation']['status'] == 'completed' for f in result['preview_fragments']))
        self.assertNotIn('GENERATION_ERROR', {f['rule_id'] for f in self.validate(result)['findings']})

    def test_cli_drops_response_metadata_and_adapter_prints(self):
        marker = 'PRIVATE_CLI_SENTINEL'
        class NoisyGenerator:
            def generate(self, request):
                print(marker)
                print(marker, file=__import__('sys').stderr)
                return {'text': request['before'], 'credential': marker, 'log': marker}
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, obj in [('bundle', self.bundle), ('analysis', self.analysis), ('org', self.org)]:
                path = Path(directory) / (name + '.json')
                path.write_text(json.dumps(obj))
                paths.append(str(path))
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(expression, 'DeterministicGenerator', NoisyGenerator), redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(expression.main(paths), 0)
            self.assertNotIn(marker, stdout.getvalue() + stderr.getvalue())
            self.assertEqual(json.loads(stdout.getvalue())['revision_result']['delivery_state'], 'preview')

    def test_approval_signal_survives_metadata_filter(self):
        for claim in ({'gate_state': 'PASS'}, {'delivery_approved': True},
                      {'approved': True}, {'nested': {'passed': True}}):
            with self.subTest(claim=claim):
                result = self.result(generator=lambda r: {'text': r['before'], **claim})
                self.assertTrue(all(f['generation'].get('approval_claim_detected') is True
                                    for f in result['preview_fragments']))
                self.assert_code(result, 'GENERATOR_APPROVAL_CLAIM')

    def test_generation_error_cannot_be_passed_check(self):
        self.bundle['writing_contract']['constraints'] = []
        self.analysis['contract_sha256'] = pipeline.canonical_json_digest(self.bundle['writing_contract'])
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        def broken(request):
            raise RuntimeError('PRIVATE_EXCEPTION_SENTINEL')
        result = self.result(broken)
        self.assertTrue(all(c['before'] == c['after'] for c in result['change_set']))
        report = self.validate(result)
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertEqual(report['expression_checks_state'], 'unresolved')
        self.assertNotIn('PRIVATE_EXCEPTION_SENTINEL', json.dumps(result) + json.dumps(report))

    def test_invalid_responses_restore_original_and_remain_unresolved(self):
        for response in (None, [], {}, {'text': ''}, {'text': 4}):
            with self.subTest(response=response):
                result = self.result(generator=lambda r: response)
                self.assertTrue(all(c['before'] == c['after'] for c in result['change_set']))
                self.assertTrue(all(f['generation'].get('error_code') == 'INVALID_RESPONSE'
                                    for f in result['preview_fragments']))
                report = self.validate(result)
                self.assertEqual(report['gate_state'], 'REVIEW')
                self.assertEqual(report['expression_checks_state'], 'unresolved')

    def test_invalid_response_does_not_hide_approval_claim(self):
        result = self.result(generator=lambda r: {'text': None, 'delivery_approved': True})
        self.assert_code(result, 'GENERATOR_APPROVAL_CLAIM')

    def test_forged_success_receipt_rejected_even_after_rehash(self):
        def broken(request):
            raise RuntimeError('unavailable')
        result = self.result(broken)
        result['findings'] = []
        for fragment in result['preview_fragments']:
            fragment['generation']['status'] = 'completed'
            fragment['generation'].pop('error_type', None)
            fragment['generation']['error_code'] = None
        self.seal(result)
        self.assert_code(result, 'GENERATION_RECORD_MISMATCH')

    def test_cleared_generation_and_findings_never_pass_checks(self):
        result = self.result(generator=lambda r: None)
        result['findings'] = []
        for fragment in result['preview_fragments']:
            fragment['generation'] = {}
        self.seal(result)
        report = self.validate(result)
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertEqual(report['expression_checks_state'], 'unresolved')
        self.assertIn('GENERATION_RECORD_UNVERIFIED', {f['rule_id'] for f in report['findings']})

    def test_removed_generation_error_finding_is_reconstructed(self):
        result = self.result(generator=lambda r: None)
        result['findings'] = []
        self.seal(result)
        self.assert_code(result, 'GENERATION_ERROR', state='REVIEW')
        self.assertEqual(self.validate(result)['expression_checks_state'], 'unresolved')

    def test_ascii_single_quote_immutable(self):
        self.reset_source('기본 요청 제한 시간은 30초다.', "기본 요청 제한 시간은 30초다. '직접 인용'")
        self.assert_code(self.rewrite('u-timeout', "기본 요청 제한 시간은 30초다. '수정 인용'"),
                         'EXCLUDED_CONTEXT_MODIFIED')

    def test_partial_ascii_single_quote_context_excluded(self):
        self.reset_source('기본 요청 제한 시간은 30초다.', "'기본 요청 제한 시간은 30초다.'")
        unit = next(u for u in self.analysis['units'] if u['id'] == 'u-timeout')
        unit['quotes'][0]['quote'] = '기본 요청 제한 시간은 30초다.'
        unit['source_spans'] = pipeline.resolve_block_quotes(unit['quotes'],
                    {b['block_id']: b for b in self.analysis['blocks']}, self.bundle['document_snapshot'])
        self.seal(self.analysis, 'analysis_sha256')
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.assert_code(self.rewrite('u-timeout', '기본 요청 제한 시간은 30초입니다.'),
                         'EXCLUDED_CONTEXT_MODIFIED')

    def test_apostrophes_are_not_quote_pairs(self):
        for text in ("don't change the user's defaults.", "users' settings don't change.",
                     "O'Reilly's guide isn't outdated."):
            with self.subTest(text=text):
                matches = [m.group(0) for m in expression.INLINE_PROTECTED.finditer(text)]
                self.assertEqual(matches, [])

    def test_single_quote_next_to_korean_particle(self):
        self.reset_source('기본 요청 제한 시간은 30초다.', "기본 요청 제한 시간은 30초다. '원문'을 인용한다.")
        self.assert_code(self.rewrite('u-timeout', "기본 요청 제한 시간은 30초다. '변경'을 인용한다."),
                         'EXCLUDED_CONTEXT_MODIFIED')

    def test_unmatched_single_quote_conservatively_excluded(self):
        self.reset_source('기본 요청 제한 시간은 30초다.', "기본 요청 제한 시간은 30초다. '닫히지 않은 인용")
        self.assert_code(self.rewrite('u-timeout', "기본 요청 제한 시간은 30초다. '변경된 인용"),
                         'EXCLUDED_CONTEXT_MODIFIED')

    def test_code_string_with_single_quotes_still_protected(self):
        self.reset_source('기본 요청 제한 시간은 30초다.', "기본 요청 제한 시간은 30초다. `print('value')`")
        self.assert_code(self.rewrite('u-timeout', "기본 요청 제한 시간은 30초다. `print('other')`"),
                         'EXCLUDED_CONTEXT_MODIFIED')

    def test_approval_signal_cannot_be_cleared_with_recomputed_hash(self):
        result = self.result(generator=lambda r: {'text': r['before'], 'approved': True})
        result['findings'] = []
        for fragment in result['preview_fragments']:
            fragment['generation']['approval_claim_detected'] = False
        self.seal(result)
        self.assert_code(result, 'GENERATOR_APPROVAL_CLAIM')
        self.assert_code(result, 'GENERATION_RECORD_MISMATCH')

    def test_prior_run_receipts_cannot_hide_new_failure(self):
        success = self.result()
        failed = self.result(generator=lambda r: None)
        failed['findings'] = []
        for clean, broken in zip(success['preview_fragments'], failed['preview_fragments']):
            broken['generation'] = copy.deepcopy(clean['generation'])
        self.seal(failed)
        self.assert_code(failed, 'GENERATION_RECORD_MISMATCH')

    def test_unknown_receipts_stay_unresolved_after_export(self):
        result = self.result()
        for fragment in result['preview_fragments']:
            fragment['generation']['receipt_id'] = 'unknown-process-receipt'
        self.seal(result)
        report = self.validate(result)
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertEqual(report['expression_checks_state'], 'unresolved')

    def test_custom_exception_name_is_not_exposed(self):
        private_exception = type('PRIVATE_EXCEPTION_CLASS_SENTINEL', (Exception,), {})
        def broken(request):
            raise private_exception('PRIVATE_EXCEPTION_MESSAGE_SENTINEL')
        result = self.result(broken)
        encoded = json.dumps(result) + json.dumps(self.validate(result))
        self.assertNotIn('PRIVATE_EXCEPTION_', encoded)
        self.assertTrue(all(f['generation'].get('error_code') == 'GENERATOR_EXCEPTION'
                            for f in result['preview_fragments']))

    def test_single_quoted_contraction_protected(self):
        text = "He said 'don't change this'. The user's guide applies."
        protected = [m.group(0) for m in expression.INLINE_PROTECTED.finditer(text)]
        self.assertEqual(protected, ["'don't change this'"])

    def test_term_edit_outside_apostrophes_is_not_excluded(self):
        request = {'before': "don't modify the user's 런타임.", 'operation': 'REVISE',
                   'excluded': False, 'constraints': {'register': '한다체', 'terminology': {'런타임': 'Runtime'}}}
        self.assertEqual(expression.DeterministicGenerator().generate(request)['text'],
                         "don't modify the user's Runtime.")

    def test_preconfigured_logging_handler_does_not_leak_generator_data(self):
        marker = 'PRIVATE_LOG_SENTINEL'
        stream = io.StringIO()
        logger = logging.getLogger('expression_generator_privacy_test')
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        old_level, old_propagate = logger.level, logger.propagate
        old_disabled = logging.root.manager.disable
        logger.setLevel(logging.WARNING)
        logger.propagate = False
        try:
            def generator(request):
                logger.warning(marker)
                return {'text': request['before'], 'internal_log': marker}
            result = self.result(generator)
            self.assertNotIn(marker, stream.getvalue() + json.dumps(result))
            self.assertEqual(logging.root.manager.disable, old_disabled)
        finally:
            logger.removeHandler(handler)
            handler.close()
            logger.setLevel(old_level)
            logger.propagate = old_propagate

    def test_plural_possessive_inside_single_quote_remains_protected(self):
        text = "He said 'The users' 런타임 settings are fixed.'"
        request = {'before': text, 'operation': 'REVISE', 'excluded': False,
                   'constraints': {'register': '한다체', 'terminology': {'런타임': 'Runtime'}}}
        self.assertEqual(expression.DeterministicGenerator().generate(request)['text'], text)
        self.reset_source('기본 요청 제한 시간은 30초다.', '기본 요청 제한 시간은 30초다. ' + text)
        self.assert_code(self.rewrite('u-timeout',
                '기본 요청 제한 시간은 30초다. ' + text.replace('런타임', 'Runtime')),
                'EXCLUDED_CONTEXT_MODIFIED')

    def test_logging_settings_restored_after_generator_exception(self):
        old_disabled = logging.root.manager.disable
        def broken(request):
            raise RuntimeError('PRIVATE_ERROR_LOG_SENTINEL')
        result = self.result(broken)
        self.assertEqual(logging.root.manager.disable, old_disabled)
        self.assertEqual(self.validate(result)['expression_checks_state'], 'unresolved')


if __name__ == '__main__':
    unittest.main()
