from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse

from app.services.treehole.treehole_service import TreeHoleService

router = APIRouter(prefix="/treehole", tags=["Tree Hole"])

treehole_service = TreeHoleService()


@router.post("/post", summary="发布树洞帖子")
async def create_post(
    content: str = Body(..., embed=True),
    anonymous_id: Optional[str] = Body(None, embed=True)
):
    try:
        post_id = await treehole_service.create_post(content, anonymous_id)
        return JSONResponse(
            status_code=201,
            content={"message": "发布成功", "post_id": post_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发布失败: {str(e)}")


@router.get("/posts", summary="获取帖子列表")
async def get_posts(page: int = 1, page_size: int = 10):
    try:
        posts = await treehole_service.get_posts(page, page_size)
        return {"posts": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.get("/post/{post_id}", summary="获取单个帖子")
async def get_post(post_id: int):
    try:
        post = await treehole_service.get_post(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        return post
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/comment", summary="添加评论")
async def add_comment(
    post_id: int = Body(..., embed=True),
    content: str = Body(..., embed=True),
    anonymous_id: Optional[str] = Body(None, embed=True)
):
    try:
        comment_id = await treehole_service.add_comment(post_id, content, anonymous_id)
        return JSONResponse(
            status_code=201,
            content={"message": "评论成功", "comment_id": comment_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评论失败: {str(e)}")


@router.post("/post/{post_id}/like", summary="点赞帖子")
async def like_post(post_id: int):
    try:
        await treehole_service.like_post(post_id)
        return {"message": "点赞成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"点赞失败: {str(e)}")


@router.post("/comment/{comment_id}/like", summary="点赞评论")
async def like_comment(comment_id: int):
    try:
        await treehole_service.like_comment(comment_id)
        return {"message": "点赞成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"点赞失败: {str(e)}")


@router.get("/search", summary="搜索帖子")
async def search_posts(keyword: str):
    try:
        posts = await treehole_service.search_posts(keyword)
        return {"posts": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/post/{post_id}/matches", summary="获取相似帖子")
async def get_matched_posts(post_id: int):
    try:
        posts = await treehole_service.get_matched_posts(post_id)
        return {"posts": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.get("/stats", summary="获取统计信息")
async def get_stats():
    try:
        stats = await treehole_service.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/user", summary="创建/获取用户")
async def create_user(anonymous_id: Optional[str] = Body(None, embed=True)):
    try:
        user_id = await treehole_service.create_user(anonymous_id)
        return {"anonymous_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")
