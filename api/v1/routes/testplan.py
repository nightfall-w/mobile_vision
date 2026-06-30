"""
测试计划API路由
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.v1.routes.testcase import get_user_nickname
from app.device.devices_models import AndroidDevice
from app.testcase.models import TestCase
from app.testplan.device_queue import add_task_to_device_queue, pop_next_task
from app.testplan.models import DeviceLock, PlanCaseRelation, TestPlan
from app.testplan.request_models import (
    AddCaseRelationRequest,
    CreatePlanRequest,
    DeletePlanRequest,
    ExecutePlanRequest,
    RemoveCaseRelationRequest,
    UpdateCaseRelationRequest,
    UpdatePlanRequest,
)
from app.testtask.models import TestJob
from app.testtask.models import TestTask as NewTestTask
from app.user.models import UserModel
from app.user.request_models import CurrentUser
from core.auth_middleware import get_current_user
from core.database import get_sync_db
from core.enums import TaskStatus
from core.response import HttpErrcode, api_response
from services.test_task_consumer import submit_test_task, update_task_status

router = APIRouter(prefix="/testplan", tags=["测试计划"])


@router.get("/list")
async def get_plan_list(
        workspace_id: int,
        page_num: int = 1,
        page_size: int = 10,
        keyword: str = "",
        db: Session = Depends(get_sync_db),
):
    """获取测试计划列表"""
    query = (
        db.query(TestPlan, func.count(PlanCaseRelation.case_id).label("case_count"))
        .outerjoin(
            PlanCaseRelation,
            (TestPlan.plan_id == PlanCaseRelation.plan_id)
            & (PlanCaseRelation.is_deleted == False),
        )
        .filter(TestPlan.workspace_id == workspace_id, TestPlan.is_deleted == False).order_by(
            -TestPlan.plan_id
        )
    )

    if keyword:
        query = query.filter(TestPlan.name.like(f"%{keyword}%"))

    query = query.group_by(TestPlan.plan_id)

    total = query.count()
    plans = query.offset((page_num - 1) * page_size).limit(page_size).all()

    result = []
    for plan, case_count in plans:
        plan_dict = plan.to_dict()
        plan_dict["case_count"] = case_count
        result.append(plan_dict)

    return api_response(
        data={
            "list": result,
            "total": total,
            "page_num": page_num,
            "page_size": page_size,
        }
    )


@router.get("/{plan_id}")
async def get_plan_detail(plan_id: int, db: Session = Depends(get_sync_db)):
    """获取测试计划详情"""
    plan = db.query(TestPlan).filter(TestPlan.plan_id == plan_id, TestPlan.is_deleted == False).first()
    if not plan:
        return api_response(code=HttpErrcode.NOT_FOUND, message="测试计划不存在")

    relations = (
        db.query(PlanCaseRelation)
        .filter(
            PlanCaseRelation.plan_id == plan_id, PlanCaseRelation.is_deleted == False
        )
        .all()
    )

    result_relations = []
    for r in relations:
        case = db.query(TestCase).filter(TestCase.case_id == r.case_id).first()
        relation_dict = r.to_dict()
        if case:
            relation_dict["case_name"] = case.case_name
            relation_dict["updater_name"] = get_user_nickname(db, case.updater)
            relation_dict["case_level"] = case.level
            relation_dict["status"] = case.status
        else:
            relation_dict["case_name"] = f"用例{r.case_id}"
            relation_dict["updater_name"] = ""
            relation_dict["case_level"] = ""
            relation_dict["status"] = ""
        result_relations.append(relation_dict)

    plan_dict = plan.to_dict()
    plan_dict["relations"] = result_relations

    return api_response(data=plan_dict)


@router.post("/create")
async def create_plan(
        request: CreatePlanRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user),
):
    """创建测试计划"""
    plan = TestPlan(
        name=request.name,
        description=request.description,
        workspace_id=request.workspace_id,
        author=current_user.username,
        create_time=datetime.now(),
        update_time=datetime.now(),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    return api_response(data=plan.to_dict())


@router.post("/update")
async def update_plan(
        request: UpdatePlanRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user),
):
    """更新测试计划"""
    plan = db.query(TestPlan).filter(TestPlan.plan_id == request.plan_id, TestPlan.is_deleted == False).first()
    if not plan:
        return api_response(code=HttpErrcode.NOT_FOUND, message="测试计划不存在")

    if request.name is not None:
        plan.name = request.name
    if request.description is not None:
        plan.description = request.description
    plan.update_time = datetime.now()

    db.commit()
    return api_response(data=plan.to_dict())


@router.post("/delete")
async def delete_plan(
        request: DeletePlanRequest,
        db: Session = Depends(get_sync_db),
        userinfo: CurrentUser = Depends(get_current_user),
):
    """删除测试计划"""
    plan = db.query(TestPlan).filter(TestPlan.plan_id == request.plan_id, TestPlan.is_deleted == False).first()
    if not plan:
        return api_response(code=HttpErrcode.NOT_FOUND, message="测试计划不存在")

    plan.is_deleted = True
    plan.update_time = datetime.now()
    db.commit()

    return api_response(message="删除成功")


@router.post("/add_case")
async def add_case_relation(
        request: AddCaseRelationRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user),
):
    """添加用例关联 - 以 device_android_id 作为设备的永久标识"""
    existing = (
        db.query(PlanCaseRelation)
        .filter(
            PlanCaseRelation.plan_id == request.plan_id,
            PlanCaseRelation.case_id == request.case_id,
        )
        .first()
    )

    device_id = request.device_id
    device_name = request.device_name
    device_android_id = request.device_android_id

    # 'dynamic' 或空字符串表示动态分配,转换为 None
    if device_id == "dynamic" or device_id == "":
        device_id = None
        device_name = None
        device_android_id = None

    # 如果选择了具体设备,根据 device_id 查询设备详情（确保获取正确的 android_id）
    if device_id:
        device = db.query(AndroidDevice).filter(AndroidDevice.id == device_id).first()
        if device:
            device_android_id = device.android_id  # 以数据库中的 android_id 为准
            device_name = f"{device.brand} {device.model}"

    if existing:
        if not existing.is_deleted:
            return api_response(
                code=HttpErrcode.PARAMS_ERROR, message="该用例已关联到计划"
            )

        existing.is_deleted = False
        existing.device_id = device_id  # 记录当前的 device_id（仅供参考）
        existing.device_name = device_name
        existing.device_android_id = device_android_id  # 关键：永久标识
        existing.llm_credential_id = request.llm_credential_id
        existing.yolo_model_id = request.yolo_model_id
        existing.ocr_engine = request.ocr_engine
        existing.reasoning_effort = request.reasoning_effort
        existing.create_time = datetime.now()
        db.commit()
        db.refresh(existing)
        return api_response(data=existing.to_dict())

    relation = PlanCaseRelation(
        plan_id=request.plan_id,
        case_id=request.case_id,
        device_id=device_id,  # 记录当前的 device_id（仅供参考，执行时会重新查找）
        device_name=device_name,
        device_android_id=device_android_id,  # 关键：永久标识
        llm_credential_id=request.llm_credential_id,
        yolo_model_id=request.yolo_model_id,
        ocr_engine=request.ocr_engine,
        reasoning_effort=request.reasoning_effort,
        create_time=datetime.now(),
    )

    db.add(relation)
    db.commit()
    db.refresh(relation)

    case = db.query(TestCase).filter(TestCase.case_id == relation.case_id).first()
    relation_dict = relation.to_dict()
    if case:
        relation_dict["case_name"] = case.case_name
        relation_dict["updater_name"] = get_user_nickname(db, case.updater)
        relation_dict["case_level"] = case.level
        relation_dict["status"] = case.status
    else:
        relation_dict["case_name"] = f"用例{relation.case_id}"
        relation_dict["updater_name"] = ""
        relation_dict["case_level"] = ""
        relation_dict["status"] = ""

    return api_response(data=relation_dict)


@router.post("/update_case")
async def update_case_relation(
        request: UpdateCaseRelationRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user),
):
    """更新用例关联"""
    relation = (
        db.query(PlanCaseRelation).filter(PlanCaseRelation.id == request.id).first()
    )

    if not relation:
        return api_response(code=HttpErrcode.NOT_FOUND, message="关联记录不存在")

    if request.device_id is not None:
        if request.device_id == "" or request.device_id == "dynamic":
            # 空字符串或'dynamic'表示改为动态分配
            relation.device_id = None
            relation.device_name = None
            relation.device_android_id = None
        else:
            # 选择了具体设备,根据 device_id 查询设备详情
            relation.device_id = request.device_id
            device = (
                db.query(AndroidDevice)
                .filter(AndroidDevice.id == request.device_id)
                .first()
            )
            if device:
                relation.device_name = f"{device.brand} {device.model}"
                relation.device_android_id = device.android_id  # 以数据库中的 android_id 为准
    if request.device_name is not None:
        relation.device_name = request.device_name
    if request.device_android_id is not None:
        relation.device_android_id = request.device_android_id
    if request.llm_credential_id is not None:
        relation.llm_credential_id = request.llm_credential_id
    if request.yolo_model_id is not None:
        relation.yolo_model_id = request.yolo_model_id
    if request.ocr_engine is not None:
        relation.ocr_engine = request.ocr_engine
    if request.reasoning_effort is not None:
        relation.reasoning_effort = request.reasoning_effort

    db.commit()
    return api_response(data=relation.to_dict())


@router.post("/remove_case")
async def remove_case_relation(
        request: RemoveCaseRelationRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user),
):
    """移除用例关联（伪删除）"""
    relation = (
        db.query(PlanCaseRelation).filter(PlanCaseRelation.id == request.id).first()
    )

    if not relation:
        return api_response(code=HttpErrcode.NOT_FOUND, message="关联记录不存在")

    relation.is_deleted = True
    db.commit()

    return api_response(message="移除成功")


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


def get_device_by_android_id(android_id: str, db: Session) -> AndroidDevice | None:
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

            add_task_to_device_queue(device.id, job.job_id)
            job_ids.append(job.job_id)

        # 如果设备空闲，启动第一个任务；否则只加入队列等待
        if not is_device_locked(device_id, db):
            first_job_id = pop_next_task(device_id)
            if first_job_id:
                lock_device(device_id, first_job_id, plan_id, db)
                submit_test_task(first_job_id)
                device_status[device_id] = "running"
        else:
            device_status[device_id] = "queued"

    return job_ids, device_status


@router.post("/execute")
async def execute_plan(
        request: ExecutePlanRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user),
):
    """执行测试计划 - 支持设备动态分配"""
    plan_id = request.plan_id
    plan = db.query(TestPlan).filter(TestPlan.plan_id == plan_id, TestPlan.is_deleted == False).first()
    if not plan:
        return api_response(code=HttpErrcode.NOT_FOUND, message="测试计划不存在")

    relations = (
        db.query(PlanCaseRelation)
        .filter(
            PlanCaseRelation.plan_id == plan_id, PlanCaseRelation.is_deleted == False
        )
        .order_by(PlanCaseRelation.create_time)
        .all()
    )

    if not relations:
        return api_response(code=HttpErrcode.PARAMS_ERROR, message="计划中没有关联用例")

    task = NewTestTask(
        workspace_id=plan.workspace_id,
        plan_id=plan_id,
        task_name=plan.name,
        author="baojun.wang",
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

    # 分离指定设备和动态分配的任务
    specified_device_tasks = []  # 指定了设备的任务
    dynamic_assign_tasks = []  # 需要动态分配设备的任务

    for relation in relations:
        if relation.device_id:
            specified_device_tasks.append(relation)
        else:
            dynamic_assign_tasks.append(relation)

    job_ids = []
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

                    add_task_to_device_queue(current_device_id, job.job_id)
                    job_ids.append(job.job_id)

                if not is_device_locked(current_device_id, db):
                    first_job_id = pop_next_task(current_device_id)
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
    if dynamic_assigned_count > 0:
        message += f"，其中 {dynamic_assigned_count} 个Job动态分配了设备"
    if offline_devices:
        message += f"，{len(offline_devices)} 个设备离线，对应Job已标记失败"
    if no_device:
        message += "，没有在线设备，对应Job已标记失败"
    if queued_devices:
        message += f"，{len(queued_devices)} 个设备正在执行其他任务，对应Job已排队等待"

    return api_response(
        data={
            "task_id": task.task_id,
            "job_ids": job_ids,
            "device_status": device_status,
            "dynamic_assigned_count": dynamic_assigned_count,
        },
        message=message,
    )


@router.get("/{plan_id}/cases")
async def get_plan_cases(
        plan_id: int,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user),
):
    """获取计划关联的用例列表"""
    relations = (
        db.query(PlanCaseRelation)
        .filter(
            PlanCaseRelation.plan_id == plan_id, PlanCaseRelation.is_deleted == False
        )
        .all()
    )

    return api_response(data=[r.to_dict() for r in relations])


@router.get("/available_devices")
async def get_available_devices_for_plan(
        workspace_id: int,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user),
):
    """获取可用于动态分配的设备列表"""
    available_devices = get_available_devices(db)

    device_list = []
    for device in available_devices:
        from app.testplan.device_queue import get_queue_length
        queue_length = get_queue_length(device.id)

        device_list.append({
            "device_id": device.id,
            "device_name": f"{device.brand} {device.model}",
            "android_id": device.android_id,
            "android_version": device.android_version,
            "resolution": device.resolution,
            "queue_length": queue_length,
        })

    return api_response(data={
        "devices": device_list,
        "total_available": len(device_list),
    })


@router.get("/{plan_id}/state")
async def get_plan_state(
        plan_id: int,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user),
):
    """获取测试计划执行状态"""
    tasks = (
        db.query(NewTestTask)
        .filter(NewTestTask.plan_id == plan_id)
        .order_by(NewTestTask.create_time)
        .all()
    )

    if not tasks:
        return api_response(
            data={
                "status": TaskStatus.PENDING.value,
                "current_task_index": 0,
                "task_list": [],
                "current_steps": [],
            }
        )

    task_list = []
    current_task_index = 0
    found_running = False

    for i, task in enumerate(tasks):
        task_info = {
            "task_id": task.task_id,
            "task_name": task.task_name,
            "total_jobs": task.total_jobs,
            "completed_jobs": task.completed_jobs,
            "failed_jobs": task.failed_jobs,
            "progress": task.progress,
            "status": task.status,
            "create_time": task.create_time.strftime("%Y-%m-%d %H:%M:%S")
            if task.create_time
            else None,
            "end_time": task.end_time.strftime("%Y-%m-%d %H:%M:%S")
            if task.end_time
            else None,
        }
        task_list.append(task_info)

        if not found_running:
            if task.status == TaskStatus.RUNNING.value:
                current_task_index = i
                found_running = True
            elif task.status not in [
                TaskStatus.COMPLETED.value,
                TaskStatus.FAILED.value,
            ]:
                current_task_index = i

    status = TaskStatus.PENDING.value
    completed_count = sum(
        1 for t in task_list if t["status"] == TaskStatus.COMPLETED.value
    )
    failed_count = sum(1 for t in task_list if t["status"] == TaskStatus.FAILED.value)

    if completed_count + failed_count == len(task_list):
        status = (
            TaskStatus.COMPLETED.value if failed_count == 0 else TaskStatus.FAILED.value
        )
    elif found_running or completed_count > 0:
        status = TaskStatus.RUNNING.value

    return api_response(
        data={
            "status": status,
            "current_task_index": current_task_index,
            "task_list": task_list,
            "current_steps": [],
        }
    )
