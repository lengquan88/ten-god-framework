#!/usr/bin/env python3
"""
search_optimizer.py — 搜索优化器
偏财主理演化，提供超参数搜索与算法调参能力。
"""

import random
import time
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
