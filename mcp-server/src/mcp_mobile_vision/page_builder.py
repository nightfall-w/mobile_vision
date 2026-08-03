"""MCP Mobile Vision - 结构化页面树构建"""

from typing import Optional

from mcp_mobile_vision.types import PageContext


def build_page_tree(context: PageContext) -> dict:
    """将 PageContext 转换为统一的 PageTree 结构"""
    elements = []

    for elem in context.structured_elements:
        entry = _convert_element(elem)
        if entry:
            elements.append(entry)

    if not elements:
        for elem in context.elements:
            entry = _convert_element(elem)
            if entry:
                elements.append(entry)

    if not elements:
        for text in context.texts:
            tb = text.get("bbox", {})
            entry = {
                "id": text.get("text_id", ""),
                "type": "text_block",
                "bbox": [
                    int(tb.get("x1", 0)),
                    int(tb.get("y1", 0)),
                    int(tb.get("x2", 0)),
                    int(tb.get("y2", 0)),
                ],
                "bbox_center": {
                    "x": int(tb.get("center_x", 0)),
                    "y": int(tb.get("center_y", 0)),
                },
                "confidence": text.get("confidence", 0),
                "text": text.get("text", ""),
                "color": text.get("color", "unknown"),
                "color_brightness": text.get("color_brightness", 0),
            }
            elements.append(entry)

    return {
        "page_width": context.image_width,
        "page_height": context.image_height,
        "dom_source": context.source,
        "elements": elements,
    }


def _convert_element(elem: dict) -> Optional[dict]:
    """将单个元素转为统一格式"""
    if not elem:
        return None

    bbox = elem.get("bbox")
    if not bbox:
        return None

    center = elem.get("bbox_center", {})
    if not center or not isinstance(center, dict):
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            center = {
                "x": int((bbox[0] + bbox[2]) / 2),
                "y": int((bbox[1] + bbox[3]) / 2),
            }

    cx = int(center.get("x", center.get("center_x", 0)))
    cy = int(center.get("y", center.get("center_y", 0)))

    entry = {
        "id": elem.get("id", elem.get("element_id", "")),
        "type": elem.get("type", "unknown"),
        "bbox": [int(b) for b in bbox] if isinstance(bbox, (list, tuple)) else bbox,
        "bbox_center": {"x": cx, "y": cy},
        "confidence": elem.get("confidence", 0.0),
    }

    if elem.get("text"):
        entry["text"] = elem["text"]
    if elem.get("color"):
        entry["color"] = elem["color"]
    if "color_brightness" in elem:
        entry["color_brightness"] = elem["color_brightness"]
    if elem.get("clickable"):
        entry["clickable"] = True
    if elem.get("enabled") is False:
        entry["enabled"] = False

    children = elem.get("children", [])
    if children:
        entry["children"] = [
            c for c in (_convert_element(child) for child in children) if c
        ]

    return entry