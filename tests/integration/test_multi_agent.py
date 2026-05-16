"""Integration tests for the multi-agent system: MessageBus, AgentSelector, Orchestrator."""

import importlib.util
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Isolated module loading
#
# The multi_agent __init__.py imports all agent classes, which pull in tools
# that trigger an MRO error at class-definition time.  We bypass the package
# __init__ entirely by stubbing the multi_agent package namespace and loading
# only message_bus.py and orchestrator.py from disk.
# ---------------------------------------------------------------------------

_PKG = "app.services.agent.multi_agent"

# Stub the multi_agent package so Python doesn't execute its __init__.py.
# The parent packages (app, app.services, app.services.agent) have empty
# __init__.py files and load fine normally.
if _PKG not in sys.modules:
    _stub = ModuleType(_PKG)
    _stub.__path__ = []
    _stub.__package__ = _PKG
    sys.modules[_PKG] = _stub


def _load_module(name: str, filepath: str) -> ModuleType:
    """Load a single Python module from *filepath* under *name*."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_msg_bus_mod = _load_module(
    f"{_PKG}.message_bus",
    "app/services/agent/multi_agent/message_bus.py",
)
_orch_mod = _load_module(
    f"{_PKG}.orchestrator",
    "app/services/agent/multi_agent/orchestrator.py",
)

MessageBus = _msg_bus_mod.MessageBus
AgentSelector = _orch_mod.AgentSelector
Orchestrator = _orch_mod.Orchestrator


# ---------------------------------------------------------------------------
# TestMessageBus
# ---------------------------------------------------------------------------

class TestMessageBus:
    """Tests for MessageBus registration, routing, and error handling."""

    def setup_method(self):
        self.bus = MessageBus()

    def test_register_and_list(self):
        """Register an agent and verify it appears in get_registered_agents()."""
        mock_agent = MagicMock()
        self.bus.register_agent("TestAgent", mock_agent)

        registered = self.bus.get_registered_agents()
        assert "TestAgent" in registered
        assert len(registered) == 1

    @pytest.mark.asyncio
    async def test_send_to_registered_agent(self):
        """Send a message to a registered agent with a mock process method."""
        mock_agent = MagicMock()
        mock_agent.process = AsyncMock(return_value={"result": "ok", "confidence": 0.95})
        self.bus.register_agent("MockAgent", mock_agent)

        result = await self.bus.send("MockAgent", {"query": "hello", "context": {}})

        assert result == {"result": "ok", "confidence": 0.95}
        mock_agent.process.assert_awaited_once_with("hello", {})

    @pytest.mark.asyncio
    async def test_send_to_unregistered_raises(self):
        """Sending to a non-existent agent raises ValueError."""
        with pytest.raises(ValueError, match="未注册"):
            await self.bus.send("GhostAgent", {"query": "hello"})


# ---------------------------------------------------------------------------
# TestAgentSelector
# ---------------------------------------------------------------------------

class TestAgentSelector:
    """Tests for AgentSelector intent-to-agent mapping."""

    def setup_method(self):
        self.selector = AgentSelector()

    def test_select_qa(self):
        assert self.selector.select("qa") == "QAAgent"

    def test_select_schedule(self):
        assert self.selector.select("schedule") == "ScheduleAgent"

    def test_select_emotional(self):
        assert self.selector.select("emotional") == "EmotionalAgent"

    def test_select_unknown_defaults_to_qa(self):
        """An unknown intent falls back to QAAgent."""
        assert self.selector.select("nonexistent") == "QAAgent"


# ---------------------------------------------------------------------------
# TestOrchestrator
# ---------------------------------------------------------------------------

class TestOrchestrator:
    """Tests for Orchestrator intent classification, routing, and fallback."""

    def setup_method(self):
        self.orchestrator = Orchestrator()

    @pytest.mark.asyncio
    @patch.object(_orch_mod, "message_bus")
    async def test_process_qa_intent(self, mock_bus):
        """QA intent is routed to QAAgent via the message bus."""
        self.orchestrator.intent_classifier.classify = AsyncMock(return_value="qa")
        mock_bus.send = AsyncMock(return_value={"result": "42", "confidence": 0.9})

        result = await self.orchestrator.process("What is AI?")

        assert result["agent"] == "QAAgent"
        assert result["result"] == "42"
        mock_bus.send.assert_awaited_once_with(
            "QAAgent", {"query": "What is AI?", "context": None}
        )

    @pytest.mark.asyncio
    @patch.object(_orch_mod, "message_bus")
    async def test_process_schedule_intent(self, mock_bus):
        """Schedule intent is routed to ScheduleAgent."""
        self.orchestrator.intent_classifier.classify = AsyncMock(return_value="schedule")
        mock_bus.send = AsyncMock(return_value={"result": "Math at 9am", "confidence": 0.85})

        result = await self.orchestrator.process("What's my schedule?")

        assert result["agent"] == "ScheduleAgent"
        assert result["result"] == "Math at 9am"
        mock_bus.send.assert_awaited_once_with(
            "ScheduleAgent", {"query": "What's my schedule?", "context": None}
        )

    @pytest.mark.asyncio
    @patch.object(_orch_mod, "message_bus")
    async def test_process_fallback_on_valueerror(self, mock_bus):
        """When the primary agent raises ValueError, Orchestrator falls back to QAAgent."""
        self.orchestrator.intent_classifier.classify = AsyncMock(return_value="knowledge")

        fallback_result = {"result": "fallback answer", "confidence": 0.5}
        mock_bus.send = AsyncMock(
            side_effect=[ValueError("智能体 KnowledgeAgent 未注册"), fallback_result]
        )

        result = await self.orchestrator.process("scholarship policy")

        assert result["agent"] == "QAAgent (fallback)"
        assert result["result"] == "fallback answer"
        assert mock_bus.send.await_count == 2
        mock_bus.send.assert_any_await(
            "KnowledgeAgent", {"query": "scholarship policy", "context": None}
        )
        mock_bus.send.assert_any_await(
            "QAAgent", {"query": "scholarship policy", "context": None}
        )
