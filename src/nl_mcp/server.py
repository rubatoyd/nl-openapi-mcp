"""FastMCP server and tool definitions for National Library of Korea Seoji OpenAPI."""

from functools import wraps
from typing import Any, Callable, Dict

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from mcp.server.mcpserver import MCPServer as FastMCP

from .client import NlSeojiClient, NlSeojiError
from .config import get_api_key
from .exporters import export_records


def _safe(fn: Callable[..., Any]) -> Callable[..., Dict[str, Any]]:
    """Decorator to catch exceptions and return JSON-serializable dict without leaking API keys."""
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        try:
            return fn(*args, **kwargs)
        except NlSeojiError as e:
            return {"error": str(e), "success": False}
        except Exception as e:
            return {"error": f"Internal error: {str(e)}", "success": False}
    return wrapper


mcp = FastMCP("nl")


@mcp.tool()
@_safe
def nl_status() -> Dict[str, Any]:
    """Check connectivity to National Library of Korea Seoji OpenAPI and verify API key configuration."""
    api_key = get_api_key()
    if not api_key:
        return {
            "success": False,
            "api_key_configured": False,
            "message": "NL_API_KEY 환경변수가 설정되지 않았습니다.",
        }

    client = NlSeojiClient(api_key=api_key)
    try:
        res = client.search(kwd="도서관", page_num=1, page_size=1)
        return {
            "success": True,
            "api_key_configured": True,
            "api_status": "ok",
            "total_sample_count": res.total,
            "message": "국립중앙도서관 국가서지 OpenAPI 정상 통신 중",
        }
    except Exception as e:
        return {
            "success": False,
            "api_key_configured": True,
            "api_status": "error",
            "message": str(e),
        }


@mcp.tool()
@_safe
def nl_search(
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
) -> Dict[str, Any]:
    """Search Korean academic bibliography and literature from National Library Seoji OpenAPI.

    Args:
        kwd: General keyword search across fields.
        title: Book or literature title filter (detail search).
        author: Author name filter (detail search).
        publisher: Publisher name filter (detail search).
        keyword: Subject keyword filter (detail search).
        isbn: ISBN or ISSN code filter (detail search).
        seoji_year: Bibliography inclusion year (e.g. '2024').
        sort: Sorting option ('title_asc', 'title_desc', 'pubyear_desc', etc.).
        page_num: Page number (1-based index).
        page_size: Records per page (default 10, max 100).
    """
    client = NlSeojiClient()
    res = client.search(
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
    return {
        "success": True,
        "total": res.total,
        "page_num": res.page_num,
        "page_size": res.page_size,
        "count": len(res.records),
        "records": [r.to_dict() for r in res.records],
    }


@mcp.tool()
@_safe
def nl_detail(
    control_no: str = "",
    title: str = "",
) -> Dict[str, Any]:
    """Get full bibliographic details for a specific record by control_no or title.

    Args:
        control_no: Unique control number or rawid of the bibliographic record.
        title: Exact or partial title of the record if control_no is unknown.
    """
    client = NlSeojiClient()
    rec = client.detail(control_no=control_no, title=title)
    if not rec:
        return {
            "success": False,
            "error": "일치하는 서지 정보를 찾을 수 없습니다.",
        }
    return {
        "success": True,
        "record": rec.to_dict(),
    }


@mcp.tool()
@_safe
def nl_collect(
    output_path: str,
    kwd: str = "",
    title: str = "",
    author: str = "",
    publisher: str = "",
    keyword: str = "",
    isbn: str = "",
    seoji_year: str = "",
    sort: str = "",
    max_records: int = 50,
    export_format: str = "",
) -> Dict[str, Any]:
    """Harvest multiple pages of bibliographic records and export to a local file (xlsx/csv/json/sqlite).

    Args:
        output_path: Local file path to save the dataset (e.g. 'books.xlsx', 'data.csv').
        kwd: General keyword query.
        title: Title filter.
        author: Author filter.
        publisher: Publisher filter.
        keyword: Subject keyword filter.
        isbn: ISBN/ISSN filter.
        seoji_year: Inclusion year filter.
        sort: Sorting option.
        max_records: Maximum total number of records to harvest across pages.
        export_format: File format ('xlsx', 'csv', 'json', 'sqlite'). If empty, inferred from output_path.
    """
    client = NlSeojiClient()
    records = client.collect(
        kwd=kwd,
        title=title,
        author=author,
        publisher=publisher,
        keyword=keyword,
        isbn=isbn,
        seoji_year=seoji_year,
        sort=sort,
        max_records=max_records,
    )
    if not records:
        return {
            "success": False,
            "count": 0,
            "error": "수집된 데이터가 없습니다.",
        }

    saved_path = export_records(records, output_path=output_path, fmt=export_format)
    return {
        "success": True,
        "count": len(records),
        "output_path": saved_path,
        "message": f"{len(records)}건의 서지 정보를 '{saved_path}'에 저장했습니다.",
    }


def main() -> None:
    """Entry point for running the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()

