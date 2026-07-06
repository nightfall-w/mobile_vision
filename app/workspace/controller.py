"""
@FileName：controller.py
@Description：工作空间相关模型的增删改查操作
@Author：baojun.wang
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, Sequence

from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.testcase.models import TestCase
from app.testplan.models import TestPlan
from app.testtask.models import TestTask, TestJob
from app.user.controller import get_user_by_username
from app.workspace.models import Workspace, MemberRole, WorkspaceMember
from utils.custom_logging import logger


class WorkspaceCRUD:
    """工作空间相关操作类"""

    def __init__(self, db: Session):
        self.db = db

    # === Workspace 相关操作 ===
    def create_workspace(
            self,
            workspace_name: str,
            workspace_desc: Optional[str],
            create_user: str,
            update_user: str,
            manager: List[str]
    ) -> Optional[Workspace]:
        """创建工作空间"""
        try:
            workspace = Workspace(
                workspace_name=workspace_name,
                workspace_desc=workspace_desc,
                create_user=create_user,
                update_user=update_user,
                manager=manager
            )
            self.db.add(workspace)
            self.db.commit()
            self.db.refresh(workspace)
            return workspace
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"创建工作空间失败: {str(e)}")
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建工作空间异常: {str(e)}")
            return None

    def get_workspace_by_id(self, workspace_id: int) -> Optional[Workspace]:
        """根据ID获取工作空间"""
        stmt = select(Workspace).where(
            Workspace.workspace_id == workspace_id,
            Workspace.is_deleted == 0
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_my_workspaces_with_count(
            self,
            username: str,
            workspace_name: Optional[str] = None,
            limit: int = 10,
            offset: int = 0
    ) -> tuple[Sequence[Workspace], Any | None]:
        """获取我所在的工作空间列表及总数"""

        member_subquery = select(WorkspaceMember.workspace_id).where(
            WorkspaceMember.username == username,
            WorkspaceMember.is_deleted == 0
        ).distinct()

        if workspace_name:
            count_stmt = select(func.count()).select_from(Workspace).where(
                and_(
                    Workspace.workspace_id.in_(member_subquery),
                    Workspace.is_deleted == 0,
                    Workspace.workspace_name.like(f"%{workspace_name}%")
                )
            )
            stmt = select(Workspace).where(
                and_(
                    Workspace.workspace_id.in_(member_subquery),
                    Workspace.is_deleted == 0,
                    Workspace.workspace_name.like(f"%{workspace_name}%")
                )
            ).order_by(Workspace.workspace_id.desc()).limit(limit).offset(offset)
        else:
            count_stmt = select(func.count()).select_from(Workspace).where(
                and_(
                    Workspace.workspace_id.in_(member_subquery),
                    Workspace.is_deleted == 0
                )
            )
            stmt = select(Workspace).where(
                and_(
                    Workspace.workspace_id.in_(member_subquery),
                    Workspace.is_deleted == 0
                )
            ).order_by(Workspace.workspace_id.desc()).limit(limit).offset(offset)

        count_result = self.db.execute(count_stmt)
        total_count = count_result.scalar()

        # 查询当前页数据
        result = self.db.execute(stmt)
        workspaces = result.scalars().all()

        return workspaces, total_count

    def get_not_my_workspaces_with_count(
            self,
            username: str,
            workspace_name: Optional[str] = None,
            limit: int = 10,
            offset: int = 0
    ) -> tuple[Sequence[Workspace], Any | None]:
        """获取我不在的工作空间列表及总数"""

        member_subquery = select(WorkspaceMember.workspace_id).where(
            WorkspaceMember.username == username,
            WorkspaceMember.is_deleted == 0
        ).distinct()

        if workspace_name:
            count_stmt = select(func.count()).select_from(Workspace).where(
                and_(
                    ~Workspace.workspace_id.in_(member_subquery),
                    Workspace.is_deleted == 0,
                    Workspace.workspace_name.like(f"%{workspace_name}%")
                )
            )
            stmt = select(Workspace).where(
                and_(
                    ~Workspace.workspace_id.in_(member_subquery),
                    Workspace.is_deleted == 0,
                    Workspace.workspace_name.like(f"%{workspace_name}%")
                )
            ).order_by(Workspace.workspace_id.desc()).limit(limit).offset(offset)
        else:
            count_stmt = select(func.count()).select_from(Workspace).where(
                and_(
                    ~Workspace.workspace_id.in_(member_subquery),
                    Workspace.is_deleted == 0
                )
            )
            stmt = select(Workspace).where(
                and_(
                    ~Workspace.workspace_id.in_(member_subquery),
                    Workspace.is_deleted == 0
                )
            ).order_by(Workspace.workspace_id.desc()).limit(limit).offset(offset)

        count_result = self.db.execute(count_stmt)
        total_count = count_result.scalar()

        result = self.db.execute(stmt)
        workspaces = result.scalars().all()

        return workspaces, total_count

    def get_my_manager_workspaces_with_count(
            self,
            username: str,
            workspace_name: Optional[str] = None,
            limit: int = 10,
            offset: int = 0
    ) -> Tuple[List[Workspace], int]:
        """获取我管理的工作空间列表及总数"""

        if workspace_name:
            count_stmt = select(func.count()).select_from(Workspace).where(
                and_(
                    func.json_contains(Workspace.manager, f'"{username}"'),
                    Workspace.is_deleted == 0,
                    Workspace.workspace_name.like(f"%{workspace_name}%")
                )
            )
            stmt = select(Workspace).where(
                and_(
                    func.json_contains(Workspace.manager, f'"{username}"'),
                    Workspace.is_deleted == 0,
                    Workspace.workspace_name.like(f"%{workspace_name}%")
                )
            ).order_by(Workspace.workspace_id.desc()).limit(limit).offset(offset)
        else:
            count_stmt = select(func.count()).select_from(Workspace).where(
                and_(
                    func.json_contains(Workspace.manager, f'"{username}"'),
                    Workspace.is_deleted == 0
                )
            )
            stmt = select(Workspace).where(
                and_(
                    func.json_contains(Workspace.manager, f'"{username}"'),
                    Workspace.is_deleted == 0
                )
            ).order_by(Workspace.workspace_id.desc()).limit(limit).offset(offset)

        count_result = self.db.execute(count_stmt)
        total_count = count_result.scalar()

        # 查询当前页数据
        result = self.db.execute(stmt)
        workspaces = result.scalars().all()

        return workspaces, total_count

    def update_workspace(
            self,
            workspace_id: int,
            workspace_name: Optional[str] = None,
            workspace_desc: Optional[str] = None,
            update_user: str = None,
            manager: Optional[List[str]] = None
    ) -> bool:
        """更新工作空间"""
        try:
            stmt = update(Workspace).where(Workspace.workspace_id == workspace_id)
            values = {}

            if workspace_name is not None:
                values["workspace_name"] = workspace_name
            if workspace_desc is not None:
                values["workspace_desc"] = workspace_desc
            if update_user is not None:
                values["update_user"] = update_user
            if manager is not None:
                values["manager"] = manager

            if values:
                stmt = stmt.values(**values)
                self.db.execute(stmt)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新工作空间失败: {str(e)}")
            return False

    def delete_workspace(self, workspace_id: int) -> bool:
        """删除工作空间（软删除）"""
        try:
            stmt = update(Workspace).where(Workspace.workspace_id == workspace_id).values(is_deleted=1)
            self.db.execute(stmt)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除工作空间失败: {str(e)}")
            return False

    # === MemberRole 相关操作 ===
    def create_member_role(
            self,
            role_name: str,
            role_description: Optional[str] = None
    ) -> Optional[MemberRole]:
        """创建成员角色"""
        try:
            role = MemberRole(
                role_name=role_name,
                role_description=role_description
            )
            self.db.add(role)
            self.db.commit()
            self.db.refresh(role)
            return role
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"创建成员角色失败: {str(e)}")
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建成员角色异常: {str(e)}")
            return None

    def get_role_by_id(self, role_id: int) -> Optional[MemberRole]:
        """根据ID获取角色"""
        stmt = select(MemberRole).where(MemberRole.role_id == role_id)
        result = self.db.execute(stmt)
        return result.scalars().first()

    # def get_role_by_name(self, role_name: str) -> Optional[MemberRole]:
    #     """根据名称获取角色"""
    #     stmt = select(MemberRole).where(MemberRole.role_name == role_name)
    #     result = self.db.execute(stmt)
    #     return result.scalars().first()

    def get_all_roles(self) -> Sequence[MemberRole]:
        """获取所有角色"""
        stmt = select(MemberRole)
        result = self.db.execute(stmt)
        return result.scalars().all()

    def update_role(
            self,
            role_id: int,
            role_name: Optional[str] = None,
            role_description: Optional[str] = None
    ) -> bool:
        """更新角色信息"""
        try:
            stmt = update(MemberRole).where(MemberRole.role_id == role_id)
            values = {}

            if role_name is not None:
                values["role_name"] = role_name
            if role_description is not None:
                values["role_description"] = role_description

            if values:
                stmt = stmt.values(**values)
                self.db.execute(stmt)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新角色失败: {str(e)}")
            return False

    def delete_role(self, role_id: int) -> bool:
        """删除角色"""
        try:
            member_count = self.count_members_by_role(role_id)
            if member_count > 0:
                logger.warning(f"角色ID {role_id} 仍有 {member_count} 个成员在使用，无法删除")
                return False

            stmt = delete(MemberRole).where(MemberRole.role_id == role_id)
            self.db.execute(stmt)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除角色失败: {str(e)}")
            return False

    # === WorkspaceMember 相关操作 ===
    def add_member_to_workspace(
            self,
            workspace_id: int,
            username: str,
            role_id: int
    ) -> Optional[WorkspaceMember]:
        """添加成员到工作空间"""
        try:
            # 检查工作空间和角色是否存在
            workspace = self.get_workspace_by_id(workspace_id)
            if not workspace:
                logger.error(f"工作空间 {workspace_id} 不存在")
                raise Exception(f"工作空间 {workspace_id} 不存在")

            role = self.get_role_by_id(role_id)
            if not role:
                logger.error(f"角色 {role_id} 不存在")
                raise Exception(f"角色ID {role_id} 不存在")

            # 检查用户是否存在
            from app.user.models import UserModel
            user = self.db.execute(
                select(UserModel).where(UserModel.username == username)
            ).scalars().first()
            if not user:
                logger.error(f"用户 {username} 不存在")
                raise Exception(f"用户 {username} 不存在")

            # 检查是否已在该工作空间中（含软删除）
            member = self.db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.username == username,
                    WorkspaceMember.workspace_id == workspace_id
                )
            ).scalars().first()
            if member:
                if member.is_deleted == 0:
                    logger.error(f"用户 {username} 已经在此工作空间中")
                    raise Exception(f"用户 {user.nickname}({username}) 已经在此工作空间中")
                # 软删除的成员重新加入，恢复记录
                member.is_deleted = 0
                member.role_id = role_id
                self.db.commit()
                self.db.refresh(member)
                return member

            member = WorkspaceMember(
                workspace_id=workspace_id,
                username=username,
                role_id=role_id
            )
            self.db.add(member)
            self.db.commit()
            self.db.refresh(member)
            return member
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"添加成员到工作空间失败: {str(e)}")
            raise Exception("添加成员到工作空间失败")
        except Exception as e:
            self.db.rollback()
            logger.error(f"添加成员到工作空间异常: {str(e)}")
            raise

    def get_member_by_id(self, member_id: int) -> Optional[WorkspaceMember]:
        """根据ID获取成员"""
        stmt = select(WorkspaceMember).where(WorkspaceMember.id == member_id, WorkspaceMember.is_deleted == 0)
        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_member_by_username_and_workspace(self, username: str, workspace_id: int) -> Optional[WorkspaceMember]:
        """根据用户名与workspace获取成员"""
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.username == username,
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.is_deleted == 0
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_members_by_workspace_with_count(self, workspace_id: int, limit: int = 10, offset: int = 0) -> tuple[
        Sequence[WorkspaceMember], Any | None]:
        """获取工作空间的成员及总数"""
        count_stmt = select(func.count()).select_from(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.is_deleted == 0)
        count_result = self.db.execute(count_stmt)
        total_count = count_result.scalar()

        stmt = select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id,
                                             WorkspaceMember.is_deleted == 0).limit(limit).offset(offset)
        result = self.db.execute(stmt)
        members = result.scalars().all()

        return members, total_count

    # def get_members_by_role(self, role_id: int) -> Sequence[WorkspaceMember]:
    #     """根据角色获取成员"""
    #     stmt = select(WorkspaceMember).where(WorkspaceMember.role_id == role_id)
    #     result = self.db.execute(stmt)
    #     return result.scalars().all()

    def update_member(
            self,
            member_id: int,
            role_id: Optional[int] = None
    ) -> bool:
        """更新成员信息"""
        try:
            stmt = update(WorkspaceMember).where(WorkspaceMember.id == member_id)
            values = {}

            if role_id is not None:
                role = self.get_role_by_id(role_id)
                if not role:
                    logger.error(f"角色 {role_id} 不存在")
                    return False
                values["role_id"] = role_id

            if values:
                stmt = stmt.values(**values)
                self.db.execute(stmt)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新成员失败: {str(e)}")
            return False

    def remove_member_from_workspace(self, member_id: int) -> bool:
        """从工作空间移除成员（软删除）"""
        try:
            stmt = update(WorkspaceMember).where(WorkspaceMember.id == member_id).values(is_deleted=1)
            self.db.execute(stmt)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"移除成员失败: {str(e)}")
            return False

    def count_members_by_role(self, role_id: int) -> int:
        """统计使用某角色的成员数量"""
        stmt = select(WorkspaceMember).where(WorkspaceMember.role_id == role_id)
        result = self.db.execute(stmt)
        return len(result.scalars().all())

    # === 关联查询操作 ===
    def get_workspace_with_members(self, workspace_id: int) -> Optional[Dict]:
        """获取工作空间及其成员信息"""
        workspace = self.get_workspace_by_id(workspace_id)
        if not workspace:
            return None

        members, total_count = self.get_members_by_workspace_with_count(workspace_id)

        member_details = []

        for member in members:
            role = self.get_role_by_id(member.role_id)
            userinfo = get_user_by_username(db=self.db, username=member.username)
            member_details.append({
                "member_id": member.id,
                "member_info": {
                    "username": userinfo.username,
                    "nickname": userinfo.nickname,
                    "email": userinfo.email,
                    "is_deleted": userinfo.is_deleted
                },
                "role": {
                    "role_id": role.role_id if role else None,
                    "role_name": role.role_name if role else None,
                    "role_description": role.role_description if role else None
                },
                "join_time": member.join_time,
                "create_time": member.create_time
            })

        return {
            "workspace": {
                "workspace_id": workspace.workspace_id,
                "workspace_name": workspace.workspace_name,
                "workspace_desc": workspace.workspace_desc,
                "create_user": workspace.create_user,
                "update_user": workspace.update_user,
                "manager": workspace.manager,
                "create_time": workspace.create_time,
                "update_time": workspace.update_time
            },
            "members": member_details
        }

    # TODO: 未使用 - 获取成员详细信息（包含工作空间和角色信息）
    # def get_member_with_details(self, member_id: int) -> Optional[Dict]:
    #     """获取成员详细信息（包含工作空间和角色信息）"""
    #     member = self.get_member_by_id(member_id)
    #     if not member:
    #         return None
    #
    #     workspace = self.get_workspace_by_id(member.workspace_id)
    #     role = self.get_role_by_id(member.role_id)
    #
    #     userinfo = get_user_by_username(db=self.db, username=member.username)
    #     return {
    #         "member": {
    #             "member_id": member.id,
    #             "member_info": {
    #                 "username": userinfo.username,
    #                 "nickname": userinfo.nickname,
    #                 "email": userinfo.email,
    #                 "is_deleted": userinfo.is_deleted
    #             },
    #             "join_time": member.join_time,
    #             "create_time": member.create_time,
    #             "update_time": member.update_time
    #         },
    #         "workspace": {
    #             "workspace_id": workspace.workspace_id if workspace else None,
    #             "workspace_name": workspace.workspace_name if workspace else None
    #         },
    #         "role": {
    #             "role_id": role.role_id if role else None,
    #             "role_name": role.role_name if role else None,
    #             "role_description": role.role_description if role else None
    #         }
    #     }
    #


# 为路由提供便捷函数（保持与旧服务层兼容的接口）
def create_workspace(workspace_name: str, workspace_desc: str, create_user: str, manager: list, db: Session):
    crud = WorkspaceCRUD(db)
    return crud.create_workspace(workspace_name, workspace_desc, create_user, create_user, manager)


def get_workspace_by_id(workspace_id: int, db: Session):
    crud = WorkspaceCRUD(db)
    workspace = crud.get_workspace_by_id(workspace_id)
    return workspace


def get_my_manager_workspaces_with_count(username: str, workspace_name: str = None, limit: int = 10, offset: int = 0,
                                         db: Session = None):
    crud = WorkspaceCRUD(db)
    return crud.get_my_manager_workspaces_with_count(username, workspace_name, limit, offset)


def get_my_workspaces_with_count(username: str, workspace_name: str = None, limit: int = 10, offset: int = 0,
                                 db: Session = None):
    crud = WorkspaceCRUD(db)
    return crud.get_my_workspaces_with_count(username, workspace_name, limit, offset)


def get_not_my_workspaces_with_count(username: str, workspace_name: str = None, limit: int = 10, offset: int = 0,
                                     db: Session = None):
    crud = WorkspaceCRUD(db)
    return crud.get_not_my_workspaces_with_count(username, workspace_name, limit, offset)


def update_workspace(workspace_id: int, workspace_name: str = None, workspace_desc: str = None, update_user: str = None,
                     manager: list = None, db: Session = None):
    crud = WorkspaceCRUD(db)
    return crud.update_workspace(workspace_id, workspace_name, workspace_desc, update_user, manager)


def delete_workspace(workspace_id: int, db: Session):
    crud = WorkspaceCRUD(db)
    return crud.delete_workspace(workspace_id)


def create_member_role(role_name: str, role_description: str = None, db: Session = None):
    crud = WorkspaceCRUD(db)
    return crud.create_member_role(role_name, role_description)


def get_all_roles(db: Session):
    crud = WorkspaceCRUD(db)
    return crud.get_all_roles()


def get_role_by_id(role_id: int, db: Session):
    crud = WorkspaceCRUD(db)
    return crud.get_role_by_id(role_id)


def update_role(role_id: int, role_name: str = None, role_description: str = None, db: Session = None):
    crud = WorkspaceCRUD(db)
    return crud.update_role(role_id, role_name, role_description)


def delete_role(role_id: int, db: Session):
    crud = WorkspaceCRUD(db)
    return crud.delete_role(role_id)


def add_member_to_workspace(workspace_id: int, username: str, role_id: int, db: Session):
    crud = WorkspaceCRUD(db)
    return crud.add_member_to_workspace(workspace_id, username, role_id)


def get_member_by_username_and_workspace(username: str, workspace_id: int, db: Session):
    crud = WorkspaceCRUD(db)
    return crud.get_member_by_username_and_workspace(username, workspace_id)


def get_members_by_workspace_with_count(workspace_id: int, limit: int = 10, offset: int = 0, db: Session = None):
    crud = WorkspaceCRUD(db)
    return crud.get_members_by_workspace_with_count(workspace_id, limit, offset)


def update_member(member_id: int, role_id: int = None, db: Session = None):
    crud = WorkspaceCRUD(db)
    return crud.update_member(member_id, role_id)


def remove_member_from_workspace(member_id: int, db: Session):
    crud = WorkspaceCRUD(db)
    return crud.remove_member_from_workspace(member_id)


def get_workspace_with_members(workspace_id: int, db: Session):
    crud = WorkspaceCRUD(db)
    return crud.get_workspace_with_members(workspace_id)


def get_workspace_statistics(workspace_id: int, db: Session, period: str = 'total'):
    """获取工作空间统计数据"""
    case_count = db.execute(
        select(func.count()).select_from(TestCase).where(TestCase.workspace_id == workspace_id)
    ).scalar() or 0

    case_by_status = db.execute(
        select(TestCase.status, func.count()).select_from(TestCase)
        .where(TestCase.workspace_id == workspace_id)
        .group_by(TestCase.status)
    ).all()

    case_by_level = db.execute(
        select(TestCase.level, func.count()).select_from(TestCase)
        .where(TestCase.workspace_id == workspace_id)
        .group_by(TestCase.level)
    ).all()

    plan_count = db.execute(
        select(func.count()).select_from(TestPlan).where(TestPlan.workspace_id == workspace_id)
    ).scalar() or 0

    active_plan_count = db.execute(
        select(func.count()).select_from(TestPlan)
        .where(TestPlan.workspace_id == workspace_id, TestPlan.is_deleted == 0)
    ).scalar() or 0

    plan_ids = [p[0] for p in db.execute(
        select(TestPlan.plan_id).where(TestPlan.workspace_id == workspace_id)
    ).all()]

    execution_count = 0
    execution_by_status = {}
    if plan_ids:
        execution_count = db.execute(
            select(func.count()).select_from(TestJob)
            .join(TestTask, TestJob.task_id == TestTask.task_id)
            .where(TestTask.plan_id.in_(plan_ids))
        ).scalar() or 0

        execution_by_status = dict(db.execute(
            select(TestJob.status, func.count()).select_from(TestJob)
            .join(TestTask, TestJob.task_id == TestTask.task_id)
            .where(TestTask.plan_id.in_(plan_ids))
            .group_by(TestJob.status)
        ).all())

    member_count = db.execute(
        select(func.count()).select_from(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
    ).scalar() or 0

    now = datetime.now()

    def _get_period_start(key: str):
        if key == 'today':
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif key == 'week':
            return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        elif key == 'month':
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif key == 'quarter':
            q = (now.month - 1) // 3
            return datetime(now.year, q * 3 + 1, 1)
        return None

    def _period_counts(since):
        c = db.execute(
            select(func.count()).select_from(TestCase)
            .where(TestCase.workspace_id == workspace_id, TestCase.create_time >= since)
        ).scalar() or 0
        e = s = 0
        if plan_ids:
            e = db.execute(
                select(func.count()).select_from(TestJob)
                .join(TestTask, TestJob.task_id == TestTask.task_id)
                .where(TestTask.plan_id.in_(plan_ids), TestJob.create_time >= since)
            ).scalar() or 0
            s = db.execute(
                select(func.count()).select_from(TestJob)
                .join(TestTask, TestJob.task_id == TestTask.task_id)
                .where(TestTask.plan_id.in_(plan_ids), TestJob.create_time >= since,
                       TestJob.status == 'completed')
            ).scalar() or 0
        return c, e, s

    def _period_active_cases(since):
        if not plan_ids:
            return 0
        return db.execute(
            select(func.count(TestJob.case_id.distinct())).select_from(TestJob)
            .join(TestTask, TestJob.task_id == TestTask.task_id)
            .where(TestTask.plan_id.in_(plan_ids), TestJob.create_time >= since)
        ).scalar() or 0

    def _period_active_plans(since):
        if not plan_ids:
            return 0
        return db.execute(
            select(func.count(TestTask.plan_id.distinct())).select_from(TestJob)
            .join(TestTask, TestJob.task_id == TestTask.task_id)
            .where(TestTask.plan_id.in_(plan_ids), TestJob.create_time >= since)
        ).scalar() or 0

    def _period_new_plans(since):
        return db.execute(
            select(func.count()).select_from(TestPlan)
            .where(TestPlan.workspace_id == workspace_id, TestPlan.create_time >= since)
        ).scalar() or 0

    def _period_case_by_level(since):
        rows = db.execute(
            select(TestCase.level, func.count()).select_from(TestCase)
            .where(TestCase.workspace_id == workspace_id, TestCase.create_time >= since)
            .group_by(TestCase.level)
        ).all()
        return dict(rows)

    def _period_execution_by_status(since):
        if not plan_ids:
            return {}
        rows = db.execute(
            select(TestJob.status, func.count()).select_from(TestJob)
            .join(TestTask, TestJob.task_id == TestTask.task_id)
            .where(TestTask.plan_id.in_(plan_ids), TestJob.create_time >= since)
            .group_by(TestJob.status)
        ).all()
        return dict(rows)

    # 全量活跃数
    total_active_cases = db.execute(
        select(func.count(TestJob.case_id.distinct())).select_from(TestJob)
        .join(TestTask, TestJob.task_id == TestTask.task_id)
        .where(TestTask.plan_id.in_(plan_ids))
    ).scalar() or 0 if plan_ids else 0

    total_active_plans = len(plan_ids)

    period_start = _get_period_start(period)
    if period == 'total' or period_start is None:
        new_cases = case_count
        new_plans = plan_count
        active_cases = total_active_cases
        active_plans = total_active_plans
        period_executions = execution_count
        period_success = dict(execution_by_status).get('completed', 0)
        period_case_level = dict(case_by_level)
        period_exec_status = execution_by_status
    else:
        new_cases, period_executions, period_success = _period_counts(period_start)
        new_plans = _period_new_plans(period_start)
        active_cases = _period_active_cases(period_start)
        active_plans = _period_active_plans(period_start)
        period_case_level = _period_case_by_level(period_start)
        period_exec_status = _period_execution_by_status(period_start)

    success_rate = round((period_success / period_executions * 100) if period_executions > 0 else 0)

    return {
        "total_cases": case_count,
        "total_plans": plan_count,
        "total_executions": execution_count,
        "total_members": member_count,

        "case_by_level": dict(case_by_level),
        "execution_by_status": execution_by_status,

        "period_data": {
            "new_cases": new_cases,
            "active_cases": active_cases,
            "new_plans": new_plans,
            "active_plans": active_plans,
            "executions": period_executions,
            "success_rate": success_rate,
        },

        "period_charts": {
            "case_by_level": period_case_level,
            "execution_by_status": period_exec_status,
        },
    }
