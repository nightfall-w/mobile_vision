"""
@FileName：redis.py
@Description：
@Author：baojun.wang
@Time：2025/10/29 21:36
"""
import json
import os
from typing import Optional, Any

import redis
from dotenv import load_dotenv

load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
REDIS_TIMEOUT = 3600


class RedisCache:
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self.pool = None

    def init_pool(self):
        """初始化 Redis 连接池"""
        if not self.pool:
            self.pool = redis.ConnectionPool.from_url(self.redis_url)

    @property
    def client(self) -> redis.Redis:
        """获取 Redis 客户端实例"""
        if not self.pool:
            raise Exception("Redis 连接池未初始化，请先调用 init_pool()")
        return redis.Redis(connection_pool=self.pool)

    def set(
            self,
            key: str,
            value: Any,
            expire: Optional[int] = REDIS_TIMEOUT
    ):
        """设置缓存"""
        client = self.client
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value)
        client.set(key, value, ex=expire)

    def setnx(self, key: str, value: Any, expire: Optional[int] = REDIS_TIMEOUT):
        """设置缓存，如果 key 不存在则设置"""
        client = self.client
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value)
        result = client.setnx(key, value)
        if not result:
            return False
        client.expire(key, expire)
        return True

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        client = self.client
        value = client.get(key)
        print(value)
        if not value:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value.decode("utf-8")

    def delete(self, key: str):
        """删除缓存"""
        client = self.client
        client.delete(key)

    def clear(self):
        """清空当前数据库缓存"""
        client = self.client
        client.flushdb()


redis_cache = RedisCache()