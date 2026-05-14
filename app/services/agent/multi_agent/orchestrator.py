import logging
from typing import Tuple, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.core.config import settings
from app.services.agent.multi_agent.message_bus import message_bus

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_api_base,
    model_name=settings.llm_model_name,
    temperature=0.1,
    max_tokens=500,
)


class IntentClassifier:
    """
    意图分类器：将用户请求分类到不同的智能体处理
    """
    
    INTENTS = {
        "qa": ["是什么", "什么是", "怎么", "如何", "哪里", "查询", "了解", "有哪些", "多少"],
        "schedule": ["课表", "课程", "上课", "时间", "提醒", "日程", "安排", "成绩", "GPA"],
        "emotional": ["难过", "开心", "郁闷", "烦恼", "倾诉", "聊天", "心情", "孤独", "压力"],
        "knowledge": ["政策", "文件", "通知", "规定", "文档", "资料", "公告", "指南"],
        "assistant": ["帮我", "我想", "计划", "安排", "任务", "规划", "如何安排"]
    }
    
    async def classify(self, query: str) -> str:
        """
        对用户查询进行意图分类
        
        Returns:
            智能体名称，如 "qa", "schedule", "emotional", "knowledge", "assistant"
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            你是一个意图分类专家。请将用户的问题分类到以下类别：
            
            - qa: 事实性问答（如"什么是人工智能？"、"图书馆在哪里？"）
            - schedule: 日程课表相关（如"我明天有什么课？"、"查询成绩"）
            - emotional: 情感需求（如"我今天心情不太好"、"我感到很孤独"）
            - knowledge: 文档知识查询（如"奖学金政策是什么？"、"校历在哪里看？"）
            - assistant: 任务协助（如"帮我安排明天的学习计划"、"帮我规划复习计划"）
            
            请输出JSON格式：{"intent": "类别名称"}
            """),
            ("user", query)
        ])
        
        chain = prompt | llm | JsonOutputParser()
        
        try:
            result = await chain.ainvoke({})
            return result.get("intent", "qa")
        except Exception as e:
            logger.error(f"意图分类失败: {str(e)}")
            return self._simple_classify(query)
    
    def _simple_classify(self, query: str) -> str:
        """简单规则匹配作为备选方案"""
        for intent, keywords in self.INTENTS.items():
            for keyword in keywords:
                if keyword in query:
                    return intent
        return "qa"


class AgentSelector:
    """
    智能体选择器：根据意图选择最合适的智能体
    """
    
    AGENT_MAPPING = {
        "qa": "QAAgent",
        "schedule": "ScheduleAgent", 
        "emotional": "EmotionalAgent",
        "knowledge": "KnowledgeAgent",
        "assistant": "AssistantAgent"
    }
    
    def select(self, intent: str) -> str:
        """
        根据意图选择智能体
        
        Returns:
            智能体名称
        """
        return self.AGENT_MAPPING.get(intent, "QAAgent")


class ResultAggregator:
    """
    结果汇总器：汇总多个智能体的结果，生成最终回复
    """
    
    async def aggregate(self, results: list, original_query: str) -> str:
        """
        汇总多个智能体的结果
        
        Args:
            results: [{"agent": "智能体名称", "result": "结果内容", "confidence": 0.9}]
            original_query: 用户原始问题
        
        Returns:
            汇总后的最终回复
        """
        if len(results) == 1:
            return results[0]["result"]
        
        results_str = "\n\n".join([
            f"【{r['agent']}】{r['result']}" for r in results
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            你是一个结果汇总专家。请将以下多个智能体的回答汇总成一个连贯的回复：
            
            原始问题：{query}
            
            智能体结果列表：
            {results}
            
            请给出一个综合、连贯的回答，保持活泼可爱的语气，使用适当的表情符号。
            """),
            ("user", "")
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({
            "query": original_query,
            "results": results_str
        })
        
        return response.content


class Orchestrator:
    """
    调度智能体：多智能体系统的核心，负责意图识别、任务分发和结果汇总
    """
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.agent_selector = AgentSelector()
        self.result_aggregator = ResultAggregator()
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理用户请求的主入口
        
        Args:
            query: 用户查询内容
            context: 上下文信息（如用户ID、历史记录等）
        
        Returns:
            {"result": "最终回复", "confidence": 置信度, "agent": "调用的智能体"}
        """
        logger.info(f"调度智能体接收到请求: {query}")
        
        # 1. 意图分类
        intent = await self.intent_classifier.classify(query)
        logger.info(f"意图分类结果: {intent}")
        
        # 2. 选择智能体
        agent_name = self.agent_selector.select(intent)
        logger.info(f"选择智能体: {agent_name}")
        
        # 3. 调用智能体
        try:
            result = await message_bus.send(agent_name, {
                "query": query,
                "context": context
            })
            
            return {
                "result": result.get("result", "处理失败"),
                "confidence": result.get("confidence", 0.0),
                "agent": agent_name
            }
        except ValueError as e:
            # 如果目标智能体未注册，使用问答智能体作为备选
            logger.warning(f"智能体未注册，使用QAAgent作为备选: {str(e)}")
            result = await message_bus.send("QAAgent", {
                "query": query,
                "context": context
            })
            
            return {
                "result": result.get("result", "处理失败"),
                "confidence": result.get("confidence", 0.0),
                "agent": "QAAgent (fallback)"
            }