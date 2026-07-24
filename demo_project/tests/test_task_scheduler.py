import pytest
import time
from tengod.正官_法度调度.task_scheduler import (
    TaskScheduler,
    Task,
    TaskPriority,
    TaskStatus,
)


class TestTaskPriority:
    def test_enum_values(self):
        assert TaskPriority.CRITICAL.value == 0
        assert TaskPriority.HIGH.value == 1
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.LOW.value == 3

    def test_enum_members(self):
        members = set(TaskPriority)
        assert TaskPriority.CRITICAL in members
        assert TaskPriority.HIGH in members
        assert TaskPriority.NORMAL in members
        assert TaskPriority.LOW in members


class TestTaskStatus:
    def test_enum_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestTaskDataclass:
    def test_task_creation_with_defaults(self):
        def dummy():
            pass

        task = Task(task_id="test", func=dummy)
        assert task.task_id == "test"
        assert task.func is dummy
        assert task.args == ()
        assert task.kwargs == {}
        assert task.priority == TaskPriority.NORMAL
        assert task.status == TaskStatus.PENDING
        assert task.created_at > 0
        assert task.started_at is None
        assert task.completed_at is None
        assert task.result is None
        assert task.error is None
        assert task.max_retries == 0
        assert task.retry_count == 0

    def test_task_lt_by_priority(self):
        def dummy():
            pass

        critical = Task(task_id="c", func=dummy, priority=TaskPriority.CRITICAL)
        high = Task(task_id="h", func=dummy, priority=TaskPriority.HIGH)
        normal = Task(task_id="n", func=dummy, priority=TaskPriority.NORMAL)
        low = Task(task_id="l", func=dummy, priority=TaskPriority.LOW)

        assert critical < high
        assert high < normal
        assert normal < low
        assert critical < normal
        assert critical < low
        assert high < low

    def test_task_lt_same_priority(self):
        def dummy():
            pass

        a = Task(task_id="a", func=dummy, priority=TaskPriority.NORMAL)
        b = Task(task_id="b", func=dummy, priority=TaskPriority.NORMAL)

        # Same priority, __lt__ returns False
        assert not (a < b)
        assert not (b < a)


class TestTaskSchedulerInit:
    def test_init_default_max_workers(self):
        scheduler = TaskScheduler()
        assert scheduler._max_workers == 4
        assert scheduler._queue == []
        assert scheduler._tasks == {}
        assert scheduler._active_count == 0
        assert scheduler._shutdown is False

    def test_init_custom_max_workers(self):
        scheduler = TaskScheduler(max_workers=8)
        assert scheduler._max_workers == 8


class TestSubmit:
    def test_submit_creates_task_and_adds_to_queue(self):
        scheduler = TaskScheduler()

        def my_func():
            return 42

        task = scheduler.submit("task1", my_func)
        assert task.task_id == "task1"
        assert task.func is my_func
        assert task.status == TaskStatus.PENDING
        assert scheduler._tasks["task1"] is task
        assert len(scheduler._queue) == 1

    def test_submit_with_all_parameters(self):
        scheduler = TaskScheduler()

        def my_func(a, b):
            return a + b

        task = scheduler.submit(
            "task2",
            my_func,
            args=(1, 2),
            kwargs={"extra": "data"},
            priority=TaskPriority.HIGH,
            max_retries=3,
        )
        assert task.args == (1, 2)
        assert task.kwargs == {"extra": "data"}
        assert task.priority == TaskPriority.HIGH
        assert task.max_retries == 3

    def test_submit_with_kwargs(self):
        scheduler = TaskScheduler()

        def my_func(x, y=10):
            return x + y

        task = scheduler.submit("task3", my_func, kwargs={"x": 5, "y": 20})
        assert task.kwargs == {"x": 5, "y": 20}

    def test_submit_multiple_tasks_queue_order(self):
        scheduler = TaskScheduler()
        import heapq

        def dummy():
            pass

        scheduler.submit("low", dummy, priority=TaskPriority.LOW)
        scheduler.submit("critical", dummy, priority=TaskPriority.CRITICAL)
        scheduler.submit("normal", dummy, priority=TaskPriority.NORMAL)

        # The queue should be a min-heap by priority value
        first = heapq.heappop(scheduler._queue)
        assert first.task_id == "critical"

    def test_duplicate_task_id_overwrites(self):
        scheduler = TaskScheduler()

        def func1():
            return 1

        def func2():
            return 2

        scheduler.submit("same", func1)
        scheduler.submit("same", func2)

        # The task in _tasks dict should be overwritten
        assert scheduler._tasks["same"].func is func2


class TestExecute:
    def test_execute_success_path(self):
        scheduler = TaskScheduler()

        def success_func():
            return "OK"

        task = Task(task_id="t", func=success_func)
        scheduler._execute(task)

        assert task.status == TaskStatus.COMPLETED
        assert task.result == "OK"
        assert task.error is None
        assert task.started_at is not None
        assert task.completed_at is not None

    def test_execute_failure_path(self):
        scheduler = TaskScheduler()

        def fail_func():
            raise RuntimeError("something went wrong")

        task = Task(task_id="t", func=fail_func, max_retries=0)
        scheduler._execute(task)

        assert task.status == TaskStatus.FAILED
        assert task.result is None
        assert task.error == "something went wrong"

    def test_execute_retry_path(self):
        scheduler = TaskScheduler()
        call_count = [0]

        def retry_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("fail")
            return "success after retry"

        task = Task(task_id="t", func=retry_func, max_retries=3)
        # First execute
        scheduler._execute(task)
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 1
        assert task.error == "fail"

        # Second execute (simulating re-queue and re-execute)
        scheduler._execute(task)
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 2

        # Third execute should succeed
        scheduler._execute(task)
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "success after retry"
        assert task.retry_count == 2

    def test_execute_max_retries_exhausted(self):
        scheduler = TaskScheduler()

        def always_fail():
            raise RuntimeError("always fail")

        task = Task(task_id="t", func=always_fail, max_retries=1)
        # First attempt: retry_count 0 < 1, retry
        scheduler._execute(task)
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 1

        # Second attempt: retry_count 1 == max_retries 1, fail
        scheduler._execute(task)
        assert task.status == TaskStatus.FAILED
        assert task.retry_count == 1

    def test_execute_with_args(self):
        scheduler = TaskScheduler()

        def add(a, b):
            return a + b

        task = Task(task_id="t", func=add, args=(3, 4))
        scheduler._execute(task)

        assert task.status == TaskStatus.COMPLETED
        assert task.result == 7

    def test_execute_with_kwargs(self):
        scheduler = TaskScheduler()

        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}"

        task = Task(task_id="t", func=greet, kwargs={"name": "World", "greeting": "Hi"})
        scheduler._execute(task)

        assert task.status == TaskStatus.COMPLETED
        assert task.result == "Hi, World"


class TestRunOnce:
    def test_run_once_starts_pending_tasks(self):
        scheduler = TaskScheduler(max_workers=4)

        def fast_func():
            return "done"

        scheduler.submit("t1", fast_func)
        started = scheduler.run_once()

        assert len(started) == 1
        assert started[0].task_id == "t1"

        # Wait for thread to complete
        time.sleep(0.1)
        assert scheduler.get_status("t1") == TaskStatus.COMPLETED

    def test_run_once_respects_max_workers(self):
        scheduler = TaskScheduler(max_workers=2)

        def slow_func():
            time.sleep(0.3)

        # Submit 4 tasks
        for i in range(4):
            scheduler.submit(f"t{i}", slow_func)

        started = scheduler.run_once()
        # Should only start up to max_workers tasks
        assert len(started) == 2

    def test_run_once_empty_queue(self):
        scheduler = TaskScheduler()
        started = scheduler.run_once()
        assert started == []


class TestRunAll:
    def test_run_all_processes_all_tasks(self):
        scheduler = TaskScheduler(max_workers=4)

        def fast_func():
            return "done"

        for i in range(5):
            scheduler.submit(f"t{i}", fast_func)

        scheduler.run_all()

        for i in range(5):
            assert scheduler.get_status(f"t{i}") == TaskStatus.COMPLETED

    def test_run_all_with_timeout(self):
        scheduler = TaskScheduler(max_workers=4)

        def slow_func():
            time.sleep(0.3)

        for i in range(10):
            scheduler.submit(f"t{i}", slow_func)

        scheduler.run_all(timeout=0.1)

        # After timeout, some tasks should still be pending
        statuses = [scheduler.get_status(f"t{i}") for i in range(10)]
        pending_count = statuses.count(TaskStatus.PENDING)
        completed_count = statuses.count(TaskStatus.COMPLETED)
        running_count = statuses.count(TaskStatus.RUNNING)

        # Some tasks should have been processed, but not all
        assert completed_count + running_count + pending_count == 10

    def test_shutdown_stops_run_all(self):
        scheduler = TaskScheduler(max_workers=4)

        def slow_func():
            time.sleep(0.3)

        for i in range(10):
            scheduler.submit(f"t{i}", slow_func)

        import threading

        def shutdown_after_delay():
            time.sleep(0.1)
            scheduler.shutdown()

        t = threading.Thread(target=shutdown_after_delay, daemon=True)
        t.start()

        scheduler.run_all()

        # After shutdown, at least some tasks should not be completed
        statuses = [scheduler.get_status(f"t{i}") for i in range(10)]
        pending_count = statuses.count(TaskStatus.PENDING)

        # Shutdown should have stopped before all tasks were processed
        assert pending_count > 0


class TestGetStatus:
    def test_get_status_returns_correct_status(self):
        scheduler = TaskScheduler()

        def func():
            return 1

        scheduler.submit("task1", func)
        assert scheduler.get_status("task1") == TaskStatus.PENDING

    def test_get_status_unknown_task_returns_none(self):
        scheduler = TaskScheduler()
        assert scheduler.get_status("unknown") is None


class TestStats:
    def test_stats_with_no_tasks(self):
        scheduler = TaskScheduler()
        stats = scheduler.stats()
        assert stats["total"] == 0
        assert stats["queue_size"] == 0
        assert stats["active"] == 0
        assert stats["by_status"] == {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }

    def test_stats_returns_correct_structure(self):
        scheduler = TaskScheduler()

        def func():
            return 1

        scheduler.submit("t1", func)
        stats = scheduler.stats()

        assert "total" in stats
        assert "queue_size" in stats
        assert "active" in stats
        assert "by_status" in stats
        assert stats["total"] == 1
        assert stats["queue_size"] == 1
        assert stats["by_status"]["pending"] == 1


class TestEdgeCases:
    def test_empty_queue_run_once(self):
        scheduler = TaskScheduler()
        started = scheduler.run_once()
        assert started == []

    def test_zero_max_workers(self):
        scheduler = TaskScheduler(max_workers=0)

        def func():
            return 1

        scheduler.submit("t1", func)
        started = scheduler.run_once()

        # active_count (0) is not < max_workers (0), so nothing starts
        assert started == []

    def test_run_all_with_empty_queue(self):
        scheduler = TaskScheduler()
        # Should complete immediately
        scheduler.run_all()
        # No exception should be raised

    def test_task_with_empty_func(self):
        scheduler = TaskScheduler()

        def noop():
            pass

        task = Task(task_id="t", func=noop)
        scheduler._execute(task)
        assert task.status == TaskStatus.COMPLETED
        assert task.result is None