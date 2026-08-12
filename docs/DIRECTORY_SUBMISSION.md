# Anthropic 디렉터리 제출 초안 (copy-paste ready)

> Claude Desktop 커넥터/익스텐션 **디렉터리 등재 신청 폼**에 붙여넣을 내용 초안.
> 영어권 리뷰어 심사에 맞춰 본문은 영문으로 작성되었습니다.

---

## 1. Basic information
- **Extension name (id):** `nl-openapi-mcp`
- **Display name:** National Library of Korea — Holdings Search (국립중앙도서관 소장자료 검색)
- **Version:** 0.2.0
- **Category:** Research / Academic & Reference / Books
- **Author / Publisher:** Yeondong Yang (GitHub: rubatoyd)
- **Contact email:** rubato103@gmail.com
- **Repository:** https://github.com/rubatoyd/nl-openapi-mcp
- **Homepage / Docs:** https://github.com/rubatoyd/nl-openapi-mcp#readme
- **License:** MIT
- **MCP Registry name:** `io.github.rubatoyd/nl-openapi-mcp`

## 2. Short description
> Search and harvest holdings of the National Library of Korea — books and online materials, with KDC classification, call numbers, and full-text availability.

## 3. Long description
> nl-openapi-mcp connects Claude to the **holdings search API of the National Library of Korea**, the national deposit library of South Korea. Users can search the library's catalogue of books and online materials and retrieve normalized records covering title, statement of responsibility, imprint, publication year, ISBN, call number, KDC classification, shelf location, and how (or whether) full text is available.
>
> The server is explicit about a hard constraint of this API: **a single search expression returns at most 500 records**, even when the reported total is far larger. Every response carries `total`, `truncated`, and `cap_hit` so that a partial result is never mistaken for a complete one, and the tool descriptions explain that the limit cannot be paged around — the query must be partitioned instead. Harvested datasets can be exported to `xlsx`, `csv`, `json`, or `sqlite` for bibliometric work.
>
> Responses are stripped of HTML highlight markup and normalized, while the original API fields are preserved alongside each record.

## 4. Tools (3 tools)
| Tool | What it does | Read-only | Auth | Data accessed / sent |
|---|---|:--:|:--:|---|
| `nl_status` | Verify the API key and perform one live round-trip to the holdings search endpoint | ✅ | API key | National Library endpoint |
| `nl_search` | Search holdings by keyword; returns `total`, `truncated`, and `cap_hit` alongside records | ✅ | API key | National Library endpoint; query parameters sent to server |
| `nl_collect` | Harvest the union of several search terms and export to a local file (`xlsx`/`csv`/`json`/`sqlite`) | ✍️ writes files | API key | National Library endpoint; writes dataset to local disk |

## 5. Safety & privacy
- **No exception ever escapes the MCP boundary.** Every tool is wrapped so it returns a structured `dict` even on missing credentials, network failure, TLS errors, or malformed responses.
- **The API key never appears in error messages.** `raise_for_status()` is deliberately avoided because it embeds the full request URL — including the key — in the exception text. Only status codes are reported.
- **Credentials are supplied by the user** through the `NL_API_KEY` environment variable (or Claude Desktop user config). Nothing is bundled or hard-coded.
- **Writes are local and non-destructive**: `nl_collect` creates files in a user-specified directory (default `~/nl-output/`) and never deletes existing data.
- **TLS verification is never disabled.** On networks that intercept SSL (common in Korean schools and enterprises) the server uses the OS trust store via `truststore`; this can be turned off with `NL_OS_TRUST=0`.

## 6. Known limitations (disclosed)
- The upstream API caps any single search expression at **500 records**; larger result sets require partitioning the query. This is surfaced in every response rather than hidden.
- Only the holdings search endpoint is covered. The National Library's separate bibliography (SEOJI) and Data4Library services are out of scope.
