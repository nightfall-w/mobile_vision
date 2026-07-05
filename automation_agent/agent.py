"""
Agent控制器
"""
import asyncio
import hashlib
import json
import time
import traceback
import uuid
from typing import Optional, List, Dict, Tuple

from utils.custom_logging import logger
from utils.task_cancel import check_cancel_signal
from .ai_service import AIService
from .types import (
    AgentConfig, PageContext, ActionStep, ActionPlan, ExecutionResult,
    Task, TaskList, TaskState, StepState, StepExecutionRecord,
    StepVerificationResult, TaskVerificationResult, OperationRecord,
)


class Agent:
    """自动化测试Agent"""

    def __init__(self, interface, config: Optional[AgentConfig] = None):
        self.interface = interface
        self.config = config or AgentConfig()
        self.ai_service = AIService(
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
        self.destroyed = False
        self.operation_history: List[OperationRecord] = []
        self.current_step_number = 0
        self.ai_call_count = 0
        self.start_time = 0.0

        # 状态上报回调
        self.on_state_update: Optional[callable] = None
        self.on_log: Optional[callable] = None
        self.on_screenshot: Optional[callable] = None
        self.job_id: Optional[int] = None
        self._stop_requested = False

        logger.info(f"Agent初始化完成, 模型: {self.config.model}")

    @property
    def interface_type(self) -> str:
        return self.interface.interface_type

    def _check_not_destroyed(self):
        if self.destroyed:
            raise RuntimeError("Agent已销毁")

    def check_abort(self) -> bool:
        """检查是否收到终止信号"""
        if self._stop_requested:
            return True
        if self.job_id:
            try:
                if check_cancel_signal(str(self.job_id), namespace="test_job"):
                    self._stop_requested = True
                    return True
            except Exception as e:
                logger.error(f"检查终止信号失败: {e}")
        return False

    def request_stop(self):
        """请求终止任务"""
        self._stop_requested = True
        self._report_log("WARNING", "收到终止请求，任务将在当前步骤完成后停止")

    def _report_state(self, state: str, data: Optional[Dict] = None):
        if self.on_state_update:
            try:
                asyncio.create_task(self.on_state_update({"type": state, "data": data or {}}))
            except Exception as e:
                logger.error(f"状态上报失败: {e}")

    def _report_log(self, level: str, message: str, page_structure: Optional[List[Dict]] = None):
        level_map = {
            'debug': 10,
            'info': 20,
            'warning': 30,
            'error': 40,
            'critical': 50
        }
        log_level = level_map.get(level.lower(), 20)
        if self.on_log:
            try:
                self.on_log(level, message, page_structure)
            except Exception as e:
                logger.error(f"日志上报失败: {e}")

    async def run_task(self, task_description: str, usage_instructions: str) -> ExecutionResult:
        """执行任务 - 核心入口"""
        self._check_not_destroyed()
        self.start_time = time.time()
        self._report_log("INFO", f"开始执行任务: {task_description}")
        self._report_state("task_started", {"description": task_description})

        try:
            task_list = await self._plan_tasks(task_description, usage_instructions)
            if not task_list.tasks:
                self._report_state("task_failed", {"error": "任务规划失败"})
                return ExecutionResult(success=False, error="任务规划失败，无法生成子任务")

            self._report_log("INFO", f"任务规划完成，共 {len(task_list.tasks)} 个子任务")
            self._report_state("planning_completed", {
                "task_count": len(task_list.tasks),
                "tasks": [
                    {"id": str(t.task_id), "description": t.description, "target_state": getattr(t, 'target_state', '')}
                    for t in task_list.tasks]
            })

            result = await self._execute_tasks(task_list, usage_instructions)
            elapsed_ms = int((time.time() - self.start_time) * 1000)

            if result.success:
                self._report_state("task_completed", {
                    "message": result.message,
                    "total_steps": self.current_step_number,
                    "elapsed_ms": elapsed_ms,
                    "ai_calls": self.ai_call_count
                })
            else:
                self._report_state("task_failed", {"error": result.error})

            return result

        except Exception as e:
            self._report_state("task_failed", {"error": str(e)})
            logger.error(f"任务执行失败: {e}")
            logger.error(traceback.format_exc())
            self._report_log("ERROR", f"任务执行失败: {e}")
            self._report_state("task_failed", {"error": str(e)})
            return ExecutionResult(success=False, error=str(e))

    async def _plan_tasks(self, task: str, usage_instructions: str) -> TaskList:
        """TaskPlanner: 将任务拆解为子任务列表"""
        system_prompt = """你是一个专业的自动化测试任务规划助手。

                        将用户需求拆解成一系列可执行的子任务。
                        
                        输出格式要求，仅输出JSON：
                        {
                            "tasks": [
                                {
                                    "task_id": 1,
                                    "description": "子任务1描述",
                                    "target_state": "期望达到的状态描述"
                                }
                            ]
                        }
                        
                        任务类型包括：
                        1. 导航类：打开应用、进入某个页面
                        2. 操作类：点击按钮、输入文本、滑动页面
                        3. 验证类：确认某个元素存在、验证内容正确
                        
                        注意：
                        1. 每个子任务应该是一个独立的、可验证的目标。
                        2. 为了防止json解析失败，返回的json键值对的value中的文本内不要使用英文双引号，只能在一个最小value的字符串整体首位使用英文双引号。
                        """

        user_prompt = f"""用户原始需求：{task}

                    APP使用说明：
                    {usage_instructions}
                    
                    请将上述需求拆解成子任务列表，但不要拆解的过于详细，因为每个子任务再后期都会重新拆解为具体的step。"""

        messages = self.ai_service.build_messages(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        response = await self.ai_service.call_ai(
            messages=messages,
            reasoning_effort=self.config.reasoning_effort,
            max_tokens=8000,
            response_format={"type": "json_object"}
        )
        self.ai_call_count += 1

        content = response.get("content", "")
        content = self._clean_json_content(content)

        thinking = response.get("thinking", "")
        if thinking:
            self._report_log("THINKING", f"[规划] {thinking}")

        try:
            plan_data = json.loads(content)
            if isinstance(plan_data, dict) and "tasks" in plan_data.keys():
                plan_data = plan_data.get("tasks", [])
            tasks = []
            for i, task_data in enumerate(plan_data):
                _task = Task(
                    task_id=task_data.get("task_id", i + 1),
                    description=task_data.get("description", ""),
                    target_state=task_data.get("target_state", "")
                )
                tasks.append(_task)

            self._report_log("INFO", f"任务规划解析成功，共 {len(tasks)} 个子任务")
            return TaskList(
                original_task=task,
                tasks=tasks,
                current_task_index=0
            )
        except Exception as e:
            logger.error(f"任务规划解析失败: {e}, content: {content}")
            self._report_log("ERROR", f"任务规划解析失败: {e}")
            return TaskList(original_task=task, tasks=[])

    async def _execute_tasks(self, task_list: TaskList, usage_instructions: str) -> ExecutionResult:
        """TaskExecutor: 按顺序执行每个子任务"""
        start_time = time.time()
        total_steps = 0

        for i, task in enumerate(task_list.tasks):
            if self.check_abort():
                self._report_state("task_aborted", {"message": "任务被用户放弃"})
                return ExecutionResult(
                    success=False,
                    error="任务被用户放弃"
                )

            if time.time() - start_time > self.config.max_total_time:
                self._report_state("task_timeout", {"elapsed": time.time() - start_time})
                return ExecutionResult(
                    success=False,
                    error=f"任务执行超时 ({self.config.max_total_time}秒)"
                )

            prev_task = task_list.tasks[i - 1] if i > 0 else None
            next_task = task_list.tasks[i + 1] if i + 1 < len(task_list.tasks) else None

            task.state = TaskState.RUNNING
            task.start_time = time.time()
            self._report_log("INFO", f"开始执行子任务 {i + 1}/{len(task_list.tasks)}: {task.description}")
            self._report_state("subtask_started", {
                "index": i,
                "total": len(task_list.tasks),
                "description": task.description
            })

            try:
                task_result, step_count = await self._execute_single_task(
                    task, usage_instructions, prev_task=prev_task, next_task=next_task
                )
            except Exception as e:
                # 捕获子任务执行中的所有异常,确保状态正确上报
                task.state = TaskState.FAILED
                task.error_message = str(e)
                task.end_time = time.time()
                task.elapsed_ms = int((task.end_time - task.start_time) * 1000)
                self._report_log("ERROR", f"子任务 {i + 1} 执行异常: {e}")
                self._report_state("subtask_failed", {
                    "index": i,
                    "error": str(e)
                })
                logger.error(f"子任务 {i + 1} 执行异常，原因: {str(e)}")
                self._report_state("task_terminated", {
                    "reason": "子任务执行异常",
                    "subtask_index": i,
                    "subtask_description": task.description,
                    "error": str(e)
                })
                raise  # 继续向上抛出,由外层处理

            total_steps += step_count

            task.end_time = time.time()
            task.elapsed_ms = int((task.end_time - task.start_time) * 1000)

            if task_result.success:
                task.state = TaskState.COMPLETED
                self._report_log("INFO", f"子任务 {i + 1} 执行成功")
                self._report_state("subtask_completed", {
                    "index": i,
                    "steps": step_count,
                    "elapsed_ms": task.elapsed_ms
                })
            else:
                task.state = TaskState.FAILED
                task.error_message = task_result.error
                self._report_log("ERROR", f"子任务 {i + 1} 执行失败: {task_result.error}")
                self._report_state("subtask_failed", {
                    "index": i,
                    "error": task_result.error
                })

                logger.error(f"子任务 {i + 1} 执行失败，原因: {task_result.error}")
                self._report_state("task_terminated", {
                    "reason": "子任务执行失败",
                    "subtask_index": i,
                    "subtask_description": task.description,
                    "error": task_result.error
                })
                return ExecutionResult(
                    success=False,
                    error=f"子任务「{task.description}」执行失败，测试终止"
                )

        logger.info(f"所有子任务执行完成，共执行 {total_steps} 步")
        self._report_log("INFO", f"任务完成，共执行 {total_steps} 步")
        return ExecutionResult(
            success=True,
            message=f"任务完成，共执行 {total_steps} 步"
        )

    async def _execute_single_task(self, task: Task, usage_instructions: str,
                                   prev_task: Task = None, next_task: Task = None) -> Tuple[ExecutionResult, int]:
        """
        执行单个子任务 - 带终止策略
        prev_task/next_task: 上一个/下一个子任务，让大模型了解上下文避免越界执行
        返回: (ExecutionResult, step_count)
        """
        step_count = 0
        consecutive_no_progress_count = 0
        last_page_hash = None
        verification_fail_count = 0
        max_verification_fails = 3
        verification_feedback = ""  # 验证失败的反馈信息
        consecutive_empty_plan_count = 0  # AI连续返回空计划计数
        max_empty_plans = 5
        context = None  # 复用上一轮末尾的感知结果，避免连续 OCR

        while step_count < self.config.max_steps_per_task:
            if self.check_abort():
                self._report_state("task_aborted", {"message": "任务被用户放弃"})
                return ExecutionResult(success=False, error="任务被用户放弃"), step_count

            if context is None:
                context = await self._perceive()

            if self.check_abort():
                self._report_state("task_aborted", {"message": "任务被用户放弃"})
                return ExecutionResult(success=False, error="任务被用户放弃"), step_count

            current_page_hash = getattr(self.interface, 'page_hash', '')

            self._report_state("step_deciding", {
                "task_description": task.description,
                "step_count": step_count
            })

            if last_page_hash == current_page_hash:
                consecutive_no_progress_count += 1
                if consecutive_no_progress_count >= self.config.max_repeat_actions:
                    error_msg = f"连续{consecutive_no_progress_count}次操作后页面无变化，判定任务失败"
                    self._report_log("ERROR", error_msg)
                    self._report_state("subtask_stuck", {
                        "reason": "页面无变化",
                        "step_count": step_count
                    })
                    return ExecutionResult(success=False, error=error_msg), step_count
            else:
                consecutive_no_progress_count = 0
                last_page_hash = current_page_hash

            next_plan = await self._decide_next_plan(task, context, usage_instructions,
                                                     feedback=verification_feedback,
                                                     prev_task=prev_task,
                                                     next_task=next_task)
            verification_feedback = ""  # 使用后清空,只对紧接着的一次决策生效

            if self.check_abort():
                self._report_state("task_aborted", {"message": "任务被用户放弃"})
                return ExecutionResult(success=False, error="任务被用户放弃"), step_count

            if next_plan is None or not next_plan.steps:
                consecutive_empty_plan_count += 1
                if consecutive_empty_plan_count >= max_empty_plans:
                    error_msg = (
                        f"连续{max_empty_plans}次AI返回空计划，大模型可能返回了无法解析的内容。"
                        f"请检查AI服务是否正常、当前页面信息是否过于复杂或为空、任务描述是否清晰。"
                    )
                    self._report_log("ERROR", error_msg)
                    self._report_state("subtask_failed", {
                        "error": error_msg,
                        "reason": "AI连续返回空计划"
                    })
                    return ExecutionResult(success=False, error=error_msg), step_count
                # 只在前几次上报 WARNING，避免刷屏
                if consecutive_empty_plan_count <= 2:
                    self._report_log("WARNING",
                                     f"AI返回空计划（第{consecutive_empty_plan_count}次），"
                                     f"可能是大模型响应格式异常或页面信息不足")
                context = None
                continue

            consecutive_empty_plan_count = 0  # 正常获得计划,重置计数

            # 执行规划的多步操作（不重感知页面）
            plan_result = await self._execute_plan_steps(next_plan, task, context, step_count)
            step_count += plan_result["steps_executed"]
            self.current_step_number += plan_result["steps_executed"]

            if plan_result["early_exit"]:
                if plan_result["success"]:
                    if plan_result.get("needs_verification", False):
                        # finish信号：做二次验证确认
                        context = await self._perceive()
                        task_verification = await self._verify_task(task, usage_instructions, context)
                        if task_verification.completed and task_verification.confidence >= 0.7:
                            self._report_log("INFO",
                                             f"置信度：{task_verification.confidence}，二次确认-判定子任务完成：{task.description}")
                            return ExecutionResult(success=True,
                                                   message=f"任务完成，共执行 {step_count} 步"), step_count
                        else:
                            verification_fail_count += 1
                            self._report_log("WARNING",
                                             f"AI判定任务完成但验证未通过（{verification_fail_count}/{max_verification_fails}次）")
                            # 将验证失败的反馈传递给下一次决策,防止AI越界执行下一个子任务
                            verification_feedback = (
                                f"⚠️ 系统提示：你上一次 finish 被拒绝了！验证未通过的原因：{task_verification.reason}。"
                                f"请仅专注于当前任务目标「{task.description}」，"
                                f"不要执行任何不属于当前任务的操作。如果当前任务确实无法完成，请先确保页面状态正确。"
                            )
                            if verification_fail_count >= max_verification_fails:
                                self._report_log("ERROR", f"连续{max_verification_fails}次验证未通过，标记子任务失败")
                                return ExecutionResult(
                                    success=False,
                                    error=f"AI判定任务完成但验证连续{max_verification_fails}次未通过：{task_verification.reason}"
                                ), step_count
                            continue
                    else:
                        return ExecutionResult(success=True,
                                               message=f"任务完成，共执行 {step_count} 步"), step_count
                else:
                    return ExecutionResult(success=False,
                                           error=plan_result.get("error", "")), step_count

            # 多步执行完后等待页面过渡，重新感知
            await asyncio.sleep(2)
            context = await self._perceive()
            new_page_hash = getattr(self.interface, 'page_hash', '')
            if new_page_hash == current_page_hash:
                consecutive_no_progress_count += 1
                if consecutive_no_progress_count >= self.config.max_repeat_actions:
                    error_msg = f"连续{consecutive_no_progress_count}次操作后页面无变化，判定任务失败"
                    self._report_log("ERROR", error_msg)
                    self._report_state("subtask_stuck", {
                        "reason": "页面无变化",
                        "step_count": step_count
                    })
                    return ExecutionResult(success=False, error=error_msg), step_count
                # 未变化，清除context，下轮循环顶重新截图感知
                self._report_log("INFO", f"页面未变化（第{consecutive_no_progress_count}次），等待下轮重试")
                context = None
            else:
                consecutive_no_progress_count = 0
                current_page_hash = new_page_hash
                # 页面已变化，下轮复用此 context 跳过 _perceive
            continue  # 跳过循环顶部的 _perceive，直接用上面的 context

        else:
            error_msg = f"达到最大步数限制({self.config.max_steps_per_task}步)"
            self._report_log("WARNING", error_msg)
            return ExecutionResult(success=False, error=error_msg), step_count

    def _hash_page_context(self, context: PageContext) -> str:
        """计算页面上下文的哈希值，用于检测页面是否变化"""
        try:
            texts = sorted([t.get("text", "") for t in context.texts if t.get("text")])
            elements = sorted([str(e.get("bbox", [])) for e in context.elements])
            content = json.dumps({"texts": texts, "elements": elements}, ensure_ascii=False)
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return str(time.time())

    async def _decide_next_plan(self, task: Task, context: PageContext, usage_instructions: str,
                                feedback: str = "", prev_task: Task = None,
                                next_task: Task = None) -> Optional[ActionPlan]:
        """StepDecider: 根据页面状态决定后续操作计划（支持多步规划）"""
        structured_str = json.dumps(context.structured_elements, ensure_ascii=False)
        logger.debug(json.dumps(context.structured_elements, ensure_ascii=False, indent=2))

        if self.operation_history:
            history_parts = []
            for record in self.operation_history[-7:]:
                status_mark = "已执行" if record.success else "执行失败"
                history_parts.append(
                    f"[步骤{record.step_number}] {record.action}: {record.description} "
                    f"→ {record.result}（{status_mark}）"
                )
            operation_history_str = "\n".join(history_parts)
        else:
            operation_history_str = "（暂无历史操作）"

        system_prompt = f"""你是一个专业的Android自动化助手。

                        根据当前页面信息、任务目标和历史操作记录，制定后续操作计划。

                        当前页面信息使用嵌套的树形JSON格式表示：

                        图片尺寸: {context.image_width}x{context.image_height}
                        元素数量: {len(context.elements)}个

                        页面结构（已按从上到下、从左到右排序）：
                        {structured_str}

                        ⚠️ 重要提示：以上页面信息是由视觉模型识别的，可能存在识别误差或不完全准确的情况,例如弹窗类型可能错误。
                        所以当你对页面信息存疑时，可以根据你的理解和常识做出自己的判断，不必完全拘泥于JSON中的描述。

                        任务目标: {task.description}
                        目标状态: {task.target_state}

                        {f"📋 上一个子任务（已完成）：{prev_task.description}，目标状态：{prev_task.target_state}" if prev_task else "📋 上一个子任务：无（这是第一个子任务）"}
                        {f"⚠️ 下一个子任务（不要提前执行）：{next_task.description}，目标状态：{next_task.target_state}" if next_task else "⚠️ 下一个子任务：无（这是最后一个子任务）"}

                        APP使用说明：
                        {usage_instructions}

                        历史操作记录（最近7条）：
                        {operation_history_str}

                        {feedback}

                        操作类型说明：
                        - tap: 点击坐标 (需要 x, y)
                        - long_press: 长按坐标 (需要 x, y, duration可选，默认1秒)
                        - input: 输入文本 (需要 text)
                        - scroll: 滚动页面 (需要 direction: up/down/left/right; 可选 distance: 滚动距离比例0.1~0.8，默认0.3约等于半屏，0.6约等于一屏)
                          ★ direction 按手指划动方向定义，不是内容移动方向：
                            up = 手指从下往上划 = 显示屏幕下方内容（如翻到页面底部）
                            down = 手指从上往下划 = 显示屏幕上方内容（如回到页面顶部）
                            left = 手指从右往左划
                            right = 手指从左往右划
                        - press_key: 按键 (需要 text: home/back/enter，而不是x，y坐标)
                        - wait: 等待一段时间 (需要 duration可选，默认2秒)
                        - open_app: 打开App (需要 text: App的包名)
                        - kill_app: 杀死App进程 (需要 text: App的包名)
                        - finish: 任务完成
                        - assert: 断言验证（验证页面状态是否满足预期，需要 assertion 字段）

                        输出JSON格式（仅输出JSON，不要输出其他内容包括分析和思考，并确保格式正确且无语法错误）：
                        {{
                            "steps": [
                                {{
                                    "action": "tap/scroll/input等",
                                    "description": "操作描述",
                                    "x": 坐标x,
                                    "y": 坐标y,
                                    "text": 输入文本或按键,
                                    "direction": 滚动方向,
                                    "duration": 持续时间
                                }}
                            ]
                        }}

                        注意：当action为assert时，assertion字段必须是一个JSON对象（object），不要写成字符串。正确的assert格式：
                        {{
                            "action": "assert",
                            "description": "描述要验证的页面状态",
                            "assertion": {{
                                "passed": true,
                                "expected": "预期页面状态描述",
                                "actual": "实际页面状态描述"
                            }}
                        }}

                        请仔细分析：
                        ★ 核心原则：你只需要完成当前子任务的目标，不要执行下一个子任务的操作。当目标状态已满足时，立即输出 action=finish 结束当前子任务。
                        ★ 不要过度思考，请及时给出结果。
                        1. 如果可以规划多个连续的步骤，请规划多步。多步规划的条件是：后续操作依赖的前置操作完成后页面不会发生显著变化。例如：
                           - 点击输入框 → 输入文字 → 点击搜索按钮（页面不会跳转，可以规划多步）
                           - 连续点击多个复选框（页面不会跳转，可以规划多步）
                           - 点击按钮 → 等待新页面加载（页面会跳转，所以只能规划1步）
                        2. 如果操作后页面可能会显著变化（如跳转、弹窗），则只规划1步，让系统重新感知页面后再决策
                        3. ★ scroll操作绝不可连续规划多步：每次scroll后页面内容必然变化，只能规划1步scroll，让系统重新感知后再决定是否继续滚动
                        3. 当前页面是否已经达到目标状态？如果是，在steps中放一个action为finish的步骤
                        4. 如果需要验证页面状态，使用action=assert并填写assertion
                        5. 当前页面与目标毫不相关时，善用press_key的back操作
                        6. 判断输入框是否已获取焦点：页面中出现"ADB Keyboard ON"表示输入框已聚焦，可以直接input输入，无需再点击输入框
                        7. ★ 页面中存在弹窗时，请先处理弹窗根据实际情况决定是否要先通过点击关闭icon来关闭弹窗，然后再执行下一步操作，如果确认需要关闭弹窗且弹窗中没有可用来点击的关闭icon，请返回action=press_key的back操作
                        8. 确保所有步骤的描述清晰且准确，避免重复描述。
                        9. 如果你发现当前页面状态与任务无关，请直接返回action=press_key的back操作，不要陷入死循环。
                        10. 坐标必须严格在图片范围内：x∈[0, {context.image_width}]，y∈[0, {context.image_height}]，超出范围的操作将被拒绝。
                        11. 输入操作的时机策略：如果规划"点击输入框 → 输入文本 → 点击按钮"这类多步连续操作：
                            - 如果输入框旁边紧邻有搜索、确认、提交等按钮，可以点击输入框后直接执行输入操作，无需等待
                            - 如果输入框是独立的，旁边没有紧挨着的按钮，点击输入框后需要插入 wait(duration=2) 步骤，等待输入框聚焦完成后再执行输入操作
"""

        user_prompt = "根据以上任务以及页面信息，分析当前页面状态并制定后续操作计划。"

        messages = self.ai_service.build_messages(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        response = await self.ai_service.call_ai(
            messages=messages,
            reasoning_effort=self.config.reasoning_effort,
            response_format={"type": "json_object"}
        )
        self.ai_call_count += 1

        content = response.get("content", "")
        content = self._clean_json_content(content)

        thinking = response.get("thinking", "")
        if thinking:
            page_struct = None
            if hasattr(context, 'structured_elements') and context.structured_elements:
                page_struct = {
                    "image_width": context.image_width,
                    "image_height": context.image_height,
                    "elements": context.structured_elements
                }
            self._report_log("THINKING", f"[决策] {thinking}", page_structure=page_struct)

        try:
            plan_data = json.loads(content)
            raw_steps = plan_data.get("steps", [])
            if not raw_steps:
                logger.error(f"AI规划结果中缺少steps，原始返回: {content[:300]}")
                self._report_log("WARNING", "大模型返回了无效的规划结果（缺少steps），可能是响应格式异常")
                return None

            steps = []
            for s in raw_steps:
                action_type = s.get("action", "").lower()

                if action_type == "finish":
                    steps.append(ActionStep(
                        action="finish", description=s.get("description", "")))
                    continue

                x_value = s.get("x")
                y_value = s.get("y")
                if x_value == "" or x_value is None:
                    x_value = None
                if y_value == "" or y_value is None:
                    y_value = None

                if action_type == "assert":
                    assertion_raw = s.get("assertion", {})
                    if isinstance(assertion_raw, str):
                        assertion = {"expected": assertion_raw, "actual": "", "passed": True}
                    else:
                        assertion = assertion_raw
                    steps.append(ActionStep(
                        action="assert", description=s.get("description", ""),
                        assertion=assertion))
                else:
                    steps.append(ActionStep(
                        action=action_type,
                        x=x_value, y=y_value,
                        text=s.get("text"),
                        direction=s.get("direction"),
                        duration=s.get("duration"),
                        description=s.get("description", "")
                    ))

            return ActionPlan(steps=steps, total_steps=len(steps))

        except Exception as e:
            logger.error(f"步骤规划解析失败: {e}, 原始返回: {content[:300]}")
            self._report_log("WARNING", f"大模型返回内容无法解析为JSON: {str(e)[:100]}")
            return None

    async def _execute_plan_steps(self, plan: ActionPlan, task: Task, context: PageContext,
                                  base_step_count: int) -> dict:
        """执行规划的多步操作（不重感知页面），返回执行结果"""
        result = {"steps_executed": 0, "early_exit": False, "success": False, "error": ""}
        step_offset = 0

        for i, step in enumerate(plan.steps):
            await asyncio.sleep(0.5)
            if self.check_abort():
                return {"steps_executed": step_offset, "early_exit": True, "success": False, "error": "任务被用户放弃"}

            step_count = base_step_count + step_offset + 1

            step_record = StepExecutionRecord(
                step_id=str(uuid.uuid4())[:8],
                action=step.action if hasattr(step, 'action') else 'finish',
                description=step.description or "",
                state=StepState.EXECUTING,
                timestamp=time.time()
            )

            # 记录执行日志
            action = step.action if hasattr(step, 'action') else 'finish'

            self._report_state("step_executing", {
                "step_number": step_count,
                "action": action,
                "description": step.description,
                "x": step.x if hasattr(step, 'x') else None,
                "y": step.y if hasattr(step, 'y') else None,
                "text": step.text if hasattr(step, 'text') else None,
                "direction": step.direction if hasattr(step, 'direction') else None,
                "duration": step.duration if hasattr(step, 'duration') else None,
                "assertion": step.assertion if hasattr(step, 'assertion') else None,
            })

            if action == "finish":
                self._report_log("INFO", f"执行步骤 {step_count}: 任务完成 - {step.description}")
                step_record.state = StepState.COMPLETED
                task.steps.append(step_record)
                self._report_state("step_completed", {
                    "step_number": step_count,
                    "action": action,
                    "success": True
                })
                result["steps_executed"] = step_offset + 1
                result["early_exit"] = True
                result["success"] = True
                result["needs_verification"] = True
                return result
            else:
                log_parts = [f"执行步骤 {step_count}: {action}"]
                if hasattr(step, 'x') and step.x is not None:
                    log_parts.append(f"x: {step.x}, y: {step.y}")
                if hasattr(step, 'text') and step.text:
                    log_parts.append(f"text: {step.text}")
                if hasattr(step, 'direction') and step.direction:
                    log_parts.append(f"direction: {step.direction}")
                if hasattr(step, 'duration') and step.duration:
                    log_parts.append(f"duration: {step.duration}")
                if hasattr(step, 'assertion') and step.assertion:
                    log_parts.append(f"assertion: {step.assertion}")
                log_parts.append(f"- {step.description}")
                self._report_log("INFO", " ".join(log_parts))

            action_result = await self._act(step)
            step_record.action_result = action_result
            step_offset += 1

            if not action_result.success:
                step_record.state = StepState.FAILED
                task.steps.append(step_record)
                self._report_log("WARNING", f"步骤{step_count}执行失败: {action_result.error}")
                self._report_state("step_failed", {
                    "step_number": step_count,
                    "error": action_result.error,
                    "action": action,
                    "success": False
                })
                result["steps_executed"] = step_offset
                result["early_exit"] = True
                result["success"] = False
                result["error"] = action_result.error
                return result

            step_record.elapsed_ms = int((time.time() - step_record.timestamp) * 1000)
            step_record.state = StepState.COMPLETED
            task.steps.append(step_record)

            self._report_state("step_completed", {
                "step_number": step_count,
                "action": action,
                "success": True
            })

            # 记录操作历史
            await self._record_operation(context, step, action_result)

        result["steps_executed"] = step_offset
        return result

    async def _act(self, step: ActionStep) -> ExecutionResult:
        """ActionExecutor: 执行单个步骤"""
        action = step.action.lower()
        start_time = time.time()

        try:
            if action == "finish":
                return ExecutionResult(success=True, message="任务完成")

            elif action == "assert":
                elapsed_ms = int((time.time() - start_time) * 1000)
                passed = step.assertion.get("passed", False) if step.assertion else False
                return ExecutionResult(
                    success=passed,
                    message=f"断言{'通过' if passed else '失败'}: {step.assertion.get('actual', '')}",
                    elapsed_ms=elapsed_ms,
                    error=f"断言{'通过' if passed else '失败'}: {step.assertion.get('actual', '')}"
                )

            elif action == "tap":
                if step.x is not None and step.y is not None:
                    await self.interface.tap(step.x, step.y)
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return ExecutionResult(
                        success=True,
                        message=f"点击 ({step.x}, {step.y})",
                        elapsed_ms=elapsed_ms
                    )

            elif action == "long_press":
                if step.x is not None and step.y is not None:
                    duration = step.duration or 1.0
                    await self.interface.long_press(step.x, step.y, duration)
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return ExecutionResult(
                        success=True,
                        message=f"长按 ({step.x}, {step.y}) 持续 {duration}秒",
                        elapsed_ms=elapsed_ms
                    )

            elif action == "wait":
                duration = step.duration or self.config.wait_default_ms / 1000
                await asyncio.sleep(duration)
                elapsed_ms = int((time.time() - start_time) * 1000)
                return ExecutionResult(
                    success=True,
                    message=f"等待 {duration}秒",
                    elapsed_ms=elapsed_ms
                )

            elif action == "input":
                if step.text:
                    await self.interface.input_text(step.text)
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return ExecutionResult(
                        success=True,
                        message=f"输入: {step.text}",
                        elapsed_ms=elapsed_ms
                    )

            elif action == "scroll":
                distance = step.distance if step.distance is not None else 0.3
                await self.interface.scroll(step.direction or "down", distance=distance)
                elapsed_ms = int((time.time() - start_time) * 1000)
                return ExecutionResult(
                    success=True,
                    message=f"滚动 {step.direction} (距离: {distance:.2f})",
                    elapsed_ms=elapsed_ms
                )

            elif action == "press_key":
                if step.text:
                    await self.interface.press_key(step.text)
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return ExecutionResult(
                        success=True,
                        message=f"按键: {step.text}",
                        elapsed_ms=elapsed_ms
                    )
                elif step.x is not None and step.y is not None:
                    await self.interface.tap(step.x, step.y)
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return ExecutionResult(
                        success=True,
                        message=f"点击坐标 ({step.x}, {step.y})",
                        elapsed_ms=elapsed_ms
                    )
                # 缺少参数，跳过但不中断流程
                logger.warning(f"press_key 缺少text/坐标，已跳过")
                return ExecutionResult(
                    success=True,
                    message="跳过: press_key缺少text字段"
                )

            elif action in ("keypress", "key", "press"):
                if step.text:
                    await self.interface.press_key(step.text)
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return ExecutionResult(
                        success=True,
                        message=f"按键: {step.text}",
                        elapsed_ms=elapsed_ms
                    )

            elif action == "open_app":
                if step.text:
                    await self.interface.open_app(step.text)
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return ExecutionResult(
                        success=True,
                        message=f"打开App: {step.text}",
                        elapsed_ms=elapsed_ms
                    )

            elif action == "kill_app":
                if step.text:
                    await self.interface.kill_app(step.text)
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return ExecutionResult(
                        success=True,
                        message=f"杀死App: {step.text}",
                        elapsed_ms=elapsed_ms
                    )

            # 未知动作: 记录但不中断流程,避免AI的拼写错误导致整个子任务失败
            logger.warning(f"未知动作 '{action}'，已跳过")
            self._report_log("WARNING", f"AI生成了未知动作 '{action}'，已跳过步骤")
            return ExecutionResult(
                success=True,
                message=f"跳过未知动作: {action}"
            )

        except Exception as e:
            logger.error(f"执行步骤失败: {e}")
            return ExecutionResult(success=False, error=str(e))

    async def _verify_task(self, task: Task, usage_instructions: str,
                           context: Optional[PageContext] = None) -> TaskVerificationResult:
        # """mock成功响应"""
        # return TaskVerificationResult(
        #     completed=True,
        #     confidence=1.0,
        #     evidence=[
        #         f"满足目标条件：{task.target_state}"
        #     ],
        #     reason="任务完成"
        # )
        """验证任务是否完成"""
        if context is None:
            context = await self._perceive()

        if self.operation_history:
            history_parts = []
            for record in self.operation_history[-3:]:
                status_mark = "已执行" if record.success else "执行失败"
                history_parts.append(
                    f"[步骤{record.step_number}] {record.action}: {record.description} "
                    f"→ {record.result}（{status_mark}）"
                )
            operation_history_str = "\n".join(history_parts)
        else:
            operation_history_str = "（暂无历史操作）"

        system_prompt = """你是一个专业的任务完成判断助手。

                根据当前页面信息和任务目标，判断任务是否已完成。
                
                输出JSON格式：
                {
                    "completed": true/false,
                    "confidence": 0.0-1.0,
                    "reason": "判断理由",
                    "evidence": ["证据1", "证据2"]
                }"""

        user_prompt = f"""任务目标: {task.description}
                目标状态: {task.target_state}
                
                历史操作记录（最近3条）：{operation_history_str}
                
                当前页面结构:
                {json.dumps(context.structured_elements, ensure_ascii=False)}
                
                APP使用说明：
                {usage_instructions}
                
                请判断任务是否完成。"""

        messages = self.ai_service.build_messages(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        response = await self.ai_service.call_ai(
            messages=messages,
            reasoning_effort=self.config.reasoning_effort,
            response_format={"type": "json_object"}
        )
        self.ai_call_count += 1

        content = response.get("content", "")
        content = self._clean_json_content(content)

        thinking = response.get("thinking", "")
        if thinking:
            page_struct = None
            if hasattr(context, 'structured_elements') and context.structured_elements:
                page_struct = {
                    "image_width": context.image_width,
                    "image_height": context.image_height,
                    "elements": context.structured_elements
                }
            self._report_log("THINKING", f"[验证] {thinking}", page_structure=page_struct)

        try:
            result = json.loads(content)
            return TaskVerificationResult(
                completed=result.get("completed", False),
                confidence=result.get("confidence", 0.0),
                reason=result.get("reason", ""),
                evidence=result.get("evidence", [])
            )
        except Exception as e:
            logger.error(f"任务验证解析失败: {e}, content: {content}")
            return TaskVerificationResult(completed=False, confidence=0.0)

    async def _record_operation(self, context: PageContext, step: ActionStep,
                                action_result: ExecutionResult,
                                verification: StepVerificationResult = None) -> None:
        """记录操作历史"""
        texts = [text.get("text", "") for text in context.texts]
        page_snapshot = "; ".join(texts[:10]) if texts else "无文字内容"

        record = OperationRecord(
            step_number=self.current_step_number,
            action=step.action,
            description=step.description or f"{step.action} {step.text or ''} {step.direction or ''}".strip(),
            result=action_result.message or action_result.error or "执行完成",
            page_snapshot=page_snapshot,
            success=action_result.success,
            timestamp=time.time()
        )

        self.operation_history.append(record)
        if len(self.operation_history) > 7:
            self.operation_history = self.operation_history[-7:]

        logger.debug(f"已记录操作历史，当前共{len(self.operation_history)}条")

    async def _perceive(self) -> PageContext:
        """感知：获取页面上下文"""
        return await self.interface.get_context()

    def _clean_json_content(self, content: str) -> str:
        """清理AI返回的JSON内容，去除可能的包装和非法字符"""
        if not content:
            return ""
        content = content.strip()
        import re
        json_match = re.search(r'```json\s*([\s\S]*?)```', content)
        if json_match:
            content = json_match.group(1).strip()
        elif content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # 修复 JSON 字符串内部的非法字符
        content = self._sanitize_json_control_chars(content)
        # 修复 value 内部的未转义双引号（如 "点击"等待"按钮"）
        content = self._fix_json_inner_quotes(content)
        return content

    def _sanitize_json_control_chars(self, text: str) -> str:
        """将 JSON 字符串内部的非法控制字符转义"""
        result = []
        in_string = False
        escape_next = False
        for ch in text:
            if escape_next:
                result.append(ch)
                escape_next = False
                continue
            if ch == '\\':
                in_string = True
                result.append(ch)
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                result.append(ch)
                continue
            if in_string and ch in '\n\r\t':
                if ch == '\n':
                    result.append('\\n')
                elif ch == '\r':
                    result.append('\\r')
                elif ch == '\t':
                    result.append('\\t')
                continue
            result.append(ch)
        return ''.join(result)

    def _fix_json_inner_quotes(self, text: str) -> str:
        """修复 JSON value 内部的未转义双引号。
        状态机：检测位于 value 字符串内部（: " 之后）的裸双引号并转义。"""
        result = []
        in_value = False  # 是否在 value 字符串内（而非 key 字符串内）
        in_string = False  # 是否在任意字符串内
        escape_next = False
        i = 0
        while i < len(text):
            ch = text[i]
            if escape_next:
                result.append(ch)
                escape_next = False
                i += 1
                continue
            if ch == '\\':
                result.append(ch)
                escape_next = True
                i += 1
                continue
            if ch == '"':
                if not in_string:
                    # 进入字符串，判断是 key 还是 value
                    in_string = True
                    # 向前看这个 " 之前最近的 : 或 ,
                    before = text[:i].rstrip()
                    in_value = before.endswith(':')
                    result.append(ch)
                else:
                    # 尝试退出字符串。检查下一个非空白字符
                    after = text[i + 1:].lstrip()
                    if in_value and after and after[0] not in ',}]\n\r':
                        # 在 value 内部遇到了 "，但后面不是 JSON 分隔符，说明是内嵌引号
                        result.append('\\"')
                    else:
                        in_string = False
                        in_value = False
                        result.append(ch)
                i += 1
                continue
            result.append(ch)
            i += 1
        return ''.join(result)

    async def destroy(self):
        """销毁Agent"""
        self.destroyed = True
        logger.info("Agent已销毁")
