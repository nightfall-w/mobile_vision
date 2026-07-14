# MobileVision

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.135+-00a473?style=for-the-badge&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue_3-3.5-4FC08D?style=for-the-badge&logo=vue.js" alt="Vue 3">
  <img src="https://img.shields.io/badge/Element_Plus-2.10-409EFF?style=for-the-badge&logo=element" alt="Element Plus">
  <img src="https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql" alt="MySQL">
  <img src="https://img.shields.io/badge/YOLOv8-ultralytics-00FFFF?style=for-the-badge&logo=ultralytics" alt="YOLOv8">
  <img src="https://img.shields.io/badge/PyTorch-2.11-EE4C2C?style=for-the-badge&logo=pytorch" alt="PyTorch">
  <img src="https://img.shields.io/badge/ADB-Android-34A853?style=for-the-badge&logo=android" alt="ADB">
</p>

<p align="center">
  <strong>YOLO 视觉识别 · 移动端 UI 自动化测试 · 智能 Agent 执行</strong>
</p>

<p align="center">
  基于视觉识别的移动端 UI 自动化测试平台，融合 YOLO 目标检测、LLM 智能体、OCR 文字识别和 ADB 设备控制，<br>
  实现从用例管理、计划编排到自动化执行、报告生成的全链路测试解决方案。
</p>

---

## 📋 目录

- [核心特性](#-核心特性)
- [技术栈](#-技术栈)
- [系统架构](#-系统架构)
- [功能模块](#-功能模块)
- [快速开始](#-快速开始)
- [API 概览](#-api-概览)
- [项目结构](#-项目结构)
- [数据库](#-数据库)
- [截图](#-截图)

---

## 🚀 核心特性

### 🤖 智能视觉识别
基于 **YOLOv8** 深度学习模型 + **双通道页面解析** 技术，实现移动端 UI 元素的精准检测与识别。支持自定义数据集标注、模型训练与部署，让自动化测试真正"看见"屏幕内容。

- **数据集管理** — 上传、标注、分割 UI 截图数据集
- **在线标注** — 内置 Web 标注工具，支持矩形框标注与标签管理；同时支持**半自动化标注**，利用已有模型对图片进行预标注，人工校验修正即可，大幅提升标注效率
- **模型训练** — 一键启动 YOLO 训练任务，实时监控训练进度
- **模型部署** — 训练完成的模型自动可用于页面元素识别
- **双通道页面解析** — 采用 **DOM 快通道 + 视觉通道** 双方案：通过 **uiautomator2** 快速 dump 页面控件树（0.3-0.8s），提取元素的类型、文本、坐标、可点击状态等结构化信息；当页面包含大量 WebView 或 DOM 信息不足时，自动切换至**视觉通道**（YOLO 目标检测 + OCR 文字识别，1-2s）进行识别。两套通道互为补充，兼顾速度与覆盖率
- **文字颜色分析** — 基于**大津法（Otsu）**自适应二值化分割，自动提取文字的 RGB 颜色与亮度信息，精确区分文字颜色（红/绿/蓝/白/黑等），帮助 LLM 理解按钮状态（如灰色禁用态）
- **半自动标注** — 利用已有 YOLO 模型对截图进行预标注，人工校验修正即可，大幅提升标注效率

### 🧠 LLM + Agent 智能执行
集成 **LLM** 作为测试执行大脑，结合视觉识别能力，Agent 可自主理解测试步骤并执行操作。

- **智能页面理解** — Agent 自动解析页面布局与 UI 元素（详见下方重点说明）
- **自然语言步骤** — 支持用自然语言描述测试操作
- **可观测思考链** — 执行过程中 Agent 实时输出**思考链 (Chain-of-Thought)**，完整记录每一步的决策依据：大模型基于当前页面数据和用例步骤"为什么选择这个操作"、预期效果与实际情况的对比。同时通过 WebSocket 实时推送**执行日志与状态变更**，用户可在监控页面上逐条追溯 Agent 的完整决策轨迹
- **动态决策步长** — Agent 在决策下一步时，智能判断当前操作场景是否会导致页面产生变化，从而动态决定输出单步或多步操作，避免不必要的截图与识别开销
- **页面结构持久化** — 每次 Agent 决策时生成的**结构化页面描述**，连同思考链日志一并持久化到 MySQL 数据库，支持后续离线分析、问题回溯与模型评估
- **双协议支持** — 兼容 **OpenAI 协议** 和 **Anthropic 协议** 两类 API 格式；国产模型如 DeepSeek、MiniMax 以及各家 Code Plan 等，均广泛支持这两种协议格式中的一种或全部，可直接接入使用
- **LLM 连接测试** — 支持在配置 LLM 凭证时一键测试连接可用性，输入 API Key、Base URL 和模型名称后即时验证，确保证件配置正确无误后再保存

> **⭐ 页面智能解析（核心）**
>
> Agent 在执行过程中，通过**双通道策略**获取当前页面的结构化描述：
> - **DOM 快通道（uiautomator2）** — 通过 uiautomator2 dump 页面控件树，0.3-0.8s 内获取完整的 XML 视图层级，提取每个元素的类型、文本、坐标、交互状态（clickable/enabled/checked 等），是最优先使用的通道
> - **视觉通道（YOLO + OCR）** — 当页面包含大量 WebView 或 DOM 信息不足时，自动切换至视觉通道：YOLO 模型识别可交互元素类型与位置，OCR 提取文字内容，大津法分析文字颜色
> - 最终融合生成 **JSON 格式的结构化页面树**，精确还原当前页面的 UI 布局结构与交互元素
>
> 这份结构化的页面描述替代了传统"截图给多模态大模型"的方式，使 Agent 能够以极低的 Token 成本准确理解页面状态，为后续操作决策提供可靠依据。

### 核心优势：结构化页面解析 vs 传统截图多模态方案

| 对比维度 | 传统方案：截图 + 多模态大模型 | 本方案：结构化页面树（DOM + YOLO + OCR） |
|---------|------------------------------|----------------------------------------|
| **模型依赖** | 必须使用**多模态大模型**（如 GPT-4V、Claude Vision），支持范围受限，成本高昂 | 仅需**文本推理大模型**，兼容 OpenAI / Anthropic / 国产模型等任意协议兼容的 LLM，选择更广、成本更低 |
| **识别精度** | 通用模型从像素中"猜测"元素，未针对目标 App 优化，坐标误差不可控 | 可针对**被测 App 进行小样本训练**，元素识别精准、坐标百分比正确，且支持自定义元素类型 |
| **可观测性与可控性** | **黑盒执行**：识别错误无法干预、无法定位根因、无法训练调优 | **完全可控**：识别过程可追溯、错误可定位、本地模型可快速迭代优化，持续改进闭环 |
| **设计目标** | 追求"**识得广**"，覆盖通用场景，但对特定 App 的精度有限 | 追求"**识得准**"，专注为被测 App 服务，在垂直场景下达到更高识别精度与可靠性 |

> **💡 可追溯的决策分析**
>
> 当执行结果不符合预期时，通过回放 Agent 的完整思考日志，可以精准定位问题根因：
> - **大模型能力不足** — 思考链显示 LLM 对页面数据的理解出现偏差或推理逻辑错误
> - **页面数据不准确** — 提供给 LLM 的结构化页面树存在元素漏检、类型误判等问题
> - **用例描述有歧义** — 自然语言步骤的表述不够清晰，导致 LLM 理解偏离原意
>
> 用户可根据思考链中的线索针对性调整模型参数、优化页面识别模型或修正用例描述，形成持续改进的闭环。

### 📱 移动端设备管理
通过 **ADB (Android Debug Bridge)** 连接并管理真实 Android 设备或模拟器。

- **设备列表** — 查看已连接的 Android 设备状态
- **屏幕投射** — 实时查看设备屏幕
- **远程控制** — 通过 Web 界面远程操作设备
- **无线连接** — 支持通过 ADB WiFi 调试模式无线连接设备，摆脱数据线束缚
- **设备重连** — 设备断连后自动通过 Android ID 匹配同设备的其他连接方式，实现无缝重连
- **队列调度** — 多 Job 按设备排队，串行执行避免冲突，完成任务后自动解锁并调度下一个任务
- **并行执行** — 支持多设备并行执行测试任务

### 📊 全链路测试管理
从用例编写到执行报告，覆盖完整测试生命周期。

- **测试用例管理** — 支持 P0-P3 优先级分级，结构化步骤编辑
- **测试计划** — 灵活编排用例，设置执行策略与设备队列
- **测试任务** — 支持定时/周期执行，实时进度跟踪
- **执行监控** — 实时查看设备截图、Agent 思考过程可视化、子任务规划与执行进度、步骤级日志，支持逐条追溯决策轨迹
- **测试报告** — 自动生成包含截图、日志、执行轨迹的详细报告

### 👥 工作空间
支持多团队协作的工作空间机制。

- **空间隔离** — 用例、计划、任务按工作空间隔离
- **角色管理** — 管理员、测试工程师、开发工程师等多级角色
- **统计概览** — 多维度数据统计，支持按日/周/月/季度筛选
- **成员管理** — 灵活的空间成员加入与权限控制

---

## 🛠 技术栈

### 后端

| 类别 | 技术 |
|------|------|
| **框架** | FastAPI 0.135+ |
| **ORM** | SQLAlchemy 2.0 (async + sync) |
| **数据库** | MySQL 8.0 (PyMySQL / aiomysql) |
| **任务队列** | FunBoost (Redis Ack-able Queue) |
| **缓存** | Redis |
| **认证** | JWT (python-jose) + 双 Token 机制 |
| **LLM SDK** | LiteLLM (多模型统一接口) |
| **OCR** | EasyOCR / RapidOCR（双引擎可选） |
| **页面解析** | uiautomator2（DOM 快通道） |
| **WebSocket** | 实时日志推送、状态同步、截图推送 |

### 前端

| 类别 | 技术 |
|------|------|
| **框架** | Vue 3 (Composition API) |
| **UI 库** | Element Plus 2.10 |
| **构建工具** | Vite 7 |
| **路由** | Vue Router 4 |
| **图表** | ECharts 6 |
| **样式** | Tailwind CSS 3 |

### AI / 自动化

| 类别 | 技术 |
|------|------|
| **目标检测** | YOLOv8 (Ultralytics) |
| **深度学习** | PyTorch 2.11 |
| **页面解析** | uiautomator2（DOM 快通道）+ EasyOCR / RapidOCR |
| **移动端控制** | ADB (Android Debug Bridge) |
| **WebSocket** | 实时日志推送与任务监控 |
| **WebSocket** | 实时日志推送与任务监控 |

---

## 🏗 系统架构
![架构图.png](docs/%E6%9E%B6%E6%9E%84%E5%9B%BE.png)

### 执行流程
![执行流程图.png](docs/%E6%89%A7%E8%A1%8C%E6%B5%81%E7%A8%8B%E5%9B%BE.png)
---

## 📦 功能模块

### 测试管理

| 模块 | 功能 |
|------|------|
| **测试用例** | 用例 CRUD、优先级 (P0-P3)、步骤编辑器、标签分类 |
| **测试计划** | 计划编排、用例关联、执行策略、设备队列分配 |
| **测试任务** | 定时/周期执行、实时进度、执行日志、任务重试 |
| **执行监控** | WebSocket 实时推送、Agent 思考过程可视化、截图回放 |
| **测试报告** | 自动生成 HTML 报告、执行轨迹、失败截图、日志归档 |

### YOLO 视觉

| 模块 | 功能 |
|------|------|
| **数据集管理** | 图片上传、COCO/YOLO 格式标注、自动数据集分割 |
| **在线标注** | 矩形框标注、标签管理、标注进度追踪 |
| **模型训练** | 超参数配置、一键训练、训练曲线可视化、早停机制 |
| **模型部署** | 训练完成自动注册、推理服务、页面元素实时检测 |

### 设备与集成

| 模块 | 功能 |
|------|------|
| **设备管理** | ADB 设备发现、状态监控、屏幕投射、无线 ADB 连接、远程触控 |
| **LLM 配置** | 多模型接入（OpenAI/Anthropic 双协议）、国产模型（DeepSeek/MiniMax 等）兼容、API Key 管理、模型参数配置 |
| **自动化 Agent** | 视觉引导的 UI 操作、页面结构化解析、动态步长决策、异常处理与恢复 |

### 工作空间

| 模块 | 功能 |
|------|------|
| **空间管理** | 创建/编辑/删除工作空间、管理员配置 |
| **成员角色** | 管理员/测试工程师/开发工程师/产品/项目经理等多级角色、权限控制 |
| **数据统计** | 用例/计划/执行多维统计、趋势图表、周期筛选 |

---

## ⚡ 快速开始

### 前置条件

- Python 3.10+、Node.js 20+、MySQL 8.0+、ADB
- Redis（可选，用于 FunBoost 任务队列）

### 快速启动

```bash
# 1. 克隆并安装后端依赖
git clone https://github.com/yourusername/mobile_vision.git
cd mobile_vision
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. 配置环境变量并初始化数据库
cp .env.example .env
# 编辑 .env 填写数据库连接信息
mysql -u root -p mobile_vision < scripts/init_database.sql

# 3. 启动后端服务（开发模式）
python main.py

# 4. 启动前端（新终端）
cd mobile_vision_web
npm install && npm run dev
```

> 完整生产部署指南（Nginx 配置、进程管理、无线 ADB 等）请参阅 [docs/deployment.md](docs/deployment.md)。

---

## 📖 API 概览

| 分组 | 路径 | 说明 |
|------|------|------|
| **认证** | `/api/v1/auth/*` | 登录、注册、Token 刷新 |
| **工作空间** | `/api/v1/workspace/*` | 空间 CRUD、成员管理、角色管理、统计 |
| **测试用例** | `/api/v1/testcase/*` | 用例 CRUD、步骤管理 |
| **测试计划** | `/api/v1/testplan/*` | 计划 CRUD、用例关联 |
| **测试任务** | `/api/v1/testtask/*` | 任务 CRUD、执行控制、进度查询 |
| **设备管理** | `/api/v1/device/*` | 设备列表、状态、屏幕投射 |
| **LLM 配置** | `/api/v1/llm/*` | 模型配置、API Key 管理 |
| **YOLO 数据集** | `/api/v1/dataset/*` | 数据集 CRUD、文件上传 |
| **YOLO 标注** | `/api/v1/annotation/*` | 标注管理、图片标注 |
| **YOLO 训练** | `/api/v1/train/*` | 训练任务管理、模型管理 |
| **实时监控** | `/ws/*` | WebSocket 日志推送 |

---

## 📁 项目结构

```
mobile_vision/
├── main.py                          # 后端入口，FastAPI 应用
├── requirements.txt                 # Python 依赖
├── funboost_cli_user.py             # FunBoost 消费者 CLI 入口
├── funboost_config.py               # FunBoost 任务队列配置
├── nb_log_config.py                 # 日志框架配置
├── api/                             # API 路由层
│   └── v1/
│       ├── routes/                  # 各模块路由
│       │   ├── user.py              # 用户认证
│       │   ├── workspace.py         # 工作空间
│       │   ├── testcase.py          # 测试用例
│       │   ├── testplan.py          # 测试计划
│       │   ├── testtask.py          # 测试任务
│       │   ├── device.py            # 设备管理
│       │   ├── llm.py               # LLM 配置
│       │   ├── dataset.py           # YOLO 数据集
│       │   ├── annotation.py        # YOLO 标注
│       │   ├── train.py             # YOLO 训练
│       │   ├── model.py             # YOLO 模型
│       │   └── monitor.py           # 执行监控
│       └── __init__.py
├── app/                             # 业务逻辑层
│   ├── user/                        # 用户模块
│   ├── workspace/                   # 工作空间模块
│   ├── testcase/                    # 测试用例模块
│   ├── testplan/                    # 测试计划模块
│   ├── testtask/                    # 测试任务模块
│   ├── device/                      # 设备管理模块
│   ├── llm/                         # LLM 配置模块
│   ├── yolo/                        # YOLO 模块
│   └── task_monitor/                # 任务监控模块
├── automation_agent/                # 自动化执行 Agent
│   ├── agent.py                     # Agent 核心逻辑
│   ├── ai_service.py                # LLM 服务封装
│   ├── page_recognizer.py           # 页面识别（YOLO + OCR）
│   ├── types.py                     # 类型定义
│   ├── cli.py                       # 命令行调试入口
│   └── interfaces/
│       └── android.py               # ADB 控制接口（双通道页面解析）
├── core/                            # 核心框架
│   ├── config.py                    # 全局配置
│   ├── database.py                  # 数据库连接
│   ├── auth_middleware.py           # JWT 认证中间件
│   ├── response.py                  # 统一响应格式
│   ├── exception.py                 # 异常处理
│   ├── redis.py                     # Redis 客户端
│   └── enums.py                     # 枚举定义
├── services/                        # 后台任务消费者
│   ├── test_task_consumer.py        # 测试任务消费者
│   └── yolo_train_consumer.py       # YOLO 训练消费者
├── db/                              # 数据库初始化
│   ├── __main__.py                  # 自动建表入口
│   └── migrations/                  # SQL 迁移脚本
├── data/                            # YOLO 数据
│   └── yolo/                        # 数据集、模型权重、训练输出
├── models/                          # 模型文件
│   └── yolo/                        # 训练完成的模型权重
├── runs/                            # YOLO 训练/检测运行记录
├── storage/                         # 运行时数据
│   ├── screenshots/                 # 执行过程截图
│   └── reports/                     # 测试报告
├── scripts/                         # 运维脚本
│   └── init_database.sql            # 数据库初始化 SQL
├── docs/                            # 文档
│   └── deployment.md                # 生产部署指南
├── mobile_vision_web/               # 前端项目
│   ├── src/
│   │   ├── views/                   # 页面组件
│   │   ├── components/              # 通用组件
│   │   ├── router/                  # 路由配置
│   │   ├── network/                 # API 封装
│   │   ├── assets/                  # 静态资源
│   │   ├── App.vue                  # 根组件
│   │   └── main.js                  # 入口文件
│   └── package.json
└── utils/                           # 工具函数
```

---

## 🗄 数据库

主要数据表：

| 表名 | 说明 |
|------|------|
| `user` | 用户信息 |
| `workspace` | 工作空间 |
| `workspace_member` | 工作空间成员 |
| `member_role` | 成员角色 |
| `test_case` | 测试用例 |
| `test_case_step` | 用例步骤 |
| `test_plan` | 测试计划 |
| `test_plan_case` | 计划-用例关联 |
| `test_task` | 测试任务 |
| `test_job` | 测试任务执行单元 |
| `device` | Android 设备 |
| `llm_config` | LLM 配置 |
| `yolo_dataset` | YOLO 数据集 |
| `yolo_annotation` | YOLO 标注 |
| `yolo_train_task` | YOLO 训练任务 |
| `yolo_model` | YOLO 模型 |

---

## 📸 截图

### 系统页面

| 登录 | 注册 | 首页 | LLM 凭证管理 |
|:---:|:---:|:---:|:---:|
| ![登录](docs/%E7%99%BB%E5%BD%95.png) | ![注册](docs/%E6%B3%A8%E5%86%8C.png) | ![首页](docs/%E9%A6%96%E9%A1%B5.png) | ![LLM 凭证](docs/LLM%E5%87%AD%E8%AF%81%E5%85%B3%E8%81%94.png) |

### 数据集与模型训练

| 数据集管理 | 数据集标注 | 自动标注 | YOLO 训练中心 | YOLO 模型单测 |
|:---:|:---:|:---:|:---:|:---:|
| ![数据集管理](docs/%E6%95%B0%E6%8D%AE%E9%9B%86%E7%AE%A1%E7%90%86.png) | ![数据集标注](docs/%E6%95%B0%E6%8D%AE%E9%9B%86%E6%A0%87%E6%B3%A8.png) | ![自动标注](docs/%E6%95%B0%E6%8D%AE%E9%9B%86%E8%87%AA%E5%8A%A8%E6%A0%87%E6%B3%A8.png) | ![训练中心](docs/YOLO%E8%AE%AD%E7%BB%83%E4%B8%AD%E5%BF%83.png) | ![模型单测](docs/YOLO%E6%A8%A1%E5%9E%8B%E5%8D%95%E6%B5%8B.png) |

### 测试管理

| 工作空间概览 | 用例管理 | 用例编辑 | 测试计划 | 关联测试用例 | 测试任务 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| ![工作空间概览](docs/%E5%B7%A5%E4%BD%9C%E7%A9%BA%E9%97%B4%E6%A6%82%E8%A7%88%E9%A1%B5.png) | ![用例管理](docs/%E7%94%A8%E4%BE%8B%E7%AE%A1%E7%90%86%E9%A1%B5.png) | ![用例编辑](docs/%E7%94%A8%E4%BE%8B%E7%BC%96%E8%BE%91%E9%A1%B5.png) | ![测试计划](docs/%E6%B5%8B%E8%AF%95%E8%AE%A1%E5%88%92%E7%AE%A1%E7%90%86.png) | ![关联用例](docs/%E5%85%B3%E8%81%94%E6%B5%8B%E8%AF%95%E7%94%A8%E4%BE%8B.png) | ![测试任务](docs/%E6%B5%8B%E8%AF%95%E4%BB%BB%E5%8A%A1%E9%A1%B5%E9%9D%A2.png) |

### 执行与监控

| 测试过程可视化 | 思考过程输入输出分析 |
|:---:|:---:|
| ![可视化](docs/%E6%B5%8B%E8%AF%95%E8%BF%87%E7%A8%8B%E5%8F%AF%E8%A7%86%E5%8C%96.png) | ![思考过程](docs/%E6%80%9D%E8%80%83%E8%BF%87%E7%A8%8B%E8%BE%93%E5%85%A5%E8%BE%93%E5%87%BA%E5%88%86%E6%9E%90.png) |

---

## 🧪 测试执行流程

```
1. 创建测试用例 (添加步骤、设置优先级)
       │
2. 创建测试计划 (编排用例、分配设备队列)
       │
3. 创建测试任务 (设置执行策略、定时/立即执行)
       │
4. Agent 执行过程:
   ├── 读取步骤 → LLM 理解意图
   ├── 页面解析 → 优先使用 uiautomator2 DOM 快通道（0.3-0.8s）获取控件树；DOM 不足时自动切换至视觉通道（YOLO + OCR + 大津法），生成结构化页面树
   ├── LLM 决策 → 基于页面树 + 用例步骤进行推理，输出思考链与操作指令
   ├── ADB 执行点击/输入/滑动/长按/系统命令等
   ├── 验证结果 → 记录执行日志与状态变更
   └── 实时上报 → WebSocket 推送思考链、日志、状态、截图至监控页面
       │
5. 生成测试报告 (截图 + 日志 + 执行轨迹)
```

---

## 🔄 待办 / 规划

- [ ] **测试过程强化学习** — 支持将用例某次执行过程标记为**标准样例**，自动提取操作步骤、页面状态与决策路径。后续执行相同用例时，优先参考本地样例进行辅助决策，逐步减少对云端大模型的调用依赖，降低执行成本与响应延迟
- [ ] **增量学习与主动发现** — 测试执行过程中 Agent 发现的页面元素可自动回流至标注系统，经人工确认后纳入训练集，实现目标检测模型的持续迭代优化
- [ ] **定时任务与消息通知** — 支持测试任务的**定时/周期调度**（Cron 表达式），执行完成后通过**机器人通知**（飞书/钉钉/企业微信 Webhook）推送结果，实现无人值守的自动化测试闭环
- [ ] **技能插件系统** — 支持接入预置 Skill 或自定义脚本作为测试执行中的**前置/后置动作**，完成数据构造、接口调用、环境准备等必要环节，打通从准备到验证的完整流程闭环
- [ ] iOS 设备支持 (XCTest / WebDriverAgent)
- [ ] CI/CD 集成 (Jenkins / GitLab CI)

---

## 📄 License

本项目仅供学习交流使用。

---

<p align="center">
  <sub>Built with ❤️ by baojun.wang</sub>
</p>
