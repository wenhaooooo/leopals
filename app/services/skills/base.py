"""
技能系统基类模块

定义技能的抽象接口和输入输出模型
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field


class SkillInput(BaseModel):
    """技能输入参数基类"""
    pass


class SkillOutput(BaseModel):
    """技能输出结果基类"""
    success: bool = Field(description="执行是否成功")
    data: Any = Field(default=None, description="执行结果数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class SkillContext(BaseModel):
    """技能执行上下文"""
    user_id: Optional[str] = Field(default=None, description="用户ID")
    session_id: Optional[str] = Field(default=None, description="会话ID")
    extra: Dict[str, Any] = Field(default_factory=dict, description="额外信息")


class BaseSkill(ABC):
    """
    技能基类
    
    所有技能必须继承此类并实现 execute 方法
    """
    
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    category: str = "general"
    enabled: bool = True
    
    def __init__(self):
        if not self.name:
            self.name = self.__class__.__name__.replace("Skill", "").lower()
    
    @abstractmethod
    async def execute(
        self,
        input: SkillInput,
        context: Optional[SkillContext] = None
    ) -> SkillOutput:
        """
        执行技能
        
        Args:
            input: 技能输入参数
            context: 执行上下文
            
        Returns:
            SkillOutput: 执行结果
        """
        pass
    
    async def validate(self, input: SkillInput) -> bool:
        """
        验证输入参数
        
        Args:
            input: 技能输入参数
            
        Returns:
            bool: 验证是否通过
        """
        try:
            input.model_validate(input)
            return True
        except Exception:
            return False
    
    async def before_execute(
        self,
        input: SkillInput,
        context: Optional[SkillContext] = None
    ) -> SkillInput:
        """
        执行前钩子，可用于参数预处理
        
        Args:
            input: 技能输入参数
            context: 执行上下文
            
        Returns:
            SkillInput: 处理后的输入参数
        """
        return input
    
    async def after_execute(
        self,
        output: SkillOutput,
        context: Optional[SkillContext] = None
    ) -> SkillOutput:
        """
        执行后钩子，可用于结果后处理
        
        Args:
            output: 技能输出结果
            context: 执行上下文
            
        Returns:
            SkillOutput: 处理后的输出结果
        """
        return output
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取技能信息
        
        Returns:
            Dict: 技能信息字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "enabled": self.enabled,
            "input_schema": self._get_input_schema(),
            "output_schema": self._get_output_schema()
        }
    
    def _get_input_schema(self) -> Dict[str, Any]:
        """获取输入参数 Schema"""
        if hasattr(self, "InputType"):
            return self.InputType.model_json_schema()
        return SkillInput.model_json_schema()
    
    def _get_output_schema(self) -> Dict[str, Any]:
        """获取输出结果 Schema"""
        return SkillOutput.model_json_schema()