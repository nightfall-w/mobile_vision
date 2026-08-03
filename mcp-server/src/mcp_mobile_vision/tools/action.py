"""MCP Mobile Vision - 操作执行工具"""

import subprocess
from typing import Optional

from mcp_mobile_vision.session import session


def _adb_args(device_id: Optional[str] = None) -> list:
    """构建 ADB 设备前缀"""
    args = ["adb"]
    if device_id:
        args.extend(["-s", device_id])
    elif session.is_connected and session.device_id:
        args.extend(["-s", session.device_id])
    return args


async def handle_click(x: int, y: int, device_id: Optional[str] = None) -> bool:
    """点击坐标"""
    if not session.is_connected and not device_id:
        raise RuntimeError("未连接设备，请先调用 connect_device")

    if session.is_connected:
        await session.device.tap(x, y)
    else:
        cmd = _adb_args(device_id) + ["shell", "input", "tap", str(int(x)), str(int(y))]
        subprocess.run(cmd, capture_output=True, timeout=30)
    return True


async def handle_long_press(
    x: int, y: int, duration: int = 1000, device_id: Optional[str] = None
) -> bool:
    """长按坐标"""
    if session.is_connected:
        await session.device.long_press(x, y, duration / 1000)
    else:
        cmd = _adb_args(device_id) + [
            "shell", "input", "swipe",
            str(x), str(y), str(x), str(y), str(duration),
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)
    return True


async def handle_swipe(
    x1: int, y1: int, x2: int, y2: int,
    duration: int = 300, device_id: Optional[str] = None,
) -> bool:
    """滑动"""
    cmd = _adb_args(device_id) + [
        "shell", "input", "swipe",
        str(x1), str(y1), str(x2), str(y2), str(duration),
    ]
    subprocess.run(cmd, capture_output=True, timeout=30)
    return True


async def handle_input_text(text: str, device_id: Optional[str] = None) -> bool:
    """输入文字"""
    if session.is_connected:
        await session.device.input_text(text)
    else:
        raise RuntimeError("输入文字需要已连接设备")
    return True


async def handle_press_back(device_id: Optional[str] = None) -> bool:
    """返回键"""
    if session.is_connected:
        await session.device.press_key("back")
    else:
        cmd = _adb_args(device_id) + ["shell", "input", "keyevent", "KEYCODE_BACK"]
        subprocess.run(cmd, capture_output=True, timeout=30)
    return True


async def handle_press_home(device_id: Optional[str] = None) -> bool:
    """Home 键"""
    if session.is_connected:
        await session.device.press_key("home")
    else:
        cmd = _adb_args(device_id) + ["shell", "input", "keyevent", "KEYCODE_HOME"]
        subprocess.run(cmd, capture_output=True, timeout=30)
    return True


async def handle_press_enter(device_id: Optional[str] = None) -> bool:
    """回车键"""
    if session.is_connected:
        await session.device.press_key("enter")
    else:
        cmd = _adb_args(device_id) + ["shell", "input", "keyevent", "KEYCODE_ENTER"]
        subprocess.run(cmd, capture_output=True, timeout=30)
    return True