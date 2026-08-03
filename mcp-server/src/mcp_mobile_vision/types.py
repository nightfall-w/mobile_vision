"""MCP Mobile Vision - 核心类型定义"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class InterfaceType(str, Enum):
    ANDROID = "android"
    WEB = "web"
    IMAGE = "image"


class PageContext:
    """页面上下文 - 双通道识别结果"""
    def __init__(
        self,
        page_id: str,
        image_width: int,
        image_height: int,
        elements: List[Dict],
        texts: List[Dict],
        structured_elements: List[Dict] = None,
        source: str = "visual",
    ):
        self.page_id = page_id
        self.image_width = image_width
        self.image_height = image_height
        self.elements = elements
        self.texts = texts
        self.structured_elements = structured_elements or []
        self.source = source


@dataclass
class BoundingBox:
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
    element_id: str
    type: str
    bbox: BoundingBox
    confidence: float
    children: List["UIElement"] = field(default_factory=list)


@dataclass
class TextElement:
    text_id: str
    text: str
    bbox: BoundingBox
    confidence: float
    language: str = ""
    color: str = "unknown"
    color_brightness: float = 0.0


@dataclass
class PageInfo:
    page_id: str
    image_width: int
    image_height: int
    elements: List[Dict]
    texts: List[Dict]
    structured_elements: List[Dict] = field(default_factory=list)