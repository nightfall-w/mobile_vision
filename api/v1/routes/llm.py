"""
@FileName：routes.py
@Description：LLM凭证管理API路由
@Author：baojun.wang
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from litellm import completion

from app.llm.controller import (
    create_llm_credential,
    get_llm_credential_by_id,
    get_all_llm_credentials,
    get_llm_credentials_by_workspace,
    update_llm_credential,
    delete_llm_credential
)
from app.llm.models import LLMCredential
from app.llm.request_models import CreateCredentialRequest, UpdateCredentialRequest, TestCredentialRequest
from app.user.models import UserModel
from core.response import api_response, HttpErrcode
from core.auth_middleware import get_current_user
from core.database import get_sync_db
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from app.yolo.controller import _get_user_nickname

router = APIRouter(prefix="/llm/credential", tags=["LLM凭证管理"])


# ========== Endpoints ==========

@router.post("/create")
def create_credential(
    request: CreateCredentialRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """创建LLM凭证"""
    api_protocol = request.api_protocol.lower()
    if api_protocol not in ["anthropic", "openai"]:
        return api_response(code=HttpErrcode.PARAMS_ERROR, message="api_protocol只能是anthropic或openai")

    credential = create_llm_credential(
        db=db,
        model=request.model,
        api_key=request.api_key,
        base_url=request.base_url,
        api_protocol=api_protocol,
        workspace_id=request.workspace_id,
        create_user=current_user.username,
        update_user=current_user.username
    )

    if not credential:
        return api_response(code=HttpErrcode.EXCEPTION, message="创建凭证失败")

    return api_response(data=credential.to_dict())


@router.get("/list")
def list_credentials(
    workspace_id: Optional[str] = Query(None),
    page_num: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """获取凭证列表（不显示api_key，支持分页）"""
    result = get_all_llm_credentials(db=db, workspace_id=workspace_id, page_num=page_num, page_size=page_size)
    data = []
    for credential in result['list']:
        item = credential.to_dict(hide_api_key=True)
        item['create_user_nickname'] = _get_user_nickname(credential.create_user)
        item['update_user_nickname'] = _get_user_nickname(credential.update_user)
        data.append(item)
    return api_response(data={'list': data, 'total': result['total']})


@router.get("/detail")
def get_credential_detail(
    id: int = Query(...),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """获取凭证详情（不显示api_key）"""
    credential = get_llm_credential_by_id(db=db, credential_id=id)
    if not credential:
        return api_response(code=HttpErrcode.NOT_FOUND, message="凭证不存在")

    return api_response(data=credential.to_dict(hide_api_key=True))


@router.get("/detail-with-key")
def get_credential_with_key(
    id: int = Query(...),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """获取凭证详情（用于编辑，api_key隐藏，需重新输入）"""
    credential = get_llm_credential_by_id(db=db, credential_id=id)
    if not credential:
        return api_response(code=HttpErrcode.NOT_FOUND, message="凭证不存在")

    return api_response(data=credential.to_dict(hide_api_key=True))


@router.get("/workspace-credentials")
def list_workspace_credentials(
    workspace_id: int = Query(..., description="工作空间ID"),
    page_num: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """获取指定工作空间的凭证（包括系统级别凭证），支持搜索，默认展示最新100条"""
    query = db.query(LLMCredential).filter(
        LLMCredential.is_deleted == 0,
        LLMCredential.is_active == 1,
        or_(
            LLMCredential.workspace_id == workspace_id,
            LLMCredential.workspace_id.is_(None)
        )
    )
    
    if search:
        query = query.filter(
            or_(
                LLMCredential.model.ilike(f'%{search}%'),
                LLMCredential.base_url.ilike(f'%{search}%')
            )
        )
    
    total = query.count()
    credentials = query.order_by(desc(LLMCredential.id)).offset((page_num - 1) * page_size).limit(page_size).all()
    data = [credential.to_dict(hide_api_key=True) for credential in credentials]
    return api_response(data={'list': data, 'total': total})


@router.post("/test")
def test_credential_connection(
    request: TestCredentialRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """测试LLM凭证连接是否可用"""
    try:
        model_name = f"{request.api_protocol.lower()}/{request.model}"
        completion(
            model=model_name,
            api_key=request.api_key,
            base_url=request.base_url,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=1,
            timeout=15
        )
        return api_response(message="连接成功")
    except Exception as e:
        error_msg = str(e)
        return api_response(code=HttpErrcode.EXCEPTION, message=f"连接失败: {error_msg[:200]}")


@router.put("/update")
def update_credential(
    request: UpdateCredentialRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """更新凭证信息"""
    if request.api_protocol:
        api_protocol = request.api_protocol.lower()
        if api_protocol not in ["anthropic", "openai"]:
            return api_response(code=HttpErrcode.PARAMS_ERROR, message="api_protocol只能是anthropic或openai")
    else:
        api_protocol = None

    success = update_llm_credential(
        db=db,
        credential_id=request.id,
        model=request.model,
        api_key=request.api_key,
        base_url=request.base_url,
        api_protocol=api_protocol,
        is_active=request.is_active,
        update_user=current_user.username
    )

    if not success:
        return api_response(code=HttpErrcode.EXCEPTION, message="更新凭证失败")

    return api_response(message="更新成功")


@router.delete("/delete")
def delete_credential(
    id: int = Query(...),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """删除凭证"""
    success = delete_llm_credential(db=db, credential_id=id)
    if not success:
        return api_response(code=HttpErrcode.EXCEPTION, message="删除凭证失败")

    return api_response(message="删除成功")