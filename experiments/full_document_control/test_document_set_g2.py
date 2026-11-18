"""G2 development tests: synthetic source contracts and input-only IR coverage."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import document_set as core
import document_set_analysis as analysis
import document_set_planning as planning
from ir_document_set_adapter import from_ir_input

ROOT = Path(__file__).resolve().parents[2]


def synthetic(label='alpha', number='37'):
    docs=[]
    for name,access,text in (
        ('guide','edit',f'# {label}\n\nRun the tool.\n\nIf count exceeds {number}, stop. Do not restart before approval.\n\n[Policy](policy.md)\n'),
        ('policy','read_only',f'# Policy\n\nIf count exceeds {number}, stop. Do not restart before approval.\n'),
        ('notes','edit','# Notes\n\nInstall the package.\n\nVerify the installation.\n'),
        ('format','format_only','# Minutes\n\nThe attempt failed.\n')):
        sha=core._digest(text)
        docs.append(dict(document_id=name,role=name,authority='supplied policy owner',access=access,
            completeness='complete',content=text,sha256=sha,audience=None,purpose=None,source_scope=None,
            provenance=dict(kind='supplied_snapshot',source_id='synthetic',path=name+'.md',snapshot_sha256=sha),
            output_target=access in {'edit','format_only'},explicit_constraints=[],pending_questions=[]))
    return dict(schema_version=core.VERSION,contract_id=label,request='Improve the supplied guides.',
        context='Synthetic offline test',audience=None,purpose=None,explicit_constraints=['Preserve conditions.'],
        pending_questions=[],origin=dict(source_id='synthetic',input_sha256='1'*64,format='synthetic'),
        document_set_completeness='complete',documents=docs,
        output_scopes=[dict(scope_id=d['document_id'],document_id=d['document_id']) for d in docs if d['output_target']],
        additional_permissions=dict.fromkeys(('external_lookup','create_document','apply_files'),'not_granted'),
        delivery=dict(mode='reviewable_candidate_only',required='Review only'))


class G2Tests(unittest.TestCase):
    def setUp(self):
        self.c=synthetic(); self.pin=core.contract_digest(self.c); self.a=self.analyze()

    def analyze(self):
        return analysis.analyze_document_set(self.c,trusted_contract_sha256=self.pin)

    def unit(self,doc,text=None,kind='paragraph'):
        return next(u['unit_id'] for u in self.a['units'] if u['document_id']==doc and u['kind']==kind
                    and (text is None or text in u['quote']))

    def proposal(self,action='KEEP',doc='notes',text='Install',**kw):
        return dict(task_id='t1',action=action,unit_ids=[self.unit(doc,text)],target_document_id=doc,
            reason='Explicit input-only organization request',evidence_unit_ids=[self.unit(doc,text)],
            depends_on=[],parameters={},**kw)

    def plan(self,tasks=None,issues=None,bindings=None,artifact=None,pin=True):
        req=planning.make_request(tasks or [],issues=issues or [],question_scopes=bindings or [])
        return planning.plan_document_set(self.c,self.a if artifact is None else artifact,req,
            trusted_contract_sha256=self.pin,trusted_request_sha256=core.contract_digest(req) if pin else None)

    def test_ir_all_documents_and_exact_source_ranges(self):
        for n,count in ((1,7),(2,4),(3,3)):
            raw=json.loads((ROOT/f'evaluation/integrated_reconstruction/inputs/IR-{n:03}.json').read_text())
            c=from_ir_input(raw); a=analysis.analyze_document_set(c,trusted_contract_sha256=core.contract_digest(c))
            self.assertEqual(len(a['documents']),count)
            self.assertEqual(a['coverage_status'],'complete_literal_coverage')
            docs={d['document_id']:d for d in c['documents']}
            self.assertEqual(set(docs),{u['document_id'] for u in a['units']})
            for u in a['units']:
                d=docs[u['document_id']]; span=u['source_span']
                self.assertEqual(d['content'][span['start']:span['end']],u['quote'])
                self.assertEqual(d['content'].encode()[span['byte_start']:span['byte_end']].decode(),u['quote'])
                self.assertEqual(u['source_sha256'],d['sha256'])
                self.assertEqual(u['access'],d['access']); self.assertEqual(u['authority'],d['authority'])
                self.assertEqual(u['semantic_status'],'unresolved')
            self.assertFalse(a['semantic_analysis_complete'])

    def test_shared_graph_exact_text_not_semantic_equivalence(self):
        kinds={r['kind'] for r in self.a['relations']}
        self.assertIn('exact_text',kinds); self.assertIn('explicit_reference',kinds)
        self.assertTrue(all(r['semantic_status']=='unresolved' for r in self.a['relations']))
        self.assertEqual(self.a['confirmed_semantic_conflicts'],[])
        same=next(r for r in self.a['relations'] if r['kind']=='exact_text')
        units={u['unit_id']:u for u in self.a['units']}
        self.assertNotEqual(units[same['unit_ids'][0]]['document_id'],units[same['unit_ids'][1]]['document_id'])

    def test_conditions_numbers_and_claim_share_atomic_source_group(self):
        u=next(u for u in self.a['units'] if u['unit_id']==self.unit('guide','exceeds'))
        self.assertTrue(u['observations']['quantities']); self.assertTrue(u['observations']['conditions'])
        self.assertEqual(u['preservation_group'],u['unit_id'])
        self.assertEqual(u['claim']['quote'],u['quote'])
        self.assertEqual(u['reader_relevance']['status'],'unresolved')

    def test_variants_not_ir_answer_or_product_specific(self):
        for label,n in (('omega','913'),('새 절차','82')):
            c=synthetic(label,n); a=analysis.analyze_document_set(c,trusted_contract_sha256=core.contract_digest(c))
            self.assertEqual(a['coverage_status'],'complete_literal_coverage')
            self.assertTrue(any(n in x['quote'] for u in a['units'] for x in u['observations']['quantities']))
            self.assertEqual(a['confirmed_semantic_conflicts'],[])

    def test_partial_and_unsupported_are_never_complete(self):
        for change in ('partial','unsupported'):
            c=synthetic()
            if change=='partial': c['documents'][0].update(completeness='excerpt',source_scope='Only provided excerpt')
            else:
                d=c['documents'][0];d['content']+='\n<div>unparsed</div>\n';d['sha256']=core._digest(d['content']);d['provenance']['snapshot_sha256']=d['sha256']
            a=analysis.analyze_document_set(c,trusted_contract_sha256=core.contract_digest(c))
            self.assertEqual(a['coverage_status'],'incomplete'); self.assertTrue(a['unanalysed'])

    def test_contract_and_analysis_tamper_stale_and_resealed_rejected(self):
        for mutate in (lambda a:a['units'].pop(),lambda a:a['relations'].clear(),
                       lambda a:a['units'][0].update(access='read_only'),lambda a:a.update(semantic_analysis_complete=True)):
            a=copy.deepcopy(self.a);mutate(a);a['analysis_sha256']=analysis.artifact_digest(a)
            self.assertEqual(self.plan(artifact=a)['gate_state'],'FAIL')
        self.c['documents'][0]['authority']='forged'
        self.assertEqual(self.analyze()['gate_state'],'FAIL')
        self.assertEqual(self.plan()['gate_state'],'FAIL')

    def test_no_pin_or_untrusted_request_denied(self):
        self.assertEqual(analysis.analyze_document_set(self.c,trusted_contract_sha256=None)['gate_state'],'FAIL')
        self.assertEqual(self.plan([self.proposal()],pin=False)['gate_state'],'FAIL')

    def test_readonly_content_and_destination_edits_denied(self):
        for task in (self.proposal('REVISE','policy','exceeds'),
                     dict(self.proposal('MOVE'),target_document_id='policy',parameters={'placement':'append'})):
            p=self.plan([task]);self.assertEqual(p['tasks'][0]['status'],'denied',p)

    def test_format_only_content_denied_undefined_format_held(self):
        for action,status in (('REVISE','denied'),('PLACE','denied'),('FORMAT','held'),('KEEP','eligible')):
            p=self.plan([self.proposal(action,'format','failed')]);self.assertEqual(p['tasks'][0]['status'],status,p)

    def test_unknown_authority_and_partial_held_locally(self):
        self.c['documents'][2]['authority']=None; self.pin=core.contract_digest(self.c);self.a=self.analyze()
        self.assertEqual(self.plan([self.proposal()])['tasks'][0]['status'],'held')

    def test_scoped_issue_holds_related_action_only(self):
        issue=dict(issue_id='policy-check',kind='potential_conflict',question='Which policy applies?',
            decision_owner='Policy maintainer',decision_needed='Confirm applicable policy',
            unit_ids=[self.unit('guide','exceeds'),self.unit('policy','exceeds')],document_ids=[],
            evidence_unit_ids=[self.unit('guide','exceeds'),self.unit('policy','exceeds')])
        independent=self.proposal('PLACE'); independent['parameters']={'anchor_unit_id':self.unit('notes','Verify'),'position':'after'}
        dependent=self.proposal('REVISE','guide','exceeds');dependent['task_id']='policy-task';dependent['parameters']={'operation':'COMPRESS','constraints':{}}
        p=self.plan([independent,dependent],[issue]);self.assertEqual([t['status'] for t in p['tasks']],['eligible','held'],p)
        q=next(q for q in p['hitl_questions'] if q['question_id']=='policy-check')
        self.assertEqual(q['dependent_task_ids'],['policy-task']);self.assertTrue(q['evidence'])
        self.assertEqual(q['held_task_ids'],['policy-task'])

    def test_global_question_unknown_scope_holds_changes_but_keep_survives(self):
        self.c['pending_questions']=['Unconfirmed policy'];self.pin=core.contract_digest(self.c);self.a=self.analyze()
        move=self.proposal('MOVE');move.update(target_document_id='guide',parameters={'placement':'append'})
        p=self.plan([move,self.proposal() | {'task_id':'keep'}]);self.assertEqual([t['status'] for t in p['tasks']],['held','eligible'])
        binding=dict(question_id='global:0',document_ids=['guide'],unit_ids=[],reason='Caller explicitly bounds policy scope')
        place=self.proposal('PLACE');place['parameters']={'anchor_unit_id':self.unit('notes','Verify'),'position':'before'}
        self.assertEqual(self.plan([place],bindings=[binding])['tasks'][0]['status'],'eligible')

    def test_dependencies_propagate_unknown_cycles_and_blocked(self):
        for dep in (['absent'],['t1']):
            task=self.proposal();task['depends_on']=dep
            self.assertEqual(self.plan([task])['tasks'][0]['status'],'held')
        a=self.proposal('REMOVE');b=self.proposal();b.update(task_id='t2',depends_on=['t1'])
        self.assertEqual([t['status'] for t in self.plan([a,b])['tasks']],['unsupported','held'])
        a=self.proposal();a['depends_on']=['t2'];b=self.proposal();b.update(task_id='t2',depends_on=['t1'])
        self.assertEqual([t['status'] for t in self.plan([a,b])['tasks']],['held','held'])

    def test_condition_group_move_not_silently_split_or_semantically_approved(self):
        task=self.proposal('MOVE','guide','exceeds');task.update(target_document_id='notes',parameters={'placement':'append'})
        p=self.plan([task]);self.assertEqual(p['tasks'][0]['status'],'held')
        self.assertIn('CONDITION_CONTEXT_REVIEW_REQUIRED',p['tasks'][0]['reasons'])
        self.assertTrue(p['tasks'][0]['preservation_obligations'])

    def test_supported_and_unsupported_placement(self):
        # A positive MOVE needs a destination without unresolved condition context.
        d=self.c['documents'][0];d['content']='# Destination\n\nGeneral notes.\n';d['sha256']=core._digest(d['content']);d['provenance']['snapshot_sha256']=d['sha256']
        self.pin=core.contract_digest(self.c);self.a=self.analyze()
        task=self.proposal('MOVE');task.update(target_document_id='guide',parameters={'placement':'append'})
        self.assertEqual(self.plan([task])['tasks'][0]['status'],'eligible')
        task['parameters']={'placement':'internal'}
        self.assertEqual(self.plan([task])['tasks'][0]['status'],'unsupported')
        for action in ('REMOVE','CREATE_DOCUMENT','PARAPHRASE','ALIEN'):
            self.assertEqual(self.plan([self.proposal(action)])['tasks'][0]['status'],'unsupported')

    def test_default_plan_preserves_all_units_and_exposes_decomposition_gap(self):
        p=self.plan();self.assertEqual({u['unit_id'] for u in self.a['units']},
            {uid for t in p['tasks'] for uid in t['unit_ids']})
        self.assertTrue(any(t['status']=='held' for t in p['tasks']))
        self.assertFalse(p['organization_complete'])

    def test_no_execution_approval_network_or_source_mutation(self):
        before=copy.deepcopy(self.c)
        with patch('socket.socket',side_effect=AssertionError('No network')),patch('builtins.open',side_effect=AssertionError('No file access')):
            a=self.analyze();p=self.plan([self.proposal()])
        self.assertEqual(self.c,before)
        for r in (a,p):
            self.assertEqual(r['execution_state'],'not_run');self.assertFalse(r['delivery_approved'])
            self.assertFalse(r['stage_transition_allowed']);self.assertFalse(r['execution_allowed'])
            self.assertNotIn('candidate_documents',r);self.assertEqual(r['semantic_judgment'],'unresolved')
        self.assertEqual(core.prepare_reconstruction(self.c,trusted_contract_sha256=self.pin)['status'],'unsupported')

    def test_extra_model_or_evaluator_fields_rejected(self):
        req=planning.make_request([self.proposal()]);req['answers']='DO_NOT_USE'
        p=planning.plan_document_set(self.c,self.a,req,trusted_contract_sha256=self.pin,
            trusted_request_sha256=core.contract_digest(req))
        self.assertEqual(p['gate_state'],'FAIL')
        c=copy.deepcopy(self.c);c['gold']='DO_NOT_USE'
        self.assertEqual(analysis.analyze_document_set(c,trusted_contract_sha256=core.contract_digest(c))['gate_state'],'FAIL')

    def test_overlapping_writes_held_even_with_distinct_task_ids(self):
        t=self.proposal('PLACE');t['parameters']={'anchor_unit_id':self.unit('notes','Verify'),'position':'after'}
        other=copy.deepcopy(t);other['task_id']='t2'
        self.assertEqual([t['status'] for t in self.plan([t,other])['tasks']],['held','held'])

    def test_malformed_request_never_crashes_or_authorizes(self):
        for req in (None,[],{},planning.make_request([{}]),planning.make_request([self.proposal()|{'action':[]}])):
            p=planning.plan_document_set(self.c,self.a,req,trusted_contract_sha256=self.pin,
                trusted_request_sha256=core.contract_digest(req))
            self.assertEqual(p['gate_state'],'FAIL',p)

    def test_revise_rules_and_exact_consolidation_support(self):
        t=self.proposal('REVISE');t['parameters']={'operation':'COMPRESS','constraints':{}}
        self.assertEqual(self.plan([t])['tasks'][0]['status'],'eligible')
        c=synthetic();d=c['documents'][2];d['content']+='\nInstall the package.\n';d['sha256']=core._digest(d['content']);d['provenance']['snapshot_sha256']=d['sha256']
        self.c=c;self.pin=core.contract_digest(c);self.a=self.analyze()
        duplicates=[u['unit_id'] for u in self.a['units'] if u['document_id']=='notes' and u['quote']=='Install the package.\n']
        t=self.proposal('CONSOLIDATE');t['unit_ids']=[duplicates[1]];t['parameters']={'primary_unit_id':duplicates[0]}
        self.assertEqual(self.plan([t])['tasks'][0]['status'],'eligible')
        t['parameters']={'primary_unit_id':self.unit('notes','Verify')}
        self.assertEqual(self.plan([t])['tasks'][0]['status'],'unsupported')

    def test_question_binding_follows_literal_and_reference_dependencies(self):
        # A source block referring to a disputed policy is not independent merely
        # because the task directly names a different document.
        self.c['pending_questions']=['Confirm policy status']
        d=self.c['documents'][2];d['content']+='\n[Policy](policy.md)\n';d['sha256']=core._digest(d['content']);d['provenance']['snapshot_sha256']=d['sha256']
        self.pin=core.contract_digest(self.c);self.a=self.analyze()
        t=self.proposal('MOVE','notes','[Policy]');t.update(target_document_id='guide',parameters={'placement':'append'})
        binding=dict(question_id='global:0',document_ids=['policy'],unit_ids=[],reason='Question concerns supplied policy')
        self.assertEqual(self.plan([t],bindings=[binding])['tasks'][0]['status'],'held')

    def test_unknown_question_scope_or_duplicate_reserved_ids_rejected(self):
        issue=dict(issue_id='global:0',kind='uncertainty',question='Question',decision_owner='Maintainer',decision_needed='Decide',
            unit_ids=[self.unit('notes')],document_ids=[],evidence_unit_ids=[self.unit('notes')])
        self.assertEqual(self.plan([self.proposal()],issues=[issue])['gate_state'],'FAIL')

    def test_changed_task_without_explicit_proposal_does_not_hide_uncovered_units(self):
        p=self.plan([self.proposal()])
        self.assertEqual(set(p['unplanned_unit_ids']),{u['unit_id'] for u in self.a['units']}-{self.unit('notes','Install')})

    def test_malformed_url_is_unresolved_source_not_analyzer_crash(self):
        d=self.c['documents'][2];d['content']+='\n[Odd](https://[invalid)\n';d['sha256']=core._digest(d['content']);d['provenance']['snapshot_sha256']=d['sha256']
        self.pin=core.contract_digest(self.c);self.a=self.analyze()
        self.assertEqual(self.a['coverage_status'],'complete_literal_coverage')
        self.assertTrue(any(r.get('literal_target')=='https://[invalid' and r['status']=='unresolved' for r in self.a['relations']))

    def test_replay_uses_strict_json_identity_for_booleans_and_numbers(self):
        a=copy.deepcopy(self.a);a['units'][0]['source_span']['start']=False
        a['analysis_sha256']=analysis.artifact_digest(a)
        self.assertEqual(self.plan(artifact=a)['gate_state'],'FAIL')

    def test_extra_task_payload_cannot_smuggle_evaluation_or_claim_approval(self):
        t=self.proposal();t['gold']='secret'
        self.assertEqual(self.plan([t])['gate_state'],'FAIL')
        t=self.proposal();t['parameters']={'final_checks':'PASS'}
        self.assertNotEqual(self.plan([t])['tasks'][0]['status'],'eligible')

    def test_unresolved_reference_blocks_changed_task(self):
        d=self.c['documents'][2];d['content']+='\n[Missing policy](missing.md)\n';d['sha256']=core._digest(d['content']);d['provenance']['snapshot_sha256']=d['sha256']
        self.pin=core.contract_digest(self.c);self.a=self.analyze()
        t=self.proposal('REVISE','notes','Missing');t['parameters']={'operation':'COMPRESS','constraints':{}}
        self.assertEqual(self.plan([t])['tasks'][0]['status'],'held')
        self.assertIn('UNRESOLVED_REFERENCE_DEPENDENCY',self.plan([t])['tasks'][0]['reasons'])

    def test_parent_condition_and_destination_condition_hold_moves(self):
        d=self.c['documents'][2];d['content']='# Notes\n\nOnly after approval.\n\n## Procedure\n\nInstall the package.\n\nVerify installation.\n'
        d['sha256']=core._digest(d['content']);d['provenance']['snapshot_sha256']=d['sha256']
        self.pin=core.contract_digest(self.c);self.a=self.analyze()
        t=self.proposal('PLACE');t['parameters']={'anchor_unit_id':self.unit('notes','Verify'),'position':'after'}
        self.assertEqual(self.plan([t])['tasks'][0]['status'],'held')
        self.c=synthetic();self.pin=core.contract_digest(self.c);self.a=self.analyze()
        t=self.proposal('MOVE');t.update(target_document_id='guide',parameters={'placement':'append'})
        self.assertEqual(self.plan([t])['tasks'][0]['status'],'held')

    def test_document_reference_carries_unit_scoped_hitl_dependencies(self):
        d=self.c['documents'][2];d['content']+='\nFollow [Policy](policy.md).\n';d['sha256']=core._digest(d['content']);d['provenance']['snapshot_sha256']=d['sha256']
        self.pin=core.contract_digest(self.c);self.a=self.analyze()
        policy=self.unit('policy','exceeds')
        issue=dict(issue_id='policy-unit',kind='uncertainty',question='Which policy?',decision_owner='Maintainer',
            decision_needed='Confirm policy',unit_ids=[policy],document_ids=[],evidence_unit_ids=[policy])
        t=self.proposal('REVISE','notes','Follow');t['parameters']={'operation':'COMPRESS','constraints':{}}
        p=self.plan([t],issues=[issue]);self.assertEqual(p['tasks'][0]['status'],'held')
        self.assertIn('policy-unit',p['tasks'][0]['required_hitl_question_ids'])

    def test_korean_conditional_literal_keeps_exact_span(self):
        d=self.c['documents'][2];d['content']='# 절차\n\n대기 건수가 82건을 넘으면 신규 작업을 중단한다.\n'
        d['sha256']=core._digest(d['content']);d['provenance']['snapshot_sha256']=d['sha256']
        self.pin=core.contract_digest(self.c);self.a=self.analyze()
        u=next(u for u in self.a['units'] if u['document_id']=='notes' and u['kind']=='paragraph')
        self.assertTrue(u['observations']['conditions'])
        for c in u['observations']['conditions']:
            self.assertEqual(d['content'][c['start']:c['end']],c['quote'])

    def test_one_task_changing_another_tasks_read_evidence_is_held(self):
        d=self.c['documents'][0];d['content']='# Runtime rule\n\nUse the stable endpoint.\n';d['sha256']=core._digest(d['content']);d['provenance']['snapshot_sha256']=d['sha256']
        d=self.c['documents'][2];d['content']='# Client guide\n\nFollow [Runtime rule](guide.md).\n';d['sha256']=core._digest(d['content']);d['provenance']['snapshot_sha256']=d['sha256']
        self.pin=core.contract_digest(self.c);self.a=self.analyze()
        left=self.proposal('REVISE','notes','Follow');left['parameters']={'operation':'COMPRESS','constraints':{}}
        right=self.proposal('REVISE','guide','stable');right.update(task_id='t2',parameters={'operation':'COMPRESS','constraints':{}})
        p=self.plan([left,right])
        self.assertEqual([t['status'] for t in p['tasks']],['held','held'])
        self.assertTrue(all('READ_WRITE_DEPENDENCY_UNRESOLVED' in t['reasons'] for t in p['tasks']))
