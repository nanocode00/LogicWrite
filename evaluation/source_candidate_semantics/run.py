#!/usr/bin/env python3
"""Materialize input-only evaluations before loading frozen development labels."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORE = ROOT/'experiments/full_document_control'
sys.path.insert(0, str(CORE))
import pipeline
import source_candidate_adapter as adapter
import final_semantic_validator as semantic

INPUTS = ROOT/'evaluation/semantic_pilot/inputs'
GOLD = ROOT/'evaluation/g3_g4/development_gold_v2_2026-11-11/development-gold.json'
IDS = {f'SP-{i:03}' for i in range(1, 13)}


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seal(value):
    value['record_sha256'] = pipeline.canonical_json_digest(value)
    return value


def predict(case_ids, *, reviewer=None, max_review_chars=48000, timeout_seconds=30):
    if not case_ids or len(set(case_ids)) != len(case_ids) or not set(case_ids) <= IDS:
        raise ValueError('Unique active G3 SP-001–012 IDs only; provisional review is separate')
    rows = []
    for cid in case_ids:
        path = INPUTS/(cid+'.json')
        raw = read(path)
        skipped = isinstance(reviewer, CliReviewer) and (
            reviewer.stopped or len(reviewer.attempts) >= reviewer.max_calls)
        result = adapter.evaluate(raw, reviewer=None if skipped else reviewer, max_review_chars=max_review_chars,
                                  timeout_seconds=timeout_seconds)
        if skipped:
            result['reasons'].append('PROVIDER_NOT_ATTEMPTED_CALL_BUDGET_OR_PREVIOUS_FAILURE')
        rows.append({'case_id': cid, 'input_path': str(path.relative_to(ROOT)),
                     'input_sha256': sha(path), 'result': result})
    return seal({'version': 'source-candidate-evaluation-run-v1', 'reference_labels_loaded': False,
                 'evidence_trust': dict(semantic.EVALUATION_EVIDENCE_TRUST),
                 'dataset_role': 'development_only', 'cases': rows})


def compare(predictions):
    body = {k: v for k, v in predictions.items() if k != 'record_sha256'}
    if predictions.get('record_sha256') != pipeline.canonical_json_digest(body):
        raise ValueError('Prediction record was altered')
    gold = read(GOLD)  # Reference data enters only this post-evaluation function.
    refs = {r['case_id']: r for r in gold['cases']}
    rows, excluded, eligible = [], [], []
    reviewed_count = 0
    ids = [p['case_id'] for p in predictions['cases']]
    if len(set(ids)) != len(ids) or not set(ids) <= IDS:
        raise ValueError('Invalid prediction inventory')
    for pos, row in enumerate(predictions['cases']):
        cid = row['case_id']
        expected_path = INPUTS/(cid+'.json')
        if (row['input_path'] != str(expected_path.relative_to(ROOT))
                or row['input_sha256'] != sha(expected_path)
                or row['input_sha256'] != refs[cid]['input_sha256']):
            raise ValueError('Frozen reference / actual evaluated input binding mismatch')
        result = row['result']
        raw = read(expected_path)
        if result.get('input_sha256') != pipeline.canonical_json_digest(raw):
            raise ValueError('Semantic result does not bind the actual input')
        if result.get('delivery_approved') is not False or result.get('stage_transition_allowed') is not False:
            raise ValueError('Evaluation cannot grant approval')
        judgment = result.get('semantic_judgment')
        classified = {'supported': 'PRESERVED', 'contradicted': 'VIOLATION'}.get(judgment)
        # REVIEW is an approval boundary, never an SP classification.
        include = result.get('evaluated') is True and classified is not None
        report = result.get('semantic_report') or {}
        reviewed = report.get('execution', {}).get('state') == 'completed'
        violation = False
        if result.get('evaluated') is True or reviewed or judgment in {'supported', 'contradicted'} or result.get('violation_confirmed'):
            report = result.get('semantic_report') or {}
            body = {k: v for k, v in report.items() if k != 'report_sha256'}
            coverage, execution = report.get('coverage', {}), report.get('execution', {})
            checks = report.get('checks', {})
            snapshots = {(side, d['document_id']): d for side, key in
                         [('source','source_documents'), ('output','candidate_documents')] for d in raw[key]}
            response = {'request_sha256': execution.get('request_sha256'),
                        'reviews': [checks[c].get('model_review') for c in semantic.CHECKS if c in checks]}
            request = {'request_sha256': execution.get('request_sha256'),
                       'snapshot_refs': report.get('snapshot_refs', [])}
            try:
                reviews, state = semantic._validate_reviews(response, request, snapshots)
            except (TypeError, KeyError, ValueError, AttributeError):
                reviews, state = {}, 'invalid'
            # Rebuild only the request from the actual input, with NO reviewer.
            # References never enter this preparation and no model is called.
            prepared = adapter.evaluate(raw)['semantic_report'] or {}
            expected_request = prepared.get('execution', {}).get('request_sha256')
            definitive = state == 'completed' and all(r['judgment'] != 'unresolved' for r in reviews.values())
            violation = state == 'completed' and any(r['judgment'] in {'contradicted','overstated'} for r in reviews.values())
            derived = 'contradicted' if violation else ('supported' if definitive else 'unresolved')
            expected_statuses = {key: ('violated' if row['judgment'] in {'contradicted','overstated'}
                                      else row['judgment']) for key, row in reviews.items()}
            if (report.get('report_sha256') != pipeline.canonical_json_digest(body)
                    or report.get('version') != 'source-candidate-semantic-evaluation-v1'
                    or report.get('delivery_approved') is not False
                    or report.get('stage_transition_allowed') is not False
                    or execution.get('state') != 'completed' or not execution.get('request_sha256')
                    or execution['request_sha256'] != expected_request
                    or report.get('snapshot_refs') != prepared.get('snapshot_refs')
                    or coverage.get('complete') is not definitive
                    or set(coverage.get('reviewed_checks', [])) != set(semantic.CHECKS)
                    or state != 'completed'
                    or any(checks[key].get('status') != value for key, value in expected_statuses.items())
                    or judgment != derived or judgment != report.get('overall_judgment')
                    or report.get('gate_state') != ('FAIL' if derived == 'contradicted' else 'REVIEW')
                    or result.get('gate_state') != report.get('gate_state')
                    or result.get('evaluated') is not definitive):
                raise ValueError('Semantic verdict requires a valid, cited seven-check review')
            # New fields are additive; old definitive records need no migration.
            for obj, key, expected in [(coverage, 'all_checks_reviewed', True),
                    (coverage, 'all_judgments_definitive', definitive),
                    (report, 'violation_confirmed', violation),
                    (result, 'all_checks_reviewed', True),
                    (result, 'all_judgments_definitive', definitive),
                    (result, 'violation_confirmed', violation)]:
                if key in obj and obj[key] is not expected:
                    raise ValueError('Semantic state flags contradict the validated review')
            reviewed_count += 1
        summary = {'case_id': cid, 'expected': refs[cid]['user_final_judgment'],
                   'actual': classified if include else None, 'included_in_metric': include,
                   'observed_classification': classified if reviewed else None,
                   'violation_confirmed': violation, 'all_checks_reviewed': reviewed,
                   'prediction_pointer': f'/cases/{pos}/result',
                   'input_path': row['input_path'], 'input_sha256': row['input_sha256'],
                   'reference_pointer': '/cases/'+str(gold['cases'].index(refs[cid])),
                   'reasons': result.get('reasons', []),
                   'reproduce': f'python3 evaluation/source_candidate_semantics/run.py predict /tmp/{cid}.json --case {cid}',
                   'priority': 'P2', 'followup': 'Supply missing context or execute a cited full-context model review'}
        rows.append(summary)
        if include:
            eligible.append(summary)
        else:
            excluded.append({'case_id': cid, 'reasons': result.get('reasons', []),
                             'semantic_judgment': judgment, 'violation_confirmed': violation})
    return {'version': 'source-candidate-post-comparison-v1', 'dataset_role': 'development_only',
            'reference_manifest_path': str(GOLD.relative_to(ROOT)), 'reference_manifest_sha256': sha(GOLD),
            'prediction_record_sha256': predictions['record_sha256'],
            'metric_scope': 'complete definitive model-advisory evaluations only; excludes unsupported/abstentions',
            'gate_state_is_not_an_sp_label': True, 'candidate_count': len(rows),
            'evidence_trust': dict(semantic.EVALUATION_EVIDENCE_TRUST),
            'reviewed_case_count': reviewed_count,
            'confirmed_violation_count': sum(r['violation_confirmed'] for r in rows),
            'evaluated_count': len(eligible), 'excluded': excluded,
            'accuracy': sum(r['actual'] == r['expected'] for r in eligible)/len(eligible) if eligible else None,
            'cases': rows}


class CliReviewer:
    """Bounded existing CLI transport; failures stop subsequent external calls."""
    def __init__(self, executable, model, max_calls=1, timeout=30):
        if not 1 <= max_calls <= 4 or timeout <= 0:
            raise ValueError('A pilot allows 1–4 calls and a positive timeout')
        self.executable, self.model = executable, model
        self.max_calls, self.timeout = max_calls, timeout
        self.attempts = []
        self.stopped = False

    def __call__(self, request):
        if self.stopped or len(self.attempts) >= self.max_calls:
            raise RuntimeError('Provider pilot stopped or call budget exhausted')
        prompt = ('Return only the requested JSON object, no Markdown. Do not use tools or edit files.\n'
                  + json.dumps(request, ensure_ascii=False))
        observation = pipeline.call_cli_provider(prompt, executable=self.executable,
                                                  model=self.model, timeout=self.timeout)
        raw = observation['stdout']
        error_bytes = observation['stderr']
        error_text = error_bytes.decode('utf-8', errors='replace') if isinstance(error_bytes, bytes) else error_bytes
        quota = any(t in error_text for t in ('RESOURCE_EXHAUSTED', '429', 'quota'))
        self.attempts.append({'requested_model': self.model, 'request_sha256': request.get('request_sha256'),
                             'request_characters': len(prompt), 'seconds': observation['seconds'],
                             'returncode': observation['returncode'], 'timed_out': observation['timed_out'],
                             'error_class': 'quota_exhausted' if quota else
                                 ('provider_failure' if observation['returncode'] != 0 else None),
                             'stdout_sha256': hashlib.sha256(raw).hexdigest(),
                             'token_usage': None, 'billed_cost': None})
        if observation['timed_out'] or observation['returncode'] != 0:
            self.stopped = True
            raise RuntimeError('Provider call failed; see bounded attempt metadata')
        try:
            return pipeline.load_json_bytes(raw)
        except (ValueError, TypeError):
            self.stopped = True
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('predict')
    p.add_argument('output', type=Path)
    p.add_argument('--case', action='append', dest='cases')
    p.add_argument('--provider', choices=('offline', 'agy'), default='offline')
    p.add_argument('--model')
    p.add_argument('--max-calls', type=int, default=1)
    p.add_argument('--max-review-chars', type=int, default=48000)
    p.add_argument('--timeout', type=int, default=30)
    p = sub.add_parser('compare')
    p.add_argument('predictions', type=Path)
    p.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'compare':
        result = compare(read(args.predictions))
    else:
        reviewer = None
        if args.provider == 'agy':
            if not args.model:
                parser.error('--model is required for a live provider; no implicit model choice')
            reviewer = CliReviewer('/home/honorbear/.local/bin/agy', args.model, args.max_calls, args.timeout)
        result = predict(args.cases or sorted(IDS), reviewer=reviewer,
                         max_review_chars=args.max_review_chars,
                         timeout_seconds=args.timeout+20 if reviewer else args.timeout)
        if reviewer:
            result.pop('record_sha256')
            result['provider_attempts'] = reviewer.attempts
            result['provider_policy'] = {'max_calls': args.max_calls, 'retry': False,
                'stop_on_failure': True, 'requested_model': args.model, 'served_model_verified': False,
                'cost_policy': 'Token usage and billed cost unavailable unless supplied by the provider; no inferred dollar cost'}
            seal(result)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
