"""Workflow invariants, not golden semantic judgments."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location('ab_spike', HERE / 'ab.py')
FIX = importlib.util.spec_from_file_location('analysis_fixture', HERE.parent / 'extraction_analysis/test_analysis.py')
fixture = importlib.util.module_from_spec(FIX); FIX.loader.exec_module(fixture)


def responses(module, raw):
    single = fixture.proposal(raw)
    inventory = {'input_sha256': single['input_sha256'],
                 'units': [{k: copy.deepcopy(v) for k, v in unit.items() if k != 'assessment'} for unit in single['units']],
                 'unresolved_questions': []}
    inventory_raw = json.dumps(inventory).encode()
    evaluation = {'input_sha256': single['input_sha256'], 'extraction_sha256': module.base.digest(inventory_raw),
                  'assessments': [{'unit_id': u['id'], 'assessment': u['assessment']} for u in single['units']],
                  'alignment': single['alignment'], 'unresolved_questions': single['unresolved_questions']}
    return inventory_raw, evaluation


class ABTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(cls.module)

    def setUp(self):
        self.raw = json.dumps(fixture.fixture(), ensure_ascii=False).encode()

    def test_a_prompt_is_unmodified_baseline(self):
        self.assertEqual(self.module.prompt_a(self.raw), self.module.base.build_prompt(self.raw))

    def test_b1_omits_actual_contract_and_task(self):
        data = fixture.fixture(); data['writing_contract']['purpose'] = 'PURPOSE_SENTINEL'
        data['writing_contract']['audience'] = 'AUDIENCE_SENTINEL'; data['task'] = 'TASK_SENTINEL'
        raw = json.dumps(data).encode(); prompt = self.module.prompt_b1(raw)
        for sentinel in ['PURPOSE_SENTINEL', 'AUDIENCE_SENTINEL', 'TASK_SENTINEL']:
            self.assertNotIn(sentinel, prompt)
        self.assertIn(data['passages'][0]['text'], prompt)

    def test_b2_has_full_input_and_exact_inventory_binding(self):
        inventory_raw, _ = responses(self.module, self.raw)
        prompt = self.module.prompt_b2(self.raw, inventory_raw)
        self.assertIn(fixture.fixture()['writing_contract']['purpose'], prompt)
        self.assertIn(self.module.base.digest(inventory_raw), prompt)

    def test_stitch_preserves_all_extracted_fields(self):
        inventory_raw, evaluation = responses(self.module, self.raw)
        assembled = self.module.stitch(self.raw, inventory_raw, json.dumps(evaluation).encode())
        for before, after in zip(json.loads(inventory_raw)['units'], json.loads(assembled)['units']):
            self.assertEqual(before, {k: v for k, v in after.items() if k != 'assessment'})
        report = self.module.base.analyze(self.raw, assembled)
        self.assertEqual(report['gate_state'], 'REVIEW'); self.assertFalse(report['delivery_approved'])

    def test_wrong_inventory_digest_rejected(self):
        inventory_raw, evaluation = responses(self.module, self.raw); evaluation['extraction_sha256'] = 'wrong'
        with self.assertRaises(ValueError): self.module.stitch(self.raw, inventory_raw, json.dumps(evaluation).encode())

    def test_missing_duplicate_unknown_or_editing_assessments_rejected(self):
        inventory_raw, evaluation = responses(self.module, self.raw)
        for change in ['missing', 'duplicate', 'unknown', 'edit']:
            with self.subTest(change=change):
                value = copy.deepcopy(evaluation)
                if change == 'missing': value['assessments'] = []
                if change == 'duplicate': value['assessments'] *= 2
                if change == 'unknown': value['assessments'][0]['unit_id'] = 'unknown'
                if change == 'edit': value['assessments'][0]['statement'] = 'changed'
                with self.assertRaises(ValueError): self.module.stitch(self.raw, inventory_raw, json.dumps(value).encode())

    def test_b1_fabricated_quote_is_rejected_before_evaluation(self):
        inventory_raw, _ = responses(self.module, self.raw); value = json.loads(inventory_raw)
        value['units'][0]['quotes'][0]['quote'] = 'fabricated'
        with self.assertRaises(ValueError): self.module.check_inventory(self.raw, json.dumps(value).encode())

    def test_inventory_checker_does_not_return_placeholder_assessments(self):
        inventory_raw, _ = responses(self.module, self.raw)
        checked = self.module.check_inventory(self.raw, inventory_raw)
        self.assertNotIn('units', checked); self.assertNotIn('alignment', checked)
        self.assertEqual(checked['source_references'], 'passed')

    def test_wrong_evaluation_input_digest_rejected(self):
        inventory_raw, evaluation = responses(self.module, self.raw); evaluation['input_sha256'] = 'different'
        with self.assertRaises(ValueError): self.module.stitch(self.raw, inventory_raw, json.dumps(evaluation).encode())

    def test_lexically_supported_but_wrong_statement_remains_unverified(self):
        inventory_raw, evaluation = responses(self.module, self.raw); inventory = json.loads(inventory_raw)
        inventory['units'][0]['statement'] = '성공은 이미 검증됐다.'
        inventory_raw = json.dumps(inventory).encode(); evaluation['extraction_sha256'] = self.module.base.digest(inventory_raw)
        report = self.module.base.analyze(self.raw, self.module.stitch(self.raw, inventory_raw, json.dumps(evaluation).encode()))
        self.assertEqual(report['checks']['source_references'], 'passed')
        self.assertEqual(report['checks']['semantic_fidelity'], 'not_run')
        self.assertEqual(report['gate_state'], 'REVIEW'); self.assertFalse(report['delivery_approved'])

    def test_two_pairs_use_counterbalanced_order(self):
        inventory_raw, evaluation = responses(self.module, self.raw)
        a = json.dumps(fixture.proposal(self.raw)).encode(); b2 = json.dumps(evaluation).encode()
        outputs = [a, inventory_raw, b2, inventory_raw, b2, a]; prompts = []
        def fake(prompt, **options):
            prompts.append(prompt)
            return {'stdout': outputs.pop(0), 'stderr': b'', 'returncode': 0, 'seconds': 0.01}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(self.module, 'call_model', side_effect=fake):
            out = Path(d)/'run'; self.module.run_experiment(self.raw, out, executable='stub', model='stub', repeats=2)
            self.assertEqual(outputs, [])
            self.assertEqual(prompts, [self.module.prompt_a(self.raw), self.module.prompt_b1(self.raw),
                                      self.module.prompt_b2(self.raw, inventory_raw), self.module.prompt_b1(self.raw),
                                      self.module.prompt_b2(self.raw, inventory_raw), self.module.prompt_a(self.raw)])

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'run'; out.mkdir()
            with self.assertRaises(FileExistsError):
                self.module.run_experiment(self.raw, out, executable='stub', model='stub', repeats=1)

    def test_runner_retains_failed_stage_and_skips_b2_without_retry(self):
        calls = []
        def fake(prompt, **options):
            calls.append(prompt)
            return {'stdout': b'not JSON', 'stderr': b'provider diagnostic', 'returncode': 0, 'seconds': 0.01}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(self.module, 'call_model', side_effect=fake):
            out = Path(d) / 'run'
            summary = self.module.run_experiment(self.raw, out, executable='stub', model='stub', repeats=1)
            self.assertEqual(len(calls), 2)
            self.assertEqual(summary['pairs'][0]['B']['gate_state'], 'STOPPED')
            self.assertTrue((out/'pair-1/B1.response.txt').exists())
            self.assertFalse((out/'pair-1/B2.response.txt').exists())
            self.assertEqual((out/'input.json').read_bytes(), self.raw)

    def test_runner_success_uses_three_calls_and_keeps_review(self):
        inventory_raw, evaluation = responses(self.module, self.raw)
        outputs = [json.dumps(fixture.proposal(self.raw)).encode(), inventory_raw, json.dumps(evaluation).encode()]
        def fake(prompt, **options):
            return {'stdout': outputs.pop(0), 'stderr': b'', 'returncode': 0, 'seconds': 0.01}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(self.module, 'call_model', side_effect=fake):
            summary = self.module.run_experiment(self.raw, Path(d)/'run', executable='stub', model='stub', repeats=1)
            self.assertEqual(outputs, [])
            for arm in ['A', 'B']:
                self.assertEqual(summary['pairs'][0][arm]['gate_state'], 'REVIEW')
                self.assertFalse(summary['pairs'][0][arm]['delivery_approved'])


if __name__ == '__main__': unittest.main()
