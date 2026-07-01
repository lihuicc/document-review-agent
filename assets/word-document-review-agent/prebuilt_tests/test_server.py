"""Server tests — verify A2A server starts and responds correctly."""
import os
import pytest
import httpx

pytestmark = pytest.mark.skipif(
    os.environ.get("IBD_TESTING") == "1",
    reason="Server tests skipped in IBD_TESTING mode (requires production credentials)",
)


@pytest.mark.server
def test_agent_card_endpoint(start_agent):
    port = start_agent["port"]
    response = httpx.get(f"http://localhost:{port}/.well-known/agent.json", timeout=10)
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "skills" in data


@pytest.mark.server
def test_agent_card_has_skills(start_agent):
    port = start_agent["port"]
    response = httpx.get(f"http://localhost:{port}/.well-known/agent.json", timeout=10)
    assert response.status_code == 200
    data = response.json()
    assert len(data.get("skills", [])) > 0
