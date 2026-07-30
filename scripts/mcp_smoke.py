"""Smoke test script for National Library Seoji OpenAPI FastMCP server."""

import asyncio
import sys
from nl_mcp.server import mcp, nl_search, nl_status


def run_smoke():
    print("=== nl-openapi-mcp Smoke Test ===")
    try:
        tools = asyncio.run(mcp.list_tools())
    except Exception:
        tools = mcp.list_tools()
    print(f"등록된 MCP 도구 개수: {len(tools)}개")
    for t in tools:
        print(f"  - [{t.name}]: {t.description[:50]}...")

    print("\n1) nl_status() 실행...")
    st = nl_status()
    print("  -> 결과:", st)

    if not st.get("api_key_configured"):
        print("\n [주의] NL_API_KEY가 미설정되어 라이브 검색 테스트는 건너뜁니다.")
        return

    print("\n2) nl_search(kwd='도서관', page_size=1) 라이브 검색 실행...")
    res = nl_search(kwd="도서관", page_size=1)
    print("  -> 성공 여부:", res.get("success"))
    print("  -> 전체 건수:", res.get("total"))
    print("  -> 반환 레코드 수:", res.get("count"))

    print("\n=== Smoke Test 모두 성공 ===")


if __name__ == "__main__":
    run_smoke()
