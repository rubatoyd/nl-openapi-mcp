"""Sample JSON responses from National Library Seoji OpenAPI for testing."""

SAMPLE_SEOJI_SEARCH_JSON = {
    "total": 12505,
    "kwd": "토지",
    "pageNum": 1,
    "pageSize": 2,
    "sort": "",
    "result": [
        {
            "titleInfo": "<span class=\"highlight\">토지</span> 그 이상의 역사  :  사진으로 보는 한국<span class=\"highlight\">토지</span>공사 35년사,  1975-2009",
            "authorInfo": " 한국<span class=\"highlight\">토지</span>공사 [편].",
            "pubInfo": "한국<span class=\"highlight\">토지</span>공사,",
            "pubYearInfo": "2009",
            "category": "점자도서",
            "seojiYear": "2012",
            "pageInfo": "275 p. : 삽도, 사진 ; 29 cm. ",
            "detailUrl": "/LI/contents/L10501000000.do?rawid=3197221",
            "isbn": "9788912345678",
        },
        {
            "titleInfo": "<span class=\"highlight\">토지</span>  :  큰글씨책",
            "authorInfo": " 박경리 원작 ;  이형우 각색",
            "pubInfo": "커뮤니케이션북스,",
            "pubYearInfo": "2014",
            "category": "일반도서",
            "seojiYear": "2014",
            "pageInfo": "123 p. ; 30 cm ",
            "detailUrl": "/LI/contents/L10501000000.do?rawid=309571",
            "isbn": "9788998765432",
        }
    ]
}

SAMPLE_SEOJI_EMPTY_JSON = {
    "total": 0,
    "kwd": "없는검색어",
    "pageNum": 1,
    "pageSize": 10,
    "result": []
}

SAMPLE_SEOJI_ERROR_JSON = {
    "errorCode": "010",
    "errorMsg": "NO KEY VALUE"
}
