"""라이브 실측(2026-08-12)으로 확정된 API 동작의 회귀 테스트.

`scripts/probe_api.py` + 후속 정밀 프로브로 실제 국립중앙도서관 API 를 호출해 확인한 사실들이다.
추정이었던 항목이 여기서 실측으로 승격됐고, 그 과정에서 코드 버그 2건이 드러났다.
"""
import json

import pytest
import samples

from nl_mcp import server as srv
from nl_mcp.client import NlClient, as_phrase
from nl_mcp.config import (
    CATEGORIES,
    MAX_PAGE_SIZE,
    SEARCH_TARGETS_FALLBACK,
    SEARCH_TARGETS_VERIFIED,
)
from nl_mcp.parser import ERROR_CODE_HINTS, ParseError, parse_holding, parse_search_response


# ══ 응답 봉투 ════════════════════════════════════════════════════════════════
def test_봉투_최상위_키_7종():
    """실측: total·kwd·pageNum·pageSize·category·sort·result"""
    body = {**samples.EMPTY_RESULT_ENVELOPE, "result": [samples.OFFLINE_FULL]}
    total, recs, env = parse_search_response(body)
    assert set(env) == set(samples.LIVE_ENVELOPE_KEYS) - {"result"}
    assert len(recs) == 1


def test_잘못된_인증키_응답():
    """실측 원문: {"errorCode":"011","errorMsg":"INVALID KEY:인증키값이 유효하지 않습니다."}"""
    with pytest.raises(ParseError) as ei:
        parse_search_response(samples.INVALID_KEY_ERROR)
    msg = str(ei.value)
    assert "011" in msg and "INVALID KEY" in msg


def test_category_오류코드_013_이_안내에_있다():
    assert "013" in ERROR_CODE_HINTS
    assert "CATEGORY" in ERROR_CODE_HINTS["013"]


def test_result_없이_total_이_0이_아니면_오류다():
    """`result` 부재를 무조건 0건으로 보면 조용한 절단이 된다.

    실측상 `result` 는 **0건일 때만** 생략된다. total>0 인데 result 가 없으면
    레코드가 통째로 사라진 이상 응답이므로 빈 목록으로 통과시키면 안 된다.
    """
    with pytest.raises(ParseError, match="1,856"):
        parse_search_response({**samples.EMPTY_RESULT_ENVELOPE, "total": 1856})


def test_result_없이_total_0이면_정상적인_빈결과():
    total, recs, _ = parse_search_response(samples.EMPTY_RESULT_ENVELOPE)
    assert total == 0 and recs == []


# ══ 하이라이트 마크업 ════════════════════════════════════════════════════════
def test_실측_마크업이_제거된다():
    """실측 class 는 `searching_txt` 이고 **매칭 토큰마다** span 이 붙는다."""
    h = parse_holding(samples.RAW_WITH_MARKUP)
    assert "<" not in h.title and ">" not in h.title
    assert "searching_txt" not in h.title
    assert h.title.startswith("교육 불평등")
    # titleInfo 말고 다른 필드에도 마크업이 실린다
    assert "<" not in h.pub_info
    assert h.pub_info == "교육과학사"
    # 원본은 raw 에 보존
    assert "searching_txt" in h.raw["titleInfo"]


# ══ pageSize 상한 ════════════════════════════════════════════════════════════
def test_pageSize_상한은_500이다():
    """실측: 100·200·500 은 그대로 반환, 1000 은 거부(반환 0건).

    초판은 100 으로 잡아 상한(500건)까지 받는 데 5회를 썼다 → 1회로 줄었다.
    """
    assert MAX_PAGE_SIZE == 500


def test_상한까지_한_번에_받는다(monkeypatch):
    c = NlClient(api_key="k", throttle=0)
    calls = []

    def fake(params):
        calls.append(dict(params))
        size = int(params["pageSize"])
        start = (int(params["pageNum"]) - 1) * size
        end = min(start + size, 500)
        recs = [{**samples.OFFLINE_FULL, "id": f"ID{i}"} for i in range(start, end)]
        return json.dumps({"total": 1856, "result": recs}, ensure_ascii=False)

    monkeypatch.setattr(c, "_call", fake)
    recs, meta = c.search_meta("교육복지", max_records=500)
    assert len(recs) == 500
    assert meta["requests"] == 1          # 5회 → 1회
    assert meta["cap_hit"] is True


# ══ 큰따옴표 구문검색 ════════════════════════════════════════════════════════
@pytest.mark.parametrize("raw, expected", [
    ("교육불평등", '"교육불평등"'),
    ("교육 불평등", '"교육 불평등"'),
    ('"이미따옴표"', '"이미따옴표"'),      # 중복으로 감싸지 않는다
    ("  공백  ", '"공백"'),
    ("", ""),
])
def test_as_phrase(raw, expected):
    assert as_phrase(raw) == expected


def test_exact_옵션이_따옴표를_씌워_전송한다(monkeypatch):
    """실측: `교육불평등` 63건(오탐 52%) → `"교육불평등"` 28건(오탐 0%)."""
    sent = []

    def fake(params):
        sent.append(dict(params))
        return json.dumps({"total": 28, "result": [samples.OFFLINE_FULL]}, ensure_ascii=False)

    c = NlClient(api_key="k", throttle=0)
    monkeypatch.setattr(c, "_call", fake)

    c.search_page("교육불평등", exact=True)
    assert sent[-1]["kwd"] == '"교육불평등"'

    c.search_page("교육불평등", exact=False)
    assert sent[-1]["kwd"] == "교육불평등"


def test_exact_는_기본값이_아니다():
    """🔴 코퍼스 수집에 exact 를 켜면 안 된다 — 실측으로 확정된 설계 결정.

    재현율 손실 평균 47%, 최악 84%(교육형평성 31→5건). 버려진 249건 중 76%가
    구성어를 모두 포함한 **관련 문헌**이었다. 원인은 한국어 복합어가 실제 표제에서
    조사·수식어로 갈라지는데(`교육의 형평성`) 구문검색이 토큰 인접을 요구하는 것.
    변형어를 3~5개로 늘려도 12건에 그쳐 기본 검색 31건에 못 미친다.

    이 테스트는 나중에 "정밀도가 좋으니 기본값으로 하자"로 되돌아가는 것을 막는다.
    """
    import inspect
    for tool in (srv.nl_search, srv.nl_collect):
        assert inspect.signature(tool).parameters["exact"].default is False
    # 도구 설명이 코퍼스 수집 부적합을 명시해야 한다
    assert "코퍼스 수집에는 부적합" in srv.nl_search.__doc__
    assert "코퍼스 수집에는 쓰지 말 것" in srv.nl_collect.__doc__
    assert "84%" in srv.nl_search.__doc__          # 최악 손실률을 숫자로 제시
    assert "특정 자료 조회" in srv.nl_collect.__doc__   # 대신 어디에 쓰는지도


def test_exact_가_수집_경로까지_전달된다(monkeypatch):
    sent = []

    def fake(params):
        sent.append(dict(params))
        return json.dumps({"total": 1, "result": [samples.OFFLINE_FULL]}, ensure_ascii=False)

    c = NlClient(api_key="k", throttle=0)
    monkeypatch.setattr(c, "_call", fake)
    monkeypatch.setattr(srv, "get_api_key", lambda: "k")
    monkeypatch.setattr(srv, "NlClient", lambda *a, **kw: c)

    srv.nl_collect(terms=["교육불평등"], exact=True, save=False)
    assert sent[0]["kwd"] == '"교육불평등"'

    sent.clear()
    srv.nl_search("교육불평등", exact=True)
    assert sent[0]["kwd"] == '"교육불평등"'


# ══ category ═════════════════════════════════════════════════════════════════
def test_category_목록에_전체가_없다():
    """실측: `category=전체` 는 오류코드 013 을 낸다. 전체 검색은 category 를 생략한다."""
    assert "전체" not in CATEGORIES
    assert len(CATEGORIES) == 12
    assert "도서" in CATEGORIES and "학위논문" in CATEGORIES


# ══ srchTarget ═══════════════════════════════════════════════════════════════
def test_검증된_srchTarget():
    """실측(2026-08-12): title·author·publisher·keyword·total 이 각각 다른 결과를 낸다.

    kwd=오욱환 → author 36 / title 13 / publisher 0 (셋이 달라 각각 해석됨이 확정)
    kwd=교육과학사 → publisher 5,973 / author 22 / total 6,095

    ⚠️ 반면 isbn·classNo·callNo 는 **조용히 전 필드 검색으로 폴백**한다.
       판별 근거: `srchTarget=isbn&kwd=오욱환` 이 0건이 아니라 total 과 같은 36건을 냈다.
       (초판은 author·publisher 까지 미지원으로 잘못 단정했다 — 주제어로 저자 검색을 해
        0건이 나온 것을 '미지원'으로 오독한 것이었다.)
    """
    assert set(SEARCH_TARGETS_VERIFIED) == {"title", "author", "publisher",
                                            "keyword", "total", "kwd"}
    assert "isbn" in SEARCH_TARGETS_FALLBACK
    assert "classNo" in SEARCH_TARGETS_FALLBACK
    doc = srv.nl_search.__doc__
    assert "폴백" in doc                    # 조용한 폴백 사실을 도구 설명이 알린다
    assert "isbn" in doc


def test_도구_설명이_핵심_함정을_알린다():
    for doc in (srv.nl_search.__doc__, srv.nl_collect.__doc__):
        assert "500" in doc                       # 상한
    # 기본 검색이 부분일치가 아니라는 사실
    assert "토큰 매칭" in srv.nl_search.__doc__
    # 서버측 연도 필터가 없다는 사실(실측)을 수집 도구가 명시한다
    assert "서버측 연도 필터는 존재하지 않는다" in srv.nl_collect.__doc__
    # exact 의 재현율 손실 경고(정정된 서술) — 옛 '오탐이 사라진다' 조언으로 되돌아가지 않도록
    assert "재현율" in srv.nl_search.__doc__
