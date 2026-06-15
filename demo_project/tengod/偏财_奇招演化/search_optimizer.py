#!/usr/bin/env python3
"""
search_optimizer.py — 搜索优化器
偏财主理演化，提供超参数搜索与算法调参能力。
版本: 1.4.0
"""

import random
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from itertools import product


@dataclass
class SearchSpace:
    """搜索空间"""
    param_ranges: Dict[str, Any] = field(default_factory=dict)

    def sample(self) -> Dict[str, Any]:
        """随机采样一组参数"""
        result = {}
        for key, space in self.param_ranges.items():
            if isinstance(space, list):
                result[key] = random.choice(space)
            elif isinstance(space, tuple) and len(space) == 3:
                # (min, max, step) 整数范围
                lo, hi, step = space
                result[key] = random.randint(0, int((hi - lo) / step)) * step + lo
            elif isinstance(space, tuple) and len(space) == 2:
                # (min, max) 浮点范围
                lo, hi = space
                result[key] = random.uniform(lo, hi)
            else:
                result[key] = space
        return result

    def all_combinations(self) -> List[Dict[str, Any]]:
        """枚举所有组合（仅当参数空间离散时）"""
        keys = list(self.param_ranges.keys())
        value_lists = []
        for key, space in self.param_ranges.items():
            if isinstance(space, list):
                value_lists.append(space)
            elif isinstance(space, tuple) and len(space) == 3:
                lo, hi, step = space
                values = [lo + i * step for i in range(int((hi - lo) / step) + 1)]
                value_lists.append(values)
            else:
                value_lists.append([space])
        return [dict(zip(keys, combo)) for combo in product(*value_lists)]


@dataclass
class SearchResult:
    """搜索结果"""
    best_params: Dict[str, Any]
    best_score: float
    iterations: int
    history: List[Dict[str, Any]] = field(default_factory=list)
    duration: float = 0.0


class SearchOptimizer:
    """搜索优化器 — 演化之眼

    支持随机搜索与网格搜索两种模式。
    """

    def __init__(self, space: SearchSpace, mode: str = "random"):
        self._space = space
        self._mode = mode
        self._history: List[Dict[str, Any]] = []

    def optimize(
        self,
        objective: Callable[[Dict[str, Any]], float],
        n_trials: int = 20,
        maximize: bool = True,
    ) -> SearchResult:
        """执行搜索"""
        start = time.time()
        best_params: Optional[Dict[str, Any]] = None
        best_score = float("-inf") if maximize else float("inf")

        if self._mode == "grid":
            candidates = self._space.all_combinations()
            n_trials = min(n_trials, len(candidates))
            candidates = candidates[:n_trials]
        else:
            candidates = [self._space.sample() for _ in range(n_trials)]

        for i, params in enumerate(candidates):
            try:
                score = objective(params)
            except Exception as e:
                score = float("-inf") if maximize else float("inf")
                params = {"_error": str(e), **params}

            self._history.append({"trial": i, "params": params, "score": score})

            is_better = (maximize and score > best_score) or (
                not maximize and score < best_score
            )
            if is_better:
                best_score = score
                best_params = params

        return SearchResult(
            best_params=best_params or {},
            best_score=best_score,
            iterations=len(candidates),
            history=self._history.copy(),
            duration=time.time() - start,
        )

    def get_history(self) -> List[Dict[str, Any]]:
        """获取历史记录"""
        return self._history.copy()

    def optimize_async(self, objective: Callable, n_trials: int = 20, maximize: bool = True, callback=None) -> str:
        """提交到全局 AsyncOptimizer，返回 task_id"""
        from 偏财_奇招演化.search_optimizer import submit_async
        return submit_async(self._space, objective, n_trials, maximize, self._mode)

    def search(self, n_trials: int, objective: Callable, maximize: bool = True) -> str:
        """submit_async 的别名（向后兼容）"""
        return self.optimize_async(objective, n_trials, maximize)


# ─────────────────────────────────────────────────────────────────────────────
# Async Search Task & Optimizer
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class AsyncSearchTask:
    """异步搜索任务"""
    task_id: str
    status: str  # "pending" | "running" | "done" | "cancelled" | "failed"
    optimizer: SearchOptimizer
    objective: Any  # Callable（pickle不可用，所以存引用）
    n_trials: int
    maximize: bool
    result: Optional[SearchResult] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


class AsyncOptimizer:
    """异步优化器 — 支持任务提交/查询/取消/保存"""

    def __init__(self):
        self._tasks: Dict[str, AsyncSearchTask] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        space: SearchSpace,
        objective: Callable,
        n_trials: int = 20,
        maximize: bool = True,
        mode: str = "random",
    ) -> str:
        """提交搜索任务，返回 task_id（立即返回，不阻塞）"""
        task_id = str(uuid.uuid4())[:8]
        optimizer = SearchOptimizer(space, mode) if space else SearchOptimizer(SearchSpace(), mode)
        task = AsyncSearchTask(
            task_id=task_id,
            status="pending",
            optimizer=optimizer,
            objective=objective,
            n_trials=n_trials,
            maximize=maximize,
        )
        with self._lock:
            self._tasks[task_id] = task
        threading.Thread(target=self._worker, args=(task_id,), daemon=True).start()
        return task_id

    def get_status(self, task_id: str) -> Dict:
        """返回任务状态"""
        with self._lock:
            task = self._tasks.get(task_id)
        if task is None:
            return {"status": "not_found"}
        return {
            "task_id": task.task_id,
            "status": task.status,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "finished_at": task.finished_at,
            "error": task.error,
        }

    def cancel(self, task_id: str) -> bool:
        """设置状态为 cancelled（如果正在运行，下一轮循环检测到后停止）"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.status in ("done", "cancelled", "failed"):
                return False
            task.status = "cancelled"
            return True

    def get_result(self, task_id: str) -> Optional[SearchResult]:
        """获取任务结果"""
        with self._lock:
            task = self._tasks.get(task_id)
        if task is None:
            return None
        return task.result

    def list_tasks(self) -> List[Dict]:
        """列出所有任务"""
        with self._lock:
            return [
                {
                    "task_id": t.task_id,
                    "status": t.status,
                    "created_at": t.created_at,
                    "started_at": t.started_at,
                    "finished_at": t.finished_at,
                }
                for t in self._tasks.values()
            ]

    def _worker(self, task_id: str):
        """内部线程函数，执行搜索"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task.status = "running"
            task.started_at = time.time()

        try:
            if task.status == "cancelled":
                return
            result = task.optimizer.optimize(
                objective=task.objective,
                n_trials=task.n_trials,
                maximize=task.maximize,
            )

            with self._lock:
                task = self._tasks.get(task_id)
                if task is None:
                    return
                if task.status == "cancelled":
                    return
                task.result = result
                task.status = "done"
                task.finished_at = time.time()
        except Exception as e:
            with self._lock:
                task = self._tasks.get(task_id)
                if task is None:
                    return
                task.error = str(e)
                task.status = "failed"
                task.finished_at = time.time()


# ─────────────────────────────────────────────────────────────────────────────
# 全局异步优化器
# ─────────────────────────────────────────────────────────────────────────────

_global_optimizer: Optional[AsyncOptimizer] = None


def get_async_optimizer() -> AsyncOptimizer:
    """获取全局异步优化器实例"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = AsyncOptimizer()
    return _global_optimizer


def submit_async(space, objective, n_trials=20, maximize=True, mode="random") -> str:
    """全局异步优化器提交任务"""
    return get_async_optimizer().submit(space, objective, n_trials, maximize, mode)


__all__ = [
    "SearchSpace",
    "SearchResult",
    "SearchOptimizer",
    "AsyncSearchTask",
    "AsyncOptimizer",
    "submit_async",
    "get_async_optimizer",
]
