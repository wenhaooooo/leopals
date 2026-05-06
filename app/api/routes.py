import json
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage

from app.services.agent.graph import graph
from app.services.agent.state import AgentState

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    query: str = Field(..., description="用户问题")
    user_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="用户身份信息，如学号、姓名等"
    )
    session_id: str = Field(
        default="default",
        description="会话 ID，用于保持对话上下文"
    )


async def chat_stream_generator(request: ChatRequest):
    try:
        initial_state = AgentState(
            messages=[HumanMessage(content=request.query)],
            user_info=request.user_info or {},
            retrieved_context="",
            next_step=""
        )

        config = {"configurable": {"thread_id": request.session_id}}

        yield f"event: thought\ndata: {json.dumps({'message': '花小狮正在思考... 🤔'})}\n\n"

        async for event in graph.astream(initial_state, config=config):
            node_name = list(event.keys())[0] if event else None
            node_output = event.get(node_name, {}) if node_name else {}

            if node_name == "router":
                next_step = node_output.get("next_step", "")
                yield f"event: thought\ndata: {json.dumps({'message': f'路由决策: {next_step}'})}\n\n"

            elif node_name == "rag_node":
                yield f"event: on_retriever_end\ndata: {json.dumps({'message': '知识库检索完成 ✅'})}\n\n"

            elif node_name == "action_node":
                yield f"event: on_tool_end\ndata: {json.dumps({'message': '工具调用完成 ✅'})}\n\n"

            elif node_name == "generate_node":
                messages = node_output.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    if hasattr(last_message, 'content'):
                        content = last_message.content
                        for i in range(0, len(content), 10):
                            chunk = content[i:i+10]
                            yield f"event: on_chat_model_stream\ndata: {json.dumps({'content': chunk})}\n\n"

        yield "event: end\ndata: {}\n\n"

    except Exception as e:
        import traceback
        error_msg = f"对话过程中发生错误: {str(e)}\n{traceback.format_exc()}"
        yield f"event: error\ndata: {json.dumps({'content': error_msg})}\n\n"


@router.post("/stream", summary="流式对话接口")
async def chat_stream(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")

    return StreamingResponse(
        chat_stream_generator(request),
        media_type="text/event-stream"
    )