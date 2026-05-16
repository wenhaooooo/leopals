"""Tests for the /chat/stream SSE endpoint."""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _mock_multi_agent_module():
    """Inject a mock multi_agent module into sys.modules to avoid import errors.

    The real module chain has an MRO conflict (ABC + BaseTool), so we pre-populate
    sys.modules with a lightweight mock before the endpoint's local import runs.
    """
    mock_module = MagicMock()
    mock_orchestrator = AsyncMock()
    mock_module.get_orchestrator.return_value = mock_orchestrator
    mock_module.orchestrator = mock_orchestrator

    real_entry = sys.modules.get("app.services.agent.multi_agent")
    sys.modules["app.services.agent.multi_agent"] = mock_module
    yield mock_module
    if real_entry is None:
        sys.modules.pop("app.services.agent.multi_agent", None)
    else:
        sys.modules["app.services.agent.multi_agent"] = real_entry


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


class TestChatStreamEndpoint:
    """Tests for POST /chat/stream."""

    def test_chat_stream_returns_sse(self, client, _mock_multi_agent_module):
        """Verify 200 status and SSE content-type."""
        _mock_multi_agent_module.get_orchestrator().process.return_value = {
            "result": "answer", "confidence": 0.9, "agent": "QAAgent"
        }

        response = client.post("/chat/stream", json={"query": "hello"})

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    def test_chat_stream_contains_thought_event(self, client, _mock_multi_agent_module):
        """Verify the response starts with a thought event."""
        _mock_multi_agent_module.get_orchestrator().process.return_value = {
            "result": "answer", "confidence": 0.9, "agent": "QAAgent"
        }

        response = client.post("/chat/stream", json={"query": "hello"})

        assert response.text.startswith("event: thought")

    def test_chat_stream_contains_answer(self, client, _mock_multi_agent_module):
        """Verify the answer content appears in the streamed response."""
        _mock_multi_agent_module.get_orchestrator().process.return_value = {
            "result": "The answer is 42", "confidence": 0.9, "agent": "QAAgent"
        }

        response = client.post("/chat/stream", json={"query": "what is the answer"})

        # The endpoint streams content in 10-char chunks, so check for a chunk
        assert "The answer" in response.text

    def test_chat_stream_empty_query_rejected(self, client):
        """Empty query should return 400."""
        response = client.post("/chat/stream", json={"query": ""})

        assert response.status_code == 400

    def test_chat_stream_whitespace_query_rejected(self, client):
        """Whitespace-only query should return 400."""
        response = client.post("/chat/stream", json={"query": "   "})

        assert response.status_code == 400

    def test_chat_stream_error_handling(self, client, _mock_multi_agent_module):
        """When orchestrator raises, response contains an error event."""
        _mock_multi_agent_module.get_orchestrator().process.side_effect = RuntimeError("boom")

        response = client.post("/chat/stream", json={"query": "trigger error"})

        assert "event: error" in response.text
