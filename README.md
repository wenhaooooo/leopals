# 🦁 LeoPals - 花小狮校园智慧助手

LeoPals 是一个面向高校师生的垂直领域智能服务平台，整合校园非结构化数据与校务系统 API，通过 **RAG**、**多智能体协作架构** 和 **Function Calling** 提供低延迟、防幻觉的问答与办事服务。

## ✨ 核心特性

### 🤖 智能问答
- **RAG 混合检索**：结合向量检索与 BM25 全文检索，使用 RRF 算法融合结果
- **语义缓存层**：减少重复查询响应时间，缓存有效期5分钟，最大缓存100条
- **Query Rewriting**：将模糊口语化查询转换为更精确的检索关键词
- **Contextual Compression**：根据用户查询过滤和压缩检索文档，去除冗余信息
- **文档版本控制**：支持文档更新和回溯，追踪历史版本
- **LangGraph 状态机**：基于状态机的多步决策 Agent，支持工具调用和知识检索
- **SSE 流式输出**：实时流式响应，区分思考过程与最终回答

### 🔧 Function Calling 业务闭环
- **课表查询**：获取指定周次的课程安排
- **成绩查询**：查询学期成绩和 GPA
- **空教室搜索**：查找可用的自习教室
- **智能提醒**：设置学习、考试提醒
- **冲突检测**：检测日程与课程冲突

### 🧠 多智能体协作架构
```
用户请求 → Orchestrator → [QAAgent/ScheduleAgent/EmotionalAgent/KnowledgeAgent/AssistantAgent/FunctionCallingAgent] → 结果汇总
```

| 智能体 | 职责 | 核心能力 |
|--------|------|---------|
| **Orchestrator** | 意图识别、任务分发 | 意图分类、智能体选择、多智能体协作 |
| **QAAgent** | 事实性问答 | RAG检索、精准回答 |
| **ScheduleAgent** | 课表查询、日程管理 | Function Calling、课表API、提醒设置 |
| **EmotionalAgent** | 情感陪伴、心理支持 | 情感分析、共情回应 |
| **KnowledgeAgent** | 深度文档理解 | 政策解读、多模态分析 |
| **AssistantAgent** | 复杂任务规划 | 任务分解、步骤执行、智能体协调 |
| **FunctionCallingAgent** | 业务系统闭环 | 动态技能系统、工具调用、参数提取自动化 |

### 🛠️ 动态技能注册系统
```
Agent (智能体)
    │
    ├─→ Skill Registry (技能注册表)
    │   ├─→ ScheduleSkill (课表技能)
    │   ├─→ GradeSkill (成绩技能)
    │   ├─→ ClassroomSkill (教室技能)
    │   └─→ NotificationSkill (通知技能)
    │
    └─→ Skill Loader (动态加载)
        ├─→ 本地技能 (.py 文件)
        ├─→ 远程技能 (Git 仓库)
        └─→ MCP Server
```

**核心特性**：
- **插件化架构**：技能以插件形式管理，支持热加载
- **类型安全**：基于 Pydantic 的参数校验
- **异步执行**：支持高并发技能调用
- **多源加载**：支持本地文件、Git 仓库、MCP Server
- **生命周期管理**：支持技能的启用、禁用、注销
- **上下文传递**：支持用户 ID、会话 ID 等上下文信息

**已实现技能**：
| 技能名称 | 功能 | 类别 |
|---------|------|------|
| `schedule_query` | 查询课表 | schedule |
| `grade_query` | 查询成绩 | academic |
| `classroom_search` | 搜索空教室 | facility |
| `notification_set` | 设置提醒 | notification |

### 📅 智能日程管理
- 课程表同步（从教务系统自动拉取）
- 智能提醒（作业截止、考试安排）
- 冲突检测（课表与活动冲突）

### 🖼️ 多模态支持
- 图片上传识别（课程表图片 → 结构化数据）
- 语音输入输出（STT + TTS）

### 🌳 AI树洞
- 匿名倾诉心事，AI智能回复安慰
- 自动匹配相似经历的同学互相鼓励
- 完全匿名，隐私保护

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
├── main.py                 # FastAPI 入口（含多智能体初始化）
├── core/                   # 核心配置
│   ├── config.py           # 环境变量配置
│   └── database.py         # 数据库连接
├── api/                    # 路由层
│   ├── routes.py           # 聊天接口
│   ├── multimodal_routes.py # 多模态接口
│   ├── schedule_routes.py  # 日程管理接口
│   └── treehole_routes.py  # 树洞接口
├── models/                 # SQLAlchemy Models
│   ├── document.py         # 文档模型（含版本控制）
│   ├── schedule.py         # 日程模型
│   └── treehole.py         # 树洞模型
├── services/
│   ├── rag/                # RAG 检索模块
│   │   ├── document_loader.py
│   │   └── pgvector_retriever.py
│   ├── agent/              # Agent 模块
│   │   ├── state.py        # 状态定义
│   │   ├── tools/          # Function Calling 工具集
│   │   │   ├── __init__.py
│   │   │   └── function_tools.py
│   │   ├── graph.py        # 状态机
│   │   └── multi_agent/    # 多智能体体系
│   │       ├── __init__.py
│   │       ├── message_bus.py     # 消息总线
│   │       ├── orchestrator.py    # 调度智能体
│   │       ├── qa_agent.py        # 问答智能体
│   │       ├── schedule_agent.py  # 日程智能体
│   │       ├── emotional_agent.py # 情感智能体
│   │       ├── knowledge_agent.py # 知识智能体
│   │       ├── assistant_agent.py # 助手智能体
│   │       └── function_calling_agent.py # Function Calling 智能体
│   ├── multimodal/         # 多模态服务
│   │   ├── image_service.py
│   │   └── audio_service.py
│   ├── schedule/           # 日程服务
│   │   └── schedule_service.py
│   └── treehole/           # 树洞服务
│       └── treehole_service.py
└── app_frontend.py         # Streamlit 主前端
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

# 启动后端（自动初始化多智能体系统）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 启动前端模块

```bash
# 主应用（问答）
streamlit run app_frontend.py       # http://localhost:8501

# 知识库管理后台
streamlit run admin_frontend.py     # http://localhost:8502

# 日程管理
streamlit run schedule_frontend.py  # http://localhost:8503

# AI树洞
streamlit run treehole_frontend.py  # http://localhost:8506
```

### 4. 访问服务

| 服务 | 地址 |
|------|------|
| API 文档 | <http://localhost:8000/docs> |
| 主应用 | <http://localhost:8501> |
| 知识库管理 | <http://localhost:8502> |
| 日程管理 | <http://localhost:8503> |
| AI树洞 | <http://localhost:8506> |
| 健康检查 | <http://localhost:8000/health> |

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

### 日程管理

```bash
# 同步课程表
curl -X POST http://localhost:8000/schedule/courses/sync \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "20240001",
    "courses": [...]
  }'

# 获取今日日程
curl http://localhost:8000/schedule/today?student_id=20240001
```

### AI树洞

```bash
# 发布帖子
curl -X POST http://localhost:8000/treehole/post \
  -H "Content-Type: application/json" \
  -d '{
    "content": "今天心情不太好..."
  }'

# 获取帖子列表
curl http://localhost:8000/treehole/posts
```

## 📝 预设问题示例

- 📅 "校历哪里看？"
- 📊 "帮我查一下上学期绩点"
- 📚 "考研加分政策是什么？"
- 💬 "你好呀！"
- 🌳 "我最近压力很大..."
- 🤝 "帮我安排明天的学习计划"
- 🏫 "明天上午有什么课？"
- 📍 "哪里有空教室可以自习？"
- ⏰ "提醒我明天早上9点复习高数"
- ⚠️ "周五下午3点开会会和我的课冲突吗？"

## 📋 配置说明

主要环境变量：

| 变量                | 说明               | 默认值                           |
| ----------------- | ---------------- | ----------------------------- |
| OPENAI_API_KEY    | DeepSeek API Key | -                             |
| OPENAI_API_BASE   | API 基础地址         | https://api.deepseek.com/v1   |
| POSTGRES_HOST     | 数据库地址            | localhost                     |
| POSTGRES_PORT     | 数据库端口            | 5432                          |
| POSTGRES_DB       | 数据库名称            | leopals                       |
| POSTGRES_USER     | 数据库用户名          | admin                         |
| POSTGRES_PASSWORD | 数据库密码            | password                      |
| OLLAMA_HOST       | Ollama 地址        | http://localhost:11434        |
| REDIS_HOST        | Redis 地址         | localhost                     |

## 📦 功能模块列表

| 模块 | 文件 | 说明 |
|------|------|------|
| 主应用 | `app_frontend.py` | 智能问答对话界面 |
| 知识库管理 | `admin_frontend.py` | 文档上传与管理 |
| 日程管理 | `schedule_frontend.py` | 课程表、提醒、冲突检测 |
| AI树洞 | `treehole_frontend.py` | 匿名倾诉、AI安慰 |

## 📚 文档目录

```
docs/
├── schema.sql              # 数据库建表脚本
├── PROJECT_HIGHLIGHTS.md   # 项目亮点文档
├── TECHNICAL_DESIGN.md     # 技术方案设计文档
├── MULTI_AGENT_DESIGN.md   # 多智能体架构设计方案
├── RESUME_CONTENT.md       # 简历话术文档（AI风控平台）
├── INTERVIEW_TALK.md       # 面试话术文档（花小狮项目）
└── resume.md               # 简历话术文档（完整版）
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
