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
    enable_schedule: Optional[bool] = Field(False, description="是否启用定时执行")
    schedule_cron_expression: Optional[str] = Field(None, description="Cron表达式(6段: 秒 分 时 日 月 周)")
    enable_notification: Optional[bool] = Field(False, description="是否发送通知")
    notify_on_failure_only: Optional[bool] = Field(False, description="仅失败时通知")
    wecom_webhooks: Optional[List[str]] = Field(default_factory=list, description="企微webhook列表")
    lark_webhooks: Optional[List[str]] = Field(default_factory=list, description="飞书webhook列表")
    dingtalk_webhooks: Optional[List[str]] = Field(default_factory=list, description="钉钉webhook列表")


class UpdatePlanRequest(BaseModel):
    """更新测试计划请求"""
    plan_id: int = Field(..., description="计划ID")
    name: Optional[str] = Field(None, description="计划名称")
    description: Optional[str] = Field(None, description="计划描述")
    enable_schedule: Optional[bool] = Field(None, description="是否启用定时执行")
    schedule_cron_expression: Optional[str] = Field(None, description="Cron表达式(6段: 秒 分 时 日 月 周)")
    enable_notification: Optional[bool] = Field(None, description="是否发送通知")
    notify_on_failure_only: Optional[bool] = Field(None, description="仅失败时通知")
    wecom_webhooks: Optional[List[str]] = Field(None, description="企微webhook列表")
    lark_webhooks: Optional[List[str]] = Field(None, description="飞书webhook列表")
    dingtalk_webhooks: Optional[List[str]] = Field(None, description="钉钉webhook列表")


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
