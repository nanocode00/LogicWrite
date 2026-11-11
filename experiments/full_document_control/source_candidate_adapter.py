"""SP input-only, evaluation-only bridge; no gold files or approval authority."""
import copy
import hashlib
import json
import re
from pathlib import Path

import jsonschema
import final_semantic_validator as semantic

SCHEMA = Path(__file__).resolve().parents[2] / 'evaluation/semantic_pilot/input.schema.json'
VERSION = 'sp-source-candidate-adapter-v1'


def evaluate(raw, reviewer=None, max_review_chars=48000, timeout_seconds=30):
    """Return an advisory evaluation only for explicit complete, bound SP pairs.

    Missing metadata is unsupported; schema violations including answer/gold fields
    are invalid input. No filesystem paths supplied in the input are opened.
    """
    result = {'version':VERSION, 'status':'unsupported','gate_state':'REVIEW',
        'semantic_judgment':'unresolved','evaluated':False,'reasons':[],
        'semantic_report':None,'contract_mapping':{},'input_sha256':None,
        'all_checks_reviewed':False, 'all_judgments_definitive':False,
        'violation_confirmed':False, 'model_execution_state':'not_run',
        'evidence_trust':copy.deepcopy(semantic.EVALUATION_EVIDENCE_TRUST),
        'delivery_approved':False,'stage_transition_allowed':False}
    try:
        raw = copy.deepcopy(raw)
        result['input_sha256'] = semantic.pipeline.canonical_json_digest(raw)
        schema = json.loads(SCHEMA.read_text())
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(raw))
        if errors:
            # Absence of evidence/metadata is an availability limitation rather
            # than a document-level semantic violation. Additional fields are invalid.
            metadata = {'availability','version','provenance','sha256','content'}
            missing_metadata = all(e.validator == 'required' and any(
                repr(key) in e.message for key in metadata) and e.absolute_path and
                e.absolute_path[0] in {'source_documents','candidate_documents'} for e in errors)
            result['status'] = 'unsupported' if missing_metadata else 'invalid_input'
            result['reasons'] = ['SP_INPUT_SCHEMA: '+e.message for e in errors]
            return result
        contract = raw['writing_contract']
        result['contract_mapping'] = {'source':'writing_contract','destination':'semantic_request.writing_contract',
            'mode':'verbatim_evaluation_contract','fields':list(contract),
            'required_information':copy.deepcopy(contract['required_information']),
            'constraints':copy.deepcopy(contract['constraints']),
            'availability_mapping':'explicit SP availability complete -> evaluation coverage complete',
            'inferred_scopes':False,'inferred_relations':False,'inferred_expected_literals':False}
        reasons = result['reasons']
        if raw['missing_context']:
            reasons.append('MISSING_CONTEXT')
        if any(r['exposure']=='pending_contract' for r in contract['required_information']):
            reasons.append('PENDING_CONTRACT')
        has_public=any(d['provenance']['kind']=='public_git' for d in raw['source_documents'])
        if has_public != (raw['source_kind']=='public_source_based'):
            reasons.append('SOURCE_KIND_PROVENANCE_MISMATCH')
        sets=[]
        for key in ('source_documents','candidate_documents'):
            docs=raw[key];sets.append({d['document_id'] for d in docs})
            if len(sets[-1]) != len(docs):reasons.append('DUPLICATE_DOCUMENT_ID')
            for d in docs:
                p=d['provenance']
                if d['version'].strip().lower() in {'','unknown','pending','unspecified','n/a','?'}:
                    reasons.append('UNKNOWN_SNAPSHOT_VERSION')
                if d['availability']!='complete' or not isinstance(d['content'],str):
                    reasons.append('INCOMPLETE_'+key.upper());continue
                if semantic.pipeline.digest_text(d['content']) != d['sha256']:
                    reasons.append('SNAPSHOT_SHA_MISMATCH')
                if p['version']!=d['version']:
                    reasons.append('PROVENANCE_VERSION_MISMATCH')
                if p['kind']=='public_git':
                    repo,version,path=p['repository'],p['version'],p['path']
                    valid_repo=isinstance(repo,str) and re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo)
                    valid_version=re.fullmatch(r'[a-f0-9]{40}',version)
                    valid_path=path and not path.startswith('/') and all(part not in {'','..','.'} for part in path.split('/'))
                    urls={f'https://raw.githubusercontent.com/{repo}/{version}/{path}',
                          f'https://github.com/{repo}/blob/{version}/{path}'}
                    if not (valid_repo and valid_version and valid_path and p['url'] in urls):
                        reasons.append('PUBLIC_PROVENANCE_IDENTITY_MISMATCH')
                    if (not all(p[k] for k in ('repository','url','snapshot_path','snapshot_sha256','git_blob_sha'))
                            or p['snapshot_sha256']!=d['sha256']):
                        reasons.append('PUBLIC_PROVENANCE_UNBOUND')
                    encoded=d['content'].encode('utf-8')
                    blob=hashlib.sha1(b'blob '+str(len(encoded)).encode()+b'\0'+encoded).hexdigest()
                    if p['git_blob_sha']!=blob:
                        reasons.append('PUBLIC_GIT_BLOB_MISMATCH')
                elif p['snapshot_sha256'] is not None and p['snapshot_sha256']!=d['sha256']:
                    reasons.append('SYNTHETIC_PROVENANCE_SHA_MISMATCH')
        if sets[0]!=sets[1] or sets[1]!=set(contract['output_document_ids']):
            reasons.append('UNKNOWN_BASELINE_OR_DESTINATION_SET')
        if len(set(contract['output_document_ids'])) != len(contract['output_document_ids']):
            reasons.append('DUPLICATE_OUTPUT_DOCUMENT_ID')
        if reasons:return result
        def snapshots(key):
            return [dict(copy.deepcopy(d),coverage='complete',snapshot_id=key+':'+d['document_id']+':'+d['sha256']) for d in raw[key]]
        report=semantic.evaluate_snapshot_pair(snapshots('source_documents'),snapshots('candidate_documents'),
            contract, context={key:raw[key] for key in ('task','source_kind','construction','missing_context','supplied_observations')},
            reviewer=reviewer,max_review_chars=max_review_chars,timeout_seconds=timeout_seconds)
        result['semantic_report']=report
        result['all_checks_reviewed']=report['coverage']['all_checks_reviewed']
        result['all_judgments_definitive']=report['coverage']['all_judgments_definitive']
        result['violation_confirmed']=report['violation_confirmed']
        result['model_execution_state']=report['execution']['state']
        result['evaluated']=report['coverage']['complete']
        result['semantic_judgment']=report['overall_judgment']
        result['gate_state']=report['gate_state']
        if result['evaluated']:result['status']='evaluated'
        elif result['all_checks_reviewed']:
            result['status']='partially_evaluated'
            reasons.append('UNRESOLVED_SEMANTIC_CHECKS')
        else:reasons.append('SEMANTIC_REVIEW_'+report['execution']['state'].upper())
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):
        result['status']='invalid_input';result['reasons']=['INVALID_SP_INPUT']
    return result
