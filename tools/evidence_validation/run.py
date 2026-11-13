"""Run immutable evaluation tests and current code regressions in separate trees."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import subprocess
import sys

import boundary
import consumers

ROOT = Path(__file__).resolve().parents[2]


def suite_plan(store, root):
    historical = sorted({str(Path(name).parent) for name in store.blobs
        if name.startswith('evaluation/') and Path(name).name.startswith('test_') and name.endswith('.py')})
    plan = [{'phase': 'historical', 'directory': name, 'pattern': 'test_*.py'} for name in historical]
    # Also retain current-Core compatibility coverage of the existing consumer
    # engines; this supplements, rather than replaces, their historical tests.
    plan.extend({'phase': 'current', 'directory': name, 'pattern': 'test_*.py'} for name in
                ('evaluation/core_pipeline_2026_11_11', 'evaluation/source_candidate_semantics'))
    for base in ('experiments', 'tools'):
        directories = sorted({str(p.parent.relative_to(root)) for p in (root / base).rglob('test_*.py')})
        plan.extend({'phase': 'current', 'directory': name, 'pattern': 'test_*.py'} for name in directories)
    # Newly versioned evaluation packages do not get silently tested on old Core.
    for path in sorted((root / 'evaluation').rglob('test_*.py')):
        name = str(path.relative_to(root))
        if name not in store.blobs:
            plan.append({'phase': 'current', 'directory': str(path.parent.relative_to(root)), 'pattern': path.name})
    return plan


def current_identity(root):
    files = {}
    for directory in ('experiments', 'tools', 'evaluation', 'tests', 'docs'):
        for path in sorted((root / directory).rglob('*')):
            if path.is_symlink():
                raise ValueError('current source symlink: ' + str(path.relative_to(root)))
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                files[str(path.relative_to(root))] = boundary.digest(path.read_bytes())
    proc = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, env=boundary.environment())
    return {'revision': proc.stdout.strip() if proc.returncode == 0 else None,
            'source_sha256': boundary.digest(json.dumps(files, sort_keys=True).encode()), 'files': files}


def run_suite(root, directory, pattern):
    command = [sys.executable, '-m', 'unittest', 'discover', '-s', directory, '-p', pattern]
    try:
        process = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                 env=boundary.environment(), timeout=120)
        output = process.stdout + process.stderr
        count = re.search(r'^Ran (\d+) tests?', output, re.MULTILINE)
        failures = re.search(r'^FAILED \(([^)]*)\)', output, re.MULTILINE)
        details = failures.group(1) if failures else ''
        tests = int(count.group(1)) if count else 0
        return {'command': command, 'directory': directory, 'pattern': pattern,
                'tests_run': tests, 'returncode': process.returncode if tests else (process.returncode or 2),
                'failures': sum(map(int, re.findall(r'failures=(\d+)', details))),
                'errors': sum(map(int, re.findall(r'errors=(\d+)', details))),
                'skipped': sum(map(int, re.findall(r'skipped=(\d+)', output))),
                'output': output if process.returncode or not tests else output[-250:]}
    except subprocess.TimeoutExpired:
        return {'command': command, 'directory': directory, 'pattern': pattern,
                'tests_run': 0, 'returncode': 124, 'failures': 0, 'errors': 1,
                'skipped': 0, 'output': 'Test process exceeded 120 seconds'}


def validate(repository=ROOT):
    root = Path(repository).resolve()
    report = {'version': 'separated-evidence-validation-v1', 'status': 'FAIL', 'suites': [],
              'delivery_approved': False, 'stage_transition_allowed': False,
              'environment': {'python': platform.python_version(), 'python_executable': sys.executable,
                              'jsonschema': importlib.metadata.version('jsonschema'),
                              'historical_environment_exactly_reproduced': False}}
    try:
        store = boundary.EvidenceStore(root)
        report['evidence'] = store.verify_evidence()
        before = current_identity(root)
        report['current_code'] = before
        with store.snapshot() as snapshot:
            report['historical_snapshot'] = store.verify_snapshot(snapshot)
            for spec in suite_plan(store, root):
                suite_root = snapshot if spec['phase'] == 'historical' else root
                result = run_suite(suite_root, spec['directory'], spec['pattern'])
                result['phase'] = spec['phase']
                report['suites'].append(result)
                print(f"{spec['phase']} {spec['directory']}: {result['tests_run']} tests, exit {result['returncode']}", file=sys.stderr, flush=True)
            report['current_consumers'] = [consumers.evaluate_current(store, snapshot, kind)
                                           for kind in ('core', 'source')]
            store.verify_snapshot(snapshot)
        store.verify_evidence()
        if before != current_identity(root):
            raise ValueError('current code changed during verification')
        report['tests_run'] = sum(row['tests_run'] for row in report['suites'])
        report['status'] = 'PASS' if report['suites'] and all(row['returncode'] == 0 for row in report['suites']) else 'FAIL'
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        report['error'] = str(exc)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional new report outside immutable evidence packages')
    args = parser.parse_args()
    if args.output and args.output.resolve().is_relative_to(ROOT):
        parser.error('Report output must be outside this repository')
    report = validate()
    raw = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(raw)
    else:
        print(raw, end='')
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
