from datetime import datetime

from sqlalchemy.orm import Session
from app.llm.models import LLMCredential
from app.testcase.models import TestCase
from app.testplan.models import DeviceLock
from app.testplan.device_queue import remove_task_from_queue
from app.testtask.models import TestTask, TestJob
from app.task_monitor.models import store
from app.yolo.controller import get_all_models
from api.v1.routes.testplan import is_device_locked, unlock_device
from core.enums import TaskStatus
from utils.task_cancel import send_cancel_signal


class TestTaskCRUD:
    @staticmethod
    def create_task(db: Session, plan_id: int, plan_name: str, author: str = None, workspace_id: int = 0):
        new_task = TestTask(
            workspace_id=workspace_id,
            plan_id=plan_id,
            task_name=plan_name,
            author=author or 'system',
            status=TaskStatus.PENDING.value,
            total_jobs=0,
            completed_jobs=0,
            failed_jobs=0,
            total_duration=0,
            create_time=datetime.now(),
            update_time=datetime.now()
        )

        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        return new_task
    
    @staticmethod
    def get_task_by_id(db: Session, task_id: int):
        return db.query(TestTask).filter(TestTask.task_id == task_id, TestTask.is_deleted == False).first()
    
    @staticmethod
    def get_tasks_by_workspace(db: Session, workspace_id: int, page_num: int, page_size: int, status: str = None, plan_id: int = None):
        offset = (page_num - 1) * page_size

        query = db.query(TestTask).filter(
            TestTask.workspace_id == workspace_id,
            TestTask.is_deleted == False
        )
        
        if status:
            query = query.filter(TestTask.status == status)
        
        if plan_id:
            query = query.filter(TestTask.plan_id == plan_id)
        
        tasks = query\
            .order_by(TestTask.task_id.desc())\
            .offset(offset)\
            .limit(page_size)\
            .all()
        
        count_query = db.query(TestTask).filter(
            TestTask.workspace_id == workspace_id,
            TestTask.is_deleted == False
        )
        if status:
            count_query = count_query.filter(TestTask.status == status)
        if plan_id:
            count_query = count_query.filter(TestTask.plan_id == plan_id)
        total = count_query.count()
        
        task_data = []
        for task in tasks:
            task_dict = {
                'task_id': task.task_id,
                'workspace_id': task.workspace_id,
                'task_name': task.task_name,
                'plan_id': task.plan_id,
                'status': task.status,
                'total_jobs': task.total_jobs,
                'completed_jobs': task.completed_jobs,
                'failed_jobs': task.failed_jobs,
                'total_duration': task.total_duration,
                'author': task.author,
                'create_time': task.create_time.strftime('%Y-%m-%d %H:%M:%S') if task.create_time else '',
                'update_time': task.update_time.strftime('%Y-%m-%d %H:%M:%S') if task.update_time else '',
                'jobs': []
            }

            jobs = db.query(TestJob).filter(TestJob.task_id == task.task_id, TestJob.is_deleted == False)\
                .order_by(TestJob.job_id).all()
            yolo_models_map = {m['id']: m['name'] for m in get_all_models()}
            for job in jobs:
                case = db.query(TestCase).filter(TestCase.case_id == job.case_id).first()
                case_name = case.case_name if case else ''

                llm_credential = db.query(LLMCredential).filter(LLMCredential.id == job.llm_credential_id).first()
                llm_name = f"{llm_credential.model}" if llm_credential else ''

                yolo_name = yolo_models_map.get(job.yolo_model_id, job.yolo_model_id or '')

                task_dict['jobs'].append({
                    'job_id': job.job_id,
                    'case_id': job.case_id,
                    'case_name': case_name,
                    'device_id': job.device_id,
                    'device_name': job.device_name or '',
                    'device_android_id': job.device_android_id or '',
                    'llm_credential_id': job.llm_credential_id,
                    'llm_name': llm_name,
                    'yolo_model_id': job.yolo_model_id,
                    'yolo_name': yolo_name,
                    'ocr_engine': job.ocr_engine or 'rapidocr',
                    'reasoning_effort': job.reasoning_effort or 'low',
                    'status': job.status,
                    'result': job.result,
                    'start_time': job.start_time.strftime('%Y-%m-%d %H:%M:%S') if job.start_time else '',
                    'end_time': job.end_time.strftime('%Y-%m-%d %H:%M:%S') if job.end_time else '',
                    'duration': job.duration or 0
                })
            
            task_data.append(task_dict)
        
        return task_data, total
    
    @staticmethod
    def update_task(db: Session, task_id: int, **kwargs):
        task = db.query(TestTask).filter(TestTask.task_id == task_id, TestTask.is_deleted == False).first()
        if not task:
            return None
        
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        task.update_time = datetime.now()
        db.commit()
        db.refresh(task)
        return task
    
    @staticmethod
    def delete_task(db: Session, task_id: int):
        task = db.query(TestTask).filter(TestTask.task_id == task_id, TestTask.is_deleted == False).first()
        if not task:
            return False, "任务不存在或已删除"

        if task.status == TaskStatus.RUNNING.value:
            return False, "运行中的任务不能删除"

        # 先清理 Redis：从设备队列移除 Job、释放设备锁、清理执行状态
        jobs = db.query(TestJob).filter(TestJob.task_id == task_id, TestJob.is_deleted == False).all()
        for job in jobs:
            remove_task_from_queue(str(job.device_id), job.job_id)
            store.delete_task(job.job_id)
        device_ids = set(job.device_id for job in jobs)
        for device_id in device_ids:
            if is_device_locked(device_id, db):
                unlock_device(device_id, db)

        task.is_deleted = True
        task.update_time = datetime.now()

        # 同时软删除关联的所有 Job
        db.query(TestJob).filter(TestJob.task_id == task_id, TestJob.is_deleted == False).update(
            {TestJob.is_deleted: True}, synchronize_session=False
        )

        db.commit()
        return True, "删除成功"
    
    @staticmethod
    def abort_task(db: Session, task_id: int):
        """放弃任务（放弃所有关联的 Job）"""
        task = db.query(TestTask).filter(TestTask.task_id == task_id, TestTask.is_deleted == False).first()
        if not task:
            return False, "任务不存在"

        jobs = db.query(TestJob).filter(TestJob.task_id == task_id).all()
        aborted_count = 0

        for job in jobs:
            if job.status in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
                was_running = (job.status == TaskStatus.RUNNING.value)
                _abort_single_job(db, job)
                aborted_count += 1
                # 只清理 PENDING Job 的 Redis 状态（RUNNING 的由 consumer 自己清理）
                if not was_running:
                    store.delete_task(job.job_id)

        task.status = TaskStatus.ABORTED.value
        task.end_time = datetime.now()
        if task.start_time:
            task.total_duration = int(
                (task.end_time - task.start_time).total_seconds()
            )
        db.commit()

        # 重新统计各状态 Job 数量
        _refresh_task_job_counts(db, task_id)

        # 释放所有关联设备的锁
        device_ids = set(job.device_id for job in jobs)
        for device_id in device_ids:
            if is_device_locked(device_id, db):
                unlock_device(device_id, db)


        return True, f"已放弃任务及其 {aborted_count} 个 Job"


def _abort_single_job(db: Session, job: TestJob):
    """内部方法：放弃单个 Job（仅处理 pending 和 running 状态）"""
    remove_task_from_queue(str(job.device_id), job.job_id)

    if job.status == TaskStatus.PENDING.value:
        job.status = TaskStatus.ABORTED.value
        job.end_time = datetime.now()
        job.result = "用户放弃"

    elif job.status == TaskStatus.RUNNING.value:
        send_cancel_signal(str(job.job_id), namespace="test_job")
        job.status = TaskStatus.ABORTED.value
        job.result = "用户放弃"


def _refresh_task_job_counts(db: Session, task_id: int):
    """重新统计任务下各状态 Job 数量并更新到 task 表"""
    task = db.query(TestTask).filter(TestTask.task_id == task_id).first()
    if not task:
        return

    completed_jobs = db.query(TestJob).filter(
        TestJob.task_id == task_id, TestJob.status == TaskStatus.COMPLETED.value
    ).count()
    failed_jobs = db.query(TestJob).filter(
        TestJob.task_id == task_id, TestJob.status == TaskStatus.FAILED.value
    ).count()
    aborted_jobs = db.query(TestJob).filter(
        TestJob.task_id == task_id, TestJob.status == TaskStatus.ABORTED.value
    ).count()
    running_jobs = db.query(TestJob).filter(
        TestJob.task_id == task_id, TestJob.status == TaskStatus.RUNNING.value
    ).count()

    task.completed_jobs = completed_jobs
    task.failed_jobs = failed_jobs
    task.aborted_jobs = aborted_jobs
    task.running_jobs = running_jobs
    task.update_time = datetime.now()
    db.commit()


class TestJobCRUD:
    @staticmethod
    def create_job(db: Session, task_id: int, case_id: int, device_id: str,
                   device_name: str = None, device_android_id: str = None,
                   llm_credential_id: int = None, yolo_model_id: str = None,
                   ocr_engine: str = 'rapidocr'):
        new_job = TestJob(
            task_id=task_id,
            case_id=case_id,
            device_id=device_id,
            device_name=device_name,
            device_android_id=device_android_id,
            llm_credential_id=llm_credential_id or 0,
            yolo_model_id=yolo_model_id,
            ocr_engine=ocr_engine,
            status=TaskStatus.PENDING.value,
            create_time=datetime.now(),
            update_time=datetime.now()
        )

        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        return new_job
    
    @staticmethod
    def abort_job(db: Session, job_id: int):
        """放弃单个 Job"""
        job = db.query(TestJob).filter(TestJob.job_id == job_id).first()
        if not job:
            return False, "Job 不存在"
        
        was_running = (job.status == TaskStatus.RUNNING.value)
        _abort_single_job(db, job)
        db.commit()

        if is_device_locked(job.device_id, db):
            lock = db.query(DeviceLock).filter(DeviceLock.device_id == job.device_id).first()
            if lock:
                unlock_device(job.device_id, db)

        # 只清理 PENDING Job 的 Redis 状态（RUNNING 的由 consumer 自己清理）
        if not was_running:
            store.delete_task(job_id)
        
        # 重新统计父任务各状态 Job 数量
        task = db.query(TestTask).filter(TestTask.task_id == job.task_id).first()
        if task:
            _refresh_task_job_counts(db, task.task_id)
            db.refresh(task)
            remaining = db.query(TestJob).filter(
                TestJob.task_id == job.task_id,
                TestJob.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value])
            ).count()
            if remaining == 0 and task.status in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
                task.status = TaskStatus.ABORTED.value
                task.end_time = datetime.now()
                if task.start_time:
                    task.total_duration = int(
                        (task.end_time - task.start_time).total_seconds()
                    )
                db.commit()

        return True, "Job 已放弃"

    @staticmethod
    def get_job_by_id(db: Session, job_id: int):
        return db.query(TestJob).filter(TestJob.job_id == job_id, TestJob.is_deleted == False).first()

    @staticmethod
    def get_jobs_by_task(db: Session, task_id: int):
        return db.query(TestJob).filter(TestJob.task_id == task_id, TestJob.is_deleted == False)\
            .order_by(TestJob.create_time).all()

    @staticmethod
    def update_job(db: Session, job_id: int, **kwargs):
        job = db.query(TestJob).filter(TestJob.job_id == job_id, TestJob.is_deleted == False).first()
        if not job:
            return None
        
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        job.update_time = datetime.now()
        db.commit()
        db.refresh(job)
        return job