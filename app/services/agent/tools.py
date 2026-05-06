import asyncio
import logging
from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class GetCourseScheduleInput(BaseModel):
    week: Optional[int] = Field(
        None,
        description="查询的周次，默认为当前周"
    )


class GetCourseScheduleTool(BaseTool):
    name: str = "get_course_schedule"
    description: str = "查询学生课表信息，输入周次获取该周课程安排"
    args_schema: Type[BaseModel] = GetCourseScheduleInput

    def _run(self, week: Optional[int] = None) -> str:
        mock_schedule = {
            "week": week or 8,
            "courses": [
                {"course_name": "高等数学", "time": "周一 8:00-9:40", "location": "教学楼A-301", "teacher": "张教授"},
                {"course_name": "大学英语", "time": "周二 10:00-11:40", "location": "教学楼B-205", "teacher": "李老师"},
                {"course_name": "计算机基础", "time": "周三 14:00-15:40", "location": "实验楼C-102", "teacher": "王老师"},
                {"course_name": "软件工程", "time": "周四 8:00-9:40", "location": "教学楼A-401", "teacher": "陈教授"},
                {"course_name": "体育", "time": "周五 14:00-15:40", "location": "体育馆", "teacher": "赵老师"},
            ]
        }

        result = f"【第{mock_schedule['week']}周课表】\n"
        for course in mock_schedule["courses"]:
            result += f"• {course['course_name']}: {course['time']} | {course['location']} | {course['teacher']}\n"

        logger.info(f"工具调用: get_course_schedule 返回 {len(mock_schedule['courses'])} 门课程")
        return result

    async def _arun(self, week: Optional[int] = None) -> str:
        await asyncio.sleep(1)
        logger.info(f"工具调用: get_course_schedule(week={week})")
        return self._run(week)


class GetGradeInfoInput(BaseModel):
    semester: str = Field(
        ...,
        description="查询的学期，格式如'2024-2025-1'表示2024-2025学年第一学期"
    )


class GetGradeInfoTool(BaseTool):
    name: str = "get_grade_info"
    description: str = "查询学生成绩信息，输入学期获取该学期绩点和成绩分布"
    args_schema: Type[BaseModel] = GetGradeInfoInput

    def _run(self, semester: str) -> str:
        mock_grades = {
            "semester": semester,
            "gpa": 3.75,
            "total_credits": 24,
            "grades": [
                {"course_name": "高等数学", "credit": 4, "grade": 92, "grade_point": 4.0},
                {"course_name": "大学英语", "credit": 3, "grade": 85, "grade_point": 3.7},
                {"course_name": "计算机基础", "credit": 3, "grade": 88, "grade_point": 3.7},
                {"course_name": "软件工程", "credit": 4, "grade": 90, "grade_point": 4.0},
                {"course_name": "体育", "credit": 2, "grade": 95, "grade_point": 4.0},
                {"course_name": "思想政治", "credit": 2, "grade": 82, "grade_point": 3.3},
            ],
            "grade_distribution": {
                "A": 4,
                "B": 2,
                "C": 0,
                "D": 0,
                "F": 0
            }
        }

        result = f"【{semester}学期成绩报告】\n"
        result += f"绩点(GPA): {mock_grades['gpa']}\n"
        result += f"总学分: {mock_grades['total_credits']}\n\n"
        result += "课程明细:\n"
        for course in mock_grades["grades"]:
            result += f"• {course['course_name']}: {course['grade']}分 ({course['credit']}学分)\n"

        logger.info(f"工具调用: get_grade_info 返回绩点 {mock_grades['gpa']}")
        return result

    async def _arun(self, semester: str) -> str:
        await asyncio.sleep(1.5)
        logger.info(f"工具调用: get_grade_info(semester={semester})")
        return self._run(semester)


tools = [GetCourseScheduleTool(), GetGradeInfoTool()]
tool_names = [tool.name for tool in tools]