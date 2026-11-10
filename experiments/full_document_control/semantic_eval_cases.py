#!/usr/bin/env python3
"""Fixed evaluation benchmark and regression suite for the LogicWrite Semantic Fidelity Validator.

Includes:
- FD-001 (`full-doc-install-guide-001`) and RW-001 (`RW-001` PKG vs DMG decision note) full-document bundles
  (constructed in memory without modifying any raw fixture or gold files).
- 14 fixed evaluation cases covering:
  1. Faithful semantic preservation (FD-001 and RW-001)
  2. Claim overstatement (RW-001 A1/A2 regression: installation requirement -> factual package behavior)
  3. Polarity reversal (affirmative <-> negative / supported <-> unsupported)
  4. Condition loss (dropping release-scope / conditional qualifiers)
  5. Quantity and unit distortion (30초 -> 30분)
  6. Unsupported addition (fabricating unstated encryption/GPU performance facts)
  7. Critical omission (backward check Source -> Analysis catching omitted B015 caveat clause)
  8. Relation distortion (RW-001 E-REL-A1 / E-REL-A2 inverted `supports` direction)
  9. Assessment-only rationale/exposure distortion (RW-001 E-REQ-B2 regression where `statement` is accurate
     but `assessment.exposure` and `assessment.reason` overstate requirements as runtime facts)
  10. Ambiguous source evidence hold (`unresolved` -> `REVIEW`)
  11. Boundary & disagreement cases for False Negative (미탐), False Positive (오탐), and inter-evaluator conflict analysis.
"""

import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
SAMPLE_INPUT_PATH = HERE / 'sample_input.json'
RW001_INPUT_PATH = REPO_ROOT / 'docs' / 'reviews' / 'diagnostic-gold-draft' / 'RW-001.input.json'

_SPEC = importlib.util.spec_from_file_location('full_document_control_pipeline', HERE / 'pipeline.py')
pipeline = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pipeline)


def load_fd001_bundle():
    """Load FD-001 full-document bundle without mutating disk files."""
    return pipeline.load_json_bytes(SAMPLE_INPUT_PATH.read_bytes())


def build_rw001_full_doc_bundle():
    """Construct a full-document bundle from RW-001.input.json's target passage without mutating the gold file."""
    raw_rw001 = pipeline.load_json_bytes(RW001_INPUT_PATH.read_bytes())
    target_passage = next(p for p in raw_rw001['passages'] if p['id'] == 'target')
    content = target_passage['text']
    return {
        'case_id': 'RW-001-full-doc-pkg-vs-dmg',
        'writing_contract': {
            'contract_id': 'contract-rw-001-packaging-decision',
            'version': '1',
            'document_type': 'decision_note',
            'audience': raw_rw001['writing_contract']['audience'],
            'purpose': raw_rw001['writing_contract']['purpose'],
            'language': 'en',
            'register': 'neutral_technical',
            'output_scopes': [
                {
                    'scope_id': 'macos-packaging-decision-note',
                    'document_id': 'doc-rw-001-packaging',
                }
            ],
            'required_information': [
                {
                    'id': 'req-applications-helper',
                    'scope_id': 'macos-packaging-decision-note',
                    'description': 'Node/cloudflared helpers requirement must be traced.',
                    'expected_literal': 'Node/cloudflared',
                    'kind': 'identifier',
                    'requires_condition_link': False,
                },
                {
                    'id': 'req-pkg-better-fit',
                    'scope_id': 'macos-packaging-decision-note',
                    'description': 'Decision that PKG is the better fit must be traced.',
                    'expected_literal': 'PKG is the better fit',
                    'kind': 'claim',
                    'requires_condition_link': False,
                },
                {
                    'id': 'req-dmg-later-condition',
                    'scope_id': 'macos-packaging-decision-note',
                    'description': 'Future DMG option qualifying the current-release PKG decision must be linked.',
                    'expected_literal': 'can still be added later',
                    'kind': 'condition',
                    'requires_condition_link': True,
                },
            ],
            'constraints': raw_rw001['writing_contract']['constraints'],
        },
        'document_snapshot': {
            'document_id': 'doc-rw-001-packaging',
            'snapshot_id': 'snap-rw-001-v1',
            'version': '1',
            'coverage': 'complete',
            'media_type': 'text/markdown',
            'content': content,
            'sha256': pipeline.digest_text(content),
            'source_record': {
                'type': 'diagnostic_gold_passage_fixture',
                'path': 'docs/reviews/diagnostic-gold-draft/RW-001.input.json#target',
                'offset_convention': 'zero_based_unicode_codepoint_half_open_no_normalization',
            },
        },
    }


def make_fd001_faithful_window_response(bundle=None, *, window_id='W001'):
    """Build a semantically faithful extraction window response for FD-001."""
    if bundle is None:
        bundle = load_fd001_bundle()
    input_sha256 = pipeline.canonical_json_digest(bundle)
    snap = bundle['document_snapshot']
    scope_id = bundle['writing_contract']['output_scopes'][0]['scope_id']

    def assessment(importance='required', preservation='retain_current',
                   exposure='주장 및 설치 지시와 함께 현재 문서에 직접 노출',
                   reason='설치 수행과 운영 제약 확인에 직접 필요한 정보다.'):
        return {
            'scope_id': scope_id,
            'relevance': 'relevant',
            'importance': importance,
            'preservation': preservation,
            'exposure': exposure,
            'reason': reason,
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
                'statement': '로컬 에이전트 런타임 v0.4.0은 외부 클라우드 업로드 없이 작업 폴더 안에서 파일 검색과 테스트 실행을 수행한다.',
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
                        'reason': '런타임 기본 동작의 30초 시간 제한 사양을 보충한다.',
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
                'statement': 'tar -xzf runtime-linux-x64.tar.gz 명령으로 압축을 해제한 뒤 ./install.sh --port 8765 명령으로 설치한다.',
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
                        'reason': 'Ubuntu 표에 정의된 runtime-linux-x64.tar.gz 패키지 아카이브를 설치 입력으로 사용한다.',
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
                        'reason': 'B003의 외부 업로드 없는 로컬 런타임 실행 주장에 대해 오프라인 모델 캐시(~/.cache/local-runtime) 존재 조건을 한정한다.',
                    }
                ],
                'assessment': assessment(
                    exposure='오프라인 모드 제약 조건을 로컬 실행 안내와 함께 직접 노출',
                    reason='오프라인 환경에서 모델 캐시가 존재할 때만 동작한다는 필수 운영 조건이다.',
                ),
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
                        'reason': 'B007 표의 macOS 패키지(runtime-macos-14.pkg) 항목에 대해 초기 실험 빌드의 자동 업데이트 미지원 및 수동 재설치 제약을 한정한다.',
                    }
                ],
                'assessment': assessment(
                    exposure='macOS 초기 실험 빌드의 자동 업데이트 미지원 및 수동 재설치 제약을 직접 노출',
                    reason='macOS 패키지는 초기 실험 빌드이므로 자동 업데이트를 지원하지 않아 수동으로 재설치해야 한다는 필수 제약이다.',
                ),
            },
        ],
        'alignment': {
            'status': 'aligned',
            'reason': '설치 안내와 운영 제약을 모두 다루며 계약 목적과 일치한다.',
        },
        'unresolved_questions': [],
    }


def make_rw001_faithful_window_response(bundle=None, *, window_id='W001'):
    """Build a semantically faithful extraction window response for RW-001 (preserving requirement modality & conditions)."""
    if bundle is None:
        bundle = build_rw001_full_doc_bundle()
    input_sha256 = pipeline.canonical_json_digest(bundle)
    snap = bundle['document_snapshot']
    scope_id = bundle['writing_contract']['output_scopes'][0]['scope_id']

    return {
        'input_sha256': input_sha256,
        'snapshot_id': snap['snapshot_id'],
        'snapshot_sha256': snap['sha256'],
        'window_id': window_id,
        'block_coverage': [
            {'block_id': 'B001', 'status': 'extracted', 'unit_ids': ['u-rw-heading'], 'unresolved_reason': None},
            {
                'block_id': 'B003',
                'status': 'extracted',
                'unit_ids': ['u-pkg-fit-release', 'u-install-reqs', 'u-beginner-open-path', 'u-dmg-later-option'],
                'unresolved_reason': None,
            },
        ],
        'units': [
            {
                'id': 'u-rw-heading',
                'statement': 'The section heading asks why PKG is chosen instead of DMG.',
                'quotes': [{'block_id': 'B001', 'quote': '### Why PKG Instead Of DMG?', 'occurrence': 0}],
                'elements': [
                    {
                        'id': 'el-rw-title',
                        'kind': 'claim',
                        'value': 'Why PKG Instead Of DMG?',
                        'quotes': [{'block_id': 'B001', 'quote': '### Why PKG Instead Of DMG?', 'occurrence': 0}],
                    }
                ],
                'relations': [],
                'assessment': {
                    'scope_id': scope_id,
                    'relevance': 'relevant',
                    'importance': 'useful',
                    'preservation': 'retain_current',
                    'exposure': 'Expose as the section heading framing the PKG vs DMG packaging decision.',
                    'reason': 'Identifies the packaging comparison question addressed by the decision note.',
                    'uncertainty': 'Grounded directly in the heading.',
                },
            },
            {
                'id': 'u-pkg-fit-release',
                'statement': 'For this release, PKG is the better fit compared to DMG.',
                'quotes': [
                    {
                        'block_id': 'B003',
                        'quote': 'For this release, **PKG is the better fit**.',
                        'occurrence': 0,
                    }
                ],
                'elements': [
                    {
                        'id': 'el-for-this-release',
                        'kind': 'condition',
                        'value': 'For this release',
                        'quotes': [
                            {
                                'block_id': 'B003',
                                'quote': 'For this release, **PKG is the better fit**.',
                                'occurrence': 0,
                            }
                        ],
                    },
                    {
                        'id': 'el-pkg-better-fit',
                        'kind': 'claim',
                        'value': 'PKG is the better fit',
                        'quotes': [
                            {
                                'block_id': 'B003',
                                'quote': 'For this release, **PKG is the better fit**.',
                                'occurrence': 0,
                            }
                        ],
                    },
                ],
                'relations': [],
                'assessment': {
                    'scope_id': scope_id,
                    'relevance': 'relevant',
                    'importance': 'required',
                    'preservation': 'retain_current',
                    'exposure': 'Present PKG as the better fit specifically scoped to this release.',
                    'reason': 'Captures the primary packaging decision while preserving the current-release scope condition.',
                    'uncertainty': 'Applies to this release only.',
                },
            },
            {
                'id': 'u-install-reqs',
                'statement': (
                    'A DMG is nicer for drag-and-drop apps, but this app needs to install a menu bar runtime under '
                    'Applications, bundle Node/cloudflared helpers, and run a non-blocking post-install Doctor.'
                ),
                'quotes': [
                    {
                        'block_id': 'B003',
                        'quote': (
                            'A DMG is nicer for drag-and-drop\napps, but this app needs to install a menu bar runtime '
                            'under Applications,\nbundle Node/cloudflared helpers, and run a non-blocking post-install Doctor.'
                        ),
                        'occurrence': 0,
                    }
                ],
                'elements': [
                    {
                        'id': 'el-dmg-drag-drop',
                        'kind': 'condition',
                        'value': 'A DMG is nicer for drag-and-drop',
                        'quotes': [
                            {
                                'block_id': 'B003',
                                'quote': 'A DMG is nicer for drag-and-drop\napps',
                                'occurrence': 0,
                            }
                        ],
                    },
                    {
                        'id': 'el-helpers-id',
                        'kind': 'identifier',
                        'value': 'Node/cloudflared',
                        'quotes': [
                            {
                                'block_id': 'B003',
                                'quote': 'bundle Node/cloudflared helpers, and run a non-blocking post-install Doctor.',
                                'occurrence': 0,
                            }
                        ],
                    },
                ],
                'relations': [
                    {
                        'kind': 'supports',
                        'target_unit_id': 'u-pkg-fit-release',
                        'reason': (
                            'The requirement that this app needs to install a menu bar runtime under Applications, '
                            'bundle Node/cloudflared helpers, and run a non-blocking post-install Doctor supports why '
                            'PKG is the better fit for this release.'
                        ),
                    }
                ],
                'assessment': {
                    'scope_id': scope_id,
                    'relevance': 'relevant',
                    'importance': 'required',
                    'preservation': 'retain_current',
                    'exposure': (
                        'State as installation requirements ("needs to install a menu bar runtime under Applications, '
                        'bundle Node/cloudflared helpers, and run a non-blocking post-install Doctor") rather than '
                        'verified runtime behaviors.'
                    ),
                    'reason': (
                        'Explains the installation requirements that make PKG a better fit than a drag-and-drop DMG '
                        'for this release while preserving requirement modality.'
                    ),
                    'uncertainty': 'Source states what the app needs to install/bundle/run, not verified package execution results.',
                },
            },
            {
                'id': 'u-beginner-open-path',
                'statement': 'PKG gives beginners a clearer "install and open" path.',
                'quotes': [
                    {
                        'block_id': 'B003',
                        'quote': 'PKG gives beginners a clearer "install and open" path.',
                        'occurrence': 0,
                    }
                ],
                'elements': [
                    {
                        'id': 'el-install-open-path',
                        'kind': 'claim',
                        'value': 'clearer "install and open" path',
                        'quotes': [
                            {
                                'block_id': 'B003',
                                'quote': 'PKG gives beginners a clearer "install and open" path.',
                                'occurrence': 0,
                            }
                        ],
                    }
                ],
                'relations': [
                    {
                        'kind': 'supports',
                        'target_unit_id': 'u-pkg-fit-release',
                        'reason': 'Giving beginners a clearer install and open path supports choosing PKG as the better fit for this release.',
                    }
                ],
                'assessment': {
                    'scope_id': scope_id,
                    'relevance': 'relevant',
                    'importance': 'useful',
                    'preservation': 'retain_current',
                    'exposure': 'Mention the clearer install-and-open path for beginners as supporting UX rationale for PKG.',
                    'reason': 'Provides the user-experience rationale supporting PKG for this release.',
                    'uncertainty': 'Grounded in source comparison statement.',
                },
            },
            {
                'id': 'u-dmg-later-option',
                'statement': 'A signed/notarized DMG can still be added later for a more consumer-style download.',
                'quotes': [
                    {
                        'block_id': 'B003',
                        'quote': 'A signed/notarized DMG\ncan still be added later for a more consumer-style download.',
                        'occurrence': 0,
                    }
                ],
                'elements': [
                    {
                        'id': 'el-dmg-later-cond',
                        'kind': 'condition',
                        'value': 'can still be added later',
                        'quotes': [
                            {
                                'block_id': 'B003',
                                'quote': 'A signed/notarized DMG\ncan still be added later for a more consumer-style download.',
                                'occurrence': 0,
                            }
                        ],
                    }
                ],
                'relations': [
                    {
                        'kind': 'qualifies',
                        'target_unit_id': 'u-pkg-fit-release',
                        'reason': (
                            'Qualifies the decision that PKG is the better fit for this release by noting that a '
                            'signed/notarized DMG can still be added later for a consumer-style download.'
                        ),
                    }
                ],
                'assessment': {
                    'scope_id': scope_id,
                    'relevance': 'relevant',
                    'importance': 'required',
                    'preservation': 'retain_current',
                    'exposure': 'Keep the qualification that a signed/notarized DMG can still be added later.',
                    'reason': 'Prevents overstating the current release PKG choice as a permanent exclusion of DMG.',
                    'uncertainty': 'Future DMG addition remains optional ("can still be added later").',
                },
            },
        ],
        'alignment': {
            'status': 'aligned',
            'reason': 'Preserves requirement modality, release scope condition, and future DMG option.',
        },
        'unresolved_questions': [],
    }


def build_semantic_evaluation_cases():
    """Return the 14 fixed semantic evaluation cases with manual ground-truth labels and analysis artifacts."""
    cases = []

    # 1. EVAL-01-FD001-FAITHFUL
    b1 = load_fd001_bundle()
    r1 = make_fd001_faithful_window_response(b1)
    a1 = pipeline.assemble_document_analysis(b1, [json.dumps(r1)])
    cases.append({
        'eval_case_id': 'EVAL-01-FD001-FAITHFUL',
        'source_case_id': 'FD-001',
        'category_focus': 'FAITHFUL_PRESERVATION',
        'description': 'FD-001 전체 문서(제목·문단·표·코드 블록·목록)의 의미를 왜곡·누락 없이 보존한 정상 사례',
        'input_bundle': b1,
        'analysis_result': a1,
        'manual_expected_judgment': 'supported',
        'manual_expected_error_categories': [],
        'manual_expected_field_paths': [],
        'manual_expected_gate_state': 'REVIEW',  # Auto-PASS disabled in first implementation
        'is_boundary_disagreement_case': False,
    })

    # 2. EVAL-02-RW001-FAITHFUL
    b2 = build_rw001_full_doc_bundle()
    r2 = make_rw001_faithful_window_response(b2)
    a2 = pipeline.assemble_document_analysis(b2, [json.dumps(r2)])
    cases.append({
        'eval_case_id': 'EVAL-02-RW001-FAITHFUL',
        'source_case_id': 'RW-001',
        'category_focus': 'FAITHFUL_PRESERVATION',
        'description': 'RW-001 원문의 설치 요구사항 양태(needs to)와 이번 릴리스 한정 조건(For this release, can still be added later)을 정확히 보존한 정상 사례',
        'input_bundle': b2,
        'analysis_result': a2,
        'manual_expected_judgment': 'supported',
        'manual_expected_error_categories': [],
        'manual_expected_field_paths': [],
        'manual_expected_gate_state': 'REVIEW',
        'is_boundary_disagreement_case': False,
    })

    # 3. EVAL-03-RW001-OVERSTATEMENT-A1-A2 (Core RW-001 regression: E-REQ-A1 / E-REQ-A2)
    b3 = build_rw001_full_doc_bundle()
    r3 = make_rw001_faithful_window_response(b3)
    for u in r3['units']:
        if u['id'] == 'u-install-reqs':
            # Reproduce exact A1/A2 distortion from extraction_ab/comparison.json:
            u['statement'] = (
                'The macOS package installs a menu bar runtime under Applications, '
                'bundles Node/cloudflared helpers, and runs a non-blocking post-install Doctor.'
            )
    a3 = pipeline.assemble_document_analysis(b3, [json.dumps(r3)])
    cases.append({
        'eval_case_id': 'EVAL-03-RW001-OVERSTATEMENT-A1-A2',
        'source_case_id': 'RW-001',
        'category_focus': 'CLAIM_OVERSTATEMENT',
        'description': 'RW-001 A/B 실험 회귀(E-REQ-A1/A2): 설치 요구사항("this app needs to install a menu bar runtime under Applications...")을 실제 검증된 패키지 동작("The macOS package installs a menu bar runtime under Applications...")으로 단정하는 주장 확대 오류',
        'input_bundle': b3,
        'analysis_result': a3,
        'manual_expected_judgment': 'overstated',
        'manual_expected_error_categories': ['CLAIM_OVERSTATEMENT'],
        'manual_expected_field_paths': ['/units/2/statement'],
        'manual_expected_gate_state': 'FAIL',
        'is_boundary_disagreement_case': False,
    })

    # 4. EVAL-04-POLARITY-REVERSAL
    b4 = load_fd001_bundle()
    r4 = make_fd001_faithful_window_response(b4)
    for u in r4['units']:
        if u['id'] == 'u-cond-macos-manual':
            u['statement'] = 'macOS 패키지는 초기 실험 빌드이지만 자동 업데이트를 지원하며 수동 재설치 없이 갱신된다.'
    a4 = pipeline.assemble_document_analysis(b4, [json.dumps(r4)])
    cases.append({
        'eval_case_id': 'EVAL-04-POLARITY-REVERSAL',
        'source_case_id': 'FD-001',
        'category_focus': 'POLARITY_REVERSAL',
        'description': 'FD-001 B015의 "자동 업데이트를 지원하지 않으며 수동으로 재설치해야 한다"를 "자동 업데이트를 지원하며"로 반전시킨 의미 반전 오류',
        'input_bundle': b4,
        'analysis_result': a4,
        'manual_expected_judgment': 'contradicted',
        'manual_expected_error_categories': ['POLARITY_REVERSAL'],
        'manual_expected_field_paths': ['/units/9/statement'],
        'manual_expected_gate_state': 'FAIL',
        'is_boundary_disagreement_case': False,
    })

    # 5. EVAL-05-CONDITION-LOSS
    b5 = build_rw001_full_doc_bundle()
    r5 = make_rw001_faithful_window_response(b5)
    for u in r5['units']:
        if u['id'] == 'u-pkg-fit-release':
            u['statement'] = 'In all releases, PKG is permanently superior and always the only installer over DMG.'
    a5 = pipeline.assemble_document_analysis(b5, [json.dumps(r5)])
    cases.append({
        'eval_case_id': 'EVAL-05-CONDITION-LOSS',
        'source_case_id': 'RW-001',
        'category_focus': 'CONDITION_LOSS',
        'description': 'RW-001의 "For this release" 범위 한정 조건을 제거하고 모든 릴리스의 영구적 결정("In all releases, PKG is permanently superior")으로 일반화한 조건 손실 오류',
        'input_bundle': b5,
        'analysis_result': a5,
        'manual_expected_judgment': 'overstated',
        'manual_expected_error_categories': ['CONDITION_LOSS'],
        'manual_expected_field_paths': ['/units/1/statement'],
        'manual_expected_gate_state': 'FAIL',
        'is_boundary_disagreement_case': False,
    })

    # 6. EVAL-06-QUANTITY-AND-UNIT-DISTORTION
    b6 = load_fd001_bundle()
    r6 = make_fd001_faithful_window_response(b6)
    for u in r6['units']:
        if u['id'] == 'u-timeout':
            u['statement'] = '기본 요청 제한 시간은 30분이다.'
    a6 = pipeline.assemble_document_analysis(b6, [json.dumps(r6)])
    cases.append({
        'eval_case_id': 'EVAL-06-QUANTITY-AND-UNIT-DISTORTION',
        'source_case_id': 'FD-001',
        'category_focus': 'QUANTITY_OR_SCOPE_DISTORTION',
        'description': 'FD-001 B003의 제한 시간 단위를 "30초"에서 "30분"으로 왜곡한 수치·단위 변경 오류',
        'input_bundle': b6,
        'analysis_result': a6,
        'manual_expected_judgment': 'contradicted',
        'manual_expected_error_categories': ['QUANTITY_OR_SCOPE_DISTORTION'],
        'manual_expected_field_paths': ['/units/2/statement'],
        'manual_expected_gate_state': 'FAIL',
        'is_boundary_disagreement_case': False,
    })

    # 7. EVAL-07-UNSUPPORTED-ADDITION
    b7 = load_fd001_bundle()
    r7 = make_fd001_faithful_window_response(b7)
    for u in r7['units']:
        if u['id'] == 'u-runtime-overview':
            u['statement'] = (
                '로컬 에이전트 런타임 v0.4.0은 외부 클라우드 업로드 없이 작업 폴더 안에서 파일 검색과 테스트 실행을 수행하며, '
                'AES-256 암호화와 systemd 자동 복구 데몬을 통해 지연 시간을 50% 감소시킨다.'
            )
    a7 = pipeline.assemble_document_analysis(b7, [json.dumps(r7)])
    cases.append({
        'eval_case_id': 'EVAL-07-UNSUPPORTED-ADDITION',
        'source_case_id': 'FD-001',
        'category_focus': 'UNSUPPORTED_ADDITION',
        'description': '원문에 전혀 없는 "AES-256 암호화", "systemd 자동 복구 데몬", "지연 시간 50% 감소" 성과를 만들어낸 근거 없는 추가 오류',
        'input_bundle': b7,
        'analysis_result': a7,
        'manual_expected_judgment': 'contradicted',
        'manual_expected_error_categories': ['UNSUPPORTED_ADDITION'],
        'manual_expected_field_paths': ['/units/1/statement'],
        'manual_expected_gate_state': 'FAIL',
        'is_boundary_disagreement_case': False,
    })

    # 8. EVAL-08-CRITICAL-OMISSION (Backward check Source -> Analysis catches omitted B015 caveat clause)
    b8 = load_fd001_bundle()
    # Remove req-macos-manual-update from required_information so deterministic PROTECTED_TRACEABILITY passes,
    # isolating the backward Source -> Analysis semantic omission detector on B015.
    b8['writing_contract']['required_information'] = [
        req for req in b8['writing_contract']['required_information']
        if req['id'] != 'req-macos-manual-update'
    ]
    r8 = make_fd001_faithful_window_response(b8)
    r8['units'] = [u for u in r8['units'] if u['id'] != 'u-cond-macos-manual']
    for cov in r8['block_coverage']:
        if cov['block_id'] == 'B015':
            cov['unit_ids'] = ['u-cond-offline-cache']
    a8 = pipeline.assemble_document_analysis(b8, [json.dumps(r8)])
    cases.append({
        'eval_case_id': 'EVAL-08-CRITICAL-OMISSION',
        'source_case_id': 'FD-001',
        'category_focus': 'CRITICAL_OMISSION',
        'description': 'B015 목록 블록의 첫 항목(오프라인 캐시 조건)만 추출하고 두 번째 필수 한계 항목(macOS 자동 업데이트 미지원 및 수동 재설치 제약)을 통째로 빠뜨린 중요 정보 누락 오류 (원문->분석 역방향 검사)',
        'input_bundle': b8,
        'analysis_result': a8,
        'manual_expected_judgment': 'contradicted',
        'manual_expected_error_categories': ['CRITICAL_OMISSION'],
        'manual_expected_field_paths': ['/blocks/6'],
        'manual_expected_gate_state': 'FAIL',
        'is_boundary_disagreement_case': False,
    })

    # 9. EVAL-09-RW001-RELATION-DISTORTION-A1-A2 (Core RW-001 regression: E-REL-A1 / E-REL-A2)
    b9 = build_rw001_full_doc_bundle()
    r9 = make_rw001_faithful_window_response(b9)
    for u in r9['units']:
        if u['id'] == 'u-install-reqs':
            u['relations'] = []
        if u['id'] == 'u-pkg-fit-release':
            u['relations'].append({
                'kind': 'supports',
                'target_unit_id': 'u-install-reqs',
                'reason': (
                    'The choice of PKG as the better fit for this release is justified by the technical installation '
                    'requirements described in u2 (needs to install a menu bar runtime under Applications, bundle '
                    'Node/cloudflared helpers, and run a non-blocking post-install Doctor).'
                ),
            })
    a9 = pipeline.assemble_document_analysis(b9, [json.dumps(r9)])
    cases.append({
        'eval_case_id': 'EVAL-09-RW001-RELATION-DISTORTION-A1-A2',
        'source_case_id': 'RW-001',
        'category_focus': 'RELATION_DISTORTION',
        'description': 'RW-001 A/B 실험 회귀(E-REL-A1/A2): 결론 단위(u-pkg-fit-release)에서 전제 단위(u-install-reqs)로 supports 방향을 뒤집어 연결한 관계 왜곡 오류',
        'input_bundle': b9,
        'analysis_result': a9,
        'manual_expected_judgment': 'contradicted',
        'manual_expected_error_categories': ['RELATION_DISTORTION'],
        'manual_expected_field_paths': ['/units/1/relations/0/reason'],
        'manual_expected_gate_state': 'FAIL',
        'is_boundary_disagreement_case': False,
    })

    # 10. EVAL-10-RW001-ASSESSMENT-ONLY-DISTORTION-B2 (Core RW-001 regression: E-REQ-B2-EXPOSURE / E-REQ-B2-REASON)
    b10 = build_rw001_full_doc_bundle()
    r10 = make_rw001_faithful_window_response(b10)
    for u in r10['units']:
        if u['id'] == 'u-install-reqs':
            # statement remains 100% faithful ("this app needs to install a menu bar runtime under Applications..."),
            # while assessment.exposure and assessment.reason reproduce B2's exact overstatement from comparison.json!
            u['assessment']['exposure'] = (
                'Retain in the current note as the concrete technical justification for choosing PKG, '
                'keeping the embedded facts about what gets installed and executed.'
            )
            u['assessment']['reason'] = (
                'For a technical collaborator, knowing that the macOS package places the menu bar runtime in '
                'Applications, bundles Node and cloudflared helpers, and triggers a non-blocking post-install '
                'Doctor check is essential to understanding why a simple drag-and-drop DMG is insufficient.'
            )
    a10 = pipeline.assemble_document_analysis(b10, [json.dumps(r10)])
    cases.append({
        'eval_case_id': 'EVAL-10-RW001-ASSESSMENT-ONLY-DISTORTION-B2',
        'source_case_id': 'RW-001',
        'category_focus': 'ASSESSMENT_RATIONALE_DISTORTION',
        'description': 'RW-001 A/B 실험 회귀(E-REQ-B2-EXPOSURE/REASON): 단위 statement는 요구사항 양태("needs to install...")를 정확히 유지했으나, assessment.exposure("embedded facts about what gets installed")와 assessment.reason("knowing that the macOS package places... bundles... triggers...")에서만 실제 패키지 동작 사실로 단정한 평가 근거 왜곡 오류',
        'input_bundle': b10,
        'analysis_result': a10,
        'manual_expected_judgment': 'overstated',
        'manual_expected_error_categories': ['ASSESSMENT_RATIONALE_DISTORTION'],
        'manual_expected_field_paths': ['/units/2/assessment/exposure', '/units/2/assessment/reason'],
        'manual_expected_gate_state': 'FAIL',
        'is_boundary_disagreement_case': False,
    })

    # 11. EVAL-11-AMBIGUOUS-SOURCE-HOLD
    b11 = load_fd001_bundle()
    ambig_clause = '\n- ARM64 서버 패키지의 오프라인 캐시 호환성 여부는 추후 외부 벤치마크 결과에 따라 결정 예정(TBD)이다.'
    b11['document_snapshot']['content'] = b11['document_snapshot']['content'].rstrip('\n') + ambig_clause + '\n'
    b11['document_snapshot']['sha256'] = pipeline.digest_text(b11['document_snapshot']['content'])
    r11 = make_fd001_faithful_window_response(b11)
    for cov in r11['block_coverage']:
        if cov['block_id'] == 'B015':
            cov['unit_ids'].append('u-ambig-arm64')
    r11['units'].append({
        'id': 'u-ambig-arm64',
        'statement': 'ARM64 서버 패키지의 오프라인 캐시 호환성 여부는 추후 외부 벤치마크 결과에 따라 결정 예정(TBD)이다.',
        'quotes': [
            {
                'block_id': 'B015',
                'quote': '- ARM64 서버 패키지의 오프라인 캐시 호환성 여부는 추후 외부 벤치마크 결과에 따라 결정 예정(TBD)이다.',
                'occurrence': 0,
            }
        ],
        'elements': [
            {
                'id': 'el-arm64-tbd',
                'kind': 'condition',
                'value': '추후 외부 벤치마크 결과에 따라 결정 예정(TBD)',
                'quotes': [
                    {
                        'block_id': 'B015',
                        'quote': '추후 외부 벤치마크 결과에 따라 결정 예정(TBD)이다.',
                        'occurrence': 0,
                    }
                ],
            }
        ],
        'relations': [],
        'assessment': {
            'scope_id': b11['writing_contract']['output_scopes'][0]['scope_id'],
            'relevance': 'relevant',
            'importance': 'useful',
            'preservation': 'retain_current',
            'exposure': '미확정 사항(TBD)으로 표시한다.',
            'reason': '원문 자체가 외부 미제공 벤치마크 결과에 의존하는 미확정 사항을 담고 있다.',
            'uncertainty': '외부 벤치마크 결과가 제공되지 않아 지원 여부를 확정할 수 없다.',
        },
    })
    a11 = pipeline.assemble_document_analysis(b11, [json.dumps(r11)])
    cases.append({
        'eval_case_id': 'EVAL-11-AMBIGUOUS-SOURCE-HOLD',
        'source_case_id': 'FD-001',
        'category_focus': 'AMBIGUOUS_SOURCE_EVIDENCE',
        'description': '원문 자체가 외부 미제공 벤치마크 및 추후 결정 예정(TBD)을 참조하여 확정 판단 대신 unresolved(REVIEW)로 보류해야 하는 사례',
        'input_bundle': b11,
        'analysis_result': a11,
        'manual_expected_judgment': 'unresolved',
        'manual_expected_error_categories': ['AMBIGUOUS_SOURCE_EVIDENCE'],
        'manual_expected_field_paths': ['/units/10/statement'],
        'manual_expected_gate_state': 'REVIEW',
        'is_boundary_disagreement_case': False,
    })

    # 12. EVAL-12-BOUNDARY-SUBTLE-SEQUENTIAL-SHIFT-FN (Boundary case: deterministic FN, model evaluator catches it)
    b12 = load_fd001_bundle()
    r12 = make_fd001_faithful_window_response(b12)
    for u in r12['units']:
        if u['id'] == 'u-runtime-overview':
            u['statement'] = (
                '로컬 에이전트 런타임 v0.4.0은 외부 클라우드 업로드 없이 작업 폴더 안에서 파일 검색을 먼저 마친 뒤에야 후속 단계로 테스트 실행을 수행한다.'
            )
    a12 = pipeline.assemble_document_analysis(b12, [json.dumps(r12)])
    cases.append({
        'eval_case_id': 'EVAL-12-BOUNDARY-SUBTLE-SEQUENTIAL-SHIFT-FN',
        'source_case_id': 'FD-001',
        'category_focus': 'CLAIM_OVERSTATEMENT',
        'description': (
            '경계 사례(규칙 감사 미탐 FN / 모델 평가기 탐지): 원문은 병렬 기능("파일 검색과 테스트 실행을 수행한다")만 서술했으나 '
            '추출문이 명시적 조건어 없이 선후 의존 관계("파일 검색을 먼저 마친 뒤에야 후속 단계로 테스트 실행을 수행한다")로 의미를 좁혀 단정한 사례'
        ),
        'input_bundle': b12,
        'analysis_result': a12,
        'manual_expected_judgment': 'overstated',
        'manual_expected_error_categories': ['CLAIM_OVERSTATEMENT'],
        'manual_expected_field_paths': ['/units/1/statement'],
        'manual_expected_gate_state': 'FAIL',
        'is_boundary_disagreement_case': True,
        'disagreement_kind': 'deterministic_false_negative_requires_model_evaluator',
    })

    # 13. EVAL-13-BOUNDARY-CONTRAST-CLAUSE-IN-REASON-FP (Boundary case: deterministic FP on contrasting clause in assessment.reason)
    b13 = load_fd001_bundle()
    r13 = make_fd001_faithful_window_response(b13)
    for u in r13['units']:
        if u['id'] == 'u-cond-macos-manual':
            # Human-faithful editorial rationale contrasting general packages with this experimental build,
            # which contains the substring "자동 업데이트를 지원한다" and triggers lexical polarity reversal FP!
            u['assessment']['reason'] = (
                '일반적인 정식 패키지가 자동 업데이트를 지원한다 하더라도 이 macOS 초기 실험 빌드는 지원하지 않으므로 수동 재설치 필요성을 명시해야 한다.'
            )
    a13 = pipeline.assemble_document_analysis(b13, [json.dumps(r13)])
    cases.append({
        'eval_case_id': 'EVAL-13-BOUNDARY-CONTRAST-CLAUSE-IN-REASON-FP',
        'source_case_id': 'FD-001',
        'category_focus': 'FAITHFUL_PRESERVATION',
        'description': (
            '경계 사례(규칙 감사 오탐 FP): 원문("자동 업데이트를 지원하지 않으며")에 충실한 assessment.reason이 '
            '"일반적인 정식 패키지가 자동 업데이트를 지원한다 하더라도 이 초기 실험 빌드는 지원하지 않으므로..."처럼 양보절 대조 표현을 사용하여 '
            '어휘 극성 규칙이 ASSESSMENT_RATIONALE_DISTORTION으로 오탐하는 사례'
        ),
        'input_bundle': b13,
        'analysis_result': a13,
        'manual_expected_judgment': 'supported',
        'manual_expected_error_categories': [],
        'manual_expected_field_paths': [],
        'manual_expected_gate_state': 'REVIEW',
        'is_boundary_disagreement_case': True,
        'disagreement_kind': 'deterministic_false_positive_on_concessive_contrast_clause',
    })

    # 14. EVAL-14-INTER-EVALUATOR-CONFLICT-HOLD (Multi-evaluator conflict -> unresolved REVIEW)
    b14 = build_rw001_full_doc_bundle()
    r14 = make_rw001_faithful_window_response(b14)
    a14 = pipeline.assemble_document_analysis(b14, [json.dumps(r14)])
    cases.append({
        'eval_case_id': 'EVAL-14-INTER-EVALUATOR-CONFLICT-HOLD',
        'source_case_id': 'RW-001',
        'category_focus': 'EVALUATOR_JUDGMENT_CONFLICT',
        'description': '복수 모델 평가기 간 판단이 supported와 overstated로 충돌할 때 자동 승인하거나 기각하지 않고 unresolved(REVIEW)로 보류하는 사례',
        'input_bundle': b14,
        'analysis_result': a14,
        'manual_expected_judgment': 'unresolved',
        'manual_expected_error_categories': ['EVALUATOR_JUDGMENT_CONFLICT'],
        'manual_expected_field_paths': ['/units/2/statement'],
        'manual_expected_gate_state': 'REVIEW',
        'is_boundary_disagreement_case': True,
        'disagreement_kind': 'inter_evaluator_judgment_conflict_held_at_review',
    })

    return cases


def make_stub_model_responder_for_eval_case(eval_case):
    """Return a stub semantic_responder (or pair of responders for EVAL-14) for an evaluation case."""
    cid = eval_case['eval_case_id']
    bundle = eval_case['input_bundle']
    analysis = eval_case['analysis_result']

    if cid == 'EVAL-14-INTER-EVALUATOR-CONFLICT-HOLD':
        def responder_pass_0(w_idx, _sw, _prompt, _att):
            return pipeline.build_stub_semantic_response_from_audit(bundle, analysis, window_index=w_idx)

        def responder_pass_1(w_idx, _sw, _prompt, _att):
            resp = pipeline.build_stub_semantic_response_from_audit(bundle, analysis, window_index=w_idx)
            for ur in resp['unit_reviews']:
                if ur['unit_id'] == 'u-install-reqs':
                    for fj in ur['field_judgments']:
                        if fj['field_path'] == '/units/2/statement':
                            fj['semantic_judgment'] = 'overstated'
                            fj['error_category'] = 'CLAIM_OVERSTATEMENT'
                            fj['rationale'] = '평가기 2는 요구사항 표현이 여전히 강한 의무 표현이라고 판단함'
            return resp

        return [responder_pass_0, responder_pass_1]

    if cid == 'EVAL-12-BOUNDARY-SUBTLE-SEQUENTIAL-SHIFT-FN':
        def model_catches_subtle_shift(w_idx, _sw, _prompt, _att):
            resp = pipeline.build_stub_semantic_response_from_audit(bundle, analysis, window_index=w_idx)
            for ur in resp['unit_reviews']:
                if ur['unit_id'] == 'u-runtime-overview':
                    for fj in ur['field_judgments']:
                        if fj['field_path'] == '/units/1/statement':
                            fj['semantic_judgment'] = 'overstated'
                            fj['error_category'] = 'CLAIM_OVERSTATEMENT'
                            fj['rationale'] = (
                                '원문 B003은 "파일 검색과 테스트 실행을 수행한다"고 병렬 나열할 뿐이나, '
                                '추출문은 "파일 검색을 먼저 마친 뒤에야 후속 단계로 테스트 실행을 수행한다"고 원문에 없는 선후 의존 관계를 단정함'
                            )
            return resp

        return model_catches_subtle_shift

    def default_stub_responder(w_idx, _sw, _prompt, _att):
        return pipeline.build_stub_semantic_response_from_audit(bundle, analysis, window_index=w_idx)

    return default_stub_responder


def evaluate_semantic_benchmark(*, mode='combined_stub'):
    """Run all 14 fixed evaluation cases and compute TP, TN, FP (오탐), FN (미탐), unresolved holds, and disagreements.

    Modes:
      - 'deterministic_only': `semantic_responder=None` (pure deterministic semantic auditor)
      - 'combined_stub': model stub responder + deterministic semantic auditor
    """
    cases = build_semantic_evaluation_cases()
    case_results = []
    disagreements = []

    tp = 0  # Manual expects distortion (overstated/contradicted) AND validator detects distortion
    tn = 0  # Manual expects supported AND validator judges supported (held at REVIEW only by auto-PASS policy)
    fp = 0  # Manual expects supported BUT validator flags distortion (contradicted/overstated)
    fn = 0  # Manual expects distortion BUT validator judges supported
    unresolved_holds = 0  # Manual expects unresolved AND validator holds as unresolved

    for c in cases:
        cid = c['eval_case_id']
        bundle = c['input_bundle']
        analysis = c['analysis_result']
        responder = None if mode == 'deterministic_only' else make_stub_model_responder_for_eval_case(c)

        gate_report = pipeline.validate_analysis_gate(
            bundle,
            analysis,
            semantic_responder=responder,
            run_semantic_validation=True,
        )
        sem_report = gate_report['semantic_report']
        actual_j = sem_report['overall_judgment']
        expected_j = c['manual_expected_judgment']
        actual_cats = sorted({
            f['error_category'] for f in sem_report['findings'] if f.get('error_category')
        })
        actual_paths = sorted({
            f['field_path'] for f in sem_report['findings'] if f.get('field_path')
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

        rec = {
            'eval_case_id': cid,
            'source_case_id': c['source_case_id'],
            'category_focus': c['category_focus'],
            'manual_expected_judgment': expected_j,
            'actual_overall_judgment': actual_j,
            'manual_expected_error_categories': c['manual_expected_error_categories'],
            'actual_error_categories': actual_cats,
            'manual_expected_field_paths': c['manual_expected_field_paths'],
            'actual_field_paths': actual_paths,
            'manual_expected_gate_state': c['manual_expected_gate_state'],
            'actual_gate_state': gate_report['gate_state'],
            'classification': classification,
            'coverage_complete': sem_report['coverage_summary']['is_complete'],
            'semantic_report_sha256': sem_report['semantic_report_sha256'],
        }
        case_results.append(rec)

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

    return {
        'mode': mode,
        'total_cases': len(cases),
        'metrics': {
            'true_positives': tp,
            'true_negatives': tn,
            'false_positives': fp,
            'false_negatives': fn,
            'unresolved_holds': unresolved_holds,
        },
        'case_results': case_results,
        'disagreements': disagreements,
    }


if __name__ == '__main__':
    det_summary = evaluate_semantic_benchmark(mode='deterministic_only')
    comb_summary = evaluate_semantic_benchmark(mode='combined_stub')
    print(json.dumps({
        'deterministic_only': det_summary['metrics'],
        'combined_stub': comb_summary['metrics'],
        'disagreements_deterministic': det_summary['disagreements'],
        'disagreements_combined': comb_summary['disagreements'],
    }, ensure_ascii=False, indent=2))
