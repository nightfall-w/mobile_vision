"""
Android设备接口 - 基于ADB实现设备控制和页面识别
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import time
from typing import List, Optional

from automation_agent.page_recognizer import PageElementRecognizer
from automation_agent.types import InterfaceType, PageContext
from utils.custom_logging import logger


class AndroidInterface:
    """Android设备接口"""

    interface_type = InterfaceType.ANDROID

    def __init__(
            self,
            device_id: Optional[str] = None,
            yolo_model_path: Optional[str] = None,
            ocr_engine: str = "rapidocr",
            class_names_from_db: List = None
    ):
        self.device_id = device_id
        self.yolo_model_path = yolo_model_path
        self.ocr_engine = ocr_engine
        self.class_names_from_db = class_names_from_db
        self._recognizer = None
        self.job_id: Optional[int] = None

        # 获取设备实际分辨率
        self.width, self.height = self._get_device_resolution()
        logger.info(f"设备分辨率: {self.width}x{self.height}")

        self._init_recognizer()
        self.page_hash: Optional[str] = None

    def _get_device_resolution(self) -> tuple:
        """获取设备实际分辨率（优先取Override size，如果没有则取Physical size）"""
        try:
            wm_cmd = ["adb"]
            if self.device_id:
                wm_cmd.extend(["-s", self.device_id])
            wm_cmd.extend(["shell", "wm", "size"])

            wm_result = subprocess.run(wm_cmd, capture_output=True, text=True, timeout=5)
            if wm_result.returncode == 0:
                # 优先匹配 Override size（设置的分辨率）
                override_match = re.search(r'Override size:\s*(\d+)x(\d+)', wm_result.stdout)
                if override_match:
                    return int(override_match.group(1)), int(override_match.group(2))
                else:
                    # 如果没有Override，匹配Physical size（物理分辨率）
                    physical_match = re.search(r'Physical size:\s*(\d+)x(\d+)', wm_result.stdout)
                    if physical_match:
                        return int(physical_match.group(1)), int(physical_match.group(2))

            logger.warning(f"无法获取设备分辨率，使用默认值: 1080x1920")
        except Exception as e:
            logger.error(f"获取设备分辨率失败: {e}")

        # 返回默认值
        return 1080, 1920

    def _init_recognizer(self):
        """初始化识别器"""
        if self.yolo_model_path and os.path.exists(self.yolo_model_path):
            try:
                import torch
                use_gpu = torch.cuda.is_available()
                self._recognizer = PageElementRecognizer(
                    yolo_model_path=self.yolo_model_path,
                    use_gpu=use_gpu,
                    ocr_engine=self.ocr_engine,
                    class_names_from_db=self.class_names_from_db,
                )
                logger.info(f"识别器初始化完成: {self.yolo_model_path}")
            except Exception as e:
                raise Exception(f"初始化识别器失败: {e}")

    def _hash_file(self, file_path: str) -> str:
        """计算文件 MD5 哈希"""
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    async def get_context(self) -> PageContext:
        """获取页面上下文（每次重新OCR识别，确保页面变化不遗漏）"""
        screenshot_path = await self._take_screenshot()
        self.last_screenshot_path = screenshot_path
        self.page_hash = self._hash_file(screenshot_path)

        if self._recognizer:
            t0 = time.time()
            page_info = self._recognizer.recognize_from_image(screenshot_path)
            t1 = time.time()

            # OCR完成后在原截图上标注YOLO结果（避免标注文字被OCR误识别）
            try:
                self._recognizer.draw_annotated_image(screenshot_path, screenshot_path)
            except Exception as e:
                logger.warning(f"生成标注截图失败: {e}")

            structured_elements = self._recognizer.integrate_elements_and_texts(
                page_info.elements, page_info.texts
            )

            t2 = time.time()
            logger.info(
                f"页面元素与文本识别耗时: {t1 - t0:.2f}s (引擎: {self.ocr_engine}), "
                f"元素整合耗时: {t2 - t1:.2f}s, 总耗时: {t2 - t0:.2f}s"
            )
            context = PageContext(
                page_id=page_info.page_id,
                image_width=page_info.image_width,
                image_height=page_info.image_height,
                elements=page_info.elements,
                texts=page_info.texts,
                structured_elements=structured_elements,
            )
            return context
        else:
            raise Exception("未找到可用的页面识别器")

    async def list_devices(self):
        """列出可用设备"""
        command = ["adb", "devices"]
        result = self._run_adb_command(command)
        return [
            line.split("\t")[0]
            for line in result.stdout.split("\n")
            if line.strip() and "\t" in line
        ]

    async def tap(self, x: float, y: float) -> None:
        """点击坐标"""
        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend(["shell", "input", "tap", str(int(x)), str(int(y))])
        self._run_adb_command(command)
        logger.debug(f"点击: ({x}, {y})")

    async def long_press(self, x: float, y: float, duration: float = 1.0) -> None:
        """长按坐标"""
        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend(
            ["shell", "input", "swipe", str(int(x)), str(int(y)), str(int(x)), str(int(y)), str(int(duration * 1000))])
        self._run_adb_command(command)
        logger.debug(f"长按: ({x}, {y}) 持续 {duration}秒")

    async def input_text(self, text: str) -> None:
        """输入文本（使用 Base64 编码方式，支持特殊字符和中文）"""
        # 0. 先清空输入框内容
        await self._clear_input()

        # 1. 将文本转换为 UTF-8 字节
        text_bytes = text.encode('utf-8')

        # 2. 进行 Base64 编码
        base64_text = base64.b64encode(text_bytes).decode('ascii')

        # 3. 构建 ADB 命令
        # 使用 ADB_INPUT_B64 action 和 --es msg 参数传递 Base64 字符串
        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])

        command.extend([
            "shell",
            "am",
            "broadcast",
            "-a",
            "ADB_INPUT_B64",  # 使用 Base64 动作
            "--es",
            "msg",
            base64_text  # 传递编码后的字符串
        ])

        # 4. 执行命令
        self._run_adb_command(command)
        logger.debug(f"输入文本 (Base64): {base64_text} (原始: {text})")

    async def _clear_input(self) -> None:
        """清空输入框内容（全选后删除）"""
        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])

        # 发送全选指令
        command_select_all = command + [
            "shell", "am", "broadcast",
            "-a", "ADB_INPUT_TEXT",
            "--es", "mcode", "4096,29"
        ]
        self._run_adb_command(command_select_all)

        # 发送 Delete 键删除选中内容
        command_delete = command + ["shell", "input", "keyevent", "67"]  # KEYCODE_DEL = 67
        self._run_adb_command(command_delete)

        logger.debug("已清空输入框内容")

    async def scroll(self, direction: str = "up", distance: float = 0.3) -> None:
        """滚动页面

        Args:
            direction: 滚动方向 up/down/left/right
            distance: 滚动距离比例（0~1），0.3=半屏滚动，0.6=全屏滚动，依此类推
        """
        # 使用设备实际分辨率
        width, height = self.width, self.height

        # 限制 distance 在合理范围内
        distance = max(0.1, min(0.8, distance))

        # 计算滚动坐标（使用屏幕中间区域）
        start_x = int(width / 2)
        start_y = int(height * 0.6)
        end_x = int(width / 2)
        end_y = int(height * (0.6 - distance))  # 根据距离比例计算终点
        duration = int(200 + distance * 600)  # 距离越长，持续时间越长

        if direction == "down":
            start_y = int(height * 0.4)
            end_y = int(height * (0.4 + distance))
        elif direction == "left":
            # 水平滚动向左
            start_x = int(width * 0.8)
            end_x = int(width * (0.8 - distance))
            start_y = int(height / 2)
            end_y = int(height / 2)
        elif direction == "right":
            # 水平滚动向右
            start_x = int(width * 0.2)
            end_x = int(width * (0.2 + distance))
            start_y = int(height / 2)
            end_y = int(height / 2)

        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend(
            [
                "shell",
                "input",
                "swipe",
                str(start_x),
                str(start_y),
                str(end_x),
                str(end_y),
                str(duration),
            ]
        )
        self._run_adb_command(command)
        logger.debug(f"滚动: {direction}")

    async def press_key(self, key: str) -> None:
        """按键"""
        key_map = {
            "home": "KEYCODE_HOME",
            "back": "KEYCODE_BACK",
            "enter": "KEYCODE_ENTER",
        }

        key_code = key_map.get(key.lower(), key)

        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend(["shell", "input", "keyevent", key_code])
        self._run_adb_command(command)
        logger.debug(f"按键: {key}")

    async def open_app(self, package_name: str) -> None:
        """打开App"""
        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        # 先尝试通过 monkey 启动（自动处理 Activity 选择）
        # adb shell monkey -p <package> -c android.intent.category.LAUNCHER 1
        command.extend(["shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"])
        self._run_adb_command(command)
        logger.debug(f"打开App: {package_name}")

    async def kill_app(self, package_name: str) -> None:
        """杀死App进程"""
        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend(["shell", "am", "force-stop", package_name])
        self._run_adb_command(command)
        logger.debug(f"杀死App: {package_name}")

    async def set_ime(self, ime_id: str = "com.android.adbkeyboard/.AdbIME") -> None:
        """切换输入法为指定IME"""
        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend(["shell", "ime", "set", ime_id])
        self._run_adb_command(command)
        logger.debug(f"切换输入法: {ime_id}")

    async def run_pre_actions(self) -> None:
        """任务执行前的前置操作"""
        logger.info("执行前置操作...")
        try:
            await self.set_ime()
            logger.info("前置操作完成: 输入法已切换为 ADBKeyBoard")
        except Exception as e:
            logger.warning(f"前置操作失败: {e}")

    async def _take_screenshot(self) -> str:
        """获取截图"""
        base_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "outputs",
            "task_screenshot",
        )

        if self.job_id:
            device_dir = os.path.join(base_dir, str(self.job_id))
        else:
            device_dir = os.path.join(base_dir, self.device_id or "unknown")

        os.makedirs(device_dir, exist_ok=True)

        import time
        timestamp = int(time.time() * 1000)
        screenshot_path = os.path.join(
            device_dir, f"{timestamp}.png"
        )

        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend(["exec-out", "screencap", "-p"])

        result = self._run_adb_command(command)
        stderr_text = result.stderr.decode("utf-8", errors="ignore") if result.stderr else ""
        if re.search(r"^error: device .*?", stderr_text):
            raise ConnectionError(f"设备 {self.device_id or 'unknown'} 已断连，截图失败")
        with open(screenshot_path, "wb") as f:
            f.write(result.stdout)

        logger.debug(f"截图保存到: {screenshot_path}")
        return screenshot_path

    def _run_adb_command(self, command: List[str]) -> subprocess.CompletedProcess:
        """运行ADB命令"""
        # 清理空字符串
        command = [c for c in command if c]
        try:
            logger.debug(f"运行ADB命令: {' '.join(command)}")
            return subprocess.run(command, capture_output=True, timeout=30)
        except subprocess.TimeoutExpired:
            logger.error(f"ADB命令超时: {' '.join(command)}")
            return subprocess.CompletedProcess(command, 1, b"", b"timeout")

    @classmethod
    async def create(cls, device_id: Optional[str] = None, **kwargs):
        """创建接口实例"""
        return cls(device_id=device_id, **kwargs)

    async def disconnect(self) -> None:
        """断开连接"""
        logger.info("断开Android设备连接")
