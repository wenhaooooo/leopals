"""
技能系统使用示例

展示如何使用动态技能注册系统
"""

import asyncio
from app.services.skills import (
    init_skills,
    get_skill,
    list_skills,
    SkillLoader,
    SkillContext,
    registry
)
from app.services.skills.impls.schedule_skill import GetScheduleInput
from app.services.skills.impls.grade_skill import GetGradeInput
from app.services.skills.impls.classroom_skill import SearchClassroomInput
from app.services.skills.impls.notification_skill import SetReminderInput


async def example_basic_usage():
    """基础使用示例"""
    print("\n" + "="*60)
    print("技能系统基础使用示例")
    print("="*60)
    
    await init_skills()
    
    print("\n📋 所有技能列表:")
    skills = list_skills()
    for skill in skills:
        print(f"  • {skill['name']} ({skill['category']}) - {skill['description']}")
    
    print("\n📊 按类别统计:")
    from app.services.skills.registry import SkillRegistry
    reg = SkillRegistry()
    for category in reg.get_categories():
        count = len(reg.list_by_category(category))
        print(f"  • {category}: {count} 个技能")


async def example_execute_schedule():
    """执行课表查询技能示例"""
    print("\n" + "="*60)
    print("课表查询技能示例")
    print("="*60)
    
    await init_skills()
    
    input_data = GetScheduleInput(week=8, day_of_week=1)
    context = SkillContext(user_id="20240001", session_id="test_session")
    
    result = await registry.execute("schedule_query", input_data, context)
    
    if result.success:
        print(f"\n✅ 查询成功: {result.metadata.get('message')}")
        data = result.data
        print(f"  周次: {data['week']}")
        print(f"  课程数: {data['count']}")
        for course in data['courses']:
            print(f"  • {course['name']}: {course['time']} @ {course['location']}")
    else:
        print(f"\n❌ 查询失败: {result.error}")


async def example_execute_grade():
    """执行成绩查询技能示例"""
    print("\n" + "="*60)
    print("成绩查询技能示例")
    print("="*60)
    
    await init_skills()
    
    input_data = GetGradeInput(semester="2024-2025-1")
    context = SkillContext(user_id="20240001")
    
    result = await registry.execute("grade_query", input_data, context)
    
    if result.success:
        print(f"\n✅ 查询成功: {result.metadata.get('message')}")
        data = result.data
        print(f"  学期: {data['semester']}")
        print(f"  GPA: {data['gpa']}")
        print(f"  总学分: {data['total_credits']}")
        print(f"  等级分布: {data['distribution']}")
    else:
        print(f"\n❌ 查询失败: {result.error}")


async def example_execute_classroom():
    """执行空教室搜索技能示例"""
    print("\n" + "="*60)
    print("空教室搜索技能示例")
    print("="*60)
    
    await init_skills()
    
    input_data = SearchClassroomInput(
        date="2024-03-15",
        start_time="09:00",
        end_time="11:00",
        capacity=50
    )
    context = SkillContext(user_id="20240001")
    
    result = await registry.execute("classroom_search", input_data, context)
    
    if result.success:
        print(f"\n✅ 搜索成功: {result.metadata.get('message')}")
        data = result.data
        print(f"  日期: {data['date']}")
        print(f"  时间: {data['time_range']}")
        print(f"  可用教室数: {data['total']}")
        for room in data['available']:
            print(f"  • {room['building']} {room['room']} (容量: {room['capacity']})")
    else:
        print(f"\n❌ 搜索失败: {result.error}")


async def example_execute_notification():
    """执行通知提醒技能示例"""
    print("\n" + "="*60)
    print("通知提醒技能示例")
    print("="*60)
    
    await init_skills()
    
    from datetime import datetime, timedelta
    remind_time = (datetime.now() + timedelta(hours=2)).isoformat()
    
    input_data = SetReminderInput(
        content="复习高等数学",
        remind_time=remind_time,
        reminder_type="study"
    )
    context = SkillContext(user_id="20240001")
    
    result = await registry.execute("notification_set", input_data, context)
    
    if result.success:
        print(f"\n✅ 提醒设置成功: {result.metadata.get('message')}")
        reminder = result.data['reminder']
        print(f"  内容: {reminder['content']}")
        print(f"  时间: {reminder['remind_time']}")
        print(f"  类型: {reminder['reminder_type']}")
        
        advance = result.data.get('advance_suggestion')
        if advance:
            print(f"  💡 {advance['message']}: {advance['advance_time']}")
    else:
        print(f"\n❌ 设置失败: {result.error}")


async def example_dynamic_loading():
    """动态加载技能示例"""
    print("\n" + "="*60)
    print("动态加载技能示例")
    print("="*60)
    
    loader = SkillLoader()
    
    print("\n📁 从目录加载技能:")
    skills = await loader.load_from_directory()
    print(f"  加载了 {len(skills)} 个技能")
    
    print("\n🔄 热重载技能:")
    if skills:
        skill = skills[0]
        reloaded = await loader.hot_reload(
            "app/services/skills/impls/schedule_skill.py"
        )
        if reloaded:
            print(f"  ✅ 热重载成功: {reloaded.name}")


async def example_skill_management():
    """技能管理示例"""
    print("\n" + "="*60)
    print("技能管理示例")
    print("="*60)
    
    await init_skills()
    
    reg = SkillRegistry()
    
    print("\n🔍 查询技能是否存在:")
    print(f"  schedule_query: {reg.has('schedule_query')}")
    print(f"  unknown_skill: {reg.has('unknown_skill')}")
    
    print("\n⚙️ 禁用/启用技能:")
    reg.disable("schedule_query")
    print(f"  禁用 schedule_query 后: {get_skill('schedule_query').enabled}")
    
    reg.enable("schedule_query")
    print(f"  启用 schedule_query 后: {get_skill('schedule_query').enabled}")
    
    print("\n📊 按类别列出技能:")
    schedule_skills = reg.list_by_category("schedule")
    print(f"  schedule 类别: {len(schedule_skills)} 个技能")
    for skill in schedule_skills:
        print(f"    • {skill['name']}")


async def main():
    """运行所有示例"""
    print("\n" + "="*60)
    print("🦁 LeoPals 技能系统示例")
    print("="*60)
    
    await example_basic_usage()
    await example_execute_schedule()
    await example_execute_grade()
    await example_execute_classroom()
    await example_execute_notification()
    await example_dynamic_loading()
    await example_skill_management()
    
    print("\n" + "="*60)
    print("✅ 所有示例执行完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
