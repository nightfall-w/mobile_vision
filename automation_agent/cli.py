"""
CLI工具 - 提供简洁的命令行接口
"""

import argparse
import asyncio
import json
import os
import sys

from loguru import logger

from automation_agent.agent import Agent
from automation_agent.types import AgentConfig
from automation_agent.interfaces.android import AndroidInterface


def get_config_help():
    """获取配置帮助信息"""
    return """
环境变量配置示例:

  # ====== 方式一：OpenAI API ======
  
  export OPENAI_API_KEY="your-key"
  agent-cli --model "openai/gpt-4o" "执行任务"

  # ====== 方式二：Anthropic API ======
  # 支持原生Claude、MiniMax、DeepSeek等
  
  # 原生Anthropic
  export ANTHROPIC_API_KEY="your-key"
  agent-cli --model "anthropic/claude-3-sonnet" "执行任务"

  # MiniMax（通过Anthropic协议接入）
  export ANTHROPIC_API_KEY="your-minimax-key"
  export ANTHROPIC_API_BASE="https://api.minimax.io/v1/chat/completions"
  agent-cli --model "MiniMax-M2.7" "执行任务"

  # DeepSeek（通过Anthropic协议接入）
  export ANTHROPIC_API_KEY="your-deepseek-key"
  export ANTHROPIC_API_BASE="https://api.deepseek.com/anthropic"
  agent-cli --model "deepseek-v4-pro" "执行任务"

支持的接入方式:
  1. OpenAI协议: openai/gpt-4o, openai/gpt-4, openai/gpt-3.5-turbo
  2. Anthropic协议: anthropic/claude-3-sonnet, MiniMax-M2.7, deepseek-v4-pro
"""


def main():
    parser = argparse.ArgumentParser(
        prog="agent-cli",
        description="自动化测试Agent - 基于YOLO+OCR+大模型的智能自动化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=get_config_help()
    )

    # 必需参数
    parser.add_argument("task", type=str, help="任务描述")

    # 设备配置
    parser.add_argument("--device", type=str, default=None, help="指定设备ID")

    # AI模型配置
    parser.add_argument("--model", type=str, default=os.getenv("AI_MODEL", "anthropic/claude-3-sonnet"),
                        help=f"AI模型（默认: anthropic/claude-3-sonnet）")
    parser.add_argument("--api-key", type=str, default=None, help="API Key")
    parser.add_argument("--base-url", type=str, default=None, help="服务地址")

    # 识别配置
    parser.add_argument("--yolo-model", type=str, default=None, help="YOLO模型路径")
    parser.add_argument("--ocr-engine", type=str, default="rapidocr", choices=["rapidocr", "easyocr"],
                        help="OCR引擎（默认: rapidocr）")

    # 调试选项
    parser.add_argument("--debug", action="store_true", help="启用调试模式")

    args = parser.parse_args()

    # 设置日志级别
    logger.remove()
    if args.debug:
        logger.add(sys.stdout, level="DEBUG")
    else:
        logger.add(sys.stdout, level="INFO")

    # 运行任务
    asyncio.run(run_task(args))


async def run_task(args):
    """运行任务"""
    try:
        # 创建设备接口
        interface = await AndroidInterface.create(
            device_id=args.device,
            yolo_model_path=args.yolo_model,
            ocr_engine=args.ocr_engine
        )

        # 创建Agent配置
        config = AgentConfig(
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url
        )

        # 创建Agent并执行任务
        agent = Agent(interface=interface, config=config)
        result = await agent.run_task(args.task)

        # 输出结果
        print("\n" + "=" * 50)
        if result.success:
            print("✅ 任务完成!")
            print(f"   消息: {result.message}")
        else:
            print("❌ 任务失败!")
            print(f"   错误: {result.error}")
        print("=" * 50 + "\n")

        await agent.destroy()

    except Exception as e:
        logger.error(f"执行失败: {e}")
        print(f"\n❌ 执行失败: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
