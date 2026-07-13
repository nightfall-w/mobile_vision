"""
设备任务队列管理工具
使用 Redis 实现设备任务排队
以 device_android_id 作为队列标识（比 ADB serial 更稳定）
"""

import os
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '') or None

DEVICE_QUEUE_PREFIX = "device_android_queue:"


_redis_pool = None


def get_redis_client():
    """获取 Redis 客户端（使用连接池 + keepalive）"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=10,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return redis.Redis(connection_pool=_redis_pool)


def get_device_queue_key(android_id: str) -> str:
    """获取设备队列的 Redis key"""
    return f"{DEVICE_QUEUE_PREFIX}{android_id}"


def add_task_to_device_queue(android_id: str, task_id: int) -> int:
    """
    添加任务到设备等待队列
    返回队列长度
    """
    rds = get_redis_client()
    queue_key = get_device_queue_key(android_id)
    return rds.rpush(queue_key, task_id)


def pop_next_task(android_id: str) -> int | None:
    """
    从设备队列取出下一个任务（从左边弹出）
    返回任务ID，如果队列为空返回 None
    """
    rds = get_redis_client()
    queue_key = get_device_queue_key(android_id)
    result = rds.lpop(queue_key)
    return int(result) if result else None


def peek_device_queue(android_id: str) -> list[int]:
    """
    查看设备队列中的所有任务ID（不弹出）
    """
    rds = get_redis_client()
    queue_key = get_device_queue_key(android_id)
    results = rds.lrange(queue_key, 0, -1)
    return [int(r) for r in results]


def get_queue_length(android_id: str) -> int:
    """获取设备队列长度"""
    rds = get_redis_client()
    queue_key = get_device_queue_key(android_id)
    return rds.llen(queue_key)


def remove_task_from_queue(android_id: str, task_id: int) -> int:
    """
    从设备队列中移除指定任务（用于取消等情况）
    返回移除的数量
    """
    rds = get_redis_client()
    queue_key = get_device_queue_key(android_id)
    return rds.lrem(queue_key, 0, task_id)


def clear_device_queue(android_id: str) -> int:
    """清空设备队列，返回清空的任务数量"""
    rds = get_redis_client()
    queue_key = get_device_queue_key(android_id)
    length = rds.llen(queue_key)
    rds.delete(queue_key)
    return length