"""Policy success uses a test authority, never real human authentication."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import expression
import final_approval as approval
import final_semantic_validator as semantic
import test_final_semantic_validator as fixtures
from test_final_semantic_validator import supported


class TestEvidenceSource:
    """Independent test store; caller JSON cannot register/alter its entries."""
    mode = 'test_only'
    source_id = 'fixture-authority'

    def __init__(self):
        self.entries = {}

    def lookup(self, record_id):
        return copy.deepcopy(self.entries.get(record_id))

    def register(self, record):
        self.entries[record['approval_id']] = {'record': copy.deepcopy(record), 'revoked': False,
            'subject': 'human:test-reviewer', 'issuer': self.source_id, 'actor_kind': 'human'}


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.FinalSemanticTests()
        fixture.setUp()
        self.bundle, self.analysis, self.org = fixture.bundle, fixture.analysis, fixture.org
        self.preview, self.result = fixture.preview, fixture.result
        self.destinations = []
        self.source = TestEvidenceSource()
        self.audit = self.audit_now()

    def args(self):
        return (self.bundle, self.analysis, self.org, self.preview, self.result)

    def audit_now(self, reviewer=supported):
        return semantic.validate_final_audit(*self.args(), reviewer=reviewer, destination_snapshots=self.destinations)

    def request(self):
        return approval.build_approval_request(*self.args(), self.audit, destination_snapshots=self.destinations)

    def record(self, decision='approve'):
        request = self.request()
        snap = self.bundle['document_snapshot']
        now = int(time.time())
        record = {'version': approval.RECORD_VERSION, 'approval_id': 'approval-1',
            'request_sha256': request['request_sha256'], 'scope': request['scope'],
            'actor': {'subject': 'human:test-reviewer', 'issuer': self.source.source_id, 'kind': 'human'},
            'decision': decision, 'reason': 'Explicit synthetic human decision for this complete candidate',
            'issued_at': now - 1, 'expires_at': now + 300,
            'resolutions': [{'item_id': item['item_id'], 'judgment': 'accepted',
                'reason': 'Synthetic human reviewed this item in context', 'evidence': [
                    {'side': side, 'document_id': snapshot['document_id'], 'snapshot_sha256': snapshot['sha256'],
                     'start': 0, 'end': len(snapshot['content']), 'quote': snapshot['content']}
                    for side, snapshot in [('source', snap), *[('source', s) for s in self.destinations],
                                           *[('output', s) for s in self.result['output_snapshots']]]
                    if snapshot['content']]}
                for item in request['required_human_reviews']]}
        expression.seal(record, 'record_sha256')
        self.source.register(record)
        return record

    def evaluate(self, record=None, **kwargs):
        return approval.evaluate_final_approval(*self.args(), self.audit, record,
                                                destination_snapshots=self.destinations, **kwargs)

    def assert_held(self, report):
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertFalse(report['delivery_approved'])
        self.assertFalse(report['stage_transition_allowed'])

    def test_request_binds_actual_bodies_and_report_status(self):
        req = self.request()
        self.assertEqual(req['version'], approval.REQUEST_VERSION)
        self.assertIn('writing_contract', req['artifact_hashes'])
        self.assertEqual(req['validation']['semantic'], 'supported')
        self.assertGreaterEqual(len(req['required_human_reviews']), len(semantic.CHECKS))
        old = req['request_sha256']
        self.bundle['writing_contract']['purpose'] = 'Changed purpose'
        self.assertNotEqual(self.request()['request_sha256'], old)

    def test_missing_approval_never_passes(self):
        report = self.evaluate()
        self.assertEqual(report['policy_state'], 'UNAPPROVED')
        self.assert_held(report)

    def test_default_has_no_trusted_issuer_even_for_approved_json(self):
        record = self.record()
        record['approved'] = True
        report = self.evaluate(record)
        self.assertNotEqual(report['policy_state'], 'APPROVED')
        self.assert_held(report)

    def test_explicit_authenticated_test_approval_only_satisfies_policy(self):
        report = self.evaluate(self.record(), evidence_source=self.source)
        self.assertEqual(report['policy_state'], 'APPROVED')
        self.assertTrue(report['approval_evidence_valid'])
        self.assertEqual(report['trust_mode'], 'test_only')
        self.assertFalse(report['issuance_enabled'])
        self.assert_held(report)

    def test_model_supported_requires_all_human_reviews(self):
        record = self.record()
        record['resolutions'] = []
        expression.seal(record, 'record_sha256')
        self.source.register(record)
        report = self.evaluate(record, evidence_source=self.source)
        self.assertEqual(report['policy_state'], 'HOLD')
        self.assertTrue(report['unresolved_items'])

    def test_unresolved_semantics_require_explicit_evidenced_human_resolution(self):
        self.audit = self.audit_now(None)
        record = self.record()
        self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'APPROVED')
        record['resolutions'][0]['evidence'] = []
        expression.seal(record, 'record_sha256')
        self.source.register(record)
        self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'HOLD')

    def test_fabricated_evidence_does_not_resolve_item(self):
        record = self.record()
        record['resolutions'][0]['evidence'][0]['quote'] = 'fabricated'
        expression.seal(record, 'record_sha256')
        self.source.register(record)
        self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'HOLD')

    def test_reject_and_hold_keep_reason_and_unresolved_audit(self):
        for decision, state in [('reject', 'REJECTED'), ('hold', 'HOLD')]:
            with self.subTest(decision=decision):
                record = self.record(decision)
                record['resolutions'] = []
                expression.seal(record, 'record_sha256')
                self.source.register(record)
                report = self.evaluate(record, evidence_source=self.source)
                self.assertEqual(report['policy_state'], state)
                self.assertEqual(report['decision_record'], record)
                self.assertTrue(report['unresolved_items'])
                self.assert_held(report)

    def test_tamper_and_rehash_are_rejected_by_independent_store(self):
        for rehash in (False, True):
            record = self.record()
            record['reason'] = 'Changed by caller'
            if rehash:
                expression.seal(record, 'record_sha256')
            self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'INVALID')

    def test_model_cannot_impersonate_human(self):
        record = self.record()
        record['actor']['kind'] = 'model'
        expression.seal(record, 'record_sha256')
        self.source.register(record)
        self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'INVALID')

    def test_expiry_revocation_and_future_issuance(self):
        for kind in ('expired', 'revoked', 'future'):
            with self.subTest(kind=kind):
                record = self.record()
                if kind == 'expired':
                    record['issued_at'] -= 1000
                    record['expires_at'] -= 1000
                elif kind == 'future':
                    record['issued_at'] += 1000
                    record['expires_at'] += 1000
                expression.seal(record, 'record_sha256')
                self.source.register(record)
                self.source.entries['approval-1']['revoked'] = kind == 'revoked'
                self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'INVALID')

    def test_source_candidate_contract_and_version_changes_invalidate_approval(self):
        for obj, field in [(self.bundle['document_snapshot'], 'content'),
                           (self.result['output_snapshots'][0], 'content'),
                           (self.bundle['writing_contract'], 'purpose'),
                           (self.bundle['document_snapshot'], 'version'),
                           (self.bundle['document_snapshot'], 'document_id')]:
            with self.subTest(field=field):
                record = self.record()
                before = copy.deepcopy(obj)
                obj[field] = str(obj.get(field, '')) + 'changed'
                self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'INVALID')
                obj.clear()
                obj.update(before)

    def test_other_request_scope_and_record_version_reuse_rejected(self):
        for field in ('request_sha256', 'scope', 'version'):
            record = self.record()
            record[field] = 'other'
            expression.seal(record, 'record_sha256')
            self.source.register(record)
            self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'INVALID')

    def test_structural_failure_cannot_be_waived(self):
        self.result['output_snapshots'][0]['content'] += 'invented claim'
        expression.seal(self.result, 'revision_sha256')
        self.audit = self.audit_now()
        report = self.evaluate(self.record(), evidence_source=self.source)
        self.assertEqual(report['policy_state'], 'BLOCKED')
        self.assertEqual(report['gate_state'], 'FAIL')

    def test_confirmed_semantic_violation_cannot_be_waived(self):
        def contradicted(request):
            response = supported(request)
            response['reviews'][0]['judgment'] = 'contradicted'
            return response
        self.audit = self.audit_now(contradicted)
        self.assertEqual(self.evaluate(self.record(), evidence_source=self.source)['policy_state'], 'BLOCKED')

    def test_rehashed_audit_and_lost_execution_receipt_fail_closed(self):
        record = self.record()
        old = copy.deepcopy(self.audit)
        self.audit['semantic_report']['overall_judgment'] = 'unresolved'
        expression.seal(self.audit['semantic_report'], 'report_sha256')
        expression.seal(self.audit, 'report_sha256')
        self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'INVALID')
        self.audit = old
        with patch.dict(semantic._RECEIPTS, {}, clear=True):
            self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'INVALID')

    def test_failed_authority_lookup_fails_closed(self):
        record = self.record()
        with patch.object(self.source, 'lookup', side_effect=RuntimeError('private secret')):
            report = self.evaluate(record, evidence_source=self.source)
        self.assertEqual(report['policy_state'], 'INVALID')
        self.assertNotIn('private secret', str(report))

    def test_unsupported_source_mode_does_not_enable_real_issuance(self):
        record = self.record()
        self.source.mode = 'production'
        self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'INVALID')

    def test_source_only_evidence_cannot_approve_complete_output(self):
        record = self.record()
        record['resolutions'][0]['evidence'] = [span for span in record['resolutions'][0]['evidence']
                                               if span['side'] == 'source']
        expression.seal(record, 'record_sha256')
        self.source.register(record)
        self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'HOLD')

    def test_source_callback_mutation_and_receipt_loss_fail_closed(self):
        record = self.record()
        lookup = self.source.lookup
        def mutate(record_id):
            self.bundle['writing_contract']['purpose'] = 'raced mutation'
            return lookup(record_id)
        with patch.object(self.source, 'lookup', side_effect=mutate):
            self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'INVALID')

    def test_missing_lookup_entry_duplicate_resolutions_and_malformed_records(self):
        for value in [True, [], 'approved', {'approved': True}]:
            self.assertEqual(self.evaluate(value, evidence_source=self.source)['policy_state'], 'INVALID')
        record = self.record()
        self.source.entries.clear()
        self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'INVALID')
        record = self.record()
        record['resolutions'].append(copy.deepcopy(record['resolutions'][0]))
        expression.seal(record, 'record_sha256')
        self.source.register(record)
        self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'HOLD')

    def test_failed_validation_execution_cannot_be_approved(self):
        def failed(request):
            raise RuntimeError('review failed')
        self.audit = self.audit_now(failed)
        self.assertEqual(self.evaluate(self.record(), evidence_source=self.source)['policy_state'], 'HOLD')

    def test_pipeline_exposes_separate_held_approval_report(self):
        import integration
        outcome = integration.run_pipeline(self.bundle, analysis=self.analysis,
                                           final_semantic_reviewer=supported)
        self.assertEqual(outcome['approval_report']['policy_state'], 'UNAPPROVED')
        self.assertFalse(outcome['delivery_approved'])
        self.assertEqual(outcome['status'], 'REVIEW')

    def test_controller_invalidates_approval_artifacts(self):
        import integration
        artifacts = dict.fromkeys(['final_report', 'final_semantic_report', 'final_audit',
                                   'approval_request', 'approval_report'], {})
        result = integration.RevisionController(artifacts).stop([{'rule_id': 'FAIL', 'severity': 'ERROR'}])
        self.assertIn('approval_report', result['invalidated_artifacts'])
        self.assertNotIn('approval_request', artifacts)

    def test_real_process_restart_loses_validation_evidence(self):
        record = self.record()
        script = ("import json,sys; import final_approval as a; "
                  "v=json.load(sys.stdin); print(json.dumps(a.evaluate_final_approval(*v)))")
        child = subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).resolve().parent,
            input=json.dumps([*self.args(), self.audit, record]), text=True, capture_output=True, check=True)
        report = json.loads(child.stdout)
        self.assertEqual(report['policy_state'], 'INVALID')
        self.assertEqual(report['findings'][0]['rule_id'], 'VALIDATION_EVIDENCE_INVALID_OR_LOST')

    def test_destination_body_and_version_change_invalidate_approval(self):
        import test_integration
        fixture = test_integration.ReconstructionTests()
        fixture.setup_move()
        self.bundle, self.analysis, self.org = fixture.bundle, fixture.analysis, fixture.org
        self.preview, self.result = fixture.preview, fixture.candidate()
        self.destinations = fixture.snaps
        self.audit = self.audit_now()
        record = self.record()
        self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'APPROVED')
        for field in ('content', 'version', 'document_id'):
            before = copy.deepcopy(self.destinations[0])
            self.destinations[0][field] += 'changed'
            self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'INVALID')
            self.destinations[0] = before

    def test_recomputed_validation_does_not_reauthorize_old_decision(self):
        record = self.record()
        self.bundle['writing_contract']['purpose'] = 'Another purpose'
        import integration, organization, reconstruction
        self.analysis = integration.analyze_source(self.bundle)
        self.org = organization.generate_organization_plan(self.bundle, self.analysis)
        self.preview = expression.generate_revision_result(self.bundle, self.analysis, self.org)
        self.result = reconstruction.reconstruct_documents(*self.args()[:4])
        self.audit = self.audit_now()
        self.assertEqual(self.evaluate(record, evidence_source=self.source)['policy_state'], 'INVALID')

    def test_policy_report_reverification_rejects_rehash_and_revocation(self):
        record = self.record()
        report = self.evaluate(record, evidence_source=self.source)
        def verify(value):
            return approval.verify_approval_report(*self.args(), self.audit, value, evidence_source=self.source)
        self.assertTrue(verify(report)['valid'])
        forged = copy.deepcopy(report)
        forged['delivery_approved'] = True
        expression.seal(forged, 'report_sha256')
        self.assertFalse(verify(forged)['valid'])
        self.source.entries['approval-1']['revoked'] = True
        self.assertFalse(verify(report)['valid'])

    def test_revocation_reason_is_retained_in_evidence_observation(self):
        record = self.record()
        self.source.entries['approval-1'].update(revoked=True, revoked_at=record['issued_at'],
                                               revocation_reason='Human withdrew decision')
        report = self.evaluate(record, evidence_source=self.source)
        self.assertEqual(report['evidence_observation']['revocation_reason'], 'Human withdrew decision')
        self.assertFalse(report['approval_evidence_valid'])

    def test_old_validation_evidence_requires_new_audit(self):
        record = self.record()
        with patch.object(semantic.time, 'monotonic', return_value=time.monotonic() + 901):
            report = self.evaluate(record, evidence_source=self.source)
        self.assertEqual(report['policy_state'], 'INVALID')
        self.assertFalse(report['approval_evidence_valid'])

    def test_missing_validation_freshness_evidence_fails_closed(self):
        record = self.record()
        with patch.dict(semantic._RECEIPT_CREATED_AT, {}, clear=True):
            report = self.evaluate(record, evidence_source=self.source)
        self.assertEqual(report['policy_state'], 'INVALID')
