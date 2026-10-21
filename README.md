# AI 待办助手 🤖

一个用于**学习全栈开发 + AI 智能体**的项目：用自然语言管理待办事项。

> 「我明天下午三点要开会，帮我记一下」→ 智能体自动调用工具 → 数据库里多一条待办

## 技术栈

| 层 | 技术 | 学什么 |
|---|---|---|
| 前端 | Vue 3 + Vite + Element Plus + axios | 组件化、组合式 API、路由、调接口 |
| 后端 | Python + FastAPI | Web 框架、Pydantic 校验、SQLite 持久化 |
| 智能体 | 智谱 GLM（glm-4-flash，免费） | Function Calling 工具调用、Agent 循环 |

## 项目结构

```
agent/
├── backend/                  # Python 后端
│   ├── app/
│   │   ├── main.py           # 入口：创建 FastAPI 应用（先看这个）
│   │   ├── database.py       # SQLite 连接与建表
│   │   ├── models.py         # Pydantic 数据模型（自动校验请求参数）
│   │   ├── routers/
│   │   │   ├── todos.py      # 待办增删改查接口
│   │   │   └── chat.py       # AI 聊天接口
│   │   └── agent/            # ★ 智能体核心，全项目精华
│   │       ├── llm.py        # 封装大模型调用
│   │       ├── tools.py      # 工具说明书 + 工具实现（Function Calling）
│   │       └── runner.py     # Agent 主循环：思考→调工具→观察→再思考
│   └── requirements.txt
├── frontend/                 # Vue 3 前端
│   └── src/
│       ├── main.js           # 前端入口
│       ├── App.vue           # 根组件（外壳+导航）
│       ├── router/index.js   # 路由：/ 和 /chat 两个页面
│       ├── api/index.js      # 所有后端接口的调用封装
│       ├── views/
│       │   ├── TodoList.vue  # 待办列表页（标准 CRUD 页面套路）
│       │   └── Chat.vue      # AI 聊天页（打字机效果）
│       └── components/
│           ├── TodoItem.vue  # 单条待办（学 props/emit 父子通信）
│           └── ChatMessage.vue # 聊天气泡
└── README.md
```

## 本地运行

### 1. 启动后端（首次需要配置）

```bash
cd backend

# 首次：创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 配置智谱 API key（免费领取：https://open.bigmodel.cn 控制台 -> API keys）
copy .env.example .env
# 用编辑器打开 .env，填入你的 key

# 启动（每次开发都要执行）
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8010
```

看到 `Application startup complete` 即成功。打开 http://127.0.0.1:8010/docs 有自动生成的接口文档。

### 2. 启动前端

```bash
cd frontend
npm install   # 首次才需要
npm run dev
```

打开 http://localhost:5173 即可使用。

## 建议的学习路线

按这个顺序读代码，每一步都动手改一改：

1. **跑通**：先后端 `python app` 跑起来，浏览器开 `/docs` 玩接口 → 再前端跑起来点一遍
2. **后端 CRUD**：读 `main.py` → `database.py` → `routers/todos.py`，
   试着加一个接口：`GET /api/todos/search?keyword=开会`（按关键字搜索）
3. **前端页面**：读 `TodoList.vue`，试着把筛选改成三个 tab 显示各自数量
4. **智能体（重点）**：按 `tools.py` → `runner.py` → `routers/chat.py` 的顺序读，
   打开聊天页发「帮我记一件事」，观察界面下方绿色标签里 AI 实际调用了什么工具
5. **动手扩展**：给智能体加一个 `update_todo` 工具（改标题/改日期），
   仿照 `add_todo` 的三处写法：TOOLS_SCHEMA 说明书、_update_todo 实现、tool_map 注册

## 核心原理：智能体是怎么工作的

大模型只会生成文字，不能直接操作数据库。Function Calling 的机制是：

```
用户: "明天提醒我开会"
        │
        ▼
① 后端把【系统提示 + 用户消息 + 工具说明书】发给大模型
        │
        ▼
② 大模型回复："请帮我调用 add_todo(title='开会', due_date='2026-10-22')"
        │
        ▼
③ 后端的 Python 代码真正执行这个函数，写入 SQLite
        │
        ▼
④ 把执行结果（成功/失败）回传给大模型
        │
        ▼
⑤ 大模型组织成自然语言："好的，已帮你记下明天开会 ✓"
```

前端聊天页会把 ②~④ 实际发生的工具调用显示成绿色标签，方便你观察。

## 待办 CRUD 接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/todos | 查列表，支持 `?completed=false` 筛选 |
| POST | /api/todos | 新建 `{title, due_date?, priority?}` |
| GET | /api/todos/{id} | 查单条 |
| PUT | /api/todos/{id} | 修改（支持部分字段） |
| DELETE | /api/todos/{id} | 删除 |
| POST | /api/chat | 和智能体对话 `{message}` |

## 进阶方向（学完基础后挑战）

- **SSE 流式输出**：现在打字机效果是前端"假"流式，改成后端真流式（FastAPI `StreamingResponse`）
- **多轮上下文**：现在每次对话独立，把历史消息传给 `/api/chat` 让 AI 记得上一句
- **用户系统**：注册登录 + 每人自己的待办（JWT / session）
- **部署上线**：服务器上 `uvicorn` + `nginx` 反代 + 前端 `npm run build` 出静态文件
- **更多工具**：让智能体能查天气、设提醒周期、统计本周完成率
