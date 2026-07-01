"""Unit tests for mcp_tools.py — IBD_TESTING=1 (mock) mode."""
import sys
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

APP_DIR = Path(__file__).parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import pytest


def _write_mock_file(data: dict, path: Path):
    path.write_text(json.dumps(data))


@pytest.fixture(autouse=True)
def reset_agw_client():
    import mcp_tools
    original = mcp_tools._agw_client
    yield
    mcp_tools._agw_client = original


@pytest.mark.asyncio
async def test_get_mcp_tools_empty_mock_file(tmp_path):
    import mcp_tools
    mock_path = tmp_path / "mcp-mock.json"
    mock_path.write_text(json.dumps({"servers": {}}))

    with patch.object(mcp_tools, "_MOCK_FILE", mock_path):
        tools = await mcp_tools.get_mcp_tools()
    assert tools == []


@pytest.mark.asyncio
async def test_get_mcp_tools_with_tools_in_mock(tmp_path):
    import mcp_tools
    mock_data = {
        "servers": {
            "test-server": {
                "tools": {
                    "get_data": {
                        "description": "Fetch data",
                        "mock_response": {"result": "ok"},
                        "input_schema": {
                            "properties": {"query": {"type": "string", "description": "A query"}},
                            "required": ["query"],
                        },
                    }
                }
            }
        }
    }
    mock_path = tmp_path / "mcp-mock.json"
    mock_path.write_text(json.dumps(mock_data))

    with patch.object(mcp_tools, "_MOCK_FILE", mock_path):
        tools = await mcp_tools.get_mcp_tools()

    assert len(tools) == 1
    assert tools[0].name == "get_data"
    assert "Fetch data" in tools[0].description


@pytest.mark.asyncio
async def test_get_mcp_tools_no_mock_file(tmp_path):
    """When mock file doesn't exist, returns empty list."""
    import mcp_tools
    missing_path = tmp_path / "nonexistent.json"

    with patch.object(mcp_tools, "_MOCK_FILE", missing_path):
        tools = await mcp_tools.get_mcp_tools()
    assert tools == []


@pytest.mark.asyncio
async def test_get_mcp_tools_multiple_types(tmp_path):
    """Test tools with int, float, bool field types."""
    import mcp_tools
    mock_data = {
        "servers": {
            "server": {
                "tools": {
                    "mixed_types": {
                        "description": "Mixed types",
                        "mock_response": {},
                        "input_schema": {
                            "properties": {
                                "count": {"type": "integer"},
                                "ratio": {"type": "number"},
                                "flag": {"type": "boolean"},
                                "name": {"type": "string"},
                            },
                            "required": ["count"],
                        },
                    }
                }
            }
        }
    }
    mock_path = tmp_path / "mcp-mock.json"
    mock_path.write_text(json.dumps(mock_data))

    with patch.object(mcp_tools, "_MOCK_FILE", mock_path):
        tools = await mcp_tools.get_mcp_tools()

    assert len(tools) == 1


@pytest.mark.asyncio
async def test_mock_tool_returns_mock_response(tmp_path):
    """The mock tool should return the mock_response JSON string when called."""
    import mcp_tools
    mock_data = {
        "servers": {
            "srv": {
                "tools": {
                    "hello": {
                        "description": "Say hello",
                        "mock_response": {"greeting": "hello world"},
                        "input_schema": {"properties": {}, "required": []},
                    }
                }
            }
        }
    }
    mock_path = tmp_path / "mcp-mock.json"
    mock_path.write_text(json.dumps(mock_data))

    with patch.object(mcp_tools, "_MOCK_FILE", mock_path):
        tools = await mcp_tools.get_mcp_tools()

    result = await tools[0].coroutine()
    parsed = json.loads(result)
    assert parsed["greeting"] == "hello world"


def test_set_and_get_user_token():
    import mcp_tools
    mcp_tools.set_user_token("test-jwt-token")
    assert mcp_tools.get_user_token() == "test-jwt-token"
    mcp_tools.set_user_token(None)
    assert mcp_tools.get_user_token() is None


@pytest.mark.asyncio
async def test_get_mcp_tools_invalid_json_mock_file(tmp_path):
    """When mock file contains invalid JSON, returns empty list."""
    import mcp_tools
    mock_path = tmp_path / "mcp-mock.json"
    mock_path.write_text("{ not valid json }")

    with patch.object(mcp_tools, "_MOCK_FILE", mock_path):
        tools = await mcp_tools.get_mcp_tools()
    assert tools == []
