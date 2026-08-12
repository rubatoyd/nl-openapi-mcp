"""적대적 검증(2026-08-12)에서 검출된 결함 4종의 회귀 테스트.

실제 로컬 HTTP 서버에 9,282회 검사를 돌려 나온 것들이다. 전부 오프라인 재현이 가능하도록
여기에 고정한다. 검출 경위는 docs/작업일지.md 참조.
"""
import json
from pathlib import Path

import pytest
import samples

from nl_mcp.client import NlClient
from nl_mcp.config import API_RECORD_CAP, MAX_PAGE_SIZE
from nl_mcp.exporters import export, safe_name
from nl_mcp.parser import ParseError, parse_holding, parse_search_response


# ══ ① resultCode 거짓 양성 ═══════════════════════════════════════════════════
# 국내 공공 API 는 resultCode 를 **성공 표시**로도 쓴다(`"00"` = 정상).
# 이것을 오류코드로 해석하면 zfill 을 거쳐 "000"(SYSTEM ERROR)이 되어
# 멀쩡한 응답 전체가 오류로 둔갑한다.
@pytest.mark.parametrize("code", ["00", "0000", 200, "200", "OK", "success"])
def test_성공응답의_resultCode_를_오류로_오판하지_않는다(code):
    payload = {"resultCode": code, "total": 50, "result": [samples.OFFLINE_FULL]}
    total, recs, _ = parse_search_response(payload)
    assert total == 50
    assert len(recs) == 1


def test_레코드가_실려있으면_오류코드가_있어도_버리지_않는다():
    """오류 봉투 철자가 미검증이므로, 데이터가 있으면 데이터를 신뢰한다."""
    payload = {"errorCode": "012", "total": 1856, "result": [samples.OFFLINE_FULL]}
    total, recs, _ = parse_search_response(payload)
    assert total == 1856 and len(recs) == 1


def test_레코드가_없을_때는_오류코드를_그대로_올린다():
    with pytest.raises(ParseError, match="INVALID KEY"):
        parse_search_response({"errorCode": "011", "result": []})


def test_봉투가_아닌_응답은_여전히_오류다():
    """조용한 통과를 막는 방어선.

    ⚠️ 단, `total` 이 있으면서 `result` 만 없는 것은 **정상적인 0건**이다(라이브 실측).
       그 구분은 test_parser.py::test_결과_0건이면_result_키가_없다_실측 가 고정한다.
    """
    with pytest.raises(ParseError, match="result"):
        parse_search_response({"resultCode": "00", "msg": "no envelope"})


# ══ ② 호출 폭주 ══════════════════════════════════════════════════════════════
class _CountingServer:
    def __init__(self, total):
        self.total = total
        self.calls = []

    def __call__(self, params):
        self.calls.append(dict(params))
        page, size = int(params["pageNum"]), int(params["pageSize"])
        start = (page - 1) * size
        end = min(start + size, self.total, API_RECORD_CAP)
        recs = ([{**samples.OFFLINE_FULL, "id": f"ID{i:06d}"} for i in range(start, end)]
                if start < min(self.total, API_RECORD_CAP) else [])
        return json.dumps({"total": self.total, "result": recs}, ensure_ascii=False)


@pytest.mark.parametrize("page_size, max_records", [(1, 1000), (1, 500), (5, 500), (10, 3000)])
def test_작은_page_size_가_호출_폭주를_일으키지_않는다(monkeypatch, page_size, max_records):
    """page_size=1·max_records=1000 이 **499회 요청**을 유발했다.

    page_size 는 전송 단위일 뿐 결과를 바꾸지 않으므로, 여러 페이지가 필요하면 최대로 올린다.
    """
    c = NlClient(api_key="k", throttle=0)
    fake = _CountingServer(499)
    monkeypatch.setattr(c, "_call", fake)
    recs, meta = c.search_meta("교육", max_records=max_records, page_size=page_size)

    assert len(recs) == 499                       # 결과는 동일해야 한다
    assert len(fake.calls) <= 8, f"{len(fake.calls)}회 요청 — 폭주"
    assert meta["requests"] == len(fake.calls)
    assert meta["page_size"] == MAX_PAGE_SIZE     # 자동 상향


def test_한_페이지면_요청한_page_size_를_유지한다(monkeypatch):
    c = NlClient(api_key="k", throttle=0)
    fake = _CountingServer(500)
    monkeypatch.setattr(c, "_call", fake)
    _, meta = c.search_meta("교육", max_records=5, page_size=5)
    assert meta["page_size"] == 5
    assert len(fake.calls) == 1


def test_요청_횟수_절대_상한이_있다(monkeypatch):
    """서버가 끝없이 새 레코드를 주더라도 무한히 요청하지 않는다."""
    c = NlClient(api_key="k", throttle=0)
    n = {"i": 0}

    def endless(params):
        size = int(params["pageSize"])
        out = [{**samples.OFFLINE_FULL, "id": f"X{n['i'] + j}"} for j in range(size)]
        n["i"] += size
        return json.dumps({"total": 10 ** 9, "result": out}, ensure_ascii=False)

    monkeypatch.setattr(c, "_call", endless)
    recs, meta = c.search_meta("교육", max_records=10 ** 6)
    assert len(recs) == API_RECORD_CAP
    assert meta["requests"] <= 10


# ══ ③ fetched / returned 분리와 경고문 ═══════════════════════════════════════
def test_경고문은_회수량_기준으로_서술한다(monkeypatch):
    """필터로 줄어든 수로 서술하면 'API 가 그만큼만 줬다'로 오독된다."""
    c = NlClient(api_key="k", throttle=0)
    monkeypatch.setattr(c, "_call", _CountingServer(1856))
    recs, meta = c.search_meta("교육복지", max_records=3000,
                               contains=["존재하지않는문자열"])

    assert meta["fetched"] == API_RECORD_CAP      # 실제 회수
    assert meta["returned"] == 0                  # 필터 후
    assert len(recs) == 0
    w = meta["warning"]
    assert "500건만 회수" in w                     # 회수량 기준 서술
    assert "1,856" in w
    assert "절단과 무관" in w                       # 필터 감소는 절단이 아님을 명시
    assert meta["contains_filtered_out"] == API_RECORD_CAP
    assert "최종 0건" in w                          # 필터 후 결과도 함께 보고


def test_필터가_없으면_경고문에_필터_설명이_붙지_않는다(monkeypatch):
    c = NlClient(api_key="k", throttle=0)
    monkeypatch.setattr(c, "_call", _CountingServer(1856))
    _, meta = c.search_meta("교육복지", max_records=3000)
    assert "절단과 무관" not in meta["warning"]
    assert meta["fetched"] == meta["returned"] == API_RECORD_CAP


# ══ ④ 출력 경로 이탈 ═════════════════════════════════════════════════════════
@pytest.mark.parametrize("bad", [
    "../escaped", "..\\escaped2", "sub/dir/x", "/abs/path", "C:\\Windows\\evil",
    "a\x00b", "CON", "PRN", "nul", " . ", "...", "", "  ",
])
def test_출력_파일명이_디렉터리를_벗어나지_못한다(tmp_path, bad):
    """name='../escaped' 가 out_dir **밖에** 파일을 썼다."""
    recs = [parse_holding(samples.OFFLINE_FULL)]
    target = tmp_path / "inside"
    paths = export(recs, ["json"], str(target), bad)
    for p in paths:
        rp = Path(p).resolve()
        assert rp.parent == target.resolve(), f"{bad!r} → {rp} 가 밖으로 벗어남"
        assert rp.exists()


def test_검색어가_그대로_파일명이_되어도_안전하다(tmp_path):
    recs = [parse_holding(samples.OFFLINE_FULL)]
    for term in ["../../pwn", "a/b", "교육 불평등", "학력격차/디지털"]:
        p = Path(export(recs, ["json"], str(tmp_path / "o"), f"nl_{term}")[0]).resolve()
        assert p.parent == (tmp_path / "o").resolve()


@pytest.mark.parametrize("raw, expect_not", [
    ("../x", ".."), ("a/b", "/"), ("a\\b", "\\"), ("a:b", ":"), ("a\x00b", "\x00"),
])
def test_safe_name_이_위험문자를_제거한다(raw, expect_not):
    assert expect_not not in safe_name(raw)


def test_safe_name_은_빈값이면_대체값을_쓴다():
    for empty in ["", "   ", "...", " . "]:
        assert safe_name(empty) == "nl_output"


def test_safe_name_은_한글을_보존한다():
    assert "교육불평등" in safe_name("교육불평등 수집")
