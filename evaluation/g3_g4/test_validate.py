"""G3/G4 integrity tests; no new human verdicts or completed counterreviews."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from validate import HERE,sha,validate_all,validate_g3,validate_g4,validate_assignments


class G3G4Tests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)/'g3_g4';shutil.copytree(HERE,self.root,ignore=shutil.ignore_patterns('__pycache__'))

    def write(self,path,value):
        p=self.root/path;p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');return sha(p.read_bytes())

    def load(self,path):return json.loads((self.root/path).read_text())

    def change_answer(self,mutate):
        m=self.load('manifest.json');row=m['cases'][0];a=self.load(row['answer_path']);mutate(a)
        row['answer_sha256']=self.write(row['answer_path'],a);self.write('manifest.json',m)

    def test_all(self):self.assertEqual(validate_all(),{'g3_prepared':12,'g4_provisional_development':12})

    def test_gold_promotion_rejected_even_with_refreshed_hash(self):
        self.change_answer(lambda a:a.update(gold_eligible=True))
        with self.assertRaises(ValueError):validate_g4(self.root)

    def test_no_fake_human_review(self):
        self.change_answer(lambda a:a['reviews'].append({'reviewer_id':'invented'}))
        with self.assertRaises(ValueError):validate_g4(self.root)

    def test_source_tamper(self):
        p=self.root/'sources/requests-document.txt';p.write_bytes(p.read_bytes()+b'changed')
        with self.assertRaises(ValueError):validate_g4(self.root)

    def test_license_tamper(self):
        p=self.root/'sources/click-license.txt';p.write_bytes(p.read_bytes()+b'changed')
        with self.assertRaises(ValueError):validate_g4(self.root)

    def test_manifest_tamper(self):
        m=self.load('manifest.json');m['cases'][0]['input_sha256']='0'*64;self.write('manifest.json',m)
        with self.assertRaises(ValueError):validate_g4(self.root)

    def test_answer_leak_in_input(self):
        m=self.load('manifest.json');row=m['cases'][0];inp=self.load(row['input_path']);inp['expected_judgment']='PRESERVED'
        row['input_sha256']=self.write(row['input_path'],inp);a=self.load(row['answer_path']);a['input_sha256']=row['input_sha256'];row['answer_sha256']=self.write(row['answer_path'],a);self.write('manifest.json',m)
        with self.assertRaises(ValueError):validate_g4(self.root)

    def test_family_overlap_case_insensitive(self):
        with self.assertRaises(ValueError):validate_assignments([{'family':'Psf/Requests','split':'development'},{'family':'psf/requests','split':'holdout'}])

    def test_duplicate_family_in_same_split_allowed(self):
        validate_assignments([{'family':'psf/requests','split':'development'}]*3)

    def test_holdout_reclassification_rejected(self):
        m=self.load('manifest.json');m['cases'][0]['split']='holdout';self.write('manifest.json',m)
        with self.assertRaises(ValueError):validate_g4(self.root)

    def test_g3_prior_user_label_preserved(self):
        p=self.load('g3-progress.json');p['cases'][2]['existing_user_judgment']='PRESERVED';self.write('g3-progress.json',p)
        with self.assertRaises(ValueError):validate_g3(self.root)

    def test_g3_no_blinding_retroactively(self):
        p=self.load('g3-progress.json');p['cases'][0]['existing_user_blinded']=True;self.write('g3-progress.json',p)
        with self.assertRaises(ValueError):validate_g3(self.root)

    def test_g3_no_gold_status_only(self):
        p=self.load('g3-progress.json');p['cases'][0]['development_gold_eligible']=True;self.write('g3-progress.json',p)
        with self.assertRaises(ValueError):validate_g3(self.root)

    def test_g3_no_new_events_even_with_refreshed_hash(self):
        p=self.load('g3-progress.json');row=p['cases'][0];rec=self.load(row['prepared_workflow_path']);rec['events']=[{'kind':'user_final'}];row['prepared_workflow_sha256']=self.write(row['prepared_workflow_path'],rec);self.write('g3-progress.json',p)
        with self.assertRaises(ValueError):validate_g3(self.root)

    def test_missing_case(self):
        (self.root/'inputs/GC-001.json').unlink()
        with self.assertRaises(ValueError):validate_g4(self.root)

    def test_evidence_tamper(self):
        self.change_answer(lambda a:a['findings'][0]['evidence'][0].update(quote='fabricated'))
        with self.assertRaises(ValueError):validate_g4(self.root)

    def test_readable_view_tamper(self):
        p=self.root/'cases/GC-001.md';p.write_bytes(p.read_bytes()+b'altered')
        with self.assertRaises(ValueError):validate_g4(self.root)

if __name__=='__main__':unittest.main()
