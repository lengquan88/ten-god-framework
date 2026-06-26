"""
observability 模块测试 —— v2.8
================================
覆盖：请求追踪、结构化日志、健康检查、Prometheus 指标、请求追踪中间件
"""

import json
import logging
import os
import tempfile
import time
import uuid
from unittest.mock import patch

import pytest

from tengod.observability import (
    HealthCheck,
    JsonFormatter,
    MetricsCollector,
    RequestTracker,
    _metric_key,
    _parse_key,
    _request_id,
    _request_start,
    generate_request_id,
    get_health_checker,
    get_logger,
    get_metrics_collector,
    get_request_id,
    get_request_tracker,
    health_check_response,
    register_health_check,
    reset_startup_time,
    set_request_id,
    setup_logging,
)


# ══════════════════════════════════════════════════════════════════════════════
# 请求追踪
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateRequestId:
    def test_returns_12_char_hex_string(self):
        rid = generate_request_id()
        assert isinstance(rid, str)
        assert len(rid) == 12
        assert all(c in "0123456789abcdef" for c in rid)

    def test_returns_unique_ids(self):
        ids = {generate_request_id() for _ in range(100)}
        assert len(ids) == 100


class TestGetSetRequestId:
    def test_get_request_id_returns_empty_when_not_set(self):
        token = _request_id.set("")
        try:
            assert get_request_id() == ""
        finally:
            _request_id.reset(token)

    def test_set_and_get_roundtrip(self):
        token = _request_id.set("")
        try:
            set_request_id("test-id-123")
            assert get_request_id() == "test-id-123"
        finally:
            _request_id.reset(token)


# ══════════════════════════════════════════════════════════════════════════════
# JsonFormatter
# ══════════════════════════════════════════════════════════════════════════════

class TestJsonFormatter:
    def test_format_basic_log_record(self):
        token = _request_id.set("")
        try:
            fmt = JsonFormatter()
            record = logging.LogRecord(
                name="test_logger", level=logging.INFO,
                pathname="test.py", lineno=42, msg="hello world",
                args=(), exc_info=None,
            )
            result = fmt.format(record)
            data = json.loads(result)
            assert data["message"] == "hello world"
            assert data["level"] == "INFO"
            assert data["logger"] == "test_logger"
            assert data["module"] == "test"
        finally:
            _request_id.reset(token)

    def test_format_with_exception(self):
        token = _request_id.set("")
        try:
            fmt = JsonFormatter()
            try:
                raise ValueError("boom")
            except ValueError:
                record = logging.LogRecord(
                    name="test", level=logging.ERROR,
                    pathname="x.py", lineno=1, msg="error",
                    args=(), exc_info=logging.sys.exc_info(),
                )
            result = fmt.format(record)
            data = json.loads(result)
            assert "exception" in data
            assert "boom" in data["exception"]
        finally:
            _request_id.reset(token)

    def test_format_with_extra_fields(self):
        token = _request_id.set("")
        try:
            fmt = JsonFormatter()
            record = logging.LogRecord(
                name="test", level=logging.INFO,
                pathname="x.py", lineno=1, msg="with extra",
                args=(), exc_info=None,
            )
            record.extra_fields = {"user_id": 42, "action": "login"}
            result = fmt.format(record)
            data = json.loads(result)
            assert data["user_id"] == 42
            assert data["action"] == "login"
        finally:
            _request_id.reset(token)

    def test_format_output_is_valid_json(self):
        token = _request_id.set("")
        try:
            fmt = JsonFormatter()
            record = logging.LogRecord(
                name="t", level=logging.DEBUG,
                pathname="t.py", lineno=1, msg="json test",
                args=(), exc_info=None,
            )
            result = fmt.format(record)
            data = json.loads(result)
            assert isinstance(data, dict)
        finally:
            _request_id.reset(token)

    def test_format_includes_expected_fields(self):
        token = _request_id.set("")
        try:
            set_request_id("abc123")
            fmt = JsonFormatter()
            record = logging.LogRecord(
                name="my.logger", level=logging.WARNING,
                pathname="/path/to/module.py", lineno=99,
                msg="test message", args=(), exc_info=None,
            )
            result = fmt.format(record)
            data = json.loads(result)
            assert "timestamp" in data
            assert "level" in data
            assert "logger" in data
            assert "message" in data
            assert "module" in data
            assert "request_id" in data
            assert data["level"] == "WARNING"
            assert data["logger"] == "my.logger"
            assert data["message"] == "test message"
            assert data["module"] == "module"
            assert data["request_id"] == "abc123"
        finally:
            _request_id.reset(token)

    def test_format_no_exc_info(self):
        """Edge case: record with exc_info=(None, None, None)"""
        token = _request_id.set("")
        try:
            fmt = JsonFormatter()
            record = logging.LogRecord(
                name="t", level=logging.INFO,
                pathname="t.py", lineno=1, msg="no exc",
                args=(), exc_info=(None, None, None),
            )
            result = fmt.format(record)
            data = json.loads(result)
            assert "exception" not in data
        finally:
            _request_id.reset(token)

    def test_format_no_extra_fields(self):
        """Edge case: record without extra_fields attribute"""
        token = _request_id.set("")
        try:
            fmt = JsonFormatter()
            record = logging.LogRecord(
                name="t", level=logging.INFO,
                pathname="t.py", lineno=1, msg="no extra",
                args=(), exc_info=None,
            )
            result = fmt.format(record)
            data = json.loads(result)
            # Should not contain any extra fields beyond the standard ones
            for key in data:
                assert key in ("timestamp", "level", "logger", "message", "module", "request_id")
        finally:
            _request_id.reset(token)


# ══════════════════════════════════════════════════════════════════════════════
# setup_logging
# ══════════════════════════════════════════════════════════════════════════════

class TestSetupLogging:
    def test_setup_logging_json_format(self):
        setup_logging(level="DEBUG", fmt="json")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) >= 1
        assert isinstance(root.handlers[0].formatter, JsonFormatter)

    def test_setup_logging_text_format(self):
        setup_logging(level="WARNING", fmt="text")
        root = logging.getLogger()
        assert root.level == logging.WARNING
        assert len(root.handlers) >= 1
        assert isinstance(root.handlers[0].formatter, logging.Formatter)
        assert not isinstance(root.handlers[0].formatter, JsonFormatter)

    def test_setup_logging_with_log_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as f:
            tmp_path = f.name
        try:
            setup_logging(level="INFO", fmt="json", log_file=tmp_path)
            # 写一条日志
            logger = logging.getLogger("test_file")
            logger.info("file log test")
            # 清理 handler 以释放文件
            root = logging.getLogger()
            for h in root.handlers:
                h.close()
            root.handlers.clear()
            # 验证文件内容
            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "file log test" in content
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_setup_logging_clears_existing_handlers(self):
        root = logging.getLogger()
        # 先添加一个 handler
        root.addHandler(logging.StreamHandler())
        before = len(root.handlers)
        assert before >= 1
        setup_logging(level="INFO", fmt="json")
        # 默认只有 1 个 handler（无 log_file）
        assert len(root.handlers) == 1

    def test_setup_logging_invalid_level_defaults_to_info(self):
        setup_logging(level="INVALID_LEVEL", fmt="text")
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_setup_logging_suppresses_third_party_loggers(self):
        setup_logging(level="DEBUG", fmt="text")
        for lib in ["uvicorn", "httpx", "httpcore", "openai", "faiss"]:
            lg = logging.getLogger(lib)
            # 第三方库被设为 WARNING
            assert lg.level == logging.WARNING
            # 但不应传播到 root 导致 WARNING 以下被过滤
            # 只是让它们默认不输出 WARNING 以下


# ══════════════════════════════════════════════════════════════════════════════
# get_logger
# ══════════════════════════════════════════════════════════════════════════════

class TestGetLogger:
    def test_returns_logger(self):
        logger = get_logger("test_component")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_component"

    def test_same_name_returns_same_logger(self):
        a = get_logger("same")
        b = get_logger("same")
        assert a is b


# ══════════════════════════════════════════════════════════════════════════════
# HealthCheck
# ══════════════════════════════════════════════════════════════════════════════

class TestHealthCheck:
    def test_register_adds_check(self):
        hc = HealthCheck()
        hc.register("db", lambda: {"status": "healthy", "detail": "ok"})
        assert "db" in hc._checks

    def test_run_all_healthy(self):
        hc = HealthCheck()
        hc.register("db", lambda: {"status": "healthy", "detail": "connected"})
        hc.register("cache", lambda: {"status": "healthy", "detail": "hit"})
        result = hc.run_all()
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert "checks" in result
        assert result["checks"]["db"]["status"] == "healthy"
        assert result["checks"]["cache"]["status"] == "healthy"

    def test_run_all_degraded(self):
        hc = HealthCheck()
        hc.register("db", lambda: {"status": "healthy", "detail": "ok"})
        hc.register("api", lambda: {"status": "degraded", "detail": "slow"})
        result = hc.run_all()
        assert result["status"] == "degraded"

    def test_run_all_unhealthy(self):
        hc = HealthCheck()
        hc.register("db", lambda: {"status": "unhealthy", "detail": "down"})
        result = hc.run_all()
        assert result["status"] == "unhealthy"

    def test_run_all_mixed_healthy_degraded(self):
        hc = HealthCheck()
        hc.register("a", lambda: {"status": "healthy", "detail": "ok"})
        hc.register("b", lambda: {"status": "degraded", "detail": "slow"})
        result = hc.run_all()
        assert result["status"] == "degraded"

    def test_run_all_mixed_healthy_unhealthy(self):
        hc = HealthCheck()
        hc.register("a", lambda: {"status": "healthy", "detail": "ok"})
        hc.register("b", lambda: {"status": "unhealthy", "detail": "down"})
        result = hc.run_all()
        assert result["status"] == "unhealthy"

    def test_run_all_mixed_degraded_unhealthy(self):
        hc = HealthCheck()
        hc.register("a", lambda: {"status": "degraded", "detail": "slow"})
        hc.register("b", lambda: {"status": "unhealthy", "detail": "down"})
        result = hc.run_all()
        assert result["status"] == "unhealthy"

    def test_run_all_check_raises_exception(self):
        hc = HealthCheck()
        hc.register("ok", lambda: {"status": "healthy", "detail": "ok"})
        hc.register("bad", lambda: (_ for _ in ()).throw(RuntimeError("crash")))
        result = hc.run_all()
        assert result["status"] == "unhealthy"
        assert result["checks"]["bad"]["status"] == "unhealthy"
        assert "crash" in result["checks"]["bad"]["detail"]

    def test_run_all_empty_checks(self):
        hc = HealthCheck()
        result = hc.run_all()
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert result["checks"] == {}

    def test_run_all_returns_timestamp_and_checks(self):
        hc = HealthCheck()
        hc.register("x", lambda: {"status": "healthy"})
        result = hc.run_all()
        assert "timestamp" in result
        assert "checks" in result
        assert isinstance(result["checks"], dict)

    def test_run_all_check_no_status(self):
        """Edge case: check returns dict without 'status' key"""
        hc = HealthCheck()
        hc.register("unknown", lambda: {"detail": "no status"})
        result = hc.run_all()
        assert result["status"] == "healthy"  # unknown status does not affect overall
        assert result["checks"]["unknown"] == {"detail": "no status"}


class TestGetHealthChecker:
    def test_returns_singleton(self):
        a = get_health_checker()
        b = get_health_checker()
        assert a is b
        assert isinstance(a, HealthCheck)


class TestRegisterHealthCheck:
    def test_registers_on_global_singleton(self):
        checker = get_health_checker()
        register_health_check("test_check", lambda: {"status": "healthy"})
        assert "test_check" in checker._checks


# ══════════════════════════════════════════════════════════════════════════════
# MetricsCollector
# ══════════════════════════════════════════════════════════════════════════════

class TestMetricsCollector:
    def test_counter_inc(self):
        mc = MetricsCollector()
        mc.counter_inc("test_total")
        assert mc._counters["test_total"] == 1

    def test_counter_inc_with_labels(self):
        mc = MetricsCollector()
        mc.counter_inc("test_total", {"method": "GET"})
        key = _metric_key("test_total", {"method": "GET"})
        assert mc._counters[key] == 1

    def test_counter_inc_multiple_times(self):
        mc = MetricsCollector()
        for _ in range(5):
            mc.counter_inc("count")
        assert mc._counters["count"] == 5

    def test_histogram_observe(self):
        mc = MetricsCollector()
        mc.histogram_observe("latency", 10.5)
        mc.histogram_observe("latency", 20.0)
        assert mc._histograms["latency"] == [10.5, 20.0]

    def test_histogram_observe_truncates_to_1000(self):
        mc = MetricsCollector()
        for i in range(1500):
            mc.histogram_observe("large", float(i))
        assert len(mc._histograms["large"]) == 1000
        # 后 1000 个：索引 500-1499
        assert mc._histograms["large"][0] == 500.0
        assert mc._histograms["large"][-1] == 1499.0

    def test_histogram_observe_empty(self):
        """Edge case: histogram with no values"""
        mc = MetricsCollector()
        # 记录后立即检查 get_metrics 不会包含空 histogram
        output = mc.get_metrics()
        assert "latency" not in output

    def test_gauge_set(self):
        mc = MetricsCollector()
        mc.gauge_set("temperature", 36.5)
        assert mc._gauges["temperature"] == 36.5

    def test_gauge_set_overwrites_previous(self):
        mc = MetricsCollector()
        mc.gauge_set("temperature", 36.5)
        mc.gauge_set("temperature", 37.0)
        assert mc._gauges["temperature"] == 37.0

    def test_get_metrics_returns_prometheus_format(self):
        mc = MetricsCollector()
        mc.counter_inc("requests_total")
        output = mc.get_metrics()
        assert "# HELP requests_total" in output
        assert "# TYPE requests_total counter" in output
        assert "requests_total" in output

    def test_get_metrics_includes_help_type_metric_lines(self):
        mc = MetricsCollector()
        mc.counter_inc("my_counter")
        mc.gauge_set("my_gauge", 42.0)
        mc.histogram_observe("my_histogram", 1.0)
        output = mc.get_metrics()
        assert "# HELP my_counter" in output
        assert "# TYPE my_counter counter" in output
        assert "# HELP my_gauge" in output
        assert "# TYPE my_gauge gauge" in output
        assert "# HELP my_histogram" in output
        assert "# TYPE my_histogram histogram" in output

    def test_get_metrics_with_empty_metrics(self):
        mc = MetricsCollector()
        output = mc.get_metrics()
        # 只有 EOF 行
        assert "# EOF" in output

    def test_get_metrics_eof_line(self):
        mc = MetricsCollector()
        mc.counter_inc("x")
        output = mc.get_metrics()
        assert "# EOF" in output

    def test_get_metrics_histogram_with_values(self):
        mc = MetricsCollector()
        mc.histogram_observe("latency", 10.0)
        mc.histogram_observe("latency", 20.0)
        output = mc.get_metrics()
        assert "latency_sum" in output
        assert "latency_count" in output
        assert "latency_avg" in output

    def test_metric_key_without_labels(self):
        result = _metric_key("test", None)
        assert result == "test"

    def test_metric_key_with_labels(self):
        result = _metric_key("test", {"a": "1", "b": "2"})
        assert result == 'test:a="1";b="2"'

    def test_metric_key_with_empty_labels(self):
        result = _metric_key("test", {})
        assert result == "test"

    def test_parse_key_without_labels(self):
        name, label_str = _parse_key("simple")
        assert name == "simple"
        assert label_str == ""

    def test_parse_key_with_labels(self):
        name, label_str = _parse_key('test:a="1";b="2"')
        assert name == "test"
        assert label_str == 'a="1",b="2"'

    def test_parse_key_no_colon(self):
        name, label_str = _parse_key("plain")
        assert name == "plain"
        assert label_str == ""


class TestGetMetricsCollector:
    def test_returns_singleton(self):
        a = get_metrics_collector()
        b = get_metrics_collector()
        assert a is b
        assert isinstance(a, MetricsCollector)


# ══════════════════════════════════════════════════════════════════════════════
# RequestTracker
# ══════════════════════════════════════════════════════════════════════════════

class TestRequestTracker:
    def test_start_request_adds_to_active(self):
        rt = RequestTracker()
        rt.start_request("rid-1", "GET", "/api/test")
        active = rt.get_active_requests()
        assert len(active) == 1
        assert active[0]["request_id"] == "rid-1"
        assert active[0]["method"] == "GET"
        assert active[0]["path"] == "/api/test"
        assert active[0]["status"] == "processing"

    def test_start_request_increments_http_requests_total(self):
        mc = MetricsCollector()
        rt = RequestTracker()
        # 使用独立的 MetricsCollector，通过 monkey-patching
        import tengod.observability as obs
        orig_metrics = obs._metrics
        obs._metrics = mc
        try:
            rt.start_request("rid", "POST", "/api")
            key = _metric_key("http_requests_total", {"method": "POST", "path": "/api"})
            assert mc._counters[key] == 1
        finally:
            obs._metrics = orig_metrics

    def test_end_request_removes_from_active(self):
        rt = RequestTracker()
        rt.start_request("rid", "GET", "/")
        rt.end_request("rid", 200, 15.5)
        active = rt.get_active_requests()
        assert len(active) == 0

    def test_end_request_records_histogram_and_counter(self):
        mc = MetricsCollector()
        import tengod.observability as obs
        orig_metrics = obs._metrics
        obs._metrics = mc
        rt = RequestTracker()
        try:
            rt.start_request("rid", "GET", "/")
            rt.end_request("rid", 200, 15.5)
            assert "http_request_duration_ms" in mc._histograms
            assert mc._histograms["http_request_duration_ms"] == [15.5]
            key = _metric_key("http_responses_total", {"status": "200"})
            assert mc._counters[key] == 1
        finally:
            obs._metrics = orig_metrics

    def test_get_active_requests_returns_elapsed_ms(self):
        rt = RequestTracker()
        rt.start_request("rid", "GET", "/")
        # 略微等待以产生可测量的 elapsed
        time.sleep(0.01)
        active = rt.get_active_requests()
        assert len(active) == 1
        assert "elapsed_ms" in active[0]
        assert active[0]["elapsed_ms"] > 0

    def test_get_active_requests_empty(self):
        rt = RequestTracker()
        active = rt.get_active_requests()
        assert active == []

    def test_multiple_concurrent_requests(self):
        rt = RequestTracker()
        rt.start_request("r1", "GET", "/a")
        rt.start_request("r2", "POST", "/b")
        rt.start_request("r3", "PUT", "/c")
        active = rt.get_active_requests()
        assert len(active) == 3
        ids = {r["request_id"] for r in active}
        assert ids == {"r1", "r2", "r3"}


class TestGetRequestTracker:
    def test_returns_singleton(self):
        a = get_request_tracker()
        b = get_request_tracker()
        assert a is b
        assert isinstance(a, RequestTracker)


# ══════════════════════════════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════════════════════════════

class TestHealthCheckResponse:
    def test_returns_expected_structure(self):
        result = health_check_response()
        assert "status" in result
        assert "timestamp" in result
        assert "checks" in result
        assert "active_requests" in result
        assert "uptime_seconds" in result
        assert isinstance(result["active_requests"], list)
        assert isinstance(result["uptime_seconds"], float)

    def test_uptime_is_positive(self):
        result = health_check_response()
        assert result["uptime_seconds"] >= 0


class TestResetStartupTime:
    def test_changes_uptime(self):
        # 先获取当前 uptime
        r1 = health_check_response()
        time.sleep(0.02)
        reset_startup_time()
        r2 = health_check_response()
        # 重置后 uptime 应该比之前小
        assert r2["uptime_seconds"] < r1["uptime_seconds"]