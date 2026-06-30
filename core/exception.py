"""
@FileName：exception.py
@Description：
@Author：baojun.wang
@Time：2025/10/28 15:16
"""
# app/core/exceptions.py
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.response import UnifiedResponse, HttpErrcode


# 统一异常处理器：处理所有异常
def unified_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 处理参数验证错误（RequestValidationError）
    if isinstance(exc, RequestValidationError):
        code = HttpErrcode.PARAMS_ERROR
        message = "参数验证失败"
        # 提取详细错误信息（字段路径 + 错误描述）
        data = [
            {"field": ".".join(map(str, error["loc"])), "message": error["msg"]}
            for error in exc.errors()
        ]
    # 处理其他未捕获的异常（如代码运行时错误）
    else:
        code = HttpErrcode.EXCEPTION
        message = "服务器内部错误"
        data = None  # 生产环境可隐藏详细错误，避免泄露信息

    # 用全局响应模型包装结果
    return JSONResponse(
        content=UnifiedResponse(
            data=data,
            code=code,
            message=message
        ).model_dump()
    )
