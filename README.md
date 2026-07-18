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

## Codex · Claude Code · Hermes에서 사용

세 에이전트가 사용하는 [Agent Skills](https://agentskills.io/) 형식으로 패키징했습니다. 공통 원본은 `.agents/skills/jsk-ai-token-saver/`이며, 두 evaluator·실행 예제·정책 문서가 함께 들어 있습니다.

> 이 프로젝트는 에이전트가 안전한 압축 규칙을 따르고 visible trace를 측정하게 만드는 skill입니다. **자동으로 실제 API 청구 토큰을 줄이는 프록시가 아닙니다.** 모델 통신을 가로채거나 provider billing·hidden reasoning을 측정하지 않습니다.

### 저장소에서 바로 사용

```bash
git clone https://github.com/jsk7767/jsk-AI-TOKEN-SAVER.git
cd jsk-AI-TOKEN-SAVER
uv sync
```

| 환경 | 자동 인식 파일 | 실행 |
|---|---|---|
| Codex | `AGENTS.md`, `.agents/skills/jsk-ai-token-saver/SKILL.md` | 저장소 루트에서 `codex` 실행 후 `$jsk-ai-token-saver` 요청 |
| Claude Code | `CLAUDE.md`, `.claude/skills/jsk-ai-token-saver/SKILL.md` | 저장소 루트에서 `claude` 실행 후 `/jsk-ai-token-saver` |
| Hermes Agent | 설치한 `jsk-ai-token-saver` skill | `/skill jsk-ai-token-saver` 또는 `hermes -s jsk-ai-token-saver` |

### Codex 전역 설치

Codex 공식 사용자 skill 경로는 `$HOME/.agents/skills`입니다.

```bash
mkdir -p "$HOME/.agents/skills"
cp -R ".agents/skills/jsk-ai-token-saver" "$HOME/.agents/skills/jsk-ai-token-saver"
test -f "$HOME/.agents/skills/jsk-ai-token-saver/SKILL.md"
```

Codex를 다시 시작한 뒤 `$jsk-ai-token-saver`로 명시 호출하거나 토큰 측정을 자연어로 요청합니다.

### Claude Code 전역 설치

Claude Code 공식 개인 skill 경로는 `$HOME/.claude/skills`입니다.

```bash
mkdir -p "$HOME/.claude/skills"
cp -R ".agents/skills/jsk-ai-token-saver" "$HOME/.claude/skills/jsk-ai-token-saver"
test -f "$HOME/.claude/skills/jsk-ai-token-saver/SKILL.md"
```

Claude Code에서 `/jsk-ai-token-saver`로 실행합니다. 저장소 안에서는 `.claude/skills/` 어댑터가 공통 skill을 자동 연결합니다.

### Windows PowerShell 복사

```powershell
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -Force ".agents\skills\jsk-ai-token-saver" "$HOME\.agents\skills\jsk-ai-token-saver"
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force ".agents\skills\jsk-ai-token-saver" "$HOME\.claude\skills\jsk-ai-token-saver"
```

### Hermes Agent 설치

Hermes는 URL의 `SKILL.md`와 그 문서가 참조한 `scripts/`, `templates/`, `references/` 파일을 함께 설치합니다.

```bash
hermes skills install 'https://raw.githubusercontent.com/jsk7767/jsk-AI-TOKEN-SAVER/main/.agents/skills/jsk-ai-token-saver/SKILL.md' --yes
hermes skills list
hermes -s jsk-ai-token-saver
```

실행 중에는 `/skill jsk-ai-token-saver`로 로드할 수도 있습니다. 설치 후 목록에 보이지 않으면 새 세션을 시작하거나 `/reload-skills`를 실행합니다.

### 에이전트에게 요청하는 예시

```text
이 작업의 baseline과 candidate를 jsk-ai-token-saver로 비교해줘.
필수 근거와 exit code를 유지하면서 worker handoff 토큰을 줄이고 PASS/FAIL을 보여줘.
이 tool trace의 반복 읽기·retry·context headroom을 측정해줘.
```

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
| Internal report safe modes | 286 | 118 | 58.74% | PASS |
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
├── .agents/       # Codex 자동 발견 + 공통 Agent Skill 패키지
├── .claude/       # Claude Code project skill 어댑터
├── AGENTS.md      # Codex 프로젝트 지침
├── CLAUDE.md      # Claude Code 프로젝트 지침
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
