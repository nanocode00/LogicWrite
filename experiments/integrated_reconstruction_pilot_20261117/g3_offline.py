"""Read-only G3 shadow of frozen Qwen candidates plus isolated G2-C examples."""
import argparse
import hashlib
import json
from pathlib import Path

from g2_c_offline import ROOT, _read, _synthetic, build_record
import document_set as core
import document_set_analysis as analysis
import document_set_planning as planning
import document_set_reconstruction as reconstruction
import document_set_verification as g3
from document_set_final_validator import candidate_row
from ir_document_set_adapter import from_ir_input

HERE = Path(__file__).resolve().parent
QWEN = HERE / 'qwen-comparison-20261117'


def _ref(document_id, quote, **context):
    return dict(document_id=document_id, quote=quote, context=context)


def _requirements(name):
    def obligation(check_id, kind, refs, targets, owner, decision):
        return dict(check_id=check_id, kind=kind, source_refs=refs, document_ids=targets,
                    task_ids=[], decision_owner=owner, decision_needed=decision)

    rules = []
    if name == 'IR-001':
        rules.append(obligation('funding-policy', 'policy_relation', [
            _ref('readme', '기부는 [후원 안내](FUNDING.md)에서 할 수 있습니다.', applicability='README 첫 방문자'),
            _ref('funding', '금전 후원은 받지 않습니다. 대신 테스트 결과와 오류 제보를 환영합니다.',
                 applicability='금전 후원 및 비금전 참여'),
        ], ['readme'], '프로젝트 후원 정책 권한자',
            'README와 후원 안내의 적용 범위 및 현재 안내할 정책을 확인한다.'))
    if name == 'IR-002':
        refs = [_ref('adr', '대기 건수가 500건을 넘으면 신규 배치를 중단한다. 당직자가 확인하기 전에는 재개하지 않는다.',
                     date='2026-11-12부터', applicability='운영 배치 중단 및 재개')]
        rules.extend([
            obligation('operator-exact-condition', 'exact_line', refs, ['ops'], '운영 정책 권한자',
                       '운영서에 승인된 중단 및 재개 문장을 현지 노출한다.'),
            obligation('operator-meaning', 'semantic', refs, ['ops'], '운영 정책 권한자',
                       '교대자가 운영서에서 중단·재개 조건을 확인할 수 있는지 검토한다.'),
            obligation('retry-policy-scope', 'semantic', [
                _ref('adr', '2026-11-11까지는 운영 환경도 30초였다. 과거 기록의 수치를 소급 변경하지 않는다.',
                     date='2026-11-11까지', applicability='이전 운영 환경'),
                _ref('adr', '외부 API 제한 때문에 운영 환경의 실패 재시도 간격은 60초로 한다. 개발 환경은 30초를 유지한다.',
                     date='2026-11-12부터', applicability='현행 운영 환경과 개발 환경'),
                _ref('weekly', '11월 11일까지 운영 재시도 간격은 30초였다. 12일부터 60초 정책을 적용했다.',
                     date='2026-11-09~11-12', applicability='정책 적용 시점이 혼합된 관찰 기간'),
            ], ['design', 'ops'], '운영 정책 권한자', '현행 정책·개발 범위와 과거 관찰의 귀속을 검토한다.'),
        ])
    return dict(version=g3.REQUIREMENTS, obligations=rules, format_policies={})


def _planning_inputs(name, contract):
    pin = core.contract_digest(contract)
    artifact = analysis.analyze_document_set(contract, trusted_contract_sha256=pin)
    proposals = []
    if name == 'IR-001':
        for task_id, did, prefix in [
            ('retain-funding-statement', 'readme', '기부는'),
            ('retain-output-description', 'usage', '출력은 JSON이다.'),
        ]:
            uid = next(u['unit_id'] for u in artifact['units']
                       if u['document_id'] == did and u['quote'].startswith(prefix))
            proposals.append(dict(task_id=task_id, action='KEEP', unit_ids=[uid], target_document_id=did,
                                  reason='Shadow impact probe for source preservation',
                                  evidence_unit_ids=[uid], depends_on=[], parameters={}))
    request = planning.make_request(proposals)
    request_pin = core.contract_digest(request)
    plan = planning.plan_document_set(contract, artifact, request, trusted_contract_sha256=pin,
                                      trusted_request_sha256=request_pin)
    grant = reconstruction.make_candidate_request(plan, task_ids=[
        row['task_id'] for row in plan['tasks'] if row['status'] == 'eligible'],
        document_ids=[s['document_id'] for s in contract['output_scopes']])
    return dict(contract=contract, analysis=artifact, plan=plan, plan_request=request, candidate_request=grant,
                trusted_contract_sha256=pin, trusted_request_sha256=request_pin,
                trusted_candidate_request_sha256=core.contract_digest(grant))


def _mapped_claim(name, variant, raw):
    # Explicit human-readable mapping of historical, heterogeneous claim fields.
    # Kept with the artifact evidence, outside Core and the requirements contract.
    checks = raw['final_checks']
    if (name, variant) == ('IR-002', 'B0'):
        claim = checks[1]
        if '500건 초과 시 신규 배치 중단' in claim and '운영서에 명확히 기재' in claim:
            return '/final_checks/1', claim, 'operator-exact-condition'
    if (name, variant) == ('IR-002', 'B1'):
        claim = checks['constraints_compliance']['contact_and_stop_condition_accessible']
        if claim is True:
            return '/final_checks/constraints_compliance/contact_and_stop_condition_accessible', claim, 'operator-exact-condition'
    if (name, variant) == ('IR-003', 'B1'):
        claim = checks[1]
        if claim['status'] == 'within_authority':
            return '/final_checks/1', claim, 'authority:meeting'
    return None


def _verify(result, requirements, inputs, mode):
    report = g3.verify_document_set(
        result, requirements, **inputs, mode=mode,
        trusted_candidate_sha256=core.contract_digest(result),
        trusted_requirements_sha256=core.contract_digest(requirements))
    if not report['accepted']:
        raise ValueError(report['reasons'])
    return report


def build_results():
    frozen = _read(QWEN / 'artifact-manifest.json')['files']
    records = {}
    for number in (1, 2, 3):
        name = f'IR-{number:03}'
        path = ROOT / 'evaluation/integrated_reconstruction/inputs' / (name + '.json')
        contract = from_ir_input(_read(path))
        inputs = _planning_inputs(name, contract)
        docs = {row['document_id']: row for row in contract['documents']}
        requirements = _requirements(name)
        for variant in ('B0', 'B1'):
            relative = f'evaluation/{name}/{variant}/candidate.json'
            payload = (QWEN / relative).read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            if digest != frozen[relative]:
                raise ValueError(f'Frozen candidate hash mismatch for {relative}')
            raw = json.loads(payload)
            result = dict(candidates=[candidate_row(docs[row['document_id']], row['content'])
                                      for row in raw['documents']], final_checks=raw['final_checks'],
                          raw_candidate_sha256=digest)
            mapped = _mapped_claim(name, variant, raw)
            if mapped:
                pointer, claim, check_id = mapped
                result['self_review'] = {check_id: 'passed'}
                result['claim_mapping'] = dict(raw_pointer=pointer, raw_claim=claim, check_id=check_id)
            report = _verify(result, requirements, inputs, 'external_shadow')
            if report['checks']['lineage']['status'] != 'unresolved':
                raise ValueError('External candidate unexpectedly has G2-C lineage')
            if mapped and not any(c['field'] == 'self_review' and c['status'] == 'violated'
                                  for c in report['self_checks']):
                raise ValueError('Mapped success claim was not contradicted')
            records[f'{name}-{variant}'] = dict(frozen_candidate=relative, raw_candidate_sha256=digest,
                                               plan=inputs['plan'], claim_mapping=result.get('claim_mapping'),
                                               requirements=requirements, verification=report)
    for case in ('synthetic-move', 'synthetic-partial'):
        record = build_record(case, _synthetic(case.endswith('partial')))
        report = _verify(record['result'], _requirements(case), record['inputs'], 'g2c')
        if report['checks']['lineage']['status'] != 'passed':
            raise ValueError('Expected genuine G2-C lineage')
        records[case] = dict(verification=report)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    records = build_results()
    args.output.mkdir(parents=True, exist_ok=False)
    for key, record in records.items():
        (args.output / (key + '.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n',
                                                 encoding='utf-8')


if __name__ == '__main__':
    main()
