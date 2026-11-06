"""Synthetic fault-injection tests; these are not gold annotations."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location('gate_spike', HERE / 'gate.py')


def snapshot(identity, text):
    return {'id': identity, 'document_id': 'guide', 'content': text,
            'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()}


def bundle():
    text = '설치 대기시간은 30초다. 🚀'
    start = text.index('30')
    return {
        'contract': {'audience': '설치 사용자', 'purpose': '설치를 시작한다',
                     'document_type': 'installation_guide',
                     'output_scopes': [{'scope_id': 'current', 'document_id': 'guide'}]},
        'source': snapshot('before', text),
        'candidate': snapshot('after', text),
        'protected_literals': [{'id': 'timeout', 'scope_id': 'current',
                                'source_span': {'snapshot_id': 'before', 'start': start, 'end': start + 2},
                                'output_span': {'snapshot_id': 'after', 'start': start, 'end': start + 2}}],
    }


def check_plan(*ids):
    return [{'check_id': check_id, 'check_version': '1'} for check_id in ids]


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(cls.gate)

    def test_intact_input_waits_for_semantic_review(self):
        report = self.gate.evaluate(bundle())
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertFalse(report['delivery_approved'])
        self.assertEqual(len(report['check_results']), len(report['plan']['required_checks']))
        checks = {r['check_id']: r['status'] for r in report['check_results']}
        self.assertEqual(checks['PROTECTED_LITERALS'], 'passed')
        self.assertEqual(checks['SEMANTIC_REVIEW'], 'not_run')

    def test_missing_purpose_fails(self):
        data = bundle(); del data['contract']['purpose']
        self.assertEqual(self.gate.evaluate(data)['gate_state'], 'FAIL')

    def test_unknown_scope_fails(self):
        data = bundle(); data['protected_literals'][0]['scope_id'] = 'invented'
        self.assertEqual(self.gate.evaluate(data)['gate_state'], 'FAIL')

    def test_duplicate_scope_fails(self):
        data = bundle(); data['contract']['output_scopes'] *= 2
        self.assertEqual(self.gate.evaluate(data)['gate_state'], 'FAIL')

    def test_unbound_destination_is_outside_supported_profile(self):
        data = bundle(); data['contract']['output_scopes'][0] = {'scope_id': 'current', 'destination_role': 'design'}
        report = self.gate.evaluate(data)
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertIn('UNSUPPORTED_PROFILE', str(report))

    def test_source_digest_mismatch_fails(self):
        data = bundle(); data['source']['content'] += '改'
        self.assertEqual(self.gate.evaluate(data)['gate_state'], 'FAIL')

    def test_changed_number_fails_despite_valid_candidate_digest(self):
        data = bundle(); data['candidate'] = snapshot('after', data['candidate']['content'].replace('30', '60'))
        self.assertEqual(self.gate.evaluate(data)['gate_state'], 'FAIL')

    def test_missing_output_trace_fails(self):
        data = bundle(); del data['protected_literals'][0]['output_span']
        self.assertEqual(self.gate.evaluate(data)['gate_state'], 'FAIL')

    def test_stale_snapshot_reference_fails(self):
        data = bundle(); data['protected_literals'][0]['source_span']['snapshot_id'] = 'old'
        self.assertEqual(self.gate.evaluate(data)['gate_state'], 'FAIL')

    def test_unicode_offsets_are_codepoints(self):
        data = bundle(); text = '🚀한글30초'
        data['source'] = snapshot('before', text); data['candidate'] = snapshot('after', text)
        for key in ['source_span', 'output_span']:
            data['protected_literals'][0][key].update(start=3, end=5)
        self.assertEqual(self.gate.evaluate(data)['gate_state'], 'REVIEW')

    def test_invalid_spans_fail(self):
        for start, end in [(-1, 2), (0, 999), (2, 2), (True, 3)]:
            with self.subTest(start=start, end=end):
                data = bundle(); data['protected_literals'][0]['source_span'].update(start=start, end=end)
                self.assertEqual(self.gate.evaluate(data)['gate_state'], 'FAIL')

    def test_missing_result_stops_and_preserves_failure(self):
        plan = check_plan('a', 'b')
        rows = [{'check_id': 'a', 'check_version': '1', 'status': 'violated', 'reason': 'protected number changed'}]
        report = self.gate.reconcile(plan, rows)
        self.assertEqual(report['gate_state'], 'STOPPED')
        self.assertEqual(report['last_gate_state'], 'FAIL')
        self.assertIn('CHECK_RESULT_MISSING', str(report))

    def test_empty_or_duplicate_results_never_pass(self):
        for rows in [[], [{'check_id': 'a', 'check_version': '1', 'status': 'passed'}] * 2]:
            report = self.gate.reconcile(check_plan('a'), rows)
            self.assertNotEqual(report['gate_state'], 'PASS')

    def test_reducer_pass_is_only_for_complete_passed_checks(self):
        report = self.gate.reconcile(check_plan('a'), [{'check_id': 'a', 'check_version': '1', 'status': 'passed'}])
        self.assertEqual(report['gate_state'], 'PASS')
        self.assertFalse(report['delivery_approved'])

    def test_missing_check_version_fails(self):
        report = self.gate.reconcile(check_plan('a'), [{'check_id': 'a', 'status': 'passed'}])
        self.assertEqual(report['gate_state'], 'FAIL')
        self.assertIn('CHECK_VERSION_MISSING', str(report))

    def test_mismatched_check_version_fails(self):
        report = self.gate.reconcile(check_plan('a'), [{'check_id': 'a', 'check_version': 'obsolete', 'status': 'passed'}])
        self.assertEqual(report['gate_state'], 'FAIL')
        self.assertIn('CHECK_VERSION_MISMATCH', str(report))

    def test_live_report_plan_pins_each_executed_check_version(self):
        report = self.gate.evaluate(bundle())
        expected = {x['check_id']: x['check_version'] for x in report['plan']['required_checks']}
        self.assertEqual(expected, {x['check_id']: x['check_version'] for x in report['check_results']})

    def test_versions_are_matched_per_check_not_plan_version(self):
        plan = [{'check_id': 'a', 'check_version': 'a-v2'},
                {'check_id': 'b', 'check_version': 'b-v3'}]
        rows = [dict(x, status='passed') for x in plan]
        self.assertEqual(self.gate.reconcile(plan, rows)['gate_state'], 'PASS')
        rows[0]['check_version'] = 'b-v3'
        self.assertEqual(self.gate.reconcile(plan, rows)['gate_state'], 'FAIL')

    def test_invalid_plan_version_never_passes(self):
        for version in [None, '', 1]:
            with self.subTest(version=version):
                plan = [{'check_id': 'a', 'check_version': version}]
                rows = [{'check_id': 'a', 'check_version': '1', 'status': 'passed'}]
                self.assertEqual(self.gate.reconcile(plan, rows)['gate_state'], 'FAIL')

    def test_version_failure_survives_another_missing_result(self):
        report = self.gate.reconcile(check_plan('a', 'b'),
                                    [{'check_id': 'a', 'check_version': 'old', 'status': 'passed'}])
        self.assertEqual(report['gate_state'], 'STOPPED')
        self.assertEqual(report['last_gate_state'], 'FAIL')
        self.assertIn('CHECK_VERSION_MISMATCH', str(report))

    def test_unknown_fields_are_not_silently_ignored(self):
        data = bundle(); data['contract']['required_information'] = ['a semantic requirement']
        self.assertEqual(self.gate.evaluate(data)['gate_state'], 'REVIEW')

    def test_validator_execution_error_stops(self):
        with mock.patch.object(self.gate, 'literal_check', side_effect=RuntimeError('synthetic execution fault')):
            report = self.gate.evaluate(bundle())
        self.assertEqual(report['gate_state'], 'STOPPED')
        self.assertIn('synthetic execution fault', str(report))

    def test_report_binds_exact_input_and_explains_changed_literal(self):
        data = bundle(); data['candidate'] = snapshot('after', data['candidate']['content'].replace('30', '60'))
        report = self.gate.evaluate(data)
        self.assertEqual(len(report['input_digest']), 64)
        row = next(x for x in report['check_results'] if x['check_id'] == 'PROTECTED_LITERALS')
        self.assertEqual(row['evidence'][0]['expected'], '30')
        self.assertEqual(row['evidence'][0]['actual'], '60')
        self.assertEqual(row['evidence'][0]['source_span'], data['protected_literals'][0]['source_span'])

    def test_unsupported_result_status_fails_integrity_check(self):
        report = self.gate.reconcile(check_plan('a'), [{'check_id': 'a', 'check_version': '1', 'status': 'maybe'}])
        self.assertEqual(report['gate_state'], 'FAIL')

    def test_unexpected_result_cannot_replace_required_one(self):
        report = self.gate.reconcile(check_plan('a'), [{'check_id': 'b', 'check_version': '1', 'status': 'passed'}])
        self.assertEqual(report['gate_state'], 'STOPPED')
        self.assertEqual(report['last_gate_state'], 'FAIL')

    def test_input_is_not_modified_and_run_is_reproducible(self):
        data = bundle(); original = copy.deepcopy(data)
        self.assertEqual(self.gate.evaluate(data), self.gate.evaluate(data))
        self.assertEqual(data, original)

    def test_cli_reports_malformed_or_duplicate_json_as_fail(self):
        for raw in ['{broken', '{"contract": {}, "contract": {}}', 'NaN']:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'input.json'; path.write_text(raw)
                result = subprocess.run([sys.executable, str(HERE / 'gate.py'), str(path)], capture_output=True, text=True)
                report = json.loads(result.stdout)
                self.assertEqual(report['gate_state'], 'FAIL', report)
                self.assertIn('INVALID_INPUT', str(report))
                self.assertNotIn('Traceback', result.stderr)

    def test_cli_escapes_unpaired_unicode_identifier_in_report(self):
        data = bundle(); data['protected_literals'][0]['id'] = '\ud800'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'; path.write_text(json.dumps(data))
            result = subprocess.run([sys.executable, str(HERE / 'gate.py'), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['gate_state'], 'REVIEW')

    def test_cli_decoder_limits_produce_reports(self):
        for raw, expected in [('1' * 5000, 'FAIL'), ('[' * 10000 + ']' * 10000, 'STOPPED')]:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'input.json'; path.write_text(raw)
                result = subprocess.run([sys.executable, str(HERE / 'gate.py'), str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['gate_state'], expected)

    def test_cli_reports_unreadable_input_as_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'does-not-exist.json'
            result = subprocess.run([sys.executable, str(HERE / 'gate.py'), str(path)], capture_output=True, text=True)
            self.assertEqual(json.loads(result.stdout)['gate_state'], 'STOPPED')
            self.assertIn('INPUT_READ_ERROR', result.stdout)

    def test_cli_emits_json_and_leaves_input_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'; raw = json.dumps(bundle(), ensure_ascii=False).encode()
            path.write_bytes(raw)
            result = subprocess.run([sys.executable, str(HERE / 'gate.py'), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['gate_state'], 'REVIEW')
            self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
