"""Corrupt isolated copies to exercise integrity boundaries, never source files."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('capability_integrity', ROOT / 'validate.py')
        self.assertTrue(spec and spec.loader and (ROOT / 'validate.py').exists(), 'validator must exist')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'pilot'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('__pycache__'))

    def edit(self, path, mutate):
        file = self.root / path
        obj = json.loads(file.read_text())
        mutate(obj)
        file.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

    def validate(self):
        return self.module.validate_package(self.root, require_reviews=False)

    def rebind(self):
        p = self.root / 'inputs/CP-T1-01.json'
        value = hashlib.sha256(p.read_bytes()).hexdigest()
        self.edit('answers/CP-T1-01.json', lambda a: a.update(input_sha256=value))
        self.edit('reviews/CP-T1-01.json', lambda r: r.update(input_sha256=value))

    def test_read_only_record_may_be_returned_but_never_edited(self):
        self.assertEqual(self.validate()['cases'], 57)
        self.edit('inputs/CP-T9-05.json', lambda i: i['allowed_edit_scope']['document_ids'].append('report'))
        p = self.root / 'inputs/CP-T9-05.json'
        value = hashlib.sha256(p.read_bytes()).hexdigest()
        self.edit('answers/CP-T9-05.json', lambda a: a.update(input_sha256=value))
        self.edit('reviews/CP-T9-05.json', lambda r: r.update(input_sha256=value))
        with self.assertRaises(ValueError): self.validate()

    def test_partial_output_is_not_correct_abstention(self):
        a = json.loads((self.root / 'answers/CP-T9-06.json').read_text())
        self.assertFalse(a['metrics']['D']['abstention']['expected'])
        self.assertEqual(a['Q']['applicability'], 'not_evaluated_incomplete')
        self.edit('answers/CP-T9-06.json', lambda a: a['metrics']['D']['abstention'].update(expected=True))
        with self.assertRaises(ValueError): self.validate()

    def test_duplicate_required_id_cannot_shrink_recall_denominator(self):
        def bad(a):
            item = dict(a['D']['required_decisions'][0])
            item['criterion'] = 'another obligation with a reused ID'
            a['D']['required_decisions'].append(item)
        self.edit('answers/CP-T1-01.json', bad)
        with self.assertRaises(ValueError): self.validate()

    def test_incomplete_or_nonindependent_raw_review_rejected(self):
        review = json.loads((self.root / 'reviews/CP-T1-01.json').read_text())
        rec = review['independent_ai_counterreview']
        self.edit(rec['path'], lambda r: r.update(method='answers read; not input-only'))
        value = hashlib.sha256((self.root / rec['path']).read_bytes()).hexdigest()
        for path in (self.root / 'reviews').glob('*.json'):
            obj = json.loads(path.read_text())
            if obj['independent_ai_counterreview']['path'] == rec['path']:
                obj['independent_ai_counterreview']['sha256'] = value
                path.write_text(json.dumps(obj, ensure_ascii=False))
        with self.assertRaises(ValueError): self.validate()

    def test_empty_counterreview_evidence_rejected(self):
        review = json.loads((self.root / 'reviews/CP-T1-01.json').read_text())
        rec = review['independent_ai_counterreview']
        self.edit(rec['path'], lambda r: r['cases'][0]['evidence'][0].update(quote=''))
        value = hashlib.sha256((self.root / rec['path']).read_bytes()).hexdigest()
        for path in (self.root / 'reviews').glob('*.json'):
            obj = json.loads(path.read_text())
            if obj['independent_ai_counterreview']['path'] == rec['path']:
                obj['independent_ai_counterreview']['sha256'] = value
                path.write_text(json.dumps(obj, ensure_ascii=False))
        with self.assertRaises(ValueError): self.validate()

    def test_malformed_human_response_rejected_without_rewriting(self):
        path = self.root / 'human_responses.json'
        path.write_text('{"unfinished_user_notes":"보존해야 함"}')
        before = path.read_bytes(), path.stat().st_mtime_ns
        with self.assertRaises(ValueError): self.validate()
        self.assertEqual(before, (path.read_bytes(), path.stat().st_mtime_ns))

    def test_user_response_never_promotes_provisional_records(self):
        self.edit('human_responses.json', lambda r: r['cases'][0].update(final_judgment='내 판단 초안: 포함 보류'))
        result = self.validate()
        self.assertEqual(result['formal_gold_approvals'], 0)
        self.assertEqual(json.loads((self.root / 'reviews/CP-T1-01.json').read_text())['status'], 'provisional')

    def test_previous_review_input_bytes_remain_bound(self):
        self.edit('reviewed_inputs/CP-T4-01.json', lambda i: i['task'].update(purpose='rewritten history'))
        with self.assertRaises(ValueError): self.validate()

    def test_dataset(self):
        result = self.validate()
        self.assertGreaterEqual(result['cases'], 36)
        self.assertEqual(result['calibration'], 9)

    def test_answer_leak_rejected_even_when_rebound(self):
        self.edit('inputs/CP-T1-01.json', lambda i: i.update(required_decisions=['KEEP']))
        self.rebind()
        with self.assertRaises(ValueError): self.validate()

    def test_stale_input_binding(self):
        self.edit('inputs/CP-T1-01.json', lambda i: i['task'].update(purpose='different'))
        with self.assertRaises(ValueError): self.validate()

    def test_bad_document_hash(self):
        self.edit('inputs/CP-T1-01.json', lambda i: i['source_documents'][0].update(content='changed'))
        self.rebind()
        with self.assertRaises(ValueError): self.validate()

    def test_invented_evidence_span(self):
        self.edit('answers/CP-T1-01.json', lambda a: a['evidence'][0].update(quote='invented'))
        with self.assertRaises(ValueError): self.validate()

    def test_alternative_cannot_require_forbidden_effect(self):
        def bad(a):
            a['D']['acceptable_alternatives'][0]['effects'].update(a['D']['forbidden_effects'])
        self.edit('answers/CP-T1-01.json', bad)
        with self.assertRaises(ValueError): self.validate()

    def test_fake_approval_rejected(self):
        self.edit('reviews/CP-T1-01.json', lambda r: r.update(gold_inclusion_approval={'approved': True}))
        with self.assertRaises(ValueError): self.validate()

    def test_snapshot_tampering_rejected(self):
        sources = json.loads((self.root / 'sources.json').read_text())
        (self.root / sources[0]['document']['path']).write_text('tampered')
        with self.assertRaises(ValueError): self.validate()

    def test_family_reuse_not_independent(self):
        self.edit('cases.json', lambda rows: rows[1].update(source_family=rows[0]['source_family']))
        with self.assertRaises(ValueError): self.validate()

    def test_path_traversal_rejected(self):
        self.edit('sources.json', lambda rows: rows[0]['document'].update(path='../escape'))
        with self.assertRaises(ValueError): self.validate()

    def test_unknown_destination_scope(self):
        self.edit('inputs/CP-T1-01.json', lambda i: i['allowed_edit_scope']['document_ids'].append('unknown'))
        self.rebind()
        with self.assertRaises(ValueError): self.validate()

    def test_missing_is_distinct_from_partial(self):
        self.edit('inputs/CP-T1-01.json', lambda i: i['source_documents'][0].update(availability='not_provided'))
        self.rebind()
        with self.assertRaises(ValueError): self.validate()

    def test_validation_never_overwrites_human_responses_even_on_error(self):
        response = self.root / 'human_responses.json'
        response.write_text('{"user_text":"검토중; 그대로 보존"}')
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        self.edit('answers/CP-T1-01.json', lambda a: a.update(input_sha256='0'*64))
        before[self.root / 'answers/CP-T1-01.json'] = ((self.root / 'answers/CP-T1-01.json').read_bytes(), (self.root / 'answers/CP-T1-01.json').stat().st_mtime_ns)
        with self.assertRaises(ValueError): self.validate()
        after = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

if __name__ == '__main__': unittest.main()
