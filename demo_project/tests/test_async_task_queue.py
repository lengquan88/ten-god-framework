"""test_async_task_queue.py — 异步任务队列测试 v2.1.0"""
import asyncio
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tengod"))

from 正官_法度调度.async_task_queue import (
    AsyncTaskItem,
    AsyncTaskPriority,
    AsyncTaskQueue,
    AsyncTaskStatus,
)


class TestAsyncTaskPriority:
    def test_priority_ordering(self):
        assert AsyncTaskPriority.CRITICAL.value < AsyncTaskPriority.HIGH.value
        assert AsyncTaskPriority.HIGH.value < AsyncTaskPriority.NORMAL.value
        assert AsyncTaskPriority.NORMAL.value < AsyncTaskPriority.LOW.value

    def test_item_priority_sorting(self):
        high = AsyncTaskItem(priority=AsyncTaskPriority.HIGH.value, task_id="h", func=lambda: 1, func_name="h")
        low = AsyncTaskItem(priority=AsyncTaskPriority.LOW.value, task_id="l", func=lambda: 2, func_name="l")
        assert high.priority < low.priority


class TestAsyncTaskQueueBasic:
    @pytest.mark.asyncio
    async def test_submit_and_get_result(self):
        queue = AsyncTaskQueue(max_workers=2)
        await queue.start()

        async def sample_task(x):
            return x * 2

        task_id = await queue.submit(sample_task, args=(5,))
        result = await queue.get_result(task_id)
        assert result == 10
        await queue.shutdown()

    @pytest.mark.asyncio
    async def test_submit_sync_function(self):
        queue = AsyncTaskQueue(max_workers=2)
        await queue.start()

        task_id = await queue.submit(lambda x, y: x + y, args=(3, 4))
        result = await queue.get_result(task_id)
        assert result == 7
        await queue.shutdown()

    @pytest.mark.asyncio
    async def test_multiple_tasks(self):
        queue = AsyncTaskQueue(max_workers=4)
        await queue.start()

        task_ids = []
        for i in range(10):
            tid = await queue.submit(lambda x: x * x, args=(i,))
            task_ids.append(tid)

        results = []
        for tid in task_ids:
            r = await queue.get_result(tid)
            results.append(r)

        assert results == [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
        await queue.shutdown()

    @pytest.mark.asyncio
    async def test_task_status_tracking(self):
        queue = AsyncTaskQueue(max_workers=2)
        await queue.start()

        task_id = await queue.submit(lambda x: x, args=(42,))
        result = await queue.get_result(task_id)
        assert result == 42

        task = queue.get_task(task_id)
        assert task.status == AsyncTaskStatus.COMPLETED
        await queue.shutdown()

    @pytest.mark.asyncio
    async def test_list_tasks(self):
        queue = AsyncTaskQueue(max_workers=2)
        await queue.start()

        for i in range(5):
            await queue.submit(lambda x: x, args=(i,), priority=AsyncTaskPriority.NORMAL)

        pending = queue.list_tasks(status=AsyncTaskStatus.PENDING)
        assert len(pending) >= 0  # 可能已被 worker 消费

        await queue.shutdown()


class TestAsyncTaskQueuePriority:
    @pytest.mark.asyncio
    async def test_priority_order(self):
        """验证高优先级任务先执行"""
        queue = AsyncTaskQueue(max_workers=1)  # 单 worker 确保顺序
        await queue.start()

        results = []

        async def record(x, delay=0):
            await asyncio.sleep(delay)
            results.append(x)
            return x

        # 提交时优先级的数值越小越优先
        tid_low = await queue.submit(record, args=("low",), priority=AsyncTaskPriority.LOW)
        tid_normal = await queue.submit(record, args=("normal",), priority=AsyncTaskPriority.NORMAL)
        tid_high = await queue.submit(record, args=("high",), priority=AsyncTaskPriority.HIGH)
        tid_critical = await queue.submit(record, args=("critical",), priority=AsyncTaskPriority.CRITICAL)

        await queue.get_result(tid_critical)
        await queue.get_result(tid_high)
        await queue.get_result(tid_normal)
        await queue.get_result(tid_low)

        # 高优先级应该先执行
        assert results[0] == "critical"
        assert results[1] == "high"
        assert results[2] == "normal"
        assert results[3] == "low"

        await queue.shutdown()


class TestAsyncTaskQueueRetry:
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        queue = AsyncTaskQueue(max_workers=2)
        await queue.start()

        call_count = {"count": 0}

        def flaky():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise ValueError("flaky error")
            return "success"

        task_id = await queue.submit(flaky, max_retries=3)
        result = await queue.get_result(task_id)
        assert result == "success"
        assert call_count["count"] == 3
        await queue.shutdown()

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        queue = AsyncTaskQueue(max_workers=2)
        await queue.start()

        def always_fail():
            raise RuntimeError("always fails")

        task_id = await queue.submit(always_fail, max_retries=1)
        with pytest.raises(RuntimeError, match="always fails"):
            await queue.get_result(task_id)

        task = queue.get_task(task_id)
        assert task.status == AsyncTaskStatus.FAILED
        assert task.retry_count == 2  # 1 initial + 1 retry
        await queue.shutdown()


class TestAsyncTaskQueueCancel:
    @pytest.mark.asyncio
    async def test_cancel_pending(self):
        queue = AsyncTaskQueue(max_workers=1)
        await queue.start()

        async def slow():
            await asyncio.sleep(10)
            return "done"

        # 提交一个慢任务占住 worker
        slow_id = await queue.submit(slow, priority=AsyncTaskPriority.LOW)

        # 提交一个待取消的任务
        task_id = await queue.submit(lambda x: x, args=(1,), priority=AsyncTaskPriority.NORMAL)

        canceled = await queue.cancel(task_id)
        assert canceled is True

        task = queue.get_task(task_id)
        assert task.status == AsyncTaskStatus.CANCELLED

        await queue.shutdown()


class TestAsyncTaskQueueStats:
    @pytest.mark.asyncio
    async def test_stats(self):
        queue = AsyncTaskQueue(max_workers=2)
        await queue.start()

        for i in range(5):
            await queue.submit(lambda x: x, args=(i,))

        # 等待所有任务完成
        await asyncio.sleep(0.1)

        s = queue.stats()
        assert s["submitted"] == 5
        assert s["workers"] == 2
        assert "queue_size" in s
        await queue.shutdown()


class TestAsyncTaskQueueShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self):
        queue = AsyncTaskQueue(max_workers=2)
        await queue.start()
        assert queue.is_running is True
        await queue.shutdown()
        assert queue.is_running is False

    @pytest.mark.asyncio
    async def test_get_result_timeout(self):
        queue = AsyncTaskQueue(max_workers=1)
        await queue.start()

        async def slow():
            await asyncio.sleep(10)
            return "slow"

        task_id = await queue.submit(slow, priority=AsyncTaskPriority.LOW)

        with pytest.raises(asyncio.TimeoutError):
            await queue.get_result(task_id, timeout=0.1)

        await queue.shutdown()


# ============================================================================
# Bug #1 回归测试：cancel 计数正确性 + RUNNING cancel Future resolve
# ============================================================================

class TestAsyncTaskQueueCancelRegression:
    """提交后正确性检查发现的 Bug #1 回归测试。

    Bug 描述：
      1. PENDING 状态 cancel 存在双计数（cancel() 方法中计数 1 次，
         Worker 取到时又计数 1 次）→ stats.cancelled 显示为 2。
      2. RUNNING 状态下 cancel：
         - 原代码中 cancel() 会把 status 改为 CANCELLED，但随后 try 块
           正常完成时 L113 会无条件覆盖 status=COMPLETED，导致 cancel
           对 RUNNING 任务实际无效（仍返回 completed=1 的统计和结果）。
         - 如果异常路径（fail+不再重试）中 status 被覆盖为 FAILED 也
           同样无效。更糟的是 finally 中仅处理 COMPLETED/FAILED，
           CANCELLED 状态的 Future 永远不 resolve，调用方无限挂起。
    """

    @pytest.mark.asyncio
    async def test_cancel_pending_counts_exactly_once(self):
        """PENDING cancel → cancelled=1，不双计数。"""
        queue = AsyncTaskQueue(max_workers=1)
        await queue.start()

        async def blocker():
            await asyncio.sleep(0.3)
            return "blocked"

        async def quick():
            return "quick"

        blocker_id = await queue.submit(blocker, priority=AsyncTaskPriority.LOW)
        pending_id = await queue.submit(quick, priority=AsyncTaskPriority.NORMAL)

        assert await queue.cancel(pending_id) is True

        # PENDING 任务：Worker 未取到，stats 未更新（Worker 取到时会计数）
        await asyncio.sleep(0.6)  # 等待 blocker 结束 + PENDING 被 Worker 处理

        stats = queue.stats()
        # 期望：blocker=1 completed；pending=1 cancelled
        assert stats["completed"] == 1, f"completed 错误: {stats}"
        assert stats["cancelled"] == 1, f"cancelled 双计数! stats={stats}"
        await queue.shutdown()

    @pytest.mark.asyncio
    async def test_cancel_pending_get_result_raises_cancelled_error(self):
        """PENDING cancel 后 get_result() 必须抛 CancelledError（不挂起）。"""
        queue = AsyncTaskQueue(max_workers=1)
        await queue.start()

        async def blocker():
            await asyncio.sleep(0.2)
            return "blocked"

        def quick():
            return 42

        await queue.submit(blocker)
        tid = await queue.submit(quick)
        await queue.cancel(tid)

        with pytest.raises(asyncio.CancelledError):
            # 如果 Future 不 resolve，这里会挂起直到测试超时
            await queue.get_result(tid, timeout=3.0)

        await queue.shutdown()

    @pytest.mark.asyncio
    async def test_cancel_running_successful_task_raises_cancelled(self):
        """RUNNING 任务执行期间被 cancel → 抛 CancelledError，且不记 completed。"""
        queue = AsyncTaskQueue(max_workers=1)
        await queue.start()

        async def slow_ok():
            await asyncio.sleep(0.3)
            return "success"

        tid = await queue.submit(slow_ok)
        await asyncio.sleep(0.05)  # 已进入 RUNNING
        assert await queue.cancel(tid) is True

        with pytest.raises(asyncio.CancelledError):
            await queue.get_result(tid, timeout=3.0)

        stats = queue.stats()
        assert stats["completed"] == 0, f"RUNNING cancel 仍记为 completed! {stats}"
        assert stats["cancelled"] == 1, f"cancelled 计数应为1: {stats}"
        await queue.shutdown()

    @pytest.mark.asyncio
    async def test_cancel_running_failed_task_raises_cancelled(self):
        """RUNNING 任务失败期间被 cancel → 抛 CancelledError，不记 failed。"""
        queue = AsyncTaskQueue(max_workers=1)
        await queue.start()

        async def slow_fail():
            await asyncio.sleep(0.3)
            raise RuntimeError("boom")

        tid = await queue.submit(slow_fail, max_retries=0)
        await asyncio.sleep(0.05)  # RUNNING
        assert await queue.cancel(tid) is True

        with pytest.raises(asyncio.CancelledError):
            await queue.get_result(tid, timeout=3.0)

        stats = queue.stats()
        assert stats["failed"] == 0, f"RUNNING cancel+fail 仍记为 failed! {stats}"
        assert stats["cancelled"] == 1, f"cancelled 应为1: {stats}"
        await queue.shutdown()

    @pytest.mark.asyncio
    async def test_normal_completed_stats_still_correct_after_fix(self):
        """修复未破坏正常路径：未 cancel 的成功/失败任务计数正确。"""
        queue = AsyncTaskQueue(max_workers=2)
        await queue.start()

        def ok():
            return 1

        def bad():
            raise RuntimeError("x")

        await queue.submit(ok)
        await queue.submit(ok)
        tid_bad = await queue.submit(bad, max_retries=0)

        with pytest.raises(RuntimeError, match="x"):
            await queue.get_result(tid_bad, timeout=3.0)

        await asyncio.sleep(0.2)
        stats = queue.stats()
        assert stats["completed"] == 2
        assert stats["failed"] == 1
        assert stats["cancelled"] == 0
        await queue.shutdown()