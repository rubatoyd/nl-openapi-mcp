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
#    ✅ 실측 확정(2026-08-12): 상한은 **레코드 오프셋 기준**이다(pageSize=10 이면 51페이지,
#    pageSize=100 이면 6페이지에서 빈 응답 — 둘 다 누적 500건).
#    → `category` 분할·검색어 세분화·구문검색으로 쪼개야 한다. 연도로는 쪼갤 수 없다
#    (서버측 연도 필터 부재 실측). 자세한 처방은 client.search_meta() 참조.
API_RECORD_CAP = int(os.environ.get("NL_API_RECORD_CAP", "500"))

# pageSize 상한 — ✅ **라이브 실측(2026-08-12)**: 500 까지 받아들이고 500건을 한 번에 준다.
# 1000 은 거부된다(반환 0건, 응답의 pageSize 에코가 null).
# 초판은 100 으로 잡았는데(수집 스크립트가 그 값을 썼을 뿐), 그 결과 상한(500건)까지
# 받는 데 5회를 쓰던 것이 **1회로 줄었다**.
MAX_PAGE_SIZE = 500

# `category` 가 받는 값 — ✅ **서버가 오류코드 013 메시지로 유효 목록을 직접 알려준다.**
# ⚠️ 고급검색 UI 에는 '전체' 탭이 있지만 **API 는 '전체' 를 거부한다**(013 CATEGORY ERROR).
#    전체 검색은 category 를 **아예 빼고** 호출해야 한다.
# 실측(kwd=교육불평등): 도서 63 · 학위논문 66 · 잡지/학술지 9 · 기사 234 · 멀티미디어 4 ·
#   웹사이트 3 · 외부연계자료 3 = 382 = category 생략 시 total 과 **정확히 일치**.
#   고문헌·신문·장애인자료·해외기록물·기타는 이 검색어에서 0건(유효한 값이나 결과 없음).
CATEGORIES = [
    "도서", "고문헌", "학위논문", "잡지/학술지", "신문", "기사",
    "멀티미디어", "장애인자료", "웹사이트", "해외기록물", "외부연계자료", "기타",
]

# `srchTarget` — ✅ 실측으로 **동작이 확인된 값**(2026-08-12)
#   kwd=오욱환: author=36 · title=13 · publisher=0   ← 셋이 서로 달라 각각 해석됨이 확정
#   kwd=교육과학사: publisher=5,973 · author=22 · total=6,095
#   kwd=교육불평등: title=63 · keyword=41 · total=110
#
# ⚠️ **지원하지 않는 값은 오류가 아니라 조용히 `total`(전 필드) 검색으로 폴백한다.**
#    판별법: 저자명을 ISBN 필드에서 찾게 하면 0건이어야 하는데 `srchTarget=isbn&kwd=오욱환`
#    이 36건(=total 과 동일)을 냈다 → 폴백. classNo·callNo·subject·오타도 동일하다.
#    즉 `srchTarget=isbn` 으로 ISBN 검색을 했다고 믿으면 전 필드 검색 결과를 받는다.
SEARCH_TARGETS_VERIFIED = ("title", "author", "publisher", "keyword", "total", "kwd")
SEARCH_TARGETS_FALLBACK = ("isbn", "issn", "classNo", "callNo", "subject", "all")

# 검색 필드 ↔ API 지원 여부(실측)
SEARCH_FIELD_LABELS = {
    "title": "제목 — 지원(토큰 매칭). 큰따옴표로 감싸면 구문검색",
    "author": "저자 — 지원",
    "publisher": "발행자 — 지원",
    "keyword": "키워드 — 지원",
    "total": "전체 필드 — 지원",
    "isbn": "표준부호 — ✗ 미지원(전 필드 검색으로 조용히 폴백)",
    "classNo": "분류기호 — ✗ 미지원(전 필드 검색으로 조용히 폴백)",
    "callNo": "청구기호 — ✗ 미지원(전 필드 검색으로 조용히 폴백)",
}


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
