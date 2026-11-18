import argparse
import tempfile
from unittest.mock import patch
import io
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import comparison_qwen as q

class QwenCampaignTests(unittest.TestCase):
    def state(self):
        return json.loads((HERE/'settlement-followup-20261117/ledger-final.json').read_text())
    def status(self,state):
        return {'usage':state['spent_usd'],'limit':'0.25','limit_remaining':str(q.base.KEY_LIMIT-q.base.amount(state['spent_usd']))}
    def test_activation_preserves_block_and_old_costs(self):
        state=self.state();before=copy.deepcopy(state)
        new=q.activate(state,self.status(state))
        self.assertEqual(state,before)
        self.assertTrue(new['blocked'])
        self.assertEqual(new['campaigns'][q.v.PROTOCOL],before['campaigns'][q.v.PROTOCOL])
        self.assertEqual(new['spent_usd'],before['spent_usd'])
        q.validate_active(new)
    def test_other_failures_pending_unreconciled_forbidden(self):
        for field,value in [('pending',True),('block_reason','timeout'),('spent_usd','0.02')]:
            with self.subTest(field=field):
                s=self.state();s[field]=value
                with self.assertRaises(q.base.Blocked):q.activate(s,self.status(s))
        s=self.state();status=self.status(s);status['usage']='0.014'
        with self.assertRaises(q.base.Blocked):q.activate(s,status)
    def test_campaign_duplicate_order_cap_and_stop(self):
        s=q.activate(self.state(),self.status(self.state()))
        q.reserve(s,'Probe-A','fake')
        with self.assertRaises(q.base.Blocked):q.reserve(s,'Probe-A','fake')
        with self.assertRaises(q.base.Blocked):q.reserve(s,'IR-001/B0','fake')
        s['campaigns'][q.PROTOCOL]['blocked']=True
        with self.assertRaises(q.base.Blocked):q.validate_active(s)
    def test_ninth_request_and_old_runner_bypass_forbidden(self):
        state=q.activate(self.state(),self.status(self.state()))
        self.assertTrue(state['blocked'])  # Both legacy runners reject this global flag.
        for target in q.TARGETS:
            attempt=q.reserve(state,target,'fake')
            q.account(state,attempt,{'cost':0})
            attempt['status']='response_complete'
        with self.assertRaises(q.base.Blocked):q.reserve(state,'Probe-A','fake')

    def test_payload_and_endpoint_pin(self):
        r=q.payload('IR-001/B0')
        self.assertNotIn('reasoning',r)
        self.assertEqual(r['provider']['only'],['deepinfra/fp8'])
        self.assertFalse(r['provider']['allow_fallbacks'])
        self.assertEqual(r['response_format'],{'type':'json_object'})
        fixture=json.loads((HERE/'token-limit-investigation-20261117/public-catalog-snapshot.json').read_text())
        raw=next(x for x in fixture['endpoints'] if x['data']['id']==q.MODEL)
        q.endpoint_status(raw,100,12000)
        raw=copy.deepcopy(raw);raw['data']['endpoints']=[e for e in raw['data']['endpoints'] if e['tag']!=q.PROVIDER]
        with self.assertRaises(q.base.Blocked):q.endpoint_status(raw,100,12000)
    def test_paid_cost_saved_even_when_tokens_invalid(self):
        s=q.activate(self.state(),self.status(self.state()));a=q.reserve(s,'Probe-A','fake')
        q.account(s,a,{'cost':.0001})
        self.assertEqual(s['spent_usd'],'0.0135719416')
        self.assertFalse(s['pending'])
        self.assertEqual(s['campaigns'][q.PROTOCOL]['spent_usd'],'0.0001')
    def test_token_limit_and_double_count(self):
        q.check_usage({'prompt_tokens':20,'completion_tokens':64,'completion_tokens_details':{'reasoning_tokens':0}},100,64)
        with self.assertRaises(q.base.Blocked):q.check_usage({'prompt_tokens':20,'completion_tokens':65},100,64)
        with self.assertRaises(q.base.Blocked):q.check_usage({'prompt_tokens':20,'completion_tokens':10,'completion_tokens_details':{'reasoning_tokens':2}},100,64)
    def test_campaign_budget_independent_of_global(self):
        s=q.activate(self.state(),self.status(self.state()))
        s['campaigns'][q.PROTOCOL]['spent_usd']='0.059'
        with self.assertRaises(q.base.Blocked):q.check_budget(s,self.status(s),q.Decimal('.002'))

    def test_fake_live_stops_and_preserves_cost_on_oversize(self):
        self.fake_request({'prompt_tokens':10,'completion_tokens':65,'cost':.0001,'is_byok':False},'token_accounting_or_limit_violation',False)
    def test_fake_live_missing_cost_keeps_pending(self):
        self.fake_request({'prompt_tokens':10,'completion_tokens':64,'is_byok':False},'missing_or_invalid_amount',True)
    def fake_request(self,usage,reason,pending):
        fixture=json.loads((HERE/'token-limit-investigation-20261117/public-catalog-snapshot.json').read_text())
        endpoint=next(x for x in fixture['endpoints'] if x['data']['id']==q.MODEL)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ledger=root/'ledger';ledger.mkdir()
            state=q.activate(self.state(),self.status(self.state()));q.base.dump(ledger/'budget.json',state)
            calls=[]
            def api(method,path,key,payload=None):
                calls.append(method)
                if path=='/key':return {'data':dict(self.status(state),limit_reset=None,byok_usage=0)}
                if path.endswith('/endpoints'):return copy.deepcopy(endpoint)
                return {'_http_status':200,'model':q.MODEL,'provider':'DeepInfra','usage':usage,
                        'choices':[{'finish_reason':'length','message':{'content':'1 2 3'}}]}
            args=argparse.Namespace(output=root/'result',target='Probe-A',phase='request',execute=True)
            with patch.object(q.base,'load_api_key',return_value=('invented-fixture','environment')), patch.object(q.base,'verify_secret_protection',return_value={}),patch('sys.stdout',new_callable=io.StringIO):
                with self.assertRaisesRegex(q.base.Blocked,reason):q.run(args,api=api,ledger_dir=ledger)
                saved=json.loads((ledger/'budget.json').read_text())
                self.assertEqual(saved['pending'],pending)
                self.assertTrue(saved['campaigns'][q.PROTOCOL]['blocked'])
                self.assertEqual(calls.count('POST'),1)
                args.output=root/'second'
                with self.assertRaises(q.base.Blocked):q.run(args,api=api,ledger_dir=ledger)
                self.assertEqual(calls.count('POST'),1)

if __name__=='__main__':unittest.main()
