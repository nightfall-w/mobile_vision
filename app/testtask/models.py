from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.llm.models import LLMCredential
from app.testcase.models import TestCase
from app.yolo.models import YoloModel
from core.database import Base
from core.enums import TaskStatus


class TestTask(Base):
    """测试任务：一次测试计划执行"""
    __tablename__ = 'test_task'
    
    task_id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, nullable=False, default=0)
    plan_id = Column(Integer, nullable=False)
    task_name = Column(String(200), nullable=False)
    author = Column(String(100), nullable=False)
    status = Column(String(50), default=TaskStatus.PENDING.value)
    total_jobs = Column(Integer, default=0)
    completed_jobs = Column(Integer, default=0)
    failed_jobs = Column(Integer, default=0)
    aborted_jobs = Column(Integer, default=0)
    running_jobs = Column(Integer, default=0)
    total_duration = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    start_time = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, nullable=True)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    jobs = relationship('TestJob', back_populates='task', cascade='all, delete-orphan')
    
    def to_dict(self, include_jobs=False, db=None):
        data = {
            'task_id': self.task_id,
            'workspace_id': self.workspace_id,
            'plan_id': self.plan_id,
            'task_name': self.task_name,
            'author': self.author,
            'status': self.status,
            'total_jobs': self.total_jobs,
            'completed_jobs': self.completed_jobs,
            'failed_jobs': self.failed_jobs,
            'aborted_jobs': self.aborted_jobs,
            'running_jobs': self.running_jobs,
            'is_deleted': self.is_deleted,
            'progress': self.total_jobs > 0 and round(((self.completed_jobs + self.failed_jobs + self.aborted_jobs) / self.total_jobs) * 100) or 0,
            'total_duration': self.total_duration,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else None,
        }
        
        if include_jobs and db:
            data['jobs'] = [job.to_dict(db=db) for job in self.jobs]
        
        return data


class TestJob(Base):
    """测试Job：对应具体测试用例的执行"""
    __tablename__ = 'test_job'
    
    job_id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('test_task.task_id'), nullable=False)
    case_id = Column(Integer, nullable=False)
    device_id = Column(String(100), nullable=False)
    device_name = Column(String(200))
    device_android_id = Column(String(100), nullable=True)
    llm_credential_id = Column(Integer, nullable=False)
    yolo_model_id = Column(String(50), nullable=True)
    ocr_engine = Column(String(20), default='rapidocr')
    reasoning_effort = Column(String(20), default='low')
    is_deleted = Column(Boolean, default=False)
    status = Column(String(50), default=TaskStatus.PENDING.value)
    result = Column(Text)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    task = relationship('TestTask', back_populates='jobs')
    
    def to_dict(self, db=None):
        data = {
            'job_id': self.job_id,
            'task_id': self.task_id,
            'case_id': self.case_id,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_android_id': self.device_android_id,
            'llm_credential_id': self.llm_credential_id,
            'yolo_model_id': self.yolo_model_id,
            'ocr_engine': self.ocr_engine,
            'reasoning_effort': self.reasoning_effort,
            'status': self.status,
            'result': self.result,
            'is_deleted': self.is_deleted,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'duration': self.duration,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else None,
        }
        
        if db:
            case = db.query(TestCase).filter(TestCase.case_id == self.case_id).first()
            if case:
                data['case_name'] = case.case_name
                data['case_content'] = case.content
                data['usage_instructions'] = case.usage_instructions

            if self.llm_credential_id:
                llm = db.query(LLMCredential).filter(LLMCredential.id == self.llm_credential_id).first()
                data['llm_name'] = llm.model if llm else ''

            if self.yolo_model_id:
                yolo = db.query(YoloModel).filter(YoloModel.id == self.yolo_model_id).first()
                data['yolo_name'] = yolo.name if yolo else ''
        
        return data
