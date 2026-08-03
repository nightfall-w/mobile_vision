"""MCP Mobile Vision - Android 设备 ADB 控制接口

从 automation_agent/interfaces/android.py 提取，去除了项目特定依赖。
"""

import base64
import io
import math
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

from mcp_mobile_vision.config import SCREENSHOTS_DIR
from mcp_mobile_vision.recognizer import PageElementRecognizer
from mcp_mobile_vision.types import InterfaceType, PageContext


class AndroidInterface:
    """Android 设备接口 - ADB 控制 + 双通道页面识别"""

    interface_type = InterfaceType.ANDROID

    def __init__(
        self,
        device_id: Optional[str] = None,
        yolo_model_path: Optional[str] = None,
        ocr_engine: str = "rapidocr",
        class_names_from_db: List = None,
    ):
        self.device_id = device_id
        self.yolo_model_path = yolo_model_path
        self.ocr_engine = ocr_engine
        self.class_names_from_db = class_names_from_db
        self._recognizer = None
        self._u2 = None
        self.job_id: Optional[int] = None
        self.last_screenshot_path: Optional[str] = None
        self.page_hash: Optional[str] = None

        # 获取设备实际分辨率
        self.width, self.height = self._get_device_resolution()

        # 初始化 uiautomator2
        try:
            import uiautomator2 as u2
            self._u2 = u2.connect(self.device_id)
        except Exception:
            self._u2 = None

        self._init_recognizer()

    # ── DOM 通道 (uiautomator2) ──────────────────────────────────────

    def _get_dom_elements(self) -> Tuple[List[Dict], bool]:
        """通过 uiautomator2 获取页面 DOM 元素列表"""
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
            if "DeadSystemException" in str(e):
                self._u2 = None
            return [], False

    def _flatten_xml_node(
        self, node: ET.Element, output: List[Dict],
        parent_index: str = "", depth: int = 0
    ):
        """递归展平 XML 节点"""
        if depth > 50:
            return

        bounds_str = node.get("bounds", "")
        bbox = self._parse_bounds(bounds_str)
        if bbox is None:
            bbox = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}

        class_name = node.get("class", "")
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

        bbox_w = bbox["x2"] - bbox["x1"]
        bbox_h = bbox["y2"] - bbox["y1"]
        has_size = bbox_w > 0 and bbox_h > 0

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
        """判断是否为系统 UI 元素"""
        resource_id = elem.get("resource_id", "") or ""
        return resource_id.startswith("com.android.systemui")

    def _is_empty_container(self, elem: Dict) -> bool:
        """判断是否为空布局容器"""
        if elem.get("text") or elem.get("content_desc"):
            return False
        type_short = elem.get("type_short", "")
        return type_short in ("View", "FrameLayout", "LinearLayout", "RelativeLayout")

    def _dom_is_rich(self, dom_elements: List[Dict]) -> bool:
        """判断 DOM 是否足够丰富"""
        clickable_count = 0
        text_count = 0
        webview_count = 0
        filtered_out = 0

        for elem in dom_elements:
            if self._is_system_ui(elem):
                filtered_out += 1
                continue
            if self._is_empty_container(elem):
                filtered_out += 1
                continue
            if "WebView" in elem.get("type", ""):
                webview_count += 1
            if elem.get("clickable"):
                clickable_count += 1
            if elem.get("text") or elem.get("content_desc"):
                text_count += 1

        remaining = len(dom_elements) - filtered_out
        if webview_count > 0 and remaining > 0 and webview_count > remaining * 0.3:
            return False

        return clickable_count >= 1 and text_count >= 1

    # ── 视觉通道 (YOLO+OCR) ──────────────────────────────────────────

    def _get_device_resolution(self) -> tuple:
        """获取设备实际分辨率"""
        try:
            wm_cmd = ["adb"]
            if self.device_id:
                wm_cmd.extend(["-s", self.device_id])
            wm_cmd.extend(["shell", "wm", "size"])

            result = subprocess.run(wm_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                override_match = re.search(
                    r'Override size:\s*(\d+)x(\d+)', result.stdout
                )
                if override_match:
                    return int(override_match.group(1)), int(override_match.group(2))
                physical_match = re.search(
                    r'Physical size:\s*(\d+)x(\d+)', result.stdout
                )
                if physical_match:
                    return int(physical_match.group(1)), int(physical_match.group(2))
        except Exception:
            pass
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
            except Exception as e:
                raise Exception(f"初始化识别器失败: {e}")

    def _hash_file(self, file_path: str) -> str:
        """计算文件 MD5 哈希"""
        import hashlib
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    async def _get_visual_context(self) -> PageContext:
        """视觉通道：截图 + YOLO + OCR 识别"""
        screenshot_path = await self._take_screenshot()
        self.last_screenshot_path = screenshot_path
        self.page_hash = self._hash_file(screenshot_path)

        if not self._recognizer:
            # OCR-only 模式
            from PIL import Image
            import numpy as np
            from dataclasses import asdict

            page_id = f"ocr_only_{int(time.time() * 1000)}"
            img = Image.open(screenshot_path)
            img_array = np.array(img)
            ocr_texts = []

            temp_reader = None
            try:
                if self.ocr_engine == "easyocr":
                    import easyocr
                    temp_reader = easyocr.Reader(["en", "ch_sim"], verbose=False)
                else:
                    from rapidocr_onnxruntime import RapidOCR
                    temp_reader = RapidOCR()
            except Exception:
                temp_reader = None

            if temp_reader:
                try:
                    if self.ocr_engine == "easyocr":
                        results = temp_reader.readtext(img_array)
                        for idx, (bbox_coords, text, confidence) in enumerate(results):
                            if not text or not text.strip():
                                continue
                            if float(confidence) < 0.1:
                                continue
                            x_coords = [p[0] for p in bbox_coords]
                            y_coords = [p[1] for p in bbox_coords]
                            ocr_texts.append({
                                "text_id": f"text_{idx}",
                                "text": text.strip(),
                                "bbox": {
                                    "x1": float(min(x_coords)),
                                    "y1": float(min(y_coords)),
                                    "x2": float(max(x_coords)),
                                    "y2": float(max(y_coords)),
                                    "center_x": float((min(x_coords) + max(x_coords)) / 2),
                                    "center_y": float((min(y_coords) + max(y_coords)) / 2),
                                },
                                "confidence": float(confidence),
                                "language": "ch_sim" if any('一' <= c <= '鿿' for c in text) else "en",
                                "color": "unknown",
                                "color_brightness": 0.0,
                            })
                    else:
                        result, _ = temp_reader(img_array, text_score=0.1)
                        if result:
                            for idx, line in enumerate(result):
                                bbox_coords, text, score = line
                                if not text or not text.strip():
                                    continue
                                x_coords = [p[0] for p in bbox_coords]
                                y_coords = [p[1] for p in bbox_coords]
                                ocr_texts.append({
                                    "text_id": f"text_{idx}",
                                    "text": text.strip(),
                                    "bbox": {
                                        "x1": float(min(x_coords)),
                                        "y1": float(min(y_coords)),
                                        "x2": float(max(x_coords)),
                                        "y2": float(max(y_coords)),
                                        "center_x": float((min(x_coords) + max(x_coords)) / 2),
                                        "center_y": float((min(y_coords) + max(y_coords)) / 2),
                                    },
                                    "confidence": float(score),
                                    "language": "ch_sim" if any('一' <= c <= '鿿' for c in text) else "en",
                                    "color": "unknown",
                                    "color_brightness": 0.0,
                                })
                except Exception:
                    pass

            return PageContext(
                page_id=page_id,
                image_width=img.width,
                image_height=img.height,
                elements=[],
                texts=ocr_texts,
                structured_elements=[],
                source="ocr_only",
            )

        # YOLO + OCR 模式
        page_info = self._recognizer.recognize_from_image(screenshot_path)
        try:
            self._recognizer.draw_annotated_image(screenshot_path, screenshot_path)
        except Exception:
            pass

        structured_elements = self._recognizer.integrate_elements_and_texts(
            page_info.elements, page_info.texts
        )

        return PageContext(
            page_id=page_info.page_id,
            image_width=page_info.image_width,
            image_height=page_info.image_height,
            elements=page_info.elements,
            texts=page_info.texts,
            structured_elements=structured_elements,
            source="visual",
        )

    async def _get_dom_context(self) -> PageContext:
        """DOM 通道：uiautomator2 dump + 截图"""
        screenshot_path = await self._take_screenshot()
        self.last_screenshot_path = screenshot_path
        self.page_hash = self._hash_file(screenshot_path)

        dom_elements, success = self._get_dom_elements()
        if not success or not dom_elements:
            return await self._get_visual_context()

        interactive_elements = [
            e for e in dom_elements
            if (e.get("clickable") or e.get("text") or e.get("content_desc"))
            and not self._is_system_ui(e)
            and not self._is_empty_container(e)
        ]

        if not interactive_elements:
            return await self._get_visual_context()

        page_id = f"dom_{int(time.time() * 1000)}"

        return PageContext(
            page_id=page_id,
            image_width=self.width,
            image_height=self.height,
            elements=dom_elements,
            texts=[],
            structured_elements=interactive_elements,
            source="dom",
        )

    # ── 公共接口 ──────────────────────────────────────────────────────

    async def get_context(self) -> PageContext:
        """获取页面上下文 - 双通道策略"""
        if self._u2 is not None:
            dom_elements, success = self._get_dom_elements()
            if success and self._dom_is_rich(dom_elements):
                return await self._get_dom_context()

        return await self._get_visual_context()

    async def list_devices(self):
        """列出可用设备"""
        result = self._run_adb_command(["adb", "devices"])
        return [
            line.split("\t")[0]
            for line in result.stdout.split("\n")
            if line.strip() and "\t" in line
        ]

    async def tap(self, x: float, y: float):
        """点击坐标"""
        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend(["shell", "input", "tap", str(int(x)), str(int(y))])
        self._run_adb_command(command)

    async def long_press(self, x: float, y: float, duration: float = 1.0):
        """长按坐标"""
        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend([
            "shell", "input", "swipe",
            str(int(x)), str(int(y)), str(int(x)), str(int(y)),
            str(int(duration * 1000)),
        ])
        self._run_adb_command(command)

    async def input_text(self, text: str):
        """输入文本（Base64 编码，支持中文）"""
        await self._clear_input()

        text_bytes = text.encode("utf-8")
        base64_text = base64.b64encode(text_bytes).decode("ascii")

        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend([
            "shell", "am", "broadcast",
            "-a", "ADB_INPUT_B64",
            "--es", "msg", base64_text,
        ])
        self._run_adb_command(command)

    async def _clear_input(self):
        """清空输入框"""
        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])

        # 全选
        cmd_select = command + [
            "shell", "am", "broadcast",
            "-a", "ADB_INPUT_TEXT",
            "--es", "mcode", "4096,29",
        ]
        self._run_adb_command(cmd_select)

        # 删除
        cmd_delete = command + ["shell", "input", "keyevent", "67"]
        self._run_adb_command(cmd_delete)

    async def press_key(self, key: str):
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

    async def _take_screenshot(self) -> str:
        """获取截图"""
        device_dir = SCREENSHOTS_DIR / (self.device_id or "unknown")
        device_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time() * 1000)
        screenshot_path = str(device_dir / f"{timestamp}.png")

        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend(["exec-out", "screencap", "-p"])

        result = self._run_adb_command(command)
        with open(screenshot_path, "wb") as f:
            f.write(result.stdout)

        return screenshot_path

    async def _take_screenshot_with_marker(
        self, x: int, y: int, end_x: int = None, end_y: int = None
    ) -> str:
        """截图并在指定坐标绘制操作标记"""
        device_dir = SCREENSHOTS_DIR / (self.device_id or "unknown")
        device_dir.mkdir(parents=True, exist_ok=True)

        command = ["adb"]
        if self.device_id:
            command.extend(["-s", self.device_id])
        command.extend(["exec-out", "screencap", "-p"])

        result = self._run_adb_command(command)
        img = Image.open(io.BytesIO(result.stdout))
        draw = ImageDraw.Draw(img)

        if end_x is not None and end_y is not None:
            # 滑动标记：起点蓝色 + 终点绿色 + 连线箭头
            sr = 10
            draw.ellipse([x - sr, y - sr, x + sr, y + sr], fill=(0, 120, 255, 180))
            draw.ellipse([x - 24, y - 24, x + 24, y + 24], outline=(0, 120, 255, 200), width=3)
            draw.ellipse([end_x - sr, end_y - sr, end_x + sr, end_y + sr], fill=(0, 200, 80, 180))
            draw.ellipse([end_x - 24, end_y - 24, end_x + 24, end_y + 24], outline=(0, 200, 80, 200), width=3)
            draw.line([(x, y), (end_x, end_y)], fill=(255, 200, 0, 220), width=4)
            angle = math.atan2(end_y - y, end_x - x)
            arrow_len = 18
            ax = end_x - arrow_len * math.cos(angle - 0.4)
            ay = end_y - arrow_len * math.sin(angle - 0.4)
            bx = end_x - arrow_len * math.cos(angle + 0.4)
            by = end_y - arrow_len * math.sin(angle + 0.4)
            draw.polygon([(end_x, end_y), (ax, ay), (bx, by)], fill=(255, 200, 0, 220))
        else:
            # 点击标记：红色圆点 + 圆圈
            r = 8
            draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 0, 0, 180))
            ring_r = 22
            draw.ellipse([x - ring_r, y - ring_r, x + ring_r, y + ring_r], outline=(255, 0, 0, 200), width=3)

        timestamp = int(time.time() * 1000)
        suffix = "_scroll.png" if end_x is not None else "_click.png"
        screenshot_path = str(device_dir / f"{timestamp}{suffix}")
        img.save(screenshot_path, "PNG")

        return screenshot_path

    def _run_adb_command(self, command: List[str]) -> subprocess.CompletedProcess:
        """运行 ADB 命令"""
        command = [c for c in command if c]
        return subprocess.run(command, capture_output=True, timeout=30)

    async def disconnect(self):
        """断开连接"""
        pass