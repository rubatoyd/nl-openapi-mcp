"""Unit tests for nl_mcp HTTP client."""

from unittest.mock import MagicMock, patch
import pytest
from nl_mcp.client import NlSeojiClient, NlSeojiError
from samples import SAMPLE_SEOJI_SEARCH_JSON


def test_search_missing_key():
    client = NlSeojiClient(api_key="")
    with pytest.raises(NlSeojiError, match="NL_API_KEY"):
        client.search(kwd="도서관")


@patch("requests.Session.get")
def test_search_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_SEOJI_SEARCH_JSON
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    client = NlSeojiClient(api_key="test-key")
    res = client.search(kwd="토지", page_num=1, page_size=2)

    assert res.total == 12505
    assert len(res.records) == 2
    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["key"] == "test-key"
    assert kwargs["params"]["kwd"] == "토지"
    assert kwargs["params"]["pageNum"] == 1
    assert kwargs["params"]["pageSize"] == 2


@patch("requests.Session.get")
def test_detail_search_params(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_SEOJI_SEARCH_JSON
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    client = NlSeojiClient(api_key="test-key")
    res = client.search(title="토지", author="박경리")

    _, kwargs = mock_get.call_args
    params = kwargs["params"]
    assert params["detailSearch"] == "true"
    assert params["f1"] == "title"
    assert params["v1"] == "토지"
    assert params["and1"] == "AND"
    assert params["f2"] == "author"
    assert params["v2"] == "박경리"
    assert "kwd" not in params
