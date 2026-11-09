@AGENTS.md

## Claude Code 전용 참고

- 서브에이전트 정의는 `.claude/agents/*.md`이며 `scripts/deploy_agents.py`가 `agents/` 원본에서 생성한다. 직접 수정하지 않는다.
- 서브에이전트는 다른 서브에이전트를 생성하지 못한다. Mosaic(구성 상담)와 Compass(리드)는 메인 세션이 역할 파일을 읽고 직접 맡는다. 세부 사항은 `agents/README.md`의 "도구별 사용 방법"을 따른다.
