"""
YOLO 模型测试集评估消费者 - 使用 FunBoost
"""
import gc
import os

from funboost import boost, BrokerEnum, BoosterParams

from app.yolo.controller import (
    get_dataset,
    get_model,
    update_model_test_metrics,
    update_model_test_status,
    generate_data_yaml
)
from core.config import YOLO_DATASETS_DIR, YOLO_MODELS_DIR
from core.enums import TaskStatus
from models.yolo.trainer import YOLOTrainer
from utils.task_cancel import check_cancel_signal, TaskCancelledException, clear_cancel_signal

DATA_STORAGE_ROOT = YOLO_DATASETS_DIR


@boost(BoosterParams(
    broker_kind=BrokerEnum.REDIS_ACK_ABLE,
    queue_name='yolo_model_test_queue',
    log_level=20,
    max_retry_times=0,
    concurrent_num=1,
    is_auto_start_consuming_message=False
))
def test_yolo_model(task_data: dict):
    """YOLO 模型测试集评估任务"""
    model_id = task_data.get('model_id')
    print(f"[FunBoost] 开始处理模型测试集评估: {model_id}")

    trainer = None
    try:
        model = get_model(model_id)
        if not model:
            print(f"[FunBoost] 模型 {model_id} 不存在")
            return

        # 检查当前状态：如果非 pending/running，直接返回
        current_status = model.get('test_status', '')
        if current_status not in ('pending', 'running'):
            print(f"[FunBoost] 模型 {model_id} 当前状态为 {current_status}，跳过执行")
            return

        model_path = model.get('path')
        if not model_path or not os.path.exists(model_path):
            print(f"[FunBoost] 模型文件不存在: {model_path}")
            update_model_test_status(model_id, 'failed')
            return

        dataset_id = model['dataset_id']
        dataset = get_dataset(dataset_id)
        if not dataset:
            print(f"[FunBoost] 数据集 {dataset_id} 不存在")
            update_model_test_status(model_id, 'failed')
            return

        # 再次检查状态（可能被并发取消）
        model = get_model(model_id)
        if model and model.get('test_status') not in ('pending', 'running'):
            print(f"[FunBoost] 模型 {model_id} 已被取消，跳过执行")
            return

        update_model_test_status(model_id, 'running')

        # 检查取消信号
        if check_cancel_signal(model_id, namespace="yolo_model_test"):
            print(f"[FunBoost] 模型 {model_id} 收到取消信号")
            return

        print(f"[FunBoost] 模型 {model_id}: 生成 data.yaml")
        yaml_path = generate_data_yaml(dataset_id)

        print(f"[FunBoost] 模型 {model_id}: 加载模型 {model_path}")
        trainer = YOLOTrainer(model_name=model_path)

        print(f"[FunBoost] 模型 {model_id}: 开始测试集评估")
        results = trainer.validate(data_path=yaml_path, split='test')

        # 评估完成后检查状态：如果已被取消，不更新指标
        model = get_model(model_id)
        if not model or model.get('test_status') in ('cancelled', 'failed'):
            print(f"[FunBoost] 模型 {model_id} 状态为 {model.get('test_status') if model else 'N/A'}，不更新指标")
            return

        test_metrics = {
            "precision": float(results.get("precision", 0)),
            "recall": float(results.get("recall", 0)),
            "map50": float(results.get("map50", 0)),
            "map50-95": float(results.get("map50-95", 0)),
        }

        print(f"[FunBoost] 模型 {model_id}: 测试集评估完成: {test_metrics}")
        update_model_test_metrics(model_id, test_metrics, 'completed')

    except TaskCancelledException:
        print(f"[FunBoost] 模型 {model_id} 被取消")
        return
    except Exception as e:
        print(f"[FunBoost] 模型 {model_id} 测试集评估失败: {str(e)}")
        try:
            model = get_model(model_id)
            if model and model.get('test_status') not in ('cancelled',):
                update_model_test_status(model_id, 'failed')
        except Exception:
            pass
        raise

    finally:
        clear_cancel_signal(model_id, namespace="yolo_model_test")
        if trainer is not None:
            del trainer
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif torch.backends.mps.is_available():
            torch.mps.empty_cache()
        gc.collect()


def start_model_test_consumer():
    """启动模型测试集评估消费者"""
    print("[FunBoost] 启动 YOLO 模型测试集评估消费者...")
    test_yolo_model.start_consuming_message()
    print("[FunBoost] YOLO 模型测试集评估消费者已启动")


def submit_model_test_task(model_id: str):
    """提交模型测试集评估任务到队列"""
    test_yolo_model.publish({"task_data": {"model_id": model_id}})
    print(f"[FunBoost] 模型测试集评估任务 {model_id} 已提交到队列")