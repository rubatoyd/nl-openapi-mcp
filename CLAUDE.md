# CLAUDE.md — nl-openapi-mcp 프로젝트 개발 가이드

## 프로젝트 개요
국립중앙도서관 국가서지 OpenAPI(`seojiSearch.do`)를 활용하여 학술 문헌 및 도서 메타데이터를 검색·수집하는 MCP 서버 + CLI 패키지.
`kci-openapi-mcp`, `scienceon-mcp`와 동일한 공통 코어 아키텍처를 가집니다.

## 주요 환경 규칙
1. **가상환경 설정 (`uv` 외부 관리)**
   - 프로젝트 경로가 OneDrive 클라우드 동기화 폴더이므로 가상환경은 반드시 로컬 외부 경로에 위치시켜야 합니다.
   - Windows cmd/PowerShell:
     ```cmd
     set UV_PROJECT_ENVIRONMENT=C:\Users\rubat\.venvs\nl-openapi-mcp
     uv sync
     ```
   - Linux / macOS / Bash:
     ```bash
     export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/nl-openapi-mcp"
     uv sync
     ```
2. **패키지 관리 및 빌드**
   - 패키지 관리: `uv` 전용
   - 빌드 백엔드: `hatchling` (`pyproject.toml`)

## 개발 명령어
- **의존성 동기화**: `uv sync`
- **단위 테스트 실행**: `uv run pytest -v`
- **특정 테스트 실행**: `uv run pytest tests/test_parser.py -v`
- **CLI 테스트**: `uv run nl-mcp status`
- **MCP 스모크 테스트**: `uv run python scripts/mcp_smoke.py`
- **패키지 빌드 (wheel/sdist)**: `uv build`

## 아키텍처 명서 (`src/nl_mcp/`)
- `config.py`: 환경변수(`NL_API_KEY` 또는 `SEOJI_API_KEY`) 로딩 및 OpenAPI base URL 정의
- `models.py`: 데이터 스키마 (`SeojiRecord`, `SearchResult`)
- `client.py`: `NlSeojiClient` — OpenAPI HTTP 통신, 페이징, 오류 핸들링
- `parser.py`: JSON/XML 정규화 파서 (HTML 하이라이트 태그 `<span class="highlight">` 정제)
- `exporters.py`: `xlsx`, `csv`, `json`, `sqlite` 파일 내보내기 도구
- `server.py`: `FastMCP("nl")` 기반 MCP 도구 핸들러 (`@_safe` 어노테이션 및 도구 주석 포함)
- `cli.py`: 명령행 인터페이스 (`status`, `search`, `collect`)
