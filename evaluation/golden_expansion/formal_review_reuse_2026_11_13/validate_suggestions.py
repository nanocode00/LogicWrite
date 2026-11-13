"""Read-only checks for review suggestions, never user evidence or activation."""
import json, pathlib, hashlib
import transcription_adapter
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
COUNTER=ROOT/'evaluation/golden_expansion/codex_counterreview_2026_11_11'
FINAL=ROOT/'evaluation/golden_expansion/user_final_2026_11_11'
APPROVAL=ROOT/'evaluation/golden_expansion/gold_inclusion_approval_2026_11_13'
def read(p):return json.loads(p.read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def run():
 provenance=transcription_adapter.validate()
 require(provenance['cases']==17 and provenance['new_gold_activated']==0 and provenance['new_formal_events']==0,'transcription cannot activate gold')
 pack=read(HERE/'suggestions.json')
 mapping=read(HERE/'format-mapping.json')
 initials=read(COUNTER/'initial-judgments.json')['cases']
 finals=read(FINAL/'events.json')['events']
 approvals=read(APPROVAL/'events.json')['events']
 ids=[f'GC-{i:03}' for i in range(1,13)]+[f'SP-{i:03}' for i in range(13,18)]
 require(mapping['status']=='draft_not_gold_eligible' and mapping['active_gold_unchanged'] is True,'mapping safety boundary')
 require(mapping['case_count']==17 and [x['case_id'] for x in mapping['cases']]==ids,'mapping coverage')
 require(mapping['field_rules']['initial.form.reviewed_at'] is None and mapping['field_rules']['initial.form.blinded_to_prior_judgments'] is None,'missing metadata must be null')
 require(pack['status']=='draft_not_human_evidence' and pack['case_count']==len(ids),'draft boundary')
 require([r['case_id'] for r in pack['cases']]==ids,'case coverage')
 proposed=0
 for i,(row,initial,final,approval) in enumerate(zip(pack['cases'],initials,finals,approvals)):
  cid=ids[i]
  mapped=mapping['cases'][i]
  require(mapped['historical_initial']=={'judgment':initial['initial_judgment'],'rationale':initial['initial_reason'],'source':'initial-judgments.json'},'initial mapping integrity')
  require(mapped['historical_final']['judgment']==final['payload']['judgment'] and mapped['historical_final']['rationale']==final['payload']['rationale'] and mapped['historical_final']['response_to_counterargument_validity']==final['payload']['counterargument_response'],'final mapping integrity')
  require(mapped['later_inclusion_approved'] is True and mapped['ai_evidence_proposals_count']==len(row['evidence_options_not_user_endorsed']),'mapping approval/evidence counts')
  require(mapped['formal_review_chain_created'] is False and mapped['eligible_for_activation'] is False and mapped['human_evidence_confirmed'] is False and mapped['challenge_responses_explicitly_bound'] is False,'mapping may not grant eligibility')
  require(cid==initial['case_id']==final['case_id']==approval['case_id'],'case match')
  inp_path=ROOT/initial['input_path']
  require(inp_path.is_relative_to(ROOT) and digest(inp_path)==initial['input_sha256']==row['input_sha256'],'input integrity')
  require(row['initial_judgment_as_submitted']==initial['initial_judgment'] and row['initial_reason_as_submitted']==initial['initial_reason'],'initial source')
  require(row['final_judgment_as_submitted']==final['payload']['judgment'] and row['final_additional_reason_as_submitted']==final['payload']['rationale'],'final source')
  require(row['counterargument_response_as_submitted']==final['payload']['counterargument_response'],'AI response source')
  require(row['development_gold_inclusion_approved'] is True and approval['approve_for_development_gold'] is True,'inclusion source')
  require(row['formal_user_initial_submitted'] is False and row['formal_user_final_submitted'] is False and row['activate_development_gold'] is False,'no fabricated review/activation')
  require(row['challenge_specific_response']=='NEEDS_EXPLICIT_HUMAN_CONFIRMATION','must not guess challenge response')
  inp=read(inp_path); options=row['evidence_options_not_user_endorsed']
  require(1<=len(options)<=2,'evidence option coverage')
  for item in options:
   require(item['source']=='existing_codex_quote' and item['user_confirmed'] is False,'human evidence attribution')
   side=item['side']; require(side in ('source','candidate'),'side')
   docs=inp[side+'_documents'];d=next((d for d in docs if d['document_id']==item['document_id']),None)
   require(d is not None and isinstance(d['content'],str),'document')
   require(0<=item['start']<item['end']<=len(d['content']),'span')
   require(d['content'][item['start']:item['end']]==item['quote'],'quote')
   proposed+=1
 return {'cases':len(ids),'unconfirmed_quotes':proposed,'approved_case_count':17,'active_new_cases':0,'ready_for_user_review_only':True}
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False))
