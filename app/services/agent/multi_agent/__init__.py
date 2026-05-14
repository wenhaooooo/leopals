"""
多智能体模块初始化

包含：
- MessageBus: 消息总线，智能体通信枢纽
- Orchestrator: 调度智能体，负责意图识别和任务分发
- QAAgent: 问答智能体，处理事实性问答
- ScheduleAgent: 日程智能体，处理课表和日程
- EmotionalAgent: 情感智能体，提供情感支持
- KnowledgeAgent: 知识智能体，处理文档知识查询
- AssistantAgent: 助手智能体，处理复杂任务

使用方式：
```python
from app.services.agent.multi_agent import orchestrator, message_bus

# 注册智能体（在应用启动时执行）
from app.services.agent.multi_agent import init_multi_agent
init_multi_agent()

# 使用调度智能体处理请求
result = await orchestrator.process("用户问题")
```
"""

from .message_bus import message_bus
from .orchestrator import Orchestrator
from .qa_agent import QAAgent
from .schedule_agent import ScheduleAgent
from .emotional_agent import EmotionalAgent
from .knowledge_agent import KnowledgeAgent
from .assistant_agent import AssistantAgent

# 创建智能体实例
orchestrator = Orchestrator()
qa_agent = QAAgent()
schedule_agent = ScheduleAgent()
emotional_agent = EmotionalAgent()
knowledge_agent = KnowledgeAgent()
assistant_agent = AssistantAgent()


def init_multi_agent():
    """
    初始化多智能体系统
    
    在应用启动时调用，注册所有智能体到消息总线
    """
    message_bus.register_agent("Orchestrator", orchestrator)
    message_bus.register_agent("QAAgent", qa_agent)
    message_bus.register_agent("ScheduleAgent", schedule_agent)
    message_bus.register_agent("EmotionalAgent", emotional_agent)
    message_bus.register_agent("KnowledgeAgent", knowledge_agent)
    message_bus.register_agent("AssistantAgent", assistant_agent)
