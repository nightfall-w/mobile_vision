"""MCP Mobile Vision 测试脚本

用法:
    # 快速检查环境（不需要设备）
    python -m mcp_mobile_vision.test_tools --check

    # 完整功能测试（需要连接 Android 设备）
    python -m mcp_mobile_vision.test_tools
"""

import sys
import os
import json
import subprocess
import argparse
import asyncio
from pathlib import Path


# ── 环境检查 ──────────────────────────────────────────────────────────

def check_environment():
    """检查环境配置（不需要设备）"""
    passed = 0
    failed = 0

    print("=" * 50)
    print("📋 环境检查")
    print("=" * 50)

    # 1. 模块导入
    try:
        from mcp_mobile_vision.adb import AndroidInterface
        print(f"  ✅ mcp_mobile_vision.adb")
        passed += 1
    except Exception as e:
        print(f"  ❌ {e}")
        failed += 1

    try:
        from mcp_mobile_vision.recognizer import PageElementRecognizer
        print(f"  ✅ mcp_mobile_vision.recognizer")
        passed += 1
    except Exception as e:
        print(f"  ❌ {e}")
        failed += 1

    try:
        from fastmcp import FastMCP
        print(f"  ✅ fastmcp")
        passed += 1
    except Exception as e:
        print(f"  ❌ {e}")
        failed += 1

    try:
        from mcp_mobile_vision.config import OCR_ENGINE
        from mcp_mobile_vision.page_builder import build_page_tree
        print(f"  ✅ mcp_mobile_vision 内部模块")
        print(f"  ✅ OCR 引擎: {OCR_ENGINE}")
        passed += 1
    except Exception as e:
        print(f"  ❌ {e}")
        failed += 1

    # 2. ADB 检查
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
        devices = [
            line.split("\t")[0]
            for line in result.stdout.split("\n")
            if line.strip() and "\t" in line
        ]
        if devices:
            print(f"  ✅ ADB 设备: {len(devices)} 个: {devices}")
        else:
            print(f"  ⚠️  ADB 正常，但未发现设备")
        passed += 1
    except FileNotFoundError:
        print(f"  ❌ adb 命令未找到")
        failed += 1
    except Exception as e:
        print(f"  ❌ ADB 检查失败: {e}")
        failed += 1

    # 3. YOLO 模型检查
    model_path = os.environ.get("MV_YOLO_MODEL_PATH", "")
    if model_path and os.path.exists(model_path):
        print(f"  ✅ YOLO 模型: {model_path}")
    else:
        print(f"  ⚠️  MV_YOLO_MODEL_PATH 未设置或文件不存在（无模型时仅使用 DOM 通道）")

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


# ── 功能测试 ──────────────────────────────────────────────────────────

async def test_tools():
    """测试工具函数（需要 Android 设备）"""
    from mcp_mobile_vision.tools.device import list_devices, get_device_info
    from mcp_mobile_vision.tools.page import handle_screenshot, handle_recognize_page
    from mcp_mobile_vision.tools.action import handle_click, handle_press_back
    from mcp_mobile_vision.session import session

    print("=" * 50)
    print("📱 功能测试（需要 Android 设备）")
    print("=" * 50)

    # 1. 设备列表
    print("\n1️⃣  list_devices")
    devices = list_devices()
    print(f"   返回: {devices}")
    if not devices:
        print("   ❌ 没有设备，请连接 Android 设备")
        return False
    device_id = devices[0]["device_id"]
    print(f"   使用设备: {device_id}")

    # 2. 连接设备
    print("\n2️⃣  connect_device")
    session.connect(device_id)
    print(f"   已连接: {session.is_connected}")

    # 3. 设备信息
    print("\n3️⃣  get_device_info")
    dev_info = get_device_info()
    print(f"   分辨率: {dev_info['resolution']}")

    # 4. 截图
    print("\n4️⃣  screenshot")
    path = await handle_screenshot()
    print(f"   截图路径: {path}")
    print(f"   文件存在: {os.path.exists(path)}")

    # 5. 页面识别
    print("\n5️⃣  recognize_page")
    try:
        page = await handle_recognize_page()
        print(f"   页面尺寸: {page['page_width']}x{page['page_height']}")
        print(f"   识别通道: {page['dom_source']}")
        print(f"   元素数量: {len(page['elements'])}")
        if page['elements']:
            print(f"   首个元素: {page['elements'][0]}")
    except Exception as e:
        print(f"   识别异常: {e}")

    # 6. 点击
    print("\n6️⃣  click(100, 500)")
    result = await handle_click(100, 500)
    print(f"   结果: {result}")

    # 7. 返回键
    print("\n7️⃣  press_back")
    result = await handle_press_back()
    print(f"   结果: {result}")

    # 8. 带标记截图
    print("\n8️⃣  screenshot with mark")
    path = await handle_screenshot(mark=True, x=100, y=500)
    print(f"   带标记截图: {path}")

    await session.disconnect()

    print("\n" + "=" * 50)
    print("✅ 所有测试完成")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Mobile Vision 测试")
    parser.add_argument("--check", action="store_true", help="仅检查环境（不需要设备）")
    args = parser.parse_args()

    if args.check:
        ok = check_environment()
        sys.exit(0 if ok else 1)
    else:
        ok = check_environment()
        if ok:
            print()
            asyncio.run(test_tools())
        else:
            print("\n❌ 环境检查未通过，请先修复后再测试功能")
            sys.exit(1)