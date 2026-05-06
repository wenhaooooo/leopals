# 🦁 LeoPals - 校园智慧助手

LeoPals 是一个面向高校师生的垂直领域智能服务平台，整合校园非结构化数据与校务系统 API，通过 RAG 和 Agent 技术提供低延迟、防幻觉的问答与办事服务。

## ✨ 核心特性

- **RAG 混合检索**：结合向量检索与 BM25 全文检索，使用 RRF 算法融合结果
- **LangGraph 状态机**：基于状态机的多步决策 Agent，支持工具调用和知识检索
- **SSE 流式输出**：实时流式响应，区分思考过程与最终回答
- **Mock 业务工具**：提供课表查询、成绩查询等模拟工具

## 🛠️ 技术栈

| 分类      | 技术                            |
| ------- | ----------------------------- |
| Web 框架  | FastAPI + Pydantic v2         |
| AI 编排   | LangChain + LangGraph         |
| 大模型 API | DeepSeek / GPT-4o (OpenAI 兼容) |
| 向量数据库   | PostgreSQL + pgvector         |
| 嵌入模型    | nomic-embed-text (Ollama)     |
| 状态存储    | Redis                         |
| 前端      | Streamlit                     |

## 📁 项目结构

```
app/
├── __init__.py
├── main.py                 # FastAPI 入口
├── core/                   # 核心配置
│   ├── config.py           # 环境变量配置
│   └── database.py         # 数据库连接
├── api/                    # 路由层
│   └── routes.py           # 聊天接口
├── models/                 # Pydantic Schemas
│   └── document.py         # 文档模型
├── services/
│   ├── rag/                # RAG 检索模块
│   │   ├── document_loader.py
│   │   └── pgvector_retriever.py
│   └── agent/              # LangGraph Agent
│       ├── state.py        # 状态定义
│       ├── tools.py        # 工具集
│       └── graph.py        # 状态机
└── app_frontend.py         # Streamlit 前端
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- Docker & Docker Compose
- DeepSeek API Key

### 2. 启动服务

```bash
# 克隆项目
git clone <repository-url>
cd leopals

# 创建环境变量文件
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key

# 启动 Docker 服务（PostgreSQL, Ollama, Redis）
docker-compose up -d

# 拉取嵌入模型（首次运行）
docker exec -it leopals-ollama ollama pull nomic-embed-text

# 安装依赖
pip install -r requirements.txt

# 启动后端
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端（新开终端）
streamlit run app_frontend.py
```

### 3. 访问服务

- **API 文档**：<http://localhost:8000/docs>
- **前端界面**：<http://localhost:8501>
- **健康检查**：<http://localhost:8000/health>

## 🔧 API 接口

### 流式对话

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "帮我查一下第8周的课表",
    "user_info": {"student_id": "20240001"},
    "session_id": "test_session"
  }'
```

## 📝 预设问题示例

- 📅 "校历哪里看？"
- 📊 "帮我查一下上学期绩点"
- 📚 "考研加分政策是什么？"
- 💬 "你好呀！"

## 📋 配置说明

主要环境变量：

| 变量                | 说明               | 默认值                           |
| ----------------- | ---------------- | ----------------------------- |
| OPENAI\_API\_KEY  | DeepSeek API Key | -                             |
| OPENAI\_API\_BASE | API 基础地址         | <https://api.deepseek.com/v1> |
| POSTGRES\_HOST    | 数据库地址            | localhost                     |
| OLLAMA\_HOST      | Ollama 地址        | <http://localhost:11434>      |

