"""
Tests for tengod.reliability — comprehensive reliability module.

Covers:
  - TokenBucket / SlidingWindow / RateLimiter
  - CircuitBreaker (all states, transitions, fallback, context manager, decorator)
  - EnhancedHealthChecker (all check methods, check_all, health_score)
  - PerformanceBenchmark (benchmark_function, specific benchmarks, report)
  - ReliabilityConfig / ReliabilityMonitor
  - Helper functions: timeit, retry, safe_call
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest

from tengod.reliability import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerState,
    EnhancedHealthChecker,
    PerformanceBenchmark,
    RateLimiter,
    ReliabilityConfig,
    ReliabilityMonitor,
    SlidingWindow,
    TokenBucket,
    retry,
    safe_call,
    timeit,
)


# ============================================================================
# TokenBucket
# ============================================================================

class TestTokenBucket:
    """Tests for TokenBucket rate limiter."""

    def test_init_defaults(self):
        tb = TokenBucket(capacity=10, refill_rate_per_second=5.0)
        assert tb.capacity == 10
        assert tb.refill_rate_per_second == 5.0
        assert tb.tokens == 10.0

    def test_init_negative_capacity_raises(self):
        with pytest.raises(ValueError, match="capacity must be positive"):
            TokenBucket(capacity=0, refill_rate_per_second=1.0)
        with pytest.raises(ValueError, match="capacity must be positive"):
            TokenBucket(capacity=-1, refill_rate_per_second=1.0)

    def test_init_negative_refill_rate_raises(self):
        with pytest.raises(ValueError, match="refill_rate_per_second must be positive"):
            TokenBucket(capacity=10, refill_rate_per_second=0.0)
        with pytest.raises(ValueError, match="refill_rate_per_second must be positive"):
            TokenBucket(capacity=10, refill_rate_per_second=-1.0)

    def test_allow_consumes_token(self):
        tb = TokenBucket(capacity=5, refill_rate_per_second=100.0)
        assert tb.allow() is True
        assert tb.get_remaining() == 4

    def test_allow_with_custom_cost(self):
        tb = TokenBucket(capacity=10, refill_rate_per_second=100.0)
        assert tb.allow(cost=3) is True
        assert tb.get_remaining() == 7

    def test_allow_denies_when_empty(self):
        tb = TokenBucket(capacity=1, refill_rate_per_second=0.001)  # very slow refill
        assert tb.allow() is True
        assert tb.allow() is False

    def test_allow_denies_when_cost_exceeds_tokens(self):
        tb = TokenBucket(capacity=3, refill_rate_per_second=0.001)
        assert tb.allow(cost=5) is False

    def test_get_remaining_returns_int(self):
        tb = TokenBucket(capacity=10, refill_rate_per_second=5.0)
        remaining = tb.get_remaining()
        assert isinstance(remaining, int)
        assert remaining == 10

    def test_refill_over_time(self):
        tb = TokenBucket(capacity=10, refill_rate_per_second=1000.0)
        # Consume all tokens
        for _ in range(10):
            tb.allow()
        assert tb.get_remaining() == 0
        # Wait for refill
        time.sleep(0.05)
        remaining = tb.get_remaining()
        assert remaining > 0

    def test_refill_does_not_exceed_capacity(self):
        tb = TokenBucket(capacity=5, refill_rate_per_second=1000.0)
        time.sleep(0.1)
        assert tb.get_remaining() <= 5

    def test_thread_safety(self):
        tb = TokenBucket(capacity=100, refill_rate_per_second=1000.0)
        results = []

        def worker():
            for _ in range(25):
                results.append(tb.allow())

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sum(results) == 100
        assert tb.get_remaining() == 0


# ============================================================================
# SlidingWindow
# ============================================================================

class TestSlidingWindow:
    """Tests for SlidingWindow rate limiter."""

    def test_init_defaults(self):
        sw = SlidingWindow(limit=10, window_seconds=1.0)
        assert sw.limit == 10
        assert sw.window_seconds == 1.0
        assert sw._use_redis is False

    def test_init_negative_limit_raises(self):
        with pytest.raises(ValueError, match="limit must be positive"):
            SlidingWindow(limit=0, window_seconds=1.0)
        with pytest.raises(ValueError, match="limit must be positive"):
            SlidingWindow(limit=-1, window_seconds=1.0)

    def test_init_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds must be positive"):
            SlidingWindow(limit=10, window_seconds=0.0)
        with pytest.raises(ValueError, match="window_seconds must be positive"):
            SlidingWindow(limit=10, window_seconds=-1.0)

    def test_allow_within_limit(self):
        sw = SlidingWindow(limit=5, window_seconds=60.0)
        for _ in range(5):
            assert sw.allow() is True

    def test_allow_exceeds_limit(self):
        sw = SlidingWindow(limit=3, window_seconds=60.0)
        assert sw.allow() is True
        assert sw.allow() is True
        assert sw.allow() is True
        assert sw.allow() is False

    def test_get_remaining(self):
        sw = SlidingWindow(limit=10, window_seconds=60.0)
        assert sw.get_remaining() == 10
        sw.allow()
        sw.allow()
        assert sw.get_remaining() == 8

    def test_get_remaining_at_limit(self):
        sw = SlidingWindow(limit=3, window_seconds=60.0)
        for _ in range(3):
            sw.allow()
        assert sw.get_remaining() == 0

    def test_window_expiry_in_memory(self):
        sw = SlidingWindow(limit=3, window_seconds=0.05)
        for _ in range(3):
            sw.allow()
        assert sw.allow() is False
        time.sleep(0.1)
        # After window expires, should allow again
        assert sw.allow() is True

    def test_redis_client_initialization(self):
        mock_redis = MagicMock()
        sw = SlidingWindow(limit=10, window_seconds=1.0, redis_client=mock_redis)
        assert sw._use_redis is True

    def test_redis_allow_success(self):
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe
        # zremrangebyscore, zcard, zadd, expire → 4 results
        mock_pipe.execute.return_value = [0, 2, 1, 1]  # current_count=2 < limit=10

        sw = SlidingWindow(limit=10, window_seconds=1.0, redis_client=mock_redis)
        assert sw.allow() is True

    def test_redis_allow_exceeds_limit(self):
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe
        mock_pipe.execute.return_value = [0, 10, 1, 1]  # current_count=10, not < limit=5

        sw = SlidingWindow(limit=5, window_seconds=1.0, redis_client=mock_redis)
        assert sw.allow() is False

    def test_redis_allow_falls_back_to_memory(self):
        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = RuntimeError("redis down")

        sw = SlidingWindow(limit=5, window_seconds=60.0, redis_client=mock_redis)
        # First call triggers redis error, falls back to memory
        result = sw.allow()
        assert result in (True, False)
        # After fallback, _use_redis should be False
        assert sw._use_redis is False

    def test_redis_get_remaining_success(self):
        mock_redis = MagicMock()
        mock_redis.zcard.return_value = 3
        mock_redis.zremrangebyscore.return_value = 0

        sw = SlidingWindow(limit=10, window_seconds=1.0, redis_client=mock_redis)
        assert sw.get_remaining() == 7

    def test_redis_get_remaining_expired_entries(self):
        """Test get_remaining purges expired entries."""
        mock_redis = MagicMock()
        mock_redis.zremrangebyscore.side_effect = RuntimeError("redis down")

        sw = SlidingWindow(limit=10, window_seconds=0.01, redis_client=mock_redis)
        sw.allow()  # triggers redis fallback, adds one request
        # Manually add an old timestamp to test the while loop purge
        sw._requests.appendleft(time.monotonic() - 1.0)
        remaining = sw.get_remaining()
        assert isinstance(remaining, int)
        assert remaining <= 10


# ============================================================================
# RateLimiter
# ============================================================================

class TestRateLimiter:
    """Tests for RateLimiter wrapper."""

    def test_token_bucket_algorithm(self):
        rl = RateLimiter("token_bucket", capacity=5, refill_rate_per_second=100.0)
        assert rl.algorithm == "token_bucket"
        assert rl.allow() is True

    def test_sliding_window_algorithm(self):
        rl = RateLimiter("sliding_window", limit=5, window_seconds=60.0)
        assert rl.algorithm == "sliding_window"
        assert rl.allow() is True

    def test_unknown_algorithm_raises(self):
        with pytest.raises(ValueError, match="Unknown algorithm"):
            RateLimiter("invalid_algo")

    def test_get_remaining_delegates(self):
        rl = RateLimiter("token_bucket", capacity=10, refill_rate_per_second=100.0)
        assert rl.get_remaining() == 10

    def test_default_parameters(self):
        rl = RateLimiter("token_bucket")
        assert rl.get_remaining() == 100  # default capacity

    def test_sliding_window_with_redis(self):
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe
        mock_pipe.execute.return_value = [0, 0, 1, 1]

        rl = RateLimiter(
            "sliding_window",
            limit=50,
            window_seconds=30.0,
            redis_client=mock_redis,
        )
        assert rl.allow() is True


# ============================================================================
# CircuitBreaker
# ============================================================================

class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_init_defaults(self):
        cb = CircuitBreaker()
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 30.0
        assert cb.success_threshold == 2
        assert cb.name == "default"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_init_custom_values(self):
        cb = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=10.0,
            success_threshold=5,
            name="my_cb",
        )
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 10.0
        assert cb.success_threshold == 5
        assert cb.name == "my_cb"

    def test_init_negative_failure_threshold_raises(self):
        with pytest.raises(ValueError, match="failure_threshold must be positive"):
            CircuitBreaker(failure_threshold=0)
        with pytest.raises(ValueError, match="failure_threshold must be positive"):
            CircuitBreaker(failure_threshold=-1)

    def test_init_negative_recovery_timeout_raises(self):
        with pytest.raises(ValueError, match="recovery_timeout must be positive"):
            CircuitBreaker(recovery_timeout=0.0)
        with pytest.raises(ValueError, match="recovery_timeout must be positive"):
            CircuitBreaker(recovery_timeout=-1.0)

    def test_init_negative_success_threshold_raises(self):
        with pytest.raises(ValueError, match="success_threshold must be positive"):
            CircuitBreaker(success_threshold=0)
        with pytest.raises(ValueError, match="success_threshold must be positive"):
            CircuitBreaker(success_threshold=-1)

    # ── state transitions ──────────────────────────────────────

    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CircuitBreakerState.CLOSED

    def test_transitions_to_open_after_failures(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0)
        for _ in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
            except RuntimeError:
                pass
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 2

    def test_raises_circuit_breaker_error_when_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except RuntimeError:
            pass
        assert cb.state == CircuitBreakerState.OPEN
        with pytest.raises(CircuitBreakerError, match="is OPEN"):
            cb.call(lambda: "ok")

    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except RuntimeError:
            pass
        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(0.05)
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(
            failure_threshold=1, recovery_timeout=0.01, success_threshold=2
        )
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except RuntimeError:
            pass
        time.sleep(0.05)
        assert cb.state == CircuitBreakerState.HALF_OPEN

        cb.call(lambda: "ok")
        cb.call(lambda: "ok")
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(
            failure_threshold=1, recovery_timeout=0.01, success_threshold=2
        )
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except RuntimeError:
            pass
        time.sleep(0.05)
        assert cb.state == CircuitBreakerState.HALF_OPEN

        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom2")))
        except RuntimeError:
            pass
        assert cb.state == CircuitBreakerState.OPEN

    # ── call ───────────────────────────────────────────────────

    def test_call_returns_result(self):
        cb = CircuitBreaker()
        result = cb.call(lambda x, y: x + y, 3, 4)
        assert result == 7

    def test_call_with_kwargs(self):
        cb = CircuitBreaker()
        result = cb.call(lambda a=0, b=0: a + b, a=10, b=20)
        assert result == 30

    def test_call_with_fallback_when_open(self):
        fallback_fn = MagicMock(return_value="fallback_result")
        cb = CircuitBreaker(
            failure_threshold=1, recovery_timeout=10.0, fallback=fallback_fn
        )
        # First call fails → fallback is called (line 307), state becomes OPEN
        result1 = cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert result1 == "fallback_result"
        assert cb.state == CircuitBreakerState.OPEN
        # Second call → circuit is OPEN → fallback is called (line 296)
        result2 = cb.call(lambda: "should_not_be_called")
        assert result2 == "fallback_result"
        assert fallback_fn.call_count == 2

    def test_call_with_fallback_on_failure(self):
        fallback_fn = MagicMock(return_value="fallback")
        cb = CircuitBreaker(failure_threshold=10, fallback=fallback_fn)
        result = cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert result == "fallback"
        fallback_fn.assert_called_once()

    def test_call_success_resets_in_closed_state(self):
        cb = CircuitBreaker(failure_threshold=5)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except RuntimeError:
            pass
        assert cb.failure_count == 1
        cb.call(lambda: "ok")
        assert cb.failure_count == 0

    # ── reset / trip ───────────────────────────────────────────

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except RuntimeError:
            pass
        assert cb.state == CircuitBreakerState.OPEN
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.last_failure_time is None

    def test_trip(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitBreakerState.CLOSED
        cb.trip()
        assert cb.state == CircuitBreakerState.OPEN

    # ── context manager ────────────────────────────────────────

    def test_context_manager_success(self):
        cb = CircuitBreaker()
        with cb:
            pass
        assert cb.state == CircuitBreakerState.CLOSED

    def test_context_manager_raises_when_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except RuntimeError:
            pass
        with pytest.raises(CircuitBreakerError, match="is OPEN"):
            with cb:
                pass

    def test_context_manager_with_exception(self):
        cb = CircuitBreaker()
        with pytest.raises(RuntimeError):
            with cb:
                raise RuntimeError("test error")
        assert cb.failure_count == 1

    def test_context_manager_with_exception_and_fallback(self):
        fallback_called = []

        def fallback_fn():
            fallback_called.append(True)

        cb = CircuitBreaker(failure_threshold=10, fallback=fallback_fn)
        # When fallback is set, __exit__ returns True → suppresses exception
        with cb:
            raise RuntimeError("test error")
        assert len(fallback_called) == 0  # fallback is not called in __exit__, just suppress
        assert cb.failure_count == 1

    def test_context_manager_half_open_transition(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except RuntimeError:
            pass
        time.sleep(0.05)
        # Now half-open
        with cb:
            pass
        assert cb.state == CircuitBreakerState.HALF_OPEN

    # ── decorator ──────────────────────────────────────────────

    def test_decorator_success(self):
        cb = CircuitBreaker()

        @cb
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5

    def test_decorator_failure_propagates(self):
        cb = CircuitBreaker(failure_threshold=10)

        @cb
        def fail():
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            fail()
        assert cb.failure_count == 1

    def test_decorator_open_raises(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)

        @cb
        def fail():
            raise RuntimeError("fail")

        try:
            fail()
        except RuntimeError:
            pass
        with pytest.raises(CircuitBreakerError):
            fail()

    def test_decorator_with_fallback(self):
        fallback_fn = MagicMock(return_value="fallback")
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0, fallback=fallback_fn)

        @cb
        def fail():
            raise RuntimeError("fail")

        try:
            fail()
        except RuntimeError:
            pass
        result = fail()
        assert result == "fallback"

    # ── properties ─────────────────────────────────────────────

    def test_last_failure_time(self):
        cb = CircuitBreaker()
        assert cb.last_failure_time is None
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except RuntimeError:
            pass
        assert cb.last_failure_time is not None

    def test_success_count(self):
        cb = CircuitBreaker()
        assert cb.success_count == 0
        cb.call(lambda: "ok")
        assert cb.success_count == 1


# ============================================================================
# EnhancedHealthChecker
# ============================================================================

class TestEnhancedHealthChecker:
    """Tests for EnhancedHealthChecker."""

    def test_init(self):
        hc = EnhancedHealthChecker()
        assert hc is not None

    # ── check_database ─────────────────────────────────────────

    def test_check_database_healthy(self):
        mock_ds_module = MagicMock()
        mock_ds_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.stats.return_value = {"queries": 100}
        mock_ds_class.return_value = mock_instance
        mock_ds_module.DataStore = mock_ds_class

        with patch.dict("sys.modules", {"tengod.data_store": mock_ds_module}):
            hc = EnhancedHealthChecker()
            result = hc.check_database()
            assert result["status"] == "healthy"
            assert result["stats"] == {"queries": 100}

    def test_check_database_unhealthy(self):
        mock_ds_module = MagicMock()
        mock_ds_module.DataStore = MagicMock(side_effect=RuntimeError("db down"))

        with patch.dict("sys.modules", {"tengod.data_store": mock_ds_module}):
            hc = EnhancedHealthChecker()
            result = hc.check_database()
            assert result["status"] == "unhealthy"
            assert "db down" in result["message"]

    def test_check_database_stats_not_dict(self):
        mock_ds_module = MagicMock()
        mock_ds_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.stats.return_value = "not a dict"
        mock_ds_class.return_value = mock_instance
        mock_ds_module.DataStore = mock_ds_class

        with patch.dict("sys.modules", {"tengod.data_store": mock_ds_module}):
            hc = EnhancedHealthChecker()
            result = hc.check_database()
            assert result["status"] == "healthy"
            assert result["stats"] == {"ok": True}

    # ── check_cache ────────────────────────────────────────────

    def test_check_cache_healthy(self):
        with patch("tengod.cache_manager.get_cache_manager") as mock_gcm:
            mock_cm = MagicMock()
            mock_cm.health_check.return_value = {"status": "healthy", "message": "ok"}
            mock_gcm.return_value = mock_cm

            hc = EnhancedHealthChecker()
            result = hc.check_cache()
            assert result["status"] == "healthy"

    def test_check_cache_fallback_to_memory(self):
        with patch("tengod.cache_manager.get_cache_manager", side_effect=ImportError("no cache")):
            with patch("tengod.cache_manager.MemoryCacheManager") as mock_mcm:
                mock_instance = MagicMock()
                mock_instance.get.return_value = "1"
                mock_mcm.return_value = mock_instance

                hc = EnhancedHealthChecker()
                result = hc.check_cache()
                assert result["status"] == "healthy"
                assert result["mode"] == "memory"

    def test_check_cache_both_fail(self):
        with patch("tengod.cache_manager.get_cache_manager", side_effect=ImportError("no cache")):
            with patch("tengod.cache_manager.MemoryCacheManager", side_effect=RuntimeError("memory fail")):
                hc = EnhancedHealthChecker()
                result = hc.check_cache()
                assert result["status"] == "unhealthy"

    def test_check_cache_health_not_dict(self):
        with patch("tengod.cache_manager.get_cache_manager") as mock_gcm:
            mock_cm = MagicMock()
            mock_cm.health_check.return_value = "not a dict"
            mock_gcm.return_value = mock_cm

            hc = EnhancedHealthChecker()
            result = hc.check_cache()
            assert result["status"] == "healthy"

    # ── check_vector_store ─────────────────────────────────────

    def test_check_vector_store_healthy(self):
        mock_vs_module = MagicMock()
        mock_vs_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.info.return_value = {"count": 1000}
        mock_vs_class.return_value = mock_instance
        mock_vs_module.VectorStore = mock_vs_class

        with patch.dict("sys.modules", {"tengod.vector_store": mock_vs_module}):
            hc = EnhancedHealthChecker()
            result = hc.check_vector_store()
            assert result["status"] == "healthy"

    def test_check_vector_store_fallback_to_pg(self):
        mock_vs_module = MagicMock()
        mock_vs_module.VectorStore = MagicMock(side_effect=ImportError("no vs"))
        mock_vs_pg_module = MagicMock()
        mock_vs_pg_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.info.return_value = {"count": 500}
        mock_vs_pg_class.return_value = mock_instance
        mock_vs_pg_module.VectorStore = mock_vs_pg_class

        with patch.dict("sys.modules", {
            "tengod.vector_store": mock_vs_module,
            "tengod.vector_store_pg": mock_vs_pg_module,
        }):
            hc = EnhancedHealthChecker()
            result = hc.check_vector_store()
            assert result["status"] == "healthy"

    def test_check_vector_store_both_fail(self):
        mock_vs_module = MagicMock()
        mock_vs_module.VectorStore = MagicMock(side_effect=ImportError("no vs"))
        mock_vs_pg_module = MagicMock()
        mock_vs_pg_module.VectorStore = MagicMock(side_effect=RuntimeError("pg fail"))

        with patch.dict("sys.modules", {
            "tengod.vector_store": mock_vs_module,
            "tengod.vector_store_pg": mock_vs_pg_module,
        }):
            hc = EnhancedHealthChecker()
            result = hc.check_vector_store()
            assert result["status"] == "unhealthy"

    def test_check_vector_store_info_not_dict(self):
        mock_vs_module = MagicMock()
        mock_vs_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.info.return_value = "not dict"
        mock_vs_class.return_value = mock_instance
        mock_vs_module.VectorStore = mock_vs_class

        with patch.dict("sys.modules", {"tengod.vector_store": mock_vs_module}):
            hc = EnhancedHealthChecker()
            result = hc.check_vector_store()
            assert result["status"] == "healthy"
            assert result["info"] == {"ok": True}

    # ── check_system_resources ─────────────────────────────────

    def test_check_system_resources_healthy(self):
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 25.0
        mock_mem = MagicMock()
        mock_mem.percent = 50.0
        mock_mem.used = 4 * 1024 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_mem
        mock_disk = MagicMock()
        mock_disk.percent = 30.0
        mock_psutil.disk_usage.return_value = mock_disk

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            hc = EnhancedHealthChecker()
            result = hc.check_system_resources()
            assert result["status"] == "healthy"
            assert result["cpu_percent"] == 25.0
            assert result["memory_percent"] == 50.0

    def test_check_system_resources_import_error(self):
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.side_effect = ImportError("no psutil")

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            hc = EnhancedHealthChecker()
            result = hc.check_system_resources()
            assert result["status"] == "degraded"
            assert result["cpu_percent"] == 0.0
            assert result["memory_percent"] == 0.0
            assert result["disk_percent"] == 0.0

    # ── check_core_engines ─────────────────────────────────────

    def test_check_core_engines_all_healthy(self):
        mock_mod = MagicMock()
        mock_cls = MagicMock()
        mock_engine = MagicMock()
        mock_engine.info = MagicMock()
        mock_cls.return_value = mock_engine
        mock_mod.LiunianJudgmentEngine = mock_cls
        mock_mod.XuankongEngine = mock_cls
        mock_mod.QizhengEngine = mock_cls

        mock_importlib = MagicMock()
        mock_importlib.import_module.return_value = mock_mod

        with patch.dict("sys.modules", {"importlib": mock_importlib}):
            hc = EnhancedHealthChecker()
            result = hc.check_core_engines()
            assert result["liunian_judgment"]["status"] == "healthy"
            assert result["xuankong"]["status"] == "healthy"
            assert result["qizheng"]["status"] == "healthy"

    def test_check_core_engines_partial_failure(self):
        call_count = [0]

        def mock_import_side_effect(name, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ImportError("no liunian")
            mod = MagicMock()
            cls = MagicMock()
            engine = MagicMock()
            engine.info = MagicMock()
            cls.return_value = engine
            if name == "tengod.fengshui.xuankong":
                mod.XuankongEngine = cls
            elif name == "tengod.qizheng.engine":
                mod.QizhengEngine = cls
            return mod

        mock_importlib = MagicMock()
        mock_importlib.import_module.side_effect = mock_import_side_effect

        with patch.dict("sys.modules", {"importlib": mock_importlib}):
            hc = EnhancedHealthChecker()
            result = hc.check_core_engines()
            assert result["liunian_judgment"]["status"] == "unhealthy"
            assert result["xuankong"]["status"] == "healthy"
            assert result["qizheng"]["status"] == "healthy"

    # ── check_all ──────────────────────────────────────────────

    def test_check_all_healthy(self):
        hc = EnhancedHealthChecker()
        with patch.object(hc, "check_database", return_value={"status": "healthy"}):
            with patch.object(hc, "check_cache", return_value={"status": "healthy"}):
                with patch.object(hc, "check_vector_store", return_value={"status": "healthy"}):
                    with patch.object(hc, "check_system_resources", return_value={"status": "healthy"}):
                        with patch.object(hc, "check_core_engines", return_value={
                            "liunian_judgment": {"status": "healthy"},
                            "xuankong": {"status": "healthy"},
                            "qizheng": {"status": "healthy"},
                        }):
                            result = hc.check_all()
                            assert result["status"] == "healthy"
                            assert result["healthy_engines"] == 3
                            assert result["total_engines"] == 3
                            assert len(result["reasons"]) == 0

    def test_check_all_degraded(self):
        hc = EnhancedHealthChecker()
        with patch.object(hc, "check_database", return_value={"status": "unhealthy", "message": "db error"}):
            with patch.object(hc, "check_cache", return_value={"status": "healthy"}):
                with patch.object(hc, "check_vector_store", return_value={"status": "healthy"}):
                    with patch.object(hc, "check_system_resources", return_value={"status": "healthy"}):
                        with patch.object(hc, "check_core_engines", return_value={
                            "liunian_judgment": {"status": "healthy"},
                            "xuankong": {"status": "healthy"},
                            "qizheng": {"status": "healthy"},
                        }):
                            result = hc.check_all()
                            assert result["status"] == "degraded"
                            assert len(result["reasons"]) >= 1

    def test_check_all_critical(self):
        hc = EnhancedHealthChecker()
        with patch.object(hc, "check_database", return_value={"status": "unhealthy", "message": "db error"}):
            with patch.object(hc, "check_cache", return_value={"status": "unhealthy", "message": "cache error"}):
                with patch.object(hc, "check_vector_store", return_value={"status": "healthy"}):
                    with patch.object(hc, "check_system_resources", return_value={"status": "healthy"}):
                        with patch.object(hc, "check_core_engines", return_value={
                            "liunian_judgment": {"status": "healthy"},
                            "xuankong": {"status": "healthy"},
                            "qizheng": {"status": "healthy"},
                        }):
                            result = hc.check_all()
                            assert result["status"] == "critical"

    def test_check_all_system_resources_degraded_adds_reason(self):
        hc = EnhancedHealthChecker()
        with patch.object(hc, "check_database", return_value={"status": "healthy"}):
            with patch.object(hc, "check_cache", return_value={"status": "healthy"}):
                with patch.object(hc, "check_vector_store", return_value={"status": "healthy"}):
                    with patch.object(hc, "check_system_resources", return_value={"status": "degraded", "message": "resource issue"}):
                        with patch.object(hc, "check_core_engines", return_value={
                            "liunian_judgment": {"status": "healthy"},
                            "xuankong": {"status": "healthy"},
                            "qizheng": {"status": "healthy"},
                        }):
                            result = hc.check_all()
                            assert "resource warning" in str(result["reasons"])

    def test_check_all_engine_info_not_dict(self):
        hc = EnhancedHealthChecker()
        with patch.object(hc, "check_database", return_value={"status": "healthy"}):
            with patch.object(hc, "check_cache", return_value={"status": "healthy"}):
                with patch.object(hc, "check_vector_store", return_value={"status": "healthy"}):
                    with patch.object(hc, "check_system_resources", return_value={"status": "healthy"}):
                        with patch.object(hc, "check_core_engines", return_value={
                            "engine1": "not a dict",
                            "engine2": {"status": "healthy"},
                        }):
                            result = hc.check_all()
                            assert result["total_engines"] == 2
                            assert result["healthy_engines"] == 1

    def test_check_all_non_dict_check_result(self):
        """Test check_all when a check method returns a non-dict."""
        hc = EnhancedHealthChecker()
        with patch.object(hc, "check_database", return_value="error string"):
            with patch.object(hc, "check_cache", return_value={"status": "healthy"}):
                with patch.object(hc, "check_vector_store", return_value={"status": "healthy"}):
                    with patch.object(hc, "check_system_resources", return_value={"status": "healthy"}):
                        with patch.object(hc, "check_core_engines", return_value={
                            "liunian_judgment": {"status": "healthy"},
                            "xuankong": {"status": "healthy"},
                            "qizheng": {"status": "healthy"},
                        }):
                            result = hc.check_all()
                            assert "reasons" in result

    # ── get_health_score ───────────────────────────────────────

    def test_get_health_score_all_healthy(self):
        hc = EnhancedHealthChecker()
        with patch.object(hc, "check_all", return_value={
            "checks": {
                "database": {"status": "healthy"},
                "cache": {"status": "healthy"},
                "vector_store": {"status": "healthy"},
                "system_resources": {"status": "healthy"},
                "core_engines": {"status": "healthy"},
            }
        }):
            assert hc.get_health_score() == 100

    def test_get_health_score_with_unhealthy(self):
        hc = EnhancedHealthChecker()
        with patch.object(hc, "check_all", return_value={
            "checks": {
                "database": {"status": "unhealthy"},
                "cache": {"status": "healthy"},
                "vector_store": {"status": "healthy"},
                "system_resources": {"status": "healthy"},
                "core_engines": {"status": "healthy"},
            }
        }):
            assert hc.get_health_score() == 80

    def test_get_health_score_with_degraded(self):
        hc = EnhancedHealthChecker()
        with patch.object(hc, "check_all", return_value={
            "checks": {
                "database": {"status": "healthy"},
                "cache": {"status": "degraded"},
                "vector_store": {"status": "healthy"},
                "system_resources": {"status": "healthy"},
                "core_engines": {"status": "healthy"},
            }
        }):
            assert hc.get_health_score() == 90

    def test_get_health_score_with_skipped(self):
        hc = EnhancedHealthChecker()
        with patch.object(hc, "check_all", return_value={
            "checks": {
                "database": {"status": "healthy"},
                "cache": {"status": "skipped"},
                "vector_store": {"status": "healthy"},
                "system_resources": {"status": "healthy"},
                "core_engines": {"status": "healthy"},
            }
        }):
            assert hc.get_health_score() == 98

    def test_get_health_score_minimum_zero(self):
        hc = EnhancedHealthChecker()
        with patch.object(hc, "check_all", return_value={
            "checks": {
                "database": {"status": "unhealthy"},
                "cache": {"status": "unhealthy"},
                "vector_store": {"status": "unhealthy"},
                "system_resources": {"status": "unhealthy"},
                "core_engines": {"status": "unhealthy"},
                "extra1": {"status": "unhealthy"},
                "extra2": {"status": "unhealthy"},
            }
        }):
            assert hc.get_health_score() == 0

    def test_get_health_score_non_dict_check(self):
        hc = EnhancedHealthChecker()
        with patch.object(hc, "check_all", return_value={
            "checks": {
                "database": "string not dict",
                "cache": {"status": "healthy"},
                "vector_store": {"status": "healthy"},
                "system_resources": {"status": "healthy"},
                "core_engines": {"status": "healthy"},
            }
        }):
            score = hc.get_health_score()
            assert score >= 0


# ============================================================================
# PerformanceBenchmark
# ============================================================================

class TestPerformanceBenchmark:
    """Tests for PerformanceBenchmark."""

    def test_init(self):
        pb = PerformanceBenchmark()
        assert pb._history == {}

    def test_benchmark_function_basic(self):
        pb = PerformanceBenchmark()
        stats = pb.benchmark_function(lambda: sum(range(100)), iterations=20, warmup=2)
        assert "avg_ms" in stats
        assert "p50" in stats
        assert "p95" in stats
        assert "p99" in stats
        assert "max_ms" in stats
        assert "min_ms" in stats
        assert stats["iterations"] == 20
        assert stats["avg_ms"] >= 0.0

    def test_benchmark_function_zero_iterations(self):
        pb = PerformanceBenchmark()
        stats = pb.benchmark_function(lambda: 1, iterations=0)
        assert stats["avg_ms"] == 0.0
        assert stats["iterations"] == 0

    def test_benchmark_function_negative_iterations(self):
        pb = PerformanceBenchmark()
        stats = pb.benchmark_function(lambda: 1, iterations=-5)
        assert stats["avg_ms"] == 0.0
        assert stats["iterations"] == -5

    def test_benchmark_function_warmup_handles_exceptions(self):
        pb = PerformanceBenchmark()
        call_count = [0]

        def flaky_func():
            call_count[0] += 1
            if call_count[0] <= 5:
                raise RuntimeError("warmup failure")
            return 42

        stats = pb.benchmark_function(flaky_func, iterations=10, warmup=5)
        assert stats["iterations"] == 10
        assert "avg_ms" in stats

    def test_benchmark_function_records_history(self):
        pb = PerformanceBenchmark()

        def my_func():
            return sum(range(10))

        pb.benchmark_function(my_func, iterations=5, warmup=1)
        assert "my_func" in pb._history

    def test_benchmark_function_anonymous(self):
        pb = PerformanceBenchmark()
        pb.benchmark_function(lambda: 1, iterations=5, warmup=1)
        # lambda __name__ is '<lambda>', not 'anonymous'
        assert "<lambda>" in pb._history

    def test_benchmark_function_percentile(self):
        pb = PerformanceBenchmark()
        stats = pb.benchmark_function(lambda: sum(range(10)), iterations=100, warmup=0)
        assert stats["p50"] <= stats["p95"] <= stats["p99"]
        assert stats["min_ms"] <= stats["p50"]
        assert stats["max_ms"] >= stats["p95"]

    def test_benchmark_bazi_calc_error(self):
        # spec=[] prevents attribute auto-creation, so BaziChart import fails
        mock_bazi_module = MagicMock(spec=[])

        with patch.dict("sys.modules", {"tengod.bazi_calculator": mock_bazi_module}):
            pb = PerformanceBenchmark()
            result = pb.benchmark_bazi_calc(iterations=10)
            assert "error" in result
            assert result["iterations"] == 10

    def test_benchmark_bazi_calc_success(self):
        """Test benchmark_bazi_calc when BaziChart is importable."""
        pb = PerformanceBenchmark()
        result = pb.benchmark_bazi_calc(iterations=5)
        assert "avg_ms" in result
        assert result["iterations"] == 5

    def test_benchmark_vector_search_error(self):
        mock_vs_module = MagicMock(spec=[])

        with patch.dict("sys.modules", {"tengod.vector_store": mock_vs_module}):
            pb = PerformanceBenchmark()
            result = pb.benchmark_vector_search(iterations=10)
            assert "error" in result
            assert result["iterations"] == 10

    def test_benchmark_full_pipeline_error(self):
        mock_bazi_module = MagicMock(spec=[])

        with patch.dict("sys.modules", {"tengod.bazi_calculator": mock_bazi_module}):
            pb = PerformanceBenchmark()
            result = pb.benchmark_full_pipeline(iterations=5)
            assert "error" in result
            assert result["iterations"] == 5

    def test_benchmark_full_pipeline_success(self):
        """Test benchmark_full_pipeline when BaziChart is importable."""
        pb = PerformanceBenchmark()
        result = pb.benchmark_full_pipeline(iterations=3)
        assert "avg_ms" in result
        assert result["iterations"] == 3

    def test_report_empty(self):
        pb = PerformanceBenchmark()
        report = pb.report()
        assert "No benchmarks recorded yet" in report

    def test_report_with_history(self):
        pb = PerformanceBenchmark()
        pb._history = {
            "test_func": {
                "iterations": 10,
                "avg_ms": 1.2345,
                "p50": 1.0,
                "p95": 2.0,
                "p99": 3.0,
                "min_ms": 0.5,
                "max_ms": 5.0,
            }
        }
        report = pb.report()
        assert "Performance Benchmark Report" in report
        assert "test_func" in report
        assert "1.2345 ms" in report


# ============================================================================
# ReliabilityConfig
# ============================================================================

class TestReliabilityConfig:
    """Tests for ReliabilityConfig dataclass."""

    def test_defaults(self):
        cfg = ReliabilityConfig()
        assert cfg.max_error_rate == 0.05
        assert cfg.max_avg_latency_ms == 1000.0
        assert cfg.max_memory_percent == 90.0
        assert cfg.max_cpu_percent == 90.0
        assert cfg.min_available_engines == 3

    def test_custom_values(self):
        cfg = ReliabilityConfig(
            max_error_rate=0.1,
            max_avg_latency_ms=500.0,
            max_memory_percent=80.0,
            max_cpu_percent=85.0,
            min_available_engines=2,
        )
        assert cfg.max_error_rate == 0.1
        assert cfg.max_avg_latency_ms == 500.0
        assert cfg.max_memory_percent == 80.0
        assert cfg.max_cpu_percent == 85.0
        assert cfg.min_available_engines == 2

    def test_as_dict(self):
        cfg = ReliabilityConfig()
        d = cfg.as_dict()
        assert isinstance(d, dict)
        assert d["max_error_rate"] == 0.05
        assert d["max_avg_latency_ms"] == 1000.0
        assert d["max_memory_percent"] == 90.0
        assert d["max_cpu_percent"] == 90.0
        assert d["min_available_engines"] == 3


# ============================================================================
# ReliabilityMonitor
# ============================================================================

class TestReliabilityMonitor:
    """Tests for ReliabilityMonitor."""

    def test_init_default_config(self):
        monitor = ReliabilityMonitor()
        assert isinstance(monitor.config, ReliabilityConfig)
        assert isinstance(monitor.health_checker, EnhancedHealthChecker)
        assert isinstance(monitor.benchmark, PerformanceBenchmark)

    def test_init_custom_config(self):
        cfg = ReliabilityConfig(max_error_rate=0.01)
        monitor = ReliabilityMonitor(config=cfg)
        assert monitor.config.max_error_rate == 0.01

    def test_record_failure(self):
        monitor = ReliabilityMonitor()
        monitor.record_failure("test_component")
        monitor.record_failure("test_component")
        monitor.record_failure("other_component")
        failures = monitor.get_component_failures()
        assert failures["test_component"] == 2
        assert failures["other_component"] == 1

    def test_get_component_failures_empty(self):
        monitor = ReliabilityMonitor()
        assert monitor.get_component_failures() == {}

    def test_get_component_failures_returns_copy(self):
        monitor = ReliabilityMonitor()
        monitor.record_failure("comp")
        failures = monitor.get_component_failures()
        failures["comp"] = 999
        assert monitor.get_component_failures()["comp"] == 1

    def test_get_metrics_snapshot_error(self):
        with patch("tengod.metrics_collector.metrics.get_snapshot", side_effect=ImportError("no metrics")):
            monitor = ReliabilityMonitor()
            result = monitor.get_metrics_snapshot()
            assert "error" in result
            assert "timestamp" in result

    def test_get_metrics_snapshot_success(self):
        with patch("tengod.metrics_collector.metrics") as mock_metrics:
            mock_metrics.get_snapshot.return_value = {"requests": {"total": 100, "errors": 2}}
            monitor = ReliabilityMonitor()
            result = monitor.get_metrics_snapshot()
            assert result["requests"]["total"] == 100

    # ── check_reliability ──────────────────────────────────────

    def test_check_reliability_healthy(self):
        monitor = ReliabilityMonitor()
        with patch.object(monitor.health_checker, "check_all", return_value={
            "status": "healthy",
            "checks": {
                "system_resources": {
                    "status": "healthy",
                    "cpu_percent": 10.0,
                    "memory_percent": 30.0,
                },
                "core_engines": {
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "healthy"},
                    "qizheng": {"status": "healthy"},
                },
            },
            "healthy_engines": 3,
            "total_engines": 3,
        }):
            with patch.object(monitor, "get_metrics_snapshot", return_value={
                "requests": {"total": 100, "errors": 0, "avg_latency_ms": 50.0}
            }):
                result = monitor.check_reliability()
                assert result["status"] == "healthy"
                assert len(result["reasons"]) == 0

    def test_check_reliability_high_cpu(self):
        cfg = ReliabilityConfig(max_cpu_percent=50.0)
        monitor = ReliabilityMonitor(config=cfg)
        with patch.object(monitor.health_checker, "check_all", return_value={
            "status": "healthy",
            "checks": {
                "system_resources": {
                    "status": "healthy",
                    "cpu_percent": 80.0,
                    "memory_percent": 30.0,
                },
                "core_engines": {
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "healthy"},
                    "qizheng": {"status": "healthy"},
                },
            },
            "healthy_engines": 3,
            "total_engines": 3,
        }):
            with patch.object(monitor, "get_metrics_snapshot", return_value={
                "requests": {"total": 0, "errors": 0, "avg_latency_ms": 0.0}
            }):
                result = monitor.check_reliability()
                assert result["status"] == "degraded"
                assert any("CPU" in r for r in result["reasons"])

    def test_check_reliability_high_memory(self):
        cfg = ReliabilityConfig(max_memory_percent=50.0)
        monitor = ReliabilityMonitor(config=cfg)
        with patch.object(monitor.health_checker, "check_all", return_value={
            "status": "healthy",
            "checks": {
                "system_resources": {
                    "status": "healthy",
                    "cpu_percent": 10.0,
                    "memory_percent": 80.0,
                },
                "core_engines": {
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "healthy"},
                    "qizheng": {"status": "healthy"},
                },
            },
            "healthy_engines": 3,
            "total_engines": 3,
        }):
            with patch.object(monitor, "get_metrics_snapshot", return_value={
                "requests": {"total": 0, "errors": 0, "avg_latency_ms": 0.0}
            }):
                result = monitor.check_reliability()
                assert any("Memory" in r for r in result["reasons"])

    def test_check_reliability_engine_shortage(self):
        cfg = ReliabilityConfig(min_available_engines=3)
        monitor = ReliabilityMonitor(config=cfg)
        with patch.object(monitor.health_checker, "check_all", return_value={
            "status": "degraded",
            "checks": {
                "system_resources": {
                    "status": "healthy",
                    "cpu_percent": 10.0,
                    "memory_percent": 30.0,
                },
                "core_engines": {
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "unhealthy", "message": "down"},
                    "qizheng": {"status": "unhealthy", "message": "down"},
                },
            },
            "healthy_engines": 1,
            "total_engines": 3,
        }):
            with patch.object(monitor, "get_metrics_snapshot", return_value={
                "requests": {"total": 0, "errors": 0, "avg_latency_ms": 0.0}
            }):
                result = monitor.check_reliability()
                assert any("engines available" in r for r in result["reasons"])

    def test_check_reliability_high_error_rate(self):
        monitor = ReliabilityMonitor()
        with patch.object(monitor.health_checker, "check_all", return_value={
            "status": "healthy",
            "checks": {
                "system_resources": {
                    "status": "healthy",
                    "cpu_percent": 10.0,
                    "memory_percent": 30.0,
                },
                "core_engines": {
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "healthy"},
                    "qizheng": {"status": "healthy"},
                },
            },
            "healthy_engines": 3,
            "total_engines": 3,
        }):
            with patch.object(monitor, "get_metrics_snapshot", return_value={
                "requests": {"total": 100, "errors": 20, "avg_latency_ms": 50.0}
            }):
                result = monitor.check_reliability()
                assert any("Error rate" in r for r in result["reasons"])

    def test_check_reliability_high_latency(self):
        cfg = ReliabilityConfig(max_avg_latency_ms=100.0)
        monitor = ReliabilityMonitor(config=cfg)
        with patch.object(monitor.health_checker, "check_all", return_value={
            "status": "healthy",
            "checks": {
                "system_resources": {
                    "status": "healthy",
                    "cpu_percent": 10.0,
                    "memory_percent": 30.0,
                },
                "core_engines": {
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "healthy"},
                    "qizheng": {"status": "healthy"},
                },
            },
            "healthy_engines": 3,
            "total_engines": 3,
        }):
            with patch.object(monitor, "get_metrics_snapshot", return_value={
                "requests": {"total": 50, "errors": 0, "avg_latency_ms": 500.0}
            }):
                result = monitor.check_reliability()
                assert any("latency" in r.lower() for r in result["reasons"])

    def test_check_reliability_component_failures(self):
        monitor = ReliabilityMonitor()
        for _ in range(6):
            monitor.record_failure("component_x")
        with patch.object(monitor.health_checker, "check_all", return_value={
            "status": "healthy",
            "checks": {
                "system_resources": {
                    "status": "healthy",
                    "cpu_percent": 10.0,
                    "memory_percent": 30.0,
                },
                "core_engines": {
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "healthy"},
                    "qizheng": {"status": "healthy"},
                },
            },
            "healthy_engines": 3,
            "total_engines": 3,
        }):
            with patch.object(monitor, "get_metrics_snapshot", return_value={
                "requests": {"total": 0, "errors": 0, "avg_latency_ms": 0.0}
            }):
                result = monitor.check_reliability()
                assert any("component failures" in r for r in result["reasons"])

    def test_check_reliability_critical(self):
        """Critical: engine shortage + another reason."""
        cfg = ReliabilityConfig(min_available_engines=3, max_cpu_percent=50.0)
        monitor = ReliabilityMonitor(config=cfg)
        with patch.object(monitor.health_checker, "check_all", return_value={
            "status": "degraded",
            "checks": {
                "system_resources": {
                    "status": "healthy",
                    "cpu_percent": 90.0,
                    "memory_percent": 30.0,
                },
                "core_engines": {
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "unhealthy", "message": "down"},
                    "qizheng": {"status": "unhealthy", "message": "down"},
                },
            },
            "healthy_engines": 1,
            "total_engines": 3,
        }):
            with patch.object(monitor, "get_metrics_snapshot", return_value={
                "requests": {"total": 0, "errors": 0, "avg_latency_ms": 0.0}
            }):
                result = monitor.check_reliability()
                assert result["status"] == "critical"

    def test_check_reliability_metrics_snapshot_error(self):
        """When metrics snapshot fails, it should still return a result."""
        monitor = ReliabilityMonitor()
        with patch.object(monitor.health_checker, "check_all", return_value={
            "status": "healthy",
            "checks": {
                "system_resources": {
                    "status": "healthy",
                    "cpu_percent": 10.0,
                    "memory_percent": 30.0,
                },
                "core_engines": {
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "healthy"},
                    "qizheng": {"status": "healthy"},
                },
            },
            "healthy_engines": 3,
            "total_engines": 3,
        }):
            with patch.object(monitor, "get_metrics_snapshot", side_effect=RuntimeError("metrics error")):
                result = monitor.check_reliability()
                assert result["status"] == "healthy"

    # ── get_reliability_score ──────────────────────────────────

    def test_get_reliability_score_healthy(self):
        monitor = ReliabilityMonitor()
        with patch.object(monitor.health_checker, "get_health_score", return_value=100):
            with patch.object(monitor.health_checker, "check_system_resources", return_value={
                "cpu_percent": 10.0,
                "memory_percent": 30.0,
            }):
                with patch.object(monitor.health_checker, "check_core_engines", return_value={
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "healthy"},
                    "qizheng": {"status": "healthy"},
                }):
                    score = monitor.get_reliability_score()
                    assert score == 100

    def test_get_reliability_score_with_component_failures(self):
        monitor = ReliabilityMonitor()
        for _ in range(5):
            monitor.record_failure("comp")
        with patch.object(monitor.health_checker, "get_health_score", return_value=100):
            with patch.object(monitor.health_checker, "check_system_resources", return_value={
                "cpu_percent": 10.0,
                "memory_percent": 30.0,
            }):
                with patch.object(monitor.health_checker, "check_core_engines", return_value={
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "healthy"},
                    "qizheng": {"status": "healthy"},
                }):
                    score = monitor.get_reliability_score()
                    assert score == 90  # 100 - 5*2

    def test_get_reliability_score_engine_check_error(self):
        monitor = ReliabilityMonitor()
        with patch.object(monitor.health_checker, "get_health_score", return_value=100):
            with patch.object(monitor.health_checker, "check_system_resources", return_value={
                "cpu_percent": 10.0,
                "memory_percent": 30.0,
            }):
                with patch.object(monitor.health_checker, "check_core_engines", side_effect=RuntimeError("engine check failed")):
                    score = monitor.get_reliability_score()
                    assert 0 <= score <= 100

    def test_get_reliability_score_high_cpu(self):
        cfg = ReliabilityConfig(max_cpu_percent=50.0)
        monitor = ReliabilityMonitor(config=cfg)
        with patch.object(monitor.health_checker, "get_health_score", return_value=100):
            with patch.object(monitor.health_checker, "check_system_resources", return_value={
                "cpu_percent": 80.0,
                "memory_percent": 30.0,
            }):
                with patch.object(monitor.health_checker, "check_core_engines", return_value={
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "healthy"},
                    "qizheng": {"status": "healthy"},
                }):
                    score = monitor.get_reliability_score()
                    assert score < 100  # CPU penalty applied

    def test_get_reliability_score_high_memory(self):
        cfg = ReliabilityConfig(max_memory_percent=50.0)
        monitor = ReliabilityMonitor(config=cfg)
        with patch.object(monitor.health_checker, "get_health_score", return_value=100):
            with patch.object(monitor.health_checker, "check_system_resources", return_value={
                "cpu_percent": 10.0,
                "memory_percent": 80.0,
            }):
                with patch.object(monitor.health_checker, "check_core_engines", return_value={
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "healthy"},
                    "qizheng": {"status": "healthy"},
                }):
                    score = monitor.get_reliability_score()
                    assert score < 100  # Memory penalty applied

    def test_get_reliability_score_engine_shortage(self):
        cfg = ReliabilityConfig(min_available_engines=3)
        monitor = ReliabilityMonitor(config=cfg)
        with patch.object(monitor.health_checker, "get_health_score", return_value=100):
            with patch.object(monitor.health_checker, "check_system_resources", return_value={
                "cpu_percent": 10.0,
                "memory_percent": 30.0,
            }):
                with patch.object(monitor.health_checker, "check_core_engines", return_value={
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "unhealthy", "message": "down"},
                    "qizheng": {"status": "unhealthy", "message": "down"},
                }):
                    score = monitor.get_reliability_score()
                    assert score < 100  # Engine shortage penalty


# ============================================================================
# Helper functions
# ============================================================================

class TestTimeit:
    """Tests for timeit helper."""

    def test_timeit_returns_result_and_elapsed(self):
        result, elapsed = timeit(lambda: sum(range(100)))
        assert result == 4950
        assert elapsed >= 0.0

    def test_timeit_with_args(self):
        result, elapsed = timeit(lambda x, y: x + y, 10, 20)
        assert result == 30
        assert elapsed >= 0.0

    def test_timeit_with_kwargs(self):
        result, elapsed = timeit(lambda a=0, b=0: a + b, a=5, b=15)
        assert result == 20
        assert elapsed >= 0.0

    def test_timeit_exception_propagates(self):
        def fail():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            timeit(fail)


class TestRetry:
    """Tests for retry decorator."""

    def test_retry_success_first_attempt(self):
        @retry(max_retries=3, delay=0.01)
        def ok():
            return "success"

        assert ok() == "success"

    def test_retry_success_after_failures(self):
        call_count = [0]

        @retry(max_retries=3, delay=0.01)
        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("flaky")
            return "ok"

        assert flaky() == "ok"
        assert call_count[0] == 3

    def test_retry_exhausted(self):
        @retry(max_retries=2, delay=0.01)
        def always_fail():
            raise RuntimeError("always fail")

        with pytest.raises(RuntimeError, match="always fail"):
            always_fail()

    def test_retry_specific_exceptions(self):
        @retry(max_retries=2, delay=0.01, exceptions=(ValueError,))
        def raise_type_error():
            raise TypeError("not caught")

        with pytest.raises(TypeError, match="not caught"):
            raise_type_error()

    def test_retry_exponential_backoff(self):
        call_count = [0]

        @retry(max_retries=3, delay=0.01, exponential=True)
        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("flaky")
            return "ok"

        assert flaky() == "ok"
        assert call_count[0] == 3

    def test_retry_preserves_function_name(self):
        @retry(max_retries=1, delay=0.01)
        def my_func():
            return "ok"

        assert my_func.__name__ == "my_func"


class TestSafeCall:
    """Tests for safe_call helper."""

    def test_safe_call_success(self):
        result = safe_call(lambda: 42)
        assert result == 42

    def test_safe_call_with_args(self):
        result = safe_call(lambda x, y: x + y, 10, 20)
        assert result == 30

    def test_safe_call_exception_returns_fallback(self):
        result = safe_call(lambda: 1 / 0, fallback="fallback_value")
        assert result == "fallback_value"

    def test_safe_call_no_timeout(self):
        result = safe_call(lambda: "ok", timeout=0)
        assert result == "ok"

    def test_safe_call_negative_timeout(self):
        """Negative timeout should be treated as no timeout."""
        result = safe_call(lambda: "ok", timeout=-1)
        assert result == "ok"

    def test_safe_call_large_timeout_skips_signal(self):
        """timeout >= 300 should skip signal entirely."""
        result = safe_call(lambda: "ok", timeout=300)
        assert result == "ok"

    def test_safe_call_no_sigalrm(self):
        """When SIGALRM is not available (e.g. Windows), just call func."""
        mock_signal = MagicMock()
        # Remove SIGALRM attribute so hasattr returns False
        del mock_signal.SIGALRM

        with patch.dict("sys.modules", {"signal": mock_signal}):
            result = safe_call(lambda: "ok", timeout=5.0)
            assert result == "ok"

    def test_safe_call_with_exception_no_timeout(self):
        result = safe_call(lambda: 1 / 0, fallback=99, timeout=0)
        assert result == 99

    def test_safe_call_timeout_error(self):
        """Test timeout via signal patching."""
        def handler(signum, frame):
            raise TimeoutError("timed out")

        mock_signal = MagicMock()
        mock_signal.SIGALRM = 14
        mock_signal.ITIMER_REAL = 0
        mock_signal.signal.return_value = "old_handler"
        mock_signal.setitimer.side_effect = lambda *args: handler(None, None)

        with patch.dict("sys.modules", {"signal": mock_signal}):
            result = safe_call(lambda: 42, fallback="timeout_fallback", timeout=1.0)
            assert result == "timeout_fallback"

    def test_safe_call_exception_during_signal_setup(self):
        """Exception in signal-protected call should return fallback."""
        mock_signal = MagicMock()
        mock_signal.SIGALRM = 14
        mock_signal.ITIMER_REAL = 0
        mock_signal.signal.return_value = "old_handler"

        with patch.dict("sys.modules", {"signal": mock_signal}):
            result = safe_call(lambda: (_ for _ in ()).throw(ValueError("boom")), fallback=42, timeout=1.0)
            assert result == 42


# ============================================================================
# Integration / edge case tests
# ============================================================================

class TestIntegration:
    """Integration-style tests."""

    def test_full_circuit_breaker_lifecycle(self):
        """Test the full lifecycle: CLOSED → OPEN → HALF_OPEN → CLOSED."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.02, success_threshold=2)

        # Fail twice to OPEN
        for _ in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
            except RuntimeError:
                pass
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for recovery
        time.sleep(0.05)
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # Succeed twice to CLOSE
        cb.call(lambda: "ok1")
        cb.call(lambda: "ok2")
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_rate_limiter_pipeline(self):
        """Test RateLimiter with both algorithms."""
        rl_tb = RateLimiter("token_bucket", capacity=10, refill_rate_per_second=100.0)
        for _ in range(10):
            assert rl_tb.allow() is True
        assert rl_tb.allow() is False

        rl_sw = RateLimiter("sliding_window", limit=3, window_seconds=60.0)
        for _ in range(3):
            assert rl_sw.allow() is True
        assert rl_sw.allow() is False

    def test_monitor_with_custom_config_passed_to_check(self):
        """check_reliability accepts a config override."""
        default_cfg = ReliabilityConfig(max_cpu_percent=50.0)
        monitor = ReliabilityMonitor(config=default_cfg)

        override_cfg = ReliabilityConfig(max_cpu_percent=99.0)
        with patch.object(monitor.health_checker, "check_all", return_value={
            "status": "healthy",
            "checks": {
                "system_resources": {
                    "status": "healthy",
                    "cpu_percent": 80.0,
                    "memory_percent": 30.0,
                },
                "core_engines": {
                    "liunian_judgment": {"status": "healthy"},
                    "xuankong": {"status": "healthy"},
                    "qizheng": {"status": "healthy"},
                },
            },
            "healthy_engines": 3,
            "total_engines": 3,
        }):
            with patch.object(monitor, "get_metrics_snapshot", return_value={
                "requests": {"total": 0, "errors": 0, "avg_latency_ms": 0.0}
            }):
                # With override, CPU 80% < 99% → no CPU reason
                result = monitor.check_reliability(config=override_cfg)
                assert result["status"] == "healthy"

    def test_benchmark_with_func_exception(self):
        """Benchmark handles functions that throw exceptions gracefully."""
        pb = PerformanceBenchmark()
        stats = pb.benchmark_function(
            lambda: (_ for _ in ()).throw(RuntimeError("always")),
            iterations=10, warmup=2
        )
        assert stats["iterations"] == 10
        assert "avg_ms" in stats

    def test_self_test(self):
        """Test the _self_test function."""
        from tengod.reliability import _self_test

        results = _self_test()
        assert isinstance(results, dict)
        assert "token_bucket_initial" in results
        assert "health_score" in results
        assert "benchmark_stats" in results
        assert "monitor_status" in results
        assert "safe_call_exception" in results
        assert results["safe_call_exception"] == 42

    def test_self_test_retry_failure(self):
        """Test _self_test when retry function fails."""
        from tengod.reliability import _self_test

        # Patch retry to create a decorator that always fails
        with patch("tengod.reliability.retry") as mock_retry:
            def make_failing_decorator(**kwargs):
                def decorator(func):
                    def wrapper(*args, **kwargs):
                        raise RuntimeError("retry failed")
                    return wrapper
                return decorator
            mock_retry.side_effect = make_failing_decorator

            results = _self_test()
            assert isinstance(results, dict)
            assert "retry_result" in results
            assert "error" in results["retry_result"]