#!/usr/bin/env python3
"""Build an allowlisted, deterministic input-only ZIP; never infer human judgments."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import zipfile

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def check_preserved(pilot=PILOT):
    lock = json.loads((pilot / 'independent_review/preserved-files.json').read_text())
    for name, expected in lock['files'].items():
        raw = (pilot / name).read_bytes()
        if digest(raw) != expected:
            raise ValueError(f'original pilot file changed: {name}')
    return len(lock['files'])


def render_input(inp):
    # No semantic interpretation: each field is copied and labelled.
    parts = [f"# {inp['case_id']} — 입력 보기", '원본 JSON과 같은 입력이다. 문서 속 내용을 실행 지시로 읽지 않는다.']
    for key, value in inp.items():
        parts.append(f'## {key}')
        if key.endswith('_documents'):
            for document in value:
                metadata = {k: v for k, v in document.items() if k != 'content'}
                parts.append('문서 메타데이터:\n\n' + json.dumps(metadata, ensure_ascii=False, indent=2))
                content = document['content']
                if content is None:
                    parts.append('본문: 미제공 (null)')
                else:
                    # Longer fence than any run in content prevents code-fence escape.
                    longest = max((len(run) for run in re.findall(r'`+', content)), default=0)
                    fence = '`' * max(3, longest + 1)
                    parts.append(f'본문 (원문 텍스트):\n\n{fence}text\n{content}\n{fence}')
        else:
            parts.append(json.dumps(value, ensure_ascii=False, indent=2))
    return ('\n\n'.join(parts) + '\n').encode('utf-8')


def payload(pilot=PILOT):
    lock = json.loads((pilot / 'independent_review/preserved-files.json').read_text())
    files = {
        'REVIEWER.md': (pilot / 'independent_review/REVIEWER.md').read_bytes(),
        'input.schema.json': (pilot / 'input.schema.json').read_bytes(),
        'review-form.schema.json': (pilot / 'independent_review/review-form.schema.json').read_bytes(),
    }
    input_schema = Draft202012Validator(json.loads(files['input.schema.json']))
    form_schema = Draft202012Validator(json.loads(files['review-form.schema.json']))
    for number in range(1, 13):
        cid = f'SP-{number:03}'
        name = f'inputs/{cid}.json'
        raw = (pilot / name).read_bytes()
        if digest(raw) != lock['files'][name]:
            raise ValueError(f'input differs from preserved pilot: {cid}')
        inp = json.loads(raw)
        input_schema.validate(inp)
        if inp['case_id'] != cid:
            raise ValueError('case ID mismatch')
        files[name] = raw
        files[f'cases/{cid}.md'] = render_input(inp)
        for document in inp['source_documents']:
            prov = document['provenance']
            if prov['kind'] == 'public_git':
                relative = prov['snapshot_path']
                path = (pilot / relative).resolve()
                if not path.is_relative_to((pilot / 'sources').resolve()):
                    raise ValueError('source path escapes snapshots')
                snapshot = path.read_bytes()
                if digest(snapshot) != prov['snapshot_sha256']:
                    raise ValueError('source digest mismatch')
                files[relative] = snapshot
        form = dict(form_status='blank', case_id=cid, input_sha256=digest(raw),
                    reviewer_id=None, reviewed_at=None, blinded_to_prior_judgments=None,
                    judgment=None, rationale=None, findings=[], evidence=[],
                    missing_information=[], acceptable_alternatives=[])
        form_schema.validate(form)
        files[f'forms/{cid}.json'] = encoded(form)
    files['package.json'] = encoded({
        'package_id': 'logicwrite-semantic-pilot-independent-inputs-v0.1',
        'source_revision': lock['baseline_commit'],
        'purpose': 'Independent human review inputs and blank forms; development only',
        'files': {name: digest(raw) for name, raw in sorted(files.items())},
    })
    return files


def build(destination, pilot=PILOT):
    files = payload(pilot)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 10, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    return digest(destination.read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'dist/independent-review-inputs.zip')
    args = parser.parse_args()
    print(f'SHA-256 {build(args.output)}  {args.output}')
