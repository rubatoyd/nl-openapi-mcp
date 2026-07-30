# Anthropic 디렉터리 제출 초안 (copy-paste ready)

> Claude Desktop 커넥터/익스텐션 **디렉터리 등재 신청 폼**에 붙여넣을 내용 초안.
> 영어권 리뷰어 심사에 맞춰 본문은 영문으로 작성되었습니다.

---

## 1. Basic information
- **Extension name (id):** `nl-openapi-mcp`
- **Display name:** National Library of Korea Seoji OpenAPI (국립중앙도서관 국가서지 검색)
- **Version:** 0.1.0
- **Category:** Research / Academic & Reference / Books
- **Author / Publisher:** Yeondong Yang (GitHub: rubato103)
- **Contact email:** rubato103@gmail.com
- **Repository:** https://github.com/rubato103/nl-openapi-mcp
- **Homepage / Docs:** https://github.com/rubato103/nl-openapi-mcp#readme
- **License:** MIT
- **MCP Registry name:** `io.github.rubato103/nl-openapi-mcp`
- **PyPI Package:** `nl-openapi-mcp`

## 2. Short description
> Search and collect Korean academic bibliography, books, and literature metadata from the National Library of Korea Seoji OpenAPI.

## 3. Long description
> nl-openapi-mcp connects Claude to the **National Library of Korea Seoji OpenAPI**, the official national bibliographic database of South Korea. It allows users to search Korean academic publications, books, and literature, retrieve normalized bibliographic records (including titles, authors, publishers, publication years, ISBNs, and physical descriptions), and bulk-harvest metadata across multiple pages.
>
> All search and detail responses are automatically stripped of HTML highlight tags and standardized into clean structured models. The tool also provides built-in exporters to save harvested datasets into local `xlsx`, `csv`, `json`, or `sqlite` files for academic research and bibliometric analysis.

## 4. Tools (4 Tools)
| Tool | What it does | Read-only | Auth | Data accessed / sent |
|---|---|:--:|:--:|---|
| `nl_status` | Check OpenAPI connectivity and verify whether `NL_API_KEY` is configured | ✅ | none | National Library endpoint |
| `nl_search` | Search Korean bibliography records by keyword, title, author, publisher, keyword, or ISBN | ✅ | API key | National Library API endpoint; query parameters sent to server |
| `nl_detail` | Get full bibliographic details for a specific record by title/control number | ✅ | API key | National Library API endpoint |
| `nl_collect` | Multi-page search harvesting and export to local file (`xlsx`/`csv`/`json`/`sqlite`) | ✍️ writes files | API key | National Library API endpoint; writes dataset to local disk |
