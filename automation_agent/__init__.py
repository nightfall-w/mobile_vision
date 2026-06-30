"""
自动化测试Agent框架

提供基于YOLO+OCR+大模型的智能自动化测试能力。

核心模块:
- types: 核心类型定义
- ai_service: AI模型服务（基于LiteLLM）
- agent: Agent控制器
- interfaces/android: Android设备接口
- cli: 命令行工具

使用示例:
    # 命令行
    agent-cli "打开微信并发送消息"

    # Python API
    from automation_agent import Agent, AndroidInterface, AgentConfig

    interface = await AndroidInterface.create()
    agent = Agent(interface=interface)
    result = await agent.run_task("打开微信并发送消息")
"""

from .types import (
    InterfaceType,
    Rect,
    PageContext,
    LocateResult,
    ExecutionResult,
    ActionStep,
    ActionPlan,
    AgentConfig,
    AIUsageInfo
)

from .ai_service import AIService
from .agent import Agent
from .interfaces.android import AndroidInterface

__all__ = [
    "InterfaceType",
    "Rect",
    "PageContext",
    "LocateResult",
    "ExecutionResult",
    "ActionStep",
    "ActionPlan",
    "AgentConfig",
    "AIUsageInfo",
    "AIService",
    "Agent",
    "AndroidInterface"
]
