"""
数据库初始化模块
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import SYNC_ENGINE, Base
from app.user.models import UserModel, SuperAdminModel
from app.workspace.models import Workspace, MemberRole, WorkspaceMember
from app.device.devices_models import AndroidDevice
from app.yolo.models import YoloDataset, YoloTask, YoloModel
from app.llm.models import LLMCredential
from app.testcase.models import TestCase
from app.testtask.models import TestTask, TestJob
from app.testplan.models import TestPlan, PlanCaseRelation, DeviceLock
from app.task_monitor.db_models import TaskExecutionRecord, TaskExecutionLog


def init_database():
    """初始化所有数据库表"""
    print("开始初始化数据库表...")

    Base.metadata.create_all(bind=SYNC_ENGINE)

    print("✅ 数据库表创建成功！")
    print("   - users (用户表)")
    print("   - super_admins (超级管理员表)")
    print("   - workspace (工作空间表)")
    print("   - member_role (成员角色表)")
    print("   - workspace_member (工作空间成员表)")
    print("   - android_devices (安卓设备表)")
    print("   - yolo_datasets (YOLO数据集表)")
    print("   - yolo_tasks (YOLO训练任务表)")
    print("   - yolo_models (YOLO模型表)")
    print("   - llm_credential (LLM凭证表)")
    print("   - test_case (测试用例表)")
    print("   - test_task (测试任务表)")
    print("   - test_job (测试Job表)")
    print("   - test_plan (测试计划表)")
    print("   - plan_case_relation (计划用例关联表)")
    print("   - device_lock (设备锁表)")
    print("   - task_execution_record (任务执行记录表)")
    print("   - task_execution_log (任务执行日志表)")


def drop_all_tables():
    """删除所有数据库表（谨慎使用）"""
    print("⚠️  开始删除所有数据库表...")
    Base.metadata.drop_all(bind=SYNC_ENGINE)
    print("✅ 所有数据库表已删除")


if __name__ == "__main__":
    init_database()
