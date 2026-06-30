"""
YOLO 训练任务 API - 使用 FunBoost 异步队列
"""
from fastapi import APIRouter, Body, Query, Depends
from pathlib import Path

from core.response import HttpErrcode, api_response
from core.config import PROJECT_ROOT
from core.enums import TaskStatus
from core.auth_middleware import get_current_user
from app.user.models import UserModel
from app.yolo.controller import (
    get_dataset,
    get_tasks,
    get_task,
    create_task,
    update_task,
    delete_task,
    abort_task,
    get_all_models,
    create_model
)
from services.yolo_train_consumer import submit_train_task

router = APIRouter(prefix="/train", tags=["训练"])

YOLO_ROOT = PROJECT_ROOT / 'models' / 'yolo'


@router.get("/models")
async def list_models_api(current_user: UserModel = Depends(get_current_user)):
    """获取可用的预训练模型列表（包含基础模型和已训练模型）"""
    models = []

    if YOLO_ROOT.exists():
        for pt_file in YOLO_ROOT.glob('*.pt'):
            models.append({
                'name': pt_file.name,
                'path': str(pt_file),
                'size': pt_file.stat().st_size,
                'type': 'base'
            })

    trained_models = get_all_models()
    for model in trained_models:
        models.append({
            'name': model['name'],
            'path': model['path'],
            'size': model.get('size', 0),
            'type': 'trained',
            'model_id': model['id'],
            'dataset_id': model['dataset_id'],
            'metrics': model.get('metrics', {})
        })

    return api_response(data=models)


@router.post("/start")
async def start_training_api(
    request_data: dict = Body(...),
    current_user: UserModel = Depends(get_current_user)
):
    """开始训练"""
    dataset_id = request_data.get('dataset_id')
    
    config_data = request_data.get('config', request_data)
    
    model_name = config_data.get('model_name', 'yolov8n.pt')
    epochs = config_data.get('epochs', 50)
    batch_size = config_data.get('batch_size', 8)
    imgsz = config_data.get('imgsz', 640)
    device = config_data.get('device', 'cpu')
    lr0 = config_data.get('lr0', 0.01)
    optimizer = config_data.get('optimizer', 'auto')

    dataset = get_dataset(dataset_id)
    if not dataset:
        return api_response(code=HttpErrcode.NOT_FOUND, message="数据集不存在")

    tasks, _ = get_tasks()
    for task in tasks:
        if task['dataset_id'] == dataset_id and task['status'] in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
            return api_response(
                code=HttpErrcode.PARAMS_ERROR,
                message="该数据集已有训练任务在运行"
            )

    train_config = {
        'model_name': model_name,
        'epochs': epochs,
        'batch_size': batch_size,
        'imgsz': imgsz,
        'device': device,
        'lr0': lr0,
        'optimizer': optimizer
    }

    task = create_task(dataset_id, train_config)

    submit_train_task(task['id'])

    return api_response(data=task, message="训练任务已提交到队列")


@router.get("/tasks")
async def list_tasks_api(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    keyword: str = Query(None, description="搜索关键词"),
    status: str = Query(None, description="任务状态"),
    current_user: UserModel = Depends(get_current_user)
):
    """训练任务列表（支持分页和筛选）"""
    tasks, total = get_tasks(page=page, page_size=page_size, keyword=keyword, status=status)
    return api_response(data={"tasks": tasks, "total": total, "page": page, "page_size": page_size})


@router.get("/tasks/{task_id}")
async def get_task_api(
    task_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """获取训练任务详情"""
    task = get_task(task_id)
    if not task:
        return api_response(code=HttpErrcode.NOT_FOUND, message="任务不存在")
    return api_response(data=task)


@router.post("/tasks/{task_id}/retry")
async def retry_training_api(
    task_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """重试训练任务"""
    task = get_task(task_id)
    if not task:
        return api_response(code=HttpErrcode.NOT_FOUND, message="任务不存在")
    
    if task['status'] != TaskStatus.FAILED.value:
        return api_response(
            code=HttpErrcode.PARAMS_ERROR,
            message="只有失败的任务才能重试"
        )
    
    update_task(
        task_id,
        status=TaskStatus.PENDING.value,
        error_message=None
    )
    
    submit_train_task(task_id)
    
    return api_response(data=task, message="训练任务已重新提交到队列")


@router.post("/tasks/{task_id}/abort")
async def abort_task_api(
    task_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """取消训练任务"""
    task = get_task(task_id)
    if not task:
        return api_response(code=HttpErrcode.NOT_FOUND, message="任务不存在")
    
    if task['status'] not in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
        return api_response(
            code=HttpErrcode.PARAMS_ERROR,
            message="只有等待中或运行中的任务才能取消"
        )
    
    abort_task(task_id)
    return api_response(message="任务已取消")


@router.delete("/tasks/{task_id}")
async def delete_task_api(
    task_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """删除训练任务"""
    delete_task(task_id)
    return api_response(message="任务删除成功")