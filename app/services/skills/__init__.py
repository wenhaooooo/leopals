"""
技能系统模块初始化

导出核心类和便捷函数
"""

from app.services.skills.base import (
    BaseSkill,
    SkillInput,
    SkillOutput,
    SkillContext
)
from app.services.skills.registry import SkillRegistry, registry
from app.services.skills.loader import SkillLoader, SkillWatcher

__all__ = [
    "BaseSkill",
    "SkillInput",
    "SkillOutput",
    "SkillContext",
    "SkillRegistry",
    "registry",
    "SkillLoader",
    "SkillWatcher",
]


_skills_initialized = False


async def init_skills():
    """
    初始化技能系统
    
    加载所有内置技能
    """
    global _skills_initialized
    
    if _skills_initialized:
        return
    
    from app.services.skills.impls.schedule_skill import ScheduleSkill
    from app.services.skills.impls.grade_skill import GradeSkill
    from app.services.skills.impls.classroom_skill import ClassroomSkill
    from app.services.skills.impls.notification_skill import NotificationSkill
    
    skills = [
        ScheduleSkill(),
        GradeSkill(),
        ClassroomSkill(),
        NotificationSkill()
    ]
    
    for skill in skills:
        SkillRegistry().register(skill)
    
    _skills_initialized = True
    print(f"✅ 技能系统初始化完成，已加载 {len(skills)} 个技能")


def get_skill(skill_name: str) -> BaseSkill:
    """获取技能实例"""
    return SkillRegistry().get(skill_name)


def list_skills(enabled_only: bool = True):
    """列出所有技能"""
    return SkillRegistry().list_all(enabled_only)
