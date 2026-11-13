"""Mutation tests use copies; never render over a person's response."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('integrated_validate', ROOT / 'validate.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'package'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('__pycache__'))

    def mutate(self, path, fn):
        p = self.root / path
        x = json.loads(p.read_text())
        fn(x)
        p.write_text(json.dumps(x, ensure_ascii=False) + '\n')

    def reject(self):
        with self.assertRaises((ValueError, KeyError)):
            v.validate_package(self.root)

    def test_valid(self):
        self.assertEqual(v.validate_package(self.root)['cases'], 3)

    def test_answer_leak(self):
        self.mutate('inputs/IR-001.json', lambda x: x.update(expected_actions=['REMOVE']))
        self.reject()

    def test_stale_input(self):
        self.mutate('inputs/IR-001.json', lambda x: x.update(request=x['request'] + ' 추가'))
        self.reject()

    def test_snapshot_hash(self):
        self.mutate('inputs/IR-001.json', lambda x: x['documents'][0].update(content='변조'))
        self.reject()

    def test_exact_quote(self):
        self.mutate('answers/IR-001.json', lambda x: x['evidence'][0].update(quote='가짜'))
        self.reject()

    def test_unknown_evidence(self):
        self.mutate('answers/IR-001.json', lambda x: x['D']['decision_criteria'][0].update(evidence_refs=['E999']))
        self.reject()

    def test_duplicate_document(self):
        self.mutate('inputs/IR-001.json', lambda x: x['documents'].append(x['documents'][0]))
        self.reject()

    def test_fake_gold(self):
        self.mutate('answers/IR-001.json', lambda x: x.update(gold_eligible=True))
        self.reject()

    def test_forged_approval(self):
        self.mutate('reviews/IR-001.json', lambda x: x.update(gold_inclusion_approval='AI 승인'))
        self.reject()

    def test_incomplete_full_output(self):
        self.mutate('reference_outputs/IR-001.json', lambda x: x['documents'].pop())
        self.reject()

    def test_read_only_output(self):
        self.mutate('reference_outputs/IR-001.json', lambda x: x['documents'][0].update(document_id='history'))
        self.reject()

    def test_format_only_semantic_edit(self):
        def change(x):
            d = x['documents'][0]
            d['content'] = d['content'].replace('1건 실패', '1건 성공')
            d['sha256'] = hashlib.sha256(d['content'].encode()).hexdigest()
        self.mutate('reference_outputs/IR-003.json', change)
        self.reject()

    def test_format_only_numeric_token_split(self):
        def change(x):
            d = x['documents'][0]
            d['content'] = d['content'].replace('12건 중 11건 완료', '1 2건 중 1 1건 완료')
            d['sha256'] = hashlib.sha256(d['content'].encode()).hexdigest()
        self.mutate('reference_outputs/IR-003.json', change)
        self.reject()

    def test_format_only_word_token_join(self):
        def change(x):
            d = x['documents'][0]
            d['content'] = d['content'].replace('12건 중', '12건중')
            d['sha256'] = hashlib.sha256(d['content'].encode()).hexdigest()
        self.mutate('reference_outputs/IR-003.json', change)
        self.reject()

    def test_path_escape(self):
        self.mutate('answers/IR-001.json', lambda x: x['Q'].update(reference_output_path='../outside.json'))
        self.reject()

    def test_broken_local_link(self):
        def change(x):
            d = x['documents'][0]
            d['content'] += '\n[없는 경로](missing.md)\n'
            d['sha256'] = hashlib.sha256(d['content'].encode()).hexdigest()
        self.mutate('reference_outputs/IR-001.json', change)
        self.reject()

    def test_alternative_cannot_skip_invariants(self):
        self.mutate('answers/IR-001.json', lambda x: x['Q']['acceptable_bundles'][0].update(must_satisfy=['Q1']))
        self.reject()

    def test_review_survives_success_and_failure(self):
        self.mutate('reviews/IR-001.json', lambda x: x.update(initial_judgment='사람이 작성한 초안 의견'))
        p = self.root / 'reviews/IR-001.json'
        before = (p.read_bytes(), p.stat().st_mtime_ns)
        v.validate_package(self.root)
        self.assertEqual(before, (p.read_bytes(), p.stat().st_mtime_ns))
        self.mutate('answers/IR-001.json', lambda x: x.update(gold_eligible=True))
        self.reject()
        self.assertEqual(before, (p.read_bytes(), p.stat().st_mtime_ns))

    def test_export_input_only(self):
        x = v.export_input(self.root, 'IR-001')
        self.assertEqual(set(x), set(json.loads((self.root/'inputs/IR-001.json').read_text())))
        self.assertNotIn('D', x)
        self.assertNotIn('source_family', x)
        self.assertNotIn('answer', json.dumps(x))

if __name__ == '__main__':
    unittest.main()
