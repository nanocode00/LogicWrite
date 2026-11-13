"""Reuse current prediction and immutable comparison, without approval changes."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import boundary

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class ConsumerTests(unittest.TestCase):
    def bridge(self):
        self.assertTrue((HERE / 'consumers.py').exists(), 'Missing current/historical consumer bridge')
        import consumers
        return consumers

    def test_current_core_predictions_and_original_comparator_remain_separate(self):
        bridge = self.bridge()
        store = boundary.EvidenceStore(ROOT)
        with store.snapshot() as snapshot, tempfile.TemporaryDirectory() as temporary:
            predictions = Path(temporary) / 'predictions.json'
            result = Path(temporary) / 'comparison.json'
            with patch.dict(os.environ, {'LOGICWRITE_CORE_CODE_ROOT': '/does/not/exist'}):
                bridge.predict_current(ROOT, 'core', predictions)
            raw = json.loads(predictions.read_text())
            self.assertFalse(raw['reference_labels_loaded'])
            self.assertEqual(len(raw['cases']), 29)
            bridge.compare_historical(snapshot, 'core', predictions, result)
            compared = json.loads(result.read_text())
            self.assertEqual(len(compared['cases']), 29)
            self.assertFalse(compared['comparison_is_sp_accuracy'])
            self.assertTrue(all(not row['delivery_approved'] for row in compared['cases']))

    def test_bad_prediction_input_binding_is_rejected(self):
        bridge = self.bridge()
        store = boundary.EvidenceStore(ROOT)
        with store.snapshot() as snapshot, tempfile.TemporaryDirectory() as temporary:
            predictions = Path(temporary) / 'predictions.json'
            bridge.predict_current(ROOT, 'core', predictions)
            raw = json.loads(predictions.read_text())
            raw['cases'][0]['input_sha256'] = '0' * 64
            predictions.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError, 'consumer compare failed'):
                bridge.compare_historical(snapshot, 'core', predictions, Path(temporary) / 'result.json')

    def test_offline_source_consumer_preserves_unresolved_and_metric_bounds(self):
        bridge = self.bridge()
        store = boundary.EvidenceStore(ROOT)
        with store.snapshot() as snapshot, tempfile.TemporaryDirectory() as temporary:
            predictions = Path(temporary) / 'predictions.json'
            result = Path(temporary) / 'result.json'
            bridge.predict_current(ROOT, 'source', predictions)
            raw = json.loads(predictions.read_text())
            self.assertFalse(raw['reference_labels_loaded'])
            self.assertEqual(len(raw['cases']), 29)
            bridge.compare_historical(snapshot, 'source', predictions, result)
            compared = json.loads(result.read_text())
            self.assertEqual(len(compared['cases']), 29)
            self.assertTrue(all(not row['included_in_metric'] for row in compared['cases']))
