"""
测试计划API路由
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.v1.routes.testcase import get_user_nickname
from app.device.devices_models import AndroidDevice
from app.llm.models import LLMCredential
from app.testcase.models import TestCase
from app.testplan.models import PlanCaseRelation, TestPlan
from app.testplan.controller import (
    PlanExecuteError,
    execute_plan_core,
    get_available_devices,
)
from app.testplan.request_models import (
    AddCaseRelationRequest,
    CreatePlanRequest,
    DeletePlanRequest,
    ExecutePlanRequest,
    RemoveCaseRelationRequest,
    UpdateCaseRelationRequest,
    UpdatePlanRequest,
)
from app.testtask.models import TestTask as NewTestTask
from app.user.models import UserModel
from app.user.request_models import CurrentUser
from core.auth_middleware import get_current_user
from core.database import get_sync_db
from core.enums import TaskStatus
from core.response import HttpErrcode, api_response
from services.scheduled_plan import (
    parse_cron_expression,
    register_plan_schedule,
    remove_plan_schedule,
    sync_plan_schedule,
)

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

        # 补充LLM凭证名称与可用状态，前端无需再从下拉列表反查（不可用的凭证不在下拉列表中）
        # llm_unavailable_reason: disabled=已禁用 deleted=已删除 missing=不存在 foreign=非本空间
        relation_dict["llm_name"] = ""
        relation_dict["llm_is_active"] = True
        relation_dict["llm_unavailable_reason"] = None
        if r.llm_credential_id:
            credential = db.query(LLMCredential).filter(
                LLMCredential.id == r.llm_credential_id
            ).first()
            if not credential:
                relation_dict["llm_is_active"] = False
                relation_dict["llm_unavailable_reason"] = "missing"
            else:
                relation_dict["llm_name"] = credential.model
                if credential.is_deleted:
                    reason = "deleted"
                elif not credential.is_active:
                    reason = "disabled"
                elif credential.workspace_id is not None and credential.workspace_id != plan.workspace_id:
                    # 凭证属于其他工作空间，对本计划不可选（系统级凭证 workspace_id 为 None，始终可用）
                    reason = "foreign"
                else:
                    reason = None
                relation_dict["llm_is_active"] = reason is None
                relation_dict["llm_unavailable_reason"] = reason
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
    # 先校验 cron，避免表达式非法时留下一条计划（定时却没生效）
    if request.enable_schedule and request.schedule_cron_expression:
        try:
            parse_cron_expression(request.schedule_cron_expression)
        except ValueError as e:
            return api_response(code=HttpErrcode.PARAMS_ERROR, message=str(e))

    plan = TestPlan(
        name=request.name,
        description=request.description,
        workspace_id=request.workspace_id,
        author=current_user.username,
        enable_schedule=bool(request.enable_schedule),
        schedule_cron_expression=request.schedule_cron_expression,
        enable_notification=bool(request.enable_notification),
        notify_on_failure_only=bool(request.notify_on_failure_only),
        wecom_webhooks=request.wecom_webhooks or [],
        lark_webhooks=request.lark_webhooks or [],
        dingtalk_webhooks=request.dingtalk_webhooks or [],
        create_time=datetime.now(),
        update_time=datetime.now(),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    # 注册定时任务（job_id 依赖 plan_id，故须在落库拿到主键后进行）
    if plan.enable_schedule and plan.schedule_cron_expression:
        try:
            plan.schedule_task_id = register_plan_schedule(plan.plan_id, plan.schedule_cron_expression)
            db.commit()
            db.refresh(plan)
        except Exception as e:
            # 定时注册失败不回滚计划本身，但需关闭开关避免"显示已启用实际没跑"
            plan.enable_schedule = False
            plan.schedule_task_id = None
            db.commit()
            return api_response(
                code=HttpErrcode.EXCEPTION,
                message=f"计划已创建，但定时任务注册失败，已关闭定时开关: {e}",
                data=plan.to_dict(),
            )

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

    # 定时配置：未传字段表示不改动，沿用原值
    schedule_changed = request.enable_schedule is not None or request.schedule_cron_expression is not None
    if schedule_changed:
        new_enable = request.enable_schedule if request.enable_schedule is not None else plan.enable_schedule
        new_cron = (
            request.schedule_cron_expression
            if request.schedule_cron_expression is not None
            else plan.schedule_cron_expression
        )
        if new_enable and new_cron:
            try:
                parse_cron_expression(new_cron)
            except ValueError as e:
                return api_response(code=HttpErrcode.PARAMS_ERROR, message=str(e))

        plan.enable_schedule = bool(new_enable)
        plan.schedule_cron_expression = new_cron

    # 通知配置：未传字段表示不改动
    if request.enable_notification is not None:
        plan.enable_notification = bool(request.enable_notification)
    if request.notify_on_failure_only is not None:
        plan.notify_on_failure_only = bool(request.notify_on_failure_only)
    if request.wecom_webhooks is not None:
        plan.wecom_webhooks = request.wecom_webhooks
    if request.lark_webhooks is not None:
        plan.lark_webhooks = request.lark_webhooks
    if request.dingtalk_webhooks is not None:
        plan.dingtalk_webhooks = request.dingtalk_webhooks

    plan.update_time = datetime.now()
    db.commit()

    if schedule_changed:
        # sync 内部会先移除同 id 旧任务再注册，不会产生双份触发
        try:
            plan.schedule_task_id = sync_plan_schedule(
                plan.plan_id, plan.enable_schedule, plan.schedule_cron_expression
            )
            db.commit()
            db.refresh(plan)
        except Exception as e:
            plan.enable_schedule = False
            plan.schedule_task_id = None
            db.commit()
            return api_response(
                code=HttpErrcode.EXCEPTION,
                message=f"计划已更新，但定时任务同步失败，已关闭定时开关: {e}",
                data=plan.to_dict(),
            )

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

    # 必须同步移除定时任务，否则成为孤儿 job 反复触发已删除的计划
    remove_plan_schedule(plan.plan_id)

    plan.is_deleted = True
    plan.enable_schedule = False
    plan.schedule_task_id = None
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


@router.post("/execute")
async def execute_plan(
        request: ExecutePlanRequest,
        db: Session = Depends(get_sync_db),
        current_user: UserModel = Depends(get_current_user),
):
    """执行测试计划 - 支持设备动态分配

    执行逻辑在 app.testplan.controller.execute_plan_core 中，与定时任务共用。
    HTTP 场景下前置校验失败直接返回错误、不创建任务（用户能立即看到提示）；
    定时场景另行处理为创建失败任务留痕。
    """
    try:
        result = execute_plan_core(plan_id=request.plan_id, author=current_user.username, db=db)
    except PlanExecuteError as e:
        code = HttpErrcode.NOT_FOUND if e.message == "测试计划不存在" else HttpErrcode.PARAMS_ERROR
        return api_response(code=code, message=e.message)

    message = result.pop("message")
    return api_response(data=result, message=message)


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
        queue_length = get_queue_length(device.android_id)

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
