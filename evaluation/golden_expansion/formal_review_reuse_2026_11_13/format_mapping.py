"""Prepare exact schema field mapping from existing user/AI records; no synthetic human events."""
import json, pathlib
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
EXP=ROOT/"evaluation/golden_expansion"
def load(p):return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
source=load(HERE/"suggestions.json")
schema=load(EXP/"record.schema.json")
events_by_kind={part["properties"]["kind"]["const"]:part for part in schema["properties"]["events"]["items"]["oneOf"]}
final_form=events_by_kind["user_final"]["properties"]["payload"]
initial_form=events_by_kind["user_initial"]["properties"]["payload"]["properties"]["form"]
assert {"reviewed_at","blinded_to_prior_judgments"}.issubset(initial_form["properties"])
assert initial_form["properties"]["reviewed_at"]["type"]==["string","null"]
assert initial_form["properties"]["blinded_to_prior_judgments"]["type"]==["boolean","null"]
assert initial_form["properties"]["evidence"].get("minItems",0)==0
assert final_form["properties"]["evidence"]["minItems"]==1
out={"schema_version":"formal-history-transcription-mapping-v1","status":"draft_not_gold_eligible","active_gold_unchanged":True,
 "recorded_history_policy":"Map actual previously submitted values to exact formal field names, with original source paths. No invented dates, evidence endorsements, identities, or new human submissions.",
 "field_rules":{
   "initial.form.case_id":"from historical initial judgment",
   "initial.form.input_sha256":"from verified historical input file",
   "initial.form.judgment":"from historical user initial",
   "initial.form.rationale":"from historical user initial reason",
   "initial.form.reviewed_at":None,
   "initial.form.blinded_to_prior_judgments":None,
   "initial.form.evidence":"empty allowed; source quotes proposed separately",
   "initial.form.findings":"VIOLATION: candidate from user original text, not additional user finding",
   "initial.form.missing_information":"UNRESOLVED: candidate from user original text; preserve exact attribution",
   "counterreview":"from historical Codex case/quote evidence; preserve AI attribution and review execution",
   "final.payload.judgment":"from user_final events",
   "final.payload.rationale":"literal user final reason",
   "final.payload.responses":"single case-level '동의' cannot be assigned to formal challenge IDs without explicit mapping",
   "final.payload.evidence":"independent Codex quotes are only candidates until user attribution is established",
   "final.payload.unresolved_issues":"initial rationale can be cited as historical user text, but is not an explicitly submitted final field",
   "final.payload.confidence_limitations":"known method limitations are facts; user confirmation in formal record not inferred",
   "final.payload.approve_for_development_gold":"from later user inclusion approval (PR #27), not historical final decision time",
   "human.actor_id":"existing repository-user pseudonym may be proposed, not authenticated identity",
   "event.recorded_at":"actual new transcription recording time only; NEVER historical backdating"
 },
 "case_count":17,"cases":[]}
for row in source["cases"]:
 j=row["initial_judgment_as_submitted"]
 assert j==row["final_judgment_as_submitted"]
 initial_additions={}
 if j=="VIOLATION":
  initial_additions["findings_candidate"]=[{"reason":row["initial_reason_as_submitted"],"source":"verbatim_human_initial","severity":"undetermined","error_type":"unspecified","confirmation":"not_a_new_human_submission"}]
 if j=="UNRESOLVED":
  initial_additions["missing_information_candidate"]=[{"text":row["initial_reason_as_submitted"],"source":"verbatim_human_initial","confirmation":"not_a_new_human_submission"}]
 out["cases"].append({
 "case_id":row["case_id"],"historical_initial":{"judgment":j,"rationale":row["initial_reason_as_submitted"],"source":"initial-judgments.json"},
 "historical_final":{"judgment":row["final_judgment_as_submitted"],"rationale":row["final_additional_reason_as_submitted"],"response_to_counterargument_validity":row["counterargument_response_as_submitted"],"source":"user_final_2026_11_11/events.json"},
 "later_inclusion_approved":row["development_gold_inclusion_approved"],
 "initial_candidates":initial_additions,
 "ai_evidence_proposals_count":len(row["evidence_options_not_user_endorsed"]),
 "human_evidence_confirmed":False,"challenge_responses_explicitly_bound":False,
 "formal_review_chain_created":False,"eligible_for_activation":False
 })
(HERE/"format-mapping.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"cases":len(out["cases"]),"initial_violations":sum(x["historical_initial"]["judgment"]=="VIOLATION" for x in out["cases"]),"initial_unresolved":sum(x["historical_initial"]["judgment"]=="UNRESOLVED" for x in out["cases"]),"formal_ready":0,"historical_user_judgments_reused":17},ensure_ascii=False))
