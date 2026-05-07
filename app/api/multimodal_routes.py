import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse

from app.services.multimodal.image_service import ImageService
from app.services.multimodal.audio_service import AudioService

router = APIRouter(prefix="/multimodal", tags=["Multimodal"])

image_service = ImageService()
audio_service = AudioService()


@router.post("/image/ocr", summary="图片OCR识别")
async def image_ocr(file: UploadFile = File(...)):
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
        text = await image_service.extract_text(str(file_path))
        return JSONResponse(
            status_code=200,
            content={
                "message": "识别成功",
                "text": text
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")
    finally:
        if file_path.exists():
            os.remove(file_path)


@router.post("/image/course-schedule", summary="课程表图片解析")
async def parse_course_schedule(file: UploadFile = File(...)):
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
        return JSONResponse(
            status_code=200,
            content={
                "message": "解析成功",
                **result
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")
    finally:
        if file_path.exists():
            os.remove(file_path)


@router.post("/image/analyze", summary="图片分析（手绘示意图识别）")
async def analyze_image(file: UploadFile = File(...)):
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
        result = await image_service.analyze_drawing(str(file_path))
        return JSONResponse(
            status_code=200,
            content={
                "message": "分析成功",
                **result
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
    finally:
        if file_path.exists():
            os.remove(file_path)


@router.post("/audio/speech-to-text", summary="语音转文字（STT）")
async def speech_to_text(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    if not audio_service.is_supported_format(file.filename):
        raise HTTPException(status_code=400, detail="不支持的音频格式")

    upload_dir = Path("uploads/audio")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = await audio_service.process_audio_input(str(file_path))
        return JSONResponse(
            status_code=200,
            content={
                "message": "识别成功",
                **result
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")
    finally:
        if file_path.exists():
            os.remove(file_path)


@router.post("/audio/text-to-speech", summary="文字转语音（TTS）")
async def text_to_speech(text: str = Form(...)):
    if not text.strip():
        raise HTTPException(status_code=400, detail="文本内容不能为空")

    try:
        result = await audio_service.process_audio_output(text)
        
        audio_path = result.get("audio_path")
        if not audio_path or not os.path.exists(audio_path):
            raise HTTPException(status_code=500, detail="语音合成失败")

        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            filename=f"response.mp3"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合成失败: {str(e)}")
    finally:
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.remove(audio_path)
