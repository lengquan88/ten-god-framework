#!/usr/bin/env python3
"""
test_monitoring.py — 可观测性测试 v2.17.0
==========================================
测试 MetricsCollector 的所有功能。

用法：
    pytest tests/test_monitoring.py -v
"""
import time

import pytest

from tengod.monitoring import (
    MetricsCollector,
    LatencyStats,
    global_metrics,
    get_metrics,
)


class TestLatencyStats:
    """延迟统计"""

    def test_empty(self):
        stats = LatencyStats()
        assert stats.count == 0
        assert stats.avg == 0.0

    def test_record(self):
        stats = LatencyStats()
        stats.record(0.1)
        stats.record(0.2)
        stats.record(0.3)
        assert stats.count == 3
        assert 0.19 < stats.avg < 0.21  # ~0.2

    def test_min_max(self):
        stats = LatencyStats()
        stats.record(0.1)
        stats.record(0.5)
        stats.record(0.3)
        assert stats.min == 0.1
        assert stats.max == 0.5

    def test_percentile(self):
        stats = LatencyStats()
        for i in range(100):
            stats.record(i * 0.01)  # 0.0, 0.01, ..., 0.99
        assert 0.48 < stats.percentile(50) < 0.52  # p50 ≈ 0.5
        assert 0.93 < stats.percentile(95) < 0.97  # p95 ≈ 0.95
        assert 0.97 < stats.percentile(99) < 1.0    # p99 ≈ 0.99

    def test_summary(self):
        stats = LatencyStats()
        stats.record(0.1)
        stats.record(0.2)
        s = stats.summary()
        assert s["count"] == 2
        assert "avg_ms" in s
        assert "p50_ms" in s
        assert "p95_ms" in s
        assert "p99_ms" in s


class TestMetricsCollector:
    """指标收集器"""

    @pytest.fixture
    def metrics(self):
        return MetricsCollector(name="test")

    def test_increment(self, metrics):
        metrics.increment("requests")
        metrics.increment("requests")
        assert metrics._counters["requests"] == 2

    def test_record_error(self, metrics):
        metrics.record_error("/api/test", "timeout")
        metrics.record_error("/api/test", "timeout")
        assert metrics._errors["/api/test:timeout"] == 2

    def test_record_latency(self, metrics):
        metrics.record_latency("test_op", 0.05)
        metrics.record_latency("test_op", 0.15)
        assert metrics._latencies["test_op"].count == 2

    def test_record_stage_latency(self, metrics):
        metrics.record_stage_latency("正官", 0.01)
        metrics.record_stage_latency("正官", 0.02)
        assert len(metrics._stage_latencies["正官"]) == 2

    def test_cache_stats(self, metrics):
        metrics.record_cache_hit()
        metrics.record_cache_hit()
        metrics.record_cache_miss()
        assert metrics._cache_hits == 2
        assert metrics._cache_misses == 1
        assert metrics.cache_hit_rate == pytest.approx(2 / 3, abs=0.01)

    def test_phi_entropy(self, metrics):
        metrics.set_phi_entropy(0.42)
        assert metrics._phi_entropy == 0.42
        assert len(metrics._phi_entropy_history) == 1

    def test_track_context_manager(self, metrics):
        with metrics.track("test_operation"):
            time.sleep(0.01)
        assert metrics._latencies["test_operation"].count == 1

    def test_uptime(self, metrics):
        assert metrics.uptime >= 0

    def test_summary(self, metrics):
        metrics.increment("requests")
        metrics.record_latency("test", 0.1)
        s = metrics.summary()
        assert s["name"] == "test"
        assert "uptime_s" in s
        assert "total_requests" in s
        assert s["total_requests"] == 1
        assert "test" in s["endpoints"]

    def test_prometheus_text(self, metrics):
        metrics.increment("requests")
        metrics.record_latency("test", 0.1)
        text = metrics.prometheus_text()
        assert "tengod_uptime_seconds" in text
        assert "tengod_requests_total" in text
        assert "tengod_errors_total" in text
        assert "tengod_cache_hit_rate" in text
        assert "tengod_phi_entropy" in text

    def test_global_metrics(self):
        assert global_metrics is not None
        assert get_metrics() is global_metrics

    def test_multiple_endpoints(self, metrics):
        metrics.record_latency("api_graph", 0.05)
        metrics.record_latency("api_bazi", 0.1)
        metrics.record_latency("api_graph", 0.15)
        assert len(metrics._latencies) == 2
        assert metrics._latencies["api_graph"].count == 2
        assert metrics._latencies["api_bazi"].count == 1

    def test_pipeline_tracking(self, metrics):
        """管道追踪场景"""
        for stage in ["正官", "元辰", "正财", "偏财", "食神"]:
            with metrics.track(stage):
                time.sleep(0.001)
                metrics.record_stage_latency(stage, 0.001)

        s = metrics.summary()
        assert len(s["endpoints"]) >= 5
        assert len(s["stages"]) >= 5