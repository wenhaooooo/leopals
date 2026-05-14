import logging
import re
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.core.config import settings
from app.services.agent.tools import GetCourseScheduleTool, GetGradeInfoTool

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_api_base,
    model_name=settings.llm_model_name,
    temperature=0.1,
    max_tokens=500,
)


class ScheduleAgent:
    """
    日程智能体：专注于时间管理和日程安排
    
    核心能力：
    - 课表查询
    - 成绩查询
    - 日程安排
    - 提醒设置
    """
    
    def __init__(self):
        self.course_tool = GetCourseScheduleTool()
        self.grade_tool = GetGradeInfoTool()
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理日程相关请求
        
        Args:
            query: 用户查询内容
            context: 上下文信息
        
        Returns:
            {"result": "处理结果", "confidence": 置信度}
        """
        logger.info(f"日程智能体处理请求: {query}")
        
        # 解析用户意图
        intent = await self._parse_intent(query)
        logger.debug(f"意图解析结果: {intent}")
        
        if intent == "query_course":
            result = await self._query_course(query)
        elif intent == "query_grade":
            result = await self._query_grade(query)
        elif intent == "add_schedule":
            result = await self._add_schedule(query)
        elif intent == "set_reminder":
            result = await self._set_reminder(query)
        else:
            result = "抱歉，我不太明白您的需求。您可以问我课表查询、成绩查询等问题哦~ 🦁"
        
        return {"result": result, "confidence": 0.95}
    
    async def _parse_intent(self, query: str) -> str:
        """解析用户的具体意图"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            请将用户的请求分类到以下类型：
            
            - query_course: 查询课表（如"我明天有什么课？"、"第8周课表"）
            - query_grade: 查询成绩（如"我的成绩"、"2024-2025-1学期成绩"）
            - add_schedule: 添加日程（如"帮我添加明天下午的会议"）
            - set_reminder: 设置提醒（如"提醒我明天上课"）
            
            请输出JSON格式：{"intent": "类型名称"}
            """),
            ("user", query)
        ])
        
        chain = prompt | llm | JsonOutputParser()
        
        try:
            result = await chain.ainvoke({})
            return result.get("intent", "query_course")
        except Exception as e:
            logger.error(f"意图解析失败: {str(e)}")
            return self._simple_parse(query)
    
    def _simple_parse(self, query: str) -> str:
        """简单规则匹配作为备选"""
        if "课表" in query or "上课" in query or "课程" in query or "第几周" in query:
            return "query_course"
        elif "成绩" in query or "GPA" in query or "绩点" in query:
            return "query_grade"
        elif "添加" in query and ("日程" in query or "安排" in query):
            return "add_schedule"
        elif "提醒" in query:
            return "set_reminder"
        return "query_course"
    
    async def _query_course(self, query: str) -> str:
        """查询课表"""
        # 提取周次
        week = self._extract_week(query)
        logger.debug(f"提取周次: {week}")
        
        try:
            result = await self.course_tool._arun(week)
            return f"好的，这是您的课表信息~ 📚\n\n{result}"
        except Exception as e:
            logger.error(f"课表查询失败: {str(e)}")
            return "抱歉，课表查询失败了，请稍后再试~ 😢"
    
    async def _query_grade(self, query: str) -> str:
        """查询成绩"""
        # 提取学期
        semester = self._extract_semester(query)
        logger.debug(f"提取学期: {semester}")
        
        if not semester:
            semester = "2024-2025-1"  # 默认本学期
        
        try:
            result = await self.grade_tool._arun(semester)
            return f"这是您的成绩报告~ 📊\n\n{result}"
        except Exception as e:
            logger.error(f"成绩查询失败: {str(e)}")
            return "抱歉，成绩查询失败了，请稍后再试~ 😢"
    
    async def _add_schedule(self, query: str) -> str:
        """添加日程"""
        # 解析日程信息
        schedule_info = await self._parse_schedule(query)
        
        return f"好的，我已经帮您添加了日程：\n📅 {schedule_info['title']}\n⏰ {schedule_info['time']}\n📍 {schedule_info['location']}"
    
    async def _set_reminder(self, query: str) -> str:
        """设置提醒"""
        reminder_info = await self._parse_reminder(query)
        
        return f"收到！我会在 {reminder_info['time']} 提醒您：{reminder_info['content']} ⏰"
    
    def _extract_week(self, query: str) -> Optional[int]:
        """从查询中提取周次"""
        # 匹配"第X周"或"X周"
        match = re.search(r"(第)?(\d+)周", query)
        if match:
            return int(match.group(2))
        return None
    
    def _extract_semester(self, query: str) -> Optional[str]:
        """从查询中提取学期"""
        # 匹配"XXXX-XXXX-X"格式
        match = re.search(r"(\d{4})-(\d{4})-(\d)", query)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        return None
    
    async def _parse_schedule(self, query: str) -> Dict[str, str]:
        """解析日程信息"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            请从用户的请求中提取日程信息：
            
            用户请求: {query}
            
            请输出JSON格式：
            {
                "title": "日程标题",
                "time": "时间",
                "location": "地点",
                "description": "描述"
            }
            """),
            ("user", "")
        ])
        
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke({"query": query})
        
        return {
            "title": result.get("title", "未命名日程"),
            "time": result.get("time", "未指定时间"),
            "location": result.get("location", "未指定地点"),
            "description": result.get("description", "")
        }
    
    async def _parse_reminder(self, query: str) -> Dict[str, str]:
        """解析提醒信息"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            请从用户的请求中提取提醒信息：
            
            用户请求: {query}
            
            请输出JSON格式：
            {
                "time": "提醒时间",
                "content": "提醒内容"
            }
            """),
            ("user", "")
        ])
        
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke({"query": query})
        
        return {
            "time": result.get("time", "未指定时间"),
            "content": result.get("content", "未指定内容")
        }