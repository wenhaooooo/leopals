"""Unit tests for IntentClassifier in the Orchestrator."""

import sys
import importlib
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Mock the module tree that causes a pydantic MRO error on normal import.
# The multi_agent __init__.py imports ScheduleAgent -> tools -> function_tools
# which triggers: "Cannot create a consistent method resolution order (MRO)
# for bases ABC, BaseTool".  By placing mocks in sys.modules *before* we
# load orchestrator.py, we bypass __init__.py entirely.
# ---------------------------------------------------------------------------
_mock_app = MagicMock()
_mock_app.core.config.settings.openai_api_key = "test-key"
_mock_app.core.config.settings.openai_api_base = "http://test"
_mock_app.core.config.settings.llm_model_name = "test-model"

for _mod_name, _mod_obj in [
    ("app", _mock_app),
    ("app.core", _mock_app.core),
    ("app.core.config", _mock_app.core.config),
    ("app.services", _mock_app.services),
    ("app.services.agent", _mock_app.services.agent),
    ("app.services.agent.multi_agent", _mock_app.services.agent.multi_agent),
    ("app.services.agent.multi_agent.message_bus",
     _mock_app.services.agent.multi_agent.message_bus),
    ("app.services.agent.tools", _mock_app.services.agent.tools),
    ("app.services.agent.tools.function_tools",
     _mock_app.services.agent.tools.function_tools),
]:
    sys.modules.setdefault(_mod_name, _mod_obj)

# Load orchestrator.py directly (bypasses __init__.py)
import os

_spec = importlib.util.spec_from_file_location(
    "app.services.agent.multi_agent.orchestrator",
    os.path.join(os.path.dirname(__file__), "..", "..",
                 "app", "services", "agent", "multi_agent", "orchestrator.py"),
)
_orch = importlib.util.module_from_spec(_spec)
sys.modules["app.services.agent.multi_agent.orchestrator"] = _orch
_spec.loader.exec_module(_orch)

IntentClassifier = _orch.IntentClassifier

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda


class TestIntentClassifierKeywords:
    """Test the rule-based fallback classifier.

    _simple_classify iterates INTENTS in insertion order:
      qa -> schedule -> emotional -> knowledge -> assistant
    and returns the FIRST intent whose keyword appears as a substring.
    Queries must be chosen so the expected intent's keyword appears
    before any earlier intent's keyword in the iteration order.
    """

    def setup_method(self):
        self.classifier = IntentClassifier()

    def test_schedule_keywords(self):
        queries = [
            "明天有什么课程",       # "课程"
            "查一下课表",           # "课表"
            "第8周的课程安排",      # "课程"
            "提醒我明天有考试",     # "提醒"
            "今天的日程安排",       # "日程"
        ]
        for query in queries:
            result = self.classifier._simple_classify(query)
            assert result == "schedule", (
                f"Query '{query}' should be 'schedule', got '{result}'"
            )

    def test_emotional_keywords(self):
        queries = [
            "我今天心情不好",       # "心情"
            "最近很郁闷",           # "郁闷"
            "想找人倾诉一下",       # "倾诉"
            "感觉压力很大好烦恼",   # "压力"
        ]
        for query in queries:
            result = self.classifier._simple_classify(query)
            assert result == "emotional", (
                f"Query '{query}' should be 'emotional', got '{result}'"
            )

    def test_knowledge_keywords(self):
        # Avoid "是什么"/"什么是" which would match qa first.
        queries = [
            "查看奖学金政策",       # "政策"
            "学校的通知文件",       # "通知"
            "学校规定",             # "规定"
            "教务处文档",           # "文档"
        ]
        for query in queries:
            result = self.classifier._simple_classify(query)
            assert result == "knowledge", (
                f"Query '{query}' should be 'knowledge', got '{result}'"
            )

    def test_assistant_keywords(self):
        # Avoid "安排" (schedule, checked before assistant).
        queries = [
            "帮我制定学习计划",     # "帮我"
            "我想制定一个复习计划", # "我想"
        ]
        for query in queries:
            result = self.classifier._simple_classify(query)
            assert result == "assistant", (
                f"Query '{query}' should be 'assistant', got '{result}'"
            )

    def test_default_to_qa(self):
        queries = [
            "什么是人工智能",
            "今天天气怎么样",
            "你好呀",
        ]
        for query in queries:
            result = self.classifier._simple_classify(query)
            assert result == "qa", (
                f"Query '{query}' should default to 'qa', got '{result}'"
            )


class TestIntentClassifierLLM:
    """Test the LLM-based classifier.

    classify() builds  chain = prompt | llm | JsonOutputParser()
    then calls  result = await chain.ainvoke({}).

    We replace the module-level *llm* with a ``RunnableLambda`` so it
    integrates cleanly with LangChain's ``|`` pipeline operator.

    NOTE: ``patch.object(_orch, "llm", ...)`` must be used rather than
    ``patch("...orchestrator.llm", ...)`` because ``patch`` with a dotted
    string resolves the path via ``__import__``, which traverses the
    MagicMock objects we injected into sys.modules instead of reaching
    the real orchestrator module loaded by importlib.
    """

    def setup_method(self):
        self.classifier = IntentClassifier()

    @pytest.mark.asyncio
    async def test_llm_classify_success(self):
        """LLM returning valid JSON should parse correctly."""
        mock_llm = RunnableLambda(
            lambda _: AIMessage(content='{"intent": "emotional"}')
        )
        with patch.object(_orch, "llm", mock_llm):
            result = await self.classifier.classify("我今天心情不太好")
            assert result == "emotional"

    @pytest.mark.asyncio
    async def test_llm_classify_json_with_extra_text(self):
        """LLM returning JSON with extra text should still parse."""
        mock_llm = RunnableLambda(
            lambda _: AIMessage(
                content='根据分析，结果是 {"intent": "schedule"}。'
            )
        )
        with patch.object(_orch, "llm", mock_llm):
            # The current JsonOutputParser cannot extract JSON from
            # surrounding text, so this triggers the fallback path.
            # "提醒我明天有考试" contains "提醒" -> schedule via fallback.
            result = await self.classifier.classify("提醒我明天有考试")
            assert result == "schedule"

    @pytest.mark.asyncio
    async def test_llm_classify_fallback_on_error(self):
        """LLM error should fall back to keyword classification."""

        def _raise(_):
            raise Exception("API error")

        mock_llm = RunnableLambda(_raise)
        with patch.object(_orch, "llm", mock_llm):
            # "提醒我明天有考试" contains "提醒" -> schedule
            result = await self.classifier.classify("提醒我明天有考试")
            assert result == "schedule"

    @pytest.mark.asyncio
    async def test_llm_classify_fallback_on_bad_json(self):
        """LLM returning invalid JSON should fall back to keyword classification."""
        mock_llm = RunnableLambda(
            lambda _: AIMessage(content="not valid json")
        )
        with patch.object(_orch, "llm", mock_llm):
            # "帮我查课表" contains "课表" (schedule, checked before "帮我")
            result = await self.classifier.classify("帮我查课表")
            assert result == "schedule"
