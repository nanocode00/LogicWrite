"""New boundary tests; all original historical tests remain unchanged."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class IntegrityTests(unittest.TestCase):
    def load_boundary(self):
        cls = type(self)
        self.assertTrue((HERE / 'boundary.py').exists(), 'Missing historical/current validation boundary')
        spec = importlib.util.spec_from_file_location('evidence_boundary', HERE / 'boundary.py')
        cls.boundary = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.boundary)
        cls.store = cls.boundary.EvidenceStore(ROOT)

    def setUp(self):
        if not hasattr(type(self), 'store'):
            self.load_boundary()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in self.store.protected_paths:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def test_current_core_change_does_not_change_historical_evidence(self):
        path = self.root / 'experiments/full_document_control/reconstruction.py'
        path.parent.mkdir(parents=True)
        path.write_text('current Core can evolve\n')
        result = self.store.verify_evidence(self.root)
        self.assertEqual(result['historical_revision'], self.boundary.HISTORICAL_REVISION)
        self.assertGreaterEqual(result['verified_files'], 542)

    def test_input_judgment_approval_manifest_and_validator_tampering_rejected(self):
        paths = ['evaluation/semantic_pilot/inputs/SP-001.json',
            'evaluation/golden_expansion/user_final_2026_11_11/events.json',
            'evaluation/g3_g4/development_gold_v3_active_2026-11-13/policy-approval.json',
            'evaluation/g3_g4/development_gold_v3_active_2026-11-13/preserved-files.json',
            'evaluation/g3_g4/development_gold_v3_active_2026-11-13/validate.py',
            'evaluation/development_gold_active/runtime.py',
            'tests/fixtures/README.md']
        for name in paths:
            with self.subTest(path=name):
                path = self.root / name
                original = path.read_bytes()
                path.write_bytes(original + b' ')
                with self.assertRaisesRegex(ValueError, 'evidence changed'):
                    self.store.verify_evidence(self.root)
                path.write_bytes(original)

    def test_deleted_evidence_and_symlink_substitution_rejected(self):
        path = self.root / 'evaluation/semantic_pilot/inputs/SP-001.json'
        raw = path.read_bytes()
        path.unlink()
        with self.assertRaises(ValueError):
            self.store.verify_evidence(self.root)
        external = self.root / 'external.json'
        external.write_bytes(raw)
        path.symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.store.verify_evidence(self.root)

    def test_unavailable_history_fails_closed(self):
        with self.assertRaises(ValueError):
            self.boundary.EvidenceStore(self.root)

    def test_historical_source_requirements_and_manifest_tampering_rejected(self):
        with self.store.snapshot() as snapshot:
            self.assertEqual(subprocess.check_output(['git', '-C', str(snapshot), 'rev-parse', 'HEAD'], text=True).strip(),
                             self.boundary.HISTORICAL_REVISION)
            for name in ['experiments/full_document_control/reconstruction.py',
                         'evaluation/semantic_pilot/requirements.txt',
                         'evaluation/g3_g4/development_gold_v3_active_2026-11-13/preserved-files.json']:
                with self.subTest(path=name):
                    path = snapshot / name
                    raw = path.read_bytes()
                    path.write_bytes(raw + b' ')
                    with self.assertRaisesRegex(ValueError, 'historical snapshot changed'):
                        self.store.verify_snapshot(snapshot)
                    path.write_bytes(raw)

    def test_changed_revision_or_tree_cannot_substitute_trust_root(self):
        original = self.boundary.HISTORICAL_TREE
        self.boundary.HISTORICAL_TREE = '0' * 40
        try:
            with self.assertRaisesRegex(ValueError, 'historical tree'):
                self.boundary.EvidenceStore(ROOT)
        finally:
            self.boundary.HISTORICAL_TREE = original
