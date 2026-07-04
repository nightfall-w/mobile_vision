"""
任务执行记录数据库模型 - 用于持久化存储
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from datetime import datetime

from core.database import Base


class TaskExecutionRecord(Base):
    """任务执行记录"""
    __tablename__ = 'task_execution_record'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False, index=True)
    status = Column(String(50), nullable=False)
    total_steps = Column(Integer, default=0)
    success_steps = Column(Integer, default=0)
    failed_steps = Column(Integer, default=0)
    task_list = Column(JSON)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'status': self.status,
            'total_steps': self.total_steps,
            'success_steps': self.success_steps,
            'failed_steps': self.failed_steps,
            'task_list': self.task_list,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TaskExecutionLog(Base):
    """任务执行日志"""
    __tablename__ = 'task_execution_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False, index=True)
    level = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    page_structure = Column(JSON, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'level': self.level,
            'message': self.message,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'page_structure': self.page_structure
        }
