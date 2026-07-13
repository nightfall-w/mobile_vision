"""
YOLO 训练任务消费者 - 使用 FunBoost
"""
import gc
import os
import shutil

from funboost import boost, BrokerEnum, BoosterParams

from app.yolo.controller import (
    get_dataset,
    get_task,
    update_task,
    create_model,
    generate_data_yaml
)
from core.config import YOLO_DATASETS_DIR, YOLO_BASE_MODELS_DIR, YOLO_MODELS_DIR, YOLO_TRAIN_RUNS_DIR
from core.enums import TaskStatus
from models.yolo.trainer import YOLOTrainer
from utils.task_cancel import check_cancel_signal, TaskCancelledException

DATA_STORAGE_ROOT = YOLO_DATASETS_DIR


def find_latest_train_dir(base_path: str = None) -> str | None:
    base_path = base_path or str(YOLO_TRAIN_RUNS_DIR)
    """查找最新的 train 目录"""
    import glob
    train_dirs = glob.glob(os.path.join(base_path, 'train*'))
    if not train_dirs:
        return None

    latest_dir = max(train_dirs, key=os.path.getmtime)
    return latest_dir


def get_last_pt_path(train_dir: str) -> str | None:
    """获取 last.pt 文件路径"""
    last_pt_path = os.path.join(train_dir, 'weights', 'last.pt')
    if os.path.exists(last_pt_path):
        return last_pt_path
    return None


@boost(BoosterParams(
    broker_kind=BrokerEnum.REDIS_ACK_ABLE,
    queue_name='yolo_train_task_queue',
    log_level=20,
    max_retry_times=0,
    concurrent_num=1,
    is_auto_start_consuming_message=False
))
def train_yolo_model(task_data: dict):
    """YOLO 模型训练任务"""
    task_id = task_data.get('task_id')
    print(f"[FunBoost] 开始处理训练任务: {task_id}")

    trainer = None
    try:

        task = get_task(task_id)
        if not task:
            print(f"[FunBoost] 任务 {task_id} 不存在")
            return

        dataset_id = task['dataset_id']
        config = task['config']
        train_dir = task.get('train_dir')

        update_task(
            task_id,
            status=TaskStatus.RUNNING.value,
            progress=0.0,
            current_epoch=0
        )

        print(f"[FunBoost] 任务 {task_id}: 生成 data.yaml")
        yaml_path = generate_data_yaml(dataset_id)
        dataset = get_dataset(dataset_id)

        continue_from_last_pt = False
        last_pt_path = None

        if train_dir and os.path.exists(train_dir):
            last_pt_path = get_last_pt_path(train_dir)
            if last_pt_path:
                print(f"[FunBoost] 任务 {task_id}: 发现已存在的训练目录 {train_dir}，将从 last.pt 继续训练")
                continue_from_last_pt = True
        elif task['status'] == TaskStatus.FAILED.value:
            print(f"[FunBoost] 任务 {task_id}: 检查是否有之前的训练目录...")
            latest_train_dir = find_latest_train_dir()
            if latest_train_dir:
                last_pt_path = get_last_pt_path(latest_train_dir)
                if last_pt_path:
                    train_dir = latest_train_dir
                    print(f"[FunBoost] 任务 {task_id}: 发现最新训练目录 {train_dir}，将从 last.pt 继续训练")
                    continue_from_last_pt = True
                    update_task(task_id, train_dir=train_dir)

        if continue_from_last_pt and last_pt_path:
            model_path = last_pt_path
        else:
            model_name = config.get('model_name', 'yolov8n.pt')
            if '/' in model_name or '\\' in model_name or model_name.startswith('.'):
                model_path = model_name
            else:
                model_path = str(YOLO_BASE_MODELS_DIR / model_name)
                if not os.path.exists(model_path):
                    model_path = str(YOLO_MODELS_DIR / model_name)

        print(f"[FunBoost] 任务 {task_id}: 使用模型: {model_path}")

        trainer = YOLOTrainer(model_name=model_path)

        try:
            results = trainer.train(
                data_path=yaml_path,
                epochs=config.get('epochs', 100),
                batch_size=config.get('batch_size', 8),
                imgsz=config.get('imgsz', 640),
                device=config.get('device', 'cpu'),
                lr0=config.get('lr0', 0.01),
                max_det=300,
                resume=continue_from_last_pt,
                cancel_check_callback=lambda: check_cancel_signal(task_id, namespace="yolo_train"),
            )
        except TaskCancelledException:
            print(f"[FunBoost] 任务 {task_id}: 训练任务已被用户取消")
            update_task(
                task_id,
                status=TaskStatus.ABORTED.value,
                progress=task.get('progress', 0),
                error_message="任务已被用户取消"
            )
            return

        save_dir = results.get('save_dir')
        if save_dir:
            update_task(task_id, train_dir=save_dir)

        print(f"[FunBoost] 任务 {task_id}: 训练完成，保存模型")

        model_path = results.get('model_path')
        if model_path:
            model_dir = YOLO_MODELS_DIR

            model_name = f"yolo_{task_id}_{dataset_id}.pt"
            final_model_path = model_dir / model_name
            shutil.copy2(model_path, final_model_path)

            update_task(
                task_id,
                status=TaskStatus.COMPLETED.value,
                progress=100.0,
                current_epoch=config.get('epochs', 100),
                metrics=results.get('val', {}),
                result_model_path=str(final_model_path)
            )

            model_filename = os.path.basename(task['model_name']) if task.get('model_name') else 'unknown'
            create_model(
                task_id=task_id,
                dataset_id=dataset_id,
                name=f"YOLO_{model_filename}_{task_id}",
                path=str(final_model_path),
                metrics=results.get('val', {}),
                classes=dataset['classes']
            )

            print(f"[FunBoost] 任务 {task_id}: 模型已保存到 {final_model_path}")
        else:
            raise Exception("训练结果未返回模型路径")

    except Exception as e:
        print(f"[FunBoost] 任务 {task_id} 执行失败: {str(e)}")

        try:
            latest_train_dir = find_latest_train_dir()
            if latest_train_dir:
                update_task(task_id, train_dir=latest_train_dir)
        except Exception as inner_e:
            print(f"[FunBoost] 任务 {task_id}: 获取训练目录失败: {str(inner_e)}")

        update_task(
            task_id,
            status=TaskStatus.FAILED.value,
            error_message=str(e)
        )
        raise

    finally:
        if trainer is not None:
            del trainer
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif torch.backends.mps.is_available():
            torch.mps.empty_cache()
        gc.collect()


def start_train_consumer():
    """启动训练任务消费者"""
    print("[FunBoost] 启动 YOLO 训练任务消费者...")
    train_yolo_model.start_consuming_message()
    print("[FunBoost] YOLO 训练任务消费者已启动")


def submit_train_task(task_id: str):
    """提交训练任务到队列"""
    train_yolo_model.publish({"task_data": {"task_id": task_id}})
    print(f"[FunBoost] 训练任务 {task_id} 已提交到队列")
