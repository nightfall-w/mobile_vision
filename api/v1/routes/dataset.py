"""
@FileName：dataset.py
@Description：数据集相关API
@Author：baojun.wang
"""
from fastapi import APIRouter, UploadFile, File, Form, Query, Body, Depends
from fastapi.responses import FileResponse
from typing import List, Optional, Any
import os
import shutil
from pathlib import Path

from core.response import HttpErrcode, api_response
from core.config import PROJECT_ROOT
from core.auth_middleware import get_current_user
from app.user.models import UserModel
from app.yolo.controller import (
    create_dataset,
    get_datasets,
    get_dataset,
    delete_dataset,
    update_dataset,
    update_dataset_statistics,
    update_dataset_stats,
    generate_data_yaml
)

router = APIRouter(prefix="/dataset", tags=["数据集"])

YOLO_ROOT = PROJECT_ROOT / 'models' / 'yolo'
DATA_STORAGE_ROOT = YOLO_ROOT / 'data'


@router.post("/create")
async def create_dataset_api(
        name: str = Form(...),
        description: str = Form(""),
        current_user: UserModel = Depends(get_current_user)
):
    """创建数据集"""
    dataset = create_dataset(name, description, [])
    return api_response(data=dataset, message="数据集创建成功")


@router.get("/list")
async def list_dataset_api(current_user: UserModel = Depends(get_current_user)):
    """数据集列表"""
    datasets = get_datasets()
    return api_response(data=datasets)


@router.get("/{dataset_id}")
async def get_dataset_api(
    dataset_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """获取数据集详情"""
    dataset = get_dataset(dataset_id)
    if dataset:
        return api_response(data=dataset)
    return api_response(code=HttpErrcode.NOT_FOUND, message="数据集不存在")


@router.delete("/{dataset_id}")
async def delete_dataset_api(
    dataset_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """删除数据集"""
    delete_dataset(dataset_id)
    return api_response(message="数据集删除成功")


@router.post("/{dataset_id}/recount")
async def recount_dataset_api(
    dataset_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """重新统计数据集"""
    update_dataset_statistics(dataset_id)
    dataset = get_dataset(dataset_id)
    if dataset:
        return api_response(data=dataset, message="统计完成")
    return api_response(code=HttpErrcode.NOT_FOUND, message="数据集不存在")


@router.post("/{dataset_id}/images")
async def upload_images_api(
        dataset_id: str,
        files: List[UploadFile] = File(...),
        split: str = Form(..., description="选择上传到哪个集合：train/val/test"),
        current_user: UserModel = Depends(get_current_user)
):
    """上传图片"""
    dataset = get_dataset(dataset_id)
    if not dataset:
        return api_response(code=HttpErrcode.NOT_FOUND, message="数据集不存在")
    
    if split not in ['train', 'val', 'test']:
        return api_response(code=HttpErrcode.PARAMS_ERROR, message="split参数必须是train、val或test")

    dataset_dir = DATA_STORAGE_ROOT / dataset_id
    images_dir = dataset_dir / 'images'
    images_dir.mkdir(exist_ok=True)
    
    target_dir = images_dir / split
    target_dir.mkdir(exist_ok=True)

    uploaded_count = 0
    for file in files:
        file_path = target_dir / file.filename
        with open(file_path, 'wb') as buffer:
            content = await file.read()
            buffer.write(content)
        uploaded_count += 1

    update_dataset_stats(dataset_id)

    return api_response(data={
        'count': uploaded_count,
        'split': split
    }, message=f"成功上传 {uploaded_count} 张图片到{'训练集' if split == 'train' else '验证集' if split == 'val' else '测试集'}")


@router.get("/{dataset_id}/images")
async def list_images_api(
        dataset_id: str,
        split: Optional[str] = Query(None, description="数据集分割：train/val/test"),
        current_user: UserModel = Depends(get_current_user)
):
    """获取数据集图片列表，按上传时间从新到旧排序"""
    dataset_dir = DATA_STORAGE_ROOT / dataset_id
    if not dataset_dir.exists():
        return api_response(code=HttpErrcode.NOT_FOUND, message="数据集不存在")

    images_dir = dataset_dir / 'images'
    image_list = []

    if split and split in ['train', 'val', 'test']:
        split_dir = images_dir / split
        if split_dir.exists():
            for f in split_dir.iterdir():
                if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                    image_list.append((f"{split}/{f.name}", f.stat().st_mtime))
    else:
        if images_dir.exists():
            for f in images_dir.iterdir():
                if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                    image_list.append((f.name, f.stat().st_mtime))
                elif f.is_dir():
                    for img in f.iterdir():
                        if img.is_file() and img.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                            image_list.append((f"{f.name}/{img.name}", img.stat().st_mtime))

    # 按修改时间从新到旧排序
    image_list.sort(key=lambda x: x[1], reverse=True)
    image_list = [item[0] for item in image_list]

    return api_response(data=image_list)


@router.get("/{dataset_id}/images/{filename:path}")
async def get_image_api(
    dataset_id: str,
    filename: str,
    current_user: UserModel = Depends(get_current_user)
):
    """获取图片文件"""
    dataset_dir = DATA_STORAGE_ROOT / dataset_id
    images_dir = dataset_dir / 'images'

    file_path = images_dir / filename
    if not file_path.exists():
        file_path = dataset_dir / filename
    if not file_path.exists():
        return api_response(code=HttpErrcode.NOT_FOUND, message="文件不存在")
    return FileResponse(file_path)


@router.post("/{dataset_id}/split")
async def split_dataset_api(
        dataset_id: str,
        train_ratio: float = 0.7,
        val_ratio: float = 0.2,
        test_ratio: float = 0.1,
        current_user: UserModel = Depends(get_current_user)
):
    """划分训练集/验证集/测试集"""
    dataset_dir = DATA_STORAGE_ROOT / dataset_id
    images_dir = dataset_dir / 'images'
    labels_dir = dataset_dir / 'labels'

    if not images_dir.exists():
        return api_response(code=HttpErrcode.NOT_FOUND, message="数据集不存在")

    import random

    all_images = []
    for f in images_dir.iterdir():
        if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
            all_images.append(f)

    if not all_images:
        return api_response(code=HttpErrcode.PARAMS_ERROR, message="没有图片可划分")

    random.shuffle(all_images)
    total = len(all_images)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)

    train_images = all_images[:train_end]
    val_images = all_images[train_end:val_end]
    test_images = all_images[val_end:]

    for split, images in [('train', train_images), ('val', val_images), ('test', test_images)]:
        split_img_dir = images_dir / split
        split_img_dir.mkdir(exist_ok=True)
        split_lbl_dir = labels_dir / split
        split_lbl_dir.mkdir(exist_ok=True)

        for img in images:
            shutil.move(str(img), str(split_img_dir / img.name))

            label_file = labels_dir / (img.stem + '.txt')
            if label_file.exists():
                shutil.move(str(label_file), str(split_lbl_dir / label_file.name))
    
    # 划分完成后自动更新 data.yaml
    yaml_path = generate_data_yaml(dataset_id)

    return api_response(data={
        'train': len(train_images),
        'val': len(val_images),
        'test': len(test_images),
        'data_yaml_path': yaml_path
    }, message="数据集划分成功")


@router.post("/update")
async def update_dataset_api(
        dataset_id: str = Body(...),
        name: str = Body(None),
        description: str = Body(None),
        classes: Any = Body(None),
        current_user: UserModel = Depends(get_current_user)
):
    """更新数据集信息"""
    dataset = get_dataset(dataset_id)
    if not dataset:
        return api_response(code=HttpErrcode.NOT_FOUND, message="数据集不存在")

    processed_classes = None
    if classes is not None:
        old_classes = dataset['classes']
        old_classes_count = len(old_classes) if isinstance(old_classes, list) else 0

        if len(classes) < old_classes_count:
            return api_response(
                code=HttpErrcode.PARAMS_ERROR,
                message="不能删除类别，只能增加新类别"
            )

        processed_classes = []
        for cls in classes:
            if isinstance(cls, dict):
                processed_classes.append({
                    'english': cls.get('english', ''),
                    'chinese': cls.get('chinese', '')
                })
            else:
                processed_classes.append(cls)

    update_dataset(
        dataset_id,
        name=name,
        description=description,
        classes=processed_classes
    )

    return api_response(message="数据集更新成功")