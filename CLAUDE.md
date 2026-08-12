# nl-openapi-mcp — 프로젝트 지침

> **국립중앙도서관(NL) 소장자료 검색** OpenAPI 수집기. 공개 **MCP 서버 + CLI**.
> 자매 프로젝트 **kci-openapi-mcp**(`../KCI openAPI`) · **scienceON-mcp**(`../scienceon`)와 동일 아키텍처.
> API 규격 → [docs/NL_API_GUIDE.md](docs/NL_API_GUIDE.md) · 이력 → [docs/작업일지.md](docs/작업일지.md)

## 1. 목표
연구 초반 **자료수집 단계**에서 반복 재사용하는 도구. 국립중앙도서관 소장자료(단행본·온라인자료)의
서지·KDC 분류·청구기호·원문 제공 여부를 검색·수집해 후속 분석 입력 데이터를 안정적으로 생산한다.
KCI·ScienceON(학술논문)과 **상호보완**: 이쪽은 **단행본·회색문헌** 축을 담당한다.

## 2. 확정 결정사항
| 항목 | 결정 |
|------|------|
| 언어/런타임 | Python 3.10+ |
| 패키지 관리 | **uv** (pyproject + uv.lock). venv는 **클라우드 폴더 밖** `C:/Users/user/.venvs/nl-openapi-mcp` (`UV_PROJECT_ENVIRONMENT`, `.claude/settings.local.json` 에 지정) |
| 의존성 | mcp(FastMCP, **`<2` 상한 필수**), requests, openpyxl, python-dotenv, truststore |
| 인터페이스 | 공용 코어 + **MCP 서버(server.py)** + **CLI(cli.py)** |
| 대상 API | **소장자료 검색** `www.nl.go.kr/NL/search/openApi/search.do` (JSON) |
| 출력 | xlsx · csv · json · sqlite |
| 공개 | MIT. `.env`·`.claude/settings.local.json`·`output/` 는 gitignore |

## 3. 구조
```
src/nl_mcp/
  config.py     # .env 로딩, 엔드포인트, API_RECORD_CAP(500), use_os_trust()
  models.py     # Holding 스키마(실응답 24개 필드 기반) + 발행연도 정규화
  parser.py     # JSON 봉투 파싱 · HTML 하이라이트 제거 · 오류코드 → ParseError
  client.py     # 검색/페이징/재시도 + search_meta(절단 노출) + search_terms_meta(합집합)
  exporters.py  # xlsx/csv/json/sqlite
  server.py     # MCP 도구: nl_status / nl_search / nl_collect
  cli.py        # status / search / collect
docs/           # NL_API_GUIDE.md(★ 실측 스키마·500 상한) · 작업일지.md · ARCHITECTURE.md
tests/          # samples.py = **실응답 발췌** + 파서·절단·서버·내보내기 회귀 66건
packaging/binary/  # PyInstaller 자체완결 바이너리용 entry + manifest
```

## 4. 자격증명
- 변수: `NL_API_KEY` (www.nl.go.kr 오픈API 신청으로 발급). **토큰/AES/공인IP 등록 불필요** — 평문 key 쿼리.
- `NL_OS_TRUST` (기본 1): 교육망·사내망 SSL 인터셉션 대응. 0 이면 비활성.
- ⚠️ 인증키는 코드/로그/커밋 금지 — `.env`(gitignore) 또는 `.claude/settings.local.json` env 로만.

## 5. MCP 도구
| 도구 | 설명 |
|------|------|
| `nl_status` | 인증키 유효성 + 소장자료 검색 API 실제 왕복 1회 |
| `nl_search` | 소장자료 검색. `total`·`truncated`·**`cap_hit`** 동반 반환 |
| `nl_collect` | 검색어 합집합 수집 → xlsx/csv/json/sqlite. `meta.cap_hit_terms` 로 상한 검색어 지목 |

## 6. 핵심 기술사실 (2026-08-12 라이브 실측 — 약 150회 호출로 확정)
### (A) ⚠️ 500건 상한 — 이 API 의 지배적 제약
오류코드 **012 DATA LIMIT 500**. 실측: `교육복지` total=1,856 → 회수 **500건**.
**기준은 레코드 오프셋**이다(pageSize=10→51페이지, pageSize=100→6페이지, 둘 다 누적 500).
따라서 같은 검색식으로는 페이지네이션으로 501번째에 도달할 수 없다.
현재 코드가 쓰는 수단은 **`category`→`manageName`→`licYn` 재귀 분할** · 검색어 세분화 · `exact`.
🔴 **정정(2026-08-12 재검증)** — "정렬 뒤집기 불가"는 **틀렸다**. 아래 두 축이 실측으로 동작하며
현행보다 효율이 높다. **아직 미구현.**
- **정렬 뒤집기** `sort=ipub_year|ititle|iauthor|ipublisher|iregdate` + `order=asc|desc`.
  asc ∩ desc = **0건**. 1,856건 질의를 **7요청으로 94%** 회수(현행 깊이3 은 7,028건에 60요청 67%).
- **f-슬롯 불리언** `detailSearch=true&f1=&v1=&and1=AND|OR|NOT&f2=&v2=`.
  f-슬롯은 `srchTarget`/`kwd` 와 **등가**(total·첫 행 일치), `AND+NOT=부모` **검산 통과**(4/4).
  → `licYn` 처럼 새지 않는 **정확한 재귀 이분할**이 가능하다.
🔴 **연도 필터도 존재한다**(3차 정정) — `ipub_year=2020` 형태. `sort` 와 똑같이 `i` 접두
색인 필드명이었고 초판 후보 11개에 그 이름이 없었다. **같은 실수 패턴 네 번째 재발.**
단일 연도만 되고(범위 ✗) 발행년 빈 레코드는 샌다(−4.5%). 다만 **모든 연도 셀이 500 미만**이라
분할 축으로 강력하다. ⚠️ f-슬롯에는 연도 필드가 없다(미지 필드명은 무시되고 토큰 AND 가 된다).

### (A-2) 🔴 검색은 제목 부분일치가 아니라 토큰 매칭 + 적합도 정렬
`교육불평등` 은 `교육`·`불평등` 으로 쪼개져 둘 중 하나만 든 제목도 회수된다.
**큰따옴표 구문검색이 동작한다**(`exact=True`) — 유일하게 해석되는 검색 문법이다.
🔴 그러나 **코퍼스 수집에 쓰면 안 된다**: 재현율 손실 평균 47% · 최악 84%(교육형평성 31→5건)이고
버려진 것의 76%가 관련 문헌이다. 한국어 복합어가 표제에서 조사로 갈라지는데(`교육의 형평성`)
구문검색은 인접을 요구하기 때문. 변형어를 늘려도 회복되지 않는다(12/31). → 기본값 `False` 유지.
AND/OR/NOT 은 연산자가 아니라 그냥 토큰이다(`kwd=AND` 단독 검색이 451,670건).

### (A-3) 🔴 `srchTarget` 미지원 값은 조용히 전 필드 검색으로 폴백
지원: `title`·`author`·`publisher`·`keyword`·`total`.
폴백: `isbn`·`classNo`·`callNo`·`subject`·오타 — **오류가 나지 않는다**.
판별 근거: `srchTarget=isbn&kwd=오욱환`(저자명)이 0건이 아니라 total 과 같은 36건.

### (A-4) 🔴 결과 0건이면 `result` 키가 아예 없다
`{"total":0,"kwd":…,"pageNum":…,"pageSize":…,"category":…,"sort":""}`.
오류가 아니라 정상적인 빈 결과다. 단 `total>0` 인데 `result` 가 없으면 레코드 누락이므로 오류다.

### (A-5) `pageSize` 상한은 500 (1000 은 거부)
초판이 100 으로 잡아 상한까지 5회 호출하던 것이 **1회**로 줄었다.

### (B) ⚠️ `docYn`·`licYn` 은 불리언이 아니다
이름은 `…Yn` 이지만 실제로는 열거코드다.
`docYn` = `NL_VIEWER`·`LD_VIEWER`·`FILE`·`LINK`·`N` / `licYn` = `L`·`F`·`S`·`D`·`N`·`Y`.
실측 1,124건에 `docYn="Y"` 는 **한 건도 없다** — Y/N 으로 가정했으면 전건 오판이었다.

### (B-2) 하이라이트 마크업은 `class="searching_txt"`
매칭 **토큰마다** span 이 붙고 `titleInfo`·`pubInfo` 등 여러 필드에 실린다.
태그를 지우면 토큰 사이 공백이 남으므로 제목 비교 시 공백 정규화가 필요하다.

### (C) 필드 결측은 정상이다
`controlNo` 31.0%, `isbn` 54.1%, `callNo`·`classNo` 54.4%, `imageUrl` 67.4% 가 빈 문자열이다
(대부분 온라인자료 `typeCode=D1`). **`id` 는 전건 존재**하므로 중복제거 1차 키로 쓴다.
`pubYearInfo` 는 4·6·8·9~14자리가 섞여 오므로 정규화 없이 쓰면 깨진다.

### (D) 서비스 구분
`search.do`(소장자료, 본 패키지) ≠ `seojiSearch.do`(서지정보, v0.1.0 까지) ≠ 정보나루(별개 서비스).

## 7. 개발 원칙
- 자격증명은 `.env`/MCP env 블록으로만. **`raise_for_status()` 금지** — 인증키가 든 URL 을 예외에 박는다.
- 정중한 호출: throttle(기본 0.4s), 지수 백오프, 페이지네이션 안전장치(새 레코드 0이면 종료).
- 원본 24개 필드는 `raw` 로 보존. 커밋 메시지 한국어, Claude 서명 금지.
- **라이브 검증 우선(추정 금지)** — 필드명·값은 실응답을 떠서 확정한다. 문서에 검증 등급(✅📄❓)을 표기.

## 8. 상태 (2026-08-12)
- 🔬 **자매 프로젝트 역방향 대조 완료** — 이 저장소의 교훈을 kci·scienceON 으로 보낸 뒤,
  **반대로 그쪽에서 나온 결함이 여기에도 있는지** 훑었다. 결과가 갈렸다.
  **이미 막혀 있던 것** — 인증키 URL 누출(`raise_for_status` 미사용), 출력 경로 이탈(`safe_name`),
  요청 크기 하한(`max(1, …)`), `_safe`·annotations. 이쪽이 먼저 발견해 고친 것들이다.
  **이식한 것 4종**
  ① **마지막 검색어가 상한을 채우면 `stopped_early` 오탐** — 남은 축이 없는데 조기 중단으로
     표시돼 전수 수집 코퍼스에 절단 경고가 붙는다. `term is not terms[-1]` 로 판정.
  ② **전송 선택** — `mcp.run()` 이 인자 없이 호출돼 stdio 전용이었다. `--transport
     stdio|sse|streamable-http` + `--host`/`--port`(환경변수 `NL_MCP_*` 도 지원).
     ⚠️ 기본은 stdio 로 못박는다 — 바뀌면 기존 등록이 전부 죽는다. 회귀 테스트로 고정.
  ③ **`__version__` 하드코딩** → `importlib.metadata` 조회(릴리스마다 어긋나는 것 방지).
  ④ **워크플로 보안** — `${{ github.ref_name }}` 이 run 블록에 직접 보간되던 스크립트 주입 패턴을
     env 경유로 바꾸고, `ci.yml`·빌드 job 에 `contents: read` 최소 권한 명시.
  **이식하지 않은 것** — kci·scienceON 의 `truncated`/`total_mismatch` 분리는 **넣지 않았다.**
  그 분리는 "API 가 `total` 을 실제 서빙량보다 크게 보고한다"는 현상 때문인데, **NL 은 라이브
  실측 결과 그렇지 않았다**(느린학습자 230/230, 경계선지능 464/464 정확 일치. 500 초과는 이미
  `cap_hit` 으로 구분됨). ⚠️ **방법론은 옮기되 API 동작 사실은 각자 실측한다** — §7 원칙 그대로.
  테스트 162 → **176**(전 모듈 임포트·전송 선택 회귀 포함).
- ✅ **v0.2.0 — 서지정보 → 소장자료 검색 교체.** v0.1.0 은 `seojiSearch.do` 를 썼으나
  **최신 소장본이 검색되지 않아** 대상 API 를 교체했다. 응답 스키마가 전혀 달라 코어 전체 재작성.
  도구도 4종(`nl_detail` 포함) → 3종으로 정리했다(소장자료 검색에는 상세조회 엔드포인트가 없다).
- 🔴 **v0.1.0 은 사실상 기동 불능이었다** — `mcp>=1.2.0` 에 **상한이 없어** mcp 2.0 으로 해석되고,
  2.0 은 `mcp.server.fastmcp` 를 제거했다. **자매 프로젝트 두 곳이 이미 겪고 고친 바로 그 버그**가
  세 번째로 반복됐다. `>=1.2.0,<2` 로 고정. 게다가 v0.1.0 의 `server.py` 는
  `except ImportError` 폴백을 두어 **반쯤 동작하는 서버가 조용히 뜨게** 돼 있었다 — 폴백도 제거했다.
- 🔴 **인증키 URL 누출** — v0.1.0 클라이언트가 `resp.raise_for_status()` 를 써서 실패 시
  **인증키가 든 전체 URL 이 예외 메시지에 실렸다**. 상태코드만 보고하도록 교체.
- 🔴 **조용한 절단** — v0.1.0 의 `nl_collect` 는 `{count, output_path}` 만 반환해 500건 상한에
  걸려도 알 방법이 없었다. `search_meta`/`search_terms_meta` 로 `total`·`truncated`·`cap_hit` 노출.
- 🟡 **truststore 정식 의존성화** + `NL_OS_TRUST` — v0.1.0 에는 아예 없었다(교육망에서 실패).
  MCP 등록 명령줄이 아니라 **코드**(`config.use_os_trust()`)에서 호출해 `.mcpb`·바이너리 경로도 덮는다.
- 🟡 **계정명 `rubato103` → `rubatoyd`** 전량 교체(pyproject·server.json·manifest·README·client UA).
  레지스트리 네임스페이스도 `io.github.rubatoyd/nl-openapi-mcp` 로 이관.
- 🟡 **MCP annotations** 선언(readOnly/openWorld/destructive) — v0.1.0 에는 없었다.
- ⚠️ **라이브 미검증 상태로 배포** — 2026-08-12 현재 `www.nl.go.kr`(124.137.58.36) 이
  **TCP 443·80 모두 접속 불가**(DNS 는 정상, KCI·PyPI·Google 은 0.04초 연결).
  샌드박스 문제가 아니다(비샌드박스·PowerShell 에서도 동일). 따라서 이번 판은
  **2026-08-11 수집한 실응답 1,124건**으로만 확정했다. 접속 복구 시 §6 의 ❓ 항목 실측 필요.
- ⚠️ **프로젝트 내 `.venv/` 파손** — `pyvenv.cfg` 의 home 이 **없는 사용자 프로필**
  `C:\Users\rubat\…`(OneDrive 로 유입된 타 PC 산출물)를 가리켰다. 자매 프로젝트 2곳과 동일 증상.
  삭제 후 `C:/Users/user/.venvs/nl-openapi-mcp` 로 이관.
- ℹ️ **기동 시 stderr 경고는 무해하다(오진 주의)** — `pydantic_settings … IncompleteFieldDefinitionWarning:
  Field 'lifespan' has an incomplete definition`. pydantic-settings 2.14+ 의 경고이고 대상은
  mcp SDK 의 FastMCP `Settings` 모델이다(우리 코드 아님). **핀하지 않는다** — 직접 쓰지 않는
  전이 의존성을 묶으면 상류가 고친 뒤에도 사용자를 낡은 버전에 잡아둔다. 자매 프로젝트와 동일 판단.
- ⚠️ **액션 버전: 이동 태그 유무를 구분할 것** — `astral-sh/setup-uv` 는 **이동 메이저 태그가 없다**.
  2026-08-12 `gh api …/git/ref/tags/v9` 로 **부재 재확인** → `@v9.0.0` 정확 고정.
  `actions/*`(checkout v7·setup-python v7·upload-artifact v7·download-artifact v8·setup-node v7)는
  이동 태그가 살아 있음을 같은 방법으로 확인했다.
- ✅ **v0.2.0 발행 완료 (2026-08-12)** — 태그 푸시로 워크플로 4개 job 전부 통과.
  릴리스 자산 4종(경량 1.2KB + win 23.5MB · macos 22.1MB · linux 37.6MB 자체완결).
  **sha256 무결성 확인** — `server.json` 주입값이 실제 자산 해시와 일치.
  **콜드 스타트 실검증** — `uvx --refresh --from git+…@v0.2.0` 로 기동·도구 3종 확인.
  ⚠️ 레지스트리는 `mcp-publisher` 가 성공 보고했으나 **독립 확인은 못 했다** —
  `registry.modelcontextprotocol.io` 가 이 망에서 접속 불가(교육망 egress 필터).
- 🔴 **적대적 검증이 결함 4종을 잡았다** — 로컬 HTTP 서버로 실제 왕복을 태워 반복 호출
  (9,282검사 중 29실패): `resultCode` 거짓 양성 · 호출 폭주(499회) · fetched/returned 혼동 ·
  출력 경로 이탈(`name="../x"`). `_call` monkeypatch 테스트는 이 층을 건너뛴다.
- 🔴 **라이브 실측이 결함 2종을 더 잡았다** — 0건 응답을 오류로 처리하던 것(이 API 는 0건이면
  `result` 키를 뺀다) · `pageSize` 상한을 100 으로 오판하던 것(실제 500 → 호출 5회가 1회로).
- ✅ **레지스트리 발행 확인** — `io.github.rubatoyd/nl-openapi-mcp v0.2.0 status:active`,
  `fileSha256` 가 실제 자산 해시와 일치(망 밖 경로로 조회).
  ⚠️ 구 네임스페이스 `io.github.rubato103/…` v0.1.0 도 **active 고아로 남는다**(회수 불가, kci 동일).
- ✅ **다축 재귀 분할 수집** (`nl_collect(auto_partition=True, partition_depth=1~3)`) —
  500 상한 부분 우회. 서버측 축은 실측 탐색으로 셋만 확인됐다:
  `category`·`manageName`(완전분할) · `licYn`(값이 빈 레코드는 못 잡음).
  `kdcCode1s`·`typeCode`·`docYn`·`regDate`·`lang` 등 나머지는 전부 무시된다.
  ⚠️ 이름 대칭 가정 금지 — `kdcCode1s`는 무시되나 `kdcName1s`는 동작, `licYn`은 되나 `docYn`은 안 됨.
  **부모 조각도 합집합에 넣어** 불완전한 축을 써도 손해가 없게 했다.
  실측(교육복지 7,028): 500(7%) → 깊이1 2,134(30%) → 깊이2 3,265(46%) → 깊이3 4,722(67%).
  요청 수는 13→25→60. 전수는 여전히 불가.
- ✅ **자체완결 바이너리 클린 검증** — win-x64 `.mcpb` 를 Python·uv 없는 환경(`env -i`)에서
  직접 실행: 기동·도구 3종·**실제 HTTPS 왕복**(total 82,769) 성공, truststore 경고 0건.
  cwd 를 프로젝트 밖에 두어 `.env` 유입이 없음도 확인(`has_api_key:false`).
- ✅ **코드 리뷰(PR #1) 지적 5건 반영 → v0.4.1** — 전부 재현·수정했다.
  🔴 도구 기본값(`max_records=500`)에서 `auto_partition` 이 **아무 일도 안 하던 것**(대표 기능이
  기본 설정에서 죽어 있었다) · 🔴 경고 꼬리가 **잘못된 키**(`capped_categories`)를 조회해
  '전수가 아니다'가 한 번도 안 붙던 것(**이 프로젝트가 막겠다고 한 조용한 절단**) ·
  CLI 인자 3종 부재(공용 코어 원칙 위반) · `walk()` 이 재귀 깊이와 축 인덱스를 한 변수로 써서
  preset 축에서 재귀가 종료되던 것 · 루트 요청 중복.
  라이브 확인: 기본값 호출 500 → 3,265건. 회귀 7건 추가(155 → 162).
  > 교훈: **키 이름 오타 하나가 안전장치를 통째로 무력화**했다. 경고 문자열은 테스트가 잘
  > 닿지 않는데 이 프로젝트의 존재 이유가 바로 그 경고다 — 이제 회귀로 고정했다.
- ✅ **교훈을 자매 프로젝트로 이관 (2026-08-12)** — kci `CLAUDE.md §7-1`, scienceon `CLAUDE.md §7`.
  방법론(대리 지표 금지·부재 증명의 대조군·실제 HTTP 왕복 하네스·경고 문자열 회귀)만 옮기고
  **API 사실은 옮기지 않았다** — 이번 세션에서 정반대 실수를 했기 때문이다.
  🔴 이관 과정에서 **양쪽 저장소에 출력 경로 이탈 결함이 그대로 있음을 실측 확인**했다
  (`name="../escaped"` 가 `out_dir` 밖에 기록). ✅ **이후 양쪽 모두 수정됨**(kci `4dcd02e`,
  scienceon `cc003fd`) — 재검증에서 6종 케이스 전부 봉쇄 확인. 회귀 테스트도 각각 추가됐다.
- ⏭️ 다음: ① 구 네임스페이스 고아 항목(`io.github.rubato103/…` v0.1.0) 회수 불가 — 기록만 유지
  → ② 깊이 3의 60회 요청은 정중함의 한계선 — 필요시 throttle 상향 검토
  → ③ 자매 2곳의 경로 이탈 결함 수정 여부는 각 저장소에서 별도 판단.
