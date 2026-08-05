"""
AI模型服务 - 基于LiteLLM统一管理多种大模型
"""

import os
import warnings

# 过滤掉LiteLLM的警告
warnings.filterwarnings("ignore", category=UserWarning, module="litellm")

from typing import Any, Callable, Dict, List, Optional

import asyncio
import re

import litellm
from utils.custom_logging import logger

litellm.logging = False  # 如果不需要日志
litellm.suppress_debug_info = True
litellm.set_verbose = False
litellm.logging = False  # 如果不需要日志

from .types import AIUsageInfo

# ── 重试配置 ──
# 服务过载、限流等临时故障可通过重试恢复，不应直接中断整个测试任务
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # 指数退避基数：2s -> 4s -> 8s

# litellm 会把上游错误归一化成这些类型，均属可重试
RETRYABLE_EXCEPTIONS = (
    litellm.exceptions.RateLimitError,
    litellm.exceptions.InternalServerError,
    litellm.exceptions.ServiceUnavailableError,
    litellm.exceptions.APIConnectionError,
    litellm.exceptions.Timeout,
    litellm.exceptions.BadGatewayError,
)

# 部分厂商把限流/过载塞进 InternalServerError 甚至 APIError 的报文里
# （如火山引擎的 ServerOverloaded / TooManyRequests），故需再按文本兜底判断
RETRYABLE_KEYWORDS = (
    "serveroverloaded",
    "server overload",
    "toomanyrequests",
    "too many requests",
    "rate limit",
    "rate_limit",
    "ratelimit",
    "请求频繁",
    "请求过于频繁",
    "稍后再试",
    "稍后重试",
    "overloaded",
    "try again later",
    "service unavailable",
    "temporarily unavailable",
    "timeout",
    "timed out",
    "502",
    "503",
    "504",
    "529",
)


def is_retryable_error(error: Exception) -> bool:
    """判断异常是否属于可通过重试恢复的临时故障"""
    if isinstance(error, RETRYABLE_EXCEPTIONS):
        return True
    text = str(error).lower()
    return any(kw in text for kw in RETRYABLE_KEYWORDS)


def summarize_error(error: Exception, limit: int = 160) -> str:
    """压缩异常文本，避免超长报文刷屏日志流

    厂商报文常是整段 JSON，此处优先提取其中的 message/code 字段，取不到再截断原文。
    """
    text = " ".join(str(error).split())

    # 优先提取报文里的可读信息，如 {"error":{"code":"ServerOverloaded","message":"..."}}
    code = re.search(r'"code"\s*:\s*"([^"]+)"', text)
    message = re.search(r'"message"\s*:\s*"([^"]+)"', text)
    if message:
        brief = message.group(1)
        if code:
            brief = f"{code.group(1)} - {brief}"
        text = brief

    return text if len(text) <= limit else text[:limit] + "…"


class AIService:
    """使用LiteLLM的统一AI模型服务"""

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 on_log: Optional[Callable] = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        # 由 Agent 注入，用于把重试过程写入监控页日志流；独立使用时为 None
        self.on_log = on_log
        litellm.set_verbose = False
        litellm.drop_params = True
        litellm.turn_off_message_logging = True

    def _log(self, level: str, message: str):
        """写入日志流（失败不影响主流程）"""
        logger.warning(message) if level == "WARNING" else logger.info(message)
        if self.on_log:
            try:
                self.on_log(level, message)
            except Exception as e:
                logger.error(f"重试日志上报失败: {e}")

    async def call_ai(
            self,
            messages: List[Dict[str, Any]],
            reasoning_effort: str = "balanced",
            max_tokens: int = 4000,
            **kwargs
    ) -> Dict[str, Any]:
        """
        调用AI模型（含自动重试）

        服务过载、限流、网络抖动等临时故障会按指数退避重试，避免单次抖动
        直接中断整个测试任务。模型返回空内容同样计入重试预算，防止无限递归。
        """
        logger.debug(f"调用LiteLLM: {self.model}, 思考模式: {reasoning_effort}")

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

        last_error: Optional[str] = None

        for attempt in range(MAX_RETRIES + 1):  # 首次调用 + 最多 MAX_RETRIES 次重试
            is_last = attempt == MAX_RETRIES
            try:
                response = await litellm.acompletion(**call_params)

                logger.debug(f"AI响应类型: {type(response)}")
                logger.debug(f"AI响应内容: {response}")

                content, thinking = self._extract_content(response)

                if not content:
                    # 空内容并入统一重试预算，避免此前的无限递归
                    last_error = "模型返回空内容"
                    if is_last:
                        self._log("ERROR", f"LLM 连续 {MAX_RETRIES + 1} 次返回空内容，已中止")
                        raise RuntimeError(f"LLM 连续 {MAX_RETRIES + 1} 次返回空内容")
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    self._log("WARNING", f"LLM 返回空内容，{delay}s 后第 {attempt + 1}/{MAX_RETRIES} 次重试")
                    await asyncio.sleep(delay)
                    continue

                if attempt > 0:
                    self._log("INFO", f"LLM 调用成功（重试 {attempt} 次后恢复）")

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
                # 空内容重试耗尽时抛出的 RuntimeError 不再二次包装
                if isinstance(e, RuntimeError) and "返回空内容" in str(e):
                    raise

                if not is_retryable_error(e):
                    # 鉴权失败、参数错误等重试无意义，立即中断
                    logger.error(f"调用AI失败(不可重试): {e}")
                    self._log("ERROR", f"LLM 调用失败：{summarize_error(e)}")
                    raise

                last_error = summarize_error(e)
                if is_last:
                    self._log("ERROR", f"LLM 调用失败，已重试 {MAX_RETRIES} 次仍未成功：{last_error}")
                    logger.error(f"调用AI失败(重试耗尽): {e}")
                    raise

                delay = RETRY_BASE_DELAY * (2 ** attempt)
                self._log("WARNING",
                          f"LLM 调用失败，{delay}s 后第 {attempt + 1}/{MAX_RETRIES} 次重试：{last_error}")
                await asyncio.sleep(delay)

        # 循环正常结束意味着重试预算耗尽（理论上不可达，兜底防御）
        raise RuntimeError(f"LLM 调用失败，已重试 {MAX_RETRIES} 次：{last_error}")

    @staticmethod
    def _extract_content(response) -> tuple:
        """从响应中提取正文与思考内容"""
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
        return content, thinking

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
