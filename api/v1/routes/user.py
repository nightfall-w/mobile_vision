"""
@FileName：user.py
@Description：用户相关API路由
@Author：baojun.wang
"""

from fastapi import APIRouter, Depends

from core.auth_middleware import JWTManager, get_current_user
from core.response import api_response, HttpErrcode
from core.database import get_sync_db
from sqlalchemy.orm import Session
from app.user.controller import (
    get_user_by_username,
    get_user_by_email,
    create_user,
    authenticate_user,
    get_users_with_count,
    get_super_admins,
    update_super_admins
)
from app.user.request_models import UserCreate, UserLogin, UserList

router = APIRouter(prefix="/user", tags=["用户"])


@router.post("/register")
def register_endpoint(
        user: UserCreate,
        db: Session = Depends(get_sync_db)
):
    """用户注册"""
    db_user = get_user_by_username(db, user.username)
    if db_user:
        return api_response(code=HttpErrcode.PARAMS_MISSING, message="用户名已经存在")

    db_email = get_user_by_email(db, user.email)
    if db_email:
        return api_response(code=HttpErrcode.PARAMS_MISSING, message="邮箱已被注册")

    user_instance = create_user(
        db=db,
        username=user.username,
        email=user.email,
        nickname=user.nickname,
        password=user.password
    )

    if not user_instance:
        return api_response(code=HttpErrcode.EXCEPTION, message="创建用户失败")

    data = {
        "id": user_instance.id,
        "username": user_instance.username,
        "email": user_instance.email,
        "nickname": user_instance.nickname,
        "is_deleted": user_instance.is_deleted
    }
    return api_response(data=data, code=HttpErrcode.SUCCESS)


@router.post("/login")
def login_endpoint(
        request: UserLogin,
        db: Session = Depends(get_sync_db)
):
    """用户登录"""
    user = authenticate_user(db, request.username, request.password)
    if not user:
        return api_response(code=HttpErrcode.PARAMS_MISSING, message="用户名或密码错误")

    access_token = JWTManager.create_access_token(data={"sub": user.username})
    userinfo = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "nickname": user.nickname,
        "is_deleted": user.is_deleted,
        "access_token": access_token,
        "token_type": "bearer"
    }
    return api_response(data=userinfo, code=HttpErrcode.SUCCESS)


@router.post("/users/list")
def get_users_endpoint(
        request: UserList,
        current_user=Depends(get_current_user),
        db: Session = Depends(get_sync_db)
):
    """获取用户列表"""
    offset = request.page_size * (request.page_num - 1)
    limit = request.page_size

    users, total = get_users_with_count(
        db=db,
        search=request.search,
        limit=limit,
        offset=offset
    )

    data = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "nickname": user.nickname,
            "is_deleted": user.is_deleted
        } for user in users
    ]

    response_data = {
        "list": data,
        "total": total
    }
    return api_response(code=HttpErrcode.SUCCESS, data=response_data)


@router.get("/users/me")
def read_users_me_endpoint(current_user=Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


@router.get("/users/me/items")
def read_own_items_endpoint(current_user=Depends(get_current_user)):
    """受保护资源示例"""
    return [{"item_id": "1", "owner": current_user.username}]


@router.post("/super-admin/update")
def update_admins_endpoint(
        request: dict,
        current_user=Depends(get_current_user),
        db: Session = Depends(get_sync_db)
):
    """更新管理员列表（支持增删）"""
    user_ids = request.get("user_ids", [])
    if not isinstance(user_ids, list):
        return api_response(code=HttpErrcode.PARAMS_MISSING, message="user_ids 必须是数组")

    success = update_super_admins(db, user_ids)
    if not success:
        return api_response(code=HttpErrcode.EXCEPTION, message="更新管理员列表失败")

    return api_response(code=HttpErrcode.SUCCESS, message="管理员列表更新成功")


@router.get("/super-admin/list")
def list_super_admins_endpoint(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_sync_db)
):
    """获取所有额外添加的超级管理员"""
    admins = get_super_admins(db)
    return api_response(data=admins, code=HttpErrcode.SUCCESS)
