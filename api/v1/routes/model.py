"""
@FileName：model.py
@Description：模型相关API
@Author：baojun.wang
"""
from fastapi import APIRouter, UploadFile, File, Form, Query, Depends
from fastapi.responses import FileResponse
from typing import List, Optional
import os
import time
import shutil
from pathlib import Path

from core.response import HttpErrcode, api_response
from core.config import YOLO_DATASETS_DIR, YOLO_MODELS_DIR, YOLO_OUTPUT_DIR, YOLO_OUTPUT_URL
from core.auth_middleware import get_current_user
from app.user.models import UserModel
from app.yolo.controller import (
    get_models,
    get_model,
    delete_model
)
from models.yolo.predictor import YOLOPredictor

router = APIRouter(prefix="/model", tags=["模型"])

DATA_STORAGE_ROOT = YOLO_DATASETS_DIR


@router.get("/list")
async def list_models_api(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    keyword: str = Query(None, description="搜索关键词"),
    current_user: UserModel = Depends(get_current_user)
):
    """模型列表（支持分页和搜索）"""
    models, total = get_models(page=page, page_size=page_size, keyword=keyword)
    return api_response(data={"models": models, "total": total, "page": page, "page_size": page_size})


@router.get("/{model_id}")
async def get_model_api(
    model_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """获取模型详情"""
    model = get_model(model_id)
    if not model:
        return api_response(code=HttpErrcode.NOT_FOUND, message="模型不存在")
    return api_response(data=model)


@router.delete("/{model_id}")
async def delete_model_api(
    model_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """删除模型"""
    delete_model(model_id)
    return api_response(message="模型删除成功")


@router.post("/predict")
async def predict_image_api(
    model_id: str = Form(...),
    image: UploadFile = File(...),
    conf_threshold: float = Form(0.25),
    save_result: bool = Form(True),
    current_user: UserModel = Depends(get_current_user)
):
    """使用模型预测图片"""
    model = get_model(model_id)
    if not model:
        return api_response(code=HttpErrcode.NOT_FOUND, message="模型不存在")
    
    if not os.path.exists(model['path']):
        return api_response(code=HttpErrcode.PARAMS_ERROR, message="模型文件不存在")
    
    temp_dir = DATA_STORAGE_ROOT / 'temp'
    temp_dir.mkdir(exist_ok=True)
    safe_filename = os.path.basename(image.filename)
    temp_img = temp_dir / safe_filename
    
    try:
        with open(temp_img, 'wb') as buffer:
            content = await image.read()
            if not content:
                return api_response(code=HttpErrcode.PARAMS_ERROR, message="上传的图像文件为空")
            buffer.write(content)
        
        predictor = YOLOPredictor(model_path=model['path'], class_names_from_db=model.get('classes'))
        
        start_time = time.time()
        results = predictor.predict(
            image_path=str(temp_img),
            conf_threshold=conf_threshold,
            save_result=save_result,
            output_dir=str(temp_dir)
        )
        elapsed_time = time.time() - start_time
        
        formatted_results = []
        for res in results:
            formatted_results.append({
                'class_id': res['class_id'],
                'class_name': res['class_name'],
                'confidence': res['confidence'],
                'bbox': res['bbox']
            })
        
        result_image = None
        if save_result:
            result_image_path = temp_dir / safe_filename
            if result_image_path.exists():
                output_dir = YOLO_OUTPUT_DIR
                output_path = output_dir / safe_filename
                shutil.copy2(str(result_image_path), str(output_path))
                result_image = f"{YOLO_OUTPUT_URL}/{safe_filename}"
        
        return api_response(data={
            'predictions': formatted_results,
            'inference_time': elapsed_time,
            'result_image': result_image
        }, message="预测完成")
    except Exception as e:
        print(f"预测出错: {str(e)}")
        return api_response(code=HttpErrcode.PARAMS_ERROR, message=f"图像预测失败: {str(e)}")


@router.post("/predict/{model_id}")
async def predict_with_model_api(
    model_id: str,
    images: List[UploadFile] = File(...),
    conf_threshold: float = Form(0.25),
    save_results: bool = Form(True),
    current_user: UserModel = Depends(get_current_user)
):
    """批量预测"""
    model = get_model(model_id)
    if not model:
        return api_response(code=HttpErrcode.NOT_FOUND, message="模型不存在")
    
    if not os.path.exists(model['path']):
        return api_response(code=HttpErrcode.PARAMS_ERROR, message="模型文件不存在")
    
    predictor = YOLOPredictor(model_path=model['path'])
    
    temp_dir = DATA_STORAGE_ROOT / 'temp'
    temp_dir.mkdir(exist_ok=True)
    
    all_results = []
    
    for img in images:
        safe_filename = os.path.basename(img.filename)
        temp_img = temp_dir / safe_filename
        
        with open(temp_img, 'wb') as buffer:
            content = await img.read()
            buffer.write(content)
        
        results = predictor.predict(
            image_path=str(temp_img),
            conf_threshold=conf_threshold,
            save_result=save_results,
            output_dir=str(temp_dir)
        )
        
        formatted = []
        for res in results:
            formatted.append({
                'class_id': res['class_id'],
                'class_name': res['class_name'],
                'confidence': res['confidence'],
                'bbox': res['bbox']
            })
        
        all_results.append({
            'image_name': img.filename,
            'predictions': formatted
        })
    
    return api_response(data=all_results, message="批量预测完成")