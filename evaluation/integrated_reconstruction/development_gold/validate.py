#!/usr/bin/env python3
"""Read-only check of the three explicitly included exposed-development cases.

This registry is a post-approval overlay. Historical v1/v2 JSON and validation
snapshots retain their pre-approval gold_eligible=false/null state.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = "development_gold/manifest.json"
IDS = {"IR-001", "IR-002", "IR-003"}


def read_file(path):
    p = (ROOT / path).resolve()
    if not p.is_relative_to(ROOT) or not p.is_file():
        raise ValueError("missing or escaping registry path: " + path)
    return p.read_bytes()


def read_json(path):
    return json.loads(read_file(path))


def blob_hash(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def check(yes, reason):
    if not yes:
        raise ValueError(reason)


def validate():
    reg = read_json(REGISTRY)
    check(reg["status"] == "included_for_development_evaluation", "not included")
    check(reg["split"] == "exposed_development", "wrong split")
    check(reg["source_family"] == "synthetic-author-cluster-20261113", "source family changed")
    check(reg["independent_source_families"] == 1, "inflated source independence")
    flags = reg["guardrails"]
    for flag in ("not_blind_holdout", "not_independent_real_examples",
                 "do_not_append_to_existing_active_29", "do_not_auto_merge_pr_36",
                 "no_claim_of_model_evaluation", "original_v1_and_earlier_validation_snapshots_remain_unchanged"):
        check(flags[flag] is True, "missing guardrail: " + flag)
    cases = reg["cases"]
    ids = [c["case_id"] for c in cases]
    check(set(ids) == IDS and len(ids) == reg["case_count"] == 3, "case set changed")
    meta = {c["case_id"]: c for c in read_json("cases.json")}
    approval = read_json("reviews/post_revision_approvals/2026-11-17.json")
    approved = {c["case_id"]: c for c in approval["cases"]}
    check(set(approved) == {"IR-001", "IR-002"}, "prior human approvals changed")
    for c in cases:
        cid = c["case_id"]
        m = meta[cid]
        check(m["source_family"] == reg["source_family"] and m["split"] == reg["split"]
              and m["independent_real_source"] is False, "case source/split mismatch: " + cid)
        expected_criteria = f"answers/{cid}.json" if cid == "IR-003" else f"criteria/v2/{cid}.json"
        expected_ref = (f"reference_outputs/{cid}.json" if cid == "IR-003"
                        else f"reference_outputs/v2_candidates/{cid}.json")
        check(c["input_path"] == f"inputs/{cid}.json"
              and c["criteria_path"] == expected_criteria
              and c["reference_path"] == expected_ref, "unexpected case version: " + cid)
        for key in ("input", "criteria", "reference", "human_review"):
            data = read_file(c[key + "_path"] if key != "human_review" else c["human_review_evidence_path"])
            check(blob_hash(data) == c[key + "_git_blob_sha"], "stale git blob: " + cid + "/" + key)
            if key in ("input", "criteria", "reference") and c.get(key + "_sha256"):
                check(hashlib.sha256(data).hexdigest() == c[key + "_sha256"],
                      "stale sha256: " + cid + "/" + key)
        criterion = read_json(c["criteria_path"])
        ref = read_json(c["reference_path"])
        check(criterion["case_id"] == ref["case_id"] == cid, "case binding mismatch")
        check(criterion["input_sha256"] == c["input_sha256"]
              == ref["input_sha256"], "input binding mismatch")
        check(ref["executed_by_system"] is False, "execution incorrectly claimed")
        check(c["gold_inclusion_approval"] == "approved_for_exposed_development",
              "gold approval missing")
        if cid == "IR-003":
            check("사람 검수 통과" in read_json("reviews/IR-003.json")["final_judgment"],
                  "IR-003 human review missing")
        else:
            a = approved[cid]
            check(a["post_revision_human_review"] == "approved"
                  and a["reference_candidate_review"].startswith("approved_"),
                  "prior human re-review missing: " + cid)
            check(a["criteria_sha256"] == c["criteria_sha256"]
                  and a["candidate_sha256"] == c["reference_sha256"],
                  "approved version/hash mismatch: " + cid)
    return {"status": "PASS", "included_development_cases": len(cases),
            "source_families": 1, "split": "exposed_development",
            "existing_active_29_modified": False,
            "gold_inclusion_approved_in_registry": True,
            "model_quality_evaluated": False}


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
