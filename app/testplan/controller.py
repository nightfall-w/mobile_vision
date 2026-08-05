"""
@FileName：controller.py
@Description：测试计划执行控制器 —— 供 HTTP 接口与定时任务共用的执行逻辑
@Author：baojun.wang
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.device.devices_models import AndroidDevice
from app.llm.models import LLMCredential
from app.testcase.models import TestCase
from app.testplan.device_queue import add_task_to_device_queue, pop_next_task
from app.testplan.models import DeviceLock, PlanCaseRelation, TestPlan
from app.testtask.models import TestJob
from app.testtask.models import TestTask as NewTestTask
from core.enums import TaskStatus
from services.test_task_consumer import submit_test_task, update_task_status


# ========== 设备锁与设备查询 ==========

def is_device_locked(device_id: str, db: Session) -> bool:
    """检查设备是否被锁定"""
    lock = db.query(DeviceLock).filter(DeviceLock.device_id == device_id).first()
    if not lock:
        return False

    if lock.expires_at and lock.expires_at < datetime.now():
        db.delete(lock)
        db.commit()
        return False

    return True


def lock_device(device_id: str, task_id: int, plan_id: int, db: Session):
    """锁定设备"""
    lock = DeviceLock(
        device_id=device_id,
        task_id=task_id,
        plan_id=plan_id,
        locked_by="system",
        locked_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=24),
    )
    db.add(lock)
    db.commit()


def unlock_device(device_id: str, db: Session):
    """解锁设备"""
    lock = db.query(DeviceLock).filter(DeviceLock.device_id == device_id).first()
    if lock:
        db.delete(lock)
        db.commit()


def get_device_by_android_id(android_id: str, db: Session) -> Optional[AndroidDevice]:
    """根据 android_id 查找当前连接的设备"""
    return db.query(AndroidDevice).filter(
        AndroidDevice.android_id == android_id,
        AndroidDevice.status == "connected",
        AndroidDevice.is_deleted == 0
    ).first()


def check_device_online_by_android_id(android_id: str, db: Session) -> bool:
    """根据 android_id 检查设备是否在线"""
    return get_device_by_android_id(android_id, db) is not None


def get_available_devices(db: Session) -> list[AndroidDevice]:
    """获取所有在线且未锁定的可用设备"""
    online_devices = db.query(AndroidDevice).filter(
        AndroidDevice.status == "connected",
        AndroidDevice.is_deleted == 0
    ).all()

    available_devices = []
    for device in online_devices:
        if not is_device_locked(device.id, db):
            available_devices.append(device)

    return available_devices


def distribute_tasks_to_devices(tasks: list, devices: list, task_id: int, plan_id: int, db: Session) -> tuple[
    list, dict]:
    """
    将任务均衡分配给可用设备
    返回: (job_ids列表, device_status字典)
    """
    if not devices:
        return [], {"error": "no_available_devices"}

    job_ids = []
    device_status = {}
    device_task_map = {d.id: [] for d in devices}
    device_android_map = {d.id: d.android_id for d in devices}  # device.id → android_id

    # 轮询分配任务到设备
    for i, relation in enumerate(tasks):
        device = devices[i % len(devices)]
        device_task_map[device.id].append((relation, device))

    # 创建Job并加入队列
    for device_id, task_list in device_task_map.items():
        if not task_list:
            continue

        for relation, device in task_list:
            job = TestJob(
                task_id=task_id,
                case_id=relation.case_id,
                device_id=device.id,
                device_name=f"{device.brand} {device.model}",
                device_android_id=device.android_id,  # 记录永久标识
                llm_credential_id=relation.llm_credential_id,
                yolo_model_id=relation.yolo_model_id,
                ocr_engine=relation.ocr_engine,
                reasoning_effort=relation.reasoning_effort or "none",
                status=TaskStatus.PENDING.value,
                create_time=datetime.now(),
                update_time=datetime.now(),
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            add_task_to_device_queue(device_android_map[device.id], job.job_id)
            job_ids.append(job.job_id)

        # 如果设备空闲，启动第一个任务；否则只加入队列等待
        if not is_device_locked(device_id, db):
            first_job_id = pop_next_task(device_android_map[device_id])
            if first_job_id:
                lock_device(device_id, first_job_id, plan_id, db)
                submit_test_task(first_job_id)
                device_status[device_id] = "running"
        else:
            device_status[device_id] = "queued"

    return job_ids, device_status


# ========== LLM 凭证可用性校验 ==========

def check_relation_credentials(plan: TestPlan, relations: list, db: Session) -> dict:
    """
    逐条校验用例关联的LLM凭证是否可用

    :return: {relation.id: 该条用例自己的不可用原因}，全部可用则为空字典
    """
    # llm_credential_id 为空或0的旧数据不在此校验，仍走消费端原有失败路径
    checked_ids = {r.llm_credential_id for r in relations if r.llm_credential_id}
    if not checked_ids:
        return {}

    credential_map = {
        c.id: c
        for c in db.query(LLMCredential).filter(LLMCredential.id.in_(checked_ids)).all()
    }
    reasons = {}
    for relation in relations:
        if not relation.llm_credential_id:
            continue
        credential = credential_map.get(relation.llm_credential_id)
        if not credential:
            reason = "凭证不存在"
        elif credential.is_deleted:
            reason = "凭证已删除"
        elif not credential.is_active:
            reason = "凭证已禁用"
        elif credential.workspace_id is not None and credential.workspace_id != plan.workspace_id:
            reason = "凭证不属于本工作空间"
        else:
            continue
        # 附带凭证 ID/模型/地址，便于直接定位是哪个凭证
        if credential:
            detail = f"ID: {credential.id}，模型: {credential.model}，地址: {credential.base_url}"
        else:
            detail = f"ID: {relation.llm_credential_id}"
        reasons[relation.id] = f"LLM{reason}（{detail}）"

    return reasons


def check_plan_llm_credentials(plan: TestPlan, relations: list, db: Session) -> list[str]:
    """
    校验计划中各用例关联的LLM凭证是否可用，返回带用例名的汇总描述

    用于 HTTP 接口的整体拦截提示；单条 job 的失败原因请用 check_relation_credentials。

    :return: 不可用项的描述列表，全部可用则返回空列表
    """
    reasons = check_relation_credentials(plan, relations, db)
    if not reasons:
        return []

    invalid_items = []
    for relation in relations:
        reason = reasons.get(relation.id)
        if not reason:
            continue
        case = db.query(TestCase).filter(TestCase.case_id == relation.case_id).first()
        case_name = case.case_name if case else f"用例{relation.case_id}"
        invalid_items.append(f"{case_name} —— {reason}")

    return invalid_items


# ========== 计划执行 ==========

class PlanExecuteError(Exception):
    """计划无法执行（前置校验未通过）"""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def get_plan_relations(plan_id: int, db: Session) -> list:
    """获取计划关联的用例列表（按创建时间排序）"""
    return (
        db.query(PlanCaseRelation)
        .filter(
            PlanCaseRelation.plan_id == plan_id, PlanCaseRelation.is_deleted == False
        )
        .order_by(PlanCaseRelation.create_time)
        .all()
    )


def _create_failed_job(task_id: int, relation, reason: str, db: Session) -> TestJob:
    """为一条用例创建 FAILED Job 并写入日志流"""
    from app.task_monitor.models import store

    job = TestJob(
        task_id=task_id,
        case_id=relation.case_id,
        device_id=relation.device_id or "",
        device_name=relation.device_name or "动态分配",
        device_android_id=relation.device_android_id,
        llm_credential_id=relation.llm_credential_id,
        yolo_model_id=relation.yolo_model_id,
        ocr_engine=relation.ocr_engine,
        reasoning_effort=relation.reasoning_effort or "none",
        status=TaskStatus.FAILED.value,
        result=reason,
        create_time=datetime.now(),
        update_time=datetime.now(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    store.add_log(job.job_id, "ERROR", reason)
    return job


def create_failed_task(plan: TestPlan, author: str, reason: str, relations: list, db: Session) -> NewTestTask:
    """
    创建一条直接失败的任务用于留痕（供定时触发场景使用）

    定时触发场景下无人在界面上看到错误返回，若静默失败则定时任务失效会无声无息，
    因此前置校验不通过时仍落一条失败任务：task 标记 FAILED，并为每条关联用例创建
    一个 FAILED 的 Job，与"设备离线"的失败留痕方式保持一致。

    :param reason: 兜底原因；能定位到具体用例时（如凭证不可用），各 Job 写自己那条的原因，
                   避免把整个计划的汇总信息写进每个 Job 造成误导
    """
    total = len(relations)
    task = NewTestTask(
        workspace_id=plan.workspace_id,
        plan_id=plan.plan_id,
        task_name=plan.name,
        author=author,
        status=TaskStatus.FAILED.value,
        total_jobs=total,
        completed_jobs=0,
        failed_jobs=total,
        create_time=datetime.now(),
        update_time=datetime.now(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 逐条取该用例自己的凭证问题；凭证正常的用例则记为"因同计划其他用例配置有误而未执行"
    relation_reasons = check_relation_credentials(plan, relations, db)

    for relation in relations:
        own_reason = relation_reasons.get(relation.id)
        if own_reason:
            job_reason = own_reason
        elif relation_reasons:
            job_reason = "同一计划中存在配置不可用的用例，本次未执行"
        else:
            job_reason = reason
        _create_failed_job(task.task_id, relation, job_reason, db)

    return task


def execute_plan_core(plan_id: int, author: str, db: Session) -> dict:
    """
    执行测试计划的核心逻辑 —— HTTP 接口与定时任务共用

    :param plan_id: 计划ID
    :param author: 执行人（定时触发时传"定时任务"）
    :param db: 数据库会话
    :return: 含 task_id / job_ids / device_status / dynamic_assigned_count / message 的字典
    :raises PlanExecuteError: 计划不存在、无关联用例、或LLM凭证不可用
    """
    plan = db.query(TestPlan).filter(
        TestPlan.plan_id == plan_id, TestPlan.is_deleted == False
    ).first()
    if not plan:
        raise PlanExecuteError("测试计划不存在")

    relations = get_plan_relations(plan_id, db)
    if not relations:
        raise PlanExecuteError("计划中没有关联用例")

    # 部分执行策略：凭证不可用的用例单独标记失败，其余用例照常执行，
    # 避免个别用例配置有误就让整个计划（尤其无人值守的定时任务）全部不跑
    invalid_reasons = check_relation_credentials(plan, relations, db)
    runnable_relations = [r for r in relations if r.id not in invalid_reasons]
    if not runnable_relations:
        # 全部用例都不可用时才整体拦截，此时创建任务没有意义
        raise PlanExecuteError(
            f"以下用例的 LLM 凭证不可用，请修改配置后再执行："
            f"{'；'.join(check_plan_llm_credentials(plan, relations, db))}"
        )

    task = NewTestTask(
        workspace_id=plan.workspace_id,
        plan_id=plan_id,
        task_name=plan.name,
        author=author,
        status=TaskStatus.PENDING.value,
        total_jobs=len(relations),
        completed_jobs=0,
        failed_jobs=0,
        create_time=datetime.now(),
        update_time=datetime.now(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    job_ids = []

    # 先为凭证不可用的用例落一条 FAILED Job，写入各自的原因供监控页查看
    skipped_count = 0
    if invalid_reasons:
        for relation in relations:
            reason = invalid_reasons.get(relation.id)
            if not reason:
                continue
            job = _create_failed_job(task.task_id, relation, reason, db)
            job_ids.append(job.job_id)
            skipped_count += 1

    # 后续只调度凭证可用的用例
    relations = runnable_relations

    # 分离指定设备和动态分配的任务
    specified_device_tasks = []  # 指定了设备的任务
    dynamic_assign_tasks = []  # 需要动态分配设备的任务

    for relation in relations:
        if relation.device_id:
            specified_device_tasks.append(relation)
        else:
            dynamic_assign_tasks.append(relation)

    device_status = {}
    dynamic_assigned_count = 0

    # 1. 处理指定了设备的任务（使用 android_id 查找当前连接的设备）
    if specified_device_tasks:
        # 按 android_id 分组（关键：用永久标识分组，而不是临时的 device_id）
        device_groups = {}
        for relation in specified_device_tasks:
            android_id = relation.device_android_id
            if not android_id:
                # 兼容旧数据：如果没有 android_id 但有 device_id，尝试用 device_id 查找并补充 android_id
                device = db.query(AndroidDevice).filter(
                    AndroidDevice.id == relation.device_id
                ).first()
                if device:
                    android_id = device.android_id
                    relation.device_android_id = android_id  # 更新关系表的 android_id
                else:
                    android_id = relation.device_id  # 找不到就用 device_id 作为 fallback

            if android_id not in device_groups:
                device_groups[android_id] = []
            device_groups[android_id].append(relation)

        for android_id, group_relations in device_groups.items():
            # 根据 android_id 查找当前连接的设备（有线/无线连接都能匹配）
            current_device = get_device_by_android_id(android_id, db)

            if current_device:
                # 设备在线：正常创建 Job，加入设备队列并立即触发
                current_device_id = current_device.id
                current_device_name = f"{current_device.brand} {current_device.model}"

                for relation in group_relations:
                    job = TestJob(
                        task_id=task.task_id,
                        case_id=relation.case_id,
                        device_id=current_device_id,
                        device_name=current_device_name,
                        device_android_id=android_id,
                        llm_credential_id=relation.llm_credential_id,
                        yolo_model_id=relation.yolo_model_id,
                        ocr_engine=relation.ocr_engine,
                        reasoning_effort=relation.reasoning_effort or "none",
                        status=TaskStatus.PENDING.value,
                        create_time=datetime.now(),
                        update_time=datetime.now(),
                    )
                    db.add(job)
                    db.commit()
                    db.refresh(job)

                    add_task_to_device_queue(android_id, job.job_id)
                    job_ids.append(job.job_id)

                if not is_device_locked(current_device_id, db):
                    first_job_id = pop_next_task(android_id)
                    if first_job_id:
                        lock_device(current_device_id, first_job_id, plan_id, db)
                        submit_test_task(first_job_id)
                        device_status[current_device_id] = "running"
                else:
                    device_status[current_device_id] = "queued"
            else:
                # 设备离线：创建 Job 并直接标记为 FAILED，让用户立刻知道结果
                offline_device_name = group_relations[0].device_name or f"设备({android_id})"

                for relation in group_relations:
                    job = TestJob(
                        task_id=task.task_id,
                        case_id=relation.case_id,
                        device_id=relation.device_id,
                        device_name=relation.device_name or offline_device_name,
                        device_android_id=android_id,
                        llm_credential_id=relation.llm_credential_id,
                        yolo_model_id=relation.yolo_model_id,
                        ocr_engine=relation.ocr_engine,
                        reasoning_effort=relation.reasoning_effort or "none",
                        status=TaskStatus.FAILED.value,
                        result=f"设备不在线（{offline_device_name}），无法执行",
                        create_time=datetime.now(),
                        update_time=datetime.now(),
                    )
                    db.add(job)
                    db.commit()
                    db.refresh(job)
                    job_ids.append(job.job_id)

                    # 写入错误日志到 Redis，前端日志流可直接展示
                    from app.task_monitor.models import store
                    store.add_log(job.job_id, "ERROR", f"设备不在线（{offline_device_name}），无法执行")

                device_status[android_id] = "offline"

    # 2. 处理需要动态分配设备的任务
    if dynamic_assign_tasks:
        available_devices = get_available_devices(db)

        if not available_devices:
            # 没有空闲设备：使用全部在线设备均衡分配，Job 排队等待
            all_online = db.query(AndroidDevice).filter(
                AndroidDevice.status == "connected",
                AndroidDevice.is_deleted == 0
            ).all()
            if all_online:
                dynamic_job_ids, dynamic_status = distribute_tasks_to_devices(
                    dynamic_assign_tasks,
                    all_online,
                    task.task_id,
                    plan_id,
                    db
                )
                job_ids.extend(dynamic_job_ids)
                device_status.update(dynamic_status)
                dynamic_assigned_count = len(dynamic_job_ids)
            else:
                # 没有任何在线设备：创建 Job 并直接标记失败
                for relation in dynamic_assign_tasks:
                    job = TestJob(
                        task_id=task.task_id,
                        case_id=relation.case_id,
                        device_id="",
                        device_name="动态分配",
                        device_android_id=None,
                        llm_credential_id=relation.llm_credential_id,
                        yolo_model_id=relation.yolo_model_id,
                        ocr_engine=relation.ocr_engine,
                        reasoning_effort=relation.reasoning_effort or "none",
                        status=TaskStatus.FAILED.value,
                        result="没有在线设备可用",
                        create_time=datetime.now(),
                        update_time=datetime.now(),
                    )
                    db.add(job)
                    db.commit()
                    db.refresh(job)
                    job_ids.append(job.job_id)
                    from app.task_monitor.models import store
                    store.add_log(job.job_id, "ERROR", "没有在线设备可用")
                device_status["dynamic"] = "no_online_device"
        else:
            # 将任务均衡分配给可用设备
            dynamic_job_ids, dynamic_status = distribute_tasks_to_devices(
                dynamic_assign_tasks,
                available_devices,
                task.task_id,
                plan_id,
                db
            )
            job_ids.extend(dynamic_job_ids)
            device_status.update(dynamic_status)
            dynamic_assigned_count = len(dynamic_job_ids)

    offline_devices = [d for d, s in device_status.items() if s == "offline"]
    queued_devices = [d for d in device_status if device_status[d] == "queued"]
    no_device = device_status.get("dynamic") == "no_online_device"

    # 刷新 Task 状态（设备离线的 Job 直接标记失败，需更新 Task 的 failed_jobs 和状态）
    update_task_status(db, task.task_id, task.status)

    message = f"已创建任务 {task.task_id}，包含 {len(job_ids)} 个Job"
    if skipped_count > 0:
        message += f"，{skipped_count} 个用例因 LLM 凭证不可用已标记失败"
    if dynamic_assigned_count > 0:
        message += f"，其中 {dynamic_assigned_count} 个Job动态分配了设备"
    if offline_devices:
        message += f"，{len(offline_devices)} 个设备离线，对应Job已标记失败"
    if no_device:
        message += "，没有在线设备，对应Job已标记失败"
    if queued_devices:
        message += f"，{len(queued_devices)} 个设备正在执行其他任务，对应Job已排队等待"

    return {
        "task_id": task.task_id,
        "job_ids": job_ids,
        "device_status": device_status,
        "dynamic_assigned_count": dynamic_assigned_count,
        "skipped_count": skipped_count,
        "message": message,
    }
