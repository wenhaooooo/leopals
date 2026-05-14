"""
工具模块初始化

包含：
- function_tools.py: 基于 LangChain Function Calling 的业务工具封装
- tools.py: 原有工具定义（兼容）

导出：
- business_tools: 所有业务工具实例列表
- tools_dict: 工具名称到实例的映射
"""

from .function_tools import (
    get_business_tools,
    get_tools_dict,
    CourseScheduleTool,
    GradeQueryTool,
    ReminderTool,
    ClassroomSearchTool,
    ConflictCheckTool,
)

business_tools = get_business_tools()
tools_dict = get_tools_dict()

__all__ = [
    "business_tools",
    "tools_dict",
    "CourseScheduleTool",
    "GradeQueryTool",
    "ReminderTool",
    "ClassroomSearchTool",
    "ConflictCheckTool",
]
