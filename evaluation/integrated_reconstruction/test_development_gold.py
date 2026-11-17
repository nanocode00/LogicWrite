"""Read-only regression checks for approved exposed-development inclusion."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
import json

ROOT = Path(__file__).resolve().parent


def load_validator():
    spec = importlib.util.spec_from_file_location("development_gold_validation",
                                                  ROOT / "development_gold/validate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DevelopmentGoldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "package"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__"))
        self.v = load_validator()
        self.old_root = self.v.ROOT
        self.v.ROOT = self.root
        self.addCleanup(lambda: setattr(self.v, "ROOT", self.old_root))

    def test_three_included_exposed_development_only(self):
        result = self.v.validate()
        self.assertEqual(result["included_development_cases"], 3)
        self.assertEqual(result["source_families"], 1)
        self.assertEqual(result["split"], "exposed_development")
        self.assertTrue(result["gold_inclusion_approved_in_registry"])

    def test_reference_mutation_rejected(self):
        p = self.root / "reference_outputs/v2_candidates/IR-001.json"
        p.write_bytes(p.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "stale git blob"):
            self.v.validate()

    def test_approval_scope_or_source_independence_mutation_rejected(self):
        p = self.root / "development_gold/manifest.json"
        original = json.loads(p.read_text())
        for key, value in (("source_family", "independent-real-world"),
                           ("independent_source_families", 3),
                           ("split", "holdout")):
            mutated = dict(original)
            mutated[key] = value
            p.write_text(json.dumps(mutated))
            with self.assertRaises(ValueError):
                self.v.validate()

    def test_ir003_criteria_version_change_rejected(self):
        p = self.root / "development_gold/manifest.json"
        m = json.loads(p.read_text())
        m["cases"][2]["criteria_path"] = "criteria/v2/IR-002.json"
        p.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, "unexpected case version"):
            self.v.validate()
