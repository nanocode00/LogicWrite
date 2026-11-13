"""Activation and evaluation integration; fixtures never become human evidence."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import runtime
import source_candidate as source
import core_diagnostics as core
v = runtime.activation_module()


class ActiveGoldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.here = base/'activation'; self.consumers=base/'consumers'; self.index=base/'active.json'
        shutil.copytree(v.HERE,self.here,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(v.CONSUMERS,self.consumers,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(v.INDEX,self.index)

    def check(self):return v.validate(here=self.here,consumers=self.consumers,index=self.index)
    def write(self,p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
    def reseal(self):
        self.write(self.here/'artifact-manifest.json',{
            n:v.sha(v.artifact(n,self.here,self.consumers,self.index).read_bytes()) for n in v.ARTIFACTS})

    def test_approved17_active29_distribution_v2_rows_unchanged(self):
        r=self.check();self.assertEqual(r['active_count'],29);self.assertEqual(r['newly_eligible'],17)
        self.assertEqual(r['distribution'],{'PRESERVED':12,'VIOLATION':9,'UNRESOLVED':8})
        active=v.load(self.here/'development-gold.json');old=v.load(v.ROOT/v.V2)
        self.assertEqual(active['cases'][:12],old['cases'])
        self.assertEqual(len(set(active['active_case_ids'])),29)
        self.assertTrue(all(x['development_gold_eligible'] for x in active['cases']))
        self.assertTrue(all(not x['independent_multi_human_complete'] for x in active['cases']))

    def test_policy_approval_exact_scope_null_metadata_and_canonical_chain(self):
        self.check();d=v.load(self.here/'policy-approval.json')
        self.assertEqual(d['case_ids'],v.IDS);self.assertEqual(len(d['case_approvals']),17)
        self.assertIsNone(d['user_approved_at']);self.assertIsNone(d['signature'])
        self.assertIsNone(d['authenticated_identity']);self.assertFalse(d['externally_authenticated'])
        self.assertEqual(d['actor_type'],'human');self.assertEqual(d['recorder_type'],'ai')

    def test_policy_approval_tampering_and_scope_expansion_after_reseal(self):
        p=self.here/'policy-approval.json';raw=p.read_bytes()
        for change in [lambda d:d.update(approved=False),lambda d:d['case_ids'].append('SP-001'),
                       lambda d:d['case_approvals'].pop(),lambda d:d.update(user_approved_at='invented')]:
            with self.subTest(change=change):
                p.write_bytes(raw);d=v.load(p);change(d);self.write(p,d);self.reseal()
                with self.assertRaises(ValueError):self.check()

    def test_manifest_label_inventory_reference_or_eligibility_tamper_rejected(self):
        p=self.here/'development-gold.json';raw=p.read_bytes()
        for change in [lambda d:d['cases'][14].update(user_final_judgment='PRESERVED'),
                       lambda d:d['cases'].pop(),lambda d:d['active_case_ids'].__setitem__(1,d['active_case_ids'][0]),
                       lambda d:d['cases'][12].update(development_gold_eligible=False),
                       lambda d:d['cases'][12]['policy_approval'].update(pointer='/case_approvals/1')]:
            with self.subTest(change=change):
                p.write_bytes(raw);d=v.load(p);change(d);self.write(p,d);self.reseal()
                with self.assertRaises(ValueError):self.check()

    def test_deletion_index_or_history_tampering_rejected(self):
        for p in [self.here/'policy-approval.json',self.here/'activation-history.json',self.index]:
            with self.subTest(path=p):
                raw=p.read_bytes();p.unlink()
                with self.assertRaises((ValueError,FileNotFoundError)):self.check()
                p.write_bytes(raw)
        d=v.load(self.index);d['active_dataset']['path']=v.V2;self.write(self.index,d);self.reseal()
        with self.assertRaises(ValueError):self.check()

    def test_original_sources_v2_and_formal_policy_remain_frozen(self):
        baseline=v.load(self.here/'preserved-files.json');root=Path(self.tmp.name)/'old'
        for name in baseline:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(v.ROOT/name,target)
        for name in [v.V2,'evaluation/golden_expansion/review.py',v.FINAL+'/events.json',v.LEGACY+'/policy.json']:
            with self.subTest(name=name):
                p=root/name;raw=p.read_bytes();p.write_bytes(raw+b' ')
                with self.assertRaisesRegex(ValueError,'existing file changed'):
                    v.validate(root=root,here=self.here,consumers=self.consumers,index=self.index)
                p.write_bytes(raw)

    def test_validation_is_read_only(self):
        paths=[p for d in (self.here,self.consumers) for p in d.rglob('*') if p.is_file()]+[self.index]
        before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths};self.check()
        self.assertEqual(before,{p:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths})

    def test_predictions_load_input_only_for_all29(self):
        original=Path.read_bytes
        def guarded(path):
            self.assertNotIn('answers',path.parts);self.assertNotEqual(path.name,'development-gold.json')
            self.assertNotEqual(path.name,'active_development_gold.json');return original(path)
        with patch.object(Path,'read_bytes',guarded):
            p=source.predict(list(runtime.CASE_IDS))
            c=core.run_predictions()
        self.assertEqual(len(p['cases']),29);self.assertEqual(len(c['cases']),29)
        self.assertFalse(p['reference_labels_loaded']);self.assertFalse(c['reference_labels_loaded'])
        self.assertTrue(all(not row['result']['delivery_approved'] for row in p['cases']))

    def test_both_consumers_resolve_v3_and_compare_all29_without_model(self):
        a=source.compare(source.predict(list(runtime.CASE_IDS)))
        b=core.compare(core.run_predictions())
        self.assertEqual(a['candidate_count'],29);self.assertEqual(len(b['cases']),29)
        self.assertEqual(a['reference_manifest_path'],runtime.GOLD_PATH)
        self.assertEqual(b['active_reference_path'],runtime.GOLD_PATH)
        self.assertEqual(sum(r['expected']=='UNRESOLVED' for r in a['cases']),8)
        self.assertEqual(a['evaluated_count'],0);self.assertIsNone(a['accuracy'])
        self.assertFalse(b['comparison_is_sp_accuracy'])

    def test_existing12_evaluation_behavior_and_forged_input_binding(self):
        r=source.compare(source.predict(['SP-005','SP-006','SP-007','SP-008']))
        self.assertEqual(r['evaluated_count'],0);self.assertEqual(len(r['excluded']),4)
        p=source.predict(['SP-006']);p['cases'][0]['input_sha256']='0'*64
        p.pop('record_sha256');source.legacy.seal(p)
        with self.assertRaises(ValueError):source.compare(p)
        p=core.run_predictions();p['cases'][0]['input_path']='evaluation/semantic_pilot/inputs/SP-002.json'
        with self.assertRaises(ValueError):core.compare(p)

    def test_completed_cited_unresolved_observation_without_core_approval(self):
        def reviewer(request):
            evidence=[dict(side=side,document_id=s['document_id'],snapshot_sha256=s['sha256'],
                start=0,end=len(s['content']),quote=s['content'])
                for side,key in [('source','source_snapshots'),('output','output_snapshots')]
                for s in request[key] if s['content']]
            return {'request_sha256':request['request_sha256'],'reviews':[
                {'check_id':c,'judgment':'unresolved','reason':'Synthetic protocol fixture only',
                 'reviewed_refs':request['snapshot_refs'],'evidence':evidence} for c in request['required_checks']]}
        p=source.predict(['SP-006'],reviewer=reviewer);r=source.compare(p)
        self.assertEqual(r['cases'][0]['three_way_observation'],'UNRESOLVED')
        self.assertEqual(r['evaluated_count'],0)
        self.assertFalse(p['cases'][0]['result']['delivery_approved'])
