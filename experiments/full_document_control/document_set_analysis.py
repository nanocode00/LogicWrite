"""G2-A shared literal analysis. No semantic oracle, model, evaluator or executor.

A caller-owned contract pin is mandatory. Derived artifacts are reproducible and
must be replayed at the planning boundary, rather than trusted by self-hash.
Offsets are Unicode codepoints and UTF-8 bytes into the supplied snapshot only.
"""
import copy
import posixpath
import re
from urllib.parse import unquote, urlsplit

import document_set as core
import pipeline

VERSION = 'core-document-set-analysis-v1'
QUANTITY = re.compile(r'(?<!\w)\d+(?:[.,]\d+)*(?:%|건|초|명|회|일|ms|MB|GB)?')
CUES = {
    'conditions': re.compile(r'\b(?:if|unless|before|after|until|when|only)\b|경우|조건|전까지|이상|초과|미만|이하|전에|전에는|[가-힣]+면',re.I),
    'exceptions': re.compile(r'\b(?:except|unless|excluding)\b|예외|제외|다만',re.I),
    'states': re.compile(r'\b(?:approved|pending|failed|draft|deprecated|must|stop|restart|not)\b|승인|미정|실패|초안|금지|중단|재개|필수|않',re.I),
    'identifiers': re.compile(r'`[^`\n]+`'),
}
LINK = re.compile(r'\[[^\]\n]*\]\(([^\s)]+)(?:\s+[^)]*)?\)')


def boundary():
    return dict(core._boundary(),execution_allowed=False,model_calls=0)


def artifact_digest(artifact):
    return core.contract_digest({k:v for k,v in artifact.items() if k!='analysis_sha256'})


def _observations(text, start):
    result={}
    for name,pattern in dict(CUES,quantities=QUANTITY).items():
        result[name]=[dict(quote=m.group(),start=start+m.start(),end=start+m.end(),
                           status='literal_observation') for m in pattern.finditer(text)]
    return result


def analyze_document_set(contract, *, trusted_contract_sha256):
    """Analyze every supplied document into one indexed graph, without editing.

    complete_literal_coverage means parseable source coverage, never semantic
    completeness. Authority text is retained, not promoted to an authority rank.
    General equivalence/conflict/relevance remains unresolved, including links
    whose target exists and byte-identical paragraphs in different contexts.
    """
    admission=core._pinned_validation(contract,trusted_contract_sha256)
    result=dict(boundary(),schema_version=VERSION,gate_state='FAIL',
        contract_sha256=admission['contract_sha256'],documents=[],units=[],relations=[],
        confirmed_semantic_conflicts=[],unanalysed=[],uncertainties=[],
        coverage_status='incomplete',semantic_analysis_complete=False,reasons=admission['reasons'])
    if not admission['structural_input_valid']:
        result['analysis_sha256']=artifact_digest(result)
        return result
    contract=copy.deepcopy(contract)
    exact={};literals={};paths={d['provenance']['path']:d['document_id'] for d in contract['documents']}
    units=result['units'];relations=result['relations'];unanalysed=result['unanalysed']
    for doc in contract['documents']:
        did=doc['document_id'];text=doc['content']
        snapshot=dict(snapshot_id=did+':'+doc['sha256'],content=text,sha256=doc['sha256'])
        blocks=pipeline.parse_markdown_blocks(snapshot)
        pipeline.verify_block_partition(snapshot,blocks)
        meta={k:copy.deepcopy(v) for k,v in doc.items() if k!='content'}
        meta.update(blocks=blocks,unit_ids=[],literal_coverage='complete')
        result['documents'].append(meta)
        if doc['completeness']!='complete':
            unanalysed.append(dict(document_id=did,unit_id=None,reason='INCOMPLETE_SUPPLIED_SNAPSHOT',source_scope=doc['source_scope']))
        if doc['role'] is None or doc['authority'] is None:
            result['uncertainties'].append(dict(kind='unknown_document_context',document_ids=[did],unit_ids=[],status='unresolved'))
        section=[]
        for b in blocks:
            if b['kind'] in pipeline.EXCLUDED_BLOCK_KINDS:
                continue
            uid=core.contract_digest([did,b['block_id'],doc['sha256']])
            if b['kind']=='heading':
                stripped=b['text'].strip();level=len(stripped)-len(stripped.lstrip('#'))
                while section and section[-1][0]>=level: section.pop()
                section.append((level,uid))
            start,end=b['start'],b['end']
            obs=_observations(b['text'],start)
            unit=dict(unit_id=uid,document_id=did,block_id=b['block_id'],kind=b['kind'],
                quote=b['text'],quote_sha256=b['sha256'],source_sha256=doc['sha256'],
                source_scope=doc['source_scope'],provenance=copy.deepcopy(doc['provenance']),
                source_span=dict(start=start,end=end,line_start=b['line_start'],line_end=b['line_end'],
                    byte_start=len(text[:start].encode('utf-8')),byte_end=len(text[:end].encode('utf-8'))),
                role=doc['role'],authority=doc['authority'],access=doc['access'],output_target=doc['output_target'],
                section_unit_ids=[uid for _,uid in section],preservation_group=uid,
                claim=dict(quote=b['text'],status='uninterpreted_source_block'),observations=obs,
                reader_relevance=dict(status='unresolved',audience=doc['audience'] or contract['audience'],
                    purpose=doc['purpose'] or contract['purpose'],request=contract['request'],
                    explicit_constraints=contract['explicit_constraints']+doc['explicit_constraints']),
                semantic_status='unresolved',analysis_status='unanalysed' if b['kind']=='unsupported' else 'literal_only')
            units.append(unit);meta['unit_ids'].append(uid)
            if b['kind']=='unsupported':
                meta['literal_coverage']='incomplete'
                unanalysed.append(dict(document_id=did,unit_id=uid,reason=b['unsupported_reason'],source_scope=doc['source_scope']))
            if obs['conditions'] or obs['exceptions']:
                relations.append(dict(kind='condition_claim_cooccurrence',unit_ids=[uid],
                    basis='same_atomic_source_block',status='observed',semantic_status='unresolved',
                    preservation='retain_entire_block_and_review_context'))
            # Deliberately no whitespace normalization or punctuation folding.
            if b['kind']=='paragraph': exact.setdefault(b['text'],[]).append(uid)
            for item in obs['quantities']+obs['identifiers']:
                literals.setdefault(item['quote'],set()).add(uid)
            for m in LINK.finditer(b['text']):
                value=m.group(1)
                try:
                    parsed=urlsplit(value)
                except ValueError:
                    parsed=None
                resolved=None
                if parsed is not None and not parsed.scheme and not parsed.netloc:
                    path=posixpath.normpath(posixpath.join(posixpath.dirname(doc['provenance']['path']),unquote(parsed.path))) if parsed.path else doc['provenance']['path']
                    resolved=paths.get(path)
                relations.append(dict(kind='explicit_reference',unit_ids=[uid],target_document_id=resolved,
                    literal_target=value,start=start+m.start(1),end=start+m.end(1),
                    status='resolved_path_only' if resolved else 'unresolved',semantic_status='unresolved'))
        result['uncertainties'].append(dict(kind='semantic_analysis_not_run',document_ids=[did],
            unit_ids=list(meta['unit_ids']),status='unresolved'))
    for text,uids in exact.items():
        if len(uids)>1:
            relations.append(dict(kind='exact_text',unit_ids=uids,basis='identical_full_paragraph_bytes',
                quote_sha256=core._digest(text),status='observed',semantic_status='unresolved'))
    for literal,uids in sorted(literals.items()):
        if len(uids)>1:
            relations.append(dict(kind='shared_literal_candidate',unit_ids=sorted(uids),literal=literal,
                status='unresolved',semantic_status='unresolved',basis='literal_overlap_only'))
    if contract['document_set_completeness']!='complete':
        unanalysed.append(dict(document_id=None,unit_id=None,reason='INCOMPLETE_DOCUMENT_SET',source_scope=None))
    if contract['context'] is None:
        result['uncertainties'].append(dict(kind='unknown_common_context',document_ids=[],unit_ids=[],status='unresolved'))
    result.update(gate_state='REVIEW',coverage_status='incomplete' if unanalysed else 'complete_literal_coverage')
    result['analysis_sha256']=artifact_digest(result)
    return result


def validate_analysis(contract, analysis, *, trusted_contract_sha256):
    """Full deterministic replay rejects even a resealed, internally valid forgery."""
    expected=analyze_document_set(contract,trusted_contract_sha256=trusted_contract_sha256)
    return (expected['gate_state']!='FAIL' and isinstance(analysis,dict) and core.contract_digest(analysis)==core.contract_digest(expected))
