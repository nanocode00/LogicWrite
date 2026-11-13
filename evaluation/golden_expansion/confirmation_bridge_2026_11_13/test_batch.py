"""No automatic elevation of historical review into current user endorsement."""
import copy
import json
import shutil
from pathlib import Path
import tempfile
import unittest
import build_batch as b
import validate_batch as v

class BatchTests(unittest.TestCase):
    def test_exact_source_backed_inventory(self):
        result = v.validate()
        self.assertEqual(result["case_count"],17)
        self.assertEqual(result["quote_candidates"],34)
        self.assertEqual(result["formally_confirmed_evidence"],0)
        self.assertEqual(result["development_gold_activated"],0)
        self.assertTrue(result["historical_user_judgments_unchanged"])

    def test_unresolved_reasons_still_unconfirmed(self):
        rows = b.build()["cases"]
        unresolved=[r for r in rows if r["historical_final"]["judgment"]=="UNRESOLVED"]
        self.assertEqual([r["case_id"] for r in unresolved],["GC-003","GC-006","GC-009","GC-012"])
        self.assertTrue(all(r["initial_unresolved_reason"]
                            and r["final_unresolved_issues_human_confirmed"] is None
                            for r in unresolved))

    def test_human_attribution_remains_unconfirmed(self):
        rows=b.build()["cases"]
        self.assertTrue(all(r["formal_challenge_id"] is None
                            and r["formal_response_decision"] is None
                            and r["response_mapping_status"] == "case_level_agreement_with_ai_assessment_only"
                            and r["historical_final"]["response_to_ai_assessment"] == "동의"
                            and r["formal_response_human_confirmed"] is None
                            and r["final_evidence_human_confirmed"] is None
                            and r["confidence_limitations_human_confirmed"] is None
                            and all(o["human_confirmed_as_final_evidence"] is None
                                    and o["attributed_to"]=="AI_Codex_source_quote"
                                    for o in r["candidate_final_evidence"])
                            for r in rows))

    def test_resealed_human_confirmation_tamper_rejected(self):
        original=b.build()
        mutations=[
            lambda x: x["cases"][0].update(formal_response_human_confirmed=True),
            lambda x: x["cases"][0]["candidate_final_evidence"][0].update(human_confirmed_as_final_evidence=True),
            lambda x: x["cases"][0]["historical_final"].update(judgment="VIOLATION"),
            lambda x: x.update(development_gold_activated=17),
            lambda x: x["cases"].pop(),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                with tempfile.TemporaryDirectory() as d:
                    clone=copy.deepcopy(original)
                    mutate(clone)
                    (Path(d)/"confirmation-batch.json").write_text(json.dumps(clone))
                    with self.assertRaises(ValueError):
                        v.validate(here=Path(d))

    def test_read_only(self):
        path=b.HERE/"confirmation-batch.json"
        before=path.read_bytes(),path.stat().st_mtime_ns
        v.validate()
        self.assertEqual(before,(path.read_bytes(),path.stat().st_mtime_ns))

    def test_reaffirmation_is_separate_from_formal_evidence(self):
        rows = b.build()["cases"]
        reaffirmed = [r for r in rows if r["retained_unresolved_reason_reaffirmation"]]
        self.assertEqual([r["case_id"] for r in reaffirmed], ["GC-003", "GC-006", "GC-009", "GC-012"])
        for row in reaffirmed:
            self.assertEqual(row["retained_unresolved_reason_reaffirmation"]["reason"], row["initial_unresolved_reason"])
            self.assertIsNone(row["formal_response_decision"])
            self.assertIsNone(row["final_evidence_human_confirmed"])

    def test_supplied_root_evidence_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copytree(b.ROOT / "evaluation", root / "evaluation", ignore=shutil.ignore_patterns("__pycache__"))
            baseline = b.load(b.ROOT / "evaluation/golden_expansion/gold_inclusion_approval_2026_11_13/preserved-files.json")
            for name in baseline:
                target = root / name
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(b.ROOT / name, target)
            here = root / "evaluation/golden_expansion/confirmation_bridge_2026_11_13"
            self.assertEqual(v.validate(root=root, here=here)["case_count"], 17)
            source = root / "evaluation/golden_expansion/user_final_2026_11_11/events.json"
            source.write_bytes(source.read_bytes() + b" ")
            with self.assertRaises(ValueError):
                v.validate(root=root, here=here)

if __name__=="__main__":
    unittest.main()
