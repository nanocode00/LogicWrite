"""Read-only evidence replay and isolated fake HTTP; never calls a live model."""
import argparse
import copy
from decimal import Decimal
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('investigated_v2',HERE/'comparison_v2.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
EVIDENCE=HERE/'settlement-followup-20261117'

class TokenLimitInvestigationTests(unittest.TestCase):
    def response(self):return json.loads((EVIDENCE/'remaining/IR-001/B1/response.json').read_text())

    def test_exact_record_and_native_metadata_agree_without_double_count(self):
        request=json.loads((EVIDENCE/'remaining/IR-001/B1/request.json').read_text())
        result=self.response();usage=result['usage']
        metadata=json.loads((HERE/'token-limit-investigation-20261117/existing-generation-metadata.json').read_text())['data']
        self.assertEqual(request['max_tokens'],12000)
        self.assertEqual(usage['completion_tokens'],16025)
        self.assertEqual(usage['completion_tokens_details']['reasoning_tokens'],14280)
        self.assertEqual(usage['completion_tokens']-usage['completion_tokens_details']['reasoning_tokens'],1745)
        self.assertEqual(result['choices'][0]['finish_reason'],'stop')
        self.assertEqual(metadata['native_tokens_completion'],usage['completion_tokens'])
        self.assertEqual(metadata['native_tokens_reasoning'],14280)
        self.assertEqual(metadata['provider_name'],'GMICloud')
        self.assertGreater(usage['completion_tokens'],request['max_tokens'])

    def test_native_token_billing_reconciles_and_reasoning_is_not_added_twice(self):
        usage=self.response()['usage']
        computed=Decimal(2262)*Decimal('.0000002088')+Decimal(16025)*Decimal('.0000003096')
        self.assertEqual(computed,Decimal('.0054336456'))
        self.assertEqual(v.base.amount(usage['cost']),computed)
        self.assertNotEqual(computed,Decimal(2262)*Decimal('.0000002088')+Decimal(16025+14280)*Decimal('.0000003096'))

    def test_replayed_oversize_usage_is_accounted_before_stop_no_retry(self):
        # Replay the observed oversized response as fake HTTP, not as a new model result.
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ledger=root/'ledger';ledger.mkdir()
            state={'spent_usd':'0','pending':False,'blocked':False,
                   'campaigns':{v.PROTOCOL:{'attempts':[],'smoke_checked':False}}}
            v.base.dump(ledger/'budget.json',state)
            catalog=json.loads((HERE/'token-limit-investigation-20261117/public-catalog-snapshot.json').read_text())
            data=next(x['data'] for x in catalog['endpoints'] if x.get('data',{}).get('id')==v.base.MODEL)
            def fake(method,path,key,payload=None):
                if path=='/key':return {'data':{'limit':.25,'limit_remaining':.25,'usage':0,'limit_reset':None,'byok_usage':0}}
                if path.endswith('/endpoints'):return {'data':copy.deepcopy(data)}
                result=self.response();result['_http_status']=200;return result
            api=Mock(side_effect=fake)
            args=argparse.Namespace(phase='smoke',execute=True,output=root/'first',confirm_smoke_checked=False)
            with patch.object(v.base,'load_api_key',return_value=('invented-fixture','environment')), \
                 patch.object(v.base,'verify_secret_protection',return_value={}),patch('sys.stdout',new_callable=io.StringIO):
                with self.assertRaises(v.base.Blocked):v.run(args,api=api,ledger_dir=ledger)
                saved=json.loads((ledger/'budget.json').read_text())
                self.assertEqual(Decimal(saved['spent_usd']),Decimal('.0054336456'))
                self.assertFalse(saved['pending']);self.assertTrue(saved['blocked'])
                self.assertEqual(saved['block_reason'],'cost_or_token_bound_exceeded')
                self.assertEqual(len(saved['campaigns'][v.PROTOCOL]['attempts']),1)
                calls=len(api.call_args_list)
                args.output=root/'second'
                with self.assertRaises(v.base.Blocked):v.run(args,api=api,ledger_dir=ledger)
                self.assertEqual(len(api.call_args_list),calls)
                self.assertEqual(sum(c.args[0]=='POST' for c in api.call_args_list),1)

    def test_actual_block_cannot_be_released_by_reasoning_or_settlement_recovery(self):
        state=json.loads((EVIDENCE/'ledger-final.json').read_text())
        before=copy.deepcopy(state)
        record=json.loads((EVIDENCE/'remaining/IR-001/B1/execution.json').read_text())
        status=json.loads((EVIDENCE/'key-status-final.json').read_text())['status']
        with self.assertRaises(v.base.Blocked):v.release_settlement_block(state,record,self.response(),status)
        with self.assertRaises(v.base.Blocked):v.recover_state(state,record,self.response(),status)
        self.assertEqual(state,before)
        with self.assertRaises(v.base.Blocked):v.reserve_attempt(state,'IR-001/B1','another-directory')
        self.assertEqual(state,before)

    def test_model_provider_and_fallback_are_fixed_in_current_runner(self):
        request=v.payload('IR-002','B0')
        self.assertEqual(request['model'],'deepseek/deepseek-v3.2')
        self.assertEqual(request['provider']['only'],['gmicloud/fp8'])
        self.assertFalse(request['provider']['allow_fallbacks'])
        self.assertTrue(request['provider']['require_parameters'])
        catalog=json.loads((HERE/'token-limit-investigation-20261117/public-catalog-snapshot.json').read_text())
        data=copy.deepcopy(next(x['data'] for x in catalog['endpoints'] if x.get('data',{}).get('id')==v.base.MODEL))
        data['id']='different/model'
        with self.assertRaises(v.base.Blocked):v.base.endpoint_status({'data':data},1000)
        data['id']=v.base.MODEL;data['endpoints']=[x for x in data['endpoints'] if x['tag']!='gmicloud/fp8']
        with self.assertRaises(v.base.Blocked):v.base.endpoint_status({'data':data},1000)

if __name__=='__main__':unittest.main()
