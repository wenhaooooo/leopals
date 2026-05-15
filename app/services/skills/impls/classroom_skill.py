"""
空教室搜索技能实现
"""

from typing import Optional
from datetime import datetime
from pydantic import Field

from app.services.skills.base import BaseSkill, SkillInput, SkillOutput, SkillContext


class SearchClassroomInput(SkillInput):
    """搜索空教室输入参数"""
    date: str = Field(..., description="日期，格式如'2024-03-15'")
    start_time: str = Field(..., description="开始时间，格式如'09:00'")
    end_time: str = Field(..., description="结束时间，格式如'11:00'")
    capacity: Optional[int] = Field(None, ge=1, description="所需人数")


class ClassroomSkill(BaseSkill):
    """
    空教室搜索技能
    
    搜索指定时间段可用的空教室
    """
    
    name = "classroom_search"
    description = "搜索空闲教室，支持按时间段和容量筛选"
    version = "1.0.0"
    category = "facility"
    
    def __init__(self):
        super().__init__()
        self._classrooms = [
            {"building": "教学楼A", "room": "A-101", "capacity": 50},
            {"building": "教学楼A", "room": "A-201", "capacity": 80},
            {"building": "教学楼A", "room": "A-301", "capacity": 120},
            {"building": "实验楼B", "room": "B-101", "capacity": 40},
            {"building": "图书馆", "room": "五楼研讨室1", "capacity": 20},
            {"building": "图书馆", "room": "五楼研讨室2", "capacity": 15},
        ]
    
    async def execute(
        self,
        input: SearchClassroomInput,
        context: Optional[SkillContext] = None
    ) -> SkillOutput:
        """执行空教室搜索"""
        try:
            datetime.strptime(input.date, "%Y-%m-%d")
            datetime.strptime(input.start_time, "%H:%M")
            datetime.strptime(input.end_time, "%H:%M")
        except ValueError:
            return SkillOutput(
                success=False,
                error="时间格式不正确，请使用标准格式"
            )
        
        import random
        random.seed(hash(input.date + input.start_time))
        
        available = []
        for room in self._classrooms:
            if input.capacity and room["capacity"] < input.capacity:
                continue
            
            if random.random() < 0.7:
                available.append(room)
        
        if not available:
            return SkillOutput(
                success=True,
                data={"available": []},
                metadata={"message": "未找到符合条件的空教室"}
            )
        
        result = {
            "date": input.date,
            "time_range": f"{input.start_time}-{input.end_time}",
            "available": available[:5],
            "total": len(available)
        }
        
        return SkillOutput(
            success=True,
            data=result,
            metadata={"message": f"找到 {len(available)} 个可用教室"}
        )