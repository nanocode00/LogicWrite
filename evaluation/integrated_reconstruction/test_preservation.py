"""Exercise preservation against real local Git objects; mutate only copies."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parent
REPO = PACKAGE.parents[1]
spec = importlib.util.spec_from_file_location('integrated_preservation', PACKAGE / 'check_preservation.py')
preservation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preservation)


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        subprocess.run(['git', 'clone', '--shared', '--quiet', str(REPO), str(self.repo)],
                       check=True, capture_output=True)

    def test_current_core_and_development_docs_can_evolve(self):
        for name in ('experiments/full_document_control/reconstruction.py', 'README.md', 'docs/roadmap.md'):
            with (self.repo / name).open('ab') as f:
                f.write(b'\n# current development\n')
        result = preservation.verify(self.repo)
        self.assertEqual(result['historical_snapshot_files_verified'], 616)
        self.assertEqual(result['current_evidence_files_unchanged'], 545)

    def test_historical_input_judgment_approval_manifest_still_rejected(self):
        for name in ('evaluation/semantic_pilot/inputs/SP-001.json',
                     'evaluation/golden_expansion/user_final_2026_11_11/events.json',
                     'evaluation/g3_g4/development_gold_v3_active_2026-11-13/policy-approval.json',
                     'evaluation/g3_g4/development_gold_v3_active_2026-11-13/preserved-files.json'):
            with self.subTest(path=name):
                path = self.repo / name
                raw = path.read_bytes()
                path.write_bytes(raw + b' ')
                with self.assertRaises(ValueError):
                    preservation.verify(self.repo)
                path.write_bytes(raw)

    def test_used_pilot_inputs_and_person_response_cannot_be_rewritten(self):
        for name in ('inputs/IR-001.json', 'reviews/IR-001.json', 'answers/IR-001.json'):
            path = self.repo / 'evaluation/integrated_reconstruction' / name
            raw = path.read_bytes()
            path.write_bytes(raw + b' ')
            with self.assertRaisesRegex(ValueError, 'pilot evidence'):
                preservation.verify(self.repo)
            path.write_bytes(raw)

    def test_preservation_baseline_cannot_be_resealed(self):
        path = self.repo / 'evaluation/integrated_reconstruction/records/protected_baseline.json'
        raw = json.loads(path.read_text())
        raw['main_files'] = {}
        path.write_text(json.dumps(raw))
        with self.assertRaisesRegex(ValueError, 'baseline'):
            preservation.verify(self.repo)

    def test_legacy_checkout_420_files_verified_and_mutation_rejected(self):
        legacy = Path(self.tmp.name) / 'legacy'
        baseline = json.loads((PACKAGE / 'records/protected_baseline.json').read_text())
        for commit, files in baseline['protected_pr_files'].items():
            for name in files:
                if name.startswith('evaluation/capability_pilot/'):
                    path = legacy / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(subprocess.check_output(['git', '--no-replace-objects', '-C', str(REPO), 'show', commit + ':' + name]))
        result = preservation.verify(self.repo, legacy)
        self.assertEqual(result['legacy_checkout_files_verified'], 420)
        path = legacy / 'evaluation/capability_pilot/inputs/CP-T1-01.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'legacy checkout'):
            preservation.verify(self.repo, legacy)

    def test_symlink_evidence_substitution_rejected(self):
        path = self.repo / 'evaluation/integrated_reconstruction/inputs/IR-001.json'
        outside = Path(self.tmp.name) / 'input.json'
        shutil.copyfile(path, outside)
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            preservation.verify(self.repo)
