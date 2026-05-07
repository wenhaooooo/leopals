import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

import pytesseract
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class ImageService:
    def __init__(self):
        self.supported_formats = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]

    async def extract_text(self, image_path: str) -> str:
        """使用OCR从图片中提取文本"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._extract_text_sync, image_path)

    def _extract_text_sync(self, image_path: str) -> str:
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            return text.strip()
        except Exception as e:
            logger.error(f"OCR识别失败: {str(e)}")
            raise

    async def parse_course_schedule(self, image_path: str) -> Dict[str, Any]:
        """从课程表图片中解析结构化数据"""
        text = await self.extract_text(image_path)
        return self._parse_course_text(text)

    def _parse_course_text(self, text: str) -> Dict[str, Any]:
        """解析课程表文本，提取结构化信息"""
        result = {
            "raw_text": text,
            "courses": [],
            "week_info": "",
            "semester": ""
        }

        lines = text.split('\n')
        current_day = None
        course_patterns = ['节', '课', '周', '一', '二', '三', '四', '五', '六', '日']

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if '周' in line and ('第' in line or '星期' in line):
                result["week_info"] = line

            if '学期' in line:
                result["semester"] = line

            day_mapping = {'一': '周一', '二': '周二', '三': '周三', '四': '周四', '五': '周五', '六': '周六', '日': '周日'}
            for day_char, day_name in day_mapping.items():
                if day_char in line and len(line) <= 5:
                    current_day = day_name
                    break

            if current_day and any(p in line for p in course_patterns):
                course_info = {
                    "day": current_day,
                    "raw_content": line
                }
                result["courses"].append(course_info)

        return result

    async def analyze_drawing(self, image_path: str) -> Dict[str, Any]:
        """分析手绘示意图，提取特征点"""
        text = await self.extract_text(image_path)
        
        result = {
            "raw_text": text,
            "type": "unknown",
            "features": [],
            "locations": []
        }

        keywords = {
            "map": ["地图", "平面图", "路线", "位置", "教学楼", "图书馆", "食堂", "宿舍"],
            "schedule": ["课程", "课表", "时间", "节", "周"],
            "notes": ["笔记", "记录", "重点", "公式", "定理"]
        }

        for doc_type, type_keywords in keywords.items():
            if any(kw in text for kw in type_keywords):
                result["type"] = doc_type
                break

        location_keywords = ["教学楼", "图书馆", "食堂", "宿舍", "操场", "体育馆", "实验楼", "行政楼"]
        for loc in location_keywords:
            if loc in text:
                result["locations"].append(loc)

        return result

    def is_supported_format(self, filename: str) -> bool:
        """检查文件格式是否支持"""
        ext = Path(filename).suffix.lower()
        return ext in self.supported_formats