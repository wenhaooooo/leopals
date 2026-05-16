# LeoPals 花小狮 - 面试话术

> 面向 Agent 实习生岗位的面试准备文档。每个技术点都包含：做了什么、为什么这么做、怎么做的、面试怎么答。

---

## 一、项目概述（30 秒版）

> LeoPals 是面向高校师生的垂直领域智能助手。核心做了三件事：1）用 RAG 混合检索解决校园文档的精准问答；2）用 Function Calling 打通 LLM 和业务系统（课表、成绩等实时数据）；3）用多智能体协作处理复杂任务（如"查成绩然后分析哪些科目需要加强"）。
>
> 技术栈是 FastAPI + LangGraph + DeepSeek + PostgreSQL/pgvector，全链路异步，SSE 流式输出。

---

## 二、核心技术点详解

### 2.1 RAG 混合检索 — 召回率 60% → 85%

**做了什么：** Vector + BM25 + RRF 三层混合检索，叠加查询重写、上下文压缩、查询缓存。

**为什么这么设计：**
- 纯向量检索在校园场景下召回率约 60%，因为校务文档多为结构化表格和政策条文，语义相似度匹配不够
- 用户口语化查询（"奖学金怎么申请啊"）和文档正式表述差距大
- 检索到的文档有很多冗余信息，直接喂给 LLM 浪费 token 且容易产生幻觉

**怎么做的：**

| 层次 | 方案 | 解决什么问题 |
|------|------|-------------|
| 向量检索 | pgvector + HNSW 索引 + nomic-embed-text 768 维 | 语义匹配，处理同义词/近义词 |
| BM25 检索 | rank-bm25，中文分词后匹配 | 精确关键词匹配（学号、课程编号等） |
| RRF 融合 | `score = Σ 1/(k + rank + 1)`, k=60 | 统一排序两路结果，不需要归一化分数 |
| 查询重写 | LLM 将口语转正式关键词 | 弥补用户表述与文档用语的 gap |
| 上下文压缩 | LLM 二次过滤，只保留相关内容 | 减少 token 消耗约 35%，降低幻觉 |
| 查询缓存 | MD5 哈希 + 5 分钟 TTL + 100 条上限 | 热点问题响应 < 50ms |

**面试话术：**

> "纯向量检索召回率约 60%，校园文档多为政策条文和结构化表格，语义相似度不够。加入 BM25 关键词匹配后用 RRF 融合，召回率提升到 85%。RRF 的好处是不需要归一化不同检索器的分数 — 同一文档在两路都出现时分数自然叠加。查询重写解决口语化表达和文档正式用语的 gap，上下文压缩减少发给 LLM 的无效 token。"

**追问：RRF 具体怎么实现的？**

> "两路检索各取 top_k*2 个结果，每个文档按排名计算 RRF 分数：1/(k + rank + 1)，k=60 是平滑参数。同一文档在两路都出现时分数叠加，按总分排序取 top_k。相比简单的分数加权，RRF 不需要归一化不同检索器的分数，天然适配异构检索结果的融合。"

**追问：BM25 每次查询都全量加载？**

> "是的，这是目前的一个性能瓶颈。每次查询从数据库加载全部 chunk 到内存做分词和匹配。文档量大了会有问题，后续计划迁移到 PostgreSQL 的 tsvector + GIN 索引做服务端全文检索，或者用 MeiliSearch 这类专业全文检索引擎。"

---

### 2.2 LangGraph 状态机 — 确定性路由

**做了什么：** 用 LangGraph StateGraph 替代 ReAct Agent，实现确定性意图路由。

**架构：**
```
router_node ──→ rag_node ──→ generate_node ──→ END
     │                              ↑
     └──→ action_node ─────────────┘
```

**为什么不用 ReAct：**
- ReAct 每步都依赖 LLM 推理决定下一步，延迟高且行为不可预测
- LangGraph 状态机只在 router 节点用一次 LLM 做意图分类，后续按预定义路径执行
- 路由逻辑确定化，整体延迟更低、行为更可预测

**各节点职责：**

| 节点 | 做什么 | 调用 LLM？ |
|------|--------|-----------|
| router_node | LLM JSON 输出分类意图 (rag/tool/direct) | 是，1 次 |
| rag_node | 混合检索获取知识库上下文 | 否（检索不经过 LLM） |
| action_node | LangGraph ToolNode 执行工具 | 否 |
| generate_node | 汇总上下文 + 工具结果，生成回答 | 是，1 次 |

**面试话术：**

> "ReAct 模式下每一步都要 LLM 决策，延迟高且不可控。我用 LangGraph 状态机把路由确定化 — router 做一次意图分类就决定了走 RAG 还是工具调用，后续节点按预定义路径执行。一次请求最多调用 2 次 LLM（路由 + 生成），而 ReAct 可能调用 4-5 次。"

**追问：意图分类失败怎么办？**

> "LLM 分类失败时（JSON 解析错误、网络超时等）回退到规则匹配 — 预定义关键词列表，遍历匹配。这是双保险机制，保证系统可用性。"

---

### 2.3 多智能体协作 — 7 Agent + 消息总线

**做了什么：** Orchestrator 中心化调度的多智能体系统。

**7 个 Agent：**

| Agent | 职责 | 核心能力 |
|-------|------|----------|
| Orchestrator | 总调度 | 意图分类（LLM + 规则双保险）、Agent 选择、结果聚合 |
| QAAgent | 事实问答 | 查询重写 → RAG 检索 → 上下文压缩 → 回答生成 |
| ScheduleAgent | 课表日程 | Function Calling 查课表/成绩，提醒管理，冲突检测 |
| EmotionalAgent | 情感陪伴 | 情感分析、共情回应生成 |
| KnowledgeAgent | 深度知识 | 文档深度分析、多模态内容检测 |
| AssistantAgent | 任务规划 | 任务分解为子步骤，通过消息总线协调其他 Agent |
| FunctionCallingAgent | 工具调用 | LLM 自主决策 → Function Calling 循环 → 技能系统集成 |

**通信机制：** MessageBus，Agent 名称 → Agent 实例的字典。send 点对点，broadcast 广播。

**面试话术：**

> "单 Agent 处理混合意图力不从心，比如'帮我查成绩然后分析哪些科目需要加强'，既要查数据又要分析。多 Agent 让每个 Agent 专注一件事，Orchestrator 负责调度。消息总线解耦了 Agent 间的依赖，新增 Agent 只需注册到总线。AssistantAgent 做任务分解后，通过消息总线把子任务分发给对应的 Agent。"

**追问：Agent 间怎么通信的？**

> "MessageBus 本质是一个字典，key 是 Agent 名称，value 是 Agent 实例。send 方法根据名称找到目标 Agent 调用其 process 方法，broadcast 遍历所有已注册 Agent。目前是同步调用，没有消息队列和异步回调 — 这是后续可以优化的点，比如加消息 ID 和 trace_id 做链路追踪。"

---

### 2.4 Function Calling 闭环

**做了什么：** LLM → Function Calling → 工具执行 → 结果回注 → 最终回答。

**流程：**
```
用户提问 → LLM bind_functions 自动选择工具
    → 工具执行（查课表/查成绩/搜教室/设提醒/检冲突）
    → 结果注入 messages → LLM 继续推理
    → SSE 流式输出（thought + answer 分阶段推送）
```

**5 个工具：**

| 工具 | 功能 | 参数 |
|------|------|------|
| CourseScheduleTool | 查课表 | week, day_of_week |
| GradeQueryTool | 查成绩 | semester |
| ReminderTool | 设提醒 | content, remind_time, type |
| ClassroomSearchTool | 搜空教室 | date, start_time, end_time, capacity |
| ConflictCheckTool | 检冲突 | start_time, end_time |

**面试话术：**

> "Function Calling 的关键是 LLM 自主决策'何时调用、调用哪个、用什么参数'。我不写 if-else 判断意图，把工具 schema 绑定到 LLM 让它自己选。工具结果注入对话上下文后，LLM 还能基于结果做二次推理 — 比如先查课表再检测冲突。参数提取也是 LLM 完成的，用户说'第8周'自动提取为 week=8。"

**追问：和在 Prompt 里写工具有什么区别？**

> "三个核心区别：1）参数提取由 LLM 完成，自动从自然语言提取结构化参数，不需要手写解析逻辑；2）类型安全，Pydantic Schema 定义参数类型，自动校验；3）function_call='auto' 让 LLM 自主决定是否调用，不需要硬编码 if-else。而且这是 OpenAI 标准协议，LangChain/LangGraph 都支持，生态成熟。"

---

### 2.5 动态技能系统 — 插件化 + 热加载 + MCP

**做了什么：** 完整的技能注册 → 发现 → 加载 → 执行管线。

**架构：**
```
FunctionCallingAgent
    ├─→ SkillRegistry (单例，全局管理)
    ├─→ SkillLoader (本地/目录/Git/MCP 四种来源)
    ├─→ SkillWatcher (watchdog 热加载)
    └─→ LangChainAdapter (Skill → BaseTool)
```

**面试话术：**

> "技能系统的核心是关注点分离。业务逻辑封装在 Skill 里（继承 BaseSkill，实现 execute 方法），注册表管理生命周期（注册/注销/启用/禁用），加载器负责发现和装配。新增技能只需写一个 Python 文件放到 impls 目录下，watchdog 监控文件变更自动重载。MCP 适配器还能接入外部进程的工具，实现跨进程技能复用。"

**追问：热加载怎么实现的？**

> "用 watchdog 库监控技能目录的文件系统事件（create/modify）。文件变更时触发回调，重新执行 load_from_file：importlib 动态加载模块，提取 BaseSkill 子类实例，注册到 SkillRegistry（override=True 覆盖旧版本）。LangChain 适配器自动把新 Skill 转为 BaseTool，FunctionCallingAgent 下次调用时就能用到新技能。整个过程不需要重启服务。"

---

### 2.6 全链路异步 + SSE 流式输出

**做了什么：** 从 HTTP 接口到数据库到 LLM，全链路 async/await；前端 SSE 实时展示。

- FastAPI async endpoints + SQLAlchemy async sessions (asyncpg) + httpx async client
- `asyncio.gather` 并行执行向量检索和 BM25 检索
- SSE 区分 thought（思考过程）和 answer（最终回答）事件类型
- 首 Token 延迟 < 500ms

**面试话术：**

> "校园助手需要对话式体验，用户不想点按钮等半天。全链路异步让服务端能并发处理多个请求，SSE 让用户在 LLM 生成第一个 token 时就能看到结果。向量检索和 BM25 检索用 asyncio.gather 并行执行，不互相等待。"

---

### 2.7 多模态 — OCR + STT + TTS

- **OCR 课表识别**：Tesseract + Pillow，解析课表图片为结构化数据
- **语音输入**：OpenAI Whisper API，语音转文字后走正常对话流程
- **语音输出**：Edge TTS（微软），文字转语音

**面试话术：**

> "学生最常用的场景是拍课表和语音问问题。OCR 不只是文字提取，还要解析表格结构、匹配课程名和时间地点。语音输入输出让移动端体验更自然。"

---

## 三、项目成果

| 指标 | 数据 |
|------|------|
| 检索召回率 | 85%+（单一向量检索 60%） |
| 回答准确率 | 90%+ |
| Token 成本 | 降低 35%（上下文压缩） |
| 首 Token 延迟 | < 500ms |
| 热点响应 | 缓存命中 < 50ms |
| Agent 数量 | 7 个专业智能体 |
| 业务工具 | 5 个 Function Calling 工具 |
| 技能系统 | 4 个内置技能 + 热加载 + MCP |
| 测试覆盖 | 56 个测试用例（单元 + 集成 + API） |

---

## 四、面试高频追问

### Q1: 为什么选 DeepSeek 而不是 GPT-4o？

> "成本是 GPT-4o 的 1/30，而且 DeepSeek 兼容 OpenAI API 格式，换模型只需要改 config 里的 model_name 和 api_base。校园项目预算有限，DeepSeek 在中文场景下的表现完全够用。"

### Q2: 为什么选 pgvector 而不是 Milvus/Chroma？

> "项目规模不需要独立向量数据库。PostgreSQL + pgvector 零额外基础设施，HNSW 索引在十万级文档上毫秒级响应。还能用同一套 PG 做业务数据和向量数据的关联查询，省了一套运维。"

### Q3: 如果要继续优化，你会怎么做？

> "三个优先级最高的改进：
> 1. **BM25 迁移**：从内存全量加载迁移到 pg tsvector + GIN 索引，解决文档量增长后的性能瓶颈
> 2. **语义缓存升级**：从 MD5 精确匹配升级为向量相似度匹配，真正实现语义级缓存
> 3. **优化 Agent 通信**：引入异步消息队列和链路追踪机制，提升多 Agent 协作的可观测性和容错性"

### Q4: 项目最大的不足是什么？

> "目前已补了 56 个测试用例覆盖核心模块（RRF 算法、意图分类、技能注册、多 Agent 协作、Chat API），但 RAG 管线的端到端集成测试还没补完。另外 Agent 间的通信目前是简单的同步调用，生产环境需要加消息 ID、trace_id、超时控制和 dead-letter queue。"

### Q5: 语义缓存真的是'语义'的吗？

> "说实话不是。目前是 MD5 哈希精确匹配，'奖学金怎么申请'和'如何申请奖学金'语义相同但缓存不命中。叫'查询缓存'更准确。真正的语义缓存需要对 query 做 embedding，用向量相似度匹配历史查询，阈值 > 0.95 才命中。这是后续可以优化的方向。"

### Q6: 多 Agent 之间怎么通信的？有没有消息丢失的风险？

> "MessageBus 是简单的内存字典，send 就是直接调用目标 Agent 的 process 方法。没有消息队列、没有持久化、没有重试机制 — 消息丢失了就丢失了。这是目前的简化设计，生产环境需要加消息 ID、trace_id、超时控制和 dead-letter queue。"

### Q7: Function Calling 的工具执行失败怎么办？

> "工具执行失败时，把错误信息作为工具结果返回给 LLM（'工具执行失败: {error}'），LLM 会基于错误信息生成友好的用户回复。不会中断对话流程。但这不是完美的方案 — 比如数据库连接失败，应该直接返回错误而不是让 LLM 编一个回答。后续需要区分可重试错误和不可重试错误。"

### Q8: 文档版本控制实现了吗？

> "Model 层定义了 DocumentVersion 模型，但实际的版本追踪和回滚逻辑还没有完全实现。目前文档更新时会覆盖旧数据，没有自动创建版本记录。这是 TODO 项。"

---

## 五、STAR 法则版（面试专用）

**S（情境）**：高校师生需要智能助手，但通用大模型有两个核心问题：1）无法获取实时业务数据（课表、成绩）；2）垂直领域问题产生幻觉。用户查询口语化模糊，知识库更新频繁。

**T（任务）**：设计并实现一个垂直领域智能服务平台，覆盖知识问答、事务办理、情感支持。

**A（行动）**：
1. **RAG 混合检索**：Vector + BM25 + RRF，查询重写 + 上下文压缩，解决幻觉
2. **Function Calling 闭环**：5 个业务工具，LLM 自主决策调用，打通实时数据
3. **多智能体协作**：LangGraph 状态机 + 7 Agent + 消息总线，处理复杂任务
4. **动态技能系统**：插件化 + 热加载 + MCP，运行时扩展
5. **全链路异步**：FastAPI + asyncpg + httpx + SSE，低延迟体验
6. **测试体系**：56 个测试用例覆盖单元、集成、API 三层

**R（结果）**：召回率 85%+，准确率 90%+，Token 成本降低 35%，首 Token < 500ms，56 个测试用例全部通过。

---

## 六、技术选型决策表

| 决策 | 选型 | 备选 | 选型理由 |
|------|------|------|----------|
| LLM | DeepSeek-Chat | GPT-4o | 成本 1/30，OpenAI 兼容 API |
| 向量库 | pgvector | Milvus, Chroma | 零额外基础设施，HNSW 毫秒级 |
| 检索策略 | Vector + BM25 + RRF | 纯向量 | 召回率 60% → 85% |
| Agent 框架 | LangGraph | ReAct | 确定性路由，延迟更低 |
| 前端 | Streamlit | React/Vue | Python 全栈，快速原型 |
| 全文检索 | rank-bm25 (内存) | pg tsvector | 实现简单，后续可迁移 |
| 缓存 | MD5 哈希 | 向量相似度 | 实现简单，后续可升级 |
