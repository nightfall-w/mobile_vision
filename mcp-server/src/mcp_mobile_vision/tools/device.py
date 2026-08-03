"""MCP Mobile Vision - 设备管理工具"""

import subprocess
from typing import Optional

from mcp_mobile_vision.session import session


def list_devices() -> list:
    """列出所有已连接的 ADB 设备"""
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
    devices = []
    for line in result.stdout.split("\n")[1:]:
        line = line.strip()
        if line and "\t" in line:
            dev_id, status = line.split("\t")
            devices.append({"device_id": dev_id, "status": status})
    return devices


def get_device_info(device_id: Optional[str] = None) -> dict:
    """获取设备信息"""
    if session.is_connected:
        if device_id and device_id != session.device_id:
            raise RuntimeError(
                f"当前活跃设备为 {session.device_id}，请先 disconnect"
            )
        return {
            "device_id": session.device.device_id,
            "resolution": {"width": session.device.width, "height": session.device.height},
        }

    if device_id:
        session.connect(device_id)
        return {
            "device_id": session.device.device_id,
            "resolution": {"width": session.device.width, "height": session.device.height},
        }

    raise RuntimeError("未连接设备，请先调用 connect_device")


async def handle_connect_device(address: str) -> dict:
    """连接设备"""
    info = get_device_info(address)
    return {"device_id": address, "status": "connected", "info": info}


async def handle_disconnect_device(device_id: Optional[str] = None) -> bool:
    """断开设备"""
    if device_id and device_id != session.device_id:
        raise RuntimeError(f"设备 {device_id} 不是当前活跃设备")
    await session.disconnect()
    return True