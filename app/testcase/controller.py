"""
@FileName：controller.py
@Description：用例相关模型的增删改查操作
@Author：baojun.wang
"""
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.testcase.models import TestCase
from utils.custom_logging import logger


class TestCaseCRUD:
    """用例相关操作类"""

    def __init__(self, db: Session):
        self.db = db

    def get_case_by_id(self, case_id: int) -> Optional[TestCase]:
        """根据ID获取用例"""
        stmt = select(TestCase).where(TestCase.case_id == case_id, TestCase.is_deleted == 0)
        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_cases_by_workspace_with_count(
            self,
            workspace_id: int,
            case_name: Optional[str] = None,
            status: Optional[str] = None,
            level: Optional[str] = None,
            limit: int = 10,
            offset: int = 0
    ) -> Tuple[List[TestCase], int]:
        """获取工作空间的用例列表及总数"""

        conditions = [TestCase.workspace_id == workspace_id, TestCase.is_deleted == 0]

        if case_name:
            conditions.append(TestCase.case_name.like(f"%{case_name}%"))

        if status:
            conditions.append(TestCase.status == status)

        if level:
            conditions.append(TestCase.level == level)

        # 查询总数
        count_stmt = select(func.count()).select_from(TestCase).where(and_(*conditions))
        count_result = self.db.execute(count_stmt)
        total_count = count_result.scalar()

        # 查询当前页数据
        stmt = select(TestCase).where(and_(*conditions)).order_by(TestCase.case_id.desc()).limit(limit).offset(offset)
        result = self.db.execute(stmt)
        cases = result.scalars().all()

        return cases, total_count

    def create_case(
            self,
            workspace_id: int,
            case_name: str,
            case_desc: Optional[str],
            content: Optional[str],
            usage_instructions: Optional[str],
            author: str,
            level: str = "P2",
            status: str = "debugging"
    ) -> Optional[TestCase]:
        """创建用例"""
        try:
            case = TestCase(
                workspace_id=workspace_id,
                case_name=case_name,
                case_desc=case_desc,
                content=content,
                usage_instructions=usage_instructions,
                author=author,
                updater=author,
                level=level,
                status=status
            )
            self.db.add(case)
            self.db.commit()
            self.db.refresh(case)
            return case
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"创建用例失败: {str(e)}")
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建用例异常: {str(e)}")
            return None

    def update_case(
            self,
            case_id: int,
            case_name: Optional[str] = None,
            case_desc: Optional[str] = None,
            content: Optional[str] = None,
            usage_instructions: Optional[str] = None,
            updater: Optional[str] = None,
            level: Optional[str] = None,
            status: Optional[str] = None
    ) -> bool:
        """更新用例"""
        try:
            stmt = update(TestCase).where(TestCase.case_id == case_id)
            values = {}

            if case_name is not None:
                values["case_name"] = case_name
            if case_desc is not None:
                values["case_desc"] = case_desc
            if content is not None:
                values["content"] = content
            if usage_instructions is not None:
                values["usage_instructions"] = usage_instructions
            if updater is not None:
                values["updater"] = updater
            if level is not None:
                values["level"] = level
            if status is not None:
                values["status"] = status

            if values:
                stmt = stmt.values(**values)
                self.db.execute(stmt)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新用例失败: {str(e)}")
            return False

    def delete_case(self, case_id: int) -> bool:
        """删除用例（软删除）"""
        try:
            stmt = update(TestCase).where(TestCase.case_id == case_id).values(is_deleted=1, update_time=datetime.now())
            self.db.execute(stmt)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除用例失败: {str(e)}")
            return False

    def get_case_count_by_workspace(self, workspace_id: int) -> int:
        """统计工作空间的用例数量"""
        stmt = select(func.count()).select_from(TestCase).where(
            and_(TestCase.workspace_id == workspace_id, TestCase.is_deleted == 0)
        )
        result = self.db.execute(stmt)
        return result.scalar()

    def get_case_count_by_status(self, workspace_id: int, status: str) -> int:
        """统计工作空间指定状态的用例数量"""
        stmt = select(func.count()).select_from(TestCase).where(
            and_(TestCase.workspace_id == workspace_id, TestCase.status == status)
        )
        result = self.db.execute(stmt)
        return result.scalar()
