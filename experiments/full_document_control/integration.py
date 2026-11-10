"""Read-only Markdown -> source analysis -> isolated candidate -> final audit CLI.

The offline analyzer inventories literal source blocks, not semantic truth. Recorded
extraction responses may be supplied. No approved stage transition is synthesized.
"""
import argparse
import copy
import json
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import expression
import organization
import pipeline
import reconstruction
import final_validator


def markdown_bundle(text, contract):
    doc = contract['output_scopes'][0]['document_id']
    sha = pipeline.digest_text(text)
    return {'case_id': 'markdown-integration', 'writing_contract': copy.deepcopy(contract),
            'document_snapshot': {'document_id': doc, 'snapshot_id': doc + ':source:' + sha[:12],
                'version': '1', 'coverage': 'complete', 'media_type': 'text/markdown', 'content': text, 'sha256': sha}}


def analyze_source(bundle, responses=None):
    """Reuse the existing assembler; default to a literal, unreviewed block inventory.

    No purpose/claim relationship is invented. Requirements needing semantic links
    can therefore fail the old gate and stop processing instead of being waived.
    """
    pipeline.validate_input_bundle(bundle)
    if responses is not None:
        return pipeline.assemble_document_analysis(bundle, responses)
    snapshot, contract = bundle['document_snapshot'], bundle['writing_contract']
    blocks = pipeline.parse_markdown_blocks(snapshot)
    by_id = {b['block_id']: b for b in blocks}
    windows = pipeline.plan_extraction_windows(snapshot, blocks, writing_contract=contract,
                  case_id=bundle['case_id'], input_sha256=pipeline.canonical_json_digest(bundle))
    raw = []
    for window in windows:
        units, coverage = [], []
        for bid in window['target_block_ids']:
            block = by_id[bid]
            uid = 'source-' + bid
            quote = {'block_id': bid, 'quote': block['text'].strip(), 'occurrence': 0}
            units.append({'id': uid, 'statement': quote['quote'], 'quotes': [quote],
                          'elements': [{'id': 'literal-' + bid, 'kind': 'claim', 'value': quote['quote'], 'quotes': [quote]}],
                          'relations': [], 'assessment': {'scope_id': contract['output_scopes'][0]['scope_id'],
                           'relevance': 'uncertain', 'importance': 'uncertain', 'preservation': 'retain_current',
                           'exposure': 'Source text retained in full', 'reason': 'Literal source-block inventory only',
                           'uncertainty': 'Semantic purpose, relationships and completeness need independent review'}})
            coverage.append({'block_id': bid, 'status': 'extracted', 'unit_ids': [uid], 'unresolved_reason': None})
        raw.append(json.dumps({'input_sha256': pipeline.canonical_json_digest(bundle), 'snapshot_id': snapshot['snapshot_id'],
                   'snapshot_sha256': snapshot['sha256'], 'window_id': window['window_id'],
                   'block_coverage': coverage, 'units': units,
                   'alignment': {'status': 'needs_review', 'reason': 'Purpose alignment has not been semantically evaluated'},
                   'unresolved_questions': ['Literal inventory is not semantic extraction or approval']}, ensure_ascii=False))
    return pipeline.assemble_document_analysis(bundle, raw)


class RevisionController:
    """Diagnose, invalidate descendants and stop. No speculative automatic retry."""
    def __init__(self, artifacts=None):
        self.artifacts = artifacts if artifacts is not None else {}

    def revalidate(self, bundle, analysis, org, preview, result, *, approval_record=None,
                   approval_evidence_source=None, **kwargs):
        audit = pipeline.validate_final_output(bundle, analysis, org, preview, result, **kwargs)
        report = audit['structural_report']
        findings = report['findings'] + audit['semantic_report']['findings']
        approval_report = pipeline.validate_final_approval_policy(bundle, analysis, org, preview, result, audit,
            approval_record, destination_snapshots=kwargs.get('destination_snapshots'),
            evidence_source=approval_evidence_source)
        return {'report': report, 'semantic_report': audit['semantic_report'], 'final_audit': audit, 'approval_report': approval_report,
                'controller': self.stop(findings) if audit['gate_state'] == 'FAIL' else None}

    def stop(self, findings):
        errors = [f for f in findings if f.get('severity') == 'ERROR']
        findings = errors or findings
        rules = ' '.join(f.get('rule_id', '') for f in findings)
        if any(k in rules for k in ('MOVE', 'DESTINATION', 'PLACEMENT', 'CONSOLIDATION', 'ORGANIZATION')):
            module, invalidated = 'information_organization', ['organization', 'expression', 'reconstruction', 'final_report']
        elif any(f.get('check_id') == 'EXPRESSION_FIDELITY' for f in findings) or any(k in rules for k in ('EXPRESSION', 'GENERATOR', 'GENERATION', 'PROTECTED_INFORMATION_LOSS', 'REGISTER', 'TERM_VIOLATION')):
            module, invalidated = 'expression_refinement', ['expression', 'reconstruction', 'final_report']
        elif any(k in rules for k in ('ANALYSIS', 'INPUT_DIGEST', 'CONTRACT_REF', 'SNAPSHOT_REF', 'EXTRACTION')):
            module, invalidated = 'information_extraction_analysis', ['analysis', 'organization', 'expression', 'reconstruction', 'final_report']
        else:
            module, invalidated = 'reconstruction', ['reconstruction', 'final_report']
        invalidated += ['final_semantic_report', 'final_audit', 'approval_request', 'approval_report']
        for name in invalidated:
            self.artifacts.pop(name, None)
        return {'state': 'STOPPED', 'last_gate_state': 'FAIL' if any(f.get('severity') == 'ERROR' for f in findings) else 'REVIEW',
                'responsible_module': module, 'invalidated_artifacts': invalidated, 'retry_count': 0,
                'reason': 'No verified automatic repair; re-run descendants after correcting the responsible input',
                'stage_transition_allowed': False}


def run_pipeline(bundle, *, responses=None, analysis=None, organization_plan=None,
                 generator=None, operations=None, destination_snapshots=None,
                 final_semantic_reviewer=None, max_final_review_chars=48000, final_review_timeout=30,
                 approval_record=None, approval_evidence_source=None):
    outcome = {'execution_mode': 'isolated_candidate', 'status': 'STOPPED', 'source_ref': copy.deepcopy(bundle.get('document_snapshot', {})),
               'analysis': None, 'analysis_report': None, 'organization_plan': None, 'expression_preview': None,
               'revision_result': None, 'final_report': None, 'final_semantic_report': None, 'final_audit': None, 'approval_report': None, 'controller': None,
               'stage_transition_allowed': False, 'delivery_approved': False}
    try:
        analysis = analysis if analysis is not None else analyze_source(bundle, responses)
        outcome['analysis'] = analysis
        report = pipeline.validate_analysis_gate(bundle, analysis)
        outcome['analysis_report'] = report
        if report['gate_state'] in {'FAIL', 'STOPPED'}:
            findings = [{'rule_id': 'ANALYSIS_INPUT_INVALID', 'severity': 'ERROR'}] + report.get('findings', [])
            outcome['controller'] = RevisionController().stop(findings)
            return outcome
        org = organization_plan if organization_plan is not None else organization.generate_organization_plan(bundle, analysis)
        outcome['organization_plan'] = org
        preview = expression.generate_revision_result(bundle, analysis, org, generator=generator,
                        operations=operations, destination_snapshots=destination_snapshots)
        outcome['expression_preview'] = preview
        revision = reconstruction.reconstruct_documents(bundle, analysis, org, preview, destination_snapshots=destination_snapshots)
        audit = pipeline.validate_final_output(bundle, analysis, org, preview, revision,
                    destination_snapshots=destination_snapshots, reviewer=final_semantic_reviewer,
                    max_review_chars=max_final_review_chars, timeout_seconds=final_review_timeout)
        final = audit['structural_report']
        approval_report = pipeline.validate_final_approval_policy(bundle, analysis, org, preview, revision, audit,
            approval_record, destination_snapshots=destination_snapshots, evidence_source=approval_evidence_source)
        outcome.update(revision_result=revision, final_report=final, final_semantic_report=audit['semantic_report'],
                       final_audit=audit, approval_report=approval_report, status=audit['gate_state'])
        if (audit['gate_state'] == 'FAIL' or revision['delivery_state'] != 'candidate'
                or any(f['rule_id'] == 'GENERATION_ERROR' for f in final['findings'])):
            outcome['status'] = 'STOPPED'
            outcome['controller'] = RevisionController().stop(final['findings'] + audit['semantic_report']['findings'])
    except Exception:
        # Fixed error codes only: provider/source exceptions may contain secrets.
        outcome['controller'] = RevisionController().stop([{'rule_id': 'EXTRACTION_OR_UPSTREAM_EXECUTION_ERROR', 'severity': 'ERROR'}])
    return outcome


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('markdown', type=Path)
    parser.add_argument('contract', type=Path)
    parser.add_argument('--response', type=Path, action='append', help='Optional existing extraction window JSON responses')
    parser.add_argument('--operations', type=Path, help='Existing expression operation mapping')
    args = parser.parse_args(argv)
    try:
        bundle = markdown_bundle(args.markdown.read_bytes().decode('utf-8'), pipeline.load_json_bytes(args.contract.read_bytes()))
        result = run_pipeline(bundle, responses=[p.read_bytes() for p in args.response] if args.response else None,
                  operations=pipeline.load_json_bytes(args.operations.read_bytes()) if args.operations else None)
    except Exception:
        result = {'status': 'STOPPED', 'error_code': 'INTEGRATION_INPUT_ERROR', 'delivery_approved': False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result['status'] == 'STOPPED' else 0


if __name__ == '__main__':
    raise SystemExit(main())
