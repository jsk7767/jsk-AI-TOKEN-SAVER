# jsk AI TOKEN SAVER

> Safety-first visible-token measurement toolkit for AI agent workflows.

**jsk AI TOKEN SAVER**는 AI 답변을 무조건 짧게 만드는 도구가 아닙니다.
정확성·필수 근거·성공률을 먼저 검증하고, 그 조건을 통과한 결과에서만 실제 visible token 절감량을 측정합니다.

## 궁극적 목적

```text
더 적은 토큰으로 더 많은 일을 처리
단, 정확성·안전성·검증 증거는 그대로 유지
```

핵심 지표는 **정확히 완료된 작업 1건당 visible tokens**입니다.

- 짧아졌지만 필수 marker가 사라지면 `FAIL`
- baseline/candidate 중 한쪽 exit code가 없으면 `FAIL`
- 성공률이 낮아지면 `FAIL`
- 짧은 요청이 오히려 길어지면 `FAIL`
- provider 청구액이나 hidden reasoning은 측정한 것처럼 주장하지 않음

## 포함된 프로그램

### 1. `token_ab_benchmark.py`

`clear / compact / minimal` 보고 fixture를 정확한 tokenizer로 비교합니다.

- marker 보존
- exit code 보존
- 안전 압축 합계 절감률
- 빈 case와 빈 marker 계약 차단

### 2. `token_visible_benchmark.py`

캡처한 작업 trace에서 다음을 측정합니다.

- system/user/tool/assistant 전체 visible tokens
- tool output tokens
- 반복 읽기 tokens
- retry tokens
- 성공 작업의 median/p90/mean
- context headroom

## 검증된 공개 fixture 결과

| Fixture | Baseline | Candidate | 절감률 | 판정 |
|---|---:|---:|---:|---|
| Internal report safe modes | 291 | 122 | 58.08% | PASS |
| RTK allowed output aggregate | 3987 | 2938 | 26.31% | PASS |
| TOON uniform / uniform-pretty-json-vs-toon | 1305 | 518 | 60.31% | PASS |
| TOON uniform / uniform-compact-json-vs-toon | 801 | 518 | 35.33% | PASS |
| TOON nested / nested-compact-json-vs-toon-guard | 609 | 731 | -20.03% | EXPECTED FAIL |
| Headroom / uniform-200-log-records | 9245 | 6265 | 32.23% | PASS |
| Headroom / nested-30-records | 1569 | 1660 | -5.8% | EXPECTED FAIL |

`EXPECTED FAIL`은 프로그램 오류가 아닙니다. 후보가 토큰을 늘리거나 안전 계약을 통과하지 못했을 때 evaluator가 정확히 차단하는지 확인하는 회귀 fixture입니다.

## 빠른 시작

### 요구사항

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

### 설치와 전체 테스트

```bash
git clone https://github.com/jsk7767/jsk-AI-TOKEN-SAVER.git
cd jsk-AI-TOKEN-SAVER
uv sync
uv run python -m unittest discover -s tests -v
```

### 내부 보고 A/B 측정

```bash
uv run python scripts/token_ab_benchmark.py \
  benchmarks/internal-report-ab.json \
  --encoding o200k_base \
  --output reports/token-ab-baseline.json
```

### RTK 도구 출력 A/B 측정

```bash
uv run python scripts/token_ab_benchmark.py \
  benchmarks/rtk-v0.43.0-tool-output.json \
  --encoding o200k_base \
  --output reports/rtk-v0.43.0-pilot.json
```

### v2 작업 trace 측정

```bash
uv run python scripts/token_visible_benchmark.py \
  benchmarks/toon-v2.3.1-uniform-visible.json \
  --encoding o200k_base \
  --output reports/toon-v2.3.1-uniform-visible.json
```

## 저장소 구조

```text
jsk-AI-TOKEN-SAVER/
├── scripts/       # exact-token evaluator 2종
├── tests/         # marker·exit·성공률·빈 계약 회귀 테스트
├── benchmarks/    # 합성·익명화 fixture
├── reports/       # 재현 가능한 fixture 결과
├── docs/          # 토큰 절약 운영 정책
└── .github/       # 공개 CI
```

## 측정 범위

이 저장소가 측정하는 것:

- fixture와 trace에 기록된 visible text
- `o200k_base` 기준 exact token count
- 필수 marker·exit code·성공률 계약

이 저장소가 주장하지 않는 것:

- 모델의 hidden reasoning tokens
- API 공급자의 실제 청구액
- 모든 업무에서 동일한 절감률
- 서로 다른 후보 절감률의 단순 합산

## 운영 원칙

자세한 기준은 [`docs/token-saving-policy.md`](docs/token-saving-policy.md)를 참고하세요.

판정 순서는 항상 다음과 같습니다.

```text
정확성 → 안전성 → 필수 근거 → 성공률 → 토큰 절감
```

## 공개 범위와 개인정보

공개 fixture는 합성·익명화 데이터만 사용합니다. 개인 경로, API 키, credential, 내부 서버/MCP schema는 포함하지 않습니다.

## 라이선스

별도 라이선스가 지정되기 전까지 저작권은 저장소 소유자에게 있습니다.
