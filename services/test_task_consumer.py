"""
测试任务消费者 - 使用 FunBoost 异步执行
"""

import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from datetime import datetime, timedelta

from funboost import BoosterParams, BrokerEnum, boost

from app.device.devices_models import AndroidDevice
from app.llm.models import LLMCredential
from app.task_monitor.models import Step, SubTask, TaskExecutionState, store
from app.task_monitor.screenshot_manager import screenshot_manager
from app.task_monitor.websocket import manager
from app.testcase.models import TestCase
from app.testplan.device_queue import pop_next_task
from app.testplan.models import DeviceLock
from app.yolo.controller import get_all_models
from automation_agent.agent import Agent
from automation_agent.interfaces.android import AndroidInterface
from automation_agent.types import AgentConfig
from core.database import SYNC_SESSION
from core.enums import SubTaskStatus, TaskStatus
from utils.task_cancel import check_cancel_signal


def get_llm_credential(db, credential_id: int, workspace_id: int):
    """获取LLM凭证"""
    credential = (
        db.query(LLMCredential).filter(LLMCredential.id == credential_id).first()
    )
    return credential


def get_test_case(db, case_id: int):
    """获取测试用例"""
    return db.query(TestCase).filter(TestCase.case_id == case_id).first()


def get_yolo_model_info(model_id: str):
    """根据模型ID获取YOLO模型路径和classes"""
    if not model_id:
        return None, None

    models = get_all_models()
    for model in models:
        if model["id"] == model_id:
            return model["path"], model.get("classes")
    return None, None


def update_task_status(db, task_id: int, status: str, duration: int = 0):
    """更新测试任务状态"""
    from app.testtask.models import TestJob, TestTask

    task = db.query(TestTask).filter(TestTask.task_id == task_id).first()
    if not task:
        return

    # 更新任务状态
    completed_jobs = (
        db.query(TestJob)
        .filter(
            TestJob.task_id == task_id, TestJob.status == TaskStatus.COMPLETED.value
        )
        .count()
    )

    failed_jobs = (
        db.query(TestJob)
        .filter(TestJob.task_id == task_id, TestJob.status == TaskStatus.FAILED.value)
        .count()
    )

    aborted_jobs = (
        db.query(TestJob)
        .filter(TestJob.task_id == task_id, TestJob.status == TaskStatus.ABORTED.value)
        .count()
    )

    running_jobs = (
        db.query(TestJob)
        .filter(TestJob.task_id == task_id, TestJob.status == TaskStatus.RUNNING.value)
        .count()
    )

    task.completed_jobs = completed_jobs
    task.failed_jobs = failed_jobs
    task.aborted_jobs = aborted_jobs
    task.running_jobs = running_jobs

    if completed_jobs + failed_jobs + aborted_jobs == task.total_jobs:
        if aborted_jobs == task.total_jobs:
            task.status = TaskStatus.ABORTED.value
        else:
            task.status = (
                TaskStatus.COMPLETED.value
                if failed_jobs == 0
                else TaskStatus.FAILED.value
            )
        task.end_time = datetime.now()
        if task.start_time:
            task.total_duration = int(
                (task.end_time - task.start_time).total_seconds()
            )
    elif running_jobs > 0 or completed_jobs > 0 or failed_jobs > 0:
        task.status = TaskStatus.RUNNING.value
        if task.start_time is None:
            task.start_time = datetime.now()

    task.update_time = datetime.now()
    db.commit()


def get_connected_devices():
    """获取当前连接的设备列表"""
    connected_device_ids = set()
    try:
        result = subprocess.run(
            ["adb", "devices", "-l"], capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split("\n")[1:]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                connected_device_ids.add(parts[0])
    except Exception as e:
        print(f"[FunBoost] 获取设备列表失败: {e}")
    return connected_device_ids


def match_device_by_android_id(db, device_id: str, device_android_id: str):
    """
    设备匹配：当设备断连时，尝试通过android_id查找相同设备的其他连接方式
    返回匹配到的设备ID，如果没有匹配则返回原设备ID

    :param db: 数据库会话
    :param device_id: 原设备ID
    :param device_android_id: 设备Android ID
    """
    connected_devices = get_connected_devices()

    if device_id in connected_devices:
        return device_id, None

    if device_android_id:
        online_devices = (
            db.query(AndroidDevice)
            .filter(
                AndroidDevice.android_id == device_android_id,
                AndroidDevice.status == "connected",
                AndroidDevice.id != device_id,
            )
            .all()
        )

        for online_device in online_devices:
            if online_device.id in connected_devices:
                print(
                    f"[FunBoost] 设备 {device_id} 已断连，自动重连 {online_device.id}"
                )
                return (
                    online_device.id,
                    f"设备 {device_id} 已断连，自动重连 {online_device.id}",
                )

    return device_id, None


@boost(
    BoosterParams(
        broker_kind=BrokerEnum.REDIS_ACK_ABLE,
        queue_name="test_task_queue",
        log_level=20,
        max_retry_times=0,
        concurrent_num=10,
        is_auto_start_consuming_message=False
    )
)
def execute_test_task(task_data: dict):
    """
    执行测试任务 - FunBoost 消费者

    task_data 包含：
    - job_id: Job ID（原task_id）
    """
    job_id = task_data.get("task_id")  # 这里保持兼容，队列中传的是 job_id
    if not job_id:
        job_id = task_data.get("job_id")

    print(f"[FunBoost] 开始处理测试Job: {job_id}")

    from app.testtask.models import TestJob, TestTask
    from core.database import SYNC_SESSION

    if not job_id:
        print("[FunBoost] Job ID不能为空")
        return

    session = SYNC_SESSION()
    try:
        job = session.query(TestJob).filter(TestJob.job_id == job_id, TestJob.is_deleted == False).first()
        if not job:
            print(f"[FunBoost] Job {job_id} 不存在或已删除")
            return

        # 检查任务是否已被放弃
        if job.status == TaskStatus.ABORTED.value:
            print(f"[FunBoost] Job {job_id} 已被放弃，跳过执行")
            return

        job.status = TaskStatus.RUNNING.value
        job.start_time = datetime.now()
        job.update_time = datetime.now()
        session.commit()
        print(f"[FunBoost] Job {job_id} 状态已更新为 {TaskStatus.RUNNING.value}")

        # 更新父任务状态
        update_task_status(session, job.task_id, TaskStatus.RUNNING.value)

        case = get_test_case(session, job.case_id)
        if not case:
            print(f"[FunBoost] Job {job_id} 用例不存在")
            job.status = TaskStatus.FAILED.value
            job.result = "用例不存在"
            job.update_time = datetime.now()
            session.commit()
            update_task_status(session, job.task_id, TaskStatus.FAILED.value)
            return

        case_content = case.content
        usage_instructions = case.usage_instructions

        credential = get_llm_credential(
            session, job.llm_credential_id, 0
        )  # workspace_id 暂时用0
        if not credential:
            print(f"[FunBoost] Job {job_id} LLM凭证不存在")
            job.status = TaskStatus.FAILED.value
            job.result = "LLM凭证不存在"
            job.update_time = datetime.now()
            session.commit()
            update_task_status(session, job.task_id, TaskStatus.FAILED.value)
            return

        yolo_path, yolo_classes = get_yolo_model_info(job.yolo_model_id)
        print(f"[FunBoost] Job {job_id}: yolo_path={yolo_path}")

        matched_device_id, match_message = match_device_by_android_id(
            session, job.device_id, job.device_android_id
        )
        if match_message:
            print(f"[FunBoost] {match_message}")

        print(f"[FunBoost] Job {job_id} 配置:")
        print(f"  设备: {matched_device_id}")
        print(f"  用例: {case.case_name}")
        print(f"  模型: {credential.model}")
        print(f"  API协议: {credential.api_protocol}")
        print(f"  YOLO: {yolo_path or '未使用'}")
        print(f"  OCR引擎: {job.ocr_engine or 'rapidocr'}")
        print(f"  Reasoning Effort: {job.reasoning_effort or 'low'}")

        execution_state = store.create_task(job_id)

        async def run_async():
            nonlocal match_message
            try:
                ocr_engine = job.ocr_engine or "rapidocr"
                interface = await AndroidInterface.create(
                    device_id=matched_device_id,
                    yolo_model_path=yolo_path,
                    ocr_engine=ocr_engine,
                    class_names_from_db=yolo_classes,
                )

                config = AgentConfig(
                    model=f"{credential.api_protocol}/{credential.model}",
                    api_key=credential.api_key,
                    base_url=credential.base_url,
                    reasoning_effort=job.reasoning_effort or "low",
                )

                agent = Agent(interface=interface, config=config)
                agent.job_id = job_id
                interface.job_id = job_id

                # 执行前置操作（切换输入法等）
                await interface.run_pre_actions()

                async def update_screenshot():
                    while True:
                        try:
                            if (
                                    hasattr(interface, "last_screenshot_path")
                                    and interface.last_screenshot_path
                            ):
                                screenshot_manager.cache_screenshot_path(
                                    job_id, interface.last_screenshot_path
                                )
                                screenshot_base64 = (
                                    screenshot_manager.get_screenshot_base64(job_id)
                                )
                                if screenshot_base64:
                                    manager.send_screenshot(job_id, screenshot_base64)
                        except Exception as e:
                            print(f"[FunBoost] 更新截图失败: {e}")
                        await asyncio.sleep(2)

                screenshot_task = asyncio.create_task(update_screenshot())

                async def on_state_update(state):
                    execution_state.status = TaskStatus.RUNNING
                    execution_state.last_update = datetime.now().isoformat()

                    state_type = state.get("type", "")
                    data = state.get("data", {})

                    if state_type == "task_started":
                        execution_state.task_id = job_id
                        manager.send_state_update(job_id, execution_state.to_dict())

                    elif state_type == "planning_completed":
                        tasks = data.get("tasks", [])
                        subtasks = []
                        for i, t in enumerate(tasks):
                            subtask = SubTask(
                                task_id=i + 1,
                                description=t.get("description", ""),
                                target_state=t.get("target_state", ""),
                                state=SubTaskStatus.PENDING,
                            )
                            subtasks.append(subtask)
                        execution_state.task_list = subtasks
                        execution_state.current_task_index = 0
                        store.update_state(job_id, execution_state)
                        manager.send_state_update(job_id, execution_state.to_dict())

                    elif state_type == "subtask_started":
                        idx = data.get("index", 0)
                        if idx < len(execution_state.task_list):
                            execution_state.task_list[idx].state = SubTaskStatus.RUNNING
                            execution_state.current_task_index = idx
                            execution_state.current_subtask = execution_state.task_list[
                                idx
                            ]
                        store.update_state(job_id, execution_state)
                        manager.send_state_update(job_id, execution_state.to_dict())

                    elif state_type == "subtask_completed":
                        idx = data.get("index", 0)
                        if idx < len(execution_state.task_list):
                            execution_state.task_list[
                                idx
                            ].state = SubTaskStatus.COMPLETED
                            execution_state.task_list[
                                idx
                            ].completed_at = datetime.now().isoformat()
                        store.update_state(job_id, execution_state)
                        manager.send_state_update(job_id, execution_state.to_dict())

                    elif state_type == "subtask_failed":
                        idx = data.get("index", 0)
                        if idx < len(execution_state.task_list):
                            execution_state.task_list[idx].state = SubTaskStatus.FAILED
                            execution_state.task_list[idx].reason = data.get(
                                "error", ""
                            )
                        store.update_state(job_id, execution_state)
                        manager.send_state_update(job_id, execution_state.to_dict())

                    elif state_type == "step_executing":
                        step = Step(
                            step_number=data.get("step_number", 0),
                            action=data.get("action", ""),
                            description=data.get("description", ""),
                            x=data.get("x"),
                            y=data.get("y"),
                            text=data.get("text"),
                            direction=data.get("direction"),
                            assertion=data.get("assertion"),
                            result="执行中...",
                            success=True,
                        )
                        execution_state.current_step = step
                        execution_state.total_steps += 1

                        if data.get("screenshot_base64"):
                            execution_state.screenshot_base64 = data.get(
                                "screenshot_base64"
                            )

                        idx = execution_state.current_task_index
                        if idx < len(execution_state.task_list):
                            execution_state.task_list[idx].steps.append(step)

                        store.update_state(job_id, execution_state)
                        manager.send_state_update(job_id, execution_state.to_dict())

                    elif state_type == "step_completed":
                        step_num = data.get("step_number", 0)
                        success = data.get("success", True)
                        change_type = data.get("change_type", "")

                        if (
                                execution_state.current_step
                                and execution_state.current_step.step_number == step_num
                        ):
                            execution_state.current_step.success = success
                            execution_state.current_step.result = change_type

                        if success:
                            execution_state.success_steps += 1
                        else:
                            execution_state.failed_steps += 1

                        idx = execution_state.current_task_index
                        if (
                                idx < len(execution_state.task_list)
                                and execution_state.task_list[idx].steps
                        ):
                            last_step = execution_state.task_list[idx].steps[-1]
                            last_step.success = success
                            last_step.result = change_type

                        store.update_state(job_id, execution_state)
                        manager.send_state_update(job_id, execution_state.to_dict())

                    elif state_type == "step_failed":
                        step_num = data.get("step_number", 0)

                        if (
                                execution_state.current_step
                                and execution_state.current_step.step_number == step_num
                        ):
                            execution_state.current_step.success = False
                            execution_state.current_step.result = data.get("error", "")

                        execution_state.failed_steps += 1

                        idx = execution_state.current_task_index
                        if (
                                idx < len(execution_state.task_list)
                                and execution_state.task_list[idx].steps
                        ):
                            last_step = execution_state.task_list[idx].steps[-1]
                            last_step.success = False
                            last_step.result = data.get("error", "")

                        store.update_state(job_id, execution_state)
                        manager.send_state_update(job_id, execution_state.to_dict())

                    elif state_type == "subtask_verification":
                        if data.get("completed"):
                            idx = execution_state.current_task_index
                            if idx < len(execution_state.task_list):
                                execution_state.task_list[
                                    idx
                                ].state = SubTaskStatus.COMPLETED

                    elif state_type == "task_completed":
                        execution_state.status = TaskStatus.COMPLETED
                        store.update_state(job_id, execution_state)
                        manager.send_state_update(job_id, execution_state.to_dict())

                    elif state_type == "task_failed":
                        execution_state.status = TaskStatus.FAILED
                        store.update_state(job_id, execution_state)
                        manager.send_state_update(job_id, execution_state.to_dict())

                    elif state_type == "task_terminated":
                        execution_state.status = TaskStatus.FAILED
                        execution_state.error_message = data.get(
                            "error", "子任务执行失败"
                        )
                        store.update_state(job_id, execution_state)
                        manager.send_state_update(job_id, execution_state.to_dict())

                    elif state_type == "task_error":
                        execution_state.status = TaskStatus.FAILED
                        execution_state.error_message = data.get("error", "任务异常")
                        store.update_state(job_id, execution_state)
                        manager.send_state_update(job_id, execution_state.to_dict())

                    elif state_type == "task_aborted":
                        execution_state.status = TaskStatus.ABORTED
                        execution_state.error_message = "任务被用户放弃"
                        store.update_state(job_id, execution_state)
                        manager.send_state_update(job_id, execution_state.to_dict())

                def on_log(level, message, page_structure=None):
                    store.add_log(job_id, level, message, page_structure=page_structure)
                    manager.send_log(job_id, level, message, page_structure=page_structure)

                agent.on_state_update = on_state_update
                agent.on_log = on_log

                try:
                    result = await agent.run_task(case_content, usage_instructions)
                finally:
                    screenshot_task.cancel()

                await agent.destroy()

                # 计算执行时长
                duration_seconds = 0
                if job.start_time:
                    duration_seconds = int(
                        (datetime.now() - job.start_time).total_seconds()
                    )

                if result.success:
                    job.status = TaskStatus.COMPLETED.value
                    job.result = (match_message + "\n" if match_message else "") + (
                            result.message or "Job执行成功"
                    )
                    job.end_time = datetime.now()
                    job.duration = duration_seconds
                    execution_state.status = TaskStatus.COMPLETED
                    print(f"[FunBoost] Job {job_id} 执行成功")
                else:
                    # 检查是否被用户放弃
                    if check_cancel_signal(str(job_id), namespace="test_job"):
                        job.status = TaskStatus.ABORTED.value
                        job.result = "任务被用户放弃"
                        execution_state.status = TaskStatus.ABORTED
                    else:
                        job.status = TaskStatus.FAILED.value
                        job.result = (match_message + "\n" if match_message else "") + (
                                result.error or "Job执行失败"
                        )
                        execution_state.status = TaskStatus.FAILED
                    job.end_time = datetime.now()
                    job.duration = duration_seconds
                    print(f"[FunBoost] Job {job_id} 执行失败: {result.error}")

                store.update_state(job_id, execution_state)
                manager.send_state_update(job_id, execution_state.to_dict())

                # 等待所有异步状态更新任务完成(避免竞态条件)
                await asyncio.sleep(0.1)

            except Exception as e:
                duration_seconds = 0
                if job.start_time:
                    duration_seconds = int(
                        (datetime.now() - job.start_time).total_seconds()
                    )

                job.status = TaskStatus.FAILED.value
                job.result = f"执行异常: {str(e)}"
                job.end_time = datetime.now()
                job.duration = duration_seconds
                execution_state.status = TaskStatus.FAILED
                execution_state.error_message = str(e)
                store.update_state(job_id, execution_state)
                store.add_log(job_id, "ERROR", f"任务执行异常: {str(e)}")
                print(f"[FunBoost] Job {job_id} 执行异常: {e}")
                import traceback

                traceback.print_exc()
                manager.send_error(job_id, str(e))

                # 等待所有异步状态更新任务完成(避免竞态条件)
                await asyncio.sleep(0.1)
            finally:
                if job:
                    job.update_time = datetime.now()
                    if job.status in [
                        TaskStatus.PENDING.value,
                        TaskStatus.RUNNING.value,
                    ]:
                        # 检查是否被用户放弃
                        try:
                            if check_cancel_signal(str(job.job_id), namespace="test_job"):
                                job.status = TaskStatus.ABORTED.value
                                job.result = "任务被用户放弃"
                                execution_state.status = TaskStatus.ABORTED
                            else:
                                job.status = TaskStatus.FAILED.value
                                job.result = "任务被放弃"
                                execution_state.status = TaskStatus.FAILED
                        except Exception:
                            job.status = TaskStatus.FAILED.value
                            job.result = "任务被放弃"
                            execution_state.status = TaskStatus.FAILED
                        job.end_time = datetime.now()

                    session.commit()
                    store.update_state(job_id, execution_state)
                    manager.send_state_update(job_id, execution_state.to_dict())

                    # 同步日志到MySQL（确保任务取消时也能完整写入）
                    print(f"[FunBoost] 同步Job {job_id} 数据到MySQL...")
                    store.sync_to_mysql(job_id)
                else:
                    session.rollback()

                # 更新父任务状态
                if job:
                    update_task_status(session, job.task_id, job.status, job.duration)

                # 解锁设备并处理下一个Job
                next_job_id = pop_next_task(job.device_android_id)
                if next_job_id:
                    existing_lock = (
                        session.query(DeviceLock)
                        .filter(DeviceLock.device_id == job.device_id)
                        .first()
                    )
                    if existing_lock:
                        session.delete(existing_lock)
                        session.commit()

                    lock = DeviceLock(
                        device_id=job.device_id,
                        task_id=next_job_id,
                        plan_id=0,
                        locked_by="system",
                        locked_at=datetime.now(),
                        expires_at=datetime.now() + timedelta(hours=24),
                    )
                    session.add(lock)
                    session.commit()
                    submit_test_task(next_job_id)
                    print(
                        f"[FunBoost] Job {job_id} 完成，自动触发队列中的下一个Job {next_job_id}"
                    )
                else:
                    print(
                        f"[FunBoost] Job {job_id} 完成，设备 {job.device_id} 队列为空"
                    )
                    # 解锁设备
                    lock = (
                        session.query(DeviceLock)
                        .filter(DeviceLock.device_id == job.device_id)
                        .first()
                    )
                    if lock:
                        session.delete(lock)
                        session.commit()
                        print(f"[FunBoost] 设备 {job.device_id} 已解锁")

        asyncio.run(run_async())

    except Exception as e:
        print(f"[FunBoost] Job {job_id} 处理失败: {e}")
        import traceback

        traceback.print_exc()

        try:
            job = session.query(TestJob).filter(TestJob.job_id == job_id).first()
            if job:
                job.status = TaskStatus.FAILED.value
                job.result = f"处理异常: {str(e)}"
                job.update_time = datetime.now()
                session.commit()
                update_task_status(session, job.task_id, TaskStatus.FAILED.value)
        except:
            pass
    finally:
        session.close()


def start_test_task_consumer():
    """启动测试任务消费者"""
    print("[FunBoost] 启动测试任务消费者...")
    execute_test_task.start_consuming_message()
    print("[FunBoost] 测试任务消费者已启动")


def submit_test_task(job_id: int):
    """提交测试Job到队列"""
    execute_test_task.publish({"task_data": {"task_id": job_id}})
    print(f"[FunBoost] 测试Job {job_id} 已提交到队列")
