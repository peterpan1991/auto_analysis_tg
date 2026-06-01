from fastapi import FastAPI
from core.router import register_routers

app = FastAPI(title="聊天分析系统")

# 挂载路由
register_routers(app)

@app.get("/")
def root():
    return {"message": "运行成功"}