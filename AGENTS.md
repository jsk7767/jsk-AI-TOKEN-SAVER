# AGENTS.md — jsk AI TOKEN SAVER

## 목적
정확히 완료된 작업당 visible token을 줄인다. 답변 길이 자체를 목표로 삼지 않는다.

## Codex native skill

Codex는 저장소의 `.agents/skills/jsk-ai-token-saver/SKILL.md`를 자동 발견한다.
토큰 절감, 보고 압축, baseline/candidate 비교, 반복 tool output 또는 context headroom 측정 요청에서는 `$jsk-ai-token-saver`를 명시적으로 호출하거나 해당 skill을 먼저 로드한다.

전역 설치본에서도 같은 skill 이름과 계약을 사용한다. 저장소 안에서는 CI 재현을 위해 루트 `scripts/`, `benchmarks/`, `reports/` 경로를 우선한다.

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
