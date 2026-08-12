"""테스트 표본 — **국립중앙도서관 소장자료 검색 API 실응답**에서 발췌.

출처: 2026-08-11 수집분 1,124건(교육불평등 지도 연구 코퍼스). 손으로 지어낸 값이 아니다.
각 표본은 파서가 실제로 마주치는 경계 사례를 대표한다.

주의: 이 표본들은 수집 스크립트(c2.py)가 저장하면서 **이미 HTML 태그를 제거한 상태**다.
따라서 하이라이트 마크업이 실제로 어떤 형태로 오는지는 여기서 확인할 수 없다 —
RAW_WITH_MARKUP 은 재구성한 것이며 라이브 검증 대상이다(docs/작업일지.md 참조).
"""

# 인쇄자료(B1) — controlNo·isbn·callNo·classNo·imageUrl 이 모두 찬 전형
OFFLINE_FULL = {
    "titleInfo": "교육격차 : 가정 배경과 학교교육의 영향력 분석",
    "typeName": "도서",
    "placeInfo": "서고자료대출반납(4층)",
    "authorInfo": "연구책임자: 류방란;공동연구자: 김성식",
    "pubInfo": "한국교육개발원",
    "menuName": "오프라인자료",
    "mediaName": "인쇄자료(책자형)",
    "manageName": "본관",
    "pubYearInfo": "2006",
    "controlNo": "KMO200734572",
    "docYn": "NL_VIEWER",
    "orgLink": "이용불가",
    "id": "73389294",
    "typeCode": "B1",
    "licYn": "L",
    "licText": "[국립중앙도서관]-무료",
    "regDate": "20070822",
    "detailLink": "/NL/contents/search.do#viewKey=73389294&viewType=AH1",
    "isbn": "8961130099",
    "callNo": "370.13-7-20",
    "kdcCode1s": "3",
    "kdcName1s": "사회과학",
    "classNo": "370.13",
    "imageUrl": "kolis/2007/KMO200734572_thumbnail.jpg"
}

# 온라인자료(D1) — controlNo·isbn·callNo·classNo·mediaName 이 빈 문자열(실측 31.0%)
ONLINE_SPARSE = {
    "titleInfo": "교육격차 : 가정 배경과 학교교육의 영향력 분석 = An analysis of educational gap",
    "typeName": "도서",
    "placeInfo": "디지털도서관 디지털자료실",
    "authorInfo": "류방란 김성식",
    "pubInfo": "서울 : 한국교육개발원, 20061229",
    "menuName": "온라인자료",
    "mediaName": "",
    "manageName": "디지털도서관",
    "pubYearInfo": "20061229",
    "controlNo": "",
    "docYn": "NL_VIEWER",
    "orgLink": "이용불가",
    "id": "0000000106053304",
    "typeCode": "D1",
    "licYn": "L",
    "licText": "[국립중앙도서관]-무료",
    "regDate": "20150403",
    "detailLink": "/NL/contents/search.do#viewKey=CNTS-00066726969&viewType=C",
    "isbn": "",
    "callNo": "",
    "kdcCode1s": "3",
    "kdcName1s": "사회과학",
    "classNo": "",
    "imageUrl": ""
}

# pubYearInfo 가 YYYYMM(6자리) — 실측 186/1124
YEAR_YYYYMM = {
    "titleInfo": "교육격차 해소와 교육안전망 : 교육안전망지원센터 개소식 기념 세미나",
    "typeName": "도서",
    "placeInfo": "디지털도서관 디지털자료실",
    "authorInfo": "한국교육개발원",
    "pubInfo": "서울 : 한국교육개발원, 200609",
    "menuName": "온라인자료",
    "mediaName": "",
    "manageName": "디지털도서관",
    "pubYearInfo": "200609",
    "controlNo": "",
    "docYn": "NL_VIEWER",
    "orgLink": "이용불가",
    "id": "0000000105731094",
    "typeCode": "D1",
    "licYn": "L",
    "licText": "[국립중앙도서관]-무료",
    "regDate": "20161114",
    "detailLink": "/NL/contents/search.do#viewKey=CNTS-00074985109&viewType=C",
    "isbn": "",
    "callNo": "",
    "kdcCode1s": "3",
    "kdcName1s": "사회과학",
    "classNo": "",
    "imageUrl": ""
}

# pubYearInfo 가 YYYYMMDD(8자리) — 실측 168/1124
YEAR_YYYYMMDD = {
    "titleInfo": "교육격차 : 가정 배경과 학교교육의 영향력 분석 = An analysis of educational gap",
    "typeName": "도서",
    "placeInfo": "디지털도서관 디지털자료실",
    "authorInfo": "류방란 김성식",
    "pubInfo": "서울 : 한국교육개발원, 20061229",
    "menuName": "온라인자료",
    "mediaName": "",
    "manageName": "디지털도서관",
    "pubYearInfo": "20061229",
    "controlNo": "",
    "docYn": "NL_VIEWER",
    "orgLink": "이용불가",
    "id": "0000000106053304",
    "typeCode": "D1",
    "licYn": "L",
    "licText": "[국립중앙도서관]-무료",
    "regDate": "20150403",
    "detailLink": "/NL/contents/search.do#viewKey=CNTS-00066726969&viewType=C",
    "isbn": "",
    "callNo": "",
    "kdcCode1s": "3",
    "kdcName1s": "사회과학",
    "classNo": "",
    "imageUrl": ""
}

# pubYearInfo 가 빈 문자열 — 실측 59/1124(5.2%). 연도 필터에서 통째로 탈락한다
YEAR_EMPTY = {
    "titleInfo": "도농간 학교교육 격차의 근본 원인과 해소방안 탐색. 1, 도농간교육격차-발제",
    "typeName": "도서",
    "placeInfo": "디지털도서관 디지털자료실",
    "authorInfo": "민병성",
    "pubInfo": "공주 : 충남교육연구소,",
    "menuName": "온라인자료",
    "mediaName": "",
    "manageName": "디지털도서관",
    "pubYearInfo": "",
    "controlNo": "",
    "docYn": "NL_VIEWER",
    "orgLink": "이용불가",
    "id": "0000000106149799",
    "typeCode": "D1",
    "licYn": "L",
    "licText": "[국립중앙도서관]-무료",
    "regDate": "20150403",
    "detailLink": "/NL/contents/search.do#viewKey=CNTS-00067619987&viewType=C",
    "isbn": "",
    "callNo": "",
    "kdcCode1s": "3",
    "kdcName1s": "사회과학",
    "classNo": "",
    "imageUrl": ""
}

# pubYearInfo 가 9~14자리 변칙 — 실측 8건. 앞 4자 절단만으로는 못 다룬다
YEAR_ODD = {
    "titleInfo": "教育格差 : 階層・地域・学歴",
    "typeName": "도서",
    "placeInfo": "서고자료대출반납(4층)",
    "authorInfo": "著者: 松岡亮二",
    "pubInfo": "筑摩書房",
    "menuName": "오프라인자료",
    "mediaName": "인쇄자료(책자형)",
    "manageName": "본관",
    "pubYearInfo": "2019 (2020 9刷)",
    "controlNo": "JMO202002441",
    "docYn": "N",
    "orgLink": "",
    "id": "694577352",
    "typeCode": "B1",
    "licYn": "N",
    "licText": "[관외이용]-무료",
    "regDate": "20200630",
    "detailLink": "/NL/contents/search.do#viewKey=694577352&viewType=AH1",
    "isbn": "9784480072375",
    "callNo": "370.13-20-13",
    "kdcCode1s": "3",
    "kdcName1s": "사회과학",
    "classNo": "370.13",
    "imageUrl": ""
}

# docYn=N — 원문 없음. 주의: docYn 은 Y/N 불리언이 아니라 열거코드다
NO_FULLTEXT = {
    "titleInfo": "教育格差 : 階層・地域・学歴",
    "typeName": "도서",
    "placeInfo": "서고자료대출반납(4층)",
    "authorInfo": "著者: 松岡亮二",
    "pubInfo": "筑摩書房",
    "menuName": "오프라인자료",
    "mediaName": "인쇄자료(책자형)",
    "manageName": "본관",
    "pubYearInfo": "2019 (2020 9刷)",
    "controlNo": "JMO202002441",
    "docYn": "N",
    "orgLink": "",
    "id": "694577352",
    "typeCode": "B1",
    "licYn": "N",
    "licText": "[관외이용]-무료",
    "regDate": "20200630",
    "detailLink": "/NL/contents/search.do#viewKey=694577352&viewType=AH1",
    "isbn": "9784480072375",
    "callNo": "370.13-20-13",
    "kdcCode1s": "3",
    "kdcName1s": "사회과학",
    "classNo": "370.13",
    "imageUrl": ""
}

# 하이라이트 마크업 재구성본 — clean_html 회귀용 (라이브 미검증, 위 주의 참조)
RAW_WITH_MARKUP = {
    **OFFLINE_FULL,
    "titleInfo": '<span class="searching-word">\uad50\uc721\ubd88\ud3c9\ub4f1</span> :  \ud559\uad50\uad50\uc721\uc758\n   \uad6c\uc870 \ubd84\uc11d',
}

ALL_SAMPLES = [OFFLINE_FULL, ONLINE_SPARSE, YEAR_YYYYMM, YEAR_YYYYMMDD,
               YEAR_EMPTY, YEAR_ODD, NO_FULLTEXT]


def envelope(records, total=None, **extra):
    """검색 응답 봉투 — c2.py 가 total/result 로 1,124건을 실제 회수해 확정한 형태."""
    return {"total": len(records) if total is None else total,
            "result": list(records), **extra}
