"""
设备管理相关的数据模型
"""
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.sql import func
from core.database import Base


class AndroidDevice(Base):
    """安卓设备表"""
    __tablename__ = 'android_devices'

    id = Column(String(64), primary_key=True, comment='设备ID（当前连接的device code，可能是有线或无线）')
    android_id = Column(String(64), nullable=True, comment='设备唯一标识（通过adb shell settings get secure android_id获取）')
    brand = Column(String(100), default='Unknown', comment='品牌')
    model = Column(String(100), default='Unknown', comment='型号')
    resolution = Column(String(20), default='Unknown', comment='分辨率')
    android_version = Column(String(50), default='Unknown', comment='系统版本')
    system_type = Column(String(20), default='android', comment='系统类型（android/harmonyos）')
    status = Column(String(20), default='disconnected', comment='连接状态（connected/offline/disconnected）')
    last_connected_at = Column(DateTime, nullable=True, comment='最后连接时间')
    is_deleted = Column(Integer, default=0, comment='是否删除(0=未删除, 1=已删除)')
    created_at = Column(DateTime, server_default=func.now(), comment='首次连接时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')
