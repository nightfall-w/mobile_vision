"""
测试计划模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from datetime import datetime

from core.database import Base


class TestPlan(Base):
    """测试计划"""
    __tablename__ = 'test_plan'
    
    plan_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    workspace_id = Column(Integer, nullable=False)
    author = Column(String(100), nullable=False)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = Column(Boolean, default=False)

    def to_dict(self):
        return {
            'plan_id': self.plan_id,
            'name': self.name,
            'description': self.description,
            'workspace_id': self.workspace_id,
            'author': self.author,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else None,
            'is_deleted': self.is_deleted
        }


class PlanCaseRelation(Base):
    """计划用例关联表"""
    __tablename__ = 'plan_case_relation'

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, nullable=False)
    case_id = Column(Integer, nullable=False)
    device_id = Column(String(100), nullable=True, comment="设备ID，为空表示动态分配")
    device_name = Column(String(200), comment="设备名称，为空表示动态分配")
    device_android_id = Column(String(64))
    llm_credential_id = Column(Integer, nullable=False)
    yolo_model_id = Column(String(50))
    ocr_engine = Column(String(20), default='rapidocr')
    reasoning_effort = Column(String(20), default='low')
    is_deleted = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'case_id': self.case_id,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_android_id': self.device_android_id,
            'llm_credential_id': self.llm_credential_id,
            'yolo_model_id': self.yolo_model_id,
            'ocr_engine': self.ocr_engine,
            'reasoning_effort': self.reasoning_effort,
            'is_deleted': self.is_deleted,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None
        }


class DeviceLock(Base):
    """设备锁 - 用于设备占用管理"""
    __tablename__ = 'device_lock'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(100), nullable=False, unique=True)
    task_id = Column(Integer)
    plan_id = Column(Integer)
    locked_by = Column(String(100))
    locked_at = Column(DateTime)
    expires_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'task_id': self.task_id,
            'plan_id': self.plan_id,
            'locked_by': self.locked_by,
            'locked_at': self.locked_at.isoformat() if self.locked_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
