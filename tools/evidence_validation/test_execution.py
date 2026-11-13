"""Execution separation and real failing-suite regressions."""
from pathlib import Path
import tempfile
import unittest
import boundary

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class ExecutionTests(unittest.TestCase):
    def runner(self):
        self.assertTrue((HERE / 'run.py').is_file(), 'Missing separated execution runner')
        import run
        return run

    def test_historical_evaluation_and_current_core_have_distinct_roots(self):
        runner = self.runner()
        store = boundary.EvidenceStore(ROOT)
        plan = runner.suite_plan(store, ROOT)
        for directory in ['evaluation/development_gold_active',
                'evaluation/golden_expansion/activation_preflight_2026_11_13',
                'evaluation/golden_expansion/codex_counterreview_2026_11_11',
                'evaluation/golden_expansion/confirmation_bridge_2026_11_13',
                'evaluation/golden_expansion/gold_inclusion_approval_2026_11_13',
                'evaluation/golden_expansion/legacy_migration_2026_11_13',
                'evaluation/golden_expansion/user_final_2026_11_11']:
            self.assertIn({'phase': 'historical', 'directory': directory, 'pattern': 'test_*.py'}, plan)
        self.assertIn({'phase': 'current', 'directory': 'experiments/full_document_control', 'pattern': 'test_*.py'}, plan)
        for directory in ('evaluation/core_pipeline_2026_11_11', 'evaluation/source_candidate_semantics'):
            self.assertIn({'phase': 'current', 'directory': directory, 'pattern': 'test_*.py'}, plan)
        self.assertIn({'phase': 'current', 'directory': 'tools/evidence_validation', 'pattern': 'test_*.py'}, plan)

    def test_current_regression_failure_is_not_hidden(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'test_defect.py').write_text('import unittest\nclass Defect(unittest.TestCase):\n def test_defect(self): self.assertEqual(1, 2)\n')
            result = runner.run_suite(root, '.', 'test_defect.py')
            self.assertEqual(result['tests_run'], 1)
            self.assertNotEqual(result['returncode'], 0)
            self.assertEqual(result['failures'], 1)
            self.assertIn('AssertionError', result['output'])

    def test_empty_suite_and_test_process_error_fail_closed(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory() as temporary:
            result = runner.run_suite(Path(temporary), '.', 'test_*.py')
            self.assertNotEqual(result['returncode'], 0)
            self.assertEqual(result['tests_run'], 0)

    def test_new_evaluation_package_runs_against_current_code(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'evaluation/new_version/test_new.py'
            path.parent.mkdir(parents=True)
            path.write_text('import unittest\n')
            plan = runner.suite_plan(boundary.EvidenceStore(ROOT), root)
            self.assertIn({'phase': 'current', 'directory': 'evaluation/new_version', 'pattern': 'test_new.py'}, plan)

    def test_current_source_fingerprint_detects_uncommitted_core_mutation(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            core = root / 'experiments/full_document_control/core.py'
            core.parent.mkdir(parents=True)
            core.write_text('original\n')
            before = runner.current_identity(root)
            core.write_text('changed\n')
            self.assertNotEqual(before['source_sha256'], runner.current_identity(root)['source_sha256'])

    def test_existing_core_regression_detects_real_source_mutation(self):
        import shutil
        runner = self.runner()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            core = root / 'experiments/full_document_control'
            shutil.copytree(ROOT / 'experiments/full_document_control', core,
                            ignore=shutil.ignore_patterns('__pycache__'))
            path = core / 'reconstruction.py'
            raw = path.read_text()
            signature = 'def bounded_text(entry, before, after, constraints):\n'
            self.assertIn(signature, raw)
            path.write_text(raw.replace(signature, signature + '    return True  # injected structural defect\n', 1))
            result = runner.run_suite(root, 'experiments/full_document_control', 'test_integration.py')
            self.assertNotEqual(result['returncode'], 0)
            self.assertIn('test_unknown_semantic_rewrite_held', result['output'])

    def test_current_identity_covers_new_evaluation_tests_helpers_and_data(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'evaluation/new_version'
            folder.mkdir(parents=True)
            for filename in ('test_new.py', 'helper.py', 'input.json'):
                (folder / filename).write_text('original\n')
            for filename in ('test_new.py', 'helper.py', 'input.json'):
                before = runner.current_identity(root)['source_sha256']
                path = folder / filename
                path.write_text('mutated\n')
                self.assertNotEqual(before, runner.current_identity(root)['source_sha256'], filename)
