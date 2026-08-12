"""조용한 절단 방지 회귀 — 이 프로젝트에서 **가장 중요한 테스트**.

자매 프로젝트 kci·scienceon 은 둘 다 `total` 을 파싱해놓고 버려서, 상한에 걸린 부분 집합을
전수로 오인할 수 있는 상태로 배포됐다(각각 v0.1.3 / v0.2.0 에서 뒤늦게 수정).
국립중앙도서관 API 는 한술 더 떠 **한 검색식당 500건이 하드 상한**이다
(공식 오류코드 012 DATA LIMIT 500). 실측: `교육복지` total=1,856 → 회수 500건.
"""
import json

import pytest
import samples

from nl_mcp.client import NlClient
from nl_mcp.config import API_RECORD_CAP


def _rec(i: int) -> dict:
    """id 만 다른 합성 레코드 — 중복제거가 삼키지 않도록."""
    return {**samples.OFFLINE_FULL, "id": f"ID{i:06d}", "controlNo": f"KMO{i:09d}"}


class FakeServer:
    """국립중앙도서관 검색 API 흉내 — total 은 크게 보고하되 상한까지만 내려준다."""

    def __init__(self, total: int, cap: int = API_RECORD_CAP):
        self.total = total
        self.cap = cap
        self.calls: list[dict] = []

    def __call__(self, params: dict) -> str:
        self.calls.append(dict(params))
        page = int(params["pageNum"])
        size = int(params["pageSize"])
        start = (page - 1) * size
        # 상한을 넘는 오프셋은 서버가 빈 배열로 답한다(실측 c2.py: 6페이지째부터 빈 결과)
        end = min(start + size, self.total, self.cap)
        recs = [_rec(i) for i in range(start, end)] if start < min(self.total, self.cap) else []
        return json.dumps({"total": self.total, "pageNum": page, "pageSize": size,
                           "result": recs}, ensure_ascii=False)


@pytest.fixture
def client(monkeypatch):
    def make(total: int, cap: int = API_RECORD_CAP):
        c = NlClient(api_key="test-key", throttle=0)
        fake = FakeServer(total, cap)
        monkeypatch.setattr(c, "_call", fake)
        c._fake = fake
        return c
    return make


# ── 500건 상한 ───────────────────────────────────────────────────────────────
def test_상한초과시_cap_hit_와_경고가_나온다(client):
    """total 1,856 / 회수 500 — 실측 '교육복지' 사례 그대로."""
    c = client(total=1856)
    recs, meta = c.search_meta("교육복지", max_records=2000)

    assert meta["total"] == 1856
    assert meta["fetched"] == API_RECORD_CAP == len(recs)
    assert meta["truncated"] is True
    assert meta["cap_hit"] is True
    assert meta["stopped_reason"] == "cap"

    w = meta["warning"]
    assert "1,856" in w and "500" in w
    assert "쪼개" in w              # 처방을 반드시 알려준다
    assert "max_records 를 올려도" in w   # 상한은 max_records 로 못 푼다는 점


def test_상한초과여도_요청은_500건을_넘지_않는다(client):
    """501건째를 요청하면 API 가 오류코드 012 를 낸다 — 애초에 요청하지 않는다."""
    c = client(total=5000)
    c.search_meta("교육복지", max_records=3000)
    for p in c._fake.calls:
        assert (int(p["pageNum"]) - 1) * int(p["pageSize"]) < API_RECORD_CAP


# ── 상한 미만 ────────────────────────────────────────────────────────────────
def test_상한미만_전건회수는_절단없음(client):
    """실측 '교육격차' total=244 — 전건 회수됐다."""
    c = client(total=244)
    recs, meta = c.search_meta("교육격차", max_records=500)
    assert len(recs) == 244
    assert meta["truncated"] is False
    assert meta["cap_hit"] is False
    assert "warning" not in meta
    assert meta["stopped_reason"] == "exhausted"


def test_max_records_로_잘리면_다른_처방을_준다(client):
    """이쪽은 max_records 를 올리면 해결된다 — cap_hit 과 구분돼야 한다."""
    c = client(total=244)
    recs, meta = c.search_meta("교육격차", max_records=100)
    assert len(recs) == 100
    assert meta["truncated"] is True
    assert meta["cap_hit"] is False
    assert "max_records 를 올려" in meta["warning"]
    assert "쪼개" not in meta["warning"]


def test_결과0건은_절단이_아니다(client):
    c = client(total=0)
    recs, meta = c.search_meta("없는검색어")
    assert recs == [] and meta["truncated"] is False and meta["cap_hit"] is False


# ── 중복제거·무한루프 방지 ───────────────────────────────────────────────────
def test_같은_레코드가_반복돼도_무한루프에_빠지지_않는다(monkeypatch):
    c = NlClient(api_key="test-key", throttle=0)
    monkeypatch.setattr(c, "_call", lambda p: json.dumps(
        {"total": 9999, "result": [_rec(1)]}, ensure_ascii=False))
    recs, meta = c.search_meta("반복", max_records=500)
    assert len(recs) == 1
    assert meta["stopped_reason"] == "empty_page"
    assert meta["truncated"] is True     # total 9999 대비 1건 — 절단으로 보고


# ── 다중 검색어 합집합 ───────────────────────────────────────────────────────
def test_합집합_수집이_상한걸린_검색어를_지목한다(monkeypatch):
    totals = {"교육복지": 1856, "교육격차": 244, "교육기회균등": 4}

    c = NlClient(api_key="test-key", throttle=0)
    offset = {"교육복지": 0, "교육격차": 10_000, "교육기회균등": 20_000}

    def fake(params):
        term = params["kwd"]
        total = totals[term]
        page, size = int(params["pageNum"]), int(params["pageSize"])
        start = (page - 1) * size
        end = min(start + size, total, API_RECORD_CAP)
        base = offset[term]
        recs = [_rec(base + i) for i in range(start, end)] if start < min(total, API_RECORD_CAP) else []
        return json.dumps({"total": total, "result": recs}, ensure_ascii=False)

    monkeypatch.setattr(c, "_call", fake)
    recs, meta = c.search_terms_meta(list(totals), max_records=2000)

    assert meta["cap_hit_terms"] == ["교육복지"]
    assert meta["union_upper_bound"] == 1856 + 244 + 4
    assert len(recs) == API_RECORD_CAP + 244 + 4     # 검색어별 id 공간이 달라 겹침 없음
    assert "교육복지" in meta["warning"]
    assert meta["axes_run"] == 3


def test_연도필터는_로컬후처리라_상한을_풀어주지_않는다(monkeypatch):
    """중요 — 연도 필터를 걸어도 API 는 여전히 500건까지만 준다.

    필터는 이미 받은 500건 안에서만 걸리므로, 상한을 우회하려면 **서버측 분할**이 필요하다.
    """
    c = NlClient(api_key="test-key", throttle=0)

    def fake(params):
        page, size = int(params["pageNum"]), int(params["pageSize"])
        start = (page - 1) * size
        end = min(start + size, API_RECORD_CAP)
        recs = []
        for i in range(start, end):
            # 절반은 연도 없음(실측 5.2% 보다 과장한 값 — 탈락 집계 확인용)
            year = "" if i % 2 else "2015"
            recs.append({**_rec(i), "pubYearInfo": year})
        return json.dumps({"total": 1856, "result": recs}, ensure_ascii=False)

    monkeypatch.setattr(c, "_call", fake)
    recs, meta = c.search_terms_meta(["교육복지"], year_from=2000, year_to=2020,
                                     max_records=2000)

    assert meta["cap_hit_terms"] == ["교육복지"]      # 필터를 걸어도 상한은 그대로
    assert meta["axes"][0]["fetched"] == API_RECORD_CAP
    assert meta["year_missing_dropped"] == API_RECORD_CAP // 2
    assert len(recs) == API_RECORD_CAP // 2
    assert all(r.pub_year == "2015" for r in recs)


def test_contains_후처리_집계(client):
    """fetched(회수)와 returned(필터 후)를 구분한다 — 섞으면 절단과 필터가 뒤엉킨다."""
    c = client(total=50)
    _, meta = c.search_meta("교육", contains=["존재하지않는문자열"])
    assert meta["contains_filtered_out"] == 50
    assert meta["fetched"] == 50      # API 로부터 실제로 받은 건수
    assert meta["returned"] == 0      # 필터를 거쳐 최종 반환한 건수
