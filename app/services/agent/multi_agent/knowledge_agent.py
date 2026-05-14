import logging
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.services.rag.pgvector_retriever import pgvector_retriever

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_api_base,
    model_name=settings.llm_model_name,
    temperature=0.1,
    max_tokens=1500,
)


class KnowledgeAgent:
    """
    知识智能体：专注于深度文档理解和专业知识问答
    
    核心能力：
    - 文档理解
    - 政策解读
    - 多模态内容分析
    """
    
    def __init__(self):
        self.retriever = pgvector_retriever
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理文档知识查询请求
        
        Args:
            query: 用户查询内容
            context: 上下文信息
        
        Returns:
            {"result": "处理结果", "confidence": 置信度}
        """
        logger.info(f"知识智能体处理请求: {query}")
        
        # 检查是否包含图片
        has_image = self._detect_image(query)
        
        if has_image:
            # 多模态分析（简化处理）
            result = await self._analyze_multimodal(query)
        else:
            # 文本检索分析
            result = await self._analyze_text(query)
        
        return {"result": result, "confidence": 0.9}
    
    def _detect_image(self, query: str) -> bool:
        """检测查询中是否包含图片引用"""
        image_patterns = ["图片", "截图", "照片", "上传", "image", "picture", "photo"]
        return any(pattern in query.lower() for pattern in image_patterns)
    
    async def _analyze_text(self, query: str) -> str:
        """分析文本知识"""
        try:
            # 1. 检索相关文档
            retrieved_docs = await self.retriever.get_relevant_documents(query)
            
            if not retrieved_docs:
                return "抱歉，我没有找到相关的文档信息。您可以尝试用其他方式描述问题~ 📚"
            
            # 2. 深度分析文档
            analysis = await self._deep_analyze(query, retrieved_docs)
            
            return analysis
        
        except Exception as e:
            logger.error(f"文本分析失败: {str(e)}")
            return f"抱歉，文档分析失败了：{str(e)}"
    
    async def _analyze_multimodal(self, query: str) -> str:
        """分析多模态内容（图片+文字）"""
        # 简化处理：实际项目中会调用多模态模型
        return f"收到您的图片请求！我来帮您分析~ 🖼️\n\n由于当前版本限制，图片分析功能正在开发中，请稍后再试。"
    
    async def _deep_analyze(self, query: str, docs: str) -> str:
        """深度分析文档内容"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            你是一个专业的文档分析专家。请根据提供的文档内容，详细解答用户的问题。
            
            【参考文档】
            {documents}
            
            【分析要求】
            1. 深入理解文档内容
            2. 提供详细、准确的回答
            3. 如果涉及政策或规定，请逐条说明
            4. 保持专业但友好的语气
            5. 使用适当的表情符号增加亲和力
            
            如果文档中没有相关信息，请明确说明。
            """),
            ("user", query)
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({
            "documents": docs
        })
        
        return response.content
    
    async def _extract_key_points(self, docs: str, query: str) -> List[str]:
        """从文档中提取关键点"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            请从以下文档中提取与用户问题相关的关键点：
            
            用户问题: {query}
            
            文档内容:
            {documents}
            
            请输出JSON格式：{"key_points": ["关键点1", "关键点2", ...]}
            """),
            ("user", "")
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({
            "query": query,
            "documents": docs
        })
        
        try:
            import json
            result = json.loads(response.content)
            return result.get("key_points", [])
        except:
            return []