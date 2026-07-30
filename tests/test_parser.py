"""Unit tests for nl_mcp parser."""

from nl_mcp.parser import clean_html, extract_rawid_from_url, parse_search_result
from samples import SAMPLE_SEOJI_EMPTY_JSON, SAMPLE_SEOJI_SEARCH_JSON


def test_clean_html():
    raw = '<span class="highlight">토지</span> 그 이상의 역사 : 사진으로 보는 한국<span class="highlight">토지</span>공사'
    cleaned = clean_html(raw)
    assert "span" not in cleaned
    assert cleaned == "토지 그 이상의 역사 : 사진으로 보는 한국토지공사"


def test_extract_rawid_from_url():
    url = "/LI/contents/L10501000000.do?rawid=3197221"
    assert extract_rawid_from_url(url) == "3197221"
    assert extract_rawid_from_url("") == ""


def test_parse_search_result_success():
    res = parse_search_result(SAMPLE_SEOJI_SEARCH_JSON)
    assert res.total == 12505
    assert res.page_num == 1
    assert res.page_size == 2
    assert len(res.records) == 2

    r0 = res.records[0]
    assert r0.control_no == "3197221"
    assert "span" not in r0.title
    assert r0.title == "토지 그 이상의 역사 : 사진으로 보는 한국토지공사 35년사, 1975-2009"
    assert r0.author == "한국토지공사 [편]."
    assert r0.pub_year == "2009"
    assert r0.detail_url.startswith("https://librarian.nl.go.kr")
    assert r0.isbn == "9788912345678"


def test_parse_search_result_empty():
    res = parse_search_result(SAMPLE_SEOJI_EMPTY_JSON)
    assert res.total == 0
    assert len(res.records) == 0
