"""
@FileName：controller.py
@Description：LLM凭证控制器
@Author：baojun.wang
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.llm.models import LLMCredential


def create_llm_credential(
    db: Session,
    model: str,
    api_key: str,
    base_url: str,
    api_protocol: str,
    workspace_id: Optional[int] = None,
    create_user: str = "",
    update_user: str = ""
) -> LLMCredential:
    """创建LLM凭证"""
    credential = LLMCredential(
        model=model,
        api_key=api_key,
        base_url=base_url,
        api_protocol=api_protocol,
        workspace_id=workspace_id,
        create_user=create_user,
        update_user=update_user
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


def get_llm_credential_by_id(db: Session, credential_id: int) -> Optional[LLMCredential]:
    """根据ID获取凭证"""
    return db.query(LLMCredential).filter(
        LLMCredential.id == credential_id,
        LLMCredential.is_deleted == 0
    ).first()


def get_llm_credential_by_id_with_key(db: Session, credential_id: int) -> Optional[LLMCredential]:
    """根据ID获取凭证（编辑用，不包含真实API密钥）"""
    return db.query(LLMCredential).filter(
        LLMCredential.id == credential_id,
        LLMCredential.is_deleted == 0
    ).first()


def get_all_llm_credentials(db: Session, workspace_id: Optional[str] = None, page_num: int = 1, page_size: int = 10) -> dict:
    """获取所有凭证（支持分页，不含已删除）"""
    query = db.query(LLMCredential).filter(
        LLMCredential.is_deleted == 0
    )
    if workspace_id is None:
        pass
    elif workspace_id == 'system':
        query = query.filter(LLMCredential.workspace_id.is_(None))
    else:
        try:
            workspace_id_int = int(workspace_id)
            query = query.filter(LLMCredential.workspace_id == workspace_id_int)
        except ValueError:
            return {'list': [], 'total': 0}
    
    total = query.count()
    offset = (page_num - 1) * page_size
    credentials = query.order_by(desc(LLMCredential.id)).offset(offset).limit(page_size).all()
    
    return {'list': credentials, 'total': total}


def get_llm_credentials_by_workspace(db: Session, workspace_id: int) -> List[LLMCredential]:
    """获取指定工作空间的凭证（包含系统级别，不含已删除）"""
    return db.query(LLMCredential).filter(
        LLMCredential.is_deleted == 0,
        LLMCredential.is_active == 1,
        or_(
            LLMCredential.workspace_id == workspace_id,
            LLMCredential.workspace_id.is_(None)
        )
    ).all()


def update_llm_credential(
    db: Session,
    credential_id: int,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    api_protocol: Optional[str] = None,
    is_active: Optional[bool] = None,
    update_user: str = ""
) -> bool:
    """更新凭证信息"""
    credential = db.query(LLMCredential).filter(LLMCredential.id == credential_id).first()
    if not credential:
        return False

    if model is not None:
        credential.model = model
    if api_key is not None and api_key.strip() != '':
        credential.api_key = api_key
    if base_url is not None:
        credential.base_url = base_url
    if api_protocol is not None:
        credential.api_protocol = api_protocol
    if is_active is not None:
        credential.is_active = int(is_active)
    credential.update_user = update_user

    db.commit()
    return True


def delete_llm_credential(db: Session, credential_id: int) -> bool:
    """删除凭证（软删除）"""
    credential = db.query(LLMCredential).filter(LLMCredential.id == credential_id).first()
    if not credential:
        return False

    credential.is_deleted = 1
    db.commit()
    return True


def get_active_credential(db: Session, workspace_id: Optional[int] = None) -> Optional[LLMCredential]:
    """获取可用的凭证（优先返回工作空间级别，若无则返回系统级别）"""
    if workspace_id is not None:
        credential = db.query(LLMCredential).filter(
            LLMCredential.workspace_id == workspace_id,
            LLMCredential.is_active == 1,
            LLMCredential.is_deleted == 0
        ).first()
        if credential:
            return credential

    return db.query(LLMCredential).filter(
        LLMCredential.workspace_id.is_(None),
        LLMCredential.is_active == 1,
        LLMCredential.is_deleted == 0
    ).first()