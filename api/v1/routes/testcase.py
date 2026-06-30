"""
@FileName：routes.py
@Description：用例管理相关API路由
@Author：baojun.wang
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.testcase.controller import TestCaseCRUD
from app.testcase.request_models import (
    CreateTestCaseRequest,
    UpdateTestCaseRequest
)
from app.user.models import UserModel
from core.response import api_response, HttpErrcode
from core.auth_middleware import get_current_user
from core.database import get_sync_db

router = APIRouter(prefix="/testcase", tags=["用例管理"])

def get_user_nickname(db: Session, username: str) -> str:
    """根据用户名获取用户昵称"""
    stmt = select(UserModel.nickname).where(UserModel.username == username)
    result = db.execute(stmt)
    nickname = result.scalar()
    return nickname if nickname else username


@router.post("/create")
def create_case(
    request: CreateTestCaseRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """创建用例"""
    crud = TestCaseCRUD(db)
    case = crud.create_case(
        workspace_id=request.workspace_id,
        case_name=request.case_name,
        case_desc=request.case_desc,
        content=request.content,
        usage_instructions=request.usage_instructions,
        author=current_user.username,
        level=request.level,
        status=request.status
    )

    if not case:
        return api_response(code=HttpErrcode.EXCEPTION, message="创建用例失败")

    return api_response(data=case.to_dict())


@router.get("/detail")
def get_case_detail(
    case_id: int = Query(...),
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user)
):
    """获取用例详情"""
    crud = TestCaseCRUD(db)
    case = crud.get_case_by_id(case_id)

    if not case:
        return api_response(code=HttpErrcode.NOT_FOUND, message="用例不存在")

    return api_response(data=case.to_dict())


@router.put("/update")
def update_case(
    request: UpdateTestCaseRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """更新用例"""
    crud = TestCaseCRUD(db)
    case = crud.get_case_by_id(request.case_id)
    if not case:
        return api_response(code=HttpErrcode.NOT_FOUND, message="用例不存在")

    success = crud.update_case(
        case_id=request.case_id,
        case_name=request.case_name,
        case_desc=request.case_desc,
        content=request.content,
        usage_instructions=request.usage_instructions,
        updater=current_user.username,
        level=request.level,
        status=request.status
    )

    if not success:
        return api_response(code=HttpErrcode.EXCEPTION, message="更新用例失败")

    return api_response(message="更新成功")


@router.delete("/delete")
def delete_case(
    case_id: int = Query(...),
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user)
):
    """删除用例"""
    crud = TestCaseCRUD(db)
    case = crud.get_case_by_id(case_id)
    if not case:
        return api_response(code=HttpErrcode.NOT_FOUND, message="用例不存在")

    success = crud.delete_case(case_id)
    if not success:
        return api_response(code=HttpErrcode.EXCEPTION, message="删除用例失败")

    return api_response(message="删除成功")


@router.get("/list")
def list_cases(
    workspace_id: int = Query(...),
    page_num: int = Query(1),
    page_size: int = Query(10),
    case_name: str = Query(None),
    status: str = Query(None),
    level: str = Query(None),
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user)
):
    """获取用例列表"""
    crud = TestCaseCRUD(db)
    limit = page_size
    offset = (page_num - 1) * page_size
    cases, total = crud.get_cases_by_workspace_with_count(
        workspace_id=workspace_id,
        case_name=case_name,
        status=status,
        level=level,
        limit=limit,
        offset=offset
    )

    cases_data = []
    for case in cases:
        case_dict = case.to_dict()
        case_dict["updater_name"] = get_user_nickname(db, case.updater)
        cases_data.append(case_dict)

    data = {
        "cases": cases_data,
        "total": total
    }
    return api_response(data=data)
