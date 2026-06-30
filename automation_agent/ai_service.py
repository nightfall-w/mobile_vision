"""
AI模型服务 - 基于LiteLLM统一管理多种大模型
"""

import os
import warnings

# 过滤掉LiteLLM的警告
warnings.filterwarnings("ignore", category=UserWarning, module="litellm")

from typing import Any, Dict, List, Optional

import litellm
from utils.custom_logging import logger

litellm.logging = False  # 如果不需要日志
litellm.suppress_debug_info = True
litellm.set_verbose = False
litellm.logging = False  # 如果不需要日志

from .types import AIUsageInfo


class AIService:
    """使用LiteLLM的统一AI模型服务"""

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        litellm.set_verbose = False
        litellm.drop_params = True
        litellm.turn_off_message_logging = True

    async def call_ai(
            self,
            messages: List[Dict[str, Any]],
            reasoning_effort: str = "balanced",
            max_tokens: int = 4000,
            **kwargs
    ) -> Dict[str, Any]:
        """调用AI模型"""
        logger.debug(f"调用LiteLLM: {self.model}, 思考模式: {reasoning_effort}")

        provider = self.model.split("/")[0] if "/" in self.model else ""

        call_params = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "drop_params": True,
        }

        if reasoning_effort != "none":
            call_params["extra_body"] = {
                "thinking": {"type": "enabled"},
            }
        else:
            call_params["extra_body"] = {
                "thinking": {"type": "disabled"},
            }

        # 添加可选参数
        if self.api_key:
            call_params["api_key"] = self.api_key
        if self.base_url:
            call_params["base_url"] = self.base_url

        try:
            response = await litellm.acompletion(**call_params)

            # 调试：打印完整响应
            logger.debug(f"AI响应类型: {type(response)}")
            logger.debug(f"AI响应内容: {response}")

            # 提取内容
            content = ""
            thinking = ""
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message'):
                    msg = choice.message
                    if hasattr(msg, 'content'):
                        content = msg.content or ""
                    # 提取思考内容（OpenAI/DeepSeek 格式）
                    if hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                        thinking = msg.reasoning_content
                    # 提取思考内容（Anthropic 格式）
                    elif hasattr(msg, 'content') and isinstance(msg.content, list):
                        for block in msg.content:
                            if isinstance(block, dict) and block.get('type') == 'thinking':
                                thinking = block.get('thinking', '')
                elif hasattr(choice, 'text'):
                    content = choice.text
            elif isinstance(response, dict):
                content = response.get('content', '')
                thinking = response.get('thinking', '')

            logger.debug(f"提取的内容: {content if content else '空'}")
            if not content:
                return await self.call_ai(messages, reasoning_effort)
            return {
                "content": content,
                "thinking": thinking,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if hasattr(response, 'usage') and hasattr(
                        response.usage, 'prompt_tokens') else 0,
                    "completion_tokens": response.usage.completion_tokens if hasattr(response, 'usage') and hasattr(
                        response.usage, 'completion_tokens') else 0,
                    "total_tokens": response.usage.total_tokens if hasattr(response, 'usage') and hasattr(
                        response.usage, 'total_tokens') else 0
                },
                "model": response.model if hasattr(response, 'model') else self.model
            }

        except Exception as e:
            logger.error(f"调用AI失败: {e}")
            raise

    def build_messages(self, system_prompt: str, user_prompt: str) -> List[Dict[str, Any]]:
        """构建消息"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def get_usage_info(self, response: Dict[str, Any]) -> AIUsageInfo:
        """从响应中提取使用信息"""
        usage = response.get("usage", {})
        return AIUsageInfo(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0)
        )
