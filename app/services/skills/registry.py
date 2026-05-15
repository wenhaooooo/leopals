"""
技能注册表模块

管理所有已注册的技能，提供注册、查询、调用接口
"""

import logging
from typing import Dict, List, Optional, Type, Any
from datetime import datetime

from app.services.skills.base import (
    BaseSkill,
    SkillInput,
    SkillOutput,
    SkillContext
)

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    技能注册表
    
    单例模式，全局唯一的技能管理器
    """
    
    _instance = None
    _skills: Dict[str, BaseSkill] = {}
    _skill_versions: Dict[str, List[str]] = {}
    _skill_categories: Dict[str, List[str]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(
        self,
        skill: BaseSkill,
        override: bool = False
    ) -> bool:
        """
        注册技能
        
        Args:
            skill: 技能实例
            override: 是否覆盖已存在的同名技能
            
        Returns:
            bool: 注册是否成功
        """
        if not skill.name:
            logger.error("技能 name 不能为空")
            return False
        
        if not override and skill.name in self._skills:
            logger.warning(f"技能 {skill.name} 已存在，跳过注册（设置 override=True 覆盖）")
            return False
        
        self._skills[skill.name] = skill
        
        if skill.name not in self._skill_versions:
            self._skill_versions[skill.name] = []
        self._skill_versions[skill.name].append(skill.version)
        
        if skill.category not in self._skill_categories:
            self._skill_categories[skill.category] = []
        if skill.name not in self._skill_categories[skill.category]:
            self._skill_categories[skill.category].append(skill.name)
        
        logger.info(f"注册技能: {skill.name} v{skill.version} ({skill.category})")
        return True
    
    def unregister(self, skill_name: str) -> bool:
        """
        注销技能
        
        Args:
            skill_name: 技能名称
            
        Returns:
            bool: 注销是否成功
        """
        if skill_name not in self._skills:
            logger.warning(f"技能 {skill_name} 不存在")
            return False
        
        skill = self._skills.pop(skill_name)
        category = skill.category
        
        self._skill_versions.pop(skill_name, None)
        
        if category in self._skill_categories and skill_name in self._skill_categories[category]:
            self._skill_categories[category].remove(skill_name)
        
        logger.info(f"注销技能: {skill_name}")
        return True
    
    def get(self, skill_name: str) -> Optional[BaseSkill]:
        """
        获取技能实例
        
        Args:
            skill_name: 技能名称
            
        Returns:
            Optional[BaseSkill]: 技能实例，不存在则返回 None
        """
        return self._skills.get(skill_name)
    
    def has(self, skill_name: str) -> bool:
        """
        检查技能是否存在
        
        Args:
            skill_name: 技能名称
            
        Returns:
            bool: 技能是否存在
        """
        return skill_name in self._skills
    
    def list_all(
        self,
        enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        列出所有技能
        
        Args:
            enabled_only: 是否只列出已启用的技能
            
        Returns:
            List[Dict]: 技能信息列表
        """
        skills = []
        for name, skill in self._skills.items():
            if enabled_only and not skill.enabled:
                continue
            skills.append(skill.get_info())
        return skills
    
    def list_by_category(
        self,
        category: str,
        enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        按类别列出技能
        
        Args:
            category: 技能类别
            enabled_only: 是否只列出已启用的技能
            
        Returns:
            List[Dict]: 技能信息列表
        """
        skills = []
        if category not in self._skill_categories:
            return skills
        
        for name in self._skill_categories[category]:
            skill = self._skills.get(name)
            if skill and (not enabled_only or skill.enabled):
                skills.append(skill.get_info())
        
        return skills
    
    def get_categories(self) -> List[str]:
        """
        获取所有技能类别
        
        Returns:
            List[str]: 类别列表
        """
        return list(self._skill_categories.keys())
    
    async def execute(
        self,
        skill_name: str,
        input: SkillInput,
        context: Optional[SkillContext] = None
    ) -> SkillOutput:
        """
        执行技能
        
        Args:
            skill_name: 技能名称
            input: 输入参数
            context: 执行上下文
            
        Returns:
            SkillOutput: 执行结果
        """
        skill = self.get(skill_name)
        if not skill:
            return SkillOutput(
                success=False,
                error=f"技能 {skill_name} 不存在"
            )
        
        if not skill.enabled:
            return SkillOutput(
                success=False,
                error=f"技能 {skill_name} 已禁用"
            )
        
        try:
            if not await skill.validate(input):
                return SkillOutput(
                    success=False,
                    error="输入参数验证失败"
                )
            
            processed_input = await skill.before_execute(input, context)
            output = await skill.execute(processed_input, context)
            processed_output = await skill.after_execute(output, context)
            
            processed_output.metadata.update({
                "skill_name": skill_name,
                "skill_version": skill.version,
                "executed_at": datetime.now().isoformat()
            })
            
            return processed_output
            
        except Exception as e:
            logger.error(f"执行技能 {skill_name} 失败: {str(e)}")
            return SkillOutput(
                success=False,
                error=f"技能执行失败: {str(e)}"
            )
    
    def enable(self, skill_name: str) -> bool:
        """
        启用技能
        
        Args:
            skill_name: 技能名称
            
        Returns:
            bool: 是否成功
        """
        skill = self.get(skill_name)
        if not skill:
            return False
        
        skill.enabled = True
        logger.info(f"启用技能: {skill_name}")
        return True
    
    def disable(self, skill_name: str) -> bool:
        """
        禁用技能
        
        Args:
            skill_name: 技能名称
            
        Returns:
            bool: 是否成功
        """
        skill = self.get(skill_name)
        if not skill:
            return False
        
        skill.enabled = False
        logger.info(f"禁用技能: {skill_name}")
        return True
    
    def clear(self):
        """清空所有技能"""
        self._skills.clear()
        self._skill_versions.clear()
        self._skill_categories.clear()
        logger.info("清空所有技能")


class registry:
    """便捷的全局注册表访问"""
    
    @staticmethod
    def register(skill: BaseSkill, override: bool = False) -> bool:
        """注册技能"""
        return SkillRegistry().register(skill, override)
    
    @staticmethod
    def get(skill_name: str) -> Optional[BaseSkill]:
        """获取技能"""
        return SkillRegistry().get(skill_name)
    
    @staticmethod
    def has(skill_name: str) -> bool:
        """检查技能是否存在"""
        return SkillRegistry().has(skill_name)
    
    @staticmethod
    def list_all(enabled_only: bool = True) -> List[Dict[str, Any]]:
        """列出所有技能"""
        return SkillRegistry().list_all(enabled_only)
    
    @staticmethod
    async def execute(
        skill_name: str,
        input: SkillInput,
        context: Optional[SkillContext] = None
    ) -> SkillOutput:
        """执行技能"""
        return await SkillRegistry().execute(skill_name, input, context)