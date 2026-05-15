"""
技能加载器模块

支持从本地文件和远程仓库动态加载技能
"""

import os
import importlib.util
import logging
import aiohttp
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.services.skills.base import BaseSkill
from app.services.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    技能加载器
    
    支持从本地文件和远程仓库加载技能
    """
    
    def __init__(self, base_path: str = "app/services/skills/impls"):
        self.base_path = Path(base_path)
        self._ensure_base_path()
    
    def _ensure_base_path(self):
        """确保技能目录存在"""
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建技能目录: {self.base_path}")
    
    async def load_from_file(
        self,
        filepath: str,
        override: bool = False
    ) -> Optional[BaseSkill]:
        """
        从 Python 文件加载技能
        
        Args:
            filepath: 文件路径
            override: 是否覆盖已存在的技能
            
        Returns:
            Optional[BaseSkill]: 加载的技能实例
        """
        try:
            spec = importlib.util.spec_from_file_location(
                f"skill_module_{os.path.basename(filepath)}",
                filepath
            )
            
            if spec is None or spec.loader is None:
                logger.error(f"无法加载模块: {filepath}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            skills = self._extract_skills_from_module(module)
            
            for skill in skills:
                SkillRegistry().register(skill, override)
            
            logger.info(f"从文件加载技能: {filepath}")
            return skills[0] if skills else None
            
        except Exception as e:
            logger.error(f"从文件加载技能失败 {filepath}: {str(e)}")
            return None
    
    async def load_from_directory(
        self,
        directory: Optional[str] = None,
        override: bool = False
    ) -> List[BaseSkill]:
        """
        从目录批量加载技能
        
        Args:
            directory: 目录路径，默认为 base_path
            override: 是否覆盖已存在的技能
            
        Returns:
            List[BaseSkill]: 加载的技能实例列表
        """
        dir_path = Path(directory) if directory else self.base_path
        
        if not dir_path.exists():
            logger.warning(f"技能目录不存在: {dir_path}")
            return []
        
        skills = []
        
        for filepath in dir_path.glob("*.py"):
            if filepath.name.startswith("_"):
                continue
            
            skill = await self.load_from_file(
                str(filepath),
                override=override
            )
            if skill:
                skills.append(skill)
        
        logger.info(f"从目录加载了 {len(skills)} 个技能: {dir_path}")
        return skills
    
    async def load_from_git(
        self,
        repo_url: str,
        branch: str = "main",
        skill_pattern: str = "*_skill.py",
        override: bool = False
    ) -> List[BaseSkill]:
        """
        从 Git 仓库加载技能（支持 GitHub、Gitee 等）
        
        Args:
            repo_url: 仓库 URL
            branch: 分支名称
            skill_pattern: 技能文件匹配模式
            override: 是否覆盖已存在的技能
            
        Returns:
            List[BaseSkill]: 加载的技能实例列表
        """
        try:
            api_url = self._convert_to_raw_url(repo_url, branch, skill_pattern)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status != 200:
                        logger.error(f"获取仓库文件失败: {response.status}")
                        return []
                    
                    content = await response.text()
                    
            skills = self._parse_git_content(content, repo_url, branch)
            
            for skill in skills:
                SkillRegistry().register(skill, override)
            
            logger.info(f"从 Git 仓库加载了 {len(skills)} 个技能: {repo_url}")
            return skills
            
        except Exception as e:
            logger.error(f"从 Git 仓库加载技能失败 {repo_url}: {str(e)}")
            return []
    
    async def load_from_mcp(
        self,
        server_url: str,
        override: bool = False
    ) -> List[BaseSkill]:
        """
        从 MCP Server 加载技能
        
        Args:
            server_url: MCP Server 地址
            override: 是否覆盖已存在的技能
            
        Returns:
            List[BaseSkill]: 加载的技能实例列表
        """
        try:
            from app.services.skills.mcp_adapter import MCPAdapter
            
            adapter = MCPAdapter(server_url)
            tools = await adapter.list_tools()
            
            skills = []
            for tool in tools:
                skill = adapter.tool_to_skill(tool)
                if skill:
                    SkillRegistry().register(skill, override)
                    skills.append(skill)
            
            logger.info(f"从 MCP Server 加载了 {len(skills)} 个技能: {server_url}")
            return skills
            
        except ImportError:
            logger.warning("MCP Adapter 未安装，跳过 MCP 技能加载")
            return []
        except Exception as e:
            logger.error(f"从 MCP Server 加载技能失败 {server_url}: {str(e)}")
            return []
    
    async def hot_reload(
        self,
        filepath: str
    ) -> Optional[BaseSkill]:
        """
        热重载技能（不重启服务）
        
        Args:
            filepath: 文件路径
            
        Returns:
            Optional[BaseSkill]: 重载的技能实例
        """
        try:
            spec = importlib.util.spec_from_file_location(
                f"skill_reload_{os.path.basename(filepath)}",
                filepath
            )
            
            if spec is None:
                logger.error(f"无法加载模块: {filepath}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            skills = self._extract_skills_from_module(module)
            
            if not skills:
                return None
            
            skill = skills[0]
            old_skill = SkillRegistry().get(skill.name)
            
            if old_skill:
                SkillRegistry().unregister(skill.name)
            
            SkillRegistry().register(skill, override=True)
            
            logger.info(f"热重载技能: {skill.name}")
            return skill
            
        except Exception as e:
            logger.error(f"热重载技能失败 {filepath}: {str(e)}")
            return None
    
    def _extract_skills_from_module(
        self,
        module: Any
    ) -> List[BaseSkill]:
        """
        从模块中提取技能类实例
        
        Args:
            module: 模块对象
            
        Returns:
            List[BaseSkill]: 技能实例列表
        """
        skills = []
        
        for attr_name in dir(module):
            if attr_name.startswith("_"):
                continue
            
            attr = getattr(module, attr_name)
            
            if isinstance(attr, type) and issubclass(attr, BaseSkill) and attr is not BaseSkill:
                try:
                    skill_instance = attr()
                    skills.append(skill_instance)
                except Exception as e:
                    logger.error(f"实例化技能失败 {attr_name}: {str(e)}")
        
        return skills
    
    def _convert_to_raw_url(
        self,
        repo_url: str,
        branch: str,
        pattern: str
    ) -> str:
        """
        将仓库 URL 转换为原始文件访问 URL
        
        Args:
            repo_url: 仓库 URL
            branch: 分支名称
            pattern: 文件匹配模式
            
        Returns:
            str: 原始文件访问 URL
        """
        if "github.com" in repo_url:
            if repo_url.endswith(".git"):
                repo_url = repo_url[:-4]
            return f"{repo_url}/raw/{branch}/"
        elif "gitee.com" in repo_url:
            if repo_url.endswith(".git"):
                repo_url = repo_url[:-4]
            return f"{repo_url}/raw/{branch}/"
        else:
            return repo_url
    
    def _parse_git_content(
        self,
        content: str,
        repo_url: str,
        branch: str
    ) -> List[BaseSkill]:
        """
        解析 Git 仓库返回的内容
        
        Args:
            content: API 返回内容
            repo_url: 仓库 URL
            branch: 分支名称
            
        Returns:
            List[BaseSkill]: 技能实例列表
        """
        skills = []
        
        try:
            import json
            files = json.loads(content)
            
            for file_info in files:
                if not file_info.get("name", "").endswith("_skill.py"):
                    continue
                
                download_url = f"{repo_url}/raw/{branch}/{file_info['name']}"
                
                skill = self._download_and_load_skill(download_url)
                if skill:
                    skills.append(skill)
                    
        except json.JSONDecodeError:
            logger.error("解析 Git 返回内容失败")
        
        return skills
    
    async def _download_and_load_skill(
        self,
        url: str
    ) -> Optional[BaseSkill]:
        """
        下载并加载技能
        
        Args:
            url: 下载 URL
            
        Returns:
            Optional[BaseSkill]: 技能实例
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    content = await response.text()
                    
            temp_file = self.base_path / f"temp_{url.split('/')[-1]}"
            
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            skill = await self.load_from_file(str(temp_file))
            
            if temp_file.exists():
                temp_file.unlink()
            
            return skill
            
        except Exception as e:
            logger.error(f"下载并加载技能失败 {url}: {str(e)}")
            return None


class SkillWatcher:
    """
    技能文件监听器
    
    监听技能文件变化，自动触发热重载
    """
    
    def __init__(self, loader: SkillLoader):
        self.loader = loader
        self._watching = False
    
    async def start(self, directory: Optional[str] = None):
        """
        开始监听文件变化
        
        Args:
            directory: 监听目录，默认为 loader.base_path
        """
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        class SkillFileHandler(FileSystemEventHandler):
            def __init__(self, loader):
                self.loader = loader
            
            async def on_modified(self, event):
                if event.is_directory:
                    return
                
                if event.src_path.endswith("_skill.py"):
                    logger.info(f"检测到文件变化: {event.src_path}")
                    await self.loader.hot_reload(event.src_path)
        
        watch_path = Path(directory) if directory else self.loader.base_path
        
        event_handler = SkillFileHandler(self.loader)
        observer = Observer()
        observer.schedule(event_handler, str(watch_path), recursive=False)
        observer.start()
        
        self._watching = True
        logger.info(f"开始监听技能目录: {watch_path}")
        
        try:
            while self._watching:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        
        observer.join()
    
    def stop(self):
        """停止监听"""
        self._watching = False
        logger.info("停止监听技能目录")