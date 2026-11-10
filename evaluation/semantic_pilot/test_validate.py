"""Integrity tests use deliberately corrupted copies; no Core or model calls."""
import copy
import json
from pathlib import Path
import tempfile
import shutil
import unittest
from validate import digest, validate_dataset, validate_pair

ROOT = Path(__file__).resolve().parent

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'pilot'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('__pycache__'))
        self.input = json.loads((ROOT / 'inputs/SP-003.json').read_text())
        self.answer = json.loads((ROOT / 'answers/SP-003.json').read_text())

    def reject(self, mutate):
        mutate(self.input, self.answer)
        # Rebind serialized input so each corruption reaches its actual invariant.
        path = self.root / 'inputs/SP-003.json'
        path.write_text(json.dumps(self.input, ensure_ascii=False))
        self.answer['input_sha256'] = digest(path.read_bytes())
        with self.assertRaises(ValueError):
            validate_pair(self.input, self.answer, self.root)

    def test_dataset(self):
        self.assertEqual(validate_dataset(ROOT), 12)

    def test_answer_leak_in_input(self):
        self.reject(lambda i, a: i.update(expected_judgment='PRESERVED'))

    def test_stale_content_hash(self):
        self.reject(lambda i, a: i['candidate_documents'][0].update(content='changed'))

    def test_bad_evidence_quote(self):
        self.reject(lambda i, a: a['findings'][0]['evidence'][0].update(quote='invented'))

    def test_bad_evidence_document(self):
        self.reject(lambda i, a: a['findings'][0]['evidence'][0].update(document_id='absent'))

    def test_duplicate_document_id(self):
        self.reject(lambda i, a: i['source_documents'].append(copy.deepcopy(i['source_documents'][0])))

    def test_unknown_output_scope(self):
        self.reject(lambda i, a: i['writing_contract']['output_document_ids'].append('absent'))

    def test_reviewed_without_humans(self):
        self.reject(lambda i, a: a.update(status='reviewed'))

    def test_adjudicated_without_record(self):
        self.reject(lambda i, a: a.update(status='adjudicated', gold_eligible=True))

    def test_provisional_cannot_be_gold(self):
        self.reject(lambda i, a: a.update(gold_eligible=True))

    def test_mismatched_case_id(self):
        self.reject(lambda i, a: a.update(case_id='SP-099'))

    def test_path_traversal(self):
        self.reject(lambda i, a: a.update(input_path='../outside.json'))

    def test_available_document_cannot_be_null(self):
        self.reject(lambda i, a: i['source_documents'][0].update(content=None, sha256=None))

    def human_reviews(self):
        evidence = copy.deepcopy(self.answer['findings'][0]['evidence'])
        return [{'reviewer_id': who, 'reviewer_type': 'human',
                 'reviewed_at': '2026-11-10T12:00:00+09:00',
                 'input_sha256': self.answer['input_sha256'],
                 'judgment': 'PRESERVED', 'rationale': 'Test-only simulated review',
                 'evidence': evidence, 'blinded_to_ai_proposal': True}
                for who in ['test-human-a', 'test-human-b']]

    def test_reviewed_pair_with_two_bound_humans(self):
        self.answer.update(status='reviewed', reviews=self.human_reviews())
        self.assertTrue(validate_pair(self.input, self.answer, ROOT))

    def test_adjudicated_pair_retains_ai_proposal(self):
        self.answer.update(status='adjudicated', reviews=self.human_reviews(),
                           gold_eligible=True, adjudication={
            'adjudicator_id': 'test-human-c',
            'adjudicated_at': '2026-11-10T13:00:00+09:00',
            'judgment': 'PRESERVED', 'rationale': 'Test-only simulated adjudication',
            'input_sha256': self.answer['input_sha256']})
        self.assertTrue(validate_pair(self.input, self.answer, ROOT))

    def test_conflicting_reviews_need_disagreement_record(self):
        self.answer.update(status='reviewed', reviews=self.human_reviews())
        self.answer['reviews'][1]['judgment'] = 'VIOLATION'
        with self.assertRaisesRegex(ValueError, 'disagreement record'):
            validate_pair(self.input, self.answer, ROOT)

    def test_stale_human_review(self):
        self.answer.update(status='reviewed', reviews=self.human_reviews())
        self.answer['reviews'][0]['input_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'stale human review'):
            validate_pair(self.input, self.answer, ROOT)

    def test_stale_answer_binding(self):
        self.answer['input_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'stale answer/input'):
            validate_pair(self.input, self.answer, ROOT)

    def test_public_snapshot_tamper(self):
        inp = json.loads((ROOT / 'inputs/SP-001.json').read_text())
        answer = json.loads((ROOT / 'answers/SP-001.json').read_text())
        path = self.root / 'sources/chatgpt2codex-README.md'
        path.write_bytes(path.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'snapshot hash'):
            validate_pair(inp, answer, self.root)

    def test_manifest_tamper_and_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'pilot'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('__pycache__'))
            path = root / 'answers/SP-001.json'
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.assertRaises(ValueError):
                validate_dataset(root)
            path.unlink()
            with self.assertRaises(ValueError):
                validate_dataset(root)

if __name__ == '__main__':
    unittest.main()
