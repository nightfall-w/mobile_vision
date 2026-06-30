"""
@FileName：models.py
@Description：
@Author：baojun.wang
@Time：2025/10/31 13:52
"""

from sqlalchemy import Column, Integer, String, Boolean

from core.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    nickname = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_deleted = Column(Boolean, default=False)


class SuperAdminModel(Base):
    __tablename__ = "super_admins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False, comment="用户ID")
    created_at = Column(String(30), nullable=False, comment="创建时间")