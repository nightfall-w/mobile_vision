"""
存储路径配置
所有路径均可通过环境变量覆盖，默认在项目根目录下
"""
import os
from pathlib import Path

# 获取当前文件（config.py）的绝对路径
current_file = Path(__file__).resolve()

PROJECT_ROOT = current_file.parent.parent

# ── 媒体 / 报告 ────────────────────────────────────────────────────
MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT', str(PROJECT_ROOT / 'media')))
REPORT_ROOT = Path(os.getenv('REPORT_ROOT', str(PROJECT_ROOT / 'storage' / 'reports')))
REPORT_URL = '/storage/reports'
REPORT_ROOT.mkdir(parents=True, exist_ok=True)

# ── YOLO ────────────────────────────────────────────────────────────
YOLO_DATASETS_DIR = Path(os.getenv('YOLO_DATASETS_DIR', str(PROJECT_ROOT / 'data' / 'yolo' / 'datasets')))
YOLO_BASE_MODELS_DIR = Path(os.getenv('YOLO_BASE_MODELS_DIR', str(PROJECT_ROOT / 'data' / 'yolo' / 'base_models')))
YOLO_MODELS_DIR = Path(os.getenv('YOLO_MODELS_DIR', str(PROJECT_ROOT / 'data' / 'yolo' / 'models')))
YOLO_OUTPUT_DIR = Path(os.getenv('YOLO_OUTPUT_DIR', str(PROJECT_ROOT / 'data' / 'yolo' / 'output')))
YOLO_TRAIN_RUNS_DIR = Path(os.getenv('YOLO_TRAIN_RUNS_DIR', str(PROJECT_ROOT / 'data' / 'yolo' / 'runs')))

# 保证目录存在
for d in [YOLO_DATASETS_DIR, YOLO_BASE_MODELS_DIR, YOLO_MODELS_DIR, YOLO_OUTPUT_DIR, YOLO_TRAIN_RUNS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# YOLO 输出 URL 访问前缀（对应 main.py 中的 mount 路径）
YOLO_OUTPUT_URL = os.getenv('YOLO_OUTPUT_URL', '/storage/yolo_output')

# ── 截图 ────────────────────────────────────────────────────────────
SCREENSHOTS_DIR = Path(os.getenv('SCREENSHOTS_DIR', str(PROJECT_ROOT / 'storage' / 'screenshots')))
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

print("项目根目录：", PROJECT_ROOT)
print("YOLO 数据集目录：", YOLO_DATASETS_DIR)
print("YOLO 模型目录：", YOLO_MODELS_DIR)
print("YOLO 输出目录：", YOLO_OUTPUT_DIR)
print("截图目录：", SCREENSHOTS_DIR)