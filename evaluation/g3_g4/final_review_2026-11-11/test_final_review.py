"""Validate actual authorized records and corrupted temporary copies, never invent approvals."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from validate import HERE, validate, digest, PREFIX


class FinalReviewTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)/'final';shutil.copytree(HERE,self.root,ignore=shutil.ignore_patterns('__pycache__'))
        self.manifest=self.read('development-gold.json')

    def read(self,name):return json.loads((self.root/name).read_text())
    def write(self,name,value):
        p=self.root/name;p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');return digest(p)
    def save_manifest(self):self.write('development-gold.json',self.manifest)
    def change_snapshot(self,cid,mutate):
        row=next(r for r in self.manifest['cases'] if r['case_id']==cid)
        name=row['snapshot_path'].removeprefix(PREFIX);record=self.read(name);mutate(record)
        row['snapshot_sha256']=self.write(name,record);self.save_manifest()
    def reject(self):
        with self.assertRaises(ValueError):validate(self.root)

    def test_valid_12_approved_11_active(self):
        result=validate(self.root)
        self.assertEqual(result['user_final_decisions'],12);self.assertEqual(result['active_development_gold'],11)
        self.assertEqual(result['preserved_files'],153)

    def test_sp009_approved_but_not_active(self):
        row=next(r for r in self.manifest['cases'] if r['case_id']=='SP-009')
        self.assertTrue(row['user_development_gold_approved']);self.assertFalse(row['development_gold_eligible'])
        self.assertEqual(row['review_level'],'user_initial_reviewed')
        self.assertNotIn('SP-009',self.manifest['active_case_ids'])

    def test_sp009_cannot_be_activated_by_index(self):
        row=next(r for r in self.manifest['cases'] if r['case_id']=='SP-009');row['development_gold_eligible']=True
        self.manifest['active_case_ids'].append('SP-009');self.manifest['workflow_eligible_count']=12;self.save_manifest();self.reject()

    def test_sp009_old_ai_cannot_be_retroactively_bound(self):
        other=self.read('final/SP-003.json')['events'][1]
        self.change_snapshot('SP-009',lambda r:r['events'].append(other));self.reject()

    def test_sp009_cannot_skip_to_final(self):
        event=self.read('final/SP-001.json')['events'][-1]
        self.change_snapshot('SP-009',lambda r:r['events'].append(event));self.reject()

    def test_final_snapshot_hash(self):
        path=self.root/'final/SP-001.json';path.write_bytes(path.read_bytes()+b' ');self.reject()

    def test_evidence_quote(self):
        self.change_snapshot('SP-007',lambda r:r['events'][-1]['payload']['evidence'][0].update(quote='invented'));self.reject()

    def test_event_prefix_preserved(self):
        self.change_snapshot('SP-003',lambda r:r['events'][0]['payload']['form'].update(rationale='changed history'));self.reject()

    def test_counterreview_cannot_be_removed(self):
        self.change_snapshot('SP-001',lambda r:r['events'].pop(1));self.reject()

    def test_ai_cannot_author_user_final(self):
        self.change_snapshot('SP-001',lambda r:r['events'][-1].update(actor_type='ai'));self.reject()

    def test_user_confirmation_required(self):
        self.change_snapshot('SP-001',lambda r:r['events'][-1]['payload'].update(human_confirmed=False));self.reject()

    def test_sp003_challenge_response_required(self):
        self.change_snapshot('SP-003',lambda r:r['events'][-1]['payload'].update(responses=[]));self.reject()

    def test_sp003_final_must_match_explicit_preserved_decision(self):
        self.change_snapshot('SP-003',lambda r:r['events'][-1]['payload'].update(judgment='UNRESOLVED',unresolved_issues=['context']));self.reject()

    def test_unresolved_is_reviewed_abstention_not_empty(self):
        self.change_snapshot('SP-011',lambda r:r['events'][-1]['payload'].update(unresolved_issues=[]));self.reject()

    def test_sp006_two_errors(self):
        approvals=self.read('user-approvals.json');approvals['cases'][5]['error_findings'].pop()
        self.manifest['user_approval_sha256']=self.write('user-approvals.json',approvals);self.save_manifest();self.reject()

    def test_inclusion_approval_required(self):
        approvals=self.read('user-approvals.json');approvals['cases'][8]['user_development_gold_approved']=False
        self.manifest['user_approval_sha256']=self.write('user-approvals.json',approvals);self.save_manifest();self.reject()

    def test_no_retroactive_blinding(self):
        approvals=self.read('user-approvals.json');approvals['cases'][0]['blinded_to_prior_judgments']=True
        self.manifest['user_approval_sha256']=self.write('user-approvals.json',approvals);self.save_manifest();self.reject()

    def test_independent_level_cannot_be_claimed(self):
        self.manifest['cases'][0]['independent_multi_human_complete']=True;self.save_manifest();self.reject()

    def test_holdout_cannot_be_claimed(self):
        self.manifest['dataset_role']='holdout';self.save_manifest();self.reject()

    def test_wrong_active_distribution(self):
        self.manifest['active_distribution']['UNRESOLVED']=4;self.save_manifest();self.reject()

    def test_input_version_binding(self):
        self.manifest['cases'][0]['input_sha256']='0'*64;self.save_manifest();self.reject()

    def test_final_events_cannot_be_backdated(self):
        self.change_snapshot('SP-001',lambda r:r['events'][-1].update(recorded_at='2026-11-10T00:00:00+00:00'));self.reject()

    def test_snapshot_path_cannot_escape(self):
        self.manifest['cases'][0]['snapshot_path']='../outside.json';self.save_manifest();self.reject()

    def test_extra_final_not_silently_active(self):
        shutil.copyfile(self.root/'final/SP-001.json',self.root/'final/SP-009.json');self.reject()

if __name__=='__main__':unittest.main()
