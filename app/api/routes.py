import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage

from app.services.agent.graph import graph
from app.services.agent.state import AgentState
from app.services.rag.pgvector_retriever import pgvector_retriever

router = APIRouter(prefix="/chat", tags=["Chat"])
kb_router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


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


@kb_router.post("/upload", summary="上传文档到知识库")
async def upload_document(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    allowed_types = [".pdf", ".md", ".markdown"]
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"仅支持文件类型: {', '.join(allowed_types)}")

    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    file_path = upload_dir / file.filename
    
    counter = 1
    while file_path.exists():
        stem = Path(file.filename).stem
        suffix = Path(file.filename).suffix
        file_path = upload_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        doc_source_id = await pgvector_retriever.add_documents(str(file_path), description)
        return JSONResponse(
            status_code=201,
            content={
                "message": "文档上传成功",
                "document_id": doc_source_id,
                "file_name": file.filename
            }
        )
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@kb_router.get("/documents", summary="获取文档列表")
async def list_documents(skip: int = 0, limit: int = 100):
    sources = await pgvector_retriever.list_document_sources(skip, limit)
    return {"documents": sources}


@kb_router.get("/documents/{source_id}", summary="获取文档详情")
async def get_document(source_id: int):
    source = await pgvector_retriever.get_document_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="文档不存在")
    return source


@kb_router.delete("/documents/{source_id}", summary="删除文档")
async def delete_document(source_id: int):
    success = await pgvector_retriever.delete_document_source(source_id)
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"message": "文档删除成功"}


@kb_router.get("/stats", summary="知识库统计")
async def get_knowledge_stats():
    stats = await pgvector_retriever.get_knowledge_stats()
    return stats
