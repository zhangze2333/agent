"""
main.py —— 整个后端的入口

启动方式（在 backend 目录下执行）：
    uvicorn app.main:app --reload --port 8010
    （--port 8010：默认 8000 端口容易被其他项目占用。如果启动报
    "error while attempting to bind ... only one usage of each socket address"，
    就说明端口被占了，换一个数字即可 —— 这是后端开发最常见的报错之一）

启动后：
    http://127.0.0.1:8010/       欢迎信息
    http://127.0.0.1:8010/docs   自动生成的交互式接口文档（FastAPI 的杀手锏）

【知识点：FastAPI 和 uvicorn 的关系】
FastAPI 是 Web 框架（定义"收到什么请求、返回什么响应"），
uvicorn 是服务器软件（真正监听 8010 端口、收发网络包）。
就像"菜谱"和"厨房"的关系。
"""

import logging
from contextlib import asynccontextmanager
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import security
from app.database import init_db
from app.routers import auth, chat, todos

# 【知识点：日志配置】
# 我们采用"双写"方案，同一条日志两处可查：
# ① basicConfig -> 标准输出 -> 被 systemd 收进 journald
#    查看：journalctl -u agent-api -f
# ② 文件处理器 -> backend/logs/agent.log（纯文本，可以直接 tail/grep）
#    查看：tail -f /opt/agent/backend/logs/agent.log
# 路径用 __file__ 拼出绝对路径：无论从哪个目录启动服务，文件都落在同一个地方
_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,  # DEBUG < INFO < WARNING < ERROR，INFO 表示记录一般运行信息
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

# 【知识点：日志切割（rotation）】
# 日志文件会无限增长，撑爆硬盘是生产事故的经典来源。TimedRotatingFileHandler
# 每天零点(when="midnight")把昨天的改名存档（agent.log.2026-10-21），
# backupCount=14 表示最多保留 14 份存档，更老的自动删除。
_file_handler = TimedRotatingFileHandler(
    _LOG_DIR / "agent.log", when="midnight", backupCount=14, encoding="utf-8"
)
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
logging.getLogger("agent").addHandler(_file_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """生命周期钩子：yield 之前的代码在服务启动时执行一次，之后在关闭时执行。"""
    if not security.JWT_SECRET:
        # 学习环境给个临时密钥保证能跑；生产必须配置——密钥泄露 = 任何人可伪造登录
        import os
        import secrets

        os.environ["JWT_SECRET"] = secrets.token_hex(32)
        security.JWT_SECRET = os.environ["JWT_SECRET"]
        logging.getLogger("agent").warning(
            "JWT_SECRET 未配置！已生成临时密钥（重启后所有登录失效）"
        )
    init_db()
    yield


app = FastAPI(
    title="AI 待办助手",
    description="Vue3 + FastAPI + GLM 智能体 学习项目",
    version="0.1.0",
    lifespan=lifespan,
)

# 【知识点：CORS 跨域】
# 浏览器有个安全策略：前端(如 localhost:5174)默认不允许请求另一个域(localhost:8010)，
# 后端必须明确"放行"前端的来源，请求才能通。不加这个中间件，前端会报 CORS 错误。
# 这里用正则放行"任意本地端口"的前端开发服务器（5173/5174/...都算同机调试）。
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

# 把三个路由文件里的接口"挂载"到主应用上
app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {"message": "AI 待办助手后端已启动", "docs": "访问 /docs 查看接口文档"}
