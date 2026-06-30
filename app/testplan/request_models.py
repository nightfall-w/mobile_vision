"""
测试计划请求模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class CreatePlanRequest(BaseModel):
    """创建测试计划请求"""
    name: str = Field(..., description="计划名称")
    description: Optional[str] = Field(None, description="计划描述")
    workspace_id: int = Field(..., description="工作空间ID")


class UpdatePlanRequest(BaseModel):
    """更新测试计划请求"""
    plan_id: int = Field(..., description="计划ID")
    name: Optional[str] = Field(None, description="计划名称")
    description: Optional[str] = Field(None, description="计划描述")


class AddCaseRelationRequest(BaseModel):
    """添加用例关联请求"""
    plan_id: int = Field(..., description="计划ID")
    case_id: int = Field(..., description="用例ID")
    device_id: Optional[str] = Field(None, description="设备ID，不填则执行时动态分配给空闲设备")
    device_name: Optional[str] = Field(None, description="设备名称，不填则执行时动态分配给空闲设备")
    device_android_id: Optional[str] = Field(None, description="设备Android ID")
    llm_credential_id: int = Field(..., description="LLM凭证ID")
    yolo_model_id: Optional[str] = Field(None, description="YOLO模型ID")
    ocr_engine: str = Field('rapidocr', description="OCR引擎")
    reasoning_effort: str = Field('low', description="推理强度，可选 none/low/medium/high")


class UpdateCaseRelationRequest(BaseModel):
    """更新用例关联请求"""
    id: int = Field(..., description="关联ID")
    device_id: Optional[str] = Field(None, description="设备ID")
    device_name: Optional[str] = Field(None, description="设备名称")
    device_android_id: Optional[str] = Field(None, description="设备Android ID")
    llm_credential_id: Optional[int] = Field(None, description="LLM凭证ID")
    yolo_model_id: Optional[str] = Field(None, description="YOLO模型ID")
    ocr_engine: Optional[str] = Field(None, description="OCR引擎")
    reasoning_effort: Optional[str] = Field(None, description="推理强度，可选 none/low/medium/high")


class ExecutePlanRequest(BaseModel):
    """执行测试计划请求"""
    plan_id: int = Field(..., description="计划ID")


class RemoveCaseRelationRequest(BaseModel):
    """移除用例关联请求（伪删除）"""
    id: int = Field(..., description="关联ID")


class DeletePlanRequest(BaseModel):
    """删除测试计划请求"""
    plan_id: int = Field(..., description="计划ID")
