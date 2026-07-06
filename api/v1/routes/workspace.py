"""
@FileName：routes.py
@Description：工作空间相关API路由
@Author：baojun.wang
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.user.models import UserModel
from app.workspace.controller import (
    WorkspaceCRUD,
    create_workspace,
    get_workspace_by_id,
    get_my_manager_workspaces_with_count,
    get_my_workspaces_with_count,
    get_not_my_workspaces_with_count,
    update_workspace,
    delete_workspace,
    create_member_role,
    get_all_roles,
    get_role_by_id,
    update_role,
    delete_role,
    add_member_to_workspace,
    get_member_by_username_and_workspace,
    get_members_by_workspace_with_count,
    update_member,
    remove_member_from_workspace,
    get_workspace_with_members,
    get_workspace_statistics
)
from app.workspace.request_models import (
    CreateWorkspaceRequest,
    UpdateWorkspaceRequest,
    CreateMemberRoleRequest,
    UpdateMemberRoleRequest,
    AddMemberRequest,
    UpdateMemberRequest,
    WorkspaceListRequest,
    DeleteMemberRoleRequest,
    JoinWorkspaceRequest,
)
from core.auth_middleware import get_current_user
from core.database import get_sync_db
from core.response import api_response, HttpErrcode

router = APIRouter(prefix="/workspace", tags=["工作空间管理"])


# ========== Workspace Endpoints ==========

@router.post("/create")
def create_workspace_endpoint(
        request: CreateWorkspaceRequest,
        current_user: UserModel = Depends(get_current_user),
        db: Session = Depends(get_sync_db)
):
    """创建工作空间"""
    workspace = create_workspace(
        workspace_name=request.workspace_name,
        workspace_desc=request.workspace_desc,
        create_user=current_user.username,
        manager=request.manager,
        db=db
    )

    if not workspace:
        return api_response(code=HttpErrcode.EXCEPTION, message="创建工作空间失败")

    return api_response(
        data={
            "workspace_id": workspace.workspace_id,
            "workspace_name": workspace.workspace_name,
            "workspace_desc": workspace.workspace_desc,
            "create_user": workspace.create_user,
            "manager": workspace.manager,
            "create_time": workspace.create_time
        }
    )


@router.get("/detail")
def get_workspace_detail_endpoint(
        workspace_id: int = Query(...),
        period: str = Query('total', description="统计周期: total/today/week/month/quarter"),
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """获取工作空间详情"""
    workspace = get_workspace_by_id(workspace_id, db)

    if not workspace:
        return api_response(code=HttpErrcode.NOT_FOUND, message="工作空间不存在")

    data = workspace.to_dict(db=db)

    # 添加统计数据
    statistics = get_workspace_statistics(workspace_id, db, period=period)
    data["statistics"] = statistics

    return api_response(data=data)


@router.put("/update")
def update_workspace_endpoint(
        request: UpdateWorkspaceRequest,
        current_user: UserModel = Depends(get_current_user),
        db: Session = Depends(get_sync_db)
):
    """更新工作空间"""
    workspace = get_workspace_by_id(request.workspace_id, db)
    if not workspace:
        return api_response(code=HttpErrcode.NOT_FOUND, message="工作空间不存在")

    success = update_workspace(
        workspace_id=request.workspace_id,
        workspace_name=request.workspace_name,
        workspace_desc=request.workspace_desc,
        update_user=current_user.username,
        manager=request.manager,
        db=db
    )

    if not success:
        return api_response(code=HttpErrcode.EXCEPTION, message="更新工作空间失败")

    return api_response(message="更新成功")


@router.delete("/delete")
def delete_workspace_endpoint(
        workspace_id: int = Query(...),
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """删除工作空间"""
    workspace = get_workspace_by_id(workspace_id, db)
    if not workspace:
        return api_response(code=HttpErrcode.NOT_FOUND, message="工作空间不存在")

    success = delete_workspace(workspace_id, db)
    if not success:
        return api_response(code=HttpErrcode.EXCEPTION, message="删除工作空间失败")

    return api_response(message="删除成功")


@router.post("/my/manage/list")
def list_my_manage_workspaces_endpoint(
        request: WorkspaceListRequest,
        current_user: UserModel = Depends(get_current_user),
        db: Session = Depends(get_sync_db)
):
    """获取我管理的工作空间列表"""
    limit = request.page_size
    offset = (request.page_num - 1) * request.page_size
    workspaces, total = get_my_manager_workspaces_with_count(
        username=current_user.username,
        workspace_name=request.workspace_name,
        limit=limit,
        offset=offset,
        db=db
    )

    data = {
        "workspaces": [ws.to_dict(db=db) for ws in workspaces],
        "total": total
    }
    return api_response(data=data)


@router.post("/my/list")
def list_my_workspaces_endpoint(
        request: WorkspaceListRequest,
        current_user: UserModel = Depends(get_current_user),
        db: Session = Depends(get_sync_db)
):
    """获取我所在的工作空间列表"""
    limit = request.page_size
    offset = (request.page_num - 1) * request.page_size
    workspaces, total = get_my_workspaces_with_count(
        username=current_user.username,
        workspace_name=request.workspace_name,
        limit=limit,
        offset=offset,
        db=db
    )

    data = {
        "workspaces": [ws.to_dict(db=db) for ws in workspaces],
        "total": total
    }
    return api_response(data=data)


@router.post("/not-my/list")
def list_not_my_workspaces_endpoint(
        request: WorkspaceListRequest,
        current_user: UserModel = Depends(get_current_user),
        db: Session = Depends(get_sync_db)
):
    """获取我不在的工作空间列表"""
    limit = request.page_size
    offset = (request.page_num - 1) * request.page_size
    workspaces, total = get_not_my_workspaces_with_count(
        username=current_user.username,
        workspace_name=request.workspace_name,
        limit=limit,
        offset=offset,
        db=db
    )

    data = {
        "workspaces": [ws.to_dict(db=db) for ws in workspaces],
        "total": total
    }
    return api_response(data=data)


# ========== Role Endpoints ==========

@router.post("/role/create")
def create_role_endpoint(
        request: CreateMemberRoleRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """创建角色"""
    role = create_member_role(
        role_name=request.role_name,
        role_description=request.role_description,
        db=db
    )

    if not role:
        return api_response(code=HttpErrcode.EXCEPTION, message="创建角色失败")

    return api_response(data=role.to_dict())


@router.get("/role/list")
def list_roles_endpoint(
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """获取角色列表"""
    roles = get_all_roles(db)
    data = [role.to_dict() for role in roles]
    return api_response(data=data)


@router.put("/role/update")
def update_role_endpoint(
        request: UpdateMemberRoleRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """更新角色"""
    role = get_role_by_id(request.role_id, db)
    if not role:
        return api_response(code=HttpErrcode.NOT_FOUND, message="角色不存在")

    success = update_role(
        role_id=request.role_id,
        role_name=request.role_name,
        role_description=request.role_description,
        db=db
    )

    if not success:
        return api_response(code=HttpErrcode.EXCEPTION, message="更新角色失败")

    return api_response(message="更新成功")


@router.delete("/role/delete")
def delete_role_endpoint(
        request: DeleteMemberRoleRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """删除角色"""
    role = get_role_by_id(request.role_id, db)
    if not role:
        return api_response(code=HttpErrcode.NOT_FOUND, message="角色不存在")

    success = delete_role(request.role_id, db)
    if not success:
        return api_response(code=HttpErrcode.EXCEPTION, message="删除角色失败，可能仍有成员使用该角色")

    return api_response(message="删除成功")


# ========== Member Endpoints ==========

@router.post("/member/join")
def member_join_workspace_endpoint(
        request: JoinWorkspaceRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """用户自行加入工作空间"""
    try:
        member = add_member_to_workspace(
            workspace_id=request.workspace_id,
            username=current_user.username,
            role_id=request.role_id,
            db=db
        )
    except Exception as e:
        return api_response(code=HttpErrcode.EXCEPTION, message=str(e))

    if not member:
        return api_response(code=HttpErrcode.EXCEPTION, message="添加成员失败")

    return api_response(data=member.to_dict())


@router.post("/member/add")
def add_member_by_admin_endpoint(
        request: AddMemberRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """管理员添加成员到工作空间"""
    try:
        member = add_member_to_workspace(
            workspace_id=request.workspace_id,
            username=request.username,
            role_id=request.role_id,
            db=db
        )
    except Exception as e:
        return api_response(code=HttpErrcode.EXCEPTION, message=str(e))

    if not member:
        return api_response(code=HttpErrcode.EXCEPTION, message="添加成员失败")

    return api_response(data=member.to_dict())


@router.get("/member/detail/")
def get_workspace_member_by_username_endpoint(
        workspace_id: int = Query(...),
        username: str = Query(...),
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """根据用户名获取工作空间成员"""
    member = get_member_by_username_and_workspace(username, workspace_id, db)
    if not member:
        return api_response(data=None)

    data = member.to_dict()
    return api_response(data=data)


@router.get("/member/list/")
def list_members_endpoint(
        workspace_id: int = Query(...),
        page_num: int = Query(1),
        page_size: int = Query(10),
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """获取工作空间成员列表"""
    workspace = get_workspace_by_id(workspace_id, db)
    if not workspace:
        return api_response(code=HttpErrcode.NOT_FOUND, message="工作空间不存在")

    members, total_count = get_members_by_workspace_with_count(workspace_id, page_size, (page_num - 1) * page_size, db)

    # 获取所有用户名，批量查询用户信息
    usernames = [member.username for member in members]
    users = db.query(UserModel).filter(UserModel.username.in_(usernames)).all() if usernames else []
    user_map = {user.username: user for user in users}

    member_details = []
    for member in members:
        role = get_role_by_id(member.role_id, db)
        user = user_map.get(member.username)
        member_details.append({
            "member_id": member.id,
            "member_info": {
                "username": member.username,
                "nickname": user.nickname if user else member.username
            },
            "role": role.to_dict() if role else None,
            "join_time": member.join_time
        })

    return api_response(data=member_details)


@router.put("/member/update")
def update_member_endpoint(
        request: UpdateMemberRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """更新成员信息"""
    crud = WorkspaceCRUD(db)
    member = crud.get_member_by_id(request.member_id)
    if not member:
        return api_response(code=HttpErrcode.NOT_FOUND, message="成员不存在")

    success = update_member(
        member_id=request.member_id,
        role_id=request.role_id,
        db=db
    )

    if not success:
        return api_response(code=HttpErrcode.EXCEPTION, message="更新成员失败")

    return api_response(message="更新成功")


@router.delete("/member/remove/{member_id}")
def remove_member_endpoint(
        member_id: int,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """移除成员"""
    crud = WorkspaceCRUD(db)
    member = crud.get_member_by_id(member_id)
    if not member:
        return api_response(code=HttpErrcode.NOT_FOUND, message="成员不存在")

    success = remove_member_from_workspace(member_id, db)
    if not success:
        return api_response(code=HttpErrcode.EXCEPTION, message="移除成员失败")

    return api_response(message="移除成功")


@router.get("/detail-with-members/{workspace_id}")
def get_workspace_with_members_endpoint(
        workspace_id: int,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user)
):
    """获取工作空间及其成员详细信息"""
    result = get_workspace_with_members(workspace_id, db)
    if not result:
        return api_response(code=HttpErrcode.NOT_FOUND, message="工作空间不存在")

    return api_response(data=result)
