import unittest
import validate
class CounterreviewValidationTests(unittest.TestCase):
 def test_exact_pointer_quote(self):
  validate.check_quote({'a/b':['보존 문자열']},{'pointer':'/a~1b/0','quote':'보존'})
 def test_wrong_quote_rejected(self):
  with self.assertRaises(ValueError):validate.check_quote({'text':'실제'},{'pointer':'/text','quote':'발명'})
 def test_object_not_string(self):
  with self.assertRaises(ValueError):validate.check_quote({'text':{'a':'x'}},{'pointer':'/text','quote':'x'})
 def test_negative_index_rejected(self):
  with self.assertRaises(ValueError):validate.check_quote({'text':['x']},{'pointer':'/text/-1','quote':'x'})
 def test_wrong_id_rejected(self):
  with self.assertRaises(ValueError):validate.check_identity({'case_id':'other','input_sha256':'abc','initial_judgment':'PRESERVED'},{'case_id':'X','input_sha256':'abc','initial_judgment':'PRESERVED'})
 def test_missing_initial_binding_rejected(self):
  with self.assertRaises(ValueError):validate.check_identity({'case_id':'X','input_sha256':'abc'},{'case_id':'X','input_sha256':'abc','initial_judgment':'PRESERVED'})

import contextlib
import io
import json
import pathlib
import shutil
import tempfile
from unittest import mock

class PackageFixture:
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.package=pathlib.Path(self.tmp.name)/'package'
  shutil.copytree(validate.OUT,self.package,ignore=shutil.ignore_patterns('__pycache__'))
  manifest=json.loads((self.package/'artifact-manifest.json').read_text())
  for name in manifest:manifest[name]=validate.sha((self.package/name).read_bytes())
  (self.package/'artifact-manifest.json').write_text(json.dumps(manifest))
  self.patch=mock.patch.object(validate,'OUT',self.package);self.patch.start();self.addCleanup(self.patch.stop)
 def snapshot(self):
  return {str(p.relative_to(self.package)):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.package.rglob('*') if p.is_file()}
 def invoke(self):
  with contextlib.redirect_stdout(io.StringIO()):return validate.main()

class ReadOnlyValidationTests(PackageFixture,unittest.TestCase):
 def test_success_is_read_only(self):
  before=self.snapshot();self.invoke();self.assertEqual(before,self.snapshot())
 def test_markdown_user_response_survives_validation(self):
  for name in ['cases/GC-001.md','REVIEW-PACKAGE.md']:
   with self.subTest(name=name):
    p=self.package/name;p.write_text(p.read_text()+'\n사용자 응답: 반론 반박. 최종 판단은 사용자가 직접 작성.\n')
    before=self.snapshot()
    with self.assertRaisesRegex(ValueError,'artifact changed'):self.invoke()
    self.assertEqual(before,self.snapshot())
 def test_json_final_judgment_survives_validation(self):
  p=self.package/'human-response-forms.json';forms=json.loads(p.read_text())
  forms[0].update(counterargument_response='반박',response_reason='사용자 작성 근거',user_final_judgment='PRESERVED',approve_for_development_gold=False)
  p.write_text(json.dumps(forms,ensure_ascii=False));before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'artifact changed'):self.invoke()
  self.assertEqual(before,self.snapshot())
 def test_missing_output_is_not_recreated(self):
  (self.package/'cases/GC-001.md').unlink();before=self.snapshot()
  with self.assertRaises((ValueError,FileNotFoundError)):self.invoke()
  self.assertEqual(before,self.snapshot())
 def test_evidence_tamper_does_not_write_outputs(self):
  p=self.package/'gc01_06.raw.json';p.write_bytes(p.read_bytes()+b' ');before=self.snapshot()
  with self.assertRaisesRegex(ValueError,'artifact changed'):self.invoke()
  self.assertEqual(before,self.snapshot())

class RenderingProtectionTests(PackageFixture,unittest.TestCase):
 def test_render_refuses_existing_directory_with_user_work(self):
  import render
  destination=pathlib.Path(self.tmp.name)/'rendered';destination.mkdir()
  user_file=destination/'GC-001.md';user_file.write_text('사용자 최종 판단: 보류')
  with self.assertRaises(FileExistsError):render.render(destination)
  self.assertEqual(user_file.read_text(),'사용자 최종 판단: 보류')
 def test_corrupt_source_creates_no_destination(self):
  import render
  p=self.package/'cases/GC-001.md';p.write_text(p.read_text()+'\n사용자 반론 응답\n')
  before=self.snapshot();destination=pathlib.Path(self.tmp.name)/'rendered'
  with self.assertRaisesRegex(ValueError,'artifact changed'):render.render(destination)
  self.assertFalse(destination.exists());self.assertEqual(before,self.snapshot())
 def test_render_new_directory_matches_committed_artifacts(self):
  import render
  before=self.snapshot();destination=pathlib.Path(self.tmp.name)/'rendered';render.render(destination)
  expected=['REVIEW-PACKAGE.md','human-response-forms.json','validation.json']+[f'cases/{r["case_id"]}.md' for r in json.loads((self.package/'initial-judgments.json').read_text())['cases']]
  for name in expected:self.assertEqual((destination/name).read_bytes(),(self.package/name).read_bytes(),name)
  self.assertEqual(before,self.snapshot())
 def test_render_refuses_source_subdirectory(self):
  import render
  destination=self.package/'new-render'
  with self.assertRaisesRegex(ValueError,'outside the source'):render.render(destination)
  self.assertFalse(destination.exists())
