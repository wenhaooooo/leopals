from sqlalchemy import Column, Integer, String, JSON, Index, DateTime, Text, ForeignKey, Time, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.core.database import Base
from app.core.config import settings


class DocumentSource(Base):
    __tablename__ = "document_sources"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False, index=True)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    chunk_count = Column(Integer, default=0)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(Text, nullable=True)
    status = Column(String, default="processed")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    embedding = Column(Vector(settings.embedding_dimension))
    doc_metadata = Column(JSONB, default={})
    chunk_index = Column(Integer, nullable=False, default=0)
    source_file = Column(String, nullable=True)
    category = Column(String, nullable=True)
    document_source_id = Column(Integer, nullable=True, index=True)
    version = Column(Integer, default=1)

    __table_args__ = (
        Index(
            "ix_document_chunks_embedding",
            embedding,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_source_id = Column(Integer, nullable=True, index=True)
    version_number = Column(Integer, default=1)
    content_hash = Column(String(64))
    file_size = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)


class CourseSchedule(Base):
    __tablename__ = "course_schedules"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, nullable=False, index=True)
    course_name = Column(String, nullable=False)
    teacher_name = Column(String, nullable=True)
    location = Column(String, nullable=True)
    day_of_week = Column(Integer, nullable=False)  # 1-7 (周一到周日)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    week_start = Column(Integer, nullable=True)
    week_end = Column(Integer, nullable=True)
    week_list = Column(String, nullable=True)  # 如 "1,3,5,7-12"
    semester = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    reminder_time = Column(DateTime(timezone=True), nullable=False)
    type = Column(String, nullable=False)  # homework, exam, event, deadline
    status = Column(String, default="pending")  # pending, completed, dismissed
    course_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String, nullable=True)
    type = Column(String, nullable=False)  # course, exam, homework, meeting, personal
    color = Column(String, default="#667eea")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())