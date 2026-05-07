import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.treehole import TreeHolePost, TreeHoleComment, TreeHoleMatch, TreeHoleUser

logger = logging.getLogger(__name__)

# 预设的AI安慰回复模板
AI_REPLIES = [
    "我理解你的感受，有时候生活确实会让人感到疲惫。但请相信，每个困难都是成长的机会，你已经做得很好了！",
    "听到你这么说，我也感到很难过。但请记住，你不是一个人，我们都在这里支持你。",
    "有时候倾诉本身就是一种释放。把心里的事说出来，已经很勇敢了。",
    "人生总会有起起落落，现在的困难只是暂时的。相信自己，你一定能渡过难关！",
    "你的感受是真实的，也是值得被理解的。不要压抑自己，好好照顾自己。",
    "我知道现在很难，但请给自己一些时间和耐心。一切都会好起来的。",
    "你已经很努力了，不要对自己太苛刻。休息一下，明天又是新的一天。",
    "无论发生什么，都请记住：你是独一无二的，你的存在本身就有价值。",
    "有时候我们需要的不是答案，而是有人愿意倾听。我在这里，听你倾诉。",
    "风雨过后总会有彩虹，坚持下去，光明就在前方。"
]

# 情感标签分类
EMOTION_TAGS = {
    "学习压力": ["考试", "作业", "论文", "成绩", "考研", "复习", "挂科"],
    "情感问题": ["失恋", "暗恋", "表白", "分手", "恋爱", "喜欢"],
    "人际关系": ["室友", "同学", "朋友", "矛盾", "孤独", "社交"],
    "家庭问题": ["父母", "家人", "亲情", "代沟"],
    "未来迷茫": ["工作", "前途", "方向", "选择", "迷茫"],
    "身体不适": ["生病", "失眠", "压力", "焦虑", "抑郁"],
    "其他": []
}


class TreeHoleService:
    def __init__(self):
        pass

    def generate_anonymous_id(self) -> str:
        """生成匿名ID"""
        return f"anonymous_{uuid.uuid4().hex[:8]}"

    def analyze_tags(self, content: str) -> List[str]:
        """分析内容，自动生成标签"""
        tags = []
        for tag, keywords in EMOTION_TAGS.items():
            for keyword in keywords:
                if keyword in content:
                    tags.append(tag)
                    break
        if not tags:
            tags.append("其他")
        return tags

    def analyze_sentiment(self, content: str) -> float:
        """简单的情感分析（正向返回正数，负向返回负数）"""
        positive_words = ["开心", "高兴", "快乐", "幸福", "顺利", "成功", "好", "棒", "赞"]
        negative_words = ["难过", "伤心", "失望", "痛苦", "焦虑", "迷茫", "压力", "累", "烦"]
        
        score = 0
        for word in positive_words:
            score += content.count(word) * 0.5
        for word in negative_words:
            score -= content.count(word) * 0.5
        
        return min(max(score, -5.0), 5.0)

    async def create_user(self, anonymous_id: Optional[str] = None) -> str:
        """创建或获取用户"""
        if not anonymous_id:
            anonymous_id = self.generate_anonymous_id()
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(TreeHoleUser).where(TreeHoleUser.anonymous_id == anonymous_id))
            user = result.scalar_one_or_none()
            
            if not user:
                user = TreeHoleUser(
                    anonymous_id=anonymous_id,
                    nickname=f"树洞用户{anonymous_id[-4:]}",
                    avatar=f"https://api.dicebear.com/7.x/avataaars/svg?seed={anonymous_id}"
                )
                db.add(user)
                await db.commit()
        
        return anonymous_id

    async def create_post(self, content: str, anonymous_id: Optional[str] = None) -> int:
        """发布树洞帖子"""
        if not anonymous_id:
            anonymous_id = self.generate_anonymous_id()
        
        await self.create_user(anonymous_id)
        
        tags = self.analyze_tags(content)
        sentiment = self.analyze_sentiment(content)
        
        async with AsyncSessionLocal() as db:
            post = TreeHolePost(
                anonymous_id=anonymous_id,
                content=content,
                tags=tags,
                sentiment_score=sentiment,
                is_anonymous="yes"
            )
            db.add(post)
            await db.commit()
            await db.refresh(post)
            
            user = await db.execute(select(TreeHoleUser).where(TreeHoleUser.anonymous_id == anonymous_id))
            user = user.scalar_one_or_none()
            if user:
                user.post_count += 1
                await db.commit()
        
        await self._generate_ai_reply(post.id)
        await self._find_matching_posts(post.id)
        
        return post.id

    async def _generate_ai_reply(self, post_id: int):
        """自动生成AI安慰回复"""
        await asyncio.sleep(1)
        
        async with AsyncSessionLocal() as db:
            post = await db.execute(select(TreeHolePost).where(TreeHolePost.id == post_id))
            post = post.scalar_one_or_none()
            
            if not post:
                return
            
            import random
            ai_reply = random.choice(AI_REPLIES)
            
            comment = TreeHoleComment(
                post_id=post_id,
                anonymous_id="AI_assistant",
                content=ai_reply,
                is_ai_reply="yes"
            )
            db.add(comment)
            await db.commit()
            
            post.reply_count += 1
            await db.commit()

    async def _find_matching_posts(self, post_id: int):
        """寻找相似经历的帖子"""
        async with AsyncSessionLocal() as db:
            post = await db.execute(select(TreeHolePost).where(TreeHolePost.id == post_id))
            post = post.scalar_one_or_none()
            
            if not post or not post.tags:
                return
            
            posts = await db.execute(
                select(TreeHolePost)
                .where(TreeHolePost.id != post_id)
                .order_by(desc(TreeHolePost.created_at))
                .limit(20)
            )
            posts = posts.scalars().all()
            
            matched_posts = []
            for other_post in posts:
                if other_post.tags:
                    common_tags = set(post.tags) & set(other_post.tags)
                    similarity = len(common_tags) / max(len(post.tags), len(other_post.tags))
                    if similarity > 0.3:
                        matched_posts.append((other_post.id, similarity))
            
            matched_posts.sort(key=lambda x: -x[1])
            
            for matched_id, score in matched_posts[:3]:
                match = TreeHoleMatch(
                    post_id=post_id,
                    matched_post_id=matched_id,
                    similarity_score=score
                )
                db.add(match)
            
            await db.commit()

    async def get_posts(self, page: int = 1, page_size: int = 10) -> List[Dict[str, Any]]:
        """获取帖子列表"""
        async with AsyncSessionLocal() as db:
            offset = (page - 1) * page_size
            result = await db.execute(
                select(TreeHolePost)
                .order_by(desc(TreeHolePost.created_at))
                .offset(offset)
                .limit(page_size)
            )
            posts = result.scalars().all()
            
            return [{
                "id": p.id,
                "content": p.content,
                "tags": p.tags,
                "sentiment_score": p.sentiment_score,
                "created_at": p.created_at.isoformat(),
                "reply_count": p.reply_count,
                "like_count": p.like_count,
                "view_count": p.view_count
            } for p in posts]

    async def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """获取单个帖子"""
        async with AsyncSessionLocal() as db:
            post = await db.execute(select(TreeHolePost).where(TreeHolePost.id == post_id))
            post = post.scalar_one_or_none()
            
            if not post:
                return None
            
            post.view_count += 1
            await db.commit()
            
            comments = await db.execute(
                select(TreeHoleComment)
                .where(TreeHoleComment.post_id == post_id)
                .order_by(TreeHoleComment.created_at)
            )
            comments = comments.scalars().all()
            
            matches = await db.execute(
                select(TreeHoleMatch)
                .where(TreeHoleMatch.post_id == post_id)
                .order_by(desc(TreeHoleMatch.similarity_score))
            )
            matches = matches.scalars().all()
            
            matched_posts = []
            for match in matches[:3]:
                matched_post = await db.execute(select(TreeHolePost).where(TreeHolePost.id == match.matched_post_id))
                matched_post = matched_post.scalar_one_or_none()
                if matched_post:
                    matched_posts.append({
                        "id": matched_post.id,
                        "content": matched_post.content[:50] + "..." if len(matched_post.content) > 50 else matched_post.content,
                        "similarity_score": match.similarity_score
                    })
            
            return {
                "id": post.id,
                "content": post.content,
                "tags": post.tags,
                "sentiment_score": post.sentiment_score,
                "created_at": post.created_at.isoformat(),
                "reply_count": post.reply_count,
                "like_count": post.like_count,
                "view_count": post.view_count,
                "comments": [{
                    "id": c.id,
                    "content": c.content,
                    "is_ai_reply": c.is_ai_reply == "yes",
                    "created_at": c.created_at.isoformat(),
                    "like_count": c.like_count
                } for c in comments],
                "matched_posts": matched_posts
            }

    async def add_comment(self, post_id: int, content: str, anonymous_id: Optional[str] = None) -> int:
        """添加评论"""
        if not anonymous_id:
            anonymous_id = self.generate_anonymous_id()
        
        await self.create_user(anonymous_id)
        
        async with AsyncSessionLocal() as db:
            comment = TreeHoleComment(
                post_id=post_id,
                anonymous_id=anonymous_id,
                content=content,
                is_ai_reply="no"
            )
            db.add(comment)
            
            post = await db.execute(select(TreeHolePost).where(TreeHolePost.id == post_id))
            post = post.scalar_one_or_none()
            if post:
                post.reply_count += 1
            
            await db.commit()
            await db.refresh(comment)
            
            user = await db.execute(select(TreeHoleUser).where(TreeHoleUser.anonymous_id == anonymous_id))
            user = user.scalar_one_or_none()
            if user:
                user.comment_count += 1
                await db.commit()
        
        return comment.id

    async def like_post(self, post_id: int):
        """点赞帖子"""
        async with AsyncSessionLocal() as db:
            post = await db.execute(select(TreeHolePost).where(TreeHolePost.id == post_id))
            post = post.scalar_one_or_none()
            
            if post:
                post.like_count += 1
                await db.commit()

    async def like_comment(self, comment_id: int):
        """点赞评论"""
        async with AsyncSessionLocal() as db:
            comment = await db.execute(select(TreeHoleComment).where(TreeHoleComment.id == comment_id))
            comment = comment.scalar_one_or_none()
            
            if comment:
                comment.like_count += 1
                await db.commit()

    async def search_posts(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索帖子"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TreeHolePost)
                .where(TreeHolePost.content.ilike(f"%{keyword}%"))
                .order_by(desc(TreeHolePost.created_at))
                .limit(20)
            )
            posts = result.scalars().all()
            
            return [{
                "id": p.id,
                "content": p.content,
                "tags": p.tags,
                "created_at": p.created_at.isoformat(),
                "reply_count": p.reply_count,
                "like_count": p.like_count
            } for p in posts]

    async def get_matched_posts(self, post_id: int) -> List[Dict[str, Any]]:
        """获取相似匹配的帖子"""
        async with AsyncSessionLocal() as db:
            matches = await db.execute(
                select(TreeHoleMatch)
                .where(TreeHoleMatch.post_id == post_id)
                .order_by(desc(TreeHoleMatch.similarity_score))
                .limit(5)
            )
            matches = matches.scalars().all()
            
            result = []
            for match in matches:
                post = await db.execute(select(TreeHolePost).where(TreeHolePost.id == match.matched_post_id))
                post = post.scalar_one_or_none()
                if post:
                    result.append({
                        "id": post.id,
                        "content": post.content,
                        "tags": post.tags,
                        "similarity_score": match.similarity_score,
                        "created_at": post.created_at.isoformat()
                    })
            
            return result

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        async with AsyncSessionLocal() as db:
            post_count = await db.execute(select(TreeHolePost).count())
            comment_count = await db.execute(select(TreeHoleComment).count())
            user_count = await db.execute(select(TreeHoleUser).count())
            
            return {
                "post_count": post_count.scalar_one(),
                "comment_count": comment_count.scalar_one(),
                "user_count": user_count.scalar_one()
            }
