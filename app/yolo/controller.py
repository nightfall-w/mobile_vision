"""
YOLO 数据控制器
"""
import os
import uuid
import shutil
import yaml
import random
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy import desc

from core.config import PROJECT_ROOT
from core.database import _get_db_session as get_db_session
from utils.task_cancel import send_cancel_signal
from app.yolo.models import YoloDataset, YoloTask, YoloModel, TaskStatus

YOLO_ROOT = PROJECT_ROOT / 'models' / 'yolo'
DATA_STORAGE_ROOT = YOLO_ROOT / 'data'
MODEL_STORAGE_ROOT = YOLO_ROOT / 'runs'

os.makedirs(DATA_STORAGE_ROOT, exist_ok=True)
os.makedirs(MODEL_STORAGE_ROOT, exist_ok=True)


def generate_data_yaml(dataset_id: str) -> str:
    """生成 data.yaml 配置文件"""
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise ValueError(f"数据集 {dataset_id} 不存在")

    dataset_dir = DATA_STORAGE_ROOT / dataset_id
    yaml_path = dataset_dir / 'data.yaml'

    images_dir = dataset_dir / 'images'
    labels_dir = dataset_dir / 'labels'

    # 获取子目录路径（如果存在）
    train_img_dir = images_dir / 'train'
    val_img_dir = images_dir / 'val'
    test_img_dir = images_dir / 'test'

    # 确定配置文件中的路径
    train_dir = str(train_img_dir) if train_img_dir.exists() else str(images_dir)
    val_dir = str(val_img_dir) if val_img_dir.exists() else str(train_img_dir if train_img_dir.exists() else images_dir)
    test_dir = str(test_img_dir) if test_img_dir.exists() else None

    classes = dataset['classes']
    class_names = []
    for cls in classes:
        if isinstance(cls, dict) and 'english' in cls:
            class_names.append(cls['english'])
        else:
            class_names.append(str(cls))

    yaml_content = f"""# YOLOv8 Dataset Configuration
# Generated automatically

train: {train_dir}
val: {val_dir}
test: {test_dir if test_dir else ''}

# Classes
nc: {dataset['class_count']}
names: {class_names}
"""

    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    return str(yaml_path)


def create_dataset(name: str, description: str = "", classes: List[str] = None) -> Dict:
    """创建数据集"""
    dataset_id = str(uuid.uuid4())[:8]
    dataset_dir = DATA_STORAGE_ROOT / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)

    if classes is None:
        classes = []

    with get_db_session() as db:
        dataset = YoloDataset(
            id=dataset_id,
            name=name,
            description=description,
            classes=classes,
            class_count=len(classes),
            image_count=0,
            label_count=0
        )
        db.add(dataset)

        (dataset_dir / 'images').mkdir(exist_ok=True)
        (dataset_dir / 'labels').mkdir(exist_ok=True)

        return {
            'id': dataset_id,
            'name': name,
            'description': description,
            'classes': classes,
            'class_count': len(classes),
            'image_count': 0,
            'label_count': 0,
            'created_at': datetime.now().isoformat()
        }


def get_datasets() -> List[Dict]:
    """获取所有数据集"""
    with get_db_session() as db:
        datasets = db.query(YoloDataset).filter(YoloDataset.is_deleted == 0).order_by(
            desc(YoloDataset.created_at)).all()
        return [_dataset_to_dict(d) for d in datasets]


def get_dataset(dataset_id: str) -> Optional[Dict]:
    """获取数据集详情"""
    with get_db_session() as db:
        dataset = db.query(YoloDataset).filter(YoloDataset.id == dataset_id, YoloDataset.is_deleted == 0).first()
        if dataset:
            return _dataset_to_dict(dataset)
        return None


def delete_dataset(dataset_id: str):
    """删除数据集"""
    with get_db_session() as db:
        dataset = db.query(YoloDataset).filter(YoloDataset.id == dataset_id).first()
        if dataset:
            dataset.is_deleted = 1

            dataset_dir = DATA_STORAGE_ROOT / dataset_id
            if dataset_dir.exists():
                shutil.rmtree(dataset_dir)


def update_dataset(dataset_id: str, name: str = None, description: str = None, classes: List[str] = None) -> Optional[
    Dict]:
    """更新数据集信息"""
    with get_db_session() as db:
        dataset = db.query(YoloDataset).filter(YoloDataset.id == dataset_id).first()
        if not dataset:
            return None

        if name is not None:
            dataset.name = name
        if description is not None:
            dataset.description = description
        if classes is not None:
            dataset.classes = classes
            dataset.class_count = len(classes)

            dataset_dir = DATA_STORAGE_ROOT / dataset_id
            yaml_path = dataset_dir / 'data.yaml'
            if yaml_path.exists():
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    yaml_data = yaml.safe_load(f) or {}
                names_dict = {}
                for i, cls in enumerate(classes):
                    if isinstance(cls, dict) and 'english' in cls:
                        names_dict[i] = cls['english']
                    else:
                        names_dict[i] = str(cls)
                yaml_data['names'] = names_dict
                yaml_data['nc'] = len(classes)
                with open(yaml_path, 'w', encoding='utf-8') as f:
                    yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False)

        dataset.updated_at = datetime.now()
        return {
            'id': dataset.id,
            'name': dataset.name,
            'description': dataset.description,
            'classes': dataset.classes,
            'class_count': dataset.class_count
        }


def update_dataset_stats(dataset_id: str):
    """更新数据集统计信息"""
    dataset_dir = DATA_STORAGE_ROOT / dataset_id

    image_count = 0
    images_dir = dataset_dir / 'images'
    if images_dir.exists():
        for f in images_dir.iterdir():
            if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                image_count += 1
            elif f.is_dir():
                for img in f.iterdir():
                    if img.is_file() and img.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                        image_count += 1

    label_count = 0
    labels_dir = dataset_dir / 'labels'
    if labels_dir.exists():
        for f in labels_dir.iterdir():
            if f.is_file() and f.suffix.lower() == '.txt':
                try:
                    with open(f, 'r') as txt_file:
                        lines = txt_file.readlines()
                        label_count += len([line for line in lines if line.strip()])
                except Exception:
                    pass
            elif f.is_dir():
                for lbl in f.iterdir():
                    if lbl.is_file() and lbl.suffix.lower() == '.txt':
                        try:
                            with open(lbl, 'r') as txt_file:
                                lines = txt_file.readlines()
                                label_count += len([line for line in lines if line.strip()])
                        except Exception:
                            pass

    with get_db_session() as db:
        dataset = db.query(YoloDataset).filter(YoloDataset.id == dataset_id).first()
        if dataset:
            dataset.image_count = image_count
            dataset.label_count = label_count


def update_dataset_statistics(dataset_id: str):
    """更新数据集统计信息（兼容旧接口）"""
    update_dataset_stats(dataset_id)


def create_task(dataset_id: str, config: Dict) -> Dict:
    """创建训练任务"""
    task_id = str(uuid.uuid4())[:8]
    with get_db_session() as db:
        task = YoloTask(
            id=task_id,
            dataset_id=dataset_id,
            model_name=config.get('model_name', 'yolov8n.pt'),
            config=config,
            status=TaskStatus.PENDING.value,
            progress=0.0,
            current_epoch=0,
            total_epochs=config.get('epochs', 100)
        )
        db.add(task)
        return {
            'id': task_id,
            'dataset_id': dataset_id,
            'config': config,
            'status': TaskStatus.PENDING.value,
            'progress': 0.0
        }


def get_tasks(page: int = 1, page_size: int = 20, keyword: str = None, status: str = None) -> tuple:
    """获取训练任务列表（支持分页和筛选）"""
    with get_db_session() as db:
        query = db.query(YoloTask).filter(YoloTask.is_deleted == 0).order_by(desc(YoloTask.created_at))

        # Filter by status
        if status:
            query = query.filter(YoloTask.status == status)

        total = query.count()

        # When keyword is provided, we need to post-filter by dataset_name
        # since dataset_name is not a DB field but resolved in _task_to_dict
        if keyword:
            all_tasks = query.all()
            # Convert to dict to get dataset_name resolved
            all_dicts = [_task_to_dict(t) for t in all_tasks]
            keyword_lower = keyword.lower()
            filtered = [t for t in all_dicts if keyword_lower in t.get('dataset_name', '').lower()]
            # Apply pagination on filtered results
            start = (page - 1) * page_size
            end = start + page_size
            return filtered[start:end], len(filtered)
        else:
            tasks = query.offset((page - 1) * page_size).limit(page_size).all()
            return [_task_to_dict(t) for t in tasks], total


def get_task(task_id: str) -> Optional[Dict]:
    """获取任务详情"""
    with get_db_session() as db:
        task = db.query(YoloTask).filter(YoloTask.id == task_id, YoloTask.is_deleted == 0).first()
        if task:
            return _task_to_dict(task)
        return None


def update_task(task_id: str, status: str = None, progress: float = None,
                current_epoch: int = None, metrics: Dict = None, error_message: str = None,
                result_model_path: str = None, train_dir: str = None):
    """更新任务状态"""
    with get_db_session() as db:
        task = db.query(YoloTask).filter(YoloTask.id == task_id).first()
        if task:
            if status:
                task.status = status
                if status == TaskStatus.RUNNING.value and not task.start_time:
                    task.start_time = datetime.now()
                elif status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value] and not task.end_time:
                    task.end_time = datetime.now()
            if progress is not None:
                task.progress = progress
            if current_epoch is not None:
                task.current_epoch = current_epoch
            if metrics:
                task.metrics = metrics
            if error_message:
                task.error_message = error_message
            if result_model_path:
                task.result_model_path = result_model_path
            if train_dir:
                task.train_dir = train_dir


def abort_task(task_id: str):
    """取消训练任务"""
    with get_db_session() as db:
        task = db.query(YoloTask).filter(YoloTask.id == task_id).first()
        if task:
            if task.status in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
                task.status = TaskStatus.ABORTED.value
                task.end_time = datetime.now()
                send_cancel_signal(task_id, namespace="yolo_train")
                return True
            return False
    return False


def delete_task(task_id: str):
    """删除训练任务"""
    with get_db_session() as db:
        task = db.query(YoloTask).filter(YoloTask.id == task_id).first()
        if task:
            task.is_deleted = 1


def create_model(task_id: str, dataset_id: str, name: str, path: str,
                 metrics: Dict, classes: List[str]) -> Dict:
    """创建模型记录"""
    model_id = str(uuid.uuid4())[:8]
    size = 0
    if os.path.exists(path):
        size = os.path.getsize(path)

    with get_db_session() as db:
        model = YoloModel(
            id=model_id,
            task_id=task_id,
            dataset_id=dataset_id,
            name=name,
            path=path,
            size=size,
            metrics=metrics,
            classes=classes
        )
        db.add(model)
        return {
            'id': model_id,
            'task_id': task_id,
            'dataset_id': dataset_id,
            'name': name,
            'path': path,
            'size': size,
            'metrics': metrics,
            'classes': classes,
            'created_at': datetime.now().isoformat()
        }


def get_models(page: int = 1, page_size: int = 20, keyword: str = None) -> tuple:
    """获取模型列表（支持分页和搜索）"""
    with get_db_session() as db:
        query = db.query(YoloModel).filter(YoloModel.is_deleted == 0).order_by(desc(YoloModel.created_at))
        if keyword:
            query = query.filter(YoloModel.name.ilike(f'%{keyword}%'))
        total = query.count()
        models = query.offset((page - 1) * page_size).limit(page_size).all()
        return [_model_to_dict(m) for m in models], total


def get_model(model_id: str) -> Optional[Dict]:
    """获取模型详情"""
    with get_db_session() as db:
        model = db.query(YoloModel).filter(YoloModel.id == model_id, YoloModel.is_deleted == 0).first()
        if model:
            return _model_to_dict(model)
        return None


def get_all_models() -> list:
    """获取所有已训练模型（不分页）"""
    with get_db_session() as db:
        models = db.query(YoloModel).filter(YoloModel.is_deleted == 0).order_by(desc(YoloModel.created_at)).all()
        return [_model_to_dict(m) for m in models]


def delete_model(model_id: str):
    """删除模型"""
    with get_db_session() as db:
        model = db.query(YoloModel).filter(YoloModel.id == model_id).first()
        if model:
            if model.path and os.path.exists(model.path):
                os.remove(model.path)
            model.is_deleted = 1


def _dataset_to_dict(dataset: YoloDataset) -> Dict:
    """数据集对象转字典"""
    return {
        'id': dataset.id,
        'name': dataset.name,
        'description': dataset.description,
        'classes': dataset.classes,
        'class_count': dataset.class_count,
        'image_count': dataset.image_count,
        'label_count': dataset.label_count,
        'data_yaml_path': dataset.data_yaml_path,
        'created_at': dataset.created_at.isoformat() if dataset.created_at else None,
        'updated_at': dataset.updated_at.isoformat() if dataset.updated_at else None
    }


def _task_to_dict(task: YoloTask) -> Dict:
    """任务对象转字典"""
    dataset_detail = _get_dataset_detail(task.dataset_id)
    model_name = os.path.basename(task.model_name) if task.model_name else ''
    return {
        'id': task.id,
        'dataset_id': task.dataset_id,
        'dataset_name': dataset_detail.get('name', '未知数据集') if dataset_detail else '未知数据集',
        'dataset_detail': dataset_detail,
        'model_name': model_name,
        'config': task.config,
        'status': task.status,
        'progress': task.progress,
        'current_epoch': task.current_epoch,
        'total_epochs': task.total_epochs,
        'metrics': task.metrics,
        'start_time': task.start_time.isoformat() if task.start_time else None,
        'end_time': task.end_time.isoformat() if task.end_time else None,
        'error_message': task.error_message,
        'result_model_path': task.result_model_path,
        'train_dir': task.train_dir,
        'created_at': task.created_at.isoformat() if task.created_at else None
    }


def _get_dataset_detail(dataset_id: str) -> Dict:
    """根据数据集ID查询数据集详细信息"""
    with get_db_session() as db:
        dataset = db.query(YoloDataset).filter(YoloDataset.id == dataset_id).first()
        if dataset:
            return {
                'id': dataset.id,
                'name': dataset.name,
                'image_count': dataset.image_count,
                'label_count': dataset.label_count,
                'class_count': dataset.class_count,
                'classes': dataset.classes
            }
        return None


def _model_to_dict(model: YoloModel) -> Dict:
    """模型对象转字典"""
    dataset_detail = _get_dataset_detail(model.dataset_id)
    config = None
    model_name = None
    with get_db_session() as db:
        if model.task_id:
            task = db.query(YoloTask).filter(YoloTask.id == model.task_id).first()
            if task:
                config = task.config
                model_name = os.path.basename(task.model_name) if task.model_name else None

    name = model.name
    if name and '/' in name:
        name = os.path.basename(name)

    return {
        'id': model.id,
        'task_id': model.task_id,
        'dataset_id': model.dataset_id,
        'dataset_name': dataset_detail.get('name', '未知数据集') if dataset_detail else '未知数据集',
        'dataset_detail': dataset_detail,
        'name': name,
        'path': model.path,
        'size': model.size,
        'metrics': model.metrics,
        'classes': model.classes,
        'config': config,
        'model_name': model_name,
        'created_at': model.created_at.isoformat() if model.created_at else None
    }
