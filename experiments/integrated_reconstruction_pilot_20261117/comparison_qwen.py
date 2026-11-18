#!/usr/bin/env python3
"""Independent Qwen campaign. No paid calls without --execute; one target per invocation."""
import argparse
import copy
from decimal import Decimal
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parent))
import comparison_v2 as v
import run as base

PROTOCOL='integrated-qwen-instruct-20261117-v1'
MODEL='qwen/qwen3-235b-a22b-2507'
PROVIDER='deepinfra/fp8'
PROMPT_PRICE=Decimal('.00000009')
OUTPUT_PRICE=Decimal('.00000055')
CAMPAIGN_LIMIT=Decimal('.06')
TARGETS=['Probe-A','Probe-B']+[f'IR-00{i}/{arm}' for i in (1,2,3) for arm in ('B0','B1')]
BASELINE=base.HERE/'settlement-followup-20261117/ledger-final.json'


def payload(target):
    if target=='Probe-A':
        messages=[{'role':'user','content':'Write an English counting list from 1 through 1000, one number per line. Continue until the list is complete.'}]
        maximum=64
    elif target=='Probe-B':
        messages=[{'role':'user','content':'Return exactly one JSON object with documents containing one document_id "demo" and content "# Demo\\n\\nReady.\\n". No other prose.'}]
        maximum=256
    else:
        cid,arm=target.split('/')
        messages=base.messages(base.export_input(base.GOLD,cid),arm)
        messages[0]['content']+=v.DELIVERY
        maximum=12000
    r={'model':MODEL,'messages':messages,'max_tokens':maximum,'temperature':0,
       'usage':{'include':True},'provider':{'only':[PROVIDER],'allow_fallbacks':False,
       'require_parameters':True,'max_price':{'prompt':.09,'completion':.55,'request':0}}}
    if target!='Probe-A':r['response_format']={'type':'json_object'}
    return r


def estimate(request):
    n=len(json.dumps(request['messages'],ensure_ascii=False).encode())+4096
    return {'input_tokens_upper_estimate':n,'max_output_tokens':request['max_tokens'],
            'upper_usd':str(n*PROMPT_PRICE+request['max_tokens']*OUTPUT_PRICE),
            'method':'UTF-8 bytes plus 4096 template allowance; planning estimate, not tokenizer proof'}


def endpoint_status(raw,inputs,outputs):
    data=raw['data']
    if data.get('id')!=MODEL:raise base.Blocked('model_catalog_mismatch')
    matches=[e for e in data['endpoints'] if e.get('tag')==PROVIDER]
    if len(matches)!=1:raise base.Blocked('pinned_endpoint_unavailable')
    e=matches[0]
    if (e.get('model_id')!=MODEL or e.get('provider_name')!='DeepInfra' or e.get('quantization')!='fp8'
        or e.get('service_tier') is not None or e.get('status')!=0):raise base.Blocked('endpoint_identity_or_availability')
    if not {'max_tokens','temperature','response_format'}.issubset(e.get('supported_parameters',[])):
        raise base.Blocked('required_parameters_unsupported')
    if e.get('context_length',0)<inputs+outputs or (e.get('max_completion_tokens') or 0)<outputs:
        raise base.Blocked('endpoint_token_capacity')
    for name,value in e['pricing'].items():
        price=base.amount(value)
        ceiling={'prompt':PROMPT_PRICE,'completion':OUTPUT_PRICE}.get(name)
        if ceiling is not None:
            if price>ceiling:raise base.Blocked('price_exceeds_approved_ceiling')
        elif name not in ('discount','input_cache_read') and price!=0:raise base.Blocked('additional_price_not_approved')
    for field in ('prompt','completion'):base.amount(e['pricing'].get(field))
    return {'checked_at':v.now(),'url':base.API+'/models/'+MODEL+'/endpoints','endpoint':e}


def history_total(state):
    costs=[base.amount(x['cost_usd']) for x in state.get('legacy_requests',[])]
    for campaign in state.get('campaigns',{}).values():
        for a in campaign['attempts']:
            if a.get('status') not in ('response_complete','failed') or 'cost_usd' not in a:
                raise base.Blocked('unsettled_request_history')
            costs.append(base.amount(a['cost_usd']))
    return sum(costs,Decimal(0))


def activate(state,status):
    baseline=json.loads(BASELINE.read_text())
    if state!=baseline or state.get('pending') is not False or state.get('block_reason')!='cost_or_token_bound_exceeded':
        raise base.Blocked('activation_only_exact_accounted_legacy_token_failure')
    if history_total(state)!=base.amount(state['spent_usd']):raise base.Blocked('history_cost_mismatch')
    if abs(base.amount(status['usage'])-base.amount(state['spent_usd']))>Decimal('.000001'):
        raise base.Blocked('activation_requires_full_server_reconciliation')
    new=copy.deepcopy(state)
    new['active_campaign']=PROTOCOL
    new['campaigns'][PROTOCOL]={'attempts':[],'spent_usd':'0','blocked':False,
                              'limit_usd':str(CAMPAIGN_LIMIT),'max_requests':8}
    new['campaign_activation_events']=[{'at':v.now(),'authorization':'user_explicit_qwen_2_probes_6_evaluations_2026-11-17',
        'legacy_state_sha256':base.digest(json.dumps(state,sort_keys=True).encode()),
        'legacy_block_preserved':True,'model':MODEL,'provider':PROVIDER,'key_status':status,
        'reason':'new independent non-thinking campaign; legacy failure is not released or reclassified'}]
    return new


def validate_active(state):
    baseline=json.loads(BASELINE.read_text())
    if state.get('active_campaign')!=PROTOCOL or state.get('pending') or not state.get('blocked'):
        raise base.Blocked('campaign_not_active_or_pending')
    if state.get('block_reason')!=baseline['block_reason']:raise base.Blocked('legacy_block_changed')
    if state['campaigns'].get(v.PROTOCOL)!=baseline['campaigns'][v.PROTOCOL] or state.get('legacy_requests')!=baseline['legacy_requests']:
        raise base.Blocked('legacy_history_changed')
    c=state['campaigns'][PROTOCOL]
    if c.get('blocked') or c.get('limit_usd')!=str(CAMPAIGN_LIMIT) or c.get('max_requests')!=8:
        raise base.Blocked('campaign_stopped_or_limits_changed')
    if history_total(state)!=base.amount(state['spent_usd']):raise base.Blocked('history_cost_mismatch')
    if sum((base.amount(a['cost_usd']) for a in c['attempts']),Decimal(0))!=base.amount(c['spent_usd']):
        raise base.Blocked('campaign_cost_mismatch')


def check_budget(state,status,upper):
    if (base.amount(state['campaigns'][PROTOCOL]['spent_usd'])+upper>CAMPAIGN_LIMIT or
        max(base.amount(status['usage']),base.amount(state['spent_usd']))+upper>base.BUDGET or
        upper>base.amount(status['limit_remaining'])):raise base.Blocked('request_upper_exceeds_budget')


def reserve(state,target,path):
    validate_active(state)
    attempts=state['campaigns'][PROTOCOL]['attempts']
    if len(attempts)>=8 or target!=TARGETS[len(attempts)] or any(a['status']!='response_complete' for a in attempts):
        raise base.Blocked('duplicate_out_of_order_or_failed_request')
    a={'target':target,'status':'reserved','evidence_path':str(path),'at':v.now()}
    attempts.append(a);state['pending']=True
    return a


def account(state,attempt,usage):
    cost=base.amount(usage.get('cost'))
    state['spent_usd']=str(base.amount(state['spent_usd'])+cost)
    c=state['campaigns'][PROTOCOL];c['spent_usd']=str(base.amount(c['spent_usd'])+cost)
    attempt.update(cost_usd=str(cost),status='accounted');state['pending']=False
    return cost


def check_usage(usage,inputs,outputs):
    for f,cap in [('prompt_tokens',inputs),('completion_tokens',outputs)]:
        if type(usage.get(f)) is not int or not 0<=usage[f]<=cap:raise base.Blocked('token_accounting_or_limit_violation')
    reason=usage.get('completion_tokens_details',{}).get('reasoning_tokens',0)
    if type(reason) is not int or reason!=0:raise base.Blocked('unexpected_reasoning_for_nonthinking_model')
    return {'reasoning_tokens':reason,'reasoning_counter_present':'reasoning_tokens' in usage.get('completion_tokens_details',{}),
            'non_reasoning_completion_tokens':usage['completion_tokens']}


def common_ledger():
    common=subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-common-dir'],cwd=base.REPO,text=True).strip()
    return Path(common)/'logicwrite-openrouter-pilot'


def run(args,*,api=base.api_json,ledger_dir=None):
    args.output.mkdir(parents=True,exist_ok=False)
    target=args.target
    plan={'protocol':PROTOCOL,'phase':args.phase,'execute':args.execute,'model':MODEL,'provider':PROVIDER,
          'temperature':0,'timeout_seconds':600,'max_requests':8,'campaign_limit_usd':'.06',
          'key_limit_usd':'.25','global_limit_usd':'.20','runner_sha256':base.digest(Path(__file__).read_bytes()),
          'base_runner_sha256':base.digest((base.HERE/'run.py').read_bytes()),
          'shared_runner_sha256':base.digest((base.HERE/'comparison_v2.py').read_bytes()),
          'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=base.REPO,text=True).strip()}
    if target:
        req=payload(target);est=estimate(req)
        plan.update(target=target,estimate=est)
        base.dump(args.output/'request.json',req);base.dump(args.output/'input.json',req['messages'])
    else:plan['all_requests']=[{'target':t,**estimate(payload(t))} for t in TARGETS]
    base.dump(args.output/'plan.json',plan);print(json.dumps(plan,indent=2),flush=True)
    if not args.execute:return
    key,source=base.load_api_key()
    base.dump(args.output/'credential-safety.json',base.verify_secret_protection(key,source))
    with v.ledger(ledger_dir or common_ledger()) as (path,state):
        if args.phase=='activate':
            status=base.key_status(api('GET','/key',key))
            endpoint=endpoint_status(api('GET','/models/'+MODEL+'/endpoints',key),12000,12000)
            new=activate(state,status)
            base.dump(args.output/'ledger-before.json',state)
            base.dump(args.output/'activation.json',{'event':new['campaign_activation_events'][-1],'endpoint':endpoint})
            base.save_ledger(path,new);base.dump(args.output/'ledger-after.json',new)
            return
        if args.phase!='request' or target not in TARGETS:raise base.Blocked('explicit_single_target_required')
        validate_active(state)
        attempt=None
        record={'protocol':PROTOCOL,'target':target,'state':'preflight','calls':0,'D':'unobserved',
                'human_final_judgment':None,'input_sha256':base.digest((args.output/'input.json').read_bytes())}
        try:
            status=base.key_status(api('GET','/key',key))
            endpoint=endpoint_status(api('GET','/models/'+MODEL+'/endpoints',key),est['input_tokens_upper_estimate'],req['max_tokens'])
            record.update(key_status=status,endpoint=endpoint)
            record['settlement_before']=v.settlement_status(status,state['spent_usd'],state.get('last_server_usage_usd','0'))
            upper=base.amount(est['upper_usd']);check_budget(state,status,upper)
            attempt=reserve(state,target,args.output.resolve())
            state['pending_target']=target;state['pending_upper_usd']=str(upper)
            state['last_server_usage_usd']=status['usage'];base.save_ledger(path,state)
            record.update(state='request_started',calls=1);base.dump(args.output/'execution.json',record)
            start=time.monotonic()
            try:result=api('POST','/chat/completions',key,req)
            finally:record['seconds']=time.monotonic()-start
            record['http_status']=result.pop('_http_status',None)
            base.dump(args.output/'response.json',base.sanitized(result,key))
            usage=result.get('usage',{});record.update(usage=usage,model_returned=result.get('model'),provider_returned=result.get('provider'))
            # Charge known cost even if token/identity/output verification fails afterwards.
            cost=account(state,attempt,usage);base.save_ledger(path,state)
            record.update(check_usage(usage,est['input_tokens_upper_estimate'],req['max_tokens']))
            if record['http_status']!=200 or result.get('error'):raise base.Blocked('api_error')
            if result.get('model')!=MODEL or result.get('provider')!='DeepInfra':raise base.Blocked('model_provider_mismatch')
            if usage.get('is_byok') is not False:raise base.Blocked('BYOK_or_unknown_billing')
            if cost>upper or base.amount(state['campaigns'][PROTOCOL]['spent_usd'])>CAMPAIGN_LIMIT or base.amount(state['spent_usd'])>base.BUDGET:
                raise base.Blocked('cost_bound_exceeded')
            choices=result.get('choices',[]);reasons=[x.get('finish_reason') for x in choices];record['finish_reasons']=reasons
            allowed=['stop','length'] if target=='Probe-A' else ['stop']
            if len(reasons)!=1 or reasons[0] not in allowed:raise base.Blocked('output_truncated_or_incomplete')
            text=choices[0].get('message',{}).get('content')
            if not isinstance(text,str) or not text.strip():raise base.Blocked('empty_response')
            if target=='Probe-A':checks={'output_tokens_within_64':True,'finish_reason':reasons[0],
                                       'long_output_enforcement_proven':False}
            elif target=='Probe-B':
                data=json.loads(text)
                if data!={'documents':[{'document_id':'demo','content':'# Demo\n\nReady.\n'}]}:raise base.Blocked('probe_json_contract')
                checks={'json_object_valid':True,'probe_document_contract':True}
            else:
                # JSON-mode output must be raw JSON, not a Markdown fence.
                json.loads(text)
                data,checks=v.output_check(text,base.export_input(base.GOLD,target.split('/')[0]))
                base.dump(args.output/'candidate.json',data)
            base.dump(args.output/'automatic-checks.json',checks)
            after=base.key_status(api('GET','/key',key));record['key_status_after']=after
            record['settlement_after']=v.settlement_status(after,state['spent_usd'],state.get('last_server_usage_usd','0'))
            state['last_server_usage_usd']=after['usage']
            attempt.update(status='response_complete',settlement=record['settlement_after'])
            record['state']='response_complete';base.save_ledger(path,state)
        except Exception as exc:
            reason=str(exc) if isinstance(exc,base.Blocked) else type(exc).__name__
            if isinstance(exc,urllib.error.HTTPError):record['http_status']=exc.code;reason='HTTP_error'
            if isinstance(exc,(TimeoutError,socket.timeout)):reason='timeout'
            record.update(state='failed',reason=reason)
            state['campaigns'][PROTOCOL].update(blocked=True,block_reason=reason)
            if attempt is not None:attempt.update(status='failed',reason=reason)
            base.save_ledger(path,state)
            base.dump(args.output/'execution.json',base.sanitized(record,key))
            base.dump(args.output/'ledger-after.json',state)
            raise base.Blocked(reason) from None
        base.dump(args.output/'execution.json',base.sanitized(record,key))
        base.dump(args.output/'ledger-after.json',state)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',choices=['prepare','activate','request'],default='prepare')
    p.add_argument('--target',choices=TARGETS)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    try:run(args)
    except base.Blocked as e:raise SystemExit(str(e)) from None
    except FileExistsError:raise SystemExit('output_directory_already_exists') from None

if __name__=='__main__':main()
