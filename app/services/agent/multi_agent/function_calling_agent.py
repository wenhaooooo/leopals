"""
基于 Function Calling 的智能体

实现 "LLM 自主决策 -> 工具调用 -> 业务系统闭环" 架构：

1. LLM 通过 Function Calling 机制自主决定调用哪个工具
2. 工具执行实际业务逻辑（查数据库、调 API）
3. 工具结果注入对话上下文，LLM 生成最终回答
"""

import logging
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.utils.function_calling import convert_to_openai_function

from app.core.config import settings
from app.services.agent.tools.function_tools import get_business_tools

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_api_base,
    model_name=settings.llm_model_name,
    temperature=0.1,
    max_tokens=1000,
)


class FunctionCallingAgent:
    """
    基于 Function Calling 的业务智能体

    核心流程：
    1. 用户提问 -> LLM 分析意图
    2. LLM 决定是否调用工具（Function Calling）
    3. 工具执行 -> 结果返回给 LLM
    4. LLM 基于工具结果生成最终回答

    优势相比 Chain-of-Thought：
    - LLM 自主决定是否调用工具，不需要先用 if-else 判断
    - 参数提取由 LLM 完成，自动从用户输入中提取（如"第8周"提取为 week=8）
    - 工具调用结果自动注入上下文，不需要手动拼接
    """

    def __init__(self):
        self.tools = get_business_tools()
        # 绑定工具到 LLM（启用 Function Calling）
        self.llm_with_tools = llm.bind_functions(
            functions=[convert_to_openai_function(tool) for tool in self.tools],
            function_call="auto"  # LLM 自主决定是否调用函数
        )
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是花小狮 (LeoPals)，一只活泼俏皮的小狮子助手！🐾

你的职责是帮助华中师范大学师生解决校园相关问题。

【能力范围】
- 查询课表和成绩
- 设置学习提醒
- 搜索空教室
- 检测日程冲突
- 回答校园知识问题

【工具调用原则】
1. 当用户询问具体数据时（如"我明天有什么课"），优先使用工具获取实时数据
2. 当用户询问知识性问题时（如"考研政策是什么"），使用 RAG 检索
3. 当用户只是闲聊时，直接回答

【回答风格】
- 活泼可爱，使用适当的表情符号
- 回答简洁明了，避免冗长
- 如果工具返回"未找到"或"无结果"，诚实告知用户

【重要规则】
- 严禁编造信息，不知道就说不知道
- 工具调用是为了获取真实数据，不是为了炫耀技术
"""

    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理用户请求

        Args:
            query: 用户查询
            context: 上下文信息（当前未使用，预留）

        Returns:
            {"result": "回答内容", "confidence": 置信度, "tool_calls": [{"name": "...", "args": {...}}]}
        """
        logger.info(f"Function Calling Agent 处理请求: {query}")

        tool_calls_made = []
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=query)
        ]

        try:
            # 第一轮：LLM 分析是否需要调用工具
            response = await self.llm_with_tools.ainvoke(messages)
            messages.append(response)

            # 如果 LLM 决定调用工具，执行工具调用循环
            while response.additional_kwargs.get("function_call"):
                function_call = response.additional_kwargs["function_call"]
                tool_name = function_call["name"]
                tool_args = function_call["arguments"]

                logger.info(f"LLM 调用工具: {tool_name}, 参数: {tool_args}")

                # 查找工具实例
                tool = self._find_tool(tool_name)
                if not tool:
                    error_msg = f"工具 {tool_name} 不存在"
                    logger.error(error_msg)
                    messages.append(AIMessage(content=error_msg))
                    break

                # 执行工具调用
                try:
                    import json
                    args_dict = json.loads(tool_args) if isinstance(tool_args, str) else tool_args
                    tool_result = await tool._arun(**args_dict)
                except Exception as e:
                    logger.error(f"工具执行失败: {str(e)}")
                    tool_result = f"工具执行失败: {str(e)}"

                tool_calls_made.append({
                    "name": tool_name,
                    "args": args_dict,
                    "result": tool_result
                })

                # 将工具结果作为消息添加到上下文
                messages.append(
                    AIMessage(
                        content="",
                        additional_kwargs={
                            "function_call": {
                                "name": tool_name,
                                "arguments": tool_args
                            }
                        }
                    )
                )
                messages.append(
                    HumanMessage(content=f"工具 {tool_name} 返回结果:\n{tool_result}\n\n请基于这个结果回答用户问题。")
                )

                # 继续下一轮对话，让 LLM 基于工具结果生成回答
                response = await self.llm_with_tools.ainvoke(messages)
                messages.append(response)

            # 最终回答
            final_answer = response.content if response.content else "抱歉，我暂时无法回答这个问题~ 🦁"

            return {
                "result": final_answer,
                "confidence": 0.9 if tool_calls_made else 0.6,
                "tool_calls": tool_calls_made
            }

        except Exception as e:
            logger.error(f"Function Calling Agent 处理失败: {str(e)}")
            return {
                "result": f"处理失败：{str(e)}",
                "confidence": 0.0,
                "tool_calls": tool_calls_made
            }

    def _find_tool(self, tool_name: str):
        """根据名称查找工具实例"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None


# 全局实例
function_calling_agent = FunctionCallingAgent()
