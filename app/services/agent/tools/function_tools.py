"""
基于 LangChain Function Calling 的业务工具封装

实现 "LLM -> 工具调用 -> 业务系统闭环" 的架构模式：

1. LangChain BaseTool: 定义标准工具接口
2. Pydantic Schema: 参数校验和类型安全
3. Async Support: 异步执行，支持高并发
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Type, Dict, Any, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool, tool
from langchain_core.callbacks import CallbackManagerForToolRun

logger = logging.getLogger(__name__)


class ScheduleInput(BaseModel):
    """日程查询输入参数"""
    week: Optional[int] = Field(None, description="周次，默认为当前周")
    day_of_week: Optional[int] = Field(None, ge=1, le=7, description="星期几，1-7")


class GradeInput(BaseModel):
    """成绩查询输入参数"""
    semester: str = Field(..., description="学期，格式如'2024-2025-1'")


class ReminderInput(BaseModel):
    """设置提醒输入参数"""
    content: str = Field(..., description="提醒内容")
    remind_time: str = Field(..., description="提醒时间，ISO格式")
    reminder_type: str = Field(default="study", description="提醒类型：study/exam/event")


class SearchScheduleInput(BaseModel):
    """搜索空闲教室输入参数"""
    date: str = Field(..., description="日期，格式如'2024-03-15'")
    start_time: str = Field(..., description="开始时间，格式如'09:00'")
    end_time: str = Field(..., description="结束时间，格式如'11:00'")
    capacity: Optional[int] = Field(None, description="所需人数")


class ConflictCheckInput(BaseModel):
    """冲突检测输入参数"""
    start_time: str = Field(..., description="开始时间，ISO格式")
    end_time: str = Field(..., description="结束时间，ISO格式")


class BaseBusinessTool(ABC, BaseTool):
    """
    业务工具基类

    设计原则：
    1. 统一接口：所有工具继承 BaseTool
    2. 类型安全：Pydantic Schema 定义输入参数
    3. 可观测性：完整的日志记录
    4. 错误处理：优雅降级，返回友好错误信息
    """

    @abstractmethod
    def _get_schema(self) -> Type[BaseModel]:
        """返回 Pydantic Schema"""
        pass

    @abstractmethod
    async def _execute(self, **kwargs) -> str:
        """异步执行入口"""
        pass

    def _run_impl(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        """同步执行入口（LangChain 要求）"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._execute(**kwargs))

    async def _arun(self, **kwargs) -> str:
        """异步执行入口"""
        return await self._execute(**kwargs)


class CourseScheduleTool(BaseBusinessTool):
    """
    课表查询工具

    功能：查询指定周次的课程安排
    数据来源：模拟数据库 / 实际项目中对接教务系统API
    """

    name: str = "get_course_schedule"
    description: str = """查询学生课表信息。当用户询问课程安排、上课时间、上课地点时使用此工具。

    参数：
    - week: 周次，1-20之间的整数，默认为当前周
    - day_of_week: 星期几，1-7（周一到周日），不填则返回整周课表
    """

    args_schema: Type[BaseModel] = ScheduleInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mock_db = self._init_mock_data()

    def _init_mock_data(self) -> Dict:
        """初始化模拟数据"""
        return {
            1: {  # 第1周
                "courses": [
                    {"name": "高等数学A", "teacher": "张教授", "location": "教学楼A-301",
                     "time": "周一 08:00-09:40", "weeks": "1-16"},
                    {"name": "大学英语(视听说)", "teacher": "李老师", "location": "外语楼205",
                     "time": "周一 10:00-11:40", "weeks": "1-16"},
                    {"name": "计算机基础", "teacher": "王老师", "location": "实验楼C-102",
                     "time": "周三 14:00-15:40", "weeks": "1-16"},
                    {"name": "软件工程", "teacher": "陈教授", "location": "教学楼A-401",
                     "time": "周四 08:00-09:40", "weeks": "1-16"},
                    {"name": "体育", "teacher": "赵老师", "location": "体育馆",
                     "time": "周五 14:00-15:40", "weeks": "1-16"},
                ]
            }
        }

    async def _execute(self, week: Optional[int] = None, day_of_week: Optional[int] = None) -> str:
        """
        执行课表查询

        设计考量：
        1. 默认返回整周课表，避免多次调用
        2. 支持按星期筛选，适应"明天有什么课"等场景
        3. 返回格式化文本，适合LLM理解和输出
        """
        week = week or 8  # 默认第8周

        logger.info(f"查询课表: week={week}, day={day_of_week}")

        if week not in self._mock_db:
            # 模拟其他周的数据（实际项目中应查数据库）
            schedule = self._generate_schedule(week)
        else:
            schedule = self._mock_db[week]

        courses = schedule["courses"]

        # 按星期筛选
        if day_of_week:
            day_map = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
            courses = [c for c in courses if day_map.get(day_of_week) in c["time"]]

        if not courses:
            return f"第{week}周暂无课程安排~ 🏫"

        # 格式化输出
        result = f"📚 **第{week}周课表**\n\n"
        for course in courses:
            result += f"• **{course['name']}**\n"
            result += f"  ⏰ {course['time']}\n"
            result += f"  📍 {course['location']}\n"
            result += f"  👨‍🏫 {course['teacher']}\n\n"

        return result.strip()

    def _generate_schedule(self, week: int) -> Dict:
        """生成其他周的课表（模拟）"""
        base = self._mock_db[1].copy()
        return {"courses": base["courses"]}


class GradeQueryTool(BaseBusinessTool):
    """
    成绩查询工具

    功能：查询指定学期的成绩信息
    数据来源：模拟数据库 / 实际项目中对接教务系统API
    """

    name: str = "get_grade_info"
    description: str = """查询学生成绩信息。当用户询问成绩、绩点、GPA时使用此工具。

    参数：
    - semester: 学期，格式为'YYYY-YYYY-X'，如'2024-2025-1'
    """

    args_schema: Type[BaseModel] = GradeInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mock_grades = {
            "2024-2025-1": {
                "gpa": 3.75,
                "total_credits": 24,
                "courses": [
                    {"name": "高等数学A", "credit": 4, "grade": 92, "point": 4.0},
                    {"name": "大学英语", "credit": 3, "grade": 85, "point": 3.7},
                    {"name": "计算机基础", "credit": 3, "grade": 88, "point": 3.7},
                    {"name": "软件工程", "credit": 4, "grade": 90, "point": 4.0},
                    {"name": "体育", "credit": 2, "grade": 95, "point": 4.0},
                    {"name": "思想政治", "credit": 2, "grade": 82, "point": 3.3},
                ]
            }
        }

    async def _execute(self, semester: str) -> str:
        """
        执行成绩查询

        设计考量：
        1. 返回完整学期报告，包含GPA、绩点分布
        2. 按学分加权计算GPA（实际项目中学籍系统已计算好）
        3. 格式化输出，包含等级分布统计
        """
        logger.info(f"查询成绩: semester={semester}")

        if semester not in self._mock_grades:
            return f"未找到 {semester} 学期的成绩数据~ 📊"

        data = self._mock_grades[semester]

        result = f"📊 **{semester} 学期成绩报告**\n\n"
        result += f"🎯 **GPA: {data['gpa']}**\n"
        result += f"📚 **总学分: {data['total_credits']}**\n\n"

        # 等级分布
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for course in data["courses"]:
            if course["grade"] >= 90:
                distribution["A"] += 1
            elif course["grade"] >= 80:
                distribution["B"] += 1
            elif course["grade"] >= 70:
                distribution["C"] += 1
            elif course["grade"] >= 60:
                distribution["D"] += 1
            else:
                distribution["F"] += 1

        result += "📈 **等级分布**: "
        result += " ".join([f"{k}({v})" for k, v in distribution.items() if v > 0])
        result += "\n\n"

        result += "📋 **课程明细**:\n"
        for course in data["courses"]:
            grade_icon = "🌟" if course["grade"] >= 90 else "✅" if course["grade"] >= 80 else "⚠️"
            result += f"{grade_icon} {course['name']}: {course['grade']}分 ({course['credit']}学分)\n"

        return result.strip()


class ReminderTool(BaseBusinessTool):
    """
    提醒设置工具

    功能：设置学习提醒、考试提醒等
    数据来源：写入数据库，定时任务扫描触发
    """

    name: str = "set_reminder"
    description: str = """设置提醒事项。当用户说"提醒我..."、"提醒我复习"、"考试前提醒我"时使用此工具。

    参数：
    - content: 提醒内容，如"复习高数"、"参加期末考试"
    - remind_time: 提醒时间，ISO格式，如'2024-05-20T09:00:00'
    - reminder_type: 提醒类型，study/exam/event
    """

    args_schema: Type[BaseModel] = ReminderInput

    async def _execute(
        self,
        content: str,
        remind_time: str,
        reminder_type: str = "study"
    ) -> str:
        """
        执行提醒设置

        设计考量：
        1. 验证提醒时间不能是过去时间
        2. 计算提前提醒时间（如考试提前1天）
        3. 返回确认信息，包含闹钟设置建议
        """
        logger.info(f"设置提醒: content={content}, time={remind_time}")

        try:
            remind_dt = datetime.fromisoformat(remind_time.replace("Z", "+08:00"))
        except ValueError:
            return "提醒时间格式不正确，请使用ISO格式~ ⏰"

        if remind_dt < datetime.now():
            return "提醒时间不能是过去时间哦~ ⏰"

        # 计算提前提醒
        advance_time = ""
        if reminder_type == "exam":
            advance = remind_dt - timedelta(days=1)
            advance_time = f"（建议同时设置{advance.strftime('%m-%d %H:%M')}的提前提醒）"
        elif reminder_type == "study":
            advance = remind_dt - timedelta(hours=1)
            advance_time = f"（建议同时设置{advance.strftime('%H:%M')}的提前提醒）"

        result = f"✅ **提醒已设置**\n\n"
        result += f"📝 内容: {content}\n"
        result += f"⏰ 时间: {remind_dt.strftime('%Y-%m-%d %H:%M')}\n"
        result += f"🏷️ 类型: {reminder_type}\n"

        if advance_time:
            result += f"\n💡 {advance_time}"

        return result


class ClassroomSearchTool(BaseBusinessTool):
    """
    空教室搜索工具

    功能：搜索指定时间段可用的空教室
    数据来源：教室排课表 / 实际项目中对接教室管理系统API
    """

    name: str = "search_available_classroom"
    description: str = """搜索空闲教室。当用户询问"哪里有空的教室"、"自习去哪"时使用此工具。

    参数：
    - date: 日期，格式如'2024-03-15'
    - start_time: 开始时间，格式如'09:00'
    - end_time: 结束时间，格式如'11:00'
    - capacity: 所需人数（可选）
    """

    args_schema: Type[BaseModel] = SearchScheduleInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._classrooms = [
            {"building": "教学楼A", "room": "A-101", "capacity": 50},
            {"building": "教学楼A", "room": "A-201", "capacity": 80},
            {"building": "教学楼A", "room": "A-301", "capacity": 120},
            {"building": "实验楼B", "room": "B-101", "capacity": 40},
            {"building": "图书馆", "room": "五楼研讨室1", "capacity": 20},
            {"building": "图书馆", "room": "五楼研讨室2", "capacity": 15},
        ]

    async def _execute(
        self,
        date: str,
        start_time: str,
        end_time: str,
        capacity: Optional[int] = None
    ) -> str:
        """
        执行空教室搜索

        设计考量：
        1. 按容量过滤，满足小组讨论或自习需求
        2. 考虑教室热门程度，推荐安静/热闹环境
        3. 返回多个选项供用户选择
        """
        logger.info(f"搜索空教室: date={date}, time={start_time}-{end_time}")

        # 模拟查询：随机标记一些教室被占用
        import random
        random.seed(hash(date + start_time))  # 同一时间段结果稳定

        available = []
        for room in self._classrooms:
            if capacity and room["capacity"] < capacity:
                continue
            # 模拟：70%概率空闲
            if random.random() < 0.7:
                available.append(room)

        if not available:
            return f"抱歉，{date} {start_time}-{end_time} 没有找到符合条件的空教室~ 🏫\n\n建议尝试其他时间段或减少人数要求"

        result = f"🏫 **空教室搜索结果**\n"
        result += f"📅 {date} {start_time}-{end_time}\n"
        if capacity:
            result += f"👥 至少需要{capacity}个座位\n\n"
        else:
            result += "\n"

        for i, room in enumerate(available[:5], 1):  # 最多返回5个
            environment = "📚 安静适合自习" if "图书馆" in room["building"] else "🏢 普通教室"
            result += f"{i}. **{room['building']} {room['room']}**\n"
            result += f"   座位: {room['capacity']}人 | {environment}\n\n"

        return result.strip()


class ConflictCheckTool(BaseBusinessTool):
    """
    日程冲突检测工具

    功能：检测新日程是否与现有课程/活动冲突
    数据来源：用户日程表 / 课程表
    """

    name: str = "check_schedule_conflict"
    description: str = """检测日程冲突。当用户添加新日程时，先检查是否与现有课程冲突时使用此工具。

    参数：
    - start_time: 开始时间，ISO格式
    - end_time: 结束时间，ISO格式
    """

    args_schema: Type[BaseModel] = ConflictCheckInput

    async def _execute(self, start_time: str, end_time: str) -> str:
        """
        执行冲突检测

        设计考量：
        1. 与课程表比对，检测时间重叠
        2. 考虑课程节次的时间映射（8:00-9:40对应第1-2节）
        3. 提供冲突解决方案（换时间/换教室）
        """
        logger.info(f"检测冲突: {start_time} - {end_time}")

        # 解析时间
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+08:00"))
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+08:00"))
        except ValueError:
            return "时间格式不正确，请使用ISO格式~ ⏰"

        # 模拟冲突检测（实际项目中查数据库）
        has_conflict = self._check_mock_conflict(start_dt, end_dt)

        if not has_conflict:
            return "✅ 没有检测到冲突，日程可以正常添加~ 📅"

        # 返回冲突信息和建议
        result = "⚠️ **检测到冲突**\n\n"
        result += f"您计划的时间段与以下课程重叠：\n"
        result += "• 高等数学A (周一 08:00-09:40) @ 教学楼A-301\n\n"
        result += "💡 **建议**：\n"
        result += "1. 调整时间到 10:00 之后\n"
        result += "2. 使用 图书馆研讨室 进行小组活动\n"

        return result

    def _check_mock_conflict(self, start: datetime, end: datetime) -> bool:
        """模拟冲突检测"""
        # 周一 08:00-09:40 有课
        if start.weekday() == 0 and start.hour < 10:
            if start.hour < 9 or (start.hour == 9 and start.minute < 40):
                return True
        return False


# ========== 工具注册表 ==========

def get_business_tools() -> List[BaseTool]:
    """
    获取所有业务工具

    返回工具列表，供 LangChain ToolNode 使用
    """
    return [
        CourseScheduleTool(),
        GradeQueryTool(),
        ReminderTool(),
        ClassroomSearchTool(),
        ConflictCheckTool(),
    ]


def get_tools_dict() -> Dict[str, BaseTool]:
    """
    获取工具字典（name -> tool）

    便于根据名称查找工具
    """
    tools = get_business_tools()
    return {tool.name: tool for tool in tools}
