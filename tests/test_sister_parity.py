"""자매 프로젝트(kci·scienceON)에서 확인된 결함의 nl 판 회귀 테스트.

한쪽에서 나온 지적은 반대쪽도 확인한다 — 이 규칙으로 오늘까지 같은 패턴이 일곱 번 반복됐다.
⚠️ 단, **API 동작 사실은 이식하지 않는다.** 예컨대 kci·scienceON 의 'total 과대보고'는
   라이브 실측 결과 nl 에는 없었다(230/230, 464/464). 그래서 total_mismatch 분리는 넣지 않았다.
"""
import importlib
import pathlib

import pytest

from nl_mcp import server as s


@pytest.mark.parametrize("mod", [p.stem for p in
                                 sorted(pathlib.Path(__file__).parents[1]
                                        .glob("src/nl_mcp/*.py"))
                                 if p.stem != "__init__"])
def test_every_module_imports(mod):
    """문법 오류 조기 검출 — 자매 프로젝트에서 cli.py 가 깨진 채 테스트를 통과한 적이 있다."""
    importlib.import_module(f"nl_mcp.{mod}")


def test_version_is_read_from_installed_metadata():
    """하드코딩하면 릴리스마다 pyproject 와 어긋난다(자매 프로젝트에서 실제로 방치됐다)."""
    import nl_mcp
    assert nl_mcp.__version__[0].isdigit()


# ── 전송 선택 (기본은 반드시 stdio) ──────────────────────────────────────────

@pytest.fixture
def spy(monkeypatch):
    calls = {}
    monkeypatch.setattr(s.mcp, "run", lambda **kw: calls.update(kw))
    host, port = s.mcp.settings.host, s.mcp.settings.port
    yield calls
    s.mcp.settings.host, s.mcp.settings.port = host, port


def test_default_is_stdio(spy):
    """기존 등록은 인자 없이 서버를 띄우므로 기본이 바뀌면 모든 사용자의 MCP 가 죽는다."""
    s.main([])
    assert spy["transport"] == "stdio"


@pytest.mark.parametrize("transport", ["sse", "streamable-http"])
def test_http_transports_selectable(spy, transport):
    s.main(["--transport", transport])
    assert spy["transport"] == transport


def test_host_and_port_applied(spy):
    s.main(["--transport", "sse", "--host", "0.0.0.0", "--port", "9125"])
    assert s.mcp.settings.host == "0.0.0.0"
    assert s.mcp.settings.port == 9125


def test_unknown_args_do_not_kill_server(spy):
    s.main(["--bogus", "x"])
    assert spy["transport"] == "stdio"


def test_non_numeric_port_env_is_ignored(spy, monkeypatch):
    monkeypatch.setenv("NL_MCP_PORT", "abc")
    before = s.mcp.settings.port
    s.main([])
    assert s.mcp.settings.port == before
