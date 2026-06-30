"""
截图管理器 - 用于存储和获取任务截图
"""

from typing import Dict, Optional
import base64
import os

from core.redis import redis_cache


class ScreenshotManager:
    """截图管理器"""
    
    SCREENSHOT_KEY_PREFIX = "task:screenshot:"
    
    def __init__(self):
        self._redis = None
        self._local_cache: Dict[int, str] = {}  # task_id -> screenshot_path
    
    def _get_redis(self):
        """获取Redis客户端"""
        if not self._redis:
            redis_cache.init_pool()
            self._redis = redis_cache.client
        return self._redis
    
    def _key(self, task_id: int) -> str:
        """生成截图存储键"""
        return f"{self.SCREENSHOT_KEY_PREFIX}{task_id}"
    
    def cache_screenshot_path(self, task_id: int, screenshot_path: str):
        """缓存截图路径"""
        self._local_cache[task_id] = screenshot_path
    
    def get_screenshot_base64(self, task_id: int) -> str:
        """获取截图的base64编码"""
        if task_id in self._local_cache:
            screenshot_path = self._local_cache[task_id]
            if os.path.exists(screenshot_path):
                try:
                    with open(screenshot_path, "rb") as f:
                        return base64.b64encode(f.read()).decode("utf-8")
                except Exception as e:
                    print(f"读取截图失败: {e}")
        
        redis_client = self._get_redis()
        data = redis_client.get(self._key(task_id))
        if data:
            return data.decode("utf-8")
        
        return ""
    
    def save_screenshot(self, task_id: int, screenshot_base64: str):
        """保存截图到Redis"""
        redis_client = self._get_redis()
        redis_client.set(self._key(task_id), screenshot_base64, ex=3600)
    
    def clear_screenshot(self, task_id: int):
        """清除截图缓存"""
        self._local_cache.pop(task_id, None)
        redis_client = self._get_redis()
        redis_client.delete(self._key(task_id))


screenshot_manager = ScreenshotManager()
