import httpx
import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="花小狮 - AI树洞",
    page_icon="🌳",
    layout="wide"
)

API_BASE_URL = "http://localhost:8000"

TAG_COLORS = {
    "学习压力": "#FF6B6B",
    "情感问题": "#FF8E72",
    "人际关系": "#FFD93D",
    "家庭问题": "#6BCB77",
    "未来迷茫": "#4D96FF",
    "身体不适": "#9B59B6",
    "其他": "#95A5A6"
}


def main():
    st.title("🌳 花小狮 - AI树洞")
    st.markdown("---")
    
    if 'anonymous_id' not in st.session_state:
        st.session_state.anonymous_id = None
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        show_post_list()
    
    with col2:
        show_sidebar()


def show_post_list():
    search_keyword = st.text_input("搜索树洞", placeholder="输入关键词搜索...")
    
    if search_keyword:
        try:
            response = httpx.get(f"{API_BASE_URL}/treehole/search?keyword={search_keyword}", timeout=10)
            if response.status_code == 200:
                posts = response.json()["posts"]
                display_posts(posts)
        except Exception as e:
            st.error(f"搜索失败: {str(e)}")
    else:
        try:
            response = httpx.get(f"{API_BASE_URL}/treehole/posts", timeout=10)
            if response.status_code == 200:
                posts = response.json()["posts"]
                display_posts(posts)
        except Exception as e:
            st.error(f"获取帖子失败: {str(e)}")


def display_posts(posts):
    if not posts:
        st.info("树洞里还没有心事，来发布第一条吧~")
        return
    
    for post in posts:
        with st.container():
            col_left, col_right = st.columns([10, 1])
            
            with col_left:
                st.markdown(f"""
                <div style='background:#f8f9fa;border-radius:12px;padding:16px;margin-bottom:12px;'>
                    <p style='font-size:16px;color:#333;'>{post['content']}</p>
                    <div style='margin-top:10px;'>
                        {''.join([f'<span style="background:{TAG_COLORS.get(tag, "#ccc")};color:white;padding:2px 8px;border-radius:12px;font-size:12px;margin-right:4px;">{tag}</span>' for tag in post['tags']])}
                    </div>
                    <div style='margin-top:10px;color:#666;font-size:14px;'>
                        <span>📅 {format_time(post['created_at'])}</span>
                        <span style='margin-left:12px;'>💬 {post['reply_count']}</span>
                        <span style='margin-left:12px;'>❤️ {post['like_count']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"查看详情 ❯", key=f"detail_{post['id']}"):
                    st.session_state.selected_post = post['id']
                    show_post_detail(post['id'])
            
            with col_right:
                if st.button("❤️", key=f"like_{post['id']}", help="点赞"):
                    try:
                        httpx.post(f"{API_BASE_URL}/treehole/post/{post['id']}/like", timeout=10)
                        st.success("感谢你的温暖 ❤️")
                    except Exception as e:
                        st.error("点赞失败")


def show_post_detail(post_id):
    try:
        response = httpx.get(f"{API_BASE_URL}/treehole/post/{post_id}", timeout=10)
        if response.status_code == 200:
            post = response.json()
            
            st.subheader("🌳 树洞详情")
            st.markdown(f"""
            <div style='background:#f8f9fa;border-radius:12px;padding:20px;'>
                <p style='font-size:18px;color:#333;line-height:1.8;'>{post['content']}</p>
                <div style='margin-top:12px;'>
                    {''.join([f'<span style="background:{TAG_COLORS.get(tag, "#ccc")};color:white;padding:3px 10px;border-radius:12px;font-size:12px;margin-right:6px;">{tag}</span>' for tag in post['tags']])}
                </div>
                <div style='margin-top:12px;color:#666;font-size:14px;'>
                    <span>📅 {format_time(post['created_at'])}</span>
                    <span style='margin-left:12px;'>👁️ {post['view_count']}</span>
                    <span style='margin-left:12px;'>💬 {post['reply_count']}</span>
                    <span style='margin-left:12px;'>❤️ {post['like_count']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if post['matched_posts']:
                st.subheader("✨ 相似经历")
                for matched in post['matched_posts']:
                    st.markdown(f"""
                    <div style='background:#fff3e0;border-radius:8px;padding:12px;margin-bottom:8px;border-left:4px solid #ff9800;'>
                        <p style='font-size:14px;color:#333;'>{matched['content']}</p>
                        <p style='font-size:12px;color:#ff9800;margin-top:4px;'>相似度: {int(matched['similarity_score'] * 100)}%</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.subheader("💬 评论区")
            for comment in post['comments']:
                ai_badge = "🤖 AI助手" if comment['is_ai_reply'] else ""
                st.markdown(f"""
                <div style='background:#fff;border-radius:8px;padding:12px;margin-bottom:8px;border:1px solid #eee;'>
                    <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>
                        <span style='font-weight:bold;color:#333;'>{ai_badge if ai_badge else '匿名用户'}</span>
                        <span style='font-size:12px;color:#999;'>{format_time(comment['created_at'])}</span>
                    </div>
                    <p style='font-size:14px;color:#333;'>{comment['content']}</p>
                    <div style='margin-top:8px;'>
                        <button style='background:none;border:none;color:#ff6b6b;font-size:14px;cursor:pointer;' onclick="likeComment({comment['id']})">
                            ❤️ {comment['like_count']}
                        </button>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            comment_content = st.text_area("写下你的安慰...")
            if st.button("发送评论"):
                if comment_content:
                    try:
                        response = httpx.post(
                            f"{API_BASE_URL}/treehole/comment",
                            json={
                                "post_id": post_id,
                                "content": comment_content,
                                "anonymous_id": st.session_state.anonymous_id
                            },
                            timeout=10
                        )
                        if response.status_code == 201:
                            st.success("评论成功！你的温暖已传递 ❤️")
                        else:
                            st.error("评论失败")
                    except Exception as e:
                        st.error(f"评论失败: {str(e)}")
                else:
                    st.warning("请输入评论内容")
    
    except Exception as e:
        st.error(f"获取详情失败: {str(e)}")


def show_sidebar():
    st.subheader("📝 发布心事")
    
    content = st.text_area("说出你的心事，这里没有人认识你...", height=150)
    
    if st.button("🌳 匿名发布", type="primary"):
        if content:
            try:
                response = httpx.post(
                    f"{API_BASE_URL}/treehole/post",
                    json={
                        "content": content,
                        "anonymous_id": st.session_state.anonymous_id
                    },
                    timeout=10
                )
                if response.status_code == 201:
                    st.success("发布成功！你的心事已被树洞接收 🌳")
                    st.balloons()
                    if not st.session_state.anonymous_id:
                        st.session_state.anonymous_id = response.json().get('anonymous_id')
                else:
                    st.error("发布失败")
            except Exception as e:
                st.error(f"发布失败: {str(e)}")
        else:
            st.warning("请输入内容")
    
    st.markdown("---")
    
    try:
        response = httpx.get(f"{API_BASE_URL}/treehole/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            st.subheader("📊 树洞统计")
            st.metric("帖子数", stats["post_count"])
            st.metric("评论数", stats["comment_count"])
            st.metric("用户数", stats["user_count"])
    except Exception as e:
        pass
    
    st.markdown("---")
    st.subheader("🔒 隐私保护")
    st.markdown("""
    - 完全匿名，不记录真实身份
    - 所有数据加密存储
    - 随时可以离开，不留痕迹
    """)


def format_time(time_str):
    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    now = datetime.now(dt.tzinfo)
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}天前"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600}小时前"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60}分钟前"
    else:
        return "刚刚"


if __name__ == "__main__":
    main()