"""
@FileName：response.py
@Description：
@Author：baojun.wang
@Time：2025/10/28 14:45
"""
from enum import IntEnum
from typing import Optional, Any

from pydantic import BaseModel, Field


class HttpErrcode(IntEnum):
    """接口错误码枚举"""
    SUCCESS = 0
    PERMISSION_DENIED = 40003
    NOT_FOUND = 40004
    PARAMS_MISSING = 40010
    PARAMS_ERROR = 40011
    EXCEPTION = 50000


class UnifiedResponse(BaseModel):
    data: Optional[Any] = None
    code: int = Field(..., description="错误码，0表示成功")
    message: str = Field(..., description="错误信息")


def api_response(data: Any = None, code: int = 0, message: str = "处理成功") -> dict:
    """统一返回结果"""
    return {
        "data": data,
        "code": code,
        "message": message
    }
