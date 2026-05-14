import logging
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.core.config import settings

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_api_base,
    model_name=settings.llm_model_name,
    temperature=0.6,
    max_tokens=500,
)


class EmotionalAgent:
    """
    情感智能体：提供情感支持和心理陪伴
    
    核心能力：
    - 情感分析
    - 共情回应
    - 心理支持
    - 匿名倾诉
    """
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理情感支持请求
        
        Args:
            query: 用户查询内容
            context: 上下文信息
        
        Returns:
            {"result": "共情回应", "confidence": 置信度}
        """
        logger.info(f"情感智能体处理请求: {query}")
        
        # 1. 情感分析
        emotion = await self._analyze_emotion(query)
        logger.debug(f"情感分析结果: {emotion}")
        
        # 2. 生成共情回应
        response = await self._generate_empathy_response(query, emotion)
        
        return {"result": response, "confidence": 0.85}
    
    async def _analyze_emotion(self, query: str) -> Dict[str, Any]:
        """分析用户的情感状态"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            你是一个情感分析专家。请分析用户的情感状态：
            
            用户输入：{text}
            
            请输出JSON格式：
            {{
                "emotion": "情感类型（如：sad, happy, angry, anxious, lonely, neutral）",
                "intensity": 强度（0-1）,
                "needs": ["用户可能的需求，如：安慰、倾听、建议、鼓励"]
            }}
            """),
            ("user", "")
        ])
        
        chain = prompt | llm | JsonOutputParser()
        
        try:
            result = await chain.ainvoke({"text": query})
            return result
        except Exception as e:
            logger.error(f"情感分析失败: {str(e)}")
            return {
                "emotion": "neutral",
                "intensity": 0.5,
                "needs": ["倾听"]
            }
    
    async def _generate_empathy_response(self, query: str, emotion: Dict[str, Any]) -> str:
        """生成共情回应"""
        emotion_type = emotion.get("emotion", "neutral")
        intensity = emotion.get("intensity", 0.5)
        needs = emotion.get("needs", ["倾听"])
        
        # 根据情感类型选择回应风格
        style = self._get_response_style(emotion_type, intensity)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""
            你是一只温暖可爱的小狮子助手。用户现在感觉{emotion_type}（强度：{intensity}），可能需要{', '.join(needs)}。
            
            请用{style}的语气回应，使用适当的表情符号，让用户感受到被理解和关心。
            """),
            ("user", query)
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({})
        
        return response.content
    
    def _get_response_style(self, emotion: str, intensity: float) -> str:
        """根据情感类型和强度选择回应风格"""
        style_map = {
            "sad": "温柔安慰",
            "happy": "开心祝福",
            "angry": "冷静倾听",
            "anxious": "安抚鼓励",
            "lonely": "温暖陪伴",
            "neutral": "友好自然"
        }
        
        base_style = style_map.get(emotion, "友好自然")
        
        # 根据强度调整风格
        if intensity > 0.7:
            return f"非常{base_style}"
        elif intensity > 0.4:
            return base_style
        else:
            return f"适度{base_style}"