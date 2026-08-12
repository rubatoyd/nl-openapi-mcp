"""파서 회귀 — 전부 **실응답 표본**으로 검증한다(추정 금지)."""
import pytest
import samples

from nl_mcp.models import normalize_pub_year
from nl_mcp.parser import ParseError, clean_html, parse_holding, parse_search_response


# ── 필드 매핑 ────────────────────────────────────────────────────────────────
def test_인쇄자료_전체필드_매핑():
    h = parse_holding(samples.OFFLINE_FULL)
    assert h.record_id == samples.OFFLINE_FULL["id"]
    assert h.control_no == samples.OFFLINE_FULL["controlNo"]
    assert h.title == samples.OFFLINE_FULL["titleInfo"]
    assert h.isbn == samples.OFFLINE_FULL["isbn"]
    assert h.call_no == samples.OFFLINE_FULL["callNo"]
    assert h.kdc_code == samples.OFFLINE_FULL["kdcCode1s"]
    assert h.type_code == "B1"
    assert h.is_online() is False
    # 원본 24개 필드가 통째로 보존돼야 한다
    assert h.raw == samples.OFFLINE_FULL
    assert len(h.raw) == 24


def test_온라인자료는_controlNo_isbn_callNo_가_빈다():
    """D1 은 실측 31.0% 가 controlNo 없음 — '결측 = 파서 버그'로 오진하지 않도록 고정."""
    h = parse_holding(samples.ONLINE_SPARSE)
    assert h.type_code == "D1"
    assert h.is_online() is True
    assert h.control_no == ""
    assert h.isbn == ""
    assert h.call_no == ""
    # 그래도 record_id 는 있어서 중복제거가 가능하다
    assert h.record_id
    assert h.dedup_key().startswith("id:")


def test_상대경로가_절대URL_로_바뀐다():
    h = parse_holding(samples.OFFLINE_FULL)
    assert h.detail_url.startswith("https://www.nl.go.kr/")
    assert h.image_url.startswith("https://www.nl.go.kr/")
    assert "//NL" not in h.detail_url          # 슬래시 중복 없음
    # orgLink 가 이미 절대 URL 이면 건드리지 않는다
    h2 = parse_holding({**samples.OFFLINE_FULL, "detailLink": "https://x.example/a"})
    assert h2.detail_url == "https://x.example/a"


# ── docYn / licYn 은 불리언이 아니다 ─────────────────────────────────────────
@pytest.mark.parametrize("doc_yn, expected", [
    ("NL_VIEWER", True), ("LD_VIEWER", True), ("FILE", True), ("LINK", True),
    ("N", False), ("", False),
])
def test_docYn_은_열거코드다(doc_yn, expected):
    """실측값 5종. Y/N 으로 가정했으면 전건 오판했을 자리."""
    h = parse_holding({**samples.OFFLINE_FULL, "docYn": doc_yn})
    assert h.has_fulltext() is expected


def test_원문없음_표본():
    h = parse_holding(samples.NO_FULLTEXT)
    assert h.doc_type == "N"
    assert h.has_fulltext() is False


# ── 발행연도 정규화 ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("sample, expected", [
    (samples.YEAR_YYYYMM, 4), (samples.YEAR_YYYYMMDD, 4), (samples.YEAR_ODD, 4),
])
def test_발행연도는_형식이_뒤섞여도_4자리로(sample, expected):
    h = parse_holding(sample)
    assert len(h.pub_year) == expected
    assert h.pub_year.isdigit()
    assert h.pub_year_raw == sample["pubYearInfo"]   # 원문도 함께 남긴다


def test_발행연도_빈값은_빈값으로():
    h = parse_holding(samples.YEAR_EMPTY)
    assert h.pub_year == ""


@pytest.mark.parametrize("raw, expected", [
    ("2006", "2006"), ("200902", "2009"), ("20141027", "2014"),
    ("2019 (2020 9쇄)", "2019"),
    ("", ""), (None, ""), ("발행년불명", ""), ("99", ""), ("3000", ""),
])
def test_normalize_pub_year(raw, expected):
    assert normalize_pub_year(raw) == expected


# ── HTML 하이라이트 제거 ─────────────────────────────────────────────────────
def test_하이라이트_태그가_제거된다():
    """실측 마크업: 매칭 **토큰마다** `<span class="searching_txt">` 가 붙는다.

    ⚠️ 태그를 지우면 토큰 사이 공백이 그대로 남는다 — 원문 제목이 `교육 불평등` 이면
       결과도 `교육 불평등` 이지 `교육불평등` 이 아니다. 제목 비교 시 공백 정규화가 필요하다.
    """
    h = parse_holding(samples.RAW_WITH_MARKUP)
    assert "<" not in h.title and ">" not in h.title
    assert "searching_txt" not in h.title
    assert "\n" not in h.title
    assert "  " not in h.title           # 연속 공백 정리
    assert h.title == "교육 불평등 : 학교교육에 의한 불평등의 재생산"
    # 원본은 raw 에 그대로 남는다
    assert "<span" in h.raw["titleInfo"]


@pytest.mark.parametrize("raw, expected", [
    ("<b>가</b>나", "가나"), ("  공백   정리  ", "공백 정리"),
    ("줄\n바꿈", "줄 바꿈"), (None, ""), ("", ""),
])
def test_clean_html(raw, expected):
    assert clean_html(raw) == expected


# ── 응답 봉투 ────────────────────────────────────────────────────────────────
def test_봉투에서_total_과_레코드를_읽는다():
    total, recs, env = parse_search_response(samples.envelope(samples.ALL_SAMPLES, total=1856))
    assert total == 1856
    assert len(recs) == len(samples.ALL_SAMPLES)
    assert "result" not in env          # 봉투 메타에는 result 를 넣지 않는다


def test_total_이_쉼표문자열로_와도_읽는다():
    total, _, _ = parse_search_response(samples.envelope([samples.OFFLINE_FULL], total="1,856"))
    assert total == 1856


def test_JSON_문자열도_받는다():
    import json
    body = json.dumps(samples.envelope([samples.OFFLINE_FULL]), ensure_ascii=False)
    total, recs, _ = parse_search_response(body)
    assert total == 1 and len(recs) == 1


def test_단건이_배열이_아니어도_받는다():
    _, recs, _ = parse_search_response({"total": 1, "result": samples.OFFLINE_FULL})
    assert len(recs) == 1


# ── 오류를 조용히 통과시키지 않는다 ──────────────────────────────────────────
def test_결과_0건이면_result_키가_없다_실측():
    """✅ 라이브 실측(2026-08-12): 0건일 때 API 는 `result` 키를 아예 빼고 보낸다.

    초판은 이것을 ParseError 로 올렸는데, 그러면 정상적인 '검색 결과 없음'이
    매번 오류로 둔갑한다(검색어 오타·빈 분류 조회 등). total 이 있으면 빈 결과로 본다.
    """
    total, recs, env = parse_search_response(samples.EMPTY_RESULT_ENVELOPE)
    assert total == 0
    assert recs == []
    assert env["kwd"]          # 봉투 메타는 그대로 전달된다


def test_result_도_total_도_없으면_ParseError():
    """봉투 자체가 아닌 응답은 여전히 오류다 — 이쪽이 조용한 통과의 진짜 방어선이다."""
    with pytest.raises(ParseError, match="result"):
        parse_search_response({"msg": "nope"})


@pytest.mark.parametrize("payload, needle", [
    ({"errorCode": "011", "result": []}, "INVALID KEY"),
    ({"errCode": "012", "result": []}, "DATA LIMIT 500"),
    ({"errorCode": "010", "errorMsg": "NO KEY", "result": []}, "인증키"),
])
def test_API_오류코드는_ParseError(payload, needle):
    with pytest.raises(ParseError) as ei:
        parse_search_response(payload)
    assert needle in str(ei.value)


def test_HTML_에러페이지는_JSON_파싱실패로():
    with pytest.raises(ParseError, match="JSON"):
        parse_search_response("<html><body>차단되었습니다</body></html>")


def test_빈_응답():
    with pytest.raises(ParseError, match="빈 응답"):
        parse_search_response("   ")
