# 국립중앙도서관 국가서지 OpenAPI 가이드

> 국립중앙도서관 공식 안내서(`SEOJI_OPENAPI_GUIDE_v1.0.doc`) 및 라이브 API 호출 분석 결과 요약 문서.
> Base URL: `https://librarian.nl.go.kr/LI/search/openApi/seojiSearch.do`

---

## 1. 요청 파라미터 (Request Parameters)

### 기본 파라미터
| 파라미터명 | 타입 | 필수 여부 | 설명 |
|---|---|:--:|---|
| `key` | String | 필수 | 발급된 API 인증키 (예: `154bd36e...`) |
| `kwd` | String | 선택 | 일반검색 키워드 (`detailSearch`와 혼용 불가) |
| `pageNum` | Integer | 필수 | 현재 페이지 번호 (1부터 시작, 기본 1) |
| `pageSize` | Integer | 필수 | 페이지당 출력 건수 (기본 10, 최대 100 등) |
| `sort` | String | 선택 | 정렬 기준 (생략 시 정확도순) |
| `apiType` | String | 선택 | 응답 형식 (`json` 또는 `xml`, 본 도구는 `json` 기본) |

### 상세검색 파라미터 (`detailSearch=true`)
| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `detailSearch` | boolean | 상세검색 사용 유무 (`true` / `false`) |
| `f1` ~ `f5` | String | 검색 조건 항목 (`title`: 표제, `author`: 저자명, `publisher`: 발행자, `keyword`: 키워드, `isbn`: ISBN 등) |
| `v1` ~ `v5` | String | 검색어 |
| `and1` ~ `and4` | String | 논리 연산자 (`AND`, `OR`, `NOT`) |
| `seoji_year` | String | 수록연도 필터 |

### 정렬 파라미터 (`sort` 값 목록)
- `title_asc`: 제목 가나다순 (`ㄱ~ㅎ`)
- `title_desc`: 제목 역순 (`ㅎ~ㄱ`)
- `author_asc`: 저자 가나다순
- `author_desc`: 저자 역순
- `pub_asc`: 발행처 가나다순
- `pub_desc`: 발행처 역순
- `pubyear_asc`: 발행년도 과거순
- `pubyear_desc`: 발행년도 최신순

---

## 2. 응답 데이터 필드 (`result` 배열 내 항목)

| 필드명 | 타입 | 설명 | 참고사항 |
|---|---|---|---|
| `titleInfo` | String | 표제 | `<span class="highlight">` 등의 HTML 하이라이트 태그 포함 가능 |
| `authorInfo` | String | 저작자사항 | 저자명 및 소속 등 |
| `pubInfo` | String | 발행자사항 | 출판사/기관명 |
| `pubYearInfo` | String | 발행년도 | 연도 4자리 등 |
| `category` | String | 자료 분류 / 제어사항 | 예: 일반도서, 아동도서, 점자도서 |
| `seojiYear` | String | 국가서지 수록연도 | |
| `pageInfo` | String | 형태사항 | 페이지수 및 크기 등 |
| `detailUrl` | String | 상세페이지 상대 경로 | `/LI/contents/...` 형태 (파서가 전체 URL로 자동 변환) |

---

## 3. 에러 코드 안내
| 코드 | 메시지 | 설명 |
|---|---|---|
| `000` | SYSTEM ERROR | 서버 내부 오류 |
| `010` | NO KEY VALUE | 인증키 누락 |
| `011` | INVALID KEY | 유효하지 않은 API 키 |
| `012` | DATA LIMIT 500 | 페이지 조회 500건 초과 제한 |
| `101` | SEARCH ERROR | 검색 조건 혹은 검색 서버 오류 |
