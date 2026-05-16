"""Unit tests for SkillRegistry."""

import pytest
from app.services.skills.registry import SkillRegistry
from app.services.skills.base import BaseSkill, SkillInput, SkillOutput, SkillContext


class ConcreteSkill(BaseSkill):
    name = "test_skill"
    description = "A test skill"
    version = "1.0.0"
    category = "testing"

    async def execute(self, input: SkillInput, context=None) -> SkillOutput:
        return SkillOutput(success=True, data={"result": "ok"})


class FailingSkill(BaseSkill):
    name = "failing_skill"
    description = "A skill that fails"
    version = "1.0.0"
    category = "testing"

    async def execute(self, input: SkillInput, context=None) -> SkillOutput:
        raise RuntimeError("Skill execution failed")


@pytest.fixture(autouse=True)
def clean_registry():
    registry = SkillRegistry()
    registry.clear()
    yield
    registry.clear()


class TestSkillRegistryRegister:

    def test_register_new_skill(self):
        registry = SkillRegistry()
        skill = ConcreteSkill()
        result = registry.register(skill)
        assert result is True
        assert registry.has("test_skill")

    def test_register_duplicate_rejected(self):
        registry = SkillRegistry()
        registry.register(ConcreteSkill())
        result = registry.register(ConcreteSkill())
        assert result is False

    def test_register_duplicate_with_override(self):
        registry = SkillRegistry()
        registry.register(ConcreteSkill())
        skill2 = ConcreteSkill()
        skill2.version = "2.0.0"
        result = registry.register(skill2, override=True)
        assert result is True
        assert registry.get("test_skill").version == "2.0.0"

    def test_register_empty_name_rejected(self):
        registry = SkillRegistry()
        skill = ConcreteSkill()
        skill.name = ""
        result = registry.register(skill)
        assert result is False


class TestSkillRegistryUnregister:

    def test_unregister_existing(self):
        registry = SkillRegistry()
        registry.register(ConcreteSkill())
        result = registry.unregister("test_skill")
        assert result is True
        assert not registry.has("test_skill")

    def test_unregister_nonexistent(self):
        registry = SkillRegistry()
        result = registry.unregister("nonexistent")
        assert result is False


class TestSkillRegistryEnableDisable:

    def test_disable_skill(self):
        registry = SkillRegistry()
        registry.register(ConcreteSkill())
        result = registry.disable("test_skill")
        assert result is True
        assert registry.get("test_skill").enabled is False

    def test_enable_skill(self):
        registry = SkillRegistry()
        skill = ConcreteSkill()
        skill.enabled = False
        registry.register(skill)
        result = registry.enable("test_skill")
        assert result is True
        assert registry.get("test_skill").enabled is True

    def test_disable_nonexistent(self):
        registry = SkillRegistry()
        result = registry.disable("nonexistent")
        assert result is False


class TestSkillRegistryList:

    def test_list_all(self):
        registry = SkillRegistry()
        registry.register(ConcreteSkill())
        skills = registry.list_all()
        assert len(skills) == 1
        assert skills[0]["name"] == "test_skill"

    def test_list_by_category(self):
        registry = SkillRegistry()
        registry.register(ConcreteSkill())
        skills = registry.list_by_category("testing")
        assert len(skills) == 1

    def test_list_by_category_empty(self):
        registry = SkillRegistry()
        registry.register(ConcreteSkill())
        skills = registry.list_by_category("nonexistent")
        assert len(skills) == 0


class TestSkillRegistryExecute:

    @pytest.mark.asyncio
    async def test_execute_success(self):
        registry = SkillRegistry()
        registry.register(ConcreteSkill())
        result = await registry.execute("test_skill", SkillInput())
        assert result.success is True
        assert result.data == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_execute_nonexistent(self):
        registry = SkillRegistry()
        result = await registry.execute("nonexistent", SkillInput())
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_disabled_skill(self):
        registry = SkillRegistry()
        registry.register(ConcreteSkill())
        registry.disable("test_skill")
        result = await registry.execute("test_skill", SkillInput())
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_metadata_enriched(self):
        registry = SkillRegistry()
        registry.register(ConcreteSkill())
        context = SkillContext(user_id="user123", session_id="sess456")
        result = await registry.execute("test_skill", SkillInput(), context=context)
        assert result.success is True
        assert "skill_name" in result.metadata
        assert result.metadata["skill_name"] == "test_skill"
        assert "skill_version" in result.metadata
        assert "executed_at" in result.metadata
