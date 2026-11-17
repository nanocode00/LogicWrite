"""Offline budget tests. Network calls are replaced with a deterministic fake."""
import argparse
from copy import deepcopy
from decimal import Decimal
import importlib.util
import json
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('router_pilot', HERE / 'run.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.calls = []
        paths=patch.object(p,'env_candidates',return_value=[])
        paths.start(); self.addCleanup(paths.stop)
        safety=patch.object(p,'verify_secret_protection',return_value={'history_scan_passed':True})
        safety.start(); self.addCleanup(safety.stop)
        quiet=patch("sys.stdout",new_callable=io.StringIO)
        quiet.start(); self.addCleanup(quiet.stop)
        self.key = {'data': {'limit': .25, 'limit_remaining': .25, 'usage': 0,
                            'limit_reset': None, 'byok_usage': 0}}
        self.endpoint = {'data': {'id': 'deepseek/deepseek-v3.2', 'endpoints': [{
            'tag': 'gmicloud/fp8', 'provider_name': 'GMICloud', 'status': 0,
            'context_length': 163840, 'max_completion_tokens': 147456,
            'supported_parameters': ['max_tokens', 'temperature', 'reasoning'],
            'pricing': {'prompt': '0.0000002088', 'completion': '0.0000003096'}}]}}
        self.response = {'model': 'deepseek/deepseek-v3.2', 'provider': 'GMICloud',
            'choices': [{'finish_reason': 'stop', 'message': {'content': 'candidate'}}],
            'usage': {'prompt_tokens': 200, 'completion_tokens': 300, 'cost': .001,
                      'completion_tokens_details': {'reasoning_tokens': 0}}}
        self.env = patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-secret'}, clear=True)
        self.env.start(); self.addCleanup(self.env.stop)

    def args(self, **changes):
        values = dict(output=self.root/'result', execute=True, case=None, arm=None,
                      smoke=True, confirm_smoke_reviewed=False)
        values.update(changes)
        return argparse.Namespace(**values)

    def api(self, method, path, key, payload=None):
        self.calls.append((method, path, deepcopy(payload)))
        if path == '/key': return deepcopy(self.key)
        if path.endswith('/endpoints'): return deepcopy(self.endpoint)
        return deepcopy(self.response)

    def run_live(self, **changes):
        return p.run(self.args(**changes), api=self.api, ledger_dir=self.root/'ledger')

    def test_offline_dry_run_never_calls_network_even_with_key(self):
        self.run_live(execute=False)
        self.assertEqual(self.calls, [])
        plan = json.loads((self.root/'result/plan.json').read_text())
        self.assertEqual(len(plan['targets']), 1)
        self.assertGreater(Decimal(plan['total_upper_usd']), 0)

    def test_smoke_one_post_and_records_real_usage_and_disabled_reasoning(self):
        self.run_live()
        posts = [x for x in self.calls if x[0] == 'POST']
        self.assertEqual(len(posts), 1)
        payload = posts[0][2]
        self.assertEqual(payload['reasoning'], {'enabled': False})
        self.assertFalse(payload['provider']['allow_fallbacks'])
        self.assertEqual(payload['provider']['only'], ['gmicloud/fp8'])
        record = json.loads((self.root/'result/IR-003/B0/execution.json').read_text())
        self.assertEqual(record['usage']['cost'], .001)
        self.assertEqual(record['reasoning_observed'], 'zero_reported_tokens')
        self.assertNotIn('test-secret', ''.join(x.read_text() for x in self.root.rglob('*.json')))

    def test_key_limit_unlimited_high_reset_or_missing_fails_before_post(self):
        for field, value in [('limit', None), ('limit', .26), ('limit_reset', 'daily'), ('usage', None)]:
            with self.subTest(field=field, value=value):
                self.key['data'][field] = value
                with self.assertRaises(p.Blocked): self.run_live(output=self.root/str(len(self.calls)))
                self.key['data'] = {'limit':.25,'limit_remaining':.25,'usage':0,'limit_reset':None,'byok_usage':0}
        self.assertFalse(any(x[0]=='POST' for x in self.calls))

    def test_budget_reserves_entire_request_bound(self):
        self.key['data']['usage'] = .199
        self.key['data']['limit_remaining'] = .051
        with self.assertRaises(p.Blocked): self.run_live()
        self.assertFalse(any(x[0]=='POST' for x in self.calls))

    def test_price_increase_or_unknown_fee_fails_closed(self):
        for pricing in [{'prompt':'NaN','completion':'.0000003'},
                        {'prompt':'.0000003','completion':'.0000003'},
                        {'prompt':'.0000002','completion':'.0000003','request':'.001'},
                        {'prompt':'.0000002','completion':'.0000003','future_fee':'unknown'}]:
            self.endpoint['data']['endpoints'][0]['pricing'] = pricing
            with self.assertRaises(p.Blocked): self.run_live(output=self.root/str(len(self.calls)))
        self.assertFalse(any(x[0]=='POST' for x in self.calls))

    def test_missing_usage_blocks_future_run_in_new_directory(self):
        del self.response['usage']['cost']
        with self.assertRaises(p.Blocked): self.run_live()
        count = len(self.calls)
        with self.assertRaises(p.Blocked): self.run_live(output=self.root/'next')
        self.assertEqual(len(self.calls), count)

    def test_timeout_remains_pending_and_never_retries(self):
        def timeout(method, path, key, payload=None):
            if method == 'POST':
                self.calls.append((method,path,payload)); raise TimeoutError('test-secret')
            return self.api(method,path,key,payload)
        with self.assertRaises(p.Blocked):
            p.run(self.args(), api=timeout, ledger_dir=self.root/'ledger')
        record=json.loads((self.root/'result/IR-003/B0/execution.json').read_text())
        self.assertEqual(record['state'], 'timeout')
        self.assertEqual(len([x for x in self.calls if x[0]=='POST']),1)
        self.assertNotIn('test-secret',json.dumps(record))
        with self.assertRaises(p.Blocked): self.run_live(output=self.root/'next')

    def test_truncation_accounts_cost_and_blocks_batch(self):
        self.response['choices'][0]['finish_reason'] = 'length'
        with self.assertRaises(p.Blocked): self.run_live()
        ledger=json.loads((self.root/'ledger/budget.json').read_text())
        self.assertEqual(Decimal(ledger['spent_usd']), Decimal('.001'))
        self.assertTrue(ledger['blocked'])
        record=json.loads((self.root/'result/IR-003/B0/execution.json').read_text())
        self.assertEqual(record['state'],'output_truncated')

    def test_non_smoke_requires_explicit_review_and_persisted_smoke(self):
        with self.assertRaises(p.Blocked): self.run_live(smoke=False)
        self.assertEqual(self.calls, [])

    def test_nonblocking_lock_prevents_parallel_runs(self):
        import fcntl
        directory=self.root/'ledger'; directory.mkdir()
        with (directory/'budget.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(p.Blocked): self.run_live()
        self.assertEqual(self.calls, [])

    def test_sequential_remainder_skips_smoke_and_keeps_global_spend(self):
        self.run_live()
        self.run_live(output=self.root/'rest', smoke=False, confirm_smoke_reviewed=True)
        posts=[x for x in self.calls if x[0]=='POST']
        self.assertEqual(len(posts),6)
        self.assertEqual(len({json.dumps(x[2]['messages']) for x in posts}),6)
        ledger=json.loads((self.root/'ledger/budget.json').read_text())
        self.assertEqual(Decimal(ledger['spent_usd']),Decimal('.006'))
        self.assertEqual(len(ledger['completed_targets']),6)

    def test_key_query_failure_sends_no_post(self):
        def failed(*a,**kw): raise OSError('test-secret')
        with self.assertRaises(p.Blocked):
            p.run(self.args(),api=failed,ledger_dir=self.root/'ledger')
        self.assertEqual(self.calls,[])

    def test_api_error_and_missing_cost_stop_remaining_requests(self):
        self.run_live()
        self.response={'error':{'code':402,'message':'test-secret'}}
        with self.assertRaises(p.Blocked):
            self.run_live(output=self.root/'rest',smoke=False,confirm_smoke_reviewed=True)
        self.assertEqual(len([x for x in self.calls if x[0]=='POST']),2)
        record=json.loads((self.root/'rest/IR-001/B0/execution.json').read_text())
        self.assertEqual(record['state'],'api_error')
        self.assertNotIn('test-secret', ''.join(x.read_text() for x in self.root.rglob('*.json')))

    def test_unknown_reasoning_does_not_claim_disabled(self):
        del self.response['usage']['completion_tokens_details']
        self.run_live()
        record=json.loads((self.root/'result/IR-003/B0/execution.json').read_text())
        self.assertEqual(record['reasoning_observed'],'unknown_not_reported')

    def test_nonzero_reasoning_stops_after_accounting(self):
        self.response['usage']['completion_tokens_details']['reasoning_tokens']=42
        with self.assertRaises(p.Blocked): self.run_live()
        ledger=json.loads((self.root/'ledger/budget.json').read_text())
        self.assertEqual(Decimal(ledger['spent_usd']),Decimal('.001'))
        self.assertTrue(ledger['blocked'])

    def test_missing_credentials_cannot_even_query_key(self):
        with patch.dict('os.environ',{},clear=True):
            with self.assertRaises(p.Blocked): self.run_live()
        self.assertEqual(self.calls,[])

    def test_cumulative_local_budget_survives_new_output_directory(self):
        self.run_live()
        path=self.root/'ledger/budget.json'
        state=json.loads(path.read_text()); state['spent_usd']='0.199'
        path.write_text(json.dumps(state))
        with self.assertRaises(p.Blocked):
            self.run_live(output=self.root/'next',smoke=False,confirm_smoke_reviewed=True)
        self.assertEqual(len([x for x in self.calls if x[0]=='POST']),1)

    def test_response_redacts_accidentally_echoed_credentials(self):
        self.response['choices'][0]['message']['content']='test-secret'
        self.run_live()
        for path in self.root.rglob('*.json'):
            self.assertNotIn('test-secret',path.read_text())

    def test_nonzero_reasoning_is_recorded_and_stops(self):
        self.response['usage']['completion_tokens_details']['reasoning_tokens']=2
        with self.assertRaises(p.Blocked): self.run_live()
        record=json.loads((self.root/'result/IR-003/B0/execution.json').read_text())
        self.assertEqual(record['reasoning_observed'],'nonzero_reported_tokens')

    def test_both_arms_share_all_generation_settings(self):
        self.run_live()
        self.run_live(output=self.root/'rest',smoke=False,confirm_smoke_reviewed=True)
        settings=[{k:v for k,v in x[2].items() if k!='messages'}
                  for x in self.calls if x[0]=='POST']
        self.assertTrue(all(s==settings[0] for s in settings))
        cfg=json.loads((HERE/'config.json').read_text())
        self.assertEqual(cfg['model'],p.MODEL)
        self.assertEqual(cfg['max_output_tokens'],p.MAX_TOKENS)
        self.assertEqual(Decimal(cfg['runner_cumulative_limit_usd']),p.BUDGET)

    def test_invalid_smoke_cannot_modify_existing_output(self):
        import subprocess,sys
        directory=self.root/'existing'; directory.mkdir()
        sentinel=directory/'blocked.json'; sentinel.write_text('preserve')
        result=subprocess.run([sys.executable,str(HERE/'run.py'),'--smoke','--case','IR-001',
                              '--output',str(directory)],capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(sentinel.read_text(),'preserve')

if __name__ == '__main__': unittest.main()
