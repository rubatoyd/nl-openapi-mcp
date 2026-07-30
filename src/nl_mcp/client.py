"""HTTP Client for National Library of Korea Seoji OpenAPI (seojiSearch.do)."""

from typing import Any, Dict, List, Optional
import requests

from .config import SEOJI_API_URL, get_api_key
from .models import SearchResult, SeojiRecord
from .parser import parse_search_result


class NlSeojiError(Exception):
    """Exception raised when National Library Seoji OpenAPI returns an error."""
    pass


class NlSeojiClient:
    """HTTP Client for National Library Seoji OpenAPI search and harvesting."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 15):
        self.api_key = get_api_key() if api_key is None else api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "nl-openapi-mcp/0.1.0 (Python3; https://github.com/rubato103/nl-openapi-mcp)",
        })

    def search(
        self,
        kwd: str = "",
        title: str = "",
        author: str = "",
        publisher: str = "",
        keyword: str = "",
        isbn: str = "",
        seoji_year: str = "",
        sort: str = "",
        page_num: int = 1,
        page_size: int = 10,
    ) -> SearchResult:
        """Search academic bibliography and literature from Seoji OpenAPI."""
        if not self.api_key:
            raise NlSeojiError("NL_API_KEY (국립중앙도서관 발급키)가 설정되지 않았습니다.")

        params: Dict[str, Any] = {
            "key": self.api_key,
            "pageNum": max(1, page_num),
            "pageSize": min(100, max(1, page_size)),
            "apiType": "json",
        }

        if sort:
            params["sort"] = sort
        if seoji_year:
            params["seoji_year"] = str(seoji_year)

        filters = []
        if title:
            filters.append(("title", title))
        if author:
            filters.append(("author", author))
        if publisher:
            filters.append(("publisher", publisher))
        if keyword:
            filters.append(("keyword", keyword))
        if isbn:
            filters.append(("isbn", isbn))

        if filters:
            params["detailSearch"] = "true"
            for i, (field_name, val) in enumerate(filters[:5], start=1):
                params[f"f{i}"] = field_name
                params[f"v{i}"] = val
                if i < len(filters[:5]):
                    params[f"and{i}"] = "AND"
        else:
            params["kwd"] = kwd or ""

        try:
            resp = self.session.get(SEOJI_API_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise NlSeojiError(f"API 통신 오류: {str(e)}") from e

        # JSON Parse
        try:
            data = resp.json()
        except Exception:
            data = resp.text

        # Error check from data if API returns error dict
        if isinstance(data, dict):
            err_code = data.get("errorCode") or data.get("errCode")
            if err_code:
                err_msg = data.get("errorMsg") or data.get("errMsg") or "Unknown error"
                raise NlSeojiError(f"OpenAPI 오류 [{err_code}]: {err_msg}")

        return parse_search_result(data)

    def detail(
        self,
        control_no: str = "",
        title: str = "",
    ) -> Optional[SeojiRecord]:
        """Fetch details for a bibliographic record by control_no or title."""
        query_title = title
        res = self.search(title=query_title, page_num=1, page_size=10)
        if not res.records and query_title:
            res = self.search(kwd=query_title, page_num=1, page_size=10)

        for rec in res.records:
            if control_no and rec.control_no == control_no:
                return rec
        return res.records[0] if res.records else None

    def collect(
        self,
        kwd: str = "",
        title: str = "",
        author: str = "",
        publisher: str = "",
        keyword: str = "",
        isbn: str = "",
        seoji_year: str = "",
        sort: str = "",
        max_records: int = 50,
    ) -> List[SeojiRecord]:
        """Harvest multiple pages of bibliographic records up to max_records."""
        collected: List[SeojiRecord] = []
        seen_keys = set()
        page_size = min(100, max(10, max_records))
        page_num = 1

        while len(collected) < max_records:
            res = self.search(
                kwd=kwd,
                title=title,
                author=author,
                publisher=publisher,
                keyword=keyword,
                isbn=isbn,
                seoji_year=seoji_year,
                sort=sort,
                page_num=page_num,
                page_size=page_size,
            )
            if not res.records:
                break

            for rec in res.records:
                dedupe_key = rec.control_no or f"{rec.title}::{rec.author}"
                if dedupe_key not in seen_keys:
                    seen_keys.add(dedupe_key)
                    collected.append(rec)
                    if len(collected) >= max_records:
                        break

            if len(res.records) < page_size or page_num * page_size >= res.total:
                break
            page_num += 1

        return collected[:max_records]
