"""
@FileName：models.py
@Description：LLM凭证模型
@Author：baojun.wang
"""
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from utils.commonlib import now


class LLMCredential(Base):
    """
    LLM凭证模型
    支持系统级别和工作空间级别配置
    """
    __tablename__ = "llm_credential"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="凭证ID")
    model: Mapped[str] = mapped_column(String(100), nullable=False, comment="模型名称")
    api_key: Mapped[str] = mapped_column(String(500), nullable=False, comment="API密钥")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="基础URL")
    api_protocol: Mapped[str] = mapped_column(String(50), nullable=False, comment="API协议类型(Anthropic/OpenAI)")
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id"),
        nullable=True,
        comment="工作空间ID，为空表示系统级别配置"
    )
    is_active: Mapped[int] = mapped_column(Integer, default=1, comment="是否启用(1=启用, 0=禁用)")
    is_deleted: Mapped[int] = mapped_column(Integer, default=0, comment="是否删除(0=未删除, 1=已删除)")
    create_user: Mapped[str] = mapped_column(String(100), nullable=False, comment="创建人")
    update_user: Mapped[str] = mapped_column(String(100), nullable=False, comment="更新人")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=now,
        onupdate=now,
        comment="更新时间"
    )

    def __repr__(self) -> str:
        return (f"<LLMCredential(id={self.id}, "
                f"model='{self.model}', "
                f"api_protocol='{self.api_protocol}')>")

    def to_dict(self, hide_api_key: bool = True) -> dict:
        """
        转换为字典
        :param hide_api_key: 是否隐藏API密钥
        """
        return {
            "id": self.id,
            "model": self.model,
            "api_key": "******" if hide_api_key else self.api_key,
            "base_url": self.base_url,
            "api_protocol": self.api_protocol,
            "workspace_id": self.workspace_id,
            "is_active": bool(self.is_active),
            "is_deleted": bool(self.is_deleted),
            "create_user": self.create_user,
            "update_user": self.update_user,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None
        }

    def to_dict_with_key(self) -> dict:
        """
        转换为字典（包含API密钥）
        """
        return self.to_dict(hide_api_key=False)