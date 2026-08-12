# nl-openapi-mcp

<!-- mcp-name: io.github.rubatoyd/nl-openapi-mcp -->

[![CI](https://github.com/rubatoyd/nl-openapi-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/rubatoyd/nl-openapi-mcp/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/rubatoyd/nl-openapi-mcp)](https://github.com/rubatoyd/nl-openapi-mcp/releases/latest)

**국립중앙도서관 소장자료 검색** OpenAPI 를 Claude 등 MCP 클라이언트에서 바로 쓰는 서버 + CLI.
단행본·온라인자료의 서지, KDC 분류, 청구기호, 원문 제공 여부를 검색·수집하고
xlsx/csv/json/sqlite 로 내보냅니다.

자매 프로젝트: [kci-openapi-mcp](https://github.com/rubatoyd/KCI_openAPI)(학술논문·인용지수) ·
[scienceON-mcp](https://github.com/rubatoyd/scienceON-mcp)(KISTI 문헌)

---

## 이 도구가 특별히 신경 쓰는 것 — 조용한 절단 방지

국립중앙도서관 검색 API 는 **한 검색식당 500건까지만** 돌려줍니다(공식 오류코드 `012 DATA LIMIT 500`).
그런데 `total` 은 그보다 큰 값을 태연히 보고합니다.

```
교육복지: total=1,856  →  실제로 받을 수 있는 건 500건
```

**이 사실을 모르면 부분 집합을 전수로 오인**하게 됩니다. 그래서 모든 응답에
`total`·`truncated`·`cap_hit` 을 함께 싣고, 상한에 걸리면 처방까지 문장으로 알려줍니다.

| 신호 | 뜻 | 처방 |
|---|---|---|
| `truncated` | 이번 호출이 `total` 보다 적게 받음 | 대개 `max_records` 를 올리면 해결 |
| `cap_hit` | `total` > 500 — **API 가 더 안 줌** | `max_records` 로는 불가 (아래 참조) |
| `meta.cap_hit_terms` | 상한에 걸린 검색어 목록 | 그 검색어만 세분화 |

### 상한을 넘겨 모으는 두 가지 방법

**① `auto_partition=True` — 서버측 축으로 재귀 분할**

응답 필드명을 파라미터로 넘겨보는 방식으로 실제 동작하는 축 3개를 찾았습니다:
`category` → `manageName`(둘 다 완전분할) → `licYn`. 상한에 걸린 조각만 다음 축으로 더 쪼개고,
**부모 조각도 합집합에 넣어** 불완전한 축을 써도 손해가 나지 않게 했습니다.

`교육복지`(전체 7,028건) 실측:

| 깊이 | 축 | 회수 | 비율 | 요청 |
|---:|---|---:|---:|---:|
| — | 분할 없음 | 500 | 7% | 1 |
| 1 | `category` | 2,134 | 30% | 13 |
| 2 | `+manageName` (기본) | 3,265 | 46% | 25 |
| 3 | `+licYn` | **4,722** | **67%** | 60 |

`partition_depth`(1~3)로 조절합니다. ⚠️ 전수는 아니며 — 깊이 3에서도 33%가 남습니다 —
못 받은 건수는 `meta.axes[].partition.unreachable` 로 보고합니다.

**② `exact=True` — 큰따옴표 구문검색 (⚠️ 넓게 모을 때는 쓰지 마세요)**

`total` 자체가 줄어들어(교육불평등 63 → 28) 상한 아래로 내려갈 수 있습니다. 다만
**재현율 손실이 큽니다** — 실측 평균 47%, 최악 84%(교육형평성 31 → 5건). 구문검색은 토큰
인접을 요구하는데 한국어 복합어는 표제에서 조사·수식어로 갈라지기 때문입니다
(`교육의 형평성`, `초중등교육의 형평성과`). 버려진 것의 76%가 관련 문헌이었습니다.

→ **코퍼스 수집은 기본 검색 + `contains` 후처리**, `exact` 는 전체 표제를 아는 특정 자료 조회용.

> ⚠️ `year_from`/`contains` 는 **이미 받은 레코드에 대한 후처리**라 상한을 풀어주지 않습니다.
> **서버측 연도 필터와 정렬은 존재하지 않습니다**(각각 11개·28개 조합으로 부재 확인).
> 자세한 내용 → [docs/NL_API_GUIDE.md §3](docs/NL_API_GUIDE.md)

---

## 설치

### 1) Claude Code / Claude Desktop (uvx — 권장)

```json
{
  "mcpServers": {
    "nl": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/rubatoyd/nl-openapi-mcp", "nl-mcp"],
      "env": { "NL_API_KEY": "발급받은_인증키" }
    }
  }
}
```

### 2) Claude Desktop `.mcpb` 원클릭

[Releases](https://github.com/rubatoyd/nl-openapi-mcp/releases) 에서 내려받아 실행합니다.
Python·uv 가 없는 환경이면 OS별 **자체완결 번들**(`-win-x64` / `-macos-arm64` / `-linux-x64`)을 쓰세요.

### 3) 로컬 개발

```bash
git clone https://github.com/rubatoyd/nl-openapi-mcp
cd nl-openapi-mcp
uv sync
uv run pytest -q
```

> 클라우드 동기화 폴더(OneDrive 등)에서 작업한다면 venv 를 **폴더 밖**에 두세요:
> `UV_PROJECT_ENVIRONMENT=~/.venvs/nl-openapi-mcp`

---

## 인증키

[www.nl.go.kr](https://www.nl.go.kr) 오픈API 신청으로 발급받아 `NL_API_KEY` 로 설정합니다.
토큰 발급·AES 암호화·공인IP 등록이 **필요 없습니다**(평문 key 쿼리 파라미터).

```bash
cp .env.example .env   # NL_API_KEY 를 채워 넣으세요 (.env 는 gitignore 됩니다)
```

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| `NL_API_KEY` | (필수) | 국립중앙도서관 오픈API 인증키 |
| `NL_OS_TRUST` | `1` | 교육망·사내망 SSL 인터셉션 대응(OS 신뢰저장소 사용). `0` 이면 비활성 |

> 학교·교육청·사내망은 자체서명 루트 CA로 TLS를 가로챕니다. 이 도구는 **검증을 끄지 않고**
> `truststore` 로 OS 신뢰저장소를 사용해 통과합니다.

---

## MCP 도구

| 도구 | 설명 |
|---|---|
| `nl_status` | 인증키 유효성 + API 실제 왕복 1회 점검 |
| `nl_search` | 소장자료 검색 (`total`·`truncated`·`cap_hit` 동반) |
| `nl_collect` | 검색어 **합집합** 수집 → 파일 저장. `save=false` 면 미리보기만 |

### 예시

> "국립중앙도서관에서 '교육불평등', '교육격차', '학력격차' 관련 단행본을 모아서 xlsx로 저장해줘"

`nl_collect` 가 세 검색어를 각각 조회해 `id` 기준으로 합집합을 만들고, 상한에 걸린 검색어가
있으면 `meta.cap_hit_terms` 로 지목합니다.

---

## CLI

```bash
nl status
nl search 교육불평등 --category 도서 --rows 20
nl collect --terms 교육불평등 교육격차 학력격차 --category 도서 --format xlsx json

# 500 상한을 넘겨 모으기 (MCP 의 auto_partition 과 동일)
nl collect --kwd 교육복지 --auto-partition --partition-depth 3 --format xlsx
```

---

## 응답 필드

정규화 25개 컬럼 + 원본 24개 필드(`raw`) 보존. 전체 표와 결측률은
[docs/NL_API_GUIDE.md §2](docs/NL_API_GUIDE.md) 참조.

**주의할 필드 2가지** — 이름이 `…Yn` 이지만 **불리언이 아닙니다**:

- `docYn` → `doc_type`: `NL_VIEWER` · `LD_VIEWER` · `FILE` · `LINK` · `N`
- `licYn` → `lic_code`: `L` · `F` · `S` · `D` · `N` · `Y`

원문 보유 판정은 `Holding.has_fulltext()` 를 쓰세요(`"N"`·빈값만 거짓).

---

## 검증 상태

- ✅ 응답 스키마 24개 필드 — **실응답 1,124건** 전수 집계로 확정
- ✅ 500건 상한 — 공식 오류코드 + 실제 수집 로그로 확인
- ✅ 오프라인 회귀 66건 · MCP stdio 핸드셰이크 · CI 콜드 스타트 스모크
- ❓ `srchTarget` 의 `title` 외 값, `sort`, 오류 응답 키 철자 — **라이브 미검증**
  (2026-08-12 현재 `www.nl.go.kr` 접속 불가). 코드는 이 항목들에 의존하지 않습니다.

---

## 라이선스

MIT
