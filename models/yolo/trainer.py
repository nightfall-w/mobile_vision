import os
import gc
from pathlib import Path
from typing import Dict, Any

os.environ["ULTRALYTICS_NO_DOWNLOAD"] = "1"
os.environ["ULTRALYTICS_DISABLE_CHECKS"] = "1"
from ultralytics import YOLO
import torch

from utils.task_cancel import TaskCancelledException

# Monkey-patch: fix MPS fancy-indexing bug in TaskAlignedAssigner.get_box_metrics
# The line `bbox_scores[mask_gt] = pd_scores[ind[0], :, ind[1]][mask_gt]` produces
# shape mismatch on Apple Silicon MPS backend for certain batch/instance combos.
# Replaced with a per-batch gather that avoids the problematic indexing pattern.
import ultralytics.utils.tal as _tal_mod

_orig_get_box_metrics = _tal_mod.TaskAlignedAssigner.get_box_metrics

def _patched_get_box_metrics(self, pd_scores, pd_bboxes, gt_labels, gt_bboxes, mask_gt):
    if pd_scores.device.type != "mps":
        return _orig_get_box_metrics(self, pd_scores, pd_bboxes, gt_labels, gt_bboxes, mask_gt)

    # MPS still has bugs with fancy indexing. Fall back to CPU for this operation.
    # This is safer than trying to re-implement the complex indexing logic.
    device = pd_scores.device
    result = _orig_get_box_metrics(
        self,
        pd_scores.to("cpu"),
        pd_bboxes.to("cpu"),
        gt_labels.to("cpu"),
        gt_bboxes.to("cpu"),
        mask_gt.to("cpu")
    )
    return tuple(x.to(device) if isinstance(x, torch.Tensor) else x for x in result)

    pd_boxes = pd_bboxes.unsqueeze(1).expand(-1, self.n_max_boxes, -1, -1)[mask_gt]
    gt_boxes = gt_bboxes.unsqueeze(2).expand(-1, -1, na, -1)[mask_gt]
    overlaps[mask_gt] = self.iou_calculation(gt_boxes, pd_boxes)

    align_metric = bbox_scores.pow(self.alpha) * overlaps.pow(self.beta)
    return align_metric, overlaps

_tal_mod.TaskAlignedAssigner.get_box_metrics = _patched_get_box_metrics


class YOLOTrainer:
    def __init__(self, model_name: str = "yolov8n.pt"):
        self.model = YOLO(model_name)
        self.train_results = None

    def _clear_gpu_memory(self):
        """清理 GPU 内存（支持 CUDA 和 MPS）"""
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        elif torch.backends.mps.is_available():
            torch.mps.empty_cache()
        gc.collect()

    def __del__(self):
        """析构时清理 GPU 内存"""
        self._clear_gpu_memory()
        self.model = None
        self.train_results = None

    def train(
            self,
            data_path: str = None,
            images_dir: str = None,
            labels_dir: str = None,
            epochs: int = 100,
            batch_size: int = 16,
            imgsz: int = 640,
            device: str = "cpu",
            cancel_check_callback=None,
            progress_callback=None,
            **kwargs,
    ) -> Dict[str, Any]:
        if data_path is None and (images_dir is None or labels_dir is None):
            raise ValueError(
                "Either data_path must be provided, or both images_dir and labels_dir must be provided"
            )

        if data_path is None:
            data_path = self._generate_data_yaml(images_dir, labels_dir)

        class EpochCallback:
            def __init__(self, cancel_callback, progress_callback=None, total_epochs=None):
                self.cancel_callback = cancel_callback
                self.progress_callback = progress_callback
                self.total_epochs = total_epochs

            def on_epoch_end(self, trainer):
                if self.cancel_callback and self.cancel_callback():
                    raise TaskCancelledException("训练任务已被取消")
                if self.progress_callback:
                    current = getattr(trainer, 'epoch', 0) + 1
                    total = getattr(trainer, 'epochs', self.total_epochs or 100)
                    self.progress_callback(current, total)

        callbacks = kwargs.pop('callbacks', [])
        callbacks.append(EpochCallback(cancel_check_callback, progress_callback, epochs))

        for cb in callbacks:
            # CancelCallback has on_epoch_end; register it for the matching event
            if hasattr(cb, 'on_epoch_end'):
                self.model.add_callback("on_train_epoch_end", cb.on_epoch_end)

        self.train_results = self.model.train(
            data=data_path,
            epochs=epochs,
            batch=batch_size,
            imgsz=imgsz,
            device=device,
            **kwargs,
        )

        return self._format_results()

    def _generate_data_yaml(self, images_dir: str, labels_dir: str) -> str:
        images_dir = os.path.abspath(images_dir)
        labels_dir = os.path.abspath(labels_dir)

        train_images = os.path.join(images_dir, "train")
        val_images = os.path.join(images_dir, "val")
        test_images = os.path.join(images_dir, "test")

        train_labels = os.path.join(labels_dir, "train")
        val_labels = os.path.join(labels_dir, "val")
        test_labels = os.path.join(labels_dir, "test")

        all_labels_dirs = [train_labels, val_labels, test_labels]
        nc, names = self._detect_classes(all_labels_dirs)

        names_str = str(names).replace("'", '"')
        yaml_content = f"""train: {train_images}
val: {val_images}
test: {test_images}

nc: {nc}
names: {names_str}
"""
        temp_yaml_path = os.path.join(os.path.dirname(labels_dir), "data_temp.yaml")
        with open(temp_yaml_path, "w") as f:
            f.write(yaml_content)

        return temp_yaml_path

    def _detect_classes(self, labels_dirs):
        class_ids = set()
        total_labels = 0

        for labels_dir in labels_dirs:
            if not os.path.exists(labels_dir):
                continue

            txt_files = [f for f in os.listdir(labels_dir) if f.endswith(".txt")]
            print(f"扫描目录 {labels_dir}: {len(txt_files)} 个标签文件")

            for filename in txt_files:
                file_path = os.path.join(labels_dir, filename)
                try:
                    with open(file_path, "r") as f:
                        lines = f.readlines()
                        if not lines:
                            print(f"警告: 标签文件为空 {filename}")
                            continue

                        for line in lines:
                            line = line.strip()
                            if line:
                                parts = line.split()
                                if len(parts) >= 5:
                                    try:
                                        class_id = int(float(parts[0]))
                                        class_ids.add(class_id)
                                        total_labels += 1
                                    except ValueError:
                                        print(f"警告: {filename} 中无效的类别ID: {parts[0]}")
                                else:
                                    print(f"警告: {filename} 中标注格式错误: {line}")
                except Exception as e:
                    print(f"警告: 无法读取标签文件 {filename}: {e}")

        print(f"\n=== 数据集统计 ===")
        print(f"总标注数量: {total_labels}")
        print(f"检测到的类别ID: {sorted(class_ids)}")

        if not class_ids:
            print("警告: 未检测到任何类别，使用默认设置")
            return 1, ["object"]

        max_class_id = max(class_ids)
        nc = max_class_id + 1
        names = [f"class_{i}" for i in range(nc)]

        print(f"类别数量 nc = {nc}")
        print(f"类别名称: {names}")

        missing_classes = [i for i in range(nc) if i not in class_ids]
        if missing_classes:
            print(f"注意: 以下类别没有标注数据: {missing_classes}")

        return nc, names

    def _format_results(self) -> Dict[str, Any]:
        if self.train_results is None:
            return {}

        results_dict = getattr(self.train_results, "results_dict", {})

        save_dir = None
        if hasattr(self.model, "trainer") and self.model.trainer:
            save_dir = Path(self.model.trainer.save_dir)
            model_path = save_dir / "weights" / "best.pt"
            if not model_path.exists():
                model_path = save_dir / "weights" / "last.pt"
        else:
            model_path = None

        results = {
            "speed": getattr(self.train_results, "speed", {}),
            "val": {
                "precision": float(results_dict.get("metrics/precision(B)", 0)),
                "recall": float(results_dict.get("metrics/recall(B)", 0)),
                "map50": float(results_dict.get("metrics/mAP50(B)", 0)),
                "map50-95": float(results_dict.get("metrics/mAP50-95(B)", 0)),
            },
            "model_path": str(model_path) if model_path and model_path.exists() else None,
            "save_dir": str(save_dir) if save_dir else None,
        }

        return results

    def validate(self, data_path: str = None, **kwargs) -> Dict[str, Any]:
        if data_path is None and self.train_results:
            data_path = self.train_results.save_dir

        results = self.model.val(data=data_path, **kwargs)

        return {
            "precision": float(results.results_dict.get("metrics/precision(B)", 0)),
            "recall": float(results.results_dict.get("metrics/recall(B)", 0)),
            "map50": float(results.results_dict.get("metrics/mAP50(B)", 0)),
            "map50-95": float(results.results_dict.get("metrics/mAP50-95(B)", 0)),
        }

    def continue_train(
            self,
            model_path: str,
            data_path: str = None,
            images_dir: str = None,
            labels_dir: str = None,
            epochs: int = 100,
            batch_size: int = 16,
            imgsz: int = 640,
            device: str = "cpu",
            **kwargs,
    ) -> Dict[str, Any]:
        if data_path is None and (images_dir is None or labels_dir is None):
            raise ValueError(
                "Either data_path must be provided, or both images_dir and labels_dir must be provided"
            )

        self.model = YOLO(model_path)
        print(f"已加载预训练模型: {model_path}")

        if data_path is None:
            data_path = self._generate_data_yaml(images_dir, labels_dir)

        self.train_results = self.model.train(
            data=data_path,
            epochs=epochs,
            batch=batch_size,
            imgsz=imgsz,
            device=device,
            **kwargs,
        )

        return self._format_results()

    def export(self, format: str = "onnx", **kwargs):
        self.model.export(format=format, **kwargs)

    def predict(self, source: str, **kwargs):
        return self.model.predict(source=source, **kwargs)
