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
    """**모집단 기반** 가짜 서버 — 자식 조각이 부모의 부분집합이 되도록 실제 의미론을 재현한다.

    고정된 레코드 모집단을 만들어 두고 질의마다 걸러 낸다. 그래서
      · 어떤 합집합도 root total 을 넘을 수 없고(셀별 id 공간 분리 모델의 오류를 피한다)
      · 상한(500)이 조각마다 따로 걸리며
      · **licYn 이 빈 레코드는 어떤 값으로도 선택되지 않는다**(실측 동작)
    실측 구조를 본떴다 — 관리기관은 완전분할(본관 6 : 디지털도서관 4),
    이용조건 코드는 절반만 값이 있고 나머지는 비어 있다.
    """

    def __init__(self, per_category: dict, no_category_total: int | None = None):
        self.per = per_category
        self.calls = []
        self.pop = []                       # 모집단
        n = 0
        for cat, t in per_category.items():
            for i in range(t):
                mn = "본관" if i % 10 < 6 else "디지털도서관"
                lic = ["F", "N", "S"][i % 3] if i % 2 == 0 else ""   # 절반은 코드 없음
                self.pop.append({"id": f"ID{n:07d}", "category": cat,
                                 "manageName": mn, "licYn": lic})
                n += 1
        self.no_cat = (no_category_total if no_category_total is not None
                       else len(self.pop))

    def _match(self, params):
        out = self.pop
        for k in ("category", "manageName", "licYn"):
            v = params.get(k)
            if v:
                out = [r for r in out if r[k] == v]
        return out

    def __call__(self, params):
        self.calls.append(dict(params))
        hits = self._match(params)
        total = len(hits)
        page, size = int(params["pageNum"]), int(params["pageSize"])
        start, end = (page - 1) * size, min(page * size, total, API_RECORD_CAP)
        if start >= min(total, API_RECORD_CAP):
            # 실측: 0건이면 result 키가 빠진다
            return json.dumps({"total": total, "kwd": params.get("kwd"),
                               "pageNum": page, "pageSize": size,
                               "category": params.get("category"), "sort": ""},
                              ensure_ascii=False)
        recs = [{**samples.OFFLINE_FULL, "id": r["id"], "manageName": r["manageName"],
                 "licYn": r["licYn"]} for r in hits[start:end]]
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
    """기본 깊이 2(category → manageName)로 재귀 분할한다."""
    c = client()
    recs, meta = c.search_terms_meta(["교육복지"], max_records=99_999, auto_partition=True)
    assert len(recs) > API_RECORD_CAP * 5          # 500 → 3천대
    assert meta["partitioned_terms"] == ["교육복지"]
    assert "분할해 재수집했습니다" in meta["warning"]


@pytest.mark.parametrize("depth, floor", [(1, 2000), (2, 3000), (3, 5000)])
def test_깊이를_올릴수록_더_회수한다(client, depth, floor):
    """실측(교육복지 7,028건): 깊이1 30% → 깊이2 46% → 깊이3 67%.

    부모 조각도 합집합에 넣기 때문에 축이 불완전해도(licYn 은 빈 값을 못 잡는다)
    깊이를 올려서 손해가 나지 않는다.
    """
    c = client()
    recs, meta = c.search_partitioned_meta("교육복지", max_depth=depth, max_records=99_999)
    assert len(recs) >= floor
    assert len(recs) <= meta["root_total"]        # 합집합은 전체를 넘을 수 없다
    assert meta["max_depth"] == depth


def test_깊이가_깊을수록_요청이_는다(client):
    """회복량과 호출 비용의 교환관계를 고정한다 — 공짜가 아님을 명시."""
    reqs = []
    for depth in (1, 2, 3):
        c = client()
        _, meta = c.search_partitioned_meta("교육복지", max_depth=depth, max_records=99_999)
        reqs.append(meta["requests"])
    assert reqs[0] < reqs[1] < reqs[2]
    assert reqs[0] <= 15                          # 깊이1 은 자료구분 12개 + 루트


def test_부모_조각도_합집합에_들어간다(client):
    """licYn 처럼 값이 빈 레코드를 못 잡는 축이 있어도 손해가 없어야 한다."""
    c = client()
    shallow, _ = c.search_partitioned_meta("교육복지", max_depth=1, max_records=99_999)
    deep, _ = c.search_partitioned_meta("교육복지", max_depth=3, max_records=99_999)
    assert {h.dedup_key() for h in shallow} <= {h.dedup_key() for h in deep}


def test_도달불가_건수를_보고한다(client):
    c = client()
    recs, meta = c.search_partitioned_meta("교육복지", max_depth=2, max_records=99_999)
    assert meta["unreachable"] == meta["root_total"] - len(recs)
    assert "도달불가" in meta["warning"]
    assert "→".join(meta["axes"]) in meta["warning"]


def test_호출자가_고정한_축은_다시_쪼개지_않는다(client):
    """category=도서 로 이미 고른 상태면 category 축은 건너뛴다."""
    c = client()
    recs, meta = c.search_partitioned_meta("교육복지", category="도서", max_depth=2,
                                           max_records=99_999)
    assert meta["root_total"] == LIVE_교육복지["도서"]
    for call in c._fake.calls:
        assert call.get("category") == "도서"


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
def test_nl_collect_에_분할_인자가_노출된다():
    import inspect
    sig = inspect.signature(srv.nl_collect).parameters
    assert sig["auto_partition"].default is False       # 호출 수가 느니 기본은 꺼둔다
    assert sig["partition_depth"].default == 2          # 켰을 때의 기본 깊이
    doc = srv.nl_collect.__doc__
    # 회복량과 호출 비용을 둘 다 숫자로 제시해야 한다 — 공짜가 아님을 알려야 하므로
    assert "67%" in doc and "60회" in doc
    assert "전수는 여전히 불가능하다" in doc
    # 어떤 축을 쓰는지, 어느 축이 불완전한지도 밝힌다
    assert "manageName" in doc and "licYn" in doc


@pytest.mark.parametrize("depth, expect", [(0, 1), (1, 1), (3, 3), (9, 3)])
def test_partition_depth_는_1_3_으로_클램프된다(monkeypatch, depth, expect):
    seen = {}

    class C:
        def __init__(self, *a, **k):
            pass

        def search_terms_meta(self, terms, **kw):
            seen["depth"] = kw.get("partition_depth")
            return [], {"axes": [], "truncated": False, "returned": 0}

    monkeypatch.setattr(srv, "get_api_key", lambda: "k")
    monkeypatch.setattr(srv, "NlClient", C)
    srv.nl_collect(kwd="x", auto_partition=True, partition_depth=depth, save=False)
    assert seen["depth"] == expect


def test_분할_대상_자료구분은_설정의_12종이다(client):
    c = client()
    _, meta = c.search_by_category_meta("교육복지", max_records=10_000)
    queried = {call.get("category") for call in c._fake.calls}
    assert queried == set(CATEGORIES)
