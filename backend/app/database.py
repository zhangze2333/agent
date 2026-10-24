"""
database.py —— 数据库连接层（SQLAlchemy ORM 版）

═══════════════════════════════════════════════════════════════════
【v1.0 企业级改造：从裸 SQL 到 ORM】

以前（裸 SQL）：
    conn.execute("SELECT * FROM todos WHERE user_id = ?", (uid,))
现在（ORM）：
    db.query(Todo).filter(Todo.user_id == uid).all()

ORM 的核心思想：一张表 = 一个 Python 类，一行数据 = 一个对象。
好处（为什么企业项目标配）：
1. 换数据库几乎零成本：本行只改 DATABASE_URL，SQL 方言由 SQLAlchemy 生成
2. 防注入：查询条件是 Python 表达式，不是手拼字符串
3. 表结构有类型提示，IDE 补全 + 重构工具都能用
═══════════════════════════════════════════════════════════════════
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

# 数据库地址走配置：默认还是项目里的 SQLite 文件。
# 未来换 PostgreSQL 只需改成：
#   DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
# 并 pip install psycopg —— 业务代码一行不用动，这就是 ORM 的价值
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{(Path(__file__).parent / 'todos.db').as_posix()}"
)

# SQLite 需要这个参数：允许多线程访问（FastAPI 的线程池会并发处理请求）
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# 会话工厂：Session 是"一次数据库交互"的上下文，负责追踪改动、提交事务
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。SQLAlchemy 靠它收集"有哪些表"。"""


def get_db():
    """
    FastAPI 依赖注入：每个请求进来创建一个会话，请求结束自动关闭。

    路由函数里写 `db: Session = Depends(get_db)` 即可拿到会话，
    不用自己管开关 —— 和 v0.1 的 with database.db() 是同一个思路的依赖化写法。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """启动时建表：根据所有继承 Base 的模型类创建不存在的表（已存在的不动）。"""
    # import 必须放在函数内：让 SQLAlchemy 此刻能看到所有模型类
    from app import db_models  # noqa: F401

    Base.metadata.create_all(engine)
