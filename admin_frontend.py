import httpx
import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="花小狮 - 知识库管理",
    page_icon="🦁",
    layout="wide"
)

API_BASE_URL = "http://localhost:8000"


def human_size(size_in_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} TB"


def format_datetime(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return dt_str


st.sidebar.title("🦁 花小狮知识库管理")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "导航菜单",
    ["📊 概览", "📁 文档管理", "⬆️ 上传文档"]
)

st.title("花小狮知识库管理后台")


if page == "📊 概览":
    st.header("知识库统计")
    
    try:
        response = httpx.get(f"{API_BASE_URL}/knowledge/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("文档总数", stats.get("total_sources", 0))
            
            with col2:
                st.metric("知识块总数", stats.get("total_chunks", 0))
            
            with col3:
                categories = stats.get("category_counts", {})
                category_count = len(categories)
                st.metric("文档分类数", category_count)
            
            st.subheader("分类统计")
            if categories:
                cat_df = [{"分类": k, "数量": v} for k, v in categories.items()]
                st.table(cat_df)
            else:
                st.info("暂无分类数据")
        else:
            st.error("获取统计数据失败")
    except Exception as e:
        st.error(f"无法连接到后端服务: {str(e)}")


elif page == "📁 文档管理":
    st.header("文档管理")
    
    try:
        response = httpx.get(f"{API_BASE_URL}/knowledge/documents", timeout=10)
        if response.status_code == 200:
            docs = response.json().get("documents", [])
            
            if docs:
                for doc in docs:
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                        
                        with col1:
                            st.subheader(doc.get("file_name", "未知"))
                            if doc.get("description"):
                                st.caption(doc.get("description"))
                            st.caption(f"分类: {doc.get('category', '未知')}")
                        
                        with col2:
                            st.metric("大小", human_size(doc.get("file_size", 0)))
                        
                        with col3:
                            st.metric("知识块", doc.get("chunk_count", 0))
                        
                        with col4:
                            st.caption(f"上传时间: {format_datetime(doc.get('upload_time', ''))}")
                        
                        with col5:
                            if st.button(f"删除 🗑️", key=f"del_{doc.get('id')}", type="secondary"):
                                delete_response = httpx.delete(
                                    f"{API_BASE_URL}/knowledge/documents/{doc.get('id')}",
                                    timeout=10
                                )
                                if delete_response.status_code == 200:
                                    st.success("文档删除成功!")
                                    st.rerun()
                                else:
                                    st.error("文档删除失败")
                        
                        st.divider()
            else:
                st.info("知识库中暂无文档，快去上传吧!")
        else:
            st.error("获取文档列表失败")
    except Exception as e:
        st.error(f"无法连接到后端服务: {str(e)}")


elif page == "⬆️ 上传文档":
    st.header("上传文档")
    
    st.markdown("""
    支持的文件格式:
    - PDF 文件 (.pdf)
    - Markdown 文件 (.md, .markdown)
    
    ⚠️ 提示：大文件上传和处理可能需要较长时间，请耐心等待
    """)
    
    uploaded_file = st.file_uploader(
        "选择要上传的文档",
        type=["pdf", "md", "markdown"]
    )
    
    description = st.text_area("文档描述 (可选)", placeholder="简要描述这个文档的内容...")
    
    if uploaded_file is not None:
        st.info(f"已选择: {uploaded_file.name} ({human_size(uploaded_file.size)})")
        
        if st.button("上传并处理文档", type="primary"):
            try:
                with st.spinner("正在上传和处理文档，请稍候..."):
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    data = {}
                    if description:
                        data["description"] = description
                    
                    timeout_time = 120 if uploaded_file.size > 1 * 1024 * 1024 else 60
                    
                    response = httpx.post(
                        f"{API_BASE_URL}/knowledge/upload",
                        files=files,
                        data=data,
                        timeout=timeout_time
                    )
                    
                    if response.status_code == 201:
                        result = response.json()
                        st.success(f"✅ 文档上传成功! 文档ID: {result.get('document_id')}")
                        st.balloons()
                    elif response.status_code == 400:
                        error_detail = response.json().get("detail", "请求错误")
                        st.error(f"❌ 请求错误: {error_detail}")
                    elif response.status_code == 500:
                        error_detail = response.json().get("detail", "服务器错误")
                        st.error(f"❌ 服务器处理失败: {error_detail}")
                    else:
                        st.error(f"❌ 上传失败，状态码: {response.status_code}")
            except httpx.TimeoutException:
                st.error("⏱️ 上传超时！文档处理时间过长，请尝试上传较小的文件或稍后重试")
            except httpx.ConnectError:
                st.error("🔌 连接失败！请检查后端服务是否正常运行")
            except Exception as e:
                st.error(f"❌ 上传过程出错: {str(e)}")


st.sidebar.markdown("---")
st.sidebar.markdown("Powered by LeoPals 🦁")
