# nl-openapi-mcp 아키텍처 및 설계 의도

> 국립중앙도서관 국가서지 OpenAPI(`seojiSearch.do`)를 활용하여 학술 문헌·도서 서지정보를
> 검색하고 대량 수집할 수 있도록 설계된 공통 코어(REST + MCP + CLI) 아키텍처.
> 자매 프로젝트 `kci-openapi-mcp`, `scienceon-mcp`와 아키텍처 호환성을 유지한다.

---

## 1. 레이어 구조

```
server.py / cli.py              ← MCP 도구 · CLI 표면
        │
     client.py                  ← 국립중앙도서관 OpenAPI HTTP 클라이언트 (NL_API_KEY 인증, 페이징)
        │
    parser.py                   ← JSON/XML 파서 + HTML 태그('<span class="highlight">') 자동 정제
        │
    models.py                   ← 통합 SeojiRecord / SearchResult 스키마
        │
   exporters.py                 ← xlsx / csv / json / sqlite 내보내기 도구
```

- **공통 코어 공유**: CLI(`nl-mcp`)와 MCP 서버(`server.py`)는 모두 `client.py`, `parser.py`, `models.py`, `exporters.py`를 공통으로 호출한다.
- **안전한 예외 차단 (`@_safe`)**: MCP 도구 계층에서 모든 HTTP 통신 오류나 파싱 오류를 캡처하여 프로토콜이 종료되지 않고 알림(`{"error": "..."}`) 형태로 반환한다.
- **가상환경 외부화**: 클라우드 동기화 폴더(`OneDrive`)에서 파일 잠금을 막기 위해 `UV_PROJECT_ENVIRONMENT` 환경변수로 외부 `~/.venvs/nl-openapi-mcp` 경로를 관리한다.

---

## 2. 통합 레코드 스키마 (`SeojiRecord`)

```python
class SeojiRecord:
    control_no: str       # 제어번호 / 분류 (예: "일반도서", "아동도서")
    title: str            # 표제 (HTML 하이라이트 태그 제거)
    author: str           # 저작자명
    publisher: str        # 발행자
    pub_year: str         # 발행년도
    seoji_year: str       # 수록연도
    isbn: str             # ISBN 또는 ISSN
    doc_yn: str           # 원문 유무 (Y/N/기타)
    page_info: str        # 형태사항 (예: "275 p. : 삽도 ; 29 cm")
    detail_url: str       # 상세페이지 전체 URL
    source: str = "seoji" # 출처 태그
    raw: dict             # 원본 응답 보존
```

---

## 3. 페이징 및 대량 수집 (`kci_collect` 호환 `nl_collect`)
- 국립중앙도서관 검색 API는 한 페이지당 `pageSize`(기본 10, 지정 가능)와 `pageNum` 파라미터를 갖는다.
- `nl_collect` 도구 및 CLI는 사용자가 요청한 `max_records`에 맞춰 여러 페이지를 연속 호출하며 중복 건을 병합한 뒤 원하는 포맷(`xlsx`, `csv`, `json`, `sqlite`)으로 출력한다.
