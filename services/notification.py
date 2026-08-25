"""
@FileName：notification.py
@Description：任务完成通知推送 —— 支持企业微信、飞书、钉钉机器人 Webhook
@Author：baojun.wang
"""
import json
import re
from datetime import datetime
from typing import Optional

import requests

from core.enums import TaskStatus
from utils.custom_logging import logger


# ═══════════════════════════════════════════════════════════════
# 三个平台的消息格式
# ═══════════════════════════════════════════════════════════════

def _build_wecom_message(title: str, content: str) -> dict:
    """企业微信机器人消息（Markdown 格式）"""
    return {
        "msgtype": "markdown",
        "markdown": {
            "content": f"# {title}\n{content}"
        }
    }


def _build_lark_message(title: str, content: str) -> dict:
    """
    飞书机器人消息（interactive 卡片 + markdown）

    之前用 post 富文本格式，手动解析 markdown 成段落并给 text 标签加 style:["bold"]，
    但飞书 text 标签不支持 style 字段，会返回 19002 "params error, unknown content value"，
    且 HTTP 仍为 200，日志误判为成功。改用卡片原生 markdown，正文可直接复用 wecom/dingtalk
    同一份 markdown 内容。
    """
    # 飞书卡片 markdown 不支持 # / ## ATX 标题，会原样显示井号；
    # 把行首的 1~6 级标题转换为粗体行（卡片 header 已展示 title）。
    converted = re.sub(
        r"^#{1,6}\s+(.+?)\s*#*\s*$",
        lambda m: f"**{m.group(1)}**",
        content,
        flags=re.MULTILINE
    )

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": [
                {"tag": "markdown", "content": converted.strip()}
            ]
        }
    }


def _build_dingtalk_message(title: str, content: str) -> dict:
    """钉钉机器人消息（Markdown 格式）"""
    return {
        "msgtype": "markdown",
        "markdown": {
            "title": title[:50],  # 钉钉标题最多 50 字
            "text": content
        }
    }


# 平台 → 消息构建函数映射
_PLATFORM_BUILDERS = {
    "wecom": _build_wecom_message,
    "lark": _build_lark_message,
    "dingtalk": _build_dingtalk_message,
}


# ═══════════════════════════════════════════════════════════════
# 发送核心
# ═══════════════════════════════════════════════════════════════

def _send_single(platform: str, webhook_url: str, title: str, content: str) -> bool:
    """向单个 webhook 发送通知"""
    builder = _PLATFORM_BUILDERS.get(platform)
    if not builder:
        logger.warning(f"[通知] 未知平台: {platform}")
        return False

    payload = builder(title, content)
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"[通知] {platform} 发送失败: HTTP {resp.status_code} {resp.text[:200]}")
            return False

        # 三个平台在 HTTP 200 下仍可能通过 body 业务码报错
        # 飞书：{code:0, StatusCode:0} 成功；企微/钉钉：{errcode:0} 成功
        body = {}
        try:
            body = resp.json()
        except ValueError:
            pass
        biz_code = body.get("code", body.get("StatusCode", body.get("errcode")))
        if biz_code not in (0, None):
            biz_msg = body.get("msg") or body.get("errmsg") or body.get("StatusMessage") or resp.text[:200]
            logger.warning(f"[通知] {platform} 发送被拒: code={biz_code} msg={biz_msg} payload={json.dumps(payload, ensure_ascii=False)[:300]}")
            return False

        logger.info(f"[通知] {platform} 发送成功")
        return True
    except requests.RequestException as e:
        logger.warning(f"[通知] {platform} 请求异常: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# 任务结果通知
# ═══════════════════════════════════════════════════════════════

def _build_task_content(task, jobs, db) -> str:
    """
    构建任务通知正文

    :param task: TestTask 对象
    :param jobs: 该任务下的所有 TestJob 列表
    :param db: 数据库会话
    :return: Markdown 格式的文本
    """
    from app.testcase.models import TestCase

    total = task.total_jobs or 0
    completed = task.completed_jobs or 0
    failed = task.failed_jobs or 0
    aborted = task.aborted_jobs or 0
    duration = task.total_duration or 0
    duration_str = f"{duration // 60}分{duration % 60}秒" if duration > 0 else "-"

    status_text = {
        TaskStatus.COMPLETED.value: "✅ 全部完成",
        TaskStatus.FAILED.value: "❌ 部分失败",
        TaskStatus.ABORTED.value: "⏹️ 已放弃",
    }.get(task.status, task.status)

    lines = [
        f"## 任务状态：{status_text}",
        "",
        f"**计划名称**：{task.task_name}",
        f"**任务 ID**：{task.task_id}",
        f"**执行时间**：{task.start_time.strftime('%Y-%m-%d %H:%M:%S') if task.start_time else '-'}",
        f"**总耗时**：{duration_str}",
        "",
        f"**执行概况**：总计 {total} 个用例，成功 {completed}，失败 {failed}，放弃 {aborted}",
    ]

    # 失败用例详情
    failed_jobs = [j for j in jobs if j.status == TaskStatus.FAILED.value]
    if failed_jobs:
        lines.append("")
        lines.append("**失败用例**：")
        for j in failed_jobs:
            case = db.query(TestCase).filter(TestCase.case_id == j.case_id).first()
            case_name = case.case_name if case else f"用例{j.case_id}"
            reason = (j.result or "")[:100]
            lines.append(f"❌ {case_name}：{reason}")

    return "\n".join(lines)


def generate_task_report(task_id: int, db) -> Optional[str]:
    """
    生成任务执行分析报告 HTML 文件

    :return: 报告文件的 URL，生成失败返回 None
    """
    from app.testplan.models import TestPlan
    from app.testtask.models import TestTask, TestJob
    from app.testcase.models import TestCase
    from core.config import REPORT_ROOT, REPORT_URL
    from core.system_setting import get_backend_base_url, get_frontend_base_url

    task = db.query(TestTask).filter(TestTask.task_id == task_id).first()
    if not task:
        return None

    jobs = db.query(TestJob).filter(TestJob.task_id == task_id).order_by(TestJob.job_id).all()
    plan = db.query(TestPlan).filter(TestPlan.plan_id == task.plan_id).first()

    # 计算统计数据
    total = len(jobs)
    completed = sum(1 for j in jobs if j.status == TaskStatus.COMPLETED.value)
    failed = sum(1 for j in jobs if j.status == TaskStatus.FAILED.value)
    aborted = sum(1 for j in jobs if j.status == TaskStatus.ABORTED.value)
    pass_rate = round(completed / total * 100, 1) if total > 0 else 0
    duration = task.total_duration or 0
    duration_str = f"{duration // 60}分{duration % 60}秒" if duration > 0 else "-"

    # 构建 job 行 HTML
    status_badge = {
        TaskStatus.COMPLETED.value: '<span class="badge badge-success">成功</span>',
        TaskStatus.FAILED.value: '<span class="badge badge-danger">失败</span>',
        TaskStatus.ABORTED.value: '<span class="badge badge-warning">放弃</span>',
    }

    frontend_base = get_frontend_base_url(db)

    jobs_rows = ""
    for j in jobs:
        badge = status_badge.get(j.status, '<span class="badge">未知</span>')
        case = db.query(TestCase).filter(TestCase.case_id == j.case_id).first()
        case_name = case.case_name if case else f"用例{j.case_id}"
        reason = (j.result or "")[:200]
        job_duration = f"{j.duration}s" if j.duration else "-"
        monitor_link = f'<a href="{frontend_base}/testjobs/{j.job_id}/monitor" target="_blank" style="color:#5b6ef7;text-decoration:none;">#{j.job_id} ↗</a>'
        jobs_rows += f"""<tr>
          <td>{monitor_link}</td>
          <td>{case_name}</td>
          <td>{badge}</td>
          <td>{reason}</td>
          <td>{job_duration}</td>
        </tr>"""

    # 任务状态概览
    task_status_text = {
        TaskStatus.COMPLETED.value: "✅ 全部完成",
        TaskStatus.FAILED.value: "❌ 部分失败",
        TaskStatus.ABORTED.value: "⏹️ 已放弃",
    }.get(task.status, task.status)

    # 失败用例摘要
    failure_items = ""
    for j in jobs:
        if j.status != TaskStatus.FAILED.value:
            continue
        case = db.query(TestCase).filter(TestCase.case_id == j.case_id).first()
        case_name = case.case_name if case else f"用例{j.case_id}"
        failure_items += f'<li><strong>{case_name}</strong>：{(j.result or "")[:200]}</li>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>测试任务报告 - {task.task_name}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f7; color: #1d1d1f; line-height: 1.6; }}
.container {{ max-width: 960px; margin: 0 auto; padding: 24px 16px; }}
.header {{ background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; padding: 24px; margin-bottom: 16px; }}
.header h1 {{ font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
.header .meta {{ color: #8e8e93; font-size: 13px; }}
.header .status {{ font-size: 16px; font-weight: 600; margin-top: 8px; }}
.summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }}
.summary-card {{ background: #fff; border-radius: 10px; border: 1px solid #e8e8e8; padding: 16px; text-align: center; }}
.summary-card .num {{ font-size: 28px; font-weight: 700; }}
.summary-card .label {{ font-size: 12px; color: #8e8e93; margin-top: 2px; }}
.card {{ background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; padding: 20px; margin-bottom: 16px; }}
.card h2 {{ font-size: 15px; font-weight: 600; margin-bottom: 12px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ text-align: left; padding: 8px 10px; background: #fafafa; color: #6b7280; font-weight: 500; border-bottom: 1px solid #e8e8e8; }}
td {{ padding: 10px; border-bottom: 1px solid #f0f0f0; }}
tr:hover td {{ background: #fafafa; }}
.badge {{ display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 11px; font-weight: 500; }}
.badge-success {{ background: #e8f5e9; color: #2e7d32; }}
.badge-danger {{ background: #fbe9e7; color: #c62828; }}
.badge-warning {{ background: #fff8e1; color: #e65100; }}
.failure-list {{ list-style: none; padding: 0; }}
.failure-list li {{ padding: 8px 12px; margin-bottom: 6px; border-radius: 8px; background: #fef2f2; border: 1px solid #fecaca; font-size: 13px; }}
.footer {{ text-align: center; font-size: 12px; color: #c0c4cc; padding: 20px; }}
.num-success {{ color: #2e7d32; }} .num-danger {{ color: #c62828; }} .num-warning {{ color: #e65100; }} .num-total {{ color: #1d1d1f; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>{task.task_name}</h1>
    <div class="meta">任务 #{task.task_id} · 计划: {plan.name if plan else '-'} · {(task.start_time.strftime("%Y-%m-%d %H:%M:%S") if task.start_time else "-")}</div>
    <div class="status">{task_status_text} · 总耗时 {duration_str}</div>
  </div>

  <div class="summary">
    <div class="summary-card"><div class="num num-total">{total}</div><div class="label">总计</div></div>
    <div class="summary-card"><div class="num num-success">{completed}</div><div class="label">成功</div></div>
    <div class="summary-card"><div class="num num-danger">{failed}</div><div class="label">失败</div></div>
    <div class="summary-card"><div class="num num-warning">{aborted}</div><div class="label">放弃</div></div>
  </div>

  {"<div class='card'><h2>❌ 失败用例</h2><ul class='failure-list'>" + failure_items + "</ul></div>" if failure_items else ""}

  <div class="card">
    <h2>执行详情</h2>
    <table>
      <thead><tr><th>Job ID</th><th>用例名称</th><th>状态</th><th>结果</th><th>耗时</th></tr></thead>
      <tbody>{jobs_rows}</tbody>
    </table>
  </div>

  <div class="footer">MobileVision · 自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
</div>
</body>
</html>"""

    # 写入文件
    try:
        file_path = REPORT_ROOT / f"task_{task_id}.html"
        file_path.write_text(html, encoding="utf-8")
        logger.info(f"[报告] 任务 {task_id} 报告已生成: {file_path}")
        backend_base = get_backend_base_url(db)
        url = f"{backend_base}{REPORT_URL}/task_{task_id}.html"
        return url
    except Exception as e:
        logger.error(f"[报告] 生成任务 {task_id} 报告失败: {e}")
        return None


def send_task_notification(task_id: int, db):
    """
    发送任务完成通知

    在任务到达终态时调用，读取关联计划的 webhook 配置，逐平台发送。
    发送失败不影响任务本身状态，仅记日志。
    """
    from app.testplan.models import TestPlan
    from app.testtask.models import TestTask, TestJob

    task = db.query(TestTask).filter(TestTask.task_id == task_id).first()
    if not task:
        return

    if task.status not in [
        TaskStatus.COMPLETED.value,
        TaskStatus.FAILED.value,
        TaskStatus.ABORTED.value,
    ]:
        return  # 非终态不通知

    plan = db.query(TestPlan).filter(TestPlan.plan_id == task.plan_id).first()
    if not plan or not plan.enable_notification:
        return

    # 仅失败时通知：成功且没有失败 job 时跳过
    if plan.notify_on_failure_only and task.status == TaskStatus.COMPLETED.value:
        return

    # 生成 HTML 报告
    report_url = generate_task_report(task_id, db)

    # 收集所有 webhook
    webhooks = []
    for url in (plan.wecom_webhooks or []):
        webhooks.append(("wecom", url))
    for url in (plan.lark_webhooks or []):
        webhooks.append(("lark", url))
    for url in (plan.dingtalk_webhooks or []):
        webhooks.append(("dingtalk", url))

    if not webhooks:
        return

    # 获取所有 job
    jobs = db.query(TestJob).filter(TestJob.task_id == task_id).all()

    title = f"测试任务完成：{task.task_name}"
    content = _build_task_content(task, jobs, db)
    # 在正文末尾附加报告链接
    if report_url:
        content += f"\n\n[查看详细 HTML 分析报告]({report_url})"

    logger.info(f"[通知] 开始发送任务 {task_id} 通知，共 {len(webhooks)} 个 webhook")
    for platform, url in webhooks:
        _send_single(platform, url, title, content)