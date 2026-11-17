#!/usr/bin/env python3
"""Reasoning-allowed, input-only campaign. Offline unless --execute is explicit."""
import argparse
import copy
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.error

sys.path.insert(0,str(Path(__file__).resolve().parent))
import run as base

PROTOCOL='integrated-reasoning-allowed-20261117-v1'
TARGETS=['IR-003/B0','IR-001/B0','IR-001/B1','IR-002/B0','IR-002/B1','IR-003/B1']
OLD=base.HERE/'smoke-rotated-key-20261117/live/IR-003/B0'
PIN='b370fa0f48eedf24a6ed352d443e50a376b5e068'
# Generic delivery format only; no evaluation-specific facts, criteria or action labels.
DELIVERY=('\n응답은 JSON 객체 하나로 제출하세요. documents 배열에 edit 또는 format_only 문서 각각의 '
          'document_id와 전체 content를 넣으세요. 변경하지 않은 편집 가능 문서도 전체 본문을 반환하세요. '
          '변경 근거는 review_notes, 확인 질문과 보류 사항은 unresolved_questions, 최종 자체 검증은 '
          'final_checks에 문서 본문과 분리해 기록하세요. 읽기 전용 문서는 수정하지 마세요. '
          '편집 전 사고과정은 요구하지 않습니다.')


def now():return datetime.now(timezone.utc).isoformat()


def payload(cid,arm):
    messages=base.messages(base.export_input(base.GOLD,cid),arm)
    messages[0]['content']+=DELIVERY
    return {'model':base.MODEL,'messages':messages,'max_tokens':base.MAX_TOKENS,
            'temperature':0,'reasoning':{'enabled':True},'usage':{'include':True},
            'provider':{'only':[base.PROVIDER],'allow_fallbacks':False,'require_parameters':True,
                        'max_price':{'prompt':0.21,'completion':0.31,'request':0}}}


def output_check(content,inp):
    raw=content.strip()
    if raw.startswith('```'):
        match=re.fullmatch(r'```(?:json)?\s*\n(.*)\n```',raw,re.S)
        if not match:raise base.Blocked('unparseable_full_output')
        raw=match.group(1)
    try:data=json.loads(raw)
    except (ValueError,TypeError):raise base.Blocked('unparseable_full_output') from None
    if not isinstance(data,dict) or not {'documents','review_notes','unresolved_questions','final_checks'}<=set(data):
        raise base.Blocked('missing_delivery_sections')
    source={d['document_id']:d for d in inp['documents']}
    expected={k for k,d in source.items() if d['access'] in ('edit','format_only')}
    if not isinstance(data['documents'],list):raise base.Blocked('missing_full_documents')
    seen=set()
    for d in data['documents']:
        if not isinstance(d,dict):raise base.Blocked('invalid_document_candidate')
        did=d.get('document_id')
        if did not in source or did in seen:raise base.Blocked('unknown_or_duplicate_document')
        text=d.get('content')
        if not isinstance(text,str) or not text.strip():raise base.Blocked('empty_document_candidate')
        seen.add(did)
        if source[did]['access']=='read_only' and text!=source[did]['content']:
            raise base.Blocked('readonly_document_modified')
    if not expected<=seen:raise base.Blocked('missing_full_documents')
    return data,{'required_editable_documents':sorted(expected),'returned_documents':sorted(seen),
                 'all_editable_documents_present':True,'nonempty_full_candidates':True,
                 'content_completeness':'candidate existence only; semantic completeness needs separate review',
                 'readonly_snapshot_changes':False,'human_final_judgment':None}


def recover_state(state,record,response,status):
    expected={'spent_usd','pending','blocked','smoke_success','completed_targets','pending_upper_usd','pending_target'}
    if (set(state)!=expected or state['pending'] is not False or state['blocked'] is not True or
        state['smoke_success'] is not False or state['completed_targets']!=[] or state['pending_target']!='IR-003/B0'):
        raise base.Blocked('only_exact_legacy_settled_reasoning_block_recoverable')
    if (record.get('reason')!='cost_token_or_reasoning_policy_violation' or record.get('http_status')!=200 or
        record.get('calls')!=1 or record.get('finish_reasons')!=['stop'] or
        record.get('model_returned')!=base.MODEL or record.get('provider_returned')!='GMICloud'):
        raise base.Blocked('legacy_failure_not_reasoning_only')
    usage=response.get('usage',{})
    cost=base.amount(usage.get('cost'))
    if (record.get('usage')!=usage or cost!=base.amount(state['spent_usd']) or
        cost>base.amount(state['pending_upper_usd']) or
        usage.get('prompt_tokens',10**9)>record['estimate']['input_tokens_upper_estimate'] or
        usage.get('completion_tokens',10**9)>base.MAX_TOKENS or
        usage.get('completion_tokens_details',{}).get('reasoning_tokens',0)<=0 or
        response.get('model')!=base.MODEL or response.get('provider')!='GMICloud' or
        response.get('choices',[{}])[0].get('finish_reason')!='stop' or
        not response['choices'][0].get('message',{}).get('content')):
        raise base.Blocked('legacy_cost_or_protocol_evidence_invalid')
    if abs(base.amount(status['usage'])-cost)>Decimal('0.000001'):
        raise base.Blocked('server_spend_not_reconciled')
    result=copy.deepcopy(state)
    result['blocked']=False
    event={'kind':'resolve_only_settled_legacy_reasoning_violation','at':now(),
           'authorization':'user_explicit_request_2026-11-17_reasoning_allowed_comparison',
           'before':copy.deepcopy(state),'server_status':status,'reason':'new protocol permits reasoning; prior result remains a failed exploratory smoke',
           'legacy_response_cost_usd':str(cost),'after_blocked':False,'cost_preserved':True}
    result['recovery_events']=[event]
    result['legacy_requests']=[{'target':'IR-003/B0','protocol':'reasoning_disabled_exploratory',
                               'cost_usd':str(cost),'status':'reasoning_policy_violation',
                               'evidence_path':str(OLD.relative_to(base.REPO))}]
    result['campaigns']={PROTOCOL:{'attempts':[],'smoke_checked':False}}
    return result,event


def settlement_status(status,spent,last_seen='0'):
    """Known response costs remain reserved even when the server counter lags."""
    server=base.amount(status['usage']);known=base.amount(spent);previous=base.amount(last_seen)
    tolerance=Decimal('0.000001')
    if server>known+tolerance:raise base.Blocked('server_usage_exceeds_known_costs')
    if server+tolerance<previous:raise base.Blocked('server_usage_regressed')
    return {'state':'settled' if abs(server-known)<=tolerance else 'lagging_known_costs',
            'server_usage_usd':str(server),'ledger_usage_usd':str(known),
            'unreflected_known_cost_usd':str(max(known-server,Decimal(0))),
            'policy':'known response costs remain charged against local budget; no generation retry'}


def release_settlement_block(state,record,response,status):
    """Explicit authorization applies only to the already-accounted v2 first response."""
    if (state.get('pending') is not False or state.get('blocked') is not True or
        state.get('block_reason')!='post_request_spend_unreconciled'):
        raise base.Blocked('only_known_settlement_lag_releasable')
    attempts=state.get('campaigns',{}).get(PROTOCOL,{}).get('attempts',[])
    if (len(attempts)!=1 or attempts[0].get('target')!='IR-003/B0' or
        attempts[0].get('status')!='failed' or attempts[0].get('reason')!='post_request_spend_unreconciled'):
        raise base.Blocked('only_first_accounted_smoke_releasable')
    usage=response.get('usage',{});cost=base.amount(usage.get('cost'))
    if (record.get('reason')!='post_request_spend_unreconciled' or record.get('http_status')!=200 or
        record.get('usage')!=usage or record.get('calls')!=1 or record.get('finish_reasons')!=['stop'] or
        response.get('model')!=base.MODEL or response.get('provider')!='GMICloud' or response.get('error') or
        response.get('choices',[{}])[0].get('finish_reason')!='stop' or usage.get('is_byok') is not False or
        base.amount(attempts[0].get('cost_usd'))!=cost):
        raise base.Blocked('settlement_response_evidence_invalid')
    estimate=base.estimate(payload('IR-003','B0')['messages'])
    if (type(usage.get('prompt_tokens')) is not int or type(usage.get('completion_tokens')) is not int or
        not 0<=usage['prompt_tokens']<=estimate['input_tokens_upper_estimate'] or
        not 0<=usage['completion_tokens']<=base.MAX_TOKENS or cost>base.amount(estimate['upper_usd'])):
        raise base.Blocked('settlement_response_budget_invalid')
    reasoning=usage.get('completion_tokens_details',{}).get('reasoning_tokens')
    if type(reasoning) is not int or not 0<=reasoning<=usage['completion_tokens']:
        raise base.Blocked('settlement_reasoning_cost_unknown')
    output_check(response['choices'][0]['message']['content'],base.export_input(base.GOLD,'IR-003'))
    legacy=sum((base.amount(x['cost_usd']) for x in state.get('legacy_requests',[])),Decimal(0))
    if legacy+cost!=base.amount(state['spent_usd']):raise base.Blocked('ledger_cost_history_mismatch')
    if abs(base.amount(status['usage'])-base.amount(state['spent_usd']))>Decimal('0.000001'):
        raise base.Blocked('release_requires_server_reconciliation')
    result=copy.deepcopy(state)
    event={'kind':'user_authorized_release_of_known_settlement_lag','at':now(),
           'authorization':'user_explicit_request_fix_runner_and_continue_2026-11-17',
           'before':copy.deepcopy(state),'key_status':status,'cost_preserved':True,
           'original_failure_preserved':True,'new_generation_requests':0}
    result['blocked']=False;result.pop('block_reason',None)
    result['last_server_usage_usd']=status['usage']
    attempt=result['campaigns'][PROTOCOL]['attempts'][0]
    attempt['status']='response_complete';attempt['settlement_release']=event['at']
    result.setdefault('settlement_release_events',[]).append(event)
    return result,event


@contextmanager
def ledger(directory):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'budget.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise base.Blocked('parallel_execution_forbidden') from None
        path=directory/'budget.json'
        if not path.is_file():raise base.Blocked('existing_ledger_required')
        state=json.loads(path.read_text())
        base.amount(state['spent_usd'])
        yield path,state


def reserve_attempt(state,target,path):
    campaign=state['campaigns'][PROTOCOL]
    attempts=campaign['attempts']
    if target not in TARGETS or len(attempts)>=6 or any(x['target']==target for x in attempts):
        raise base.Blocked('max_six_or_duplicate_request_forbidden')
    attempts.append({'target':target,'status':'reserved','evidence_path':str(path),'at':now()})
    state['pending']=True
    return attempts[-1]


def legacy_evidence():
    for name in ('execution.json','response.json'):
        path=OLD/name
        original=subprocess.check_output(['git','show',PIN+':'+str(path.relative_to(base.REPO))],cwd=base.REPO)
        if path.read_bytes()!=original:raise base.Blocked('legacy_evidence_changed')
    return json.loads((OLD/'execution.json').read_text()),json.loads((OLD/'response.json').read_text())


def run(args,*,api=base.api_json,ledger_dir=None):
    # Creation is deliberately before credentials/network. Existing output is never modified.
    args.output.mkdir(parents=True,exist_ok=False)
    targets=['IR-003/B0'] if args.phase=='smoke' else TARGETS[1:] if args.phase=='remaining' else TARGETS
    plan={'protocol':PROTOCOL,'phase':args.phase,'execute':args.execute,'targets':[],
          'reasoning':{'enabled':True},'max_tokens':base.MAX_TOKENS,'temperature':0,
          'max_new_requests_campaign':6,'server_limit_usd':str(base.KEY_LIMIT),
          'runner_limit_usd':str(base.BUDGET),'model':base.MODEL,'provider':base.PROVIDER}
    for target in targets:
        cid,arm=target.split('/');req=payload(cid,arm)
        folder=args.output/cid/arm;folder.mkdir(parents=True)
        base.dump(folder/'input.json',req['messages']);base.dump(folder/'request.json',req)
        plan['targets'].append({'target':target,**base.estimate(req['messages'])})
    plan['new_cost_upper_usd']=str(sum((base.amount(x['upper_usd']) for x in plan['targets']),Decimal(0)))
    plan['runner_sha256']=base.digest(Path(__file__).read_bytes())
    plan['base_runner_sha256']=base.digest((base.HERE/'run.py').read_bytes())
    plan['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=base.REPO,text=True).strip()
    base.dump(args.output/'plan.json',plan)
    print(json.dumps(plan,ensure_ascii=False,indent=2),flush=True)
    if not args.execute:return
    if args.phase=='prepare':raise base.Blocked('prepare_has_no_live_requests')
    key,source=base.load_api_key()
    base.dump(args.output/'credential-safety.json',base.verify_secret_protection(key,source))
    if ledger_dir is None:
        common=Path(subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-common-dir'],cwd=base.REPO,text=True).strip())
        ledger_dir=common/'logicwrite-openrouter-pilot'
    with ledger(ledger_dir) as (path,state):
        if args.phase=='recover':
            # No generation request in this phase. Check costs, prices, original evidence first.
            record,response=legacy_evidence()
            status=base.key_status(api('GET','/key',key))
            endpoint=base.endpoint_status(api('GET','/models/'+base.MODEL+'/endpoints',key),
                                          max(x['input_tokens_upper_estimate'] for x in plan['targets']))
            endpoint['reasoning_disable_requested']=False;endpoint['reasoning_allowed']=True
            new,event=recover_state(state,record,response,status)
            event['legacy_record_sha256']=base.digest((OLD/'execution.json').read_bytes())
            event['legacy_response_sha256']=base.digest((OLD/'response.json').read_bytes())
            event['endpoint']=endpoint
            base.dump(args.output/'recovery-before.json',state)
            # Write durable audit before transition; save_ledger is atomic under the shared lock.
            base.dump(args.output/'recovery-event.json',event)
            base.save_ledger(path,new)
            base.dump(args.output/'recovery-after.json',new)
            return
        if args.phase=='settle':
            record_path=base.HERE/'reasoning-comparison-20261117/smoke/IR-003/B0/execution.json'
            response_path=record_path.with_name('response.json')
            for evidence in [record_path,response_path]:
                pinned=subprocess.check_output(['git','show','82a4980008da79f6691de4c03e9d1728a367f242:'+str(evidence.relative_to(base.REPO))],cwd=base.REPO)
                if evidence.read_bytes()!=pinned:raise base.Blocked('settlement_evidence_changed')
            status=base.key_status(api('GET','/key',key))
            new,event=release_settlement_block(state,json.loads(record_path.read_text()),json.loads(response_path.read_text()),status)
            event['record_sha256']=base.digest(record_path.read_bytes())
            event['response_sha256']=base.digest(response_path.read_bytes())
            base.dump(args.output/'settlement-before.json',state)
            base.dump(args.output/'settlement-event.json',event)
            base.save_ledger(path,new);base.dump(args.output/'settlement-after.json',new)
            return
        if state.get('blocked') or state.get('pending'):raise base.Blocked('unresolved_ledger_stop')
        if PROTOCOL not in state.get('campaigns',{}):raise base.Blocked('audited_recovery_required')
        campaign=state['campaigns'][PROTOCOL]
        if args.phase=='smoke' and campaign['attempts']:raise base.Blocked('smoke_already_attempted_no_retry')
        if args.phase=='remaining':
            attempts=campaign['attempts']
            if not (len(attempts)==1 and attempts[0]['target']=='IR-003/B0' and
                    attempts[0]['status']=='response_complete' and args.confirm_smoke_checked):
                raise base.Blocked('complete_smoke_and_explicit_operator_check_required')
            campaign['smoke_checked']=True
            campaign['smoke_check_authorization']='user authorized agent completeness/cost/protocol check; human semantic judgment remains pending'
            base.save_ledger(path,state)
        for item in plan['targets']:
            target=item['target'];cid,arm=target.split('/');folder=args.output/cid/arm
            record={'protocol':PROTOCOL,'target':target,'state':'preflight','calls':0,'D':'unobserved',
                    'usage':None,'human_final_judgment':None,'input_sha256':base.digest((folder/'input.json').read_bytes())}
            base.dump(folder/'execution.json',record)
            attempt=None
            try:
                status=base.key_status(api('GET','/key',key))
                endpoint=base.endpoint_status(api('GET','/models/'+base.MODEL+'/endpoints',key),item['input_tokens_upper_estimate'])
                endpoint['reasoning_disable_requested']=False;endpoint['reasoning_allowed']=True
                record.update(key_status=status,endpoint=endpoint)
                record['settlement_before']=settlement_status(status,state['spent_usd'],state.get('last_server_usage_usd','0'))
                state['last_server_usage_usd']=status['usage']
                upper=base.amount(item['upper_usd'])
                if max(base.amount(status['usage']),base.amount(state['spent_usd']))+upper>base.BUDGET or upper>base.amount(status['limit_remaining']):
                    raise base.Blocked('request_upper_bound_exceeds_remaining_budget')
                attempt=reserve_attempt(state,target,str(folder.resolve()))
                state['pending_upper_usd']=str(upper);state['pending_target']=target
                base.save_ledger(path,state)
                record.update(state='request_started',calls=1);base.dump(folder/'execution.json',record)
                start=time.monotonic()
                try:result=api('POST','/chat/completions',key,json.loads((folder/'request.json').read_text()))
                finally:record['seconds']=time.monotonic()-start
                record['http_status']=result.pop('_http_status',None)
                base.dump(folder/'response.json',base.sanitized(result,key))
                usage=result.get('usage',{});cost=base.amount(usage.get('cost'))
                for field in ('prompt_tokens','completion_tokens'):
                    if type(usage.get(field)) is not int or usage[field]<0:raise base.Blocked('missing_token_accounting')
                reasoning=usage.get('completion_tokens_details',{}).get('reasoning_tokens')
                # Separately record reasoning and non-reasoning output; never add reasoning twice.
                if type(reasoning) is not int or not 0<=reasoning<=usage['completion_tokens']:
                    raise base.Blocked('reasoning_token_accounting_unknown')
                record.update(usage=usage,reasoning_tokens=reasoning,
                    non_reasoning_completion_tokens=usage['completion_tokens']-reasoning,
                    model_returned=result.get('model'),provider_returned=result.get('provider'))
                state['spent_usd']=str(base.amount(state['spent_usd'])+cost)
                state['pending']=False;attempt.update(cost_usd=str(cost),status='accounted')
                base.save_ledger(path,state)
                reasons=[c.get('finish_reason') for c in result.get('choices',[])];record['finish_reasons']=reasons
                if result.get('error') or record['http_status']!=200:raise base.Blocked('api_error')
                if result.get('model')!=base.MODEL or result.get('provider')!=endpoint['provider_name']:
                    raise base.Blocked('model_provider_mismatch')
                if usage.get('is_byok') is not False:raise base.Blocked('BYOK_or_unknown_billing')
                if cost>upper or usage['prompt_tokens']>item['input_tokens_upper_estimate'] or usage['completion_tokens']>base.MAX_TOKENS:
                    raise base.Blocked('cost_or_token_bound_exceeded')
                if reasons!=['stop']:raise base.Blocked('output_truncated' if 'length' in reasons else 'incomplete_response')
                content=result['choices'][0].get('message',{}).get('content')
                if not isinstance(content,str) or not content.strip():raise base.Blocked('empty_response')
                data,checks=output_check(content,base.export_input(base.GOLD,cid))
                base.dump(folder/'candidate.json',data);base.dump(folder/'automatic-checks.json',checks)
                # Full candidates stay in the experiment directory, never actual document paths.
                after=base.key_status(api('GET','/key',key));record['key_status_after']=after
                record['settlement_after']=settlement_status(after,state['spent_usd'],state.get('last_server_usage_usd','0'))
                state['last_server_usage_usd']=after['usage']
                attempt['settlement']=record['settlement_after']
                if max(base.amount(after['usage']),base.amount(state['spent_usd']))>base.BUDGET:
                    raise base.Blocked('budget_exceeded')
                record['state']='response_complete';record['semantic_quality']='pending_AI_and_human_review'
                attempt['status']='response_complete';base.save_ledger(path,state)
            except Exception as exc:
                reason=str(exc) if isinstance(exc,base.Blocked) else type(exc).__name__
                record.update(state='failed',reason=reason)
                if isinstance(exc,urllib.error.HTTPError):record['http_status']=exc.code
                if isinstance(exc,(TimeoutError,socket.timeout)):record['reason']='timeout'
                state['blocked']=True;state['block_reason']=record['reason']
                if attempt is not None:attempt.update(status='failed',reason=record['reason'])
                base.save_ledger(path,state);base.dump(folder/'execution.json',base.sanitized(record,key))
                raise base.Blocked(record['reason']) from None
            base.dump(folder/'execution.json',base.sanitized(record,key))
        base.dump(args.output/'ledger-after.json',state)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=['prepare','recover','settle','smoke','remaining'],default='prepare')
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--confirm-smoke-checked',action='store_true')
    args=parser.parse_args()
    try:run(args)
    except base.Blocked as e:raise SystemExit(str(e)) from None
    except FileExistsError:raise SystemExit('output_directory_already_exists') from None

if __name__=='__main__':main()
