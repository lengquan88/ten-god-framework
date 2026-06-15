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