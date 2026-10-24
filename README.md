# AI 待办助手 🤖

一个用于**学习全栈开发 + AI 智能体**的项目：注册登录后，用自然语言管理你自己的待办事项。

> 「我明天下午三点要开会，帮我记一下」→ 智能体自动调用工具 → 数据库里多一条**属于你**的待办

## 技术栈

| 层 | 技术 | 学什么 |
|---|---|---|
| 前端 | Vue 3 + Vite + Element Plus + axios | 组件化、组合式 API、路由守卫、拦截器 |
| 后端 | Python + FastAPI + SQLAlchemy | ORM、JWT 认证、越权防护、SSE 流式 |
| 智能体 | 智谱 GLM | Function Calling 工具调用、Agent 循环、澄清机制 |
| 工程化 | Ruff / ESLint / Docker Compose | 代码规范、容器化部署 |

## 功能特性（v1.0 企业级）

- ✅ 注册/登录（bcrypt 密码哈希 + JWT 令牌，24 小时有效）
- ✅ 数据隔离：每人只能看到/操作自己的待办（后端强制过滤，防水平越权）
- ✅ 智能体以当前用户身份执行工具（user_id 由后端注入，大模型无法指定操作他人数据）
- ✅ 真流式输出（SSE）：思考过程、执行步骤、回复全部实时可见
- ✅ 澄清机制：信息不足时智能体会反问（如添加待办没提时间）
- ✅ 双写日志：journald + 文件（按天切割保留 14 天）
- ✅ 代码规范：Ruff + ESLint/Prettier 全绿
- ✅ Docker 容器化：`docker compose up -d` 一条命令拉起全套

## 项目结构

```
agent/
├── backend/                  # Python 后端
│   ├── app/
│   │   ├── main.py           # 入口：组装所有部件（先看这个）
│   │   ├── database.py       # SQLAlchemy 引擎/会话（DATABASE_URL 可配）
│   │   ├── db_models.py      # ORM 模型：User / Todo 两张表
│   │   ├── models.py         # Pydantic 模型：接口出入参
│   │   ├── security.py       # ★ 密码哈希 + JWT 签发/校验 + 当前用户依赖
│   │   ├── routers/
│   │   │   ├── auth.py       # 注册 / 登录 / me
│   │   │   ├── todos.py      # 待办增删改查（全部要求登录+数据隔离）
│   │   │   └── chat.py       # AI 聊天（普通版 + SSE 流式版）
│   │   └── agent/            # ★ 智能体核心
│   │       ├── llm.py        # 封装大模型调用
│   │       ├── tools.py      # 工具说明书 + 实现（user_id 后端注入）
│   │       └── runner.py     # Agent 主循环（流式 + 事件播报）
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # Vue 3 前端
│   ├── src/
│   │   ├── main.js           # 前端入口
│   │   ├── App.vue           # 外壳 + 导航（含用户名/退出）
│   │   ├── router/index.js   # 路由 + 登录守卫
│   │   ├── stores/auth.js    # 登录态（token/用户名）
│   │   ├── api/index.js      # 接口封装 + axios 拦截器（带token/401跳转）
│   │   ├── views/
│   │   │   ├── Login.vue     # 登录/注册页
│   │   │   ├── TodoList.vue  # 待办列表页
│   │   │   └── Chat.vue      # AI 聊天页（fetch 读 SSE 流）
│   │   └── components/
│   │       ├── TodoItem.vue
│   │       └── ChatMessage.vue  # 聊天气泡 + 可折叠思考块
│   ├── Dockerfile            # 多阶段构建：node 打包 → nginx 托管
│   └── nginx.docker.conf     # 容器版 nginx（/api 反代到 api 服务）
├── docker-compose.yml        # api + web 两个服务
└── docs/                     # 学习指南、k8s 入门、基础训练
```

## 本地运行

### 1. 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows；Linux/macOS 是 source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env            # 填三项：ZHIPU_API_KEY、GLM_MODEL/GLM_BASE_URL、JWT_SECRET
                                  # JWT_SECRET 生成：python -c "import secrets; print(secrets.token_hex(32))"

.venv\Scripts\activate
uvicorn app.main:app --port 8010  # 开发时加 --reload
```

接口文档：http://127.0.0.1:8010/docs

### 2. 前端

```bash
cd frontend
npm install
npm run dev        # 开发服务器，/api 自动代理到 8010
```

打开 http://localhost:5173 ，先注册一个账号。

### 3. 代码规范（提交前跑一遍）

```bash
cd backend && .venv/Scripts/ruff check app --fix && .venv/Scripts/ruff format app
cd frontend && npm run lint && npm run format
```

## Docker 部署（服务器）

```bash
# 前置：服务器装好 Docker Engine 和 docker compose 插件
git clone https://github.com/zhangze2333/agent.git && cd agent

# 密钥不进仓库，单独配置（三项同上）
cp backend/.env.example backend/.env && vi backend/.env

docker compose up -d --build
docker compose logs -f api        # 看后端日志
```

架构：`web` 容器（nginx）占 80 端口对外，静态文件直接托管、`/api` 反代到 `api`
容器；`api` 不映射端口，只在 compose 内部网络可达。SQLite 数据存命名卷
`api-data`，容器重建不丢。

## 学习路线

1. **跑通**：本地起前后端，注册登录玩一遍，F12 看 Network 里 Authorization 头
2. **认证流程**：按 `auth.py` → `security.py` → `api/index.js` → `router/index.js`
   顺序读，画一张"从提交密码到带上 token 请求"的时序图
3. **ORM**：对比 `db_models.py` 和旧版裸 SQL 写法（git log 里有），理解 ORM 价值
4. **越权防护**：读 `routers/todos.py` 每个查询的 `user_id` 过滤和 `agent/tools.py`
   的 user_id 注入设计——为什么后者必须由后端注入而不是让大模型传？
5. **动手扩展**：给智能体加 `update_todo` 工具；或给待办加"搜索"接口

## 进阶方向

- 自动化测试（pytest）+ GitHub Actions CI
- Alembic 数据库迁移（表结构变更的版本管理）
- PostgreSQL 切换（改 DATABASE_URL + 装驱动即可，ORM 的红利）
- HTTPS（需要域名 + 证书）
- 更细的日志监控（接入你服务器上已有的 Langfuse？）

## 待办 API 一览（全部需要 Authorization: Bearer <token>）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/auth/register | 注册 `{username, password}` → 返回 token |
| POST | /api/auth/login | 登录 → 返回 token |
| GET | /api/auth/me | 当前用户信息 |
| GET | /api/todos | 查自己的列表，支持 `?completed=false` |
| POST | /api/todos | 新建 `{title, due_date?, priority?}` |
| PUT | /api/todos/{id} | 修改（支持部分字段） |
| DELETE | /api/todos/{id} | 删除 |
| POST | /api/chat | 和智能体对话（一次性返回） |
| POST | /api/chat/stream | SSE 流式对话（前端实际用的） |
