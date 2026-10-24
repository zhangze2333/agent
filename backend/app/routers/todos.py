"""
routers/todos.py —— 待办增删改查（SQLAlchemy ORM 版 + 数据隔离）

【v1.0 企业级改造的两大变化】
1. ORM：裸 SQL 全部换成 SQLAlchemy 查询
2. 数据隔离：每个路由都注入 `user: User = Depends(get_current_user)`，
   所有查询强制过滤 user.id —— 用户 A 永远看不到用户 B 的待办。

【越权漏洞课】
假设查询不筛 user_id（只靠前端不显示别人的数据），攻击者拿着自己的
登录 token 直接 curl /api/todos/88 就能翻出别人的待办——这叫"水平越权"，
是后端事故排行榜的常客。防它的唯一正确姿势：**服务端每个查询都带身份过滤**，
永远不要相信"前端没展示"。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import db_models
from app.database import get_db
from app.models import TodoCreate, TodoOut, TodoUpdate
from app.security import get_current_user

router = APIRouter(prefix="/api/todos", tags=["待办管理"])


@router.get("", response_model=list[TodoOut])
def list_todos(
    completed: bool | None = None,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查当前用户的待办列表。completed 查询参数可选筛选。"""
    stmt = select(db_models.Todo).where(db_models.Todo.user_id == user.id)
    if completed is not None:
        stmt = stmt.where(db_models.Todo.completed == completed)
    # 未完成的在前，新的在前
    stmt = stmt.order_by(db_models.Todo.completed, db_models.Todo.id.desc())
    return db.scalars(stmt).all()  # ORM 对象列表 -> FastAPI 按 TodoOut 序列化


@router.post("", response_model=TodoOut, status_code=201)
def create_todo(
    body: TodoCreate,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """新建待办。注意 user_id 来自登录态，不是请求参数——前端传什么都不算数。"""
    todo = db_models.Todo(
        user_id=user.id, title=body.title, due_date=body.due_date, priority=body.priority
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


@router.get("/{todo_id}", response_model=TodoOut)
def get_todo(
    todo_id: int,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = db.get(db_models.Todo, todo_id)
    # 两个 404 合一个：不存在，或不是你的（不泄露"这条数据属于别人"的信息）
    if todo is None or todo.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"待办 {todo_id} 不存在")
    return todo


@router.put("/{todo_id}", response_model=TodoOut)
def update_todo(
    todo_id: int,
    body: TodoUpdate,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = db.get(db_models.Todo, todo_id)
    if todo is None or todo.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"待办 {todo_id} 不存在")

    # 只更新请求里出现的字段（部分更新的标准 ORM 写法）
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(todo, field, value)
    db.commit()
    db.refresh(todo)
    return todo


@router.delete("/{todo_id}")
def delete_todo(
    todo_id: int,
    user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = db.get(db_models.Todo, todo_id)
    if todo is None or todo.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"待办 {todo_id} 不存在")
    db.delete(todo)
    db.commit()
    return {"message": f"已删除待办 {todo_id}"}
