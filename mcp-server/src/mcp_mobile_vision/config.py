"""MCP Mobile Vision - 配置"""

import os
from pathlib import Path

# 截图存储目录（默认当前目录下的 screenshots/）
SCREENSHOTS_DIR = Path(os.environ.get(
    "MV_SCREENSHOTS_DIR",
    str(Path.cwd() / "screenshots")
))
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# OCR 引擎: "easyocr" 或 "rapidocr"
OCR_ENGINE = os.environ.get("MV_OCR_ENGINE", "rapidocr")

# ADB 命令
ADB_CMD = os.environ.get("MV_ADB_CMD", "adb")

# 默认设备地址
DEFAULT_DEVICE_ID = os.environ.get("MV_DEVICE_ID", "")

# YOLO 模型路径（通过 set_model 工具或环境变量配置）
YOLO_MODEL_PATH = os.environ.get("MV_YOLO_MODEL_PATH", "")