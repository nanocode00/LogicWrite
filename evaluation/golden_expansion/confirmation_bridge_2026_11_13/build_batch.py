"""Build reviewable 17-case source-backed user-confirmation proposal.

No signed human events, no historical backdating, no gold activation.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "evaluation/golden_expansion/formal_review_reuse_2026_11_13"
EXPECTED_IDS = [f"GC-{n:03}" for n in range(1, 13)] + [f"SP-{n:03}" for n in range(13, 18)]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def link(path, ptr=""):
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path), "pointer": ptr}


def build():
    spec = importlib.util.spec_from_file_location("historical_adaptor", SOURCE / "transcription_adapter.py")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    historical = adapter.build()
    suggestions = load(SOURCE / "suggestions.json")
    assert historical["number_of_cases"] == suggestions["case_count"] == 17
    assert [r["case_id"] for r in historical["cases"]] == EXPECTED_IDS
    assert [r["case_id"] for r in suggestions["cases"]] == EXPECTED_IDS

    result = {
        "schema_version": "gold-review-confirmation-batch-proposal-v1",
        "status": "proposed_not_human_confirmed",
        "purpose": "Take the already submitted user judgments as immutable and request only provenance/evidence/resolution acknowledgments absent from formal schema.",
        "source": link(SOURCE / "transcription.json"),
        "existing_inclusion_approved": 17,
        "proposed_evidence_quotes": 34,
        "new_user_evidence_confirmations": 0,
        "new_formal_user_events": 0,
        "development_gold_activated": 0,
        "human_reviewed_at": None,
        "historical_events_rewritten": False,
        "cases": [],
    }
    for i, (history, suggestion) in enumerate(zip(historical["cases"], suggestions["cases"])):
        cid = EXPECTED_IDS[i]
        assert history["case_id"] == suggestion["case_id"] == cid
        assert history["initial_human"]["judgment"] == history["final_human"]["judgment"]
        assert history["later_gold_inclusion"]["approved"] is True
        assert history["final_human"]["response"] == "동의"

        quotes = []
        for quote in suggestion["evidence_options_not_user_endorsed"]:
            assert quote["user_confirmed"] is False
            quotes.append({
                "side": quote["side"], "document_id": quote["document_id"],
                "start": quote["start"], "end": quote["end"], "quote": quote["quote"],
                "attributed_to": "AI_Codex_source_quote",
                "human_confirmed_as_final_evidence": None,
            })

        result["cases"].append({
            "case_id": cid,
            "input_sha256": history["input"]["sha256"],
            "input_reference": history["input"],
            "historical_initial": {
                "judgment": history["initial_human"]["judgment"],
                "rationale": history["initial_human"]["rationale"],
                "source": history["initial_human"]["source"],
            },
            "historical_final": {
                "judgment": history["final_human"]["judgment"],
                "rationale": history["final_human"]["rationale"],
                "response_to_ai_assessment": history["final_human"]["response"],
                "source": history["final_human"]["source"],
            },
            "gold_inclusion_approved": True,
            "gold_inclusion_source": history["later_gold_inclusion"]["source"],
            "historical_codex_argument": history["codex_counterreview"]["strongest_counterargument"],
            "codex_assessment": history["codex_counterreview"]["ai_evaluation"],
            "codex_source": history["codex_counterreview"]["source"],
            "suggested_formal_challenge_id": "legacy-strongest-" + cid,
            "suggested_formal_response": "reject",
            "response_suggestion_basis": "AI validity rejected strongest counterargument; historical user agreed with the assessment, but did not provide a formal challenge-ID-specific response.",
            "formal_response_human_confirmed": None,
            "candidate_final_evidence": quotes,
            "final_evidence_human_confirmed": None,
            "confidence_limitations_human_confirmed": None,
            "initial_unresolved_reason": history["initial_human"]["rationale"] if history["final_human"]["judgment"] == "UNRESOLVED" else None,
            "final_unresolved_issues_human_confirmed": None if history["final_human"]["judgment"] == "UNRESOLVED" else "not_applicable",
            "formal_gold_eligible": False,
        })
    return result


def main():
    HERE.mkdir(parents=True, exist_ok=True)
    target = HERE / "confirmation-batch.json"
    if target.exists():
        raise RuntimeError("Refusing to overwrite existing human-review proposal")
    package = build()
    target.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    from collections import Counter
    print(json.dumps({"cases":len(package["cases"]), "quotes":sum(len(x["candidate_final_evidence"]) for x in package["cases"]), "historical_labels":dict(Counter(c["historical_final"]["judgment"] for c in package["cases"])),"new_user_events":package["new_formal_user_events"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
