"""
@FileName：request_models.py
@Description：用例相关的请求模型
@Author：baojun.wang
"""
from pydantic import BaseModel
from typing import Optional


class CreateTestCaseRequest(BaseModel):
    workspace_id: int
    case_name: str
    case_desc: Optional[str] = None
    content: Optional[str] = None
    usage_instructions: Optional[str] = None
    level: str = "P2"
    status: str = "debugging"


class UpdateTestCaseRequest(BaseModel):
    case_id: int
    case_name: Optional[str] = None
    case_desc: Optional[str] = None
    content: Optional[str] = None
    usage_instructions: Optional[str] = None
    level: Optional[str] = None
    status: Optional[str] = None


class TestCaseListRequest(BaseModel):
    workspace_id: int
    case_name: Optional[str] = None
    status: Optional[str] = None
    level: Optional[str] = None
    page_num: int = 1
    page_size: int = 10
