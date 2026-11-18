"""G2-B conditional planning, never execution or semantic/approval certification.

Explicit proposals and scope assertions are trusted caller inputs, pinned outside
models just like G1. A digest does not authenticate genuine external authority.
Generic Core never imports IR/evaluation data. Unknown request decomposition is
held; there is no hidden invocation of Organization or Reconstruction executors.
"""
import copy
import document_set as core
import document_set_analysis as analysis

VERSION = 'core-document-set-plan-v1'
REQUEST_VERSION = 'core-document-set-plan-request-v1'
TASK_KEYS = {'task_id','action','unit_ids','target_document_id','reason','evidence_unit_ids','depends_on','parameters'}
ISSUE_KEYS = {'issue_id','kind','question','decision_owner','decision_needed','unit_ids','document_ids','evidence_unit_ids'}
SCOPE_KEYS = {'question_id','document_ids','unit_ids','reason'}
SUPPORTED = {'KEEP','PLACE','MOVE','REVISE','CONSOLIDATE','FORMAT'}


def make_request(tasks, *, issues=None, question_scopes=None):
    """Build input-only proposals; caller retains the digest before untrusted use."""
    return dict(schema_version=REQUEST_VERSION,tasks=copy.deepcopy(tasks),
        issues=copy.deepcopy(issues or []),question_scopes=copy.deepcopy(question_scopes or []))


def _text(x):
    return isinstance(x,str) and bool(x.strip())


def _ids(x):
    return isinstance(x,list) and all(_text(i) for i in x) and len(set(x))==len(x)


def _valid_request(r):
    if not isinstance(r,dict) or set(r)!={'schema_version','tasks','issues','question_scopes'}: return False
    if r['schema_version']!=REQUEST_VERSION: return False
    if not all(isinstance(r[k],list) for k in ('tasks','issues','question_scopes')): return False
    for t in r['tasks']:
        if not isinstance(t,dict) or set(t)!=TASK_KEYS: return False
        if not all(_text(t[k]) for k in ('task_id','action','target_document_id','reason')): return False
        if not all(_ids(t[k]) for k in ('unit_ids','evidence_unit_ids','depends_on')): return False
        if not t['unit_ids'] or not t['evidence_unit_ids'] or not isinstance(t['parameters'],dict): return False
    for i in r['issues']:
        if not isinstance(i,dict) or set(i)!=ISSUE_KEYS: return False
        if not all(_text(i[k]) for k in ('issue_id','kind','question','decision_owner','decision_needed')): return False
        if i['kind'] not in {'potential_conflict','uncertainty'}: return False
        if i['issue_id'].startswith(('global:','document:','task:')) or i['issue_id']=='request-decomposition': return False
        if not all(_ids(i[k]) for k in ('unit_ids','document_ids','evidence_unit_ids')): return False
        if not (i['unit_ids'] or i['document_ids']) or not i['evidence_unit_ids']: return False
    for s in r['question_scopes']:
        if not isinstance(s,dict) or set(s)!=SCOPE_KEYS: return False
        if not all(_text(s[k]) for k in ('question_id','reason')): return False
        if not _ids(s['unit_ids']) or not _ids(s['document_ids']): return False
        if not(s['unit_ids'] or s['document_ids']): return False
    for key,field in (('tasks','task_id'),('issues','issue_id'),('question_scopes','question_id')):
        ids=[x[field] for x in r[key]]
        if len(set(ids))!=len(ids): return False
    return True


def _evidence(uid, units):
    u=units[uid]
    return {k:copy.deepcopy(u[k]) for k in ('unit_id','document_id','quote','source_sha256','source_span','source_scope','provenance','authority','access')}


def _question(qid,question,*,docs=None,uids=None,evidence=None,owner='Requesting user / document authority owner',decision='Clarify scope or supply missing authority/context',origin='contract'):
    return dict(question_id=qid,question=question,document_ids=list(docs or []),unit_ids=list(uids or []),
        evidence=list(evidence or []),decision_owner=owner,decision_needed=decision,origin=origin,
        status='unresolved',dependent_task_ids=[],held_task_ids=[])


def _change(t):
    return t['action']!='KEEP'


def _touches(t, units):
    uids=set(t['unit_ids'])
    for k in ('anchor_unit_id','primary_unit_id'):
        value=t['parameters'].get(k)
        if isinstance(value,str): uids.add(value)
    # Evidence is a read dependency, not permission to modify its source.
    deps=uids|set(t['evidence_unit_ids'])
    docs={units[u]['document_id'] for u in deps if u in units}|{t['target_document_id']}
    return uids,deps,docs


def _affected(q, deps, docs):
    return (not(q['document_ids'] or q['unit_ids']) or bool(set(q['document_ids'])&docs or set(q['unit_ids'])&deps))


def _operation_reasons(t, units, docs):
    action=t['action'];p=t['parameters'];src=[units[u] for u in t['unit_ids']]
    target=t['target_document_id'];source_docs={u['document_id'] for u in src}
    if action=='KEEP':
        if p or source_docs!={target}: return 'unsupported',['KEEP_REQUIRES_ORIGINAL_LOCATION']
        return 'eligible',[]
    if action not in SUPPORTED: return 'unsupported',['CORE_OPERATION_UNSUPPORTED']
    if action=='FORMAT': return 'held',['FORMAT_TRANSFORM_POLICY_UNDEFINED']
    if len(src)!=1 or src[0]['kind']!='paragraph': return 'held',['WHOLE_STANDALONE_PARAGRAPH_REQUIRED']
    u=src[0]
    if action=='MOVE':
        if p!={'placement':'append'}: return 'unsupported',['MOVE_APPEND_ONLY']
        if target in source_docs: return 'unsupported',['CROSS_DOCUMENT_MOVE_REQUIRED']
    elif action=='PLACE':
        if set(p)!={'anchor_unit_id','position'} or p['position'] not in ('before','after'):
            return 'unsupported',['SIMPLE_PARAGRAPH_ANCHOR_REQUIRED']
        anchor=units.get(p['anchor_unit_id']) if isinstance(p['anchor_unit_id'],str) else None
        if not anchor or anchor['kind']!='paragraph' or anchor['unit_id']==u['unit_id']:
            return 'held',['PLACEMENT_ANCHOR_UNRESOLVED']
        if source_docs!={target} or anchor['document_id']!=target:
            return 'unsupported',['IN_DOCUMENT_PLACEMENT_ONLY']
    elif action=='CONSOLIDATE':
        if set(p)!={'primary_unit_id'}: return 'unsupported',['EXACT_PRIMARY_PARAGRAPH_REQUIRED']
        primary=units.get(p['primary_unit_id']) if isinstance(p['primary_unit_id'],str) else None
        if not primary or primary['unit_id']==u['unit_id']: return 'held',['CONSOLIDATION_PRIMARY_UNRESOLVED']
        if primary['document_id']!=u['document_id'] or target!=u['document_id']:
            return 'unsupported',['IN_DOCUMENT_CONSOLIDATION_ONLY']
        if primary['kind']!='paragraph' or u['quote']!=primary['quote']:
            return 'unsupported',['EXACT_PARAGRAPH_BYTES_REQUIRED']
        # Identical bytes do not prove identical contextual obligations.
        if primary['section_unit_ids']!=u['section_unit_ids']:
            return 'held',['CONSOLIDATION_CONTEXT_UNRESOLVED']
    elif action=='REVISE':
        if set(p)!={'operation','constraints'} or p.get('operation') not in ('REVISE','COMPRESS'):
            return 'unsupported',['BOUNDED_EXPRESSION_SETTINGS_REQUIRED']
        c=p['constraints']
        if not isinstance(c,dict) or set(c)-{'register','terminology'}:
            return 'unsupported',['BOUNDED_EXPRESSION_SETTINGS_REQUIRED']
        if c.get('register') not in (None,'합니다체','해요체','한다체'):
            return 'unsupported',['BOUNDED_EXPRESSION_SETTINGS_REQUIRED']
        terms=c.get('terminology',{})
        if not isinstance(terms,dict) or not all(_text(k) and _text(v) for k,v in terms.items()):
            return 'unsupported',['BOUNDED_EXPRESSION_SETTINGS_REQUIRED']
        if source_docs!={target}: return 'unsupported',['REVISE_IN_PLACE_ONLY']
        if not c and p['operation']=='REVISE': return 'held',['EXPLICIT_EXPRESSION_RULE_REQUIRED']
    # Whole-block atomicity prevents splitting conditions from their claim. A
    # condition-bearing source section still needs contextual review for edits.
    if action in {'PLACE','MOVE','REVISE','CONSOLIDATE'}:
        for other in units.values():
            if other['document_id']!=u['document_id']: continue
            source_path=u['section_unit_ids']; other_path=other['section_unit_ids']
            same_section=(source_path[:len(other_path)]==other_path)
            if (same_section or other['unit_id']==u['unit_id']) and (other['observations']['conditions'] or other['observations']['exceptions']):
                return 'held',['CONDITION_CONTEXT_REVIEW_REQUIRED']
    if action=='MOVE':
        for other in units.values():
            if other['document_id']==target and (other['observations']['conditions'] or other['observations']['exceptions']):
                return 'held',['DESTINATION_CONDITION_CONTEXT_REVIEW_REQUIRED']
    return 'eligible',[]


def plan_document_set(contract, artifact, request, *, trusted_contract_sha256, trusted_request_sha256):
    """Return tasks + scoped HITL. Every eligible row is conditional, never runnable.

    Requests are caller proposals, not evidence that the broad natural-language
    purpose was solved. Pending questions cannot be silently dropped or answered.
    """
    result=dict(analysis.boundary(),schema_version=VERSION,gate_state='FAIL',tasks=[],hitl_questions=[],
        contract_sha256=None,analysis_sha256=None,request_sha256=None,plan_sha256=None,
        organization_complete=False,unplanned_unit_ids=[],reasons=[])
    try:
        if not analysis.validate_analysis(contract,artifact,trusted_contract_sha256=trusted_contract_sha256):
            result['reasons']=['STALE_OR_INVALID_ANALYSIS'];return result
        if not _valid_request(request):
            result['reasons']=['INVALID_PLAN_REQUEST'];return result
        digest=core.contract_digest(request)
        if trusted_request_sha256 is None or digest!=trusted_request_sha256:
            result['reasons']=['TRUSTED_REQUEST_MISMATCH'];return result
        # Snapshot inputs before reasoning so no output aliases caller data.
        contract=copy.deepcopy(contract);artifact=copy.deepcopy(artifact);request=copy.deepcopy(request)
        units={u['unit_id']:u for u in artifact['units']};docs={d['document_id']:d for d in contract['documents']}
        qs=[]
        for n,q in enumerate(contract['pending_questions']): qs.append(_question('global:'+str(n),q))
        for did,d in docs.items():
            for n,q in enumerate(d['pending_questions']):
                qs.append(_question('document:'+did+':'+str(n),q,docs=[did]))
        known={q['question_id']:q for q in qs}
        for s in request['question_scopes']:
            if s['question_id'] not in known or not set(s['document_ids'])<=docs.keys() or not set(s['unit_ids'])<=units.keys():
                raise ValueError('INVALID_QUESTION_SCOPE')
            q=known[s['question_id']]
            # Document-local questions cannot be narrowed out of their document.
            if q['document_ids']:
                raise ValueError('DOCUMENT_QUESTION_CANNOT_BE_NARROWED')
            q.update(document_ids=s['document_ids'],unit_ids=s['unit_ids'],scope_basis=s['reason'],scope_origin='trusted_caller_assertion')
        for i in request['issues']:
            if (i['issue_id'] in known or not set(i['unit_ids']+i['evidence_unit_ids'])<=units.keys()
                    or not set(i['document_ids'])<=docs.keys()): raise ValueError('INVALID_ISSUE_BINDING')
            # Evidence not explicitly scoped remains a dependency of the issue.
            q=_question(i['issue_id'],i['question'],docs=i['document_ids'],uids=sorted(set(i['unit_ids']+i['evidence_unit_ids'])),
                evidence=[_evidence(u,units) for u in i['evidence_unit_ids']],owner=i['decision_owner'],
                decision=i['decision_needed'],origin='trusted_caller_reported_'+i['kind'])
            qs.append(q);known[q['question_id']]=q
        proposals=request['tasks']
        if not proposals:
            proposals=[dict(task_id='keep:'+uid,action='KEEP',unit_ids=[uid],target_document_id=u['document_id'],
                reason='Preserve source pending explicit task decomposition',evidence_unit_ids=[uid],depends_on=[],parameters={})
                for uid,u in units.items()]
        result.update(contract_sha256=trusted_contract_sha256,analysis_sha256=artifact['analysis_sha256'],request_sha256=digest)
        rows=result['tasks'];touches={}
        for t in proposals:
            row=copy.deepcopy(t);rows.append(row)
            row.update(status='held',reasons=[],required_hitl_question_ids=[],execution_allowed=False,
                semantic_judgment='unresolved',eligibility_is_conditional=True,applied=False,
                source_evidence=[],applicable_permissions=[],preservation_obligations=[],
                executor_mapping=None,conflicts=[],uncertainties=[])
            if not set(t['unit_ids']+t['evidence_unit_ids'])<=units.keys() or t['target_document_id'] not in docs:
                row.update(status='denied',reasons=['UNKNOWN_SOURCE_OR_TARGET']);continue
            writes,deps,touched_docs=_touches(t,units)
            # Read dependencies include explicit links and literal candidates.
            # This is conservative dependency tracking, never equivalence proof.
            # Retain containing/ancestor prose as read dependencies. It can
            # qualify a whole subsection even when the task names one paragraph.
            for uid in list(deps):
                if uid not in units: continue
                u=units[uid]
                for other in units.values():
                    path=other['section_unit_ids']
                    if other['document_id']==u['document_id'] and u['section_unit_ids'][:len(path)]==path:
                        deps.add(other['unit_id'])
            if t['action']=='MOVE':
                deps.update(u['unit_id'] for u in units.values() if u['document_id']==t['target_document_id'])
            for _ in units:
                before=(len(deps),len(touched_docs))
                for relation in artifact['relations']:
                    if not set(relation['unit_ids'])&deps: continue
                    if relation['kind'] in {'exact_text','shared_literal_candidate'}:
                        deps.update(relation['unit_ids'])
                    if relation['kind']=='explicit_reference' and relation['target_document_id']:
                        touched_docs.add(relation['target_document_id'])
                        deps.update(u['unit_id'] for u in units.values() if u['document_id']==relation['target_document_id'])
                touched_docs.update(units[u]['document_id'] for u in deps if u in units)
                if before==(len(deps),len(touched_docs)): break
            touches[t['task_id']]=(writes,deps,touched_docs)
            row['source_evidence']=[_evidence(u,units) for u in sorted(deps) if u in units]
            permission_docs={units[u]['document_id'] for u in writes if u in units}|{t['target_document_id']}
            row['applicable_permissions']=[dict(document_id=d,access=docs[d]['access'],output_target=docs[d]['output_target'],authority=docs[d]['authority'],operation='reference' if t['action']=='KEEP' else 'format' if t['action']=='FORMAT' else 'edit_content') for d in sorted(permission_docs)]
            row['preservation_obligations']=[dict(kind='retain_source_binding',unit_id=u,preservation_group=units[u]['preservation_group'],
                quote_sha256=units[u]['quote_sha256'],source_sha256=units[u]['source_sha256']) for u in sorted(deps) if u in units]
            row['preservation_obligations']+= [dict(kind='uninterpreted_constraint',document_id=None,text=c) for c in contract['explicit_constraints']]
            for d in sorted(touched_docs):
                row['preservation_obligations'] += [dict(kind='uninterpreted_constraint',document_id=d,text=c) for c in docs[d]['explicit_constraints']]
            if _change(t) and any(docs[d]['access']=='read_only' or
                    (not docs[d]['output_target'] and docs[d]['access']!='pending') or
                    (docs[d]['access']=='format_only' and t['action']!='FORMAT') for d in permission_docs):
                row.update(status='denied',reasons=['DOCUMENT_ACCESS_DENIED']);continue
            if any(docs[d]['access']=='pending' or docs[d]['authority'] is None or docs[d]['role'] is None for d in touched_docs):
                row.update(status='held',reasons=['UNKNOWN_PERMISSION_OR_CONTEXT'])
            elif (contract['document_set_completeness']!='complete' or contract['context'] is None or
                  any(docs[d]['completeness']!='complete' for d in touched_docs) or
                  any(x['document_id'] in touched_docs or x['document_id'] is None for x in artifact['unanalysed'])):
                row.update(status='held',reasons=['INCOMPLETE_ANALYSIS_OR_CONTEXT'])
            else:
                status,reasons=_operation_reasons(t,units,docs);row.update(status=status,reasons=reasons)
            unresolved_refs=[r for r in artifact['relations'] if r['kind']=='explicit_reference'
                             and r['target_document_id'] is None and set(r['unit_ids'])&deps]
            if _change(t) and unresolved_refs:
                if row['status']=='eligible': row['status']='held'
                row['reasons'].append('UNRESOLVED_REFERENCE_DEPENDENCY')
            for q in qs:
                if _change(t) and _affected(q,deps,touched_docs):
                    q['dependent_task_ids'].append(t['task_id']);row['required_hitl_question_ids'].append(q['question_id'])
                    if row['status']=='eligible': row.update(status='held')
                    row['reasons'].append('UNRESOLVED_SCOPED_QUESTION')
            row['uncertainties']=[r for r in artifact['relations'] if set(r['unit_ids'])&deps and r['semantic_status']=='unresolved']
            if row['status']=='eligible':
                row['executor_mapping']=dict(component='organization' if t['action'] in {'KEEP','PLACE','CONSOLIDATE'} else 'reconstruction',
                    action='KEEP' if t['action']=='PLACE' else t['action'],requires_g2c_binding=True,
                    mode='reference_only' if t['action']=='KEEP' and not docs[t['target_document_id']]['output_target'] else 'candidate_plan_only',
                    requires_source_and_constraint_revalidation=True,requires_independent_semantic_review=True)
        # Overlapping writes/anchor movement are unresolved even if an ordering
        # was requested: no general sequential materialization proof exists here.
        for n,left in enumerate(rows):
            if not _change(left) or left['task_id'] not in touches: continue
            lw,ldeps,_=touches[left['task_id']]
            for right in rows[n+1:]:
                if not _change(right) or right['task_id'] not in touches: continue
                rw,rdeps,_=touches[right['task_id']]
                same_append=(left['action']==right['action']=='MOVE' and left['target_document_id']==right['target_document_id'])
                read_write=bool(lw&rdeps or rw&ldeps)
                if lw&rw or same_append or read_write:
                    for a,b in ((left,right),(right,left)):
                        a['conflicts'].append(b['task_id'])
                        if a['status']=='eligible':a['status']='held'
                        a['reasons'].append('OVERLAPPING_TASK_EFFECTS' if lw&rw or same_append else 'READ_WRITE_DEPENDENCY_UNRESOLVED')
        byid={t['task_id']:t for t in rows}
        # Reachability detects cycles without trusting proposed task order.
        def cycle(start):
            pending=list(byid[start]['depends_on']);seen=set()
            while pending:
                x=pending.pop()
                if x==start:return True
                if x in seen or x not in byid:continue
                seen.add(x);pending.extend(byid[x]['depends_on'])
            return False
        for t in rows:
            if cycle(t['task_id']) or any(d not in byid for d in t['depends_on']):
                if t['status']=='eligible': t['status']='held'
                t['reasons'].append('UNKNOWN_OR_CYCLIC_DEPENDENCY')
        for _ in rows:
            changed=False
            for t in rows:
                if t['status']=='eligible' and any(byid[d]['status']!='eligible' for d in t['depends_on']):
                    t.update(status='held');t['reasons'].append('DEPENDENCY_NOT_ELIGIBLE');changed=True
            if not changed:break
        if not request['tasks']:
            q=_question('request-decomposition','Which source-bound operations implement the supplied request?',
                decision='Supply explicit task proposals and resolve semantic relevance',origin='planner_gap')
            q['dependent_task_ids']=['request-decomposition'];qs.append(q)
            for pending in qs:
                if 'request-decomposition' not in pending['dependent_task_ids']:
                    pending['dependent_task_ids'].append('request-decomposition')
            rows.append(dict(task_id='request-decomposition',action='DECOMPOSE_REQUEST',unit_ids=[],target_document_id=None,
                evidence_unit_ids=[],source_evidence=[],reason=contract['request'],status='held',
                reasons=['REQUEST_DECOMPOSITION_UNRESOLVED'],depends_on=[],parameters={},applicable_permissions=[],
                preservation_obligations=[],required_hitl_question_ids=[q['question_id']],executor_mapping=None,
                execution_allowed=False,semantic_judgment='unresolved',eligibility_is_conditional=True,applied=False,
                conflicts=[],uncertainties=[]))
        for t in rows:
            if t['status']=='held' and not t['required_hitl_question_ids']:
                q=_question('task:'+t['task_id'],' / '.join(t['reasons']),uids=t['unit_ids'],
                    evidence=t['source_evidence'],decision='Resolve recorded task prerequisites; do not execute before G2-C',origin='planner_prerequisite')
                q['dependent_task_ids']=[t['task_id']];qs.append(q);t['required_hitl_question_ids'].append(q['question_id'])
            if t['status']!='eligible': t['executor_mapping']=None
        # Decision impact includes transitive dependents, not only direct scope.
        for q in qs:
            dependents=set(q['dependent_task_ids'])
            for _ in rows:
                dependents|={t['task_id'] for t in rows if set(t['depends_on'])&dependents}
            q['dependent_task_ids']=sorted(dependents)
            q['held_task_ids']=[t['task_id'] for t in rows if t['task_id'] in dependents and t['status']=='held']
            for t in rows:
                if t['task_id'] in dependents and t['status']=='held' and q['question_id'] not in t['required_hitl_question_ids']:
                    t['required_hitl_question_ids'].append(q['question_id'])
        result['unplanned_unit_ids']=sorted(set(units)-{uid for t in rows for uid in t['unit_ids']})
        result.update(gate_state='REVIEW',hitl_questions=qs,
            reasons=['PLANNING_ONLY_SEMANTIC_REVIEW_AND_EXECUTION_NOT_RUN'])
        result['plan_sha256']=core.contract_digest({k:v for k,v in result.items() if k!='plan_sha256'})
        return result
    except (ValueError,TypeError,KeyError,OverflowError,UnicodeError):
        result.update(gate_state='FAIL',tasks=[],hitl_questions=[],reasons=['INVALID_PLAN_BINDING'])
        return result
