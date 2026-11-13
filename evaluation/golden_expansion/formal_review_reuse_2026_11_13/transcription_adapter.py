"""Provenance-preserving normalization of completed review history.

Never produces a formal human workflow event, a gold-eligible record, or activation.
All recorded human statements come from immutable repository sources; proposed
Codex evidence is explicitly distinct from human-provided evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXPANSION = "evaluation/golden_expansion/"
INITIAL = EXPANSION + "codex_counterreview_2026_11_11/initial-judgments.json"
FINAL = EXPANSION + "user_final_2026_11_11/events.json"
APPROVAL = EXPANSION + "gold_inclusion_approval_2026_11_13/events.json"
SUGGESTIONS = EXPANSION + "formal_review_reuse_2026_11_13/suggestions.json"
IDS = [f"GC-{i:03}" for i in range(1, 13)] + [f"SP-{i:03}" for i in range(13, 18)]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def reference(root, path, pointer):
    absolute = (root / path).resolve()
    require(absolute.is_relative_to(root.resolve()) and absolute.is_file(), "unsafe/missing source reference")
    return {"path": path, "sha256": digest(absolute.read_bytes()), "pointer": pointer}


def build(root=ROOT):
    """Rebuild all values from known immutable sources; no timestamps or events created."""
    originals = load(root / INITIAL)["cases"]
    finals = load(root / FINAL)["events"]
    approvals = load(root / APPROVAL)["events"]
    suggestions = load(root / SUGGESTIONS)["cases"]
    require(len(originals) == len(finals) == len(approvals) == len(suggestions) == 17,
            "source count mismatch")
    require([x["case_id"] for x in originals] == IDS, "original order")
    require([x["case_id"] for x in finals] == IDS, "final order")
    require([x["case_id"] for x in approvals] == IDS, "approval order")
    require([x["case_id"] for x in suggestions] == IDS, "suggestion order")

    cases = []
    for i, (original, final, approval, suggestion) in enumerate(
            zip(originals, finals, approvals, suggestions)):
        cid = IDS[i]
        require(original["initial_judgment"] == final["payload"]["judgment"],
                "historical initial/final changed")
        require(final["payload"]["rationale"] == "추가 의견 없음"
                and final["payload"]["counterargument_response"] == "동의",
                "unrecorded final response")
        require(approval["approve_for_development_gold"] is True
                and approval["activate_development_gold"] is False,
                "approval/activation boundary")
        require(original["input_sha256"] == final["input_sha256"] == approval["input_sha256"],
                "different case input hashes")

        raw_ref = final["counterreview_reference"]
        raw_doc = load(root / raw_ref["path"])
        raw_index = int(raw_ref["pointer"].split("/")[-1])
        raw_case = raw_doc["cases"][raw_index]
        require(raw_case["case_id"] == cid, "Codex reference case mismatch")
        require(digest((root / raw_ref["path"]).read_bytes()) == raw_ref["sha256"],
                "Codex reference sha mismatch")
        input_ref = reference(root, original["input_path"], "")
        require(input_ref["sha256"] == original["input_sha256"], "input sha mismatch")

        proposed_evidence = suggestion["evidence_options_not_user_endorsed"]
        require(proposed_evidence and all(e["user_confirmed"] is False
                and e["source"] == "existing_codex_quote" for e in proposed_evidence),
                "AI evidence may not be relabeled as human")
        require(suggestion["initial_judgment_as_submitted"] == original["initial_judgment"]
                and suggestion["initial_reason_as_submitted"] == original["initial_reason"]
                and suggestion["final_judgment_as_submitted"] == final["payload"]["judgment"],
                "suggestion has different judgments")

        cases.append({
            "case_id": cid,
            "input": input_ref,
            "initial_human": {
                "source": reference(root, INITIAL, f"/cases/{i}"),
                "judgment": original["initial_judgment"],
                "rationale": original["initial_reason"],
                "reviewed_at": None,
                "blinded_to_prior_judgments": None,
                "user_evidence_recorded": False,
            },
            "codex_counterreview": {
                "source": raw_ref,
                "strongest_counterargument": raw_case["strongest_counterargument"],
                "ai_evaluation": raw_case["counterargument_validity"],
                "quote_candidates": proposed_evidence,
                "quote_candidates_are_user_evidence": False,
            },
            "final_human": {
                "source": reference(root, FINAL, f"/events/{i}"),
                "judgment": final["payload"]["judgment"],
                "rationale": final["payload"]["rationale"],
                "response_target": "AI counterargument evaluation",
                "response": final["payload"]["counterargument_response"],
                "per_challenge_responses_recorded": False,
                "final_evidence_user_confirmed": False,
                "confidence_limitations_user_confirmed": False,
                "final_unresolved_issues_confirmed": False if
                    final["payload"]["judgment"] == "UNRESOLVED" else None,
            },
            "later_gold_inclusion": {
                "source": reference(root, APPROVAL, f"/events/{i}"),
                "approved": True,
                "activation_authorized": False,
            },
            "formal_event_chain_recorded": False,
            "eligible_for_activation": False,
        })
    return {
        "schema_version": "historical-review-format-transcription-v1",
        "status": "historical_transcription_only",
        "source_reviewer_authentication": "not_claimed",
        "all_original_judgments_preserved": True,
        "reuse_not_re_adjudication": True,
        "changes_to_formal_workflow": False,
        "number_of_cases": 17,
        "activation_authorized": False,
        "cases": cases,
    }


def validate(root=ROOT, here=HERE):
    stored = load(here / "transcription.json")
    expected = build(root)
    require(stored == expected, "historical transcription is stale or altered")
    return {
        "cases": len(stored["cases"]),
        "preserved_original_judgments": True,
        "human_verified_evidence_count": 0,
        "new_formal_events": 0,
        "new_gold_activated": 0,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False))
