"""
成绩查询技能实现
"""

from pydantic import Field

from app.services.skills.base import BaseSkill, SkillInput, SkillOutput, SkillContext


class GetGradeInput(SkillInput):
    """查询成绩输入参数"""
    semester: str = Field(..., description="学期，格式如'2024-2025-1'")


class GradeSkill(BaseSkill):
    """
    成绩查询技能
    
    查询指定学期的成绩信息
    """
    
    name = "grade_query"
    description = "查询学生成绩信息，包括GPA、绩点和课程明细"
    version = "1.0.0"
    category = "academic"
    
    def __init__(self):
        super().__init__()
        self._mock_grades = {
            "2024-2025-1": {
                "gpa": 3.75,
                "total_credits": 24,
                "courses": [
                    {"name": "高等数学A", "credit": 4, "grade": 92, "point": 4.0},
                    {"name": "大学英语", "credit": 3, "grade": 85, "point": 3.7},
                    {"name": "计算机基础", "credit": 3, "grade": 88, "point": 3.7},
                    {"name": "软件工程", "credit": 4, "grade": 90, "point": 4.0},
                    {"name": "体育", "credit": 2, "grade": 95, "point": 4.0},
                    {"name": "思想政治", "credit": 2, "grade": 82, "point": 3.3},
                ]
            }
        }
    
    async def execute(
        self,
        input: GetGradeInput,
        context: Optional[SkillContext] = None
    ) -> SkillOutput:
        """执行成绩查询"""
        semester = input.semester
        
        if semester not in self._mock_grades:
            return SkillOutput(
                success=False,
                error=f"未找到 {semester} 学期的成绩数据"
            )
        
        data = self._mock_grades[semester]
        
        distribution = self._calculate_distribution(data["courses"])
        
        result = {
            "semester": semester,
            "gpa": data["gpa"],
            "total_credits": data["total_credits"],
            "courses": data["courses"],
            "distribution": distribution
        }
        
        return SkillOutput(
            success=True,
            data=result,
            metadata={"message": f"查询到 {len(data['courses'])} 门课程成绩"}
        )
    
    def _calculate_distribution(self, courses):
        """计算成绩分布"""
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        
        for course in courses:
            if course["grade"] >= 90:
                distribution["A"] += 1
            elif course["grade"] >= 80:
                distribution["B"] += 1
            elif course["grade"] >= 70:
                distribution["C"] += 1
            elif course["grade"] >= 60:
                distribution["D"] += 1
            else:
                distribution["F"] += 1
        
        return distribution