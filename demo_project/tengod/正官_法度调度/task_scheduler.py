#!/usr/bin/env python3
"""
task_scheduler.py — 任务调度器
正官主理法度，承担系统级任务调度的职责。
"""

import heapq
import time
import threading
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0  # 紧急
    HIGH = 1      # 高
    NORMAL = 2    # 普通
    LOW = 3       # 低


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """任务对象"""
    task_id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    max_retries: int = 0
    retry_count: int = 0

    def __lt__(self, other):
        """用于堆排序：优先级数值越小越高"""
        return self.priority.value < other.priority.value


class TaskScheduler:
    """任务调度器 — 法度之器

    负责系统级任务的有序执行，支持优先级队列、并发控制、失败重试。
    """

    def __init__(self, max_workers: int = 4):
        self._queue: List[Task] = []
        self._lock = threading.RLock()
        self._max_workers = max_workers
        self._active_count = 0
        self._tasks: Dict[str, Task] = {}
        self._shutdown = False

    def submit(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 0,
    ) -> Task:
        """提交任务"""
        if kwargs is None:
            kwargs = {}

        with self._lock:
            task = Task(
                task_id=task_id,
                func=func,
                args=args,
                kwargs=kwargs,
                priority=priority,
                max_retries=max_retries,
            )
            self._tasks[task_id] = task
            heapq.heappush(self._queue, task)
            return task

    def _execute(self, task: Task) -> None:
        """执行任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self._active_count += 1

        try:
            task.result = task.func(*task.args, **task.kwargs)
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.error = str(e)
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                with self._lock:
                    heapq.heappush(self._queue, task)
            else:
                task.status = TaskStatus.FAILED
        finally:
            task.completed_at = time.time()
            self._active_count -= 1

    def run_once(self) -> List[Task]:
        """执行一轮调度（按优先级取出可执行的任务）"""
        completed = []
        with self._lock:
            while self._queue and self._active_count < self._max_workers:
                task = heapq.heappop(self._queue)
                if task.status == TaskStatus.PENDING:
                    thread = threading.Thread(
                        target=self._execute, args=(task,), daemon=True
                    )
                    thread.start()
                    completed.append(task)
        return completed

    def run_all(self, timeout: Optional[float] = None) -> None:
        """执行所有任务直至队列清空"""
        start = time.time()
        self._shutdown = False
        while not self._shutdown and (self._queue or self._active_count > 0):
            self.run_once()
            if timeout and (time.time() - start) > timeout:
                break
            time.sleep(0.05)

    def shutdown(self) -> None:
        """关闭调度器"""
        self._shutdown = True

    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """查询任务状态"""
        with self._lock:
            task = self._tasks.get(task_id)
            return task.status if task else None

    def stats(self) -> Dict[str, int]:
        """统计信息"""
        with self._lock:
            status_count = {s.value: 0 for s in TaskStatus}
            for task in self._tasks.values():
                status_count[task.status.value] += 1
            return {
                "total": len(self._tasks),
                "queue_size": len(self._queue),
                "active": self._active_count,
                "by_status": status_count,
            }
