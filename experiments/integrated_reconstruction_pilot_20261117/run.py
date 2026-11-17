#!/usr/bin/env python3
"""Input-only preparation and opt-in, one-call OpenAI-compatible HTTP execution.
No Core modification, application, CLI agent, reference output, or scoring.
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    cfg = json.loads((HERE / 'config.json').read_text())
    # A fresh directory is mandatory, including for preparation. Never overwrite evidence.
    args.output.mkdir(parents=True, exist_ok=False)
    ready = all(os.environ.get(k) for k in ('PILOT_API_KEY', 'PILOT_BASE_URL', 'PILOT_MODEL'))
    dump(args.output / 'environment.json', {
        'python': sys.version, 'platform': sys.platform,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        'config': cfg, 'api_environment_ready': ready,
        'credential_values_recorded': False, 'execute_requested': args.execute,
        'model_requested': os.environ.get('PILOT_MODEL'),
        'endpoint': os.environ.get('PILOT_BASE_URL'),
        'provenance': 'input-only preparation; API readiness is environment presence, not connectivity proof'})
    for cid in ('IR-001', 'IR-002', 'IR-003'):
        inp = export_input(GOLD, cid)
        for arm in ('B0', 'B1', 'B2'):
            dest = args.output / cid / arm
            dest.mkdir(parents=True)
            if arm == 'B2':
                dump(dest / 'execution.json', {'state': 'unsupported_current_integration', 'calls': 0,
                     'reason': 'Single source snapshot/concrete scope; no joint document analysis or native per-document access mapping. No adapter or pipeline executed.',
                     'hitl': 'not_assessed'})
                continue
            prompt = messages(inp, arm)
            dump(dest / 'input.json', prompt)
            raw_input = (dest / 'input.json').read_bytes()
            record = {'state': 'prepared_not_run', 'calls': 0, 'input_sha256': digest(raw_input),
                      'source_input_sha256': digest((GOLD / 'inputs' / (cid + '.json')).read_bytes()),
                      'D': 'unobserved', 'Q': 'not_evaluated_no_model_output', 'F': 'not_evaluated',
                      'HITL': 'not_assessed', 'usage': None, 'seconds': None}
            if not args.execute or not ready:
                record['blocker'] = 'execution_not_requested' if ready else 'missing_dedicated_api_environment'
                dump(dest / 'execution.json', record)
                continue
            payload = {'model': os.environ['PILOT_MODEL'], 'messages': prompt,
                       'max_completion_tokens': cfg['max_completion_tokens']}
            dump(dest / 'request.json', payload)
            request = urllib.request.Request(os.environ['PILOT_BASE_URL'].rstrip('/') + '/chat/completions',
                data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + os.environ['PILOT_API_KEY']})
            start = time.monotonic()
            record.update(state='request_started', calls=1)
            dump(dest / 'execution.json', record)
            try:
                with urllib.request.urlopen(request, timeout=cfg['timeout_seconds']) as response:
                    raw = response.read()
                (dest / 'response.raw.json').write_bytes(raw)
                result = json.loads(raw)
                record.update(state='response_received', response_sha256=digest(raw),
                    model_returned=result.get('model'), usage=result.get('usage'),
                    finish_reasons=[c.get('finish_reason') for c in result.get('choices', [])])
                # Receipt is not a completeness or semantic success judgment.
                record['Q'] = 'pending_output_completeness_review'
            except Exception as exc:
                # Provider exceptions may contain credential or source text: record only type/status.
                record.update(state='execution_failed', error_type=type(exc).__name__,
                              http_status=getattr(exc, 'code', None))
            record['seconds'] = time.monotonic() - start
            dump(dest / 'execution.json', record)
    if args.execute and not ready:
        raise SystemExit('No model called: PILOT_API_KEY, PILOT_BASE_URL, PILOT_MODEL required')


if __name__ == '__main__':
    main()
