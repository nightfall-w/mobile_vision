"""
YOLO 相关的请求和响应模型
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class DatasetCreate(BaseModel):
    """创建数据集请求模型"""
    name: str
    description: Optional[str] = ""
    classes: Optional[List[str]] = None


class DatasetUpdate(BaseModel):
    """更新数据集请求模型"""
    dataset_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    classes: Optional[Any] = None


class DatasetDetail(BaseModel):
    """数据集详情响应模型"""
    id: str
    name: str
    description: str
    classes: List[str]
    class_count: int
    image_count: int
    label_count: int
    data_yaml_path: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class TaskCreate(BaseModel):
    """创建训练任务请求模型"""
    dataset_id: str
    config: Optional[Dict[str, Any]] = None


class TaskUpdate(BaseModel):
    """更新任务状态请求模型"""
    task_id: str
    status: Optional[str] = None
    progress: Optional[float] = None
    current_epoch: Optional[int] = None
    metrics: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    result_model_path: Optional[str] = None
    train_dir: Optional[str] = None


class TaskDetail(BaseModel):
    """训练任务详情响应模型"""
    id: str
    dataset_id: str
    dataset_name: str
    dataset_detail: Optional[Dict]
    model_name: str
    config: Dict[str, Any]
    status: str
    progress: float
    current_epoch: int
    total_epochs: int
    metrics: Optional[Dict[str, Any]]
    start_time: Optional[str]
    end_time: Optional[str]
    error_message: Optional[str]
    result_model_path: Optional[str]
    train_dir: Optional[str]
    created_at: Optional[str]


class ModelCreate(BaseModel):
    """创建模型记录请求模型"""
    task_id: str
    dataset_id: str
    name: str
    path: str
    metrics: Dict[str, Any]
    classes: List[str]


class ModelDetail(BaseModel):
    """模型详情响应模型"""
    id: str
    task_id: Optional[str]
    dataset_id: str
    dataset_name: str
    dataset_detail: Optional[Dict]
    name: str
    path: str
    size: int
    metrics: Optional[Dict[str, Any]]
    classes: List[str]
    config: Optional[Dict[str, Any]]
    model_name: Optional[str]
    created_at: Optional[str]


class PaginationResponse(BaseModel):
    """分页响应模型"""
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


class ImageUploadResponse(BaseModel):
    """图片上传响应模型"""
    count: int
    message: str