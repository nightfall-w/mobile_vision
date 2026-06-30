"""
任务监控相关API - Redis存储 + MySQL持久化 + SSE实时推送
"""

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from core.response import api_response, HttpErrcode
from core.auth_middleware import get_current_user
from app.user.models import UserModel
from app.task_monitor.models import store
from app.task_monitor.screenshot_manager import screenshot_manager

router = APIRouter(prefix="/task", tags=["任务监控"])


@router.get("/{task_id}/state")
async def get_task_state(
    task_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """获取任务当前状态（优先从Redis读取，不存在则从MySQL读取）"""
    try:
        task_id_int = int(task_id)
    except ValueError:
        return api_response(code=HttpErrcode.PARAMS_ERROR, message="task_id必须是整数")

    state = store.get_state(task_id_int)
    if not state:
        state = store.get_from_mysql(task_id_int)
        if not state:
            return api_response(code=HttpErrcode.NOT_FOUND, message="任务不存在")
    return api_response(data=state.to_dict())


@router.get("/{task_id}/logs")
async def get_task_logs(
    task_id: str,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_user)
):
    """获取任务执行日志（优先从Redis读取）"""
    try:
        task_id_int = int(task_id)
    except ValueError:
        return api_response(code=HttpErrcode.PARAMS_ERROR, message="task_id必须是整数")

    logs = store.get_logs(task_id_int, limit)
    if not logs:
        state = store.get_state(task_id_int)
        if not state:
            state = store.get_from_mysql(task_id_int)
            if not state:
                return api_response(code=HttpErrcode.NOT_FOUND, message="任务不存在")
    # get_logs已经返回字典列表,直接返回即可
    return api_response(data=logs)


@router.get("/{task_id}/screenshot")
async def get_task_screenshot(
    task_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """获取任务当前截图"""
    try:
        task_id_int = int(task_id)
    except ValueError:
        return api_response(code=HttpErrcode.PARAMS_ERROR, message="task_id必须是整数")
    
    screenshot_base64 = screenshot_manager.get_screenshot_base64(task_id_int)
    if screenshot_base64:
        return api_response(data={"screenshot_base64": screenshot_base64})
    return api_response(data={"screenshot_base64": ""}, message="暂无截图")


@router.get("/{task_id}/stream")
async def task_stream(
    task_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """SSE实时流 - 推送任务状态和日志更新"""
    try:
        task_id_int = int(task_id)
    except ValueError:
        return api_response(code=HttpErrcode.PARAMS_ERROR, message="task_id必须是整数")
    
    async def event_generator():
        last_log_count = 0
        last_state_hash = ""

        while True:
            try:
                state = store.get_state(task_id_int)
                if state:
                    state_data = state.to_dict()
                    # 只在状态变化时推送,减少不必要的流量
                    current_state_hash = f"{state_data['status']}_{state_data['last_update']}"
                    if current_state_hash != last_state_hash:
                        yield f"event: state_update\ndata: {json.dumps(state_data)}\n\n"
                        last_state_hash = current_state_hash

                logs = store.get_logs(task_id_int, 500)
                if len(logs) > last_log_count:
                    new_logs = logs[last_log_count:]
                    # get_logs已经返回字典列表,直接序列化即可
                    for log in new_logs:
                        yield f"event: log\ndata: {json.dumps(log)}\n\n"
                    last_log_count = len(logs)

                await asyncio.sleep(1)

            except Exception as e:
                print(f"SSE stream error for task {task_id_int}: {e}")
                import traceback
                traceback.print_exc()
                # 出错后短暂等待再重试,不要直接break
                await asyncio.sleep(2)
                continue
    
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }
    
    return StreamingResponse(event_generator(), headers=headers)
