"""Prepare source-backed REVIEW SUGGESTIONS only. Never create human events or activate gold."""
import json, hashlib, pathlib, re
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=ROOT/"evaluation/golden_expansion"
COUNTER=BASE/"codex_counterreview_2026_11_11"
FINAL=BASE/"user_final_2026_11_11"
APPROVAL=BASE/"gold_inclusion_approval_2026_11_13"
IDS=[f"GC-{i:03}" for i in range(1,13)]+[f"SP-{i:03}" for i in range(13,18)]
def read(p):return json.loads(pathlib.Path(p).read_text())
def h(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def raw_for(i):
 if i<6:return read(COUNTER/"gc01_06.raw.json")["cases"][i]
 if i<12:return read(COUNTER/"gc07_12.raw.json")["cases"][i-6]
 return read(COUNTER/"sp13_17.raw.json")["cases"][i-12]
initials=read(COUNTER/"initial-judgments.json")["cases"]
finals=read(FINAL/"events.json")["events"]
approvals=read(APPROVAL/"events.json")["events"]
proposal=[]
for i,cid in enumerate(IDS):
 initial,final,approval,ai=initials[i],finals[i],approvals[i],raw_for(i)
 assert cid==initial["case_id"]==final["case_id"]==approval["case_id"]==ai["case_id"]
 p=ROOT/initial["input_path"];assert h(p)==initial["input_sha256"]
 inp=read(p)
 suggestions=[]; seen=set()
 for evidence in ai["evidence"]:
  m=re.fullmatch(r"/(source_documents|candidate_documents)/(\d+)/content",evidence["pointer"])
  if not m:continue
  key,ix=m[1],int(m[2]);docs=inp[key];doc=docs[ix];content=doc.get("content")
  quote=evidence["quote"]
  if not isinstance(content,str) or not quote:continue
  offset=content.find(quote)
  if offset<0:continue
  side="source" if key.startswith("source") else "candidate"
  candidate={"side":side,"document_id":doc["document_id"],"start":offset,"end":offset+len(quote),"quote":quote,"source":"existing_codex_quote","user_confirmed":False}
  if (side,doc["document_id"],offset,quote) in seen:continue
  seen.add((side,doc["document_id"],offset,quote));suggestions.append(candidate)
  if len(suggestions)>=2:break
 assert suggestions,"No exact source-backed quote for "+cid
 proposal.append({
  "case_id":cid,"input_path":initial["input_path"],"input_sha256":initial["input_sha256"],
  "initial_judgment_as_submitted":initial["initial_judgment"],"initial_reason_as_submitted":initial["initial_reason"],
  "final_judgment_as_submitted":final["payload"]["judgment"],"counterargument_response_as_submitted":final["payload"]["counterargument_response"],
  "final_additional_reason_as_submitted":final["payload"]["rationale"],
  "development_gold_inclusion_approved":approval["approve_for_development_gold"],
  "ai_strongest_counterargument":ai["strongest_counterargument"],"ai_counterargument_assessment":ai["counterargument_validity"],
  "evidence_options_not_user_endorsed":suggestions,
  "challenge_specific_response":"NEEDS_EXPLICIT_HUMAN_CONFIRMATION",
  "formal_user_initial_submitted":False,"formal_user_final_submitted":False,
  "activate_development_gold":False,
 })
result={"schema_version":"formal-review-suggestions-only-v1","status":"draft_not_human_evidence",
 "meaning_of_null":{"reviewed_at":"May be null under initial form schema; do not invent past timing","blinded_to_prior_judgments":"May be null; do not infer exposure"},
 "method":"reuse exact quotes from independent Codex only as unconfirmed human-review suggestions",
 "fixed_policy":"No retrospective user event, no AI-created user evidence, no gold activation, no historical edits",
 "case_count":len(proposal),"cases":proposal}
HERE.mkdir(parents=True,exist_ok=True)
(HERE/"suggestions.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"cases":len(proposal),"quotes":sum(len(x["evidence_options_not_user_endorsed"]) for x in proposal),"unconfirmed":sum(all(not e["user_confirmed"] for e in x["evidence_options_not_user_endorsed"]) for x in proposal),"output":str(HERE/"suggestions.json")},ensure_ascii=False))
