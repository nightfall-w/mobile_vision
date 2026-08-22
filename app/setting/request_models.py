"""
@FileName：request_models.py
@Description：系统配置相关请求模型
@Author：baojun.wang
"""
from typing import Optional

from pydantic import BaseModel


class SystemConfigListRequest(BaseModel):
    """配置项列表请求"""
    page_num: int = 1
    page_size: int = 10


class UpdateSystemConfigRequest(BaseModel):
    """
    更新配置项请求

    key/type/required 由代码定义，前端回传也不生效，仅 value/desc/verified 可改。
    """
    config_id: int
    value: Optional[str] = None
    desc: Optional[str] = None
    verified: Optional[bool] = None


class CheckReachableRequest(BaseModel):
    """连通性检查请求"""
    config_id: int
