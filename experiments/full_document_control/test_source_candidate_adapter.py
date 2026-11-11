"""Evaluation-only adapter: synthetic fixtures, no reference labels."""
import copy
import hashlib
import unittest
import final_semantic_validator as semantic
try:
    import source_candidate_adapter as adapter
except ImportError:
    adapter = None


def doc(name='a', text='지원한다. 제한은 30초다.', version='v1'):
    return {'document_id': name, 'version': version, 'availability': 'complete', 'content': text,
            'sha256': hashlib.sha256(text.encode()).hexdigest(), 'provenance': {
                'kind': 'controlled_synthetic', 'repository': None, 'path': name+'.md',
                'version': version, 'git_blob_sha': None, 'url': None, 'snapshot_path': None,
                'snapshot_sha256': None, 'captured_on': '2026-11-11'}}


def fixture():
    return {'schema_version':'0.1.0','case_id':'SP-099','task':'Compare all documents',
        'source_kind':'controlled_synthetic','construction':'Synthetic test only',
        'source_documents':[doc()], 'candidate_documents':[doc(version='candidate-v1')],
        'writing_contract': {'contract_id':'test','version':'1','audience':'readers','purpose':'preserve',
            'language':'ko','output_document_ids':['a'],'required_information':[
                {'id':'R1','description':'Preserve limitation and support condition','exposure':'same_document'}],
            'constraints':['Preserve all claims; moving requires linked context']},
        'missing_context':[], 'supplied_observations':[]}


def review(request, judgment='supported'):
    evidence=[]
    for side, key in [('source','source_snapshots'),('output','output_snapshots')]:
        for s in request[key]:
            if s['content']:
                evidence.append({'side':side,'document_id':s['document_id'], 'snapshot_sha256':s['sha256'],
                    'start':0,'end':len(s['content']),'quote':s['content']})
    return {'request_sha256': request['request_sha256'], 'reviews':[
        {'check_id':c,'judgment':judgment,'reason':'Reviewed complete supplied pair only',
         'reviewed_refs':request['snapshot_refs'],'evidence':copy.deepcopy(evidence)} for c in request['required_checks']]}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(adapter, 'source/candidate evaluation adapter is missing')
        self.raw=fixture()

    def test_equality_without_reviewer_is_unresolved_and_has_no_receipt(self):
        before=copy.deepcopy(semantic._RECEIPTS)
        result=adapter.evaluate(self.raw)
        self.assertEqual((result['status'],result['gate_state'],result['semantic_judgment'],result['evaluated']),
                         ('unsupported','REVIEW','unresolved',False))
        self.assertEqual(semantic._RECEIPTS,before)

    def test_full_cited_review_supports_only_advisory_evaluation(self):
        original=copy.deepcopy(self.raw)
        seen=[]
        def reviewer(req):
            seen.append(req)
            return review(req)
        result=adapter.evaluate(self.raw,reviewer=reviewer)
        self.assertEqual((result['status'],result['gate_state'],result['semantic_judgment'],result['evaluated']),
                         ('evaluated','REVIEW','supported',True))
        self.assertEqual(seen[0]['writing_contract'],original['writing_contract'])
        self.assertEqual(self.raw,original)
        self.assertFalse(result['delivery_approved']);self.assertFalse(result['stage_transition_allowed'])
        self.assertNotIn(result['semantic_report']['report_sha256'],semantic._RECEIPTS)

    def test_multidocument_move_is_complete_pair_not_forged_lineage(self):
        self.raw['source_documents'].append(doc('b','조건은 별도 문서에 있다.'))
        self.raw['candidate_documents'].append(doc('b','조건은 별도 문서에 있다.', 'candidate'))
        self.raw['writing_contract']['output_document_ids'].append('b')
        self.raw['writing_contract']['required_information'][0]['exposure']='linked_document'
        result=adapter.evaluate(self.raw,reviewer=review)
        self.assertTrue(result['evaluated'])
        self.assertEqual(len(result['semantic_report']['snapshot_refs']),4)

    def test_missing_context_pending_contract_and_unknown_baseline_are_unsupported(self):
        for mutate in [lambda r:r['missing_context'].append('Missing baseline authority'),
                       lambda r:r['writing_contract']['required_information'][0].update(exposure='pending_contract'),
                       lambda r:r['source_documents'][0].update(document_id='a-v2')]:
            raw=fixture();mutate(raw)
            result=adapter.evaluate(raw,reviewer=review)
            self.assertEqual(result['status'],'unsupported');self.assertFalse(result['evaluated'])

    def test_incomplete_or_unbound_metadata_never_reaches_reviewer(self):
        mutations=[lambda d:d.update(availability='partial'), lambda d:d.pop('availability'),
                   lambda d:d.update(sha256='0'*64),lambda d:d.pop('version'),
                   lambda d:d['provenance'].update(version='wrong'), lambda d:d.pop('provenance')]
        for mutate in mutations:
            raw=fixture();mutate(raw['candidate_documents'][0])
            calls=[]
            def callback(r):
                calls.append(r);return review(r)
            result=adapter.evaluate(raw,reviewer=callback)
            self.assertEqual(calls,[])
            self.assertEqual(result['status'],'unsupported');self.assertFalse(result['evaluated'])

    def test_public_git_blob_identity_is_bound_to_full_supplied_content(self):
        source=self.raw['source_documents'][0]
        p=source['provenance']
        p.update(kind='public_git',repository='example/repo',url='https://example.test/source',
                 snapshot_path='never-open-this-file',snapshot_sha256=source['sha256'],git_blob_sha='0'*40)
        self.raw['source_kind']='public_source_based'
        result=adapter.evaluate(self.raw,reviewer=review)
        self.assertFalse(result['evaluated'])
        self.assertIn('PUBLIC_GIT_BLOB_MISMATCH',result['reasons'])

    def test_native_missing_coverage_stays_legacy_organization_only(self):
        import integration
        import organization
        import reconstruction
        from test_integration import contract
        bundle=integration.markdown_bundle('# Source\n',contract())
        bundle['writing_contract']['output_scopes'].append({'scope_id':'details','document_id':'details'})
        text='# Details\n'
        snap={'document_id':'details','version':'1','content':text,
              'sha256':hashlib.sha256(text.encode()).hexdigest()}
        self.assertTrue(organization.evaluate_destination_scope(
            {'scope_id':'details','kind':'document','document_id':'details'},bundle,
            destination_snapshots=[snap])['allows_confirmed_move'])
        with self.assertRaises(reconstruction.IncompleteSnapshot):
            reconstruction.source_documents(bundle,[snap])
        self.raw['candidate_documents'][0].pop('availability')
        self.assertEqual(adapter.evaluate(self.raw,reviewer=review)['status'],'unsupported')

    def test_unknown_version_and_source_kind_provenance_mismatch_are_unsupported(self):
        self.raw['source_documents'][0]['version']='unknown'
        self.raw['source_documents'][0]['provenance']['version']='unknown'
        self.assertFalse(adapter.evaluate(self.raw,reviewer=review)['evaluated'])
        self.raw=fixture();self.raw['source_kind']='public_source_based'
        self.assertFalse(adapter.evaluate(self.raw,reviewer=review)['evaluated'])

    def test_public_provenance_requires_pinned_matching_repository_path_version(self):
        source=self.raw['source_documents'][0];p=source['provenance']
        version='a'*40;source['version']=version;p['version']=version
        encoded=source['content'].encode()
        p.update(kind='public_git',repository='org/repo',path='doc.md',snapshot_path='unread',
            snapshot_sha256=source['sha256'],git_blob_sha=hashlib.sha1(
                b'blob '+str(len(encoded)).encode()+b'\0'+encoded).hexdigest(),
            url='https://raw.githubusercontent.com/org/repo/'+version+'/doc.md')
        self.raw['source_kind']='public_source_based'
        self.assertTrue(adapter.evaluate(self.raw,reviewer=review)['evaluated'])
        for url in ['https://evil.test/org/repo/'+version+'/doc.md',
                    'https://raw.githubusercontent.com/org/repo/main/doc.md',
                    'https://raw.githubusercontent.com/org/repo/'+version+'/other.md']:
            p['url']=url
            self.assertFalse(adapter.evaluate(self.raw,reviewer=review)['evaluated'])

    def test_review_coverage_and_definitive_contradiction(self):
        def incomplete(r):
            out=review(r);out['reviews'].pop();return out
        def unresolved(r):return review(r,'unresolved')
        def forged_ref(r):
            out=review(r);out['reviews'][0]['reviewed_refs'][0]['version']='forged';return out
        for callback in (incomplete,unresolved,forged_ref):
            self.assertFalse(adapter.evaluate(self.raw,reviewer=callback)['evaluated'])
        result=adapter.evaluate(self.raw,reviewer=lambda r:review(r,'contradicted'))
        self.assertEqual((result['evaluated'],result['gate_state'],result['semantic_judgment']),
                         (True,'FAIL','contradicted'))

    def test_callback_mutation_cannot_change_caller_input_or_bound_request(self):
        before=copy.deepcopy(self.raw)
        def mutate(r):
            r['source_snapshots'][0]['content']='invented'
            return review(r)
        result=adapter.evaluate(self.raw,reviewer=mutate)
        self.assertEqual(self.raw,before)
        self.assertFalse(result['evaluated'])

    def test_low_level_public_api_cannot_bypass_pending_or_missing_context(self):
        raw=fixture()
        snapshots=[]
        for side in ('source_documents','candidate_documents'):
            d=copy.deepcopy(raw[side][0]);d.update(coverage='complete',snapshot_id=side)
            snapshots.append([d])
        for contract,context in [(dict(raw['writing_contract'],required_information=[
                {'id':'R1','description':'Pending','exposure':'pending_contract'}]),{}),
                (raw['writing_contract'],{'missing_context':['unavailable']})]:
            calls=[]
            def callback(r):
                calls.append(r);return review(r)
            report=semantic.evaluate_snapshot_pair(*snapshots,contract,context=context,reviewer=callback)
            self.assertEqual(calls,[])
            self.assertEqual(report['overall_judgment'],'unresolved')
            self.assertEqual(report['gate_state'],'REVIEW')

    def test_low_level_snapshot_identifiers_and_versions_require_nonblank_strings(self):
        raw=fixture()
        for field,value in [('version','   '),('document_id',' '),('snapshot_id',' '),('version',1)]:
            source=dict(copy.deepcopy(raw['source_documents'][0]),coverage='complete',snapshot_id='source')
            output=dict(copy.deepcopy(raw['candidate_documents'][0]),coverage='complete',snapshot_id='output')
            source[field]=value
            report=semantic.evaluate_snapshot_pair([source],[output],raw['writing_contract'],
                reviewer=lambda r:self.fail('Invalid metadata reached reviewer'))
            self.assertEqual(report['execution']['state'],'invalid_input')
        raw['source_documents'][0]['version']='   '
        raw['source_documents'][0]['provenance']['version']='   '
        self.assertEqual(adapter.evaluate(raw,reviewer=review)['status'],'unsupported')

    def test_answer_fields_are_rejected(self):
        self.raw['gold_label']='PRESERVED'
        self.assertEqual(adapter.evaluate(self.raw)['status'],'invalid_input')

    def test_literal_difference_without_model_remains_unresolved(self):
        self.raw['candidate_documents']=[doc(text='지원한다. 제한은 60초다.',version='candidate')]
        result=adapter.evaluate(self.raw)
        self.assertEqual((result['gate_state'],result['semantic_judgment'],result['evaluated']),('REVIEW','unresolved',False))

    def test_invalid_or_approval_response_budget_timeout_never_evaluated(self):
        import time
        def approval(r):
            out=review(r);out['delivery_approved']=True;return out
        def malformed(r):
            out=review(r);out['reviews'][0]['evidence'][0]['quote']='invented';return out
        for reviewer, kwargs in [(approval,{}),(malformed,{}),(review,{'max_review_chars':1}),
                (lambda r:(time.sleep(.05),review(r))[1],{'timeout_seconds':.001})]:
            result=adapter.evaluate(self.raw,reviewer=reviewer,**kwargs)
            self.assertFalse(result['evaluated']);self.assertNotEqual(result['semantic_judgment'],'supported')

if __name__=='__main__':unittest.main()
