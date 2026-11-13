"""Offline subprocess bridge; frozen comparators retain all original checks.

Low-level functions operate on caller-validated roots. The whole-run entrypoint
is run.validate(), which authenticates current evidence and snapshot before/after.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import boundary

SCRIPTS = {'core': 'evaluation/development_gold_active/core_diagnostics.py',
           'source': 'evaluation/development_gold_active/source_candidate.py'}


def _execute(root, kind, operation, *args):
    if kind not in SCRIPTS:
        raise ValueError('unknown consumer')
    command = [sys.executable, str(Path(root) / SCRIPTS[kind]), operation, *map(str, args)]
    try:
        process = subprocess.run(command, cwd=root, capture_output=True,
                                 env=boundary.environment(), timeout=120)
    except subprocess.TimeoutExpired as exc:
        raise ValueError('consumer ' + operation + ' timed out') from exc
    if process.returncode:
        raise ValueError('consumer ' + operation + ' failed: ' + kind)


def predict_current(root, kind, output):
    _execute(root, kind, 'predict', output)


def compare_historical(snapshot, kind, predictions, output):
    _execute(snapshot, kind, 'compare', predictions, output)


def evaluate_current(store, snapshot, kind):
    store.verify_evidence()
    store.verify_snapshot(snapshot)
    with tempfile.TemporaryDirectory(prefix='logicwrite-current-consumer-') as temporary:
        predictions = Path(temporary) / 'predictions.json'
        comparison = Path(temporary) / 'comparison.json'
        predict_current(store.repository, kind, predictions)
        raw = json.loads(predictions.read_bytes())
        if raw.get('reference_labels_loaded') is not False:
            raise ValueError('prediction label boundary invalid')
        compare_historical(snapshot, kind, predictions, comparison)
        result = json.loads(comparison.read_bytes())
        store.verify_evidence()
        store.verify_snapshot(snapshot)
        return {'consumer': kind, 'producer_tree': 'current',
                'comparator_revision': boundary.HISTORICAL_REVISION,
                'predictions_sha256': boundary.digest(predictions.read_bytes()),
                'comparison_sha256': boundary.digest(comparison.read_bytes()),
                'prediction_count': len(raw['cases']), 'comparison': result,
                'reference_labels_loaded_before_predictions': False,
                'real_model': 'not_run'}
