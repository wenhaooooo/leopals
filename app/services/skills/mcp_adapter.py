"""
MCP 适配器模块

将 MCP Tool 转换为 Skill
"""

import logging
from typing import Dict, Any, List, Optional

from app.services.skills.base import BaseSkill, SkillInput, SkillOutput, SkillContext

logger = logging.getLogger(__name__)


class MCPAdapter:
    """
    MCP 适配器
    
    将 MCP Server 的 Tool 转换为 Skill
    """
    
    def __init__(self, server_url: str):
        self.server_url = server_url
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取 MCP Server 的所有工具
        
        Returns:
            List[Dict]: 工具列表
        """
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.server_url}/tools/list"
                ) as response:
                    if response.status != 200:
                        logger.error(f"获取 MCP 工具列表失败: {response.status}")
                        return []
                    
                    data = await response.json()
                    return data.get("tools", [])
                    
        except Exception as e:
            logger.error(f"获取 MCP 工具列表失败: {str(e)}")
            return []
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 参数字典
            
        Returns:
            Dict: 调用结果
        """
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.server_url}/tools/call",
                    json={
                        "name": tool_name,
                        "arguments": arguments
                    }
                ) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"调用失败: {response.status}"
                        }
                    
                    return await response.json()
                    
        except Exception as e:
            logger.error(f"调用 MCP 工具失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def tool_to_skill(self, tool: Dict[str, Any]) -> Optional[BaseSkill]:
        """
        将 MCP Tool 转换为 Skill
        
        Args:
            tool: MCP Tool 定义
            
        Returns:
            Optional[BaseSkill]: 技能实例
        """
        try:
            class MCPSkill(BaseSkill):
                def __init__(self, tool_def: Dict[str, Any], adapter: MCPAdapter):
                    self.name = tool_def["name"]
                    self.description = tool_def.get("description", "")
                    self.version = "1.0.0"
                    self.category = "mcp"
                    self._tool_def = tool_def
                    self._adapter = adapter
                
                async def execute(
                    self,
                    input: SkillInput,
                    context: Optional[SkillContext] = None
                ) -> SkillOutput:
                    result = await self._adapter.call_tool(
                        self.name,
                        input.model_dump()
                    )
                    
                    if result.get("success"):
                        return SkillOutput(
                            success=True,
                            data=result.get("data"),
                            metadata={"source": "mcp"}
                        )
                    else:
                        return SkillOutput(
                            success=False,
                            error=result.get("error", "未知错误")
                        )
            
            return MCPSkill(tool, self)
            
        except Exception as e:
            logger.error(f"转换 MCP Tool 为 Skill 失败: {str(e)}")
            return None


class MCPSkillLoader:
    """
    MCP 技能加载器
    
    从 MCP Server 批量加载技能
    """
    
    def __init__(self):
        self._adapters: Dict[str, MCPAdapter] = {}
    
    def add_server(self, server_url: str, name: Optional[str] = None):
        """
        添加 MCP Server
        
        Args:
            server_url: Server URL
            name: Server 名称（可选）
        """
        server_name = name or server_url
        self._adapters[server_name] = MCPAdapter(server_url)
        logger.info(f"添加 MCP Server: {server_name}")
    
    async def load_all(self, override: bool = False) -> List[BaseSkill]:
        """
        从所有 MCP Server 加载技能
        
        Args:
            override: 是否覆盖已存在的技能
            
        Returns:
            List[BaseSkill]: 加载的技能列表
        """
        from app.services.skills.registry import SkillRegistry
        
        all_skills = []
        
        for server_name, adapter in self._adapters.items():
            tools = await adapter.list_tools()
            
            for tool in tools:
                skill = adapter.tool_to_skill(tool)
                if skill:
                    SkillRegistry().register(skill, override)
                    all_skills.append(skill)
            
            logger.info(f"从 MCP Server {server_name} 加载了 {len(tools)} 个技能")
        
        return all_skills
    
    async def load_from_server(
        self,
        server_url: str,
        override: bool = False
    ) -> List[BaseSkill]:
        """
        从指定 MCP Server 加载技能
        
        Args:
            server_url: Server URL
            override: 是否覆盖已存在的技能
            
        Returns:
            List[BaseSkill]: 加载的技能列表
        """
        from app.services.skills.registry import SkillRegistry
        
        if server_url not in self._adapters:
            self.add_server(server_url)
        
        adapter = self._adapters[server_url]
        tools = await adapter.list_tools()
        
        skills = []
        for tool in tools:
            skill = adapter.tool_to_skill(tool)
            if skill:
                SkillRegistry().register(skill, override)
                skills.append(skill)
        
        logger.info(f"从 MCP Server {server_url} 加载了 {len(skills)} 个技能")
        return skills