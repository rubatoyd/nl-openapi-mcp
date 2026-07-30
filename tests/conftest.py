"""pytest fixtures for nl-openapi-mcp tests."""

import pytest
from nl_mcp.models import SeojiRecord


@pytest.fixture
def sample_records():
    return [
        SeojiRecord(
            control_no="3197221",
            title="토지 그 이상의 역사 : 사진으로 보는 한국토지공사 35년사",
            author="한국토지공사 [편].",
            publisher="한국토지공사",
            pub_year="2009",
            seoji_year="2012",
            category="점자도서",
            isbn="9788912345678",
            doc_yn="N",
            page_info="275 p.",
            detail_url="https://librarian.nl.go.kr/LI/contents/L10501000000.do?rawid=3197221",
        ),
        SeojiRecord(
            control_no="309571",
            title="토지 : 큰글씨책",
            author="박경리 원작 ; 이형우 각색",
            publisher="커뮤니케이션북스",
            pub_year="2014",
            seoji_year="2014",
            category="일반도서",
            isbn="9788998765432",
            doc_yn="Y",
            page_info="123 p.",
            detail_url="https://librarian.nl.go.kr/LI/contents/L10501000000.do?rawid=309571",
        ),
    ]
