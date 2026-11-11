"""Corrupt temporary copies of the actual approval; never generate human decisions."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from validate import HERE,PREFIX,validate,sha

class ActivationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)/'v2'
        shutil.copytree(HERE,self.root,ignore=shutil.ignore_patterns('__pycache__'));self.m=self.read('development-gold.json')
    def read(self,name):return json.loads((self.root/name).read_text())
    def write(self,name,obj):
        p=self.root/name;p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');return sha(p)
    def save(self):self.write('development-gold.json',self.m)
    def reject(self):
        with self.assertRaises(ValueError):validate(self.root)
    def record_change(self,fn):
        r=next(r for r in self.m['cases'] if r['case_id']=='SP-009');name=r['snapshot_path'].removeprefix(PREFIX);rec=self.read(name);fn(rec);r['snapshot_sha256']=self.write(name,rec);self.save()
    def confirmation_change(self,fn):
        name='user-reconfirmation.json';c=self.read(name);fn(c);self.m['sp009_reconfirmation_sha256']=self.write(name,c);self.save()
    def test_12_active(self):self.assertEqual(validate(self.root)['workflow_eligible'],12)
    def test_no_inclusion(self):self.confirmation_change(lambda c:c.update(development_inclusion_approved=False));self.reject()
    def test_missing_actual_reply(self):self.confirmation_change(lambda c:c.update(user_quote=''));self.reject()
    def test_stale_confirmation_binding(self):self.confirmation_change(lambda c:c.update(counterreview_sha256='0'*64));self.reject()
    def test_old_11_rows_unchanged(self):self.m['cases'][0]['snapshot_sha256']='0'*64;self.save();self.reject()
    def test_no_historical_counterreview(self):
        row=next(r for r in self.m['cases'] if r['case_id']=='SP-009');row['source_counterreview_path']='evaluation/g3_g4/review_round_2026-11-11/ai-counterreview.raw.json';self.save();self.reject()
    def test_no_ai_as_user(self):self.record_change(lambda r:r['events'][-1].update(actor_type='ai'));self.reject()
    def test_abstention_reason_required(self):self.record_change(lambda r:r['events'][-1]['payload'].update(unresolved_issues=[]));self.reject()
    def test_prefix_not_rewritten(self):self.record_change(lambda r:r['events'][0]['payload']['form'].update(rationale='edited'));self.reject()
    def test_cannot_claim_preserved(self):self.record_change(lambda r:r['events'][-1]['payload'].update(judgment='PRESERVED'));self.reject()
    def test_balance_checked(self):self.m['active_distribution']['UNRESOLVED']=3;self.save();self.reject()
    def test_holdout_rejected(self):self.m['dataset_role']='holdout';self.save();self.reject()
    def test_missing_case(self):self.m['active_case_ids'].remove('SP-009');self.save();self.reject()
    def test_no_retroactive_blinding(self):self.confirmation_change(lambda c:c.update(blinded_to_prior_judgments=True));self.reject()

if __name__=='__main__':unittest.main()
