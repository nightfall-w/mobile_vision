"""
@FileName：config.py
@Description：
@Author：baojun.wang
@Time：2025/10/29 19:49
"""
from pathlib import Path

# 获取当前文件（config.py）的绝对路径
current_file = Path(__file__).resolve()

PROJECT_ROOT = current_file.parent.parent
MEDIA_ROOT = PROJECT_ROOT / 'media'
REPORT_ROOT = MEDIA_ROOT / 'report'
REPORT_URL = '/media/report'
if not REPORT_ROOT.exists():
    REPORT_ROOT.mkdir(parents=True)
print("项目根目录：", PROJECT_ROOT)
print("媒体目录：", MEDIA_ROOT)
