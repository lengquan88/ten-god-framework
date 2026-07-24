"""
Tests for tengod.metrics_collector — monitoring metrics collector.

Covers:
  - Data classes: RequestMetrics, BusinessMetrics, SystemMetrics
  - MetricsCollector: singleton, record_request, business recorders,
    system metrics, get_snapshot, to_prometheus
  - HealthChecker: check_all with mocked dependencies
  - Edge cases: empty state, negative values, no requests, singleton reset
"""

from __future__ import annotations

import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from tengod.metrics_collector import (
    BusinessMetrics,
    HealthChecker,
    MetricsCollector,
    RequestMetrics,
    SystemMetrics,
    metrics,
)


# ============================================================================
# Helpers
# ============================================================================

def _reset_singleton():
    """Reset the MetricsCollector singleton for isolated tests."""
    MetricsCollector._instance = None


# ============================================================================
# Data class tests
# ============================================================================

class TestRequestMetrics:
    """Tests for RequestMetrics dataclass."""

    def test_default_initialization(self):
        rm = RequestMetrics()
        assert rm.total_requests == 0
        assert rm.total_errors == 0
        assert rm.total_latency_ms == 0.0
        assert rm.status_counts == {}
        assert rm.endpoint_counts == {}

    def test_custom_initialization(self):
        rm = RequestMetrics(
            total_requests=10,
            total_errors=2,
            total_latency_ms=500.0,
            status_counts={200: 8, 500: 2},
            endpoint_counts={"/api/v1/bazi": 10},
        )
        assert rm.total_requests == 10
        assert rm.total_errors == 2
        assert rm.total_latency_ms == 500.0
        assert rm.status_counts == {200: 8, 500: 2}
        assert rm.endpoint_counts == {"/api/v1/bazi": 10}

    def test_status_counts_is_defaultdict(self):
        rm = RequestMetrics()
        # status_counts is a defaultdict(int) via field factory
        assert rm.status_counts[999] == 0
        assert isinstance(rm.status_counts, dict)

    def test_endpoint_counts_is_defaultdict(self):
        rm = RequestMetrics()
        assert rm.endpoint_counts["/nonexistent"] == 0

    def test_mutation(self):
        rm = RequestMetrics()
        rm.total_requests += 5
        rm.status_counts[200] += 3
        rm.endpoint_counts["/api/test"] += 1
        assert rm.total_requests == 5
        assert rm.status_counts[200] == 3
        assert rm.endpoint_counts["/api/test"] == 1


class TestBusinessMetrics:
    """Tests for BusinessMetrics dataclass."""

    def test_default_initialization(self):
        bm = BusinessMetrics()
        assert bm.bazi_calcs == 0
        assert bm.ziwei_calcs == 0
        assert bm.liuyao_calcs == 0
        assert bm.qimen_calcs == 0
        assert bm.name_analyses == 0
        assert bm.marriage_analyses == 0
        assert bm.ai_chats == 0
        assert bm.ai_reports == 0
        assert bm.knowledge_searches == 0

    def test_custom_values(self):
        bm = BusinessMetrics(
            bazi_calcs=5,
            ziwei_calcs=3,
            liuyao_calcs=2,
            qimen_calcs=1,
            name_analyses=4,
            marriage_analyses=6,
            ai_chats=10,
            ai_reports=7,
            knowledge_searches=8,
        )
        assert bm.bazi_calcs == 5
        assert bm.ziwei_calcs == 3
        assert bm.liuyao_calcs == 2
        assert bm.qimen_calcs == 1
        assert bm.name_analyses == 4
        assert bm.marriage_analyses == 6
        assert bm.ai_chats == 10
        assert bm.ai_reports == 7
        assert bm.knowledge_searches == 8


class TestSystemMetrics:
    """Tests for SystemMetrics dataclass."""

    def test_default_initialization(self):
        sm = SystemMetrics()
        assert sm.cpu_percent == 0.0
        assert sm.memory_percent == 0.0
        assert sm.memory_used_mb == 0.0
        assert sm.disk_percent == 0.0
        assert sm.uptime_seconds == 0.0

    def test_custom_values(self):
        sm = SystemMetrics(
            cpu_percent=45.5,
            memory_percent=60.0,
            memory_used_mb=8192.0,
            disk_percent=70.0,
            uptime_seconds=3600.0,
        )
        assert sm.cpu_percent == 45.5
        assert sm.memory_percent == 60.0
        assert sm.memory_used_mb == 8192.0
        assert sm.disk_percent == 70.0
        assert sm.uptime_seconds == 3600.0


# ============================================================================
# MetricsCollector tests
# ============================================================================

class TestMetricsCollectorSingleton:
    """Tests for MetricsCollector singleton pattern."""

    def setup_method(self):
        _reset_singleton()

    def teardown_method(self):
        _reset_singleton()

    def test_returns_same_instance(self):
        mc1 = MetricsCollector()
        mc2 = MetricsCollector()
        assert mc1 is mc2

    def test_initialized_flag_prevents_reinit(self):
        mc1 = MetricsCollector()
        original_start = mc1._start_time
        mc1._start_time = 999999.0  # tamper
        mc2 = MetricsCollector()
        assert mc2._start_time == 999999.0  # not re-initialized

    def test_has_lock_attribute(self):
        mc = MetricsCollector()
        assert hasattr(mc, "_lock_data")
        assert isinstance(mc._lock_data, type(threading.Lock()))


class TestMetricsCollectorRecordRequest:
    """Tests for record_request method."""

    def setup_method(self):
        _reset_singleton()

    def teardown_method(self):
        _reset_singleton()

    def test_record_single_request(self):
        mc = MetricsCollector()
        mc.record_request("/api/v1/bazi", 200, 15.5)

        snap = mc.get_snapshot()
        assert snap["requests"]["total"] == 1
        assert snap["requests"]["errors"] == 0
        assert snap["requests"]["avg_latency_ms"] == 15.5
        assert snap["requests"]["status_codes"] == {200: 1}
        assert snap["requests"]["top_endpoints"] == {"/api/v1/bazi": 1}

    def test_record_multiple_requests_same_endpoint(self):
        mc = MetricsCollector()
        for _ in range(5):
            mc.record_request("/api/v1/bazi", 200, 10.0)

        snap = mc.get_snapshot()
        assert snap["requests"]["total"] == 5
        assert snap["requests"]["status_codes"] == {200: 5}
        assert snap["requests"]["top_endpoints"] == {"/api/v1/bazi": 5}

    def test_record_error_request_status_400(self):
        mc = MetricsCollector()
        mc.record_request("/api/v1/bazi", 400, 20.0)

        snap = mc.get_snapshot()
        assert snap["requests"]["total"] == 1
        assert snap["requests"]["errors"] == 1

    def test_record_error_request_status_500(self):
        mc = MetricsCollector()
        mc.record_request("/api/v1/bazi", 500, 50.0)

        snap = mc.get_snapshot()
        assert snap["requests"]["total"] == 1
        assert snap["requests"]["errors"] == 1

    def test_status_399_not_error(self):
        mc = MetricsCollector()
        mc.record_request("/api/v1/bazi", 399, 5.0)

        snap = mc.get_snapshot()
        assert snap["requests"]["errors"] == 0

    def test_mixed_requests(self):
        mc = MetricsCollector()
        mc.record_request("/api/v1/bazi", 200, 10.0)
        mc.record_request("/api/v1/bazi", 200, 20.0)
        mc.record_request("/api/v1/ziwei", 500, 30.0)
        mc.record_request("/api/v1/ziwei", 404, 40.0)

        snap = mc.get_snapshot()
        assert snap["requests"]["total"] == 4
        assert snap["requests"]["errors"] == 2
        assert snap["requests"]["avg_latency_ms"] == 25.0
        assert snap["requests"]["status_codes"] == {200: 2, 500: 1, 404: 1}
        assert snap["requests"]["top_endpoints"] == {"/api/v1/bazi": 2, "/api/v1/ziwei": 2}

    def test_zero_latency(self):
        mc = MetricsCollector()
        mc.record_request("/api/v1/test", 200, 0.0)

        snap = mc.get_snapshot()
        assert snap["requests"]["avg_latency_ms"] == 0.0

    def test_large_latency_value(self):
        mc = MetricsCollector()
        mc.record_request("/api/v1/test", 200, 999999.0)

        snap = mc.get_snapshot()
        assert snap["requests"]["avg_latency_ms"] == 999999.0

    def test_top_endpoints_sorted_by_count(self):
        mc = MetricsCollector()
        for _ in range(20):
            mc.record_request("/api/v1/hot", 200, 1.0)
        for _ in range(5):
            mc.record_request("/api/v1/warm", 200, 1.0)
        for _ in range(2):
            mc.record_request("/api/v1/cold", 200, 1.0)

        snap = mc.get_snapshot()
        endpoints = list(snap["requests"]["top_endpoints"].keys())
        assert endpoints[0] == "/api/v1/hot"
        assert endpoints[1] == "/api/v1/warm"
        assert endpoints[2] == "/api/v1/cold"

    def test_top_endpoints_capped_at_10(self):
        mc = MetricsCollector()
        for i in range(15):
            for _ in range(i + 1):
                mc.record_request(f"/api/endpoint_{i}", 200, 1.0)

        snap = mc.get_snapshot()
        assert len(snap["requests"]["top_endpoints"]) == 10


class TestMetricsCollectorBusinessMethods:
    """Tests for all business metric recording methods."""

    def setup_method(self):
        _reset_singleton()

    def teardown_method(self):
        _reset_singleton()

    def test_record_bazi_calc(self):
        mc = MetricsCollector()
        mc.record_bazi_calc()
        mc.record_bazi_calc()
        snap = mc.get_snapshot()
        assert snap["business"]["bazi_calcs"] == 2

    def test_record_ziwei_calc(self):
        mc = MetricsCollector()
        mc.record_ziwei_calc()
        mc.record_ziwei_calc()
        mc.record_ziwei_calc()
        snap = mc.get_snapshot()
        assert snap["business"]["ziwei_calcs"] == 3

    def test_record_liuyao_calc(self):
        mc = MetricsCollector()
        mc.record_liuyao_calc()
        snap = mc.get_snapshot()
        assert snap["business"]["liuyao_calcs"] == 1

    def test_record_qimen_calc(self):
        mc = MetricsCollector()
        mc.record_qimen_calc()
        snap = mc.get_snapshot()
        assert snap["business"]["qimen_calcs"] == 1

    def test_record_name_analysis(self):
        mc = MetricsCollector()
        mc.record_name_analysis()
        mc.record_name_analysis()
        snap = mc.get_snapshot()
        assert snap["business"]["name_analyses"] == 2

    def test_record_marriage_analysis(self):
        mc = MetricsCollector()
        mc.record_marriage_analysis()
        snap = mc.get_snapshot()
        assert snap["business"]["marriage_analyses"] == 1

    def test_record_ai_chat(self):
        mc = MetricsCollector()
        for _ in range(10):
            mc.record_ai_chat()
        snap = mc.get_snapshot()
        assert snap["business"]["ai_chats"] == 10

    def test_record_ai_report(self):
        mc = MetricsCollector()
        mc.record_ai_report()
        mc.record_ai_report()
        mc.record_ai_report()
        snap = mc.get_snapshot()
        assert snap["business"]["ai_reports"] == 3

    def test_record_knowledge_search(self):
        mc = MetricsCollector()
        mc.record_knowledge_search()
        snap = mc.get_snapshot()
        assert snap["business"]["knowledge_searches"] == 1

    def test_all_business_methods_independent(self):
        mc = MetricsCollector()
        mc.record_bazi_calc()
        mc.record_ziwei_calc()
        mc.record_ai_chat()

        snap = mc.get_snapshot()
        assert snap["business"]["bazi_calcs"] == 1
        assert snap["business"]["ziwei_calcs"] == 1
        assert snap["business"]["ai_chats"] == 1
        assert snap["business"]["liuyao_calcs"] == 0
        assert snap["business"]["qimen_calcs"] == 0


class TestMetricsCollectorGetSnapshot:
    """Tests for get_snapshot method."""

    def setup_method(self):
        _reset_singleton()

    def teardown_method(self):
        _reset_singleton()

    def test_empty_snapshot(self):
        mc = MetricsCollector()
        with patch("psutil.cpu_percent", return_value=0.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=0.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=0.0)):
            snap = mc.get_snapshot()

        assert "timestamp" in snap
        assert "uptime_seconds" in snap
        assert snap["requests"]["total"] == 0
        assert snap["requests"]["errors"] == 0
        assert snap["requests"]["error_rate_percent"] == 0
        assert snap["requests"]["avg_latency_ms"] == 0
        assert snap["requests"]["status_codes"] == {}
        assert snap["requests"]["top_endpoints"] == {}
        assert snap["business"]["bazi_calcs"] == 0
        assert snap["system"]["cpu_percent"] == 0.0
        assert snap["system"]["memory_percent"] == 0.0

    def test_snapshot_structure_keys(self):
        mc = MetricsCollector()
        with patch("psutil.cpu_percent", return_value=0.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=0.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=0.0)):
            snap = mc.get_snapshot()

        assert set(snap.keys()) == {"timestamp", "uptime_seconds", "requests", "business", "system"}
        assert set(snap["requests"].keys()) == {
            "total", "errors", "error_rate_percent", "avg_latency_ms",
            "status_codes", "top_endpoints",
        }
        assert set(snap["business"].keys()) == {
            "bazi_calcs", "ziwei_calcs", "liuyao_calcs", "qimen_calcs",
            "name_analyses", "marriage_analyses", "ai_chats", "ai_reports",
            "knowledge_searches",
        }
        assert set(snap["system"].keys()) == {
            "cpu_percent", "memory_percent", "memory_used_mb", "disk_percent",
        }

    def test_error_rate_calculation(self):
        mc = MetricsCollector()
        mc.record_request("/api/test", 200, 10.0)
        mc.record_request("/api/test", 200, 10.0)
        mc.record_request("/api/test", 500, 10.0)

        with patch("psutil.cpu_percent", return_value=0.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=0.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=0.0)):
            snap = mc.get_snapshot()

        # 1 error out of 3 = ~33.33%
        assert snap["requests"]["error_rate_percent"] == pytest.approx(33.33, abs=0.01)

    def test_avg_latency_when_zero_requests(self):
        mc = MetricsCollector()
        with patch("psutil.cpu_percent", return_value=0.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=0.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=0.0)):
            snap = mc.get_snapshot()

        assert snap["requests"]["avg_latency_ms"] == 0


class TestMetricsCollectorSystemMetrics:
    """Tests for _collect_system_metrics."""

    def setup_method(self):
        _reset_singleton()

    def teardown_method(self):
        _reset_singleton()

    def test_collects_system_metrics_successfully(self):
        mc = MetricsCollector()

        mock_mem = MagicMock()
        mock_mem.percent = 45.2
        mock_mem.used = 8589934592  # 8 GB in bytes

        mock_disk = MagicMock()
        mock_disk.percent = 55.0

        with patch("psutil.cpu_percent", return_value=23.5), \
             patch("psutil.virtual_memory", return_value=mock_mem), \
             patch("psutil.disk_usage", return_value=mock_disk):
            mc._collect_system_metrics()

        assert mc._system_metrics.cpu_percent == 23.5
        assert mc._system_metrics.memory_percent == 45.2
        assert mc._system_metrics.memory_used_mb == pytest.approx(8192.0, abs=0.1)
        assert mc._system_metrics.disk_percent == 55.0
        assert mc._system_metrics.uptime_seconds >= 0

    def test_collect_system_metrics_handles_psutil_error(self):
        mc = MetricsCollector()

        with patch("psutil.cpu_percent", side_effect=OSError("psutil error")):
            # Should not raise
            mc._collect_system_metrics()

        # Values should remain at defaults after error
        assert mc._system_metrics.cpu_percent == 0.0

    def test_collect_system_metrics_partial_failure(self):
        mc = MetricsCollector()

        with patch("psutil.cpu_percent", return_value=50.0), \
             patch("psutil.virtual_memory", side_effect=Exception("boom")):
            mc._collect_system_metrics()

        # cpu_percent was set before the exception in virtual_memory
        assert mc._system_metrics.cpu_percent == 50.0
        # memory remained at default
        assert mc._system_metrics.memory_percent == 0.0


class TestMetricsCollectorToPrometheus:
    """Tests for to_prometheus method."""

    def setup_method(self):
        _reset_singleton()

    def teardown_method(self):
        _reset_singleton()

    def test_output_is_string(self):
        mc = MetricsCollector()
        with patch("psutil.cpu_percent", return_value=0.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=0.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=0.0)):
            output = mc.to_prometheus()

        assert isinstance(output, str)
        assert output.endswith("\n")

    def test_contains_help_and_type_lines(self):
        mc = MetricsCollector()
        with patch("psutil.cpu_percent", return_value=0.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=0.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=0.0)):
            output = mc.to_prometheus()

        assert "# HELP tengod_requests_total" in output
        assert "# TYPE tengod_requests_total counter" in output
        assert "# HELP tengod_cpu_percent" in output
        assert "# TYPE tengod_cpu_percent gauge" in output

    def test_counts_reflect_recorded_data(self):
        mc = MetricsCollector()
        mc.record_request("/api/test", 200, 10.0)
        mc.record_request("/api/test", 500, 20.0)
        mc.record_bazi_calc()
        mc.record_bazi_calc()

        with patch("psutil.cpu_percent", return_value=30.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0, used=8589934592)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)):
            output = mc.to_prometheus()

        assert "tengod_requests_total 2" in output
        assert "tengod_request_errors_total 1" in output
        assert "tengod_bazi_calcs_total 2" in output
        assert "tengod_cpu_percent 30.0" in output

    def test_contains_system_metrics(self):
        mc = MetricsCollector()
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=25.0, used=4194304000)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=60.0)):
            output = mc.to_prometheus()

        assert "tengod_cpu_percent 10.0" in output
        assert "tengod_memory_percent 25.0" in output
        assert "tengod_uptime_seconds" in output

    def test_empty_state_output(self):
        mc = MetricsCollector()
        with patch("psutil.cpu_percent", return_value=0.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=0.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=0.0)):
            output = mc.to_prometheus()

        assert "tengod_requests_total 0" in output
        assert "tengod_request_errors_total 0" in output
        assert "tengod_bazi_calcs_total 0" in output


# ============================================================================
# Edge case tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def setup_method(self):
        _reset_singleton()

    def teardown_method(self):
        _reset_singleton()

    def test_snapshot_with_no_requests_division_by_zero(self):
        """get_snapshot should handle zero requests without division error."""
        mc = MetricsCollector()
        with patch("psutil.cpu_percent", return_value=0.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=0.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=0.0)):
            snap = mc.get_snapshot()

        assert snap["requests"]["avg_latency_ms"] == 0
        assert snap["requests"]["error_rate_percent"] == 0

    def test_snapshot_with_no_errors_division_by_zero(self):
        mc = MetricsCollector()
        mc.record_request("/api/test", 200, 10.0)

        with patch("psutil.cpu_percent", return_value=0.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=0.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=0.0)):
            snap = mc.get_snapshot()

        assert snap["requests"]["error_rate_percent"] == 0.0

    def test_large_number_of_requests(self):
        mc = MetricsCollector()
        for i in range(10000):
            mc.record_request(f"/api/endpoint_{i % 100}", 200, 5.0)

        with patch("psutil.cpu_percent", return_value=0.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=0.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=0.0)):
            snap = mc.get_snapshot()

        assert snap["requests"]["total"] == 10000
        assert snap["requests"]["avg_latency_ms"] == 5.0

    def test_status_code_0(self):
        mc = MetricsCollector()
        mc.record_request("/api/test", 0, 10.0)
        snap = mc.get_snapshot()
        assert snap["requests"]["total"] == 1
        assert snap["requests"]["errors"] == 0  # 0 < 400

    def test_negative_status_code(self):
        mc = MetricsCollector()
        mc.record_request("/api/test", -1, 10.0)
        snap = mc.get_snapshot()
        assert snap["requests"]["total"] == 1
        # -1 < 400, so not counted as error
        assert snap["requests"]["errors"] == 0

    def test_very_large_status_code(self):
        mc = MetricsCollector()
        mc.record_request("/api/test", 9999, 10.0)
        snap = mc.get_snapshot()
        assert snap["requests"]["errors"] == 1

    def test_negative_latency(self):
        """Negative latency is unusual but should not crash."""
        mc = MetricsCollector()
        mc.record_request("/api/test", 200, -50.0)

        with patch("psutil.cpu_percent", return_value=0.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=0.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=0.0)):
            snap = mc.get_snapshot()

        assert snap["requests"]["avg_latency_ms"] == -50.0

    def test_empty_endpoint_string(self):
        mc = MetricsCollector()
        mc.record_request("", 200, 10.0)

        snap = mc.get_snapshot()
        assert snap["requests"]["top_endpoints"] == {"": 1}

    def test_special_characters_in_endpoint(self):
        mc = MetricsCollector()
        mc.record_request("/api/v1/测试?param=值&x=y", 200, 10.0)

        snap = mc.get_snapshot()
        assert snap["requests"]["top_endpoints"]["/api/v1/测试?param=值&x=y"] == 1

    def test_concurrent_recording(self):
        """Test that multiple threads can record metrics concurrently."""
        mc = MetricsCollector()

        def record_batch(n):
            for _ in range(n):
                mc.record_request("/api/test", 200, 5.0)
                mc.record_bazi_calc()

        threads = []
        for _ in range(5):
            t = threading.Thread(target=record_batch, args=(200,))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with patch("psutil.cpu_percent", return_value=0.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=0.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=0.0)):
            snap = mc.get_snapshot()

        assert snap["requests"]["total"] == 1000
        assert snap["business"]["bazi_calcs"] == 1000


# ============================================================================
# Global metrics instance tests
# ============================================================================

class TestGlobalMetricsInstance:
    """Tests for the global `metrics` singleton instance."""

    def setup_method(self):
        _reset_singleton()

    def teardown_method(self):
        _reset_singleton()

    def test_global_metrics_is_metrics_collector(self):
        from tengod.metrics_collector import metrics
        assert isinstance(metrics, MetricsCollector)

    def test_global_metrics_is_singleton(self):
        """After resetting the singleton, a new MetricsCollector() creates
        a fresh instance. The global ``metrics`` variable was bound at
        import time, so it still points to the original instance.  Both
        are valid MetricsCollector instances."""
        from tengod.metrics_collector import metrics
        mc = MetricsCollector()
        # Both are valid MetricsCollector instances
        assert isinstance(metrics, MetricsCollector)
        assert isinstance(mc, MetricsCollector)
        # After reset, the new mc is the current singleton
        mc2 = MetricsCollector()
        assert mc is mc2


# ============================================================================
# HealthChecker tests
# ============================================================================

class TestHealthChecker:
    """Tests for HealthChecker.check_all method."""

    def setup_method(self):
        _reset_singleton()

    def teardown_method(self):
        _reset_singleton()

    def test_check_all_structure(self):
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=30.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch("tengod.metrics_collector.HealthChecker.check_all", wraps=HealthChecker.check_all):

            # We need to mock the internal imports for DataStore, redis, VectorStore
            with patch.dict(sys.modules, {
                "tengod.data_store": MagicMock(),
                "tengod.vector_store": MagicMock(),
            }):
                import tengod.metrics_collector as mc_module
                # Mock DataStore
                mock_ds = MagicMock()
                mock_ds.stats.return_value = {"total": 100}
                sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)

                # Mock VectorStore
                mock_vs = MagicMock()
                mock_vs.info.return_value = {"total_nodes": 50}
                sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

                result = HealthChecker.check_all()

        assert "status" in result
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert "checks" in result
        assert "api" in result["checks"]
        assert "database" in result["checks"]
        assert "redis" in result["checks"]
        assert "vector_store" in result["checks"]
        assert "system" in result["checks"]

    def test_check_all_api_healthy(self):
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=30.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 0}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            result = HealthChecker.check_all()

        assert result["checks"]["api"]["status"] == "healthy"

    def test_check_all_database_unhealthy(self):
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=30.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)):
            # Simulate DataStore import failure
            with patch.dict(sys.modules, {
                "tengod.data_store": MagicMock(),
                "tengod.vector_store": MagicMock(),
            }):
                sys.modules["tengod.data_store"].DataStore = MagicMock(
                    side_effect=Exception("DB connection failed")
                )
                mock_vs = MagicMock()
                mock_vs.info.return_value = {"total_nodes": 0}
                sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

                result = HealthChecker.check_all()

        assert result["checks"]["database"]["status"] == "unhealthy"
        assert "DB connection failed" in result["checks"]["database"]["message"]

    def test_check_all_redis_skipped_when_not_configured(self):
        with patch.dict(os.environ, {"TENGOD_REDIS_URL": ""}, clear=True), \
             patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=30.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 0}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            result = HealthChecker.check_all()

        assert result["checks"]["redis"]["status"] == "skipped"

    def test_check_all_redis_healthy_when_configured(self):
        with patch.dict(os.environ, {"TENGOD_REDIS_URL": "redis://localhost:6379"}, clear=True), \
             patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=30.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
                 "redis": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 0}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            mock_redis = MagicMock()
            sys.modules["redis"].from_url = MagicMock(return_value=mock_redis)

            result = HealthChecker.check_all()

        assert result["checks"]["redis"]["status"] == "healthy"

    def test_check_all_redis_unhealthy_when_ping_fails(self):
        with patch.dict(os.environ, {"TENGOD_REDIS_URL": "redis://localhost:6379"}, clear=True), \
             patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=30.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
                 "redis": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 0}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            mock_redis = MagicMock()
            mock_redis.ping.side_effect = Exception("Connection refused")
            sys.modules["redis"].from_url = MagicMock(return_value=mock_redis)

            result = HealthChecker.check_all()

        assert result["checks"]["redis"]["status"] == "unhealthy"

    def test_check_all_vector_store_healthy(self):
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=30.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 100}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            result = HealthChecker.check_all()

        assert result["checks"]["vector_store"]["status"] == "healthy"
        assert "100 nodes" in result["checks"]["vector_store"]["message"]

    def test_check_all_vector_store_unhealthy(self):
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=30.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(
                side_effect=Exception("Vector store not available")
            )

            result = HealthChecker.check_all()

        assert result["checks"]["vector_store"]["status"] == "unhealthy"

    def test_check_all_overall_healthy(self):
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=30.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 0}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            result = HealthChecker.check_all()

        assert result["status"] == "healthy"

    def test_check_all_overall_degraded_when_any_unhealthy(self):
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=30.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
             }):
            sys.modules["tengod.data_store"].DataStore = MagicMock(
                side_effect=Exception("fail")
            )
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 0}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            result = HealthChecker.check_all()

        assert result["status"] == "degraded"

    def test_check_all_system_healthy(self):
        with patch("psutil.cpu_percent", return_value=50.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=50.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 0}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            result = HealthChecker.check_all()

        assert result["checks"]["system"]["status"] == "healthy"

    def test_check_all_system_warning_cpu_high(self):
        with patch("psutil.cpu_percent", return_value=95.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=50.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 0}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            result = HealthChecker.check_all()

        assert result["checks"]["system"]["status"] == "warning"

    def test_check_all_system_warning_memory_high(self):
        with patch("psutil.cpu_percent", return_value=50.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=95.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=50.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 0}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            result = HealthChecker.check_all()

        assert result["checks"]["system"]["status"] == "warning"

    def test_check_all_system_critical_disk_high(self):
        with patch("psutil.cpu_percent", return_value=50.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=95.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 0}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            result = HealthChecker.check_all()

        assert result["checks"]["system"]["status"] == "critical"

    def test_check_all_system_critical_takes_priority(self):
        """When both cpu > 90 and disk > 90, disk critical takes priority."""
        with patch("psutil.cpu_percent", return_value=95.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=95.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=95.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 0}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            result = HealthChecker.check_all()

        assert result["checks"]["system"]["status"] == "critical"

    def test_check_all_contains_system_values(self):
        with patch("psutil.cpu_percent", return_value=42.0), \
             patch("psutil.virtual_memory", return_value=MagicMock(percent=55.0, used=0)), \
             patch("psutil.disk_usage", return_value=MagicMock(percent=68.0)), \
             patch.dict(sys.modules, {
                 "tengod.data_store": MagicMock(),
                 "tengod.vector_store": MagicMock(),
             }):
            mock_ds = MagicMock()
            mock_ds.stats.return_value = {}
            sys.modules["tengod.data_store"].DataStore = MagicMock(return_value=mock_ds)
            mock_vs = MagicMock()
            mock_vs.info.return_value = {"total_nodes": 0}
            sys.modules["tengod.vector_store"].VectorStore = MagicMock(return_value=mock_vs)

            result = HealthChecker.check_all()

        assert result["checks"]["system"]["cpu_percent"] == 42.0
        assert result["checks"]["system"]["memory_percent"] == 55.0
        assert result["checks"]["system"]["disk_percent"] == 68.0


# ============================================================================
# __all__ exports test
# ============================================================================

def test_module_exports():
    """Verify the module exports the expected symbols."""
    from tengod import metrics_collector

    assert hasattr(metrics_collector, "MetricsCollector")
    assert hasattr(metrics_collector, "HealthChecker")
    assert hasattr(metrics_collector, "metrics")
    assert hasattr(metrics_collector, "RequestMetrics")
    assert hasattr(metrics_collector, "BusinessMetrics")
    assert hasattr(metrics_collector, "SystemMetrics")