"""
Android设备接口 - 基于ADB实现设备控制和页面识别
支持双通道页面感知：DOM快通道 (uiautomator2) + 视觉兜底 (YOLO+OCR)
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Tuple

from automation_agent.page_recognizer import PageElementRecognizer
from automation_agent.types import InterfaceType, PageContext
from utils.custom_logging import logger

# 尝试导入 uiautomator2，失败时降级
try:
    import uiautomator2 as u2

    _HAS_U2 = True
except ImportError:
    _HAS_U2 = False
    logger.warning("uiautomator2 未安装，DOM 识别通道不可用，将使用视觉通道")


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
        self._u2 = None
        self.job_id: Optional[int] = None

        # 获取设备实际分辨率
        self.width, self.height = self._get_device_resolution()
        logger.info(f"设备分辨率: {self.width}x{self.height}")

        # 初始化 uiautomator2（可选）
        if _HAS_U2:
            try:
                self._u2 = u2.connect(self.device_id)
                logger.info("uiautomator2 初始化成功")
            except Exception as e:
                logger.warning(f"uiautomator2 初始化失败，将使用视觉通道: {e}")
                self._u2 = None

        self._init_recognizer()
        self.page_hash: Optional[str] = None

    # ── DOM 通道 (uiautomator2) ──────────────────────────────────────

    def _get_dom_elements(self) -> Tuple[List[Dict], bool]:
        """通过 uiautomator2 获取页面 DOM 元素列表

        Returns:
            (elements, success): elements 为结构化元素列表，success 表示是否成功获取
        """
        if self._u2 is None:
            return [], False

        try:
            xml = self._u2.dump_hierarchy()
            if not xml or not xml.strip():
                return [], False

            root = ET.fromstring(xml.encode("utf-8"))
            elements = []
            self._flatten_xml_node(root, elements, parent_index="0")
            return elements, True
        except Exception as e:
            logger.warning(f"DOM 获取失败: {e}")
            return [], False

    def _flatten_xml_node(self, node: ET.Element, output: List[Dict],
                          parent_index: str = "", depth: int = 0):
        """递归展平 XML 节点为结构化元素列表"""
        if depth > 50:  # 防止过深递归
            return

        # 解析 bounds: "[x1,y1][x2,y2]" → {"x1":..., "y1":..., "x2":..., "y2":...}
        bounds_str = node.get("bounds", "")
        bbox = self._parse_bounds(bounds_str)
        if bbox is None:
            bbox = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}

        class_name = node.get("class", "")
        # 提取短类名: "android.widget.Button" → "Button"
        type_short = class_name.split(".")[-1] if class_name else "Unknown"

        text = node.get("text", "")
        content_desc = node.get("content-desc", "")
        resource_id = node.get("resource-id", "")
        clickable = node.get("clickable", "false") == "true"
        enabled = node.get("enabled", "true") == "true"
        checkable = node.get("checkable", "false") == "true"
        checked = node.get("checked", "false") == "true"
        focusable = node.get("focusable", "false") == "true"
        focused = node.get("focused", "false") == "true"
        scrollable = node.get("scrollable", "false") == "true"

        index = node.get("index", "0")
        node_id = f"{parent_index}.{index}" if parent_index != "0" else index

        # 只保留有意义的节点（有尺寸、或是交互元素）
        bbox_w = bbox["x2"] - bbox["x1"]
        bbox_h = bbox["y2"] - bbox["y1"]
        has_size = bbox_w > 0 and bbox_h > 0

        # 构建元素
        element = {
            "id": f"dom_{node_id}",
            "type": class_name,
            "type_short": type_short,
            "bbox": [int(bbox["x1"]), int(bbox["y1"]), int(bbox["x2"]), int(bbox["y2"])],
            "bbox_center": {
                "center_x": int((bbox["x1"] + bbox["x2"]) / 2),
                "center_y": int((bbox["y1"] + bbox["y2"]) / 2),
            },
            "text": text,
            "content_desc": content_desc,
            "resource_id": resource_id,
            "clickable": clickable,
            "enabled": enabled,
            "checkable": checkable,
            "checked": checked,
            "focusable": focusable,
            "focused": focused,
            "scrollable": scrollable,
            "source": "dom",
            "depth": depth,
            "children": [],
        }

        if has_size:
            output.append(element)

        # 递归子节点
        for child in node:
            self._flatten_xml_node(child, output, node_id, depth + 1)

    def _parse_bounds(self, bounds_str: str) -> Optional[Dict]:
        """解析 uiautomator2 bounds 格式: "[x1,y1][x2,y2]" """
        if not bounds_str:
            return None
        match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
        if match:
            return {
                "x1": int(match.group(1)),
                "y1": int(match.group(2)),
                "x2": int(match.group(3)),
                "y2": int(match.group(4)),
            }
        return None

    def _is_system_ui(self, elem: Dict) -> bool:
        """判断是否为系统 UI 元素（状态栏、导航栏）"""
        resource_id = elem.get("resource_id", "") or ""
        return resource_id.startswith("com.android.systemui")

    def _is_empty_container(self, elem: Dict) -> bool:
        """判断是否为空布局容器（无文本、无描述、纯布局用途）"""
        if elem.get("text") or elem.get("content_desc"):
            return False
        type_short = elem.get("type_short", "")
        return type_short in ("View", "FrameLayout", "LinearLayout", "RelativeLayout")

    def _dom_is_rich(self, dom_elements: List[Dict]) -> bool:
        """判断 DOM 是否足够丰富，值得使用 DOM 通道

        规则：
        - 排除系统 UI 元素（状态栏、导航栏）
        - 排除空布局容器（View/FrameLayout 等无文本节点）
        - 排除 WebView 只读场景
        - 剩余元素中至少 3 个 clickable，至少 1 个有文本
        """
        clickable_count = 0
        text_count = 0
        webview_count = 0
        filtered_out = 0

        for elem in dom_elements:
            # 跳过系统 UI（状态栏、导航栏）
            if self._is_system_ui(elem):
                filtered_out += 1
                continue

            # 跳过空布局容器
            if self._is_empty_container(elem):
                filtered_out += 1
                continue

            if "WebView" in elem.get("type", ""):
                webview_count += 1

            if elem.get("clickable"):
                clickable_count += 1

            if elem.get("text") or elem.get("content_desc"):
                text_count += 1

        # 如果 WebView 占比过高
        remaining = len(dom_elements) - filtered_out
        if webview_count > 0 and remaining > 0 and webview_count > remaining * 0.3:
            logger.info(f"【uiautomator2】DOM 通道跳过：WebView 占比过高 ({webview_count}/{remaining})")
            return False

        is_rich = clickable_count >= 3 and text_count >= 1
        logger.info(
            f"【uiautomator2】DOM 丰富度检查: "
            f"有效元素(clickable={clickable_count}, text={text_count}), "
            f"已过滤(系统UI+空容器={filtered_out}), "
            f"总计={len(dom_elements)}, rich={is_rich}"
        )
        return is_rich

    # ── 视觉通道 (YOLO+OCR) ──────────────────────────────────────────

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

    async def _get_visual_context(self) -> PageContext:
        """视觉通道：截图 + YOLO + OCR 识别"""
        logger.info("【视觉通道】开始 YOLO+OCR 识别...")
        screenshot_path = await self._take_screenshot()
        self.last_screenshot_path = screenshot_path
        self.page_hash = self._hash_file(screenshot_path)

        if not self._recognizer:
            raise Exception("未找到可用的页面识别器")

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
            f"【视觉通道】识别耗时: {t1 - t0:.2f}s (引擎: {self.ocr_engine}), "
            f"元素整合耗时: {t2 - t1:.2f}s, 总耗时: {t2 - t0:.2f}s, "
            f"元素数: {len(page_info.elements)}, 文本数: {len(page_info.texts)}"
        )

        logger.info("【视觉通道】识别完成，返回 PageContext(source=visual)")
        context = PageContext(
            page_id=page_info.page_id,
            image_width=page_info.image_width,
            image_height=page_info.image_height,
            elements=page_info.elements,
            texts=page_info.texts,
            structured_elements=structured_elements,
            source="visual",
        )
        return context

    async def _get_dom_context(self) -> PageContext:
        """DOM 通道：uiautomator2 dump + 截图"""
        logger.info("【DOM 通道】开始 uiautomator2 识别...")
        screenshot_path = await self._take_screenshot()
        self.last_screenshot_path = screenshot_path
        self.page_hash = self._hash_file(screenshot_path)

        dom_elements, success = self._get_dom_elements()
        if not success or not dom_elements:
            logger.warning("【DOM 通道】获取失败，降级到视觉通道")
            return await self._get_visual_context()

        # 过滤出有意义的元素用于决策（排除系统 UI 和空容器）
        interactive_elements = [
            e for e in dom_elements
            if (e.get("clickable") or e.get("text") or e.get("content_desc"))
            and not self._is_system_ui(e)
            and not self._is_empty_container(e)
        ]

        # 如果没有交互元素，降级到视觉
        if not interactive_elements:
            logger.info("【DOM 通道】无交互元素，降级到视觉通道")
            return await self._get_visual_context()

        page_id = f"dom_{int(time.time() * 1000)}"

        # 使用 DOM 元素作为 structured_elements
        # 同时保留原始 DOM 数据在 elements 中
        logger.info(
            f"【DOM 通道】识别完成: 共 {len(dom_elements)} 个元素, "
            f"{len(interactive_elements)} 个交互元素"
        )
        logger.info(
            f"【DOM 通道】交互元素示例: "
            f"{json.dumps(interactive_elements[:3], ensure_ascii=False, indent=2)}"
        )

        logger.info("【DOM 通道】识别完成，返回 PageContext(source=dom)")
        context = PageContext(
            page_id=page_id,
            image_width=self.width,
            image_height=self.height,
            elements=dom_elements,
            texts=[],
            structured_elements=interactive_elements,
            source="dom",
        )
        return context

    # ── 公共接口 ──────────────────────────────────────────────────────

    async def get_context(self) -> PageContext:
        """获取页面上下文

        双通道策略：
        1. 尝试 DOM 快通道（uiautomator2，0.3-0.8s）
        2. 如果 DOM 不够丰富，降级到视觉通道（YOLO+OCR，2-3s）
        """
        # ---- 通道选择日志 ----
        if self._u2 is not None:
            logger.info("═" * 50)
            logger.info(f"【uiautomator2】DOM 通道可用，开始尝试...")
            dom_elements, success = self._get_dom_elements()
            if success:
                clickable_count = sum(1 for e in dom_elements if e.get("clickable"))
                text_count = sum(1 for e in dom_elements if e.get("text") or e.get("content_desc"))
                logger.info(f"【uiautomator2】DOM 获取成功: {len(dom_elements)} 个元素, "
                            f"clickable={clickable_count}, 含文本={text_count}")

                if self._dom_is_rich(dom_elements):
                    logger.info(f"【uiautomator2】DOM 足够丰富 → 使用 DOM 快通道")
                    logger.info("═" * 50)
                    return await self._get_dom_context()
                else:
                    logger.info(f"【uiautomator2】DOM 不够丰富 → 降级到视觉通道")
            else:
                logger.warning(f"【uiautomator2】DOM 获取失败 → 降级到视觉通道")
            logger.info("═" * 50)
        else:
            logger.info(f"【uiautomator2】未初始化或不可用 → 使用视觉通道")
            logger.info(f"    (如需启用请安装 uiautomator2 并确保设备已连接)")

        return await self._get_visual_context()

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
        from core.config import SCREENSHOTS_DIR
        base_dir = str(SCREENSHOTS_DIR)

        if self.job_id:
            device_dir = os.path.join(base_dir, str(self.job_id))
        else:
            device_dir = os.path.join(base_dir, self.device_id or "unknown")

        os.makedirs(device_dir, exist_ok=True)

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