"""
@FileName：auth_middleware.py
@Description：
@Author：baojun.wang
@Time：2025/11/3 21:06
"""
import os
import time

from dotenv import load_dotenv
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from core.database import get_sync_db
from app.user.controller import get_user_by_username, verify_password, is_super_admin
from utils.commonlib import now_with_offset

load_dotenv()
REFRESH_TOKEN_THRESHOLD_MINUTES = 30

SECRET_KEY = "2af555fd2e8c2e68b0af48b312de1009"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))


class JWTManager:
    @staticmethod
    def create_access_token(data: dict):
        to_encode = data.copy()
        expire = now_with_offset(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

    @staticmethod
    def is_token_expiring_soon(payload: dict):
        if not payload or "exp" not in payload:
            return False
        exp_timestamp = payload["exp"]
        return exp_timestamp - time.time() < REFRESH_TOKEN_THRESHOLD_MINUTES * 60


security = HTTPBearer()


def authenticate_user(db: Session, username: str, password: str):
    """验证用户"""
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


# === JWT 工具函数 ===

def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security),
                     db=Depends(get_sync_db)):
    token = credentials.credentials
    payload = JWTManager.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的认证凭证")

    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="无效的认证凭证")

    env_super_admin = os.getenv("SYSTEM_ADMIN")
    if env_super_admin and username == env_super_admin:
        user = type('User', (), {
            'id': 0,
            'username': username,
            'email': 'admin@example.com',
            'nickname': '超级管理员',
            'is_deleted': False
        })()
    else:
        user = get_user_by_username(db, username)
        if user is None:
            raise HTTPException(status_code=401, detail="用户不存在")

    new_token = None
    if JWTManager.is_token_expiring_soon(payload):
        new_token_data = {"sub": user.username}
        new_token = JWTManager.create_access_token(new_token_data)

    request.state.new_token = new_token

    return user


def get_current_super_admin(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security),
                            db=Depends(get_sync_db)):
    """获取当前超级管理员用户"""
    user = get_current_user(request, credentials, db)

    if user.id == 0:
        return user

    if not is_super_admin(db, user.id):
        raise HTTPException(status_code=403, detail="需要超级管理员权限")

    return user
