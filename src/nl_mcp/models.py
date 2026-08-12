"""정규화된 소장자료 레코드 스키마.

필드는 **국립중앙도서관 소장자료 검색 API 실응답 1,124건**(2026-08-11 수집)에서 확정했다.
추정으로 만든 필드는 없다 — 실측 근거는 docs/NL_API_GUIDE.md §2 참조.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# 표 출력(csv/xlsx/sqlite) 시 컬럼 순서
COLUMNS = [
    "source", "record_id", "control_no", "title", "authors",
    "pub_info", "pub_year", "type_name", "type_code",
    "menu_name", "media_name", "manage_name", "place_info",
    "isbn", "call_no", "class_no", "kdc_code", "kdc_name",
    "doc_type", "lic_code", "lic_text", "reg_date",
    "org_link", "detail_url", "image_url",
]

_DIGITS = re.compile(r"\D")


def normalize_pub_year(value: str | None) -> str:
    """발행연도 문자열에서 **4자리 연도**만 추출.

    ⚠️ `pubYearInfo` 는 형식이 하나가 아니다 — 실측 1,124건에서 길이 4(YYYY) 703건,
       6(YYYYMM) 186건, 8(YYYYMMDD) 168건, 9·13·14 소수, 빈값 59건이 섞여 나온다.
       그대로 정수 변환하거나 앞 4자를 자르면 조용히 깨진다.
    """
    digits = _DIGITS.sub("", str(value or ""))[:4]
    if len(digits) == 4 and 1000 <= int(digits) <= 2100:
        return digits
    return ""


@dataclass
class Holding:
    """국립중앙도서관 소장자료 1건 (정규화).

    원본 24개 필드는 `raw` 에 그대로 보존한다 — 정규화가 버린 정보를 되찾을 수 있도록.
    """

    source: str = "nl_search"
    # ── 식별자 ────────────────────────────────────────────────────────────────
    record_id: str = ""      # id — 실측 1,124건 **전건 존재**. 1차 중복제거 키.
    control_no: str = ""     # controlNo — KOLIS 제어번호(KMO…/JMO…/KJU…/WMO…).
    #                          ⚠️ 온라인자료(typeCode=D1)에는 **없다**(실측 31.0% 빈값).
    # ── 서지 ──────────────────────────────────────────────────────────────────
    title: str = ""          # titleInfo (HTML 하이라이트 태그 제거 후)
    authors: str = ""        # authorInfo — 원문 그대로의 저작자사항 문자열
    #                          (예: "저작권자: 홍길동;책임편집: 김성수" — 세미콜론 구분)
    pub_info: str = ""       # pubInfo — "발행지 : 발행처, 발행년" 결합 문자열
    pub_year: str = ""       # pubYearInfo 를 4자리로 정규화(normalize_pub_year)
    pub_year_raw: str = ""   # pubYearInfo 원문(YYYY/YYYYMM/YYYYMMDD 혼재)
    # ── 자료 구분 ─────────────────────────────────────────────────────────────
    type_name: str = ""      # typeName — 자료유형명(예: 도서)
    type_code: str = ""      # typeCode — 실측 B1(인쇄자료)·D1(온라인자료)
    menu_name: str = ""      # menuName — 실측 오프라인자료 / 온라인자료
    media_name: str = ""     # mediaName — 예: 인쇄자료(책자형). 온라인자료는 빈값
    manage_name: str = ""    # manageName — 본관 / 디지털도서관 / 어린이청소년도서관
    place_info: str = ""     # placeInfo — 소장 위치(예: 서고자료대출반납(4층))
    # ── 분류·식별 ─────────────────────────────────────────────────────────────
    isbn: str = ""           # isbn — 실측 54.1% 빈값(온라인자료·연속간행물 등)
    call_no: str = ""        # callNo — 청구기호. 온라인자료는 빈값
    class_no: str = ""       # classNo — 분류번호(예: 370.13)
    kdc_code: str = ""       # kdcCode1s — KDC 대분류 코드(0~9, Z)
    kdc_name: str = ""       # kdcName1s — KDC 대분류명(사회과학 등)
    # ── 이용 ──────────────────────────────────────────────────────────────────
    doc_type: str = ""       # docYn — ⚠️ **Y/N 불리언이 아니다.** 원문 제공 방식 코드:
    #                          실측 NL_VIEWER·LD_VIEWER·FILE·LINK·N. 'N'만 원문 없음.
    lic_code: str = ""       # licYn — ⚠️ 이것도 불리언이 아니다. 실측 L·F·S·D·N·Y
    lic_text: str = ""       # licText — 사람이 읽는 이용조건(예: [관외이용]-무료)
    reg_date: str = ""       # regDate — 등록일 YYYYMMDD
    # ── 링크 ──────────────────────────────────────────────────────────────────
    org_link: str = ""       # orgLink — 원문 링크. "이용불가" 같은 안내문이 들어오기도 한다
    detail_url: str = ""     # detailLink 를 절대 URL 로 변환한 값
    image_url: str = ""      # imageUrl 을 절대 URL 로 변환한 값
    raw: dict[str, Any] = field(default_factory=dict)   # 원본 24개 필드 보존

    def to_row(self) -> dict[str, Any]:
        """평탄화된 표 한 행(dict)."""
        return {col: getattr(self, col) for col in COLUMNS}

    def has_fulltext(self) -> bool:
        """원문(디지털 뷰어/파일/링크)이 제공되는가.

        `doc_type` 이 'N' 이거나 비어 있으면 없음. 나머지(NL_VIEWER/LD_VIEWER/FILE/LINK)는 제공.
        """
        return bool(self.doc_type) and self.doc_type.upper() != "N"

    def is_online(self) -> bool:
        """온라인자료(typeCode=D1)인가 — 실측상 controlNo·callNo·classNo 가 비는 부류."""
        return self.type_code.upper() == "D1"

    def dedup_key(self) -> str:
        """항상 동일 타입(str) 키 — 키스페이스 분리로 우연한 충돌 방지.

        `id` 는 실측 1,124건 전건에 존재하므로 1차 키로 충분하다. 그래도 결측 대비 폴백을 둔다.
        (수집 스크립트 c2.py 도 `id or controlNo` 로 중복제거했다.)
        """
        if self.record_id:
            return "id:" + self.record_id
        if self.control_no:
            return "cn:" + self.control_no
        if len(self.isbn) >= 10:
            return "isbn:" + re.sub(r"[^0-9Xx]", "", self.isbn).upper()
        return "tt:" + self.title.strip().lower() + "|" + self.pub_year

    def haystack(self) -> str:
        """부분일치 필터용 전체 텍스트(소문자)."""
        parts = [self.title, self.authors, self.pub_info, self.kdc_name,
                 self.class_no, self.isbn, self.place_info]
        parts += [v for v in self.raw.values() if isinstance(v, str)]
        return "\n".join(parts).lower()

    def matches(self, subs) -> bool:
        """subs(문자열 또는 목록) 중 하나라도 부분일치하면 True (대소문자 무시).

        빈 필터(None/빈 리스트)는 '필터 없음 = 전부 통과'로 처리한다.
        """
        if isinstance(subs, str):
            subs = [subs]
        subs = [s for s in (subs or []) if s and s.strip()]
        if not subs:
            return True
        hay = self.haystack()
        return any(s.lower() in hay for s in subs)
