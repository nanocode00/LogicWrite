"""G1 permission, identity, completeness and generator-input boundaries."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

import document_set as core
import ir_document_set_adapter as adapter

ROOT = Path(__file__).resolve().parents[2]


def ir(number=3):
    return json.loads((ROOT / f'evaluation/integrated_reconstruction/inputs/IR-{number:03}.json').read_text())


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


class DocumentSetTests(unittest.TestCase):
    def setUp(self):
        self.raw = ir()
        self.contract = adapter.from_ir_input(self.raw)
        self.pin = core.contract_digest(self.contract)

    def validate(self, contract=None):
        return core.validate_contract(self.contract if contract is None else contract, expected_sha256=self.pin)

    def candidates(self):
        return [{'document_id': d['document_id'], 'source_sha256':d['sha256'],
                 'source_path':d['provenance']['path'], 'content':d['content'], 'sha256':d['sha256']}
                for d in self.contract['documents'] if d['output_target']]

    def check(self, rows=None):
        return core.validate_candidates(self.contract, self.candidates() if rows is None else rows,
                                        trusted_contract_sha256=self.pin)

    def test_ir_document_counts_and_permissions_preserved_without_mutation(self):
        for n, counts in ((1, (2,0,5)), (2,(2,0,2)), (3,(0,1,2))):
            raw = ir(n); before = copy.deepcopy(raw)
            contract = adapter.from_ir_input(raw)
            report = core.validate_contract(contract)
            self.assertTrue(report['structural_input_valid'])
            self.assertEqual(tuple(sum(d['access']==a for d in contract['documents'])
                                   for a in ('edit','format_only','read_only')), counts)
            for source, doc in zip(raw['documents'],contract['documents']):
                for key in ('document_id','role','authority','access','completeness','content','sha256'):
                    self.assertEqual(doc[key], source[key])
                self.assertEqual(doc['provenance']['path'],source['path'])
            self.assertEqual(raw,before)
            self.assertFalse(report['b2_reconstruction_success'])
            self.assertEqual(report['semantic_judgment'],'unresolved')
            self.assertEqual(report['gate_state'],'REVIEW')

    def test_generic_contract_is_not_limited_to_ir_case_ids(self):
        self.contract['contract_id']='project-alpha'
        self.contract['documents'][0]['document_id']='release-notes'
        self.contract['output_scopes'][0]['document_id']='release-notes'
        self.assertTrue(core.validate_contract(self.contract)['structural_input_valid'])

    def test_duplicate_missing_document_ids_and_paths_are_rejected(self):
        for mutate in (lambda c:c['documents'].append(copy.deepcopy(c['documents'][0])),
                       lambda c:c['documents'][0].pop('document_id'),
                       lambda c:c['documents'][1].update(document_id=c['documents'][0]['document_id']),
                       lambda c:c['documents'][1]['provenance'].update(path=c['documents'][0]['provenance']['path'])):
            c=copy.deepcopy(self.contract); mutate(c)
            self.assertFalse(core.validate_contract(c)['structural_input_valid'])

    def test_hash_provenance_origin_and_output_scope_corruption_rejected(self):
        mutations=(lambda c:c['documents'][0].update(sha256='0'*64),
                   lambda c:c['documents'][0]['provenance'].update(snapshot_sha256='0'*64),
                   lambda c:c['documents'][0]['provenance'].update(source_id='other-origin'),
                   lambda c:c['output_scopes'].clear(),
                   lambda c:c['output_scopes'].append({'scope_id':'x','document_id':'absent'}),
                   lambda c:c['output_scopes'].append(copy.deepcopy(c['output_scopes'][0])),
                   lambda c:c['documents'][0].update(output_target=False),
                   lambda c:c['documents'].pop())
        for mutate in mutations:
            c=copy.deepcopy(self.contract); mutate(c)
            self.assertFalse(core.validate_contract(c,expected_sha256=self.pin)['structural_input_valid'])

    def test_read_only_cannot_be_promoted_even_if_all_internal_hashes_recomputed(self):
        self.contract['documents'][1].update(access='edit',output_target=True)
        self.contract['output_scopes'].append({'scope_id':'extra','document_id':'experiment'})
        self.contract['documents'][1]['provenance']['path']='forged.md'
        result=self.validate()
        self.assertFalse(result['structural_input_valid'])
        result=self.check()
        self.assertEqual(result['gate_state'],'FAIL')

    def test_permission_operations_distinguish_edit_format_and_reference(self):
        c=adapter.from_ir_input(ir(1)); pin=core.contract_digest(c)
        edit=next(d['document_id'] for d in c['documents'] if d['access']=='edit')
        ro=next(d['document_id'] for d in c['documents'] if d['access']=='read_only')
        for doc,op,status in ((edit,'edit_content','eligible'),(edit,'format','eligible'),
                              (ro,'reference','eligible'),(ro,'edit_content','denied'),
                              (ro,'format','denied'),('missing','edit_content','denied')):
            self.assertEqual(core.check_operation(c,doc,op,trusted_contract_sha256=pin)['status'],status)
        for op,want in (('edit_content','denied'),('format','eligible'),('reference','eligible'),
                        ('external_lookup','unsupported'),('create_document','unsupported'),
                        ('apply_files','unsupported'),('something_new','unsupported')):
            r=core.check_operation(self.contract,'meeting',op,trusted_contract_sha256=self.pin)
            self.assertEqual(r['status'],want)
            self.assertFalse(r['execution_allowed'])

    def test_no_pin_or_wrong_pin_cannot_authorize_operations_or_candidates(self):
        for pin in (None,'0'*64):
            self.assertEqual(core.check_operation(self.contract,'meeting','format',trusted_contract_sha256=pin)['status'],'denied')
            self.assertEqual(core.validate_candidates(self.contract,self.candidates(),trusted_contract_sha256=pin)['gate_state'],'FAIL')

    def test_partial_unknown_and_pending_access_are_held(self):
        mutations=(lambda c:c.update(document_set_completeness='partial'),
                   lambda c:c['documents'][0].update(completeness='excerpt',source_scope='first section'),
                   lambda c:c['documents'][0].update(access='pending'),
                   lambda c:c['documents'][0].update(role=None),
                   lambda c:c['documents'][0]['pending_questions'].append('Confirm editing authority'))
        for mutate in mutations:
            c=copy.deepcopy(self.contract); mutate(c)
            # Pending target must be removed; no unconfirmed output authorization.
            if c['documents'][0]['access']=='pending':
                c['documents'][0]['output_target']=False; c['output_scopes']=[]
            r=core.validate_contract(c)
            self.assertTrue(r['structural_input_valid'],r)
            self.assertFalse(r['ready_for_planning'])
            self.assertEqual(r['gate_state'],'REVIEW')
            pin=core.contract_digest(c)
            self.assertEqual(core.check_operation(c,'meeting','format',trusted_contract_sha256=pin)['status'],'held')

    def test_noop_full_candidates_allowed_without_semantic_pass_or_generation(self):
        r=self.check()
        self.assertEqual(r['permission_status'],'within_declared_access')
        self.assertEqual(r['gate_state'],'REVIEW')
        self.assertEqual(r['semantic_judgment'],'unresolved')
        self.assertFalse(r['b2_reconstruction_success'])
        self.assertFalse(r['delivery_approved'])
        self.assertFalse(r['stage_transition_allowed'])

    def test_format_only_changed_content_requires_review_even_for_whitespace(self):
        for transform in (lambda s:s.replace('실패다.','실패.'),lambda s:s+'\n',lambda s:s.replace('12','13')):
            rows=self.candidates(); rows[0]['content']=transform(rows[0]['content']); rows[0]['sha256']=digest(rows[0]['content'])
            r=self.check(rows)
            self.assertEqual(r['permission_status'],'unresolved')
            self.assertIn('FORMAT_CHANGE_REQUIRES_REVIEW',r['reasons'])
            self.assertEqual(r['gate_state'],'REVIEW')

    def test_edit_candidate_is_only_permission_eligible(self):
        self.contract=adapter.from_ir_input(ir(2)); self.pin=core.contract_digest(self.contract)
        rows=self.candidates();rows[0]['content']='Unreviewed replacement';rows[0]['sha256']=digest(rows[0]['content'])
        r=self.check(rows)
        self.assertEqual(r['permission_status'],'within_declared_access')
        self.assertEqual(r['semantic_judgment'],'unresolved')

    def test_missing_duplicate_extra_readonly_and_corrupt_candidate_rejected(self):
        ro=self.contract['documents'][1]
        mutations=(lambda rows:rows.clear(),lambda rows:rows.append(copy.deepcopy(rows[0])),
                   lambda rows:rows.append(dict(rows[0],document_id='absent')),
                   lambda rows:rows.append({'document_id':ro['document_id'],'content':ro['content'],
                       'sha256':ro['sha256'],'source_sha256':ro['sha256'],'source_path':ro['provenance']['path']}),
                   lambda rows:rows[0].update(source_sha256='0'*64),
                   lambda rows:rows[0].update(source_path='other.md'),
                   lambda rows:rows[0].update(sha256='0'*64),
                   lambda rows:rows[0].update(final_checks='PASS'))
        for mutate in mutations:
            rows=self.candidates();mutate(rows)
            self.assertEqual(self.check(rows)['gate_state'],'FAIL')

    def test_partial_contract_candidate_cannot_claim_permission_clearance(self):
        self.contract['documents'][0]['completeness']='excerpt'
        self.contract['documents'][0]['source_scope']='section 1'
        self.pin=core.contract_digest(self.contract)
        self.assertEqual(self.check()['permission_status'],'unresolved')

    def test_adapter_rejects_gold_and_review_fields_at_every_known_boundary(self):
        for key in ('answers','gold','criteria','reviews','expected_output','final_verdict'):
            for target in ('root','document'):
                raw=copy.deepcopy(self.raw)
                obj=raw if target=='root' else raw['documents'][0]
                obj[key]='SENTINEL_EVALUATOR_ONLY'
                with self.assertRaises(ValueError): adapter.from_ir_input(raw)
        contract=adapter.from_ir_input(self.raw)
        self.assertEqual(contract['request'],self.raw['request'])
        self.assertEqual(contract['context'],self.raw['context'])
        self.assertEqual(contract['explicit_constraints'],self.raw['explicit_constraints'])
        self.assertEqual(contract['pending_questions'],self.raw['availability']['gaps'])

    def test_adapter_refuses_corrupt_ir_hash_duplicate_id_and_path(self):
        for mutate in (lambda r:r['documents'][0].update(sha256='0'*64),
                       lambda r:r['documents'].append(copy.deepcopy(r['documents'][0])),
                       lambda r:r['documents'][1].update(path=r['documents'][0]['path'])):
            raw=copy.deepcopy(self.raw); mutate(raw)
            with self.assertRaises(ValueError): adapter.from_ir_input(raw)

    def test_ir_v2_excerpt_metadata_preserved_but_held(self):
        raw=copy.deepcopy(self.raw); raw['schema_version']='integrated-input-v2'
        raw['availability']['document_set']='partial'
        raw['documents'][0].update(completeness='excerpt',source_scope='provided excerpt only',role=None)
        contract=adapter.from_ir_input(raw)
        self.assertEqual(contract['documents'][0]['source_scope'],'provided excerpt only')
        r=core.validate_contract(contract)
        self.assertTrue(r['structural_input_valid']); self.assertFalse(r['ready_for_planning'])

    def test_untrusted_extra_core_fields_and_malformed_values_fail_closed(self):
        for value in (None,[],{},dict(self.contract,gold='hidden'),dict(self.contract,documents=[None])):
            r=core.validate_contract(value)
            self.assertFalse(r['structural_input_valid'])
            self.assertEqual(r['gate_state'],'FAIL')
        for rows in (None,{},[None],[{}]): self.assertEqual(self.check(rows if rows is not None else {})['gate_state'],'FAIL')

    def test_reconstruction_remains_explicitly_unsupported(self):
        r=core.prepare_reconstruction(self.contract,trusted_contract_sha256=self.pin)
        self.assertEqual(r['status'],'unsupported')
        self.assertEqual(r['execution_state'],'not_run')
        self.assertEqual(r['reason'],'DOCUMENT_SET_RECONSTRUCTION_NOT_IMPLEMENTED')
        self.assertFalse(r['b2_reconstruction_success'])
        self.assertNotIn('candidate_documents',r)

    def test_malformed_operation_values_never_raise_or_authorize(self):
        for op in (None,[],{},True,1):
            r=core.check_operation(self.contract,'meeting',op,trusted_contract_sha256=self.pin)
            self.assertEqual(r['status'],'unsupported')
            self.assertFalse(r['execution_allowed'])

    def test_malformed_adapter_version_fails_with_explicit_input_error(self):
        for version in (None,[],{},True,1):
            raw=copy.deepcopy(self.raw); raw['schema_version']=version
            with self.assertRaises(ValueError): adapter.from_ir_input(raw)

    def test_editable_evidence_can_remain_outside_output_scope(self):
        # Access and delivery are distinct: edit eligibility alone does not submit a document.
        contract=adapter.from_ir_input(ir(2))
        contract['documents'][0]['output_target']=False
        omitted=contract['documents'][0]['document_id']
        contract['output_scopes']=[s for s in contract['output_scopes'] if s['document_id']!=omitted]
        r=core.validate_contract(contract)
        self.assertTrue(r['structural_input_valid'])
        pin=core.contract_digest(contract)
        r=core.check_operation(contract,omitted,'edit_content',trusted_contract_sha256=pin)
        self.assertEqual(r['status'],'denied')
        self.assertEqual(core.check_operation(contract,omitted,'reference',trusted_contract_sha256=pin)['status'],'eligible')

    def test_internal_bindings_fail_without_relying_on_external_digest_mismatch(self):
        mutations=(('SOURCE_SHA256_MISMATCH',lambda c:c['documents'][0].update(content='tampered')),
                   ('SOURCE_PROVENANCE_MISMATCH',lambda c:c['documents'][0]['provenance'].update(snapshot_sha256='0'*64)),
                   ('SOURCE_PROVENANCE_MISMATCH',lambda c:c['documents'][0]['provenance'].update(source_id='wrong')),
                   ('OUTPUT_SCOPE_SET_MISMATCH',lambda c:c['output_scopes'].clear()),
                   ('OUTPUT_ACCESS_MISMATCH',lambda c:c['documents'][1].update(output_target=True)),
                   ('INVALID_SOURCE_PATH',lambda c:c['documents'][0]['provenance'].update(path='../meeting.md')))
        for reason,mutate in mutations:
            c=copy.deepcopy(self.contract);mutate(c)
            r=core.validate_contract(c)
            self.assertFalse(r['structural_input_valid'])
            self.assertIn(reason,r['reasons'])

    def test_readonly_changed_candidate_and_spoofed_permissions_are_rejected(self):
        ro=self.contract['documents'][1]
        text=ro['content']+'Unauthorized change'
        rows=self.candidates()+[{'document_id':ro['document_id'],'source_sha256':ro['sha256'],
            'source_path':ro['provenance']['path'],'content':text,'sha256':digest(text)}]
        r=self.check(rows)
        self.assertEqual(r['permission_status'],'denied')
        self.assertIn('UNAUTHORIZED_OUTPUT_DOCUMENT',r['reasons'])
        rows=self.candidates();rows[0]['access']='edit'
        self.assertEqual(self.check(rows)['gate_state'],'FAIL')
