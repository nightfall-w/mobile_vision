"""
任务取消信号管理

统一 yolo_train 和 test_task 两套任务取消机制：
- send_cancel_signal: API 层调用，向 Redis 写入取消信号
- check_cancel_signal: consumer/agent 运行时轮询检查
- clear_cancel_signal: 任务结束后清理
"""
from core.redis import redis_cache

CANCEL_KEY_PREFIX = "task:cancel"


class TaskCancelledException(Exception):
    """任务被用户取消"""


def send_cancel_signal(task_id: str, namespace: str = "default"):
    """向 Redis 写入取消信号
    namespace: yolo_train / test_job 等，区分不同业务避免 ID 冲突
    """
    redis_cache.init_pool()
    redis_cache.set(f"{CANCEL_KEY_PREFIX}:{namespace}:{task_id}", "1", expire=86400)


def check_cancel_signal(task_id: str, namespace: str = "default") -> bool:
    """检查 Redis 中是否存在取消信号"""
    try:
        redis_cache.init_pool()
        return redis_cache.client.exists(f"{CANCEL_KEY_PREFIX}:{namespace}:{task_id}") > 0
    except Exception:
        return False


def clear_cancel_signal(task_id: str, namespace: str = "default"):
    """清理取消信号"""
    try:
        redis_cache.init_pool()
        redis_cache.delete(f"{CANCEL_KEY_PREFIX}:{namespace}:{task_id}")
    except Exception:
        pass
