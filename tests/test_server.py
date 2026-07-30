"""Unit tests for nl_mcp server tools."""

from unittest.mock import MagicMock, patch
import pytest

from nl_mcp.server import nl_collect, nl_detail, nl_search, nl_status
from samples import SAMPLE_SEOJI_SEARCH_JSON


@patch("nl_mcp.server.get_api_key", return_value=None)
def test_nl_status_no_key(mock_get_key):
    res = nl_status()
    assert res["success"] is False
    assert res["api_key_configured"] is False


@patch("requests.Session.get")
@patch("nl_mcp.server.get_api_key", return_value="test-key")
def test_nl_status_ok(mock_get_key, mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_SEOJI_SEARCH_JSON
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    res = nl_status()
    assert res["success"] is True
    assert res["api_status"] == "ok"


@patch("requests.Session.get")
@patch("nl_mcp.client.get_api_key", return_value="test-key")
def test_nl_search_tool(mock_get_key, mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_SEOJI_SEARCH_JSON
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    res = nl_search(kwd="토지", page_num=1, page_size=2)
    assert res["success"] is True
    assert res["total"] == 12505
    assert len(res["records"]) == 2


@patch("requests.Session.get")
@patch("nl_mcp.client.get_api_key", return_value="test-key")
def test_nl_detail_tool(mock_get_key, mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_SEOJI_SEARCH_JSON
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    res = nl_detail(control_no="3197221", title="토지")
    assert res["success"] is True
    assert res["record"]["control_no"] == "3197221"


@patch("requests.Session.get")
@patch("nl_mcp.client.get_api_key", return_value="test-key")
def test_nl_collect_tool(mock_get_key, mock_get, tmp_path):
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_SEOJI_SEARCH_JSON
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    out_file = str(tmp_path / "collect_test.xlsx")
    res = nl_collect(output_path=out_file, kwd="토지", max_records=2)
    assert res["success"] is True
    assert res["count"] == 2
    assert res["output_path"] == out_file
