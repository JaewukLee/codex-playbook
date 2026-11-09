# Codex Playbook

역할 기반 에이전트 팀을 구성하고 운영 노하우를 축적하는 저장소입니다.

사용자가 요구사항을 먼저 정리하고 AI와 목표·범위·역할을 협의합니다. 팀별로 업무 성격만 정의하고 Mosaic와 실제 에이전트 구성을 의논합니다. 합의한 내용을 검증 가능한 태스크로 기록한 뒤 선택한 태스크를 팀에 배정하고, 구현·검증·회고 결과를 다음 작업에 반영합니다.

- [업무 프로세스](WORKFLOW.md): 요구사항 협의 → 설계 → 태스크 분해 → 선택한 태스크 실행 → 검증·회고
- [기록 템플릿](templates/): 요구사항, 팀 구성, 작업 계획, 태스크, 회고
- [역할 목록과 운영 가이드](agents/README.md): 분야별 역할 후보 16개, 업무 배정, 회고, 지침 개선 방법
- [팀 업무 프로필](teams/TEAM_PROFILES.md): 버그 수정, 신규 기능, 외부 API 연동, 리팩터링, 성능 개선
- [영문 사례 조사: 팀 구성·모니터링·효율 개선](research/2026-11-06-agent-teams-and-observability.md): 실제 사례와 도구 후보, 현재 팀에 적용할 실험

## 역할 원본과 실행용 배치

```text
agents/
  coordination/    # Mosaic, Compass
  design/          # Atlas, Occam, Sentinel
  implementation/  # Bolt, Scalpel, Weaver, Forge, Pulse
  verification/    # Probe, Journey, Anchor, Harness
  research/        # Scout
  knowledge/       # Curator
teams/             # 멤버를 고정하지 않는 업무 프로필
.codex/agents/     # 스크립트가 배치한 실행용 사본
```

역할을 수정할 때는 `agents/`의 원본을 편집한 뒤 Python 3.11 이상으로 배치합니다. 실행용 사본을 직접 수정하면 충돌로 감지합니다.

```bash
python3 scripts/deploy_agents.py
python3 scripts/deploy_agents.py --check
python3 -m unittest discover -s tests -v
```

팀은 폴더별로 자동 구성되지 않습니다. Mosaic와 업무를 의논하며 후보를 선택합니다. 배치가 실제 에이전트 실행이나 기존 세션의 자동 재등록을 의미하지는 않습니다.

## 시작하기

이 저장소를 작업 공간으로 열고 요구사항부터 의논하려면 다음처럼 요청합니다.

```text
WORKFLOW.md와 agents/coordination/mosaic.toml을 읽고 팀 구성 상담을 해줘.
내 요구사항 초안: …
discovery 업무에 필요한 관점과 후보를 제안하고 나와 구성을 의논해줘.
이번에는 협의와 태스크 계획까지만 하고 구현은 시작하지 마.
```

태스크와 팀 구성이 준비되어 있다면 다음처럼 실행 범위를 지정합니다.

```text
<팀 구성 기록>에 합의한 에이전트와 리드로 작업해줘.
업무 기준은 teams/TEAM_PROFILES.md의 bugfix를 따라줘.
대상 프로젝트: <작업할 저장소 경로>
태스크: <해결할 문제>
완료 조건: <검증 가능한 결과>
```

다른 프로젝트에서 사용하려면 이 저장소의 역할 파일을 절대 경로로 지정하거나, `.codex/agents/`를 해당 프로젝트로 복사합니다. 기존 파일이 있다면 비교 후 병합합니다. 대상 프로젝트의 지침과 권한을 따릅니다.

## 운영 노하우 반영

개별 역할의 행동은 `agents/<분류>/<이름>.toml` 원본의 `developer_instructions`에, 팀별 규칙은 `teams/TEAM_PROFILES.md`에 기록합니다. 프로젝트 고유 규칙은 대상 프로젝트의 `AGENTS.md`에서 관리합니다. 회고 근거를 확인한 뒤 적용 조건과 예외를 명시해 규칙을 개선합니다.

이 저장소에는 인증키나 토큰을 저장하지 않습니다. 역할 파일과 프리셋은 재사용할 지침이며 파일을 읽는 것만으로 팀이 자동 실행되지는 않습니다.
