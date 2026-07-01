"""Unit tests for load_skill_resources.py."""
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

APP_DIR = Path(__file__).parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import pytest


VALID_SKILL_CONTENT = """---
name: test-skill
description: A test skill for unit testing
---
# Test Skill

This is the body of the test skill. It provides instructions.
"""

MISSING_NAME_CONTENT = """---
description: Missing name field
---
Body text.
"""

NO_FRONTMATTER_CONTENT = """Just some content without frontmatter."""


def _write_skill(skills_dir: Path, skill_name: str, content: str):
    """Write skill content to SKILL.md in the skills directory."""
    skill_dir = skills_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content)
    return skill_file


def test_validate_and_parse_frontmatter_valid():
    from load_skill_resources import _validate_and_parse_frontmatter
    name, description = _validate_and_parse_frontmatter(VALID_SKILL_CONTENT)
    assert name == "test-skill"
    assert description == "A test skill for unit testing"


def test_validate_and_parse_frontmatter_no_opening():
    from load_skill_resources import _validate_and_parse_frontmatter
    with pytest.raises(ValueError, match="missing frontmatter"):
        _validate_and_parse_frontmatter(NO_FRONTMATTER_CONTENT)


def test_validate_and_parse_frontmatter_missing_field():
    from load_skill_resources import _validate_and_parse_frontmatter
    with pytest.raises(ValueError, match="missing required field"):
        _validate_and_parse_frontmatter(MISSING_NAME_CONTENT)


def test_validate_and_parse_no_closing_fence():
    from load_skill_resources import _validate_and_parse_frontmatter
    no_closing = "---\nname: foo\ndescription: bar\n"
    with pytest.raises(ValueError, match="not closed"):
        _validate_and_parse_frontmatter(no_closing)


def test_get_load_skill_resource_tool_no_skills_dir(tmp_path):
    """When skills dir doesn't exist, returns empty list."""
    from load_skill_resources import get_load_skill_resource_tool
    non_existent = tmp_path / "skills"
    with patch("load_skill_resources._SKILLS_DIR", non_existent):
        tools = get_load_skill_resource_tool()
    assert tools == []


def test_get_load_skill_resource_tool_with_valid_skill(tmp_path):
    """When a valid skill exists, returns a StructuredTool."""
    from load_skill_resources import get_load_skill_resource_tool
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "my-skill", VALID_SKILL_CONTENT)

    with patch("load_skill_resources._SKILLS_DIR", skills_dir):
        tools = get_load_skill_resource_tool()

    assert len(tools) == 1
    assert tools[0].name == "load"


def test_get_load_skill_resource_tool_description_includes_skill(tmp_path):
    from load_skill_resources import get_load_skill_resource_tool
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "my-skill", VALID_SKILL_CONTENT)

    with patch("load_skill_resources._SKILLS_DIR", skills_dir):
        tools = get_load_skill_resource_tool()

    description = tools[0].description
    assert "test-skill" in description or "my-skill" in description or "load" in description


@pytest.mark.asyncio
async def test_load_tool_invoke_returns_skill_content(tmp_path):
    """Calling the load tool with a valid skill path returns its content."""
    from load_skill_resources import get_load_skill_resource_tool
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "my-skill", VALID_SKILL_CONTENT)

    with patch("load_skill_resources._SKILLS_DIR", skills_dir):
        tools = get_load_skill_resource_tool()
        tool = tools[0]
        result = await tool.coroutine(path="my-skill")

    assert "Test Skill" in result or "test-skill" in result


@pytest.mark.asyncio
async def test_load_tool_invoke_invalid_skill(tmp_path):
    """Calling the load tool with an unknown skill path returns an error message."""
    from load_skill_resources import get_load_skill_resource_tool
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "my-skill", VALID_SKILL_CONTENT)

    with patch("load_skill_resources._SKILLS_DIR", skills_dir):
        tools = get_load_skill_resource_tool()
        tool = tools[0]
        result = await tool.coroutine(path="nonexistent-skill")

    assert "not found" in result.lower() or "error" in result.lower()
