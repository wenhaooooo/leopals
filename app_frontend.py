import asyncio
import json
import httpx
import streamlit as st

st.set_page_config(
    page_title="花小狮 - 校园智慧助手",
    page_icon="🦁",
    layout="wide"
)

CUSTOM_CSS = """
<style>
.user-bubble {
    background: #c8f7c5;
    color: #1a1a1a;
    border-radius: 16px 16px 4px 16px;
    padding: 12px 16px;
    margin-bottom: 8px;
    max-width: 70%;
    margin-left: auto;
    font-weight: 500;
}

.assistant-bubble {
    background: #ffffff;
    color: #1a1a1a;
    border-radius: 16px 16px 16px 4px;
    padding: 12px 16px;
    margin-bottom: 8px;
    max-width: 70%;
    border: 1px solid #e0e0e0;
    font-weight: 500;
}

.thought-box {
    background-color: #f0f2f6;
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 8px;
    border-left: 4px solid #667eea;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []


def get_ai_response_sync(prompt: str, user_info: dict = None):
    try:
        with httpx.Client(timeout=60) as client:
            with client.stream(
                "POST",
                "http://localhost:8000/chat/stream",
                json={
                    "query": prompt,
                    "user_info": user_info or {},
                    "session_id": "streamlit_session"
                }
            ) as response:
                event_type = None
                for line in response.iter_lines():
                    if not line:
                        continue

                    if line.startswith("event: "):
                        event_type = line.replace("event: ", "").strip()
                        continue

                    if line.startswith("data: "):
                        data_str = line.replace("data: ", "").strip()
                        try:
                            data = json.loads(data_str)
                            yield (event_type, data)
                        except json.JSONDecodeError:
                            continue

    except httpx.ConnectError:
        yield ("error", {"message": "无法连接到后端服务，请确保 FastAPI 服务已启动"})
    except Exception as e:
        yield ("error", {"message": f"请求失败: {str(e)}"})


def main():
    init_session_state()

    with st.sidebar:
        st.markdown("""
            # 🦁 花小狮

            你的校园智慧小助手！

            我可以帮你：
            - 📅 查询课表和校历
            - 📊 查看成绩和绩点
            - 📚 了解考研政策
            - 💬 闲聊解闷
        """)

        if st.button("🧹 清除对话", type="secondary"):
            st.session_state.messages = []
            st.rerun()

    st.title("🦁 花小狮 - 校园智慧助手")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("校历哪里看？"):
            st.session_state.messages.append({"role": "user", "content": "校历哪里看？"})
            st.rerun()
    with col2:
        if st.button("帮我查一下上学期绩点"):
            st.session_state.messages.append({"role": "user", "content": "帮我查一下上学期绩点"})
            st.rerun()
    with col3:
        if st.button("考研加分政策是什么？"):
            st.session_state.messages.append({"role": "user", "content": "考研加分政策是什么？"})
            st.rerun()

    st.markdown("---")

    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="user-bubble">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="assistant-bubble">{message["content"]}</div>', unsafe_allow_html=True)

    thought_placeholder = st.empty()
    user_input = st.chat_input("有什么可以帮你？")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with chat_container:
            st.markdown(f'<div class="user-bubble">{user_input}</div>', unsafe_allow_html=True)

        with st.spinner("花小狮正在思考..."):
            ai_response = ""
            response_placeholder = st.empty()

            for event_type, data in get_ai_response_sync(user_input):
                if event_type == "error":
                    thought_placeholder.markdown(
                        f'<div class="thought-box">❌ {data.get("message")}</div>',
                        unsafe_allow_html=True
                    )
                    break

                elif event_type == "thought":
                    thought_placeholder.markdown(
                        f'<div class="thought-box">🤔 {data.get("message", "")}</div>',
                        unsafe_allow_html=True
                    )

                elif event_type in ["on_retriever_start", "on_tool_start"]:
                    thought_placeholder.markdown(
                        f'<div class="thought-box">� {data.get("message", "")}</div>',
                        unsafe_allow_html=True
                    )

                elif event_type in ["on_retriever_end", "on_tool_end"]:
                    thought_placeholder.markdown(
                        f'<div class="thought-box">✅ {data.get("message", "")}</div>',
                        unsafe_allow_html=True
                    )

                elif event_type == "on_chat_model_stream":
                    ai_response += data.get("content", "")
                    response_placeholder.markdown(
                        f'<div class="assistant-bubble">{ai_response}</div>',
                        unsafe_allow_html=True
                    )

            thought_placeholder.empty()
            if ai_response:
                st.session_state.messages.append({"role": "assistant", "content": ai_response})


if __name__ == "__main__":
    main()