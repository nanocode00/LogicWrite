"""Versioned document-set admission and permission foundation, not a G2 executor.

Callers retain the trusted contract digest independently of candidate/model data.
A digest authenticates only that supplied baseline; it does not establish external
truth, genuine user authority, semantic quality or approval. No file paths in an
input are opened. This module neither generates documents nor applies files.
"""
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath

import jsonschema

VERSION = 'core-document-set-v1'
_SCHEMA = json.loads(Path(__file__).with_name('document-set-v1.schema.json').read_text())
_VALIDATOR = jsonschema.Draft202012Validator(_SCHEMA)


def contract_digest(contract):
    """Canonical UTF-8 identity; caller must pin it before untrusted execution."""
    return hashlib.sha256(json.dumps(contract,ensure_ascii=False,sort_keys=True,
        separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()


def _digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _boundary():
    return {'gate_state':'REVIEW','semantic_judgment':'unresolved',
            'execution_state':'not_run','b2_reconstruction_success':False,
            'delivery_approved':False,'stage_transition_allowed':False}


def validate_contract(contract, *, expected_sha256=None):
    """Validate structure/bindings. Pending context is REVIEW, never semantic PASS.

    Unpinned admission can describe an input but cannot authorize operations.
    Provenance validates internal identity, not the truth of source assertions.
    """
    report = dict(_boundary(),version=VERSION,structural_input_valid=False,
                  ready_for_planning=False,contract_sha256=None,baseline_pinned=False,reasons=[])
    reasons=report['reasons']
    try:
        contract=copy.deepcopy(contract)
        if list(_VALIDATOR.iter_errors(contract)):
            reasons.append('DOCUMENT_SET_SCHEMA_INVALID')
        else:
            report['contract_sha256']=contract_digest(contract)
            if expected_sha256 is not None:
                if expected_sha256 != report['contract_sha256']:
                    reasons.append('TRUSTED_CONTRACT_MISMATCH')
                else:
                    report['baseline_pinned']=True
            docs=contract['documents']
            ids=[d['document_id'] for d in docs]
            paths=[d['provenance']['path'] for d in docs]
            if len(ids)!=len(set(ids)): reasons.append('DUPLICATE_DOCUMENT_ID')
            if len(paths)!=len(set(paths)): reasons.append('DUPLICATE_SOURCE_PATH')
            for doc in docs:
                p=doc['provenance']; path=p['path']
                if (path.startswith('/') or '\\' in path or any(c in path for c in ('\x00','\n','\r'))
                        or str(PurePosixPath(path))!=path or '..' in path.split('/')):
                    reasons.append('INVALID_SOURCE_PATH')
                if _digest(doc['content'])!=doc['sha256']:
                    reasons.append('SOURCE_SHA256_MISMATCH')
                if p['snapshot_sha256']!=doc['sha256'] or p['source_id']!=contract['origin']['source_id']:
                    reasons.append('SOURCE_PROVENANCE_MISMATCH')
                if doc['output_target'] and doc['access'] not in {'edit','format_only'}:
                    reasons.append('OUTPUT_ACCESS_MISMATCH')
                if doc['completeness']=='excerpt' and not doc['source_scope']:
                    reasons.append('EXCERPT_SCOPE_MISSING')
            scopes=contract['output_scopes']
            scoped_ids=[s['document_id'] for s in scopes]
            scope_ids=[s['scope_id'] for s in scopes]
            if len(scoped_ids)!=len(set(scoped_ids)) or len(scope_ids)!=len(set(scope_ids)):
                reasons.append('DUPLICATE_OUTPUT_SCOPE')
            if set(scoped_ids)!={d['document_id'] for d in docs if d['output_target']}:
                reasons.append('OUTPUT_SCOPE_SET_MISMATCH')
        if reasons:
            report['gate_state']='FAIL'
            return report
        report['structural_input_valid']=True
        holds=[]
        if contract['document_set_completeness']!='complete': holds.append('INCOMPLETE_DOCUMENT_SET')
        if contract['context'] is None: holds.append('UNKNOWN_CONTEXT')
        for doc in contract['documents']:
            if doc['completeness']!='complete': holds.append('INCOMPLETE_DOCUMENT')
            if doc['access']=='pending': holds.append('PENDING_ACCESS')
            if doc['role'] is None or doc['authority'] is None: holds.append('UNKNOWN_DOCUMENT_CONTEXT')
            if doc['pending_questions']: holds.append('PENDING_DOCUMENT_PERMISSION_OR_CONTEXT')
        # Global questions remain explicit context, not invented revocations of
        # otherwise complete, declared per-document grants.
        report['reasons']=sorted(set(holds))
        report['ready_for_planning']=not holds
    except (TypeError,ValueError,KeyError,UnicodeError,OverflowError):
        report.update(gate_state='FAIL',reasons=['DOCUMENT_SET_INVALID'])
    return report


def _pinned_validation(contract, pin):
    report=validate_contract(contract,expected_sha256=pin)
    if pin is None:
        report.update(structural_input_valid=False,ready_for_planning=False,
                      gate_state='FAIL',reasons=['TRUSTED_CONTRACT_REQUIRED'])
    return report


def check_operation(contract, document_id, operation, *, trusted_contract_sha256):
    """Eligibility only. Explicit operations avoid inferring permission from prose."""
    report=_pinned_validation(contract,trusted_contract_sha256)
    result=dict(_boundary(),status='denied',execution_allowed=False,reasons=report['reasons'])
    if not report['structural_input_valid']: return result
    if not isinstance(operation,str) or operation not in {'reference','edit_content','format'}:
        result.update(status='unsupported',reasons=['SEPARATE_OPERATION_AUTHORIZATION_REQUIRED'])
        return result
    doc=next((d for d in contract['documents'] if d['document_id']==document_id),None)
    if doc is None:
        result['reasons']=['UNKNOWN_DOCUMENT_ID']; return result
    if not report['ready_for_planning']:
        result['status']='held';return result
    eligible=(operation=='reference' or (doc['output_target'] and
        (doc['access']=='edit' or (doc['access']=='format_only' and operation=='format'))))
    result.update(status='eligible' if eligible else 'denied',
                  reasons=[] if eligible else ['DOCUMENT_ACCESS_DENIED'])
    return result


def validate_candidates(contract, candidates, *, trusted_contract_sha256):
    """Check external full candidate coverage and declared access, without G3 claims.

    Output rows contain document_id/source_sha256/source_path/content/sha256 only.
    read_only docs are evidence, never output targets. Changed format_only content
    is always unresolved until an independently specified formatting policy exists.
    Edit permission does not prove constraints, meaning or reader-task quality.
    """
    admission=_pinned_validation(contract,trusted_contract_sha256)
    result=dict(_boundary(),version='document-set-candidate-check-v1',
                permission_status='unresolved',reasons=list(admission['reasons']),
                candidate_sha256=None,contract_sha256=admission['contract_sha256'])
    if not admission['structural_input_valid']:
        result.update(gate_state='FAIL',permission_status='denied');return result
    errors=[];holds=[]
    try:
        if not isinstance(candidates,list): raise ValueError('candidate list required')
        ids=[];docs={d['document_id']:d for d in contract['documents']}
        for row in candidates:
            if not isinstance(row,dict) or set(row)!={'document_id','source_sha256','source_path','content','sha256'}:
                raise ValueError('invalid candidate fields')
            if not all(isinstance(v,str) for v in row.values()): raise ValueError('invalid candidate values')
            ids.append(row['document_id']); doc=docs.get(row['document_id'])
            if doc is None or not doc['output_target']:
                errors.append('UNAUTHORIZED_OUTPUT_DOCUMENT');continue
            if row['source_sha256']!=doc['sha256'] or row['source_path']!=doc['provenance']['path']:
                errors.append('CANDIDATE_SOURCE_MISMATCH')
            if _digest(row['content'])!=row['sha256']:
                errors.append('CANDIDATE_SHA256_MISMATCH')
            if doc['access']=='format_only' and row['content']!=doc['content']:
                holds.append('FORMAT_CHANGE_REQUIRES_REVIEW')
        if len(ids)!=len(set(ids)):errors.append('DUPLICATE_CANDIDATE_DOCUMENT_ID')
        if set(ids)!={d['document_id'] for d in contract['documents'] if d['output_target']}:
            errors.append('CANDIDATE_OUTPUT_SET_MISMATCH')
        result['candidate_sha256']=contract_digest(candidates)
    except (TypeError,ValueError,KeyError,UnicodeError,OverflowError):
        errors.append('INVALID_CANDIDATE_INPUT')
    result['reasons']=sorted(set(result['reasons']+errors+holds))
    if errors:
        result.update(gate_state='FAIL',permission_status='denied')
    elif admission['ready_for_planning'] and not holds:
        result['permission_status']='within_declared_access'
    return result


def prepare_reconstruction(contract, *, trusted_contract_sha256):
    """Explicit G2 boundary; no legacy executor delegation or candidate emission."""
    return dict(_boundary(),status='unsupported',
        reason='DOCUMENT_SET_RECONSTRUCTION_NOT_IMPLEMENTED',
        admission=_pinned_validation(contract,trusted_contract_sha256))
