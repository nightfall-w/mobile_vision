"""MCP Mobile Vision - 会话状态管理"""

from typing import Optional

from mcp_mobile_vision.adb import AndroidInterface
from mcp_mobile_vision.config import OCR_ENGINE


class Session:
    """MCP Server 会话状态"""

    def __init__(self):
        self._device: Optional[AndroidInterface] = None
        self._device_id: Optional[str] = None
        self._model_path: Optional[str] = None

    @property
    def device(self) -> Optional[AndroidInterface]:
        return self._device

    @property
    def device_id(self) -> Optional[str]:
        return self._device_id

    @property
    def is_connected(self) -> bool:
        return self._device is not None

    @property
    def model_path(self) -> Optional[str]:
        return self._model_path

    def connect(self, device_id: str) -> AndroidInterface:
        """连接设备"""
        if self._device is not None:
            import asyncio
            try:
                asyncio.get_event_loop().run_until_complete(self._device.disconnect())
            except Exception:
                pass
            self._device = None

        self._device = AndroidInterface(
            device_id=device_id,
            yolo_model_path=self._model_path,
            ocr_engine=OCR_ENGINE,
        )
        self._device_id = device_id
        return self._device

    async def disconnect(self):
        """断开设备连接"""
        if self._device is not None:
            await self._device.disconnect()
        self._device = None
        self._device_id = None

    def set_model(self, model_path: str):
        """设置 YOLO 模型路径"""
        self._model_path = model_path

    def get_model_info(self) -> dict:
        """获取当前模型信息"""
        if not self._model_path:
            return {"model_path": None, "status": "not_configured"}
        return {
            "model_path": self._model_path,
            "status": "configured",
        }


# 全局单例
session = Session()