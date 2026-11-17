"""Input-only IR -> generic Core contract bridge. No gold/evaluator file access."""
import copy
import json
from pathlib import Path

import jsonschema
import document_set as core

_INPUTS = Path(__file__).resolve().parents[2] / 'evaluation/integrated_reconstruction'
_SCHEMAS = {version: json.loads((_INPUTS / name).read_text()) for version,name in (
    ('integrated-input-v1','input.schema.json'),('integrated-input-v2','input-v2.schema.json'))}


def from_ir_input(raw):
    """Accept only strict versioned input schema; unknown evaluation fields reject.

    No audience/purpose inference or permissions extracted from document prose.
    Only complete supplied snapshots are eligible for later planning. Source path
    strings are identifiers, never opened. Caller pins the returned digest.
    """
    raw=copy.deepcopy(raw)
    if (not isinstance(raw,dict) or not isinstance(raw.get('schema_version'),str)
            or raw['schema_version'] not in _SCHEMAS):
        raise ValueError('UNSUPPORTED_IR_INPUT_VERSION')
    if list(jsonschema.Draft202012Validator(_SCHEMAS[raw['schema_version']]).iter_errors(raw)):
        raise ValueError('IR_INPUT_SCHEMA_INVALID')
    origin_hash=core.contract_digest(raw)
    source_id='supplied-input:'+origin_hash
    docs=[]
    for source in raw['documents']:
        docs.append({key:copy.deepcopy(source[key]) for key in
            ('document_id','role','authority','access','completeness','content','sha256')})
        docs[-1].update(audience=None,purpose=None,source_scope=source.get('source_scope'),
            provenance={'kind':'supplied_snapshot','source_id':source_id,'path':source['path'],
                        'snapshot_sha256':source['sha256']},
            output_target=source['access'] in {'edit','format_only'},
            explicit_constraints=[],pending_questions=[])
    contract={'schema_version':core.VERSION,'contract_id':raw['case_id'],
        'request':raw['request'],'context':raw['context'],'audience':None,'purpose':None,
        'explicit_constraints':copy.deepcopy(raw['explicit_constraints']),
        'pending_questions':copy.deepcopy(raw['availability']['gaps']),
        'origin':{'source_id':source_id,'input_sha256':origin_hash,'format':raw['schema_version']},
        # v1 describes complete supplied snapshots, never a complete external world.
        'document_set_completeness':raw['availability'].get('document_set','complete'),
        'documents':docs,'output_scopes':[{'scope_id':'document:'+d['document_id'],'document_id':d['document_id']}
            for d in docs if d['output_target']],
        'additional_permissions':dict.fromkeys(('external_lookup','create_document','apply_files'),'not_granted'),
        'delivery':copy.deepcopy(raw['delivery'])}
    report=core.validate_contract(contract)
    if not report['structural_input_valid']:
        raise ValueError('IR_CONTRACT_INVALID: '+','.join(report['reasons']))
    return contract
