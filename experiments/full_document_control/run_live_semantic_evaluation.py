"""Run independent live LLM Semantic Fidelity evaluation across all 14 benchmark cases.

Model: gemini-3.8-flash-low via `agy` CLI provider
Saves all prompts, raw responses, verified semantic reports, and gate reports into
`experiments/full_document_control/runs/live_eval_gemini_3_8_flash/`.
Generates overall summary in `experiments/full_document_control/runs/live_semantic_eval_summary.json`.
"""
import copy
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline
import semantic_eval_cases


def run_live_semantic_benchmark(
    *,
    model='gemini-3.8-flash-low',
    executable='agy',
    timeout_sec=90,
    output_dir='experiments/full_document_control/runs/live_eval_gemini_3_8_flash',
    summary_file='experiments/full_document_control/runs/live_semantic_eval_summary.json',
):
    os.makedirs(output_dir, exist_ok=True)
    cases = semantic_eval_cases.build_semantic_evaluation_cases()

    case_summaries = {}
    tp = 0
    tn = 0
    fp = 0
    fn = 0
    unresolved_holds = 0
    disagreements = []

    print(f'Starting live semantic evaluation of {len(cases)} cases using model {model!r}...')
    benchmark_start = time.monotonic()

    for idx, c in enumerate(cases):
        cid = c['eval_case_id']
        bundle = c['input_bundle']
        analysis = c['analysis_result']
        expected_j = c['manual_expected_judgment']
        case_dir = os.path.join(output_dir, cid)
        os.makedirs(case_dir, exist_ok=True)

        print(f'\n[{idx + 1}/{len(cases)}] Running {cid} (focus: {c["category_focus"]})...')
        case_start = time.monotonic()

        prompt_records = []
        raw_response_records = []

        def live_responder(w_idx, sw, prompt_text, attempt_no):
            sw_id = sw['semantic_window_id']
            prompt_file = os.path.join(case_dir, f'window_{w_idx}_{sw_id}_attempt_{attempt_no}.prompt.txt')
            with open(prompt_file, 'w', encoding='utf-8') as pf:
                pf.write(prompt_text)
            prompt_records.append({'window_index': w_idx, 'window_id': sw_id, 'attempt': attempt_no, 'path': prompt_file})

            res = pipeline.call_cli_provider(
                prompt_text,
                executable=executable,
                model=model,
                timeout=timeout_sec,
            )

            resp_file = os.path.join(case_dir, f'window_{w_idx}_{sw_id}_attempt_{attempt_no}.response.txt')
            with open(resp_file, 'wb') as rf:
                rf.write(res.get('stdout') or b'')
            raw_response_records.append({
                'window_index': w_idx,
                'window_id': sw_id,
                'attempt': attempt_no,
                'path': resp_file,
                'returncode': res.get('returncode'),
                'seconds': res.get('seconds'),
            })

            return res

        gate_report = pipeline.validate_analysis_gate(
            bundle,
            analysis,
            semantic_responder=live_responder,
            run_semantic_validation=True,
        )
        elapsed = time.monotonic() - case_start
        sem_report = gate_report.get('semantic_report') or {}
        actual_j = sem_report.get('overall_judgment', 'unresolved')
        gate_state = gate_report.get('gate_state', 'UNKNOWN')

        actual_cats = sorted({
            f['error_category'] for f in sem_report.get('findings', []) if f.get('error_category')
        })
        actual_paths = sorted({
            f['field_path'] for f in sem_report.get('findings', []) if f.get('field_path')
        })

        expect_is_error = expected_j in {'contradicted', 'overstated'}
        actual_is_error = actual_j in {'contradicted', 'overstated'}

        if expected_j == 'unresolved' and actual_j == 'unresolved':
            classification = 'UNRESOLVED_HOLD_MATCH'
            unresolved_holds += 1
        elif expect_is_error and actual_is_error:
            classification = 'TRUE_POSITIVE'
            tp += 1
        elif (not expect_is_error) and (not actual_is_error) and expected_j == actual_j:
            classification = 'TRUE_NEGATIVE'
            tn += 1
        elif (not expect_is_error) and actual_is_error:
            classification = 'FALSE_POSITIVE'
            fp += 1
        elif expect_is_error and (not actual_is_error):
            classification = 'FALSE_NEGATIVE'
            fn += 1
        else:
            classification = 'JUDGMENT_DIVERGENCE'

        # Verify integrity of produced report
        integrity_check = pipeline.verify_semantic_report_integrity(bundle, analysis, sem_report)

        # Save gate and semantic reports
        with open(os.path.join(case_dir, 'gate_report.json'), 'w', encoding='utf-8') as gf:
            json.dump(gate_report, gf, ensure_ascii=False, indent=2)
        with open(os.path.join(case_dir, 'semantic_report.json'), 'w', encoding='utf-8') as sf:
            json.dump(sem_report, sf, ensure_ascii=False, indent=2)

        meta = {
            'eval_case_id': cid,
            'source_case_id': c['source_case_id'],
            'category_focus': c['category_focus'],
            'description': c['description'],
            'manual_expected_judgment': expected_j,
            'actual_overall_judgment': actual_j,
            'manual_expected_gate_state': c['manual_expected_gate_state'],
            'actual_gate_state': gate_state,
            'manual_expected_error_categories': c['manual_expected_error_categories'],
            'actual_error_categories': actual_cats,
            'manual_expected_field_paths': c['manual_expected_field_paths'],
            'actual_field_paths': actual_paths,
            'classification': classification,
            'elapsed_seconds': round(elapsed, 3),
            'integrity_valid': integrity_check.get('valid', False),
            'integrity_code': integrity_check.get('code'),
            'coverage_complete': sem_report.get('coverage_summary', {}).get('is_complete', False),
            'prompt_files': [p['path'] for p in prompt_records],
            'response_files': [r['path'] for r in raw_response_records],
        }
        with open(os.path.join(case_dir, 'case_meta.json'), 'w', encoding='utf-8') as mf:
            json.dump(meta, mf, ensure_ascii=False, indent=2)

        case_summaries[cid] = meta
        print(f'   -> actual: {actual_j!r} (expected: {expected_j!r}) | gate: {gate_state} | class: {classification} ({elapsed:.1f}s)')

        if classification in {'FALSE_POSITIVE', 'FALSE_NEGATIVE', 'JUDGMENT_DIVERGENCE'} or c.get('is_boundary_disagreement_case'):
            disagreements.append({
                'eval_case_id': cid,
                'disagreement_kind': c.get('disagreement_kind', classification),
                'classification_in_mode': classification,
                'manual_expected_judgment': expected_j,
                'actual_overall_judgment': actual_j,
                'description': c['description'],
                'actual_error_categories': actual_cats,
            })

    total_benchmark_sec = round(time.monotonic() - benchmark_start, 2)
    summary_data = {
        'benchmark_metadata': {
            'model': model,
            'executable': executable,
            'total_cases': len(cases),
            'total_elapsed_seconds': total_benchmark_sec,
            'timestamp_iso': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'validator_version': sem_report.get('validator_version', 'v1'),
        },
        'metrics': {
            'true_positives': tp,
            'true_negatives': tn,
            'false_positives': fp,
            'false_negatives': fn,
            'unresolved_holds': unresolved_holds,
        },
        'case_summaries': case_summaries,
        'disagreements': disagreements,
    }

    with open(summary_file, 'w', encoding='utf-8') as sum_f:
        json.dump(summary_data, sum_f, ensure_ascii=False, indent=2)

    print('\n============================================================')
    print('Live Semantic Evaluation Complete!')
    print(f'Total Time: {total_benchmark_sec}s | Cases: {len(cases)}')
    print(f'TP: {tp} | TN: {tn} | FP: {fp} | FN: {fn} | Holds: {unresolved_holds}')
    print(f'Summary written to {summary_file}')
    print('============================================================')
    return summary_data


if __name__ == '__main__':
    run_live_semantic_benchmark()

