"""Data models for National Library Seoji OpenAPI bibliographic records."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SeojiRecord:
    """Normalized bibliographic record from National Library of Korea Seoji OpenAPI."""
    control_no: str = ""
    title: str = ""
    author: str = ""
    publisher: str = ""
    pub_year: str = ""
    seoji_year: str = ""
    category: str = ""
    isbn: str = ""
    doc_yn: str = ""
    page_info: str = ""
    detail_url: str = ""
    source: str = "seoji"
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to JSON-serializable dictionary."""
        return {
            "control_no": self.control_no,
            "title": self.title,
            "author": self.author,
            "publisher": self.publisher,
            "pub_year": self.pub_year,
            "seoji_year": self.seoji_year,
            "category": self.category,
            "isbn": self.isbn,
            "doc_yn": self.doc_yn,
            "page_info": self.page_info,
            "detail_url": self.detail_url,
            "source": self.source,
        }


@dataclass
class SearchResult:
    """Normalized search results payload with pagination metadata."""
    total: int = 0
    page_num: int = 1
    page_size: int = 10
    records: List[SeojiRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert payload to JSON-serializable dictionary."""
        return {
            "total": self.total,
            "page_num": self.page_num,
            "page_size": self.page_size,
            "records": [r.to_dict() for r in self.records],
        }
