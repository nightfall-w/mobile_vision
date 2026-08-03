# MCP Mobile Vision

将手机 UI 自动化能力（ADB + YOLO + OCR）暴露为 MCP 工具，供 Claude Code / Codex 等 AI 客户端调用。

## 安装

### 方式一：pip 安装

```bash
pip install mcp-mobile-vision
```

### 方式二：源码安装

```bash
cd mcp-server
pip install -e .
```

## 前置条件

- Python 3.10+
- ADB 已安装并配置到 PATH
- Android 设备已连接（USB 或 WiFi ADB）
- YOLO 模型文件（可选，不提供时仅使用 DOM 快通道）

## 配置到 Claude Code

```bash
claude mcp add mobile-vision -- python -m mcp_mobile_vision.server
```

或手动添加到 `~/.claude.json`：

```json
{
  "mcpServers": {
    "mobile-vision": {
      "command": "python",
      "args": ["-m", "mcp_mobile_vision.server"]
    }
  }
}
```

## 配置 YOLO 模型（可选）

不配置时，`recognize_page` 将仅使用 DOM 快通道（uiautomator2）识别页面。

**方式一：在 Claude Code 中动态设置**

```
用户: "设置 YOLO 模型为 /path/to/model.pt"
工具: set_model(model_path="/path/to/model.pt")
```

**方式二：通过环境变量**

```bash
export MV_YOLO_MODEL_PATH=/path/to/model.pt
python -m mcp_mobile_vision.server
```

## 可用工具

### 设备管理
| 工具 | 说明 |
|------|------|
| `list_devices` | 列出所有已连接的 ADB 设备 |
| `connect_device` | 连接设备（有线/无线 ADB） |
| `disconnect_device` | 断开设备连接 |
| `get_device_info` | 获取设备详细信息（分辨率、型号等） |

### 页面识别
| 工具 | 说明 |
|------|------|
| `recognize_page` | **[推荐]** 双通道识别，返回结构化页面树 |
| `screenshot` | 截图，可选标记操作坐标 |

### 操作执行
| 工具 | 说明 |
|------|------|
| `click(x, y)` | 点击坐标 |
| `long_press(x, y, duration)` | 长按 |
| `swipe(x1, y1, x2, y2)` | 滑动 |
| `input_text(text)` | 输入文字 |
| `press_back` | 返回键 |
| `press_home` | Home 键 |
| `press_enter` | 回车键 |

### 模型配置
| 工具 | 说明 |
|------|------|
| `set_model` | 指定 YOLO 模型路径 |
| `get_model_info` | 获取当前模型信息 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MV_YOLO_MODEL_PATH` | `""` | YOLO 模型路径 |
| `MV_OCR_ENGINE` | `rapidocr` | OCR 引擎：`easyocr` 或 `rapidocr` |
| `MV_ADB_CMD` | `adb` | ADB 命令路径 |
| `MV_DEVICE_ID` | `""` | 默认设备地址 |
| `MV_SCREENSHOTS_DIR` | `./screenshots` | 截图存储目录 |

## 测试

```bash
python -m mcp_mobile_vision.test_tools
```