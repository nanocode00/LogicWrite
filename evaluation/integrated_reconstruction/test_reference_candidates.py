"""Candidate package integrity tests, not a general semantic evaluator."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class ReferenceCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'package'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('__pycache__'))
        spec = importlib.util.spec_from_file_location('candidate_validation', ROOT / 'validate_reference_candidates.py')
        self.v = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.v)

    def mutate_reference(self, cid, fn):
        path = self.root / 'reference_outputs/v2_candidates' / (cid + '.json')
        ref = json.loads(path.read_text())
        fn(ref)
        for doc in ref['documents']:
            doc['sha256'] = hashlib.sha256(doc['content'].encode()).hexdigest()
        path.write_text(json.dumps(ref, ensure_ascii=False) + '\n')
        manifest_path = path.parent / 'manifest.json'
        m = json.loads(manifest_path.read_text())
        next(e for e in m['cases'] if e['case_id'] == cid)['reference_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(m))

    def test_valid_and_not_approved(self):
        r = self.v.validate(self.root)
        self.assertEqual(r['candidate_cases'], 2)
        self.assertFalse(r['gold_eligible'])
        self.assertEqual(r['semantic_approval'], 'not_granted')

    def test_missing_writable_document_rejected(self):
        self.mutate_reference('IR-001', lambda r: r['documents'].pop())
        with self.assertRaisesRegex(ValueError, 'document set'):
            self.v.validate(self.root)

    def test_read_only_document_return_rejected(self):
        self.mutate_reference('IR-002', lambda r: r['documents'].append(dict(document_id='adr', content='changed', sha256='0'*64)))
        with self.assertRaisesRegex(ValueError, 'document set'):
            self.v.validate(self.root)

    def test_unapproved_funding_rewrite_rejected_for_this_candidate(self):
        self.mutate_reference('IR-001', lambda r: r['documents'][0].update(content=r['documents'][0]['content'].replace('기부는 [후원 안내](FUNDING.md)에서 할 수 있습니다.', '금전 후원은 받지 않습니다.')))
        with self.assertRaisesRegex(ValueError, 'frozen passage'):
            self.v.validate(self.root)

    def test_unconfirmed_diary_removal_rejected_for_this_candidate(self):
        self.mutate_reference('IR-001', lambda r: r['documents'][0].update(content=r['documents'][0]['content'].replace('11월 7일 회의 간식은 귤이었다.', '')))
        with self.assertRaisesRegex(ValueError, 'frozen passage'):
            self.v.validate(self.root)

    def test_blanket_deferral_with_no_hitl_context_rejected(self):
        self.mutate_reference('IR-001', lambda r: r.update(unresolved_questions=[], deferred_scope=[]))
        with self.assertRaisesRegex(ValueError, 'HITL'):
            self.v.validate(self.root)

    def test_stale_criteria_and_original_reference_rejected(self):
        for name in ('criteria/v2/IR-001.json', 'reference_outputs/IR-002.json'):
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.assertRaises(ValueError):
                self.v.validate(self.root)
            path.write_bytes(original)

    def test_missing_and_broken_link_rejected(self):
        self.mutate_reference('IR-002', lambda r: r['documents'][0].update(content=r['documents'][0]['content']+'\n[운영](missing.md)\n'))
        with self.assertRaisesRegex(ValueError, 'broken local link'):
            self.v.validate(self.root)

    def test_review_and_input_hashes_bound(self):
        for name in ('reference_outputs/v2_candidates/REVIEW.md', 'inputs/IR-001.json'):
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.assertRaises(ValueError):
                self.v.validate(self.root)
            path.write_bytes(original)

    def test_validation_never_overwrites_candidate(self):
        def snapshot():
            return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        before = snapshot()
        self.v.validate(self.root)
        self.assertEqual(before, snapshot())
        self.mutate_reference('IR-001', lambda r: r.update(executed_by_system=True))
        before = snapshot()
        with self.assertRaises(ValueError):
            self.v.validate(self.root)
        self.assertEqual(before, snapshot())

    def test_execution_conditions_in_this_fixture(self):
        ref = json.loads((self.root / 'reference_outputs/v2_candidates/IR-001.json').read_text())
        docs = {d['document_id']: d['content'] for d in ref['documents']}
        self.assertNotIn('python -m pip install', docs['readme'])
        usage = docs['usage']
        for value in ('Python 3.11 이상', 'python -m pip install paperdock==0.8.0',
                      'paperdock index ./notes --out ./index.json', 'python -m unittest',
                      '입력 폴더 기준 상대 경로', '본문을 바꾸거나 외부로 전송하지 않습니다'):
            self.assertIn(value, usage)
        self.assertLess(usage.index('출력 상위 폴더가 미리 존재'), usage.index('paperdock index'))
        self.assertLess(usage.index('기존 파일을 덮어쓰지 않습니다'), usage.index('paperdock index'))

    def test_single_policy_location_and_bounded_observation_fixture(self):
        ref = json.loads((self.root / 'reference_outputs/v2_candidates/IR-002.json').read_text())
        docs = {d['document_id']: d['content'] for d in ref['documents']}
        self.assertNotIn('60초', docs['design'])
        self.assertNotIn('30초', docs['design'])
        for value in ('2026-11-12부터 운영 환경은 60초, 개발 환경은 30초',
                      '2026-11-11까지는 운영 환경도 30초', '09:00', '10분 이상',
                      '500건을 넘으면', '당직자가 확인하기 전에는 재개하지 않는다',
                      '#queue-oncall', 'Q-1', '24시간'):
            self.assertIn(value, docs['ops'])
        for value in ('2026-11-09~11-12', '20건', '19건 처리, 1건 대기',
                      '재처리 완료 여부는 미확인', '표본이 적고 정책 적용 시점이 섞여',
                      '안정성을 입증한 결과가 아니다'):
            self.assertIn(value, docs['design'])
