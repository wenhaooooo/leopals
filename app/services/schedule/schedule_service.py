import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.document import CourseSchedule, Reminder, CalendarEvent

logger = logging.getLogger(__name__)


class ScheduleService:
    def __init__(self):
        pass

    async def sync_course_schedule(self, student_id: str, courses: List[Dict[str, Any]]) -> int:
        """同步课程表（模拟从教务系统拉取）"""
        async with AsyncSessionLocal() as db:
            await db.execute(delete(CourseSchedule).where(CourseSchedule.student_id == student_id))
            
            count = 0
            for course in courses:
                day_of_week = course.get("day_of_week")
                if not isinstance(day_of_week, int) or day_of_week < 1 or day_of_week > 7:
                    continue
                
                start_time = self._parse_time(course.get("start_time", "08:00"))
                end_time = self._parse_time(course.get("end_time", "09:40"))
                
                if not start_time or not end_time:
                    continue
                
                db_course = CourseSchedule(
                    student_id=student_id,
                    course_name=course.get("course_name", ""),
                    teacher_name=course.get("teacher_name"),
                    location=course.get("location"),
                    day_of_week=day_of_week,
                    start_time=start_time,
                    end_time=end_time,
                    week_start=course.get("week_start"),
                    week_end=course.get("week_end"),
                    week_list=course.get("week_list"),
                    semester=course.get("semester", "2024-2025-2")
                )
                db.add(db_course)
                count += 1
            
            await db.commit()
            logger.info(f"Synchronized {count} courses for student {student_id}")
            return count

    def _parse_time(self, time_str: str) -> Optional[time]:
        """解析时间字符串"""
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            try:
                return datetime.strptime(time_str, "%H:%M:%S").time()
            except ValueError:
                return None

    async def get_course_schedule(self, student_id: str, week_num: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取课程表"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(CourseSchedule).where(CourseSchedule.student_id == student_id))
            courses = result.scalars().all()
            
            result = []
            for course in courses:
                if week_num is not None:
                    if not self._is_in_week(course, week_num):
                        continue
                
                result.append({
                    "id": course.id,
                    "course_name": course.course_name,
                    "teacher_name": course.teacher_name,
                    "location": course.location,
                    "day_of_week": course.day_of_week,
                    "start_time": course.start_time.strftime("%H:%M"),
                    "end_time": course.end_time.strftime("%H:%M"),
                    "week_start": course.week_start,
                    "week_end": course.week_end,
                    "week_list": course.week_list,
                    "semester": course.semester
                })
            
            return sorted(result, key=lambda x: (x["day_of_week"], x["start_time"]))

    def _is_in_week(self, course: CourseSchedule, week_num: int) -> bool:
        """检查课程是否在指定周"""
        if course.week_list:
            week_list = self._parse_week_list(course.week_list)
            return week_num in week_list
        
        if course.week_start is not None and course.week_end is not None:
            return course.week_start <= week_num <= course.week_end
        
        return True

    def _parse_week_list(self, week_str: str) -> List[int]:
        """解析周次列表字符串"""
        result = []
        parts = week_str.split(",")
        for part in parts:
            if "-" in part:
                start, end = part.split("-")
                result.extend(range(int(start), int(end) + 1))
            else:
                result.append(int(part))
        return result

    async def add_reminder(self, student_id: str, reminder: Dict[str, Any]) -> int:
        """添加提醒"""
        async with AsyncSessionLocal() as db:
            reminder_time = datetime.fromisoformat(reminder["reminder_time"])
            
            db_reminder = Reminder(
                student_id=student_id,
                title=reminder.get("title", ""),
                description=reminder.get("description"),
                reminder_time=reminder_time,
                type=reminder.get("type", "event"),
                course_id=reminder.get("course_id")
            )
            db.add(db_reminder)
            await db.commit()
            await db.refresh(db_reminder)
            
            logger.info(f"Added reminder {db_reminder.id} for student {student_id}")
            return db_reminder.id

    async def get_pending_reminders(self, student_id: str) -> List[Dict[str, Any]]:
        """获取待处理的提醒"""
        async with AsyncSessionLocal() as db:
            now = datetime.now()
            result = await db.execute(
                select(Reminder)
                .where(Reminder.student_id == student_id)
                .where(Reminder.status == "pending")
                .where(Reminder.reminder_time >= now)
                .order_by(Reminder.reminder_time)
            )
            reminders = result.scalars().all()
            
            return [{
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "reminder_time": r.reminder_time.isoformat(),
                "type": r.type,
                "status": r.status,
                "course_id": r.course_id
            } for r in reminders]

    async def complete_reminder(self, reminder_id: int) -> bool:
        """标记提醒为已完成"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
            reminder = result.scalar_one_or_none()
            
            if not reminder:
                return False
            
            reminder.status = "completed"
            await db.commit()
            return True

    async def add_event(self, student_id: str, event: Dict[str, Any]) -> int:
        """添加日程事件"""
        async with AsyncSessionLocal() as db:
            start_time = datetime.fromisoformat(event["start_time"])
            end_time = datetime.fromisoformat(event["end_time"])
            
            db_event = CalendarEvent(
                student_id=student_id,
                title=event.get("title", ""),
                description=event.get("description"),
                start_time=start_time,
                end_time=end_time,
                location=event.get("location"),
                type=event.get("type", "personal"),
                color=event.get("color", "#667eea")
            )
            db.add(db_event)
            await db.commit()
            await db.refresh(db_event)
            
            logger.info(f"Added event {db_event.id} for student {student_id}")
            return db_event.id

    async def get_events(self, student_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取日程事件"""
        async with AsyncSessionLocal() as db:
            query = select(CalendarEvent).where(CalendarEvent.student_id == student_id)
            
            if start_date:
                start_dt = datetime.fromisoformat(start_date)
                query = query.where(CalendarEvent.start_time >= start_dt)
            
            if end_date:
                end_dt = datetime.fromisoformat(end_date)
                query = query.where(CalendarEvent.end_time <= end_dt)
            
            result = await db.execute(query.order_by(CalendarEvent.start_time))
            events = result.scalars().all()
            
            return [{
                "id": e.id,
                "title": e.title,
                "description": e.description,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat(),
                "location": e.location,
                "type": e.type,
                "color": e.color
            } for e in events]

    async def check_conflicts(self, student_id: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """检测时间冲突"""
        conflicts = []
        
        course_conflicts = await self._check_course_conflicts(student_id, start_time, end_time)
        conflicts.extend(course_conflicts)
        
        event_conflicts = await self._check_event_conflicts(student_id, start_time, end_time)
        conflicts.extend(event_conflicts)
        
        return conflicts

    async def _check_course_conflicts(self, student_id: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """检测与课程的冲突"""
        day_of_week = start_time.isoweekday()
        current_time = start_time.time()
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(CourseSchedule)
                .where(CourseSchedule.student_id == student_id)
                .where(CourseSchedule.day_of_week == day_of_week)
            )
            courses = result.scalars().all()
            
            conflicts = []
            for course in courses:
                if (course.start_time <= current_time <= course.end_time or
                    course.start_time <= end_time.time() <= course.end_time):
                    conflicts.append({
                        "type": "course",
                        "title": course.course_name,
                        "location": course.location,
                        "start_time": start_time.replace(
                            hour=course.start_time.hour,
                            minute=course.start_time.minute
                        ).isoformat(),
                        "end_time": start_time.replace(
                            hour=course.end_time.hour,
                            minute=course.end_time.minute
                        ).isoformat()
                    })
            
            return conflicts

    async def _check_event_conflicts(self, student_id: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """检测与已有事件的冲突"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(CalendarEvent)
                .where(CalendarEvent.student_id == student_id)
                .where(CalendarEvent.start_time < end_time)
                .where(CalendarEvent.end_time > start_time)
            )
            events = result.scalars().all()
            
            return [{
                "type": "event",
                "title": e.title,
                "location": e.location,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat()
            } for e in events]

    async def get_today_schedule(self, student_id: str) -> Dict[str, Any]:
        """获取今日日程"""
        today = datetime.now().date()
        start_time = datetime.combine(today, time.min)
        end_time = datetime.combine(today, time.max)
        
        courses = await self.get_course_schedule(student_id)
        today_courses = [c for c in courses if c["day_of_week"] == datetime.now().isoweekday()]
        
        events = await self.get_events(student_id, start_time.isoformat(), end_time.isoformat())
        
        reminders = await self.get_pending_reminders(student_id)
        today_reminders = [r for r in reminders if datetime.fromisoformat(r["reminder_time"]).date() == today]
        
        return {
            "courses": today_courses,
            "events": events,
            "reminders": today_reminders
        }

    async def generate_suggestions(self, student_id: str) -> List[Dict[str, Any]]:
        """生成日程建议"""
        suggestions = []
        
        pending_reminders = await self.get_pending_reminders(student_id)
        upcoming_reminders = [r for r in pending_reminders 
                              if (datetime.fromisoformat(r["reminder_time"]) - datetime.now()).days <= 3]
        
        if upcoming_reminders:
            suggestions.append({
                "type": "reminder",
                "message": f"您有 {len(upcoming_reminders)} 个即将到来的任务需要完成",
                "data": upcoming_reminders
            })
        
        today_schedule = await self.get_today_schedule(student_id)
        if not today_schedule["courses"] and not today_schedule["events"]:
            suggestions.append({
                "type": "empty",
                "message": "今天没有课程和活动安排，可以适当休息一下！"
            })
        
        return suggestions