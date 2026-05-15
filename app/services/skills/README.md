# 🛠️ 动态技能注册系统

## 概述

LeoPals 技能系统是一个插件化的智能体能力管理框架，支持动态加载、热重载和远程技能集成。

## 架构

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

## 核心组件

### 1. BaseSkill (技能基类)

所有技能必须继承 `BaseSkill` 并实现 `execute` 方法：

```python
from app.services.skills.base import BaseSkill, SkillInput, SkillOutput

class MySkill(BaseSkill):
    name = "my_skill"
    description = "我的技能"
    version = "1.0.0"
    category = "custom"
    
    async def execute(self, input: SkillInput, context: SkillContext) -> SkillOutput:
        # 执行技能逻辑
        return SkillOutput(success=True, data={"result": "success"})
```

### 2. SkillRegistry (技能注册表)

全局单例，管理所有已注册的技能：

```python
from app.services.skills.registry import SkillRegistry

# 注册技能
registry = SkillRegistry()
registry.register(skill_instance)

# 查询技能
skill = registry.get("skill_name")

# 执行技能
result = await registry.execute("skill_name", input_data, context)

# 列出所有技能
skills = registry.list_all()
```

### 3. SkillLoader (技能加载器)

支持多种加载方式：

```python
from app.services.skills import SkillLoader

loader = SkillLoader()

# 从文件加载
await loader.load_from_file("path/to/skill.py")

# 从目录批量加载
skills = await loader.load_from_directory("app/services/skills/impls")

# 从 Git 仓库加载
skills = await loader.load_from_git(
    repo_url="https://github.com/user/skills.git",
    branch="main"
)

# 从 MCP Server 加载
skills = await loader.load_from_mcp("http://localhost:3000")

# 热重载
reloaded = await loader.hot_reload("path/to/skill.py")
```

## 已实现的技能

| 技能名称 | 功能 | 类别 |
|---------|------|------|
| `schedule_query` | 查询课表 | schedule |
| `grade_query` | 查询成绩 | academic |
| `classroom_search` | 搜索空教室 | facility |
| `notification_set` | 设置提醒 | notification |

## 使用示例

### 基础使用

```python
from app.services.skills import init_skills, registry
from app.services.skills.impls.schedule_skill import GetScheduleInput

# 初始化技能系统
await init_skills()

# 执行技能
input_data = GetScheduleInput(week=8, day_of_week=1)
result = await registry.execute("schedule_query", input_data)

if result.success:
    print(result.data)
else:
    print(f"Error: {result.error}")
```

### 动态加载技能

```python
from app.services.skills import SkillLoader

loader = SkillLoader()

# 从目录加载所有技能
skills = await loader.load_from_directory()

# 热重载单个技能
reloaded = await loader.hot_reload("app/services/skills/impls/schedule_skill.py")
```

### 技能管理

```python
from app.services.skills.registry import SkillRegistry

reg = SkillRegistry()

# 禁用技能
reg.disable("schedule_query")

# 启用技能
reg.enable("schedule_query")

# 注销技能
reg.unregister("schedule_query")

# 按类别列出技能
schedule_skills = reg.list_by_category("schedule")
```

## 创建自定义技能

1. 创建技能文件 `app/services/skills/impls/my_skill.py`:

```python
from typing import Optional
from pydantic import Field
from app.services.skills.base import BaseSkill, SkillInput, SkillOutput, SkillContext

class MySkillInput(SkillInput):
    """输入参数定义"""
    param1: str = Field(..., description="参数1")
    param2: Optional[int] = Field(None, description="参数2")

class MySkill(BaseSkill):
    """我的技能"""
    
    name = "my_skill"
    description = "技能描述"
    version = "1.0.0"
    category = "custom"
    
    async def execute(
        self,
        input: MySkillInput,
        context: Optional[SkillContext] = None
    ) -> SkillOutput:
        """执行技能"""
        try:
            # 技能逻辑
            result = {
                "param1": input.param1,
                "param2": input.param2
            }
            
            return SkillOutput(
                success=True,
                data=result,
                metadata={"message": "执行成功"}
            )
            
        except Exception as e:
            return SkillOutput(
                success=False,
                error=str(e)
            )
```

2. 注册技能：

```python
from app.services.skills.impls.my_skill import MySkill
from app.services.skills.registry import SkillRegistry

registry = SkillRegistry()
registry.register(MySkill())
```

## MCP 集成

将 MCP Server 的工具转换为技能：

```python
from app.services.skills.mcp_adapter import MCPSkillLoader

loader = MCPSkillLoader()

# 添加 MCP Server
loader.add_server("http://localhost:3000", "campus_services")

# 从所有 MCP Server 加载技能
skills = await loader.load_all()

# 从指定 Server 加载
skills = await loader.load_from_server("http://localhost:3000")
```

## LangChain 集成

将技能转换为 LangChain 工具，无缝集成到 Function Calling：

```python
from app.services.skills.langchain_adapter import convert_all_skills_to_tools

# 转换所有技能为 LangChain 工具
tools = convert_all_skills_to_tools()

# 转换指定类别的技能
from app.services.skills.langchain_adapter import get_skill_tools_by_category
schedule_tools = get_skill_tools_by_category("schedule")

# 在 Function Calling Agent 中使用
from app.services.agent.multi_agent.function_calling_agent import FunctionCallingAgent

agent = FunctionCallingAgent(use_skill_system=True)
result = await agent.process("帮我查一下第8周的课表")
```

**技术优势**：
- 自动参数提取：LLM 自动从用户输入中提取技能参数
- 类型安全：基于 Pydantic 的参数校验
- 无缝集成：技能自动转换为 LangChain 工具
- 动态扩展：新技能无需修改 Agent 代码

## 运行示例

```bash
# 运行所有示例
python app/services/skills/example.py
```

## 技术亮点

1. **插件化架构**：技能以插件形式管理，支持热加载
2. **类型安全**：基于 Pydantic 的参数校验
3. **异步执行**：支持高并发技能调用
4. **多源加载**：支持本地文件、Git 仓库、MCP Server
5. **生命周期管理**：支持技能的启用、禁用、注销
6. **上下文传递**：支持用户 ID、会话 ID 等上下文信息

## 扩展方向

- 技能依赖管理
- 技能版本控制
- 技能性能监控
- 技能权限控制
- 技能组合（Composite Skill）
