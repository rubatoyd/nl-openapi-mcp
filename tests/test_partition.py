"""자료구분 분할 수집 — 500 상한의 부분 우회.

실측 근거(2026-08-12): 자료구분별 total 의 합이 category 생략 시 total 과 **정확히 일치**한다.
  교육복지 7,028=7,028 · 교육 784,809=784,809 · 교육불평등 382=382
→ 자료구분은 겹치지 않는 완전 분할이므로 쪼개서 합치면 회수량이 는다.
실측 회복량: 교육복지 500 → 2,134건(4.3배) · 교육 500 → 4,559건(9.1배)
"""
import json

import pytest
import samples

from nl_mcp import server as srv
from nl_mcp.client import NlClient
from nl_mcp.config import API_RECORD_CAP, CATEGORIES

# 실측 분포 — '교육복지' (합 7,028)
LIVE_교육복지 = {
    "기사": 3879, "도서": 1856, "학위논문": 659, "잡지/학술지": 193,
    "외부연계자료": 185, "웹사이트": 149, "멀티미디어": 94, "신문": 7,
    "기타": 5, "해외기록물": 1, "고문헌": 0, "장애인자료": 0,
}


class CategoryServer:
    """자료구분별 total 을 흉내내고, 상한까지만 레코드를 준다."""

    def __init__(self, per_category: dict, no_category_total: int | None = None):
        self.per = per_category
        self.no_cat = (no_category_total if no_category_total is not None
                       else sum(per_category.values()))
        self.calls = []

    def __call__(self, params):
        self.calls.append(dict(params))
        cat = params.get("category")
        total = self.per.get(cat, 0) if cat else self.no_cat
        page, size = int(params["pageNum"]), int(params["pageSize"])
        start = (page - 1) * size
        end = min(start + size, total, API_RECORD_CAP)
        if start >= min(total, API_RECORD_CAP):
            # 실측: 0건이면 result 키가 빠진다
            return json.dumps({"total": total, "kwd": params.get("kwd"),
                               "pageNum": page, "pageSize": size,
                               "category": cat, "sort": ""}, ensure_ascii=False)
        # 자료구분마다 id 공간을 분리해 합집합이 실제로 늘어나게 한다
        base = (hash(cat or "") % 1000) * 100_000
        recs = [{**samples.OFFLINE_FULL, "id": f"ID{base + i}"} for i in range(start, end)]
        return json.dumps({"total": total, "result": recs}, ensure_ascii=False)


@pytest.fixture
def client(monkeypatch):
    def make(per=None, no_cat=None):
        c = NlClient(api_key="k", throttle=0)
        fake = CategoryServer(per if per is not None else LIVE_교육복지, no_cat)
        monkeypatch.setattr(c, "_call", fake)
        c._fake = fake
        return c
    return make


# ══ 분할 자체 ════════════════════════════════════════════════════════════════
def test_분할하면_상한보다_많이_회수한다(client):
    c = client()
    recs, meta = c.search_by_category_meta("교육복지", max_records=10_000)

    assert meta["partition_total"] == 7028            # 자료구분별 합
    assert meta["recoverable_upper_bound"] == sum(
        min(v, API_RECORD_CAP) for v in LIVE_교육복지.values())
    assert meta["fetched"] == meta["recoverable_upper_bound"] == 2134
    assert meta["unreachable"] == 7028 - 2134
    assert len(recs) == 2134


def test_여전히_상한_넘는_자료구분을_지목한다(client):
    c = client()
    _, meta = c.search_by_category_meta("교육복지", max_records=10_000)
    assert set(meta["capped_categories"]) == {"기사", "도서", "학위논문"}
    w = meta["warning"]
    assert "전수는 아닙니다" in w
    assert "4,894" in w                                # 도달 불가 건수를 명시
    for cat in ("기사", "도서", "학위논문"):
        assert cat in w


def test_결과가_없는_자료구분은_보고에서_빠진다(client):
    c = client()
    _, meta = c.search_by_category_meta("교육복지", max_records=10_000)
    reported = {p["category"] for p in meta["partitions"]}
    assert "고문헌" not in reported and "장애인자료" not in reported
    assert len(reported) == 10


def test_전부_상한_아래면_경고가_없다(client):
    """실측 '교육불평등' — 자료구분별 전부 500 미만이라 분할해도 손실이 없다."""
    c = client({"기사": 234, "학위논문": 66, "도서": 63, "잡지/학술지": 9,
                "멀티미디어": 4, "웹사이트": 3, "외부연계자료": 3})
    recs, meta = c.search_by_category_meta("교육불평등", max_records=10_000)
    assert meta["fetched"] == 382 == meta["partition_total"]
    assert meta["unreachable"] == 0
    assert meta["capped_categories"] == []
    assert "warning" not in meta


def test_max_records_를_넘기지_않는다(client):
    c = client()
    recs, meta = c.search_by_category_meta("교육복지", max_records=300)
    assert len(recs) == 300


# ══ 수집 경로 통합 ═══════════════════════════════════════════════════════════
def test_auto_partition_이_꺼져있으면_상한에_머문다(client):
    c = client()
    recs, meta = c.search_terms_meta(["교육복지"], max_records=10_000)
    assert len(recs) == API_RECORD_CAP
    assert meta["cap_hit_terms"] == ["교육복지"]
    assert meta["partitioned_terms"] == []
    assert "auto_partition=True" in meta["warning"]      # 처방을 알려준다


def test_auto_partition_이_켜지면_분할한다(client):
    c = client()
    recs, meta = c.search_terms_meta(["교육복지"], max_records=10_000, auto_partition=True)
    assert len(recs) == 2134
    assert meta["partitioned_terms"] == ["교육복지"]
    assert "분할해 재수집했습니다" in meta["warning"]
    assert "기사" in meta["warning"]                     # 남은 손실도 함께


def test_category_를_지정했으면_분할하지_않는다(client):
    """이미 자료구분을 고른 상태에서는 더 쪼갤 축이 없다."""
    c = client()
    recs, meta = c.search_terms_meta(["교육복지"], category="도서",
                                     max_records=10_000, auto_partition=True)
    assert len(recs) == API_RECORD_CAP
    assert meta["partitioned_terms"] == []
    assert "검색어를 더 좁게" in meta["warning"]


def test_상한에_안_걸리면_분할하지_않는다(client):
    c = client({"도서": 63, "기사": 234})
    recs, meta = c.search_terms_meta(["교육불평등"], max_records=10_000, auto_partition=True)
    assert meta["partitioned_terms"] == []
    assert meta["cap_hit_terms"] == []
    assert len(c._fake.calls) <= 2                       # 불필요한 호출 없음


def test_분할이_이득이_없으면_교체하지_않는다(monkeypatch):
    """자료구분 조회가 오히려 적게 준다면 원래 결과를 유지한다."""
    c = NlClient(api_key="k", throttle=0)

    def fake(params):
        cat = params.get("category")
        total = 501 if not cat else 0        # 자료구분별로는 하나도 안 나온다
        page, size = int(params["pageNum"]), int(params["pageSize"])
        start = (page - 1) * size
        end = min(start + size, total, API_RECORD_CAP)
        if start >= min(total, API_RECORD_CAP):
            return json.dumps({"total": total, "sort": ""}, ensure_ascii=False)
        recs = [{**samples.OFFLINE_FULL, "id": f"X{i}"} for i in range(start, end)]
        return json.dumps({"total": total, "result": recs}, ensure_ascii=False)

    monkeypatch.setattr(c, "_call", fake)
    recs, meta = c.search_terms_meta(["x"], max_records=10_000, auto_partition=True)
    assert len(recs) == API_RECORD_CAP        # 원래 결과 유지
    assert meta["partitioned_terms"] == []


# ══ 도구 노출 ════════════════════════════════════════════════════════════════
def test_nl_collect_에_auto_partition_이_있다():
    import inspect
    sig = inspect.signature(srv.nl_collect).parameters
    assert "auto_partition" in sig
    assert sig["auto_partition"].default is False       # 호출 수가 느니 기본은 꺼둔다
    doc = srv.nl_collect.__doc__
    assert "4.3배" in doc and "전수는 아니다" in doc


def test_분할_대상_자료구분은_설정의_12종이다(client):
    c = client()
    _, meta = c.search_by_category_meta("교육복지", max_records=10_000)
    queried = {call.get("category") for call in c._fake.calls}
    assert queried == set(CATEGORIES)
