#!/usr/bin/env python3
"""Verify historical objects and current evidence, allowing current code to evolve."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PILOT_REVISION = '1b0776bedb3be16920bebcfdf9aef5824c8f19ec'
PACKAGE = 'evaluation/integrated_reconstruction/'
BASELINE = PACKAGE + 'records/protected_baseline.json'
spec = importlib.util.spec_from_file_location('integrated_evidence_boundary',
    ROOT.parents[1] / 'tools/evidence_validation/boundary.py')
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)


def verify_bytes(repo, name, expected, label):
    repo = Path(repo).resolve()
    path = repo / name
    if any(p.is_symlink() for p in (path, *path.parents) if p != repo and repo in p.parents):
        raise ValueError(label + ' symlink: ' + name)
    if boundary.digest(path.read_bytes()) != expected:
        raise ValueError(label + ' changed: ' + name)


def verify(repo, legacy_checkout=None):
    repo = Path(repo).resolve()
    store = boundary.EvidenceStore(repo)
    # Authenticate the original baseline; never regenerate it from current files.
    original = store.git('show', PILOT_REVISION + ':' + BASELINE)
    verify_bytes(repo, BASELINE, boundary.digest(original), 'preservation baseline')
    baseline = json.loads(original)
    if baseline['main_commit'] != boundary.HISTORICAL_REVISION or set(baseline['main_files']) != set(store.blobs):
        raise ValueError('historical baseline identity mismatch')
    for name, expected in baseline['main_files'].items():
        if boundary.digest(store.blobs[name]) != expected:
            raise ValueError('historical baseline blob mismatch: ' + name)
    current = store.verify_evidence()
    with store.snapshot() as snapshot:
        historical = store.verify_snapshot(snapshot)
    legacy_count = 0
    for commit, files in baseline['protected_pr_files'].items():
        for name, expected in files.items():
            raw = store.git('show', commit + ':' + name)
            if boundary.digest(raw) != expected:
                raise ValueError('protected PR object changed: ' + name)
            if legacy_checkout is not None and name.startswith('evaluation/capability_pilot/'):
                verify_bytes(legacy_checkout, name, expected, 'legacy checkout asset')
                legacy_count += 1
    # Inputs/answers/references stay byte-identical. Authorized review updates
    # retain the original pilot forms plus prior and current record snapshots.
    pilot_files = store.git('ls-tree', '-r', '--name-only', PILOT_REVISION, '--', PACKAGE).decode().splitlines()
    protected = [name for name in pilot_files if name.startswith(tuple(PACKAGE + part for part in
        ('inputs/', 'answers/', 'reference_outputs/', 'reviews/')))
        or name in {PACKAGE + 'cases.json', PACKAGE + 'sources.json', PACKAGE + 'legacy_triage.json'}]
    for name in protected:
        raw = store.git('show', PILOT_REVISION + ':' + name)
        target = name
        if name.startswith(PACKAGE + 'reviews/'):
            target = PACKAGE + 'reviews/history/pilot-v1/' + Path(name).name
        verify_bytes(repo, target, boundary.digest(raw), 'pilot evidence')
    prior = '6d6f32140b951cac025701ef42995ddba43565e0'
    for cid in ('IR-001', 'IR-002', 'IR-003'):
        raw = store.git('show', prior + ':' + PACKAGE + 'reviews/' + cid + '.json')
        verify_bytes(repo, PACKAGE + 'reviews/history/before-criteria-v2/' + cid + '.json',
                     boundary.digest(raw), 'prior human review')
    raw = store.git('show', prior + ':' + PACKAGE + 'CHANGE_REQUESTS.md')
    verify_bytes(repo, PACKAGE + 'reviews/history/before-criteria-v2/CHANGE_REQUESTS.md',
                 boundary.digest(raw), 'prior change requests')
    correction_parent = 'bd30dbdd65b1b895ebea3e8ee53fbe06a4b541e7'
    for source, archive in (
            ('criteria/v2/IR-001.json', 'criteria/v2/history/before-clarification-01/IR-001.json'),
            ('criteria/v2/manifest.json', 'criteria/v2/history/before-clarification-01/manifest.json'),
            ('reviews/IR-003.json', 'reviews/history/recorded-2026-11-16/IR-003.json'),
            ('CHANGE_REQUESTS.md', 'reviews/history/before-clarification-01/CHANGE_REQUESTS.md')):
        raw = store.git('show', correction_parent + ':' + PACKAGE + source)
        verify_bytes(repo, PACKAGE + archive, boundary.digest(raw), 'correction parent archive')
    for name in ('IR-001.json', 'manifest.json'):
        raw = store.git('show', 'ae1e8cc758090ee87f7ddd62fe0fa9f65a919fa6:' + PACKAGE + 'criteria/v2/' + name)
        verify_bytes(repo, PACKAGE + 'criteria/v2/history/before-clarification-02/' + name,
                     boundary.digest(raw), 'follow-up parent archive')
    spec = importlib.util.spec_from_file_location('preservation_criteria', ROOT / 'validate_criteria.py')
    criteria = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(criteria)
    criteria.validate(repo / PACKAGE)
    return dict(historical_revision=boundary.HISTORICAL_REVISION,
                historical_snapshot_files_verified=historical['verified_files'],
                current_evidence_files_unchanged=current['verified_files'],
                protected_pr_objects_verified=sum(len(x) for x in baseline['protected_pr_files'].values()),
                pilot_evidence_files_unchanged=len(protected),
                original_review_forms='authenticated_archives',
                prior_review_records_verified=3, current_review_records_verified=3,
                legacy_checkout_checked=legacy_checkout is not None,
                legacy_checkout_files_verified=legacy_count,
                current_core_comparison='historical equality not required', gold_promoted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT.parents[1])
    parser.add_argument('--legacy-checkout', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.repo, args.legacy_checkout), indent=2))
