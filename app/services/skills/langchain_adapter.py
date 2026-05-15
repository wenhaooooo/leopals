"""
技能到LangChain工具的适配器

将技能系统中的技能转换为LangChain可用的工具
"""

import logging
from typing import Any, Dict, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.skills import SkillRegistry, SkillContext

logger = logging.getLogger(__name__)


class SkillToolInput(BaseModel):
    """技能工具的输入参数"""
    skill_name: str = Field(..., description="技能名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="技能参数")


class SkillTool(BaseTool):
    """技能工具包装器"""

    name: str = "skill_executor"
    description: str = "执行指定的技能"
    args_schema: Type[BaseModel] = SkillToolInput

    def __init__(self, skill_name: str, skill_description: str, **kwargs):
        """初始化技能工具"""
        self.skill_name = skill_name
        self.skill_description = skill_description
        super().__init__(
            name=skill_name,
            description=skill_description,
            **kwargs
        )

    async def _arun(self, **kwargs) -> str:
        """异步执行技能"""
        try:
            registry = SkillRegistry()
            
            # 构建技能输入
            from app.services.skills.base import SkillInput
            
            # 动态创建输入类
            input_class = self._create_input_class(kwargs)
            skill_input = input_class(**kwargs)
            
            # 构建上下文
            context = SkillContext(
                user_id=kwargs.get("user_id", "unknown"),
                session_id=kwargs.get("session_id", "default")
            )
            
            # 执行技能
            result = await registry.execute(self.skill_name, skill_input, context)
            
            if result.success:
                return self._format_result(result.data, result.metadata)
            else:
                return f"技能执行失败: {result.error}"
                
        except Exception as e:
            logger.error(f"技能工具执行失败: {str(e)}")
            return f"技能执行失败: {str(e)}"

    def _run(self, **kwargs) -> str:
        """同步执行（LangChain要求）"""
        import asyncio
        return asyncio.run(self._arun(**kwargs))

    def _create_input_class(self, kwargs: Dict[str, Any]) -> Type:
        """动态创建输入类"""
        fields = {}
        for key, value in kwargs.items():
            if key not in ["user_id", "session_id"]:
                fields[key] = (type(value), Field(default=value, description=key))
        
        return type("DynamicSkillInput", (BaseModel,), {"__annotations__": fields})

    def _format_result(self, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """格式化技能结果"""
        import json
        result = {
            "data": data,
            "message": metadata.get("message", "执行成功") if metadata else "执行成功"
        }
        return json.dumps(result, ensure_ascii=False, indent=2)


def convert_skill_to_tool(skill_name: str, skill_description: str) -> SkillTool:
    """
    将技能转换为LangChain工具
    
    Args:
        skill_name: 技能名称
        skill_description: 技能描述
    
    Returns:
        SkillTool实例
    """
    return SkillTool(
        skill_name=skill_name,
        skill_description=skill_description
    )


def convert_all_skills_to_tools() -> list:
    """
    将所有已注册的技能转换为LangChain工具
    
    Returns:
        工具列表
    """
    registry = SkillRegistry()
    skills = registry.list_all(enabled_only=True)
    
    tools = []
    for skill_info in skills:
        skill = registry.get(skill_info["name"])
        if skill:
            tool = convert_skill_to_tool(
                skill_name=skill.name,
                skill_description=skill.description
            )
            tools.append(tool)
    
    logger.info(f"转换了 {len(tools)} 个技能为LangChain工具")
    return tools


def get_skill_tools_by_category(category: str) -> list:
    """
    获取指定类别的技能工具
    
    Args:
        category: 技能类别
    
    Returns:
        工具列表
    """
    registry = SkillRegistry()
    skills = registry.list_by_category(category)
    
    tools = []
    for skill_info in skills:
        skill = registry.get(skill_info["name"])
        if skill:
            tool = convert_skill_to_tool(
                skill_name=skill.name,
                skill_description=skill.description
            )
            tools.append(tool)
    
    return tools