"""Configuration and environment variables for National Library Seoji OpenAPI."""

import os
from dotenv import load_dotenv

load_dotenv(override=False)

SEOJI_API_URL = "https://librarian.nl.go.kr/LI/search/openApi/seojiSearch.do"
NL_BASE_URL = "https://librarian.nl.go.kr"


def get_api_key() -> str | None:
    """Return configured API key from NL_API_KEY or SEOJI_API_KEY environment variable."""
    return os.getenv("NL_API_KEY") or os.getenv("SEOJI_API_KEY")
