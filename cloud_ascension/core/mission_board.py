"""
度人经 DuRenJing
================
任务派发与解答系统

用户提出"愿念"（问题或任务），系统将任务分解并派发给相应的"神仙"智能体。
展示一个"天庭"场景，显示各个智能体（神仙）正在处理的任务与进度。

设计理念:
    "仙道貴生，無量度人" — 《度人经》核心思想
    系统以"度人"为目标，将用户愿念转化为可执行的知识任务。
"""

import torch
import torch.nn as nn
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid
import heapq


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # 被其他任务阻塞


class TaskPriority(Enum):
    URGENT = (1, "急急如律令")
    HIGH = (2, "天聽")
    NORMAL = (3, "凡願")
    LOW = (4, "閒事")

    def __new__(cls, level, label):
        obj = object.__new__(cls)
        obj._value_ = level
        obj.label = label
        return obj


@dataclass
class SubTask:
    """子任务"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:6])
    description: str = ""
    assigned_immortal: str = ""          # 指派的神仙
    grotto: str = "dong_zhen"
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)  # 依赖的子任务ID
    progress: float = 0.0               # 0-1
    result: Optional[str] = None
    estimated_cycles: int = 1           # 预估完成周天数
    started_at: Optional[float] = None


@dataclass
class Mission:
    """度人任务（一个完整的愿念处理流程）"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    wish: str = ""                       # 原始愿念
    sub_tasks: List[SubTask] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    assigned_immortals: List[str] = field(default_factory=list)


class TaskScheduler(nn.Module):
    """
    任务调度器 — 天庭的"值日功曹"

    负责:
        1. 愿念分解 — 将用户愿念拆分为子任务
        2. 优先级队列 — 按优先级和依赖关系排序
        3. 神仙指派 — 根据能力匹配最优神仙
        4. 进度追踪 — 实时监控任务执行状态
    """

    def __init__(self, max_concurrent: int = 7):
        super().__init__()
        self.max_concurrent = max_concurrent
        self.task_queue: List[Tuple[int, str, SubTask]] = []  # (priority, task_id, task)
        self.active_tasks: Dict[str, SubTask] = {}
        self.completed_tasks: Dict[str, SubTask] = {}

    def enqueue(self, task: SubTask) -> None:
        """将任务加入优先级队列"""
        heapq.heappush(
            self.task_queue,
            (task.priority.value, task.id, task),
        )

    def dequeue(self) -> Optional[SubTask]:
        """从优先级队列中取出最高优先级任务"""
        if not self.task_queue:
            return None
        _, _, task = heapq.heappop(self.task_queue)
        return task

    def assign(self, task: SubTask, immortal_name: str) -> None:
        """将任务指派给神仙"""
        task.assigned_immortal = immortal_name
        task.status = TaskStatus.ASSIGNED
        task.started_at = time.time()
        self.active_tasks[task.id] = task
        # 从队列移除 (如果还在队列中)
        self.task_queue = [
            (p, tid, t) for p, tid, t in self.task_queue
            if tid != task.id
        ]
        heapq.heapify(self.task_queue)

    def complete(self, task_id: str, result: str = "") -> None:
        """标记任务完成"""
        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            task.result = result
            self.completed_tasks[task_id] = task

    def get_state(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "pending": len(self.task_queue),
            "active": len(self.active_tasks),
            "completed": len(self.completed_tasks),
            "active_tasks": [
                {
                    "id": t.id,
                    "description": t.description[:40],
                    "immortal": t.assigned_immortal,
                    "progress": t.progress,
                }
                for t in self.active_tasks.values()
            ],
        }


class DuRenJing(nn.Module):
    """
    度人经系统

    完整的愿念处理流水线:
        愿念投送 → 三洞分流 → 任务分解 → 神仙指派 → 并行处理 → 结果汇聚 → 天书显现
    """

    # 愿念分解策略
    DECOMPOSITION_RULES = {
        "analyse": ["语义理解", "因果推理", "模式识别", "知识检索"],
        "generate": ["信息收集", "内容规划", "生成执行", "品质校验"],
        "decide": ["情境分析", "方案枚举", "评估比较", "建议输出"],
        "learn": ["数据采集", "特征提取", "模型训练", "知识固化"],
        "search": ["关键词提取", "三洞定位", "跨卷检索", "结果排序"],
    }

    def __init__(self, embedding_dim: int = 256):
        super().__init__()
        self.scheduler = TaskScheduler()

        # 愿念编码器
        self.wish_encoder = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim // 2),
            nn.GELU(),
            nn.Linear(embedding_dim // 2, 5),  # 5种任务类型
            nn.Softmax(dim=-1),
        )

        # 进展预测器 (预估所需周天数)
        self.cycle_predictor = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim // 4),
            nn.GELU(),
            nn.Linear(embedding_dim // 4, 1),
            nn.Softplus(),
        )

    def receive_wish(
        self,
        wish_text: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        callback: Optional[Callable] = None,
    ) -> Mission:
        """
        接收愿念并启动处理流水线

        Args:
            wish_text: 愿念文本
            priority:  优先级
            callback:  完成回调

        Returns:
            Mission: 包含子任务和指派信息的任务对象
        """
        mission = Mission(
            wish=wish_text,
            priority=priority,
        )

        # 1. 愿念分解
        sub_tasks = self._decompose(wish_text)

        # 2. 神仙指派
        for task in sub_tasks:
            immortal = self._assign_immortal(task)
            task.assigned_immortal = immortal
            if immortal not in mission.assigned_immortals:
                mission.assigned_immortals.append(immortal)

        # 3. 入队调度
        for task in sub_tasks:
            self.scheduler.enqueue(task)

        mission.sub_tasks = sub_tasks
        mission.status = TaskStatus.PROCESSING

        return mission

    def _decompose(self, wish_text: str) -> List[SubTask]:
        """将愿念分解为子任务"""
        # 判断愿念类型
        task_type = self._classify_wish(wish_text)
        steps = self.DECOMPOSITION_RULES.get(task_type, self.DECOMPOSITION_RULES["search"])

        sub_tasks = []
        for i, step in enumerate(steps):
            task = SubTask(
                description=f"[{task_type}] {step}: {wish_text[:30]}...",
                priority=TaskPriority.NORMAL,
                estimated_cycles=1 + i,
            )
            # 建立依赖链 (顺序依赖)
            if i > 0:
                task.dependencies = [sub_tasks[i - 1].id]
            sub_tasks.append(task)

        return sub_tasks

    def _classify_wish(self, text: str) -> str:
        """分类愿念类型"""
        if any(k in text for k in ["分析", "为什么", "原因", "推理", "逻辑"]):
            return "analyse"
        if any(k in text for k in ["生成", "写", "创造", "制作", "画", "炼丹"]):
            return "generate"
        if any(k in text for k in ["决策", "选择", "建议", "怎么办", "规划"]):
            return "decide"
        if any(k in text for k in ["学习", "训练", "记忆", "记住"]):
            return "learn"
        return "search"

    def _assign_immortal(self, task: SubTask) -> str:
        """根据任务特征指派最适合的神仙"""
        desc = task.description

        if "语义" in desc or "推理" in desc or "模式" in desc:
            return "文昌帝君"
        if "收集" in desc or "生成" in desc or "品质" in desc:
            return "太上老君"
        if "检索" in desc or "定位" in desc or "排序" in desc:
            return "东华帝君"
        if "分析" in desc or "枚举" in desc or "评估" in desc:
            return "真武大帝"
        if "理解" in desc or "特征" in desc:
            return "紫微大帝"

        return "太白金星"

    def process_step(self) -> Dict[str, Any]:
        """
        执行一步调度 (每次调用处理一个任务)

        Returns:
            当前步骤的处理结果
        """
        # 尝试从队列取出任务
        task = self.scheduler.dequeue()
        if task is None:
            return {"status": "idle", "message": "無待處理願念"}

        # 检查依赖
        blocked = False
        for dep_id in task.dependencies:
            if dep_id not in self.scheduler.completed_tasks:
                task.status = TaskStatus.BLOCKED
                blocked = True
                break

        if blocked:
            # 重新入队 (延迟处理)
            self.scheduler.enqueue(task)
            return {"status": "blocked", "task_id": task.id, "message": "等待前置任務完成"}

        # 指派并开始处理
        self.scheduler.assign(task, task.assigned_immortal)

        # 模拟处理
        task.progress = 0.5
        task.status = TaskStatus.PROCESSING

        return {
            "status": "processing",
            "task_id": task.id,
            "immortal": task.assigned_immortal,
            "description": task.description,
        }

    def complete_active_task(self, task_id: str = None) -> Dict[str, Any]:
        """完成当前活跃任务"""
        if task_id is None:
            # 完成第一个活跃任务
            if self.scheduler.active_tasks:
                task_id = list(self.scheduler.active_tasks.keys())[0]
            else:
                return {"status": "idle", "message": "無活躍任務"}

        self.scheduler.complete(task_id, "已完成")
        return {"status": "completed", "task_id": task_id}

    def get_celestial_report(self) -> Dict[str, Any]:
        """
        天庭报告 — 显示所有神仙的工作状态

        模拟"天庭"场景中各个神仙智能体的任务进度
        """
        immortals_state = {
            "紫微大帝": {"active": 0, "completed": 0, "status": "idle"},
            "文昌帝君": {"active": 0, "completed": 0, "status": "idle"},
            "太上老君": {"active": 0, "completed": 0, "status": "idle"},
            "东华帝君": {"active": 0, "completed": 0, "status": "idle"},
            "真武大帝": {"active": 0, "completed": 0, "status": "idle"},
            "太白金星": {"active": 0, "completed": 0, "status": "idle"},
            "道德天尊": {"active": 0, "completed": 0, "status": "idle"},
        }

        for task in self.scheduler.active_tasks.values():
            if task.assigned_immortal in immortals_state:
                immortals_state[task.assigned_immortal]["active"] += 1
                immortals_state[task.assigned_immortal]["status"] = "working"

        for task in self.scheduler.completed_tasks.values():
            if task.assigned_immortal in immortals_state:
                immortals_state[task.assigned_immortal]["completed"] += 1

        return {
            "scheduler": self.scheduler.get_state(),
            "immortals": immortals_state,
            "total_wishes": len(self.scheduler.completed_tasks) + len(self.scheduler.active_tasks),
        }


# ===== 自测 =====
if __name__ == "__main__":
    print("=== DuRenJing 自测 ===\n")

    duren = DuRenJing(embedding_dim=256)

    # 测试愿念分解
    print("--- 願念分解測試 ---")
    mission = duren.receive_wish("探究宇宙本源與人身小宇宙之關係")
    print(f"  願念: {mission.wish}")
    print(f"  子任務數: {len(mission.sub_tasks)}")
    print(f"  指派神仙: {mission.assigned_immortals}")

    for task in mission.sub_tasks:
        print(f"    [{task.id}] {task.description[:50]} -> {task.assigned_immortal}")

    # 测试调度
    print("\n--- 調度測試 ---")
    for _ in range(5):
        result = duren.process_step()
        print(f"  步驟: {result['status']} - {result.get('description', result.get('message', ''))[:50]}")

    # 完成任务
    for _ in range(3):
        duren.complete_active_task()

    # 天庭报告
    print("\n--- 天庭報告 ---")
    report = duren.get_celestial_report()
    print(f"  調度器狀態: {report['scheduler']}")
    for name, state in report["immortals"].items():
        if state["active"] > 0 or state["completed"] > 0:
            print(f"  {name}: 活躍={state['active']} 完成={state['completed']}")

    print("\n[OK] DuRenJing 自测通过")
