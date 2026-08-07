"""
设备锁归属校验测试

回归场景（Bug）：一台设备上，任务A的 Job 正在运行（持有设备锁），任务B的 Job 在设备队列中排队。
此时用户删除/放弃任务B，delete_task / abort_task / abort_job 无差别调用 unlock_device，
会误删任务A的 Job 持有的设备锁 → 之后派发新任务时系统误判设备空闲 → 同设备并发执行。

修复后：只有锁的 task_id（即 Job ID）属于本任务/本 Job 时才允许解锁。

说明：unlock_device 的调用点有两个命名空间——
  - 修复前：app.testtask.controller.unlock_device（从 testplan.controller 导入的引用）
  - 修复后：unlock_device_if_owned 内部调用 app.testplan.controller.unlock_device
因此测试用同一个 Mock 同时补丁这两个绑定，确保在两种实现上都生效。
"""
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.testplan.models import DeviceLock
from app.testtask.controller import TestJobCRUD, TestTaskCRUD
from app.testtask.models import TestJob, TestTask

DEVICE = "127.0.0.1:6555"


@contextmanager
def _patched_unlock():
    """拦截两个命名空间中的 unlock_device，返回同一个 Mock 供断言"""
    unlock = MagicMock()
    with patch("app.testtask.controller.unlock_device", unlock, create=True), \
            patch("app.testplan.controller.unlock_device", unlock):
        yield unlock


def _make_job(job_id, task_id, device_id, status):
    job = MagicMock()
    job.job_id = job_id
    job.task_id = task_id
    job.device_id = device_id
    job.device_android_id = "android-1"
    job.status = status
    return job


def _make_lock(task_id):
    """构造一个持有中的设备锁（expires_at 在未来，is_device_locked 判定为已锁定）"""
    lock = MagicMock()
    lock.device_id = DEVICE
    lock.task_id = task_id
    lock.expires_at = datetime.now() + timedelta(hours=1)
    return lock


def _make_task(task_id, status="pending"):
    task = MagicMock()
    task.task_id = task_id
    task.status = status
    task.start_time = datetime.now()
    task.end_time = None
    return task


def _make_db(task, jobs, lock):
    db = MagicMock()

    def query(model):
        q = MagicMock()
        if model is TestTask:
            q.filter.return_value.first.return_value = task
        elif model is TestJob:
            q.filter.return_value.all.return_value = jobs
            q.filter.return_value.first.return_value = jobs[0] if jobs else None
            q.filter.return_value.count.return_value = 0
        elif model is DeviceLock:
            q.filter.return_value.first.return_value = lock
        else:
            q.filter.return_value.first.return_value = None
            q.filter.return_value.all.return_value = []
        return q

    db.query.side_effect = query
    return db


def _run(call, db, task_id):
    with _patched_unlock() as unlock, \
            patch("app.testtask.controller.store"), \
            patch("app.testtask.controller.remove_task_from_queue"), \
            patch("app.testtask.controller.send_cancel_signal"):
        call(db, task_id)
    return unlock


# ==================== delete_task ====================

class TestDeleteTaskLockOwnership:
    def test_delete_queued_task_keeps_other_tasks_running_lock(self):
        """任务B删除时，设备锁正被任务A运行中的Job(850)持有 → 不得解锁"""
        task = _make_task(511, status="pending")
        jobs = [
            _make_job(852, 511, DEVICE, "pending"),
            _make_job(853, 511, DEVICE, "pending"),
        ]
        db = _make_db(task, jobs, lock=_make_lock(task_id=850))

        unlock = _run(TestTaskCRUD.delete_task, db, 511)
        unlock.assert_not_called()

    def test_delete_task_releases_its_own_lock(self):
        """锁属于本任务的Job(852)时，删除任务应正常解锁"""
        task = _make_task(511, status="pending")
        jobs = [
            _make_job(852, 511, DEVICE, "pending"),
            _make_job(853, 511, DEVICE, "pending"),
        ]
        db = _make_db(task, jobs, lock=_make_lock(task_id=852))

        unlock = _run(TestTaskCRUD.delete_task, db, 511)
        unlock.assert_called_once_with(DEVICE, db)


# ==================== abort_task ====================

class TestAbortTaskLockOwnership:
    def test_abort_queued_task_keeps_other_tasks_running_lock(self):
        """任务B放弃时，设备锁正被任务A运行中的Job(850)持有 → 不得解锁"""
        task = _make_task(511, status="pending")
        jobs = [
            _make_job(852, 511, DEVICE, "pending"),
            _make_job(853, 511, DEVICE, "pending"),
        ]
        db = _make_db(task, jobs, lock=_make_lock(task_id=850))

        unlock = _run(TestTaskCRUD.abort_task, db, 511)
        unlock.assert_not_called()

    def test_abort_task_releases_its_own_lock(self):
        """锁属于本任务的Job(852)时，放弃任务应正常解锁"""
        task = _make_task(511, status="pending")
        jobs = [
            _make_job(852, 511, DEVICE, "pending"),
            _make_job(853, 511, DEVICE, "pending"),
        ]
        db = _make_db(task, jobs, lock=_make_lock(task_id=852))

        unlock = _run(TestTaskCRUD.abort_task, db, 511)
        unlock.assert_called_once_with(DEVICE, db)


    def test_abort_terminal_task_keeps_terminal_status(self):
        """所有 Job 都已终态时，放弃不应把任务状态改写为 aborted（应为 failed）"""
        task = _make_task(510, status="failed")
        jobs = [
            _make_job(850, 510, DEVICE, "completed"),
            _make_job(851, 510, DEVICE, "failed"),
        ]
        db = _make_db(task, jobs, lock=None)

        with patch("app.testtask.controller.store"), \
                patch("app.testtask.controller.remove_task_from_queue"), \
                patch("app.testtask.controller.send_cancel_signal"):
            TestTaskCRUD.abort_task(db, 510)

        assert task.status == "failed"
        assert task.end_time is None  # 未实际放弃任何 Job，不应覆盖 end_time


# ==================== abort_job ====================

class TestAbortJobLockOwnership:
    def test_abort_job_keeps_other_jobs_lock(self):
        """放弃Job(850)时，设备锁正被另一个Job(851)持有 → 不得解锁"""
        job = _make_job(850, 510, DEVICE, "pending")
        task = _make_task(510, status="running")
        db = _make_db(task, [job], lock=_make_lock(task_id=851))

        unlock = _run(TestJobCRUD.abort_job, db, 850)
        unlock.assert_not_called()

    def test_abort_job_releases_its_own_lock(self):
        """锁属于当前放弃的Job(850)时，应正常解锁"""
        job = _make_job(850, 510, DEVICE, "pending")
        task = _make_task(510, status="running")
        db = _make_db(task, [job], lock=_make_lock(task_id=850))

        unlock = _run(TestJobCRUD.abort_job, db, 850)
        unlock.assert_called_once_with(DEVICE, db)
