"""
routers/chat.py —— AI 聊天接口

前端把用户输入 POST 到 /api/chat，这里调用智能体主循环，
把最终回复 + 工具执行记录一起返回。
"""
from fastapi import APIRouter, HTTPException

from app.agent import llm, runner
from app.models import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["AI 聊天"])


@router.post("")
def chat(body: ChatRequest):
    if not llm.is_configured():
        raise HTTPException(
            status_code=503,
            detail="还没配置智谱 API key：请把 backend/.env.example 复制为 backend/.env，填入你的 key 后重启后端",
        )
    try:
        return runner.run_agent(body.message)
    except Exception as e:  # 网络超时、模型服务报错等都兜到这里
        raise HTTPException(status_code=500, detail=f"智能体调用失败：{e}")
