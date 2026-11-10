"""Package boundary and preservation tests; no synthetic completed human reviews."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from jsonschema.exceptions import ValidationError
from export import PILOT, build, check_preserved, digest, payload
from check_form import check_form


class PackageTests(unittest.TestCase):
    def test_original_27_files_unchanged(self):
        self.assertEqual(check_preserved(), 27)

    def test_exact_allowlist(self):
        files = payload()
        expected = {'REVIEWER.md', 'input.schema.json', 'review-form.schema.json',
                    'package.json', 'sources/chatgpt2codex-README.md'}
        for n in range(1, 13):
            expected.update({f'inputs/SP-{n:03}.json', f'cases/SP-{n:03}.md',
                             f'forms/SP-{n:03}.json'})
        self.assertEqual(set(files), expected)
        inventory = json.loads(files['package.json'])['files']
        self.assertEqual(set(inventory), set(files) - {'package.json'})
        for name, expected_hash in inventory.items():
            self.assertEqual(digest(files[name]), expected_hash)

    def test_inputs_are_byte_exact_and_forms_blank(self):
        files = payload()
        for n in range(1, 13):
            cid = f'SP-{n:03}'
            self.assertEqual(files[f'inputs/{cid}.json'], (PILOT / f'inputs/{cid}.json').read_bytes())
            form = json.loads(files[f'forms/{cid}.json'])
            self.assertEqual(check_form(form), 'blank')
            for field in ['reviewer_id', 'reviewed_at', 'judgment', 'rationale', 'blinded_to_prior_judgments']:
                self.assertIsNone(form[field])
            rendered = files[f'cases/{cid}.md'].decode()
            inp = json.loads(files[f'inputs/{cid}.json'])
            for side in ['source_documents', 'candidate_documents']:
                for document in inp[side]:
                    if document['content'] is not None:
                        self.assertIn(document['content'], rendered)

    def test_zip_reproducible_and_no_answers(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a.zip', Path(d) / 'b.zip'
            self.assertEqual(build(a), build(b))
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with zipfile.ZipFile(a) as archive:
                self.assertEqual(set(archive.namelist()), set(payload()))
                self.assertIsNone(archive.testzip())

    def test_no_answer_dependency(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'pilot'
            shutil.copytree(PILOT, root, ignore=shutil.ignore_patterns('dist', '__pycache__'))
            shutil.rmtree(root / 'answers')
            (root / 'manifest.json').unlink()
            self.assertEqual(payload(root), payload())

    def test_mutated_input_or_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'pilot'
            shutil.copytree(PILOT, root, ignore=shutil.ignore_patterns('dist', '__pycache__'))
            p = root / 'inputs/SP-001.json'
            original = p.read_bytes()
            p.write_bytes(original + b' ')
            with self.assertRaisesRegex(ValueError, 'input differs'):
                payload(root)
            p.write_bytes(original)
            p = root / 'sources/chatgpt2codex-README.md'
            p.write_bytes(p.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'source digest'):
                payload(root)

    def test_blank_cannot_masquerade_as_submitted(self):
        form = json.loads(payload()['forms/SP-001.json'])
        form['form_status'] = 'submitted'
        with self.assertRaises(ValidationError):
            check_form(form)

    def test_blank_does_not_allow_ai_prefilled_judgment(self):
        form = json.loads(payload()['forms/SP-001.json'])
        form['judgment'] = 'PRESERVED'
        with self.assertRaises(ValidationError):
            check_form(form)

    def test_stale_form_rejected(self):
        form = json.loads(payload()['forms/SP-001.json'])
        form['input_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'stale form'):
            check_form(form)


if __name__ == '__main__':
    unittest.main()
