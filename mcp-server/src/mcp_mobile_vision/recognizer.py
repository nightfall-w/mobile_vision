"""MCP Mobile Vision - YOLO + OCR 页面识别引擎

从 automation_agent/page_recognizer.py 提取，去除了项目特定依赖。
"""

import json
import math
import os
import time
from dataclasses import asdict
from typing import Dict, List, Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from mcp_mobile_vision.types import (
    BoundingBox,
    PageInfo,
    TextElement,
    UIElement,
)


class PageElementRecognizer:
    """YOLO + OCR 页面元素识别器"""

    YOLO_CLASS_NAMES = {
        0: "按钮",
        1: "输入框",
        2: "图片",
        3: "图标",
        4: "文字",
        5: "列表",
        6: "开关",
        7: "复选框",
        8: "单选按钮",
        9: "弹窗",
        10: "关闭按钮",
        11: "关闭小程序按钮",
        12: "搜索Icon",
        13: "活动弹窗",
        14: "底部导航",
        15: "返回按钮",
        16: "Tab",
        17: "卡片",
        18: "头像",
        19: "悬浮按钮",
        20: "搜索框",
        21: "广告",
        22: "输入框Icon",
        23: "二维码",
        24: "展开按钮",
        25: "收起按钮",
        26: "客服Icon",
        27: "购物车Icon",
        28: "分享Icon",
        29: "更多Icon",
        30: "删除Icon",
        31: "关注按钮",
        32: "点赞Icon",
        33: "位置Icon",
        34: "电话Icon",
        35: "微信Icon",
        36: "朋友圈Icon",
        37: "链接Icon",
        38: "菜单Icon",
        39: "通知Icon",
        40: "设置Icon",
        41: "用户Icon",
        42: "播放Icon",
        43: "暂停Icon",
        44: "刷新Icon",
        45: "加载Icon",
        46: "错误Icon",
        47: "成功Icon",
        48: "警告Icon",
        49: "信息Icon",
        50: "帮助Icon",
        51: "搜索Icon",
        52: "关闭Icon",
        53: "添加Icon",
        54: "减少Icon",
        55: "确认Icon",
        56: "取消Icon",
        57: "编辑Icon",
        58: "删除Icon",
        59: "更多Icon",
    }

    # 颜色映射 (BGR)
    _COLOR_MAP = {
        (0, 0, 255): "red",
        (0, 255, 0): "green",
        (255, 0, 0): "blue",
        (255, 255, 255): "white",
        (0, 0, 0): "black",
        (0, 128, 128): "gray",
        (0, 165, 255): "orange",
        (128, 0, 128): "purple",
        (0, 255, 255): "yellow",
    }

    def __init__(
        self,
        yolo_model_path: str,
        use_gpu: bool = False,
        ocr_engine: str = "rapidocr",
        class_names_from_db: List = None,
    ):
        self.yolo_model_path = yolo_model_path
        self.use_gpu = use_gpu
        self.ocr_engine = ocr_engine
        self.class_names_from_db = class_names_from_db or []

        self._yolo = None
        self._ocr = None
        self._font = None

        self.initialize()

    def initialize(self):
        """初始化 YOLO 和 OCR 引擎"""
        self._init_yolo()
        self._init_ocr()
        self._font = self._get_chinese_font()

    def _init_yolo(self):
        """初始化 YOLO 模型"""
        if not self.yolo_model_path or not os.path.exists(self.yolo_model_path):
            raise FileNotFoundError(f"YOLO 模型文件不存在: {self.yolo_model_path}")

        from ultralytics import YOLO
        self._yolo = YOLO(self.yolo_model_path)
        _ = self._yolo.model  # 触发模型加载

        # 如果数据库中有自定义类别，使用自定义类别
        if self.class_names_from_db:
            class_num = len(self.class_names_from_db)
            self._yolo.model.names = {
                i: self.class_names_from_db[i] for i in range(class_num)
            }
        else:
            self._yolo.model.names = self.YOLO_CLASS_NAMES

    def _init_ocr(self):
        """初始化 OCR 引擎"""
        if self.ocr_engine == "easyocr":
            self._init_easyocr()
        else:
            self._init_rapidocr()

    def _init_easyocr(self):
        """初始化 EasyOCR"""
        import easyocr
        self._ocr = easyocr.Reader(["en", "ch_sim"], verbose=False)

    def _init_rapidocr(self):
        """初始化 RapidOCR"""
        from rapidocr_onnxruntime import RapidOCR
        self._ocr = RapidOCR()

    def recognize_from_image(
        self, image_path: str, conf_threshold: float = 0.25
    ) -> PageInfo:
        """识别图片中的页面元素

        Args:
            image_path: 图片路径
            conf_threshold: YOLO 置信度阈值

        Returns:
            PageInfo: 识别结果
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        # 读取图片
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")

        height, width = img.shape[:2]

        # YOLO 检测
        elements = self._recognize_elements(image_path, conf_threshold)

        # OCR 识别
        texts = self._recognize_texts(img, image_path)

        # 整合结构化元素
        structured = self.integrate_elements_and_texts(elements, texts)

        return PageInfo(
            page_id=f"page_{int(time.time() * 1000)}",
            image_width=width,
            image_height=height,
            elements=elements,
            texts=texts,
            structured_elements=structured,
        )

    def _recognize_elements(
        self, image_path: str, conf_threshold: float
    ) -> List[Dict]:
        """YOLO 检测页面元素"""
        if not self._yolo:
            return []

        results = self._yolo(image_path, conf=conf_threshold, verbose=False)
        elements = []

        for result in results:
            if result.boxes is None:
                continue

            for i, box in enumerate(result.boxes):
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])

                class_name = self._yolo.model.names.get(class_id, f"class_{class_id}")

                element = {
                    "element_id": f"elem_{i}",
                    "type": class_name,
                    "bbox": [x1, y1, x2, y2],
                    "bbox_center": {
                        "center_x": (x1 + x2) // 2,
                        "center_y": (y1 + y2) // 2,
                    },
                    "confidence": round(confidence, 2),
                }
                elements.append(element)

        return elements

    def draw_annotated_image(self, image_path: str, output_path: str):
        """在图片上绘制 YOLO 检测框和标签"""
        if not self._yolo:
            return

        results = self._yolo(image_path, verbose=False)
        img = cv2.imread(image_path)

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = self._yolo.model.names.get(class_id, "unknown")

                color = self._get_color(class_id)
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

                label = f"{class_name} {confidence:.2f}"
                (label_w, label_h), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
                )
                cv2.rectangle(
                    img, (x1, y1 - label_h - 5), (x1 + label_w, y1), color, -1
                )
                cv2.putText(
                    img,
                    label,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    2,
                )

        cv2.imwrite(output_path, img)

    def _get_chinese_font(self, font_size: int = 22):
        """获取中文字体"""
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    return ImageFont.truetype(fp, font_size, encoding="utf-8")
                except Exception:
                    continue
        return None

    def _get_color(self, class_id: int) -> tuple:
        """根据类别 ID 返回 BGR 颜色"""
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
            (255, 0, 255), (0, 255, 255), (128, 0, 0), (0, 128, 0),
            (0, 0, 128), (128, 128, 0), (128, 0, 128), (0, 128, 128),
        ]
        return colors[class_id % len(colors)]

    def _recognize_texts(
        self, image_array: np.ndarray, image_path: str
    ) -> List[Dict]:
        """OCR 识别文字"""
        if self.ocr_engine == "easyocr":
            return self._recognize_texts_easyocr(image_array, image_path)
        return self._recognize_texts_rapidocr(image_array, image_path)

    def _recognize_texts_easyocr(
        self, image_array: np.ndarray, image_path: str
    ) -> List[Dict]:
        """EasyOCR 识别"""
        if not self._ocr:
            return []

        results = self._ocr.readtext(image_array)
        texts = []

        for idx, (bbox_coords, text, confidence) in enumerate(results):
            if not text or not text.strip():
                continue
            if float(confidence) < 0.1:
                continue

            x_coords = [p[0] for p in bbox_coords]
            y_coords = [p[1] for p in bbox_coords]
            bbox = BoundingBox(
                x1=float(min(x_coords)), y1=float(min(y_coords)),
                x2=float(max(x_coords)), y2=float(max(y_coords)),
            )

            text_element = TextElement(
                text_id=f"text_{idx}",
                text=text.strip(),
                bbox=bbox,
                confidence=float(confidence),
                language="ch_sim" if any('一' <= c <= '鿿' for c in text) else "en",
                color="unknown",
                color_brightness=0.0,
            )
            text_dict = asdict(text_element)
            text_dict["bbox"]["center_x"] = bbox.center_x
            text_dict["bbox"]["center_y"] = bbox.center_y
            texts.append(text_dict)

        return texts

    def _recognize_texts_rapidocr(
        self, image_array: np.ndarray, image_path: str
    ) -> List[Dict]:
        """RapidOCR 识别"""
        if not self._ocr:
            return []

        result, _ = self._ocr(image_array, text_score=0.1)
        texts = []

        if result:
            for idx, line in enumerate(result):
                bbox_coords, text, score = line
                if not text or not text.strip():
                    continue

                x_coords = [p[0] for p in bbox_coords]
                y_coords = [p[1] for p in bbox_coords]
                bbox = BoundingBox(
                    x1=float(min(x_coords)), y1=float(min(y_coords)),
                    x2=float(max(x_coords)), y2=float(max(y_coords)),
                )

                text_element = TextElement(
                    text_id=f"text_{idx}",
                    text=text.strip(),
                    bbox=bbox,
                    confidence=float(score),
                    language="ch_sim" if any('一' <= c <= '鿿' for c in text) else "en",
                    color="unknown",
                    color_brightness=0.0,
                )
                text_dict = asdict(text_element)
                text_dict["bbox"]["center_x"] = bbox.center_x
                text_dict["bbox"]["center_y"] = bbox.center_y
                texts.append(text_dict)

        return texts

    def integrate_elements_and_texts(
        self, elements: List[Dict], texts: List[Dict]
    ) -> List[Dict]:
        """整合 YOLO 元素和 OCR 文字"""
        integrated = []

        for elem in elements:
            bbox = elem.get("bbox", [])
            if len(bbox) < 4:
                continue

            elem_center_x = (bbox[0] + bbox[2]) / 2
            elem_center_y = (bbox[1] + bbox[3]) / 2

            # 找到属于该元素的文字
            child_texts = []
            for text in texts:
                tb = text.get("bbox", {})
                tx = tb.get("center_x", tb.get("x", 0))
                ty = tb.get("center_y", tb.get("y", 0))
                if bbox[0] <= tx <= bbox[2] and bbox[1] <= ty <= bbox[3]:
                    child_texts.append(text.get("text", ""))

            entry = {
                "id": elem.get("element_id", ""),
                "type": elem.get("type", "unknown"),
                "bbox": bbox,
                "bbox_center": {
                    "x": int(elem_center_x),
                    "y": int(elem_center_y),
                },
                "confidence": elem.get("confidence", 0.0),
            }

            if child_texts:
                entry["text"] = " ".join(filter(None, child_texts))

            integrated.append(entry)

        # 添加未匹配的文字
        if not integrated:
            for text in texts:
                entry = {
                    "id": text.get("text_id", ""),
                    "type": "text_block",
                    "bbox": [
                        int(text["bbox"]["x1"]),
                        int(text["bbox"]["y1"]),
                        int(text["bbox"]["x2"]),
                        int(text["bbox"]["y2"]),
                    ],
                    "bbox_center": {
                        "x": int(text["bbox"]["center_x"]),
                        "y": int(text["bbox"]["center_y"]),
                    },
                    "confidence": text.get("confidence", 0.0),
                    "text": text.get("text", ""),
                }
                integrated.append(entry)

        return integrated