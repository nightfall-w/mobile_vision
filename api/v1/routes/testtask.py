"""
测试任务相关路由
"""
import asyncio
import base64
import json
import os
import traceback
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.testtask.controller import TestTaskCRUD, TestJobCRUD
from app.testtask.request_models import CreateTaskRequest, UpdateTaskRequest
from app.testtask.models import TestTask, TestJob
from app.task_monitor.models import store
from app.task_monitor.screenshot_manager import screenshot_manager
from app.user.models import UserModel
from core.auth_middleware import get_current_user
from core.config import SCREENSHOTS_DIR
from core.database import get_sync_db, SYNC_SESSION
from core.response import api_response, HttpErrcode
from core.enums import TaskStatus

try:
    from services.test_task_consumer import submit_test_task
    FUNBOOST_AVAILABLE = True
except ImportError:
    FUNBOOST_AVAILABLE = False

router = APIRouter(prefix="/testtask", tags=["测试任务"])


class TaskListRequest(BaseModel):
    workspace_id: int
    page_num: int = 1
    page_size: int = 10
    plan_id: Optional[int] = None
    status: Optional[str] = None
    keyword: Optional[str] = None


def get_user_nickname(db: Session, username: str) -> str:
    """获取用户昵称，如果不存在则返回用户名"""
    user = db.query(UserModel).filter(UserModel.username == username).first()
    return user.nickname if user else username


# ==================== CRUD 接口 ====================

@router.post("/create")
def create_task(req: CreateTaskRequest, db: Session = Depends(get_sync_db),
                current_user: UserModel = Depends(get_current_user)):
    """创建测试任务"""
    try:
        author = current_user.username
        task = TestTaskCRUD.create_task(
            db,
            workspace_id=req.workspace_id,
            plan_id=0,
            plan_name=f"任务-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            author=author
        )
        if not task:
            return api_response(code=HttpErrcode.EXCEPTION, message="创建失败")
        return api_response(data=task.to_dict(), message="创建成功")
    except Exception as e:
        traceback.print_exc()
        return api_response(code=HttpErrcode.EXCEPTION, message=str(e))


@router.post("/execute/{task_id}")
def execute_task(task_id: int, db: Session = Depends(get_sync_db)):
    """执行测试任务 - 通过 FunBoost 异步队列"""
    try:
        task = TestTaskCRUD.get_task_by_id(db, task_id)
        if not task:
            return api_response(code=HttpErrcode.NOT_FOUND, message="任务不存在")

        if task.status == TaskStatus.RUNNING.value:
            return api_response(code=HttpErrcode.PARAMS_ERROR, message="任务正在执行中，请勿重复提交")

        if FUNBOOST_AVAILABLE:
            jobs = TestJobCRUD.get_jobs_by_task(db, task_id)
            pending_jobs = [j for j in jobs if j.status == TaskStatus.PENDING.value]

            if pending_jobs:
                first_job = pending_jobs[0]
                submit_test_task(first_job.job_id)
                first_job.status = TaskStatus.RUNNING.value
                db.commit()

            task.status = TaskStatus.RUNNING.value
            task.start_time = datetime.now()
            task.update_time = datetime.now()
            db.commit()
            return api_response(data={'task_id': task_id, 'status': TaskStatus.RUNNING.value}, message="任务已提交到执行队列")
        else:
            return api_response(code=HttpErrcode.EXCEPTION, message="FunBoost 未安装，无法执行任务")
    except Exception as e:
        traceback.print_exc()
        return api_response(code=HttpErrcode.EXCEPTION, message=str(e))


@router.post("/list")
async def get_task_list(req: TaskListRequest, db: Session = Depends(get_sync_db)):
    """获取测试任务列表"""
    query = db.query(TestTask).filter(
        TestTask.is_deleted == False,
        TestTask.workspace_id == req.workspace_id,
    )

    if req.plan_id:
        query = query.filter(TestTask.plan_id == req.plan_id)

    query = query.order_by(TestTask.create_time.desc())

    total = query.count()
    tasks = query.offset((req.page_num - 1) * req.page_size).limit(req.page_size).all()

    task_list = []
    for task in tasks:
        task_dict = task.to_dict(include_jobs=True, db=db)
        task_dict['author_name'] = get_user_nickname(db, task.author)
        task_list.append(task_dict)

    return api_response(data={
        "list": task_list,
        "total": total,
        "page_num": req.page_num,
        "page_size": req.page_size,
    })


@router.get("/detail")
def get_task_detail(task_id: int = Query(..., description="任务ID"), db: Session = Depends(get_sync_db)):
    """获取任务详情"""
    try:
        task = TestTaskCRUD.get_task_by_id(db, task_id)
        if not task:
            return api_response(code=HttpErrcode.NOT_FOUND, message="任务不存在")

        task_dict = task.to_dict(db=db)
        task_dict['author_name'] = get_user_nickname(db, task.author)
        return api_response(data=task_dict)
    except Exception as e:
        traceback.print_exc()
        return api_response(code=HttpErrcode.EXCEPTION, message=str(e))


@router.put("/update")
def update_task(req: dict, db: Session = Depends(get_sync_db)):
    """更新任务"""
    try:
        task_id = req.get('task_id')
        if not task_id:
            return api_response(code=HttpErrcode.PARAMS_ERROR, message="参数验证失败: task_id 不能为空")

        update_data = {k: v for k, v in req.items() if k != 'task_id'}

        task = TestTaskCRUD.update_task(db, task_id, **update_data)
        if not task:
            return api_response(code=HttpErrcode.NOT_FOUND, message="任务不存在")

        return api_response(data=task.to_dict(), message="更新成功")
    except Exception as e:
        traceback.print_exc()
        return api_response(code=HttpErrcode.EXCEPTION, message=str(e))


@router.delete("/delete")
def delete_task(task_id: int = Query(..., description="任务ID"), db: Session = Depends(get_sync_db)):
    """删除任务（软删除）"""
    try:
        if not task_id:
            return api_response(code=HttpErrcode.PARAMS_ERROR, message="参数验证失败")

        success, message = TestTaskCRUD.delete_task(db, task_id)
        if not success:
            return api_response(code=HttpErrcode.EXCEPTION, message=message)

        return api_response(message=message)
    except Exception as e:
        traceback.print_exc()
        return api_response(code=HttpErrcode.EXCEPTION, message=str(e))


# ==================== Job 接口 ====================

@router.get("/job/{job_id}")
async def get_job_detail(job_id: int, db: Session = Depends(get_sync_db)):
    """获取Job详情"""
    job = db.query(TestJob).filter(TestJob.job_id == job_id, TestJob.is_deleted == False).first()
    if not job:
        return api_response(code=HttpErrcode.NOT_FOUND, message="Job不存在")
    return api_response(data=job.to_dict(db=db))


@router.get("/job/{job_id}/state")
async def get_job_state(job_id: int, db: Session = Depends(get_sync_db)):
    """获取Job执行状态"""
    job = db.query(TestJob).filter(TestJob.job_id == job_id, TestJob.is_deleted == False).first()
    if not job:
        return api_response(code=HttpErrcode.NOT_FOUND, message="Job不存在")

    execution_state = store.get_state(job_id)
    logs = store.get_logs(job_id, limit=50)

    state_data = {
        "job_id": job.job_id,
        "task_id": job.task_id,
        "status": job.status,
        "result": job.result,
        "start_time": job.start_time.strftime("%Y-%m-%d %H:%M:%S") if job.start_time else None,
        "end_time": job.end_time.strftime("%Y-%m-%d %H:%M:%S") if job.end_time else None,
        "duration": job.duration,
    }

    if execution_state:
        state_data.update({
            "status": execution_state.status,
            "current_task_index": execution_state.current_task_index,
            "current_subtask": execution_state.current_subtask.to_dict() if execution_state.current_subtask else None,
            "task_list": [t.to_dict() for t in execution_state.task_list],
            "current_step": execution_state.current_step.to_dict() if execution_state.current_step else None,
            "total_steps": execution_state.total_steps,
            "success_steps": execution_state.success_steps,
            "failed_steps": execution_state.failed_steps,
            "logs": [log.to_dict() for log in logs],
        })
    else:
        state_data.update({
            "current_task_index": 0,
            "current_subtask": None,
            "task_list": [],
            "current_step": None,
            "total_steps": 0,
            "success_steps": 0,
            "failed_steps": 0,
            "logs": [],
        })

    return api_response(data=state_data)


@router.get("/job/{job_id}/screenshot")
async def get_job_screenshot(job_id: int, db: Session = Depends(get_sync_db)):
    """获取Job的设备截图"""
    job = db.query(TestJob).filter(TestJob.job_id == job_id, TestJob.is_deleted == False).first()
    if not job:
        return api_response(code=HttpErrcode.NOT_FOUND, message="Job不存在")

    screenshot_base64 = screenshot_manager.get_screenshot_base64(job_id)
    if screenshot_base64:
        return api_response(data={"screenshot_base64": screenshot_base64})

    screenshot_base64 = _read_latest_screenshot(job_id)
    if screenshot_base64:
        return api_response(data={"screenshot_base64": screenshot_base64})

    return api_response(data={"screenshot_base64": ""})


def _read_latest_screenshot(job_id: int) -> str:
    """从文件读取最新的截图"""
    screenshot_dir = os.path.join(str(SCREENSHOTS_DIR), str(job_id))

    if not os.path.exists(screenshot_dir):
        return ""

    files = [f for f in os.listdir(screenshot_dir) if f.endswith(".png")]
    if not files:
        return ""

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(screenshot_dir, f)))
    file_path = os.path.join(screenshot_dir, latest_file)

    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"读取截图失败: {e}")
        return ""


@router.post("/job/{job_id}/abort")
def abort_job(job_id: int = Path(..., description="Job ID"), db: Session = Depends(get_sync_db)):
    """放弃单个 Job"""
    try:
        success, message = TestJobCRUD.abort_job(db, job_id)
        if not success:
            return api_response(code=HttpErrcode.NOT_FOUND, message=message)
        return api_response(message=message)
    except Exception as e:
        traceback.print_exc()
        return api_response(code=HttpErrcode.EXCEPTION, message=str(e))


# ==================== 任务/Job SSE 流 ====================

@router.get("/job/{job_id}/stream")
async def job_stream(job_id: int, db: Session = Depends(get_sync_db)):
    """SSE实时流 - 仅推送Job执行状态（不含日志）"""
    async def event_generator():
        while True:
            try:
                job = db.query(TestJob).filter(TestJob.job_id == job_id, TestJob.is_deleted == False).first()
                if not job:
                    await asyncio.sleep(1)
                    continue

                execution_state = store.get_state(job_id)

                state_data = {
                    "job_id": job.job_id,
                    "task_id": job.task_id,
                    "case_id": job.case_id,
                    "status": job.status,
                    "result": job.result,
                    "start_time": job.start_time.strftime("%Y-%m-%d %H:%M:%S") if job.start_time else None,
                    "end_time": job.end_time.strftime("%Y-%m-%d %H:%M:%S") if job.end_time else None,
                    "duration": job.duration,
                }

                if execution_state:
                    state_data.update({
                        "status": execution_state.status,
                        "current_task_index": execution_state.current_task_index,
                        "current_subtask": execution_state.current_subtask.to_dict() if execution_state.current_subtask else None,
                        "task_list": [t.to_dict() for t in execution_state.task_list],
                        "current_step": execution_state.current_step.to_dict() if execution_state.current_step else None,
                        "total_steps": execution_state.total_steps,
                        "success_steps": execution_state.success_steps,
                        "failed_steps": execution_state.failed_steps,
                    })
                else:
                    state_data.update({
                        "current_task_index": 0,
                        "current_subtask": None,
                        "task_list": [],
                        "current_step": None,
                        "total_steps": 0,
                        "success_steps": 0,
                        "failed_steps": 0,
                    })

                yield f"event: state_update\ndata: {json.dumps(state_data, ensure_ascii=False)}\n\n"

                if job.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.ABORTED.value]:
                    break

                await asyncio.sleep(1)
            except Exception as e:
                print(f"SSE stream error: {e}")
                traceback.print_exc()
                await asyncio.sleep(1)

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return StreamingResponse(event_generator(), headers=headers)


@router.get("/job/{job_id}/logs")
async def job_logs_stream(job_id: int, db: Session = Depends(get_sync_db)):
    """SSE实时流 - 仅推送新增日志（独立通道）"""
    async def event_generator():
        last_count = 0
        while True:
            try:
                job = db.query(TestJob).filter(TestJob.job_id == job_id, TestJob.is_deleted == False).first()
                if not job:
                    await asyncio.sleep(1)
                    continue

                current_count = store.get_log_count(job_id)
                if current_count > last_count:
                    new_logs = store.get_logs_after(job_id, last_count, limit=current_count - last_count)
                    for log in new_logs:
                        yield f"event: log_entry\ndata: {json.dumps(log, ensure_ascii=False)}\n\n"
                    last_count = current_count

                if job.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.ABORTED.value]:
                    break

                await asyncio.sleep(1)
            except Exception as e:
                print(f"Log stream error: {e}")
                await asyncio.sleep(1)

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return StreamingResponse(event_generator(), headers=headers)


@router.get("/job/{job_id}/screenshots")
async def job_screenshot_stream(job_id: int, db: Session = Depends(get_sync_db)):
    """SSE实时流 - 推送截图更新"""
    async def event_generator():
        last_mtime = 0
        while True:
            try:
                job = db.query(TestJob).filter(TestJob.job_id == job_id, TestJob.is_deleted == False).first()
                if not job:
                    await asyncio.sleep(1)
                    continue

                screenshot_dir = os.path.join(str(SCREENSHOTS_DIR), str(job_id))

                if os.path.exists(screenshot_dir):
                    files = [f for f in os.listdir(screenshot_dir) if f.endswith(".png")]
                    if files:
                        latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(screenshot_dir, f)))
                        file_path = os.path.join(screenshot_dir, latest_file)
                        mtime = os.path.getmtime(file_path)

                        if mtime > last_mtime:
                            with open(file_path, "rb") as f:
                                screenshot_base64 = base64.b64encode(f.read()).decode("utf-8")
                                yield f"event: screenshot\ndata: {json.dumps({'screenshot_base64': screenshot_base64}, ensure_ascii=False)}\n\n"
                                last_mtime = mtime

                if job.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.ABORTED.value]:
                    break

                await asyncio.sleep(1.5)
            except Exception as e:
                print(f"Screenshot stream error: {e}")
                await asyncio.sleep(1.5)

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return StreamingResponse(event_generator(), headers=headers)


# ==================== 任务级别接口 ====================

@router.get("/{task_id}")
async def get_task_detail_with_jobs(task_id: int, db: Session = Depends(get_sync_db)):
    """获取任务详情（包含所有Job）"""
    task = db.query(TestTask).filter(TestTask.task_id == task_id, TestTask.is_deleted == False).first()
    if not task:
        return api_response(code=HttpErrcode.NOT_FOUND, message="任务不存在")
    return api_response(data=task.to_dict(include_jobs=True, db=db))


@router.get("/{task_id}/jobs")
async def get_task_jobs(task_id: int, db: Session = Depends(get_sync_db)):
    """获取任务的所有Job"""
    jobs = db.query(TestJob).filter(TestJob.task_id == task_id, TestJob.is_deleted == False).order_by(TestJob.create_time).all()
    return api_response(data=[job.to_dict(db=db) for job in jobs])


@router.post("/{task_id}/abort")
def abort_task(task_id: int = Path(..., description="任务ID"), db: Session = Depends(get_sync_db)):
    """放弃任务（包含所有 Job）"""
    try:
        success, message = TestTaskCRUD.abort_task(db, task_id)
        if not success:
            return api_response(code=HttpErrcode.NOT_FOUND, message=message)
        return api_response(message=message)
    except Exception as e:
        traceback.print_exc()
        return api_response(code=HttpErrcode.EXCEPTION, message=str(e))


@router.get("/{task_id}/stream")
async def task_stream(task_id: int, db: Session = Depends(get_sync_db)):
    """SSE实时流 - 推送任务执行状态（包含所有Job）"""
    async def event_generator():
        while True:
            try:
                task = db.query(TestTask).filter(TestTask.task_id == task_id, TestTask.is_deleted == False).first()
                if not task:
                    await asyncio.sleep(1)
                    continue

                jobs = db.query(TestJob).filter(TestJob.task_id == task_id, TestJob.is_deleted == False).order_by(TestJob.create_time).all()

                state_data = {
                    "task_id": task.task_id,
                    "workspace_id": task.workspace_id,
                    "plan_id": task.plan_id,
                    "task_name": task.task_name,
                    "status": task.status,
                    "total_jobs": task.total_jobs,
                    "completed_jobs": task.completed_jobs,
                    "failed_jobs": task.failed_jobs,
                    "running_jobs": task.running_jobs,
                    "progress": task.progress,
                    "total_duration": task.total_duration,
                    "create_time": task.create_time.strftime("%Y-%m-%d %H:%M:%S") if task.create_time else None,
                    "end_time": task.end_time.strftime("%Y-%m-%d %H:%M:%S") if task.end_time else None,
                    "jobs": [job.to_dict(db=db) for job in jobs],
                }

                yield f"event: state_update\ndata: {json.dumps(state_data)}\n\n"

                if task.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                    break

                await asyncio.sleep(1)
            except Exception as e:
                print(f"SSE stream error: {e}")
                await asyncio.sleep(1)

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return StreamingResponse(event_generator(), headers=headers)


# ==================== 设备队列 ====================

@router.get("/queue/{android_id}/status")
def get_device_queue_status(android_id: str):
    """获取设备队列状态"""
    from app.testplan.device_queue import peek_device_queue, get_queue_length

    try:
        queue_length = get_queue_length(android_id)
        waiting_job_ids = peek_device_queue(android_id)

        session = SYNC_SESSION()
        waiting_jobs = []
        for job_id in waiting_job_ids:
            job = session.query(TestJob).filter(TestJob.job_id == job_id, TestJob.is_deleted == False).first()
            if job:
                job_dict = job.to_dict(db=session)
                waiting_jobs.append(job_dict)

        session.close()

        return api_response(data={
            'android_id': android_id,
            'queue_length': queue_length,
            'waiting_jobs': waiting_jobs
        })
    except Exception as e:
        traceback.print_exc()
        return api_response(code=HttpErrcode.EXCEPTION, message=str(e))
