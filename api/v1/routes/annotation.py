"""
@FileName：annotation.py
@Description：标注相关API
@Author：baojun.wang
"""
from fastapi import APIRouter, Body, Depends
from typing import List, Dict
from pathlib import Path

from core.response import HttpErrcode, api_response
from core.config import PROJECT_ROOT
from core.auth_middleware import get_current_user
from app.user.models import UserModel
from app.yolo.controller import (
    get_dataset,
    update_dataset_stats
)

router = APIRouter(prefix="/annotation", tags=["标注"])

YOLO_ROOT = PROJECT_ROOT / 'models' / 'yolo'
DATA_STORAGE_ROOT = YOLO_ROOT / 'data'


@router.get("/{dataset_id}/{image_name:path}")
async def get_annotation_api(
    dataset_id: str,
    image_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """获取图片的标注"""
    dataset = get_dataset(dataset_id)
    if not dataset:
        return api_response(code=HttpErrcode.NOT_FOUND, message="数据集不存在")
    
    image_path = Path(image_name)
    label_name = image_path.stem + '.txt'
    
    dataset_dir = DATA_STORAGE_ROOT / dataset_id
    labels_dir = dataset_dir / 'labels'
    
    label_file = None
    if labels_dir.exists():
        if (labels_dir / label_name).exists():
            label_file = labels_dir / label_name
        else:
            for split in ['train', 'val', 'test']:
                split_dir = labels_dir / split
                if (split_dir / label_name).exists():
                    label_file = split_dir / label_name
                    break
    
    annotations = []
    if label_file and label_file.exists():
        with open(label_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split()
                    if len(parts) >= 5:
                        class_id = int(float(parts[0]))
                        annotations.append({
                            'class_id': class_id,
                            'class_name': dataset['classes'][class_id] if class_id < len(dataset['classes']) else f'class_{class_id}',
                            'x': float(parts[1]),
                            'y': float(parts[2]),
                            'width': float(parts[3]),
                            'height': float(parts[4])
                        })
    
    return api_response(data={
        'image_name': image_name,
        'annotations': annotations,
        'classes': dataset['classes']
    })


@router.post("/{dataset_id}/{image_name:path}")
async def save_annotation_api(
    dataset_id: str,
    image_name: str,
    annotations: List[Dict] = Body(...),
    current_user: UserModel = Depends(get_current_user)
):
    """保存图片标注"""
    dataset = get_dataset(dataset_id)
    if not dataset:
        return api_response(code=HttpErrcode.NOT_FOUND, message="数据集不存在")
    
    image_path = Path(image_name)
    label_name = image_path.stem + '.txt'
    
    dataset_dir = DATA_STORAGE_ROOT / dataset_id
    labels_dir = dataset_dir / 'labels'
    
    save_dir = labels_dir
    if '/' in image_name or '\\' in image_name:
        parts = image_path.parts
        for i, part in enumerate(parts):
            if part in ['train', 'val', 'test']:
                split_dir = labels_dir / part
                split_dir.mkdir(exist_ok=True)
                save_dir = split_dir
                break
    
    label_file = save_dir / label_name
    
    with open(label_file, 'w') as f:
        for ann in annotations:
            class_id = ann.get('class_id', 0)
            x = ann.get('x', 0.0)
            y = ann.get('y', 0.0)
            width = ann.get('width', 0.0)
            height = ann.get('height', 0.0)
            f.write(f"{class_id} {x} {y} {width} {height}\n")
    
    update_dataset_stats(dataset_id)
    
    return api_response(message="标注保存成功")


@router.delete("/{dataset_id}/{image_name:path}")
async def delete_annotation_api(
    dataset_id: str,
    image_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """删除图片标注"""
    dataset = get_dataset(dataset_id)
    if not dataset:
        return api_response(code=HttpErrcode.NOT_FOUND, message="数据集不存在")
    
    image_path = Path(image_name)
    label_name = image_path.stem + '.txt'
    
    dataset_dir = DATA_STORAGE_ROOT / dataset_id
    labels_dir = dataset_dir / 'labels'
    
    deleted = False
    if labels_dir.exists():
        label_file = labels_dir / label_name
        if label_file.exists():
            label_file.unlink()
            deleted = True
        for split in ['train', 'val', 'test']:
            split_dir = labels_dir / split
            label_file = split_dir / label_name
            if label_file.exists():
                label_file.unlink()
                deleted = True
    
    if deleted:
        update_dataset_stats(dataset_id)
    
    return api_response(message="标注删除成功" if deleted else "没有找到标注文件")