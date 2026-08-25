"""
@FileName：system_setting.py
@Description：系统配置读取 —— 从 system_config 表取值，未配置时回退到原有环境变量/本机 IP 逻辑
@Author：baojun.wang
"""
import os
import socket
from typing import Optional

from utils.custom_logging import logger

# ── 配置项键名（页面上展示的就是这些 key，代码里只认这里的常量）────────
KEY_BACKEND_BASE_URL = "BACKEND_BASE_URL"
KEY_FRONTEND_BASE_URL = "FRONTEND_BASE_URL"

# 内置配置项定义，用于首次访问时补齐表中缺失的行
DEFAULT_CONFIGS = [
    {
        "key": KEY_BACKEND_BASE_URL,
        "value": "",
        "desc": "后端服务对外访问地址（含协议与端口，如 http://mv.example.com:8080）。"
                "通知消息里的 HTML 报告链接以此为前缀。留空则回退为本机 IP + BACKEND_PORT。",
        "type": "STRING",
        "required": False,
    },
    {
        "key": KEY_FRONTEND_BASE_URL,
        "value": "",
        "desc": "前端页面对外访问地址（含协议与端口，如 http://mv.example.com:5173）。"
                "报告中的 Job 监控页跳转链接以此为前缀。留空则回退为本机 IP + FRONTEND_PORT。",
        "type": "STRING",
        "required": False,
    },
]


def _get_local_ip() -> str:
    """获取本机局域网 IP，用于未配置域名时构造链接"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_config_value(key: str, db=None) -> Optional[str]:
    """
    读取配置项的值，不存在或为空返回 None

    :param db: 已有的数据库会话；不传则自建一个短会话
    """
    from app.setting.models import SystemConfig

    def _query(session):
        row = session.query(SystemConfig).filter(SystemConfig.key == key).first()
        return (row.value or "").strip() or None if row else None

    try:
        if db is not None:
            return _query(db)
        from core.database import _get_db_session
        with _get_db_session() as session:
            return _query(session)
    except Exception as e:
        logger.warning(f"[系统配置] 读取 {key} 失败，回退默认值: {e}")
        return None


def _normalize_base_url(value: str) -> str:
    """确保地址带协议、末尾无斜杠，避免被浏览器当成相对路径"""
    value = value.strip().rstrip("/")
    if value and not value.startswith(("http://", "https://")):
        value = "http://" + value
    return value


def get_backend_base_url(db=None) -> str:
    """
    后端对外访问地址，用于拼接 HTML 报告链接

    优先取系统配置；未配置时回退为 本机IP + BACKEND_PORT（保持历史行为）。
    """
    configured = get_config_value(KEY_BACKEND_BASE_URL, db)
    if configured:
        return _normalize_base_url(configured)
    return f"http://{_get_local_ip()}:{os.getenv('BACKEND_PORT', '8080')}"


def get_frontend_base_url(db=None) -> str:
    """
    前端对外访问地址，用于拼接 Job 监控页链接

    优先取系统配置；未配置时回退为 本机IP + FRONTEND_PORT（保持历史行为）。
    """
    configured = get_config_value(KEY_FRONTEND_BASE_URL, db)
    if configured:
        return _normalize_base_url(configured)
    return f"http://{_get_local_ip()}:{os.getenv('FRONTEND_PORT', '5173')}"
