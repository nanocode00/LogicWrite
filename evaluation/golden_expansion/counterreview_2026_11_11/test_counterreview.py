import unittest
import run
class EvidenceTests(unittest.TestCase):
 def test_pointer_and_escaped_tokens(self):
  self.assertEqual(run.resolve({'a/b':{'~x':['exact']}},'/input/a~1b/~0x/0'),'exact')
 def test_reject_invented_quote(self):
  d=dict(case_id='X',initial_judgment='PRESERVED',independent_recommendation='PRESERVED',strongest_counterargument='x',counterargument_validity='x',remaining_uncertainty='x',user_question='x',evidence=[dict(pointer='/text',quote='invented')])
  with self.assertRaises(AssertionError):run.validate(d,dict(case_id='X',initial_judgment='PRESERVED'),dict(text='actual'))
 def test_initial_coverage(self):
  rows=run.inputs();self.assertEqual(len(rows),17);self.assertEqual(len(set(r['case_id'] for r in rows)),17)
  self.assertEqual([sum(r['initial_judgment']==k for r in rows) for k in ['PRESERVED','VIOLATION','UNRESOLVED']],[8,5,4])
if __name__=='__main__':unittest.main()
