"""
tests/test_phase29.py — Stage 29 (Performance & Reliability) 单元测试
"""

from __future__ import annotations

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


# ============================================================================
# TestRateLimiting —— 限流
# ============================================================================

class TestRateLimiting:
    def test_token_bucket_initial_state(self):
        tb = TokenBucket(capacity=10, refill_rate_per_second=1.0)
        assert tb.get_remaining() == 10

    def test_token_bucket_allows_requests(self):
        tb = TokenBucket(capacity=5, refill_rate_per_second=1.0)
        results = [tb.allow() for _ in range(5)]
        assert all(results)
        assert tb.get_remaining() == 0

    def test_token_bucket_blocks_when_empty(self):
        tb = TokenBucket(capacity=2, refill_rate_per_second=0.01)
        tb.allow()
        tb.allow()
        # 现在应为 0，接下来的请求会被拒绝（在不补充足够令牌的情况下）
        after_empty = tb.allow()
        assert after_empty is False

    def test_token_bucket_refills_over_time(self):
        tb = TokenBucket(capacity=5, refill_rate_per_second=10.0)
        # 先耗尽
        while tb.allow():
            pass
        assert tb.get_remaining() == 0
        time.sleep(0.3)
        remaining = tb.get_remaining()
        # 至少应有 2~3 个新令牌被补充
        assert remaining >= 2

    def test_sliding_window_basic(self):
        sw = SlidingWindow(limit=3, window_seconds=1.0)
        results = [sw.allow() for _ in range(3)]
        assert all(results)
        # 第 4 个请求应被拒绝
        assert sw.allow() is False
        assert sw.get_remaining() == 0

    def test_sliding_window_resets_after_window(self):
        sw = SlidingWindow(limit=2, window_seconds=0.2)
        assert sw.allow() is True
        assert sw.allow() is True
        assert sw.allow() is False
        time.sleep(0.3)
        # 窗口过去后应有可用
        assert sw.get_remaining() >= 1
        assert sw.allow() is True

    def test_get_remaining_returns_int(self):
        rl = RateLimiter("token_bucket", capacity=7, refill_rate_per_second=1.0)
        remaining = rl.get_remaining()
        assert isinstance(remaining, int)
        assert remaining == 7
        # 使用滑动窗口
        sw = RateLimiter("sliding_window", limit=5, window_seconds=1.0)
        assert isinstance(sw.get_remaining(), int)

    def test_high_frequency_blocking(self):
        rl = RateLimiter("sliding_window", limit=10, window_seconds=1.0)
        allowed = sum(1 for _ in range(100) if rl.allow())
        # 由于只允许 10 个，允许的请求不应超过太多（考虑精确窗口）
        assert allowed <= 15


# ============================================================================
# TestCircuitBreaker —— 熔断器
# ============================================================================

class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        assert cb.state == CircuitBreakerState.CLOSED

    def test_failures_trip_circuit(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=5.0)
        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail1")))
        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail2")))
        # 此时已超过阈值，下一次应直接被熔断
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: "never reached")
        assert cb.state == CircuitBreakerState.OPEN

    def test_success_resets_counter(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
        # 一个失败
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("x")))
        except Exception:
            pass
        # 一次成功应重置
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.failure_count == 0

    def test_open_blocks_calls(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except Exception:
            pass
        # OPEN 状态时应抛出
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: "nope")

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except Exception:
            pass
        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(0.15)
        # 访问 state 属性应触发 HALF_OPEN 转换
        # 在真正调用前先确认
        _ = cb.state
        # 调用成功
        result = cb.call(lambda: "hello")
        assert result == "hello"

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=2,
        )
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except Exception:
            pass
        time.sleep(0.15)
        cb.call(lambda: "ok1")
        cb.call(lambda: "ok2")
        assert cb.state == CircuitBreakerState.CLOSED

    def test_context_manager(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=1.0)
        with cb:
            x = 1 + 1
        assert x == 2
        assert cb.state == CircuitBreakerState.CLOSED

    def test_decorator(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=1.0)

        @cb
        def add(a, b):
            return a + b

        assert add(2, 3) == 5
        assert add(10, 20) == 30


# ============================================================================
# TestHealthChecker —— 健康检查
# ============================================================================

class TestHealthChecker:
    def test_check_all_returns_dict(self):
        hc = EnhancedHealthChecker()
        result = hc.check_all()
        assert isinstance(result, dict)
        assert "status" in result
        assert "timestamp" in result
        assert "checks" in result

    def test_check_all_valid_states(self):
        hc = EnhancedHealthChecker()
        result = hc.check_all()
        valid = {"healthy", "degraded", "critical"}
        assert result["status"] in valid

    def test_check_database(self):
        hc = EnhancedHealthChecker()
        db_check = hc.check_database()
        assert isinstance(db_check, dict)
        assert "status" in db_check

    def test_check_system_resources(self):
        hc = EnhancedHealthChecker()
        resources = hc.check_system_resources()
        assert isinstance(resources, dict)
        # 即便没有 psutil 也应有合理的结构
        assert "cpu_percent" in resources
        assert "memory_percent" in resources
        assert "disk_percent" in resources

    def test_health_score_range(self):
        hc = EnhancedHealthChecker()
        score = hc.get_health_score()
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_check_core_engines(self):
        hc = EnhancedHealthChecker()
        engines = hc.check_core_engines()
        assert isinstance(engines, dict)
        # 至少包含我们注册的引擎
        assert len(engines) >= 1
        for name, info in engines.items():
            assert isinstance(info, dict)
            assert "status" in info

    def test_enhanced_health_checker_import(self):
        # 验证类可被实例化
        assert EnhancedHealthChecker() is not None

    def test_check_cache(self):
        hc = EnhancedHealthChecker()
        cache_check = hc.check_cache()
        assert isinstance(cache_check, dict)
        assert "status" in cache_check


# ============================================================================
# TestPerformanceBenchmark —— 性能基准
# ============================================================================

class TestPerformanceBenchmark:
    def test_benchmark_basic(self):
        pb = PerformanceBenchmark()
        stats = pb.benchmark_function(lambda: sum(range(100)), iterations=10, warmup=2)
        assert isinstance(stats, dict)
        assert stats["iterations"] == 10

    def test_benchmark_returns_stats(self):
        pb = PerformanceBenchmark()
        stats = pb.benchmark_function(lambda: sum(range(50)), iterations=5, warmup=1)
        for key in ("avg_ms", "p50", "p95", "p99", "max_ms", "min_ms"):
            assert key in stats
            assert isinstance(stats[key], float)

    def test_timeit_returns_tuple(self):
        result, elapsed = timeit(lambda: sum(range(1000)))
        assert isinstance(elapsed, float)
        assert elapsed >= 0
        assert result == sum(range(1000))

    def test_benchmark_bazi_calc(self):
        pb = PerformanceBenchmark()
        stats = pb.benchmark_bazi_calc(iterations=5)
        # 即使计算失败也应有返回 dict
        assert isinstance(stats, dict)
        assert "avg_ms" in stats

    def test_p95_greater_than_p50(self):
        pb = PerformanceBenchmark()
        stats = pb.benchmark_function(
            lambda: time.sleep(0.001), iterations=20, warmup=2
        )
        # 统计意义上 p95 >= p50
        assert stats["p95"] >= stats["p50"] - 1e-6

    def test_report_returns_string(self):
        pb = PerformanceBenchmark()
        pb.benchmark_function(lambda: sum(range(10)), iterations=3, warmup=1)
        report = pb.report()
        assert isinstance(report, str)
        assert "Performance" in report or "Benchmark" in report


# ============================================================================
# TestReliabilityMonitor —— 综合监控
# ============================================================================

class TestReliabilityMonitor:
    def test_monitor_check_returns_status(self):
        monitor = ReliabilityMonitor()
        result = monitor.check_reliability()
        assert isinstance(result, dict)
        assert "status" in result

    def test_status_is_valid_string(self):
        monitor = ReliabilityMonitor()
        result = monitor.check_reliability()
        assert result["status"] in {"healthy", "degraded", "critical"}

    def test_reliability_score_range(self):
        monitor = ReliabilityMonitor()
        score = monitor.get_reliability_score()
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_record_failure_tracks_component(self):
        monitor = ReliabilityMonitor()
        for _ in range(5):
            monitor.record_failure("db")
        monitor.record_failure("cache")
        failures = monitor.get_component_failures()
        assert failures["db"] == 5
        assert failures["cache"] == 1

    def test_get_metrics_snapshot(self):
        monitor = ReliabilityMonitor()
        snap = monitor.get_metrics_snapshot()
        assert isinstance(snap, dict)
        # MetricsCollector 通常会返回 timestamp / requests / ... 等字段

    def test_retry_with_backoff(self):
        calls = {"n": 0}

        @retry(max_retries=3, delay=0.01)
        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("transient")
            return "success"

        assert flaky() == "success"
        assert calls["n"] == 3

    def test_safe_call_handles_exception(self):
        result = safe_call(lambda: 1 / 0, fallback="no-problem")
        assert result == "no-problem"

    def test_safe_call_with_timeout(self):
        result = safe_call(
            lambda: "fast value", fallback="fallback", timeout=1.0
        )
        # 简单调用在超时前返回
        assert result == "fast value"


# ============================================================================
# TestReliabilityConfig —— 配置
# ============================================================================

class TestReliabilityConfig:
    def test_default_config_sane(self):
        cfg = ReliabilityConfig()
        assert 0 <= cfg.max_error_rate <= 1
        assert cfg.max_avg_latency_ms > 0
        assert 0 < cfg.max_memory_percent <= 100
        assert 0 < cfg.max_cpu_percent <= 100
        assert cfg.min_available_engines >= 0

    def test_config_is_mutable(self):
        cfg = ReliabilityConfig()
        cfg.max_cpu_percent = 50
        cfg.min_available_engines = 1
        assert cfg.max_cpu_percent == 50
        assert cfg.min_available_engines == 1

    def test_config_applied_in_check_reliability(self):
        monitor = ReliabilityMonitor()
        # 高阈值：通常应健康
        healthy_cfg = ReliabilityConfig(
            max_error_rate=1.0,
            max_avg_latency_ms=10_000.0,
            max_memory_percent=100.0,
            max_cpu_percent=100.0,
            min_available_engines=0,
        )
        healthy_result = monitor.check_reliability(config=healthy_cfg)
        # 低阈值：通常应 degraded
        strict_cfg = ReliabilityConfig(
            max_error_rate=0.0,
            max_avg_latency_ms=0.001,
            max_memory_percent=0.01,
            max_cpu_percent=0.01,
            min_available_engines=99,
        )
        strict_result = monitor.check_reliability(config=strict_cfg)
        # 至少有一个结果是 degraded 或 critical（严格阈值）
        assert strict_result["status"] in {"degraded", "critical"}
