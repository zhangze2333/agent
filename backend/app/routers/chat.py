"""
routers/chat.py —— AI 聊天接口（普通版 + SSE 流式版，均已要求登录）

【v1.0】两个接口都加了 get_current_user 依赖：
- 智能体的工具调用以当前用户身份执行（数据隔离延伸到 AI）
- 未登录请求直接 401，token 过期同样 401
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app import db_models
from app.agent import llm, runner
from app.models import ChatRequest
from app.security import get_current_user

logger = logging.getLogger("agent")

_NO_KEY_MSG = (
    "还没配置智谱 API key：请把 backend/.env.example 复制为 backend/.env，填入你的 key 后重启后端"
)

router = APIRouter(prefix="/api/chat", tags=["AI 聊天"])


@router.post("")
def chat(body: ChatRequest, user: db_models.User = Depends(get_current_user)):
    """普通版：攒齐了一次性返回（方便 curl 测试）。前端实际用的是下面的流式版。"""
    if not llm.is_configured():
        raise HTTPException(status_code=503, detail=_NO_KEY_MSG)
    try:
        return runner.run_agent(body.message, body.history, user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能体调用失败：{e}")


@router.post("/stream")
async def chat_stream(body: ChatRequest, user: db_models.User = Depends(get_current_user)):
    """流式版（SSE）：智能体的每一步实时推给前端。"""
    if not llm.is_configured():
        raise HTTPException(status_code=503, detail=_NO_KEY_MSG)

    def event_stream():
        try:
            for event, payload in runner.run_agent_stream(body.message, body.history, user.id):
                yield f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("流式对话出错")  # exception() 会把堆栈也打进日志，排查必备
            yield (
                "event: error\ndata: "
                + json.dumps({"detail": f"智能体调用失败：{e}"}, ensure_ascii=False)
                + "\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # 告诉 nginx 别缓冲这个响应：SSE 要一条条实时到达，攒齐了再发就失去意义了
            "X-Accel-Buffering": "no",
        },
    )
