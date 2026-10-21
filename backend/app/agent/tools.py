"""
agent/tools.py —— 智能体的"工具箱"

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
你听过的"智能体 Agent"，底层机制就是这个循环。
═══════════════════════════════════════════════════════════════════
"""
import json

from app import database

# ─────────────────────────────────────────────
# 第一部分：工具说明书（JSON Schema 格式，这是业界标准写法）
# description 写得越清楚，大模型越知道什么时候该用哪个工具、参数怎么填
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# 第二部分：工具的真正实现（就是普通的 Python 函数，直接操作数据库）
# ─────────────────────────────────────────────
def _add_todo(title: str, due_date: str | None = None, priority: str = "medium") -> dict:
    with database.db() as conn:
        cursor = conn.execute(
            "INSERT INTO todos (title, due_date, priority) VALUES (?, ?, ?)",
            (title, due_date, priority),
        )
        todo_id = cursor.lastrowid
    return {"success": True, "todo_id": todo_id, "message": f"已创建待办：{title}"}


def _list_todos(completed: bool | None = None) -> dict:
    with database.db() as conn:
        if completed is None:
            rows = conn.execute("SELECT * FROM todos ORDER BY completed, id DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM todos WHERE completed = ? ORDER BY id DESC", (completed,)
            ).fetchall()
    return {"count": len(rows), "todos": [database.row_to_todo(r) for r in rows]}


def _complete_todo(todo_id: int) -> dict:
    with database.db() as conn:
        cursor = conn.execute("UPDATE todos SET completed = 1 WHERE id = ?", (todo_id,))
        if cursor.rowcount == 0:
            return {"success": False, "message": f"待办 {todo_id} 不存在"}
    return {"success": True, "message": f"待办 {todo_id} 已标记完成"}


def _delete_todo(todo_id: int) -> dict:
    with database.db() as conn:
        cursor = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        if cursor.rowcount == 0:
            return {"success": False, "message": f"待办 {todo_id} 不存在"}
    return {"success": True, "message": f"待办 {todo_id} 已删除"}


# ─────────────────────────────────────────────
# 第三部分：调度器——大模型点名要用的工具，由它来执行
# ─────────────────────────────────────────────
def execute_tool(name: str, args: dict) -> dict:
    """
    根据工具名执行对应函数。返回值一定是 dict（后面会转成 JSON 传回大模型）。

    args 是大模型生成的参数字典。如果大模型传了不存在的参数或类型不对，
    这里用 **args 展开时可能报错，所以套一层 try 兜底，把错误信息也回传给
    大模型——它看到报错后通常会自己修正参数再试一次，这本身就是 Agent 的
    自我纠错能力。
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
        return func(**args)
    except TypeError as e:
        return {"success": False, "message": f"参数不对: {e}"}
