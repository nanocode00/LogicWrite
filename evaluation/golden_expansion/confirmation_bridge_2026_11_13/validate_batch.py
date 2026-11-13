"""Validate a frozen user-confirmation proposal against all original review sources.

This checks provenance and candidate accuracy, not human endorsement or gold eligibility.
"""
import json
import importlib.util
from pathlib import Path
import build_batch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def validate(root=ROOT, here=HERE):
    stored = json.loads((here / "confirmation-batch.json").read_text(encoding="utf-8"))
    # Validate the supplied repository, not a different trusted checkout.
    for folder, entry, method in [
        ("codex_counterreview_2026_11_11", "validate.py", "verify"),
        ("user_final_2026_11_11", "validate_submission.py", "validate"),
        ("gold_inclusion_approval_2026_11_13", "validate_approval.py", "validate"),
    ]:
        path = root / "evaluation/golden_expansion" / folder / entry
        spec = importlib.util.spec_from_file_location("bridge_" + folder, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = getattr(module, method)()
        if method == "verify":
            require(result[0]["completed"] == 17 and result[0]["failed"] == 0, "incomplete AI review")
    require(stored == build_batch.build(root), "proposal diverged from source history")
    require(stored["status"] == "proposed_not_human_confirmed", "wrong status")
    require(stored["new_user_evidence_confirmations"] == 0 and stored["new_formal_user_events"] == 0
            and stored["development_gold_activated"] == 0, "false claim of activation/confirmation")
    cases = stored["cases"]
    require([r["case_id"] for r in cases] == build_batch.EXPECTED_IDS, "wrong case set/order")
    count = 0
    for row in cases:
        require(row["historical_final"]["judgment"] == row["historical_initial"]["judgment"],
                "user labels modified")
        require(row["gold_inclusion_approved"] is True and row["formal_gold_eligible"] is False,
                "approval and eligibility boundary")
        require(row["formal_challenge_id"] is None
                and row["formal_response_decision"] is None
                and row["response_mapping_status"] == "case_level_agreement_with_ai_assessment_only"
                and row["formal_response_human_confirmed"] is None
                and row["final_evidence_human_confirmed"] is None
                and row["confidence_limitations_human_confirmed"] is None,
                "invented formal human response")
        if row["historical_final"]["judgment"] == "UNRESOLVED":
            require(row["initial_unresolved_reason"]
                    and row["final_unresolved_issues_human_confirmed"] is None,
                    "must not invent final unresolved reason")
        options = row["candidate_final_evidence"]
        require(options and len(options) == 2, "missing quote proposals")
        input_source = json.loads((root / row["input_reference"]["path"]).read_text(encoding="utf-8"))
        for option in options:
            docs = input_source[option["side"] + "_documents"]
            target = next((d for d in docs if d["document_id"] == option["document_id"]), None)
            require(target is not None, "bad source document")
            require(target["content"][option["start"]:option["end"]] == option["quote"],
                    "unverifiable quote")
            require(option["attributed_to"] == "AI_Codex_source_quote"
                    and option["human_confirmed_as_final_evidence"] is None,
                    "AI quote falsely attributed to human")
            count += 1
    require(count == stored["proposed_evidence_quotes"] == 34, "quote count mismatch")
    return {"case_count":len(cases), "quote_candidates":count,
            "formally_confirmed_evidence":0, "development_gold_activated":0,
            "historical_user_judgments_unchanged":True}


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False))
