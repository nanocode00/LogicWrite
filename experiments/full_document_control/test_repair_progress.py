"""Synthetic progress policy cases; real integration lives in test_repair_loop."""
import unittest
import repair_loop as repair


def audit(status, findings=()):
    return {'structural_report': {'checks': {}, 'findings': []},
            'semantic_report': {'checks': {'CLAIM_FACTS': {'status': status}}, 'findings': list(findings)}}


def finding(quote='wrong claim', start=0, message='violation'):
    return {'check_id': 'CLAIM_FACTS', 'rule_id': 'CLAIM_CHANGED', 'severity': 'ERROR',
        'message': message, 'evidence': [{'side': 'output', 'document_id': 'doc',
            'quote': quote, 'start': start, 'end': start+len(quote), 'snapshot_sha256': str(start)}]}


class ProgressTests(unittest.TestCase):
    def test_violation_to_unresolved_is_not_resolution(self):
        before, after = audit('violated', [finding()]), audit('unresolved')
        self.assertIn(('semantic', 'CLAIM_FACTS'), repair.newly_unresolved(before, after))
        delta = repair.compare_progress(before, after)
        self.assertFalse(delta['resolved'])
        self.assertTrue(delta['unconfirmed'])

    def test_violation_to_supported_is_resolution(self):
        delta = repair.compare_progress(audit('violated', [finding()]), audit('supported'))
        self.assertTrue(delta['resolved'])
        self.assertFalse(delta['unconfirmed'])

    def test_relocated_evidence_is_same_violation(self):
        self.assertEqual(repair.violations(audit('violated', [finding()])),
                         repair.violations(audit('violated', [finding(start=99, message='now at 99')])) )

    def test_different_claim_document_or_duplicate_remains_new(self):
        before = audit('violated', [finding()])
        other = finding(); other['evidence'][0]['document_id'] = 'other'
        for after in (audit('violated', [finding('another wrong claim')]),
                      audit('violated', [other]), audit('violated', [finding(), finding(start=99)])):
            self.assertTrue(repair.violations(after)-repair.violations(before))

    def test_ungrounded_messages_are_not_coalesced(self):
        a, b = finding(), finding(message='different ungrounded error')
        for evidence in ([], [{'note': 'not a grounded location'}]):
            a['evidence'] = b['evidence'] = evidence
            self.assertNotEqual(repair.violations(audit('violated', [a])), repair.violations(audit('violated', [b])))


class RealAuditProgressTests(unittest.TestCase):
    def test_actual_output_shift_preserves_quantity_violation_identity(self):
        import test_final_semantic_validator as fixtures
        fixture = fixtures.FinalSemanticTests()
        fixture.setUp()
        fixture.mutate('30초', '60초')
        def validate_quantity():
            audit = repair.pipeline.validate_final_output(fixture.bundle, fixture.analysis,
                fixture.org, fixture.preview, fixture.result)
            # Compare one witnessed error from real full audits; unrelated heading
            # violations are intentionally outside this identity assertion.
            audit['structural_report']['findings'] = []
            audit['semantic_report']['findings'] = [f for f in audit['semantic_report']['findings']
                if f['rule_id'] == 'LITERAL_QUANTITY_OR_VERSION_REPLACED']
            self.assertTrue(audit['semantic_report']['findings'])
            return audit
        before = validate_quantity()
        fixture.mutate('# 안내', '# 긴 안내 제목')
        after = validate_quantity()
        self.assertNotEqual(before['semantic_report']['findings'][0]['evidence'],
                            after['semantic_report']['findings'][0]['evidence'])
        self.assertEqual(repair.violations(before), repair.violations(after))

    def test_distinct_source_occurrences_do_not_merge(self):
        a, b = finding(), finding()
        a['evidence'][0]['side'] = b['evidence'][0]['side'] = 'source'
        b['evidence'][0]['start'] = 99
        self.assertNotEqual(repair.violations(audit('violated', [a])),
                            repair.violations(audit('violated', [b])))

    def test_actual_trace_repair_with_completed_test_review_is_resolved(self):
        import copy
        import expression
        import test_final_semantic_validator as fixtures
        fixture = fixtures.FinalSemanticTests()
        fixture.setUp()
        valid = copy.deepcopy(fixture.result)
        fixture.result['trace'][0]['unit_refs'] = ['unknown']
        expression.seal(fixture.result, 'revision_sha256')
        def validate(result):
            return repair.pipeline.validate_final_output(fixture.bundle, fixture.analysis,
                fixture.org, fixture.preview, result, reviewer=fixtures.supported)
        before, after = validate(fixture.result), validate(valid)
        self.assertEqual(before['semantic_report']['checks']['PROVENANCE']['status'], 'violated')
        self.assertEqual(after['semantic_report']['checks']['PROVENANCE']['status'], 'supported')
        delta = repair.compare_progress(before, after)
        self.assertTrue(delta['resolved'])
        self.assertFalse(delta['unconfirmed'])
        self.assertFalse(delta['introduced'])
