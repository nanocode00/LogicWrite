"""Render a legible, complete but non-authoritative confirmation booklet."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
data = json.loads((HERE/"confirmation-batch.json").read_text(encoding="utf-8"))
target = HERE/"REVIEW.md"
if target.exists():
    raise ValueError("Refusing to overwrite review booklet")
lines=[
 "# 기존 17건 검토 내용 — 정식 기록 연결 검토안",
 "",
 "**판단 재검토가 아니다.** 이미 제출한 사용자 최초/최종 판단·Codex 반례 검토·개발용 골드 포함 승인 17건을 유지한다.",
 "",
 "- 기존 포함 승인: 17/17",
 "- 기존 신규 적격성/활성화: 0/17, 기존 골드 SP-001~012 12건 유지",
 "- Codex 인용 근거 후보: 34개, 아직 사용자가 정식 최종 증거로 확인한 것은 0개",
 "- 반론 응답 원문: 17건 모두 사용자는 Codex의 반론 타당성 평가에 동의했다. 정식 challenge별 accept/reject/defer는 매핑하지 않는다.",
 "- UNRESOLVED 4건의 기존 사유·판단 유지 재확인은 별도 user-reconfirmation.json에 전사했다. 정식 evidence·challenge 응답 확인으로 확장하지 않으며, 완료된 검토를 다시 요구하지 않는다.",
 "",
 "## 사례별 기존 판단과 제안 근거",
 "",
 "| 사례 | 사용자 최종 판단 | 최초 사용자 이유 | 검토 상태 |",
 "|---|---|---|---|"
]
for row in data["cases"]:
    lines.append(f"| {row['case_id']} | {row['historical_final']['judgment']} | {row['historical_initial']['rationale'].replace('|','/')} | 포함 승인됨 / 정식 응답·증거 미확인 |")
lines.extend(["", "## Codex 반론과 근거 인용 (사용자 채택 전)", ""])
for row in data["cases"]:
    lines.extend([
      f"### {row['case_id']} · {row['historical_final']['judgment']}",
      "",
      f"- 기존 최초 판단: {row['historical_initial']['rationale']}",
      f"- Codex가 검토한 반론: {row['historical_codex_argument']}",
      f"- Codex의 반론 타당성 평가: {row['codex_assessment']}",
      f"- 실제 사용자 응답: Codex 평가에 동의 / 최종 판단 {row['historical_final']['judgment']}",
      "- 정식 challenge ID·응답: 미확정 (사용자의 기존 동의를 임의로 accept/reject/defer로 치환하지 않음)",
    ])
    if row["initial_unresolved_reason"]:
        lines.append(f"- 사용자가 유지를 재확인한 기존 미해결 이유: {row['initial_unresolved_reason']}")
    for e in row["candidate_final_evidence"]:
        quote = e["quote"].replace("\n"," ⏎ ").replace("|","/")
        lines.append(f"- AI 출처 인용 후보 [{e['side']} / {e['document_id']} / {e['start']}:{e['end']}]: “{quote}”")
    lines.append("")
lines.extend([
 "## 제출·활성화 경계",
 "",
 "이 책자는 사용자 확인을 준비한 초안이며 새로운 사용자 증거·정식 최종 이벤트·골드 활성화가 아니다.",
 "기존 판단·포함 승인과 미해결 사유 유지 재확인을 재수집하지 않는다. 별도 레거시 이관 경로는 후속 PR에서 검수하며 AI 인용·응답 매핑·확인되지 않은 필드는 사용자 제출로 만들지 않는다.",
 "사용자 확인 이후에도 review.py의 정식 event-chain 충족 여부는 독립적으로 검증해야 하며, 자동으로 개발용 골드를 활성화하지 않는다.",
 ""
])
target.write_text("\n".join(lines),encoding="utf-8")
print(f"rendered {len(data['cases'])} cases into {target.name}")
