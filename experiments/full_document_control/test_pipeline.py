import copy
import json
from pathlib import Path
import unittest

from experiments.full_document_control import pipeline

HERE = Path(__file__).resolve().parent
SAMPLE_INPUT_PATH = HERE / 'sample_input.json'


def load_sample_bundle():
    return pipeline.load_json_bytes(SAMPLE_INPUT_PATH.read_bytes())


def make_valid_window_response(bundle=None, *, window_id='W001'):
    if bundle is None:
        bundle = load_sample_bundle()
    input_sha256 = pipeline.canonical_json_digest(bundle)
    snap = bundle['document_snapshot']
    scope_id = bundle['writing_contract']['output_scopes'][0]['scope_id']

    def assessment(importance='required', preservation='retain_current',
                   exposure='주장 및 설치 지시와 함께 현재 문서에 직접 노출'):
        return {
            'scope_id': scope_id,
            'relevance': 'relevant',
            'importance': importance,
            'preservation': preservation,
            'exposure': exposure,
            'reason': '설치 수행과 운영 제약 확인에 직접 필요한 정보다.',
            'uncertainty': '원문 서술에 근거하며 실제 런타임 동작은 별도 실행 검증하지 않았다.',
        }

    return {
        'input_sha256': input_sha256,
        'snapshot_id': snap['snapshot_id'],
        'snapshot_sha256': snap['sha256'],
        'window_id': window_id,
        'block_coverage': [
            {'block_id': 'B001', 'status': 'extracted', 'unit_ids': ['u-heading-main'], 'unresolved_reason': None},
            {'block_id': 'B003', 'status': 'extracted', 'unit_ids': ['u-runtime-overview', 'u-timeout'], 'unresolved_reason': None},
            {'block_id': 'B005', 'status': 'extracted', 'unit_ids': ['u-heading-env'], 'unresolved_reason': None},
            {'block_id': 'B007', 'status': 'extracted', 'unit_ids': ['u-table-ubuntu', 'u-table-macos'], 'unresolved_reason': None},
            {'block_id': 'B009', 'status': 'extracted', 'unit_ids': ['u-code-install'], 'unresolved_reason': None},
            {'block_id': 'B013', 'status': 'extracted', 'unit_ids': ['u-heading-caveats'], 'unresolved_reason': None},
            {'block_id': 'B015', 'status': 'extracted', 'unit_ids': ['u-cond-offline-cache', 'u-cond-macos-manual'], 'unresolved_reason': None},
        ],
        'units': [
            {
                'id': 'u-heading-main',
                'statement': '문서는 로컬 런타임 설치 안내를 다룬다.',
                'quotes': [{'block_id': 'B001', 'quote': '# 로컬 런타임 설치 안내', 'occurrence': 0}],
                'elements': [
                    {
                        'id': 'el-title',
                        'kind': 'claim',
                        'value': '로컬 런타임 설치 안내',
                        'quotes': [{'block_id': 'B001', 'quote': '# 로컬 런타임 설치 안내', 'occurrence': 0}],
                    }
                ],
                'relations': [],
                'assessment': assessment(importance='useful'),
            },
            {
                'id': 'u-runtime-overview',
                'statement': '로컬 에이전트 런타임 v0.4.0은 외부 클라우드 업로드 없이 작업 폴더 내에서 파일 검색과 테스트 실행을 수행한다.',
                'quotes': [
                    {
                        'block_id': 'B003',
                        'quote': '로컬 에이전트 런타임 v0.4.0은 외부 클라우드 업로드 없이 작업 폴더 안에서 파일 검색과 테스트 실행을 수행한다.',
                        'occurrence': 0,
                    }
                ],
                'elements': [
                    {
                        'id': 'el-version',
                        'kind': 'identifier',
                        'value': 'v0.4.0',
                        'quotes': [{'block_id': 'B003', 'quote': '로컬 에이전트 런타임 v0.4.0은', 'occurrence': 0}],
                    },
                    {
                        'id': 'el-no-cloud',
                        'kind': 'claim',
                        'value': '외부 클라우드 업로드 없이 작업 폴더 안에서 파일 검색과 테스트 실행을 수행한다',
                        'quotes': [
                            {
                                'block_id': 'B003',
                                'quote': '외부 클라우드 업로드 없이 작업 폴더 안에서 파일 검색과 테스트 실행을 수행한다.',
                                'occurrence': 0,
                            }
                        ],
                    },
                ],
                'relations': [],
                'assessment': assessment(),
            },
            {
                'id': 'u-timeout',
                'statement': '기본 요청 제한 시간은 30초다.',
                'quotes': [{'block_id': 'B003', 'quote': '기본 요청 제한 시간은 30초다.', 'occurrence': 0}],
                'elements': [
                    {
                        'id': 'el-timeout-val',
                        'kind': 'quantity',
                        'value': '30초',
                        'quotes': [{'block_id': 'B003', 'quote': '기본 요청 제한 시간은 30초다.', 'occurrence': 0}],
                    }
                ],
                'relations': [
                    {
                        'kind': 'supports',
                        'target_unit_id': 'u-runtime-overview',
                        'reason': '런타임 기본 동작의 시간 제한 사양을 보충한다.',
                    }
                ],
                'assessment': assessment(),
            },
            {
                'id': 'u-heading-env',
                'statement': '지원 환경 및 패키지 섹션 제목이다.',
                'quotes': [{'block_id': 'B005', 'quote': '## 지원 환경 및 패키지', 'occurrence': 0}],
                'elements': [
                    {
                        'id': 'el-env-heading',
                        'kind': 'claim',
                        'value': '지원 환경 및 패키지',
                        'quotes': [{'block_id': 'B005', 'quote': '## 지원 환경 및 패키지', 'occurrence': 0}],
                    }
                ],
                'relations': [],
                'assessment': assessment(importance='useful'),
            },
            {
                'id': 'u-table-ubuntu',
                'statement': 'Ubuntu 최소 지원 버전은 22.04 LTS이며 설치 패키지는 runtime-linux-x64.tar.gz다.',
                'quotes': [
                    {
                        'block_id': 'B007',
                        'quote': '| Ubuntu | 22.04 LTS | `runtime-linux-x64.tar.gz` |',
                        'occurrence': 0,
                    }
                ],
                'elements': [
                    {
                        'id': 'el-ubuntu-ver',
                        'kind': 'quantity',
                        'value': '22.04 LTS',
                        'quotes': [{'block_id': 'B007', 'quote': '| Ubuntu | 22.04 LTS | `runtime-linux-x64.tar.gz` |', 'occurrence': 0}],
                    },
                    {
                        'id': 'el-linux-pkg',
                        'kind': 'identifier',
                        'value': 'runtime-linux-x64.tar.gz',
                        'quotes': [{'block_id': 'B007', 'quote': '| Ubuntu | 22.04 LTS | `runtime-linux-x64.tar.gz` |', 'occurrence': 0}],
                    },
                ],
                'relations': [],
                'assessment': assessment(),
            },
            {
                'id': 'u-table-macos',
                'statement': 'macOS 최소 지원 버전은 14.0이며 설치 패키지는 runtime-macos-14.pkg다.',
                'quotes': [
                    {
                        'block_id': 'B007',
                        'quote': '| macOS | 14.0 | `runtime-macos-14.pkg` |',
                        'occurrence': 0,
                    }
                ],
                'elements': [
                    {
                        'id': 'el-macos-ver',
                        'kind': 'quantity',
                        'value': '14.0',
                        'quotes': [{'block_id': 'B007', 'quote': '| macOS | 14.0 | `runtime-macos-14.pkg` |', 'occurrence': 0}],
                    },
                    {
                        'id': 'el-macos-pkg',
                        'kind': 'identifier',
                        'value': 'runtime-macos-14.pkg',
                        'quotes': [{'block_id': 'B007', 'quote': '| macOS | 14.0 | `runtime-macos-14.pkg` |', 'occurrence': 0}],
                    },
                ],
                'relations': [],
                'assessment': assessment(),
            },
            {
                'id': 'u-code-install',
                'statement': 'Linux 패키지를 압축 해제한 뒤 ./install.sh --port 8765 명령으로 설치한다.',
                'quotes': [
                    {
                        'block_id': 'B009',
                        'quote': 'tar -xzf runtime-linux-x64.tar.gz\n./install.sh --port 8765',
                        'occurrence': 0,
                    }
                ],
                'elements': [
                    {
                        'id': 'el-install-cmd',
                        'kind': 'claim',
                        'value': './install.sh --port 8765',
                        'quotes': [{'block_id': 'B009', 'quote': './install.sh --port 8765', 'occurrence': 0}],
                    }
                ],
                'relations': [
                    {
                        'kind': 'depends_on',
                        'target_unit_id': 'u-table-ubuntu',
                        'reason': '표에 정의된 Linux 패키지 아카이브를 입력으로 사용한다.',
                    }
                ],
                'assessment': assessment(),
            },
            {
                'id': 'u-heading-caveats',
                'statement': '운영 제약 및 주의사항 섹션 제목이다.',
                'quotes': [{'block_id': 'B013', 'quote': '## 운영 제약 및 주의사항', 'occurrence': 0}],
                'elements': [
                    {
                        'id': 'el-caveat-heading',
                        'kind': 'claim',
                        'value': '운영 제약 및 주의사항',
                        'quotes': [{'block_id': 'B013', 'quote': '## 운영 제약 및 주의사항', 'occurrence': 0}],
                    }
                ],
                'relations': [],
                'assessment': assessment(importance='useful'),
            },
            {
                'id': 'u-cond-offline-cache',
                'statement': '오프라인 모드는 사전 다운로드된 모델 캐시(~/.cache/local-runtime)가 존재할 때만 동작한다.',
                'quotes': [
                    {
                        'block_id': 'B015',
                        'quote': '- 오프라인 모드는 사전 다운로드된 모델 캐시(`~/.cache/local-runtime`)가 존재할 때만 동작한다.',
                        'occurrence': 0,
                    }
                ],
                'elements': [
                    {
                        'id': 'el-cache-path',
                        'kind': 'condition',
                        'value': '~/.cache/local-runtime',
                        'quotes': [
                            {
                                'block_id': 'B015',
                                'quote': '사전 다운로드된 모델 캐시(`~/.cache/local-runtime`)가 존재할 때만 동작한다.',
                                'occurrence': 0,
                            }
                        ],
                    }
                ],
                'relations': [
                    {
                        'kind': 'qualifies',
                        'target_unit_id': 'u-runtime-overview',
                        'reason': 'B003의 외부 업로드 없는 로컬 실행 주장에 대해 오프라인 캐시 선행 조건을 한정한다.',
                    }
                ],
                'assessment': assessment(),
            },
            {
                'id': 'u-cond-macos-manual',
                'statement': 'macOS 패키지는 초기 실험 빌드이므로 자동 업데이트를 지원하지 않으며 수동으로 재설치해야 한다.',
                'quotes': [
                    {
                        'block_id': 'B015',
                        'quote': '- macOS 패키지는 초기 실험 빌드이므로 자동 업데이트를 지원하지 않으며 수동으로 재설치해야 한다.',
                        'occurrence': 0,
                    }
                ],
                'elements': [
                    {
                        'id': 'el-macos-manual-cond',
                        'kind': 'condition',
                        'value': '자동 업데이트를 지원하지 않으며 수동으로 재설치해야 한다',
                        'quotes': [
                            {
                                'block_id': 'B015',
                                'quote': '자동 업데이트를 지원하지 않으며 수동으로 재설치해야 한다.',
                                'occurrence': 0,
                            }
                        ],
                    }
                ],
                'relations': [
                    {
                        'kind': 'qualifies',
                        'target_unit_id': 'u-table-macos',
                        'reason': 'B007 표의 macOS 패키지 항목에 대해 자동 업데이트 미지원 제약을 한정한다.',
                    }
                ],
                'assessment': assessment(),
            },
        ],
        'alignment': {
            'status': 'aligned',
            'reason': '설치 안내와 운영 제약을 모두 다루며 계약 목적과 일치한다.',
        },
        'unresolved_questions': [],
    }


class Stage1FullDocumentTests(unittest.TestCase):
    def test_full_document_partition_has_no_gaps_or_overlaps(self):
        bundle = load_sample_bundle()
        snapshot = bundle['document_snapshot']
        blocks = pipeline.parse_markdown_blocks(snapshot)
        self.assertEqual(len(blocks), 15)
        self.assertEqual(blocks[0]['start'], 0)
        self.assertEqual(blocks[-1]['end'], len(snapshot['content']))
        for prev, curr in zip(blocks, blocks[1:]):
            self.assertEqual(prev['end'], curr['start'])
        kinds = [b['kind'] for b in blocks if b['extractable']]
        self.assertEqual(
            kinds,
            ['heading', 'paragraph', 'heading', 'table', 'code_block', 'heading', 'list'],
        )
        excluded = [b for b in blocks if not b['extractable']]
        self.assertTrue(all(b['exclusion_reason'] is not None for b in excluded))

    def test_unsupported_markdown_is_preserved_as_unsupported_never_dropped(self):
        bundle = load_sample_bundle()
        snap = copy.deepcopy(bundle['document_snapshot'])
        snap['content'] += '\n<div>raw html block</div>\n```python\nunclosed_code()\n'
        snap['sha256'] = pipeline.digest_text(snap['content'])
        blocks = pipeline.parse_markdown_blocks(snap)
        unsupported = [b for b in blocks if b['kind'] == 'unsupported']
        self.assertEqual(len(unsupported), 2)
        self.assertEqual(unsupported[0]['unsupported_reason'], 'unsupported_markdown_construct')
        self.assertEqual(unsupported[1]['unsupported_reason'], 'unclosed_code_fence')
        self.assertEqual(blocks[-1]['end'], len(snap['content']))

    def test_window_planning_retains_document_identity_and_context(self):
        bundle = load_sample_bundle()
        snapshot = bundle['document_snapshot']
        blocks = pipeline.parse_markdown_blocks(snapshot)
        windows = pipeline.plan_extraction_windows(snapshot, blocks, max_window_chars=180)
        self.assertGreater(len(windows), 1)
        all_targets = []
        for w in windows:
            self.assertEqual(w['snapshot_id'], snapshot['snapshot_id'])
            self.assertEqual(w['snapshot_sha256'], snapshot['sha256'])
            self.assertEqual(len(w['document_block_outline']), len(blocks))
            self.assertTrue(set(w['target_block_ids']).isdisjoint(set(w['context_block_ids'])))
            all_targets.extend(w['target_block_ids'])
        extractable_ids = [b['block_id'] for b in blocks if b['extractable']]
        self.assertEqual(all_targets, extractable_ids)

    def test_assemble_document_analysis_tracks_cross_block_relations_and_all_structures(self):
        bundle = load_sample_bundle()
        resp = make_valid_window_response(bundle)
        analysis = pipeline.assemble_document_analysis(bundle, [ json.dumps(resp) ])
        self.assertEqual(analysis['snapshot_sha256'], bundle['document_snapshot']['sha256'])
        self.assertEqual(analysis['semantic_fidelity'], 'not_run')
        self.assertFalse(analysis['delivery_approved'])
        self.assertTrue(all(rb['satisfied'] for rb in analysis['requirement_bindings']))
        cross_block_rels = [
            rel for u in analysis['units'] for rel in u['relations'] if rel['cross_block']
        ]
        self.assertEqual(len(cross_block_rels), 3)


class Stage2ValidationGateTests(unittest.TestCase):
    def test_valid_structure_passes_deterministic_checks_but_remains_review(self):
        bundle = load_sample_bundle()
        resp = make_valid_window_response(bundle)
        analysis = pipeline.assemble_document_analysis(bundle, [json.dumps(resp)])
        report = pipeline.validate_analysis_gate(bundle, analysis)
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertEqual(report['execution_state'], 'completed')
        self.assertFalse(report['delivery_approved'])
        self.assertFalse(report['next_stage_allowed'])
        by_id = {r['check_id']: r['status'] for r in report['check_results']}
        self.assertEqual(by_id['SNAPSHOT_AND_CONTRACT'], 'passed')
        self.assertEqual(by_id['BLOCK_COVERAGE'], 'passed')
        self.assertEqual(by_id['UNIT_AND_SPAN_INTEGRITY'], 'passed')
        self.assertEqual(by_id['PROTECTED_TRACEABILITY'], 'passed')
        self.assertEqual(by_id['SEMANTIC_FIDELITY'], 'not_run')

    def test_missing_and_duplicate_blocks_fail_block_coverage_gate(self):
        bundle = load_sample_bundle()
        # 1. Missing block B005
        resp_missing = make_valid_window_response(bundle)
        resp_missing['block_coverage'] = [
            b for b in resp_missing['block_coverage'] if b['block_id'] != 'B005'
        ]
        resp_missing['units'] = [
            u for u in resp_missing['units'] if u['id'] != 'u-heading-env'
        ]
        analysis_missing = pipeline.assemble_document_analysis(bundle, [json.dumps(resp_missing)])
        report_missing = pipeline.validate_analysis_gate(bundle, analysis_missing)
        self.assertEqual(report_missing['gate_state'], 'FAIL')
        by_id = {r['check_id']: r for r in report_missing['check_results']}
        self.assertEqual(by_id['BLOCK_COVERAGE']['status'], 'violated')
        self.assertIn('EXTRACTABLE_BLOCK_MISSING', by_id['BLOCK_COVERAGE']['reason'])

        # 2. Duplicate block B001
        resp_dup = make_valid_window_response(bundle)
        resp_dup['block_coverage'].append(dict(resp_dup['block_coverage'][0]))
        analysis_dup = pipeline.assemble_document_analysis(bundle, [json.dumps(resp_dup)])
        report_dup = pipeline.validate_analysis_gate(bundle, analysis_dup)
        self.assertEqual(report_dup['gate_state'], 'FAIL')
        by_id_dup = {r['check_id']: r for r in report_dup['check_results']}
        self.assertEqual(by_id_dup['BLOCK_COVERAGE']['status'], 'violated')
        self.assertIn('EXTRACTABLE_BLOCK_DUPLICATED', by_id_dup['BLOCK_COVERAGE']['reason'])

    def test_bad_span_or_missing_protected_info_or_unlinked_condition_fails_gate(self):
        bundle = load_sample_bundle()
        resp = make_valid_window_response(bundle)
        analysis = pipeline.assemble_document_analysis(bundle, [json.dumps(resp)])

        # Tamper with a span offset in analysis
        bad_span_analysis = copy.deepcopy(analysis)
        bad_span_analysis['units'][1]['source_spans'][0]['end'] += 1
        report_bad_span = pipeline.validate_analysis_gate(bundle, bad_span_analysis)
        self.assertEqual(report_bad_span['gate_state'], 'FAIL')
        by_id = {r['check_id']: r for r in report_bad_span['check_results']}
        self.assertEqual(by_id['UNIT_AND_SPAN_INTEGRITY']['status'], 'violated')

        # Remove cross-block condition relation on u-cond-offline-cache
        unlinked_analysis = copy.deepcopy(analysis)
        for u in unlinked_analysis['units']:
            if u['id'] == 'u-cond-offline-cache':
                u['relations'] = []
        report_unlinked = pipeline.validate_analysis_gate(bundle, unlinked_analysis)
        self.assertEqual(report_unlinked['gate_state'], 'FAIL')
        by_id_unlinked = {r['check_id']: r for r in report_unlinked['check_results']}
        self.assertEqual(by_id_unlinked['PROTECTED_TRACEABILITY']['status'], 'violated')
        self.assertIn('req-offline-cache-condition', by_id_unlinked['PROTECTED_TRACEABILITY']['reason'])

        # Remove protected literal from code block unit
        missing_lit_analysis = copy.deepcopy(analysis)
        for u in missing_lit_analysis['units']:
            if u['id'] == 'u-code-install':
                u['elements'] = []
        report_missing_lit = pipeline.validate_analysis_gate(bundle, missing_lit_analysis)
        self.assertEqual(report_missing_lit['gate_state'], 'FAIL')
        by_id_lit = {r['check_id']: r for r in report_missing_lit['check_results']}
        self.assertEqual(by_id_lit['PROTECTED_TRACEABILITY']['status'], 'violated')
        self.assertIn('req-install-port', by_id_lit['PROTECTED_TRACEABILITY']['reason'])

    def test_model_self_approval_and_missing_check_results_are_rejected(self):
        bundle = load_sample_bundle()
        resp = make_valid_window_response(bundle)
        analysis = pipeline.assemble_document_analysis(bundle, [json.dumps(resp)])

        # Self-approval injection in analysis artifact
        spoofed = copy.deepcopy(analysis)
        spoofed['delivery_approved'] = True
        report_spoof = pipeline.validate_analysis_gate(bundle, spoofed)
        self.assertEqual(report_spoof['gate_state'], 'FAIL')
        self.assertFalse(report_spoof['delivery_approved'])

        # Missing required check row -> STOPPED, preserving last_gate_state='FAIL' if a violation occurred
        plan = pipeline.build_validation_plan(bundle)
        checked = {
            'snapshot_sha256': bundle['document_snapshot']['sha256'],
            'analysis_sha256': analysis['analysis_sha256'],
        }
        partial_rows = [
            {
                'check_id': 'SNAPSHOT_AND_CONTRACT',
                'check_version': '1',
                'status': 'violated',
                'reason': 'Digest mismatch',
                'evidence': [],
                'checked_snapshot_sha256': checked['snapshot_sha256'],
                'checked_analysis_sha256': checked['analysis_sha256'],
            }
        ]
        reconciled = pipeline.reconcile_validation_plan(plan, partial_rows, checked)
        self.assertEqual(reconciled['gate_state'], 'STOPPED')
        self.assertEqual(reconciled['execution_state'], 'stopped')
        self.assertEqual(reconciled['last_gate_state'], 'FAIL')
        self.assertFalse(reconciled['delivery_approved'])
        self.assertTrue(any(d.startswith('CHECK_RESULT_MISSING:') for d in reconciled['diagnostics']))


class Stage3And4ControllerE2ETests(unittest.TestCase):
    def test_scenario_1_normal_full_document_input_and_block_range_tracking(self):
        bundle = load_sample_bundle()
        adapter = pipeline.OrganizationBoundaryAdapter()
        controller = pipeline.ExecutionController(max_attempts=2, organization_adapter=adapter)
        resp = make_valid_window_response(bundle)
        result = controller.run(bundle, lambda _idx, _win, _prompt, _att: json.dumps(resp))

        self.assertEqual(result['gate_state'], 'REVIEW')
        self.assertEqual(result['execution_state'], 'completed')
        self.assertEqual(result['attempts_used'], 1)
        blocks = result['analysis']['blocks']
        self.assertEqual(blocks[0]['start'], 0)
        self.assertEqual(blocks[-1]['end'], len(bundle['document_snapshot']['content']))
        for a, b in zip(blocks, blocks[1:]):
            self.assertEqual(a['end'], b['start'])
        ledger = result['analysis']['coverage_ledger']
        self.assertEqual(len(ledger), len(blocks))
        excluded = [row for row in ledger if row['status'] == 'excluded']
        self.assertEqual(len(excluded), 8)  # 7 blank separators + 1 thematic_break
        self.assertTrue(all(bool(row['exclusion_reason']) for row in excluded))

    def test_scenario_2_missing_and_duplicate_block_handling(self):
        bundle = load_sample_bundle()
        # Missing block B009 -> fails gate and exhausts 1 attempt -> STOPPED with last_gate_state == 'FAIL'
        resp_missing = make_valid_window_response(bundle)
        resp_missing['block_coverage'] = [b for b in resp_missing['block_coverage'] if b['block_id'] != 'B009']
        resp_missing['units'] = [u for u in resp_missing['units'] if u['id'] != 'u-code-install']

        adapter = pipeline.OrganizationBoundaryAdapter()
        controller = pipeline.ExecutionController(max_attempts=1, organization_adapter=adapter)
        res_missing = controller.run(bundle, lambda _i, _w, _p, _a: json.dumps(resp_missing))
        self.assertEqual(res_missing['gate_state'], 'STOPPED')
        self.assertEqual(res_missing['last_gate_state'], 'FAIL')
        self.assertEqual(res_missing['return_to_stage'], 'information_extraction_analysis')
        self.assertFalse(res_missing['next_stage_invoked'])
        self.assertEqual(len(adapter.invocations), 0)
        self.assertEqual(len(adapter.blocked_attempts), 1)

        # Duplicate block B003
        resp_dup = make_valid_window_response(bundle)
        resp_dup['block_coverage'].append(
            {'block_id': 'B003', 'status': 'extracted', 'unit_ids': ['u-timeout'], 'unresolved_reason': None}
        )
        controller_dup = pipeline.ExecutionController(max_attempts=1)
        res_dup = controller_dup.run(bundle, lambda _i, _w, _p, _a: json.dumps(resp_dup))
        self.assertEqual(res_dup['gate_state'], 'STOPPED')
        self.assertEqual(res_dup['last_gate_state'], 'FAIL')
        self.assertTrue(any('EXTRACTABLE_BLOCK_DUPLICATED' in r for r in res_dup['failure_reasons']))

    def test_scenario_3_cross_block_claims_and_conditions(self):
        bundle = load_sample_bundle()
        resp = make_valid_window_response(bundle)
        analysis = pipeline.assemble_document_analysis(bundle, [json.dumps(resp)])
        units_by_id = {u['id']: u for u in analysis['units']}

        # B015 condition qualifies B003 claim
        cond_offline = units_by_id['u-cond-offline-cache']
        self.assertEqual(cond_offline['origin_block_ids'], ['B015'])
        self.assertEqual(units_by_id['u-runtime-overview']['origin_block_ids'], ['B003'])
        self.assertTrue(any(
            r['kind'] == 'qualifies' and r['target_unit_id'] == 'u-runtime-overview' and r['cross_block']
            for r in cond_offline['relations']
        ))

        # B015 condition qualifies B007 table entry
        cond_macos = units_by_id['u-cond-macos-manual']
        self.assertEqual(cond_macos['origin_block_ids'], ['B015'])
        self.assertEqual(units_by_id['u-table-macos']['origin_block_ids'], ['B007'])
        self.assertTrue(any(
            r['kind'] == 'qualifies' and r['target_unit_id'] == 'u-table-macos' and r['cross_block']
            for r in cond_macos['relations']
        ))

        # Multi-window split still preserves cross-block relations across windows
        w_blocks = pipeline.parse_markdown_blocks(bundle['document_snapshot'])
        windows = pipeline.plan_extraction_windows(bundle['document_snapshot'], w_blocks, max_window_chars=200)
        self.assertEqual(len(windows), 4)
        full_units_by_block = {}
        for u in resp['units']:
            bid = u['quotes'][0]['block_id']
            full_units_by_block.setdefault(bid, []).append(u)
        cov_by_block = {c['block_id']: c for c in resp['block_coverage']}

        window_payloads = []
        for w in windows:
            w_units = [u for bid in w['target_block_ids'] for u in full_units_by_block.get(bid, [])]
            w_cov = [cov_by_block[bid] for bid in w['target_block_ids']]
            window_payloads.append(json.dumps({
                'input_sha256': resp['input_sha256'],
                'snapshot_id': resp['snapshot_id'],
                'snapshot_sha256': resp['snapshot_sha256'],
                'window_id': w['window_id'],
                'block_coverage': w_cov,
                'units': w_units,
                'alignment': resp['alignment'],
                'unresolved_questions': [],
            }))
        merged = pipeline.assemble_document_analysis(bundle, window_payloads, max_window_chars=200)
        merged_report = pipeline.validate_analysis_gate(bundle, merged)
        self.assertEqual(merged_report['gate_state'], 'REVIEW')
        by_id = {r['check_id']: r['status'] for r in merged_report['check_results']}
        self.assertEqual(by_id['BLOCK_COVERAGE'], 'passed')
        self.assertEqual(by_id['PROTECTED_TRACEABILITY'], 'passed')

    def test_scenario_4_important_info_in_code_block_table_and_list(self):
        bundle = load_sample_bundle()
        resp = make_valid_window_response(bundle)
        analysis = pipeline.assemble_document_analysis(bundle, [json.dumps(resp)])
        units_by_id = {u['id']: u for u in analysis['units']}

        # Table (B007), Code block (B009), List (B015) all have verified spans and elements
        self.assertEqual(units_by_id['u-table-ubuntu']['source_spans'][0]['block_kind'], 'table')
        self.assertEqual(units_by_id['u-code-install']['source_spans'][0]['block_kind'], 'code_block')
        self.assertEqual(units_by_id['u-cond-offline-cache']['source_spans'][0]['block_kind'], 'list')

        bindings = {b['requirement_id']: b for b in analysis['requirement_bindings']}
        self.assertTrue(bindings['req-linux-package']['satisfied'])
        self.assertTrue(bindings['req-install-port']['satisfied'])
        self.assertTrue(bindings['req-offline-cache-condition']['satisfied'])
        self.assertTrue(bindings['req-macos-manual-update']['satisfied'])

    def test_scenario_5_invalid_source_reference_and_missing_protected_info(self):
        bundle = load_sample_bundle()
        # Invalid quote in B009
        bad_quote_resp = make_valid_window_response(bundle)
        for u in bad_quote_resp['units']:
            if u['id'] == 'u-code-install':
                u['quotes'][0]['quote'] = './install.sh --port 9999'

        controller = pipeline.ExecutionController(max_attempts=1)
        res_bad_quote = controller.run(bundle, lambda _i, _w, _p, _a: json.dumps(bad_quote_resp))
        self.assertEqual(res_bad_quote['gate_state'], 'STOPPED')
        self.assertEqual(res_bad_quote['last_gate_state'], 'FAIL')
        self.assertEqual(res_bad_quote['return_to_stage'], 'information_extraction_analysis')
        self.assertFalse(res_bad_quote['next_stage_invoked'])
        self.assertTrue(any('QUOTE_NOT_FOUND_IN_BLOCK' in r for r in res_bad_quote['failure_reasons']))

        # Protected unit marked as omit_candidate
        omit_resp = make_valid_window_response(bundle)
        for u in omit_resp['units']:
            if u['id'] == 'u-timeout':
                u['assessment']['preservation'] = 'omit_candidate'
        controller_omit = pipeline.ExecutionController(max_attempts=1)
        res_omit = controller_omit.run(bundle, lambda _i, _w, _p, _a: json.dumps(omit_resp))
        self.assertEqual(res_omit['gate_state'], 'STOPPED')
        self.assertEqual(res_omit['last_gate_state'], 'FAIL')
        self.assertTrue(any('PROTECTED_TRACEABILITY_VIOLATION' in r for r in res_omit['failure_reasons']))

    def test_scenario_6_missing_required_check_results(self):
        bundle = load_sample_bundle()
        resp = make_valid_window_response(bundle)
        analysis = pipeline.assemble_document_analysis(bundle, [json.dumps(resp)])
        full_report = pipeline.validate_analysis_gate(bundle, analysis)

        # Strip PROTECTED_TRACEABILITY and SEMANTIC_FIDELITY from check_results
        incomplete_report = copy.deepcopy(full_report)
        incomplete_report['check_results'] = [
            r for r in incomplete_report['check_results']
            if r['check_id'] not in {'PROTECTED_TRACEABILITY', 'SEMANTIC_FIDELITY'}
        ]
        # Even if caller spoofs gate_state='PASS' and delivery_approved=True on the incomplete report:
        incomplete_report['gate_state'] = 'PASS'
        incomplete_report['delivery_approved'] = True

        adapter = pipeline.OrganizationBoundaryAdapter()
        controller = pipeline.ExecutionController(organization_adapter=adapter)
        reuse_res = controller.attempt_reuse_validation_report(bundle, analysis, incomplete_report)
        self.assertEqual(reuse_res['gate_state'], 'STOPPED')
        self.assertFalse(reuse_res['next_stage_allowed'])
        self.assertFalse(reuse_res['next_stage_invoked'])
        self.assertEqual(len(adapter.invocations), 0)
        self.assertEqual(len(adapter.blocked_attempts), 1)

    def test_scenario_7_stale_validation_report_reuse_after_input_or_contract_change(self):
        bundle = load_sample_bundle()
        resp = make_valid_window_response(bundle)
        adapter = pipeline.OrganizationBoundaryAdapter()
        controller = pipeline.ExecutionController(max_attempts=1, organization_adapter=adapter)
        first_run = controller.run(bundle, lambda _i, _w, _p, _a: json.dumps(resp))
        prior_analysis = first_run['analysis']
        prior_report = first_run['validation_report']

        # Case A: DocumentSnapshot content changes
        modified_doc_bundle = copy.deepcopy(bundle)
        modified_doc_bundle['document_snapshot']['version'] = '2'
        modified_doc_bundle['document_snapshot']['content'] = (
            modified_doc_bundle['document_snapshot']['content'].replace('30초', '60초')
        )
        modified_doc_bundle['document_snapshot']['sha256'] = pipeline.digest_text(
            modified_doc_bundle['document_snapshot']['content']
        )
        reuse_doc = controller.attempt_reuse_validation_report(
            modified_doc_bundle, prior_analysis, prior_report
        )
        self.assertEqual(reuse_doc['gate_state'], 'FAIL')
        self.assertTrue(reuse_doc['invalidated'])
        self.assertFalse(reuse_doc['next_stage_allowed'])
        self.assertFalse(reuse_doc['next_stage_invoked'])
        self.assertEqual(reuse_doc['return_to_stage'], 'information_extraction_analysis')
        self.assertIn('document_snapshot', reuse_doc['invalidation']['changed_components'])
        self.assertGreaterEqual(len(controller.invalidation_log), 1)

        # Case B: WritingContract changes
        modified_contract_bundle = copy.deepcopy(bundle)
        modified_contract_bundle['writing_contract']['version'] = '2'
        modified_contract_bundle['writing_contract']['purpose'] = '내부 아키텍처 의사결정 이력을 보존한다.'
        reuse_contract = controller.attempt_reuse_validation_report(
            modified_contract_bundle, prior_analysis, prior_report
        )
        self.assertEqual(reuse_contract['gate_state'], 'FAIL')
        self.assertTrue(reuse_contract['invalidated'])
        self.assertFalse(reuse_contract['next_stage_invoked'])
        self.assertEqual(reuse_contract['return_to_stage'], 'contract_resolution')
        self.assertIn('writing_contract', reuse_contract['invalidation']['changed_components'])

    def test_scenario_8_failed_or_unverified_analysis_blocked_from_next_stage(self):
        bundle = load_sample_bundle()
        resp = make_valid_window_response(bundle)
        analysis = pipeline.assemble_document_analysis(bundle, [json.dumps(resp)])
        review_report = pipeline.validate_analysis_gate(bundle, analysis)

        adapter = pipeline.OrganizationBoundaryAdapter()
        # 1. Direct call to OrganizationBoundaryAdapter with REVIEW report is blocked
        with self.assertRaises(pipeline.StageTransitionBlockedError):
            adapter.enter_organization_stage(bundle, analysis, review_report)
        self.assertEqual(len(adapter.invocations), 0)
        self.assertEqual(len(adapter.blocked_attempts), 1)
        self.assertEqual(adapter.blocked_attempts[0]['gate_state'], 'REVIEW')

        # 2. Retry loop: attempt 1 fails (missing block), attempt 2 fixes block -> reaches REVIEW (still blocked from Organization),
        #    and verifies finite retry budget when all attempts fail.
        bad_resp = make_valid_window_response(bundle)
        bad_resp['block_coverage'] = [b for b in bad_resp['block_coverage'] if b['block_id'] != 'B001']
        bad_resp['units'] = [u for u in bad_resp['units'] if u['id'] != 'u-heading-main']

        controller_recover = pipeline.ExecutionController(max_attempts=2, organization_adapter=adapter)
        res_recover = controller_recover.run(
            bundle,
            lambda _i, _w, _p, attempt: json.dumps(bad_resp if attempt == 1 else resp),
        )
        self.assertEqual(res_recover['attempts_used'], 2)
        self.assertEqual(res_recover['gate_state'], 'REVIEW')
        self.assertEqual(res_recover['attempt_history'][0]['gate_state'], 'FAIL')
        self.assertEqual(res_recover['attempt_history'][1]['gate_state'], 'REVIEW')
        self.assertEqual(len(res_recover['invalidation_log']), 1)
        self.assertFalse(res_recover['next_stage_invoked'])
        self.assertEqual(len(adapter.invocations), 0)

        # 3. Exhausting max_attempts=2 when both attempts fail -> STOPPED with last_gate_state='FAIL'
        controller_exhaust = pipeline.ExecutionController(max_attempts=2)
        res_exhaust = controller_exhaust.run(bundle, lambda _i, _w, _p, _a: json.dumps(bad_resp))
        self.assertEqual(res_exhaust['attempts_used'], 2)
        self.assertEqual(res_exhaust['gate_state'], 'STOPPED')
        self.assertEqual(res_exhaust['execution_state'], 'stopped')
        self.assertEqual(res_exhaust['last_gate_state'], 'FAIL')
        self.assertIn('MAX_ATTEMPTS_EXCEEDED', res_exhaust['stop_reason'])
        self.assertFalse(res_exhaust['next_stage_invoked'])

    def test_scenario_9_structural_pass_never_mistaken_for_semantic_pass(self):
        bundle = load_sample_bundle()
        resp = make_valid_window_response(bundle)
        analysis = pipeline.assemble_document_analysis(bundle, [json.dumps(resp)])
        report = pipeline.validate_analysis_gate(bundle, analysis)

        # All 4 structural checks pass, but SEMANTIC_FIDELITY is not_run -> gate_state is REVIEW, never PASS
        deterministic = [r for r in report['check_results'] if r['kind'] == 'deterministic']
        self.assertEqual(len(deterministic), 4)
        self.assertTrue(all(r['status'] == 'passed' for r in deterministic))
        sem = [r for r in report['check_results'] if r['check_id'] == 'SEMANTIC_FIDELITY'][0]
        self.assertEqual(sem['status'], 'not_run')
        self.assertEqual(report['gate_state'], 'REVIEW')
        self.assertFalse(report['delivery_approved'])
        self.assertFalse(report['next_stage_allowed'])

        # Even if someone mutates report['gate_state'] = 'PASS' without SEMANTIC_FIDELITY actually passing,
        # can_advance_to_organization re-reconciles check_results and blocks transition!
        forged_report = copy.deepcopy(report)
        forged_report['gate_state'] = 'PASS'
        forged_report['delivery_approved'] = True
        forged_report['next_stage_allowed'] = True
        decision = pipeline.can_advance_to_organization(bundle, analysis, forged_report)
        self.assertFalse(decision['allowed'])
        self.assertEqual(decision['gate_state'], 'REVIEW')

    def test_cli_prompt_and_run_modes(self):
        import subprocess
        import sys
        import tempfile

        bundle = load_sample_bundle()
        resp = make_valid_window_response(bundle)
        with tempfile.TemporaryDirectory() as tmp:
            resp_path = Path(tmp) / 'response.json'
            resp_path.write_text(json.dumps(resp))

            prompt_proc = subprocess.run(
                [sys.executable, str(HERE / 'pipeline.py'), 'prompt', str(SAMPLE_INPUT_PATH)],
                capture_output=True, text=True, check=True,
            )
            self.assertIn('WINDOW_INPUT_JSON:', prompt_proc.stdout)

            run_proc = subprocess.run(
                [sys.executable, str(HERE / 'pipeline.py'), 'run',
                 '--input', str(SAMPLE_INPUT_PATH), '--response', str(resp_path)],
                capture_output=True, text=True, check=True,
            )
            run_json = json.loads(run_proc.stdout)
            self.assertEqual(run_json['gate_state'], 'REVIEW')
            self.assertFalse(run_json['next_stage_invoked'])

            md_proc = subprocess.run(
                [sys.executable, str(HERE / 'pipeline.py'), 'run',
                 '--input', str(SAMPLE_INPUT_PATH), '--response', str(resp_path), '--markdown'],
                capture_output=True, text=True, check=True,
            )
            self.assertIn('# 전체 문서 정보 추출·검증·실행 제어 결과', md_proc.stdout)


if __name__ == '__main__':
    unittest.main()



