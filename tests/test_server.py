"""MCP 도구 계약 — 예외 누수 금지 · annotations · 자격증명 누락 처리."""
import asyncio

import pytest
import samples

from nl_mcp import server as srv


@pytest.fixture(autouse=True)
def _no_key(monkeypatch):
    """기본은 '키 없음' 상태 — 실수로 라이브 호출이 나가지 않게."""
    monkeypatch.delenv("NL_API_KEY", raising=False)
    monkeypatch.setattr(srv, "get_api_key", lambda: None)


def _tools() -> dict:
    return {t.name: t for t in asyncio.run(srv.mcp.list_tools())}


# ── annotations ──────────────────────────────────────────────────────────────
def test_도구_3종이_등록된다():
    assert set(_tools()) == {"nl_status", "nl_search", "nl_collect"}


@pytest.mark.parametrize("name", ["nl_status", "nl_search", "nl_collect"])
def test_모든_도구가_openWorld_를_선언한다(name):
    a = _tools()[name].annotations
    assert a is not None, f"{name} 에 annotations 가 없다"
    assert a.openWorldHint is True


def test_조회도구는_읽기전용_수집도구는_쓰기_비파괴():
    t = _tools()
    assert t["nl_status"].annotations.readOnlyHint is True
    assert t["nl_search"].annotations.readOnlyHint is True
    # 파일을 만드므로 읽기전용이 아니지만, 기존 데이터를 지우지는 않는다
    assert t["nl_collect"].annotations.readOnlyHint is False
    assert t["nl_collect"].annotations.destructiveHint is False


# ── 예외 누수 금지 ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("call", [
    lambda: srv.nl_search("교육불평등"),
    lambda: srv.nl_collect(terms=["교육불평등"]),
])
def test_키가_없으면_조회도구는_error_를_돌려준다(call):
    """scienceon 은 자격증명 누락 RuntimeError 를 프로토콜 밖으로 흘린 전례가 있다."""
    out = call()
    assert isinstance(out, dict)
    assert "error" in out
    assert "NL_API_KEY" in out["error"]
    assert "hint" in out          # 발급 경로를 함께 알려준다


def test_키가_없으면_status_는_진단결과를_돌려준다():
    """status 는 '실패'가 아니라 **상태 보고**다 — error 대신 구조화된 진단을 준다."""
    out = srv.nl_status()
    assert isinstance(out, dict)
    assert out["has_api_key"] is False
    assert out["ok"] is False
    assert "NL_API_KEY" in out["note"]
    assert out["api_record_cap"] == 500


def test_어떤_예외도_새지_않는다(monkeypatch):
    monkeypatch.setattr(srv, "get_api_key", lambda: "test-key")

    class Boom:
        def __init__(self, *a, **k):
            raise ValueError("터졌다")

    monkeypatch.setattr(srv, "NlClient", Boom)
    for out in (srv.nl_status(), srv.nl_search("x"), srv.nl_collect(kwd="x")):
        assert isinstance(out, dict) and "error" in out
        assert "터졌다" in out["error"]


def test_검색어가_비면_오류를_돌려준다(monkeypatch):
    monkeypatch.setattr(srv, "get_api_key", lambda: "test-key")
    out = srv.nl_collect(terms=["  ", ""])
    assert "error" in out and "검색어" in out["error"]


# ── 응답 계약 ────────────────────────────────────────────────────────────────
def test_검색응답이_total_과_cap_hit_을_싣는다(monkeypatch):
    monkeypatch.setattr(srv, "get_api_key", lambda: "test-key")

    class C:
        def __init__(self, *a, **k):
            pass

        def search_page(self, kwd, **kw):
            return 1856, [_holding()], {"pageNum": 1}

    monkeypatch.setattr(srv, "NlClient", C)
    out = srv.nl_search("교육복지", rows=1)
    assert out["total"] == 1856
    assert out["cap_hit"] is True
    assert "500" in out["warning"] and "쪼개" in out["warning"]


def _holding():
    from nl_mcp.parser import parse_holding
    return parse_holding(samples.OFFLINE_FULL)


def test_저장하지_않는_미리보기(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "get_api_key", lambda: "test-key")

    class C:
        def __init__(self, *a, **k):
            pass

        def search_terms_meta(self, terms, **kw):
            return [_holding()], {"axes": [], "truncated": False, "returned": 1}

    monkeypatch.setattr(srv, "NlClient", C)
    out = srv.nl_collect(terms=["교육불평등"], save=False)
    assert "files" not in out
    assert len(out["preview"]) == 1
    assert out["preview"][0]["title"]
