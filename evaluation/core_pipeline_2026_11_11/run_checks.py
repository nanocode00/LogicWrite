#!/usr/bin/env python3
"""Run each unittest directory in an isolated Python process (duplicate module names)."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def provenance(repo):
    paths = sorted(p for p in repo.rglob('*.py') if '.git' not in p.parts and '__pycache__' not in p.parts)
    diff = subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=repo)
    return {'head_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
            'tracked_diff_sha256': hashlib.sha256(diff).hexdigest(),
            'working_tree_status': subprocess.check_output(['git', 'status', '--short'], cwd=repo, text=True),
            'python_files_sha256': {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}


def run(repo):
    before = provenance(repo)
    rows = []
    directories = sorted({p.parent for p in repo.rglob('test_*.py') if '.git' not in p.parts and '__pycache__' not in p.parts})
    for directory in directories:
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', str(directory.relative_to(repo)), '-p', 'test_*.py']
        result = subprocess.run(command, cwd=repo, capture_output=True, text=True)
        output = result.stdout+result.stderr
        count = re.search(r'Ran (\d+) tests?', output)
        rows.append({'directory': str(directory.relative_to(repo)), 'command': command,
                     'exit_code': result.returncode, 'test_count': int(count[1]) if count else 0, 'output': output})
    after = provenance(repo)
    return {'source_commit': before['head_commit'],
            'source_commit_meaning': 'HEAD only; tested working tree is bound separately below',
            'tested_tree_before': before, 'tested_tree_after': after,
            'python_inputs_unchanged': before['python_files_sha256'] == after['python_files_sha256'],
            'test_count': sum(r['test_count'] for r in rows), 'all_passed': all(r['exit_code']==0 for r in rows),
            'suites': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.repo.resolve())
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('test_count','all_passed')}))
    raise SystemExit(0 if report['all_passed'] else 1)
