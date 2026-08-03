"""MCP Mobile Vision - 页面识别 + 截图工具"""

import os
from typing import Optional

from mcp_mobile_vision.page_builder import build_page_tree
from mcp_mobile_vision.session import session


async def handle_recognize_page(device_id: Optional[str] = None) -> dict:
    """双通道识别页面，返回结构化页面树"""
    interface = _get_interface(device_id)

    if session.model_path and not interface._recognizer:
        if os.path.exists(session.model_path):
            interface.yolo_model_path = session.model_path
            interface._init_recognizer()

    context = await interface.get_context()
    result = build_page_tree(context)

    # 当 YOLO 未配置且实际走的是纯 OCR 兜底时，添加醒目提示
    if not session.model_path and context.source == "ocr_only":
        result["notice"] = (
            "⚠️ YOLO 模型未配置，当前仅使用 OCR 识别文字，"
            "无法识别图标、按钮、图片等视觉元素。"
            "如需更准确的识别，请先调用 set_model 设置 YOLO 模型路径。"
        )

    return result


async def handle_screenshot(
    device_id: Optional[str] = None,
    mark: bool = False,
    x: Optional[int] = None,
    y: Optional[int] = None,
    end_x: Optional[int] = None,
    end_y: Optional[int] = None,
) -> str:
    """截图，返回文件路径"""
    interface = _get_interface(device_id)

    if mark and x is not None and y is not None:
        return await interface._take_screenshot_with_marker(x, y, end_x, end_y)
    return await interface._take_screenshot()


def _get_interface(device_id: Optional[str] = None):
    """获取当前活跃的 AndroidInterface 实例"""
    if session.is_connected:
        if device_id and device_id != session.device_id:
            raise RuntimeError(
                f"当前活跃设备为 {session.device_id}，请先 disconnect 再连接 {device_id}"
            )
        return session.device

    if device_id:
        return session.connect(device_id)

    raise RuntimeError("未连接设备，请先调用 connect_device")