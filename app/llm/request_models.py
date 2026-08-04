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
    # None 表示系统级别，是合法取值；用 model_fields_set 区分"未传"与"传了null"
    workspace_id: Optional[int] = None


class TestCredentialRequest(BaseModel):
    """测试凭证连接请求"""
    model: str
    api_key: Optional[str] = None
    base_url: str
    api_protocol: str
    credential_id: Optional[int] = None  # 编辑时未填写api_key，则使用该凭证库中已保存的密钥
