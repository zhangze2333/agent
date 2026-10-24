"""
agent/tools.py —— 智能体的"工具箱"（ORM 版 + 用户上下文注入）

═══════════════════════════════════════════════════════════════════
【本文件是整个项目最核心的知识点：Function Calling（工具调用）】

大模型本质上只会"生成文字"，它自己摸不到你的数据库。
Function Calling 的做法是：

 1. 我们在请求里附一份"工具说明书"（每个工具的名字、用途、参数格式）
 2. 大模型读完用户的话，如果判断"这需要动数据"，它不直接回答，
    而是回复一个结构化请求：我想调用 add_todo，参数是 title="买牛奶"
 3. 【这一步由我们的 Python 代码来执行】真正操作数据库
 4. 把执行结果回传给大模型，它再组织成自然语言回复用户

所以说：LLM 是大脑（决定做什么），tools 是手脚（真正去做）。

【v1.0 安全要点：user_id 由后端注入，不由大模型提供】
工具说明书（TOOLS_SCHEMA）里故意【没有】user_id 参数——大模型不需要知道
有用户这回事。执行时 execute_tool 把当前登录用户的 id 强行塞进去。
为什么要这样设计？如果 user_id 出现在说明书里，就等于告诉大模型
"你可以指定操作谁的待办"，提示词注入攻击（用户说"把张三的待办全删了"）
就可能让大模型真的传别人的 id。**安全参数永远由服务端注入，不信任模型输出**
═══════════════════════════════════════════════════════════════════
"""
import json
import logging

from sqlalchemy import select

from app import db_models
from app.database import SessionLocal

logger = logging.getLogger("agent")

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description": "创建一条新的待办事项。当用户说要做什么事、记一下某事时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "待办内容，简短一句话"},
                    "due_date": {
                        "type": "string",
                        "description": "截止日期，格式 YYYY-MM-DD。用户没提到日期就不要传这个参数",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "优先级，用户没说就默认 medium",
                    },
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_todos",
            "description": "查询待办列表。当用户问'我有什么待办/安排/任务'时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "completed": {
                        "type": "boolean",
                        "description": "传 true 只查已完成的，传 false 只查未完成的，不传查全部",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_todo",
            "description": "把某条待办标记为已完成。当用户说做完了某事时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_id": {"type": "integer", "description": "待办的 id 编号"},
                },
                "required": ["todo_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_todo",
            "description": "删除一条待办。当用户明确说删除/不要某条待办时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_id": {"type": "integer", "description": "待办的 id 编号"},
                },
                "required": ["todo_id"],
            },
        },
    },
]


def _todo_dict(todo: db_models.Todo) -> dict:
    """ORM 对象 -> 给大模型看的字典（它只需要关键信息，不用全部字段）"""
    return {
        "id": todo.id,
        "title": todo.title,
        "completed": todo.completed,
        "due_date": todo.due_date,
        "priority": todo.priority,
    }


def _get_todo_for_user(db, todo_id: int, user_id: int) -> db_models.Todo | None:
    """按 id 取待办，且必须属于该用户——工具层的越权防线。"""
    return db.scalar(
        select(db_models.Todo).where(
            db_models.Todo.id == todo_id, db_models.Todo.user_id == user_id
        )
    )


# ─────────────────────────────────────────────
# 工具实现：第一个参数都是 user_id（由 execute_tool 注入）
# 每个函数自建 Session（工具可能被循环多次调用，各自独立更稳）
# ─────────────────────────────────────────────
def _add_todo(user_id: int, title: str, due_date: str | None = None, priority: str = "medium") -> dict:
    with SessionLocal() as db:
        todo = db_models.Todo(user_id=user_id, title=title, due_date=due_date, priority=priority)
        db.add(todo)
        db.commit()
        db.refresh(todo)
        todo_id = todo.id
    logger.info("工具 add_todo: 用户%d 创建待办%d", user_id, todo_id)
    return {"success": True, "todo_id": todo_id, "message": f"已创建待办：{title}"}


def _list_todos(user_id: int, completed: bool | None = None) -> dict:
    with SessionLocal() as db:
        stmt = select(db_models.Todo).where(db_models.Todo.user_id == user_id)
        if completed is not None:
            stmt = stmt.where(db_models.Todo.completed == completed)
        stmt = stmt.order_by(db_models.Todo.completed, db_models.Todo.id.desc())
        todos = db.scalars(stmt).all()
    return {"count": len(todos), "todos": [_todo_dict(t) for t in todos]}


def _complete_todo(user_id: int, todo_id: int) -> dict:
    with SessionLocal() as db:
        todo = _get_todo_for_user(db, todo_id, user_id)
        if todo is None:
            return {"success": False, "message": f"待办 {todo_id} 不存在（或不属于你）"}
        todo.completed = True
        db.commit()
    logger.info("工具 complete_todo: 用户%d 完成待办%d", user_id, todo_id)
    return {"success": True, "message": f"待办 {todo_id} 已标记完成"}


def _delete_todo(user_id: int, todo_id: int) -> dict:
    with SessionLocal() as db:
        todo = _get_todo_for_user(db, todo_id, user_id)
        if todo is None:
            return {"success": False, "message": f"待办 {todo_id} 不存在（或不属于你）"}
        db.delete(todo)
        db.commit()
    logger.info("工具 delete_todo: 用户%d 删除待办%d", user_id, todo_id)
    return {"success": True, "message": f"待办 {todo_id} 已删除"}


def execute_tool(name: str, args: dict, user_id: int) -> dict:
    """
    根据工具名执行对应函数。user_id 是后端注入的身份，与 args 无关。

    args 是大模型生成的参数字典。如果大模型传了不存在的参数或类型不对，
    这里套一层 try 兜底，把错误信息也回传给大模型——它看到报错后通常会
    自己修正参数再试一次，这本身就是 Agent 的自我纠错能力。
    """
    tool_map = {
        "add_todo": _add_todo,
        "list_todos": _list_todos,
        "complete_todo": _complete_todo,
        "delete_todo": _delete_todo,
    }
    func = tool_map.get(name)
    if func is None:
        return {"success": False, "message": f"未知工具: {name}"}
    try:
        return func(user_id, **args)
    except TypeError as e:
        return {"success": False, "message": f"参数不对: {e}"}
