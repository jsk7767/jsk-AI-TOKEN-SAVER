# AGENTS.md — jsk AI TOKEN SAVER

## 목적
정확히 완료된 작업당 visible token을 줄인다. 답변 길이 자체를 목표로 삼지 않는다.

## Codex native skill

Codex는 저장소의 `.agents/skills/jsk-ai-token-saver/SKILL.md`를 자동 발견한다.
저장소·리서치·장기 작업·멀티에이전트·반복 tool/file 작업 또는 토큰 절감 요청에서는 `$jsk-ai-token-saver`를 먼저 로드하고 실제 절약 루프를 적용한다.

## 실제 절약 규칙

- 현재 검증된 컨텍스트 → 프로젝트 포인터 → 검색 → 필요한 줄 범위 순서로 읽는다.
- 변경되지 않은 파일·로그·성공한 검사 결과를 이유 없이 반복해서 읽거나 실행하지 않는다.
- 독립 조회는 일괄 실행하고, 서브에이전트는 중간 과정이 아닌 최종 근거·경로·검증·판정만 반환한다.
- 측정기는 정책 변경, A/B 비교, 절감률 주장 때만 사용한다. 측정이 기본 작업 흐름이 아니다.
- 세부 절차의 단일 원본은 `.agents/skills/jsk-ai-token-saver/SKILL.md`다. 이 파일에 장문 절차를 복제하지 않는다.

## 불변 규칙
- 정확성, 안전성, required marker, exit code, 성공률을 토큰 절감보다 먼저 판정한다.
- `billing_claim`과 `hidden_reasoning_measured`는 실제 근거 없이 `true`로 바꾸지 않는다.
- 빈 suite/task/case와 빈 required marker가 PASS하지 못하게 한다.
- 서로 다른 fixture 또는 token surface의 절감률을 합산하지 않는다.
- 실패 후보를 통과시키기 위해 assertion이나 threshold를 약화하지 않는다.
- 공개 fixture에 개인 경로, credential, 실제 서버·고객 데이터를 넣지 않는다.

## 검증
```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run python scripts/token_ab_benchmark.py benchmarks/internal-report-ab.json --encoding o200k_base
uv run python scripts/token_ab_benchmark.py benchmarks/rtk-v0.43.0-tool-output.json --encoding o200k_base
uv run python scripts/token_visible_benchmark.py benchmarks/toon-v2.3.1-uniform-visible.json --encoding o200k_base
```

`headroom-v0.32.0-lossless-visible.json`과 `toon-v2.3.1-nested-guard-visible.json`은 evaluator가 위험 후보를 차단하는지 보는 expected-fail fixture다.
