# AGENTS.md

Codex와 Claude Code가 공통으로 읽는 저장소 지침이다. Claude Code는 `CLAUDE.md`에서 이 파일을 import한다.

## 저장소 성격

역할 기반 에이전트 팀을 구성하고 운영 노하우를 축적하는 playbook이다. 제품 코드는 없으며 역할 원본, 팀 업무 프로필, 업무 프로세스, 기록 템플릿과 배치 스크립트로 구성된다. 개요는 [README.md](README.md), 운영 흐름은 [WORKFLOW.md](WORKFLOW.md)를 읽는다.

## 원본과 실행용 사본

- 역할 원본은 `agents/<분류>/<이름>.toml` 하나뿐이다. 역할을 고칠 때는 원본만 편집한다.
- 실행용 사본은 스크립트가 생성한다. 직접 수정하지 않는다.
  - Codex: `.codex/agents/<이름>.toml`
  - Claude Code: `.claude/agents/<이름>.md`
- 각 사본 디렉터리의 `.deployment-manifest.json`은 배치 이력이므로 직접 편집하지 않는다.
- 원본을 수정한 뒤 배치하고, 테스트와 최신 여부 검사를 통과시킨다.

```bash
python3 scripts/deploy_agents.py            # 모든 도구에 배치
python3 scripts/deploy_agents.py --check    # 최신 여부만 검사 (STALE이면 종료 코드 1)
python3 scripts/deploy_agents.py --runtime claude   # 특정 도구만
python3 -m unittest discover -s tests -v
```

Python 3.11 이상이 필요하다.

## 공통 작업 규칙

- 문서와 역할 지침은 한국어로 작성하고 코드 식별자는 유지한다.
- 역할 지침에는 관찰 가능한 행동을 적는다. 도구별 설정 차이는 원본 TOML의 필드로 표현하고 지침 본문에 도구 이름을 섞지 않는다.
- 인증키, 토큰, 개인 설정 파일을 커밋하지 않는다.
