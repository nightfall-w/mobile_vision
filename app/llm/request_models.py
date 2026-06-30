"""
@FileName：request_models.py
@Description：LLM凭证相关请求模型
"""
from typing import Optional

from pydantic import BaseModel


class CreateCredentialRequest(BaseModel):
    """创建凭证请求"""
    model: str
    api_key: str
    base_url: str
    api_protocol: str
    workspace_id: Optional[int] = None


class UpdateCredentialRequest(BaseModel):
    """更新凭证请求"""
    id: int
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    api_protocol: Optional[str] = None
    is_active: Optional[bool] = None
