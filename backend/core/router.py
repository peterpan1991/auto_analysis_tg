from fastapi import FastAPI
from api.v1 import tasks, chat, analysis, extract, vectorize

def register_routers(app: FastAPI):
    app.include_router(tasks.router, prefix="/api/v1", tags=["任务管理"])
    app.include_router(chat.router, prefix="/api/v1", tags=["聊天记录"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["分析结果"])
    app.include_router(extract.router, prefix="/api/v1", tags=["提取信息"])
    app.include_router(vectorize.router, prefix="/api/v1", tags=["向量化与AI对话"])
