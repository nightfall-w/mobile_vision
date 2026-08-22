"""
@FileName：models.py
@Description：系统配置模型
@Author：baojun.wang
"""
from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from utils.commonlib import now


class SystemConfig(Base):
    """
    系统级配置项

    以 key-value 形式存放全局配置，避免域名、端口一类部署相关的值散落在代码里。
    键名由代码约定（见 core/system_setting.py 中的常量），页面上只允许改值和描述。
    """
    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="配置项ID")
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="配置项键名")
    value: Mapped[str] = mapped_column(Text, nullable=True, comment="配置项值（统一按字符串存，按 type 解析）")
    desc: Mapped[str] = mapped_column(String(500), nullable=True, comment="配置项描述")
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="STRING",
                                      comment="值类型(STRING/NUMBER/BOOLEAN/DICT/LIST)")
    required: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否必填")
    verified: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否通过可用性验证")
    update_user: Mapped[str] = mapped_column(String(100), nullable=True, comment="更新人")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, comment="更新时间")

    def __repr__(self) -> str:
        return f"<SystemConfig(id={self.id}, key='{self.key}')>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "desc": self.desc,
            "type": self.type,
            "required": bool(self.required),
            "verified": bool(self.verified),
            "update_user": self.update_user,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None,
        }
