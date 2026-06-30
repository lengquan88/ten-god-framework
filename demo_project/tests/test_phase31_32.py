"""
test_phase31_32.py — Phase 2 企业级基础设施测试 v2.31.0 → v2.32.0
=====================================================================
测试覆盖：
  - enterprise_config.py: 配置加载、优先级链、热重载、Pydantic v2验证、审计
  - error_handler.py: 分级错误、九宫格分类、自动回退、熔断器
  - cognitive_metrics.py: TBCE漂移监控、门禁通过率、推测解码统计
  - tracing.py: 全链路追踪、跨度管理、自修正审计日志
"""

import pytest
import os
import time
import math
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tengod.enterprise_config import (
    EnterpriseConfigManager,
    EnterpriseConfig,
    ConfigPriority,
    ConfigSource,
    ConfigChangeRecord,
    TwelveGodsGateConfig,
    TBCEConfig,
    SevenTheoriesConfig,
    SelfCorrectionConfig,
    ImagingConfig,
    CognitiveConfig,
    get_enterprise_config,
    reset_enterprise_config,
)
from tengod.error_handler import (
    ErrorLevel,
    NinePalaceErrorCategory,
    FallbackStrategy,
    ErrorRecord,
    ErrorHandler,
    get_error_handler,
    reset_error_handler,
)
from tengod.cognitive_metrics import (
    TBCEDriftRecord,
    GatePassRecord,
    CognitiveSnapshot,
    CognitiveMetricsCollector,
    get_cognitive_metrics,
    reset_cognitive_metrics,
)
from tengod.tracing import (
    SpanKind,
    SpanStatus,
    TraceSpan,
    Trace,
    CorrectionAuditEntry,
    TraceManager,
    get_trace_manager,
    reset_trace_manager,
)


# ============================================================================
# 测试夹具
# ============================================================================

@pytest.fixture(autouse=True)
def reset_all():
    """每个测试前重置所有单例"""
    reset_enterprise_config()
    reset_error_handler()
    reset_cognitive_metrics()
    reset_trace_manager()
    yield
    reset_enterprise_config()
    reset_error_handler()
    reset_cognitive_metrics()
    reset_trace_manager()


# ============================================================================
# 一、enterprise_config.py 测试
# ============================================================================

class TestConfigPriority:
    """配置优先级测试"""

    def test_priority_ordering(self):
        """验证优先级顺序：DEFAULT < YAML < ENV < RUNTIME"""
        assert ConfigPriority.DEFAULT.value < ConfigPriority.YAML_FILE.value
        assert ConfigPriority.YAML_FILE.value < ConfigPriority.ENV_VARIABLE.value
        assert ConfigPriority.ENV_VARIABLE.value < ConfigPriority.RUNTIME.value

    def test_source_enum(self):
        """验证配置来源枚举"""
        assert ConfigSource.DEFAULT.value == "default"
        assert ConfigSource.YAML.value == "yaml"
        assert ConfigSource.ENV.value == "env"
        assert ConfigSource.RUNTIME.value == "runtime"


class TestEnterpriseConfigDefaults:
    """企业级配置默认值测试"""

    def test_load_defaults(self):
        """测试加载默认配置"""
        mgr = EnterpriseConfigManager()
        cfg = mgr.load()
        assert cfg is not None
        assert cfg.name == "tengod-enterprise"
        assert cfg.version == "2.31.0"
        assert cfg.environment == "production"

    def test_cognitive_defaults(self):
        """测试认知配置默认值"""
        mgr = EnterpriseConfigManager()
        cfg = mgr.load()
        c = cfg.cognitive
        assert c.twelve_gods.enabled is True
        assert c.twelve_gods.majority_threshold == 0.5
        assert c.twelve_gods.veto_enabled is True
        assert c.twelve_gods.max_boost == 0.15

    def test_tbce_defaults(self):
        """测试TBCE配置默认值"""
        mgr = EnterpriseConfigManager()
        cfg = mgr.load()
        c = cfg.cognitive.tbce
        assert c.default_coordinates == [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        assert c.drift_warning_threshold == 0.3
        assert c.drift_critical_threshold == 0.5

    def test_seven_theories_defaults(self):
        """测试七论配置默认值"""
        mgr = EnterpriseConfigManager()
        cfg = mgr.load()
        c = cfg.cognitive.seven_theories
        assert c.thresholds["ontology"] == 0.7
        assert c.thresholds["epistemology"] == 0.7
        assert c.thresholds["practice"] == 0.6
        assert c.interruptible is True


class TestEnterpriseConfigAccess:
    """配置访问测试"""

    def test_get_config(self):
        """测试获取配置"""
        mgr = EnterpriseConfigManager()
        cfg = mgr.get_config()
        assert cfg is not None
        assert cfg.name == "tengod-enterprise"

    def test_get_nested(self):
        """测试点号路径访问"""
        mgr = EnterpriseConfigManager()
        mgr.load()
        assert mgr.get("cognitive.twelve_gods.enabled") is True
        assert mgr.get("cognitive.twelve_gods.majority_threshold") == 0.5
        assert mgr.get("cognitive.tbce.drift_warning_threshold") == 0.3

    def test_get_with_default(self):
        """测试不存在键返回默认值"""
        mgr = EnterpriseConfigManager()
        mgr.load()
        assert mgr.get("nonexistent.key", "default_val") == "default_val"
        assert mgr.get("cognitive.nonexistent", 42) == 42

    def test_reload(self):
        """测试强制重载"""
        mgr = EnterpriseConfigManager()
        cfg1 = mgr.load()
        cfg2 = mgr.reload()
        assert cfg2 is not None


class TestEnterpriseConfigRuntime:
    """运行时配置覆盖测试"""

    def test_set_runtime_override(self):
        """测试运行时覆盖配置"""
        mgr = EnterpriseConfigManager()
        mgr.load()
        assert mgr.get("cognitive.twelve_gods.strict_mode") is False

        mgr.set_runtime("cognitive.twelve_gods.strict_mode", True, reason="测试")
        assert mgr.get("cognitive.twelve_gods.strict_mode") is True

    def test_runtime_override_audit(self):
        """测试运行时覆盖生成审计记录"""
        mgr = EnterpriseConfigManager()
        mgr.load()
        mgr.set_runtime("cognitive.twelve_gods.majority_threshold", 0.7, reason="提高阈值")
        audit = mgr.get_audit_log()
        assert len(audit) > 0
        assert audit[-1]["key"] == "cognitive.twelve_gods.majority_threshold"
        assert audit[-1]["source"] == "runtime"

    def test_audit_summary(self):
        """测试审计摘要"""
        mgr = EnterpriseConfigManager()
        mgr.load()
        mgr.set_runtime("cognitive.twelve_gods.enabled", False, "测试1")
        mgr.set_runtime("cognitive.twelve_gods.strict_mode", True, "测试2")
        summary = mgr.get_audit_summary()
        assert summary["total_changes"] >= 2
        assert summary["by_source"]["runtime"] >= 2


class TestEnterpriseConfigHealth:
    """配置健康度测试"""

    def test_health_check_healthy(self):
        """测试健康配置"""
        mgr = EnterpriseConfigManager()
        mgr.load()
        result = mgr.health_check()
        assert result["status"] in ("healthy", "warning")
        assert "config_hash" in result

    def test_health_check_warnings(self):
        """测试配置警告检测"""
        mgr = EnterpriseConfigManager()
        mgr.load()
        mgr.set_runtime("cognitive.twelve_gods.majority_threshold", 0.1, "过低阈值")
        result = mgr.health_check()
        # 阈值0.1 < 0.3 应触发警告
        assert len(result["warnings"]) > 0 or len(result["issues"]) > 0

    def test_config_hash(self):
        """测试配置哈希"""
        mgr = EnterpriseConfigManager()
        mgr.load()
        h1 = mgr.health_check()["config_hash"]
        mgr.set_runtime("cognitive.twelve_gods.strict_mode", True, "变更")
        h2 = mgr.health_check()["config_hash"]
        assert h1 != h2

    def test_to_dict(self):
        """测试配置导出为字典"""
        mgr = EnterpriseConfigManager()
        mgr.load()
        d = mgr.to_dict()
        assert "name" in d
        assert "cognitive" in d
        assert "twelve_gods" in d["cognitive"]


class TestEnterpriseConfigListeners:
    """配置变更监听测试"""

    def test_on_change_listener(self):
        """测试变更监听器"""
        mgr = EnterpriseConfigManager()
        mgr.load()
        changes = []

        def listener(key, old, new):
            changes.append((key, old, new))

        mgr.on_change(listener)
        mgr.set_runtime("cognitive.twelve_gods.strict_mode", True, "test")
        assert len(changes) > 0

    def test_remove_listener(self):
        """测试移除监听器"""
        mgr = EnterpriseConfigManager()
        mgr.load()
        changes = []

        def listener(key, old, new):
            changes.append((key, old, new))

        mgr.on_change(listener)
        mgr.remove_listener(listener)
        mgr.set_runtime("cognitive.twelve_gods.strict_mode", True, "test")
        assert len(changes) == 0


class TestConfigChangeRecord:
    """配置变更记录测试"""

    def test_record_creation(self):
        """测试变更记录创建"""
        record = ConfigChangeRecord(
            key="test.key",
            old_value="old",
            new_value="new",
            source=ConfigSource.RUNTIME,
            reason="测试变更",
        )
        d = record.to_dict()
        assert d["key"] == "test.key"
        assert d["old_value"] == "old"
        assert d["new_value"] == "new"
        assert d["source"] == "runtime"


# ============================================================================
# 二、error_handler.py 测试
# ============================================================================

class TestErrorLevel:
    """错误分级测试"""

    def test_error_levels(self):
        """测试错误级别"""
        assert ErrorLevel.DEBUG.value == 0
        assert ErrorLevel.INFO.value == 1
        assert ErrorLevel.WARNING.value == 2
        assert ErrorLevel.ERROR.value == 3
        assert ErrorLevel.CRITICAL.value == 4
        assert ErrorLevel.FATAL.value == 5

    def test_is_recoverable(self):
        """测试可恢复判断"""
        assert ErrorLevel.DEBUG.is_recoverable is True
        assert ErrorLevel.INFO.is_recoverable is True
        assert ErrorLevel.WARNING.is_recoverable is True
        assert ErrorLevel.ERROR.is_recoverable is True
        assert ErrorLevel.CRITICAL.is_recoverable is False
        assert ErrorLevel.FATAL.is_recoverable is False

    def test_requires_immediate_action(self):
        """测试紧急判断"""
        assert ErrorLevel.DEBUG.requires_immediate_action is False
        assert ErrorLevel.CRITICAL.requires_immediate_action is True
        assert ErrorLevel.FATAL.requires_immediate_action is True


class TestNinePalaceErrorCategory:
    """九宫格错误分类测试"""

    def test_classify_value_error(self):
        """测试ValueError分类 → 坎1(数据源)"""
        cat = NinePalaceErrorCategory.classify(ValueError("invalid data"))
        assert cat == NinePalaceErrorCategory.KAN1

    def test_classify_key_error(self):
        """测试KeyError分类 → 坎1(数据源)"""
        cat = NinePalaceErrorCategory.classify(KeyError("missing_key"))
        assert cat == NinePalaceErrorCategory.KAN1

    def test_classify_io_error(self):
        """测试IOError分类 → 坤2(存储)"""
        cat = NinePalaceErrorCategory.classify(IOError("disk full"))
        assert cat == NinePalaceErrorCategory.KUN2

    def test_classify_file_not_found(self):
        """测试FileNotFoundError分类 → 坤2(存储)"""
        cat = NinePalaceErrorCategory.classify(FileNotFoundError("no file"))
        assert cat == NinePalaceErrorCategory.KUN2

    def test_classify_import_error(self):
        """测试ImportError分类 → 震3(初始化)"""
        cat = NinePalaceErrorCategory.classify(ImportError("no module"))
        assert cat == NinePalaceErrorCategory.ZHEN3

    def test_classify_connection_error(self):
        """测试连接错误分类 → 巽4(通信)"""
        cat = NinePalaceErrorCategory.classify(ConnectionError("timeout"))
        assert cat == NinePalaceErrorCategory.XUN4

    def test_classify_permission_error(self):
        """测试权限错误分类 → 乾6(权限)"""
        cat = NinePalaceErrorCategory.classify(PermissionError("denied"))
        assert cat == NinePalaceErrorCategory.QIAN6

    def test_classify_type_error(self):
        """测试TypeError分类 → 兑7(输出)"""
        cat = NinePalaceErrorCategory.classify(TypeError("bad type"))
        assert cat == NinePalaceErrorCategory.DUI7

    def test_classify_default(self):
        """测试默认分类 → 中5(核心)"""
        cat = NinePalaceErrorCategory.classify(Exception("unknown"))
        assert cat == NinePalaceErrorCategory.ZHONG5

    def test_palace_attributes(self):
        """测试九宫格属性"""
        cat = NinePalaceErrorCategory.KAN1
        assert cat.palace_name == "坎一"
        assert cat.element == "水"
        assert cat.category_name == "数据源错误"

    def test_all_nine_categories(self):
        """测试全部九宫格分类"""
        assert len(NinePalaceErrorCategory) == 9


class TestFallbackStrategy:
    """回退策略测试"""

    def test_strategy_values(self):
        """测试策略枚举值"""
        assert FallbackStrategy.DEGRADE.value == "degrade"
        assert FallbackStrategy.RETRY.value == "retry"
        assert FallbackStrategy.CHAOS_SEA.value == "chaos_sea"
        assert FallbackStrategy.CIRCUIT_BREAK.value == "break"


class TestErrorHandler:
    """错误处理器测试"""

    def test_handle_value_error(self):
        """测试处理ValueError"""
        handler = ErrorHandler()
        record = handler.handle(ValueError("bad value"), module="test", function="test_func")
        assert record is not None
        assert record.level == ErrorLevel.ERROR
        assert record.category == NinePalaceErrorCategory.KAN1
        assert record.module == "test"

    def test_handle_with_context(self):
        """测试带上下文错误处理"""
        handler = ErrorHandler()
        record = handler.handle(
            Exception("test error"),
            level=ErrorLevel.WARNING,
            context={"user_id": "123", "action": "test"},
        )
        assert record.context["user_id"] == "123"

    def test_auto_level_classification(self):
        """测试自动分级"""
        handler = ErrorHandler()
        record = handler.handle(ValueError("test"))
        assert record.level == ErrorLevel.ERROR

    def test_error_counter(self):
        """测试错误计数"""
        handler = ErrorHandler()
        handler.handle(ValueError("e1"))
        handler.handle(TypeError("e2"))
        stats = handler.get_stats()
        assert stats["total_errors"] >= 2

    def test_category_counter(self):
        """测试分类计数"""
        handler = ErrorHandler()
        handler.handle(ValueError("e1"))
        handler.handle(ValueError("e2"))
        stats = handler.get_stats()
        assert stats["by_category"]["坎一"] >= 2

    def test_recent_errors(self):
        """测试获取最近错误"""
        handler = ErrorHandler()
        for i in range(5):
            handler.handle(ValueError(f"error_{i}"))
        recent = handler.get_recent_errors(limit=3)
        assert len(recent) == 3

    def test_get_errors_by_category(self):
        """测试按分类获取错误"""
        handler = ErrorHandler()
        handler.handle(ValueError("e1"))
        handler.handle(ValueError("e2"))
        handler.handle(PermissionError("denied"))
        kan_errors = handler.get_errors_by_category(NinePalaceErrorCategory.KAN1)
        assert len(kan_errors) >= 2

    def test_gate_impact(self):
        """测试门禁影响评估"""
        handler = ErrorHandler()
        record = handler.handle(ValueError("bad data"))
        assert record.gate_impact is not None
        assert "affected_god" in record.gate_impact
        assert "impact_description" in record.gate_impact

    def test_gate_impact_summary(self):
        """测试门禁影响摘要"""
        handler = ErrorHandler()
        handler.handle(ValueError("e1"))
        handler.handle(PermissionError("e2"))
        summary = handler.get_gate_impact_summary()
        assert len(summary) > 0

    def test_safe_execute_success(self):
        """测试安全执行成功"""
        handler = ErrorHandler()
        result, error = handler.safe_execute(
            lambda x: x * 2, 21, module="test", function="double"
        )
        assert result == 42
        assert error is None

    def test_safe_execute_with_default(self):
        """测试安全执行失败返回默认值"""
        handler = ErrorHandler()

        def failing_func():
            raise ValueError("boom")

        result, error = handler.safe_execute(
            failing_func, module="test", function="fail", default="fallback"
        )
        assert result == "fallback"
        assert error is not None

    def test_safe_execute_retry(self):
        """测试安全执行重试"""
        handler = ErrorHandler()
        attempts = []

        def flaky_func():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("temporary")
            return "success"

        result, error = handler.safe_execute(
            flaky_func, module="test", function="flaky", max_retries=3
        )
        assert result == "success"
        assert len(attempts) == 3

    def test_circuit_breaker(self):
        """测试熔断器"""
        handler = ErrorHandler()
        for i in range(6):
            record = handler.handle(
                RuntimeError("critical"),
                level=ErrorLevel.CRITICAL,
                module="broken",
                function="fail",
            )
        assert handler.is_circuit_broken("broken", "fail") is True

    def test_reset_circuit_breaker(self):
        """测试重置熔断器"""
        handler = ErrorHandler()
        for i in range(6):
            handler.handle(
                RuntimeError("critical"),
                level=ErrorLevel.CRITICAL,
                module="broken",
                function="fail",
            )
        handler.reset_circuit_breaker("broken", "fail")
        assert handler.is_circuit_broken("broken", "fail") is False

    def test_error_record_dict(self):
        """测试错误记录序列化"""
        handler = ErrorHandler()
        record = handler.handle(ValueError("test"))
        d = record.to_dict()
        assert "error_id" in d
        assert "level" in d
        assert "category" in d
        assert "message" in d


# ============================================================================
# 三、cognitive_metrics.py 测试
# ============================================================================

class TestTBCEDriftRecord:
    """TBCE漂移记录测试"""

    def test_record_creation(self):
        """测试漂移记录创建"""
        record = TBCEDriftRecord(
            unit_id="unit_1",
            unit_name="test_unit",
            coords_before=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
            coords_after=[0.6, 0.6, 0.6, 0.6, 0.6, 0.6],
            drift_distance=0.245,
            drift_per_dimension=[0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
            trigger="gate_judge",
        )
        assert record.unit_id == "unit_1"
        assert record.drift_distance == pytest.approx(0.245)

    def test_is_warning(self):
        """测试漂移警告判定"""
        record = TBCEDriftRecord(
            unit_id="u1", unit_name="test",
            coords_before=[0.5]*6, coords_after=[0.9]*6,
            drift_distance=0.4, drift_per_dimension=[0.4]*6,
        )
        assert record.is_warning is True
        assert record.is_critical is False

    def test_is_critical(self):
        """测试漂移严重判定"""
        record = TBCEDriftRecord(
            unit_id="u1", unit_name="test",
            coords_before=[0.5]*6, coords_after=[1.0]*6,
            drift_distance=0.6, drift_per_dimension=[0.5]*6,
        )
        assert record.is_critical is True

    def test_to_dict(self):
        """测试漂移记录序列化"""
        record = TBCEDriftRecord(
            unit_id="u1", unit_name="test",
            coords_before=[0.5]*6, coords_after=[0.6]*6,
            drift_distance=0.245, drift_per_dimension=[0.1]*6,
        )
        d = record.to_dict()
        assert "unit_id" in d
        assert "drift_distance" in d
        assert d["is_warning"] is False


class TestGatePassRecord:
    """门禁通过记录测试"""

    def test_record_creation(self):
        """测试门禁记录创建"""
        record = GatePassRecord(
            gate_name="比肩·劫财",
            god_name="比肩",
            element="木",
            passed=True,
            score=0.85,
            element_boost=0.05,
            reason="架构健康",
        )
        assert record.gate_name == "比肩·劫财"
        assert record.passed is True
        assert record.element == "木"

    def test_to_dict(self):
        """测试门禁记录序列化"""
        record = GatePassRecord(
            gate_name="食神·伤官",
            god_name="食神",
            element="火",
            passed=False,
            score=0.45,
            element_boost=0.0,
            reason="创新质量不足",
        )
        d = record.to_dict()
        assert d["gate_name"] == "食神·伤官"
        assert d["passed"] is False
        assert d["score"] == 0.45


class TestCognitiveMetricsCollector:
    """认知指标采集器测试"""

    def test_record_tbce_drift(self):
        """测试记录TBCE漂移"""
        collector = CognitiveMetricsCollector()
        record = collector.record_tbce_drift(
            unit_id="unit_1",
            unit_name="test_unit",
            coords_before=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
            coords_after=[0.6, 0.6, 0.6, 0.6, 0.6, 0.6],
            trigger="gate_judge",
        )
        assert record is not None
        assert record.drift_distance > 0

    def test_drift_distance_calculation(self):
        """测试漂移距离计算正确性"""
        collector = CognitiveMetricsCollector()
        record = collector.record_tbce_drift(
            unit_id="u1", unit_name="test",
            coords_before=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            coords_after=[0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        )
        expected = math.sqrt(6 * 0.01)  # sqrt(0.06)
        assert record.drift_distance == pytest.approx(expected)

    def test_drift_stats(self):
        """测试漂移统计"""
        collector = CognitiveMetricsCollector()
        for i in range(5):
            collector.record_tbce_drift(
                unit_id=f"u{i}", unit_name=f"unit_{i}",
                coords_before=[0.5]*6,
                coords_after=[0.5 + i*0.1]*6,
            )
        stats = collector.get_drift_stats()
        assert stats["total"] == 5
        assert "mean_drift" in stats
        assert "by_dimension" in stats

    def test_drift_alerts(self):
        """测试漂移告警"""
        collector = CognitiveMetricsCollector()
        for i in range(20):
            collector.record_tbce_drift(
                unit_id=f"u{i}", unit_name=f"unit_{i}",
                coords_before=[0.5]*6,
                coords_after=[0.9]*6,  # 大漂移
            )
        alerts = collector.check_drift_alerts()
        assert len(alerts) > 0

    def test_record_gate_pass(self):
        """测试记录门禁通过"""
        collector = CognitiveMetricsCollector()
        record = collector.record_gate_pass(
            gate_name="比肩·劫财",
            god_name="比肩",
            element="木",
            passed=True,
            score=0.9,
            element_boost=0.05,
            reason="健康",
        )
        assert record is not None
        assert record.passed is True

    def test_gate_stats(self):
        """测试门禁统计"""
        collector = CognitiveMetricsCollector()
        for i in range(10):
            collector.record_gate_pass(
                gate_name="比肩·劫财",
                god_name="比肩",
                element="木",
                passed=i < 8,  # 80%通过
                score=0.7 + i * 0.02,
                element_boost=0.05,
            )
        stats = collector.get_gate_stats()
        assert stats["total"] == 10
        assert stats["overall_pass_rate"] == 0.8
        assert "by_gate" in stats
        assert "by_element" in stats

    def test_gate_stats_by_element(self):
        """测试按五行门禁统计"""
        collector = CognitiveMetricsCollector()
        collector.record_gate_pass("木门", "比肩", "木", True, 0.9, 0.05)
        collector.record_gate_pass("火门", "食神", "火", False, 0.4, 0.0)
        collector.record_gate_pass("木门2", "劫财", "木", True, 0.8, 0.03)
        stats = collector.get_gate_stats()
        assert "木" in stats["by_element"]
        assert "火" in stats["by_element"]

    def test_gate_trend(self):
        """测试门禁通过率趋势"""
        collector = CognitiveMetricsCollector()
        for i in range(30):
            collector.record_gate_pass(
                gate_name="比肩·劫财",
                god_name="比肩",
                element="木",
                passed=i % 2 == 0,  # 交替通过
                score=0.5 + (i % 2) * 0.4,
            )
        trend = collector.get_gate_trend(window_size=10)
        assert "比肩·劫财" in trend

    def test_record_inference(self):
        """测试记录推理耗时"""
        collector = CognitiveMetricsCollector()
        collector.record_inference(150.0)
        collector.record_inference(250.0)
        stats = collector.get_inference_stats()
        assert stats["count"] == 2
        assert stats["mean_ms"] == 200.0

    def test_record_speculation(self):
        """测试推测解码统计"""
        collector = CognitiveMetricsCollector()
        collector.record_speculation(True)
        collector.record_speculation(True)
        collector.record_speculation(False)
        stats = collector.get_speculation_stats()
        assert stats["total"] == 3
        assert stats["hits"] == 2
        assert stats["hit_rate"] == pytest.approx(2 / 3, abs=1e-3)

    def test_record_correction(self):
        """测试自修正统计"""
        collector = CognitiveMetricsCollector()
        collector.record_correction(True)
        collector.record_correction(True)
        collector.record_correction(False)
        stats = collector.get_correction_stats()
        assert stats["total"] == 3
        assert stats["success"] == 2

    def test_record_chaos_sea_entry(self):
        """测试混沌海统计"""
        collector = CognitiveMetricsCollector()
        collector.record_chaos_sea_entry()
        collector.record_chaos_sea_entry()
        stats = collector.get_correction_stats()
        assert stats["chaos_sea_entries"] == 2

    def test_layer_coverage(self):
        """测试认知层覆盖"""
        collector = CognitiveMetricsCollector()
        collector.update_layer_coverage({1: 10, 2: 5, 3: 3})
        coverage = collector.get_layer_coverage()
        assert coverage[1] == 10
        assert coverage[2] == 5

    def test_take_snapshot(self):
        """测试认知快照"""
        collector = CognitiveMetricsCollector()
        collector.record_gate_pass("门", "神", "木", True, 0.9, 0.05)
        collector.record_inference(100.0)
        snap = collector.take_snapshot()
        assert snap is not None
        assert snap.gate_total > 0

    def test_latest_snapshot(self):
        """测试获取最新快照"""
        collector = CognitiveMetricsCollector()
        collector.take_snapshot()
        snap = collector.get_latest_snapshot()
        assert snap is not None

    def test_snapshot_history(self):
        """测试快照历史"""
        collector = CognitiveMetricsCollector()
        for i in range(5):
            collector.take_snapshot()
        history = collector.get_snapshot_history()
        assert len(history) == 5

    def test_dashboard_data(self):
        """测试仪表盘数据"""
        collector = CognitiveMetricsCollector()
        collector.record_gate_pass("门", "神", "木", True, 0.9, 0.05)
        collector.record_inference(100.0)
        data = collector.get_dashboard_data()
        assert "overall_health" in data
        assert "gates" in data
        assert "drift" in data
        assert "inference" in data
        assert "alerts" in data

    def test_health_score(self):
        """测试健康分数"""
        collector = CognitiveMetricsCollector()
        for i in range(10):
            collector.record_gate_pass("门", "神", "木", True, 0.9, 0.05)
        score = collector._compute_health_score()
        assert 0.0 <= score <= 1.0

    def test_health_status(self):
        """测试健康状态"""
        collector = CognitiveMetricsCollector()
        status = collector.get_health_status()
        assert status["status"] in ("healthy", "warning", "degraded", "critical")
        assert "score" in status


# ============================================================================
# 四、tracing.py 测试
# ============================================================================

class TestSpanKind:
    """跨度类型测试"""

    def test_span_kinds(self):
        """测试跨度类型"""
        assert SpanKind.ROOT.value == "root"
        assert SpanKind.GATE_JUDGE.value == "gate_judge"
        assert SpanKind.SELF_CORRECTION.value == "self_correction"
        assert SpanKind.TBCE_DRIFT.value == "tbce_drift"


class TestSpanStatus:
    """跨度状态测试"""

    def test_span_statuses(self):
        """测试跨度状态"""
        assert SpanStatus.STARTED.value == "started"
        assert SpanStatus.SUCCESS.value == "success"
        assert SpanStatus.FAILED.value == "failed"
        assert SpanStatus.INTERRUPTED.value == "interrupted"
        assert SpanStatus.CHAOS_SEA.value == "chaos_sea"


class TestTraceSpan:
    """追踪跨度测试"""

    def test_span_creation(self):
        """测试跨度创建"""
        span = TraceSpan(
            span_id="span_001",
            parent_span_id=None,
            trace_id="trace_001",
            name="test_span",
            kind=SpanKind.ROOT,
        )
        assert span.span_id == "span_001"
        assert span.status == SpanStatus.STARTED

    def test_span_finish(self):
        """测试跨度结束"""
        span = TraceSpan(
            span_id="s1", parent_span_id=None,
            trace_id="t1", name="test", kind=SpanKind.ROOT,
        )
        span.finish(SpanStatus.SUCCESS, metadata={"result": "ok"})
        assert span.status == SpanStatus.SUCCESS
        assert span.duration_ms > 0
        assert span.metadata["result"] == "ok"

    def test_span_to_dict(self):
        """测试跨度序列化"""
        span = TraceSpan(
            span_id="s1", parent_span_id=None,
            trace_id="t1", name="test", kind=SpanKind.GATE_JUDGE,
            gate_name="比肩·劫财", element_boost=0.05,
        )
        span.finish()
        d = span.to_dict()
        assert d["span_id"] == "s1"
        assert d["kind"] == "gate_judge"
        assert d["gate_name"] == "比肩·劫财"


class TestTrace:
    """追踪链测试"""

    def test_trace_creation(self):
        """测试追踪链创建"""
        trace = Trace(
            trace_id="trace_001",
            root_span_id="root_001",
        )
        assert trace.trace_id == "trace_001"
        assert trace.status == SpanStatus.STARTED

    def test_trace_finish(self):
        """测试追踪链结束"""
        trace = Trace(trace_id="t1", root_span_id="r1")
        trace.finish(SpanStatus.SUCCESS)
        assert trace.status == SpanStatus.SUCCESS
        assert trace.total_duration_ms > 0

    def test_trace_to_dict(self):
        """测试追踪链序列化"""
        trace = Trace(trace_id="t1", root_span_id="r1")
        span = TraceSpan(
            span_id="r1", parent_span_id=None,
            trace_id="t1", name="root", kind=SpanKind.ROOT,
        )
        span.finish()
        trace.spans.append(span)
        trace.finish()
        d = trace.to_dict()
        assert d["trace_id"] == "t1"
        assert d["span_count"] == 1


class TestTraceManager:
    """追踪管理器测试"""

    def test_start_trace(self):
        """测试开始追踪"""
        mgr = TraceManager()
        trace = mgr.start_trace("test_inference", "test_module")
        assert trace is not None
        assert trace.trace_id.startswith("trace_")
        assert len(trace.spans) == 1  # 根跨度

    def test_start_span(self):
        """测试创建子跨度"""
        mgr = TraceManager()
        trace = mgr.start_trace("test")
        span = mgr.start_span(
            trace_id=trace.trace_id,
            name="gate_judge",
            kind=SpanKind.GATE_JUDGE,
            module="test",
            function="judge",
        )
        assert span is not None
        assert span.parent_span_id == trace.root_span_id
        assert len(trace.spans) == 2

    def test_finish_span(self):
        """测试结束跨度"""
        mgr = TraceManager()
        trace = mgr.start_trace("test")
        span = mgr.start_span(trace.trace_id, "test_span", SpanKind.CUSTOM)
        mgr.finish_span(span, SpanStatus.SUCCESS)
        assert span.status == SpanStatus.SUCCESS
        assert span.duration_ms > 0

    def test_finish_trace(self):
        """测试结束追踪"""
        mgr = TraceManager()
        trace = mgr.start_trace("test")
        finished = mgr.finish_trace(trace.trace_id)
        assert finished is not None
        assert finished.status == SpanStatus.SUCCESS

    def test_trace_gate_judge(self):
        """测试门禁裁决追踪"""
        mgr = TraceManager()
        trace = mgr.start_trace("test")

        class MockVerdict:
            passed = True
            state = type('obj', (object,), {'value': 'open'})()
            def to_dict(self):
                return {"passed": True, "score": 0.9}

        span = mgr.trace_gate_judge(
            trace_id=trace.trace_id,
            gate_name="比肩·劫财",
            verdict=MockVerdict(),
            element_boost=0.05,
        )
        assert span is not None
        assert span.kind == SpanKind.GATE_JUDGE
        assert span.gate_name == "比肩·劫财"

    def test_trace_correction_step(self):
        """测试自修正步骤追踪"""
        mgr = TraceManager()
        trace = mgr.start_trace("test")
        span = mgr.trace_correction_step(
            trace_id=trace.trace_id,
            step_index=1,
            step_name="观自在",
            tech_name="偏差检测",
            status="completed",
            gate_passed=True,
            gate_verdict={"passed": True},
            interrupted_reason="",
            delta=0.1,
            confidence=0.9,
            duration_ms=50.0,
        )
        assert span is not None
        assert span.correction_step == 1
        assert span.correction_name == "观自在"

    def test_trace_tbce_drift(self):
        """测试TBCE漂移追踪"""
        mgr = TraceManager()
        trace = mgr.start_trace("test")
        span = mgr.trace_tbce_drift(
            trace_id=trace.trace_id,
            unit_name="test_unit",
            coords_before={"S": 0.5, "T": 0.5, "P": 0.5, "C": 0.5, "I": 0.5, "E": 0.5},
            coords_after={"S": 0.6, "T": 0.6, "P": 0.6, "C": 0.6, "I": 0.6, "E": 0.6},
            drift=0.245,
        )
        assert span is not None
        assert span.tbce_drift == pytest.approx(0.245)

    def test_get_trace(self):
        """测试获取追踪"""
        mgr = TraceManager()
        trace = mgr.start_trace("test")
        mgr.finish_trace(trace.trace_id)
        result = mgr.get_trace(trace.trace_id)
        assert result is not None
        assert result["trace_id"] == trace.trace_id

    def test_get_active_traces(self):
        """测试获取活跃追踪"""
        mgr = TraceManager()
        mgr.start_trace("test1")
        mgr.start_trace("test2")
        active = mgr.get_active_traces()
        assert len(active) == 2

    def test_get_completed_traces(self):
        """测试获取已完成追踪"""
        mgr = TraceManager()
        trace = mgr.start_trace("test")
        mgr.finish_trace(trace.trace_id)
        completed = mgr.get_completed_traces()
        assert len(completed) == 1

    def test_audit_log(self):
        """测试审计日志"""
        mgr = TraceManager()
        trace = mgr.start_trace("test")
        mgr.trace_correction_step(
            trace_id=trace.trace_id,
            step_index=1, step_name="观自在", tech_name="检测",
            status="completed", gate_passed=True,
            gate_verdict={"passed": True}, interrupted_reason="",
            delta=0.1, confidence=0.9, duration_ms=50.0,
        )
        mgr.trace_correction_step(
            trace_id=trace.trace_id,
            step_index=2, step_name="格物致知", tech_name="归因",
            status="completed", gate_passed=True,
            gate_verdict={"passed": True}, interrupted_reason="",
            delta=0.2, confidence=0.85, duration_ms=60.0,
        )
        audit = mgr.get_audit_log()
        assert len(audit) == 2

    def test_audit_filter_by_trace(self):
        """测试按追踪ID过滤审计"""
        mgr = TraceManager()
        t1 = mgr.start_trace("test1")
        t2 = mgr.start_trace("test2")
        mgr.trace_correction_step(
            trace_id=t1.trace_id, step_index=1, step_name="s1", tech_name="t1",
            status="completed", gate_passed=True,
            gate_verdict={}, interrupted_reason="",
            delta=0.1, confidence=0.9, duration_ms=50.0,
        )
        mgr.trace_correction_step(
            trace_id=t2.trace_id, step_index=1, step_name="s1", tech_name="t1",
            status="completed", gate_passed=True,
            gate_verdict={}, interrupted_reason="",
            delta=0.1, confidence=0.9, duration_ms=50.0,
        )
        filtered = mgr.get_audit_log(trace_id=t1.trace_id)
        assert len(filtered) == 1

    def test_audit_summary(self):
        """测试审计摘要"""
        mgr = TraceManager()
        trace = mgr.start_trace("test")
        mgr.trace_correction_step(
            trace_id=trace.trace_id, step_index=1, step_name="s1", tech_name="t1",
            status="completed", gate_passed=True,
            gate_verdict={}, interrupted_reason="",
            delta=0.1, confidence=0.9, duration_ms=50.0,
        )
        summary = mgr.get_audit_summary()
        assert summary["total_entries"] == 1
        assert summary["pass_rate"] == 1.0

    def test_trace_stats(self):
        """测试追踪统计"""
        mgr = TraceManager()
        trace = mgr.start_trace("test")
        mgr.trace_gate_judge(
            trace_id=trace.trace_id,
            gate_name="test_gate",
            verdict=type('v', (), {'passed': True, 'to_dict': lambda: {}})(),
        )
        mgr.finish_trace(trace.trace_id)
        stats = mgr.get_trace_stats()
        assert stats["total_traces"] == 1

    def test_inference_chain(self):
        """测试推理链可追溯"""
        mgr = TraceManager()
        trace = mgr.start_trace("test_inference")
        mgr.trace_gate_judge(
            trace_id=trace.trace_id,
            gate_name="比肩·劫财",
            verdict=type('v', (), {'passed': True, 'to_dict': lambda: {}})(),
        )
        mgr.finish_trace(trace.trace_id)
        chain = mgr.get_inference_chain(trace.trace_id)
        assert chain is not None
        assert chain["trace_id"] == trace.trace_id
        assert "chain" in chain

    def test_nested_spans(self):
        """测试嵌套跨度"""
        mgr = TraceManager()
        trace = mgr.start_trace("test")
        parent = mgr.start_span(trace.trace_id, "parent", SpanKind.CUSTOM)
        child = mgr.start_span(
            trace.trace_id, "child", SpanKind.CUSTOM,
            parent_span_id=parent.span_id,
        )
        assert child.parent_span_id == parent.span_id
        assert len(trace.spans) == 3  # root + parent + child


# ============================================================================
# 五、集成测试
# ============================================================================

class TestPhase2Integration:
    """Phase 2 集成测试"""

    def test_config_to_error_integration(self):
        """配置 → 错误处理集成"""
        cfg_mgr = EnterpriseConfigManager()
        cfg_mgr.load()
        assert cfg_mgr.get("cognitive.twelve_gods.enabled") is True

        err_handler = ErrorHandler()
        record = err_handler.handle(ValueError("test"))
        assert record.gate_impact is not None

    def test_error_to_tracing_integration(self):
        """错误处理 → 追踪集成"""
        err_handler = ErrorHandler()
        trace_mgr = TraceManager()
        trace = trace_mgr.start_trace("test")
        span = trace_mgr.start_span(trace.trace_id, "error_test", SpanKind.CUSTOM)
        err_handler.handle(ValueError("test"), module="test", function="test_func")
        trace_mgr.finish_span(span, SpanStatus.FAILED, "test error")
        trace_mgr.finish_trace(trace.trace_id)
        assert trace_mgr.get_trace(trace.trace_id) is not None

    def test_metrics_to_tracing_integration(self):
        """指标采集 → 追踪集成"""
        collector = CognitiveMetricsCollector()
        trace_mgr = TraceManager()
        trace = trace_mgr.start_trace("test")

        collector.record_gate_pass("比肩·劫财", "比肩", "木", True, 0.9, 0.05)
        trace_mgr.trace_gate_judge(
            trace_id=trace.trace_id,
            gate_name="比肩·劫财",
            verdict=type('v', (), {'passed': True, 'to_dict': lambda: {}})(),
        )
        trace_mgr.finish_trace(trace.trace_id)

        stats = collector.get_gate_stats()
        assert stats["total"] >= 1

    def test_full_pipeline_trace(self):
        """全管道追踪集成"""
        trace_mgr = TraceManager()
        collector = CognitiveMetricsCollector()

        # 开始推理追踪
        trace = trace_mgr.start_trace("full_pipeline", "pipeline")

        # 门禁裁决追踪
        for gate_name in ["比肩·劫财", "食神·伤官", "正财·偏财"]:
            span = trace_mgr.trace_gate_judge(
                trace_id=trace.trace_id,
                gate_name=gate_name,
                verdict=type('v', (), {'passed': True, 'to_dict': lambda: {}})(),
            )
            collector.record_gate_pass(gate_name, "test", "木", True, 0.8, 0.05)

        # 自修正追踪
        for step in range(1, 8):
            trace_mgr.trace_correction_step(
                trace_id=trace.trace_id,
                step_index=step, step_name=f"step_{step}", tech_name="test",
                status="completed", gate_passed=True,
                gate_verdict={"passed": True}, interrupted_reason="",
                delta=0.1, confidence=0.9, duration_ms=50.0,
            )
            collector.record_correction(True)

        # 推理统计
        collector.record_inference(200.0)
        collector.record_speculation(True)

        # 结束追踪
        trace_mgr.finish_trace(trace.trace_id)

        # 验证
        chain = trace_mgr.get_inference_chain(trace.trace_id)
        assert chain is not None
        assert len(chain["chain"]["children"]) >= 3  # 3个门禁

        stats = collector.get_gate_stats()
        assert stats["total"] >= 3

        correction = collector.get_correction_stats()
        assert correction["total"] >= 7


# ============================================================================
# 六、边界条件测试
# ============================================================================

class TestEdgeCases:
    """边界条件测试"""

    def test_empty_config_stats(self):
        """空配置统计"""
        mgr = EnterpriseConfigManager()
        mgr.load()
        stats = mgr.get_audit_log()
        assert stats == []

    def test_empty_error_stats(self):
        """空错误统计"""
        handler = ErrorHandler()
        stats = handler.get_stats()
        assert stats["total_errors"] == 0

    def test_empty_metrics_stats(self):
        """空指标统计"""
        collector = CognitiveMetricsCollector()
        stats = collector.get_gate_stats()
        assert stats["total"] == 0

    def test_empty_trace_stats(self):
        """空追踪统计"""
        trace_mgr = TraceManager()
        stats = trace_mgr.get_trace_stats()
        assert stats["total_traces"] == 0

    def test_nonexistent_trace(self):
        """不存在的追踪"""
        trace_mgr = TraceManager()
        result = trace_mgr.get_trace("nonexistent")
        assert result is None

    def test_nonexistent_inference_chain(self):
        """不存在的推理链"""
        trace_mgr = TraceManager()
        result = trace_mgr.get_inference_chain("nonexistent")
        assert result is None

    def test_empty_audit_summary(self):
        """空审计摘要"""
        trace_mgr = TraceManager()
        summary = trace_mgr.get_audit_summary()
        assert summary["total_entries"] == 0

    def test_reset_all_singletons(self):
        """重置所有单例"""
        # 先使用
        get_enterprise_config().load()
        get_error_handler().handle(ValueError("test"))
        get_cognitive_metrics().record_gate_pass("g", "s", "e", True, 0.5)
        get_trace_manager().start_trace("test")

        # 重置
        reset_enterprise_config()
        reset_error_handler()
        reset_cognitive_metrics()
        reset_trace_manager()

        # 验证重置后为空
        assert get_error_handler().get_stats()["total_errors"] == 0
        assert get_cognitive_metrics().get_gate_stats()["total"] == 0
        assert get_trace_manager().get_trace_stats()["total_traces"] == 0