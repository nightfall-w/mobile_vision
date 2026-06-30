"""
@FileName：models.py
@Description：
@Author：baojun.wang
@Time：2025/10/30 17:50
"""
from datetime import datetime
from typing import List

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from utils.commonlib import now


class Workspace(Base):
    """
    工作空间模型
    """
    __tablename__ = "workspace"

    workspace_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="工作空间ID")
    workspace_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="工作空间名称")
    workspace_desc: Mapped[str] = mapped_column(Text, nullable=True, comment="工作空间描述")
    create_user: Mapped[str] = mapped_column(String(100), nullable=False, comment="创建人信息")
    update_user: Mapped[str] = mapped_column(String(100), nullable=False, comment="更新人信息")
    manager: Mapped[List[str]] = mapped_column(JSON, nullable=False, comment="管理员信息")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=now,
        onupdate=now,
        comment="更新时间"
    )
    is_deleted: Mapped[int] = mapped_column(Integer, default=0, comment="是否删除(0=未删除, 1=已删除)")

    def __repr__(self) -> str:
        return (f"<Workspace(workspace_id={self.workspace_id}, "
                f"workspace_name='{self.workspace_name}')>")

    def to_dict(self, db=None) -> dict:
        """
        转换为字典
        :param db: 数据库会话，用于获取管理员用户信息
        """
        manager_info = []
        
        if db and self.manager and isinstance(self.manager, list):
            from app.user.controller import get_user_by_username
            for username in self.manager:
                user = get_user_by_username(db=db, username=username)
                if user:
                    manager_info.append({
                        "username": user.username,
                        "nickname": user.nickname
                    })
                else:
                    manager_info.append({
                        "username": username,
                        "nickname": username
                    })
        else:
            # 没有数据库连接，直接返回用户名
            if self.manager and isinstance(self.manager, list):
                manager_info = [{
                    "username": m,
                    "nickname": m
                } for m in self.manager]

        return {
            "workspace_id": self.workspace_id,
            "workspace_name": self.workspace_name,
            "workspace_desc": self.workspace_desc,
            "create_user": self.create_user,
            "update_user": self.update_user,
            "manager": manager_info,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None
        }


class MemberRole(Base):
    """
    成员角色模型
    """
    __tablename__ = "member_role"

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="角色ID")
    role_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="角色名称")
    role_description: Mapped[str] = mapped_column(Text, nullable=True, comment="角色描述")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=now,
        onupdate=now,
        comment="更新时间"
    )

    # 预定义的角色常量
    ADMIN = "管理员"
    DEVELOPER = "开发"
    TESTER = "测试"
    PRODUCT_MANAGER = "产品"
    PROJECT_MANAGER = "项目经理"

    def to_dict(self) -> dict:
        return {
            'role_id': self.role_id,
            'role_name': self.role_name,
            'role_description': self.role_description,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else None,
        }

    def __repr__(self) -> str:
        return (f"<MemberRole(role_id={self.role_id}, "
                f"role_name='{self.role_name}')>")


class WorkspaceMember(Base):
    """
    工作空间成员模型
    """
    __tablename__ = "workspace_member"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id"),
        nullable=False,
        comment="工作空间ID"
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, comment="成员username")
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("member_role.role_id"),
        nullable=False,
        comment="角色ID"
    )
    join_time: Mapped[datetime] = mapped_column(DateTime, default=now, comment="加入时间")
    is_deleted: Mapped[int] = mapped_column(Integer, default=0, comment="是否删除(0=未删除, 1=已删除)")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=now,
        onupdate=now,
        comment="更新时间"
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'workspace_id': self.workspace_id,
            'username': self.username,
            'role_id': self.role_id,
            'join_time': self.join_time.strftime('%Y-%m-%d %H:%M:%S') if self.join_time else None,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
        }

    def __repr__(self) -> str:
        return (f"<WorkspaceMember(id={self.id}, "
                f"workspace_id={self.workspace_id}, "
                f"role_id={self.role_id})>")
