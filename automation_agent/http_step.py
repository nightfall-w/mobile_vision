"""
HTTP 步骤执行器 —— 在用例执行过程中发起接口请求，并从响应中提取变量供后续步骤使用。

典型场景：先调用接口获取卡号/卡密/token，再把提取到的值通过 {{变量名}} 引用到 input 动作里。

不引入第三方依赖，自带一个精简 JSONPath 实现（支持 $.a.b、$.a[0].b、$.a[*].b），
覆盖 99% 的取值场景；如需复杂表达式可后续替换为 jsonpath-ng。
"""
import json
import re
from typing import Any, Dict, Optional, Tuple

import requests

from utils.custom_logging import logger

_VAR_PATTERN = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


def render_template(value: Any, variables: Dict[str, Any]) -> Any:
    """递归地把字符串里的 {{var}} 替换为变量池中的值。

    - 纯占位符 "{{x}}"（整个字符串就是一个占位）会替换为变量的原始类型（int/dict/list 等），
      方便在 body 里传数字/布尔值；
    - 嵌入在文本中的占位符则做字符串拼接。
    dict/list 会递归处理每个元素。
    """
    if isinstance(value, str):
        m = _VAR_PATTERN.fullmatch(value.strip())
        if m:
            name = m.group(1)
            if name in variables:
                return variables[name]
            return value  # 变量不存在，保留原样以便日志排查
        return _VAR_PATTERN.sub(
            lambda mm: str(variables.get(mm.group(1), mm.group(0))), value
        )
    if isinstance(value, dict):
        return {k: render_template(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [render_template(v, variables) for v in value]
    return value


def _jsonpath_get(data: Any, expr: str) -> Tuple[bool, Any]:
    """精简 JSONPath 取值。

    支持：
      $            整个对象
      $.a.b        嵌套字段
      $.a[0]       数组下标
      $.a[*].b     数组通配，返回列表
      $..b         递归下降查找 key=b（取第一个匹配）
    返回 (found, value)。
    """
    if not expr or not expr.startswith("$"):
        return False, None

    path = expr[1:]
    if path == "":
        return True, data

    current = [data]
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == ".":
            # 递归下降 ..key
            if path[i + 1:i + 2] == ".":
                m = re.match(r"\.([\w]+)", path[i + 1:])
                if not m:
                    return False, None
                key = m.group(1)
                i += 2 + len(key)
                found_vals = []

                def _walk(node):
                    if isinstance(node, dict):
                        for k, v in node.items():
                            if k == key:
                                found_vals.append(v)
                            _walk(v)
                    elif isinstance(node, list):
                        for item in node:
                            _walk(item)

                for node in current:
                    _walk(node)
                if not found_vals:
                    return False, None
                current = found_vals
                continue

            m = re.match(r"\.([\w]+)", path[i:])
            if not m:
                return False, None
            key = m.group(1)
            i += 1 + len(key)
            next_vals = []
            for node in current:
                if isinstance(node, dict) and key in node:
                    next_vals.append(node[key])
            if not next_vals:
                return False, None
            current = next_vals
            continue

        if ch == "[":
            end = path.find("]", i)
            if end == -1:
                return False, None
            idx_expr = path[i + 1:end].strip()
            i = end + 1
            next_vals = []
            for node in current:
                if not isinstance(node, list):
                    continue
                if idx_expr == "*":
                    next_vals.extend(node)
                else:
                    try:
                        idx = int(idx_expr)
                    except ValueError:
                        return False, None
                    if -len(node) <= idx < len(node):
                        next_vals.append(node[idx])
            if not next_vals:
                return False, None
            current = next_vals
            continue

        # 无法识别的字符，前进避免死循环
        i += 1

    if not current:
        return False, None
    # 单元素结果解包；多元素返回列表
    return True, (current[0] if len(current) == 1 else current)


def execute_http(
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Any] = None,
        form: Optional[Dict[str, Any]] = None,
        extract: Optional[Dict[str, str]] = None,
        variables: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0,
        retries: int = 3,
) -> Dict[str, Any]:
    """执行一次 HTTP 请求并提取变量。

    :param body: JSON 请求体（dict/list），以 application/json 发送
    :param form: 表单请求体（dict），以 application/x-www-form-urlencoded 发送
    :param retries: 网络异常 / 429 / 5xx 时的重试次数（指数退避），默认 3
    :return: {"success": bool, "message": str, "status_code": int,
              "response": 解析后的 JSON 或文本, "extracted": {...}, "elapsed_ms": int}
    """
    import time as _time
    start = _time.time()
    variables = variables if variables is not None else {}

    # 变量替换
    url = render_template(url, variables)
    headers = render_template(headers or {}, variables)
    params = render_template(params or {}, variables)
    body = render_template(body, variables) if body is not None else None
    form = render_template(form, variables) if form is not None else None

    method = (method or "GET").upper()
    kwargs = {"headers": headers, "params": params, "timeout": timeout}
    if body is not None and method in ("POST", "PUT", "PATCH", "DELETE"):
        kwargs["json"] = body
    elif form is not None and method in ("POST", "PUT", "PATCH", "DELETE"):
        kwargs["data"] = form

    # 可重试的状态码（限流 / 服务端错误）
    retryable_status = {429, 500, 502, 503, 504}
    last_error = ""
    resp = None

    logger.info(f"[HTTP] {method} {url}")
    for attempt in range(1, max(retries, 1) + 1):
        try:
            resp = requests.request(method, url, **kwargs)
            last_error = ""
            if resp.status_code not in retryable_status:
                break
            last_error = f"HTTP {resp.status_code}"
            logger.warning(f"[HTTP] 第 {attempt} 次请求收到 {resp.status_code}，准备重试")
        except requests.RequestException as e:
            # SSL EOF / 连接重置 / 超时等网络层抖动
            last_error = str(e)
            logger.warning(f"[HTTP] 第 {attempt} 次请求异常: {e}")
            resp = None

        if attempt < max(retries, 1):
            backoff = min(2 ** (attempt - 1), 5)  # 1s, 2s, 4s...
            _time.sleep(backoff)

    elapsed_ms = int((_time.time() - start) * 1000)

    # 网络层最终失败（重试用尽仍异常）
    if resp is None:
        return {
            "success": False,
            "message": f"HTTP 请求异常（重试{retries}次后仍失败）: {last_error}",
            "status_code": 0,
            "response": None,
            "extracted": {},
            "elapsed_ms": elapsed_ms,
        }

    # 解析响应体
    parsed: Any
    try:
        parsed = resp.json()
        response_preview = json_preview(parsed)
    except ValueError:
        parsed = resp.text
        response_preview = (resp.text or "")[:300]

    if resp.status_code >= 400:
        return {
            "success": False,
            "message": f"HTTP {resp.status_code}: {response_preview}",
            "status_code": resp.status_code,
            "response": parsed,
            "extracted": {},
            "elapsed_ms": elapsed_ms,
        }

    # 提取变量
    extracted: Dict[str, Any] = {}
    if extract:
        for var_name, jsonpath_expr in extract.items():
            found, value = _jsonpath_get(parsed, jsonpath_expr)
            if found:
                extracted[var_name] = value
                variables[var_name] = value
            else:
                logger.warning(f"[HTTP] 提取变量 '{var_name}' 失败：JSONPath '{jsonpath_expr}' 未命中")

    logger.info(
        f"[HTTP] 响应 {resp.status_code}，耗时 {elapsed_ms}ms，"
        f"提取变量 {list(extracted.keys()) if extracted else '无'}"
    )
    return {
        "success": True,
        "message": f"HTTP {resp.status_code}，提取到 {len(extracted)} 个变量",
        "status_code": resp.status_code,
        "response": parsed,
        "extracted": extracted,
        "elapsed_ms": elapsed_ms,
    }


def json_preview(data: Any, limit: int = 300) -> str:
    """生成响应体预览字符串，用于日志/结果消息"""
    try:
        text = json_dumps(data)
    except Exception:
        text = str(data)
    return text[:limit]


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)
