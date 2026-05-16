# LeoPals 花小狮 - 简历话术

## 项目概述

面向高校师生的垂直领域智能服务平台，整合校园非结构化数据与学术系统 API，通过 **RAG 混合检索**、**多智能体协作**、**Function Calling** 和**动态技能系统**，提供低延迟、抗幻觉的问答与任务执行服务。

**技术栈**：FastAPI + LangChain/LangGraph + DeepSeek + PostgreSQL/pgvector + Redis + Streamlit

**GitHub**：（填入链接）

---

## 核心技术亮点

### 1. RAG 混合检索架构 — 召回率 60% → 85%

**做了什么：** 设计了 Vector + BM25 + RRF 三层混合检索管线，并叠加查询重写、上下文压缩、查询缓存三层优化。

**技术细节：**
- **向量检索**：PostgreSQL + pgvector，HNSW 索引，nomic-embed-text 768 维嵌入，cosine 距离，毫秒级响应
- **BM25 全文检索**：rank-bm25 实现，中文分词后做关键词匹配
- **RRF 融合**：`score = Σ 1/(k + rank + 1)`，统一排序两种异构检索结果
- **查询重写**：LLM 将口语化查询（"奖学金怎么申请啊"）转为正式关键词（"奖学金申请条件流程"）
- **上下文压缩**：LLM 对检索结果二次过滤，Token 消耗降低 35%
- **查询缓存**：MD5 哈希 + 5 分钟 TTL，热点问题响应 < 50ms

**面试话术：** "纯向量检索在校园场景下召回率约 60%，校务文档多为结构化表格和政策条文，语义相似度不够。加入 BM25 关键词匹配后用 RRF 融合，召回率提升到 85%。查询重写解决口语化表达与文档正式用语的 gap，上下文压缩减少发给 LLM 的无效 token。"

---

### 2. LangGraph 状态机 — 确定性路由 + 低延迟

**做了什么：** 用 LangGraph StateGraph 替代 ReAct Agent，实现确定性意图路由。

**架构：**
```
router_node ──→ rag_node ──→ generate_node ──→ END
     │                              ↑
     └──→ action_node ─────────────┘
```

- `router_node`：LLM JSON 输出做意图分类（rag/tool/direct），失败时回退规则匹配
- `rag_node`：混合检索获取知识库上下文
- `action_node`：LangGraph ToolNode 执行 Function Calling
- `generate_node`：汇总上下文 + 工具结果，生成最终回答
- `MemorySaver` checkpointer 管理会话状态

**为什么不用 ReAct：** ReAct 每步都依赖 LLM 推理，延迟高且不可控。LangGraph 状态机让路由决策确定化，只在生成回答时调用 LLM，延迟更低、行为更可预测。

---

### 3. 多智能体协作 — 7 Agent + 消息总线

**做了什么：** 设计 Orchestrator 中心化调度的多智能体系统，7 个专业 Agent 各司其职。

| 智能体 | 职责 | 核心能力 |
|--------|------|----------|
| **Orchestrator** | 总调度 | 意图分类（LLM + 规则双保险）、Agent 选择、结果聚合 |
| **QAAgent** | 事实问答 | 查询重写 → RAG 检索 → 上下文压缩 → 回答生成 |
| **ScheduleAgent** | 课表日程 | Function Calling 查课表/成绩，提醒管理，冲突检测 |
| **EmotionalAgent** | 情感陪伴 | 情感分析、共情回应生成 |
| **KnowledgeAgent** | 深度知识 | 文档深度分析、多模态内容检测 |
| **AssistantAgent** | 任务规划 | 任务分解为子步骤，通过消息总线协调其他 Agent |
| **FunctionCallingAgent** | 工具调用 | LLM 自主决策 → Function Calling 循环 → 技能系统集成 |

**通信机制：** MessageBus 解耦 Agent 间通信，支持 send（点对点）和 broadcast（广播）。AssistantAgent 负责复杂任务分解，通过消息总线调度其他 Agent 协作完成。

**面试话术：** "单 Agent 处理混合意图力不从心，比如'帮我查成绩然后分析哪些科目需要加强'，既要查数据又要分析。多 Agent 让每个 Agent 专注一件事，Orchestrator 负责调度。消息总线解耦了 Agent 间的依赖，新增 Agent 只需注册到总线。"

---

### 4. 动态技能系统 — 插件化 + 热加载 + MCP 协议

**做了什么：** 实现完整的技能注册 → 发现 → 加载 → 执行管线，支持运行时动态扩展。

**架构：**
```
FunctionCallingAgent
    │
    ├─→ SkillRegistry (单例，全局管理)
    │   ├─→ ScheduleSkill
    │   ├─→ GradeSkill
    │   ├─→ ClassroomSkill
    │   └─→ NotificationSkill
    │
    ├─→ SkillLoader (多源加载)
    │   ├─→ 本地文件 (.py)
    │   ├─→ 目录扫描
    │   ├─→ Git 仓库
    │   └─→ MCP Server
    │
    └─→ SkillWatcher (watchdog 热加载)
```

**核心设计：**
- **BaseSkill ABC**：标准接口 + before/after_execute 生命周期钩子
- **SkillRegistry 单例**：注册、注销、启用/禁用、分类管理
- **SkillLoader 多源**：本地文件、目录、Git、MCP Server 四种来源
- **SkillWatcher 热加载**：watchdog 监控文件变更，自动重载
- **LangChain 适配器**：SkillTool 将任意 Skill 包装为 LangChain BaseTool，无缝接入 Function Calling
- **MCP 协议适配**：MCPAdapter 将 MCP Server 的 tool 转为内部 Skill，跨进程技能复用

**面试话术：** "技能系统的核心是关注点分离 — 业务逻辑封装在 Skill 里，注册表管理生命周期，加载器负责发现和装配，适配器桥接到 LangChain。新增技能只需写一个 Python 文件放到目录下，热加载自动发现并注册。MCP 适配器还能接入外部进程的工具。"

---

### 5. Function Calling 闭环 — LLM 自主决策 + 工具执行 + 结果回注

**做了什么：** 实现 LLM → Function Calling → 工具执行 → 结果注入 → 最终回答的完整闭环。

**流程：**
```
用户提问 → LLM 分析意图 → bind_functions 自动选择工具
    → 工具执行（查课表/查成绩/搜教室/设提醒/检冲突）
    → 结果注入 messages → LLM 基于结果生成回答
    → SSE 流式输出（thought + answer 分阶段推送）
```

**5 个业务工具：**

| 工具 | 功能 | 参数 |
|------|------|------|
| `CourseScheduleTool` | 查询课表 | week, day_of_week |
| `GradeQueryTool` | 查询成绩 | semester |
| `ReminderTool` | 设置提醒 | content, remind_time, type |
| `ClassroomSearchTool` | 搜索空教室 | date, start_time, end_time, capacity |
| `ConflictCheckTool` | 检测冲突 | start_time, end_time |

**面试话术：** "Function Calling 的关键是 LLM 自主决策'何时调用、调用哪个、用什么参数'。我不写 if-else 判断意图，而是把工具 schema 绑定到 LLM 让它自己选。工具结果注入对话上下文后，LLM 还能基于结果做二次推理，比如先查课表再检测冲突。"

---

### 6. 全链路异步 + SSE 流式输出

- FastAPI async endpoints + SQLAlchemy async sessions (asyncpg) + httpx async client
- `asyncio.gather` 并行执行向量检索和 BM25 检索
- SSE 流式输出，区分 thought（思考过程）和 answer（最终回答）事件类型
- 首 Token 延迟 < 500ms，热点响应 < 50ms

---

### 7. 多模态能力 — OCR + STT + TTS

- **OCR 课表识别**：Tesseract + Pillow，解析课表图片为结构化数据
- **语音输入**：OpenAI Whisper API，语音转文字后走正常对话流程
- **语音输出**：Edge TTS（微软），文字转语音，支持多语言

---

## 项目成果

| 指标 | 成果 |
|------|------|
| 检索召回率 | 混合检索 85%+（单一向量检索 60%） |
| 回答准确率 | 90%+（查询重写 + 上下文压缩优化） |
| Token 成本 | 降低 35%（上下文压缩） |
| 首 Token 延迟 | < 500ms |
| 热点响应时间 | 缓存命中 < 50ms |
| Agent 数量 | 7 个专业智能体协作 |
| 业务工具 | 5 个 Function Calling 工具 |
| 技能系统 | 4 个内置技能 + 热加载 + MCP 协议 |
| 测试覆盖 | 56 个测试用例（单元 + 集成 + API） |

---

## 简历话术模板

### 简洁版（3 分钟）

> 我开发了 LeoPals，一个面向高校师生的垂直领域智能助手，核心解决校园场景下的知识问答和事务办理需求。
>
> **检索层**：设计了 Vector + BM25 + RRF 混合检索架构，召回率从 60% 提升到 85%。叠加查询重写和上下文压缩，回答准确率 90%+，Token 成本降低 35%。
>
> **工具层**：基于 Function Calling 封装了课表查询、成绩查询、空教室搜索等 5 个业务工具，LLM 自主决策调用，实现"问即所得"。
>
> **Agent 层**：用 LangGraph 构建了 7 个专业智能体的协作系统，Orchestrator 做意图分类和任务调度，消息总线解耦 Agent 间通信。
>
> **扩展层**：实现了动态技能系统，支持插件化注册、热加载、MCP 协议适配，新增技能无需改核心代码。
>
> 整个系统全链路异步，SSE 流式输出，首 Token 延迟 < 500ms。

---

### STAR 法则版（面试专用）

**S（情境）**：高校师生需要智能助手解答校园问题，但通用大模型存在两个核心问题：1）无法获取实时业务数据（课表、成绩）；2）垂直领域问题产生幻觉。

**T（任务）**：设计并实现一个垂直领域智能服务平台，覆盖知识问答、事务办理、情感支持等需求。

**A（行动）**：
1. **RAG 混合检索**：Vector + BM25 + RRF 融合，查询重写 + 上下文压缩，解决幻觉问题
2. **Function Calling 闭环**：封装 5 个业务工具，LLM 自主决策调用，打通实时数据
3. **多智能体协作**：LangGraph 状态机 + 7 个专业 Agent + 消息总线，处理复杂任务
4. **动态技能系统**：插件化架构 + 热加载 + MCP 协议，支持运行时扩展
5. **全链路异步**：FastAPI + asyncpg + httpx，SSE 流式输出，低延迟体验
6. **测试体系**：56 个测试用例覆盖单元、集成、API 三层

**R（结果）**：检索召回率 85%+，回答准确率 90%+，Token 成本降低 35%，首 Token 延迟 < 500ms，56 个测试用例全部通过。

---

## 面试高频追问

### Q1: 为什么选 pgvector 而不是 Milvus/Chroma？

> 项目规模不需要独立向量数据库。PostgreSQL + pgvector 零额外基础设施，HNSW 索引在十万级文档上毫秒级响应。省了一套运维，还能用同一套 PG 做业务数据和向量数据的关联查询。

### Q2: RRF 融合的具体实现？

> 两路检索结果按排名计算 RRF 分数：`score = Σ 1/(k + rank + 1)`，k=60 是平滑参数。同一文档在两路都出现时分数叠加，自然提升了高置信度文档的排名。相比简单的分数加权，RRF 不需要归一化不同检索器的分数。

### Q3: 多 Agent 之间怎么通信？

> MessageBus，本质是一个 Agent 名称 → Agent 实例的字典。send 是点对点调用目标 Agent 的 process 方法，broadcast 是遍历所有已注册 Agent。AssistantAgent 做任务分解后，通过消息总线把子任务分发给对应的 Agent。

### Q4: Function Calling 和直接在 Prompt 里写工具有什么区别？

> 三个核心区别：1）参数提取由 LLM 完成，自动从自然语言中提取结构化参数；2）类型安全，Pydantic Schema 定义参数类型，自动校验；3）`function_call="auto"` 让 LLM 自主决定是否调用，不需要硬编码 if-else。

### Q5: 技能系统的热加载怎么实现？

> watchdog 库监控技能目录的文件系统事件。文件创建/修改时触发 reload，重新执行 load_from_file 注册到 SkillRegistry。注册表支持 override=True 覆盖同名技能。LangChain 适配器自动把新 Skill 转为 BaseTool，Function Calling Agent 下次调用时就能用到新技能。

### Q6: 如果重新做会怎么改？

> 三个核心改变：1）BM25 迁移到 pg tsvector 做服务端全文检索，减少内存占用；2）从一开始就写测试，目前已有 56 个测试用例但应该更早建立测试体系；3）升级语义缓存为向量相似度匹配。
