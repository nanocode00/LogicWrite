"""Offline reproduction verifies scope without importing evaluator answers."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import g2_ab_offline as offline


class G2OfflineTests(unittest.TestCase):
    def test_all_ir_and_synthetic_artifacts_reproducible_and_no_execution(self):
        results,summary=offline.build_results()
        again,summary_again=offline.build_results()
        self.assertEqual(results,again);self.assertEqual(summary,summary_again)
        self.assertEqual([r['documents'] for r in summary[:3]],[7,4,3])
        for pair in results.values():
            for artifact in pair.values():
                self.assertEqual(artifact['gate_state'],'REVIEW')
                self.assertFalse(artifact['execution_allowed'])
                self.assertFalse(artifact['delivery_approved'])
                self.assertEqual(artifact['model_calls'],0)
        self.assertEqual(summary[-1]['task_statuses'],dict(eligible=1,held=1,denied=1,unsupported=1))

    def test_runner_reads_only_declared_inputs_no_gold_or_judgments(self):
        paths=[];original=offline._read
        def record(path):
            paths.append(path.relative_to(offline.ROOT).as_posix());return original(path)
        with patch.object(offline,'_read',side_effect=record): offline.build_results()
        self.assertEqual(len(paths),5)
        self.assertTrue(all(p.startswith('evaluation/integrated_reconstruction/inputs/') or
            Path(p).name in {'g2_ab_synthetic_input.json','g2_ab_synthetic_request.json'} for p in paths))

    def test_cli_preserves_existing_output_directory(self):
        with tempfile.TemporaryDirectory() as root:
            with patch('sys.argv',['g2_ab_offline','--output',root]),patch('sys.stderr'):
                with self.assertRaises(SystemExit) as ex: offline.main()
            self.assertEqual(ex.exception.code,2)

    def test_explicit_example_has_evidence_and_scoped_hitl(self):
        results,_=offline.build_results();p=results['synthetic']['plan']
        questions={q['question_id']:q for q in p['hitl_questions']}
        policy=questions['commercial-policy']
        self.assertEqual(policy['held_task_ids'],['policy-revision'])
        self.assertTrue(policy['evidence']);self.assertTrue(policy['decision_owner'])
        self.assertEqual(policy['origin'],'trusted_caller_reported_potential_conflict')
        self.assertFalse(any('independent-placement' in q['held_task_ids'] for q in questions.values()))
