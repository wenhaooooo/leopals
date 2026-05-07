import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

import httpx
from pydub import AudioSegment

logger = logging.getLogger(__name__)


class AudioService:
    def __init__(self):
        self.supported_formats = [".wav", ".mp3", ".m4a", ".ogg", ".flac"]

    async def speech_to_text(self, audio_path: str) -> str:
        """将语音转换为文本（使用OpenAI Whisper API）"""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                with open(audio_path, "rb") as f:
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        files={"file": (Path(audio_path).name, f, "audio/wav")},
                        data={"model": "whisper-1", "language": "zh"},
                        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}"}
                    )
                
                if response.status_code == 200:
                    return response.json().get("text", "")
                else:
                    logger.error(f"语音识别失败: {response.text}")
                    return ""
        except Exception as e:
            logger.error(f"语音识别异常: {str(e)}")
            return ""

    async def text_to_speech(self, text: str, output_path: str = None) -> str:
        """将文本转换为语音（使用Edge TTS）"""
        try:
            edge_tts = __import__('edge_tts')
            
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoyiNeural")
            
            if output_path is None:
                output_path = f"temp_{hash(text)}.mp3"
            
            await communicate.save(output_path)
            return output_path
        except ImportError:
            logger.error("请安装 edge-tts 库: pip install edge-tts")
            return ""
        except Exception as e:
            logger.error(f"语音合成失败: {str(e)}")
            return ""

    def convert_audio_format(self, input_path: str, output_format: str = "wav") -> str:
        """转换音频格式"""
        try:
            audio = AudioSegment.from_file(input_path)
            output_path = Path(input_path).stem + f".{output_format}"
            audio.export(output_path, format=output_format)
            return output_path
        except Exception as e:
            logger.error(f"音频格式转换失败: {str(e)}")
            return input_path

    def is_supported_format(self, filename: str) -> bool:
        """检查文件格式是否支持"""
        ext = Path(filename).suffix.lower()
        return ext in self.supported_formats

    async def process_audio_input(self, audio_path: str) -> Dict[str, Any]:
        """处理音频输入，返回识别结果"""
        text = await self.speech_to_text(audio_path)
        return {
            "text": text,
            "confidence": 0.9 if text else 0.0
        }

    async def process_audio_output(self, text: str) -> Dict[str, Any]:
        """处理音频输出，返回音频文件路径"""
        audio_path = await self.text_to_speech(text)
        return {
            "audio_path": audio_path,
            "text": text
        }