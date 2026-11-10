"""Synthetic in-memory workflow tests; these are not actual human review records."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from workflow import new_record, append_event, assess, save_new, assess_independent_record

PILOT = Path(__file__).resolve().parents[1]

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.record = new_record('SP-003')
        self.inp = json.loads((PILOT / 'inputs/SP-003.json').read_text())
        self.evidence = json.loads((PILOT / 'answers/SP-003.json').read_text())['findings'][0]['evidence']

    def event(self, kind, payload, actor='human'):
        return dict(event_id=f'test-{len(self.record["events"])+1}', kind=kind,
                    actor_type=actor, actor_id='test-user' if actor=='human' else 'test-ai',
                    recorded_at='2026-11-10T17:00:00+09:00', payload=payload)

    def add(self, kind, payload, actor='human'):
        self.record = append_event(self.record, self.event(kind, payload, actor))

    def initial(self):
        form = dict(form_status='submitted', case_id='SP-003', input_sha256=self.record['input_sha256'],
                    reviewer_id='test-user', reviewed_at='2026-11-10T17:00:00+09:00',
                    blinded_to_prior_judgments=False, judgment='UNRESOLVED', rationale='TEST ONLY: context missing',
                    findings=[], evidence=self.evidence, missing_information=['TEST ONLY: first-use context'],
                    acceptable_alternatives=[])
        self.add('user_initial', dict(form=form, human_confirmed=True, ai_proposal_exposure='seen'))

    def counter(self, challenges=True):
        self.add('ai_counterreview', dict(model='test-model', separate_review=True,
            initial_event_id=self.record['events'][-1]['event_id'],
            review_scope=['counterexamples','missing_conditions','contradictions'],
            challenges=[dict(challenge_id='c1', rationale='TEST ONLY: could local exposure be mandatory?',
                             evidence=self.evidence)] if challenges else [],
            no_challenge_reason=None if challenges else 'TEST ONLY: no counterexample found within provided context'), 'ai')

    def final_payload(self):
        return dict(counterreview_event_id=self.record['events'][-1]['event_id'] if self.record['events'] else 'absent',
                    judgment='UNRESOLVED', rationale='TEST ONLY: await context', evidence=self.evidence,
                    responses=[dict(challenge_id='c1', decision='accept', rationale='TEST ONLY: request context')],
                    unresolved_issues=['TEST ONLY: context not supplied'], approve_for_development_gold=True,
                    confidence_limitations=['TEST ONLY: single human and AI assistance'], human_confirmed=True)

    def finalized(self):
        self.initial(); self.counter(); self.add('user_final', self.final_payload())

    def test_blank_record_is_only_ai_provisional(self):
        result=assess(self.record)
        self.assertEqual(result['review_level'], 'ai_provisional')
        self.assertFalse(result['development_gold_eligible'])
        self.assertFalse(result['independent_multi_human_complete'])

    def test_initial_exposure_retained(self):
        self.initial()
        self.assertEqual(assess(self.record)['review_level'],'user_initial_reviewed')
        self.assertFalse(self.record['events'][0]['payload']['form']['blinded_to_prior_judgments'])

    def test_ai_counterreview_not_gold(self):
        self.initial(); self.counter()
        self.assertEqual(assess(self.record)['review_level'],'ai_counterreview_completed')
        self.assertFalse(assess(self.record)['development_gold_eligible'])

    def test_single_user_final_is_development_only(self):
        self.finalized(); result=assess(self.record)
        self.assertEqual(result['review_level'],'user_final_confirmed')
        self.assertTrue(result['development_gold_eligible'])
        self.assertFalse(result['independent_multi_human_complete'])
        self.assertEqual(result['final_judgment'],'UNRESOLVED')

    def test_no_automatic_final_without_initial(self):
        with self.assertRaises(ValueError): self.add('user_final',self.final_payload())

    def test_no_final_without_counterreview(self):
        self.initial()
        with self.assertRaises(ValueError): self.add('user_final',self.final_payload())

    def test_ai_cannot_sign_user_final(self):
        self.initial(); self.counter()
        with self.assertRaises(ValueError): self.add('user_final',self.final_payload(),'ai')

    def test_no_user_confirmation(self):
        self.initial(); self.counter(); p=self.final_payload();p['human_confirmed']=False
        with self.assertRaises(ValueError): self.add('user_final',p)

    def test_all_challenges_need_response(self):
        self.initial(); self.counter();p=self.final_payload();p['responses']=[]
        with self.assertRaises(ValueError): self.add('user_final',p)

    def test_deferral_prevents_gold(self):
        self.initial(); self.counter();p=self.final_payload();p['responses'][0]['decision']='defer'
        with self.assertRaises(ValueError): self.add('user_final',p)
        p['approve_for_development_gold']=False;self.add('user_final',p)
        self.assertFalse(assess(self.record)['development_gold_eligible'])

    def test_no_challenge_still_needs_rationale(self):
        self.initial();self.counter(False);p=self.final_payload();p['responses']=[]
        self.add('user_final',p);self.assertTrue(assess(self.record)['development_gold_eligible'])

    def test_no_empty_ai_counterreview(self):
        self.initial();self.counter(False);bad=copy.deepcopy(self.record)
        bad['events'][-1]['payload']['no_challenge_reason']=None
        with self.assertRaises(ValueError): assess(bad)

    def test_reopen_revokes_eligibility_preserves_history(self):
        self.finalized();old=copy.deepcopy(self.record['events'])
        self.add('reopen',dict(reason='TEST ONLY: new context',human_confirmed=True))
        self.assertEqual(self.record['events'][:-1],old)
        self.assertEqual(assess(self.record)['review_level'],'reopened')
        self.assertFalse(assess(self.record)['development_gold_eligible'])
        self.initial();self.counter();p=self.final_payload();p.update(judgment='PRESERVED',unresolved_issues=[],rationale='TEST ONLY: context resolved')
        self.add('user_final',p);self.assertEqual(assess(self.record)['final_judgment'],'PRESERVED')
        self.assertEqual(self.record['events'][:3],old)

    def test_bound_input_and_proposal(self):
        for field in ['input_sha256','ai_proposal_sha256']:
            bad=copy.deepcopy(self.record);bad[field]='0'*64
            with self.assertRaises(ValueError):assess(bad)

    def test_invalid_evidence_rejected(self):
        self.initial();self.counter();p=self.final_payload();p['evidence']=copy.deepcopy(self.evidence);p['evidence'][0]['quote']='invented'
        with self.assertRaises(ValueError):self.add('user_final',p)

    def test_wrong_initial_case(self):
        self.initial();bad=copy.deepcopy(self.record);bad['events'][0]['payload']['form']['case_id']='SP-001'
        with self.assertRaises(ValueError):assess(bad)

    def test_ai_must_review_current_initial(self):
        self.initial();self.counter();bad=copy.deepcopy(self.record);bad['events'][-1]['payload']['initial_event_id']='absent'
        with self.assertRaises(ValueError):assess(bad)

    def test_wrong_counterreview_binding(self):
        self.initial();self.counter();p=self.final_payload();p['counterreview_event_id']='absent'
        with self.assertRaises(ValueError):self.add('user_final',p)

    def test_no_injected_status_or_eligibility(self):
        bad=copy.deepcopy(self.record);bad['gold_eligible']=True
        with self.assertRaises(ValueError):assess(bad)

    def test_independent_method_cannot_be_claimed(self):
        bad=copy.deepcopy(self.record);bad['method']='independent_multi_human'
        with self.assertRaises(ValueError):assess(bad)

    def test_hash_chain_detects_history_edit(self):
        self.initial();self.counter();bad=copy.deepcopy(self.record);bad['events'][0]['payload']['form']['rationale']='edited'
        with self.assertRaises(ValueError):assess(bad)

    def independent_answer(self):
        answer=json.loads((PILOT/'answers/SP-003.json').read_text())
        # Test-only in-memory upper-level records; never persisted as real review.
        base=copy.deepcopy(answer['reviews'][0]);base['blinded_to_ai_proposal']=True
        answer['reviews']=[dict(base,reviewer_id=who,judgment='PRESERVED') for who in ['test-a','test-b']]
        answer.update(status='adjudicated',gold_eligible=True,adjudication=dict(
            adjudicator_id='test-c',adjudicated_at='2026-11-10T18:00:00+09:00',
            judgment='PRESERVED',rationale='TEST ONLY',input_sha256=answer['input_sha256']))
        return answer

    def test_upper_level_is_separate_and_legacy_validated(self):
        result=assess_independent_record(self.independent_answer())
        self.assertEqual(result['review_level'],'independent_multi_human_adjudicated')
        self.assertTrue(result['independent_multi_human_complete'])
        self.assertTrue(result['legacy_gold_eligible'])

    def test_upper_level_rejects_single_human(self):
        answer=self.independent_answer();answer['reviews']=answer['reviews'][:1]
        with self.assertRaises(ValueError):assess_independent_record(answer)

    def test_upper_level_rejects_exposed_review(self):
        answer=self.independent_answer();answer['reviews'][0]['blinded_to_ai_proposal']=False
        with self.assertRaises(ValueError):assess_independent_record(answer)

    def test_upper_level_rejects_same_adjudicator(self):
        answer=self.independent_answer();answer['adjudication']['adjudicator_id']='test-a'
        with self.assertRaises(ValueError):assess_independent_record(answer)

    def test_user_identity_cannot_switch(self):
        self.initial();self.counter();event=self.event('user_final',self.final_payload());event['actor_id']='other-human'
        with self.assertRaises(ValueError):append_event(self.record,event)

    def test_initial_unsubmitted_form_rejected(self):
        self.initial();bad=copy.deepcopy(self.record);bad['events'][0]['payload']['form']['form_status']='blank'
        with self.assertRaises(ValueError):assess(bad)

    def test_final_bound_to_latest_review_after_reopen(self):
        self.finalized();old_counter=self.record['events'][1]['event_id']
        self.add('reopen',dict(reason='TEST ONLY',human_confirmed=True));self.initial();self.counter()
        payload=self.final_payload();payload['counterreview_event_id']=old_counter
        with self.assertRaises(ValueError):self.add('user_final',payload)

    def test_final_does_not_allow_hidden_unresolved_conditions(self):
        self.initial();self.counter();payload=self.final_payload();payload['judgment']='PRESERVED'
        with self.assertRaises(ValueError):self.add('user_final',payload)

    def test_exposure_cannot_be_retroactively_blinded(self):
        self.initial();bad=copy.deepcopy(self.record)
        bad['events'][0]['payload']['form']['blinded_to_prior_judgments']=True
        with self.assertRaises(ValueError):assess(bad)

    def test_upper_sidecar_preserves_original_ai_label(self):
        answer=self.independent_answer();answer['expected_judgment']='UNRESOLVED'
        with self.assertRaises(ValueError):assess_independent_record(answer)

    def test_templates_are_not_completed_review_records(self):
        folder=Path(__file__).parent/'templates'
        for path in folder.glob('*.json'):
            with self.subTest(template=path.name), self.assertRaises(ValueError):
                append_event(self.record,json.loads(path.read_text()))

    def test_legacy_data_is_never_changed(self):
        lock=json.loads((PILOT/'independent_review/preserved-files.json').read_text())
        import hashlib
        for name, expected in lock['files'].items():
            self.assertEqual(hashlib.sha256((PILOT/name).read_bytes()).hexdigest(),expected)

    def test_write_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'record.json';save_new(path,self.record)
            with self.assertRaises(FileExistsError):save_new(path,self.record)

if __name__=='__main__':unittest.main()
