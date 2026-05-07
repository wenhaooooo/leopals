import httpx
import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(
    page_title="花小狮 - 智能日程管理",
    page_icon="🦁",
    layout="wide"
)

API_BASE_URL = "http://localhost:8000"

DAY_NAMES = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def format_time(time_str: str) -> str:
    return time_str[:5]


def get_week_number() -> int:
    today = datetime.now()
    start_of_semester = datetime(2024, 9, 2)
    delta = today - start_of_semester
    week_num = delta.days // 7 + 1
    return max(1, min(week_num, 20))


def main():
    st.title("🦁 花小狮 - 智能日程管理")
    st.markdown("---")

    st.sidebar.title("导航")
    page = st.sidebar.radio(
        "功能菜单",
        ["📅 今日日程", "📚 课程表", "🔔 提醒管理", "➕ 添加事件", "⚠️ 冲突检测"]
    )

    student_id = st.sidebar.text_input("学号", value="20240001")

    if page == "📅 今日日程":
        show_today_schedule(student_id)

    elif page == "📚 课程表":
        show_course_schedule(student_id)

    elif page == "🔔 提醒管理":
        show_reminder_management(student_id)

    elif page == "➕ 添加事件":
        show_add_event(student_id)

    elif page == "⚠️ 冲突检测":
        show_conflict_check(student_id)


def show_today_schedule(student_id: str):
    st.header("今日日程概览")

    try:
        response = httpx.get(f"{API_BASE_URL}/schedule/today?student_id={student_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("今日课程", len(data.get("courses", [])))
            with col2:
                st.metric("今日活动", len(data.get("events", [])))
            with col3:
                st.metric("待办提醒", len(data.get("reminders", [])))

            if data.get("courses"):
                st.subheader("📚 今日课程")
                for course in data["courses"]:
                    with st.container():
                        st.markdown(f"**{course['course_name']}**")
                        st.caption(f"{DAY_NAMES[course['day_of_week']]} {format_time(course['start_time'])} - {format_time(course['end_time'])}")
                        st.caption(f"地点: {course.get('location', '未指定')}")
                        st.caption(f"教师: {course.get('teacher_name', '未指定')}")
                        st.divider()

            if data.get("events"):
                st.subheader("📅 今日活动")
                for event in data["events"]:
                    with st.container():
                        st.markdown(f"**{event['title']}**")
                        start_dt = datetime.fromisoformat(event["start_time"])
                        end_dt = datetime.fromisoformat(event["end_time"])
                        st.caption(f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}")
                        if event.get("location"):
                            st.caption(f"地点: {event['location']}")
                        st.divider()

            if data.get("reminders"):
                st.subheader("🔔 待办提醒")
                for reminder in data["reminders"]:
                    with st.container():
                        st.markdown(f"**{reminder['title']}**")
                        remind_dt = datetime.fromisoformat(reminder["reminder_time"])
                        st.caption(f"提醒时间: {remind_dt.strftime('%H:%M')}")
                        if reminder.get("description"):
                            st.caption(f"描述: {reminder['description']}")
                        if st.button(f"已完成 ✓", key=f"remind_done_{reminder['id']}"):
                            response = httpx.put(f"{API_BASE_URL}/schedule/reminders/{reminder['id']}/complete", timeout=10)
                            if response.status_code == 200:
                                st.success("已标记完成!")
                                st.rerun()
                        st.divider()

            if not data.get("courses") and not data.get("events") and not data.get("reminders"):
                st.info("今天没有安排，可以好好休息一下！")

        else:
            st.error("获取今日日程失败")
    except Exception as e:
        st.error(f"无法连接到后端服务: {str(e)}")


def show_course_schedule(student_id: str):
    st.header("课程表")

    current_week = get_week_number()
    week_num = st.number_input("周次", min_value=1, max_value=20, value=current_week)

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("同步课程表"):
            try:
                response = httpx.get(f"{API_BASE_URL}/schedule/mock/courses", timeout=10)
                if response.status_code == 200:
                    courses = response.json()["courses"]
                    sync_response = httpx.post(
                        f"{API_BASE_URL}/schedule/courses/sync",
                        json={"student_id": student_id, "courses": courses},
                        timeout=10
                    )
                    if sync_response.status_code == 200:
                        st.success(f"成功同步 {sync_response.json()['count']} 门课程")
                    else:
                        st.error("同步失败")
            except Exception as e:
                st.error(f"同步失败: {str(e)}")
    
    with col2:
        uploaded_file = st.file_uploader("上传课程表图片", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        if uploaded_file is not None:
            with st.spinner("正在解析课程表..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    data = {"student_id": student_id, "semester": "2024-2025-2"}
                    
                    response = httpx.post(
                        f"{API_BASE_URL}/schedule/courses/upload",
                        files=files,
                        data=data,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("count", 0) > 0:
                            st.success(f"成功解析并导入 {result['count']} 门课程!")
                            st.info(f"识别到的课程: {', '.join(c['course_name'] for c in result.get('parsed_courses', []))}")
                        else:
                            st.warning("未识别到课程信息，请确保图片清晰")
                    else:
                        st.error(f"解析失败: {response.json().get('detail', '未知错误')}")
                except Exception as e:
                    st.error(f"上传失败: {str(e)}")

    try:
        response = httpx.get(f"{API_BASE_URL}/schedule/courses?student_id={student_id}&week_num={week_num}", timeout=10)
        if response.status_code == 200:
            courses = response.json().get("courses", [])
            
            if courses:
                day_courses = {i: [] for i in range(1, 8)}
                for course in courses:
                    day_courses[course["day_of_week"]].append(course)

                time_slots = [
                    ("08:00", "09:40"),
                    ("10:00", "11:40"),
                    ("14:00", "15:40"),
                    ("16:00", "17:40"),
                    ("19:00", "20:40")
                ]

                for time_idx, (start, end) in enumerate(time_slots):
                    cols = st.columns(8)
                    with cols[0]:
                        st.write(f"**{start}-{end}**")
                    for day in range(1, 8):
                        with cols[day]:
                            day_courses_list = day_courses.get(day, [])
                            found = False
                            for course in day_courses_list:
                                if course["start_time"].startswith(start[:2]):
                                    st.markdown(f"<div style='background:#667eea;color:white;padding:8px;border-radius:8px;font-size:12px;'>{course['course_name']}</div>", unsafe_allow_html=True)
                                    st.write(f"<span style='font-size:10px;'>{course.get('location', '')}</span>", unsafe_allow_html=True)
                                    found = True
                            if not found:
                                st.write("")
            else:
                st.info("暂无课程数据，请先同步课程表")
        else:
            st.error("获取课程表失败")
    except Exception as e:
        st.error(f"无法连接到后端服务: {str(e)}")


def show_reminder_management(student_id: str):
    st.header("提醒管理")

    with st.form("add_reminder_form"):
        title = st.text_input("提醒标题")
        description = st.text_area("描述")
        reminder_time = st.datetime_input("提醒时间")
        reminder_type = st.selectbox("类型", ["homework", "exam", "event", "deadline"])
        
        if st.form_submit_button("添加提醒"):
            if title and reminder_time:
                try:
                    response = httpx.post(
                        f"{API_BASE_URL}/schedule/reminders",
                        json={
                            "student_id": student_id,
                            "title": title,
                            "description": description,
                            "reminder_time": reminder_time.isoformat(),
                            "type": reminder_type
                        },
                        timeout=10
                    )
                    if response.status_code == 201:
                        st.success("提醒添加成功!")
                    else:
                        st.error("添加失败")
                except Exception as e:
                    st.error(f"添加失败: {str(e)}")
            else:
                st.warning("请填写标题和时间")

    st.subheader("待处理提醒")
    try:
        response = httpx.get(f"{API_BASE_URL}/schedule/reminders?student_id={student_id}", timeout=10)
        if response.status_code == 200:
            reminders = response.json().get("reminders", [])
            for reminder in reminders:
                with st.container():
                    st.markdown(f"**{reminder['title']}**")
                    remind_dt = datetime.fromisoformat(reminder["reminder_time"])
                    st.caption(f"时间: {remind_dt.strftime('%Y-%m-%d %H:%M')}")
                    st.caption(f"类型: {reminder['type']}")
                    if reminder.get("description"):
                        st.caption(f"描述: {reminder['description']}")
                    if st.button(f"已完成 ✓", key=f"rem_done_{reminder['id']}"):
                        httpx.put(f"{API_BASE_URL}/schedule/reminders/{reminder['id']}/complete", timeout=10)
                        st.success("已标记完成!")
                        st.rerun()
                    st.divider()
        else:
            st.error("获取提醒失败")
    except Exception as e:
        st.error(f"无法连接到后端服务: {str(e)}")


def show_add_event(student_id: str):
    st.header("添加日程事件")

    with st.form("add_event_form"):
        title = st.text_input("事件标题")
        description = st.text_area("描述")
        start_time = st.datetime_input("开始时间")
        end_time = st.datetime_input("结束时间")
        location = st.text_input("地点")
        event_type = st.selectbox("类型", ["course", "exam", "homework", "meeting", "personal"])
        color = st.color_picker("颜色", "#667eea")
        
        if st.form_submit_button("添加事件"):
            if title and start_time and end_time:
                if end_time <= start_time:
                    st.warning("结束时间必须晚于开始时间")
                else:
                    try:
                        response = httpx.post(
                            f"{API_BASE_URL}/schedule/events",
                            json={
                                "student_id": student_id,
                                "title": title,
                                "description": description,
                                "start_time": start_time.isoformat(),
                                "end_time": end_time.isoformat(),
                                "location": location,
                                "type": event_type,
                                "color": color
                            },
                            timeout=10
                        )
                        if response.status_code == 201:
                            st.success("事件添加成功!")
                        else:
                            st.error("添加失败")
                    except Exception as e:
                        st.error(f"添加失败: {str(e)}")
            else:
                st.warning("请填写标题和时间")


def show_conflict_check(student_id: str):
    st.header("时间冲突检测")

    with st.form("conflict_form"):
        start_time = st.datetime_input("开始时间")
        end_time = st.datetime_input("结束时间")
        
        if st.form_submit_button("检测冲突"):
            if start_time and end_time:
                try:
                    response = httpx.post(
                        f"{API_BASE_URL}/schedule/conflicts/check",
                        json={
                            "student_id": student_id,
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat()
                        },
                        timeout=10
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if result["has_conflict"]:
                            st.error("⚠️ 检测到时间冲突!")
                            for conflict in result["conflicts"]:
                                st.markdown(f"**{conflict['type']}: {conflict['title']}**")
                                st.caption(f"时间: {conflict['start_time']} - {conflict['end_time']}")
                                if conflict.get("location"):
                                    st.caption(f"地点: {conflict['location']}")
                                st.divider()
                        else:
                            st.success("✅ 该时间段没有冲突，可以安排!")
                    else:
                        st.error("检测失败")
                except Exception as e:
                    st.error(f"检测失败: {str(e)}")
            else:
                st.warning("请填写时间")

    st.subheader("日程建议")
    try:
        response = httpx.get(f"{API_BASE_URL}/schedule/suggestions?student_id={student_id}", timeout=10)
        if response.status_code == 200:
            suggestions = response.json().get("suggestions", [])
            for suggestion in suggestions:
                st.info(suggestion["message"])
        else:
            st.error("获取建议失败")
    except Exception as e:
        st.error(f"无法连接到后端服务: {str(e)}")


if __name__ == "__main__":
    main()