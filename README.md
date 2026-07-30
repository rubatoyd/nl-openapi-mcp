# nl-openapi-mcp

<!-- mcp-name: io.github.rubato103/nl-openapi-mcp -->

[![CI](https://github.com/rubato103/nl-openapi-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/rubato103/nl-openapi-mcp/actions/workflows/ci.yml)

국립중앙도서관 **대한민국 국가서지 OpenAPI (Seoji OpenAPI)** 문헌·도서 서지 메타데이터 검색·수집 **MCP 서버 + CLI**.
자매 프로젝트 `kci-openapi-mcp` 및 `scienceon-mcp`와 동일한 공통 코어(REST/MCP/CLI/Exporter) 아키텍처를 공유합니다.

> An MCP server + CLI for National Library of Korea Seoji OpenAPI. Bring your own API key and search & harvest Korean academic literature and book bibliography metadata in any project.

---

## 무엇을 할 수 있나
- 🔎 **일반 검색 (`kwd`) & 상세 검색 (`title`, `author`, `publisher`, `keyword`, `isbn`, `seoji_year`)**: 국가서지 도서 및 문헌 검색
- 📄 **단건 조회**: 제어번호(`control_no`) 및 URL 경로를 통한 서지사항 확인
- 💾 **대량 수집 & 파일 저장**: 검색 결과를 **`xlsx` / `csv` / `json` / `sqlite`** 형태로 로컬 내보내기
- 🤖 **두 가지 사용법**: Claude에서 도구 호출(MCP) · 터미널 배치(CLI) — 같은 코어 공유

---

## 요구사항
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (패키지 관리)
- 국립중앙도서관 OpenAPI 발급키 (`NL_API_KEY`)

---

## 1) API 키 발급
1. [국립중앙도서관 OpenAPI 안내 페이지](https://librarian.nl.go.kr)에 접속하여 회원가입·로그인
2. **OpenAPI 이용신청** → `대한민국 국가서지 Open API` 신청 및 승인 후 API 키 발급
3. 환경변수 `NL_API_KEY` (또는 프로젝트 내 `.env`)에 발급키 설정

---

## 2) 설치 및 실행

**전제: [uv](https://docs.astral.sh/uv/) 설치** (Windows: `winget install astral-sh.uv`).

### 방법 A — uvx (설정 직접, 설치 불필요 - PyPI / Git)
PyPI 정식 등록 후:
```bash
uvx nl-openapi-mcp status
uvx nl-openapi-mcp search --kwd "정보"
```
또는 GitHub 소스에서 실행:
```bash
uvx --from git+https://github.com/rubato103/nl-openapi-mcp nl-mcp status
```

### 방법 B — 로컬 개발 환경 (OneDrive 동기화 폴더 대응)
클라우드 동기화 폴더 안에서 작업할 경우 가상환경을 외부에 생성합니다:
```bash
# Windows (PowerShell/CMD)
set UV_PROJECT_ENVIRONMENT=C:\Users\rubat\.venvs\nl-openapi-mcp
uv sync

# Linux / macOS
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/nl-openapi-mcp"
uv sync
```

---

## 3) Claude에 MCP 연결

**Claude Code** (`.mcp.json`):
```bash
claude mcp add nl --env NL_API_KEY=$NL_API_KEY -- uvx --from git+https://github.com/rubato103/nl-openapi-mcp nl-mcp
```

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "nl-seoji": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/rubato103/nl-openapi-mcp", "nl-mcp"],
      "env": {
        "NL_API_KEY": "발급받은_API_KEY"
      }
    }
  }
}
```

---

## 4) MCP 도구 및 CLI 사용법

### MCP 도구 목록
- `nl_status`: API 키 설정 여부 및 OpenAPI 서버 상태 점검
- `nl_search`: 일반/상세 키워드 검색 및 페이징 (title, author, publisher, keyword, isbn 등)
- `nl_detail`: 제어번호 또는 표제를 통한 단건 상세 정보 조회
- `nl_collect`: 대량 수집 및 로컬 파일(`xlsx`, `csv`, `json`, `sqlite`) 저장

### CLI 예시
```bash
# 상태 점검
nl-mcp status

# 일반 검색
nl-mcp search --kwd "도서관" --rows 5

# 상세 검색
nl-mcp search --title "토지" --author "박경리"

# 대량 수집 후 엑셀 저장
nl-mcp collect --kwd "정보학" --max-records 50 --format xlsx --output results.xlsx
```

---

## 5) 공식 MCP 레지스트리 및 PyPI 등록
- **MCP Registry Identifier**: `io.github.rubato103/nl-openapi-mcp`
- **PyPI Package**: `nl-openapi-mcp`

---

## 라이선스
MIT License © Yeondong Yang (rubato103)
