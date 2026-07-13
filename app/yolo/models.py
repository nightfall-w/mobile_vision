"""
YOLO 数据集模型
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, Enum
from sqlalchemy.sql import func
from core.database import Base
from core.enums import TaskStatus


class YoloDataset(Base):
    """YOLO 数据集表"""
    __tablename__ = 'yolo_datasets'

    id = Column(String(8), primary_key=True, comment='数据集ID')
    name = Column(String(255), nullable=False, comment='数据集名称')
    description = Column(Text, default='', comment='数据集描述')
    classes = Column(JSON, nullable=False, comment='类别列表')
    class_count = Column(Integer, default=0, comment='类别数量')
    image_count = Column(Integer, default=0, comment='图片数量')
    label_count = Column(Integer, default=0, comment='标注数量')
    data_yaml_path = Column(String(512), nullable=True, comment='生成的data.yaml路径')
    create_user = Column(String(100), nullable=True, comment='创建人用户名')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')
    is_deleted = Column(Integer, default=0, comment='是否删除(0=未删除, 1=已删除)')


class YoloTask(Base):
    """YOLO 训练任务表"""
    __tablename__ = 'yolo_tasks'

    id = Column(String(8), primary_key=True, comment='任务ID')
    dataset_id = Column(String(8), nullable=False, index=True, comment='数据集ID')
    model_name = Column(String(512), default='yolov8n.pt', comment='预训练模型名称')
    config = Column(JSON, nullable=False, comment='训练配置')
    status = Column(String(20), default=TaskStatus.PENDING.value, comment='任务状态')
    progress = Column(Float, default=0.0, comment='训练进度 0-100')
    current_epoch = Column(Integer, default=0, comment='当前轮次')
    total_epochs = Column(Integer, default=0, comment='总轮次')
    start_time = Column(DateTime, nullable=True, comment='开始时间')
    end_time = Column(DateTime, nullable=True, comment='结束时间')
    metrics = Column(JSON, nullable=True, comment='训练指标')
    error_message = Column(Text, nullable=True, comment='错误信息')
    result_model_path = Column(String(512), nullable=True, comment='训练结果模型路径')
    train_dir = Column(String(512), nullable=True, comment='训练目录路径')
    create_user = Column(String(100), nullable=True, comment='创建人用户名')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')
    is_deleted = Column(Integer, default=0, comment='是否删除(0=未删除, 1=已删除)')


class YoloModel(Base):
    """YOLO 模型表"""
    __tablename__ = 'yolo_models'

    id = Column(String(8), primary_key=True, comment='模型ID')
    task_id = Column(String(8), nullable=True, index=True, comment='训练任务ID')
    dataset_id = Column(String(8), nullable=False, index=True, comment='数据集ID')
    name = Column(String(255), nullable=False, comment='模型名称')
    path = Column(String(512), nullable=False, comment='模型文件路径')
    size = Column(Integer, default=0, comment='模型大小(字节)')
    metrics = Column(JSON, nullable=True, comment='模型指标')
    classes = Column(JSON, nullable=False, comment='类别列表')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    is_deleted = Column(Integer, default=0, comment='是否删除(0=未删除, 1=已删除)')
