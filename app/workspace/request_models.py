"""
@FileName：request_models.py
@Description：工作空间相关请求模型
@Author：baojun.wang
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from app.user.request_models import PaginationRequestModel


class CreateWorkspaceRequest(BaseModel):
    """创建工作空间请求"""
    workspace_name: str
    workspace_desc: Optional[str] = None
    manager: List[str]


class UpdateWorkspaceRequest(BaseModel):
    """更新工作空间请求"""
    workspace_id: int
    workspace_name: Optional[str] = None
    workspace_desc: Optional[str] = None
    manager: Optional[List[str]] = None
    delete_manager_info_list: Optional[List[Dict[str, Any]]] = None


class DeleteWorkspaceRequest(BaseModel):
    """删除工作空间请求"""
    workspace_id: int


class DetailsWorkspaceRequest(BaseModel):
    """工作空间详情请求"""
    workspace_id: int


class CreateMemberRoleRequest(BaseModel):
    """创建成员角色请求"""
    role_name: str
    role_description: Optional[str] = None


class UpdateMemberRoleRequest(BaseModel):
    """更新成员角色请求"""
    role_id: int
    role_name: Optional[str] = None
    role_description: Optional[str] = None


class DeleteMemberRoleRequest(BaseModel):
    """删除成员角色请求"""
    role_id: int


class AddMemberRequest(BaseModel):
    """添加成员请求"""
    workspace_id: int
    username: str
    role_id: int


class JoinWorkspaceRequest(BaseModel):
    """自行加入工作空间请求"""
    workspace_id: int
    role_id: int


class UpdateMemberRequest(BaseModel):
    """更新成员请求"""
    member_id: int
    role_id: int


class WorkspaceListRequest(PaginationRequestModel):
    """工作空间列表请求"""
    workspace_name: Optional[str] = None


class MemberListRequest(PaginationRequestModel):
    """成员列表请求"""
    workspace_id: int
    username: Optional[str] = None
