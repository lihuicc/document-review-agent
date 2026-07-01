"""Unit tests for util.py helper functions."""
import sys
from pathlib import Path

APP_DIR = Path(__file__).parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import pytest
from unittest.mock import MagicMock

from util import enhance_tool_description, enhance_tool_name


def _make_mock_tool(server_name: str, name: str, description: str = "A test tool") -> MagicMock:
    tool = MagicMock()
    tool.server_name = server_name
    tool.name = name
    tool.description = description
    tool.fragment_name = server_name
    tool.input_schema = {"properties": {}, "required": []}
    return tool


def test_enhance_tool_description_basic():
    tool = _make_mock_tool("my-server", "my_tool", "Does something")
    result = enhance_tool_description(tool)
    assert "my-server" in result
    assert "Does something" in result


def test_enhance_tool_description_none():
    result = enhance_tool_description(None)
    assert result == ""


def test_enhance_tool_name_simple():
    tool = _make_mock_tool("simple-server", "my_tool")
    result = enhance_tool_name(tool)
    assert "my_tool" in result
    assert "simple-server" in result


def test_enhance_tool_name_with_colon_segments():
    tool = _make_mock_tool("sap.mcpbuilder:apiResource:cost-center:v1", "list_cost_centers")
    result = enhance_tool_name(tool)
    assert "list_cost_centers" in result
    assert "cost" in result.lower() or "v1" in result


def test_enhance_tool_name_none():
    result = enhance_tool_name(None)
    assert result == ""


def test_enhance_tool_name_max_64_chars():
    long_server = "a" * 50
    long_tool = "b" * 30
    tool = _make_mock_tool(long_server, long_tool)
    result = enhance_tool_name(tool)
    assert len(result) <= 64


def test_enhance_tool_name_sanitizes_special_chars():
    tool = _make_mock_tool("org:type:res:v1", "tool.name-here")
    result = enhance_tool_name(tool)
    # Should only contain a-zA-Z0-9-_
    import re
    assert re.match(r'^[a-zA-Z0-9\-_]+$', result), f"Invalid chars in: {result}"
