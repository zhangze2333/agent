"""
models.py —— Pydantic 数据模型（HTTP 接口的出入参）

【v1.0 更新】
- 新增 TodoOut：接口的统一返回格式（response_model）。企业规范是"出参也要建模"，
  而不是随手返回 dict——返回结构有了合同，前端和文档（/docs）都受益
- 新增认证相关模型：注册/登录请求、token 响应
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ───── 待办 ─────
class TodoCreate(BaseModel):
    """创建待办时的请求体"""

    title: str = Field(..., min_length=1, max_length=200, description="待办内容")
    due_date: Optional[str] = Field(None, description="截止日期，格式 2026-10-22")
    priority: str = Field("medium", description="优先级: high / medium / low")


class TodoUpdate(BaseModel):
    """修改待办时的请求体：所有字段都可选，只改传了的那几项（部分更新）"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    completed: Optional[bool] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None


class TodoOut(BaseModel):
    """
    待办的出参模型。
    model_config = from_attributes 允许"从 ORM 对象直接转"：
    路由 return ORM 对象时，FastAPI 按这个模型的字段挑着序列化——
    password_hash 之类的敏感字段想漏都漏不出去。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    completed: bool
    due_date: Optional[str]
    priority: str
    created_at: datetime


# ───── 用户认证 ─────
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, description="用户名，3-30 字符")
    password: str = Field(..., min_length=6, max_length=50, description="密码，至少 6 位")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    username: str


class UserOut(BaseModel):
    id: int
    username: str


# ───── AI 聊天 ─────
class ChatMessage(BaseModel):
    """历史对话里的一条消息（只有 user / assistant 两种）"""

    role: str = Field(..., description="user 或 assistant")
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    """
    AI 聊天接口的请求体。

    history 是多轮对话的关键：大模型本身没有记忆，
    "它记得上一句"的本质就是前端把之前的问答一起发过来。
    """

    message: str = Field(..., min_length=1, max_length=2000, description="用户对智能体说的话")
    history: list[ChatMessage] = Field(default_factory=list, max_length=20, description="之前的对话")
