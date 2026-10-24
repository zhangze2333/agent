"""
routers/auth.py —— 用户注册 / 登录 / 我是谁

【为什么密码错误和用户不存在要返回同一个提示？】
看 login() 的写法：用户不存在和密码错误都返回"用户名或密码错误"。
如果分别提示"用户不存在"和"密码错误"，攻击者就能借此枚举哪些用户名注册过。
这种细节是企业安全规范的常识，叫"防止用户枚举"。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import db_models
from app.database import get_db
from app.models import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["用户认证"])


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    # 用户名唯一性检查（username 列本身也有 unique 约束双保险）
    exists = db.scalar(select(db_models.User).where(db_models.User.username == body.username))
    if exists:
        raise HTTPException(status_code=400, detail="用户名已被注册")

    user = db_models.User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)  # 提交后拿回数据库生成的 id

    # 注册即登录：直接签发 token，省一次登录操作
    return TokenResponse(token=create_access_token(user), username=user.username)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(db_models.User).where(db_models.User.username == body.username))
    # 防用户枚举：两种失败返回同一句话（见文件头注释）
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return TokenResponse(token=create_access_token(user), username=user.username)


@router.get("/me", response_model=UserOut)
def me(user: db_models.User = Depends(get_current_user)):
    """前端用来"恢复登录态"：拿着 token 问一句我是谁。"""
    return user
