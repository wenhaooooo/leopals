import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageBus:
    """
    消息总线：智能体之间的通信枢纽
    
    负责智能体的注册、消息路由和结果汇总，实现智能体之间的解耦通信。
    """
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.callbacks: Dict[str, List] = {}
    
    def register_agent(self, agent_name: str, agent_instance):
        """注册智能体到消息总线"""
        self.agents[agent_name] = agent_instance
        logger.info(f"智能体注册成功: {agent_name}")
    
    async def send(self, agent_name: str, message: dict) -> dict:
        """
        发送消息给指定智能体
        
        Args:
            agent_name: 目标智能体名称
            message: 消息内容，格式为 {"query": "问题", "context": {...}}
        
        Returns:
            智能体处理结果，格式为 {"result": "...", "confidence": 0.9}
        """
        if agent_name not in self.agents:
            logger.error(f"智能体未注册: {agent_name}")
            raise ValueError(f"智能体 {agent_name} 未注册")
        
        agent = self.agents[agent_name]
        
        try:
            result = await agent.process(message["query"], message.get("context"))
            logger.info(f"智能体 {agent_name} 处理完成")
            return result
        except Exception as e:
            logger.error(f"智能体 {agent_name} 处理失败: {str(e)}")
            return {"result": "处理失败", "confidence": 0.0}
    
    async def broadcast(self, message: dict, exclude: Optional[List[str]] = None):
        """
        广播消息给所有智能体（除了排除列表中的）
        
        Args:
            message: 消息内容
            exclude: 需要排除的智能体名称列表
        """
        exclude = exclude or []
        tasks = []
        
        for name, agent in self.agents.items():
            if name not in exclude:
                tasks.append(agent.process(message.get("query", ""), message.get("context")))
        
        return await asyncio.gather(*tasks)
    
    def get_registered_agents(self) -> List[str]:
        """获取所有已注册的智能体列表"""
        return list(self.agents.keys())


# 全局消息总线实例
message_bus = MessageBus()