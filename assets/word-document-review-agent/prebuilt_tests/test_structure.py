"""Structure tests — verify required files and modules exist."""
import pytest
from pathlib import Path


AGENT_ROOT = Path(__file__).parent.parent
APP_DIR = AGENT_ROOT / "app"

REQUIRED_FILES = [
    APP_DIR / "__init__.py",
    APP_DIR / "main.py",
    APP_DIR / "agent.py",
    APP_DIR / "agent_executor.py",
    APP_DIR / "mcp_tools.py",
    APP_DIR / "util.py",
    APP_DIR / "load_skill_resources.py",
    APP_DIR / "tools" / "document_parser.py",
    APP_DIR / "tools" / "document_annotator.py",
    AGENT_ROOT / "requirements.txt",
    AGENT_ROOT / "conftest.py",
]


@pytest.mark.structure
@pytest.mark.parametrize("filepath", REQUIRED_FILES, ids=[str(f.relative_to(AGENT_ROOT)) for f in REQUIRED_FILES])
def test_required_file_exists(filepath: Path):
    assert filepath.exists(), f"Required file missing: {filepath}"


@pytest.mark.structure
def test_agent_decorators_present():
    content = (APP_DIR / "agent.py").read_text()
    assert "agent_model" in content
    assert "agent_config" in content
    assert "prompt_section" in content


@pytest.mark.structure
def test_milestone_logging_present():
    content = (APP_DIR / "agent.py").read_text()
    for milestone in ["M1.achieved", "M2.achieved", "M3.achieved", "M4.achieved", "M5.achieved"]:
        assert milestone in content, f"Missing milestone log: {milestone}"


@pytest.mark.structure
def test_no_src_imports():
    for py_file in APP_DIR.rglob("*.py"):
        content = py_file.read_text()
        assert "from src." not in content, f"Forbidden 'from src.' import in {py_file}"
        assert "import src." not in content, f"Forbidden 'import src.' in {py_file}"
