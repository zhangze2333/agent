"""
db_models.py —— ORM 模型（数据库表的定义）

命名说明：models.py 是给"接口出入参"用的 Pydantic 模型，
这个文件是给"数据库表"用的 SQLAlchemy 模型。两套模型各司其职：
  Pydantic  -> 校验/描述 HTTP JSON
  SQLAlchemy -> 映射/操作数据库表
企业项目里通常分开写（也有人用同一文件），关键是脑子里要分清。

【Mapped / mapped_column 是 SQLAlchemy 2.0 的新写法】
带类型提示，IDE 能推断 row.user_id 是 int，比旧写法 Column() 舒服很多。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """用户表：登录凭据。密码只存哈希（security.py 负责），永远不存明文。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),  # 由数据库生成创建时间
    )


class Todo(Base):
    """待办表：每条待办属于一个用户（user_id 外键）——数据隔离的根基。"""

    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    completed: Mapped[bool] = mapped_column(default=False)
    due_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
