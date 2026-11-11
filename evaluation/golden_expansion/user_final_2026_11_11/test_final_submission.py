import contextlib,copy,io,json,pathlib,shutil,tempfile,unittest
from unittest import mock
import validate_submission as v
class FinalSubmissionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.folder=pathlib.Path(self.tmp.name)/'submission';shutil.copytree(v.HERE,self.folder,ignore=shutil.ignore_patterns('__pycache__'))
  patch=mock.patch.object(v,'HERE',self.folder);patch.start();self.addCleanup(patch.stop)
 def check(self):
  with contextlib.redirect_stdout(io.StringIO()):return v.validate()
 def events(self):return json.loads((self.folder/'events.json').read_text())
 def store(self,d): (self.folder/'events.json').write_text(json.dumps(d,ensure_ascii=False))
 def test_submission_values_and_read_only(self):
  before={p:p.read_bytes() for p in self.folder.rglob('*') if p.is_file()};result=self.check()
  self.assertEqual(result['final_distribution'],{'PRESERVED':8,'VIOLATION':5,'UNRESOLVED':4});self.assertEqual(result['changed_from_initial'],0);self.assertIsNone(result['approve_for_development_gold'])
  self.assertEqual(before,{p:p.read_bytes() for p in self.folder.rglob('*') if p.is_file()})
 def test_modified_event_rejected(self):
  d=self.events();d['events'][0]['payload']['judgment']='VIOLATION';self.store(d)
  with self.assertRaises(ValueError):self.check()
 def test_deleted_event_rejected(self):
  d=self.events();d['events'].pop();self.store(d)
  with self.assertRaises(ValueError):self.check()
 def test_gold_approval_rejected(self):
  d=self.events();d['events'][0]['payload']['approve_for_development_gold']=True
  with self.assertRaises(ValueError):v.check_event(d['events'][0],v.load(self.folder/'submission.json')['cases'][0])
 def test_user_reason_not_replaced_with_ai_reason(self):
  d=self.events();d['events'][0]['payload']['rationale']='AI가 만든 추가 근거'
  with self.assertRaises(ValueError):v.check_event(d['events'][0],v.load(self.folder/'submission.json')['cases'][0])
 def test_collection_order_and_duplicates_rejected(self):
  for mutate in [lambda a:a.reverse(),lambda a:a.__setitem__(1,copy.deepcopy(a[0]))]:
   with self.subTest(mutate=mutate):
    d=self.events();mutate(d['events']);self.store(d)
    with self.assertRaises(ValueError):self.check()
 def test_review_timestamps_not_invented(self):
  for e in self.events()['events']:
   self.assertIsNone(e['user_reviewed_at']);self.assertIsNone(e['signature']);self.assertEqual(e['actor_type'],'human');self.assertEqual(e['recorder_type'],'ai')

 def test_modified_event_rejected_even_after_resealing_manifest_and_chain(self):
  d=self.events();d['events'][0]['payload']['rationale']='AI 분석을 사용자 근거로 잘못 귀속'
  previous=None
  for event in d['events']:
   event['previous_event_sha256']=previous;previous=v.event_digest(event)
  d['terminal_event_sha256']=previous;self.store(d);self.reseal_events_file()
  with self.assertRaises(ValueError):self.check()
 def test_deleted_event_rejected_after_resealing_manifest(self):
  d=self.events();d['events'].pop();self.store(d);self.reseal_events_file()
  with self.assertRaisesRegex(ValueError,'coverage/order'):self.check()
 def reseal_events_file(self):
  f=self.folder/'artifact-manifest.json';d=json.loads(f.read_text());d['events.json']=v.sha((self.folder/'events.json').read_bytes());f.write_text(json.dumps(d))
