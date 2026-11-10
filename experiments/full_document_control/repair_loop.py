"""Bounded candidate repair. Host adapters propose data, never validation or approval.

Callbacks run with isolated copies in daemon threads; hosts must cancel external I/O.
The host process and independently configured validators remain trusted.
"""
import copy
import math
import time
from typing import Protocol

import expression
import final_semantic_validator
import integration
import organization
import pipeline
import reconstruction

STAGES = ('analysis', 'organization', 'expression', 'reconstruction')
REPORTS = ('final_report', 'final_semantic_report', 'final_audit', 'approval_request', 'approval_report')


class RepairAdapter(Protocol):
    def __call__(self, request: dict) -> dict:
        """Return exactly {'candidate': artifact}; no success or approval claims."""


# Explicit rules only: unknown ownership must never fall through to reconstruction.
RULES = {
    'MISSING_UNIT_STATEMENT': 'analysis',
    'UNKNOWN_RELATION_TARGET': 'analysis',
    'MISSING_RELATION_REASON': 'analysis',
    'PROTECTED_TRACEABILITY_VIOLATION': 'analysis',
    'ACTUAL_PLACEMENT_MISMATCH': 'organization',
    'PLACEMENT_ORDER_MISMATCH': 'organization',
    'MOVE_SEVERS_REQUIRED_CONDITION': 'organization',
    'GENERATION_ERROR': 'expression',
    'PROTECTED_INFORMATION_LOSS': 'expression',
    'REGISTER_VIOLATION': 'expression',
    'TERM_VIOLATION': 'expression',
    'EXPRESSION_CHANGE_HELD': 'expression',
    'OUTPUT_COVERAGE_GAP_OR_OVERLAP': 'reconstruction',
    'TRACE_SOURCE_OUTPUT_MISMATCH': 'reconstruction',
    'UNIT_TRACE_INVALID': 'reconstruction',
    'INFORMATION_UNIT_OMITTED': 'reconstruction',
    'LEDGER_OUTPUT_MISMATCH': 'reconstruction',
    'CHANGESET_LEDGER_MISMATCH': 'reconstruction',
}
TRUST_CHECKS = {'SNAPSHOT_INTEGRITY', 'APPROVAL_BOUNDARY'}


def diagnose(findings):
    actionable = [f for f in findings if f.get('severity') == 'ERROR' or f.get('rule_id') in {'GENERATION_ERROR', 'GENERATION_RECORD_UNVERIFIED'}]
    if not actionable:
        return None
    stages = []
    for f in actionable:
        rule = f.get('rule_id', '')
        if f.get('check_id') in TRUST_CHECKS or any(s in rule for s in
                ('DIGEST', 'STALE', 'CONTRACT', 'RECEIPT', 'UNVERIFIED', 'UNAUTHORIZED', 'SNAPSHOT')):
            return None
        stage = RULES.get(rule)
        if stage is None:
            return None
        stages.append(stage)
    return min(stages, key=STAGES.index)


def violations(audit):
    # Preserve check identity and grounded evidence, independent of report/run IDs.
    return {pipeline.canonical_json_digest({k: f[k] for k in ('check_id', 'rule_id', 'evidence', 'message') if k in f})
            for report in ('structural_report', 'semantic_report') for f in audit[report]['findings']
            if f.get('severity') == 'ERROR'}


def unresolved(audit):
    return {('structure', k) for k, v in audit['structural_report']['checks'].items() if v == 'unresolved'} | {
        ('semantic', k) for k, v in audit['semantic_report']['checks'].items() if v['status'] == 'unresolved'}


def newly_unresolved(before, after):
    previously_violated = {('structure', k) for k, v in before['structural_report']['checks'].items() if v == 'violated'} | {
        ('semantic', k) for k, v in before['semantic_report']['checks'].items() if v['status'] == 'violated'}
    return unresolved(after) - unresolved(before) - previously_violated


def effective_hash(artifacts):
    # Receipt IDs/nonces are deliberately excluded: new receipts are not new content.
    a, o, e, r = (artifacts.get(k) or {} for k in STAGES)
    return pipeline.canonical_json_digest([a.get('units'), o.get('placements'), o.get('actions'),
        e.get('output_snapshots'),
        [dict({k: f.get(k) for k in ('fragment_id', 'unit_id', 'content', 'source_span')},
              generation_status=f.get('generation', {}).get('status'))
         for f in e.get('preview_fragments', [])], r.get('output_snapshots'), r.get('trace')])


class DeterministicExpressionRepair:
    """Regenerate with the existing bounded deterministic generator, then re-audit."""
    def __call__(self, request):
        a = request['artifacts']
        return {'candidate': expression.generate_revision_result(request['bundle'], a['analysis'], a['organization'],
            destination_snapshots=request['destination_snapshots'])}


class RepairLoop:
    def __init__(self, *, max_attempts=3, budget_seconds=60, adapter_timeout=10):
        if type(max_attempts) is not int or max_attempts < 0:
            raise ValueError('max_attempts must be a nonnegative integer')
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
               for v in (budget_seconds, adapter_timeout)):
            raise ValueError('budgets must be finite and positive')
        self.max_attempts, self.budget_seconds, self.adapter_timeout = max_attempts, budget_seconds, adapter_timeout

    def run(self, bundle, artifacts, *, adapters=None, destination_snapshots=None, reviewer=None):
        start = time.monotonic()
        binding = pipeline.canonical_json_digest([bundle, destination_snapshots])
        b, destinations, state = copy.deepcopy((bundle, destination_snapshots, artifacts))
        for name in REPORTS:
            state.pop(name, None)
        history, seen = [], {effective_hash(state)}
        adapters = adapters or {}
        audit = None
        reason = 'MAX_ATTEMPTS'
        def changed():
            return pipeline.canonical_json_digest([bundle, destination_snapshots]) != binding
        def remaining():
            return self.budget_seconds - (time.monotonic() - start)
        def validate():
            upstream = pipeline.validate_analysis_gate(b, state.get('analysis'))
            if upstream['gate_state'] in {'FAIL', 'STOPPED'}:
                # A blocked upstream gate is explicit failure, never a final validation receipt.
                return {'gate_state': 'FAIL', 'upstream_report': upstream,
                    'structural_report': {'gate_state': 'FAIL', 'findings': upstream['findings'],
                                          'checks': dict.fromkeys(final_semantic_validator.final_validator.CHECKS, 'unresolved')},
                    'semantic_report': {'findings': [], 'checks': {
                        k: {'status': 'unresolved'} for k in final_semantic_validator.CHECKS}}}
            return pipeline.validate_final_output(b, *(state[k] for k in STAGES),
                destination_snapshots=destinations, reviewer=reviewer,
                timeout_seconds=max(0.001, min(self.adapter_timeout, remaining())))
        try:
            # Do not trust caller-supplied reports or approval evidence.
            audit = validate()
            for attempt in range(1, self.max_attempts + 1):
                if changed():
                    reason = 'INPUT_CHANGED'; break
                if remaining() <= 0:
                    reason = 'BUDGET_EXHAUSTED'; break
                findings = audit['structural_report']['findings'] + audit['semantic_report']['findings']
                target = diagnose(findings)
                if target is None:
                    reason = 'CANDIDATE_VALIDATED' if (not violations(audit) and state['reconstruction'].get('delivery_state') == 'candidate'
                        and not any(f.get('rule_id') == 'GENERATION_RECORD_UNVERIFIED' for f in findings)) else 'NO_TRUSTED_REPAIR_POINT'
                    break
                adapter = adapters.get(target)
                if adapter is None:
                    reason = 'ADAPTER_UNAVAILABLE'; break
                before = copy.deepcopy(audit)
                row = {'attempt': attempt, 'target_module': target, 'input_sha256': binding,
                       'before_candidate_sha256': effective_hash(state), 'evidence': copy.deepcopy(findings),
                       'before_validation': before, 'after_validation': None, 'after_candidate_sha256': None,
                       'invalidated': [], 'regenerated': [],
                       'judgment': 'not_applied', 'termination_reason': None,
                       'started_elapsed_seconds': time.monotonic()-start,
                       'snapshot_sha256': pipeline.canonical_json_digest([b['document_snapshot'], destinations])}
                history.append(row)
                tick = time.monotonic()
                request = {'attempt': attempt, 'target_module': target, 'bundle': b,
                    'destination_snapshots': destinations, 'artifacts': state, 'findings': findings}
                call_state, response = final_semantic_validator._call(adapter, request, min(self.adapter_timeout, remaining()))
                row['elapsed_seconds'] = time.monotonic() - tick
                if changed():
                    reason = 'INPUT_CHANGED'; break
                if remaining() <= 0:
                    reason = 'BUDGET_EXHAUSTED'; break
                if call_state != 'completed':
                    reason = 'ADAPTER_' + call_state.upper(); break
                if not isinstance(response, dict) or set(response) != {'candidate'} or not isinstance(response['candidate'], dict):
                    reason = 'INVALID_ADAPTER_RESPONSE'; break
                if expression.response_claims_approval(response):
                    reason = 'INVALID_ADAPTER_RESPONSE'; break
                # A report is current only until the first candidate mutation.
                audit = None
                index = STAGES.index(target)
                row['invalidated'] = list(STAGES[index:]) + list(REPORTS)
                for name in row['invalidated']:
                    state.pop(name, None)
                state[target] = copy.deepcopy(response['candidate'])
                if index < 1:
                    if pipeline.validate_analysis_gate(b, state['analysis'])['gate_state'] in {'FAIL', 'STOPPED'}:
                        reason = 'INVALID_ANALYSIS_CANDIDATE'; break
                    state['organization'] = organization.generate_organization_plan(b, state['analysis'], destination_snapshots=destinations)
                    row['regenerated'].append('organization')
                if index < 2:
                    state['expression'] = expression.generate_revision_result(b, state['analysis'], state['organization'], destination_snapshots=destinations)
                    row['regenerated'].append('expression')
                if index < 3:
                    state['reconstruction'] = reconstruction.reconstruct_documents(b, state['analysis'], state['organization'], state['expression'], destination_snapshots=destinations)
                    row['regenerated'].append('reconstruction')
                audit = validate()
                row['after_validation'] = copy.deepcopy(audit)
                fingerprint = effective_hash(state)
                row['after_candidate_sha256'] = fingerprint
                old, new = violations(before), violations(audit)
                row.update(resolved=sorted(old-new), introduced=sorted(new-old), unresolved_increased=sorted(newly_unresolved(before, audit)))
                if changed():
                    reason = 'INPUT_CHANGED'; break
                if remaining() <= 0:
                    reason = 'BUDGET_EXHAUSTED'; break
                if fingerprint in seen:
                    row['judgment'] = 'repeated'; reason = 'REPEATED_STATE'; break
                seen.add(fingerprint)
                if new-old or newly_unresolved(before, audit):
                    row['judgment'] = 'worsened'; reason = 'WORSENED'; break
                row['judgment'] = 'violations_resolved' if old-new else 'no_verified_progress'
                if not new and state['reconstruction'].get('delivery_state') == 'candidate' and not any(
                        f.get('rule_id') in {'GENERATION_ERROR', 'GENERATION_RECORD_UNVERIFIED'} for f in audit['structural_report']['findings']):
                    reason = 'CANDIDATE_VALIDATED'; break
                if not old-new:
                    reason = 'NO_VERIFIED_PROGRESS'; break
        except Exception:
            reason = 'EXECUTION_ERROR'
        if changed():
            reason = 'INPUT_CHANGED'
        for i, row in enumerate(history):
            end = history[i+1]['started_elapsed_seconds'] if i+1 < len(history) else time.monotonic()-start
            row['elapsed_seconds'] = end-row['started_elapsed_seconds']
        if history:
            history[-1]['termination_reason'] = reason
        # On changed input no report is current. Never export stale approval data.
        if reason == 'INPUT_CHANGED':
            audit = None
            state.clear()
        status = 'REVIEW' if reason == 'CANDIDATE_VALIDATED' else 'FAIL' if audit and violations(audit) else 'STOPPED'
        return {'status': status, 'termination_reason': reason, 'attempts': history,
                'artifacts': state, 'final_audit': audit, 'elapsed_seconds': time.monotonic()-start,
                'delivery_approved': False, 'stage_transition_allowed': False}


def run_repair_pipeline(bundle, *, adapters=None, max_attempts=3, budget_seconds=60,
                        adapter_timeout=10, reviewer=None, **kwargs):
    """Real integration path; extraction retries remain exclusively in ExecutionController."""
    controller = RepairLoop(max_attempts=max_attempts, budget_seconds=budget_seconds,
                            adapter_timeout=adapter_timeout)
    started = time.monotonic()
    binding = pipeline.canonical_json_digest([bundle, kwargs.get('destination_snapshots')])
    call_state, initial = final_semantic_validator._call(
        lambda request: integration.run_pipeline(request['bundle'], **request['options']),
        {'bundle': bundle, 'options': kwargs}, min(budget_seconds, adapter_timeout))
    elapsed = time.monotonic()-started
    changed = pipeline.canonical_json_digest([bundle, kwargs.get('destination_snapshots')]) != binding
    if call_state != 'completed' or elapsed >= budget_seconds or changed:
        return {'status': 'STOPPED', 'termination_reason': 'INPUT_CHANGED' if changed else
                'INITIAL_' + call_state.upper() if call_state != 'completed' else 'BUDGET_EXHAUSTED',
                'attempts': [], 'artifacts': {}, 'final_audit': None, 'elapsed_seconds': elapsed,
                'delivery_approved': False, 'stage_transition_allowed': False}
    controller.budget_seconds = budget_seconds-elapsed
    artifacts = dict(zip(STAGES, (initial['analysis'], initial['organization_plan'],
                                  initial['expression_preview'], initial['revision_result'])))
    result = controller.run(bundle, artifacts, adapters=adapters,
                      destination_snapshots=kwargs.get('destination_snapshots'), reviewer=reviewer)
    result['elapsed_seconds'] = time.monotonic()-started
    return result
