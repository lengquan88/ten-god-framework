"""
test_v28_observability.py — v2.8.0 新增功能测试
================================================
测试范围：
  - 配置管理 (config_manager)
  - 可观测性 (observability: 日志/健康检查/指标/追踪)
  - 统一配置 schema (config_schema)
  - 向后兼容性
"""

import pytest
import sys
import os
import json
import time
import logging
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Test 1: Config Manager
# ============================================================================

class TestConfigManager:
    """配置管理器测试"""

    def test_load_config_default(self):
        """测试默认配置加载"""
        from tengod.config_manager import load_config, get_config
        cfg = load_config()
        assert cfg is not None
        assert cfg.name == "tengod"
        assert cfg.server.host == "0.0.0.0"
        assert cfg.server.port == 8000

    def test_get_config_cached(self):
        """测试配置缓存"""
        from tengod.config_manager import get_config
        cfg1 = get_config()
        cfg2 = get_config()
        assert cfg1 is cfg2

    def test_get_config_dict(self):
        """测试配置字典"""
        from tengod.config_manager import get_config_dict
        d = get_config_dict()
        assert isinstance(d, dict)
        assert "name" in d
        assert "server" in d

    def test_get_server_config(self):
        """测试服务器配置"""
        from tengod.config_manager import get_server_config
        s = get_server_config()
        assert "host" in s
        assert "port" in s
        assert s["port"] == 8000

    def test_get_llm_config(self):
        """测试 LLM 配置（脱敏）"""
        from tengod.config_manager import get_llm_config
        llm = get_llm_config()
        assert "provider" in llm
        assert "model" in llm
        if llm.get("api_key"):
            assert "****" in llm["api_key"] or len(llm["api_key"]) < 8

    def test_reload_config(self):
        """测试配置重载"""
        from tengod.config_manager import reload_config, get_config
        cfg = reload_config()
        assert cfg is not None
        assert cfg.name == "tengod"

    def test_env_override(self, monkeypatch):
        """测试环境变量覆盖"""
        monkeypatch.setenv("TENGOD_NAME", "test_env_override")
        monkeypatch.setenv("TENGOD_PORT", "9999")

        from tengod.config_manager import load_config
        cfg = load_config()
        assert cfg.name == "test_env_override"
        assert cfg.server.port == 9999

        monkeypatch.delenv("TENGOD_NAME", raising=False)
        monkeypatch.delenv("TENGOD_PORT", raising=False)

    def test_generate_yaml(self):
        """测试生成示例 YAML"""
        from tengod.config_schema import generate_example_yaml
        yaml_str = generate_example_yaml()
        assert isinstance(yaml_str, str)
        assert "tengod" in yaml_str.lower() or "name" in yaml_str


# ============================================================================
# Test 2: Observability - Logging
# ============================================================================

class TestObservabilityLogging:
    """可观测性 - 日志测试"""

    def test_setup_logging_json(self):
        """测试 JSON 日志配置"""
        from tengod.observability import setup_logging, get_logger
        setup_logging(level="DEBUG", fmt="json")
        log = get_logger("test")
        log.info("test message")
        assert log.getEffectiveLevel() == logging.DEBUG

    def test_setup_logging_text(self):
        """测试文本日志配置"""
        from tengod.observability import setup_logging, get_logger
        setup_logging(level="WARNING", fmt="text")
        log = get_logger("test")
        assert log.getEffectiveLevel() == logging.WARNING

    def test_json_formatter_output(self):
        """测试 JSON 格式化输出"""
        from tengod.observability import JsonFormatter, set_request_id
        set_request_id("test123")
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=1,
            msg="hello world", args=(), exc_info=None
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "hello world"
        assert parsed["request_id"] == "test123"

    def test_request_id_generation(self):
        """测试请求ID生成"""
        from tengod.observability import generate_request_id, set_request_id, get_request_id
        rid = generate_request_id()
        assert len(rid) == 12
        set_request_id(rid)
        assert get_request_id() == rid


# ============================================================================
# Test 3: Observability - Health Check
# ============================================================================

class TestHealthCheck:
    """健康检查测试"""

    def test_register_and_run(self):
        """测试注册和运行健康检查"""
        from tengod.observability import HealthCheck, health_check_response
        hc = HealthCheck()
        hc.register("test_ok", lambda: {"status": "healthy", "detail": "all good"})
        hc.register("test_warn", lambda: {"status": "degraded", "detail": "slow"})

        result = hc.run_all()
        assert result["status"] == "degraded"
        assert "test_ok" in result["checks"]
        assert result["checks"]["test_ok"]["status"] == "healthy"
        assert result["checks"]["test_warn"]["status"] == "degraded"

    def test_register_unhealthy(self):
        """测试不健康检查"""
        from tengod.observability import HealthCheck
        hc = HealthCheck()
        hc.register("bad", lambda: {"status": "unhealthy", "detail": "down"})
        result = hc.run_all()
        assert result["status"] == "unhealthy"

    def test_register_exception(self):
        """测试检查异常处理"""
        from tengod.observability import HealthCheck
        hc = HealthCheck()

        def _fail():
            raise RuntimeError("connection refused")

        hc.register("failing", _fail)
        result = hc.run_all()
        assert result["status"] == "unhealthy"
        assert "connection refused" in result["checks"]["failing"]["detail"]

    def test_health_check_response(self):
        """测试健康检查响应格式"""
        from tengod.observability import health_check_response, get_health_checker
        get_health_checker().register("v28_test", lambda: {"status": "healthy", "detail": "OK"})
        resp = health_check_response()
        assert "status" in resp
        assert "timestamp" in resp
        assert "checks" in resp
        assert "active_requests" in resp
        assert "uptime_seconds" in resp


# ============================================================================
# Test 4: Observability - Metrics
# ============================================================================

class TestMetrics:
    """指标收集测试"""

    def test_counter(self):
        """测试计数器"""
        from tengod.observability import MetricsCollector
        mc = MetricsCollector()
        mc.counter_inc("test_requests")
        mc.counter_inc("test_requests")
        mc.counter_inc("test_requests", {"method": "GET"})

        metrics = mc.get_metrics()
        assert "test_requests" in metrics

    def test_histogram(self):
        """测试直方图"""
        from tengod.observability import MetricsCollector
        mc = MetricsCollector()
        for v in [10, 20, 30, 40, 50]:
            mc.histogram_observe("test_latency", v)

        metrics = mc.get_metrics()
        assert "test_latency_sum" in metrics
        assert "test_latency_count" in metrics
        assert "test_latency_avg" in metrics

    def test_gauge(self):
        """测试仪表"""
        from tengod.observability import MetricsCollector
        mc = MetricsCollector()
        mc.gauge_set("memory_usage", 512.5)
        metrics = mc.get_metrics()
        assert "memory_usage" in metrics
        assert "512.5" in metrics

    def test_prometheus_format(self):
        """测试 Prometheus 格式"""
        from tengod.observability import MetricsCollector
        mc = MetricsCollector()
        mc.counter_inc("sample_counter")
        output = mc.get_metrics()
        assert "# HELP" in output
        assert "# TYPE" in output
        assert "# EOF" in output


# ============================================================================
# Test 5: Request Tracker
# ============================================================================

class TestRequestTracker:
    """请求追踪测试"""

    def test_start_end_request(self):
        """测试请求追踪"""
        from tengod.observability import RequestTracker
        rt = RequestTracker()
        rt.start_request("req_001", "GET", "/api/test")
        active = rt.get_active_requests()
        assert len(active) == 1
        assert active[0]["method"] == "GET"

        rt.end_request("req_001", 200, 45.2)
        active = rt.get_active_requests()
        assert len(active) == 0

    def test_multiple_requests(self):
        """测试并发请求追踪"""
        from tengod.observability import RequestTracker
        rt = RequestTracker()
        rt.start_request("r1", "GET", "/a")
        rt.start_request("r2", "POST", "/b")
        rt.start_request("r3", "GET", "/c")
        active = rt.get_active_requests()
        assert len(active) == 3

        rt.end_request("r2", 201, 30.0)
        active = rt.get_active_requests()
        assert len(active) == 2


# ============================================================================
# Test 6: 向后兼容性
# ============================================================================

class TestV28Regression:
    """v2.8 向后兼容性测试"""

    def test_imports(self):
        """测试新模块导入"""
        from tengod.config_manager import load_config, get_config
        from tengod.observability import setup_logging, HealthCheck, MetricsCollector
        assert load_config is not None
        assert get_config is not None
        assert setup_logging is not None
        assert HealthCheck is not None
        assert MetricsCollector is not None

    def test_v27_imports_still_work(self):
        """测试 v2.7 模块仍可用"""
        from tengod.chart_visualizer import LiuyaoChartVisualizer
        from tengod.cache_manager import cached_engine
        assert LiuyaoChartVisualizer is not None
        assert cached_engine is not None

    def test_v26_imports_still_work(self):
        """测试 v2.6 模块仍可用"""
        from tengod.chart_visualizer import QimenChartVisualizer, FengshuiVisualizer
        assert QimenChartVisualizer is not None
        assert FengshuiVisualizer is not None

    def test_config_schema_imports(self):
        """测试配置 schema 导入"""
        from tengod.config_schema import (
            TengodConfig, ServerConfig, LLMConfig,
            validate_and_load, load_from_yaml, generate_example_yaml,
        )
        assert TengodConfig is not None
        assert ServerConfig is not None
        assert LLMConfig is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])