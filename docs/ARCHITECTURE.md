# nl-openapi-mcp 아키텍처 및 설계 의도

> 국립중앙도서관 **소장자료 검색** OpenAPI(`www.nl.go.kr/NL/search/openApi/search.do`)를
> 검색·대량수집하는 공통 코어(REST + MCP + CLI) 아키텍처.
> 자매 프로젝트 `kci-openapi-mcp`·`scienceON-mcp` 와 레이어 구성을 맞춘다.

---

## 1. 레이어 구조

```
server.py / cli.py         ← MCP 도구 · CLI 표면 (@_safe · annotations)
        │
     client.py             ← HTTP · 페이징 · 재시도 · **절단 메타 산출**
        │
     parser.py             ← JSON 봉투 파싱 · HTML 하이라이트 제거 · 오류 → ParseError
        │
     models.py             ← Holding 스키마(실응답 24개 필드) · 발행연도 정규화 · 중복제거 키
        │
   exporters.py            ← xlsx / csv / json / sqlite
```

`config.py` 는 모든 층이 참조한다(엔드포인트 · `API_RECORD_CAP` · 자격증명 · `use_os_trust`).

---

## 2. 설계 결정과 그 이유

### 2-1. 절단은 **데이터가 아니라 메타로** 전달한다
`client.search_meta()` 는 `(records, meta)` 튜플을 돌려주고, `search()` 는 그 위의 얇은 래퍼다.
레코드만 반환하는 API 를 기본으로 두면 호출자가 `total` 을 볼 방법이 없어지고,
그 순간 **부분 집합을 전수로 오인**하는 사고가 난다(자매 프로젝트 2곳에서 실제로 발생).

`cap_hit` 과 `truncated` 를 **분리한 것이 핵심**이다. 처방이 다르기 때문이다:
- `truncated` → `max_records` 를 올리면 대개 해결
- `cap_hit` → API 가 500건까지만 준다. **올려도 해결 안 됨** → 검색식 분할 필요

### 2-2. 필터의 위치를 분명히 한다
`year_from`/`contains` 는 **로컬 후처리**다. 서버측 필터가 아니므로 500건 상한을 풀어주지 않는다.
이 성질은 회귀 테스트로 고정돼 있다 — 나중에 "연도를 걸면 되지 않나?" 로 되돌아가지 않도록.

### 2-3. 원본을 버리지 않는다
`Holding.raw` 에 24개 필드를 통째로 보존한다. 정규화는 손실 변환이고, 이 API 는
`orgLink` 에 URL 대신 안내문이 오는 등 **예외가 잦다**. json 내보내기도 `raw` 를 함께 싣는다.

### 2-4. 실패는 시끄럽게
- `server.py` 는 `mcp.server.fastmcp` 를 **조건부 import 하지 않는다** — 폴백을 두면
  의존성 상한 누락이 감춰지고 반쯤 동작하는 서버가 뜬다(v0.1.0 의 실제 결함).
- `parser` 는 `result` 키 부재를 **오류로 본다** — 빈 목록 통과는 인증키 오류를 '0건'으로 둔갑시킨다.
- 반대로 **MCP 도구 경계에서는 조용하게**: `@_safe` 가 모든 예외를 dict 로 바꾼다.
  프로토콜 밖으로 예외가 새면 클라이언트가 깨진다.

### 2-5. 인증키는 예외 메시지에도 남기지 않는다
`raise_for_status()` 를 쓰지 않는다 — requests 가 **키가 든 전체 URL 을 메시지에 박기** 때문이다
(v0.1.0 의 실제 누출 경로). 상태코드만 보고한다.

### 2-6. TLS 는 코드에서 처리한다
`config.use_os_trust()` 를 `NlClient.__init__` 에서 호출한다. MCP 등록 명령줄에 두면
`.mcpb` 번들·PyInstaller 바이너리 경로에 적용되지 않아 교육망에서 실패한다
(scienceon 이 이 함정에 빠졌다). 검증을 끄지 않고 OS 신뢰저장소를 쓴다.

### 2-7. venv 는 클라우드 폴더 밖
OneDrive 동기화 폴더 안의 venv 는 파손된다(실제로 자매 프로젝트 3곳 모두 `pyvenv.cfg` 의 home 이
**존재하지 않는 사용자 프로필**을 가리키는 상태로 발견됐다).
`UV_PROJECT_ENVIRONMENT` 로 외부 경로를 지정한다 — 환경변수 전용이라 pyproject 로는 지정 불가.

---

## 3. 통합 레코드 스키마 (`Holding`)

실응답 24개 필드 → 정규화 25개 컬럼. 전체 표·결측률 → [NL_API_GUIDE.md §2](NL_API_GUIDE.md).

```python
class Holding:
    record_id: str      # id — 전건 존재 → 중복제거 1차 키
    control_no: str     # controlNo — 온라인자료엔 없음(31.0% 빈값)
    title: str          # titleInfo (HTML 하이라이트 제거)
    authors: str        # authorInfo — "역할: 이름" 을 ';' 로 연결한 원문
    pub_info: str       # pubInfo — 발행지·발행처·발행년 결합 문자열
    pub_year: str       # 4자리 정규화 (+ pub_year_raw 로 원문 보존)
    type_code: str      # B1=인쇄자료 / D1=온라인자료
    kdc_code / kdc_name / class_no / call_no
    doc_type: str       # docYn — ⚠️ 불리언 아님(NL_VIEWER/LD_VIEWER/FILE/LINK/N)
    lic_code / lic_text # licYn — ⚠️ 불리언 아님(L/F/S/D/N/Y)
    detail_url / image_url / org_link
    raw: dict           # 원본 24개 필드
```

중복제거 키는 `id:` → `cn:` → `isbn:` → `tt:` 순으로 **키스페이스를 분리**한다
(항상 `str` 을 반환해 우연한 충돌을 막는다).

---

## 4. 대량 수집 흐름

```
nl_collect(terms=[…])
   → 검색어별 search_meta()            … 각각 최대 500건(API 상한)
   → id 기준 합집합                     … axes[] 에 축별 total·fetched·new 기록
   → 연도·contains 로컬 후처리          … 필터링 건수를 meta 에 집계
   → exporters.export()                … xlsx/csv/json/sqlite
   → meta.cap_hit_terms 로 상한 검색어 지목
```

**변형어별 개별검색 후 합집합**을 쓰는 1차 이유는 500건 상한이다 — 검색어를 쪼개면 조각마다
한도를 새로 받는다. 2차 이유는 `kwd` 안에서 OR 을 표현하는 문법이 API 에 있는지 확인되지 않았다는 점이다.

> ⚠️ **정정(2026-08-12)**: 초판에는 "검색식에 OR 연산자가 없다"고 적었으나, 이는 자매 프로젝트
> KCI 에서 검증된 사실을 국립중앙도서관에 **근거 없이 옮긴 것**이었다. 실제 고급검색 UI 에는
> 필드 간 **AND/OR/NOT** 선택과 **발행년 범위** 필터가 있다. API 가 이를 노출하는지는 미검증이며,
> 노출한다면 합집합 전략보다 나은 경로가 생긴다 → `scripts/probe_api.py` 참조.
