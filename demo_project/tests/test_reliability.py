#!/usr/bin/env python3
"""
reliability.py 测试套件
========================
覆盖: TokenBucket, SlidingWindow, RateLimiter, CircuitBreaker,
      EnhancedHealthChecker, PerformanceBenchmark, ReliabilityMonitor
      timeit, retry, safe_call
"""

import time

import pytest

from tengod.reliability import (
    TokenBucket,
    SlidingWindow,
    RateLimiter,
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerError,
    EnhancedHealthChecker,
    PerformanceBenchmark,
    ReliabilityConfig,
    ReliabilityMonitor,
    timeit,
    retry,
    safe_call,
)


# ═══════════════════════════════════════════════════════════
# TokenBucket 测试
# ═══════════════════════════════════════════════════════════

class TestTokenBucket:

    def test_initial_state(self):
        tb = TokenBucket(capacity=10, refill_rate_per_second=5.0)
        assert tb.capacity == 10
        assert tb.refill_rate_per_second == 5.0
        assert tb.get_remaining() == 10

    def test_allow_consumes_tokens(self):
        tb = TokenBucket(capacity=3, refill_rate_per_second=1.0)
        assert tb.allow() is True
        assert tb.get_remaining() == 2
        assert tb.allow() is True
        assert tb.get_remaining() == 1
        assert tb.allow() is True
        assert tb.get_remaining() == 0

    def test_denies_when_empty(self):
        tb = TokenBucket(capacity=2, refill_rate_per_second=0.1)
        assert tb.allow() is True
        assert tb.allow() is True
        assert tb.allow() is False
        assert tb.get_remaining() == 0

    def test_refills_over_time(self):
        tb = TokenBucket(capacity=10, refill_rate_per_second=100.0)
        for _ in range(10):
            tb.allow()
        assert tb.get_remaining() == 0
        time.sleep(0.02)
        assert tb.get_remaining() >= 1

    def test_custom_cost(self):
        tb = TokenBucket(capacity=10, refill_rate_per_second=1.0)
        assert tb.allow(cost=5) is True
        assert tb.get_remaining() == 5
        assert tb.allow(cost=6) is False

    def test_invalid_initialization(self):
        with pytest.raises(ValueError, match="capacity must be positive"):
            TokenBucket(capacity=0, refill_rate_per_second=1.0)
        with pytest.raises(ValueError, match="refill_rate_per_second must be positive"):
            TokenBucket(capacity=10, refill_rate_per_second=0)


# ═══════════════════════════════════════════════════════════
# SlidingWindow 测试
# ═══════════════════════════════════════════════════════════

class TestSlidingWindow:

    def test_initial_state(self):
        sw = SlidingWindow(limit=5, window_seconds=1.0)
        assert sw.limit == 5
        assert sw.window_seconds == 1.0

    def test_allow_within_limit(self):
        sw = SlidingWindow(limit=3, window_seconds=1.0)
        assert sw.allow() is True
        assert sw.allow() is True
        assert sw.allow() is True
        assert sw.get_remaining() == 0

    def test_denies_over_limit(self):
        sw = SlidingWindow(limit=2, window_seconds=1.0)
        assert sw.allow() is True
        assert sw.allow() is True
        assert sw.allow() is False

    def test_requests_expire_over_time(self):
        sw = SlidingWindow(limit=2, window_seconds=0.1)
        assert sw.allow() is True
        assert sw.allow() is True
        assert sw.allow() is False
        time.sleep(0.15)
        assert sw.allow() is True

    def test_get_remaining(self):
        sw = SlidingWindow(limit=5, window_seconds=1.0)
        assert sw.get_remaining() == 5
        sw.allow()
        assert sw.get_remaining() == 4
        sw.allow()
        assert sw.get_remaining() == 3

    def test_invalid_initialization(self):
        with pytest.raises(ValueError, match="limit must be positive"):
            SlidingWindow(limit=0, window_seconds=1.0)
        with pytest.raises(ValueError, match="window_seconds must be positive"):
            SlidingWindow(limit=5, window_seconds=0)


# ═══════════════════════════════════════════════════════════
# RateLimiter 测试
# ═══════════════════════════════════════════════════════════

class TestRateLimiter:

    def test_token_bucket_algorithm(self):
        rl = RateLimiter("token_bucket", capacity=5, refill_rate_per_second=10.0)
        assert rl.algorithm == "token_bucket"
        assert rl.get_remaining() == 5
        assert rl.allow() is True

    def test_sliding_window_algorithm(self):
        rl = RateLimiter("sliding_window", limit=5, window_seconds=1.0)
        assert rl.algorithm == "sliding_window"
        assert rl.get_remaining() == 5
        assert rl.allow() is True

    def test_unknown_algorithm(self):
        with pytest.raises(ValueError, match="Unknown algorithm"):
            RateLimiter("unknown", capacity=10)


# ═══════════════════════════════════════════════════════════
# CircuitBreaker 测试
# ═══════════════════════════════════════════════════════════

class TestCircuitBreaker:

    def test_initial_state(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_success_call(self):
        cb = CircuitBreaker(failure_threshold=3)
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_transitions_to_open_on_failures(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 2

    def test_open_state_blocks_calls(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1.0)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitBreakerState.OPEN
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: "should not execute")

    def test_fallback_on_open(self):
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=1.0,
            fallback=lambda: "fallback_value"
        )
        result1 = cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert result1 == "fallback_value"
        assert cb.state == CircuitBreakerState.OPEN
        result2 = cb.call(lambda: "should not execute")
        assert result2 == "fallback_value"

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(0.06)
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_resets_to_closed_on_success_in_half_open(self):
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0.05,
            success_threshold=2
        )
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        time.sleep(0.06)
        assert cb.state == CircuitBreakerState.HALF_OPEN
        cb.call(lambda: "success1")
        cb.call(lambda: "success2")
        assert cb.state == CircuitBreakerState.CLOSED

    def test_trip_and_reset(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.trip()
        assert cb.state == CircuitBreakerState.OPEN
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_context_manager_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        with cb:
            pass
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.success_count > 0

    def test_context_manager_failure(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(RuntimeError):
            with cb:
                raise RuntimeError("boom")
        assert cb.state == CircuitBreakerState.OPEN

    def test_decorator_usage(self):
        cb = CircuitBreaker(failure_threshold=3)

        @cb
        def flaky_fn(fail_count):
            if fail_count > 0:
                fail_count -= 1
                raise RuntimeError("fail")
            return "ok"

        counter = {"val": 2}

        def call_fn():
            return flaky_fn(counter["val"])

        with pytest.raises(RuntimeError):
            call_fn()
        counter["val"] -= 1
        with pytest.raises(RuntimeError):
            call_fn()
        counter["val"] -= 1
        result = call_fn()
        assert result == "ok"

    def test_invalid_initialization(self):
        with pytest.raises(ValueError, match="failure_threshold must be positive"):
            CircuitBreaker(failure_threshold=0)
        with pytest.raises(ValueError, match="recovery_timeout must be positive"):
            CircuitBreaker(recovery_timeout=0)
        with pytest.raises(ValueError, match="success_threshold must be positive"):
            CircuitBreaker(success_threshold=0)


# ═══════════════════════════════════════════════════════════
# EnhancedHealthChecker 测试
# ═══════════════════════════════════════════════════════════

class TestEnhancedHealthChecker:

    def test_check_all_returns_dict(self):
        hc = EnhancedHealthChecker()
        result = hc.check_all()
        assert isinstance(result, dict)
        assert "status" in result
        assert "timestamp" in result
        assert "checks" in result

    def test_health_score_is_integer(self):
        hc = EnhancedHealthChecker()
        score = hc.get_health_score()
        assert isinstance(score, int)
        assert 0 <= score <= 100


# ═══════════════════════════════════════════════════════════
# PerformanceBenchmark 测试
# ═══════════════════════════════════════════════════════════

class TestPerformanceBenchmark:

    def test_benchmark_function(self):
        pb = PerformanceBenchmark()
        stats = pb.benchmark_function(
            lambda: sum(range(100)),
            iterations=20,
            warmup=2
        )
        assert isinstance(stats, dict)
        assert "avg_ms" in stats
        assert "p50" in stats
        assert "p95" in stats
        assert "p99" in stats
        assert stats["iterations"] == 20

    def test_report_generation(self):
        pb = PerformanceBenchmark()
        pb.benchmark_function(lambda: sum(range(100)), iterations=10)
        report = pb.report()
        assert isinstance(report, str)
        assert "Performance Benchmark Report" in report


# ═══════════════════════════════════════════════════════════
# ReliabilityMonitor 测试
# ═══════════════════════════════════════════════════════════

class TestReliabilityMonitor:

    def test_initialization(self):
        config = ReliabilityConfig(max_error_rate=0.1)
        monitor = ReliabilityMonitor(config=config)
        assert monitor.config.max_error_rate == 0.1

    def test_record_failure(self):
        monitor = ReliabilityMonitor()
        monitor.record_failure("test_component")
        failures = monitor.get_component_failures()
        assert failures.get("test_component") == 1

    def test_check_reliability(self):
        monitor = ReliabilityMonitor()
        result = monitor.check_reliability()
        assert isinstance(result, dict)
        assert "status" in result
        assert "timestamp" in result

    def test_reliability_score(self):
        monitor = ReliabilityMonitor()
        score = monitor.get_reliability_score()
        assert isinstance(score, int)
        assert 0 <= score <= 100


# ═══════════════════════════════════════════════════════════
# Helper Functions 测试
# ═══════════════════════════════════════════════════════════

class TestHelperFunctions:

    def test_timeit(self):
        result, elapsed = timeit(lambda: sum(range(100)))
        assert result == 4950
        assert isinstance(elapsed, float)
        assert elapsed > 0

    def test_retry_success_on_third_attempt(self):
        counter = {"calls": 0}

        @retry(max_retries=3, delay=0.01)
        def flaky():
            counter["calls"] += 1
            if counter["calls"] < 3:
                raise RuntimeError("fail")
            return "success"

        result = flaky()
        assert result == "success"
        assert counter["calls"] == 3

    def test_retry_exponential_backoff(self):
        counter = {"calls": 0}

        @retry(max_retries=2, delay=0.01, exponential=True)
        def flaky():
            counter["calls"] += 1
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            flaky()
        assert counter["calls"] == 3

    def test_safe_call_success(self):
        result = safe_call(lambda: 42)
        assert result == 42

    def test_safe_call_fallback_on_exception(self):
        result = safe_call(lambda: 1 / 0, fallback="fallback")
        assert result == "fallback"

    def test_safe_call_timeout(self):
        def slow_fn():
            time.sleep(0.5)
            return "slow"
        result = safe_call(slow_fn, fallback="timeout", timeout=0.1)
        assert result == "timeout"
