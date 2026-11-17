import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pilot', HERE / 'run.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)

class PilotBoundaryTests(unittest.TestCase):
    def test_both_arms_receive_exact_same_validated_input(self):
        for cid in ('IR-001', 'IR-002', 'IR-003'):
            inp = pilot.export_input(pilot.GOLD, cid)
            a, b = pilot.messages(inp, 'B0'), pilot.messages(inp, 'B1')
            self.assertEqual(a[1], b[1])
            self.assertEqual(json.loads(a[1]['content']), inp)
            self.assertNotEqual(a[0], b[0])
            self.assertEqual(set(json.loads(a[1]['content'])), set(inp))

    def test_prepared_inputs_and_hashes_match_current_export(self):
        for cid in ('IR-001', 'IR-002', 'IR-003'):
            for arm in ('B0', 'B1'):
                folder = HERE / 'prepared' / cid / arm
                self.assertEqual(json.loads((folder / 'input.json').read_text()),
                                 pilot.messages(pilot.export_input(pilot.GOLD, cid), arm))
                self.assertEqual(json.loads((folder / 'execution.json').read_text())['input_sha256'],
                                 pilot.digest((folder / 'input.json').read_bytes()))
                self.assertFalse((folder / 'response.raw.json').exists())

    def test_refuses_overwriting_any_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory) / 'sentinel'
            sentinel.write_text('preserve')
            result = subprocess.run([sys.executable, str(HERE / 'run.py'), '--output', directory],
                                    capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(), 'preserve')

    def test_no_credentials_fails_before_any_http_request(self):
        import argparse
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            args=argparse.Namespace(output=Path(directory)/'run',execute=True,
                case=None,arm=None,smoke=True,confirm_smoke_reviewed=False)
            with patch.object(pilot,'load_api_key',side_effect=pilot.Blocked('missing_fixture')):
                with patch.object(pilot,'api_json',side_effect=AssertionError('no HTTP')):
                    with self.assertRaises(pilot.Blocked): pilot.run(args)
            self.assertFalse(any(args.output.rglob('response.json')))

if __name__ == '__main__':
    unittest.main()
