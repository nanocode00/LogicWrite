"""Adversarial checks: normalization may not manufacture human evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import transcription_adapter as t
import validate_suggestions as s


class TranscriptionTests(unittest.TestCase):
    def test_existing_history_is_reused_without_formal_events(self):
        got = t.validate()
        self.assertEqual(got["cases"], 17)
        self.assertEqual(got["human_verified_evidence_count"], 0)
        self.assertEqual(got["new_formal_events"], 0)
        self.assertEqual(got["new_gold_activated"], 0)
        pack = t.build()
        self.assertEqual([x["case_id"] for x in pack["cases"]], t.IDS)
        self.assertTrue(all(x["later_gold_inclusion"]["approved"]
                            and not x["later_gold_inclusion"]["activation_authorized"]
                            and not x["formal_event_chain_recorded"]
                            and not x["eligible_for_activation"]
                            and not x["codex_counterreview"]["quote_candidates_are_user_evidence"]
                            and not x["final_human"]["per_challenge_responses_recorded"]
                            for x in pack["cases"]))

    def test_historical_label_distribution_preserved(self):
        from collections import Counter
        labels = Counter(r["final_human"]["judgment"] for r in t.build()["cases"])
        self.assertEqual(labels, {"PRESERVED": 8, "VIOLATION": 5, "UNRESOLVED": 4})
        self.assertEqual(sum(x["final_human"]["final_unresolved_issues_confirmed"] is False
                             for x in t.build()["cases"]), 4)

    def test_no_fabricated_review_time_or_blinding(self):
        self.assertTrue(all(x["initial_human"]["reviewed_at"] is None
                            and x["initial_human"]["blinded_to_prior_judgments"] is None
                            for x in t.build()["cases"]))

    def test_stored_transcription_tamper_detected(self):
        source = t.build()
        for mutate in (
            lambda d: d["cases"][0]["final_human"].update(judgment="VIOLATION"),
            lambda d: d["cases"][0]["codex_counterreview"].update(quote_candidates_are_user_evidence=True),
            lambda d: d["cases"][0].update(eligible_for_activation=True),
            lambda d: d["cases"].pop(),
        ):
            with self.subTest(mutate=mutate):
                with tempfile.TemporaryDirectory() as tmp:
                    edited = copy.deepcopy(source)
                    mutate(edited)
                    (Path(tmp) / "transcription.json").write_text(json.dumps(edited))
                    with self.assertRaises(ValueError):
                        t.validate(here=Path(tmp))

    def test_original_input_hash_corruption_detected(self):
        oldload = t.load
        def corrupt(path):
            data = oldload(path)
            if str(path) == str(t.ROOT / t.INITIAL):
                data["cases"][0]["input_sha256"] = "0" * 64
            return data
        with patch.object(t, "load", side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, "input sha|different case input"):
                t.build()

    def test_corrupt_codex_source_ref_rejected(self):
        oldload = t.load
        def corrupt(path):
            data = oldload(path)
            if str(path) == str(t.ROOT / t.FINAL):
                data["events"][0]["counterreview_reference"]["sha256"] = "0" * 64
            return data
        with patch.object(t, "load", side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, "Codex reference sha"):
                t.build()

    def test_missing_user_approval_rejected(self):
        oldload = t.load
        def corrupt(path):
            data = oldload(path)
            if str(path) == str(t.ROOT / t.APPROVAL):
                data["events"][0]["approve_for_development_gold"] = False
            return data
        with patch.object(t, "load", side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, "approval/activation"):
                t.build()

    def test_existing_quote_candidates_exact_and_not_user_evidence(self):
        summary = s.run()
        self.assertEqual(summary["cases"], 17)
        self.assertEqual(summary["unconfirmed_quotes"], 34)
        self.assertTrue(summary["ready_for_user_review_only"])

    def test_validation_is_read_only(self):
        paths = [t.HERE / "transcription.json", t.HERE / "suggestions.json",
                 t.HERE / "format-mapping.json"]
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
        t.validate()
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                                  for p in paths})


if __name__ == "__main__":
    unittest.main()
