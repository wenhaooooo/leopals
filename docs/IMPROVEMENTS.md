# LeoPals 待优化点

> 面向 Agent 实习生简历项目，识别可改进方向并给出优化建议。这些点在面试中被追问时，能展示你的技术思考深度。

---

## 1. ~~零测试覆盖 — 最大的工程短板~~ (已解决)

**现状：** 已建立完整的测试体系，56 个测试用例全部通过。

**已实现的测试覆盖：**
- **单元测试**：RRF 融合算法（8）、IntentClassifier 意图分类（9）、SkillRegistry 技能注册表（16）
- **集成测试**：多 Agent 系统（10）、技能系统生命周期（7）
- **API 测试**：`/chat/stream` 端点（6）

**测试结构：**
```
tests/
├── conftest.py                      # 共享 fixtures
├── unit/
│   ├── test_rrf_fusion.py          # RRF 融合算法
│   ├── test_intent_classifier.py   # 意图分类器
│   └── test_skill_registry.py      # 技能注册表
├── integration/
│   ├── test_multi_agent.py         # MessageBus + Orchestrator
│   └── test_skill_system.py        # 技能系统端到端
└── api/
    └── test_chat_endpoint.py       # Chat API 接口测试
```

**后续优化方向：**
- 补 RAG 管线集成测试（上传文档 → 检索 → 验证召回）
- 加 CI 流水线（GitHub Actions），push 时自动跑测试
- 提升覆盖率到 80%+

---

## 2. BM25 全量加载 — 性能瓶颈

**现状：** `_bm25_search` 每次查询都从数据库加载全部 DocumentChunk，在内存中构建 BM25 索引。

```python
# pgvector_retriever.py:352-357
results = await db.execute(
    select(DocumentChunk.id, DocumentChunk.content, DocumentChunk.doc_metadata)
)
docs = [(row.id, row.content, row.doc_metadata) for row in results]
```

**问题：**
- 文档量增长后，每次查询都要全表扫描 + 内存分词，O(n) 复杂度
- 没有增量更新机制，每次查询重建索引
- 内存占用随文档量线性增长

**优化建议：**
- 使用 PostgreSQL 的 `tsvector` + `GIN` 索引做服务端全文检索，替代内存 BM25
- 或用 Elasticsearch / MeiliSearch 做专业全文检索
- 如果坚持内存方案，至少加一个索引缓存层（文档变更时才重建）

---

## 3. 语义缓存用 MD5 哈希 — 名不副实

**现状：** 缓存键是 `md5(query.lower().strip())`，严格匹配才命中。

```python
# pgvector_retriever.py:154-156
async def _get_cache_key(self, query: str) -> str:
    return md5(query.lower().strip().encode()).hexdigest()
```

**问题：**
- "奖学金怎么申请" 和 "如何申请奖学金" 语义相同但缓存不命中
- 叫"语义缓存"但实际是精确匹配缓存，面试被问会尴尬
- 5 分钟 TTL + 100 条上限，缓存命中率极低

**优化建议：**
- 真正的语义缓存：对 query 做 embedding，用向量相似度匹配历史查询（阈值 > 0.95 才命中）
- 或者改名叫"查询缓存"，别误导
- TTL 可以根据场景调长（如 30 分钟），热门问题命中率更高

---

## 4. ~~Function Calling Agent 与 LangGraph Agent 并存 — 架构冗余~~ (已解决)

**现状：** 项目已通过多智能体架构统一了 Agent 系统：
- **Orchestrator** 作为总入口，负责意图分类和任务调度
- **FunctionCallingAgent** 集成动态技能系统，处理 Function Calling 任务
- **LangGraph graph** 作为基础的状态机框架，被多智能体系统复用

**已实现的统一架构：**
```
用户请求 → Orchestrator → [QAAgent/ScheduleAgent/EmotionalAgent/KnowledgeAgent/AssistantAgent/FunctionCallingAgent] → 结果汇总
```

**架构优势：**
- 统一的请求入口和调度机制
- 各 Agent 专业化分工，职责清晰
- 通过消息总线实现 Agent 间协作
- 动态技能系统支持插件化扩展

**后续优化方向：**
- 考虑将 LangGraph graph 作为 Orchestrator 的子图，进一步整合路由逻辑
- 优化 Agent 间的通信延迟，考虑引入异步消息队列

---

## 5. 所有业务数据都是 Mock — 缺乏真实数据验证

**现状：** `function_tools.py` 中的课表、成绩、教室数据全部是硬编码 mock。

**问题：**
- 无法验证真实数据格式下的解析和展示
- 无法测试边界情况（空数据、异常格式、大数据量）
- 面试时被问"数据从哪来"会暴露 demo 性质

**优化建议：**
- 至少做一个"demo 模式"和"生产模式"的切换
- Mock 数据覆盖更多边界情况（空课表、超长课程名、特殊字符）
- 准备一份真实数据格式的 schema 文档，说明对接方案

---

## 6. 错误处理过于宽泛 — 吞掉异常

**现状：** 大量 `try/except Exception as e` 只做 log 然后返回空值或默认值。

```python
# graph.py:70-74
try:
    result = await chain.ainvoke({})
    action = result.get("action", "direct")
except Exception as e:
    action = "direct"  # 静默降级，用户不知道发生了什么
```

**问题：**
- LLM 返回格式错误、网络超时、数据库连接失败都被同一个 catch 吞掉
- 用户看到的是"正常但错误"的回答，而不是"出了问题"的提示
- 排查问题时日志不够细

**优化建议：**
- 区分异常类型：`LLMOutputError`（格式错误 → 重试）、`NetworkError`（超时 → 降级）、`DatabaseError`（连接失败 → 报错）
- 对用户透明：关键环节失败时在 SSE 流中发送 error 事件
- 加结构化日志（request_id, user_id, agent_name, latency）

---

## 7. 多 Agent 通信缺乏状态追踪

**现状：** MessageBus 是简单的 send/broadcast，没有消息追踪、超时控制、重试机制。

```python
# message_bus.py - 简单的 dict 存储
_agents: Dict[str, BaseAgent] = {}
```

**问题：**
- Agent A 发消息给 Agent B，如果 B 处理失败或超时，A 无法知道
- 没有消息链路追踪，无法调试复杂的多 Agent 协作
- 没有并发控制，多个 Agent 可能同时修改共享状态

**优化建议：**
- 加消息 ID 和 trace_id，支持链路追踪
- 加超时和重试机制
- 考虑用 asyncio.Queue 替代直接函数调用，支持异步消息传递
- 加 dead-letter queue 存储失败消息

---

## 8. 前端 4 个独立 Streamlit 应用 — 体验割裂

**现状：** 4 个独立的 Streamlit 文件：`app_frontend.py`、`admin_frontend.py`、`schedule_frontend.py`、`treehole_frontend.py`。

**问题：**
- 用户需要打开 4 个不同的页面/端口
- 没有统一的导航和状态共享
- 每个页面独立启动，资源浪费

**优化建议：**
- 合并为一个 Streamlit 多页应用（`pages/` 目录结构）
- 或迁移到 FastAPI + 前端框架（Vue/React），Streamlit 更适合原型验证
- 统一用户会话和认证

---

## 9. 安全性缺失 — 无认证、无鉴权、无输入校验

**现状：**
- 所有 API 端点无认证，任何人可以访问
- 文件上传无类型/大小校验（虽然 Streamlit 有限制，但 API 层没有）
- SQL 注入风险低（用了 SQLAlchemy ORM），但 prompt injection 风险未处理

**问题：**
- 知识库管理接口暴露，可被恶意上传/删除文档
- 用户对话无鉴权，可冒充他人
- Prompt injection 可能绕过系统指令

**优化建议：**
- 加 JWT 认证中间件
- 文件上传加类型白名单和大小限制
- 对用户输入做 sanitization，防 prompt injection
- 敏感操作加 RBAC

---

## 10. 依赖管理不规范

**现状：** 使用 `requirements.txt`，无版本锁定，无 `pyproject.toml`。

**问题：**
- `requirements.txt` 中部分依赖无版本号（如 `fitz`、`pytesseract`）
- 无 dev/prod 依赖分离
- 无 lock 文件，不同环境可能装到不同版本

**优化建议：**
- 迁移到 `pyproject.toml` + `poetry` 或 `uv`
- 所有依赖锁定版本
- 分离 dev 依赖（pytest, black, ruff）
- 生成 `poetry.lock` 或 `requirements.lock`

---

## 11. 日志和可观测性不足

**现状：** 使用 Python `logging` 模块，只有基础的 info/warning/error 日志。

**问题：**
- 无结构化日志（JSON 格式），难以做日志分析
- 无请求链路追踪（request_id 贯穿全链路）
- 无性能指标采集（RAG 延迟、LLM 延迟、工具执行时间）
- 无告警机制

**优化建议：**
- 用 `structlog` 或 `loguru` 做结构化日志
- 加 request_id 中间件，贯穿 API → Service → DB 全链路
- 关键路径加 latency metric（RAG 检索耗时、LLM 生成耗时）
- 接入 Prometheus + Grafana 或简单的日志聚合

---

## 12. 文档版本管理功能未完善

**现状：** `DocumentVersion` 模型已定义，但文档更新时未自动创建版本记录。

**问题：**
- 用户更新文档后无法回滚到历史版本
- 版本模型存在但无实际使用，代码冗余

**优化建议：**
- 在 `add_documents` 覆盖同名文档时自动创建 `DocumentVersion`
- 提供版本列表和回滚接口
- 或者删除未使用的模型，保持代码整洁

---

## 面试中如何主动展示这些思考

**被问到"项目有什么不足"时的模板回答：**

> "目前已补了 56 个测试用例覆盖核心模块，但 RAG 管线的端到端集成测试还没补完。其次是 BM25 检索的性能问题，目前是全量加载到内存，文档量大了会有瓶颈，计划迁移到 PostgreSQL 的 tsvector 做服务端全文检索。另外语义缓存目前是 MD5 精确匹配，不是真正的语义匹配，后续会升级为向量相似度匹配。"

**被问到"如果重新做会怎么改"时的模板回答：**

> "三个核心改变：第一，BM25 迁移到 pg tsvector，减少内存占用；第二，从一开始就写测试，目前已有 56 个测试用例，但应该更早建立测试体系；第三，优化语义缓存，用向量相似度替代 MD5 精确匹配。"
