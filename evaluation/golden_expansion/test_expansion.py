"""Synthetic test events exist only in memory; they are never user review records."""
import copy
import tempfile
import unittest
from pathlib import Path
import review
import export
import validate
class ExpansionTests(unittest.TestCase):
    def test_dataset(self):self.assertEqual(validate.validate()['user_judgment_pending'],17)
    def test_namespaces(self):
        for cid in ['GC-001','GC-012','SP-013','SP-017']:
            self.assertFalse(review.assess(review.new_record(cid))['development_gold_eligible'])
    def test_unregistered_rejected(self):
        for cid in ['SP-001','GC-013','../SP-013']:
            with self.assertRaises(ValueError):review.new_record(cid)
    def test_no_stale_bindings(self):
        r=review.new_record('GC-001');r['input_sha256']='0'*64
        with self.assertRaises(ValueError):review.assess(r)
    def test_ai_cannot_become_user(self):
        r=review.new_record('SP-013');event=dict(event_id='test',kind='user_initial',actor_type='ai',actor_id='test-ai',recorded_at='2026-11-11T12:00:00+09:00',payload=dict(human_confirmed=True,ai_proposal_exposure='not_seen',form=dict(form_status='submitted',case_id='SP-013',input_sha256=r['input_sha256'],reviewer_id='test-ai',reviewed_at='2026-11-11T12:00:00+09:00',blinded_to_prior_judgments=True,judgment='PRESERVED',rationale='TEST ONLY',findings=[],evidence=[],missing_information=[],acceptable_alternatives=[])))
        with self.assertRaises(ValueError):review.append_event(r,event)
    def test_no_final_without_initial(self):
        r=review.new_record('GC-001')
        e=dict(event_id='test-only',kind='user_final',actor_type='human',actor_id='test',recorded_at='2026-11-11T12:00:00+09:00',payload=dict(counterreview_event_id='none',judgment='PRESERVED',rationale='TEST ONLY',evidence=[],responses=[],unresolved_issues=[],approve_for_development_gold=True,confidence_limitations=['TEST ONLY'],human_confirmed=True))
        with self.assertRaises(ValueError):review.append_event(r,e)
    def test_exclusive_save(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'record.json';review.save_new(p,review.new_record('GC-001'))
            with self.assertRaises(FileExistsError):review.save_new(p,review.new_record('GC-001'))
    def test_export_allowlist_and_determinism(self):
        f=export.payload();self.assertEqual(len([n for n in f if n.startswith('inputs/')]),17)
        self.assertFalse(any('answer' in n or 'review.json' in n for n in f))
        with tempfile.TemporaryDirectory() as d:self.assertEqual(export.build(Path(d)/'a.zip'),export.build(Path(d)/'b.zip'))

class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.record=review.new_record('GC-001');self.ev=review.load(review.resolve(review.row('GC-001')['answer_path']))['findings'][0]['evidence']
    def add(self,kind,p,actor='human'):
        self.record=review.append_event(self.record,dict(event_id=f'test-{len(self.record["events"])}',kind=kind,actor_type=actor,actor_id='test-human' if actor=='human' else 'test-ai',recorded_at='2026-11-11T12:00:00+09:00',payload=p))
    def initial(self):
        self.add('user_initial',dict(human_confirmed=True,ai_proposal_exposure='not_seen',form=dict(form_status='submitted',case_id='GC-001',input_sha256=self.record['input_sha256'],reviewer_id='test-human',reviewed_at='2026-11-11T12:00:00+09:00',blinded_to_prior_judgments=True,judgment='PRESERVED',rationale='TEST ONLY',findings=[],evidence=self.ev,missing_information=[],acceptable_alternatives=[])))
    def counter(self):
        self.add('ai_counterreview',dict(model='test-model',separate_review=True,initial_event_id=self.record['events'][-1]['event_id'],review_scope=['counterexamples','missing_conditions','contradictions'],challenges=[dict(challenge_id='c1',rationale='TEST ONLY',evidence=self.ev)],no_challenge_reason=None),'ai')
    def final(self):
        return dict(counterreview_event_id=self.record['events'][-1]['event_id'],judgment='PRESERVED',rationale='TEST ONLY',evidence=self.ev,responses=[dict(challenge_id='c1',decision='reject',rationale='TEST ONLY')],unresolved_issues=[],approve_for_development_gold=True,confidence_limitations=['TEST ONLY'],human_confirmed=True)
    def test_initial_not_gold(self):
        self.initial();self.assertFalse(review.assess(self.record)['development_gold_eligible'])
    def test_counter_not_gold(self):
        self.initial();self.counter();self.assertFalse(review.assess(self.record)['development_gold_eligible'])
    def test_final_requires_counter(self):
        self.initial()
        with self.assertRaises(ValueError):self.add('user_final',self.final())
    def test_explicit_human_final_required(self):
        self.initial();self.counter();p=self.final()
        with self.assertRaises(ValueError):self.add('user_final',p,'ai')
        p['human_confirmed']=False
        with self.assertRaises(ValueError):self.add('user_final',p)
    def test_final_with_all_gates(self):
        self.initial();self.counter();self.add('user_final',self.final());self.assertTrue(review.assess(self.record)['development_gold_eligible'])
    def test_deferred_challenge_blocks(self):
        self.initial();self.counter();p=self.final();p['responses'][0]['decision']='defer'
        with self.assertRaises(ValueError):self.add('user_final',p)
    def test_missing_response_blocks(self):
        self.initial();self.counter();p=self.final();p['responses']=[]
        with self.assertRaises(ValueError):self.add('user_final',p)
    def test_hidden_gap_blocks(self):
        self.initial();self.counter();p=self.final();p['unresolved_issues']=['TEST ONLY gap']
        with self.assertRaises(ValueError):self.add('user_final',p)
    def test_reopen_revokes(self):
        self.initial();self.counter();self.add('user_final',self.final());self.add('reopen',dict(human_confirmed=True,reason='TEST ONLY'));self.assertFalse(review.assess(self.record)['development_gold_eligible'])
    def test_history_tamper_blocks(self):
        self.initial();self.counter();self.record['events'][0]['payload']['form']['rationale']='changed'
        with self.assertRaises(ValueError):review.assess(self.record)
    def test_false_blinding_blocks(self):
        self.initial();self.record['events'][0]['payload']['ai_proposal_exposure']='seen'
        with self.assertRaises(ValueError):review.assess(self.record)

if __name__=='__main__':unittest.main()
