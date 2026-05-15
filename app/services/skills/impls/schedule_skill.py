"""
课表查询技能实现
"""

from typing import Optional
from pydantic import Field

from app.services.skills.base import BaseSkill, SkillInput, SkillOutput, SkillContext


class GetScheduleInput(SkillInput):
    """查询课表输入参数"""
    week: Optional[int] = Field(None, ge=1, le=20, description="周次，1-20")
    day_of_week: Optional[int] = Field(None, ge=1, le=7, description="星期几，1-7")


class ScheduleSkill(BaseSkill):
    """
    课表查询技能
    
    查询指定周次的课程安排
    """
    
    name = "schedule_query"
    description = "查询学生课表信息，支持按周次和星期筛选"
    version = "1.0.0"
    category = "schedule"
    
    def __init__(self):
        super().__init__()
        self._mock_db = self._init_mock_data()
    
    def _init_mock_data(self):
        """初始化模拟数据"""
        return {
            1: {
                "courses": [
                    {
                        "name": "高等数学A",
                        "teacher": "张教授",
                        "location": "教学楼A-301",
                        "time": "周一 08:00-09:40",
                        "weeks": "1-16"
                    },
                    {
                        "name": "大学英语(视听说)",
                        "teacher": "李老师",
                        "location": "外语楼205",
                        "time": "周一 10:00-11:40",
                        "weeks": "1-16"
                    },
                    {
                        "name": "计算机基础",
                        "teacher": "王老师",
                        "location": "实验楼C-102",
                        "time": "周三 14:00-15:40",
                        "weeks": "1-16"
                    },
                    {
                        "name": "软件工程",
                        "teacher": "陈教授",
                        "location": "教学楼A-401",
                        "time": "周四 08:00-09:40",
                        "weeks": "1-16"
                    },
                    {
                        "name": "体育",
                        "teacher": "赵老师",
                        "location": "体育馆",
                        "time": "周五 14:00-15:40",
                        "weeks": "1-16"
                    }
                ]
            }
        }
    
    async def execute(
        self,
        input: GetScheduleInput,
        context: Optional[SkillContext] = None
    ) -> SkillOutput:
        """执行课表查询"""
        week = input.week or 8
        
        if week not in self._mock_db:
            schedule = self._generate_schedule(week)
        else:
            schedule = self._mock_db[week]
        
        courses = schedule["courses"]
        
        if input.day_of_week:
            day_map = {
                1: "周一",
                2: "周二",
                3: "周三",
                4: "周四",
                5: "周五",
                6: "周六",
                7: "周日"
            }
            courses = [c for c in courses if day_map.get(input.day_of_week) in c["time"]]
        
        if not courses:
            return SkillOutput(
                success=True,
                data={"week": week, "courses": []},
                metadata={"message": f"第{week}周暂无课程安排"}
            )
        
        result = {
            "week": week,
            "courses": courses,
            "count": len(courses)
        }
        
        return SkillOutput(
            success=True,
            data=result,
            metadata={"message": f"查询到 {len(courses)} 门课程"}
        )
    
    def _generate_schedule(self, week: int):
        """生成其他周的课表（模拟）"""
        base = self._mock_db[1].copy()
        return {"courses": base["courses"]}