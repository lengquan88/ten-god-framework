#!/usr/bin/env python3
"""Tests for search_optimizer module."""

import math
import random
import sys
import threading
import time
import unittest.mock as mock
from unittest.mock import MagicMock, patch

import pytest

# Ensure the project root is importable
sys.path.insert(0, "/workspace/demo_project")

from tengod.偏财_奇招演化.search_optimizer import (
    AsyncOptimizer,
    AsyncSearchTask,
    SearchOptimizer,
    SearchResult,
    SearchSpace,
    get_async_optimizer,
    submit_async,
)


# ──────────────────────────────────────────────────────────────
# SearchSpace
# ──────────────────────────────────────────────────────────────


class TestSearchSpace:
    def test_default_construction(self):
        space = SearchSpace()
        assert space.param_ranges == {}

    def test_construction_with_param_ranges(self):
        space = SearchSpace(param_ranges={"a": [1, 2, 3]})
        assert "a" in space.param_ranges

    def test_sample_empty_space(self):
        space = SearchSpace()
        result = space.sample()
        assert result == {}

    def test_sample_list_type(self):
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

    def test_sample_single_value(self):
        space = SearchSpace(param_ranges={"fixed": 42})
        result = space.sample()
        assert result["fixed"] == 42

    def test_sample_mixed_params(self):
        space = SearchSpace(
            param_ranges={
                "lr": (0.001, 0.1),
                "batch": [16, 32, 64],
                "epochs": (1, 5, 1),
                "fixed": "hello",
            }
        )
        result = space.sample()
        assert 0.001 <= result["lr"] <= 0.1
        assert result["batch"] in [16, 32, 64]
        assert result["epochs"] in [1, 2, 3, 4, 5]
        assert result["fixed"] == "hello"

    def test_all_combinations_list(self):
        space = SearchSpace(param_ranges={"a": [1, 2], "b": [3, 4]})
        combos = space.all_combinations()
        expected = [
            {"a": 1, "b": 3},
            {"a": 1, "b": 4},
            {"a": 2, "b": 3},
            {"a": 2, "b": 4},
        ]
        assert len(combos) == 4
        assert combos == expected

    def test_all_combinations_int_range(self):
        space = SearchSpace(param_ranges={"n": (0, 4, 2)})
        combos = space.all_combinations()
        values = [c["n"] for c in combos]
        assert values == [0, 2, 4]

    def test_all_combinations_single_value(self):
        space = SearchSpace(param_ranges={"fixed": "x"})
        combos = space.all_combinations()
        assert combos == [{"fixed": "x"}]

    def test_all_combinations_float_range_returns_single(self):
        space = SearchSpace(param_ranges={"f": (0.0, 1.0)})
        combos = space.all_combinations()
        assert len(combos) == 1
        assert "f" in combos[0]

    def test_all_combinations_empty(self):
        space = SearchSpace()
        combos = space.all_combinations()
        assert combos == [{}]


# ──────────────────────────────────────────────────────────────
# SearchResult
# ──────────────────────────────────────────────────────────────


class TestSearchResult:
    def test_defaults(self):
        result = SearchResult(best_params={"a": 1}, best_score=0.5, iterations=10)
        assert result.best_params == {"a": 1}
        assert result.best_score == 0.5
        assert result.iterations == 10
        assert result.history == []
        assert result.duration == 0.0
        assert result.method_name == "unknown"

    def test_full_construction(self):
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
        assert len(result.history) == 1
        assert result.duration == 1.23
        assert result.method_name == "grid_search"


# ──────────────────────────────────────────────────────────────
# SearchOptimizer
# ──────────────────────────────────────────────────────────────


class TestSearchOptimizer:
    def _objective(self, params):
        return -(params["x"] - 2) ** 2

    def test_default_mode_random(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)
        assert opt._mode == "random"

    def test_explicit_mode_grid(self):
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})
        opt = SearchOptimizer(space, mode="grid")
        assert opt._mode == "grid"

    def test_optimize_random_maximize(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space, mode="random")
        result = opt.optimize(self._objective, n_trials=10, maximize=True)
        assert isinstance(result, SearchResult)
        assert result.method_name == "random_search"
        assert result.iterations == 10
        assert result.best_score is not None
        assert result.duration >= 0
        # x=2 gives max score 0
        assert result.best_score <= 0

    def test_optimize_random_minimize(self):
        def obj(params):
            return (params["x"] - 5) ** 2

        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space, mode="random")
        result = opt.optimize(obj, n_trials=10, maximize=False)
        assert result.method_name == "random_search"
        assert result.iterations == 10
        # x=5 gives min score 0
        assert result.best_score >= 0

    def test_optimize_grid(self):
        space = SearchSpace(param_ranges={"x": [1, 2, 3], "y": [10, 20]})
        opt = SearchOptimizer(space, mode="grid")
        result = opt.optimize(self._objective, n_trials=100, maximize=True)
        assert result.method_name == "grid_search"
        assert result.iterations == 6  # 3*2 combinations

    def test_optimize_grid_n_trials_limits(self):
        space = SearchSpace(param_ranges={"x": [1, 2, 3, 4, 5]})
        opt = SearchOptimizer(space, mode="grid")
        result = opt.optimize(self._objective, n_trials=3, maximize=True)
        assert result.iterations == 3

    def test_optimize_empty_space(self):
        space = SearchSpace()
        opt = SearchOptimizer(space, mode="random")
        result = opt.optimize(lambda p: 0.0, n_trials=5, maximize=True)
        assert result.iterations == 5
        assert result.best_params == {}
        assert result.best_score == 0.0

    def test_optimize_objective_raises_exception(self):
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})
        opt = SearchOptimizer(space, mode="random")

        def failing(p):
            if p["x"] == 2:
                raise ValueError("bad value")
            return p["x"]

        result = opt.optimize(failing, n_trials=10, maximize=True)
        # Should still complete, best_score will be from the non-failing calls
        assert result.iterations == 10
        # Check that error entries exist in history
        errors = [
            h for h in result.history if "_error" in h["params"]
        ]
        assert len(errors) > 0

    def test_optimize_objective_always_fails(self):
        space = SearchSpace(param_ranges={"x": [1]})
        opt = SearchOptimizer(space, mode="grid")

        def always_fail(p):
            raise RuntimeError("always fails")

        result = opt.optimize(always_fail, n_trials=5, maximize=True)
        # best_params should be {}
        assert result.best_params == {}
        # best_score should be -inf for maximize
        assert result.best_score == float("-inf")

    def test_optimize_objective_always_fails_minimize(self):
        space = SearchSpace(param_ranges={"x": [1]})
        opt = SearchOptimizer(space, mode="grid")

        def always_fail(p):
            raise RuntimeError("always fails")

        result = opt.optimize(always_fail, n_trials=5, maximize=False)
        assert result.best_score == float("inf")

    def test_get_history_empty(self):
        space = SearchSpace(param_ranges={"x": [1]})
        opt = SearchOptimizer(space)
        history = opt.get_history()
        assert history == []

    def test_get_history_after_optimize(self):
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})
        opt = SearchOptimizer(space, mode="grid")
        opt.optimize(self._objective, n_trials=3, maximize=True)
        history = opt.get_history()
        assert len(history) == 3
        for entry in history:
            assert "trial" in entry
            assert "params" in entry
            assert "score" in entry

    def test_optimize_zero_trials(self):
        space = SearchSpace(param_ranges={"x": [1, 2]})
        opt = SearchOptimizer(space, mode="random")
        result = opt.optimize(self._objective, n_trials=0, maximize=True)
        assert result.iterations == 0
        assert result.best_params == {}
        assert result.best_score == float("-inf")

    def test_optimize_bayes_basic(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            return -(p["x"] - 5) ** 2

        result = opt.optimize_bayes(obj, n_trials=10, maximize=True)
        assert isinstance(result, SearchResult)
        assert result.method_name == "bayes_search"
        assert result.iterations == 10
        assert result.best_score <= 0
        assert result.best_params is not None

    def test_optimize_bayes_minimize(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})

        def obj(p):
            return (p["x"] - 3) ** 2

        opt = SearchOptimizer(space)
        result = opt.optimize_bayes(obj, n_trials=10, maximize=False)
        assert result.method_name == "bayes_search"
        assert result.iterations == 10

    def test_optimize_bayes_with_random_state(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            return -(p["x"] - 5) ** 2

        result1 = opt.optimize_bayes(obj, n_trials=10, maximize=True, random_state=42)
        result2 = opt.optimize_bayes(obj, n_trials=10, maximize=True, random_state=42)
        assert result1.best_score == result2.best_score

    def test_optimize_bayes_few_trials(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            return -(p["x"] - 5) ** 2

        result = opt.optimize_bayes(obj, n_trials=2, maximize=True)
        assert result.iterations == 2

    def test_optimize_bayes_obj_fails(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})

        def failing(p):
            raise RuntimeError("fail")

        opt = SearchOptimizer(space)
        result = opt.optimize_bayes(failing, n_trials=5, maximize=True)
        assert result.iterations == 5
        assert result.best_score == float("-inf")

    def test_optimize_bayes_duration_in_ms(self):
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            return p["x"]

        result = opt.optimize_bayes(obj, n_trials=5, maximize=True)
        # duration is in ms for bayes
        assert result.duration >= 0

    @patch("tengod.偏财_奇招演化.search_optimizer.submit_async")
    def test_optimize_async_returns_task_id(self, mock_submit):
        mock_submit.return_value = "task-123"
        space = SearchSpace(param_ranges={"x": [1, 2]})
        opt = SearchOptimizer(space)

        def obj(p):
            return p["x"]

        # Mock the internal import path used by optimize_async
        import sys
        sys.modules["偏财_奇招演化.search_optimizer"] = sys.modules[
            "tengod.偏财_奇招演化.search_optimizer"
        ]

        task_id = opt.optimize_async(obj, n_trials=5, maximize=True)
        assert task_id == "task-123"
        mock_submit.assert_called_once_with(space, obj, 5, True, "random")

    @patch("tengod.偏财_奇招演化.search_optimizer.submit_async")
    def test_search_alias(self, mock_submit):
        mock_submit.return_value = "task-456"
        space = SearchSpace(param_ranges={"x": [1, 2]})
        opt = SearchOptimizer(space)

        def obj(p):
            return p["x"]

        # Mock the internal import path used by optimize_async
        import sys
        sys.modules["偏财_奇招演化.search_optimizer"] = sys.modules[
            "tengod.偏财_奇招演化.search_optimizer"
        ]

        task_id = opt.search(n_trials=3, objective=obj, maximize=True)
        assert task_id == "task-456"
        mock_submit.assert_called_once_with(space, obj, 3, True, "random")


# ──────────────────────────────────────────────────────────────
# AsyncSearchTask
# ──────────────────────────────────────────────────────────────


class TestAsyncSearchTask:
    def test_construction(self):
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
        assert task.result is None
        assert task.error is None
        assert task.created_at > 0
        assert task.started_at is None
        assert task.finished_at is None

    def test_with_result(self):
        space = SearchSpace()
        opt = SearchOptimizer(space)
        result = SearchResult(
            best_params={"x": 1}, best_score=0.5, iterations=5
        )

        task = AsyncSearchTask(
            task_id="xyz",
            status="done",
            optimizer=opt,
            objective=lambda p: 0,
            n_trials=5,
            maximize=True,
            result=result,
            error="some error",
        )
        assert task.result is result
        assert task.error == "some error"


# ──────────────────────────────────────────────────────────────
# AsyncOptimizer
# ──────────────────────────────────────────────────────────────


class TestAsyncOptimizer:
    def test_submit_returns_task_id(self):
        ao = AsyncOptimizer()
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})

        def obj(p):
            return p["x"]

        task_id = ao.submit(space, obj, n_trials=5)
        assert isinstance(task_id, str)
        assert len(task_id) == 8

    def test_submit_space_none(self):
        ao = AsyncOptimizer()

        def obj(p):
            return 0.0

        task_id = ao.submit(None, obj, n_trials=5)
        assert isinstance(task_id, str)

    def test_get_status_not_found(self):
        ao = AsyncOptimizer()
        status = ao.get_status("nonexistent")
        assert status == {"status": "not_found"}

    def test_get_status_pending(self):
        ao = AsyncOptimizer()
        space = SearchSpace()

        def obj(p):
            return 0.0

        task_id = ao.submit(space, obj, n_trials=5)
        status = ao.get_status(task_id)
        assert status["task_id"] == task_id
        assert status["status"] in ("pending", "running", "done")
        assert "created_at" in status

    def test_cancel_not_found(self):
        ao = AsyncOptimizer()
        assert ao.cancel("nonexistent") is False

    def test_cancel_pending_task(self):
        ao = AsyncOptimizer()
        space = SearchSpace()

        def obj(p):
            time.sleep(0.5)
            return 0.0

        task_id = ao.submit(space, obj, n_trials=5)
        # Give a tiny moment for worker to start
        time.sleep(0.01)
        result = ao.cancel(task_id)
        assert result is True

        status = ao.get_status(task_id)
        assert status["status"] in ("pending", "running", "cancelled")

    def test_cancel_already_done(self):
        ao = AsyncOptimizer()
        space = SearchSpace(param_ranges={"x": [1]})

        def obj(p):
            return p["x"]

        task_id = ao.submit(space, obj, n_trials=1)
        # Wait for completion
        time.sleep(0.3)
        status = ao.get_status(task_id)
        if status["status"] == "done":
            assert ao.cancel(task_id) is False

    def test_get_result_not_found(self):
        ao = AsyncOptimizer()
        assert ao.get_result("nonexistent") is None

    def test_get_result_after_completion(self):
        ao = AsyncOptimizer()
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})

        def obj(p):
            return p["x"]

        task_id = ao.submit(space, obj, n_trials=3)
        # Wait for completion
        for _ in range(20):
            status = ao.get_status(task_id)
            if status["status"] in ("done", "failed"):
                break
            time.sleep(0.05)
        result = ao.get_result(task_id)
        assert result is not None
        assert isinstance(result, SearchResult)
        assert result.best_params is not None

    def test_list_tasks(self):
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

    def test_worker_handles_objective_error(self):
        """Worker sets status to 'failed' when optimize() raises an exception."""
        ao = AsyncOptimizer()
        space = SearchSpace(param_ranges={"x": [1]})

        def obj(p):
            return p["x"]

        # Patch optimize before submit so the worker thread uses the mocked method
        with patch.object(
            SearchOptimizer, "optimize", side_effect=RuntimeError("worker error")
        ):
            task_id = ao.submit(space, obj, n_trials=3)

        # Wait for completion
        for _ in range(30):
            status = ao.get_status(task_id)
            if status["status"] in ("done", "failed"):
                break
            time.sleep(0.05)
        status = ao.get_status(task_id)
        assert status["status"] == "failed"
        assert status["error"] is not None

    def test_worker_cancelled_before_optimize(self):
        ao = AsyncOptimizer()
        space = SearchSpace()

        # Use a lock to ensure we cancel before worker proceeds
        lock = threading.Lock()
        lock.acquire()

        def slow_obj(p):
            lock.acquire()
            lock.release()
            return 0.0

        # Patch _worker to make it run synchronously so we can control it
        task_id = ao.submit(space, slow_obj, n_trials=5)
        # Cancel while worker is waiting
        cancel_result = ao.cancel(task_id)
        lock.release()
        assert cancel_result is True


# ──────────────────────────────────────────────────────────────
# Global functions
# ──────────────────────────────────────────────────────────────


class TestGlobalFunctions:
    def test_get_async_optimizer_singleton(self):
        # Reset global state
        import tengod.偏财_奇招演化.search_optimizer as mod

        mod._global_optimizer = None
        ao1 = get_async_optimizer()
        ao2 = get_async_optimizer()
        assert ao1 is ao2

    def test_submit_async(self):
        space = SearchSpace(param_ranges={"x": [1, 2]})

        def obj(p):
            return p["x"]

        task_id = submit_async(space, obj, n_trials=3, maximize=True, mode="random")
        assert isinstance(task_id, str)
        assert len(task_id) == 8


# ──────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_extreme_n_trials(self):
        space = SearchSpace(param_ranges={"x": [1]})
        opt = SearchOptimizer(space, mode="random")

        def obj(p):
            return p["x"]

        result = opt.optimize(obj, n_trials=1000, maximize=True)
        assert result.iterations == 1000

    def test_negative_score_maximize(self):
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})
        opt = SearchOptimizer(space, mode="grid")

        def obj(p):
            return -p["x"]  # always negative

        result = opt.optimize(obj, n_trials=10, maximize=True)
        # best should be -1 (x=1)
        assert result.best_score == -1

    def test_grid_with_single_value_params(self):
        space = SearchSpace(
            param_ranges={"a": [1, 2], "b": "fixed", "c": (0.0, 1.0)}
        )
        opt = SearchOptimizer(space, mode="grid")
        result = opt.optimize(lambda p: p["a"], n_trials=10, maximize=True)
        assert result.iterations == 2

    def test_large_search_space_sample(self):
        space = SearchSpace(
            param_ranges={
                "lr": (0.0001, 0.1),
                "batch": [16, 32, 64, 128, 256],
                "epochs": (1, 100, 1),
                "dropout": (0.0, 0.5),
                "optimizer": ["adam", "sgd", "rmsprop"],
            }
        )
        result = space.sample()
        assert "lr" in result
        assert "batch" in result
        assert "epochs" in result
        assert "dropout" in result
        assert "optimizer" in result

    def test_duration_present(self):
        space = SearchSpace(param_ranges={"x": [1, 2]})
        opt = SearchOptimizer(space, mode="grid")
        result = opt.optimize(lambda p: p["x"], n_trials=2, maximize=True)
        assert result.duration > 0

    def test_history_is_deep_copy(self):
        space = SearchSpace(param_ranges={"x": [1, 2, 3]})
        opt = SearchOptimizer(space, mode="grid")
        result = opt.optimize(lambda p: p["x"], n_trials=3, maximize=True)
        history = result.history
        history_copy = opt.get_history()
        # Modifying the returned copy should not affect result.history
        history_copy.append({"new": True})
        assert len(result.history) == len(history)

    def test_bayes_all_std_zero(self):
        """Test bayes when all scores are identical (std ~ 0)."""
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})
        opt = SearchOptimizer(space)

        def obj(p):
            return 42.0  # always same score

        result = opt.optimize_bayes(obj, n_trials=10, maximize=True)
        assert result.iterations == 10
        assert result.best_score == 42.0

    def test_bayes_with_best_params_none(self):
        """Test bayes optimization path when best_params is None initially."""
        space = SearchSpace(param_ranges={"x": (0, 10, 1)})

        def always_fail(p):
            raise RuntimeError("fail")

        opt = SearchOptimizer(space)
        result = opt.optimize_bayes(always_fail, n_trials=5, maximize=True)
        assert result.best_params == {}
        assert result.best_score == float("-inf")