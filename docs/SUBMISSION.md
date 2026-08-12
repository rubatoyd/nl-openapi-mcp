# MCP 레지스트리 배포 가이드

> 공식 MCP 레지스트리(`io.github.rubatoyd/nl-openapi-mcp`) 발행 요구사항과 절차.

---

## 1. 배포 경로 — mcpb 방식 (PyPI 불필요)

자매 프로젝트와 동일하게 **`.mcpb` + GitHub OIDC** 경로를 쓴다. PyPI 게시는 하지 않는다.

> ⚠️ v0.1.0 에는 `publish-pypi.yml` 이 있었으나 PyPI Trusted Publishing 이 설정된 적이 없어
> **태그를 밀 때마다 실패했을** 워크플로였다. v0.2.0 에서 제거했다.
> PyPI 배포가 필요해지면 pypi.org 에서 신뢰 게시자를 먼저 등록한 뒤 워크플로를 되살릴 것.

## 2. 트리거

버전 태그(`v*`) 푸시 → `.github/workflows/publish-mcp.yml` 한 번으로 전부 처리한다.

```
binaries (win/macos/linux 매트릭스)
  PyInstaller 자체완결 바이너리 → mcpb pack → artifact 업로드
        ↓ needs
publish
  경량 .mcpb 팩 → sha256 계산 → server.json 의 __MCPB_SHA256__ 치환
  → GitHub Release 생성(자산 4종 첨부) → mcp-publisher login github-oidc → publish
```

⚠️ `GITHUB_TOKEN` 으로 만든 release 는 다른 워크플로의 `release: published` 를 트리거하지 않는다
(Actions 재귀 방지). 그래서 바이너리 빌드를 **별도 워크플로로 분리하지 않고** 선행 job 으로 둔다.

## 3. 발행 전 점검

- [ ] 버전 동기화 **5곳** — `pyproject.toml` · `src/nl_mcp/__init__.py` · `server.json`(2곳: `version`·`identifier` URL) · `mcpb/manifest.json` · `packaging/binary/manifest.json`
- [ ] `server.json` 의 `name` 이 `io.github.rubatoyd/…` 인지 (레지스트리는 **소문자**)
- [ ] README 상단 `<!-- mcp-name: … -->` 주석 일치
- [ ] `uv run pytest -q` 통과
- [ ] `uv run python scripts/mcp_smoke.py` 통과
- [ ] `npx @anthropic-ai/mcpb@latest validate mcpb/manifest.json` (및 packaging/binary/)

> ⚠️ 레지스트리 발행은 **immutable** 이고 GitHub OIDC 로 계정 소유를 검증한다.
> 계정명이 바뀌면 구 네임스페이스 항목은 회수 불가한 고아로 남는다(kci 의 실제 사례).

## 4. Claude Desktop 디렉터리 등재 심사 준비

- **도구 3종 정상 동작**: `nl_status` · `nl_search` · `nl_collect`
- **Annotations**: 조회 2종 `readOnlyHint=true`, `nl_collect` 는 `readOnlyHint=false` +
  `destructiveHint=false`(로컬 비파괴 쓰기). 전부 `openWorldHint=true`
- **예외 누수 없음**: 모든 도구가 `@_safe` 로 감싸여 **항상 dict** 를 반환한다
  (자격증명 누락·네트워크·파싱 오류 포함). 회귀 테스트 `tests/test_server.py` 가 고정
- **보안**: 인증키는 `.env`/환경변수로만 주입. `raise_for_status()` 를 쓰지 않아
  **예외 메시지에 키가 든 URL 이 실리지 않는다**
- **정직한 한계 고지**: 500건 상한을 README·도구 description·응답 `warning` 에 명시
