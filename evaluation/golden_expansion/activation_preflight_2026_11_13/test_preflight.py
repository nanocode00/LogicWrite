"""Tests use disposable copies; never manufacture human review evidence."""
import copy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import validate_preflight as v


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        for name in v.load(v.HERE / 'preserved-files.json'):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(v.ROOT / name, target)
        self.here = self.root / v.PACKAGE
        shutil.copytree(v.HERE, self.here, ignore=shutil.ignore_patterns('__pycache__'))

    def check(self):
        return v.validate(self.here, self.root)

    def test_all_17_approved_but_blocked_12_remain_active(self):
        report = self.check()
        self.assertEqual(report['new_inclusion_approved'], 17)
        self.assertEqual(report['new_eligible'], 0)
        self.assertEqual(report['new_activated'], 0)
        self.assertEqual(report['active_count'], 12)
        self.assertEqual(report['active_distribution'], {'PRESERVED': 4, 'VIOLATION': 4, 'UNRESOLVED': 4})
        self.assertEqual(report['target_only']['distribution'], {'PRESERVED': 12, 'VIOLATION': 9, 'UNRESOLVED': 8})
        self.assertEqual([r['case_id'] for r in report['cases']], v.IDS)
        self.assertTrue(all(r['blockers'] for r in report['cases']))
        with self.assertRaisesRegex(ValueError, 'activation blocked'):
            v.require_activation_ready(report)

    def test_existing_unresolved_reasons_preserved_but_not_invented_as_final_issues(self):
        rows = [r for r in self.check()['cases'] if r['user_final_judgment'] == 'UNRESOLVED']
        self.assertEqual([r['case_id'] for r in rows], ['GC-003', 'GC-006', 'GC-009', 'GC-012'])
        for row in rows:
            self.assertTrue(row['initial_reason'])
            self.assertIsNone(row['formal_final_unresolved_issues'])
            self.assertIn('FINAL_UNRESOLVED_ISSUES_NOT_SUBMITTED', row['blockers'])

    def test_integrity_rejects_changed_or_missing_evidence(self):
        for name in [v.FINAL + '/events.json', v.APPROVAL + '/events.json',
                     v.COUNTER + '/gc01_06.raw.json', v.ACTIVE,
                     'evaluation/golden_expansion/record.schema.json']:
            p = self.root / name
            raw = p.read_bytes()
            with self.subTest(name=name, action='modify'):
                p.write_bytes(raw + b' ')
                with self.assertRaises(ValueError): self.check()
            with self.subTest(name=name, action='delete'):
                p.unlink()
                with self.assertRaises((ValueError, FileNotFoundError)): self.check()
            p.write_bytes(raw)

    def test_changed_input_and_parent_lineage_rejected(self):
        for name in ['evaluation/g3_g4/inputs/GC-003.json', 'evaluation/golden_expansion/registry.json']:
            p = self.root / name
            raw = p.read_bytes()
            p.write_bytes(raw + b' ')
            with self.assertRaises(ValueError): self.check()
            p.write_bytes(raw)

    def test_report_label_scope_approval_and_activation_tampering_rejected_after_manifest_reseal(self):
        original = (self.here / 'report.json').read_bytes()
        mutations = [lambda r: r['cases'][0].update(inclusion_approved=False),
                     lambda r: r['cases'][2].update(user_final_judgment='PRESERVED'),
                     lambda r: r['cases'].pop(),
                     lambda r: r['cases'].__setitem__(1, copy.deepcopy(r['cases'][0])),
                     lambda r: r.update(active_count=29, new_activated=17),
                     lambda r: r['cases'][0].update(blockers=[])]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                (self.here / 'report.json').write_bytes(original)
                report = v.load(self.here / 'report.json')
                mutate(report)
                v_json = __import__('json')
                (self.here / 'report.json').write_text(v_json.dumps(report))
                manifest = v.load(self.here / 'artifact-manifest.json')
                manifest['report.json'] = v.sha((self.here / 'report.json').read_bytes())
                (self.here / 'artifact-manifest.json').write_text(v_json.dumps(manifest))
                with self.assertRaises(ValueError): self.check()

    def test_read_only_and_consumers_still_reference_v2(self):
        paths = [p for p in self.root.rglob('*') if p.is_file()]
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
        self.check()
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths})
        for name in v.CONSUMERS:
            self.assertIn(v.ACTIVE, (self.root / name).read_text())

    def test_missing_baseline_entry_rejected(self):
        import json
        path = self.here / 'preserved-files.json'
        data = v.load(path)
        data.pop(next(iter(data)))
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError): self.check()
