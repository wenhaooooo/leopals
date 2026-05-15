"""
通知提醒技能实现
"""

from typing import Optional
from datetime import datetime
from pydantic import Field

from app.services.skills.base import BaseSkill, SkillInput, SkillOutput, SkillContext


class SetReminderInput(SkillInput):
    """设置提醒输入参数"""
    content: str = Field(..., description="提醒内容")
    remind_time: str = Field(..., description="提醒时间，ISO格式")
    reminder_type: str = Field(default="study", description="提醒类型：study/exam/event")


class NotificationSkill(BaseSkill):
    """
    通知提醒技能
    
    设置学习提醒、考试提醒等
    """
    
    name = "notification_set"
    description = "设置提醒事项，支持学习、考试、活动等类型"
    version = "1.0.0"
    category = "notification"
    
    def __init__(self):
        super().__init__()
        self._reminders = []
    
    async def execute(
        self,
        input: SetReminderInput,
        context: Optional[SkillContext] = None
    ) -> SkillOutput:
        """执行提醒设置"""
        try:
            remind_dt = datetime.fromisoformat(
                input.remind_time.replace("Z", "+08:00")
            )
        except ValueError:
            return SkillOutput(
                success=False,
                error="提醒时间格式不正确，请使用ISO格式"
            )
        
        if remind_dt < datetime.now():
            return SkillOutput(
                success=False,
                error="提醒时间不能是过去时间"
            )
        
        reminder = {
            "id": len(self._reminders) + 1,
            "content": input.content,
            "remind_time": input.remind_time,
            "reminder_type": input.reminder_type,
            "user_id": context.user_id if context else None,
            "created_at": datetime.now().isoformat()
        }
        
        self._reminders.append(reminder)
        
        advance_time = self._calculate_advance_time(
            remind_dt,
            input.reminder_type
        )
        
        result = {
            "reminder": reminder,
            "advance_suggestion": advance_time
        }
        
        return SkillOutput(
            success=True,
            data=result,
            metadata={"message": "提醒设置成功"}
        )
    
    def _calculate_advance_time(self, remind_dt: datetime, reminder_type: str):
        """计算提前提醒时间"""
        if reminder_type == "exam":
            advance = remind_dt.replace(days=1)
            return {
                "message": "建议设置提前提醒",
                "advance_time": advance.isoformat()
            }
        elif reminder_type == "study":
            advance = remind_dt.replace(hours=-1)
            return {
                "message": "建议设置提前提醒",
                "advance_time": advance.isoformat()
            }
        
        return None