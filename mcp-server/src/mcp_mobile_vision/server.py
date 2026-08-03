"""MCP Mobile Vision Server

将手机 UI 自动化能力（ADB + YOLO + OCR）暴露为 MCP 工具，
供 Claude Code / Codex 等 AI 客户端调用。

使用方式:
    # 直接运行
    python -m mcp_mobile_vision.server

    # 安装后运行
    mcp-mobile-vision

    # 配置到 Claude Code (~/.claude.json)
    {
        "mcpServers": {
            "mobile-vision": {
                "command": "python",
                "args": ["-m", "mcp_mobile_vision.server"]
            }
        }
    }
"""

import os
import sys
from pathlib import Path

from fastmcp import FastMCP

from mcp_mobile_vision.tools.device import (
    list_devices,
    get_device_info,
    handle_connect_device,
    handle_disconnect_device,
)
from mcp_mobile_vision.tools.page import handle_recognize_page, handle_screenshot
from mcp_mobile_vision.tools.action import (
    handle_click,
    handle_long_press,
    handle_swipe,
    handle_input_text,
    handle_press_back,
    handle_press_home,
    handle_press_enter,
)
from mcp_mobile_vision.session import session

# ── 启动提醒 ──────────────────────────────────────────────────────────
yolo_path = os.environ.get("MV_YOLO_MODEL_PATH", "")
if not yolo_path:
    print(
        "⚠️  YOLO 模型未配置。recognize_page 将仅使用 DOM 快通道（uiautomator2）识别页面。\n"
        "   如需视觉识别（YOLO + OCR），请使用 set_model 工具指定模型路径，\n"
        "   或设置环境变量 MV_YOLO_MODEL_PATH=/path/to/model.pt"
    )
else:
    print(f"✅ YOLO 模型已配置: {yolo_path}")
# ─────────────────────────────────────────────────────────────────────

# 创建 MCP Server
mcp = FastMCP("mobile-vision")

# ── 设备管理 ──────────────────────────────────────────────────────────

@mcp.tool()
async def list_devices() -> list:
    """列出所有已连接的 ADB 设备"""
    return list_devices()


@mcp.tool()
async def connect_device(address: str) -> dict:
    """连接设备（有线/无线 ADB）

    Args:
        address: 设备地址，如 "192.168.1.100:5555" 或 USB 序列号
    """
    return await handle_connect_device(address)


@mcp.tool()
async def disconnect_device(device_id: str = None) -> bool:
    """断开设备连接

    Args:
        device_id: 设备 ID，省略时断开当前活跃设备
    """
    return await handle_disconnect_device(device_id)


@mcp.tool()
async def get_device_info(device_id: str = None) -> dict:
    """获取设备详细信息（分辨率、型号等）

    Args:
        device_id: 设备 ID，省略时使用当前活跃设备
    """
    return get_device_info(device_id)


# ── 页面识别 ──────────────────────────────────────────────────────────

@mcp.tool()
async def recognize_page(device_id: str = None) -> dict:
    """【推荐】双通道识别页面，返回结构化页面树（JSON 格式，含元素类型、坐标、文本）

    这是理解当前页面的首选工具！比 screenshot 更高效，因为：
    - 返回结构化数据（元素类型、坐标、文本、颜色等），LLM 可直接分析
    - 优先使用 DOM 快通道（0.3-0.8s），信息不足时自动切换视觉通道（YOLO + OCR）
    - 无需多模态能力，不依赖图像理解

    返回的每个元素都包含 bbox_center 坐标，可直接用于 click 等操作。

    适用场景：
    - 用户说"看看屏幕有什么"、"识别页面"、"分析页面" → 用 recognize_page
    - 需要找到某个元素的位置 → 用 recognize_page
    - 用户说"截图"、"截屏"、"给我看" → 用 screenshot

    💡 如果没有设置 YOLO 模型，优先使用 DOM 快通道识别页面，
       信息不足时自动降级为纯 OCR 识别（仅文字，无图标/按钮等视觉元素）。
       如需视觉识别，请先调用 set_model 指定 YOLO 模型路径。

    Args:
        device_id: 设备 ID，省略时使用当前活跃设备
    """
    return await handle_recognize_page(device_id)


@mcp.tool()
async def screenshot(
    device_id: str = None,
    mark: bool = False,
    x: int = None,
    y: int = None,
    end_x: int = None,
    end_y: int = None,
) -> str:
    """截图，返回文件路径。仅用于查看屏幕视觉效果或确认操作结果。

    注意：理解页面内容请优先使用 recognize_page（返回结构化数据，更高效）。
    只在以下情况使用 screenshot：
    - 用户明确要求"截图"、"截屏"、"给我看"
    - recognize_page 返回的数据不足以判断页面状态
    - 需要在操作后截图确认效果（如：点击后截图确认页面变化）

    Args:
        device_id: 设备 ID，省略时使用当前活跃设备
        mark: 是否在截图上标记操作坐标
        x: 点击/滑动起始 x
        y: 点击/滑动起始 y
        end_x: 滑动终点 x（滑动标记时需要）
        end_y: 滑动终点 y（滑动标记时需要）

    Returns:
        截图文件路径
    """
    return await handle_screenshot(device_id, mark, x, y, end_x, end_y)


# ── 操作执行 ──────────────────────────────────────────────────────────

@mcp.tool()
async def click(x: int, y: int, device_id: str = None) -> bool:
    """点击屏幕指定坐标

    Args:
        x: x 坐标（像素）
        y: y 坐标（像素）
        device_id: 设备 ID，省略时使用当前活跃设备
    """
    return await handle_click(x, y, device_id)


@mcp.tool()
async def long_press(
    x: int, y: int, duration: int = 1000, device_id: str = None
) -> bool:
    """长按屏幕指定坐标

    Args:
        x: x 坐标（像素）
        y: y 坐标（像素）
        duration: 长按持续时间（毫秒），默认 1000ms
        device_id: 设备 ID，省略时使用当前活跃设备
    """
    return await handle_long_press(x, y, duration, device_id)


@mcp.tool()
async def swipe(
    x1: int, y1: int, x2: int, y2: int,
    duration: int = 300, device_id: str = None,
) -> bool:
    """滑动操作

    Args:
        x1: 起始 x 坐标
        y1: 起始 y 坐标
        x2: 终点 x 坐标
        y2: 终点 y 坐标
        duration: 滑动持续时间（毫秒），默认 300ms
        device_id: 设备 ID，省略时使用当前活跃设备
    """
    return await handle_swipe(x1, y1, x2, y2, duration, device_id)


@mcp.tool()
async def input_text(text: str, device_id: str = None) -> bool:
    """输入文字（支持中文和特殊字符）

    Args:
        text: 要输入的文本
        device_id: 设备 ID，省略时使用当前活跃设备
    """
    return await handle_input_text(text, device_id)


@mcp.tool()
async def press_back(device_id: str = None) -> bool:
    """按返回键"""
    return await handle_press_back(device_id)


@mcp.tool()
async def press_home(device_id: str = None) -> bool:
    """按 Home 键"""
    return await handle_press_home(device_id)


@mcp.tool()
async def press_enter(device_id: str = None) -> bool:
    """按回车键"""
    return await handle_press_enter(device_id)


# ── 模型配置 ──────────────────────────────────────────────────────────

@mcp.tool()
async def set_model(model_path: str) -> bool:
    """指定 YOLO 模型路径。调用后 recognize_page 将启用视觉识别通道。

    💡 如果没有 YOLO 模型，recognize_page 将使用 DOM 快通道或纯 OCR 兜底。
       如需训练 YOLO 模型，请参考主项目的在线标注与训练功能。

    Args:
        model_path: YOLO 模型文件路径（.pt 文件）
    """
    if not Path(model_path).exists():
        raise FileNotFoundError(f"模型文件不存在: {model_path}")
    session.set_model(model_path)
    return True


@mcp.tool()
async def get_model_info() -> dict:
    """获取当前 YOLO 模型信息"""
    return session.get_model_info()


# ── 启动 ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()