"""환경설정 및 자격증명 로딩 — 국립중앙도서관 소장자료 검색 OpenAPI.

인증키는 코드/로그에 하드코딩하지 않고 `.env`(gitignore) 또는 OS 환경변수에서만 읽는다.
`NL_API_KEY` 하나면 된다(토큰 발급·AES·공인IP 등록 없음 — KCI 와 동일하게 평문 key 쿼리 파라미터).
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

# .env 를 한 번 로드 (이미 설정된 환경변수는 덮어쓰지 않음)
load_dotenv(override=False)

# 소장자료 검색 (본 패키지의 대상 API)
SEARCH_API_URL = os.environ.get(
    "NL_SEARCH_API_URL", "https://www.nl.go.kr/NL/search/openApi/search.do"
)
NL_BASE_URL = os.environ.get("NL_BASE_URL", "https://www.nl.go.kr")

# ⚠️ API 가 한 검색식당 돌려주는 **최대 레코드 수**(공식 에러코드 012 "DATA LIMIT 500").
#    total 이 이 값을 넘어도 501번째부터는 어떤 페이징으로도 받을 수 없다.
#    → 검색식을 연도·분류 등으로 쪼개야 한다. 자세한 처방은 client.search_meta() 참조.
API_RECORD_CAP = int(os.environ.get("NL_API_RECORD_CAP", "500"))

# pageSize 상한 (실측 100 사용 — c2 수집 스크립트가 100 으로 1,124건 회수)
MAX_PAGE_SIZE = 100


def get_api_key() -> str | None:
    """소장자료 검색 인증키 — 없으면 None."""
    return (os.environ.get("NL_API_KEY") or "").strip() or None


def require_api_key() -> str:
    key = get_api_key()
    if not key:
        raise RuntimeError(
            "NL_API_KEY 가 설정되지 않았습니다 — 국립중앙도서관 소장자료 검색 API 는 인증키가 필요합니다. "
            ".env(.env.example 참고) 또는 OS 환경변수로 설정하세요. "
            "발급: https://www.nl.go.kr 오픈API 신청."
        )
    return key


def redact(key: str | None) -> str:
    """로그용 마스킹 (인증키 노출 방지)."""
    if not key:
        return "(none)"
    return f"{key[:4]}…{key[-2:]}" if len(key) > 6 else "***"


_TRUST_INJECTED = False


def use_os_trust() -> bool:
    """OS 신뢰 저장소(Windows/macOS)로 TLS 검증을 위임.

    교육망(학교/교육청)·사내망의 SSL 인터셉션은 자체서명 루트 CA를 OS 신뢰저장소에 심어둔다.
    requests 는 기본적으로 certifi 만 보므로 그 CA를 모른다 → truststore 로 OS 저장소를 쓰게 하면
    **검증을 끄지 않고도** 통과한다. `NL_OS_TRUST=0` 이면 비활성. (한 번만 주입)

    ⚠️ MCP 등록 명령줄이 아니라 **코드**에서 호출한다 — `.mcpb` 번들·PyInstaller 바이너리 경로에도
       적용되어야 하기 때문이다(자매 프로젝트 scienceon 이 등록 명령줄에만 두어 번들 경로가
       교육망에서 실패했다).
    """
    global _TRUST_INJECTED
    if _TRUST_INJECTED:
        return True
    if (os.environ.get("NL_OS_TRUST") or "1").strip().lower() in ("0", "false", "no"):
        return False
    try:
        import truststore

        truststore.inject_into_ssl()
        _TRUST_INJECTED = True
        return True
    except Exception as e:  # noqa: BLE001
        import logging

        logging.getLogger("nl_mcp").warning(
            "truststore OS 신뢰저장소 주입 실패(%s) — TLS 인터셉션 망에서 인증서 오류 가능. "
            "대안: REQUESTS_CA_BUNDLE 로 루트 CA 지정.", type(e).__name__)
        return False
