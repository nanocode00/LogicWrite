"""Adversarial tests for the separate inclusion-intent history."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import validate_approval as v


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / 'approval'
        shutil.copytree(v.HERE, self.folder, ignore=shutil.ignore_patterns('__pycache__'))
        p = patch.object(v, 'HERE', self.folder)
        p.start()
        self.addCleanup(p.stop)

    def save(self, name, value):
        (self.folder / name).write_text(json.dumps(value, ensure_ascii=False))

    def reseal(self):
        self.save('artifact-manifest.json', {
            name: v.sha((self.folder / name).read_bytes()) for name in v.ARTIFACTS
        })

    def mutate_record(self, mutate, reseal=False):
        record = v.load(self.folder / 'events.json')
        mutate(record)
        previous = None
        for event in record['events']:
            event['previous_event_sha256'] = previous
            previous = v.final.event_digest(event)
        record['terminal_event_sha256'] = previous
        self.save('events.json', record)
        if reseal:
            self.reseal()

    def test_17_approved_unchanged_finals_no_activation_and_read_only(self):
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.folder.iterdir() if p.is_file()}
        result = v.validate()
        self.assertEqual(result['approved_count'], 17)
        self.assertEqual(result['final_distribution'], {'PRESERVED': 8, 'VIOLATION': 5, 'UNRESOLVED': 4})
        self.assertEqual(result['active_gold_count'], 12)
        self.assertEqual(result['final_judgment_changes'], 0)
        self.assertFalse(result['activation_performed'])
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                                  for p in self.folder.iterdir() if p.is_file()})

    def test_tampering_detected_without_repair(self):
        self.mutate_record(lambda r: r['events'][0].update(approve_for_development_gold=False))
        raw = (self.folder / 'events.json').read_bytes()
        with self.assertRaises(ValueError):
            v.validate()
        self.assertEqual(raw, (self.folder / 'events.json').read_bytes())

    def test_event_file_deletion_detected_without_repair(self):
        (self.folder / 'events.json').unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            v.validate()
        self.assertFalse((self.folder / 'events.json').exists())

    def test_missing_duplicate_reordered_extra_cases_even_after_reseal(self):
        mutations = [lambda r: r['events'].pop(),
                     lambda r: r['events'].__setitem__(1, copy.deepcopy(r['events'][0])),
                     lambda r: r['events'].reverse(),
                     lambda r: r['events'].append(copy.deepcopy(r['events'][0]))]
        original = (self.folder / 'events.json').read_bytes()
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                (self.folder / 'events.json').write_bytes(original)
                self.mutate_record(mutate, reseal=True)
                with self.assertRaises(ValueError):
                    v.validate()

    def test_false_approval_wrong_input_or_final_binding_after_reseal(self):
        original = (self.folder / 'events.json').read_bytes()
        for field, value in [('approve_for_development_gold', False),
                             ('input_sha256', '0' * 64),
                             ('final_event_sha256', '0' * 64),
                             ('actor_type', 'ai'), ('user_approved_at', '2026-11-13T00:00:00Z'),
                             ('signature', 'invented'), ('authentication', 'invented'),
                             ('activate_development_gold', True)]:
            with self.subTest(field=field):
                (self.folder / 'events.json').write_bytes(original)
                self.mutate_record(lambda r: r['events'][0].update({field: value}), reseal=True)
                with self.assertRaises(ValueError):
                    v.validate()

    def test_final_reference_cannot_point_to_another_case(self):
        self.mutate_record(lambda r: r['events'][0]['final_reference'].update(pointer='/events/1'), reseal=True)
        with self.assertRaises(ValueError):
            v.validate()

    def test_source_scope_provenance_and_quote_cannot_change(self):
        original = (self.folder / 'approval-declaration.json').read_bytes()
        for field, value in [('statement', '승인하지 않음'), ('case_ids', v.IDS[:-1]),
                             ('externally_authenticated', True), ('human_reviewer_count', 2),
                             ('user_approved_at', '2026-11-13'), ('signature', 'fake'),
                             ('authentication', {'verified': True}), ('activation_authorized', True)]:
            with self.subTest(field=field):
                (self.folder / 'approval-declaration.json').write_bytes(original)
                data = v.load(self.folder / 'approval-declaration.json')
                data[field] = value
                self.save('approval-declaration.json', data)
                self.reseal()
                with self.assertRaises(ValueError):
                    v.validate()

    def test_preservation_baseline_cannot_be_reduced_after_reseal(self):
        data = v.load(self.folder / 'preserved-files.json')
        data.pop(next(iter(data)))
        self.save('preserved-files.json', data)
        self.reseal()
        with self.assertRaises(ValueError):
            v.validate()

    def test_manifest_cannot_omit_evidence(self):
        data = v.load(self.folder / 'artifact-manifest.json')
        data.pop('events.json')
        self.save('artifact-manifest.json', data)
        with self.assertRaises(ValueError):
            v.validate()

    def test_stale_terminal_chain_rejected_after_manifest_reseal(self):
        data = v.load(self.folder / 'events.json')
        data['terminal_event_sha256'] = '0' * 64
        self.save('events.json', data)
        self.reseal()
        with self.assertRaises(ValueError):
            v.validate()

    def test_input_final_history_and_active_dataset_changes_detected(self):
        root_copy = Path(self.tmp.name) / 'repository'
        preserved = v.load(self.folder / 'preserved-files.json')
        for name in preserved:
            target = root_copy / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((v.ROOT / name).read_bytes())
        initial = v.load(v.ROOT / 'evaluation/golden_expansion/codex_counterreview_2026_11_11/initial-judgments.json')
        for name in [initial['cases'][0]['input_path'], v.FINAL_PATH, v.ACTIVE_PATH]:
            with self.subTest(path=name):
                target = root_copy / name
                original = target.read_bytes()
                target.write_bytes(original + b' ')
                with patch.object(v, 'ROOT', root_copy):
                    with self.assertRaisesRegex(ValueError, 'existing file changed'):
                        v.validate()
                self.assertEqual(target.read_bytes(), original + b' ')
                target.write_bytes(original)
