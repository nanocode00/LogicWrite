"""Run: python3 experiments/full_document_control/repair_example.py

Offline generation failure -> deterministic repair -> reconstruction -> full audit.
This synthetic example is not a gold-set evaluation or delivery authorization.
"""
import json
import integration
from repair_loop import DeterministicExpressionRepair, run_repair_pipeline


def main():
    contract = {'contract_id': 'repair-demo', 'version': '1', 'document_type': 'guide',
        'audience': 'developers', 'purpose': 'installation', 'language': 'ko', 'register': '한다체',
        'output_scopes': [{'scope_id': 'guide', 'document_id': 'demo'}],
        'required_information': [], 'constraints': []}
    bundle = integration.markdown_bundle('# 설치\n\n기본 제한 시간은 30초다.\n', contract)
    def failing_generator(_):
        raise RuntimeError('synthetic failure')
    result = run_repair_pipeline(bundle, generator=failing_generator,
        adapters={'expression': DeterministicExpressionRepair()})
    print(json.dumps({'status': result['status'], 'termination_reason': result['termination_reason'],
        'attempts': len(result['attempts']), 'delivery_approved': result['delivery_approved'],
        'stage_transition_allowed': result['stage_transition_allowed'],
        'regenerated': result['attempts'][0]['regenerated']}, indent=2))
    return 0 if result['termination_reason'] == 'CANDIDATE_VALIDATED' and not result['delivery_approved'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
