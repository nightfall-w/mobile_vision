"""
页面元素识别服务
结合YOLO模型识别UI元素和OCR识别文字
支持easyOCR和RapidOCR两种引擎
"""

import json
import os
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import easyocr
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO
from rapidocr_onnxruntime import RapidOCR


@dataclass
class BoundingBox:
    """边界框"""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def center(self) -> tuple:
        return (self.center_x, self.center_y)


@dataclass
class UIElement:
    """UI元素"""
    element_id: str
    element_type: str
    class_name: str
    bbox: BoundingBox
    confidence: float
    text: Optional[str] = None


@dataclass
class TextElement:
    """文字元素"""
    text_id: str
    text: str
    bbox: BoundingBox
    confidence: float
    language: str = "en"
    color: str = "unknown"
    color_brightness: float = 0.0


@dataclass
class PageInfo:
    """页面信息"""
    page_id: str
    image_path: str
    image_width: int
    image_height: int
    elements: List[Dict]
    texts: List[Dict]
    total_elements: int
    total_texts: int


class PageElementRecognizer:
    """页面元素识别器"""

    def __init__(
            self,
            yolo_model_path: str,
            use_gpu: bool = True,
            languages: List[str] = ['en', 'ch_sim'],
            ocr_engine: str = "rapidocr",
            ocr_conf_threshold: float = 0.1,
            class_names_from_db: List = None
    ):
        """初始化页面元素识别器"""
        self.yolo_model_path = yolo_model_path
        self.yolo_model = None
        self.ocr_reader = None
        self.use_gpu = use_gpu
        self.languages = languages
        self.ocr_engine = ocr_engine.lower()
        self.ocr_conf_threshold = ocr_conf_threshold
        self._initialized = False

        # 优先使用数据库中的 classes 作为显示名称（中文优先）
        self.db_class_names = class_names_from_db or []
        self._display_names = {}
        self.class_names = {}

        if self.ocr_engine not in ["easyocr", "rapidocr"]:
            raise ValueError(f"不支持的OCR引擎: {ocr_engine}，可选 'easyocr' 或 'rapidocr'")

    def _init_yolo(self):
        """初始化YOLO模型"""
        if self.yolo_model is None:
            self.yolo_model = YOLO(self.yolo_model_path)
            self.class_names = self.yolo_model.names if hasattr(self.yolo_model, 'names') else {}
            # 优先使用数据库中的 classes 作为显示名称
            if self.db_class_names:
                self._display_names = {i: name for i, name in enumerate(self.db_class_names)}
            else:
                self._display_names = self.class_names
            print(f"YOLO模型加载成功: {self.yolo_model_path}")

    def _init_ocr(self):
        """初始化OCR引擎"""
        if self.ocr_reader is None:
            if self.ocr_engine == "easyocr":
                self._init_easyocr()
            elif self.ocr_engine == "rapidocr":
                self._init_rapidocr()

    def _init_easyocr(self):
        """初始化easyOCR"""
        self.ocr_reader = easyocr.Reader(
            self.languages,
            gpu=self.use_gpu,
            verbose=False
        )
        print(f"EasyOCR初始化成功, 语言: {self.languages}")

    def _init_rapidocr(self):
        """初始化RapidOCR"""
        try:
            self.ocr_reader = RapidOCR(return_word_box=True)
            print(f"RapidOCR初始化成功, 语言: {self.languages}")
        except ImportError:
            print("错误: 未安装RapidOCR，请运行 `pip install rapidocr-onnxruntime`")
            raise

    def initialize(self):
        """初始化所有模型"""
        if not self._initialized:
            self._init_yolo()
            self._init_ocr()
            self._initialized = True
            print("页面元素识别器初始化完成")

    def recognize_from_image(self, image_path: str, conf_threshold: float = 0.25) -> PageInfo:
        """从图片识别页面元素和文字"""
        if not self._initialized:
            self.initialize()

        # ====================== 核心：重试逻辑 ======================
        max_retry = 3
        retry_delay = 0.5
        image = None

        for attempt in range(1, max_retry + 1):
            try:
                image = Image.open(image_path)
                image.verify()
                image.close()

                image = Image.open(image_path)
                break

            except Exception as e:
                print(f"⚠️  图片损坏，可能是与设备断连，第 {attempt} 次重试，等待 {retry_delay}s...")
                if attempt >= max_retry:
                    raise ConnectionError(f"设备可能已断连，截图文件损坏：{image_path}") from e
                time.sleep(retry_delay)
        # ===========================================================

        image_width, image_height = image.size
        image_array = np.array(image)

        # OCR不需要全分辨率，缩小到短边<=1200像素，速度翻倍精度几乎无损
        h, w = image_array.shape[:2]
        ocr_scale = 1.0
        max_side = max(h, w)
        if max_side > 1200:
            ocr_scale = 1200 / max_side
            new_h, new_w = int(h * ocr_scale), int(w * ocr_scale)
            ocr_array = cv2.resize(image_array, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            ocr_array = image_array

        elements = self._recognize_elements(image_path, conf_threshold)
        texts = self._recognize_texts(ocr_array, image_path)

        # 将 OCR 坐标从缩放空间映射回原始图像空间
        if ocr_scale < 1.0 and texts:
            for t in texts:
                b = t["bbox"]
                b["x1"] = b["x1"] / ocr_scale
                b["y1"] = b["y1"] / ocr_scale
                b["x2"] = b["x2"] / ocr_scale
                b["y2"] = b["y2"] / ocr_scale
                b["center_x"] = b["center_x"] / ocr_scale
                b["center_y"] = b["center_y"] / ocr_scale

        page_id = str(uuid.uuid4())[:8]

        return PageInfo(
            page_id=page_id,
            image_path=image_path,
            image_width=image_width,
            image_height=image_height,
            elements=elements,
            texts=texts,
            total_elements=len(elements),
            total_texts=len(texts)
        )

    def _recognize_elements(self, image_path: str, conf_threshold: float) -> List[Dict]:
        """识别UI元素"""
        results = self.yolo_model.predict(
            source=image_path,
            conf=conf_threshold,
            verbose=False,
            device='cpu'
        )

        elements = []

        for result in results:
            boxes = result.boxes
            for idx, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls = int(box.cls[0].cpu().numpy())
                # 中文优先：如果是dict格式（含chinese/english），优先取中文
                raw_display = self._display_names.get(cls, self.class_names.get(cls, f'class_{cls}'))
                if isinstance(raw_display, dict):
                    display_name = raw_display.get("chinese", raw_display.get("english", f'class_{cls}'))
                else:
                    display_name = raw_display
                class_name = display_name

                bbox = BoundingBox(
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2)
                )

                element = UIElement(
                    element_id=f"elem_{idx}",
                    element_type="ui_component",
                    class_name=class_name,
                    bbox=bbox,
                    confidence=conf
                )
                elem_dict = asdict(element)
                elem_dict["bbox"]["center_x"] = bbox.center_x
                elem_dict["bbox"]["center_y"] = bbox.center_y
                elements.append(elem_dict)

        return elements

    def draw_annotated_image(self, image_path: str, output_path: str):
        """在截图标注YOLO识别的UI元素边框和类别名，保存到output_path"""
        if not self.yolo_model:
            self._init_yolo()

        results = self.yolo_model.predict(
            source=image_path,
            conf=0.25,
            verbose=False,
            device='cpu'
        )

        image = Image.open(image_path).convert('RGB')
        draw = ImageDraw.Draw(image)

        font_size = max(16, min(image.size) // 55)
        font = self._get_chinese_font(font_size)

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls = int(box.cls[0].cpu().numpy())

                display_name = self._display_names.get(cls, self.class_names.get(cls, f'class_{cls}'))
                if isinstance(display_name, dict):
                    display_name = display_name.get('chinese', display_name.get('english', f'class_{cls}'))

                color = self._get_color(cls)

                # 边框
                draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)

                # 标签文字
                text = f'{display_name}: {conf:.2f}'
                text_bbox = draw.textbbox((x1, y1 - font_size - 4), text, font=font)
                label_h = text_bbox[3] - text_bbox[1]
                label_w = text_bbox[2] - text_bbox[0]
                draw.rectangle([(x1, y1 - label_h - 4), (x1 + label_w + 8, y1)], fill=color)
                draw.text((x1 + 4, y1 - label_h - 4), text, fill='white', font=font)

        image.save(output_path, quality=95)

    @staticmethod
    def _get_chinese_font(font_size: int = 22):
        """获取中文字体"""
        chinese_font_paths = [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        ]
        for fp in chinese_font_paths:
            if os.path.exists(fp):
                try:
                    return ImageFont.truetype(fp, font_size)
                except Exception:
                    continue
        try:
            return ImageFont.truetype('/System/Library/Fonts/SFNSDisplay.ttf', font_size)
        except Exception:
            return ImageFont.load_default()

    @staticmethod
    def _get_color(class_id: int) -> tuple:
        colors = [
            (255, 0, 0), (0, 150, 255), (0, 200, 0), (255, 0, 150),
            (0, 100, 255), (255, 200, 0), (150, 0, 255), (0, 200, 200),
            (200, 100, 0), (100, 200, 100),
        ]
        return colors[class_id % len(colors)]

    def _recognize_texts(self, image_array: np.ndarray, image_path: str) -> List[Dict]:
        """识别文字"""
        if self.ocr_engine == "easyocr":
            return self._recognize_texts_easyocr(image_array, image_path)
        elif self.ocr_engine == "rapidocr":
            return self._recognize_texts_rapidocr(image_array, image_path)

    def _recognize_texts_easyocr(self, image_array: np.ndarray, image_path: str) -> List[Dict]:
        """使用easyOCR识别文字"""
        ocr_results = self.ocr_reader.readtext(image_array)

        texts = []
        for idx, (bbox_coords, text, confidence) in enumerate(ocr_results):
            if not text or not text.strip():
                continue

            # 过滤低置信度文本
            if float(confidence) < self.ocr_conf_threshold:
                continue

            if isinstance(bbox_coords, np.ndarray):
                bbox_coords = bbox_coords.tolist()

            x_coords = [point[0] for point in bbox_coords]
            y_coords = [point[1] for point in bbox_coords]

            x1, y1 = min(x_coords), min(y_coords)
            x2, y2 = max(x_coords), max(y_coords)

            bbox = BoundingBox(
                x1=float(x1),
                y1=float(y1),
                x2=float(x2),
                y2=float(y2)
            )

            color_info = self._analyze_text_color(image_path, bbox_coords)

            text_element = TextElement(
                text_id=f"text_{idx}",
                text=text.strip(),
                bbox=bbox,
                confidence=float(confidence),
                language=self._detect_text_language(text),
                color=color_info['color'],
                color_brightness=color_info['brightness']
            )
            text_dict = asdict(text_element)
            text_dict["bbox"]["center_x"] = bbox.center_x
            text_dict["bbox"]["center_y"] = bbox.center_y
            texts.append(text_dict)

        return texts

    def _recognize_texts_rapidocr(self, image_array: np.ndarray, image_path: str) -> List[Dict]:
        """使用RapidOCR识别文字（支持 numpy array，可配合缩放加速）"""
        result, _ = self.ocr_reader(image_array, text_score=self.ocr_conf_threshold)

        texts = []
        if result is None:
            return texts

        h, w = image_array.shape[:2]
        for idx, line in enumerate(result):
            bbox_coords, text, score = line

            if not text or not text.strip():
                continue

            # RapidOCR已经使用text_score过滤，这里再做一次保险过滤
            if float(score) < self.ocr_conf_threshold:
                continue

            x_coords = [point[0] for point in bbox_coords]
            y_coords = [point[1] for point in bbox_coords]

            x1, y1 = min(x_coords), min(y_coords)
            x2, y2 = max(x_coords), max(y_coords)

            # clamp 到图片范围内，防止溢出
            x1 = max(0.0, min(float(x1), float(w)))
            x2 = max(0.0, min(float(x2), float(w)))
            y1 = max(0.0, min(float(y1), float(h)))
            y2 = max(0.0, min(float(y2), float(h)))

            bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)

            color_info = self._analyze_text_color(image_path, bbox_coords)

            text_element = TextElement(
                text_id=f"text_{idx}",
                text=text.strip(),
                bbox=bbox,
                confidence=float(score),
                language=self._detect_text_language(text),
                color=color_info['color'],
                color_brightness=color_info['brightness']
            )
            text_dict = asdict(text_element)
            text_dict["bbox"]["center_x"] = bbox.center_x
            text_dict["bbox"]["center_y"] = bbox.center_y
            texts.append(text_dict)

        return texts

    def _detect_text_language(self, text: str) -> str:
        """简单检测文本语言"""
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            return "ch_sim"
        return "en"

    def _analyze_text_color(self, image_path: str, bbox_coords: list) -> dict:
        """通用文字颜色分析"""
        try:
            img = Image.open(image_path).convert('RGB')
            img_array = np.array(img)

            # 获取边界框范围
            x_coords = [point[0] for point in bbox_coords]
            y_coords = [point[1] for point in bbox_coords]
            x1 = int(np.clip(min(x_coords), 0, img.width - 1))
            y1 = int(np.clip(min(y_coords), 0, img.height - 1))
            x2 = int(np.clip(max(x_coords), 0, img.width - 1))
            y2 = int(np.clip(max(y_coords), 0, img.height - 1))

            if x2 <= x1 or y2 <= y1:
                return {'color': 'unknown', 'brightness': 0.0}

            roi = img_array[y1:y2, x1:x2]
            h, w = roi.shape[:2]

            # 超小元素直接去ROI中心像素的RGB值
            if h < 3 or w < 3:
                center_color = roi[h // 2, w // 2]
                r, g, b = int(center_color[0]), int(center_color[1]), int(center_color[2])
                brightness = (r + g + b) / 3
                return self._classify_color(r, g, b, brightness)

            # 步骤1：大津法二值化
            gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 前景（白色区域）和背景（黑色区域）
            fg_mask = (binary == 255)
            bg_mask = (binary == 0)

            fg_pixels = roi[fg_mask]
            bg_pixels = roi[bg_mask]

            # 步骤2：核心原则 - 文字通常是面积较小的那一类
            # 因为文字笔画占整个边界框的比例通常 < 50%
            if len(fg_pixels) == 0 or len(bg_pixels) == 0:
                # 单一颜色，直接返回
                median_color = np.median(roi, axis=(0, 1))
                r, g, b = int(median_color[0]), int(median_color[1]), int(median_color[2])
                brightness = (r + g + b) / 3
                return self._classify_color(r, g, b, brightness)

            # 面积较小的作为文字像素
            if len(fg_pixels) < len(bg_pixels):
                text_pixels = fg_pixels
            else:
                text_pixels = bg_pixels

            # 步骤3：但如果面积较小的像素亮度极低且饱和度也低，
            # 可能只是边框阴影，此时取面积较大的作为文字（兜底）
            if len(text_pixels) > 0:
                text_brightness = np.mean(text_pixels) / 255.0
                text_saturation = self._calculate_saturation(text_pixels)

                # 如果提取的文字太暗且饱和度低，可能是误提取的背景杂质
                if text_brightness < 0.15 and text_saturation < 0.1:
                    # 改为取面积较大的作为文字
                    if len(fg_pixels) > len(bg_pixels):
                        text_pixels = fg_pixels
                    else:
                        text_pixels = bg_pixels

            # 步骤4：提取文字颜色
            if len(text_pixels) == 0:
                median_color = np.median(roi, axis=(0, 1))
            else:
                median_color = np.median(text_pixels, axis=0)

            r, g, b = int(median_color[0]), int(median_color[1]), int(median_color[2])
            brightness = (r + g + b) / 3

            return self._classify_color(r, g, b, brightness)

        except Exception as e:
            print(f"颜色分析失败: {e}")
            return {'color': 'unknown', 'brightness': 0.0}

    def _calculate_saturation(self, pixels):
        """计算像素集合的平均饱和度"""
        if len(pixels) == 0:
            return 0.0
        max_rgb = np.max(pixels, axis=1).astype(float)
        min_rgb = np.min(pixels, axis=1).astype(float)
        with np.errstate(invalid='ignore', divide='ignore'):
            diff = max_rgb - min_rgb
            saturation = np.zeros_like(diff)
            mask = max_rgb > 0
            saturation[mask] = diff[mask] / max_rgb[mask]
        return float(np.mean(saturation))

    def _classify_color(self, r: int, g: int, b: int, brightness: float) -> dict:
        """颜色分类（保持原有逻辑）"""
        # 极黑/极白
        if brightness < 45:
            return {'color': 'black', 'brightness': brightness}
        elif brightness > 225:
            return {'color': 'white', 'brightness': brightness}

        # 计算饱和度
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        saturation = max_val - min_val

        # 低饱和度 -> 灰色
        if saturation < 35:
            if brightness < 100:
                return {'color': 'dark_gray', 'brightness': brightness}
            elif brightness > 180:
                return {'color': 'light_gray', 'brightness': brightness}
            else:
                return {'color': 'gray', 'brightness': brightness}

        # 彩色判断
        if r > g + 35 and r > b + 35:
            return {'color': 'red', 'brightness': brightness}
        elif g > r + 35 and g > b + 35:
            return {'color': 'green', 'brightness': brightness}
        elif b > r + 35 and b > g + 35:
            return {'color': 'blue', 'brightness': brightness}
        elif r > 180 and g > 150 and b < 120:
            return {'color': 'orange', 'brightness': brightness}
        elif r > 200 and g > 180 and b < 130:
            return {'color': 'yellow', 'brightness': brightness}

        # 兜底
        if brightness < 100:
            return {'color': 'dark', 'brightness': brightness}
        else:
            return {'color': 'light', 'brightness': brightness}

    def to_json(self, page_info: PageInfo, indent: int = 2) -> str:
        """将页面信息转换为JSON字符串"""
        return json.dumps(asdict(page_info), ensure_ascii=False, indent=indent)

    def save_json(self, page_info: PageInfo, output_path: str):
        """保存页面信息到JSON文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json(page_info))
        print(f"页面信息已保存到: {output_path}")

    def get_combined_elements(self, page_info: PageInfo) -> List[Dict]:
        """
        合并UI元素和文字元素
        返回统一格式的列表
        """
        combined = []

        for elem in page_info.elements:
            combined.append({
                "id": elem["element_id"],
                "type": elem["element_type"],
                "class_name": elem["class_name"],
                "bbox": {
                    "x1": elem["bbox"]["x1"],
                    "y1": elem["bbox"]["y1"],
                    "x2": elem["bbox"]["x2"],
                    "y2": elem["bbox"]["y2"],
                    "center_x": (elem["bbox"]["x1"] + elem["bbox"]["x2"]) / 2,
                    "center_y": (elem["bbox"]["y1"] + elem["bbox"]["y2"]) / 2,
                    "width": elem["bbox"]["x2"] - elem["bbox"]["x1"],
                    "height": elem["bbox"]["y2"] - elem["bbox"]["y1"]
                },
                "confidence": elem["confidence"],
                "text": elem.get("text"),
                "source": "yolo"
            })

        for text in page_info.texts:
            combined.append({
                "id": text["text_id"],
                "type": "text",
                "text": text["text"],
                "bbox": {
                    "x1": text["bbox"]["x1"],
                    "y1": text["bbox"]["y1"],
                    "x2": text["bbox"]["x2"],
                    "y2": text["bbox"]["y2"],
                    "center_x": (text["bbox"]["x1"] + text["bbox"]["x2"]) / 2,
                    "center_y": (text["bbox"]["y1"] + text["bbox"]["y2"]) / 2,
                    "width": text["bbox"]["x2"] - text["bbox"]["x1"],
                    "height": text["bbox"]["y2"] - text["bbox"]["y1"]
                },
                "confidence": text["confidence"],
                "language": text.get("language", "en"),
                "source": "ocr"
            })

        return combined

    def integrate_elements_and_texts(self, elements: List[Dict], texts: List[Dict]) -> List[Dict]:
        """通过空间关系将元素和文本整合为嵌套的树形结构"""
        # 去重：bbox 高度重叠（>80%）的元素只保留置信度最高的
        deduped_elements = self._dedup_overlapping_elements(elements)

        all_items = []

        for i, elem in enumerate(deduped_elements):
            raw_bbox = elem.get("bbox", {})
            all_items.append({
                "id": f"elem_{i}",
                "type": elem.get("class_name", "unknown"),
                "bbox": {
                    "x1": raw_bbox.get("x1", 0),
                    "y1": raw_bbox.get("y1", 0),
                    "x2": raw_bbox.get("x2", 0),
                    "y2": raw_bbox.get("y2", 0),
                    "center_x": raw_bbox.get("center_x", 0),
                    "center_y": raw_bbox.get("center_y", 0),
                },
                "raw": elem,
                "text": elem.get("text"),
                "children": []
            })

        for j, text in enumerate(texts):
            raw_bbox = text.get("bbox", {})
            all_items.append({
                "id": f"text_{j}",
                "type": "text_block",
                "bbox": {
                    "x1": raw_bbox.get("x1", 0),
                    "y1": raw_bbox.get("y1", 0),
                    "x2": raw_bbox.get("x2", 0),
                    "y2": raw_bbox.get("y2", 0),
                    "center_x": raw_bbox.get("center_x", 0),
                    "center_y": raw_bbox.get("center_y", 0),
                },
                "raw": text,
                "text": text.get("text", ""),
                "color": text.get("color", "unknown"),
                "color_brightness": text.get("color_brightness", 0.0),
                "children": []
            })

        all_items.sort(key=lambda x: self._get_area(x["bbox"]))

        for i, item in enumerate(all_items):
            parent = self._find_containing_parent(item, all_items, i)
            if parent:
                parent["children"].append(item)

        root_items = [item for item in all_items if not self._has_parent(item, all_items)]

        def sort_children_recursive(item):
            if item["children"]:
                item["children"].sort(key=lambda x: (
                    x["bbox"].get("y1", 0),
                    x["bbox"].get("x1", 0)
                ))
                for child in item["children"]:
                    sort_children_recursive(child)

        for item in root_items:
            sort_children_recursive(item)

        def convert_to_output(item):
            """ 将内部元素结构转换为标准输出格式（递归处理嵌套子元素）"""
            bbox = item["bbox"]
            result = {
                "id": item["id"],
                "type": item["type"],
                "bbox": [
                    int(bbox.get("x1", 0)),
                    int(bbox.get("y1", 0)),
                    int(bbox.get("x2", 0)),
                    int(bbox.get("y2", 0))
                ],
                "bbox_center": {
                    "center_x": int(bbox.get("center_x")),
                    "center_y": int(bbox.get("center_y"))
                },
                "confidence": item["raw"].get("confidence", 0) if item.get("raw") else 0
            }

            # 添加文本内容（普通元素直接从text字段获取）
            if item.get("text"):
                result["text"] = item["text"]
            # 文本块类型需要从raw中提取完整文本信息及颜色属性
            if item["type"] == "text_block":
                result["text"] = item["raw"].get("text", "") if item.get("raw") else ""
                result["color"] = item["color"]
                result["color_brightness"] = item["color_brightness"]

            # 递归转换子元素为输出格式
            if item["children"]:
                result["children"] = [convert_to_output(child) for child in item["children"]]

            return result

        # 按从上到下、从左到右的顺序排列根元素
        root_items.sort(key=lambda x: (
            x["bbox"].get("y1", 0),
            x["bbox"].get("x1", 0)
        ))

        # 转换所有根元素并返回最终结果
        return [convert_to_output(item) for item in root_items]

    def _dedup_overlapping_elements(self, elements: List[Dict]) -> List[Dict]:
        """对 bbox 高度重叠（IoU >= 0.8）的元素去重，保留置信度最高的"""
        if len(elements) <= 1:
            return elements
        # 按置信度降序排列，高置信度优先保留
        indexed = sorted(enumerate(elements), key=lambda x: x[1].get("confidence", 0), reverse=True)
        kept = []
        kept_indices = set()
        for idx, elem in indexed:
            if idx in kept_indices:
                continue
            # 检查是否与已保留的元素高度重叠
            overlaps = False
            for k_idx in kept_indices:
                if self._calculate_iou(elem["bbox"], elements[k_idx]["bbox"]) >= 0.8:
                    overlaps = True
                    break
            if not overlaps:
                kept.append(elem)
                kept_indices.add(idx)
        return kept

    @staticmethod
    def _calculate_iou(bbox_a: Dict, bbox_b: Dict) -> float:
        """计算两个 bbox 的 IoU"""
        x1 = max(bbox_a.get("x1", 0), bbox_b.get("x1", 0))
        y1 = max(bbox_a.get("y1", 0), bbox_b.get("y1", 0))
        x2 = min(bbox_a.get("x2", 0), bbox_b.get("x2", 0))
        y2 = min(bbox_a.get("y2", 0), bbox_b.get("y2", 0))
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inter = (x2 - x1) * (y2 - y1)
        area_a = (bbox_a.get("x2", 0) - bbox_a.get("x1", 0)) * (bbox_a.get("y2", 0) - bbox_a.get("y1", 0))
        area_b = (bbox_b.get("x2", 0) - bbox_b.get("x1", 0)) * (bbox_b.get("y2", 0) - bbox_b.get("y1", 0))
        return inter / (area_a + area_b - inter) if (area_a + area_b - inter) > 0 else 0.0

    def _find_containing_parent(self, item: Dict, all_items: List[Dict], current_index: int) -> Optional[Dict]:
        """找到包含item的最小父容器（在它之后的更大元素中）。
        文本块只允许被 UI 元素包含，不允许文本之间互相嵌套，防止吞文本。"""
        best_parent = None
        best_area = float('inf')

        for j in range(current_index + 1, len(all_items)):
            candidate = all_items[j]
            # 文本块之间不互相包含，避免嵌套吞噬
            if item["type"] == "text_block" and candidate["type"] == "text_block":
                continue
            if self._is_inside(item["bbox"], candidate["bbox"]):
                candidate_area = self._get_area(candidate["bbox"])
                if candidate_area < best_area:
                    best_area = candidate_area
                    best_parent = candidate

        return best_parent

    def _has_parent(self, item: Dict, all_items: List[Dict]) -> bool:
        """检查item是否有父容器"""
        for other in all_items:
            if other is item:
                continue
            if self._is_inside(item["bbox"], other["bbox"]):
                return True
        return False

    def _get_area(self, bbox: Dict) -> float:
        """计算矩形面积"""
        width = bbox.get("x2", 0) - bbox.get("x1", 0)
        height = bbox.get("y2", 0) - bbox.get("y1", 0)
        return width * height

    def _calculate_intersection_ratio(self, x1: float, y1: float, x2: float, y2: float,
                                      tx1: float, ty1: float, tx2: float, ty2: float) -> float:
        """计算相交面积占inner框面积的比例（用于判断包含关系）"""
        inter_x1 = max(x1, tx1)
        inter_y1 = max(y1, ty1)
        inter_x2 = min(x2, tx2)
        inter_y2 = min(y2, ty2)

        inter_width = max(0, inter_x2 - inter_x1)
        inter_height = max(0, inter_y2 - inter_y1)
        inter_area = inter_width * inter_height

        # 计算inner框的面积（第一个框作为inner）
        inner_area = (x2 - x1) * (y2 - y1)

        if inner_area == 0:
            return 0

        # 返回相交面积占inner框面积的比例
        return inter_area / inner_area

    def _is_inside(self, inner: Dict, outer: Dict) -> bool:
        """检查inner是否完全在outer内部"""
        in_x1 = inner.get("x1", 0)
        in_y1 = inner.get("y1", 0)
        in_x2 = inner.get("x2", 0)
        in_y2 = inner.get("y2", 0)

        out_x1 = outer.get("x1", 0)
        out_y1 = outer.get("y1", 0)
        out_x2 = outer.get("x2", 0)
        out_y2 = outer.get("y2", 0)

        # 使用_calculate_intersection_ratio计算inner有多少比例在outer内
        overlap_ratio = self._calculate_intersection_ratio(in_x1, in_y1, in_x2, in_y2,
                                                           out_x1, out_y1, out_x2, out_y2)

        # inner至少80%的面积在outer内，视为包含
        if overlap_ratio >= 0.8:
            return True

        # 兜底：使用相对margin容差
        width = max(out_x2 - out_x1, 1)
        height = max(out_y2 - out_y1, 1)
        margin_x = width * 0.05  # 5%的宽度容差
        margin_y = height * 0.05  # 5%的高度容差

        return (in_x1 >= out_x1 - margin_x and
                in_y1 >= out_y1 - margin_y and
                in_x2 <= out_x2 + margin_x and
                in_y2 <= out_y2 + margin_y)


def main():
    """测试函数"""
    import sys

    yolo_model = "/Users/baojunw/Desktop/毕设/mobile_vision/models/yolo/runs/detect/train4/weights/best.pt"
    test_image = "/Users/baojunw/Desktop/毕设/mobile_vision/test_images/test1.png"
    ocr_engine = "easyocr"

    if len(sys.argv) > 1:
        test_image = sys.argv[1]
    if len(sys.argv) > 2:
        yolo_model = sys.argv[2]
    if len(sys.argv) > 3:
        ocr_engine = sys.argv[3]

    print(f"初始化页面元素识别器...")
    print(f"模型路径: {yolo_model}")
    print(f"测试图片: {test_image}")
    print(f"OCR引擎: {ocr_engine}")

    recognizer = PageElementRecognizer(
        yolo_model_path=yolo_model,
        use_gpu=False,
        languages=['en', 'ch_sim'],
        ocr_engine=ocr_engine
    )

    print(f"\n开始识别...")
    page_info = recognizer.recognize_from_image(test_image, conf_threshold=0.25)

    print(f"\n{'=' * 60}")
    print(f"页面识别结果")
    print(f"{'=' * 60}")
    print(f"页面ID: {page_info.page_id}")
    print(f"图片尺寸: {page_info.image_width}x{page_info.image_height}")
    print(f"UI元素数量: {page_info.total_elements}")
    print(f"文字数量: {page_info.total_texts}")

    print(f"\n--- UI元素 (YOLO) ---")
    for elem in page_info.elements[:10]:
        bbox = elem['bbox']
        print(f"  [{elem['element_id']}] {elem['class_name']}")
        print(f"      位置: ({bbox['x1']:.1f}, {bbox['y1']:.1f}) -> ({bbox['x2']:.1f}, {bbox['y2']:.1f})")
        print(f"      中心: ({((bbox['x1'] + bbox['x2']) / 2):.1f}, {((bbox['y1'] + bbox['y2']) / 2):.1f})")
        print(f"      置信度: {elem['confidence']:.2f}")

    print(f"\n--- 文字 ({ocr_engine.upper()}) ---")
    for text in page_info.texts[:20]:
        bbox = text['bbox']
        print(f"  [{text['text_id']}] \"{text['text']}\"")
        print(f"      位置: ({bbox['x1']:.1f}, {bbox['y1']:.1f}) -> ({bbox['x2']:.1f}, {bbox['y2']:.1f})")
        print(f"      中心: ({((bbox['x1'] + bbox['x2']) / 2):.1f}, {((bbox['y1'] + bbox['y2']) / 2):.1f})")
        print(f"      语言: {text['language']}, 置信度: {text['confidence']:.2f}")

    print(f"\n--- 合并结果 (JSON) ---")
    combined = recognizer.get_combined_elements(page_info)
    print(json.dumps(combined, ensure_ascii=False, indent=2))

    output_json = "/Users/baojunw/Desktop/毕设/mobile_vision/test_images/page_info.json"
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    recognizer.save_json(page_info, output_json)

    return page_info


if __name__ == "__main__":
    main()
