from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                embedding vector(768),
                doc_metadata JSONB DEFAULT '{}',
                chunk_index INTEGER NOT NULL DEFAULT 0,
                source_file TEXT,
                category TEXT
            )
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding
            ON document_chunks USING hnsw (embedding vector_cosine_ops)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_document_chunks_category
            ON document_chunks (category)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_document_chunks_content
            ON document_chunks USING gin (to_tsvector('english', content))
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_document_chunks_source
            ON document_chunks (source_file)
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS document_sources (
                id SERIAL PRIMARY KEY,
                file_name VARCHAR NOT NULL,
                file_path VARCHAR NOT NULL,
                file_type VARCHAR NOT NULL,
                file_size INTEGER NOT NULL,
                category VARCHAR NOT NULL,
                chunk_count INTEGER DEFAULT 0,
                upload_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                status VARCHAR DEFAULT 'processed'
            )
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_document_sources_file_name
            ON document_sources (file_name)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_document_sources_category
            ON document_sources (category)
        """))

        