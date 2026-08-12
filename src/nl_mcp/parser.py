"""소장자료 검색 API(JSON) 응답 파서.

응답 봉투는 `{"total": <건수>, "result": [ {24개 필드}, … ], …}` 형태다
(수집 스크립트 c2.py 가 `total`·`result` 로 1,124건을 실제 회수한 것으로 확정).
KCI·ScienceON 은 XML 이었으나 이쪽은 JSON 이라 파서가 훨씬 단순하다.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .config import NL_BASE_URL
from .models import Holding, normalize_pub_year


class ParseError(RuntimeError):
    """응답이 검색결과 봉투가 아니거나 API 가 오류를 보고했을 때."""


_HTML_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

# 공식 안내서에 기재된 오류코드. 응답 키 철자는 미검증이라 후보를 넓게 본다.
#
# ⚠️ `resultCode` 는 **일부러 뺐다.** 국내 공공 API 는 이 키를 성공 표시로도 쓴다
#    (`resultCode: "00"` = 정상). 적대적 검증에서 `"00"` → zfill → `"000"` → "SYSTEM ERROR" 로
#    해석돼 **정상 응답 50건을 통째로 오류 처리**하는 거짓 양성이 재현됐다.
#    오류 응답 봉투를 라이브로 확인하지 못한 상태이므로, 이름에 error/err 가 든 키만 신뢰한다.
_ERROR_CODE_KEYS = ("errorCode", "errCode", "error_code", "ERR_CODE", "ERROR_CODE")
_ERROR_MSG_KEYS = ("errorMsg", "errMsg", "error_message", "ERR_MSG", "message")
ERROR_CODE_HINTS = {
    "000": "SYSTEM ERROR — 서버 내부 오류",
    "010": "NO KEY VALUE — 인증키가 전달되지 않음",
    "011": "INVALID KEY — 유효하지 않은 인증키",       # ✅ 실측 확인(2026-08-12)
    "012": "DATA LIMIT 500 — 한 검색식당 500건 초과 조회 불가",
    "013": "CATEGORY ERROR — category 값이 유효하지 않음(서버가 유효 목록을 함께 알려준다)",
    "101": "SEARCH ERROR — 검색 조건 또는 검색 서버 오류",
}


def clean_html(text: Any) -> str:
    """HTML 태그 제거 + 공백 정리.

    ⚠️ 검색 API 는 매칭어를 하이라이트하려고 제목 등에 `<span …>` 을 끼워 보낸다.
       제거하지 않으면 제목 비교·중복제거·내보내기가 전부 오염된다
       (실제 수집 스크립트 c2.py 도 전 필드에 같은 정제를 적용했다).
    """
    if text is None:
        return ""
    return _WS.sub(" ", _HTML_TAG.sub("", str(text))).strip()


def _abs_url(path: Any) -> str:
    """상대 경로(`/NL/contents/…`, `kolis/2007/…`)를 절대 URL 로."""
    p = clean_html(path)
    if not p:
        return ""
    if p.startswith(("http://", "https://")):
        return p
    return f"{NL_BASE_URL}/{p.lstrip('/')}"


def parse_holding(item: dict[str, Any]) -> Holding:
    """`result` 배열의 항목 1건 → Holding.

    필드명은 실응답에서 확정한 24개다. 값은 전부 clean_html 을 거치되 `raw` 에 원본을 남긴다.
    """
    g = lambda k: clean_html(item.get(k))  # noqa: E731
    raw_year = g("pubYearInfo")
    return Holding(
        source="nl_search",
        record_id=g("id"),
        control_no=g("controlNo"),
        title=g("titleInfo"),
        authors=g("authorInfo"),
        pub_info=g("pubInfo"),
        pub_year=normalize_pub_year(raw_year),
        pub_year_raw=raw_year,
        type_name=g("typeName"),
        type_code=g("typeCode"),
        menu_name=g("menuName"),
        media_name=g("mediaName"),
        manage_name=g("manageName"),
        place_info=g("placeInfo"),
        isbn=g("isbn"),
        call_no=g("callNo"),
        class_no=g("classNo"),
        kdc_code=g("kdcCode1s"),
        kdc_name=g("kdcName1s"),
        doc_type=g("docYn"),
        lic_code=g("licYn"),
        lic_text=g("licText"),
        reg_date=g("regDate"),
        org_link=g("orgLink"),
        detail_url=_abs_url(item.get("detailLink")),
        image_url=_abs_url(item.get("imageUrl")),
        raw=dict(item),
    )


def _as_int(value: Any) -> int:
    """`total` 은 숫자로도 문자열("1,856")로도 올 수 있다 — 둘 다 받는다."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    digits = re.sub(r"[^0-9]", "", str(value or ""))
    return int(digits) if digits else 0


def check_api_error(data: dict[str, Any]) -> None:
    """API 가 보고한 오류를 ParseError 로 올린다 (조용한 통과 금지).

    ⚠️ **레코드가 실제로 실려 있으면 오류로 보지 않는다.** 오류 봉투 철자가 미검증인 상태에서
       키 이름만 보고 단정하면, 멀쩡한 데이터를 오류로 버리는 쪽이 훨씬 큰 피해다.
       (조용한 통과를 막는 진짜 방어선은 `result` 키 부재 검사다 — parse_search_response 참조.)
    """
    items = data.get("result")
    if isinstance(items, list) and items:
        return
    for k in _ERROR_CODE_KEYS:
        code = data.get(k)
        if code in (None, "", "0", 0):
            continue
        code_s = str(code).strip()
        msg = next((str(data[m]) for m in _ERROR_MSG_KEYS if data.get(m)), "")
        hint = ERROR_CODE_HINTS.get(code_s.zfill(3), "")
        raise ParseError(
            f"국립중앙도서관 API 오류 [{code_s}]"
            + (f" {msg}" if msg else "")
            + (f" — {hint}" if hint else "")
        )


def parse_search_response(body: str | dict[str, Any]) -> tuple[int, list[Holding], dict[str, Any]]:
    """검색 응답 → (total, 레코드 목록, 봉투 메타).

    반환하는 봉투 메타에는 `result` 를 뺀 최상위 필드가 담긴다(pageNum·pageSize 등 진단용).

    ⚠️ `result` 키가 아예 없으면 **오류로 본다**. 빈 목록으로 조용히 통과시키면
       인증키 오류·검색 서버 오류가 '결과 0건'으로 둔갑한다(KCI 에서 같은 실수를 고쳤다).
    """
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8", "replace")
    if isinstance(body, str):
        text = body.strip()
        if not text:
            raise ParseError("빈 응답 — 네트워크 또는 서버 오류로 보입니다.")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            head = _WS.sub(" ", _HTML_TAG.sub(" ", text[:300])).strip()
            raise ParseError(
                f"JSON 파싱 실패({e.msg}) — apiType=json 인데 JSON 이 아닙니다. "
                f"응답 앞부분: {head!r}"
            ) from None
    else:
        data = body

    if not isinstance(data, dict):
        raise ParseError(f"예상과 다른 응답 최상위 타입: {type(data).__name__} (dict 여야 함)")

    check_api_error(data)

    if "result" not in data:
        # ✅ 라이브 실측(2026-08-12): **검색 결과가 0건이면 `result` 키 자체가 없다.**
        #    응답은 `{"total":0,"kwd":…,"pageNum":…,"pageSize":…,"category":…,"sort":…}` 이다.
        #    초판은 이것을 오류로 올렸는데, 그러면 정상적인 '결과 없음'이 매번 오류로 둔갑한다
        #    (검색어 오타·빈 분류 조회 등 흔한 경우 전부).
        #
        # ⚠️ 그렇다고 `result` 부재를 **무조건** 0건으로 보면 안 된다. `total` 이 0 이 아닌데
        #    `result` 가 없다면 그것은 정상적인 빈 결과가 아니라 **레코드가 통째로 사라진 것**이고,
        #    빈 목록으로 통과시키면 조용한 절단이 된다. 실측상 이 조합은 나타나지 않으므로
        #    이상 신호로 보고 오류로 올린다. (적대적 검증에서 이 구멍이 지적됐다.)
        total_v = _as_int(data.get("total")) if "total" in data else None
        envelope = {k: v for k, v in data.items() if k != "result"}
        if total_v == 0:
            return 0, [], envelope
        if total_v is not None:
            raise ParseError(
                f"응답에 `result` 가 없는데 total 은 {total_v:,}건입니다 — 정상적인 '결과 0건'이 "
                f"아닙니다(0건일 때만 result 가 생략됩니다). 레코드가 누락된 응답으로 보입니다."
            )
        keys = ", ".join(list(data)[:12]) or "(키 없음)"
        raise ParseError(
            f"응답에 `result` 도 `total` 도 없습니다 — 검색결과 봉투가 아닙니다. 최상위 키: {keys}")

    items = data.get("result") or []
    if isinstance(items, dict):      # 단건일 때 배열이 아닐 가능성에 대비
        items = [items]
    if not isinstance(items, list):
        raise ParseError(f"`result` 타입이 배열이 아닙니다: {type(items).__name__}")

    records = [parse_holding(it) for it in items if isinstance(it, dict)]
    envelope = {k: v for k, v in data.items() if k != "result"}
    return _as_int(data.get("total")), records, envelope
