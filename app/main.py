from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db
from app.api.routes import router as chat_router, kb_router
from app.api.multimodal_routes import router as multimodal_router
from app.api.schedule_routes import router as schedule_router
from app.api.treehole_routes import router as treehole_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description="LeoPals - 高校垂直领域智能服务平台",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(kb_router)
app.include_router(multimodal_router)
app.include_router(schedule_router)
app.include_router(treehole_router)


@app.get("/", tags=["Health Check"])
async def root():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Welcome to {settings.app_name}", "status": "running"}
    )


@app.get("/health", tags=["Health Check"], summary="健康检查接口")
async def health_check():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": settings.app_name,
            "environment": settings.app_env,
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
        log_level=settings.log_level.lower()
    )