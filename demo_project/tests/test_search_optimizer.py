#!/usr/bin/env python3
"""
test_search_optimizer.py — 搜索优化器模块综合测试
覆盖 SearchSpace, SearchResult, SearchOptimizer, AsyncSearchTask, AsyncOptimizer
"""

import math
import sys
import time
import pytest
from unittest.mock import patch

from tengod.偏财_奇招演化.search_optimizer import (
    SearchSpace,
    SearchResult,
    SearchOptimizer,
    AsyncSearchTask,
    AsyncOptimizer,
    get_async_optimizer,
    submit_async,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def simple_objective():
    """简单目标函数：最小化 (x-2)^2 + (y-3)^2"""
    def _objective(params):
        x = params.get("x", 0)
        y = params.get("y", 0)
        return (x - 2) ** 2 + (y - 3) ** 2
    return _objective


@pytest.fixture
def raising_objective():
    """会抛出异常的目标函数"""
    def _objective(params):
        if params.get("fail", False):
            raise ValueError("intentional failure")
        return 1.0
    return _objective


@pytest.fixture
def discrete_space():
    """离散参数搜索空间"""
    return SearchSpace(param_ranges={
        "a": [1, 2, 3],
        "b": [10, 20],
        "c": ["x", "y"],
    })


@pytest.fixture
def mixed_space():
    """混合参数搜索空间"""
    return SearchSpace(param_ranges={
        "lr": (0.001, 0.1),          # float range
        "batch": (16, 64, 16),       # int range with step
        "optimizer": ["adam", "sgd"],  # discrete list
        "seed": 42,                   # scalar
    })


@pytest.fixture
def simple_space():
    """简单搜索空间"""
    return SearchSpace(param_ranges={
        "x": (0.0, 10.0),
        "y": (0.0, 10.0),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SearchSpace 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestSearchSpaceSample:
    """测试 SearchSpace.sample()"""

    def test_sample_list_params(self):
        """列表参数：随机选择列表中的值"""
        space = SearchSpace(param_ranges={"color": ["red", "green", "blue"]})
        for _ in range(20):
            result = space.sample()
            assert result["color"] in ["red", "green", "blue"]

    def test_sample_tuple_int_params(self):
        """三元组 (min, max, step) 整数参数"""
        space = SearchSpace(param_ranges={"n": (0, 10, 2)})
        for _ in range(30):
            result = space.sample()
            assert result["n"] in [0, 2, 4, 6, 8, 10]
            assert isinstance(result["n"], int)

    def test_sample_tuple_float_params(self):
        """二元组 (min, max) 浮点参数"""
        space = SearchSpace(param_ranges={"rate": (0.0, 1.0)})
        for _ in range(20):
            result = space.sample()
            assert 0.0 <= result["rate"] <= 1.0
            assert isinstance(result["rate"], float)

    def test_sample_scalar_params(self):
        """标量参数：直接返回标量"""
        space = SearchSpace(param_ranges={"fixed": 42, "name": "test"})
        result = space.sample()
        assert result["fixed"] == 42
        assert result["name"] == "test"

    def test_sample_mixed_params(self, mixed_space):
        """混合参数空间采样"""
        result = mixed_space.sample()
        assert 0.001 <= result["lr"] <= 0.1
        assert result["batch"] in [16, 32, 48, 64]
        assert result["optimizer"] in ["adam", "sgd"]
        assert result["seed"] == 42

    def test_sample_empty_space(self):
        """空搜索空间采样"""
        space = SearchSpace(param_ranges={})
        result = space.sample()
        assert result == {}


class TestSearchSpaceAllCombinations:
    """测试 SearchSpace.all_combinations()"""

    def test_all_combinations_discrete(self, discrete_space):
        """离散参数：枚举所有组合"""
        combos = discrete_space.all_combinations()
        # 3 * 2 * 2 = 12 combinations
        assert len(combos) == 12
        assert isinstance(combos, list)
        for combo in combos:
            assert set(combo.keys()) == {"a", "b", "c"}

    def test_all_combinations_mixed(self, mixed_space):
        """混合参数：枚举所有组合（包含int range）"""
        combos = mixed_space.all_combinations()
        # lr: 2-tuple → scalar (whole tuple), batch: 4, optimizer: 2, seed: 1
        # Total: 1 * 4 * 2 * 1 = 8
        assert len(combos) == 8
        for combo in combos:
            assert set(combo.keys()) == {"lr", "batch", "optimizer", "seed"}
            assert combo["optimizer"] in ["adam", "sgd"]
            assert combo["batch"] in [16, 32, 48, 64]
            # (0.001, 0.1) — 2-tuple treated as scalar in all_combinations()
            assert combo["lr"] == (0.001, 0.1)
            assert combo["seed"] == 42

    def test_all_combinations_int_range(self):
        """整数范围：枚举所有取值"""
        space = SearchSpace(param_ranges={"n": (0, 4, 1)})
        combos = space.all_combinations()
        assert len(combos) == 5
        values = [c["n"] for c in combos]
        assert values == [0, 1, 2, 3, 4]

    def test_all_combinations_empty(self):
        """空搜索空间"""
        space = SearchSpace(param_ranges={})
        combos = space.all_combinations()
        assert combos == [{}]

    def test_all_combinations_scalar_only(self):
        """纯标量搜索空间"""
        space = SearchSpace(param_ranges={"a": 1, "b": 2})
        combos = space.all_combinations()
        assert len(combos) == 1
        assert combos[0] == {"a": 1, "b": 2}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SearchResult 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestSearchResult:
    """测试 SearchResult 数据类"""

    def test_create_result(self):
        result = SearchResult(
            best_params={"x": 2.0, "y": 3.0},
            best_score=0.0,
            iterations=100,
            history=[{"trial": 0, "params": {"x": 1.0}, "score": 5.0}],
            duration=0.5,
            method_name="random_search",
        )
        assert result.best_params == {"x": 2.0, "y": 3.0}
        assert result.best_score == 0.0
        assert result.iterations == 100
        assert len(result.history) == 1
        assert result.duration == 0.5
        assert result.method_name == "random_search"

    def test_default_values(self):
        result = SearchResult(
            best_params={},
            best_score=float("inf"),
            iterations=0,
        )
        assert result.history == []
        assert result.duration == 0.0
        assert result.method_name == "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SearchOptimizer 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestSearchOptimizerInit:
    """测试 SearchOptimizer.__init__()"""

    def test_init_random_mode(self, simple_space):
        opt = SearchOptimizer(simple_space, mode="random")
        assert opt._mode == "random"
        assert opt._history == []

    def test_init_grid_mode(self, simple_space):
        opt = SearchOptimizer(simple_space, mode="grid")
        assert opt._mode == "grid"

    def test_init_default_mode(self, simple_space):
        opt = SearchOptimizer(simple_space)
        assert opt._mode == "random"


class TestSearchOptimizerOptimize:
    """测试 SearchOptimizer.optimize()"""

    def test_optimize_random_mode(self, simple_space, simple_objective):
        opt = SearchOptimizer(simple_space, mode="random")
        result = opt.optimize(simple_objective, n_trials=50, maximize=False)

        assert result.iterations == 50
        assert result.method_name == "random_search"
        assert result.duration >= 0
        # 随机搜索在50次中应找到小于10的最优值（目标函数 min 在 x=2, y=3 处为0）
        assert result.best_score < 10.0
        assert "x" in result.best_params
        assert "y" in result.best_params
        assert len(result.history) == 50

    def test_optimize_grid_mode(self, discrete_space):
        opt = SearchOptimizer(discrete_space, mode="grid")
        # 目标：最小化 a + b
        def objective(params):
            a = params["a"]
            b = params["b"]
            return a + b

        result = opt.optimize(objective, n_trials=12, maximize=False)
        assert result.iterations == 12
        assert result.method_name == "grid_search"
        # a in [1,2,3], b in [10,20], min = a=1, b=10 => 11
        assert result.best_score == 11

    def test_optimize_grid_mode_truncated(self, discrete_space):
        """grid mode with n_trials less than total combinations"""
        opt = SearchOptimizer(discrete_space, mode="grid")
        def objective(params):
            return params["a"]

        result = opt.optimize(objective, n_trials=5, maximize=False)
        assert result.iterations == 5
        assert result.method_name == "grid_search"

    def test_optimize_maximize(self, simple_space):
        """最大化目标函数"""
        opt = SearchOptimizer(simple_space, mode="random")
        def objective(params):
            return -(params["x"] ** 2 + params["y"] ** 2)  # 越接近0越好

        result = opt.optimize(objective, n_trials=30, maximize=True)
        assert result.best_score <= 0

    def test_optimize_maximize_false(self, simple_space, simple_objective):
        """maximize=False 最小化"""
        opt = SearchOptimizer(simple_space, mode="random")
        result = opt.optimize(simple_objective, n_trials=30, maximize=False)
        assert result.best_score >= 0

    def test_optimize_objective_raises(self, simple_space, raising_objective):
        """目标函数抛出异常时继续搜索"""
        opt = SearchOptimizer(simple_space, mode="random")
        # 使用一个会抛异常的函数，但参数不会触发 fail
        result = opt.optimize(raising_objective, n_trials=20, maximize=False)
        assert result.iterations == 20
        assert result.best_score == 1.0

    def test_optimize_objective_raises_with_fail_param(self):
        """目标函数抛出异常时，错误被捕获并记录"""
        space = SearchSpace(param_ranges={"fail": [True, False], "x": [1, 2, 3]})
        opt = SearchOptimizer(space, mode="grid")

        def obj(params):
            if params["fail"]:
                raise RuntimeError("forced error")
            return params["x"]

        result = opt.optimize(obj, n_trials=6, maximize=False)
        history = opt.get_history()
        error_entries = [h for h in history if "_error" in h["params"]]
        assert len(error_entries) > 0

    def test_optimize_no_trials(self, simple_space, simple_objective):
        """n_trials=0 时"""
        opt = SearchOptimizer(simple_space, mode="random")
        result = opt.optimize(simple_objective, n_trials=0, maximize=False)
        assert result.iterations == 0
        assert result.best_params == {}
        assert result.history == []


class TestSearchOptimizerGetHistory:
    """测试 get_history()"""

    def test_get_history_returns_copy(self, simple_space):
        opt = SearchOptimizer(simple_space, mode="random")
        def obj(p):
            return p["x"]
        result = opt.optimize(obj, n_trials=5, maximize=False)

        history = opt.get_history()
        assert len(history) == 5
        # 验证返回的是副本
        history.append({"trial": 999, "params": {}, "score": 999})
        assert len(opt.get_history()) == 5  # 原始数据未变

    def test_get_history_empty(self, simple_space):
        opt = SearchOptimizer(simple_space)
        assert opt.get_history() == []


class TestSearchOptimizerOptimizeBayes:
    """测试 optimize_bayes()"""

    def test_optimize_bayes_basic(self, simple_space):
        """贝叶斯优化基本测试"""
        opt = SearchOptimizer(simple_space, mode="random")
        def objective(params):
            return (params["x"] - 5.0) ** 2 + (params["y"] - 5.0) ** 2

        result = opt.optimize_bayes(objective, n_trials=20, maximize=False)
        assert result.iterations == 20
        assert result.method_name == "bayes_search"
        assert result.duration >= 0
        assert "x" in result.best_params
        assert "y" in result.best_params

    def test_optimize_bayes_with_random_state(self, simple_space):
        """random_state 确保确定性"""
        def objective(params):
            return params["x"] + params["y"]

        opt1 = SearchOptimizer(simple_space, mode="random")
        result1 = opt1.optimize_bayes(objective, n_trials=10, maximize=False, random_state=42)

        opt2 = SearchOptimizer(simple_space, mode="random")
        result2 = opt2.optimize_bayes(objective, n_trials=10, maximize=False, random_state=42)

        assert result1.best_score == result2.best_score
        assert result1.iterations == result2.iterations

    def test_optimize_bayes_maximize(self, simple_space):
        """贝叶斯优化最大化"""
        opt = SearchOptimizer(simple_space, mode="random")
        def objective(params):
            return -(params["x"] ** 2 + params["y"] ** 2)

        result = opt.optimize_bayes(objective, n_trials=10, maximize=True)
        assert result.iterations == 10
        assert result.method_name == "bayes_search"

    def test_optimize_bayes_objective_raises(self, simple_space):
        """贝叶斯优化中目标函数抛出异常"""
        opt = SearchOptimizer(simple_space, mode="random")
        call_count = [0]

        def objective(params):
            call_count[0] += 1
            if call_count[0] == 2:
                raise ValueError("bayes error")
            return params["x"]

        result = opt.optimize_bayes(objective, n_trials=10, maximize=False)
        assert result.iterations == 10


class TestSearchOptimizerOptimizeAsync:
    """测试 optimize_async() 和 search()"""

    @pytest.fixture(autouse=True)
    def _patch_import(self):
        """源码中 from 偏财_奇招演化.search_optimizer import submit_async
        路径不正确，需要将 偏财_奇招演化 映射到 tengod.偏财_奇招演化"""
        import tengod.偏财_奇招演化 as _pkg
        sys.modules["偏财_奇招演化"] = _pkg
        # 确保子模块也可导入
        import tengod.偏财_奇招演化.search_optimizer as _so
        sys.modules["偏财_奇招演化.search_optimizer"] = _so
        yield
        sys.modules.pop("偏财_奇招演化", None)
        sys.modules.pop("偏财_奇招演化.search_optimizer", None)

    def test_optimize_async(self, simple_space):
        """optimize_async 提交任务并返回 task_id"""
        opt = SearchOptimizer(simple_space, mode="random")
        def objective(params):
            return params["x"]

        task_id = opt.optimize_async(objective, n_trials=5, maximize=False)
        assert isinstance(task_id, str)
        assert len(task_id) > 0

        # 等待任务完成
        time.sleep(0.5)
        ao = get_async_optimizer()
        result = ao.get_result(task_id)
        assert result is not None, f"task status: {ao.get_status(task_id)}"
        assert result.iterations == 5

    def test_search_alias(self, simple_space):
        """search() 是 optimize_async 的别名"""
        opt = SearchOptimizer(simple_space, mode="random")
        def objective(params):
            return params["x"]

        task_id = opt.search(n_trials=3, objective=objective, maximize=False)
        assert isinstance(task_id, str)

        time.sleep(0.3)
        ao = get_async_optimizer()
        result = ao.get_result(task_id)
        assert result is not None, f"task status: {ao.get_status(task_id)}"
        assert result.iterations == 3


# ═══════════════════════════════════════════════════════════════════════════════
# 4. AsyncSearchTask 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsyncSearchTask:
    """测试 AsyncSearchTask 数据类"""

    def test_create_task(self, simple_space):
        opt = SearchOptimizer(simple_space)
        task = AsyncSearchTask(
            task_id="test-001",
            status="pending",
            optimizer=opt,
            objective=lambda p: 1.0,
            n_trials=10,
            maximize=True,
        )
        assert task.task_id == "test-001"
        assert task.status == "pending"
        assert task.n_trials == 10
        assert task.maximize is True
        assert task.result is None
        assert task.error is None
        assert task.created_at > 0
        assert task.started_at is None
        assert task.finished_at is None

    def test_task_with_result_and_error(self, simple_space):
        opt = SearchOptimizer(simple_space)
        result = SearchResult(
            best_params={"x": 1.0},
            best_score=0.5,
            iterations=10,
        )
        task = AsyncSearchTask(
            task_id="test-002",
            status="done",
            optimizer=opt,
            objective=lambda p: 1.0,
            n_trials=10,
            maximize=True,
            result=result,
            error="some error",
            started_at=1000.0,
            finished_at=2000.0,
        )
        assert task.result is result
        assert task.error == "some error"
        assert task.started_at == 1000.0
        assert task.finished_at == 2000.0


# ═══════════════════════════════════════════════════════════════════════════════
# 5. AsyncOptimizer 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsyncOptimizerSubmit:
    """测试 AsyncOptimizer.submit()"""

    def test_submit_returns_task_id(self, simple_space):
        ao = AsyncOptimizer()
        def objective(params):
            return params["x"]

        task_id = ao.submit(simple_space, objective, n_trials=5, maximize=False)
        assert isinstance(task_id, str)
        assert len(task_id) == 8
        # 等待完成
        time.sleep(0.3)
        status = ao.get_status(task_id)
        assert status["status"] in ("done", "running")

    def test_submit_with_defaults(self, simple_space):
        ao = AsyncOptimizer()
        task_id = ao.submit(simple_space, lambda p: 1.0)
        assert isinstance(task_id, str)

        time.sleep(0.3)
        result = ao.get_result(task_id)
        assert result is not None
        assert result.iterations == 20  # default n_trials

    def test_submit_multiple_tasks(self, simple_space):
        ao = AsyncOptimizer()
        task_ids = []
        for i in range(3):
            tid = ao.submit(simple_space, lambda p: p["x"], n_trials=2, maximize=False)
            task_ids.append(tid)

        assert len(task_ids) == len(set(task_ids))  # unique IDs

        time.sleep(0.5)
        for tid in task_ids:
            status = ao.get_status(tid)
            assert status["status"] == "done"


class TestAsyncOptimizerGetStatus:
    """测试 AsyncOptimizer.get_status()"""

    def test_get_status_existing(self, simple_space):
        ao = AsyncOptimizer()
        task_id = ao.submit(simple_space, lambda p: 1.0, n_trials=2)
        status = ao.get_status(task_id)
        assert status["task_id"] == task_id
        assert status["status"] in ("pending", "running", "done")
        assert "created_at" in status

    def test_get_status_non_existing(self):
        ao = AsyncOptimizer()
        status = ao.get_status("nonexistent")
        assert status == {"status": "not_found"}


class TestAsyncOptimizerCancel:
    """测试 AsyncOptimizer.cancel()"""

    def test_cancel_non_existing(self):
        ao = AsyncOptimizer()
        assert ao.cancel("nonexistent") is False

    def test_cancel_pending_task(self, simple_space):
        """取消一个 pending 状态的任务"""
        ao = AsyncOptimizer()
        # 直接创建任务不通过 submit（避免 worker 线程启动）
        task_id = "direct-cancel-test"
        opt = SearchOptimizer(simple_space)
        task = AsyncSearchTask(
            task_id=task_id,
            status="pending",
            optimizer=opt,
            objective=lambda p: 1.0,
            n_trials=5,
            maximize=True,
        )
        with ao._lock:
            ao._tasks[task_id] = task

        assert ao.cancel(task_id) is True
        assert ao.get_status(task_id)["status"] == "cancelled"

    def test_cancel_already_done(self, simple_space):
        """取消一个已完成的任务应返回 False"""
        ao = AsyncOptimizer()
        task_id = "done-cancel-test"
        opt = SearchOptimizer(simple_space)
        task = AsyncSearchTask(
            task_id=task_id,
            status="done",
            optimizer=opt,
            objective=lambda p: 1.0,
            n_trials=5,
            maximize=True,
        )
        with ao._lock:
            ao._tasks[task_id] = task

        assert ao.cancel(task_id) is False

    def test_cancel_already_cancelled(self, simple_space):
        """取消一个已取消的任务应返回 False"""
        ao = AsyncOptimizer()
        task_id = "cancelled-test"
        opt = SearchOptimizer(simple_space)
        task = AsyncSearchTask(
            task_id=task_id,
            status="cancelled",
            optimizer=opt,
            objective=lambda p: 1.0,
            n_trials=5,
            maximize=True,
        )
        with ao._lock:
            ao._tasks[task_id] = task

        assert ao.cancel(task_id) is False


class TestAsyncOptimizerGetResult:
    """测试 AsyncOptimizer.get_result()"""

    def test_get_result_before_completion(self, simple_space):
        ao = AsyncOptimizer()
        task_id = ao.submit(simple_space, lambda p: p["x"], n_trials=5, maximize=False)
        # 立即查询可能还没完成
        result = ao.get_result(task_id)
        if result is None:
            time.sleep(0.3)
            result = ao.get_result(task_id)
        assert result is not None

    def test_get_result_after_completion(self, simple_space):
        ao = AsyncOptimizer()
        task_id = ao.submit(simple_space, lambda p: p["x"], n_trials=3, maximize=False)
        time.sleep(0.3)
        result = ao.get_result(task_id)
        assert result is not None
        assert isinstance(result, SearchResult)
        assert result.iterations == 3

    def test_get_result_non_existing(self):
        ao = AsyncOptimizer()
        assert ao.get_result("nonexistent") is None


class TestAsyncOptimizerListTasks:
    """测试 AsyncOptimizer.list_tasks()"""

    def test_list_tasks_empty(self):
        ao = AsyncOptimizer()
        tasks = ao.list_tasks()
        assert tasks == []

    def test_list_tasks_with_entries(self, simple_space):
        ao = AsyncOptimizer()
        task_id = ao.submit(simple_space, lambda p: 1.0, n_trials=2)
        time.sleep(0.2)
        tasks = ao.list_tasks()
        assert len(tasks) >= 1
        task_ids = [t["task_id"] for t in tasks]
        assert task_id in task_ids
        for t in tasks:
            assert "status" in t
            assert "created_at" in t


class TestAsyncOptimizerWorker:
    """测试 _worker() 内部方法"""

    def test_worker_successful(self, simple_space):
        """_worker 成功执行搜索"""
        ao = AsyncOptimizer()
        task_id = "worker-success-test"
        opt = SearchOptimizer(simple_space, mode="random")

        def objective(params):
            return params["x"]

        task = AsyncSearchTask(
            task_id=task_id,
            status="pending",
            optimizer=opt,
            objective=objective,
            n_trials=3,
            maximize=False,
        )
        with ao._lock:
            ao._tasks[task_id] = task

        ao._worker(task_id)
        assert task.status == "done"
        assert task.result is not None
        assert task.finished_at is not None
        assert task.error is None

    def test_worker_failed(self, simple_space):
        """_worker 中 optimize() 本身抛出异常"""
        ao = AsyncOptimizer()
        task_id = "worker-fail-test"
        opt = SearchOptimizer(simple_space, mode="random")

        def bad_objective(params):
            return params["x"]

        task = AsyncSearchTask(
            task_id=task_id,
            status="pending",
            optimizer=opt,
            objective=bad_objective,
            n_trials=3,
            maximize=False,
        )
        with ao._lock:
            ao._tasks[task_id] = task

        # 让 optimize() 本身抛出异常（目标函数被 optimize 内部捕获，不会传播到 _worker）
        with patch.object(opt, "optimize", side_effect=RuntimeError("worker failure")):
            ao._worker(task_id)

        assert task.status == "failed"
        assert task.error is not None
        assert "worker failure" in task.error
        assert task.result is None
        assert task.finished_at is not None

    def test_worker_nonexistent_task(self):
        """_worker 处理不存在的任务"""
        ao = AsyncOptimizer()
        # 不应抛出异常
        ao._worker("nonexistent-task")

    def test_worker_cancelled_before_start(self, simple_space):
        """_worker 在任务被取消后仍然执行（_worker 先设 running 再检查 cancelled）"""
        ao = AsyncOptimizer()
        task_id = "worker-cancelled-test"
        opt = SearchOptimizer(simple_space, mode="random")

        task = AsyncSearchTask(
            task_id=task_id,
            status="cancelled",  # 已经是 cancelled
            optimizer=opt,
            objective=lambda p: p["x"],
            n_trials=3,
            maximize=False,
        )
        with ao._lock:
            ao._tasks[task_id] = task

        ao._worker(task_id)
        # _worker 先将 status 设为 "running"，然后执行 optimize，
        # 由于 optimize 成功，status 最终为 "done"
        assert task.status == "done"
        assert task.result is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 6. get_async_optimizer() 单例测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetAsyncOptimizer:
    """测试 get_async_optimizer() 单例"""

    def test_singleton(self):
        """多次调用返回同一实例"""
        ao1 = get_async_optimizer()
        ao2 = get_async_optimizer()
        assert ao1 is ao2

    def test_returns_async_optimizer(self):
        ao = get_async_optimizer()
        assert isinstance(ao, AsyncOptimizer)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. submit_async() 便捷函数测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestSubmitAsync:
    """测试 submit_async() 便捷函数"""

    def test_submit_async_returns_task_id(self, simple_space):
        def objective(params):
            return params["x"]

        task_id = submit_async(simple_space, objective, n_trials=3, maximize=False)
        assert isinstance(task_id, str)
        assert len(task_id) == 8

        time.sleep(0.3)
        ao = get_async_optimizer()
        result = ao.get_result(task_id)
        assert result is not None
        assert result.iterations == 3

    def test_submit_async_with_defaults(self, simple_space):
        task_id = submit_async(simple_space, lambda p: 1.0)
        assert isinstance(task_id, str)

        time.sleep(0.3)
        ao = get_async_optimizer()
        result = ao.get_result(task_id)
        assert result is not None
        assert result.iterations == 20


# ═══════════════════════════════════════════════════════════════════════════════
# 8. 边界条件与边缘情况测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """测试边界条件"""

    def test_empty_param_ranges(self):
        """空 param_ranges"""
        space = SearchSpace(param_ranges={})
        assert space.sample() == {}
        assert space.all_combinations() == [{}]

        opt = SearchOptimizer(space, mode="random")
        def objective(params):
            return 0.0

        result = opt.optimize(objective, n_trials=5, maximize=False)
        assert result.iterations == 5
        assert result.best_params == {}
        assert result.best_score == 0.0

    def test_zero_trials_random(self):
        """n_trials=0 随机搜索"""
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})
        opt = SearchOptimizer(space, mode="random")
        def objective(params):
            return params["x"]

        result = opt.optimize(objective, n_trials=0, maximize=False)
        assert result.iterations == 0
        assert result.best_params == {}
        assert result.best_score == float("inf")

    def test_zero_trials_grid(self):
        """n_trials=0 网格搜索"""
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})
        opt = SearchOptimizer(space, mode="grid")
        def objective(params):
            return params["x"]

        result = opt.optimize(objective, n_trials=0, maximize=False)
        assert result.iterations == 0
        assert result.best_params == {}

    def test_large_n_trials_random(self, simple_space):
        """大 n_trials 随机搜索"""
        opt = SearchOptimizer(simple_space, mode="random")
        result = opt.optimize(lambda p: p["x"], n_trials=200, maximize=False)
        assert result.iterations == 200
        assert len(result.history) == 200

    def test_grid_mode_fewer_combinations_than_trials(self, discrete_space):
        """网格搜索：n_trials > 组合数时截断"""
        opt = SearchOptimizer(discrete_space, mode="grid")
        # 只有12个组合，请求100个
        result = opt.optimize(lambda p: p["a"], n_trials=100, maximize=False)
        assert result.iterations == 12  # truncated to total combinations

    def test_single_param_search(self):
        """单参数搜索"""
        space = SearchSpace(param_ranges={"x": [1, 2, 3, 4, 5]})
        opt = SearchOptimizer(space, mode="grid")
        result = opt.optimize(lambda p: p["x"], n_trials=5, maximize=False)
        assert result.best_score == 1
        assert result.best_params == {"x": 1}

    def test_maximize_inf_initial(self, simple_space):
        """maximize=True 时初始 best_score 为 -inf"""
        opt = SearchOptimizer(simple_space, mode="random")
        result = opt.optimize(lambda p: p["x"], n_trials=5, maximize=True)
        assert result.best_score != float("-inf")

    def test_minimize_inf_initial(self, simple_space):
        """maximize=False 时初始 best_score 为 inf"""
        opt = SearchOptimizer(simple_space, mode="random")
        result = opt.optimize(lambda p: p["x"], n_trials=5, maximize=False)
        assert result.best_score != float("inf")

    def test_bayes_small_trials(self, simple_space):
        """贝叶斯优化少量试验"""
        opt = SearchOptimizer(simple_space, mode="random")
        result = opt.optimize_bayes(lambda p: p["x"], n_trials=1, maximize=False)
        assert result.iterations == 1
        assert result.method_name == "bayes_search"

    def test_bayes_no_random_state(self, simple_space):
        """贝叶斯优化不指定 random_state"""
        opt = SearchOptimizer(simple_space, mode="random")
        result = opt.optimize_bayes(lambda p: p["x"], n_trials=5, maximize=False)
        assert result.iterations == 5
        assert result.method_name == "bayes_search"

    def test_bayes_init_trials_less_than_3(self, simple_space):
        """贝叶斯优化 n_trials < 3 时初始点数调整"""
        opt = SearchOptimizer(simple_space, mode="random")
        result = opt.optimize_bayes(lambda p: p["x"], n_trials=2, maximize=False)
        assert result.iterations == 2

    def test_all_combinations_mixed_with_float_tuple(self):
        """混合参数中 float tuple 被 all_combinations 当作 scalar"""
        space = SearchSpace(param_ranges={
            "lr": (0.001, 0.1),
            "batch": [16, 32],
        })
        combos = space.all_combinations()
        # lr: 2-tuple → scalar (whole tuple stored), batch: list → 2 values
        assert len(combos) == 2
        assert combos[0]["lr"] == (0.001, 0.1)

    def test_optimize_maximize_with_errors(self):
        """最大化时目标函数抛出异常，score 设为 -inf"""
        space = SearchSpace(param_ranges={"fail": [True], "x": [1]})
        opt = SearchOptimizer(space, mode="grid")

        def obj(params):
            if params.get("fail"):
                raise ValueError("error")
            return params["x"]

        result = opt.optimize(obj, n_trials=1, maximize=True)
        assert result.best_score == float("-inf")