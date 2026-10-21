"""
database.py —— 数据库模块

【知识点：SQLite 是什么？】
SQLite 是一个"文件数据库"：整个数据库就是硬盘上的一个 .db 文件，
不需要像 MySQL 那样安装数据库软件、开服务、设密码，Python 标准库自带支持。
学习和小项目用它最合适；以后数据量大了再换 MySQL/PostgreSQL，思路完全一样。

【知识点：为什么不用全局变量存数据？】
后端进程一重启，内存里的数据就没了（这叫"易失"）。
写入数据库 = 写入硬盘，重启后数据还在，这叫"持久化"。
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

# __file__ 是当前文件的路径，这样写保证无论从哪个目录启动程序，都能找到正确的数据库文件
DB_PATH = Path(__file__).parent / "todos.db"


@contextmanager
def db():
    """
    一个"上下文管理器"，用法：

        with db() as conn:
            conn.execute("SELECT ...")

    with 代码块结束时自动提交事务（commit）并关闭连接（close），
    避免我们忘记 close 导致资源泄漏。@contextmanager 是 Python 的语法糖，
    相当于帮你把 try/finally 写法包装得更优雅。
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 让每行结果既能用下标 row[0]，也能用列名 row["title"] 访问
    try:
        yield conn
        conn.commit()  # 增删改操作真正落盘
    finally:
        conn.close()


def init_db():
    """项目启动时调用：建表。IF NOT EXISTS 保证重复启动也不会报错。"""
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增主键，每条待办的唯一编号
                title      TEXT    NOT NULL,                   -- 待办内容
                completed  INTEGER NOT NULL DEFAULT 0,         -- SQLite 没有布尔类型，0=未完成 1=已完成
                due_date   TEXT,                               -- 截止日期，格式 2026-10-22，可以为空
                priority   TEXT    NOT NULL DEFAULT 'medium',  -- 优先级 high / medium / low
                created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )


def row_to_todo(row) -> dict:
    """把数据库的一行(row)转成字典(dict)，返回给前端的就是 JSON，字典会自动变 JSON。"""
    return {
        "id": row["id"],
        "title": row["title"],
        "completed": bool(row["completed"]),  # 转回真正的 true/false 给前端
        "due_date": row["due_date"],
        "priority": row["priority"],
        "created_at": row["created_at"],
    }
