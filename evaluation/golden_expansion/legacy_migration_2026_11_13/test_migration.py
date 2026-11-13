"""Only disposable copies are altered; no synthetic human review events."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import validate_migration as v


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.here = Path(self.tmp.name) / 'migration'
        self.v3 = Path(self.tmp.name) / 'v3'
        shutil.copytree(v.HERE, self.here, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(v.V3, self.v3, ignore=shutil.ignore_patterns('__pycache__'))

    def check(self):
        return v.validate(here=self.here, v3=self.v3)

    def write(self, path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

    def reseal(self):
        self.write(self.here / 'artifact-manifest.json', {
            name: v.sha(v.artifact_path(name, self.here, self.v3).read_bytes()) for name in v.ARTIFACTS
        })

    def test_29_candidate_correct_distribution_and_v2_rows_unchanged(self):
        result = self.check()
        candidate = v.load(self.v3 / 'development-gold.json')
        old = v.load(v.ROOT / v.V2_PATH)
        self.assertEqual(candidate['cases'][:12], old['cases'])
        self.assertEqual(candidate['case_count'], 29)
        self.assertEqual(candidate['distribution'], {'PRESERVED': 12, 'VIOLATION': 9, 'UNRESOLVED': 8})
        self.assertEqual(len(set(candidate['case_ids'])), 29)
        self.assertEqual(result['legacy_evidence_validated'], 17)
        self.assertEqual(result['new_activation_eligible'], 0)
        self.assertEqual(result['current_active_count'], 12)
        self.assertEqual(result['existing_eligible'], 12)

    def test_pending_policy_blocks_actual_activation(self):
        with self.assertRaisesRegex(ValueError, 'policy approval required'):
            v.require_activation_ready(here=self.here, v3=self.v3)
        candidate = v.load(self.v3 / 'development-gold.json')
        self.assertFalse(candidate['active'])
        self.assertEqual(candidate['active_case_ids'], [])
        self.assertIsNone(v.load(self.here / 'policy.json')['user_policy_approval'])
        self.assertTrue(all(not r['development_gold_eligible'] for r in candidate['cases'][12:]))

    def test_case_agreement_not_mapped_and_ai_evidence_not_human(self):
        self.check()
        for row in v.load(self.here / 'legacy-records.json')['cases']:
            self.assertEqual(row['final_human']['response'], '동의')
            self.assertEqual(row['final_human']['response_target'], 'AI counterargument validity assessment')
            self.assertIsNone(row['unrecorded_formal_fields']['challenge_decision'])
            self.assertIsNone(row['unrecorded_formal_fields']['user_final_evidence'])
            self.assertIsNone(row['unrecorded_formal_fields']['user_reviewed_at'])
            self.assertFalse(row['ai_review']['evidence_attributed_to_human'])

    def test_unresolved_8_preserved_4_reaffirmed_without_new_review(self):
        self.check()
        rows = v.load(self.here / 'legacy-records.json')['cases']
        unresolved = [r for r in rows if r['final_human']['judgment'] == 'UNRESOLVED']
        self.assertEqual([r['case_id'] for r in unresolved], ['GC-003','GC-006','GC-009','GC-012'])
        for r in unresolved:
            self.assertEqual(r['reason_retention']['reason'], r['initial_human']['reason'])
            self.assertEqual(r['reason_retention']['attribution'], 'user_reason_retained_by_current_request')
        self.assertEqual(v.load(self.v3 / 'development-gold.json')['distribution']['UNRESOLVED'], 8)

    def test_source_families_and_parent_relationships_preserved(self):
        self.check()
        rows = v.load(self.here / 'legacy-records.json')['cases']
        families = {f for r in rows[:12] for f in r['lineage']['source_families']}
        self.assertEqual(families, {'psf/requests','encode/httpx','pallets/click','prometheus/prometheus'})
        self.assertTrue(all(r['lineage']['parent_inputs'] for r in rows[12:]))
        self.assertTrue(all(r['development_only'] and not r['independent_multi_human_complete'] for r in rows))

    def test_resealed_record_tampering_scope_label_approval_attribution(self):
        path = self.here / 'legacy-records.json'
        original = path.read_bytes()
        changes = [lambda x: x['cases'].pop(),
                   lambda x: x['cases'].__setitem__(1, copy.deepcopy(x['cases'][0])),
                   lambda x: x['cases'].reverse(),
                   lambda x: x['cases'][2]['final_human'].update(judgment='PRESERVED'),
                   lambda x: x['cases'][0]['final_human'].update(response='reject'),
                   lambda x: x['cases'][0]['ai_review'].update(evidence_attributed_to_human=True),
                   lambda x: x['cases'][0].update(activation_eligible=True),
                   lambda x: x['cases'][0]['inclusion'].update(approved=False)]
        for mutate in changes:
            with self.subTest(mutate=mutate):
                path.write_bytes(original)
                data = v.load(path); mutate(data); self.write(path, data); self.reseal()
                with self.assertRaises(ValueError): self.check()

    def test_resealed_v3_wrong_label_missing_duplicate_or_active_rejected(self):
        path = self.v3 / 'development-gold.json'; original = path.read_bytes()
        for mutate in [lambda x: x['cases'][0].update(user_final_judgment='VIOLATION'),
                       lambda x: x['cases'][14].update(user_final_judgment='PRESERVED'),
                       lambda x: x['cases'].pop(),
                       lambda x: x['case_ids'].__setitem__(1, x['case_ids'][0]),
                       lambda x: x.update(active=True, active_case_ids=x['case_ids'])]:
            with self.subTest(mutate=mutate):
                path.write_bytes(original)
                data=v.load(path);mutate(data);self.write(path,data);self.reseal()
                with self.assertRaises(ValueError): self.check()

    def test_policy_or_request_cannot_be_implicitly_approved(self):
        for filename, key, value in [('policy.json','user_policy_approval',True),
                                     ('policy.json','status','approved'),
                                     ('continuation-request.json','user_reviewed_at','invented')]:
            with self.subTest(filename=filename,key=key):
                path=self.here/filename; original=path.read_bytes()
                data=v.load(path);data[key]=value;self.write(path,data);self.reseal()
                with self.assertRaises(ValueError): self.check()
                path.write_bytes(original)

    def test_event_order_uses_git_ancestry_not_invented_timestamps(self):
        order=v.verify_order(v.ROOT)
        self.assertEqual([r['stage'] for r in order], ['initial','ai_counterreview','user_final','inclusion'])
        with self.assertRaises(ValueError): v.verify_order(v.ROOT, list(reversed(v.STAGES)))
        self.assertTrue(all('user_reviewed_at' not in r for r in order))

    def test_existing_sources_policy_v2_and_evaluation_records_unchanged(self):
        root = Path(self.tmp.name)/'source-copy'
        for name in v.load(self.here/'preserved-files.json'):
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(v.ROOT/name,target)
        for name in [v.V2_PATH, v.FINAL+'/events.json', v.APPROVAL+'/events.json',
                     v.COUNTER+'/gc01_06.raw.json', 'evaluation/golden_expansion/review.py',
                     'evaluation/golden_expansion/record.schema.json']:
            with self.subTest(name=name):
                path=root/name;raw=path.read_bytes();path.write_bytes(raw+b' ')
                with self.assertRaisesRegex(ValueError,'existing file changed'):
                    v.validate(root=root,here=self.here,v3=self.v3)
                path.write_bytes(raw)

    def test_read_only_and_current_active_references_remain_v2(self):
        paths=[p for folder in (self.here,self.v3) for p in folder.rglob('*') if p.is_file()]
        before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths}
        self.check()
        self.assertEqual(before,{p:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths})
        for name in v.CONSUMERS: self.assertIn(v.V2_PATH,(v.ROOT/name).read_text())

    def test_deleted_evidence_and_reduced_manifest_rejected(self):
        path=self.here/'legacy-records.json';raw=path.read_bytes();path.unlink()
        with self.assertRaises((ValueError,FileNotFoundError)):self.check()
        path.write_bytes(raw)
        manifest=v.load(self.here/'artifact-manifest.json');manifest.pop('migration/legacy-records.json')
        self.write(self.here/'artifact-manifest.json',manifest)
        with self.assertRaises(ValueError):self.check()
