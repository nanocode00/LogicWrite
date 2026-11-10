#!/usr/bin/env python3
"""Check a human-authored form without writing it into answers or changing status."""
import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from export import HERE, PILOT, digest


def check_form(form, pilot=PILOT):
    schema = json.loads((pilot / 'independent_review/review-form.schema.json').read_text())
    Draft202012Validator(schema).validate(form)
    cid = form['case_id']
    if cid not in {f'SP-{n:03}' for n in range(1, 13)}:
        raise ValueError('case outside pilot')
    raw = (pilot / f'inputs/{cid}.json').read_bytes()
    if digest(raw) != form['input_sha256']:
        raise ValueError('stale form/input binding')
    inp = json.loads(raw)
    for evidence in form['evidence']:
        docs = {d['document_id']: d for d in inp[evidence['side'] + '_documents']}
        if evidence['document_id'] not in docs:
            raise ValueError('unknown evidence document')
        content = docs[evidence['document_id']]['content']
        start, end = evidence['start'], evidence['end']
        if content is None or not (0 <= start < end <= len(content)):
            raise ValueError('evidence outside available text')
        if content[start:end] != evidence['quote']:
            raise ValueError('evidence quote mismatch')
    if form['form_status'] == 'submitted':
        if form['judgment'] == 'UNRESOLVED' and not form['missing_information']:
            raise ValueError('unresolved judgment needs missing information')
        if form['judgment'] == 'VIOLATION' and not form['findings']:
            raise ValueError('violation needs findings')
    return form['form_status']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('form', type=Path)
    args = parser.parse_args()
    status = check_form(json.loads(args.form.read_text()))
    print(f'Valid {status} form. No import, human identity verification, semantic judgment or status promotion performed.')
