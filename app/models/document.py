from sqlalchemy import Column, Integer, String, JSON, Index
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from app.core.database import Base
from app.core.config import settings


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    embedding = Column(Vector(settings.embedding_dimension))
    doc_metadata = Column(JSONB, default={})
    chunk_index = Column(Integer, nullable=False, default=0)
    source_file = Column(String, nullable=True)
    category = Column(String, nullable=True)

    __table_args__ = (
        Index(
            "ix_document_chunks_embedding",
            embedding,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
    )