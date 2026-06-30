"""
@FileName：commonlib.py
@Description：
@Author：baojun.wang
@Time：2025/6/21 23:29
"""
import asyncio
import datetime
import os
import random
import time
import uuid
from functools import partial
import socket
import pytz
from dotenv import load_dotenv
from tenacity import stop_after_attempt, retry, wait_exponential

from utils.custom_logging import logger

load_dotenv()


class Env:
    QA = 'qa'
    OL = 'ol'


def record_function_log(custom_tag: str = ''):
    """
    通用日志装饰器 记录被装饰方法的输入输出
    :param custom_tag: 自定义标签，可以快速定位日志
    :return: 被装饰方法的返回值
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"debug日志自定义标签:{custom_tag}, 方法名:{func.__name__}, Input arguments: {args} {kwargs}")

            # 调用原始方法
            result = func(*args, **kwargs)

            # 打印返回值
            logger.debug(f"debug日志自定义标签:{custom_tag}, 方法名:{func.__name__}, Output result: {result}")

            return result

        return wrapper

    return decorator


def url_encode(s: str) -> str:
    """将字符串转换为 URL 编码格式"""
    encoded = []
    for char in s:
        # 如果字符是字母、数字或允许的特殊字符，则直接保留
        if (
                'a' <= char <= 'z' or
                'A' <= char <= 'Z' or
                '0' <= char <= '9' or
                char in '-_.~'
        ):
            encoded.append(char)
        else:
            # 否则将字符转换为 %XX 格式
            encoded.append(f'%{ord(char):02X}')
    return ''.join(encoded)


def get_current_date():
    current_datetime = datetime.datetime.now()
    current_date = current_datetime.strftime("%Y-%m-%d")
    return current_date


def get_current_weekday():
    current_datetime = datetime.datetime.now()
    weekday = current_datetime.weekday()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return weekdays[weekday]


def now():
    """返回北京时区的当前时间"""
    tz = pytz.timezone(os.getenv('TIMEZONE', 'Asia/Shanghai'))
    tz_time = datetime.datetime.now(tz)
    return tz_time.strftime("%Y-%m-%d %H:%M:%S")


def now_with_offset(minutes: int = 0):
    """返回北京时区的当前时间，可添加分钟偏移"""
    tz = pytz.timezone(os.getenv('TIMEZONE', 'Asia/Shanghai'))
    tz_time = datetime.datetime.now(tz) + datetime.timedelta(minutes=minutes)
    return tz_time


def timestamp_format(timestamp: int):
    return datetime.datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")


def generate_unique_uid() -> str:
    """生成唯一且符合长度要求的 UID"""
    return str(uuid.uuid4())[:40]  # 保证不超过 String(40)


def safe_call_with_retry(func, args=(), kwargs=None, max_retries=3):
    """同步函数通用安全调用函数，带重试逻辑"""
    kwargs = kwargs or {}
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"调用 {func.__name__} 异常 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(1)  # 简单重试间隔


async def run_sync_func_async(func, *args, **kwargs):
    """
    将同步函数包装为异步调用
    :param func: 同步函数
    :param args: 参数
    :param kwargs: 关键字参数
    :return: 异步执行结果
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


async def run_with_retry_async(func, max_retries=3, *args, **kwargs):
    @retry(stop=stop_after_attempt(max_retries), wait=wait_exponential(multiplier=1, max=10))
    async def _wrapper():
        if asyncio.iscoroutinefunction(func):
            # 如果是异步函数，直接 await
            return await func(*args, **kwargs)
        else:
            # 否则作为同步函数在 executor 中运行
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    return await _wrapper()


def float_2_percentage(float_number):
    """
    标准化浮点数转百分比
    """
    return float(str(float('%.4f' % float_number) * 100)[:5])


def current_time_format_ms():
    """
    当前时间格式化 毫秒级
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def is_chinese(word):
    for ch in word:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False


def ts_10():
    # 生成10位时间戳
    return int(time.time())


def ts_13():
    # 生成13位时间戳
    return int(time.time() * 1000)


def random_integer():
    """
    随机整型
    """
    return random.randint(1, 900000)


# 在 commonlib.py 中修改 get_host_ip 函数
def get_host_ip():
    """
    获取主机ip
    """
    try:
        # 尝试连接外部地址来获取本地IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        return ip
    except Exception:
        # fallback到localhost
        return "127.0.0.1"


print(get_host_ip())
