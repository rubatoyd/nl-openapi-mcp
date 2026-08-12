"""국립중앙도서관 소장자료 검색 OpenAPI — MCP 서버 & CLI."""

# 하드코딩하면 릴리스마다 pyproject 와 어긋난다(자매 프로젝트에서 실제로 방치됐다) → 설치 메타데이터 조회.
try:
    from importlib.metadata import version as _pkg_version

    __version__ = _pkg_version("nl-openapi-mcp")
except Exception:  # 미설치(소스 직접 실행) 등
    __version__ = "0.0.0+unknown"
