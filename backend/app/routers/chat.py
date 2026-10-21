"""
routers/chat.py —— AI 聊天接口（普通版 + SSE 流式版）

【知识点：SSE（Server-Sent Events，服务器推送事件）】
一种 HTTP 长连接协议：响应头是 text/event-stream，服务器可以源源不断地
往连接里写"事件块"，浏览器逐块接收。每个事件块长这样：

    event: delta
    data: {"text": "已记下"}

（空行分隔多个事件块）

对比普通接口"攒齐了再一次性返回"，SSE 让用户看到 AI 边想边说。
前端不用 axios（它拿不到逐段数据），用原生 fetch 读响应流（见 Chat.vue）。
"""
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agent import llm, runner
from app.models import ChatRequest

logger = logging.getLogger("agent")

router = APIRouter(prefix="/api/chat", tags=["AI 聊天"])


@router.post("")
def chat(body: ChatRequest):
    """普通版：攒齐了一次性返回（方便 curl 测试）。前端实际用的是下面的流式版。"""
    if not llm.is_configured():
        raise HTTPException(
            status_code=503,
            detail="还没配置智谱 API key：请把 backend/.env.example 复制为 backend/.env，填入你的 key 后重启后端",
        )
    try:
        return runner.run_agent(body.message, body.history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能体调用失败：{e}")


@router.post("/stream")
async def chat_stream(body: ChatRequest):
    """流式版（SSE）：智能体的每一步实时推给前端。"""
    if not llm.is_configured():
        raise HTTPException(
            status_code=503,
            detail="还没配置智谱 API key：请把 backend/.env.example 复制为 backend/.env，填入你的 key 后重启后端",
        )

    def event_stream():
        try:
            for event, payload in runner.run_agent_stream(body.message, body.history):
                yield f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("流式对话出错")  # exception() 会把堆栈也打进日志，排查必备
            yield "event: error\ndata: " + json.dumps({"detail": f"智能体调用失败：{e}"}, ensure_ascii=False) + "\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # 告诉 nginx 别缓冲这个响应：SSE 要一条条实时到达，攒齐了再发就失去意义了
            "X-Accel-Buffering": "no",
        },
    )
