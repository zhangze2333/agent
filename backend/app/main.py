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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import chat, todos

# 【知识点：日志配置】
# logging 是 Python 标准库。basicConfig 设置全局格式后，
# 任何模块里 logging.getLogger("名字") 拿到的日志器都会按这个格式输出。
# 我们用 systemd 跑服务，print/logging 输出会自动被系统日志服务(journald)收集，
# 用 journalctl -u agent-api 就能看（见 README 部署章节）。
logging.basicConfig(
    level=logging.INFO,  # DEBUG < INFO < WARNING < ERROR，INFO 表示记录一般运行信息
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """生命周期钩子：yield 之前的代码在服务启动时执行一次（建表），之后在关闭时执行。"""
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

# 把两个路由文件里的接口"挂载"到主应用上
app.include_router(todos.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {"message": "AI 待办助手后端已启动", "docs": "访问 /docs 查看接口文档"}
