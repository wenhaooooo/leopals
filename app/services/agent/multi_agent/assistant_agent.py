import logging
from typing import Dict, Any, Optional, List
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
    temperature=0.3,
    max_tokens=1000,
)


class AssistantAgent:
    """
    助手智能体：处理需要多步骤操作的复杂任务
    
    核心能力：
    - 任务分解
    - 多步骤规划
    - 智能体协作协调
    """
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理复杂任务请求
        
        Args:
            query: 用户查询内容
            context: 上下文信息
        
        Returns:
            {"result": "处理结果", "confidence": 置信度}
        """
        logger.info(f"助手智能体处理请求: {query}")
        
        try:
            # 1. 任务分解
            steps = await self._decompose_task(query)
            logger.debug(f"任务分解结果: {steps}")
            
            if not steps:
                return {"result": "抱歉，我无法理解您的请求。", "confidence": 0.5}
            
            # 2. 执行每个步骤
            results = []
            for step in steps:
                result = await self._execute_step(step)
                results.append(result)
            
            # 3. 汇总结果
            final_result = await self._summarize_results(results, query)
            
            return {"result": final_result, "confidence": 0.85}
        
        except Exception as e:
            logger.error(f"助手智能体处理失败: {str(e)}")
            return {"result": f"抱歉，处理失败：{str(e)}", "confidence": 0.0}
    
    async def _decompose_task(self, query: str) -> List[Dict[str, str]]:
        """将复杂任务分解为多个步骤"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            你是一个任务规划专家。请将用户的请求分解为多个步骤：
            
            用户请求：{query}
            
            可用的智能体：
            - QAAgent: 回答事实性问题
            - ScheduleAgent: 查询课表、成绩、设置提醒
            - EmotionalAgent: 情感支持
            - KnowledgeAgent: 文档知识查询
            
            请输出JSON格式：
            {{
                "steps": [
                    {{"step": "步骤描述", "agent": "需要调用的智能体名称", "query": "传递给智能体的查询"}},
                    ...
                ]
            }}
            
            每个步骤应该是一个简单的子任务，可以由单个智能体完成。
            """),
            ("user", "")
        ])
        
        chain = prompt | llm | JsonOutputParser()
        
        try:
            result = await chain.ainvoke({"query": query})
            return result.get("steps", [])
        except Exception as e:
            logger.error(f"任务分解失败: {str(e)}")
            return []
    
    async def _execute_step(self, step: Dict[str, str]) -> Dict[str, Any]:
        """执行单个步骤（调用对应智能体）"""
        agent_name = step.get("agent", "QAAgent")
        query = step.get("query", "")
        step_desc = step.get("step", "")
        
        logger.info(f"执行步骤: {step_desc} -> {agent_name}")
        
        try:
            result = await message_bus.send(agent_name, {"query": query})
            return {
                "step": step_desc,
                "agent": agent_name,
                "result": result.get("result", "")
            }
        except Exception as e:
            logger.error(f"步骤执行失败: {str(e)}")
            return {"step": step_desc, "agent": agent_name, "result": f"执行失败: {str(e)}"}
    
    async def _summarize_results(self, results: List[Dict[str, Any]], original_query: str) -> str:
        """汇总所有步骤的结果"""
        # 如果只有一个步骤，直接返回结果
        if len(results) == 1:
            return results[0]["result"]
        
        # 多步骤结果汇总
        results_str = "\n\n".join([
            f"【步骤{idx+1}: {r['step']}】\n{r['result']}" 
            for idx, r in enumerate(results)
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            你是一个任务总结专家。请将以下多个步骤的执行结果汇总成一个连贯的回复：
            
            用户原始请求：{query}
            
            执行步骤及结果：
            {results}
            
            请用自然、友好的语言总结整个任务的执行过程和最终结果，使用适当的表情符号。
            """),
            ("user", "")
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({
            "query": original_query,
            "results": results_str
        })
        
        return response.content