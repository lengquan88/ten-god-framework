#!/usr/bin/env python3
"""
test_metrics.py — 统一日志与监控测试
======================================
测试 StructuredLogger、PrometheusMetrics、LogLevel 及模块级函数。

用法：
    pytest tests/test_metrics.py -v --tb=short
"""

import json
import threading
import time

import pytest

from tengod.metrics import (
    LogLevel,
    PrometheusMetrics,
    StructuredLogger,
    get_logger,
    get_metrics,
)


# ═══════════════════════════════════════════════════════════════════════════════
# LogLevel
# ═══════════════════════════════════════════════════════════════════════════════


class TestLogLevel:
    """LogLevel 枚举值测试"""

    def test_enum_values(self):
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"

    def test_enum_count(self):
        assert len(LogLevel) == 4

    def test_enum_comparison(self):
        assert LogLevel.DEBUG is LogLevel.DEBUG
        assert LogLevel.DEBUG is not LogLevel.INFO


# ═══════════════════════════════════════════════════════════════════════════════
# StructuredLogger
# ═══════════════════════════════════════════════════════════════════════════════


class TestStructuredLogger:
    """StructuredLogger 统一结构化日志测试"""

    # ── 初始化 ────────────────────────────────────────────────────────────────

    def test_init_default(self):
        logger = StructuredLogger()
        assert logger._name == "tengod"
        assert logger._min_level == LogLevel.INFO

    def test_init_custom_name(self):
        logger = StructuredLogger(name="myapp")
        assert logger._name == "myapp"

    def test_init_custom_min_level(self):
        logger = StructuredLogger(min_level=LogLevel.DEBUG)
        assert logger._min_level == LogLevel.DEBUG

    def test_init_both_custom(self):
        logger = StructuredLogger(name="custom", min_level=LogLevel.WARNING)
        assert logger._name == "custom"
        assert logger._min_level == LogLevel.WARNING

    # ── set_level ─────────────────────────────────────────────────────────────

    def test_set_level_debug(self):
        logger = StructuredLogger()
        logger.set_level("DEBUG")
        assert logger._min_level == LogLevel.DEBUG

    def test_set_level_warning(self):
        logger = StructuredLogger()
        logger.set_level("WARNING")
        assert logger._min_level == LogLevel.WARNING

    def test_set_level_error(self):
        logger = StructuredLogger()
        logger.set_level("ERROR")
        assert logger._min_level == LogLevel.ERROR

    def test_set_level_lowercase(self):
        logger = StructuredLogger()
        logger.set_level("debug")
        assert logger._min_level == LogLevel.DEBUG

    def test_set_level_invalid_defaults_to_info(self):
        logger = StructuredLogger(min_level=LogLevel.DEBUG)
        logger.set_level("INVALID")
        assert logger._min_level == LogLevel.INFO

    # ── 各级别日志输出 ────────────────────────────────────────────────────────

    def test_log_debug(self, capsys):
        logger = StructuredLogger(min_level=LogLevel.DEBUG)
        logger.debug("debug message")
        captured = capsys.readouterr()
        entry = json.loads(captured.err.strip())
        assert entry["level"] == "DEBUG"
        assert entry["message"] == "debug message"
        assert entry["logger"] == "tengod"

    def test_log_info(self, capsys):
        logger = StructuredLogger()
        logger.info("info message")
        captured = capsys.readouterr()
        entry = json.loads(captured.err.strip())
        assert entry["level"] == "INFO"
        assert entry["message"] == "info message"

    def test_log_warning(self, capsys):
        logger = StructuredLogger()
        logger.warning("warning message")
        captured = capsys.readouterr()
        entry = json.loads(captured.err.strip())
        assert entry["level"] == "WARNING"
        assert entry["message"] == "warning message"

    def test_log_error(self, capsys):
        logger = StructuredLogger()
        logger.error("error message")
        captured = capsys.readouterr()
        entry = json.loads(captured.err.strip())
        assert entry["level"] == "ERROR"
        assert entry["message"] == "error message"

    # ── 级别过滤 ──────────────────────────────────────────────────────────────

    def test_default_info_level_filters_debug(self, capsys):
        """默认 INFO 级别不输出 DEBUG"""
        logger = StructuredLogger()
        logger.debug("should not appear")
        logger.info("should appear")
        captured = capsys.readouterr()
        lines = captured.err.strip().split("\n")
        assert len(lines) == 1
        assert "should appear" in lines[0]

    def test_warning_level_filters_debug_and_info(self, capsys):
        """WARNING 级别只输出 WARNING 和 ERROR"""
        logger = StructuredLogger(min_level=LogLevel.WARNING)
        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        captured = capsys.readouterr()
        lines = captured.err.strip().split("\n")
        assert len(lines) == 2
        entries = [json.loads(line) for line in lines]
        levels = [e["level"] for e in entries]
        assert levels == ["WARNING", "ERROR"]

    def test_error_level_filters_all_but_error(self, capsys):
        """ERROR 级别只输出 ERROR"""
        logger = StructuredLogger(min_level=LogLevel.ERROR)
        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        captured = capsys.readouterr()
        lines = captured.err.strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["level"] == "ERROR"

    def test_debug_level_shows_all(self, capsys):
        """DEBUG 级别输出所有"""
        logger = StructuredLogger(min_level=LogLevel.DEBUG)
        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        captured = capsys.readouterr()
        lines = captured.err.strip().split("\n")
        assert len(lines) == 4
        entries = [json.loads(line) for line in lines]
        levels = [e["level"] for e in entries]
        assert levels == ["DEBUG", "INFO", "WARNING", "ERROR"]

    # ── JSON 格式 ─────────────────────────────────────────────────────────────

    def test_json_format_has_timestamp(self, capsys):
        logger = StructuredLogger()
        logger.info("test")
        captured = capsys.readouterr()
        entry = json.loads(captured.err.strip())
        assert "timestamp" in entry
        assert "T" in entry["timestamp"]  # ISO-like format

    def test_json_extra_kwargs(self, capsys):
        logger = StructuredLogger(min_level=LogLevel.DEBUG)
        logger.debug("test", user_id=42, action="login")
        captured = capsys.readouterr()
        entry = json.loads(captured.err.strip())
        assert entry["user_id"] == 42
        assert entry["action"] == "login"

    # ── counters ──────────────────────────────────────────────────────────────

    def test_counters_initial_empty(self):
        logger = StructuredLogger()
        assert logger.counters() == {}

    def test_counters_tracks_all_levels(self, capsys):
        logger = StructuredLogger(min_level=LogLevel.DEBUG)
        logger.debug("d")
        logger.info("i")
        logger.warning("w")
        logger.error("e")
        logger.error("e2")
        capsys.readouterr()  # consume output
        c = logger.counters()
        assert c["DEBUG"] == 1
        assert c["INFO"] == 1
        assert c["WARNING"] == 1
        assert c["ERROR"] == 2

    def test_counters_respects_filtering(self, capsys):
        """被过滤的日志不计入 counter"""
        logger = StructuredLogger(min_level=LogLevel.WARNING)
        logger.debug("d")
        logger.info("i")
        logger.warning("w")
        capsys.readouterr()
        c = logger.counters()
        assert "DEBUG" not in c
        assert "INFO" not in c
        assert c["WARNING"] == 1

    def test_counters_returns_copy(self):
        logger = StructuredLogger(min_level=LogLevel.DEBUG)
        logger.info("test")
        c = logger.counters()
        c["MODIFIED"] = 999
        assert "MODIFIED" not in logger.counters()

    # ── 线程安全 ──────────────────────────────────────────────────────────────

    def test_thread_safety(self):
        """并发写入不应崩溃或丢失计数"""
        logger = StructuredLogger(min_level=LogLevel.DEBUG)
        errors = []

        def log_many(num):
            try:
                for i in range(num):
                    logger.info(f"msg_{i}")
                    logger.debug(f"debug_{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(10):
            t = threading.Thread(target=log_many, args=(20,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        c = logger.counters()
        assert c["INFO"] == 200
        assert c["DEBUG"] == 200


# ═══════════════════════════════════════════════════════════════════════════════
# PrometheusMetrics
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrometheusMetrics:
    """PrometheusMetrics 指标暴露器测试"""

    # ── 初始化 ────────────────────────────────────────────────────────────────

    def test_init_default(self):
        pm = PrometheusMetrics()
        assert pm._name == "tengod"
        assert pm._start_time > 0

    def test_init_custom_name(self):
        pm = PrometheusMetrics(name="myapp")
        assert pm._name == "myapp"

    # ── counter_inc ───────────────────────────────────────────────────────────

    def test_counter_inc_basic(self):
        pm = PrometheusMetrics()
        pm.counter_inc("tengod_http_requests_total")
        assert pm._counters["tengod_http_requests_total"] == 1.0

    def test_counter_inc_multiple(self):
        pm = PrometheusMetrics()
        pm.counter_inc("tengod_http_requests_total", 3)
        pm.counter_inc("tengod_http_requests_total", 2)
        assert pm._counters["tengod_http_requests_total"] == 5.0

    def test_counter_inc_default_value(self):
        pm = PrometheusMetrics()
        pm.counter_inc("tengod_tasks_total")
        assert pm._counters["tengod_tasks_total"] == 1.0

    def test_counter_inc_with_labels(self):
        pm = PrometheusMetrics()
        pm.counter_inc("tengod_http_requests_total", labels={"method": "GET"})
        key = 'tengod_http_requests_total{method="GET"}'
        assert pm._counters[key] == 1.0

    def test_counter_inc_multi_labels(self):
        pm = PrometheusMetrics()
        pm.counter_inc(
            "tengod_http_requests_total",
            value=5,
            labels={"method": "POST", "status": "200"},
        )
        key = 'tengod_http_requests_total{method="POST",status="200"}'
        assert pm._counters[key] == 5.0

    # ── gauge_set ─────────────────────────────────────────────────────────────

    def test_gauge_set_basic(self):
        pm = PrometheusMetrics()
        pm.gauge_set("tengod_tasks_active", 42)
        assert pm._gauges["tengod_tasks_active"] == 42.0

    def test_gauge_set_overwrite(self):
        pm = PrometheusMetrics()
        pm.gauge_set("tengod_tasks_active", 10)
        pm.gauge_set("tengod_tasks_active", 20)
        assert pm._gauges["tengod_tasks_active"] == 20.0

    def test_gauge_set_with_labels(self):
        pm = PrometheusMetrics()
        pm.gauge_set("tengod_db_connections", 5, labels={"pool": "main"})
        key = 'tengod_db_connections{pool="main"}'
        assert pm._gauges[key] == 5.0

    # ── histogram_observe ─────────────────────────────────────────────────────

    def test_histogram_observe_single(self):
        pm = PrometheusMetrics()
        pm.histogram_observe("tengod_http_request_duration_seconds", 0.5)
        assert pm._histograms["tengod_http_request_duration_seconds"] == [0.5]

    def test_histogram_observe_multiple(self):
        pm = PrometheusMetrics()
        pm.histogram_observe("tengod_http_request_duration_seconds", 0.1)
        pm.histogram_observe("tengod_http_request_duration_seconds", 0.2)
        pm.histogram_observe("tengod_http_request_duration_seconds", 0.3)
        assert pm._histograms["tengod_http_request_duration_seconds"] == [0.1, 0.2, 0.3]

    def test_histogram_observe_with_labels(self):
        pm = PrometheusMetrics()
        pm.histogram_observe(
            "tengod_http_request_duration_seconds",
            0.15,
            labels={"method": "GET"},
        )
        key = 'tengod_http_request_duration_seconds{method="GET"}'
        assert pm._histograms[key] == [0.15]

    # ── _metric_key ───────────────────────────────────────────────────────────

    def test_metric_key_no_labels(self):
        pm = PrometheusMetrics()
        assert pm._metric_key("my_metric") == "my_metric"

    def test_metric_key_with_labels(self):
        pm = PrometheusMetrics()
        key = pm._metric_key("my_metric", {"code": "200", "method": "GET"})
        # labels sorted by key
        assert key == 'my_metric{code="200",method="GET"}'

    def test_metric_key_empty_labels(self):
        pm = PrometheusMetrics()
        key = pm._metric_key("my_metric", {})
        assert key == "my_metric"

    # ── _extract_help ─────────────────────────────────────────────────────────

    def test_extract_help_known_metric(self):
        pm = PrometheusMetrics()
        help_text, label_str = pm._extract_help("tengod_http_requests_total")
        assert help_text == "Total HTTP requests processed"
        assert label_str == ""

    def test_extract_help_known_metric_with_labels(self):
        pm = PrometheusMetrics()
        key = 'tengod_http_requests_total{method="GET"}'
        help_text, label_str = pm._extract_help(key)
        assert help_text == "Total HTTP requests processed"
        assert label_str == '{method="GET"}'

    def test_extract_help_unknown_metric(self):
        pm = PrometheusMetrics()
        help_text, label_str = pm._extract_help("custom_metric")
        assert help_text == "Metric custom_metric"
        assert label_str == ""

    def test_extract_help_unknown_metric_with_labels(self):
        pm = PrometheusMetrics()
        help_text, label_str = pm._extract_help('custom_metric{key="val"}')
        assert help_text == "Metric custom_metric"
        assert label_str == '{key="val"}'

    # ── generate_text ─────────────────────────────────────────────────────────

    def test_generate_text_empty(self):
        pm = PrometheusMetrics()
        text = pm.generate_text()
        # 即使为空，也应包含 uptime
        assert "tengod_uptime_seconds" in text
        assert "# HELP" in text
        assert "# TYPE" in text

    def test_generate_text_counter(self):
        pm = PrometheusMetrics()
        pm.counter_inc("tengod_http_requests_total", 10)
        text = pm.generate_text()
        assert "# HELP tengod_http_requests_total Total HTTP requests processed" in text
        assert "# TYPE tengod_http_requests_total counter" in text
        assert "tengod_http_requests_total 10" in text

    def test_generate_text_gauge(self):
        pm = PrometheusMetrics()
        pm.gauge_set("tengod_tasks_active", 7)
        text = pm.generate_text()
        assert "# HELP tengod_tasks_active Currently active tasks" in text
        assert "# TYPE tengod_tasks_active gauge" in text
        assert "tengod_tasks_active 7.000000" in text

    def test_generate_text_histogram(self):
        pm = PrometheusMetrics()
        pm.histogram_observe("tengod_http_request_duration_seconds", 0.1)
        pm.histogram_observe("tengod_http_request_duration_seconds", 0.3)
        text = pm.generate_text()
        assert "# HELP tengod_http_request_duration_seconds HTTP request duration in seconds" in text
        assert "# TYPE tengod_http_request_duration_seconds histogram" in text
        assert "tengod_http_request_duration_seconds_sum 0.400000" in text
        assert "tengod_http_request_duration_seconds_count 2" in text

    def test_generate_text_histogram_with_labels(self):
        pm = PrometheusMetrics()
        pm.histogram_observe(
            "tengod_http_request_duration_seconds",
            0.5,
            labels={"method": "GET"},
        )
        text = pm.generate_text()
        assert 'tengod_http_request_duration_seconds_sum{method="GET"} 0.500000' in text
        assert 'tengod_http_request_duration_seconds_count{method="GET"} 1' in text

    def test_generate_text_mixed_metrics(self):
        pm = PrometheusMetrics()
        pm.counter_inc("tengod_http_requests_total", 100)
        pm.gauge_set("tengod_tasks_active", 3)
        pm.histogram_observe("tengod_http_request_duration_seconds", 0.05)
        text = pm.generate_text()
        assert "tengod_http_requests_total 100" in text
        assert "tengod_tasks_active 3.000000" in text
        assert "tengod_http_request_duration_seconds_sum 0.050000" in text
        assert "tengod_uptime_seconds" in text

    def test_generate_text_uptime(self):
        pm = PrometheusMetrics()
        text = pm.generate_text()
        assert "# HELP tengod_uptime_seconds Service uptime in seconds" in text
        assert "# TYPE tengod_uptime_seconds gauge" in text
        assert "tengod_uptime_seconds " in text

    def test_generate_text_ends_with_newline(self):
        pm = PrometheusMetrics()
        text = pm.generate_text()
        assert text.endswith("\n")

    # ── get_stats ─────────────────────────────────────────────────────────────

    def test_get_stats_empty(self):
        pm = PrometheusMetrics()
        stats = pm.get_stats()
        assert "start_time" in stats
        assert "uptime_seconds" in stats
        assert stats["counters"] == {}
        assert stats["gauges"] == {}
        assert stats["histogram_counts"] == {}

    def test_get_stats_with_data(self):
        pm = PrometheusMetrics()
        pm.counter_inc("tengod_http_requests_total", 5)
        pm.gauge_set("tengod_tasks_active", 2)
        pm.histogram_observe("tengod_http_request_duration_seconds", 0.1)
        pm.histogram_observe("tengod_http_request_duration_seconds", 0.2)

        stats = pm.get_stats()
        assert stats["counters"]["tengod_http_requests_total"] == 5.0
        assert stats["gauges"]["tengod_tasks_active"] == 2.0
        assert (
            stats["histogram_counts"]["tengod_http_request_duration_seconds"] == 2
        )
        assert stats["uptime_seconds"] >= 0

    def test_get_stats_uptime_is_number(self):
        pm = PrometheusMetrics()
        stats = pm.get_stats()
        assert isinstance(stats["uptime_seconds"], (int, float))

    def test_get_stats_start_time_format(self):
        pm = PrometheusMetrics()
        stats = pm.get_stats()
        assert "T" in stats["start_time"]

    # ── 线程安全 ──────────────────────────────────────────────────────────────

    def test_thread_safety(self):
        """并发写入不应崩溃或丢失数据"""
        pm = PrometheusMetrics()
        errors = []

        def write_metrics(num):
            try:
                for i in range(num):
                    pm.counter_inc("tengod_http_requests_total")
                    pm.counter_inc("tengod_http_requests_total", labels={"method": "GET"})
                    pm.gauge_set("tengod_tasks_active", float(i % 10))
                    pm.histogram_observe("tengod_http_request_duration_seconds", 0.01 * i)
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(10):
            t = threading.Thread(target=write_metrics, args=(50,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        # total = 10 threads * 50 = 500
        assert pm._counters["tengod_http_requests_total"] == 500.0
        assert 'tengod_http_requests_total{method="GET"}' in pm._counters
        assert len(pm._histograms["tengod_http_request_duration_seconds"]) == 500


# ═══════════════════════════════════════════════════════════════════════════════
# 模块级全局函数
# ═══════════════════════════════════════════════════════════════════════════════


class TestGlobalInstances:
    """模块级 get_logger / get_metrics 全局实例测试"""

    def test_get_logger_returns_instance(self):
        logger = get_logger()
        assert isinstance(logger, StructuredLogger)

    def test_get_logger_returns_same_instance(self):
        a = get_logger()
        b = get_logger()
        assert a is b

    def test_get_logger_default_name(self):
        logger = get_logger()
        assert logger._name == "tengod"

    def test_get_metrics_returns_instance(self):
        pm = get_metrics()
        assert isinstance(pm, PrometheusMetrics)

    def test_get_metrics_returns_same_instance(self):
        a = get_metrics()
        b = get_metrics()
        assert a is b

    def test_get_metrics_default_name(self):
        pm = get_metrics()
        assert pm._name == "tengod"