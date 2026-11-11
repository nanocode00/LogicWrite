"""A hash of partial destination text cannot establish complete MOVE context."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import integration
import organization
import pipeline
from test_integration import contract


class DestinationCoverageTests(unittest.TestCase):
    def test_explicit_partial_destination_cannot_confirm_move(self):
        bundle = integration.markdown_bundle('# Source\n\nKeep this condition.\n', contract())
        scope = {'scope_id': 'details', 'kind': 'document', 'document_id': 'details'}
        text = '# Details\n\nOnly a fragment.\n'
        for coverage in ('partial', 'not_provided', ''):
            with self.subTest(coverage=coverage):
                snap = {'document_id': 'details', 'version': '1', 'coverage': coverage,
                        'content': text, 'sha256': pipeline.digest_text(text)}
                result = organization.evaluate_destination_scope(scope, bundle, destination_snapshots=[snap])
                self.assertFalse(result['allows_confirmed_move'])
                self.assertEqual(result['verification_status'], 'incomplete_destination_snapshot')

    def test_complete_destination_and_legacy_minimal_metadata_remain_supported(self):
        bundle = integration.markdown_bundle('# Source\n', contract())
        scope = {'scope_id': 'details', 'kind': 'document', 'document_id': 'details'}
        text = '# Complete details\n'
        for coverage in (None, 'complete'):
            snap = {'document_id': 'details', 'version': '1', 'content': text, 'sha256': pipeline.digest_text(text)}
            if coverage is not None:
                snap['coverage'] = coverage
            self.assertTrue(organization.evaluate_destination_scope(scope, bundle,
                            destination_snapshots=[snap])['allows_confirmed_move'])


if __name__ == '__main__':
    unittest.main()
