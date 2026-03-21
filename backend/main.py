from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.test import router as test_router
from routes.settings import router as settings_router
from routes.chat import router as chat_router
from routes.agent import router as agent_router
from routes.history import router as history_router

app = FastAPI(title="Liquidation Guard API", version="0.1.0")

# 允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://liquidation-guard.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(test_router, prefix="/test", tags=["测试连接"])
app.include_router(settings_router, prefix="/settings", tags=["用户设置"])
app.include_router(chat_router, prefix="/chat", tags=["对话历史"])
app.include_router(agent_router, prefix="/agent", tags=["AI Agent"])
app.include_router(history_router, prefix="/history", tags=["健康历史"])


@app.get("/health")
def health():
    return {"status": "ok"}
