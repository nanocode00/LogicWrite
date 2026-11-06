"""Experimental structural checks only. Not LogicWrite's adopted engine or schema."""
import argparse
import hashlib
import json
from pathlib import Path

VERSION = 'minimal-gate-spike-v2'
CHECKS = ('INPUT_CONTRACT', 'SNAPSHOT_INTEGRITY', 'SPAN_REFERENCES',
          'PROTECTED_LITERALS', 'SEMANTIC_REVIEW')
# Per-check implementation versions are distinct from the plan/report policy version.
CHECK_VERSIONS = {check_id: '1' for check_id in CHECKS}


def required_checks():
    return [{'check_id': key, 'check_version': CHECK_VERSIONS[key]} for key in CHECKS]


class InvalidInput(ValueError):
    def __init__(self, reason, evidence=None):
        super().__init__(reason)
        self.evidence = evidence or []


class UnsupportedProfile(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise InvalidInput(reason)


def object_fields(value, required, optional=()):
    require(isinstance(value, dict), 'Expected an object')
    require(set(required) <= value.keys(), 'Missing fields: ' + ', '.join(sorted(set(required) - value.keys())))
    unknown = value.keys() - set(required) - set(optional)
    if unknown:
        raise UnsupportedProfile('Unsupported fields: ' + ', '.join(sorted(unknown)))


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def contract_check(data):
    object_fields(data, ('contract', 'source', 'candidate', 'protected_literals'))
    contract = data['contract']
    object_fields(contract, ('audience', 'purpose', 'document_type', 'output_scopes'))
    for key in ('audience', 'purpose', 'document_type'):
        require(nonempty(contract[key]), 'Contract requires nonempty ' + key)
    scopes = contract['output_scopes']
    require(isinstance(scopes, list) and scopes, 'output_scopes must be nonempty')
    ids = []
    for scope in scopes:
        require(isinstance(scope, dict) and nonempty(scope.get('scope_id')), 'Missing scope_id')
        ids.append(scope['scope_id'])
    require(len(ids) == len(set(ids)), 'Duplicate scope_id')
    if len(scopes) != 1 or 'destination_role' in scopes[0]:
        raise UnsupportedProfile('Only one concrete document scope is supported; destination roles/groups need review')
    object_fields(scopes[0], ('scope_id', 'document_id'))
    require(nonempty(scopes[0]['document_id']), 'Missing document_id')
    require(isinstance(data['protected_literals'], list), 'protected_literals must be a list')


def snapshot_check(data):
    ids = []
    document = data['contract']['output_scopes'][0]['document_id']
    for key in ('source', 'candidate'):
        snap = data[key]
        object_fields(snap, ('id', 'document_id', 'content', 'sha256'))
        require(nonempty(snap['id']), 'Snapshot requires an id')
        require(snap['document_id'] == document, 'Snapshot document does not match scope')
        require(isinstance(snap['content'], str), 'Snapshot content must be text')
        actual = hashlib.sha256(snap['content'].encode('utf-8')).hexdigest()
        require(snap['sha256'] == actual, key + ' digest mismatch')
        ids.append(snap['id'])
    require(ids[0] != ids[1], 'Source and candidate need distinct snapshot ids')


def span_text(span, snap):
    object_fields(span, ('snapshot_id', 'start', 'end'))
    require(span['snapshot_id'] == snap['id'], 'Stale or unknown snapshot reference')
    start, end = span['start'], span['end']
    require(type(start) is int and type(end) is int, 'Offsets must be integer codepoints, not bool')
    require(0 <= start < end <= len(snap['content']), 'Invalid span bounds')
    return snap['content'][start:end]


def span_check(data):
    ids = []
    scope_id = data['contract']['output_scopes'][0]['scope_id']
    for literal in data['protected_literals']:
        object_fields(literal, ('id', 'scope_id', 'source_span', 'output_span'))
        require(nonempty(literal['id']), 'Protected literal requires id')
        ids.append(literal['id'])
        require(literal['scope_id'] == scope_id, 'Unknown scope reference')
        span_text(literal['source_span'], data['source'])
        span_text(literal['output_span'], data['candidate'])
    require(len(ids) == len(set(ids)), 'Duplicate protected literal id')


def literal_check(data):
    evidence = []
    for literal in data['protected_literals']:
        before = span_text(literal['source_span'], data['source'])
        after = span_text(literal['output_span'], data['candidate'])
        evidence.append({'literal_id': literal['id'], 'expected': before, 'actual': after,
                         'source_span': dict(literal['source_span']),
                         'output_span': dict(literal['output_span'])})
        if before != after:
            raise InvalidInput('Protected literal changed: ' + literal['id'], evidence)
    return evidence


def reconcile(required_checks, rows):
    """Reconcile internally executed checks. The CLI never accepts caller result rows."""
    expected = {}
    diagnostics = []
    if not required_checks:
        diagnostics.append('INVALID_PLAN')
    for check in required_checks:
        if not isinstance(check, dict) or not nonempty(check.get('check_id')):
            diagnostics.append('INVALID_PLAN')
            continue
        check_id = check['check_id']
        if check_id in expected or not nonempty(check.get('check_version')):
            diagnostics.append('INVALID_PLAN')
        expected[check_id] = check.get('check_version')
    ids = [row.get('check_id') for row in rows]
    failed = any(row.get('status') == 'violated' for row in rows)
    if len(set(ids)) != len(ids) or set(ids) - expected.keys():
        diagnostics.append('REPORT_INTEGRITY_ERROR')
    for row in rows:
        check_id = row.get('check_id')
        if check_id in expected:
            if not nonempty(row.get('check_version')):
                diagnostics.append('CHECK_VERSION_MISSING: ' + check_id)
            elif row['check_version'] != expected[check_id]:
                diagnostics.append('CHECK_VERSION_MISMATCH: ' + check_id)
    if any(row.get('status') not in {'passed', 'violated', 'unresolved', 'not_run', 'execution_error'} for row in rows):
        diagnostics.append('REPORT_INTEGRITY_ERROR')
    failed = failed or bool(diagnostics)
    missing = sorted(expected.keys() - set(ids))
    if missing:
        diagnostics.append('CHECK_RESULT_MISSING: ' + ', '.join(missing))
    stopped = bool(missing) or any(row.get('status') == 'execution_error' for row in rows)
    if stopped:
        state = 'STOPPED'
    elif failed:
        state = 'FAIL'
    elif any(row['status'] != 'passed' for row in rows):
        state = 'REVIEW'
    else:
        state = 'PASS'
    return {'gate_state': state, 'execution_state': 'stopped' if stopped else 'completed',
            'last_gate_state': 'FAIL' if stopped and failed else None,
            'diagnostics': diagnostics, 'delivery_approved': False}


def evaluate(data):
    rows = []
    blocked = None
    for check_id, validator in zip(CHECKS[:-1], (contract_check, snapshot_check, span_check, literal_check)):
        status, reason = 'passed', 'Supported structural check passed'
        evidence = []
        if blocked:
            status, reason = 'not_run', 'Dependency unavailable: ' + blocked
        else:
            try:
                evidence = validator(data) or []
            except UnsupportedProfile as error:
                status, reason = 'unresolved', 'UNSUPPORTED_PROFILE: ' + str(error)
                blocked = check_id
            except (InvalidInput, UnicodeError) as error:
                status, reason = 'violated', str(error)
                evidence = getattr(error, 'evidence', [])
                blocked = check_id
            except Exception as error:
                status, reason = 'execution_error', type(error).__name__ + ': ' + str(error)
                blocked = check_id
        rows.append({'check_id': check_id, 'check_version': CHECK_VERSIONS[check_id], 'status': status, 'reason': reason, 'evidence': evidence})
    rows.append({'check_id': 'SEMANTIC_REVIEW', 'check_version': CHECK_VERSIONS['SEMANTIC_REVIEW'], 'status': 'not_run',
                 'reason': 'Awaiting human semantic review; no semantic engine is implemented'})
    report = reconcile(required_checks(), rows)
    # This canonicalization is an experimental choice, not the shared model's adopted digest policy.
    input_digest = hashlib.sha256(json.dumps(data, ensure_ascii=True, sort_keys=True,
                                            separators=(',', ':')).encode('ascii')).hexdigest()
    report.update({'input_digest': input_digest, 'record_kind': 'experimental_gate_report_not_adopted_schema',
                   'plan': {'version': VERSION, 'boundary': 'single_document_structural_spike',
                            'required_checks': required_checks()}, 'check_results': rows})
    return report


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def reject_constant(value):
    raise InvalidInput('Non-JSON numeric constant: ' + value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    try:
        # Read bytes to avoid universal-newline normalization of source text.
        data = json.loads(args.input.read_bytes().decode('utf-8'),
                          object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (UnicodeError, ValueError) as error:
        report = evaluate(None)
        report['diagnostics'].append('INVALID_INPUT: ' + str(error))
    except RecursionError as error:
        report = reconcile(required_checks(), [])
        report['diagnostics'].append('INPUT_PARSE_ERROR: ' + str(error))
    except OSError as error:
        report = reconcile(required_checks(), [])
        report['diagnostics'].append('INPUT_READ_ERROR: ' + str(error))
    else:
        report = evaluate(data)
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
