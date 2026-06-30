from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class CreateTaskRequest(BaseModel):
    workspace_id: int = Field(..., description="工作空间ID")
    case_id: int = Field(..., description="用例ID")
    device_id: str = Field(..., description="设备ID")
    device_name: str = Field(..., description="设备名称")
    device_android_id: Optional[str] = Field(None, description="设备Android ID")
    llm_credential_id: int = Field(..., description="LLM凭证ID")
    yolo_model_id: Optional[str] = Field(None, description="YOLO模型ID")
    ocr_engine: Optional[str] = Field('rapidocr', description="OCR引擎，可选 easyocr 或 rapidocr")


class UpdateTaskRequest(BaseModel):
    model_config = ConfigDict(extra='allow')

    task_id: int = Field(..., description="任务ID")
    case_id: int = Field(None, description="用例ID")
    device_id: str = Field(None, description="设备ID")
    device_name: str = Field(None, description="设备名称")
    device_android_id: Optional[str] = Field(None, description="设备Android ID")
    llm_credential_id: int = Field(None, description="LLM凭证ID")
    yolo_model_id: Optional[str] = Field(None, description="YOLO模型ID")
    ocr_engine: Optional[str] = Field(None, description="OCR引擎")
    status: str = Field(None, description="任务状态")
