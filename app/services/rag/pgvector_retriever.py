import asyncio
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from hashlib import md5

import httpx
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.document import DocumentChunk, DocumentSource
from app.services.rag.document_loader import CampusDocumentLoader

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


class QueryRewriter:
    """查询重写器，将模糊查询转换为更精确的检索查询"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
            model_name=settings.llm_model_name,
            temperature=0.3,
            max_tokens=200
        )
        
        self.rewrite_prompt = ChatPromptTemplate.from_messages([
            ("system", """
你是一个查询优化助手。请将用户的问题重写为更清晰、更适合检索的形式。

规则：
1. 保持原意不变，但使查询更精确
2. 将口语化表达转换为正式关键词
3. 如果问题模糊，扩展为多个可能的关键词
4. 使用中文

示例：
原问题: "奖学金怎么申请啊"
优化后: "奖学金申请条件流程"

原问题: "考研有什么政策吗"
优化后: "研究生招生政策考研加分政策"

原问题: "校历哪里看"
优化后: "校历查询"

原问题: "成绩怎么查"
优化后: "成绩查询成绩查询方法"
            """),
            ("user", "原问题: {query}\n优化后:"),
        ])
    
    async def rewrite(self, query: str) -> str:
        """重写查询"""
        try:
            chain = self.rewrite_prompt | self.llm
            response = await chain.ainvoke({"query": query})
            return response.content.strip()
        except Exception as e:
            logger.warning(f"Query rewriting failed: {str(e)}")
            return query


class ContextCompressor:
    """上下文压缩器，根据用户查询过滤和压缩检索到的文档内容"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
            model_name=settings.llm_model_name,
            temperature=0.1,
            max_tokens=500
        )
        
        self.compress_prompt = ChatPromptTemplate.from_messages([
            ("system", """
你是一个文档内容压缩专家。请根据用户的问题，从提供的文档中提取最相关、最关键的信息。

规则：
1. 只保留与用户问题直接相关的内容
2. 删除冗余、重复或无关的信息
3. 保持信息的完整性和准确性
4. 输出格式保持与原文一致
5. 使用中文

示例：
用户问题: "奖学金申请条件"
文档内容: "我校奖学金分为多种类型，包括学业奖学金、励志奖学金等。申请条件包括：1. 成绩优异，GPA达到3.5以上；2. 无违纪记录；3. 积极参与社会实践。申请时间为每年9月。"
压缩后: "奖学金申请条件：1. 成绩优异，GPA达到3.5以上；2. 无违纪记录；3. 积极参与社会实践。"
            """),
            ("user", "用户问题: {query}\n\n文档内容:\n{context}\n\n压缩后:"),
        ])
    
    async def compress(self, query: str, context: str) -> str:
        """压缩上下文，保留与查询相关的内容"""
        if not context:
            return ""
        
        try:
            chain = self.compress_prompt | self.llm
            response = await chain.ainvoke({
                "query": query,
                "context": context
            })
            result = response.content.strip()
            logger.info(f"上下文压缩完成，原长度: {len(context)}, 压缩后长度: {len(result)}")
            return result
        except Exception as e:
            logger.warning(f"Context compression failed: {str(e)}")
            return context


class OllamaEmbeddingClient:
    def __init__(self, model_name: str = "nomic-embed-text:v1.5"):
        self.model_name = model_name
        self.base_url = settings.ollama_host

    async def embed(self, text: str) -> List[float]:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        tasks = [self.embed(text) for text in texts]
        return await asyncio.gather(*tasks, return_exceptions=False)


class PgVectorHybridRetriever:
    def __init__(self):
        self.embedding_client = OllamaEmbeddingClient()
        self.document_loader = CampusDocumentLoader()
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
        self._semantic_cache = {}  # 语义缓存，key为query的hash值
        self._cache_max_size = 100  # 缓存最大条目数
        self._query_rewriter = QueryRewriter()  # 查询重写器
        self._context_compressor = ContextCompressor()  # 上下文压缩器
    
    async def _get_cache_key(self, query: str) -> str:
        """生成查询的缓存键"""
        return md5(query.lower().strip().encode()).hexdigest()
    
    async def _update_cache(self, query: str, result: str):
        """更新语义缓存"""
        cache_key = await self._get_cache_key(query)
        
        # 如果缓存已满，删除最早的条目
        if len(self._semantic_cache) >= self._cache_max_size:
            oldest_key = next(iter(self._semantic_cache))
            del self._semantic_cache[oldest_key]
        
        self._semantic_cache[cache_key] = {
            "result": result,
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def _get_cached_result(self, query: str) -> Optional[str]:
        """获取缓存结果"""
        cache_key = await self._get_cache_key(query)
        cached = self._semantic_cache.get(cache_key)
        
        if cached:
            # 检查缓存是否过期（5分钟）
            if asyncio.get_event_loop().time() - cached["timestamp"] < 300:
                logger.info(f"使用缓存结果，query: {query[:30]}...")
                return cached["result"]
            else:
                del self._semantic_cache[cache_key]
        
        return None

    async def add_documents(self, file_path: str, description: Optional[str] = None) -> int:
        docs = await self.document_loader.async_load_and_split(file_path)
        
        if not docs:
            raise ValueError("文档内容为空")
        
        path = Path(file_path)
        category = self.document_loader._infer_category(path.name)
        
        async with AsyncSessionLocal() as db:
            doc_source = DocumentSource(
                file_name=path.name,
                file_path=str(path),
                file_type=path.suffix.lower(),
                file_size=path.stat().st_size,
                category=category,
                chunk_count=len(docs),
                description=description,
                status="processing"
            )
            db.add(doc_source)
            await db.flush()
            doc_source_id = doc_source.id
            
            contents = [doc.page_content for doc in docs]
            embeddings = await self.embedding_client.embed_documents(contents)
            
            for i, doc in enumerate(docs):
                embedding = embeddings[i]

                db_chunk = DocumentChunk(
                    content=doc.page_content,
                    embedding=embedding,
                    doc_metadata=doc.metadata,
                    chunk_index=doc.metadata.get("chunk_index", 0),
                    source_file=doc.metadata.get("source", ""),
                    category=doc.metadata.get("category", ""),
                    document_source_id=doc_source_id
                )
                db.add(db_chunk)

            doc_source.status = "processed"
            await db.commit()
            logger.info(f"Added {len(docs)} document chunks to database")
            return doc_source_id

    async def list_document_sources(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(DocumentSource).order_by(DocumentSource.upload_time.desc()).offset(skip).limit(limit)
            )
            sources = result.scalars().all()
            
            return [
                {
                    "id": s.id,
                    "file_name": s.file_name,
                    "file_type": s.file_type,
                    "file_size": s.file_size,
                    "category": s.category,
                    "chunk_count": s.chunk_count,
                    "upload_time": s.upload_time.isoformat() if s.upload_time else None,
                    "description": s.description,
                    "status": s.status
                }
                for s in sources
            ]

    async def get_document_source(self, source_id: int) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(DocumentSource).where(DocumentSource.id == source_id))
            source = result.scalar_one_or_none()
            if not source:
                return None
            return {
                "id": source.id,
                "file_name": source.file_name,
                "file_type": source.file_type,
                "file_size": source.file_size,
                "category": source.category,
                "chunk_count": source.chunk_count,
                "upload_time": source.upload_time.isoformat() if source.upload_time else None,
                "description": source.description,
                "status": source.status
            }

    async def delete_document_source(self, source_id: int) -> bool:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(DocumentSource).where(DocumentSource.id == source_id))
            source = result.scalar_one_or_none()
            if not source:
                return False
            
            await db.execute(delete(DocumentChunk).where(DocumentChunk.document_source_id == source_id))
            await db.execute(delete(DocumentSource).where(DocumentSource.id == source_id))
            await db.commit()
            
            if os.path.exists(source.file_path):
                try:
                    os.remove(source.file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete file {source.file_path}: {e}")
            
            logger.info(f"Deleted document source {source_id}")
            return True

    async def get_knowledge_stats(self) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            chunk_count = await db.execute(select(func.count(DocumentChunk.id)))
            source_count = await db.execute(select(func.count(DocumentSource.id)))
            category_stats = await db.execute(
                select(DocumentSource.category, func.count(DocumentSource.id))
                .group_by(DocumentSource.category)
            )
            
            return {
                "total_chunks": chunk_count.scalar() or 0,
                "total_sources": source_count.scalar() or 0,
                "category_counts": {row[0]: row[1] for row in category_stats.all()}
            }

    async def add_directory(self, directory_path: str):
        docs = await self.document_loader.async_load_directory(directory_path)

        async with AsyncSessionLocal() as db:
            for doc in docs:
                embedding = await self.embedding_client.embed(doc.page_content)

                db_chunk = DocumentChunk(
                    content=doc.page_content,
                    embedding=embedding,
                    doc_metadata=doc.metadata,
                    chunk_index=doc.metadata.get("chunk_index", 0),
                    source_file=doc.metadata.get("source", ""),
                    category=doc.metadata.get("category", "")
                )
                db.add(db_chunk)

            await db.commit()
            logger.info(f"Added {len(docs)} document chunks from directory")

    async def _vector_search(self, query: str, top_k: int = 10) -> List[Tuple[int, float, dict]]:
        query_embedding = await self.embedding_client.embed(query)

        async with AsyncSessionLocal() as db:
            results = await db.execute(
                select(
                    DocumentChunk.id,
                    DocumentChunk.content,
                    DocumentChunk.doc_metadata,
                    DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
                )
                .order_by("distance")
                .limit(top_k)
            )

            return [
                (row.id, 1 - row.distance, {"content": row.content, "doc_metadata": row.doc_metadata})
                for row in results
            ]

    async def _bm25_search(self, query: str, top_k: int = 10) -> List[Tuple[int, float, dict]]:
        from rank_bm25 import BM25Okapi
        import re

        async with AsyncSessionLocal() as db:
            results = await db.execute(
                select(DocumentChunk.id, DocumentChunk.content, DocumentChunk.doc_metadata)
            )

            docs = [(row.id, row.content, row.doc_metadata) for row in results]

        if not docs:
            return []

        tokenized_corpus = [re.findall(r'\w+', doc[1].lower()) for doc in docs]
        bm25 = BM25Okapi(tokenized_corpus)

        tokenized_query = re.findall(r'\w+', query.lower())
        scores = bm25.get_scores(tokenized_query)

        scored_docs = [(docs[i][0], scores[i], {"content": docs[i][1], "doc_metadata": docs[i][2]})
                      for i in range(len(docs))]
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        return scored_docs[:top_k]

    def _rrf_fusion(
        self,
        dense_results: List[Tuple[int, float, dict]],
        sparse_results: List[Tuple[int, float, dict]],
        k: int = 60,
    ) -> List[Tuple[int, float, dict]]:
        scores = defaultdict(float)
        doc_map = {}

        for rank, (doc_id, score, payload) in enumerate(dense_results):
            scores[doc_id] += 1.0 / (k + rank + 1)
            doc_map[doc_id] = payload

        for rank, (doc_id, score, payload) in enumerate(sparse_results):
            scores[doc_id] += 1.0 / (k + rank + 1)
            if doc_id not in doc_map:
                doc_map[doc_id] = payload

        combined = [(doc_id, score, doc_map[doc_id]) for doc_id, score in scores.items()]
        combined.sort(key=lambda x: x[1], reverse=True)

        return combined

    async def get_relevant_documents(
        self,
        query: str,
        top_k: int = 5,
        use_cache: bool = True,
        use_rewrite: bool = True,
        use_compression: bool = True
    ) -> str:
        # 检查缓存
        if use_cache:
            cached_result = await self._get_cached_result(query)
            if cached_result:
                return cached_result
        
        # 查询重写
        if use_rewrite:
            rewritten_query = await self._query_rewriter.rewrite(query)
            if rewritten_query != query:
                logger.info(f"查询重写: '{query}' -> '{rewritten_query}'")
            search_query = rewritten_query
        else:
            search_query = query
        
        try:
            vector_task = self._vector_search(search_query, top_k * 2)
            bm25_task = self._bm25_search(search_query, top_k * 2)

            vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)

            fused_results = self._rrf_fusion(vector_results, bm25_results)

            contexts = []
            for doc_id, score, payload in fused_results[:top_k]:
                content = payload.get("content", "")
                doc_metadata = payload.get("doc_metadata", {})
                category = doc_metadata.get("category", "")
                file_name = doc_metadata.get("file_name", "")

                context = f"""【{category}】{file_name}
内容：{content}
---"""
                contexts.append(context)

            result = "\n\n".join(contexts)
            
            # 上下文压缩
            if use_compression and result:
                result = await self._context_compressor.compress(query, result)
            
            # 更新缓存
            if use_cache:
                await self._update_cache(query, result)
            
            return result

        except Exception as e:
            logger.error(f"Error during hybrid search: {str(e)}")
            raise


pgvector_retriever = PgVectorHybridRetriever()