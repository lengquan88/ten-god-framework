"""async_task_queue.py — 异步任务队列 (v2.1.0)

用 asyncio.Queue 替代当前 in-memory thread 方案，支持任务优先级。
"""
import asyncio
import inspect
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


class AsyncTaskPriority(Enum):
    """任务优先级 — 数值越小优先级越高"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class AsyncTaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class AsyncTaskItem:
    """异步任务项 — 支持优先级排序"""
    priority: int = field(compare=True)
    task_id: str = field(compare=False)
    func: Any = field(compare=False)
    func_name: str = field(compare=False)
    args: tuple = field(compare=False, default_factory=tuple)
    kwargs: dict = field(compare=False, default_factory=dict)
    created_at: float = field(compare=False, default_factory=time.time)
    status: AsyncTaskStatus = field(compare=False, default=AsyncTaskStatus.PENDING)
    started_at: Optional[float] = field(compare=False, default=None)
    completed_at: Optional[float] = field(compare=False, default=None)
    result: Any = field(compare=False, default=None)
    error: Optional[str] = field(compare=False, default=None)
    max_retries: int = field(compare=False, default=0)
    retry_count: int = field(compare=False, default=0)


class AsyncTaskQueue:
    """异步任务队列 — 优先级队列 + Worker 池

    用法：
        queue = AsyncTaskQueue(max_workers=4)
        task_id = await queue.submit(priority=AsyncTaskPriority.HIGH, func=my_func, args=(1,))
        result = await queue.get_result(task_id)
        await queue.shutdown()
    """

    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._tasks: Dict[str, AsyncTaskItem] = {}
        self._results: Dict[str, asyncio.Future] = {}
        self._shutdown = False
        self._workers: List[asyncio.Task] = []
        self._stats = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }

    async def start(self):
        """启动 Worker 协程"""
        self._workers = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(self._max_workers)
        ]

    async def _worker(self, name: str):
        """Worker 协程 — 持续从队列取任务执行"""
        while not self._shutdown:
            try:
                # 非阻塞等待，支持 shutdown 信号
                item: AsyncTaskItem = await asyncio.wait_for(
                    self._queue.get(), timeout=0.5
                )
            except asyncio.TimeoutError:
                continue

            if item.status == AsyncTaskStatus.CANCELLED:
                self._stats["cancelled"] += 1
                continue

            item.status = AsyncTaskStatus.RUNNING
            item.started_at = time.time()

            try:
                if inspect.iscoroutinefunction(item.func):
                    result = await item.func(*item.args, **item.kwargs)
                else:
                    result = item.func(*item.args, **item.kwargs)

                item.result = result
                item.status = AsyncTaskStatus.COMPLETED
                self._stats["completed"] += 1
            except Exception as e:
                item.retry_count += 1
                if item.retry_count <= item.max_retries:
                    item.status = AsyncTaskStatus.PENDING
                    item.priority = max(0, item.priority - 1)  # 提升优先级
                    await self._queue.put(item)
                    continue
                item.error = str(e)
                item.status = AsyncTaskStatus.FAILED
                self._stats["failed"] += 1
            finally:
                item.completed_at = time.time()
                if item.task_id in self._results:
                    future = self._results[item.task_id]
                    if not future.done():
                        if item.status == AsyncTaskStatus.COMPLETED:
                            future.set_result(item.result)
                        elif item.status == AsyncTaskStatus.FAILED:
                            future.set_exception(RuntimeError(item.error))

    async def submit(
        self,
        func: Union[Callable, str],
        args: tuple = (),
        kwargs: dict = None,
        priority: AsyncTaskPriority = AsyncTaskPriority.NORMAL,
        max_retries: int = 0,
        func_name: str = "",
    ) -> str:
        """提交任务到队列，返回 task_id"""
        if kwargs is None:
            kwargs = {}
        task_id = uuid.uuid4().hex[:12]

        item = AsyncTaskItem(
            priority=priority.value,
            task_id=task_id,
            func=func,
            func_name=func_name or getattr(func, "__name__", "unknown"),
            args=args,
            kwargs=kwargs,
            max_retries=max_retries,
        )
        self._tasks[task_id] = item
        self._results[task_id] = asyncio.Future()
        self._stats["submitted"] += 1
        await self._queue.put(item)
        return task_id

    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """等待任务结果"""
        if task_id not in self._results:
            raise KeyError(f"Task {task_id} not found")
        future = self._results[task_id]
        if timeout:
            return await asyncio.wait_for(future, timeout=timeout)
        return await future

    def get_task(self, task_id: str) -> Optional[AsyncTaskItem]:
        """获取任务状态"""
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[AsyncTaskStatus] = None) -> List[Dict]:
        """列出任务"""
        tasks = self._tasks.values()
        if status:
            tasks = [t for t in tasks if t.status == status]
        return [
            {
                "task_id": t.task_id,
                "func_name": t.func_name,
                "priority": t.priority,
                "status": t.status.value,
                "created_at": t.created_at,
                "retry_count": t.retry_count,
            }
            for t in sorted(tasks, key=lambda x: x.priority)
        ]

    async def cancel(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._tasks:
            item = self._tasks[task_id]
            if item.status in (AsyncTaskStatus.PENDING, AsyncTaskStatus.RUNNING):
                item.status = AsyncTaskStatus.CANCELLED
                self._stats["cancelled"] += 1
                return True
        return False

    def stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "total_tracked": len(self._tasks),
            "workers": self._max_workers,
            "shutdown": self._shutdown,
        }

    async def shutdown(self):
        """关闭队列"""
        self._shutdown = True
        for worker in self._workers:
            if not worker.done():
                worker.cancel()
        # 等待所有 worker 结束
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    @property
    def is_running(self) -> bool:
        return not self._shutdown