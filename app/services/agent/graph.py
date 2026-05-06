import asyncio
import logging
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings
from app.services.agent.state import AgentState
from app.services.agent.tools import tools
from app.services.rag.pgvector_retriever import pgvector_retriever

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_api_base,
    model_name=settings.llm_model_name,
    temperature=settings.llm_temperature,
    max_tokens=settings.llm_max_tokens,
)

SYSTEM_PROMPT = """
你是花小狮 (LeoPals)，一只活泼俏皮的小狮子助手！🐾
你的任务是帮助高校师生解决校园相关问题。

**性格特点**：
- 说话活泼可爱，带点小俏皮
- 喜欢用表情符号增加亲切感
- 回答简洁明了，避免冗长

**核心规则**：
1. 如果问题需要查阅校务文档（如考研政策、校历等），请调用 RAG 检索
2. 如果问题需要实时数据（如课表、成绩），请调用业务工具
3. 如果只是闲聊，可以直接回答
4. **最重要**：如果没有找到答案，请诚实说"不知道"，严禁编造信息！

**可用工具**：
- get_course_schedule(week): 查询课表
- get_grade_info(semester): 查询成绩

请根据用户问题判断需要执行的操作类型：
- "rag": 需要查阅校务文档
- "tool": 需要调用业务工具
- "direct": 直接回答即可

请输出 JSON 格式：{"action": "rag"|"tool"|"direct"}
"""


async def router_node(state: AgentState) -> AgentState:
    """
    路由节点：判断用户意图，决定下一步行动
    """
    last_message = state["messages"][-1]
    user_query = last_message.content

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", user_query)
    ])

    chain = prompt | llm | JsonOutputParser()
    
    try:
        result = await chain.ainvoke({})
        action = result.get("action", "direct")
    except Exception as e:
        action = "direct"

    return {
        **state,
        "next_step": action
    }


async def rag_node(state: AgentState) -> AgentState:
    """
    RAG 检索节点：从知识库获取相关文档
    """
    last_message = state["messages"][-1]
    user_query = last_message.content

    try:
        context = await pgvector_retriever.get_relevant_documents(user_query)
        context_count = context.count("---") + 1 if context else 0
        logger.info(f"RAG 检索完成，找到 {context_count} 条相关文档")
    except Exception as e:
        context = ""
        logger.error(f"RAG 检索失败: {str(e)}")

    return {
        **state,
        "retrieved_context": context,
        "next_step": "generate"
    }


async def action_node(state: AgentState) -> AgentState:
    """
    工具调用节点：使用 ToolNode 处理实际的工具执行
    """
    tool_node = ToolNode(tools)
    result = await tool_node.ainvoke(state)
    return result


async def generate_node(state: AgentState) -> AgentState:
    """
    生成节点：汇总所有信息，生成最终回复
    """
    last_message = state["messages"][-1]
    user_query = last_message.content
    context = state.get("retrieved_context", "")

    tool_results = []
    for msg in state["messages"]:
        if isinstance(msg, ToolMessage):
            tool_results.append(msg.content)

    system_prompt = """
你是花小狮 (LeoPals)，一只活泼俏皮的小狮子助手！🐾

请根据以下信息回答用户问题：

【知识库信息】
{context}

【工具调用结果】
{tool_results}

**规则**：
1. 如果知识库或工具结果中有相关信息，请基于这些信息回答
2. 如果没有找到答案，请诚实说"不知道"，严禁编造！
3. 保持回答活泼可爱，使用适当的表情符号
4. 避免冗长，保持简洁
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_query)
    ])

    chain = prompt | llm
    response = await chain.ainvoke({
        "context": context or "无相关知识",
        "tool_results": "\n\n".join(tool_results) or "无工具调用结果"
    })

    return {
        **state,
        "messages": [AIMessage(content=response.content)],
        "next_step": "end"
    }


def route_decision(state: AgentState) -> Literal["rag_node", "action_node", "generate_node", END]:
    """
    条件路由：根据 next_step 决定下一个节点
    """
    next_step = state.get("next_step", "direct")
    
    if next_step == "rag":
        return "rag_node"
    elif next_step == "tool":
        return "action_node"
    elif next_step == "generate":
        return "generate_node"
    elif next_step == "direct":
        return "generate_node"
    else:
        return END


def build_graph() -> StateGraph:
    """
    构建完整的 LangGraph 状态机
    流程：router -> [rag_node | action_node] -> generate_node -> END
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("rag_node", rag_node)
    workflow.add_node("action_node", action_node)
    workflow.add_node("generate_node", generate_node)

    workflow.set_entry_point("router")

    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "rag_node": "rag_node",
            "action_node": "action_node",
            "generate_node": "generate_node",
            END: END
        }
    )

    workflow.add_edge("rag_node", "generate_node")
    workflow.add_edge("action_node", "generate_node")
    workflow.add_edge("generate_node", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


graph = build_graph()