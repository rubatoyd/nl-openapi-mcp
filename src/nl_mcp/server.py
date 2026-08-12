"""국립중앙도서관 소장자료 검색 MCP 서버 (FastMCP).

⚠️ `mcp.server.fastmcp` 를 **조건부 import 하지 않는다.** mcp 2.0 은 이 모듈을 제거했으므로
   폴백을 두면 반쯤 동작하는 서버가 조용히 뜬다. pyproject 의 `mcp>=1.2.0,<2` 상한이
   유일한 방어선이고, 여기서는 실패를 시끄럽게 내는 편이 옳다.
   (자매 프로젝트 kci·scienceon 이 이 상한 누락으로 각각 기동 불능을 겪었다.)
"""
from __future__ import annotations

import argparse
import functools
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .client import NlClient, NlError
from .config import API_RECORD_CAP, CATEGORIES, get_api_key

mcp = FastMCP("nl")


def _safe(fn):
    """도구는 **항상 JSON 직렬화 가능한 dict** 를 반환 — 어떤 예외도 도구 밖으로 누수 금지.

    네트워크/SSL/HTTP/파싱 예외는 물론 자격증명 누락(RuntimeError)도 여기서 잡는다.
    (scienceon 이 특정 예외만 잡다가 RuntimeError 를 프로토콜 밖으로 흘린 전례가 있다.)
    _call 단계에서 인증키가 든 URL 은 이미 제거되므로 메시지에 키가 노출되지 않는다.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            return {"error": f"{type(e).__name__}: {e}"}
    return wrapper


# 도구 안전성 힌트(MCP annotations) — 디렉터리 심사·클라이언트 표시에 쓰인다.
# 전부 외부 API 조회(openWorld). collect 만 파일 생성(쓰기, 비파괴).
_READ = {"readOnlyHint": True, "openWorldHint": True}
_WRITE = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}

_NO_KEY = {
    "error": "NL_API_KEY 미설정 — 국립중앙도서관 소장자료 검색에는 인증키가 필요합니다.",
    "hint": "https://www.nl.go.kr 에서 오픈API 인증키를 발급받아 .env 또는 환경변수 NL_API_KEY 로 설정하세요.",
}


@mcp.tool(annotations=_READ)
@_safe
def nl_status() -> dict:
    """연결 점검 — 인증키 보유 여부 + 소장자료 검색 API 실제 왕복 1회."""
    info: dict = {"has_api_key": get_api_key() is not None,
                  "api": "국립중앙도서관 소장자료 검색 (search.do)",
                  "api_record_cap": API_RECORD_CAP}
    if not info["has_api_key"]:
        info["ok"] = False
        info["note"] = _NO_KEY["error"]
        info["hint"] = _NO_KEY["hint"]
        return info
    try:
        total, recs, _env = NlClient().search_page("도서관", page_num=1, page_size=1)
        info["ok"] = True
        info["probe"] = {"kwd": "도서관", "total": total, "returned": len(recs)}
        info["note"] = "인증키 유효 — 소장자료 검색 정상 응답."
    except NlError as e:
        info["ok"] = False
        info["note"] = str(e)
    return info


@mcp.tool(annotations=_READ)
@_safe
def nl_search(kwd: str, srch_target: str = "title", exact: bool = False,
              category: str | None = None, rows: int = 20, page: int = 1,
              extra_params: dict | None = None) -> dict:
    """[소장자료 검색] 국립중앙도서관 소장자료를 검색한다.

    kwd: 검색어.
    exact: True 면 큰따옴표 **구문검색**(토큰 인접 요구). 특정 자료를 정확히 찾을 때만 쓸 것 —
      코퍼스 수집에는 부적합하다(아래 참조).
    srch_target: 실측 지원값 — `title`(제목) · `author`(저자) · `publisher`(발행자) ·
      `keyword`(키워드) · `total`(전 필드).
      ⚠️ **`isbn`·`classNo`·`callNo` 등 미지원 값은 오류가 나지 않고 조용히 전 필드 검색으로
         폴백한다.** ISBN 으로 찾았다고 믿으면 실제로는 전 필드 결과를 받는다
         (실측: `srchTarget=isbn&kwd=오욱환` 이 저자 검색과 같은 36건을 반환).
         ISBN 을 찾으려면 `srch_target="total"` 로 두고 ISBN 문자열을 넣는 편이 정직하다.
    category: 도서·고문헌·학위논문·잡지/학술지·신문·기사·멀티미디어·장애인자료·웹사이트·
      해외기록물·외부연계자료·기타. ⚠️ **"전체" 는 오류(013)** — 전체 검색은 생략할 것.
    rows: 반환 건수(1~100, 문맥 절약을 위한 도구 자체 상한. API 는 500까지 받는다).
    extra_params: 임의 API 파라미터 전달.

    ⚠️ **기본 검색은 제목 부분일치가 아니라 토큰 매칭 + 적합도 정렬이다.**
       `교육불평등` 은 `교육`·`불평등` 으로 쪼개져 둘 중 하나만 든 제목도 회수된다.
    ⚠️ **`exact=True` 는 재현율을 크게 떨어뜨린다** — 실측 6개 검색어에서 평균 47% 손실,
       최악 84%(`교육형평성` 31건 → 5건). 한국어 복합어가 표제에서 조사·수식어로 갈라지기
       때문이다(`교육의 형평성`, `초중등교육의 형평성과`) — 구문검색은 인접을 요구한다.
       버려지는 것의 76%가 구성어를 모두 포함한 **관련 문헌**이었다.
       → 자료를 넓게 모을 때는 쓰지 말고, **전체 표제를 아는 특정 자료 조회**에만 쓸 것.
       AND/OR/NOT 은 연산자가 아니라 그냥 토큰이다(`AND` 단독 검색 시 451,670건).

    ⚠️ `total` 은 국립중앙도서관이 보고한 전체 건수, `truncated` 는 이번 응답이 그보다 적다는 뜻.
       **`cap_hit=true` 는 다르다** — total 이 500을 넘어 501번째부터는 어떤 페이징으로도
       받을 수 없다(레코드 오프셋 기준 상한, 실측 확인). 그 경우 검색식을 쪼개야 한다.
       빈 `records` 를 '자료 없음'으로 오독하지 말고 total 을 함께 볼 것.
    """
    if get_api_key() is None:
        return dict(_NO_KEY)
    # API 는 pageSize=500 까지 받지만, 도구 응답은 그대로 모델 문맥에 실리므로 100 으로 제한한다.
    rows = max(1, min(int(rows), 100))
    extra = {k: v for k, v in (extra_params or {}).items() if v not in (None, "")}
    try:
        total, recs, envelope = NlClient().search_page(
            kwd, srch_target=srch_target, category=category, exact=exact,
            page_num=page, page_size=rows, **extra)
    except NlError as e:
        return {"error": str(e)}
    out = {
        "count": len(recs),
        "total": total,
        "page": page,
        "rows": rows,
        "truncated": bool(total) and (page * rows) < total,
        "cap_hit": bool(total) and total > API_RECORD_CAP,
        "api_record_cap": API_RECORD_CAP,
        "records": [r.to_row() for r in recs],
    }
    if out["cap_hit"]:
        out["warning"] = (
            f"⚠️ total {total:,}건 — 국립중앙도서관 검색 API 는 한 검색식당 "
            f"{API_RECORD_CAP}건까지만 내려줍니다. 나머지는 페이징으로도 받을 수 없으니 "
            f"category 분할·검색어 세분화·exact=True 구문검색으로 쪼개세요"
            f"(연도로는 쪼갤 수 없습니다 — 서버측 연도 필터가 없습니다)."
        )
    elif out["truncated"]:
        out["warning"] = (
            f"전체 {total:,}건 중 이 페이지 {len(recs)}건만 반환했습니다 — "
            f"page 를 넘기거나 전건 수집은 nl_collect 를 쓰세요."
        )
    if envelope:
        out["envelope"] = envelope
    return out


@mcp.tool(annotations=_WRITE)
@_safe
def nl_collect(terms: list[str] | None = None, kwd: str | None = None,
               srch_target: str = "title", exact: bool = False,
               category: str | None = None, auto_partition: bool = False,
               partition_depth: int = 2, sort_depth: int = 0, bisect_depth: int = 0,
               year_from: int | None = None, year_to: int | None = None,
               contains: list[str] | None = None, formats: list[str] | None = None,
               max_records: int = 500, out_dir: str | None = None,
               name: str | None = None, save: bool = True,
               extra_params: dict | None = None) -> dict:
    """[수집] 검색어들을 각각 조회해 **합집합**으로 모으고 파일로 저장한다.

    terms: 변형어 목록(각각 개별 검색 후 합집합). 검색어를 쪼갤수록 500건 상한을 덜 받으므로
      넓은 말 하나보다 좁은 말 여럿이 회수량이 많다.
    kwd: 단일 검색어(terms 대신).
    exact: 🔴 **코퍼스 수집에는 쓰지 말 것.** 구문검색은 토큰 인접을 요구해 한국어 복합어가
      조사·수식어로 갈라진 표제(`교육의 형평성`)를 전부 놓친다. 실측 재현율 손실 평균 47%,
      최악 84%(교육형평성 31→5건)이고 버려진 것의 76%가 관련 문헌이었다.
      변형어를 늘려도 회복되지 않는다(12/31). **자료를 넓게 모으려면 False 로 두고 걸러내기는
      `contains` 후처리로 하라.** exact 는 전체 표제를 아는 특정 자료 조회용이다.
    category: 도서·학위논문·잡지/학술지·기사 등. ⚠️ "전체" 는 오류(013) — 생략할 것.
    auto_partition: **500 상한 우회.** 검색어가 상한에 걸리고 category 를 지정하지 않았으면
      서버측 축으로 **재귀 분할**해 재수집한다. 축은 실측으로 찾은 3개다 —
      `category` → `manageName`(둘 다 완전분할) → `licYn`(값이 빈 레코드는 못 잡음).
      상한에 걸린 조각만 다음 축으로 더 쪼개고, **부모 조각도 합집합에 넣어** 불완전한
      축을 써도 손해가 나지 않게 한다.
    partition_depth: 분할 깊이(1~3, 기본 2). 실측 회복량(`교육복지` 전체 7,028건):
      분할 없음 500(7%) → 깊이1 2,134(30%) → 깊이2 3,265(46%) → 깊이3 4,722(67%).
      ⚠️ 호출 수가 함께 는다(13 → 25 → 60회). 깊이 3은 코퍼스 전수성이 중요할 때만.
      ⚠️ **전수는 여전히 불가능하다.** `meta.axes[].partition.unreachable` 과
         `still_capped` 가 못 받은 건수와 남은 조각을 보고한다.
    sort_depth: **정렬 뒤집기**(0~5, 기본 0=끄기). 같은 검색식을 정렬 순서만 바꿔 다시 훑는다.
      `asc` 와 `desc` 의 교집합이 **0건**이라(실측) 정렬축 하나가 상한을 사실상 2배로 늘린다.
      실측(`교육복지`/`도서` 1,856건): 500 → `ipub_year` 1,247 → `+ititle` 1,558
      → `+iauthor` **1,746(94%)**, 단 **7요청**. **분할보다 훨씬 싸다.**
      `auto_partition` 과 **함께 쓸 수 있다**(축을 쪼갠 뒤 각 조각을 다시 훑는다).
      ⚠️ 상한에 걸리지 않은 검색식은 훑지 않는다(호출 낭비 없음).
    bisect_depth: f-슬롯 AND/NOT **재귀 이분할**(0~8, 기본 0=끄기).
      `AND + NOT = 부모` 가 모든 깊이에서 정확해 누락이 없고 임의 깊이로 쪼갤 수 있다.
      🔴 **그러나 보통은 `auto_partition`+`sort_depth` 가 더 낫다** — 실측
         `교육`/`도서`(197,651건): 분할3+정렬1 **17,893건/60요청** vs
         이분할8+정렬1 11,633건/**135요청**(회수는 적고 요청은 2배).
      쓸 자리: category·manageName·licYn 를 전부 고정한 조각이 여전히 500을 넘을 때.
    contains: 결과 텍스트 부분일치 후처리. year_from/year_to: 발행연도 필터.
    formats: xlsx/csv/json/sqlite (기본 3종). save=false 면 저장 없이 미리보기만.
    out_dir 미지정 시 홈의 nl-output/. extra_params: 임의 API 파라미터 전달.

    ⚠️ **`year_from`/`year_to`/`contains` 는 로컬 후처리다** — 이미 받은 레코드에만 걸린다.
       500건 상한을 풀어주지 않는다. **서버측 연도 필터는 존재하지 않는다**(실측:
       startPubYear·pubYearStart 등 11개 후보 전부 무시됨). 연도로 상한을 우회할 수는 없다.

    ⚠️ `meta.cap_hit_terms` 에 검색어가 있으면 그 검색어는 500건에서 잘린 것이다.
       `max_records` 를 올려도 해결되지 않는다 — **검색어를 좁히거나 `category` 로 쪼갤 것**.
       `meta.year_missing_dropped` 는 발행연도가 비어 연도 필터에서 탈락한 건수다
       (실측 5.2%의 레코드는 pubYearInfo 가 비어 있다).
    """
    if get_api_key() is None:
        return dict(_NO_KEY)
    kws = [t for t in (terms or ([kwd] if kwd else [])) if t and t.strip()]
    if not kws:
        return {"error": "검색어가 없습니다 — terms 또는 kwd 중 하나는 필요합니다."}
    extra = {k: v for k, v in (extra_params or {}).items() if v not in (None, "")}
    if exact:
        extra["exact"] = True
    # ⚠️ `max_records` 가 API 상한 이하이면 분할해도 더 담을 자리가 없어 **아무 일도 안 일어난다.**
    #    auto_partition 을 켠 것은 500 을 넘겨 받겠다는 뜻이므로 천장을 올린다(조용히 하지 않고 보고).
    raised_from = None
    if auto_partition and max_records <= API_RECORD_CAP:
        raised_from, max_records = max_records, API_RECORD_CAP * len(CATEGORIES)
    try:
        recs, meta = NlClient().search_terms_meta(
            kws, srch_target=srch_target, category=category,
            auto_partition=auto_partition, partition_depth=max(1, min(partition_depth, 3)),
            sort_depth=max(0, min(sort_depth, 5)),
            bisect_depth=max(0, min(bisect_depth, 8)),
            year_from=year_from, year_to=year_to, contains=contains,
            max_records=max_records, **extra)
    except NlError as e:
        return {"error": str(e)}

    out = {"count": len(recs), "terms": kws, "truncated": meta["truncated"], "meta": meta}
    if raised_from is not None:
        out["note"] = (f"auto_partition=True 이므로 max_records 를 {raised_from} → {max_records} 로 "
                       f"올렸습니다. 상한({API_RECORD_CAP}) 이하로는 분할해도 더 담을 자리가 없습니다.")
        meta["max_records_raised_from"] = raised_from
    if meta.get("warning"):
        out["warning"] = meta["warning"]
    if not save:
        out["preview"] = [r.to_row() for r in recs[:100]]
        # ⚠️ note 를 덮어쓰면 위의 max_records 상향 안내가 사라진다 — 이어 붙인다
        out["note"] = " ".join(filter(None, [
            out.get("note"), "save=false — 파일을 만들지 않았습니다(앞 100건 미리보기)."]))
        return out

    from .exporters import export
    fmts = formats or ["xlsx", "csv", "json"]
    base = out_dir or str(Path.home() / "nl-output")
    # 파일명 정규화는 exporters.export 가 담당한다 — 사용자 입력(name·검색어)이 경로에
    # 닿으므로 한 곳에서 처리해야 빠뜨리지 않는다(적대적 검증에서 경로 이탈이 재현됐다).
    out["files"] = export(recs, fmts, base, name or f"nl_{kws[0]}")
    return out


def _env_port(name: str) -> int | None:
    """숫자가 아니면 조용히 무시 — 잘못된 환경변수 하나로 서버가 못 뜨면 안 된다."""
    raw = (os.environ.get(name) or "").strip()
    return int(raw) if raw.isdigit() else None


def main(argv: list[str] | None = None) -> None:
    """MCP 서버 기동.

    기본은 **stdio** — 클라이언트가 로컬 서브프로세스로 띄우는 방식이고 기존 동작과 동일하다.
    `--transport sse|streamable-http` 로 HTTP 전송도 된다. MCP 를 지원하는 어떤 클라이언트든
    (Cursor·Cline·Zed·OpenAI Agents SDK·자체 에이전트) 붙을 수 있고, 원격 호스팅도 가능하다.

    ⚠️ **HTTP 전송에는 인증이 없다.** 기본 바인드는 루프백(127.0.0.1)이다. 외부 주소에 열면
       인증키를 품은 서버를 그대로 공개하는 것과 같으므로 신뢰된 망에서만 쓸 것.
    """
    p = argparse.ArgumentParser(prog="nl-mcp", description="국립중앙도서관 소장자료 검색 MCP 서버")
    p.add_argument("--transport", choices=["stdio", "sse", "streamable-http"],
                   default=os.environ.get("NL_MCP_TRANSPORT") or "stdio",
                   help="전송 방식 (기본 stdio). 환경변수 NL_MCP_TRANSPORT 로도 지정 가능.")
    p.add_argument("--host", default=os.environ.get("NL_MCP_HOST"),
                   help="HTTP 전송 바인드 주소 (기본 127.0.0.1 — 루프백)")
    p.add_argument("--port", type=int, default=_env_port("NL_MCP_PORT"),
                   help="HTTP 전송 포트 (기본 8000)")
    # 클라이언트가 예기치 않은 인자를 넘겨도 서버는 떠야 한다 → 미지의 인자는 경고만 하고 무시
    args, unknown = p.parse_known_args(argv)
    if unknown:
        print(f"[nl-mcp] 알 수 없는 인자 무시: {unknown}", file=sys.stderr)
    if args.host:
        mcp.settings.host = args.host
    if args.port:
        mcp.settings.port = args.port
    if args.transport != "stdio":
        path = mcp.settings.sse_path if args.transport == "sse" else mcp.settings.streamable_http_path
        print(f"[nl-mcp] {args.transport} 전송 — "
              f"http://{mcp.settings.host}:{mcp.settings.port}{path}", file=sys.stderr)
        if mcp.settings.host not in ("127.0.0.1", "localhost", "::1"):
            print("[nl-mcp] ⚠️ 루프백 외 주소에 바인드했습니다. HTTP 전송에는 인증이 없어 "
                  "인증키를 가진 서버가 그대로 노출됩니다. 신뢰된 망에서만 사용하세요.", file=sys.stderr)
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
