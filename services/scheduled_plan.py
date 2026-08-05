"""
@FileName：scheduled_plan.py
@Description：测试计划定时调度 —— 基于 funboost ApsJobAdder，jobstore 使用 Redis
@Author：baojun.wang
"""
from typing import Optional

from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger
from funboost import ApsJobAdder, BoosterParams, BrokerEnum, boost

from core.database import get_sync_db

# APScheduler job id 前缀，与计划一一对应
JOB_ID_PREFIX = "testplan_"

# Cron 表达式字段顺序（6 段）
CRON_FIELDS = ("second", "minute", "hour", "day", "month", "day_of_week")


def build_job_id(plan_id: int) -> str:
    """构造计划对应的定时任务ID"""
    return f"{JOB_ID_PREFIX}{plan_id}"


def parse_cron_expression(expression: str) -> dict:
    """
    解析 6 段 Cron 表达式为 APScheduler 的 cron 参数

    :param expression: 形如 "0 0 2 * * *"（秒 分 时 日 月 周）
    :return: {"second": "0", "minute": "0", ...}
    :raises ValueError: 段数不为6或字段值非法
    """
    if not expression or not expression.strip():
        raise ValueError("定时表达式不能为空")

    parts = expression.split()
    if len(parts) != 6:
        raise ValueError(f"定时表达式需为6段（秒 分 时 日 月 周），当前为{len(parts)}段")

    cron_kwargs = dict(zip(CRON_FIELDS, parts))

    # 交给 APScheduler 自行校验各字段取值，避免段数对但内容非法（如 "99 * * * * *"）
    try:
        CronTrigger(**cron_kwargs)
    except Exception as e:
        raise ValueError(f"定时表达式非法: {e}")

    return cron_kwargs


@boost(
    BoosterParams(
        broker_kind=BrokerEnum.REDIS_ACK_ABLE,
        queue_name="scheduled_plan_queue",
        log_level=20,
        max_retry_times=0,
        concurrent_num=5,
        is_auto_start_consuming_message=False,
    )
)
def trigger_scheduled_plan(plan_id: int, trigger_user: str = "定时任务"):
    """
    定时触发测试计划 —— ApsJobAdder 的目标函数

    与 HTTP 接口的差异：定时场景下无人在界面上看到错误返回，若静默失败则
    定时任务失效会无声无息，因此前置校验不通过时创建一条失败任务留痕。
    """
    # 延迟导入：app.testplan.controller 依赖 services.test_task_consumer，
    # 模块级导入会与消费者模块形成环
    from app.testplan.controller import (
        PlanExecuteError,
        create_failed_task,
        execute_plan_core,
        get_plan_relations,
    )
    from app.testplan.models import TestPlan

    db = next(get_sync_db())
    try:
        try:
            result = execute_plan_core(plan_id=plan_id, author=trigger_user, db=db)
            print(f"[定时任务] 计划 {plan_id} 触发成功: {result['message']}")
            return result
        except PlanExecuteError as e:
            # 计划不存在时无法留痕（没有 workspace_id 等信息），只记日志
            plan = db.query(TestPlan).filter(
                TestPlan.plan_id == plan_id, TestPlan.is_deleted == False
            ).first()
            if not plan:
                print(f"[定时任务] 计划 {plan_id} 触发失败: {e.message}（计划不存在，无法留痕）")
                return None

            relations = get_plan_relations(plan_id, db)
            if not relations:
                print(f"[定时任务] 计划 {plan_id} 触发失败: {e.message}（无关联用例，无法留痕）")
                return None

            task = create_failed_task(plan, trigger_user, e.message, relations, db)
            print(f"[定时任务] 计划 {plan_id} 触发失败: {e.message}，已创建失败任务 {task.task_id} 留痕")
            return {"task_id": task.task_id, "failed": True, "reason": e.message}
    finally:
        db.close()


def _get_aps_adder() -> ApsJobAdder:
    """获取 ApsJobAdder（jobstore 使用 Redis，与 funboost 共用配置）"""
    return ApsJobAdder(trigger_scheduled_plan, job_store_kind="redis")


def register_plan_schedule(plan_id: int, cron_expression: str) -> str:
    """
    注册/更新计划的定时任务

    :return: 注册成功的 job_id
    :raises ValueError: Cron 表达式非法
    """
    cron_kwargs = parse_cron_expression(cron_expression)
    job_id = build_job_id(plan_id)

    _get_aps_adder().add_push_job(
        id=job_id,
        trigger="cron",
        replace_existing=True,  # 同 id 覆盖，避免修改cron后产生双份触发
        kwargs={"plan_id": plan_id, "trigger_user": "定时任务"},
        **cron_kwargs,
    )
    print(f"[定时任务] 已注册 {job_id}: {cron_expression}")
    return job_id


def remove_plan_schedule(plan_id: int) -> bool:
    """
    移除计划的定时任务

    :return: True=已移除，False=任务本不存在
    """
    job_id = build_job_id(plan_id)
    try:
        _get_aps_adder().aps_obj.remove_job(job_id=job_id)
        print(f"[定时任务] 已移除 {job_id}")
        return True
    except JobLookupError:
        # 计划本来就没开定时，或任务已被移除
        return False
    except Exception as e:
        print(f"[定时任务] 移除 {job_id} 异常: {e}")
        return False


def sync_plan_schedule(plan_id: int, enable: Optional[bool], cron_expression: Optional[str]) -> Optional[str]:
    """
    按计划配置同步定时任务（供创建/更新计划时调用）

    :param enable: 是否启用定时
    :param cron_expression: Cron 表达式
    :return: 启用时返回 job_id，未启用返回 None
    :raises ValueError: Cron 表达式非法
    """
    if enable and cron_expression:
        return register_plan_schedule(plan_id, cron_expression)

    remove_plan_schedule(plan_id)
    return None


def restore_all_plan_schedules() -> dict:
    """
    服务启动时按数据库配置重建定时任务，以数据库为准

    定时任务本身持久化在 Redis jobstore 中，正常重启不会丢失；此处做一次对账，
    覆盖以下情况：Redis 被清空、jobstore 数据与数据库不一致、
    或计划在服务停止期间被直接改库。

    :return: {"restored": n, "failed": n, "cleaned": n}
    """
    from app.testplan.models import TestPlan

    db = next(get_sync_db())
    restored = failed = cleaned = 0
    try:
        plans = db.query(TestPlan).filter(TestPlan.is_deleted == False).all()
        db_job_ids = set()

        for plan in plans:
            if plan.enable_schedule and plan.schedule_cron_expression:
                db_job_ids.add(build_job_id(plan.plan_id))
                try:
                    register_plan_schedule(plan.plan_id, plan.schedule_cron_expression)
                    restored += 1
                except Exception as e:
                    failed += 1
                    print(f"[定时任务] 计划 {plan.plan_id} 恢复失败: {e}")

        # 清理 jobstore 中已无对应启用计划的孤儿任务
        try:
            for job in _get_aps_adder().aps_obj.get_jobs():
                if job.id.startswith(JOB_ID_PREFIX) and job.id not in db_job_ids:
                    _get_aps_adder().aps_obj.remove_job(job_id=job.id)
                    cleaned += 1
                    print(f"[定时任务] 已清理孤儿任务 {job.id}")
        except Exception as e:
            print(f"[定时任务] 清理孤儿任务异常: {e}")

        print(f"[定时任务] 启动对账完成: 恢复 {restored}，失败 {failed}，清理孤儿 {cleaned}")
        return {"restored": restored, "failed": failed, "cleaned": cleaned}
    finally:
        db.close()
