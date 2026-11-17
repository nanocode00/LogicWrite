"""Offline tests for explicitly authorized recovery and six-request campaign."""
import importlib.util
import json
from pathlib import Path
import unittest
import argparse
import io
import tempfile
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('comparison_v2',HERE/'comparison_v2.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

class ComparisonV2Tests(unittest.TestCase):
    def fixture(self):
        old=HERE/'smoke-rotated-key-20261117/live/IR-003/B0'
        record=json.loads((old/'execution.json').read_text())
        response=json.loads((old/'response.json').read_text())
        state={'spent_usd':'0.0027089352','pending':False,'blocked':True,'smoke_success':False,
               'completed_targets':[],'pending_upper_usd':'0.00545376','pending_target':'IR-003/B0'}
        status={'usage':'0.002708935','limit':'0.25','limit_remaining':'0.247291065','limit_reset':None,'byok_usage':'0'}
        return state,record,response,status

    def test_recovery_preserves_cost_and_records_exact_before_state(self):
        state,record,response,status=self.fixture()
        before=json.loads(json.dumps(state))
        new,event=v.recover_state(state,record,response,status)
        self.assertFalse(new['blocked']);self.assertEqual(new['spent_usd'],before['spent_usd'])
        self.assertEqual(event['before'],before)
        self.assertEqual(state,before)
        self.assertIn('user_explicit',event['authorization'])

    def test_pending_timeout_unknown_cost_or_unrelated_state_cannot_recover(self):
        for change in [{'pending':True},{'spent_usd':'0.1'},{'pending_target':'IR-001/B0'},
                       {'blocked':False},{'extra_request':'unknown'}]:
            state,record,response,status=self.fixture();state.update(change)
            with self.assertRaises(v.base.Blocked): v.recover_state(state,record,response,status)
        for field,value in [('reason','timeout'),('http_status',500),('finish_reasons',['length'])]:
            state,record,response,status=self.fixture();record[field]=value
            with self.assertRaises(v.base.Blocked): v.recover_state(state,record,response,status)
        state,record,response,status=self.fixture();del response['usage']['cost']
        with self.assertRaises(v.base.Blocked): v.recover_state(state,record,response,status)

    def test_recovery_rejects_unreconciled_server_spend(self):
        state,record,response,status=self.fixture();status['usage']='0.02'
        with self.assertRaises(v.base.Blocked):v.recover_state(state,record,response,status)

    def test_payload_settings_equal_and_input_only(self):
        for cid in ['IR-001','IR-002','IR-003']:
            a,b=v.payload(cid,'B0'),v.payload(cid,'B1')
            self.assertEqual(a['messages'][1],b['messages'][1])
            self.assertEqual({k:x for k,x in a.items() if k!='messages'},
                             {k:x for k,x in b.items() if k!='messages'})
            self.assertTrue(a['reasoning']['enabled']);self.assertEqual(a['max_tokens'],12000)
            inp=v.base.export_input(v.base.GOLD,cid)
            self.assertEqual(json.loads(a['messages'][1]['content']),inp)

    def test_missing_truncated_readonly_modified_and_extra_doc_fail(self):
        inp=v.base.export_input(v.base.GOLD,'IR-003')
        src={d['document_id']:d['content'] for d in inp['documents']}
        good={'documents':[{'document_id':'meeting','content':src['meeting']}],
              'review_notes':'unchanged','unresolved_questions':['audience?'],'final_checks':'review'}
        self.assertTrue(v.output_check(json.dumps(good),inp)[1]['all_editable_documents_present'])
        for docs in [[],[{'document_id':'meeting','content':''}],
                     good['documents']+[{'document_id':'public','content':'new'}],
                     good['documents']+[{'document_id':'experiment','content':'changed'}]]:
            bad=dict(good,documents=docs)
            with self.assertRaises(v.base.Blocked):v.output_check(json.dumps(bad),inp)

    def test_max_six_and_no_duplicate_or_failed_retry(self):
        state={'campaigns':{v.PROTOCOL:{'attempts':[]}}}
        for target in v.TARGETS:
            v.reserve_attempt(state,target,'fixture')
        self.assertEqual(len(state['campaigns'][v.PROTOCOL]['attempts']),6)
        with self.assertRaises(v.base.Blocked):v.reserve_attempt(state,v.TARGETS[0],'newpath')

    def test_sequential_campaign_persists_six_attempts_and_never_retries_unknown_cost(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ledger_dir=root/'ledger';ledger_dir.mkdir()
            state,record,response,status=self.fixture()
            state,event=v.recover_state(state,record,response,status)
            v.base.dump(ledger_dir/'budget.json',state)
            spent=v.base.amount(state['spent_usd']);posts=[];bad_cost=False;stale=False
            def api(method,path,key,payload=None):
                nonlocal spent
                if path=='/key':
                    reported=v.base.amount('.0027089352') if stale and posts else spent
                    return {'data':{'limit':.25,'limit_remaining':str(v.base.KEY_LIMIT-reported),
                        'usage':str(reported),'limit_reset':None,'byok_usage':0}}
                if path.endswith('/endpoints'):
                    return {'data':{'id':v.base.MODEL,'endpoints':[{'tag':v.base.PROVIDER,'provider_name':'GMICloud',
                        'status':0,'context_length':163840,'max_completion_tokens':147456,
                        'supported_parameters':['max_tokens','temperature','reasoning'],
                        'pricing':{'prompt':'.0000002088','completion':'.0000003096'}}]}}
                posts.append(payload)
                inp=json.loads(payload['messages'][1]['content'])
                output={'documents':[{'document_id':d['document_id'],'content':d['content']}
                                     for d in inp['documents'] if d['access']!='read_only'],
                        'review_notes':'unchanged','unresolved_questions':[],'final_checks':'checked'}
                spent+=v.base.amount('.0001')
                usage={'cost':.0001,'prompt_tokens':10,'completion_tokens':20,
                       'is_byok':False,'completion_tokens_details':{'reasoning_tokens':10}}
                if bad_cost:del usage['cost']
                return {'_http_status':200,'model':v.base.MODEL,'provider':'GMICloud','usage':usage,
                        'choices':[{'finish_reason':'stop','message':{'content':json.dumps(output)}}]}
            def args(phase,name,confirm=False):
                return argparse.Namespace(phase=phase,execute=True,output=root/name,confirm_smoke_checked=confirm)
            with patch.object(v.base,'load_api_key',return_value=('fixture-only','environment')), \
                 patch.object(v.base,'verify_secret_protection',return_value={}),patch('sys.stdout',new_callable=io.StringIO):
                v.run(args('smoke','smoke'),api=api,ledger_dir=ledger_dir)
                with self.assertRaises(v.base.Blocked):v.run(args('remaining','not-confirmed'),api=api,ledger_dir=ledger_dir)
                v.run(args('remaining','remaining',True),api=api,ledger_dir=ledger_dir)
                self.assertEqual(len(posts),6)
                saved=json.loads((ledger_dir/'budget.json').read_text())
                self.assertEqual(len(saved['campaigns'][v.PROTOCOL]['attempts']),6)
                self.assertEqual(v.base.amount(saved['spent_usd']),spent)
                with self.assertRaises(v.base.Blocked):v.run(args('smoke','again'),api=api,ledger_dir=ledger_dir)
                self.assertEqual(len(posts),6)
                # Delayed server settlement is a campaign stop, never an automatic release.
                state,record,response,status=self.fixture();state,_=v.recover_state(state,record,response,status)
                v.base.dump(ledger_dir/'budget.json',state);spent=v.base.amount(state['spent_usd']);stale=True;posts=[]
                with self.assertRaises(v.base.Blocked):v.run(args('smoke','stale'),api=api,ledger_dir=ledger_dir)
                saved=json.loads((ledger_dir/'budget.json').read_text())
                self.assertFalse(saved['pending']);self.assertTrue(saved['blocked'])
                self.assertEqual(saved['block_reason'],'post_request_spend_unreconciled')
                self.assertEqual(v.base.amount(saved['spent_usd']),spent)
                self.assertEqual(len(posts),1)
                with self.assertRaises(v.base.Blocked):v.run(args('remaining','stale-next',True),api=api,ledger_dir=ledger_dir)
                self.assertEqual(len(posts),1)
                stale=False
                # Independent fake campaign: unknown cost stays pending and blocks future work.
                state,record,response,status=self.fixture();state,_=v.recover_state(state,record,response,status)
                v.base.dump(ledger_dir/'budget.json',state);spent=v.base.amount(state['spent_usd']);bad_cost=True
                with self.assertRaises(v.base.Blocked):v.run(args('smoke','unknown'),api=api,ledger_dir=ledger_dir)
                saved=json.loads((ledger_dir/'budget.json').read_text())
                self.assertTrue(saved['pending']);self.assertTrue(saved['blocked'])
                count=len(posts)
                with self.assertRaises(v.base.Blocked):v.run(args('smoke','unknown-retry'),api=api,ledger_dir=ledger_dir)
                self.assertEqual(len(posts),count)

if __name__=='__main__':unittest.main()
