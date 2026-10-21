"""
routers/todos.py —— 待办事项的增删改查接口（REST API）

【知识点：RESTful 是一种接口设计风格】
用「URL 定位资源」+「HTTP 方法表达操作」：
    GET    /api/todos       查列表
    POST   /api/todos       新建一条
    PUT    /api/todos/3     修改第 3 条
    DELETE /api/todos/3     删除第 3 条
前端 axios 调用时一一对应，整个团队看到 URL 就知道接口是干嘛的。

【知识点：APIRouter】
把接口按功能拆到不同文件（路由分组），而不是全堆在 main.py 里，
项目大了才不会乱。main.py 里用 app.include_router() 把它们组装起来。
"""
from fastapi import APIRouter, HTTPException

from app import database
from app.models import TodoCreate, TodoUpdate

# prefix 表示这个文件里所有接口的 URL 前缀都是 /api/todos
router = APIRouter(prefix="/api/todos", tags=["待办管理"])


@router.get("")
def list_todos(completed: bool | None = None):
    """
    查询待办列表。
    completed 是"查询参数"（URL 问号后面的部分）：
      /api/todos              -> 返回全部
      /api/todos?completed=false -> 只返回未完成的
    """
    with database.db() as conn:
        if completed is None:
            # ORDER BY completed：未完成(0)排在已完成(1)前面；再按 id 倒序，新的在前
            rows = conn.execute("SELECT * FROM todos ORDER BY completed, id DESC").fetchall()
        else:
            # ? 占位符传参可以防止 SQL 注入攻击，永远不要用 f-string 拼 SQL！
            rows = conn.execute(
                "SELECT * FROM todos WHERE completed = ? ORDER BY id DESC", (completed,)
            ).fetchall()
    return [database.row_to_todo(r) for r in rows]


@router.post("")
def create_todo(body: TodoCreate):
    """新建待办。body: TodoCreate 让 FastAPI 自动解析并校验请求体 JSON。"""
    with database.db() as conn:
        cursor = conn.execute(
            "INSERT INTO todos (title, due_date, priority) VALUES (?, ?, ?)",
            (body.title, body.due_date, body.priority),
        )
        new_id = cursor.lastrowid  # 数据库自动分配的自增 id
    return get_todo_by_id(new_id)


@router.get("/{todo_id}")
def get_todo_by_id(todo_id: int):
    """按 id 查单条。路径里的 {todo_id} 会自动传进函数，并自动转成 int。"""
    with database.db() as conn:
        row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if row is None:
        # HTTPException 会返回指定状态码给前端，404 = 资源不存在
        raise HTTPException(status_code=404, detail=f"待办 {todo_id} 不存在")
    return database.row_to_todo(row)


@router.put("/{todo_id}")
def update_todo(todo_id: int, body: TodoUpdate):
    """
    修改待办（支持只改部分字段）。
    小技巧：把"传了值的字段"动态拼进 UPDATE 语句（值仍然用 ? 占位，安全）。
    """
    # 只收集用户传了的字段，组成 {列名: 新值} 字典
    fields = body.model_dump(exclude_unset=True)  # Pydantic 方法：只保留请求里出现的字段
    if not fields:
        raise HTTPException(status_code=400, detail="没有提供任何要修改的字段")

    set_clause = ", ".join(f"{col} = ?" for col in fields)  # 例如 "title = ?, completed = ?"
    params = list(fields.values()) + [todo_id]

    with database.db() as conn:
        cursor = conn.execute(f"UPDATE todos SET {set_clause} WHERE id = ?", params)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"待办 {todo_id} 不存在")
    return get_todo_by_id(todo_id)


@router.delete("/{todo_id}")
def delete_todo(todo_id: int):
    with database.db() as conn:
        cursor = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"待办 {todo_id} 不存在")
    return {"message": f"已删除待办 {todo_id}"}
