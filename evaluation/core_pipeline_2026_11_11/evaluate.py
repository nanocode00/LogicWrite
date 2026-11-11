#!/usr/bin/env python3
"""Read-only, label-blind Core diagnostics; reference comparison is a separate step.

SP's bundle/contract schema is not Core's schema. This adapter therefore reports
native lexical witnesses and source-only pipeline projections, never SP predictions
or full-candidate structural gates for externally authored SP candidates.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CORE = Path(os.environ.get('LOGICWRITE_CORE_CODE_ROOT', REPO / 'experiments/full_document_control')).resolve()
INPUTS = REPO / 'evaluation/semantic_pilot/inputs'
GOLD = REPO / 'evaluation/g3_g4/development_gold_v2_2026-11-11/development-gold.json'
sys.path.insert(0, str(CORE))
import expression
import final_semantic_validator as semantic
import integration
import organization
import pipeline
import reconstruction
import repair_loop

INPUT_KEYS = {'schema_version', 'case_id', 'task', 'source_kind', 'construction',
              'source_documents', 'candidate_documents', 'writing_contract',
              'missing_context', 'supplied_observations'}


def read(path):
    return json.loads(Path(path).read_bytes())


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract(doc='document'):
    """Diagnostic-only contract: does not pretend to resolve SP requirements."""
    return {'contract_id': 'readonly-core-diagnostic', 'version': '1',
            'document_type': 'diagnostic', 'audience': 'developer',
            'purpose': 'Inventory supplied source text without approval',
            'language': 'mixed', 'register': 'neutral_technical',
            'output_scopes': [{'scope_id': 'source', 'document_id': doc}],
            'required_information': [], 'constraints': []}


def snapshot(doc, side):
    text = doc['content']
    return {'document_id': doc['document_id'], 'snapshot_id': side+':'+doc['document_id'],
            'version': doc['version'], 'coverage': 'complete', 'media_type': 'text/markdown',
            'content': text, 'sha256': pipeline.digest_text(text)}


def ledger(source, output):
    """Positional diagnostic pairing, not a reconstructed or authenticated edit ledger.

    Same line counts permit line-wise literal witnesses; otherwise use the full
    document. Reorders may confuse this heuristic, so no SP classification follows.
    """
    before = source['content'].splitlines(keepends=True)
    after = output['content'].splitlines(keepends=True)
    if len(before) != len(after):
        before, after = [source['content']], [output['content']]
    rows, a, b = [], 0, 0
    for first, second in zip(before, after):
        if first and second:
            rows.append({'source_document_id': source['document_id'],
                'output_document_id': output['document_id'], 'start': a, 'end': a+len(first),
                'output_start': b, 'output_end': b+len(second), 'text': second})
        a += len(first)
        b += len(second)
    return rows


def predict(raw):
    if set(raw) != INPUT_KEYS:
        raise ValueError('Only the input-only SP schema is accepted; no answer/reference fields')
    # Deep-copy only input artifacts. No answer or development registry is loaded here.
    data = copy.deepcopy(raw)
    result = {'case_id': data['case_id'], 'runtime_input_sha256': pipeline.canonical_json_digest(data),
              'comparison_scope': 'native_literal_diagnostic_only', 'sp_prediction': None,
              'delivery_approved': False, 'stage_transition_allowed': False,
              'real_model': 'not_run', 'witness_rule_ids': [], 'witnesses': [],
              'limitations': ['SP_CONTRACT_NOT_NATIVE_CORE_CONTRACT',
                 'POSITIONAL_DIAGNOSTIC_LEDGER_NOT_PIPELINE_PROVENANCE',
                 'NO_SEMANTIC_EQUIVALENCE_OR_EXTERNAL_TRUTH_OR_APPROVAL_INFERENCE'],
              'source_only_pipeline': []}
    sources, candidates = data['source_documents'], data['candidate_documents']
    if any(d.get('availability') != 'complete' or not isinstance(d.get('content'), str)
           or not d['content'].strip() for d in sources+candidates):
        result['comparison_scope'] = 'unsupported'
        result['limitations'].append('COMPLETE_SOURCE_AND_OUTPUT_SNAPSHOTS_REQUIRED')
        return result
    source_ids = [d['document_id'] for d in sources]
    candidate_ids = [d['document_id'] for d in candidates]
    if (set(source_ids) != set(candidate_ids) or len(set(source_ids)) != len(source_ids)
            or len(set(candidate_ids)) != len(candidate_ids)):
        result['comparison_scope'] = 'unsupported'
        result['limitations'].append('DOCUMENT_ID_SET_DIFFERS_NO_BASELINE_RESOLVER')
        return result
    docs = {d['document_id']: snapshot(d, 'source') for d in sources}
    outputs = {d['document_id']: snapshot(d, 'output') for d in candidates}
    b = {'case_id': data['case_id'], 'document_snapshot': next(iter(docs.values())),
         'writing_contract': contract(source_ids[0])}
    findings, pairs = [], []
    def add(check, status, rule, evidence):
        findings.append({'check_id': check, 'status': status, 'rule_id': rule, 'evidence': evidence})
    projected_result = {'block_ledger': [r for doc in docs for r in ledger(docs[doc], outputs[doc])], 'trace': []}
    semantic._deterministic(b, {'units': []}, projected_result, docs, outputs, add, pairs)
    result['witnesses'] = findings
    result['witness_rule_ids'] = sorted({f['rule_id'] for f in findings})
    result['literal_pair_count'] = len(pairs)
    if len(docs) > 1:
        result['limitations'].append('CROSS_DOCUMENT_DEPENDENCIES_NOT_INFERRED')
    for doc in sources:
        bundle = integration.markdown_bundle(doc['content'], contract(doc['document_id']))
        bundle['document_snapshot']['version'] = doc['version']
        outcome = integration.run_pipeline(bundle)
        result['source_only_pipeline'].append({'document_id': doc['document_id'],
            'runtime_bundle_sha256': pipeline.canonical_json_digest(bundle),
            'status': outcome['status'], 'delivery_approved': outcome['delivery_approved'],
            'analysis_gate': outcome['analysis_report']['gate_state'] if outcome['analysis_report'] else None,
            'final_gate': outcome['final_audit']['gate_state'] if outcome['final_audit'] else None,
            'candidate_equals_source': (outcome['revision_result']['output_snapshots'][0]['content'] == doc['content'])
                 if outcome['revision_result'] and outcome['revision_result']['output_snapshots'] else None})
    return result


def run_predictions():
    rows = []
    # Fixed input inventory: deliberately independent from the gold manifest.
    for n in range(1, 13):
        path = INPUTS / f'SP-{n:03}.json'
        row = predict(read(path))
        row.update(input_path=str(path.relative_to(REPO)), input_sha256=file_sha(path))
        rows.append(row)
    return {'schema_version': '1', 'mode': 'deterministic_readonly_diagnostics',
            'real_model': 'not_run', 'reference_labels_loaded': False, 'cases': rows}


def compare(predictions):
    """References enter only here, after predictions have been materialized."""
    gold = read(GOLD)
    expected = {r['case_id']: r for r in gold['cases']}
    if len(predictions['cases']) != 12 or {r['case_id'] for r in predictions['cases']} != set(expected):
        raise ValueError('Incomplete or duplicate prediction inventory')
    rows = []
    for p in predictions['cases']:
        r = expected[p['case_id']]
        if p['input_sha256'] != r['input_sha256'] or file_sha(REPO/p['input_path']) != r['input_sha256']:
            raise ValueError('Prediction/reference input hash mismatch')
        label = r['user_final_judgment']
        witnesses = [w for w in p['witnesses'] if w['status'] == 'violated']
        if p['comparison_scope'] == 'unsupported':
            outcome = '미해결: 미지원 입력 또는 기준 버전 미확정'
        elif witnesses and label == 'VIOLATION':
            outcome = '올바른 탐지: 제한된 리터럴 증거; 전체 3분류는 미실행'
        elif witnesses:
            outcome = '오탐 후보: 위치 기반 증거의 문맥 검토 필요'
        elif label == 'VIOLATION':
            outcome = '미탐: 결정론적 리터럴 진단에서 위반 확증 없음'
        else:
            outcome = '미해결: 의미 보존/계약 충족 자동 판정 미지원'
        rows.append({'case_id': p['case_id'], 'expected_sp_judgment': label,
            'actual_sp_prediction': p['sp_prediction'], 'actual_core_gate_for_sp_candidate': None,
            'analysis': outcome, 'module': 'final_semantic_validator._deterministic (diagnostic invocation)',
            'error_type': ('unsupported_context' if p['comparison_scope']=='unsupported' else
                           'bounded_literal_detection' if witnesses else 'semantic_coverage_gap'),
            'input_path': p['input_path'], 'input_sha256': p['input_sha256'],
            'reference_path': str(GOLD.relative_to(REPO)),
            'reference_pointer': '/cases/'+str(gold['cases'].index(r)),
            'prediction_pointer': '/cases/'+str(predictions['cases'].index(p)),
            'evidence_pointer': '/cases/'+str(predictions['cases'].index(p))+'/witnesses',
            'witness_rule_ids': p['witness_rule_ids'],
            'priority': 'P2', 'fix_needed': 'Future semantic/context adapter evaluation; no automatic gate policy change',
            'reproduce': 'python3 evaluation/core_pipeline_2026_11_11/evaluate.py predict /tmp/predictions.json'})
    return {'dataset_role': gold['dataset_role'], 'reference_manifest_sha256': file_sha(GOLD),
            'comparison_is_sp_accuracy': False, 'reason': 'No Core API implements the SP three-way task; no gate renaming',
            'cases': rows}


def native_case(text='# 안내\n\n제한 시간은 30초다.\n\n자동 업데이트를 지원하지 않음.\n\n캐시가 있을 때만 실행 가능하다.\n'):
    bundle = integration.markdown_bundle(text, contract())
    outcome = integration.run_pipeline(bundle)
    return bundle, outcome['analysis'], outcome['organization_plan'], outcome['expression_preview'], outcome['revision_result']


def mutate_result(result, before, after):
    """Adversarial forged candidate; whole audit must reject it independently."""
    result = copy.deepcopy(result)
    snap = result['output_snapshots'][0]
    snap['content'] = snap['content'].replace(before, after)
    snap['sha256'] = pipeline.digest_text(snap['content'])
    cursor = 0
    for row in result['block_ledger']:
        if row.get('alias'):
            continue
        row['text'] = row['text'].replace(before, after)
        row['output_start'], row['output_end'] = cursor, cursor+len(row['text'])
        cursor = row['output_end']
    expression.seal(result, 'revision_sha256')
    return result


def native_probes():
    bundle, analysis, org, preview, result = native_case()
    rows = []
    for cid, before, after, expected in [
        ('N-01-quantity-unit', '30초', '30분', 'FAIL'),
        ('N-02-negation', '지원하지 않음', '지원함', 'FAIL'),
        ('N-03-unsupported-addition', '30초다.', '30초다. SOC 2 인증을 보장한다.', 'FAIL'),
        ('N-04-condition-loss', '캐시가 있을 때만 실행 가능하다.', '항상 실행 가능하다.', 'FAIL'),
        ('N-05-unchanged-unapproved', 'absent', 'unused', 'REVIEW')]:
        candidate = mutate_result(result, before, after)
        audit = pipeline.validate_final_output(bundle, analysis, org, preview, candidate)
        approval = pipeline.validate_final_approval_policy(bundle, analysis, org, preview, candidate, audit)
        rows.append({'case_id': cid, 'expected_gate': expected, 'actual_gate': audit['gate_state'],
            'structural_gate': audit['structural_report']['gate_state'],
            'semantic_gate': audit['semantic_report']['gate_state'],
            'semantic_checks': audit['semantic_report']['checks'],
            'semantic_execution': audit['semantic_report']['execution']['state'],
            'structural_rule_ids': sorted({f['rule_id'] for f in audit['structural_report']['findings']}),
            'approval_gate': approval['gate_state'], 'approval_policy': approval['policy_state'],
            'delivery_approved': approval['delivery_approved'],
            'analysis': ('미해결 의미 검수 / 승인 보류' if expected == 'REVIEW' else
                         '올바른 구조적 안전 차단; 의미 탐지는 개별 semantic_checks만 참조')
                         if expected == audit['gate_state'] else '미탐/오탐',
            'mutation': {'before': before, 'after': after},
            'input_bundle_sha256': pipeline.canonical_json_digest(bundle),
            'output_snapshot': candidate['output_snapshots'][0]})
    scope = {'scope_id': 'details', 'kind': 'document', 'document_id': 'details'}
    for coverage in (None, 'partial', 'complete'):
        snapshots = [] if coverage is None else [{'document_id': 'details', 'version': '1',
            'content': '# Details\n', 'sha256': pipeline.digest_text('# Details\n'), 'coverage': coverage}]
        observed = organization.evaluate_destination_scope(scope, bundle, destination_snapshots=snapshots)
        expected = coverage == 'complete'
        rows.append({'case_id': 'N-06-destination-'+str(coverage), 'expected_allows_move': expected,
                     'actual': observed, 'analysis': '올바른 탐지' if observed['allows_confirmed_move']==expected else '미탐',
                     'input_destination_snapshots': snapshots, 'module': 'organization.evaluate_destination_scope'})
    # Real repair path: regenerate expression/reconstruction after a real generator exception.
    def broken(_):
        raise RuntimeError('controlled evaluation generator failure')
    broken_outcome = integration.run_pipeline(bundle, generator=broken)
    artifacts = dict(zip(repair_loop.STAGES, [broken_outcome['analysis'], broken_outcome['organization_plan'],
                    broken_outcome['expression_preview'], broken_outcome['revision_result']]))
    repairs = [('N-07-repeated', lambda r: {'candidate': r['artifacts']['expression']}, {}, 'REPEATED_STATE'),
               ('N-08-budget', repair_loop.DeterministicExpressionRepair(), {'budget_seconds': 1e-6}, 'BUDGET_EXHAUSTED'),
               ('N-09-attempt-limit', repair_loop.DeterministicExpressionRepair(), {'max_attempts': 0}, 'MAX_ATTEMPTS'),
               ('N-10-invalidate-revalidate', repair_loop.DeterministicExpressionRepair(), {}, 'VALIDATION_INCOMPLETE')]
    for cid, adapter, kwargs, expected in repairs:
        observed = repair_loop.RepairLoop(**kwargs).run(bundle, artifacts, adapters={'expression': adapter})
        rows.append({'case_id': cid, 'expected_termination': expected,
            'actual_termination': observed['termination_reason'], 'status': observed['status'],
            'attempt_count': len(observed['attempts']), 'delivery_approved': observed['delivery_approved'],
            'attempts': [{k: r[k] for k in ('target_module', 'invalidated', 'regenerated', 'judgment', 'termination_reason')}
                         for r in observed['attempts']], 'module': 'repair_loop.RepairLoop',
            'analysis': '올바른 탐지' if observed['termination_reason']==expected else '미해결'})
    partial = copy.deepcopy(result)
    partial['output_snapshots'][0]['coverage'] = 'partial'
    expression.seal(partial, 'revision_sha256')
    partial_audit = pipeline.validate_final_output(bundle, analysis, org, preview, partial)
    rows.append({'case_id': 'N-11-partial-output', 'expected_gate': 'FAIL',
        'actual_gate': partial_audit['gate_state'], 'analysis': '올바른 구조적 안전 차단',
        'mutation': {'output_snapshots/0/coverage': 'partial'},
        'evidence': partial_audit['structural_report']['findings']})
    partial_bundle = copy.deepcopy(bundle)
    partial_bundle['document_snapshot']['coverage'] = 'partial'
    stopped = integration.run_pipeline(partial_bundle)
    rows.append({'case_id': 'N-12-partial-source', 'expected_gate': 'STOPPED',
        'actual_gate': stopped['status'], 'delivery_approved': stopped['delivery_approved'],
        'analysis': '올바른 구조적 안전 차단',
        'mutation': {'document_snapshot/coverage': 'partial'}, 'evidence': stopped['controller']})
    broken_trace = dict(zip(repair_loop.STAGES, copy.deepcopy([analysis, org, preview, result])))
    broken_trace['reconstruction']['trace'][0]['unit_refs'] = ['unknown']
    expression.seal(broken_trace['reconstruction'], 'revision_sha256')
    def no_progress(request):
        candidate = copy.deepcopy(request['artifacts']['reconstruction'])
        candidate['trace'][0]['justification'] = 'Changed without fixing the invalid unit reference'
        expression.seal(candidate, 'revision_sha256')
        return {'candidate': candidate}
    no_progress_result = repair_loop.RepairLoop().run(bundle, broken_trace,
                         adapters={'reconstruction': no_progress})
    rows.append({'case_id': 'N-13-no-progress', 'expected_termination': 'NO_VERIFIED_PROGRESS',
        'actual_termination': no_progress_result['termination_reason'], 'status': no_progress_result['status'],
        'analysis': '올바른 진전 없음 종료', 'delivery_approved': no_progress_result['delivery_approved'],
        'mutation': {'trace/0/unit_refs': ['unknown'], 'adapter': 'change justification only'},
        'evidence': no_progress_result['attempts']})
    good = copy.deepcopy(analysis)
    broken_analysis = dict(zip(repair_loop.STAGES, copy.deepcopy([analysis, org, preview, result])))
    broken_analysis['analysis']['units'][0]['statement'] = ''
    expression.seal(broken_analysis['analysis'], 'analysis_sha256')
    repaired = repair_loop.RepairLoop().run(bundle, broken_analysis,
               adapters={'analysis': lambda request: {'candidate': good}})
    rows.append({'case_id': 'N-14-all-descendants-revalidated', 'expected_termination': 'VALIDATION_INCOMPLETE',
        'actual_termination': repaired['termination_reason'], 'status': repaired['status'],
        'analysis': '상위 오류 수정 후 전체 하위 재생성 및 의미 REVIEW 보존',
        'delivery_approved': repaired['delivery_approved'],
        'mutation': {'analysis/units/0/statement': '', 'adapter': 'restore original literal inventory'},
        'evidence': repaired['attempts']})
    # Supplied synthetic dependency: no relationship is inferred from gold labels.
    moved_bundle = integration.markdown_bundle('# 원본\n\n로컬 실행이 가능하다.\n\n캐시가 있을 때만 동작한다.\n', contract())
    moved_analysis = integration.analyze_source(moved_bundle)
    claim, condition = moved_analysis['units'][1:]
    condition['relations'] = [{'kind': 'qualifies', 'target_unit_id': claim['id'], 'reason': 'Controlled required cache condition'}]
    moved_bundle['writing_contract']['output_scopes'].append({'scope_id': 'details', 'document_id': 'details'})
    moved_analysis['contract_sha256'] = pipeline.canonical_json_digest(moved_bundle['writing_contract'])
    moved_analysis['input_sha256'] = pipeline.canonical_json_digest(moved_bundle)
    expression.seal(moved_analysis, 'analysis_sha256')
    destination = {'snapshot_id': 'details-v1', 'document_id': 'details', 'version': '1',
        'content': '# 목적지\n\n기존 문서 내용이다.\n', 'coverage': 'complete', 'media_type': 'text/markdown'}
    destination['sha256'] = pipeline.digest_text(destination['content'])
    for together in (False, True):
        unit_ids = [claim['id'], condition['id']] if together else [claim['id']]
        moved_org = organization.generate_organization_plan(moved_bundle, moved_analysis,
            candidate_actions={uid: {'action': 'MOVE', 'target_scope_id': 'details'} for uid in unit_ids},
            destination_snapshots=[destination])
        state, evidence = 'REJECTED_BEFORE_EXPRESSION', None
        try:
            moved_preview = expression.generate_revision_result(moved_bundle, moved_analysis, moved_org,
                             destination_snapshots=[destination])
            moved_result = reconstruction.reconstruct_documents(moved_bundle, moved_analysis, moved_org, moved_preview,
                             destination_snapshots=[destination])
            moved_audit = pipeline.validate_final_output(moved_bundle, moved_analysis, moved_org, moved_preview,
                             moved_result, destination_snapshots=[destination])
            state = moved_audit['gate_state']
            evidence = {'outputs': moved_result['output_snapshots'], 'audit': moved_audit}
        except ValueError:
            evidence = {'organization_validation': organization.validate_organization_plan(
                moved_bundle, moved_analysis, moved_org, destination_snapshots=[destination])}
        rows.append({'case_id': 'N-16-condition-atomic-move' if together else 'N-15-condition-split',
            'expected_gate': 'REVIEW' if together else 'REJECTED_BEFORE_EXPRESSION', 'actual_gate': state,
            'analysis': '조건 동반 이동은 의미 REVIEW; 조건 분리는 구조적 차단',
            'module': 'organization + expression + reconstruction + final validators',
            'mutation': {'move_condition_with_claim': together}, 'evidence': evidence})
    for index, row in enumerate(rows):
        row.setdefault('module', 'final_validator + final_semantic_validator + integration')
        row.setdefault('delivery_approved', False)
        row['input_location'] = 'evaluate.py:native_case/native_probes (controlled synthetic inputs)'
        row['output_evidence_pointer'] = '/cases/'+str(index)
        row['priority'] = 'P1' if row['case_id']=='N-06-destination-partial' else 'P2'
        row['fix_needed'] = ('Reject explicit incomplete destination coverage' if row['case_id']=='N-06-destination-partial'
                            else 'No confirmed defect in this bounded native probe')
        row['reproduce'] = 'python3 evaluation/core_pipeline_2026_11_11/evaluate.py native /tmp/native.json'
    return {'mode': 'deterministic_native_core_probes', 'real_model': 'not_run',
            'code_root': str(CORE), 'cases': rows}


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('predict'); p.add_argument('output', type=Path)
    p = sub.add_parser('compare'); p.add_argument('predictions', type=Path); p.add_argument('output', type=Path)
    p = sub.add_parser('native'); p.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'predict':
        write(args.output, run_predictions())
    elif args.command == 'compare':
        write(args.output, compare(read(args.predictions)))
    else:
        write(args.output, native_probes())


if __name__ == '__main__':
    main()
