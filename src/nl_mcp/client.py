"""국립중앙도서관 소장자료 검색 API 클라이언트.

호출: `search.do?key=<인증키>&apiType=json&srchTarget=…&kwd=…&pageNum=…&pageSize=…` (GET, JSON/UTF-8)

**조용한 절단이 이 API 의 핵심 위험**이다. 한 검색식당 500건까지만 내려주는데
(공식 오류코드 012 "DATA LIMIT 500"), `total` 은 그보다 큰 값을 태연히 보고한다.
실측: `교육복지` total=1,856 → 실제 회수 500건. 이 클라이언트는 total 을 절대 버리지 않고
`search_meta()` 로 절단 사실을 호출자에게 강제로 노출한다.
"""
from __future__ import annotations

import time

import requests

from .config import (
    API_RECORD_CAP,
    MAX_PAGE_SIZE,
    SEARCH_API_URL,
    require_api_key,
    use_os_trust,
)
from .models import Holding
from .parser import ParseError, parse_search_response


class NlError(RuntimeError):
    """네트워크·HTTP·응답 오류. 메시지에 인증키가 절대 들어가지 않는다."""


class NlClient:
    def __init__(self, api_key: str | None = None, *, throttle: float = 0.4,
                 timeout: int = 30):
        use_os_trust()  # 교육망/사내망 SSL 인터셉션 CA를 OS 저장소로 신뢰(검증 유지)
        self.api_key = api_key or require_api_key()
        self.throttle = throttle
        self.timeout = timeout
        self.session = requests.Session()
        # ⚠️ 기본 UA 를 그대로 쓰지 않는다 — 자매 프로젝트 KCI 에서 공공기관 방화벽이
        #    User-Agent 로 차단하는 사례를 확인했다(curl 기본 UA 는 400, 브라우저 UA 는 200).
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; nl-openapi-mcp)",
            "Accept": "application/json",
        })

    # ── 저수준 호출 ───────────────────────────────────────────────────────────
    def _call(self, params: dict) -> str:
        """GET 1회(재시도 포함). 예외 메시지에 인증키가 실리지 않도록 URL 을 절대 노출하지 않는다."""
        query = {"key": self.api_key, "apiType": "json"}
        query.update({k: v for k, v in params.items() if v not in (None, "")})
        last_exc: Exception | None = None
        r = None
        for attempt in range(3):
            try:
                r = self.session.get(SEARCH_API_URL, params=query, timeout=self.timeout)
            except requests.exceptions.RequestException as e:
                last_exc = e
                if attempt < 2:
                    time.sleep(1.5 * (2 ** attempt))
                    continue
                raise NlError(
                    f"네트워크 오류({type(e).__name__}) — www.nl.go.kr 연결/SSL 을 확인하세요. "
                    f"교육망·사내망이면 NL_OS_TRUST=1(기본)로 OS 신뢰저장소를 씁니다."
                ) from None
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(1.5 * (2 ** attempt))
                continue
            break
        if r is None:  # pragma: no cover
            raise NlError(f"요청 실패({type(last_exc).__name__ if last_exc else 'unknown'}).")
        if r.status_code == 429:
            raise NlError("요청 한도 초과(429) — throttle 을 올리거나 잠시 후 재시도하세요.")
        if r.status_code >= 400:
            # ⚠️ raise_for_status() 는 **인증키가 든 전체 URL 을 예외 메시지에 박는다**. 쓰지 않는다.
            raise NlError(f"HTTP {r.status_code} — 국립중앙도서관 서버 응답 오류.")
        # charset 헤더가 없으면 requests 가 Latin-1 로 폴백해 한글이 깨진다.
        if not r.encoding or r.encoding.lower() in ("iso-8859-1", "latin-1"):
            r.encoding = r.apparent_encoding or "utf-8"
        return r.text

    # ── 페이지 단위 ───────────────────────────────────────────────────────────
    def search_page(self, kwd: str, *, srch_target: str = "title", category: str | None = None,
                    page_num: int = 1, page_size: int = MAX_PAGE_SIZE,
                    **extra) -> tuple[int, list[Holding], dict]:
        """1페이지 조회 → (total, 레코드, 봉투 메타)."""
        params = {
            "srchTarget": srch_target,
            "kwd": kwd,
            "category": category,
            "pageNum": max(1, int(page_num)),
            "pageSize": min(int(page_size), MAX_PAGE_SIZE),
        }
        params.update(extra)   # sort 등 추가 파라미터 통과
        try:
            return parse_search_response(self._call(params))
        except ParseError as e:
            raise NlError(str(e)) from e

    # ── 절단을 드러내는 수집 ──────────────────────────────────────────────────
    def search_meta(self, kwd: str, *, srch_target: str = "title", category: str | None = None,
                    max_records: int = 500, page_size: int = MAX_PAGE_SIZE,
                    contains=None, **extra) -> tuple[list[Holding], dict]:
        """검색 + **회수 메타** — 조용한 절단 방지.

        meta 필드
          total          : API 가 보고한 전체 건수
          fetched        : **API 로부터 실제 회수한** 건수(중복제거 후, contains 필터 전)
          returned       : 후처리 필터까지 거쳐 최종 반환한 건수
          truncated      : fetched < total (=일부만 받았다)
          cap_hit        : total > 500 (=**나머지는 어떤 페이징으로도 받을 수 없다**)
          api_record_cap : 500
          stopped_reason : exhausted | cap | max_records | empty_page | request_guard
          requests       : 실제 HTTP 요청 횟수
          warning        : 절단 시 사람이 읽는 경고문

        ⚠️ `cap_hit` 과 `truncated` 는 다른 뜻이다.
           - truncated: 이번 호출이 덜 받았다 → max_records 를 올리면 해결될 수 있다.
           - cap_hit  : API 자체가 500건까지만 준다 → **max_records 를 올려도 해결되지 않는다.**
             연도(`pub_year` 후처리)·분류·검색어를 쪼개서 각 조각이 500 미만이 되게 해야 한다.

        ⚠️ `fetched` 와 `returned` 도 구분한다. contains 로 걸러낸 결과를 `fetched` 에 덮어쓰면
           "API 가 1건만 줬다"와 "500건 받아 1건 남겼다"가 구별되지 않는다(적대적 검증에서 검출).
        """
        # 500건을 넘겨 요청하면 API 가 오류코드 012 를 낸다 → 상한 안에서만 페이징한다.
        # 하한 1 — max_records=0 이면 한 번도 호출하지 않아 total 이 0 으로 남고,
        # 그 결과가 '검색 결과 없음'으로 오독된다(적대적 검증 ⑫에서 확인).
        ceiling = max(1, min(int(max_records), API_RECORD_CAP))
        rows = max(1, min(int(page_size), MAX_PAGE_SIZE))
        # 여러 페이지가 필요하면 **페이지 크기를 최대로 올린다.** page_size 는 전송 단위일 뿐
        # 결과 집합을 바꾸지 않으므로, 작은 값으로 두면 같은 데이터를 받으려고 요청 수만 늘어난다.
        # (적대적 검증에서 page_size=1·max_records=1000 조합이 **499회 요청**을 유발했다.
        #  공공 API 에 대한 예의 문제이자 실패 확률·소요시간 문제다.)
        if ceiling > rows:
            rows = MAX_PAGE_SIZE
        # 그래도 폭주하지 않도록 절대 상한을 둔다(500/1페이지당 최소 1건 가정 시에도 충분).
        max_requests = max(2, -(-ceiling // rows) + 2)

        out: list[Holding] = []
        seen: set[str] = set()
        total = 0
        page = 1
        requests_made = 0
        stopped = "exhausted"

        while len(out) < ceiling:
            if requests_made >= max_requests:
                stopped = "request_guard"
                break
            total_p, recs, _env = self.search_page(
                kwd, srch_target=srch_target, category=category,
                page_num=page, page_size=rows, **extra)
            requests_made += 1
            if total_p:
                total = total_p
            if not recs:
                stopped = "empty_page"
                break
            before = len(out)
            for h in recs:
                k = h.dedup_key()
                if k in seen:
                    continue
                seen.add(k)
                out.append(h)
            if len(out) == before:      # 새 레코드가 없으면 무한루프 방지
                stopped = "empty_page"
                break
            if total and page * rows >= total:
                stopped = "exhausted"
                break
            if page * rows >= ceiling:
                stopped = "cap" if ceiling == API_RECORD_CAP else "max_records"
                break
            page += 1
            time.sleep(self.throttle)

        out = out[:ceiling]
        fetched = len(out)
        meta = {
            "term": kwd,
            "srch_target": srch_target,
            "category": category or "",
            "total": total,
            "fetched": fetched,
            "returned": fetched,
            "truncated": bool(total) and fetched < total,
            "cap_hit": bool(total) and total > API_RECORD_CAP,
            "api_record_cap": API_RECORD_CAP,
            "max_records": int(max_records),
            "page_size": rows,
            "requests": requests_made,
            "stopped_reason": stopped,
        }
        if contains:
            subs = [contains] if isinstance(contains, str) else list(contains)
            kept = [h for h in out if h.matches(subs)]
            meta["contains_filtered_out"] = fetched - len(kept)
            out = kept
            meta["returned"] = len(out)
        if meta["truncated"]:
            meta["warning"] = _truncation_warning(meta)
        return out, meta

    def search(self, kwd: str, **kw) -> list[Holding]:
        """레코드만 반환하는 얇은 래퍼. 절단 여부까지 필요하면 search_meta() 를 쓴다."""
        return self.search_meta(kwd, **kw)[0]

    # ── 다중 검색어 합집합 ────────────────────────────────────────────────────
    def search_terms_meta(self, terms, *, srch_target: str = "title",
                          category: str | None = None, max_records: int = 2000,
                          page_size: int = MAX_PAGE_SIZE, contains=None,
                          year_from: int | None = None, year_to: int | None = None,
                          **extra) -> tuple[list[Holding], dict]:
        """여러 검색어를 **각각 조회해 합집합** + 축별 회수 메타.

        국립중앙도서관 검색식에는 필드 내 OR 연산자가 없으므로 변형어별 개별검색 합집합이 정석이다
        (KCI 에서 검증된 것과 같은 전략).

        연도 필터는 API 파라미터가 아니라 **회수 후 로컬 후처리**다 —
        `pub_year` 는 정규화된 4자리 연도이고, 원문 `pubYearInfo` 는 형식이 뒤섞여 있다.
        """
        terms = [t.strip() for t in (terms or []) if t and t.strip()]
        out: list[Holding] = []
        seen: set[str] = set()
        axes: list[dict] = []
        stopped_early = False

        for term in terms:
            recs, m = self.search_meta(
                term, srch_target=srch_target, category=category,
                max_records=max_records, page_size=page_size, **extra)
            new = 0
            for h in recs:
                k = h.dedup_key()
                if k in seen:
                    continue
                seen.add(k)
                out.append(h)
                new += 1
            axes.append({**m, "new": new})
            if len(out) >= max_records:
                stopped_early = True
                break

        out = out[:max_records]
        meta = {
            "axes": axes,
            "axes_planned": len(terms),
            "axes_run": len(axes),
            "union": len(out),
            "union_upper_bound": sum(a["total"] for a in axes),
            "max_records": max_records,
            "api_record_cap": API_RECORD_CAP,
            "cap_hit_terms": [a["term"] for a in axes if a["cap_hit"]],
            "truncated": bool(stopped_early or len(axes) < len(terms)
                              or any(a["truncated"] for a in axes)),
        }
        # 연도 후처리 — pub_year 가 빈 레코드(실측 5.2%)는 연도 필터를 걸면 사라진다는 점을 알린다.
        if year_from or year_to:
            before = len(out)
            no_year = sum(1 for h in out if not h.pub_year)
            lo = year_from or 0
            hi = year_to or 9999
            out = [h for h in out if h.pub_year and lo <= int(h.pub_year) <= hi]
            meta["year_filtered_out"] = before - len(out)
            meta["year_missing_dropped"] = no_year
        if contains:
            subs = [contains] if isinstance(contains, str) else list(contains)
            before = len(out)
            out = [h for h in out if h.matches(subs)]
            meta["contains_filtered_out"] = before - len(out)
        meta["returned"] = len(out)

        warns = []
        if meta["cap_hit_terms"]:
            warns.append(
                f"⚠️ API 500건 상한에 걸린 검색어: {', '.join(meta['cap_hit_terms'])}. "
                f"이 검색어들은 max_records 를 올려도 501번째부터 받을 수 없습니다 — "
                f"연도·분류로 검색식을 쪼개세요."
            )
        if stopped_early or len(axes) < len(terms):
            warns.append(
                f"⚠️ max_records={max_records} 상한에 걸려 검색축 {len(axes)}/{len(terms)}개만 "
                f"실행했습니다. 실행분 total 합(합집합 상한)은 {meta['union_upper_bound']}건입니다."
            )
        if warns:
            meta["warning"] = " ".join(warns)
        return out, meta

    def search_terms(self, terms, **kw) -> list[Holding]:
        """레코드만 반환하는 얇은 래퍼."""
        return self.search_terms_meta(terms, **kw)[0]


def _truncation_warning(meta: dict) -> str:
    """절단 경고문 — 원인별로 처방이 다르므로 구분해서 쓴다.

    ⚠️ 항상 **회수량(fetched)** 기준으로 서술한다. 후처리 필터로 줄어든 수(returned)로 쓰면
       "API 가 그만큼밖에 안 줬다"와 "내가 걸러냈다"가 뒤섞인다(적대적 검증에서 검출).
    """
    if meta["cap_hit"]:
        base = (
            f"⚠️ 절단됨 — API 가 보고한 total 은 {meta['total']:,}건인데 "
            f"{meta['fetched']:,}건만 회수했습니다. 국립중앙도서관 검색 API 는 "
            f"**한 검색식당 {meta['api_record_cap']}건까지만** 내려줍니다(오류코드 012 DATA LIMIT 500). "
            f"max_records 를 올려도 나머지는 받을 수 없습니다 — 검색어를 좁히거나 "
            f"연도·분류(category)로 검색식을 쪼개 각 조각이 {meta['api_record_cap']}건 미만이 되게 하세요."
        )
    else:
        base = (
            f"⚠️ 절단됨 — total {meta['total']:,}건 중 {meta['fetched']:,}건만 회수했습니다 "
            f"(max_records={meta['max_records']} 상한). max_records 를 올려 재수집하세요."
        )
    if meta.get("contains_filtered_out"):
        base += (
            f" (참고: 회수한 {meta['fetched']:,}건 중 contains 필터로 "
            f"{meta['contains_filtered_out']:,}건이 제외돼 최종 {meta['returned']:,}건이 반환됩니다 — "
            f"이 감소는 절단과 무관합니다.)"
        )
    return base
