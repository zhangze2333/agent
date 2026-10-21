"""
models.py —— 数据模型（基于 Pydantic）

【知识点：Pydantic 是干嘛的？】
它用"类"来描述数据应该长什么样。FastAPI 拿到前端发来的 JSON 后会自动：
1. 校验：title 是不是字符串？空不空？超不超过 200 字？不合格直接返回 422 错误
2. 转换：JSON -> Python 对象，你直接用 obj.title 访问
3. 生成文档：访问 /docs 能看到根据这些模型自动生成的接口文档

没有它的话，这些检查你得自己写一堆 if，很容易漏。
"""
from typing import Optional

from pydantic import BaseModel, Field


class TodoCreate(BaseModel):
    """创建待办时的请求体格式"""

    title: str = Field(..., min_length=1, max_length=200, description="待办内容")
    # "..." 表示必填；Optional[str] = None 表示可不填，默认为空
    due_date: Optional[str] = Field(None, description="截止日期，格式 2026-10-22")
    priority: str = Field("medium", description="优先级: high / medium / low")


class TodoUpdate(BaseModel):
    """修改待办时的请求体格式：所有字段都可选，只改传了的那几项（部分更新）"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    completed: Optional[bool] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None


class ChatRequest(BaseModel):
    """AI 聊天接口的请求体"""

    message: str = Field(..., min_length=1, max_length=2000, description="用户对智能体说的话")
