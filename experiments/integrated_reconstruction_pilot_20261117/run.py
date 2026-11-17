#!/usr/bin/env python3
"""Offline-first, budget-limited sequential OpenRouter pilot.
No Core changes, document application, reference outputs, or semantic scoring.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import urllib.error
from decimal import Decimal, InvalidOperation
import fcntl
import socket
from contextlib import contextmanager

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
GOLD = REPO / 'evaluation/integrated_reconstruction'
sys.path.insert(0, str(GOLD))
from validate import export_input

BASE = ('제공된 원문과 사용자 요청 및 권한에 따라 검토 가능한 전체 문서 후보를 작성하세요. '
        'delivery 요구에 따라 변경 근거, 미해결 사항, 최종 검증을 전체 후보와 별도로 제출하세요. '
        '변경하지 않은 편집 가능 문서도 전체 원문을 반환하세요. 실제 저장·발행은 하지 마세요. '
        '비공개 사고과정은 제출하지 마세요.')
IMPROVED = ('문서별 독자·목적·근거·권한을 확인하고 필요한 개선만 수행하세요. '
            '수치·조건·적용 범위·출처와 고유 정보를 보존하고 충돌을 임의 해결하지 마세요. '
            '확인할 사항은 별도 검토 기록에 근거와 질문으로 남기고, 독립적으로 가능한 작업은 계속하세요. '
            '전체 후보를 문서군 단위로 재검토하세요. 불필요한 변경은 피하세요.')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def messages(inp, arm):
    return [{'role': 'system', 'content': BASE + ('\n' + IMPROVED if arm == 'B1' else '')},
            {'role': 'user', 'content': json.dumps(inp, ensure_ascii=False)}]


# These are ceilings approved for this pilot, never automatic price upgrades.
API = 'https://openrouter.ai/api/v1'
MODEL = 'deepseek/deepseek-v3.2'
PROVIDER = 'gmicloud/fp8'
PROMPT_PRICE = Decimal('0.00000021')
OUTPUT_PRICE = Decimal('0.00000031')
BUDGET = Decimal('0.20')
KEY_LIMIT = Decimal('0.25')
MAX_TOKENS = 12000
TIMEOUT = 600

class Blocked(RuntimeError):
    """Fixed safe reason only; never include provider errors or credentials."""


def amount(value):
    if isinstance(value, bool) or value is None:
        raise Blocked('missing_or_invalid_amount')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise Blocked('missing_or_invalid_amount') from None
    if not result.is_finite() or result < 0:
        raise Blocked('missing_or_invalid_amount')
    return result


def estimate(prompt):
    # Deliberately loose UTF-8 byte bound + chat-template allowance, NOT a tokenizer.
    upper = len(json.dumps(prompt, ensure_ascii=False).encode('utf-8')) + 4096
    return {'input_tokens_upper_estimate': upper, 'max_output_tokens': MAX_TOKENS,
            'upper_usd': str(upper * PROMPT_PRICE + MAX_TOKENS * OUTPUT_PRICE),
            'method': 'UTF-8 bytes plus 4096 template allowance; conservative estimate, not exact tokens'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Blocked('redirect_refused')


def api_json(method, path, key, payload=None):
    # Fixed host, no redirects, no retries, no dotenv/config discovery.
    request = urllib.request.Request(API + path, method=method,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=TIMEOUT if method == 'POST' else 30) as r:
        return json.loads(r.read())


def key_status(result):
    data = result['data']
    cap, remaining, used = (amount(data.get(k)) for k in ('limit','limit_remaining','usage'))
    if cap <= 0 or cap > KEY_LIMIT or data.get('limit_reset', 'missing') is not None:
        raise Blocked('key_requires_lifetime_limit_at_most_0.25')
    if amount(data.get('byok_usage')) != 0:
        raise Blocked('BYOK_not_supported')
    if remaining > cap or used + remaining > cap + Decimal('.000001'):
        raise Blocked('inconsistent_key_accounting')
    return {'limit': str(cap), 'limit_remaining': str(remaining), 'usage': str(used),
            'limit_reset': None, 'byok_usage': '0'}


def endpoint_status(result, input_bound):
    data = result['data']
    if data.get('id') != MODEL:
        raise Blocked('model_catalog_mismatch')
    matches = [e for e in data['endpoints'] if e.get('tag') == PROVIDER]
    if len(matches) != 1:
        raise Blocked('pinned_endpoint_unavailable')
    e = matches[0]
    prices = e['pricing']
    prompt, completion = amount(prices.get('prompt')), amount(prices.get('completion'))
    if prompt > PROMPT_PRICE or completion > OUTPUT_PRICE:
        raise Blocked('price_exceeds_approved_ceiling')
    for name, value in prices.items():
        if name in ('prompt','completion','input_cache_read','input_cache_write','discount'):
            # Cache write may be an additional cost: this harness never requests it.
            if name == 'input_cache_write' and amount(value) != 0:
                raise Blocked('additional_cache_write_price')
            amount(value)
        elif amount(value) != 0:
            raise Blocked('unknown_or_additional_price')
    supported = e.get('supported_parameters', [])
    if not {'max_tokens','temperature','reasoning'}.issubset(supported):
        raise Blocked('required_parameters_unsupported')
    if e.get('status') != 0 or e['context_length'] < input_bound + MAX_TOKENS:
        raise Blocked('endpoint_unavailable_or_context_exceeded')
    if (e.get('max_completion_tokens') or 0) < MAX_TOKENS:
        raise Blocked('endpoint_output_limit_too_low')
    return {'tag': PROVIDER, 'provider_name': e['provider_name'], 'pricing': prices,
            'supported_parameters': supported, 'reasoning_disable_requested': True}


@contextmanager
def budget_ledger(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory/'budget.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Blocked('parallel_execution_forbidden') from None
        path = directory/'budget.json'
        if path.exists():
            try:
                state=json.loads(path.read_text())
                amount(state['spent_usd'])
                if type(state['pending']) is not bool or type(state['blocked']) is not bool:
                    raise ValueError()
                if state['pending'] or state['blocked']:
                    raise Blocked('prior_request_unresolved_or_failed_manual_reconciliation_required')
            except (ValueError, KeyError):
                raise Blocked('invalid_budget_ledger') from None
        else:
            state={'spent_usd':'0', 'pending':False, 'blocked':False, 'smoke_success':False,
                   'completed_targets':[]}
        yield path, state


def save_ledger(path, state):
    # Same-directory atomic replacement while holding a separate stable lock inode.
    temp=path.with_suffix('.tmp')
    with temp.open('w') as file:
        json.dump(state,file,indent=2); file.flush(); os.fsync(file.fileno())
    temp.replace(path)


def sanitized(value, key):
    return json.loads(json.dumps(value,ensure_ascii=False).replace(key,'[REDACTED]'))


def select_targets(args):
    if args.smoke:
        if args.case not in (None,'IR-003') or args.arm not in (None,'B0'):
            raise Blocked('first_smoke_must_be_IR-003_B0')
        return [('IR-003','B0')]
    return [(c,a) for c in ([args.case] if args.case else ['IR-001','IR-002','IR-003'])
            for a in ([args.arm] if args.arm else ['B0','B1'])]


def run(args, *, api=api_json, ledger_dir=None):
    targets=select_targets(args)
    args.output.mkdir(parents=True,exist_ok=False)
    plans=[]
    for cid,arm in targets:
        prompt=messages(export_input(GOLD,cid),arm)
        folder=args.output/cid/arm; folder.mkdir(parents=True)
        dump(folder/'input.json',prompt)
        plans.append(dict(case=cid,arm=arm,**estimate(prompt)))
    plan={'mode':'live_requested' if args.execute else 'offline_dry_run',
          'model':MODEL,'provider':PROVIDER,'max_output_tokens':MAX_TOKENS,
          'timeout_seconds':TIMEOUT,'targets':plans,
          'total_upper_usd':str(sum((amount(x['upper_usd']) for x in plans),Decimal(0))),
          'budget_usd':str(BUDGET),'server_key_limit_usd':str(KEY_LIMIT),
          'pricing':'offline ceilings; live endpoint prices must be revalidated before every POST',
          'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()}
    dump(args.output/'plan.json',plan)
    print(json.dumps(plan,ensure_ascii=False,indent=2),flush=True)
    if not args.execute:
        return
    key=os.environ.get('OPENROUTER_API_KEY')
    if not key:
        raise Blocked('OPENROUTER_API_KEY_required')
    if ledger_dir is None:
        common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=REPO,text=True).strip())
        if not common.is_absolute(): common=REPO/common
        ledger_dir=common/'logicwrite-openrouter-pilot'
    with budget_ledger(ledger_dir) as (ledger_path,state):
        if not args.smoke and not (state['smoke_success'] and args.confirm_smoke_reviewed):
            raise Blocked('run_smoke_then_explicitly_confirm_cost_and_completeness_review')
        for item in plans:
            cid,arm=item['case'],item['arm']
            target=cid+'/'+arm
            if target in state['completed_targets']:
                dump(args.output/cid/arm/'execution.json', {'state':'skipped_previously_completed','calls':0})
                continue
            folder=args.output/cid/arm
            record={'state':'preflight','calls':0,'usage':None,'D':'unobserved',
                    'Q':'not_evaluated','F':'not_evaluated','HITL':'not_assessed',
                    'estimate':item, 'input_sha256':digest((folder/'input.json').read_bytes())}
            dump(folder/'execution.json',record)
            try:
                status=key_status(api('GET','/key',key))
                endpoint=endpoint_status(api('GET','/models/'+MODEL+'/endpoints',key),item['input_tokens_upper_estimate'])
                record.update(key_status=status,endpoint=endpoint)
                upper=amount(item['upper_usd'])
                used=max(amount(status['usage']),amount(state['spent_usd']))
                if used + upper > BUDGET or upper > amount(status['limit_remaining']):
                    raise Blocked('request_upper_bound_exceeds_remaining_budget')
                prompt=json.loads((folder/'input.json').read_text())
                payload={'model':MODEL,'messages':prompt,'max_tokens':MAX_TOKENS,'temperature':0,
                         'reasoning':{'enabled':False},'usage':{'include':True},
                         'provider':{'only':[PROVIDER],'allow_fallbacks':False,'require_parameters':True,
                                     'max_price':{'prompt':0.21,'completion':0.31,'request':0}}}
                dump(folder/'request.json',payload)
                state.update(pending=True, pending_upper_usd=str(upper),pending_target=target)
                save_ledger(ledger_path,state)
                record.update(state='request_started',calls=1)
                dump(folder/'execution.json',record)
                started=time.monotonic()
                try:
                    result=api('POST','/chat/completions',key,payload)
                finally:
                    record['seconds']=time.monotonic()-started
                # Never archive untrusted provider text without credential redaction.
                dump(folder/'response.json',sanitized(result,key))
                usage=result.get('usage',{})
                if result.get('error'):
                    record['state']='api_error'
                    if not isinstance(usage,dict) or usage.get('cost') is None:
                        raise Blocked('api_error_cost_unknown')
                cost=amount(usage.get('cost'))
                for field in ('prompt_tokens','completion_tokens'):
                    if type(usage.get(field)) is not int or usage[field]<0:
                        raise Blocked('missing_token_accounting')
                state['spent_usd']=str(amount(state['spent_usd'])+cost)
                state['pending']=False
                record.update(usage=usage,model_returned=result.get('model'),provider_returned=result.get('provider'))
                reasons=[c.get('finish_reason') for c in result.get('choices',[])]
                record['finish_reasons']=reasons
                reasoning=usage.get('completion_tokens_details',{}).get('reasoning_tokens')
                record['reasoning_observed']=('zero_reported_tokens' if reasoning==0 else
                    'nonzero_reported_tokens' if reasoning is not None else 'unknown_not_reported')
                if usage.get('is_byok') is True:
                    raise Blocked('BYOK_not_supported')
                if result.get('error') or 'error' in reasons:
                    record['state']='api_error'; raise Blocked('api_error')
                if reasons==['length']:
                    record['state']='output_truncated'; raise Blocked('output_truncated')
                if reasons!=['stop'] or not result['choices'][0].get('message',{}).get('content'):
                    raise Blocked('incomplete_or_empty_response')
                if result.get('model')!=MODEL or result.get('provider')!=endpoint['provider_name']:
                    raise Blocked('model_or_provider_mismatch')
                if (usage['prompt_tokens']>item['input_tokens_upper_estimate'] or
                    usage['completion_tokens']>MAX_TOKENS or cost>upper or reasoning not in (None,0)):
                    raise Blocked('cost_token_or_reasoning_policy_violation')
                # Recheck status after settlement; failure freezes the experiment.
                after=key_status(api('GET','/key',key))
                record['key_status_after']=after
                if max(amount(after['usage']),amount(state['spent_usd']))>BUDGET:
                    raise Blocked('budget_exceeded_stop')
                record.update(state='response_received',Q='pending_human_completeness_and_semantic_review')
                state['completed_targets'].append(target)
                if args.smoke: state['smoke_success']=True
                save_ledger(ledger_path,state)
            except Exception as exc:
                if record['state'] not in ('api_error','output_truncated'):
                    record['state']=('timeout' if isinstance(exc,(TimeoutError,socket.timeout)) or
                        isinstance(exc,urllib.error.URLError) and isinstance(exc.reason,TimeoutError) else
                        'api_error' if isinstance(exc,urllib.error.HTTPError) else
                        'accounting_or_preflight_failure')
                record['reason']=str(exc) if isinstance(exc,Blocked) else type(exc).__name__
                if isinstance(exc,urllib.error.HTTPError): record['http_status']=exc.code
                if record['calls']:
                    state['blocked']=True; save_ledger(ledger_path,state)
                dump(folder/'execution.json',sanitized(record,key))
                raise Blocked(record['state']) from None
            dump(folder/'execution.json',sanitized(record,key))


def main():
    parser=argparse.ArgumentParser(description='Offline by default; budget-limited sequential OpenRouter pilot')
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--execute',action='store_true',help='Explicitly enable authenticated GETs and paid POSTs')
    parser.add_argument('--case',choices=['IR-001','IR-002','IR-003'])
    parser.add_argument('--arm',choices=['B0','B1'])
    parser.add_argument('--smoke',action='store_true',help='Exactly IR-003/B0; mandatory first live run')
    parser.add_argument('--confirm-smoke-reviewed',action='store_true',help='User confirms actual cost and complete smoke output reviewed')
    args=parser.parse_args()
    try:
        run(args)
    except (Blocked,FileExistsError) as exc:
        # Fixed reasons only; never echo environment or provider exception strings.
        reason=str(exc) if isinstance(exc,Blocked) else 'output_directory_already_exists'
        raise SystemExit(reason) from None

if __name__=='__main__': main()
