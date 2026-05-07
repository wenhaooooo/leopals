import asyncio
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

import httpx
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.document import DocumentChunk, DocumentSource
from app.services.rag.document_loader import CampusDocumentLoader

logger = logging.getLogger(__name__)


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
    ) -> str:
        try:
            vector_task = self._vector_search(query, top_k * 2)
            bm25_task = self._bm25_search(query, top_k * 2)

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

            return "\n\n".join(contexts)

        except Exception as e:
            logger.error(f"Error during hybrid search: {str(e)}")
            raise


pgvector_retriever = PgVectorHybridRetriever()