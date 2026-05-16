"""Integration tests for the skill system end-to-end lifecycle."""

import pytest
from typing import Optional

from app.services.skills.base import BaseSkill, SkillInput, SkillOutput, SkillContext
from app.services.skills.registry import SkillRegistry


# ---------------------------------------------------------------------------
# Helpers: concrete inputs and skills used by the tests
# ---------------------------------------------------------------------------

class GreetingInput(SkillInput):
    """Input model for GreetingSkill."""
    name: str
    language: Optional[str] = "zh"


class GreetingSkill(BaseSkill):
    """Returns a greeting message based on language preference."""
    name = "greeting"
    description = "Greet a user in their preferred language"
    version = "1.0.0"
    category = "communication"

    async def execute(
        self, input: GreetingInput, context: Optional[SkillContext] = None
    ) -> SkillOutput:
        if input.language == "en":
            message = f"Hello, {input.name}!"
        else:
            message = f"你好，{input.name}！"
        return SkillOutput(success=True, data={"message": message})


class ContextAwareSkill(BaseSkill):
    """A skill that reads user_id from the execution context."""
    name = "context_aware"
    description = "Reads context.user_id"
    version = "1.0.0"
    category = "testing"

    async def execute(
        self, input: SkillInput, context: Optional[SkillContext] = None
    ) -> SkillOutput:
        user_id = context.user_id if context else None
        return SkillOutput(success=True, data={"user_id": user_id})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_registry():
    """Ensure a fresh registry for every test."""
    registry = SkillRegistry()
    registry.clear()
    yield
    registry.clear()


class TestSkillSystemEndToEnd:
    """Full lifecycle integration tests: register -> execute."""

    @pytest.mark.asyncio
    async def test_register_and_execute(self):
        """Register a skill and execute it with default (Chinese) language."""
        registry = SkillRegistry()
        registry.register(GreetingSkill())

        result = await registry.execute(
            "greeting", GreetingInput(name="张三")
        )

        assert result.success is True
        assert result.data["message"] == "你好，张三！"

    @pytest.mark.asyncio
    async def test_execute_with_different_params(self):
        """Execute with language='en' to verify English greeting."""
        registry = SkillRegistry()
        registry.register(GreetingSkill())

        result = await registry.execute(
            "greeting", GreetingInput(name="Alice", language="en")
        )

        assert result.success is True
        assert result.data["message"] == "Hello, Alice!"

    @pytest.mark.asyncio
    async def test_metadata_enriched(self):
        """Verify the registry injects skill_name, skill_version, executed_at."""
        registry = SkillRegistry()
        registry.register(GreetingSkill())

        result = await registry.execute(
            "greeting", GreetingInput(name="张三")
        )

        assert result.success is True
        assert result.metadata["skill_name"] == "greeting"
        assert result.metadata["skill_version"] == "1.0.0"
        assert "executed_at" in result.metadata

    @pytest.mark.asyncio
    async def test_disable_prevents_execution(self):
        """A disabled skill should return a failure output."""
        registry = SkillRegistry()
        registry.register(GreetingSkill())
        registry.disable("greeting")

        result = await registry.execute(
            "greeting", GreetingInput(name="张三")
        )

        assert result.success is False
        assert "禁用" in result.error

    @pytest.mark.asyncio
    async def test_re_enable_allows_execution(self):
        """Re-enabling a disabled skill restores normal execution."""
        registry = SkillRegistry()
        registry.register(GreetingSkill())

        registry.disable("greeting")
        disabled_result = await registry.execute(
            "greeting", GreetingInput(name="张三")
        )
        assert disabled_result.success is False

        registry.enable("greeting")
        enabled_result = await registry.execute(
            "greeting", GreetingInput(name="张三")
        )
        assert enabled_result.success is True
        assert enabled_result.data["message"] == "你好，张三！"

    @pytest.mark.asyncio
    async def test_unregister_removes_skill(self):
        """After unregistering, execution should fail with 'not found'."""
        registry = SkillRegistry()
        registry.register(GreetingSkill())
        registry.unregister("greeting")

        result = await registry.execute(
            "greeting", GreetingInput(name="张三")
        )

        assert result.success is False
        assert "不存在" in result.error

    @pytest.mark.asyncio
    async def test_context_passed_through(self):
        """Verify SkillContext.user_id is accessible inside the skill."""
        registry = SkillRegistry()
        registry.register(ContextAwareSkill())

        ctx = SkillContext(user_id="user-42", session_id="sess-7")
        result = await registry.execute("context_aware", SkillInput(), context=ctx)

        assert result.success is True
        assert result.data["user_id"] == "user-42"
