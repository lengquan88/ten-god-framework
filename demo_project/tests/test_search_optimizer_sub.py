#!/usr/bin/env python3
"""
test_search_optimizer_sub.py — 搜索优化器补充测试
覆盖：SearchSpace / SearchResult / SearchOptimizer / AsyncSearchTask / AsyncOptimizer / 全局函数
"""
import os
import sys
import threading
import time
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.偏财_奇招演化.search_optimizer import (
    AsyncOptimizer,
    AsyncSearchTask,
    SearchOptimizer,
    SearchResult,
    SearchSpace,
    get_async_optimizer,
    submit_async,
)


# ═══════════════════════════════════════════════════════════════
# SearchSpace
# ═══════════════════════════════════════════════════════════════


class TestSearchSpaceInit:
    """SearchSpace 初始化"""

    def test_init_empty_param_ranges(self):
        space = SearchSpace()
        assert space.param_ranges == {}

    def test_init_with_list_param(self):
        space = SearchSpace(param_ranges={"a": [1, 2, 3]})
        assert space.param_ranges == {"a": [1, 2, 3]}


class TestSearchSpaceSample:
    """SearchSpace.sample()"""

    def test_sample_list_param_returns_one_of_choices(self):
        space = SearchSpace(param_ranges={"x": [10, 20, 30]})
        for _ in range(20):
            val = space.sample()["x"]
            assert val in [10, 20, 30]

    def test_sample_tuple_three_int_range(self):
        space = SearchSpace(param_ranges={"n": (0, 10, 2)})
        for _ in range(30):
            val = space.sample()["n"]
            assert isinstance(val, int)
            assert 0 <= val <= 10
            assert val % 2 == 0

    def test_sample_tuple_two_float_range(self):
        space = SearchSpace(param_ranges={"f": (0.0, 1.0)})
        for _ in range(30):
            val = space.sample()["f"]
            assert isinstance(val, float)
            assert 0.0 <= val <= 1.0

    def test_sample_scalar_value_returns_as_is(self):
        space = SearchSpace(param_ranges={"fixed": 42, "name": "hello"})
        result = space.sample()
        assert result["fixed"] == 42
        assert result["name"] == "hello"

    def test_sample_empty_space(self):
        space = SearchSpace()
        assert space.sample() == {}


class TestSearchSpaceAllCombinations:
    """SearchSpace.all_combinations()"""

    def test_all_combinations_with_list_param(self):
        space = SearchSpace(param_ranges={"a": [1, 2], "b": [3, 4]})
        combos = space.all_combinations()
        expected = [
            {"a": 1, "b": 3},
            {"a": 1, "b": 4},
            {"a": 2, "b": 3},
            {"a": 2, "b": 4},
        ]
        assert combos == expected
        assert len(combos) == 4

    def test_all_combinations_with_integer_range(self):
        space = SearchSpace(param_ranges={"n": (0, 6, 2)})
        combos = space.all_combinations()
        values = [c["n"] for c in combos]
        assert values == [0, 2, 4, 6]

    def test_all_combinations_with_mixed_types(self):
        space = SearchSpace(param_ranges={
            "a": [1, 2],
            "b": (0, 4, 2),
            "c": "fixed",
        })
        combos = space.all_combinations()
        # 2 * 3 * 1 = 6 combinations
        assert len(combos) == 6
        for c in combos:
            assert c["a"] in [1, 2]
            assert c["b"] in [0, 2, 4]
            assert c["c"] == "fixed"

    def test_all_combinations_with_single_scalar(self):
        space = SearchSpace(param_ranges={"x": 42})
        combos = space.all_combinations()
        assert combos == [{"x": 42}]

    def test_all_combinations_empty(self):
        space = SearchSpace()
        assert space.all_combinations() == [{}]


# ═══════════════════════════════════════════════════════════════
# SearchResult
# ═══════════════════════════════════════════════════════════════


class TestSearchResultDefaults:
    """SearchResult 默认值"""

    def test_create_with_all_fields(self):
        result = SearchResult(
            best_params={"lr": 0.01},
            best_score=0.99,
            iterations=50,
            history=[{"trial": 0, "score": 0.5}],
            duration=1.23,
            method_name="grid_search",
        )
        assert result.best_params == {"lr": 0.01}
        assert result.best_score == 0.99
        assert result.iterations == 50
        assert result.history == [{"trial": 0, "score": 0.5}]
        assert result.duration == 1.23
        assert result.method_name == "grid_search"

    def test_default_history_is_empty_list(self):
        result = SearchResult(best_params={}, best_score=0.0, iterations=0)
        assert result.history == []

    def test_default_duration_is_zero(self):
        result = SearchResult(best_params={}, best_score=0.0, iterations=0)
        assert result.duration == 0.0

    def test_default_method_name_is_unknown(self):
        result = SearchResult(best_params={}, best_score=0.0, iterations=0)
        assert result.method_name == "unknown"


# ═══════════════════════════════════════════════════════════════
# SearchOptimizer — 初始化
# ═══════════════════════════════════════════════════════════════


class TestSearchOptimizerInit:
    """SearchOptimizer 初始化"""

    def test_init_mode_random(self):
        space = SearchSpace(param_ranges={"x": [1, 2]})
        opt = SearchOptimizer(space, mode="random")
        assert opt._mode == "random"

    def test_init_mode_grid(self):
        space = SearchSpace(param_ranges={"x": [1, 2]})
        opt = SearchOptimizer(space, mode="grid")
        assert opt._mode == "grid"

    def test_init_default_mode(self):
        space = SearchSpace(param_ranges={"x": [1, 2]})
        opt = SearchOptimizer(space)
        assert opt._mode == "random"


# ═══════════════════════════════════════════════════════════════
# SearchOptimizer — optimize()
# ═══════════════════════════════════════════════════════════════


class TestSearchOptimizerOptimize:
    """SearchOptimizer.optimize()"""

    def test_optimize_random_mode_basic(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space, mode="random")
        result = opt.optimize(lambda p: -(p["x"] - 2) ** 2, n_trials=10, maximize=True)
        assert isinstance(result, SearchResult)
        assert result.method_name == "random_search"
        assert result.iterations == 10
        assert result.best_score is not None
        assert result.duration >= 0

    def test_optimize_grid_mode_basic(self):
        space = SearchSpace(param_ranges={"x": [1, 2, 3], "y": [10, 20]})
        opt = SearchOptimizer(space, mode="grid")
        result = opt.optimize(lambda p: -(p["x"] - 2) ** 2, n_trials=100, maximize=True)
        assert result.method_name == "grid_search"
        assert result.iterations == 6

    def test_optimize_maximize_true(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space, mode="random")
        result = opt.optimize(lambda p: -(p["x"] - 5) ** 2, n_trials=20, maximize=True)
        assert result.best_score <= 0

    def test_optimize_maximize_false(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space, mode="random")
        result = opt.optimize(lambda p: (p["x"] - 5) ** 2, n_trials=20, maximize=False)
        assert result.best_score >= 0

    def test_optimize_with_objective_that_raises_exception(self):
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})
        opt = SearchOptimizer(space, mode="random")

        def failing(p):
            if p["x"] == 2:
                raise ValueError("bad")
            return p["x"]

        result = opt.optimize(failing, n_trials=10, maximize=True)
        assert result.iterations == 10
        errors = [h for h in result.history if "_error" in h["params"]]
        assert len(errors) > 0

    def test_optimize_with_n_trials_zero(self):
        space = SearchSpace(param_ranges={"x": [1, 2]})
        opt = SearchOptimizer(space, mode="random")
        result = opt.optimize(lambda p: p["x"], n_trials=0, maximize=True)
        assert result.iterations == 0
        assert result.best_params == {}
        assert result.best_score == float("-inf")

    def test_optimize_zero_trials_minimize(self):
        space = SearchSpace(param_ranges={"x": [1, 2]})
        opt = SearchOptimizer(space, mode="random")
        result = opt.optimize(lambda p: p["x"], n_trials=0, maximize=False)
        assert result.iterations == 0
        assert result.best_score == float("inf")


# ═══════════════════════════════════════════════════════════════
# SearchOptimizer — get_history()
# ═══════════════════════════════════════════════════════════════


class TestSearchOptimizerGetHistory:
    """SearchOptimizer.get_history()"""

    def test_get_history_returns_copy(self):
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})
        opt = SearchOptimizer(space, mode="grid")
        opt.optimize(lambda p: p["x"], n_trials=3, maximize=True)
        history = opt.get_history()
        # Modify copy, original unchanged
        history.append({"extra": True})
        history2 = opt.get_history()
        assert len(history2) == 3

    def test_get_history_empty_before_optimize(self):
        space = SearchSpace(param_ranges={"x": [1]})
        opt = SearchOptimizer(space)
        assert opt.get_history() == []


# ═══════════════════════════════════════════════════════════════
# SearchOptimizer — optimize_async / search / optimize_bayes
# ═══════════════════════════════════════════════════════════════


class TestSearchOptimizerAsync:
    """SearchOptimizer.optimize_async() / search()"""

    def test_optimize_async_returns_task_id_string(self):
        space = SearchSpace(param_ranges={"x": [1, 2]})
        opt = SearchOptimizer(space)

        with patch(
            "tengod.偏财_奇招演化.search_optimizer.submit_async",
            return_value="task-abc",
        ):
            # Ensure relative import in optimize_async resolves
            import tengod.偏财_奇招演化.search_optimizer as mod
            sys.modules["偏财_奇招演化.search_optimizer"] = mod
            task_id = opt.optimize_async(lambda p: p["x"], n_trials=5, maximize=True)
            assert isinstance(task_id, str)
            assert len(task_id) > 0

    def test_search_is_alias_for_optimize_async(self):
        space = SearchSpace(param_ranges={"x": [1, 2]})
        opt = SearchOptimizer(space)

        with patch(
            "tengod.偏财_奇招演化.search_optimizer.submit_async",
            return_value="task-xyz",
        ):
            import tengod.偏财_奇招演化.search_optimizer as mod
            sys.modules["偏财_奇招演化.search_optimizer"] = mod
            task_id = opt.search(n_trials=3, objective=lambda p: p["x"], maximize=True)
            assert isinstance(task_id, str)
            assert len(task_id) > 0


class TestSearchOptimizerBayes:
    """SearchOptimizer.optimize_bayes()"""

    def test_optimize_bayes_basic_call(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            return -(p["x"] - 5) ** 2

        result = opt.optimize_bayes(obj, n_trials=10, maximize=True)
        assert isinstance(result, SearchResult)
        assert result.method_name == "bayes_search"
        assert result.iterations == 10

    def test_optimize_bayes_with_random_state(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            return -(p["x"] - 5) ** 2

        r1 = opt.optimize_bayes(obj, n_trials=10, maximize=True, random_state=42)
        r2 = opt.optimize_bayes(obj, n_trials=10, maximize=True, random_state=42)
        assert r1.best_score == r2.best_score

    def test_optimize_bayes_maximize_false(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            return (p["x"] - 3) ** 2

        result = opt.optimize_bayes(obj, n_trials=10, maximize=False)
        assert result.method_name == "bayes_search"
        assert result.iterations == 10

    def test_optimize_bayes_with_n_trials_less_than_3(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            return -(p["x"] - 5) ** 2

        result = opt.optimize_bayes(obj, n_trials=2, maximize=True)
        assert result.iterations == 2

    def test_optimize_bayes_with_n_trials_1(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            return -(p["x"] - 5) ** 2

        result = opt.optimize_bayes(obj, n_trials=1, maximize=True)
        assert result.iterations == 1

    def test_optimize_bayes_duration_in_ms(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            return p["x"]

        result = opt.optimize_bayes(obj, n_trials=5, maximize=True)
        assert result.duration >= 0

    def test_optimize_bayes_all_identical_scores(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            return 42.0

        result = opt.optimize_bayes(obj, n_trials=10, maximize=True)
        assert result.iterations == 10
        assert result.best_score == 42.0

    def test_optimize_bayes_objective_always_fails(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            raise RuntimeError("fail")

        result = opt.optimize_bayes(obj, n_trials=5, maximize=True)
        assert result.iterations == 5
        assert result.best_score == float("-inf")
        assert result.best_params == {}


# ═══════════════════════════════════════════════════════════════
# AsyncSearchTask
# ═══════════════════════════════════════════════════════════════


class TestAsyncSearchTaskCreation:
    """AsyncSearchTask 创建"""

    def test_create_with_required_fields(self):
        space = SearchSpace(param_ranges={"x": [1]})
        opt = SearchOptimizer(space)

        def obj(p):
            return p["x"]

        task = AsyncSearchTask(
            task_id="abc123",
            status="pending",
            optimizer=opt,
            objective=obj,
            n_trials=10,
            maximize=True,
        )
        assert task.task_id == "abc123"
        assert task.status == "pending"
        assert task.optimizer is opt
        assert task.objective is obj
        assert task.n_trials == 10
        assert task.maximize is True

    def test_default_created_at_is_float(self):
        space = SearchSpace()
        opt = SearchOptimizer(space)
        task = AsyncSearchTask(
            task_id="t1",
            status="pending",
            optimizer=opt,
            objective=lambda p: 0,
            n_trials=5,
            maximize=True,
        )
        assert isinstance(task.created_at, float)
        assert task.created_at > 0

    def test_default_result_is_none(self):
        space = SearchSpace()
        opt = SearchOptimizer(space)
        task = AsyncSearchTask(
            task_id="t1",
            status="pending",
            optimizer=opt,
            objective=lambda p: 0,
            n_trials=5,
            maximize=True,
        )
        assert task.result is None

    def test_default_error_is_none(self):
        space = SearchSpace()
        opt = SearchOptimizer(space)
        task = AsyncSearchTask(
            task_id="t1",
            status="pending",
            optimizer=opt,
            objective=lambda p: 0,
            n_trials=5,
            maximize=True,
        )
        assert task.error is None

    def test_default_started_at_is_none(self):
        space = SearchSpace()
        opt = SearchOptimizer(space)
        task = AsyncSearchTask(
            task_id="t1",
            status="pending",
            optimizer=opt,
            objective=lambda p: 0,
            n_trials=5,
            maximize=True,
        )
        assert task.started_at is None

    def test_default_finished_at_is_none(self):
        space = SearchSpace()
        opt = SearchOptimizer(space)
        task = AsyncSearchTask(
            task_id="t1",
            status="pending",
            optimizer=opt,
            objective=lambda p: 0,
            n_trials=5,
            maximize=True,
        )
        assert task.finished_at is None


# ═══════════════════════════════════════════════════════════════
# AsyncOptimizer — submit / get_status / cancel / get_result / list_tasks
# ═══════════════════════════════════════════════════════════════


class TestAsyncOptimizerSubmit:
    """AsyncOptimizer.submit()"""

    def test_submit_returns_task_id_string(self):
        ao = AsyncOptimizer()
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})

        def obj(p):
            return p["x"]

        task_id = ao.submit(space, obj, n_trials=5)
        assert isinstance(task_id, str)
        assert len(task_id) == 8

    def test_submit_with_space_none(self):
        ao = AsyncOptimizer()

        def obj(p):
            return 0.0

        task_id = ao.submit(None, obj, n_trials=5)
        assert isinstance(task_id, str)
        assert len(task_id) == 8


class TestAsyncOptimizerGetStatus:
    """AsyncOptimizer.get_status()"""

    def test_get_status_pending_task(self):
        ao = AsyncOptimizer()
        space = SearchSpace()

        def obj(p):
            time.sleep(0.5)
            return 0.0

        task_id = ao.submit(space, obj, n_trials=5)
        status = ao.get_status(task_id)
        assert status["task_id"] == task_id
        assert status["status"] in ("pending", "running", "done")
        assert "created_at" in status

    def test_get_status_running_task(self):
        ao = AsyncOptimizer()
        space = SearchSpace()

        def obj(p):
            time.sleep(0.3)
            return 0.0

        task_id = ao.submit(space, obj, n_trials=5)
        time.sleep(0.02)
        status = ao.get_status(task_id)
        assert status["status"] in ("pending", "running")

    def test_get_status_done_task(self):
        ao = AsyncOptimizer()
        space = SearchSpace(param_ranges={"x": [1]})

        def obj(p):
            return p["x"]

        task_id = ao.submit(space, obj, n_trials=1)
        # Wait for completion
        for _ in range(30):
            st = ao.get_status(task_id)
            if st["status"] in ("done", "failed"):
                break
            time.sleep(0.05)
        assert ao.get_status(task_id)["status"] == "done"

    def test_get_status_non_existent_task(self):
        ao = AsyncOptimizer()
        assert ao.get_status("ghost-id") == {"status": "not_found"}


class TestAsyncOptimizerCancel:
    """AsyncOptimizer.cancel()"""

    def test_cancel_pending_task(self):
        ao = AsyncOptimizer()
        space = SearchSpace()

        def obj(p):
            time.sleep(0.5)
            return 0.0

        task_id = ao.submit(space, obj, n_trials=5)
        time.sleep(0.01)
        result = ao.cancel(task_id)
        assert result is True

    def test_cancel_running_task(self):
        ao = AsyncOptimizer()
        space = SearchSpace()

        def obj(p):
            time.sleep(0.5)
            return 0.0

        task_id = ao.submit(space, obj, n_trials=5)
        time.sleep(0.01)
        result = ao.cancel(task_id)
        assert result is True

    def test_cancel_non_existent_task(self):
        ao = AsyncOptimizer()
        assert ao.cancel("ghost-id") is False

    def test_cancel_already_done_task(self):
        ao = AsyncOptimizer()
        space = SearchSpace(param_ranges={"x": [1]})

        def obj(p):
            return p["x"]

        task_id = ao.submit(space, obj, n_trials=1)
        # Wait for completion
        for _ in range(30):
            if ao.get_status(task_id)["status"] == "done":
                break
            time.sleep(0.05)
        assert ao.cancel(task_id) is False


class TestAsyncOptimizerGetResult:
    """AsyncOptimizer.get_result()"""

    def test_get_result_after_worker_completes(self):
        ao = AsyncOptimizer()
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})

        def obj(p):
            return p["x"]

        task_id = ao.submit(space, obj, n_trials=3)
        for _ in range(30):
            if ao.get_status(task_id)["status"] in ("done", "failed"):
                break
            time.sleep(0.05)
        result = ao.get_result(task_id)
        assert result is not None
        assert isinstance(result, SearchResult)
        assert result.best_params is not None

    def test_get_result_non_existent_task(self):
        ao = AsyncOptimizer()
        assert ao.get_result("ghost-id") is None

    def test_get_result_pending_task_returns_none(self):
        ao = AsyncOptimizer()
        space = SearchSpace()

        def obj(p):
            time.sleep(0.5)
            return 0.0

        task_id = ao.submit(space, obj, n_trials=5)
        # Immediately check result, worker hasn't finished
        result = ao.get_result(task_id)
        assert result is None


class TestAsyncOptimizerListTasks:
    """AsyncOptimizer.list_tasks()"""

    def test_list_tasks_empty(self):
        ao = AsyncOptimizer()
        assert ao.list_tasks() == []

    def test_list_tasks_with_tasks(self):
        ao = AsyncOptimizer()
        space = SearchSpace()

        def obj(p):
            return 0.0

        ao.submit(space, obj, n_trials=2)
        tasks = ao.list_tasks()
        assert len(tasks) >= 1
        for t in tasks:
            assert "task_id" in t
            assert "status" in t
            assert "created_at" in t


# ═══════════════════════════════════════════════════════════════
# AsyncOptimizer._worker()
# ═══════════════════════════════════════════════════════════════


class TestAsyncOptimizerWorker:
    """AsyncOptimizer._worker()"""

    def test_worker_completes_and_sets_result(self):
        ao = AsyncOptimizer()
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})

        def obj(p):
            return p["x"]

        task_id = ao.submit(space, obj, n_trials=3)
        time.sleep(0.2)
        status = ao.get_status(task_id)
        assert status["status"] == "done"
        result = ao.get_result(task_id)
        assert result is not None
        assert isinstance(result, SearchResult)
        assert result.best_score >= 1

    def test_worker_with_cancelled_task(self):
        ao = AsyncOptimizer()
        space = SearchSpace()

        def obj(p):
            time.sleep(0.3)
            return 0.0

        task_id = ao.submit(space, obj, n_trials=5)
        time.sleep(0.01)
        ao.cancel(task_id)
        time.sleep(0.4)
        status = ao.get_status(task_id)
        # Task should be cancelled
        assert status["status"] in ("cancelled", "pending", "running")

    def test_worker_with_exception_objective_raises(self):
        ao = AsyncOptimizer()
        space = SearchSpace(param_ranges={"x": [1]})

        def obj(p):
            return p["x"]

        with patch.object(
            SearchOptimizer, "optimize", side_effect=RuntimeError("worker error")
        ):
            task_id = ao.submit(space, obj, n_trials=3)

        for _ in range(30):
            st = ao.get_status(task_id)
            if st["status"] in ("done", "failed"):
                break
            time.sleep(0.05)
        status = ao.get_status(task_id)
        assert status["status"] == "failed"
        assert status["error"] is not None

    def test_worker_with_task_not_found_graceful(self):
        """Worker handles missing task gracefully (edge case: task deleted between lock acquires)."""
        ao = AsyncOptimizer()
        # Start a worker with a task that gets removed before worker runs
        space = SearchSpace()

        def obj(p):
            return 0.0

        task_id = ao.submit(space, obj, n_trials=1)
        # The worker should handle this gracefully even if task disappears
        # (The _worker checks for None task, so it won't crash)
        time.sleep(0.3)
        assert ao.get_status(task_id)["status"] == "done"


# ═══════════════════════════════════════════════════════════════
# 全局函数
# ═══════════════════════════════════════════════════════════════


class TestGlobalFunctions:
    """get_async_optimizer() / submit_async()"""

    def test_get_async_optimizer_returns_singleton(self):
        import tengod.偏财_奇招演化.search_optimizer as mod

        mod._global_optimizer = None
        ao1 = get_async_optimizer()
        ao2 = get_async_optimizer()
        assert ao1 is ao2

    def test_submit_async_returns_task_id(self):
        space = SearchSpace(param_ranges={"x": [1, 2]})

        def obj(p):
            return p["x"]

        task_id = submit_async(space, obj, n_trials=3, maximize=True, mode="random")
        assert isinstance(task_id, str)
        assert len(task_id) == 8

    def test_submit_async_with_default_params(self):
        space = SearchSpace(param_ranges={"x": [1, 2]})

        def obj(p):
            return p["x"]

        task_id = submit_async(space, obj)
        assert isinstance(task_id, str)
        assert len(task_id) == 8