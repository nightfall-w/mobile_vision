"""
@FileName：setting.py
@Description：系统配置管理API路由
@Author：baojun.wang
"""
import requests
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.setting.controller import (
    get_system_config_by_id,
    get_system_configs,
    update_system_config,
    validate_config_value,
)
from app.setting.request_models import (
    CheckReachableRequest,
    SystemConfigListRequest,
    UpdateSystemConfigRequest,
)
from core.auth_middleware import get_current_super_admin
from core.database import get_sync_db
from core.response import HttpErrcode, api_response

router = APIRouter(prefix="/setting/system-config", tags=["系统配置"])


@router.post("/list")
def list_system_configs(
    request: SystemConfigListRequest,
    current_user=Depends(get_current_super_admin),
    db: Session = Depends(get_sync_db)
):
    """获取系统配置项列表（仅超级管理员）"""
    result = get_system_configs(db=db, page_num=request.page_num, page_size=request.page_size)
    return api_response(data=result)


@router.put("/update")
def update_config(
    request: UpdateSystemConfigRequest,
    current_user=Depends(get_current_super_admin),
    db: Session = Depends(get_sync_db)
):
    """更新系统配置项（仅超级管理员）"""
    config = get_system_config_by_id(db=db, config_id=request.config_id)
    if not config:
        return api_response(code=HttpErrcode.NOT_FOUND, message="配置项不存在")

    # 只在本次请求确实要改值时才校验，单独回写 verified 的场景不受影响
    if request.value is not None:
        error = validate_config_value(request.value, config.type, config.required)
        if error:
            return api_response(code=HttpErrcode.PARAMS_ERROR, message=error)

    success = update_system_config(
        db=db,
        config_id=request.config_id,
        value=request.value,
        desc=request.desc,
        verified=request.verified,
        update_user=current_user.username,
    )
    if not success:
        return api_response(code=HttpErrcode.EXCEPTION, message="更新配置项失败")

    return api_response(message="更新成功")


@router.post("/check-reachable")
def check_config_reachable(
    request: CheckReachableRequest,
    current_user=Depends(get_current_super_admin),
    db: Session = Depends(get_sync_db)
):
    """
    检查配置的地址是否可访问，并把结果写回 verified

    由后端发起请求而非浏览器，避免跨域与混合内容拦截造成的误判。
    """
    config = get_system_config_by_id(db=db, config_id=request.config_id)
    if not config:
        return api_response(code=HttpErrcode.NOT_FOUND, message="配置项不存在")

    url = (config.value or "").strip()
    if not url:
        return api_response(code=HttpErrcode.PARAMS_ERROR, message="该配置项值为空，无需检查")
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"

    try:
        resp = requests.get(url, timeout=5)
        # 5xx 说明服务端异常，视为不可用；4xx 至少证明地址能连通（可能只是需要鉴权）
        reachable = resp.status_code < 500
        message = (f"地址可访问，状态码 {resp.status_code}" if reachable
                   else f"地址不可用，服务端返回状态码 {resp.status_code}")
    except requests.RequestException as e:
        reachable = False
        message = f"地址无法访问: {str(e)[:200]}"

    update_system_config(db=db, config_id=config.id, verified=reachable,
                         update_user=current_user.username)

    return api_response(data={"reachable": reachable}, message=message)
