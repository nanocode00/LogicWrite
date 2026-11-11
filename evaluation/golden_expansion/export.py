#!/usr/bin/env python3
"""Build only allowlisted inputs, blank forms, and readable source/candidate views."""
import importlib.util
import json
from pathlib import Path
import zipfile
import review
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('input_renderer',HERE.parent/'semantic_pilot/independent_review/export.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)

def payload():
    files={'REVIEWER.md':(HERE/'REVIEWER.md').read_bytes()}
    for row in review.load(HERE/'registry.json')['cases']:
        cid=row['case_id'];raw=review.resolve(row['input_path']).read_bytes()
        review.require(review.sha(raw)==row['input_sha256'],'stale input')
        inp=json.loads(raw);files[f'inputs/{cid}.json']=raw;files[f'cases/{cid}.md']=renderer.render_input(inp)
        form=dict(form_status='blank',case_id=cid,input_sha256=row['input_sha256'],reviewer_id=None,reviewed_at=None,blinded_to_prior_judgments=None,judgment=None,rationale=None,findings=[],evidence=[],missing_information=[],acceptable_alternatives=[])
        files[f'forms/{cid}.json']=renderer.encoded(form)
    files['package.json']=renderer.encoded(dict(dataset_role='development_only',source_revision=review.load(HERE/'registry.json')['base_commit'],files={n:review.sha(raw) for n,raw in sorted(files.items())}))
    return files

def build(destination):
    files=payload();destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,raw in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;archive.writestr(info,raw)
    return review.sha(destination.read_bytes())

if __name__=='__main__':
    print(build(HERE/'dist/review-inputs.zip'))
