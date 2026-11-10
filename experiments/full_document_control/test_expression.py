"""Source-bound Expression previews and independent anti-forgery counterexamples."""
import copy
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


if __name__ == '__main__':
    unittest.main()
