"""
WebSocket连接管理器 - 用于任务执行状态的实时推送
"""

from datetime import datetime
from typing import Dict, Set, Optional, Callable
import asyncio
import threading
import json
from loguru import logger

from fastapi import WebSocket

# 全局事件循环，用于在同步代码中调用异步方法
_event_loop = None
_loop_thread = None

def get_event_loop():
    """获取全局事件循环"""
    global _event_loop, _loop_thread
    if _event_loop is None:
        _event_loop = asyncio.new_event_loop()
        _loop_thread = threading.Thread(target=_event_loop.run_forever, daemon=True)
        _loop_thread.start()
    return _event_loop

def run_async(coro):
    """在全局事件循环中运行协程"""
    loop = get_event_loop()
    try:
        asyncio.run_coroutine_threadsafe(coro, loop)
    except Exception as e:
        logger.error(f"运行异步任务失败: {e}")


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, task_id: int, websocket: WebSocket):
        """建立WebSocket连接"""
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        self.active_connections[task_id].add(websocket)
        logger.info(f"WebSocket连接建立: task_id={task_id}, 当前连接数={len(self.active_connections[task_id])}")

    def disconnect(self, task_id: int, websocket: WebSocket):
        """断开WebSocket连接"""
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
            logger.info(f"WebSocket连接断开: task_id={task_id}")

    async def _send_json(self, task_id: int, data: dict):
        """向指定任务的所有连接发送JSON数据（内部异步方法）"""
        if task_id not in self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections[task_id].copy():
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.warning(f"发送消息失败: {e}")
                disconnected.add(connection)

        for conn in disconnected:
            self.active_connections[task_id].discard(conn)

    def send_json(self, task_id: int, data: dict):
        """向指定任务的所有连接发送JSON数据（同步方法）"""
        run_async(self._send_json(task_id, data))

    def send_state_update(self, task_id: int, state: dict):
        """发送状态更新（同步方法）"""
        self.send_json(task_id, {
            "type": "state_update",
            "data": state,
            "timestamp": datetime.now().isoformat()
        })

    def send_log(self, task_id: int, level: str, message: str, page_structure: Optional[list] = None):
        """发送日志消息（同步方法）"""
        data = {
            "type": "log",
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if page_structure:
            data["page_structure"] = page_structure
        self.send_json(task_id, data)

    def send_screenshot(self, task_id: int, screenshot_base64: str):
        """发送截图（同步方法）"""
        self.send_json(task_id, {
            "type": "screenshot",
            "data": screenshot_base64,
            "timestamp": datetime.now().isoformat()
        })

    def send_error(self, task_id: int, error: str):
        """发送错误消息（同步方法）"""
        self.send_json(task_id, {
            "type": "error",
            "data": error,
            "timestamp": datetime.now().isoformat()
        })

    def send_complete(self, task_id: int, result: dict):
        """发送任务完成消息（同步方法）"""
        self.send_json(task_id, {
            "type": "complete",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })

    def get_connection_count(self, task_id: int) -> int:
        """获取指定任务的连接数"""
        return len(self.active_connections.get(task_id, set()))


manager = ConnectionManager()
