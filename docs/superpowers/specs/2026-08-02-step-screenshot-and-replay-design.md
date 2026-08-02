# 历史步骤截图查看与回放功能设计

## 1. 概述

在测试任务执行过程中和结束后，支持两种功能：
1. **历史步骤截图查看**：点击任意历史步骤，查看该步骤执行时的设备截图
2. **回放**：测试任务结束后，以 3X 倍速回放整个执行过程的截图

## 2. 数据流变更

### 2.1 Step 数据模型扩展

**文件：** `app/task_monitor/models.py` → `Step` 数据类

新增字段：`screenshot_path: Optional[str] = None`

存储该步骤执行时对应的截图文件名（相对于 `{SCREENSHOTS_DIR}/{job_id}/` 目录，仅文件名，如 `"1712345678000.png"`）。

### 2.2 截图关联时机

**文件：** `services/test_task_consumer.py` → `on_state_update` 回调

在 `step_executing` 分支中，通过闭包捕获 `interface.last_screenshot_path`：

```python
elif state_type == "step_executing":
    screenshot_filename = None
    if hasattr(interface, "last_screenshot_path") and interface.last_screenshot_path:
        screenshot_filename = os.path.basename(interface.last_screenshot_path)
    
    step = Step(
        step_number=data.get("step_number", 0),
        action=data.get("action", ""),
        description=data.get("description", ""),
        x=data.get("x"),
        y=data.get("y"),
        text=data.get("text"),
        direction=data.get("direction"),
        assertion=data.get("assertion"),
        result="执行中...",
        success=True,
        screenshot_path=screenshot_filename,  # 新增
    )
```

`interface.last_screenshot_path` 由 `update_screenshot` 异步循环（每 2 秒）和 agent 的 `_perceive()` 方法在截图时设置。

### 2.3 截图文件存储

**现状（无需改动）：** 截图已保存为 `{SCREENSHOTS_DIR}/{job_id}/{timestamp_ms}.png`，文件名即为毫秒时间戳。

## 3. 后端 API 变更

### 3.1 新增：获取指定截图文件

**路由：** `GET /api/v1/testtask/job/{job_id}/screenshot/file/{filename}`

**文件：** `api/v1/routes/testtask.py`

从 `{SCREENSHOTS_DIR}/{job_id}/{filename}` 读取文件，返回 base64 编码的图片数据。

```json
{
  "code": 0,
  "data": {
    "screenshot_base64": "iVBORw0KGgo..."
  }
}
```

### 3.2 新增：获取截图文件列表

**路由：** `GET /api/v1/testtask/job/{job_id}/screenshots/list`

**文件：** `api/v1/routes/testtask.py`

列出 `{SCREENSHOTS_DIR}/{job_id}/` 目录下所有 `.png` 文件，按修改时间排序。

```json
{
  "code": 0,
  "data": {
    "screenshots": [
      {"filename": "1712345678000.png", "timestamp": 1712345678000},
      {"filename": "1712345680000.png", "timestamp": 1712345680000}
    ],
    "total": 42
  }
}
```

## 4. 前端变更

### 4.1 步骤点击查看截图

**文件：** `mobile_vision_web/src/views/JobMonitor.vue`

#### 状态管理
新增响应式变量：
- `historyScreenshot` (`string`) — 当前查看的历史步骤截图 base64
- `viewingHistoryStep` (`boolean`) — 是否在查看历史步骤截图
- `viewingStepNumber` (`number | null`) — 当前查看的步骤编号

#### 步骤点击处理
- 步骤列表中的每个 `.step-item` 变为可点击
- 点击后调用 `fetchStepScreenshot(filename)` 获取该步骤的截图
- 设置 `historyScreenshot` 和 `viewingHistoryStep`

#### 截图区域显示逻辑
- `viewingHistoryStep = true` 时，显示 `historyScreenshot` 替代实时截图
- 截图上方显示指示条："📋 历史截图 - 步骤 N" + "返回实时" 按钮
- 点击"返回实时"恢复为实时截图模式

#### 截图加载状态
- 加载历史截图时显示加载动画
- 如果步骤没有关联截图，显示"暂无截图"占位

### 4.2 回放功能

**文件：** `mobile_vision_web/src/views/JobMonitor.vue`

#### 回放按钮
- Header 右侧添加"回放"按钮（仅任务结束后显示：`completed`/`failed`/`aborted`）
- 与"放弃任务"按钮并排放置
- 点击后开始回放，按钮变为"暂停/继续"切换

#### 回放控制
- 调用 `GET /api/v1/testtask/job/{job_id}/screenshots/list` 获取所有截图列表
- 按 667ms 间隔（原始 2s / 3X 倍速）依次展示截图
- 循环播放，直到用户暂停或到达最后一张截图
- 底部显示进度条（`el-slider`），显示当前回放位置
- 暂停时进度条可拖动选择回放位置

#### 截图区域显示
- 回放时复用左侧截图区域
- 显示指示条："🎬 回放中 N/M" + 进度条
- 回放结束后恢复到实时截图模式

#### 回放状态管理
- `isReplaying` (`boolean`) — 是否在回放中
- `isReplayPaused` (`boolean`) — 是否暂停
- `replayScreenshots` (`Array`) — 截图文件列表
- `replayIndex` (`number`) — 当前回放到的索引
- `replayTimer` — 计时器引用

#### 回放计时器
```
间隔 = 原始间隔 / 3X 倍速
     = 2000ms / 3 ≈ 667ms
```

由于截图间隔不固定，使用固定间隔 667ms 依次播放截图列表。

### 4.3 回放与步骤高亮联动

回放时，根据当前时间戳匹配到对应的步骤进行高亮显示。每个截图文件的时间戳与步骤的 `timestamp` 字段进行匹配，找到最接近的步骤进行高亮。

## 5. 涉及文件清单

### 后端
| 文件 | 改动 |
|------|------|
| `app/task_monitor/models.py` | `Step` 数据类新增 `screenshot_path` 字段 |
| `services/test_task_consumer.py` | `on_state_update` 中 `step_executing` 分支捕获截图路径 |
| `api/v1/routes/testtask.py` | 新增两个 API 端点 |

### 前端
| 文件 | 改动 |
|------|------|
| `mobile_vision_web/src/views/JobMonitor.vue` | 步骤点击查看截图 + 回放功能 |

## 6. 边界情况

### 步骤截图
- 步骤执行时如果 `interface.last_screenshot_path` 为空（如首次截图尚未完成），`screenshot_path` 为 `None`，前端显示"暂无截图"
- 任务结束后，从 Redis/MySQL 读取的步骤数据中 `screenshot_path` 字段为空时，依然显示"暂无截图"

### 回放
- 截图目录为空时，回放按钮禁用或点后提示"无截图可回放"
- 回放过程中如果只有 1 张截图，保持显示该截图
- 回放过程中用户切换到其他页面，回放自动停止
- 回放过程中任务状态变更（理论上不会发生，因为回放仅在任务结束后可用）