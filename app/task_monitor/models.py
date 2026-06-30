"""
任务执行状态数据模型 - Redis存储 + MySQL持久化
"""

import json
import redis
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from core.redis import redis_cache
from core.enums import TaskStatus, SubTaskStatus, StepStatus


@dataclass
class Step:
    """执行步骤"""
    step_number: int
    action: str
    description: str
    result: str = ""
    success: bool = True
    timestamp: str = ""
    x: Optional[float] = None
    y: Optional[float] = None
    text: Optional[str] = None
    direction: Optional[str] = None
    assertion: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Step':
        return cls(**data)


@dataclass
class SubTask:
    """子任务"""
    task_id: int
    description: str
    target_state: str = ""
    state: SubTaskStatus = SubTaskStatus.PENDING
    steps: List[Step] = field(default_factory=list)
    retry_count: int = 0
    completed_at: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "target_state": self.target_state,
            "state": self.state.value if isinstance(self.state, Enum) else self.state,
            "steps": [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.steps],
            "retry_count": self.retry_count,
            "completed_at": self.completed_at,
            "reason": self.reason
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SubTask':
        steps = []
        for step_data in data.get("steps", []):
            if isinstance(step_data, dict):
                steps.append(Step.from_dict(step_data))
        return cls(
            task_id=data.get("task_id"),
            description=data.get("description", ""),
            target_state=data.get("target_state", ""),
            state=SubTaskStatus(data.get("state", SubTaskStatus.PENDING)),
            steps=steps,
            retry_count=data.get("retry_count", 0),
            completed_at=data.get("completed_at"),
            reason=data.get("reason", "")
        )


@dataclass
class TaskExecutionState:
    """任务执行状态"""
    task_id: int
    status: TaskStatus = TaskStatus.PENDING
    current_task_index: int = 0
    current_subtask: Optional[SubTask] = None
    task_list: List[SubTask] = field(default_factory=list)
    current_step: Optional[Step] = None
    screenshot_base64: str = ""
    start_time: str = ""
    last_update: str = ""
    total_steps: int = 0
    success_steps: int = 0
    failed_steps: int = 0

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "current_task_index": self.current_task_index,
            "current_subtask": self.current_subtask.to_dict() if self.current_subtask else None,
            "task_list": [t.to_dict() if hasattr(t, 'to_dict') else t for t in self.task_list],
            "current_step": self.current_step.to_dict() if self.current_step and hasattr(self.current_step,
                                                                                         'to_dict') else self.current_step,
            "screenshot_base64": self.screenshot_base64,
            "start_time": self.start_time,
            "last_update": self.last_update,
            "total_steps": self.total_steps,
            "success_steps": self.success_steps,
            "failed_steps": self.failed_steps
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TaskExecutionState':
        task_list = []
        for subtask_data in data.get("task_list", []):
            if isinstance(subtask_data, dict):
                task_list.append(SubTask.from_dict(subtask_data))

        current_subtask = None
        if data.get("current_subtask"):
            current_subtask = SubTask.from_dict(data["current_subtask"])

        current_step = None
        if data.get("current_step"):
            current_step = Step.from_dict(data["current_step"])

        return cls(
            task_id=data.get("task_id"),
            status=TaskStatus(data.get("status", TaskStatus.PENDING)),
            current_task_index=data.get("current_task_index", 0),
            current_subtask=current_subtask,
            task_list=task_list,
            current_step=current_step,
            screenshot_base64=data.get("screenshot_base64", ""),
            start_time=data.get("start_time", ""),
            last_update=data.get("last_update", ""),
            total_steps=data.get("total_steps", 0),
            success_steps=data.get("success_steps", 0),
            failed_steps=data.get("failed_steps", 0)
        )


@dataclass
class LogEntry:
    """日志条目"""
    level: str
    message: str
    timestamp: str = ""
    page_structure: Optional[List[Dict]] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.page_structure is not None:
            d["page_structure"] = self.page_structure
        return d

    @classmethod
    def from_dict(cls, data: dict) -> 'LogEntry':
        return cls(**data)


class TaskExecutionStore:
    """任务执行状态存储 - Redis + MySQL持久化"""

    # Redis键前缀
    STATE_KEY_PREFIX = "task:state:"
    LOG_KEY_PREFIX = "task:logs:"
    LOG_LIST_KEY_PREFIX = "task:log_list:"

    def __init__(self):
        self._redis = None

    def _get_redis(self):
        """获取Redis客户端"""
        if not self._redis:
            try:
                redis_cache.init_pool()
                self._redis = redis_cache.client
            except Exception as e:
                print(f"Redis连接池初始化失败: {e}")
                raise
        return self._redis

    def _redis_retry(self, func, *args, max_retries=3, **kwargs):
        """Redis操作重试机制 - 处理连接断开的情况"""
        for i in range(max_retries):
            try:
                return func(*args, **kwargs)
            except (redis.ConnectionError, redis.TimeoutError,
                    redis.exceptions.ConnectionError) as e:
                if i < max_retries - 1:
                    print(f"Redis连接失败,第{i+1}次重试: {str(e)[:100]}")
                    # 完全重置连接池,处理服务端断开连接的情况
                    self._redis = None
                    redis_cache.pool = None  # 重置全局连接池
                    import time
                    time.sleep(0.2 * (i + 1))  # 指数退避
                else:
                    print(f"Redis连接最终失败({max_retries}次重试): {str(e)[:100]}")
                    raise
            except Exception as e:
                print(f"Redis操作异常: {str(e)[:100]}")
                raise

    def _state_key(self, task_id: int) -> str:
        """生成状态存储键"""
        return f"{self.STATE_KEY_PREFIX}{task_id}"

    def _log_list_key(self, task_id: int) -> str:
        """生成日志列表键"""
        return f"{self.LOG_LIST_KEY_PREFIX}{task_id}"

    def _log_key(self, task_id: int, log_id: str) -> str:
        """生成日志详情键"""
        return f"{self.LOG_KEY_PREFIX}{task_id}:{log_id}"

    def create_task(self, task_id: int) -> TaskExecutionState:
        """创建任务状态"""
        state = TaskExecutionState(
            task_id=task_id,
            start_time=datetime.now().isoformat(),
            last_update=datetime.now().isoformat()
        )
        self._save_state(task_id, state)
        return state

    def _save_state(self, task_id: int, state: TaskExecutionState):
        """保存状态到Redis"""
        try:
            redis_client = self._get_redis()
            state_dict = state.to_dict()
            self._redis_retry(
                redis_client.set,
                self._state_key(task_id),
                json.dumps(state_dict),
                ex=86400
            )
        except Exception as e:
            print(f"保存任务{task_id}状态到Redis失败: {e}")

    def get_state(self, task_id: int) -> Optional[TaskExecutionState]:
        """获取任务状态（优先从Redis读取，Redis为空则从MySQL回退）"""
        try:
            redis_client = self._get_redis()
            data = self._redis_retry(redis_client.get, self._state_key(task_id))
            if data:
                try:
                    state_dict = json.loads(data)
                    return TaskExecutionState.from_dict(state_dict)
                except (json.JSONDecodeError, Exception) as e:
                    print(f"从Redis解析任务{task_id}状态失败: {e}")
        except Exception as e:
            print(f"从Redis读取任务{task_id}状态失败: {e}")

        # Redis读取失败或为空,从MySQL回退
        try:
            mysql_state = self.get_from_mysql(task_id)
            if mysql_state:
                return mysql_state
        except Exception as e:
            print(f"从MySQL读取任务{task_id}状态失败: {e}")
        return None

    def update_state(self, task_id: int, state: TaskExecutionState):
        """更新任务状态"""
        state.last_update = datetime.now().isoformat()
        self._save_state(task_id, state)

    def add_log(self, task_id: int, level: str, message: str, page_structure: Optional[List[Dict]] = None):
        """添加日志到Redis"""
        try:
            redis_client = self._get_redis()
            log_entry = LogEntry(
                level=level,
                message=message,
                timestamp=datetime.now().isoformat(),
                page_structure=page_structure
            )

            log_id = f"{task_id}:{int(datetime.now().timestamp() * 1000)}"
            log_key = self._log_key(task_id, log_id)
            log_list_key = self._log_list_key(task_id)

            # 在日志数据中保存log_id
            log_dict = log_entry.to_dict()
            log_dict['_log_id'] = log_id

            self._redis_retry(redis_client.set, log_key, json.dumps(log_dict), ex=86400)
            self._redis_retry(redis_client.rpush, log_list_key, log_id)

            max_logs = 500
            self._redis_retry(redis_client.ltrim, log_list_key, -max_logs, -1)

            return log_id
        except Exception as e:
            print(f"添加日志到Redis失败 task={task_id}: {e}")
            return None

    def get_log_count(self, task_id: int) -> int:
        """获取日志数量（优先从Redis读取，Redis为空则从MySQL回退）"""
        try:
            redis_client = self._get_redis()
            log_list_key = self._log_list_key(task_id)
            redis_count = self._redis_retry(redis_client.llen, log_list_key)

            if redis_count > 0:
                return redis_count
        except Exception as e:
            print(f"从Redis读取日志数量失败 task={task_id}: {e}")

        # Redis读取失败或为空,从MySQL回退
        try:
            mysql_count = self.get_log_count_from_mysql(task_id)
            return mysql_count
        except Exception as e:
            print(f"从MySQL读取日志数量失败 task={task_id}: {e}")
            return 0

    def get_logs(self, task_id: int, limit: int = 100) -> List[dict]:
        """获取日志（优先从Redis读取，Redis为空则从MySQL回退）"""
        try:
            redis_client = self._get_redis()
            log_list_key = self._log_list_key(task_id)
            log_ids = self._redis_retry(redis_client.lrange, log_list_key, 0, limit - 1)

            if log_ids:
                logs = []
                for log_id in log_ids:
                    log_id_str = log_id.decode() if isinstance(log_id, bytes) else log_id
                    log_key = self._log_key(task_id, log_id_str)
                    data = self._redis_retry(redis_client.get, log_key)
                    if data:
                        try:
                            log_dict = json.loads(data)
                            log_dict['_log_id'] = log_id_str
                            logs.append(log_dict)
                        except (json.JSONDecodeError, Exception) as e:
                            print(f"解析日志JSON失败 task={task_id}: {e}")

                if logs:
                    return logs
        except Exception as e:
            print(f"从Redis读取日志失败 task={task_id}: {e}")

        # Redis读取失败或为空,从MySQL回退
        try:
            return self.get_logs_from_mysql(task_id, limit)
        except Exception as e:
            print(f"从MySQL读取日志失败 task={task_id}: {e}")
            return []

    def get_logs_after(self, task_id: int, start_index: int, limit: int = 20) -> List[dict]:
        """从指定索引开始获取后续日志（Redis为空则从MySQL回退）"""
        try:
            redis_client = self._get_redis()
            log_list_key = self._log_list_key(task_id)

            log_ids = self._redis_retry(
                redis_client.lrange, log_list_key, start_index, start_index + limit - 1
            )

            if log_ids:
                logs = []
                for log_id in log_ids:
                    log_id_str = log_id.decode() if isinstance(log_id, bytes) else log_id
                    log_key = self._log_key(task_id, log_id_str)
                    data = self._redis_retry(redis_client.get, log_key)
                    if data:
                        try:
                            log_dict = json.loads(data)
                            log_dict['_log_id'] = log_id_str
                            logs.append(log_dict)
                        except (json.JSONDecodeError, Exception) as e:
                            print(f"解析日志JSON失败 task={task_id}: {e}")

                if logs:
                    return logs
        except Exception as e:
            print(f"从Redis读取日志失败 task={task_id}: {e}")

        # Redis读取失败或为空,从MySQL回退
        try:
            mysql_logs = self.get_logs_from_mysql(task_id, limit)
            if start_index == 0:
                return mysql_logs[:limit]
            else:
                return mysql_logs[start_index:start_index + limit]
        except Exception as e:
            print(f"从MySQL读取日志失败 task={task_id}: {e}")
            return []

    def delete_task(self, task_id: int):
        """删除任务状态"""
        try:
            redis_client = self._get_redis()

            state_key = self._state_key(task_id)
            log_list_key = self._log_list_key(task_id)

            log_ids = self._redis_retry(redis_client.lrange, log_list_key, 0, -1)
            for log_id in log_ids:
                log_key = self._log_key(task_id, log_id.decode())
                self._redis_retry(redis_client.delete, log_key)

            self._redis_retry(redis_client.delete, state_key)
            self._redis_retry(redis_client.delete, log_list_key)
        except Exception as e:
            print(f"删除任务状态失败 task={task_id}: {e}")

    def sync_to_mysql(self, task_id: int):
        """同步任务数据到MySQL"""
        try:
            from core.database import SYNC_SESSION
            from .db_models import TaskExecutionRecord, TaskExecutionLog

            session = SYNC_SESSION()
            try:
                state = self.get_state(task_id)
                if not state:
                    print(f"任务 {task_id} 状态不存在，跳过同步")
                    return

                existing_record = session.query(TaskExecutionRecord).filter(
                    TaskExecutionRecord.task_id == task_id
                ).first()

                if existing_record:
                    existing_record.status = state.status.value
                    existing_record.total_steps = state.total_steps
                    existing_record.success_steps = state.success_steps
                    existing_record.failed_steps = state.failed_steps
                    existing_record.task_list = state.to_dict()
                    existing_record.end_time = datetime.now()
                else:
                    record = TaskExecutionRecord(
                        task_id=task_id,
                        status=state.status.value,
                        total_steps=state.total_steps,
                        success_steps=state.success_steps,
                        failed_steps=state.failed_steps,
                        task_list=state.to_dict(),
                        start_time=datetime.fromisoformat(state.start_time) if state.start_time else datetime.now(),
                        end_time=datetime.now()
                    )
                    session.add(record)

                logs = self.get_logs(task_id)
                for log_entry in logs:
                    log_timestamp = log_entry.get('timestamp') if isinstance(log_entry, dict) else log_entry.timestamp
                    log_level = log_entry.get('level') if isinstance(log_entry, dict) else log_entry.level
                    log_message = log_entry.get('message') if isinstance(log_entry, dict) else log_entry.message
                    # 用task_id+timestamp+level+message联合判断，避免同秒的不同日志被去重漏掉
                    existing_log = session.query(TaskExecutionLog).filter(
                        TaskExecutionLog.task_id == task_id,
                        TaskExecutionLog.timestamp == datetime.fromisoformat(log_timestamp),
                        TaskExecutionLog.level == log_level,
                        TaskExecutionLog.message == log_message
                    ).first()
                    if not existing_log:
                        log_record = TaskExecutionLog(
                            task_id=task_id,
                            level=log_level,
                            message=log_message,
                            timestamp=datetime.fromisoformat(log_timestamp)
                        )
                        session.add(log_record)

                session.commit()
                print(f"任务 {task_id} 数据已同步到MySQL")

            except Exception as e:
                session.rollback()
                print(f"同步任务 {task_id} 到MySQL失败: {e}")
                import traceback
                traceback.print_exc()
            finally:
                session.close()

        except ImportError as e:
            print(f"导入MySQL模型失败: {e}")

    def get_from_mysql(self, task_id: int) -> Optional[TaskExecutionState]:
        """从MySQL获取历史任务状态"""
        try:
            from core.database import SYNC_SESSION
            from .db_models import TaskExecutionRecord

            session = SYNC_SESSION()
            try:
                record = session.query(TaskExecutionRecord).filter(
                    TaskExecutionRecord.task_id == task_id
                ).first()

                if record and record.task_list:
                    return TaskExecutionState.from_dict(record.task_list)
                return None
            finally:
                session.close()
        except ImportError as e:
            print(f"导入MySQL模型失败: {e}")
            return None

    def get_log_count_from_mysql(self, task_id: int) -> int:
        """从MySQL获取日志数量"""
        try:
            from core.database import SYNC_SESSION
            from .db_models import TaskExecutionLog

            session = SYNC_SESSION()
            try:
                count = session.query(TaskExecutionLog).filter(
                    TaskExecutionLog.task_id == task_id
                ).count()
                return count
            finally:
                session.close()
        except ImportError as e:
            print(f"导入MySQL模型失败: {e}")
            return 0

    def get_logs_from_mysql(self, task_id: int, limit: int = 100) -> List[dict]:
        """从MySQL获取历史日志"""
        try:
            from core.database import SYNC_SESSION
            from .db_models import TaskExecutionLog

            session = SYNC_SESSION()
            try:
                records = session.query(TaskExecutionLog).filter(
                    TaskExecutionLog.task_id == task_id
                ).order_by(TaskExecutionLog.timestamp).limit(limit).all()

                logs = []
                for i, record in enumerate(records):
                    logs.append({
                        'level': record.level,
                        'message': record.message,
                        'timestamp': record.timestamp.isoformat() if record.timestamp else '',
                        '_log_id': f"{task_id}:mysql:{i}"
                    })
                return logs
            finally:
                session.close()
        except ImportError as e:
            print(f"导入MySQL模型失败: {e}")
            return []


store = TaskExecutionStore()
