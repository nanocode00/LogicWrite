#!/usr/bin/env python3
"""Compare protected repository assets read-only, including an optional PR #34 checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(repo, legacy_checkout=None):
    baseline = json.loads((ROOT/'records/protected_baseline.json').read_text())
    for path, expected in baseline['main_files'].items():
        if digest((repo/path).read_bytes()) != expected:
            raise ValueError('main asset changed: ' + path)
    for commit, files in baseline['protected_pr_files'].items():
        for path, expected in files.items():
            raw = subprocess.check_output(['git', 'show', commit+':'+path], cwd=repo)
            if digest(raw) != expected:
                raise ValueError('protected PR object changed: ' + path)
            if legacy_checkout and path.startswith('evaluation/capability_pilot/'):
                if digest((legacy_checkout/path).read_bytes()) != expected:
                    raise ValueError('legacy checkout asset changed: ' + path)
    return dict(main_files_unchanged=len(baseline['main_files']),
                protected_pr_objects_verified=sum(len(x) for x in baseline['protected_pr_files'].values()),
                legacy_checkout_checked=legacy_checkout is not None,
                core_modified=False, gold_promoted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT.parents[1])
    parser.add_argument('--legacy-checkout', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.repo, args.legacy_checkout), indent=2))
