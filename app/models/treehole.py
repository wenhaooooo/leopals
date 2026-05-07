from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class TreeHolePost(Base):
    __tablename__ = "treehole_posts"

    id = Column(Integer, primary_key=True, index=True)
    anonymous_id = Column(String, nullable=False, index=True)  # 匿名ID，不存储真实身份
    content = Column(Text, nullable=False)
    tags = Column(JSONB, nullable=True)  # 标签：学习压力、情感问题、人际关系等
    sentiment_score = Column(Float, nullable=True)  # 情感分数
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_anonymous = Column(String, default="yes")  # 是否匿名
    reply_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)


class TreeHoleComment(Base):
    __tablename__ = "treehole_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, nullable=False, index=True)
    anonymous_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    is_ai_reply = Column(String, default="no")  # 是否是AI回复
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    like_count = Column(Integer, default=0)


class TreeHoleMatch(Base):
    __tablename__ = "treehole_matches"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, nullable=False, index=True)
    matched_post_id = Column(Integer, nullable=False, index=True)
    similarity_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TreeHoleUser(Base):
    __tablename__ = "treehole_users"

    id = Column(Integer, primary_key=True, index=True)
    anonymous_id = Column(String, nullable=False, unique=True, index=True)
    nickname = Column(String, nullable=True)  # 可选昵称
    avatar = Column(String, nullable=True)  # 头像URL或emoji
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    post_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)