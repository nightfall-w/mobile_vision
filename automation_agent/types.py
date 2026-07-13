"""
Agent框架核心类型定义 - 增强版
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class InterfaceType(str, Enum):
    ANDROID = "android"
    WEB = "web"
    IMAGE = "image"


class ActionType(str, Enum):
    TAP = "tap"
    LONG_PRESS = "long_press"
    INPUT = "input"
    SCROLL = "scroll"
    PRESS_KEY = "press_key"
    WAIT = "wait"
    OPEN_APP = "open_app"
    KILL_APP = "kill_app"
    FINISH = "finish"


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


class StepState(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Rect(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2


class PageContext(BaseModel):
    page_id: str
    image_width: int
    image_height: int
    elements: List[Dict[str, Any]]
    texts: List[Dict[str, Any]]
    structured_elements: List[Dict[str, Any]] = []
    screenshot_base64: str = ""
    source: str = "visual"  # "visual" | "dom"


class ExecutionResult(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    elapsed_ms: int = 0


class LocateResult(BaseModel):
    success: bool = False
    x: Optional[float] = None
    y: Optional[float] = None
    confidence: float = 0.0
    description: Optional[str] = None


class AIUsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0


class ActionStep(BaseModel):
    action: str
    target: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    text: Optional[str] = None
    direction: Optional[str] = None
    distance: Optional[float] = None
    duration: Optional[float] = None
    description: Optional[str] = None
    step_id: Optional[str] = None
    assertion: Optional[dict] = None


class TaskCompleteSignal(BaseModel):
    """任务完成信号 - 用于区分AI判定任务完成和解析异常"""
    reason: Optional[str] = None
    stop: Optional[bool] = True
    action: Optional[str] = None
    target: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    text: Optional[str] = None
    direction: Optional[str] = None
    distance: Optional[float] = None
    duration: Optional[float] = None
    description: Optional[str] = None
    step_id: Optional[str] = None
    assertion: Optional[dict] = None


class ActionPlan(BaseModel):
    task_id: Optional[str] = None
    steps: List[ActionStep] = []
    total_steps: int = 0
    current_step: int = 0


class StepExecutionRecord(BaseModel):
    step_id: str
    action: str
    description: str
    state: StepState = StepState.PENDING
    action_result: Optional[ExecutionResult] = None
    verification_result: Optional["StepVerificationResult"] = None
    timestamp: float = 0
    elapsed_ms: int = 0


class StepVerificationResult(BaseModel):
    success: bool
    page_changed: bool
    change_type: str = ""
    error_detected: bool = False
    error_message: str = ""
    details: Dict[str, Any] = {}
    confidence: float = 0.0


class TaskVerificationResult(BaseModel):
    completed: bool
    confidence: float = 0.0
    reason: str = ""
    evidence: List[str] = []


class Task(BaseModel):
    task_id: Union[int, str]
    description: str
    target_state: str = ""
    state: TaskState = TaskState.PENDING
    retry_count: int = 0
    max_retries: int = 3
    steps: List[StepExecutionRecord] = []
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    elapsed_ms: int = 0
    last_action_hash: Optional[str] = None
    consecutive_repeat_count: int = 0
    error_message: Optional[str] = None


class TaskList(BaseModel):
    original_task: str
    tasks: List[Task] = []
    current_task_index: int = 0


class OperationRecord(BaseModel):
    step_number: int = 0
    action: str = ""
    description: str = ""
    result: str = ""
    page_snapshot: str = ""
    success: bool = True
    timestamp: float = 0


class AgentConfig(BaseModel):
    test_id: Optional[str] = None
    model: str = "anthropic/claude-3-sonnet"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_total_time: int = 1800
    max_consecutive_failures: int = 5
    max_steps_per_task: int = 20
    max_repeat_actions: int = 8
    reasoning_effort: str = "low"
    step_timeout_ms: int = 30000
    wait_default_ms: int = 1000


class ExecutionSummary(BaseModel):
    success: bool
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_steps: int
    elapsed_ms: int
    ai_calls: int
    messages: List[str] = []
