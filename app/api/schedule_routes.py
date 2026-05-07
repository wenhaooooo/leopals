import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Body, File, UploadFile
from fastapi.responses import JSONResponse

from app.services.schedule.schedule_service import ScheduleService
from app.services.multimodal.image_service import ImageService

router = APIRouter(prefix="/schedule", tags=["Schedule Management"])

schedule_service = ScheduleService()
image_service = ImageService()


@router.post("/courses/sync", summary="同步课程表")
async def sync_courses(
    student_id: str = Body(..., embed=True),
    courses: List[Dict[str, Any]] = Body(..., embed=True)
):
    try:
        count = await schedule_service.sync_course_schedule(student_id, courses)
        return JSONResponse(
            status_code=200,
            content={"message": "课程表同步成功", "count": count}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/courses", summary="获取课程表")
async def get_courses(student_id: str, week_num: Optional[int] = None):
    try:
        courses = await schedule_service.get_course_schedule(student_id, week_num)
        return {"courses": courses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/reminders", summary="添加提醒")
async def add_reminder(
    student_id: str = Body(..., embed=True),
    title: str = Body(..., embed=True),
    description: Optional[str] = Body(None, embed=True),
    reminder_time: str = Body(..., embed=True),
    type: str = Body("event", embed=True),
    course_id: Optional[int] = Body(None, embed=True)
):
    try:
        reminder_id = await schedule_service.add_reminder(student_id, {
            "title": title,
            "description": description,
            "reminder_time": reminder_time,
            "type": type,
            "course_id": course_id
        })
        return JSONResponse(
            status_code=201,
            content={"message": "提醒添加成功", "reminder_id": reminder_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@router.get("/reminders", summary="获取待处理提醒")
async def get_reminders(student_id: str):
    try:
        reminders = await schedule_service.get_pending_reminders(student_id)
        return {"reminders": reminders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.put("/reminders/{reminder_id}/complete", summary="标记提醒已完成")
async def complete_reminder(reminder_id: int):
    try:
        success = await schedule_service.complete_reminder(reminder_id)
        if not success:
            raise HTTPException(status_code=404, detail="提醒不存在")
        return {"message": "提醒已标记为完成"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.post("/events", summary="添加日程事件")
async def add_event(
    student_id: str = Body(..., embed=True),
    title: str = Body(..., embed=True),
    description: Optional[str] = Body(None, embed=True),
    start_time: str = Body(..., embed=True),
    end_time: str = Body(..., embed=True),
    location: Optional[str] = Body(None, embed=True),
    type: str = Body("personal", embed=True),
    color: str = Body("#667eea", embed=True)
):
    try:
        event_id = await schedule_service.add_event(student_id, {
            "title": title,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "type": type,
            "color": color
        })
        return JSONResponse(
            status_code=201,
            content={"message": "事件添加成功", "event_id": event_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@router.get("/events", summary="获取日程事件")
async def get_events(student_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    try:
        events = await schedule_service.get_events(student_id, start_date, end_date)
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/conflicts/check", summary="检测时间冲突")
async def check_conflicts(
    student_id: str = Body(..., embed=True),
    start_time: str = Body(..., embed=True),
    end_time: str = Body(..., embed=True)
):
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        
        conflicts = await schedule_service.check_conflicts(student_id, start_dt, end_dt)
        return {"conflicts": conflicts, "has_conflict": len(conflicts) > 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.get("/today", summary="获取今日日程")
async def get_today_schedule(student_id: str):
    try:
        schedule = await schedule_service.get_today_schedule(student_id)
        return schedule
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.get("/suggestions", summary="获取日程建议")
async def get_suggestions(student_id: str):
    try:
        suggestions = await schedule_service.generate_suggestions(student_id)
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.get("/mock/courses", summary="获取模拟课程数据")
async def get_mock_courses():
    mock_courses = [
        {
            "course_name": "高等数学",
            "teacher_name": "王教授",
            "location": "教学楼A-301",
            "day_of_week": 1,
            "start_time": "08:00",
            "end_time": "09:40",
            "week_start": 1,
            "week_end": 16,
            "semester": "2024-2025-2"
        },
        {
            "course_name": "大学英语",
            "teacher_name": "李老师",
            "location": "教学楼B-205",
            "day_of_week": 2,
            "start_time": "10:00",
            "end_time": "11:40",
            "week_start": 1,
            "week_end": 16,
            "semester": "2024-2025-2"
        },
        {
            "course_name": "数据结构",
            "teacher_name": "张教授",
            "location": "计算机楼-401",
            "day_of_week": 3,
            "start_time": "14:00",
            "end_time": "15:40",
            "week_list": "1,3,5,7,9,11,13,15",
            "semester": "2024-2025-2"
        },
        {
            "course_name": "操作系统",
            "teacher_name": "刘教授",
            "location": "计算机楼-401",
            "day_of_week": 4,
            "start_time": "08:00",
            "end_time": "09:40",
            "week_list": "2,4,6,8,10,12,14,16",
            "semester": "2024-2025-2"
        },
        {
            "course_name": "人工智能导论",
            "teacher_name": "陈教授",
            "location": "计算机楼-502",
            "day_of_week": 5,
            "start_time": "14:00",
            "end_time": "16:30",
            "week_start": 1,
            "week_end": 16,
            "semester": "2024-2025-2"
        }
    ]
    return {"courses": mock_courses}


@router.post("/courses/upload", summary="上传课程表图片并解析创建日程")
async def upload_course_schedule(
    student_id: str = Body(..., embed=True),
    file: UploadFile = File(...),
    semester: str = Body("2024-2025-2", embed=True)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    if not image_service.is_supported_format(file.filename):
        raise HTTPException(status_code=400, detail="不支持的图片格式")

    upload_dir = Path("uploads/images")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = await image_service.parse_course_schedule(str(file_path))
        
        courses = result.get("courses", [])
        parsed_courses = []
        
        for course in courses:
            parsed_course = await parse_course_info(course, semester)
            if parsed_course:
                parsed_courses.append(parsed_course)
        
        if parsed_courses:
            count = await schedule_service.sync_course_schedule(student_id, parsed_courses)
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": "课程表解析并导入成功",
                    "count": count,
                    "parsed_courses": parsed_courses,
                    "raw_text": result.get("raw_text", "")
                }
            )
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "message": "未识别到课程信息",
                    "raw_text": result.get("raw_text", ""),
                    "suggestion": "请确保图片清晰，包含课程名称、时间等信息"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")
    finally:
        if file_path.exists():
            os.remove(file_path)


async def parse_course_info(course: Dict[str, Any], semester: str) -> Optional[Dict[str, Any]]:
    """解析课程信息"""
    day_mapping = {
        '周一': 1, '周二': 2, '周三': 3, '周四': 4, '周五': 5, '周六': 6, '周日': 7,
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '日': 7
    }
    
    day_of_week = None
    day = course.get("day", "")
    
    for key, value in day_mapping.items():
        if key in day:
            day_of_week = value
            break
    
    if day_of_week is None:
        return None
    
    content = course.get("raw_content", "")
    
    course_name = extract_course_name(content)
    teacher_name = extract_teacher_name(content)
    location = extract_location(content)
    time_info = extract_time_info(content)
    
    if not course_name:
        course_name = "未知课程"
    
    return {
        "course_name": course_name,
        "teacher_name": teacher_name,
        "location": location,
        "day_of_week": day_of_week,
        "start_time": time_info.get("start_time", "08:00"),
        "end_time": time_info.get("end_time", "09:40"),
        "week_start": 1,
        "week_end": 16,
        "semester": semester
    }


def extract_course_name(content: str) -> str:
    """从文本中提取课程名称"""
    keywords_to_remove = ['节', '周', '一', '二', '三', '四', '五', '六', '日', '上午', '下午', '晚上']
    name = content
    
    for keyword in keywords_to_remove:
        name = name.replace(keyword, '')
    
    name = name.strip()
    
    if len(name) > 0 and not name.isdigit():
        return name
    return ""


def extract_teacher_name(content: str) -> Optional[str]:
    """从文本中提取教师姓名"""
    if '老师' in content:
        parts = content.split('老师')
        if len(parts) > 0:
            prefix = parts[0][-3:] if len(parts[0]) > 3 else parts[0]
            return f"{prefix.strip()}老师"
    return None


def extract_location(content: str) -> Optional[str]:
    """从文本中提取上课地点"""
    import re
    patterns = [
        r'([A-Za-z]楼[\d]+-[A-Za-z0-9]+)',
        r'([A-Za-z]楼[\d]+室)',
        r'(教学楼[\d]+-[A-Za-z0-9]+)',
        r'(实验楼[\d]+-[A-Za-z0-9]+)',
        r'([\d]+-[A-Za-z0-9]+)',
        r'([\d]+楼[\d]+室)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    return None


def extract_time_info(content: str) -> Dict[str, str]:
    """从文本中提取时间信息"""
    import re
    
    period_patterns = {
        '1': ('08:00', '08:45'),
        '2': ('08:55', '09:40'),
        '3': ('10:00', '10:45'),
        '4': ('10:55', '11:40'),
        '5': ('14:00', '14:45'),
        '6': ('14:55', '15:40'),
        '7': ('16:00', '16:45'),
        '8': ('16:55', '17:40'),
        '9': ('19:00', '19:45'),
        '10': ('19:55', '20:40'),
    }
    
    match = re.search(r'(\d+)节', content)
    if match:
        period = match.group(1)
        if period in period_patterns:
            return {
                "start_time": period_patterns[period][0],
                "end_time": period_patterns[period][1]
            }
    
    match = re.search(r'(\d+):(\d+)-(\d+):(\d+)', content)
    if match:
        return {
            "start_time": f"{match.group(1)}:{match.group(2)}",
            "end_time": f"{match.group(3)}:{match.group(4)}"
        }
    
    return {"start_time": "08:00", "end_time": "09:40"}
