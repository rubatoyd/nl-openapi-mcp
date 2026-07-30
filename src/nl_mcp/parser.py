"""Parser and HTML cleaner for National Library of Korea Seoji OpenAPI responses."""

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Union

from .config import NL_BASE_URL
from .models import SearchResult, SeojiRecord

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def clean_html(text: str | None) -> str:
    """Remove HTML tags (like <span class='highlight'>) and clean whitespace."""
    if not text:
        return ""
    text_clean = _HTML_TAG_RE.sub("", str(text))
    return re.sub(r"\s+", " ", text_clean).strip()


def extract_rawid_from_url(url: str | None) -> str:
    """Extract rawid query parameter from detailUrl as unique control_no."""
    if not url:
        return ""
    match = re.search(r"[?&]rawid=([^&]+)", url)
    return match.group(1) if match else ""


def parse_seoji_record(item: Dict[str, Any]) -> SeojiRecord:
    """Parse a single JSON record item from seojiSearch.do into SeojiRecord."""
    detail_url = str(item.get("detailUrl") or "").strip()
    if detail_url and detail_url.startswith("/"):
        full_detail_url = f"{NL_BASE_URL}{detail_url}"
    elif detail_url and not detail_url.startswith("http"):
        full_detail_url = f"{NL_BASE_URL}/{detail_url}"
    else:
        full_detail_url = detail_url

    control_no = extract_rawid_from_url(detail_url) or str(item.get("controlNo") or item.get("id") or "")
    isbn = clean_html(item.get("isbn") or item.get("isbnCode") or item.get("isbnInfo") or "")

    return SeojiRecord(
        control_no=control_no,
        title=clean_html(item.get("titleInfo")),
        author=clean_html(item.get("authorInfo")),
        publisher=clean_html(item.get("pubInfo")),
        pub_year=clean_html(item.get("pubYearInfo")),
        seoji_year=clean_html(item.get("seojiYear")),
        category=clean_html(item.get("category")),
        isbn=isbn,
        doc_yn=clean_html(item.get("docYn") or "N"),
        page_info=clean_html(item.get("pageInfo")),
        detail_url=full_detail_url,
        source="seoji",
        raw=item,
    )


def parse_search_result(data: Union[Dict[str, Any], str]) -> SearchResult:
    """Parse JSON dict or XML string response from seojiSearch.do into SearchResult."""
    if isinstance(data, str):
        data_str = data.strip()
        if data_str.startswith("<"):
            return _parse_xml_search_result(data_str)
        # fallback if stringified json
        import json
        try:
            data = json.loads(data_str)
        except Exception:
            return SearchResult()

    if not isinstance(data, dict):
        return SearchResult()

    total = int(data.get("total") or 0)
    page_num = int(data.get("pageNum") or 1)
    page_size = int(data.get("pageSize") or 10)
    items = data.get("result") or []
    if not isinstance(items, list):
        items = []

    records = [parse_seoji_record(item) for item in items if isinstance(item, dict)]
    return SearchResult(
        total=total,
        page_num=page_num,
        page_size=page_size,
        records=records,
    )


def _parse_xml_search_result(xml_str: str) -> SearchResult:
    """Fallback XML parser if API response is XML."""
    try:
        root = ET.fromstring(xml_str)
    except Exception:
        return SearchResult()

    total_text = root.findtext("total", "0")
    page_num_text = root.findtext("pageNum", "1")
    page_size_text = root.findtext("pageSize", "10")

    records = []
    for node in root.findall(".//result"):
        item = {child.tag: child.text for child in node}
        records.append(parse_seoji_record(item))

    return SearchResult(
        total=int(total_text) if total_text.isdigit() else 0,
        page_num=int(page_num_text) if page_num_text.isdigit() else 1,
        page_size=int(page_size_text) if page_size_text.isdigit() else len(records),
        records=records,
    )
