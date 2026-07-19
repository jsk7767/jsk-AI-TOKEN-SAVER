# jsk AI TOKEN SAVER

> v0.4 — active context, tool-output, handoff, and response token-saving runtime for AI agents.

**jsk AI TOKEN SAVER**는 토큰을 세기만 하는 도구가 아닙니다.
Codex·Claude Code·Hermes가 작업할 때 불필요한 문서 로딩, 파일 재조회, 긴 tool output, 서브에이전트 중간 과정, 중복 보고를 실제로 줄이게 만드는 실행 Skill입니다.

## 궁극적 목적

```text
더 적은 토큰으로 더 많은 일을 처리
단, 정확성·안전성·검증 증거는 그대로 유지
```

핵심 지표는 **정확히 완료된 작업 1건당 visible tokens**입니다. 측정은 검증 보조이며, 본체는 에이전트의 작업 방식을 바꾸는 것입니다.

- 짧아졌지만 필수 marker가 사라지면 `FAIL`
- baseline/candidate 중 한쪽 exit code가 없으면 `FAIL`
- 성공률이 낮아지면 `FAIL`
- 짧은 요청이 오히려 길어지면 `FAIL`
- provider 청구액이나 hidden reasoning은 측정한 것처럼 주장하지 않음

## Caveman v1.9.1 head-to-head

**결론: 동일한 tool-rich 저장소 탐색 범위에서는 jsk v0.4가 Caveman v1.9.1보다 낫다고 말할 수 있습니다.**

동일한 `claude-fable-5`, 저장소, prompt, `Read/Grep/Glob`, low effort, read-only permission으로 **3 tasks × 3 trials**를 실행했습니다. 양쪽 모두 정답 marker와 Tool 사용 계약을 100% 통과했고, jsk는 3개 중 2개 task에서 승리했으며 성공 task 중앙값 합계가 10.3% 적었습니다.

| Task | Caveman 중앙값 | jsk 중앙값 | jsk 절감 | 양쪽 성공률 |
|---|---:|---:|---:|---:|
| 반복 읽기 계산 위치 찾기 | 26,943 | 26,743 | 0.74% | 100% |
| kernel token budget 찾기 | 26,471 | 27,055 | -2.21% | 100% |
| CI expected-fail guard 찾기 | 36,494 | 26,848 | 26.43% | 100% |
| **중앙값 합계** | **89,908** | **80,646** | **10.3%** | **100%** |

상시 activation prompt도 같은 `o200k_base` 기준 **Caveman 163 tokens → jsk 152 tokens**입니다. jsk는 출력 문체만 줄이지 않고 검색 후 필요한 slice만 읽기, 결정적 검색 뒤 확인용 재조회 금지, bounded Tool, findings-only handoff까지 함께 적용합니다.

측정값은 Claude Code가 보고한 `input + cache_creation + cache_read + output` token 합계입니다. 동일 조건의 상대 비교용이며 **provider billing claim이 아닙니다**. 출력 압축만 필요한 일부 task에서는 Caveman이 이길 수 있고, 모든 모델·모든 업무에서 10.3%가 보장된다는 뜻도 아닙니다.

- 재현 config: [`benchmarks/caveman-head-to-head-v0.4.json`](benchmarks/caveman-head-to-head-v0.4.json)
- 성공 게이트 runner: [`scripts/head_to_head_benchmark.py`](scripts/head_to_head_benchmark.py)
- raw run·usage·최종 답변 포함 결과: [`reports/caveman-head-to-head-v0.4.json`](reports/caveman-head-to-head-v0.4.json)
- 비교 원본: Caveman v1.9.1 commit `0d95a81`, activation rule SHA-256 `e0343100…e9f3`

```bash
uv run python scripts/head_to_head_benchmark.py \
  benchmarks/caveman-head-to-head-v0.4.json \
  --output reports/caveman-head-to-head-v0.4.json \
  --trials 3 --arms caveman,jsk
```

## 실제 토큰 절약 방식

Skill이 로드되면 에이전트는 다음 순서로 작업합니다.

```text
Hot Cache → Pointer → Search → Slice → Bounded Tools → Compact Handoff → Verified Answer
```

| 절약 지점 | 기존 낭비 | 적용 후 |
|---|---|---|
| 컨텍스트 | 관련 문서와 대화 전체 로딩 | 현재 검증값 → 프로젝트 포인터 → 검색 결과 → 필요한 줄만 읽기 |
| 파일 읽기 | 같은 파일·로그 반복 조회 | 읽은 경로·범위를 재사용하고 변경됐을 때만 재조회 |
| Tool output | 전체 로그·전체 JSON 반환 | 실패 원인, 변경 파일, 필요한 행만 제한 반환 |
| Tool 호출 | 독립 조회를 한 번씩 순차 실행 | 독립 조회는 한 번에 병렬 처리 |
| Skill/지침 | 긴 절차를 모든 AGENTS·프롬프트에 복제 | 포인터만 유지하고 필요한 Skill만 로드 |
| 활성 규칙 | 1,000-token 이상 장문 Skill을 항상 주입 | 152-token kernel만 주입하고 playbook·정책은 필요할 때만 로드 |
| 서브에이전트 | 탐색 과정과 raw transcript까지 메인에 반환 | 최종 근거·경로·검증·위험·판정만 반환 |
| 보고 | 모든 역할이 같은 긴 보고 | Investigator/Reviewer=`minimal`, Worker/QA=`compact`, 위험 작업=`clear` |
| 긴 세션 | 성공 로그와 폐기된 가설까지 계속 보존 | 목표·결정·변경 경로·검증·다음 행동만 압축 보존 |

상세 실행 절차는 [`docs/token-saving-playbook.md`](docs/token-saving-playbook.md)에 있습니다. 이 Skill은 에이전트의 visible context와 작업 출력을 적극적으로 줄이지만, 모델 통신을 가로채는 billing proxy는 아니므로 provider의 실제 청구액은 별도 telemetry 없이는 측정하지 않습니다.

## Codex · Claude Code · Hermes에서 사용

세 에이전트가 사용하는 [Agent Skills](https://agentskills.io/) 형식으로 패키징했습니다. 공통 원본은 `.agents/skills/jsk-ai-token-saver/`이며, 실행 플레이북·compact handoff 템플릿·정책·검증 evaluator가 함께 들어 있습니다. Claude와 Codex에는 opt-in runtime hook, Claude에는 bounded agent preset 3종도 제공합니다.

> 설치 후 Skill을 로드하면 실제 작업 중 선택적 읽기·도구 출력 제한·최종 handoff 압축 규칙이 적용됩니다. evaluator는 절감 정책을 변경하거나 절감률을 주장할 때만 사용합니다.

### 저장소에서 바로 사용

```bash
git clone https://github.com/jsk7767/jsk-AI-TOKEN-SAVER.git
cd jsk-AI-TOKEN-SAVER
uv sync
```

| 환경 | 자동 인식 파일 | 실행 |
|---|---|---|
| Codex | `AGENTS.md`, `.agents/skills/...`, `.codex/hooks.json` | trusted project에서 `codex` 실행 후 `$jsk-ai-token-saver` 요청 |
| Claude Code | `CLAUDE.md`, `.claude/skills/...`, `.claude-plugin/plugin.json` | `claude --plugin-dir .` 또는 `/jsk-ai-token-saver` |
| Hermes Agent | 설치한 `jsk-ai-token-saver` skill | `/skill jsk-ai-token-saver` 또는 `hermes -s jsk-ai-token-saver` |

### Claude runtime hook + compact agents

```bash
claude --plugin-dir .
```

SessionStart에서 152-token kernel을 한 번 주입하고, UserPromptSubmit에는 40-token 이하 reminder만 넣습니다. `agents/jsk-scout.md`, `jsk-worker.md`, `jsk-reviewer.md`는 parent context로 raw 탐색 과정을 되가져오지 않는 출력 계약을 사용합니다. hook을 끄려면 실행 전에 `JSK_TOKEN_SAVER=off`를 설정하거나 `--plugin-dir` 없이 실행합니다. hook은 파일을 수정하거나 telemetry를 보내지 않습니다.

Codex의 project-local `.codex/config.toml`과 `.codex/hooks.json`은 Codex 보안 정책상 저장소를 trusted project로 승인한 뒤에만 로드됩니다. 승인 전에도 Agent Skill은 명시 호출할 수 있지만 SessionStart hook은 실행되지 않습니다.

### Codex 전역 설치

Codex 공식 사용자 skill 경로는 `$HOME/.agents/skills`입니다.

```bash
mkdir -p "$HOME/.agents/skills"
cp -R ".agents/skills/jsk-ai-token-saver" "$HOME/.agents/skills/jsk-ai-token-saver"
test -f "$HOME/.agents/skills/jsk-ai-token-saver/SKILL.md"
```

Codex를 다시 시작한 뒤 `$jsk-ai-token-saver`로 명시 호출하거나 “이 작업을 토큰 절약 모드로 진행해”라고 요청합니다.

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

Hermes에는 GitHub의 `owner/repo/path` 식별자로 설치합니다. 이 방식은 `SKILL.md`뿐 아니라 같은 skill 폴더의 `scripts/`, `templates/`, `references/` 파일까지 함께 설치합니다.

```bash
hermes skills install 'jsk7767/jsk-AI-TOKEN-SAVER/.agents/skills/jsk-ai-token-saver' --yes
hermes skills list
hermes -s jsk-ai-token-saver
```

실행 중에는 `/skill jsk-ai-token-saver`로 로드할 수도 있습니다. 설치 후 목록에 보이지 않으면 새 세션을 시작하거나 `/reload-skills`를 실행합니다.

### 에이전트에게 요청하는 예시

```text
이 저장소 작업을 jsk-ai-token-saver 모드로 진행해. 검색 후 필요한 줄만 읽고 같은 파일은 반복 조회하지 마.
서브에이전트는 중간 과정을 가져오지 말고 경로·근거·검증·판정만 compact로 반환해.
긴 로그와 전체 JSON은 넣지 말고 실패 원인과 필요한 행만 가져와.
마지막에 실제 적용한 절약 규칙과 PASS/FAIL만 보고해.
```

## 측정은 검증 보조

일반 작업에서는 아래 프로그램을 실행하지 않습니다. 절약 정책을 바꾸거나 baseline/candidate를 비교하거나 수치로 절감률을 주장할 때만 사용합니다.

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

### 3. `head_to_head_benchmark.py`

실제 Claude Code를 같은 모델·작업·Tool·permission으로 실행해 baseline/Caveman/jsk/hybrid를 비교합니다. competitor rule은 pinned commit과 SHA-256이 일치해야 실행되며, 정답 marker·최소 Tool 호출·성공률을 먼저 통과한 run만 비교합니다. live runner는 개발용 저장소 도구이며 Hermes 설치 Skill bundle에는 포함하지 않습니다.

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
├── .claude-plugin/# Claude SessionStart/UserPromptSubmit runtime
├── .codex/        # Codex SessionStart hook
├── agents/        # bounded scout/worker/reviewer 출력 계약
├── AGENTS.md      # Codex 프로젝트 지침
├── CLAUDE.md      # Claude Code 프로젝트 지침
├── scripts/       # offline evaluator 2종 + live head-to-head runner
├── tests/         # marker·exit·성공률·빈 계약 회귀 테스트
├── benchmarks/    # 합성·익명화 fixture
├── reports/       # 재현 가능한 fixture 결과
├── docs/          # 실제 절약 플레이북 + 측정·안전 정책
└── .github/       # 공개 CI
```

## 검증 측정 범위

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

실제 작업 절차는 [`docs/token-saving-playbook.md`](docs/token-saving-playbook.md), 측정·안전 기준은 [`docs/token-saving-policy.md`](docs/token-saving-policy.md)를 참고하세요.

판정 순서는 항상 다음과 같습니다.

```text
정확성 → 안전성 → 필수 근거 → 성공률 → 토큰 절감
```

## 공개 범위와 개인정보

공개 fixture는 합성·익명화 데이터만 사용합니다. 개인 경로, API 키, credential, 내부 서버/MCP schema는 포함하지 않습니다.

## 라이선스

별도 라이선스가 지정되기 전까지 저작권은 저장소 소유자에게 있습니다.
