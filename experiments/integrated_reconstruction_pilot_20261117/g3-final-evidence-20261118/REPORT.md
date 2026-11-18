# G3 최종 검증 증거 보존

2026-11-18 PR #36의 [최종 검증 보고서](../G3_FINAL_VERIFICATION_20261118.md)에 등록된 원본 10개를 찾아 각각의 SHA-256을 대조했다. 실행 코드 리비전은 `8f748b1c35e063a347889e1fa5e7ad3f232f42e4`이고, 보존 작업 시작 기준은 `a1cee29a2fd4e5a05ae41405a853446554d1edbf`다. 공식 실행은 Python 3.12.3, jsonschema 4.10.3에서 이루어졌다. 과거 실행 환경의 완전 재현 여부는 공식 JSON에 기록되어 있다.

| 보존 증거 | 수량 및 내용 |
| --- | --- |
| [공식 전체 회귀 JSON](logicwrite-g3-final-evidence.json) | 31개 suite·962개 통과. 실패·오류·스킵·예상 실패·예상 밖 성공 0건 |
| [G3 단위 테스트 로그](logicwrite-g3-final-unit.log) | 18개 실행·통과 |
| IR-001~003 B0/B1 JSON | 동결 Qwen 외부 후보 shadow 6건. 원본 후보 경로·해시, 의무, 인용 범위, 자체 주장, HITL 포함 |
| 합성 MOVE·부분 보류 JSON | 실제 G2-C 후보 2건. 구조 계보, 작업 결과, 영향 범위 포함 |
| [SHA-256 manifest](manifest.json) | 10개 파일별 원본·보존본 해시, 경로 변환 횟수, 실행 코드 식별자 |

단위 로그와 사례 JSON 8개는 원본과 바이트가 같다. 공식 JSON 보존본은 로컬 Python 실행기와 임시 픽스처의 절대 경로만 정규화했다. 실행 결과, 판정, 코드 해시는 보존했고 원본 SHA-256과 정규화된 보존본 SHA-256을 각각 기록했다. 동결 Qwen 후보 본문 파일은 기존 경로와 해시를 참조한다.

| 사례 | 판정 |
| --- | --- |
| [IR-001 B0](IR-001-B0.json) / [B1](IR-001-B1.json) | README와 FUNDING의 원문을 인용하고 후원 정책은 `unresolved`. B0의 usage는 KEEP 전용 비교 계획 범위를 위반했다. B1은 후원 작업을 보류하고 출력 설명 작업을 유지했다. |
| [IR-002 B0](IR-002-B0.json) / [B1](IR-002-B1.json) | 두 ops의 500건 초과 중단과 당직자 확인 전 재개 금지 문구 누락은 `violated`. 중단 조건 관련 자체 주장 및 B1의 `completeness_verified`와 충돌하며 일반 의미 검토는 `unresolved`다. |
| [IR-003 B0](IR-003-B0.json) / [B1](IR-003-B1.json) | B0 무수정 권한 검사 통과. B1의 “실패다.” → “실패.” 변경은 `FORMAT_LEXICAL_CHANGE`이며 자체 권한 준수 주장과 충돌한다. |
| [합성 MOVE](synthetic-move.json) / [부분 보류](synthetic-partial.json) | 이동과 원장·trace 결속 통과. 부분 후보는 `place-label` 실행, `move-alarm` 보류. |

모든 사례는 `REVIEW`다. 보존 과정에서 오프라인 사례 8개를 새 경로에서 재실행해 원본과 바이트 단위로 대조했다. 재실행물은 보존본의 출처로 쓰지 않았다. 추가 오프라인 검사에서 후보 변조, 독립 의무 변경, 요구사항 스키마 버전 불일치, 보고서의 검증기 결속 변조 각각에 대해 `is_current_report`가 거부하는 것을 확인했다. 전체 회귀와 단위 테스트 수치는 해시를 확인한 원본 실행 결과다.

## 재현

기준 리비전에서 실행하고, 생성 경로가 이미 사용 중이면 새 이름을 쓴다.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s experiments/full_document_control -p 'test_document_set_g3.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 experiments/integrated_reconstruction_pilot_20261117/g3_offline.py --output /tmp/logicwrite-g3-shadow-new
PYTHONDONTWRITEBYTECODE=1 python3 tools/evidence_validation/run.py --output /tmp/logicwrite-g3-evidence-new.json
```

사례 JSON은 해시를 직접 비교한다. 회귀 JSON과 로그의 재실행본은 실행 시간과 환경 기록이 달라질 수 있으므로 시험 수·결과·코드 리비전을 대조한다.
