"""`extra_params` 패스스루 — 미검증 API 파라미터를 코드 수정 없이 실험할 수 있어야 한다.

고급검색 UI 에 있는 기능(발행년 범위·제목 완전일치·필드 간 AND/OR)이 API 에 어떤 이름으로
노출되는지 확인되지 않았다. 이름이 밝혀지면 즉시 쓸 수 있도록 통로만 열어 둔다.
"""
import json

import pytest
import samples

from nl_mcp import server as srv
from nl_mcp.client import NlClient
from nl_mcp.config import CATEGORIES, SEARCH_FIELD_LABELS


@pytest.fixture
def spy(monkeypatch):
    """실제 전송 파라미터를 붙잡는다."""
    seen = []

    def fake(params):
        seen.append(dict(params))
        return json.dumps({"total": 1, "result": [samples.OFFLINE_FULL]}, ensure_ascii=False)

    c = NlClient(api_key="k", throttle=0)
    monkeypatch.setattr(c, "_call", fake)
    monkeypatch.setattr(srv, "get_api_key", lambda: "k")
    monkeypatch.setattr(srv, "NlClient", lambda *a, **k: c)
    return seen


def test_nl_search_가_임의_파라미터를_그대로_전달한다(spy):
    srv.nl_search("교육", extra_params={"startPubYear": "2020", "endPubYear": "2020"})
    assert spy[0]["startPubYear"] == "2020"
    assert spy[0]["endPubYear"] == "2020"
    assert spy[0]["kwd"] == "교육"          # 기본 파라미터도 유지


def test_nl_collect_도_전달한다(spy):
    srv.nl_collect(terms=["교육"], save=False, extra_params={"matchType": "exact"})
    assert spy[0]["matchType"] == "exact"


def test_빈값은_전달하지_않는다(spy):
    srv.nl_search("교육", extra_params={"a": "", "b": None, "c": "v"})
    assert "a" not in spy[0] and "b" not in spy[0]
    assert spy[0]["c"] == "v"


def test_sort_는_도구에서_제거됐다():
    """실측: `sort` 는 어떤 값을 줘도 결과 순서가 바뀌지 않는다(미지원).

    지원하지 않는 파라미터를 도구 인자로 노출하면 '정렬했다'는 착각을 만든다.
    실험이 필요하면 extra_params 로 넘길 수 있다.
    """
    import inspect
    assert "sort" not in inspect.signature(srv.nl_search).parameters


def test_미지원_파라미터도_extra_params_로는_보낼_수_있다(spy):
    srv.nl_search("교육", extra_params={"sort": "pubyear_desc", "x": "1"})
    assert spy[0]["sort"] == "pubyear_desc" and spy[0]["x"] == "1"


def test_extra_params_없이도_동작한다(spy):
    out = srv.nl_search("교육")
    assert out["count"] == 1
    assert "startPubYear" not in spy[0]


def test_카테고리_목록은_API_가_받는_12종이다():
    """UI 는 '전체' 탭을 포함해 13종이지만 **API 는 '전체' 를 거부한다**(오류 013, 실측)."""
    assert len(CATEGORIES) == 12
    assert "전체" not in CATEGORIES
    for expected in ["도서", "고문헌", "학위논문", "잡지/학술지", "신문", "기사", "멀티미디어",
                     "장애인자료", "웹사이트", "해외기록물", "외부연계자료", "기타"]:
        assert expected in CATEGORIES


def test_검색필드_라벨이_지원여부를_명시한다():
    """미지원 필드는 오류가 아니라 조용히 전 필드 검색으로 폴백하므로 라벨에 표시한다.

    실측(2026-08-12): title·author·publisher·keyword·total 은 지원,
    isbn·classNo·callNo 는 폴백.
    """
    assert SEARCH_FIELD_LABELS["title"].startswith("제목")
    for supported in ("author", "publisher", "keyword", "total"):
        assert "미지원" not in SEARCH_FIELD_LABELS[supported]
    for fallback in ("isbn", "classNo", "callNo"):
        assert "미지원" in SEARCH_FIELD_LABELS[fallback]
        assert "폴백" in SEARCH_FIELD_LABELS[fallback]
