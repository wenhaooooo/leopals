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
    max_tokens=1000,
)


class QAAgent:
    """
    问答智能体：专注于事实性知识问答
    
    核心能力：
    - RAG检索问答
    - 知识库查询
    - 常见问题解答
    """
    
    def __init__(self):
        self.retriever = pgvector_retriever
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理问答请求
        
        Args:
            query: 用户查询内容
            context: 上下文信息
        
        Returns:
            {"result": "回答内容", "confidence": 置信度, "sources": 来源列表}
        """
        logger.info(f"问答智能体处理请求: {query}")
        
        try:
            # 1. 查询重写
            rewritten_query = await self._rewrite_query(query)
            logger.debug(f"查询重写结果: {rewritten_query}")
            
            # 2. 检索相关文档
            retrieved_docs = await self.retriever.get_relevant_documents(rewritten_query)
            
            # 3. 上下文压缩
            compressed_context = await self._compress_context(retrieved_docs, query)
            
            # 4. 生成回答
            answer = await self._generate_answer(query, compressed_context)
            
            # 5. 计算置信度
            confidence = self._calculate_confidence(retrieved_docs)
            
            return {
                "result": answer,
                "confidence": confidence,
                "sources": self._extract_sources(retrieved_docs)
            }
        
        except Exception as e:
            logger.error(f"问答智能体处理失败: {str(e)}")
            return {
                "result": f"抱歉，我暂时无法回答这个问题。错误信息：{str(e)}",
                "confidence": 0.0,
                "sources": []
            }
    
    async def _rewrite_query(self, query: str) -> str:
        """使用LLM优化查询表述"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            你是一个查询优化助手。请将用户的问题重写为更清晰、更适合检索的形式。
            保持原意不变，但使查询更精确。
            
            示例：
            原问题: "奖学金怎么申请啊"
            优化后: "奖学金申请条件和流程"
            
            原问题: "考研有什么政策吗"
            优化后: "研究生招生政策考研加分政策"
            """),
            ("user", query)
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({})
        return response.content
    
    async def _compress_context(self, docs: str, query: str) -> str:
        """压缩上下文，只保留与查询相关的内容"""
        if not docs:
            return ""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            请根据用户问题，从以下文档中提取最相关的内容。
            只保留与问题直接相关的信息，去除冗余和无关内容。
            
            用户问题: {query}
            
            文档内容:
            {context}
            
            请输出压缩后的关键信息：
            """),
            ("user", "")
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({
            "query": query,
            "context": docs
        })
        
        return response.content
    
    async def _generate_answer(self, query: str, context: str) -> str:
        """基于上下文生成回答"""
        system_prompt = """
        你是花小狮 (LeoPals)，一只活泼俏皮的小狮子助手！🐾
        
        请根据以下信息回答用户问题：
        
        【知识库信息】
        {context}
        
        **规则**：
        1. 如果知识库中有相关信息，请基于这些信息回答
        2. 如果没有找到答案，请诚实说"不知道"，严禁编造！
        3. 保持回答活泼可爱，使用适当的表情符号
        4. 避免冗长，保持简洁
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", query)
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({
            "context": context or "无相关知识"
        })
        
        return response.content
    
    def _calculate_confidence(self, docs: str) -> float:
        """根据检索结果计算置信度"""
        if not docs:
            return 0.3
        
        # 根据文档数量和相关性计算置信度
        doc_count = docs.count("---") + 1
        if doc_count >= 3:
            return min(0.95, 0.6 + doc_count * 0.1)
        elif doc_count == 2:
            return 0.75
        elif doc_count == 1:
            return 0.6
        else:
            return 0.3
    
    def _extract_sources(self, docs: str) -> List[str]:
        """从检索结果中提取来源信息"""
        sources = []
        if docs:
            lines = docs.split("\n")
            for line in lines:
                if "来源:" in line or "文档:" in line or "链接:" in line:
                    sources.append(line.strip())
        return sources[:3]