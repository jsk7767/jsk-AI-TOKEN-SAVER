# Compact Agent Handoff

[결과]
- `DONE` / `FOUND` / `CHANGES_REQUESTED` / `PASS` / `FAIL`

[변경·발견]
- `path:line` — 한 줄 설명

[검증]
- `command or probe` → 실제 결과

[위험·보류]
- 없음 / 남은 위험 한 줄

[판정]
- 다음 에이전트가 바로 실행할 한 단계 또는 `없음`

규칙:
- 중간 추론·탐색 기록·전체 로그를 붙이지 않는다.
- 이미 전달한 배경을 반복하지 않는다.
- 경로, 줄, 명령, exit, PASS/FAIL 같은 재현 증거는 생략하지 않는다.
- 서버·보안·DB·권한·배포는 이 템플릿 대신 `clear` 보고를 사용한다.
