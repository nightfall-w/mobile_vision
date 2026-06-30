"""
@FileName：controller.py
@Description：用户相关工具类
@Author：baojun.wang
"""
import os
from typing import Optional, List, Tuple

from dotenv import load_dotenv
from passlib.context import CryptContext
from sqlalchemy import select, func, or_, delete
from sqlalchemy.orm import Session

from app.user.models import UserModel, SuperAdminModel
from utils.commonlib import now

load_dotenv()
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


# === 密码工具 ===
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# === 用户 CRUD ===
def get_user_by_username(db: Session, username: str) -> Optional[UserModel]:
    """根据用户名查询用户"""
    result = db.execute(select(UserModel).where(UserModel.username == username))
    return result.scalars().first()


def get_nickname_by_username(db: Session, username: str) -> Optional[str]:
    """获取用户昵称"""
    user = get_user_by_username(db, username)
    return user.nickname if user else None


def get_user_by_email(db: Session, email: str) -> Optional[UserModel]:
    """根据邮箱查询用户"""
    result = db.execute(select(UserModel).where(UserModel.email == email))
    return result.scalars().first()


def get_user_by_id(db: Session, user_id: int) -> Optional[UserModel]:
    """根据ID查询用户"""
    result = db.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalars().first()


def create_user(db: Session, username: str, email: str, nickname: str, password: str) -> Optional[UserModel]:
    """创建用户"""
    hashed_password = get_password_hash(password)
    user = UserModel(
        username=username,
        email=email,
        hashed_password=hashed_password,
        nickname=nickname,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[UserModel]:
    """验证用户登录"""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_users_with_count(
        db: Session,
        search: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
) -> Tuple[List[UserModel], int]:
    """获取用户列表及总数"""
    if not search:
        count_stmt = select(func.count(UserModel.id)).where(UserModel.is_deleted == False)
        count_result = db.execute(count_stmt)
        total = count_result.scalar()

        stmt = select(UserModel).where(UserModel.is_deleted == False).offset(offset).limit(limit)
        result = db.execute(stmt)
        users = result.scalars().all()
    else:
        count_stmt = select(func.count(UserModel.id)).where(
            UserModel.is_deleted == False,
            or_(
                UserModel.nickname.like(f"%{search}%"),
                UserModel.username.like(f"%{search}%")
            )
        )
        count_result = db.execute(count_stmt)
        total = count_result.scalar()

        stmt = select(UserModel).where(
            UserModel.is_deleted == False,
            or_(
                UserModel.nickname.like(f"%{search}%"),
                UserModel.username.like(f"%{search}%")
            )
        ).offset(offset).limit(limit)
        result = db.execute(stmt)
        users = result.scalars().all()

    return users, total


def is_super_admin(db: Session, user_id: int) -> bool:
    """判断用户是否为超级管理员"""
    env_super_admin = os.getenv("SYSTEM_ADMIN")
    if env_super_admin:
        env_user = get_user_by_username(db, env_super_admin)
        if env_user and env_user.id == user_id:
            return True

    stmt = select(SuperAdminModel).where(SuperAdminModel.user_id == user_id)
    result = db.execute(stmt)
    super_admin = result.scalars().first()
    return super_admin is not None


def get_super_admins(db: Session) -> List[dict]:
    """获取所有额外添加的超级管理员"""
    stmt = select(UserModel, SuperAdminModel.created_at).join(
        SuperAdminModel, SuperAdminModel.user_id == UserModel.id
    )
    result = db.execute(stmt)
    admins = result.all()

    return [
        {
            "id": admin.UserModel.id,
            "username": admin.UserModel.username,
            "nickname": admin.UserModel.nickname,
            "email": admin.UserModel.email,
            "created_at": admin.created_at
        }
        for admin in admins
    ]


def add_super_admin(db: Session, user_id: int) -> bool:
    """添加超级管理员"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False

    # 检查是否已经是超级管理员
    if is_super_admin(db, user_id):
        return False

    # 检查数量上限
    count_stmt = select(func.count(SuperAdminModel.id))
    count_result = db.execute(count_stmt)
    super_admin_count = count_result.scalar()
    if super_admin_count >= 3:
        return False

    # 添加超级管理员
    super_admin = SuperAdminModel(
        user_id=user_id,
        created_at=now()
    )
    db.add(super_admin)
    db.commit()
    return True


def remove_super_admin(db: Session, user_id: int) -> bool:
    """移除超级管理员"""
    env_super_admin = os.getenv("SYSTEM_ADMIN")
    if env_super_admin:
        env_user = get_user_by_username(db, env_super_admin)
        if env_user and env_user.id == user_id:
            return False

    stmt = select(SuperAdminModel).where(SuperAdminModel.user_id == user_id)
    result = db.execute(stmt)
    super_admin = result.scalars().first()
    if not super_admin:
        return False

    db.delete(super_admin)
    db.commit()
    return True


def update_super_admins(db: Session, user_ids: List[int]) -> bool:
    """更新管理员列表（支持增删）"""
    stmt = select(SuperAdminModel.user_id)
    result = db.execute(stmt)
    existing_admins = set(result.scalars().all())

    to_remove = existing_admins - set(user_ids)
    to_add = set(user_ids) - existing_admins

    for user_id in to_remove:
        env_super_admin = os.getenv("SYSTEM_ADMIN")
        if env_super_admin:
            env_user = get_user_by_username(db, env_super_admin)
            if env_user and env_user.id == user_id:
                continue
        db.execute(delete(SuperAdminModel).where(SuperAdminModel.user_id == user_id))

    for user_id in to_add:
        if is_super_admin(db, user_id):
            continue
        count_stmt = select(func.count(SuperAdminModel.id))
        count_result = db.execute(count_stmt)
        super_admin_count = count_result.scalar()
        if super_admin_count >= 3:
            continue
        user = get_user_by_id(db, user_id)
        if not user:
            continue
        db.add(SuperAdminModel(user_id=user_id, created_at=now()))

    db.commit()
    return True
