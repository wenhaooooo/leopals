import asyncio
import logging
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.document import DocumentChunk
from app.services.rag.document_loader import CampusDocumentLoader

logger = logging.getLogger(__name__)


class OllamaEmbeddingClient:
    def __init__(self, model_name: str = "nomic-embed-text:v1.5"):
        self.model_name = model_name
        self.base_url = settings.ollama_host

    async def embed(self, text: str) -> List[float]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        tasks = [self.embed(text) for text in texts]
        return await asyncio.gather(*tasks)


class PgVectorHybridRetriever:
    def __init__(self):
        self.embedding_client = OllamaEmbeddingClient()
        self.document_loader = CampusDocumentLoader()

    async def add_documents(self, file_path: str):
        docs = await self.document_loader.async_load_and_split(file_path)

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
            logger.info(f"Added {len(docs)} document chunks to database")

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