# MCP 레지스트리 및 PyPI 정식 배포 가이드

> 공식 MCP 레지스트리(`io.github.rubato103/nl-openapi-mcp`)와
> PyPI 정식 패키지(`nl-openapi-mcp`) 발행을 위한 요구사항 및 진행 가이드입니다.

---

## 1. PyPI 정식 등록 가이드
1. PyPI 계정 및 **Trusted Publishing (OIDC)** 설정
   - PyPI.org에서 프로젝트(`nl-openapi-mcp`) 생성 또는 신규 등록 시 GitHub Actions Trusted Publishing 추가
   - Repo: `rubato103/nl-openapi-mcp`, Workflow: `publish-pypi.yml`
2. **배포 트리거**
   - GitHub Release 생성 시 `.github/workflows/publish-pypi.yml`이 작동하여 자동으로 wheel 및 sdist를 PyPI에 등록합니다.
   - 배포 후 사용자는 다음 명령어로 즉시 설치 및 실행할 수 있습니다:
     ```bash
     pip install nl-openapi-mcp
     # 또는
     uvx nl-openapi-mcp status
     ```

---

## 2. 공식 MCP 레지스트리 등재 가이드
1. 레포지토리 내 `server.json` 파일의 정합성 유지
   - `name`: `"io.github.rubato103/nl-openapi-mcp"`
   - `packages`: PyPI 패키지 및 버전 정보 기재
2. **MCP 레지스트리 배포 트리거**
   - 버전 태그(`v*`) 푸시 시 `.github/workflows/publish-mcp.yml`이 실행됩니다.
   - GitHub OIDC를 통해 `mcp-publisher`가 자동으로 MCP 레지스트리에 업데이트를 전송합니다.

---

## 3. Claude Desktop 디렉터리 등재 심사 준비
- **모든 도구 기능 동작**: 4개 도구(`nl_status`, `nl_search`, `nl_detail`, `nl_collect`)의 정상 응답 보장
- **안전성 (Annotations)**: 조회 도구는 `readOnlyHint=True`, 파일 저장 도구(`nl_collect`)는 로컬 비파괴 쓰기 명시
- **보안**: API 키는 `.env` 및 환경변수(`NL_API_KEY`)로만 주입되며, 예외 및 로그 메시지에 API 키나 인증 URL이 노출되지 않도록 처리(`@_safe`)
