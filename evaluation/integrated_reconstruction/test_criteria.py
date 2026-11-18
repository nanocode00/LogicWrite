"""Version/lineage mutations; all writes stay in disposable package copies."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class CriteriaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'package'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('__pycache__'))
        spec = importlib.util.spec_from_file_location('criteria_validation', ROOT / 'validate_criteria.py')
        self.v = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.v)

    def mutate(self, path, fn, reseal=False):
        p = self.root / path
        d = json.loads(p.read_text())
        fn(d)
        p.write_text(json.dumps(d, ensure_ascii=False) + '\n')
        if reseal:
            m = self.root / 'criteria/v2/manifest.json'
            manifest = json.loads(m.read_text())
            for entry in manifest['cases']:
                if entry['criteria_path'] == path:
                    entry['criteria_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            m.write_text(json.dumps(manifest))

    def test_valid(self):
        result = self.v.validate(self.root)
        self.assertEqual(result['change_requests_implemented'], 6)
        self.assertFalse(result['gold_eligible'])

    def test_stale_parent_and_input_rejected(self):
        for path in ['answers/IR-001.json', 'inputs/IR-002.json', 'reference_outputs/IR-001.json']:
            with self.subTest(path=path):
                p = self.root / path
                original = p.read_bytes()
                p.write_bytes(original + b' ')
                with self.assertRaises(ValueError):
                    self.v.validate(self.root)
                p.write_bytes(original)

    def test_resealed_unapproved_criterion_change_rejected(self):
        self.mutate('criteria/v2/IR-002.json', lambda d: d['Q']['invariants'][1].update(criterion='500건 이상'), True)
        with self.assertRaisesRegex(ValueError, 'unauthorized criterion'):
            self.v.validate(self.root)

    def test_resealed_false_evidence_rejected(self):
        self.mutate('criteria/v2/IR-001.json', lambda d: d['evidence'][0].update(quote='없는 인용'), True)
        with self.assertRaisesRegex(ValueError, 'quote mismatch'):
            self.v.validate(self.root)

    def test_missing_request_rejected(self):
        self.mutate('criteria/v2/manifest.json', lambda d: d['cases'][0]['change_requests'].pop())
        with self.assertRaises(ValueError):
            self.v.validate(self.root)

    def test_no_invented_human_recheck_or_approval(self):
        for key, value in [('post_revision_human_review', 'passed'), ('gold_inclusion_approval', 'approved')]:
            with self.subTest(key=key):
                original = (self.root / 'criteria/v2/manifest.json').read_bytes()
                self.mutate('criteria/v2/manifest.json', lambda d: d['cases'][0].update({key: value}))
                with self.assertRaises(ValueError):
                    self.v.validate(self.root)
                (self.root / 'criteria/v2/manifest.json').write_bytes(original)

    def test_ir003_criteria_not_revised(self):
        self.mutate('criteria/v2/manifest.json', lambda d: d['cases'][1].update(case_id='IR-003'))
        with self.assertRaises(ValueError):
            self.v.validate(self.root)

    def test_review_overwrite_rejected(self):
        self.mutate('reviews/IR-003.json', lambda d: d.update(counterreview='독립 사람 검수 완료'))
        with self.assertRaises(ValueError):
            self.v.validate(self.root)

    def test_read_only_on_success_and_failure(self):
        def snapshot():
            return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        before = snapshot()
        self.v.validate(self.root)
        self.assertEqual(before, snapshot())
        self.mutate('criteria/v2/manifest.json', lambda d: d['cases'][0].update(criteria_sha256='0' * 64))
        before = snapshot()
        with self.assertRaises(ValueError):
            self.v.validate(self.root)
        self.assertEqual(before, snapshot())

    def test_invalid_request_location_rejected(self):
        self.mutate('criteria/v2/manifest.json', lambda d: d['cases'][0]['change_requests'][0].update(locations=['D.not_present']))
        with self.assertRaisesRegex(ValueError, 'request location'):
            self.v.validate(self.root)

    def test_q1_matches_user_revision_exactly(self):
        record = json.loads((self.root / 'criteria/v2/IR-002.json').read_text())
        expected = '문서군 전체에서 2026-11-12 이후 운영 환경 60초, 개발 환경 30초라는 현행 정책과 적용 시점을 정확하게 확인할 수 있어야 한다. 각 문서는 자신의 역할에 필요한 조건을 제공하며, 동일한 조건을 서술하는 경우 문서 간 충돌이 없어야 한다.'
        self.assertEqual(record['Q']['invariants'][0]['criterion'], expected)

    def test_ir003_stages_and_gated_gold_are_separate(self):
        review = json.loads((self.root / 'reviews/IR-003.json').read_text())
        self.assertEqual(review['initial_judgment'], '당장 추가하거나 뺄 내용이 보이지 않으며, 수정 권한과 회의 대상을 확인하면 될 것으로 보인다.')
        self.assertIn('AI 초안 열람 이전', review['answer_exposure'])
        self.assertIn('이후 ChatGPT', review['answer_exposure'])
        self.assertIn('독립 사람 반례 검토로 집계하지 않는다', review['counterreview'])
        self.assertIn('사람 검수 통과', review['final_judgment'])
        self.assertIsNone(review['gold_inclusion_approval'])

    def test_q3_review_location_and_reader_task(self):
        record = json.loads((self.root / 'criteria/v2/IR-001.json').read_text())
        q3 = record['Q']['invariants'][2]['criterion']
        self.assertIn('평가 제출물의 검토 기록·HITL 요청', q3)
        self.assertIn('README 본문에는 내부 검토 의견이나 미확정 정책을 남기는 것을 허용하지 않는다', q3)
        self.assertIn('평가 제출물의 검토 기록·HITL 요청에만', q3)
        self.assertIn('독립적으로 가능한 개선은 계속한다', q3)
        self.assertEqual(q3, record['Q']['reader_tasks'][2])

    def test_correction_parent_hash_cannot_be_resealed(self):
        self.mutate('criteria/v2/manifest.json', lambda d: d['correction'].update(parent_manifest_sha256='0' * 64))
        with self.assertRaises(ValueError):
            self.v.validate(self.root)

    def test_ir001_d2_and_f1_cannot_change_during_clarification(self):
        for section, index in [('D', 1), ('Q', 0)]:
            original = (self.root / 'criteria/v2/IR-001.json').read_bytes()
            manifest = (self.root / 'criteria/v2/manifest.json').read_bytes()
            group = 'decision_criteria' if section == 'D' else 'forbidden_outcomes'
            self.mutate('criteria/v2/IR-001.json', lambda d: d[section][group][index].update(criterion='임의 정책 적용'), True)
            with self.assertRaises(ValueError):
                self.v.validate(self.root)
            (self.root / 'criteria/v2/IR-001.json').write_bytes(original)
            (self.root / 'criteria/v2/manifest.json').write_bytes(manifest)

    def test_readme_prohibition_parent_hash_verified(self):
        self.mutate('criteria/v2/manifest.json', lambda d: d['correction']['follow_up'].update(parent_criteria_sha256='0' * 64))
        with self.assertRaises(ValueError):
            self.v.validate(self.root)
