"""
security.py —— 认证安全模块（密码哈希 + JWT + 当前用户依赖）

═══════════════════════════════════════════════════════════════════
【JWT 登录全流程（企业标准做法）】

1. 用户 POST /api/auth/login 提交用户名密码
2. 服务端 bcrypt 校验密码哈希 → 通过则签发 JWT（一串带签名的令牌）
3. 前端把 token 存 localStorage，之后每个请求带上请求头：
       Authorization: Bearer eyJhbGciOi...
4. 服务端 get_current_user 依赖：验签 + 查库，把"当前用户"注入路由函数
5. 服务端不存任何会话状态（无状态认证），天生适合横向扩容

JWT 内容其实是三段 Base64：头部.载荷.签名。载荷能看到内容（别放敏感信息！），
但没人能伪造——签名只有握着 JWT_SECRET 的服务端能算出来。
所以 JWT_SECRET 绝不能进代码库，只能放 .env。
═══════════════════════════════════════════════════════════════════
"""

import os
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import db_models
from app.database import get_db

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "1440"))  # 默认 24 小时


def hash_password(password: str) -> str:
    """
    bcrypt 哈希：自带随机盐，同一个密码每次哈希结果都不同，
    但 checkpw 能验证。数据库泄露时攻击者拿到的只是哈希，不能直接登录。
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user: db_models.User) -> str:
    """签发 JWT。sub 存用户 id（JWT 标准字段），exp 是过期时间。"""
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "exp": datetime.now(UTC) + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


# HTTPBearer 负责解析 "Authorization: Bearer xxx" 请求头
# auto_error=False：没带头时不自动抛错，由我们返回统一的 401 信息
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> db_models.User:
    """
    FastAPI 依赖：任何需要登录的路由加一行参数
        user: User = Depends(get_current_user)
    就完成了"必须登录 + 拿到当前用户"两件事。
    """
    if creds is None:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的登录凭证")

    user = db.get(db_models.User, int(payload["sub"]))
    if user is None:  # token 有效但用户已被删
        raise HTTPException(status_code=401, detail="用户不存在")
    return user
