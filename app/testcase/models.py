"""
@FileName：models.py
@Description：用例模型
@Author：baojun.wang
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from utils.commonlib import now


class TestCase(Base):
    """
    用例模型
    """
    __tablename__ = "test_case"

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="用例ID")
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspace.workspace_id"),
        nullable=False,
        comment="工作空间ID"
    )
    case_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="用例名称")
    case_desc: Mapped[str] = mapped_column(Text, nullable=True, comment="用例描述")
    content: Mapped[str] = mapped_column(Text, nullable=True, comment="测试任务正文（支持Markdown）")
    usage_instructions: Mapped[str] = mapped_column(Text, nullable=True, comment="APP使用说明（支持Markdown）")
    author: Mapped[str] = mapped_column(String(100), nullable=False, comment="创建人用户名")
    updater: Mapped[str] = mapped_column(String(100), nullable=False, comment="更新人用户名")
    level: Mapped[str] = mapped_column(Enum("P0", "P1", "P2", "P3"), nullable=False, default="P2", comment="优先级")
    status: Mapped[str] = mapped_column(Enum("debugging", "completed", "disabled"), nullable=False, default="debugging", comment="状态")
    is_deleted: Mapped[int] = mapped_column(Integer, default=0, comment="是否删除(0=未删除, 1=已删除)")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=now,
        onupdate=now,
        comment="更新时间"
    )

    def __repr__(self) -> str:
        return (f"<TestCase(case_id={self.case_id}, "
                f"case_name='{self.case_name}', "
                f"status='{self.status}')>")

    def to_dict(self) -> dict:
        """
        转换为字典
        """
        status_map = {
            "debugging": "调试中",
            "completed": "已完成",
            "disabled": "禁用"
        }
        
        level_map = {
            "P0": "P0",
            "P1": "P1",
            "P2": "P2",
            "P3": "P3"
        }

        return {
            "case_id": self.case_id,
            "workspace_id": self.workspace_id,
            "case_name": self.case_name,
            "case_desc": self.case_desc,
            "content": self.content,
            "usage_instructions": self.usage_instructions,
            "author": self.author,
            "updater": self.updater,
            "level": self.level,
            "level_display": level_map.get(self.level, self.level),
            "status": self.status,
            "status_display": status_map.get(self.status, self.status),
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None
        }