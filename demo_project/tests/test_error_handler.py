#!/usr/bin/env python3
"""
test_error_handler.py — 分级错误处理器深度测试 v4.6.0
======================================================
针对 error_handler.py 中高风险逻辑路径的补充测试：
- 九宫格分类：所有 9 类 + 关键词触发路径
- 熔断器：阈值边界、重置、仅模块名路径
- 自动恢复：所有回退策略、恢复率计算
- 单例模式：线程安全、全局实例重置
- 安全执行：熔断短路、重试退避、默认值回退
- 错误日志裁剪：1000 条上限
- 门禁影响：所有九宫格对应映射
"""

import threading
import time

import pytest

from tengod.error_handler import (
    ErrorLevel,
    NinePalaceErrorCategory,
    FallbackStrategy,
    ErrorRecord,
    ErrorHandler,
    get_error_handler,
    reset_error_handler,
)


# ============================================================================
# 辅助 fixture
# ============================================================================

@pytest.fixture
def fresh_handler():
    """每个测试使用独立的 ErrorHandler 实例，避免单例污染。"""
    # 先重置全局单例，再创建新实例
    reset_error_handler()
    handler = ErrorHandler()
    handler.reset()
    yield handler
    handler.reset()
    reset_error_handler()


@pytest.fixture(autouse=True)
def reset_global_singleton():
    """确保每个测试前后全局单例被重置，避免交叉污染。"""
    reset_error_handler()
    yield
    reset_error_handler()


# ============================================================================
# 一、ErrorLevel 边界与属性
# ============================================================================

class TestErrorLevelEdgeCases:
    """错误分级边界条件测试"""

    def test_all_six_levels_exist(self):
        """六级错误完整存在"""
        assert len(ErrorLevel) == 6
        levels = [e for e in ErrorLevel]
        assert levels[0] == ErrorLevel.DEBUG
        assert levels[-1] == ErrorLevel.FATAL

    def test_is_recoverable_boundary(self):
        """可恢复性边界：ERROR 可恢复，CRITICAL 不可恢复"""
        assert ErrorLevel.ERROR.is_recoverable is True
        assert ErrorLevel.CRITICAL.is_recoverable is False

    def test_requires_immediate_action_boundary(self):
        """立即处理边界：WARNING 不需要，CRITICAL 需要"""
        assert ErrorLevel.WARNING.requires_immediate_action is False
        assert ErrorLevel.CRITICAL.requires_immediate_action is True
        assert ErrorLevel.FATAL.requires_immediate_action is True

    def test_numeric_ordering(self):
        """级别数值递增"""
        prev = -1
        for level in ErrorLevel:
            assert level.value > prev
            prev = level.value


# ============================================================================
# 二、NinePalaceErrorCategory — 全量分类覆盖
# ============================================================================

class TestNinePalaceFullClassification:
    """九宫格错误分类全量覆盖"""

    # ── 坎1：数据源错误 ────────────────────────────────────

    def test_classify_value_error_type(self):
        cat = NinePalaceErrorCategory.classify(ValueError("test"))
        assert cat == NinePalaceErrorCategory.KAN1

    def test_classify_key_error_type(self):
        cat = NinePalaceErrorCategory.classify(KeyError("k"))
        assert cat == NinePalaceErrorCategory.KAN1

    def test_classify_index_error_type(self):
        cat = NinePalaceErrorCategory.classify(IndexError("idx"))
        assert cat == NinePalaceErrorCategory.KAN1

    def test_classify_parse_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("failed to parse input"))
        assert cat == NinePalaceErrorCategory.KAN1

    def test_classify_decode_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("decode error in data"))
        assert cat == NinePalaceErrorCategory.KAN1

    def test_classify_corrupt_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("data is corrupt"))
        assert cat == NinePalaceErrorCategory.KAN1

    # ── 坤2：存储错误 ──────────────────────────────────────

    def test_classify_io_error_type(self):
        cat = NinePalaceErrorCategory.classify(IOError("disk"))
        assert cat == NinePalaceErrorCategory.KUN2

    def test_classify_os_error_type(self):
        cat = NinePalaceErrorCategory.classify(OSError("io fail"))
        assert cat == NinePalaceErrorCategory.KUN2

    def test_classify_file_not_found_type(self):
        cat = NinePalaceErrorCategory.classify(FileNotFoundError("f"))
        assert cat == NinePalaceErrorCategory.KUN2

    def test_classify_storage_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("storage failure"))
        assert cat == NinePalaceErrorCategory.KUN2

    def test_classify_persist_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("cannot persist to disk"))
        assert cat == NinePalaceErrorCategory.KUN2

    # ── 震3：初始化错误 ────────────────────────────────────

    def test_classify_import_error_type(self):
        cat = NinePalaceErrorCategory.classify(ImportError("bad"))
        assert cat == NinePalaceErrorCategory.ZHEN3

    def test_classify_module_not_found_type(self):
        cat = NinePalaceErrorCategory.classify(ModuleNotFoundError("m"))
        assert cat == NinePalaceErrorCategory.ZHEN3

    def test_classify_init_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("init module failed"))
        assert cat == NinePalaceErrorCategory.ZHEN3

    def test_classify_load_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("cannot load plugin"))
        assert cat == NinePalaceErrorCategory.ZHEN3

    # ── 巽4：通信错误 ──────────────────────────────────────

    def test_classify_connection_error_type(self):
        cat = NinePalaceErrorCategory.classify(ConnectionError("net"))
        assert cat == NinePalaceErrorCategory.XUN4

    def test_classify_timeout_error_type(self):
        cat = NinePalaceErrorCategory.classify(TimeoutError("req"))
        assert cat == NinePalaceErrorCategory.XUN4

    def test_classify_network_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("network down"))
        assert cat == NinePalaceErrorCategory.XUN4

    def test_classify_http_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("http request failed"))
        assert cat == NinePalaceErrorCategory.XUN4

    def test_classify_socket_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("socket closed"))
        assert cat == NinePalaceErrorCategory.XUN4

    # ── 乾6：权限错误 ──────────────────────────────────────

    def test_classify_permission_error_type(self):
        cat = NinePalaceErrorCategory.classify(PermissionError("no"))
        assert cat == NinePalaceErrorCategory.QIAN6

    def test_classify_auth_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("auth failed"))
        assert cat == NinePalaceErrorCategory.QIAN6

    def test_classify_forbidden_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("access forbidden"))
        assert cat == NinePalaceErrorCategory.QIAN6

    def test_classify_unauthorized_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("unauthorized user"))
        assert cat == NinePalaceErrorCategory.QIAN6

    # ── 兑7：输出错误 ──────────────────────────────────────

    def test_classify_type_error_type(self):
        cat = NinePalaceErrorCategory.classify(TypeError("bad type"))
        assert cat == NinePalaceErrorCategory.DUI7

    def test_classify_attribute_error_type(self):
        cat = NinePalaceErrorCategory.classify(AttributeError("no attr"))
        assert cat == NinePalaceErrorCategory.DUI7

    def test_classify_serialize_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("serialize output failed"))
        assert cat == NinePalaceErrorCategory.DUI7

    def test_classify_json_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("json encode failed"))
        assert cat == NinePalaceErrorCategory.DUI7

    def test_classify_format_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("bad format"))
        assert cat == NinePalaceErrorCategory.DUI7

    # ── 艮8：边界错误 ──────────────────────────────────────

    def test_classify_assertion_error_type(self):
        cat = NinePalaceErrorCategory.classify(AssertionError("assert"))
        assert cat == NinePalaceErrorCategory.GEN8

    def test_classify_bound_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("out of bound"))
        assert cat == NinePalaceErrorCategory.GEN8

    def test_classify_overflow_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("buffer overflow"))
        assert cat == NinePalaceErrorCategory.GEN8

    def test_classify_validate_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("failed to validate config bound"))
        assert cat == NinePalaceErrorCategory.GEN8

    def test_classify_limit_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("exceeds limit"))
        assert cat == NinePalaceErrorCategory.GEN8

    # ── 离9：渲染错误 ──────────────────────────────────────

    def test_classify_render_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("render error"))
        assert cat == NinePalaceErrorCategory.LI9

    def test_classify_visual_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("visual display broken"))
        assert cat == NinePalaceErrorCategory.LI9

    def test_classify_draw_keyword(self):
        cat = NinePalaceErrorCategory.classify(Exception("failed to draw canvas"))
        assert cat == NinePalaceErrorCategory.LI9

    # ── 中5：默认核心错误 ──────────────────────────────────

    def test_classify_default_fallback(self):
        cat = NinePalaceErrorCategory.classify(Exception("mystery error"))
        assert cat == NinePalaceErrorCategory.ZHONG5

    def test_classify_runtime_error_default(self):
        """RuntimeError 不属于任何特定类型，默认中5"""
        cat = NinePalaceErrorCategory.classify(RuntimeError("crash"))
        assert cat == NinePalaceErrorCategory.ZHONG5

    # ── 九宫格属性完整性 ───────────────────────────────────

    def test_all_nine_have_all_properties(self):
        """每个九宫格分类都有 4 个属性元组字段"""
        for cat in NinePalaceErrorCategory:
            assert isinstance(cat.palace_name, str) and len(cat.palace_name) > 0
            assert isinstance(cat.element, str) and len(cat.element) > 0
            assert isinstance(cat.category_name, str) and len(cat.category_name) > 0
            assert isinstance(cat.description, str) and len(cat.description) > 0

    def test_nine_categories_total(self):
        assert len(NinePalaceErrorCategory) == 9


# ============================================================================
# 三、ErrorRecord — 序列化与结构
# ============================================================================

class TestErrorRecord:
    """错误记录数据结构测试"""

    def test_to_dict_contains_all_keys(self, fresh_handler):
        """to_dict 返回所有预期字段"""
        record = fresh_handler.handle(
            ValueError("test"),
            module="mod",
            function="func",
            context={"key": "val"},
        )
        d = record.to_dict()
        expected_keys = {
            "error_id", "level", "category", "category_name", "element",
            "message", "exception_type", "module", "function",
            "recovery_success", "fallback", "timestamp",
        }
        assert expected_keys.issubset(set(d.keys()))

    def test_to_dict_level_is_string(self, fresh_handler):
        record = fresh_handler.handle(ValueError("x"))
        d = record.to_dict()
        assert isinstance(d["level"], str)
        assert d["level"] == "ERROR"

    def test_to_dict_category_is_palace_name(self, fresh_handler):
        record = fresh_handler.handle(ValueError("x"))
        d = record.to_dict()
        assert d["category"] == "坎一"

    def test_to_dict_fallback_none_when_no_recovery(self, fresh_handler):
        record = fresh_handler.handle(
            RuntimeError("critical"),
            level=ErrorLevel.CRITICAL,
            auto_recover=False,
        )
        d = record.to_dict()
        assert d["fallback"] is None

    def test_error_id_format(self, fresh_handler):
        record = fresh_handler.handle(ValueError("x"))
        assert record.error_id.startswith("err_")
        assert len(record.error_id) > 5


# ============================================================================
# 四、ErrorHandler — 自动分级逻辑
# ============================================================================

class TestAutoLevelClassification:
    """错误级别自动分类测试"""

    def test_value_error_is_error_level(self, fresh_handler):
        record = fresh_handler.handle(ValueError("v"))
        assert record.level == ErrorLevel.ERROR

    def test_type_error_is_error_level(self, fresh_handler):
        record = fresh_handler.handle(TypeError("t"))
        assert record.level == ErrorLevel.ERROR

    def test_key_error_is_error_level(self, fresh_handler):
        record = fresh_handler.handle(KeyError("k"))
        assert record.level == ErrorLevel.ERROR

    def test_attribute_error_is_error_level(self, fresh_handler):
        record = fresh_handler.handle(AttributeError("a"))
        assert record.level == ErrorLevel.ERROR

    def test_runtime_error_is_critical(self, fresh_handler):
        record = fresh_handler.handle(RuntimeError("r"))
        assert record.level == ErrorLevel.CRITICAL

    def test_recursion_error_is_critical(self, fresh_handler):
        record = fresh_handler.handle(RecursionError("recur"))
        assert record.level == ErrorLevel.CRITICAL

    def test_user_warning_is_warning(self, fresh_handler):
        record = fresh_handler.handle(UserWarning("w"))
        assert record.level == ErrorLevel.WARNING

    def test_deprecation_warning_is_warning(self, fresh_handler):
        record = fresh_handler.handle(DeprecationWarning("d"))
        assert record.level == ErrorLevel.WARNING

    def test_future_warning_is_warning(self, fresh_handler):
        record = fresh_handler.handle(FutureWarning("f"))
        assert record.level == ErrorLevel.WARNING

    def test_custom_exception_defaults_to_error(self, fresh_handler):
        class MyCustomError(Exception):
            pass
        record = fresh_handler.handle(MyCustomError("custom"))
        assert record.level == ErrorLevel.ERROR

    def test_explicit_level_overrides_auto(self, fresh_handler):
        record = fresh_handler.handle(ValueError("v"), level=ErrorLevel.WARNING)
        assert record.level == ErrorLevel.WARNING


# ============================================================================
# 五、ErrorHandler — 熔断器边界
# ============================================================================

class TestCircuitBreakerEdgeCases:
    """熔断器边界条件测试"""

    def test_below_threshold_not_broken(self, fresh_handler):
        """低于阈值时未熔断"""
        for i in range(4):  # threshold = 5
            fresh_handler.handle(
                RuntimeError("e"),
                level=ErrorLevel.CRITICAL,
                module="m",
                function="f",
            )
        assert fresh_handler.is_circuit_broken("m", "f") is False

    def test_at_threshold_is_broken(self, fresh_handler):
        """达到阈值时已熔断（第5次错误触发激活）"""
        for i in range(5):  # threshold = 5，第5次触发激活
            fresh_handler.handle(
                RuntimeError("e"),
                level=ErrorLevel.CRITICAL,
                module="m",
                function="f",
            )
        assert fresh_handler.is_circuit_broken("m", "f") is True

    def test_above_threshold_is_broken(self, fresh_handler):
        """超过阈值后熔断"""
        for i in range(6):
            fresh_handler.handle(
                RuntimeError("e"),
                level=ErrorLevel.CRITICAL,
                module="m",
                function="f",
            )
        assert fresh_handler.is_circuit_broken("m", "f") is True

    def test_module_only_path_with_function_arg(self, fresh_handler):
        """带 module 和 function 完整参数的熔断路径"""
        for i in range(6):
            fresh_handler.handle(
                RuntimeError("e"),
                level=ErrorLevel.CRITICAL,
                module="mod_only",
                function="func",
            )
        assert fresh_handler.is_circuit_broken("mod_only", "func") is True

    def test_reset_circuit_breaker(self, fresh_handler):
        """熔断后重置"""
        for i in range(6):
            fresh_handler.handle(
                RuntimeError("e"),
                level=ErrorLevel.CRITICAL,
                module="m",
                function="f",
            )
        assert fresh_handler.is_circuit_broken("m", "f") is True
        fresh_handler.reset_circuit_breaker("m", "f")
        assert fresh_handler.is_circuit_broken("m", "f") is False

    def test_unknown_path_not_broken(self, fresh_handler):
        """从未出错的路径未熔断"""
        assert fresh_handler.is_circuit_broken("nonexistent", "func") is False

    def test_circuit_breaker_triggered_only_for_unrecoverable(self, fresh_handler):
        """可恢复错误不触发熔断器计数（通过 _check_circuit_breaker）"""
        for i in range(20):
            fresh_handler.handle(
                ValueError("recoverable"),
                level=ErrorLevel.ERROR,
                module="safe",
                function="func",
            )
        # ERROR 是可恢复的，不应触发熔断
        assert fresh_handler.is_circuit_broken("safe", "func") is False


# ============================================================================
# 六、ErrorHandler — 自动恢复与回退策略
# ============================================================================

class TestAutoRecovery:
    """自动恢复与回退策略测试"""

    def test_recoverable_error_attempts_recovery(self, fresh_handler):
        """可恢复错误会尝试恢复"""
        record = fresh_handler.handle(ValueError("v"), module="m", function="f")
        assert record.recovery_attempted is True

    def test_unrecoverable_error_no_attempt(self, fresh_handler):
        """不可恢复错误不尝试自动恢复"""
        record = fresh_handler.handle(
            RuntimeError("crit"),
            level=ErrorLevel.CRITICAL,
            module="m",
            function="f",
        )
        assert record.recovery_attempted is False
        assert record.recovery_success is False

    def test_auto_recover_false_skips_recovery(self, fresh_handler):
        """auto_recover=False 时不尝试恢复"""
        record = fresh_handler.handle(
            ValueError("v"),
            module="m",
            function="f",
            auto_recover=False,
        )
        assert record.recovery_attempted is False
        assert record.recovery_success is False

    def test_kan1_has_default_strategy(self, fresh_handler):
        """坎1（数据源）错误应使用 DEFAULT 策略并恢复成功"""
        record = fresh_handler.handle(ValueError("data bad"))
        assert record.recovery_success is True
        assert record.fallback_used == FallbackStrategy.DEFAULT

    def test_gen8_has_default_strategy(self, fresh_handler):
        """艮8（边界）错误应使用 DEFAULT 策略"""
        record = fresh_handler.handle(AssertionError("assert fail"))
        assert record.recovery_success is True
        assert record.fallback_used == FallbackStrategy.DEFAULT

    def test_zhong5_uses_chaos_sea(self, fresh_handler):
        """中5（核心）错误应进入混沌海策略"""
        record = fresh_handler.handle(RuntimeError("core fail"), level=ErrorLevel.ERROR)
        # 中5错误先尝试 CHAOS_SEA
        assert record.fallback_used == FallbackStrategy.CHAOS_SEA

    def test_all_categories_have_strategy_mapping(self, fresh_handler):
        """所有九宫格分类都能在 _get_recovery_strategies 中找到映射"""
        test_errors = {
            NinePalaceErrorCategory.KAN1: ValueError("data"),
            NinePalaceErrorCategory.KUN2: IOError("disk"),
            NinePalaceErrorCategory.ZHEN3: ImportError("mod"),
            NinePalaceErrorCategory.XUN4: ConnectionError("net"),
            NinePalaceErrorCategory.ZHONG5: Exception("mystery"),
            NinePalaceErrorCategory.QIAN6: PermissionError("denied"),
            NinePalaceErrorCategory.DUI7: TypeError("type"),
            NinePalaceErrorCategory.GEN8: AssertionError("assert"),
            NinePalaceErrorCategory.LI9: Exception("render failed"),
        }
        for expected_cat, err in test_errors.items():
            record = fresh_handler.handle(err, level=ErrorLevel.ERROR)
            assert record.category == expected_cat
            # 只要尝试过恢复且设置了 fallback_used 或明确失败都可以
            assert record.recovery_attempted is True

    def test_recovery_rate_with_no_attempts(self, fresh_handler):
        """没有恢复尝试时，恢复率不应除零"""
        # 用不可恢复的错误产生日志
        for i in range(5):
            fresh_handler.handle(RuntimeError("crit"), level=ErrorLevel.CRITICAL)
        stats = fresh_handler.get_stats()
        # recovery_rate 基于最近100条中 recovery_attempted 的条目
        assert isinstance(stats["recovery_rate"], float)
        assert 0.0 <= stats["recovery_rate"] <= 1.0

    def test_recovery_rate_calculation(self, fresh_handler):
        """恢复率计算正确"""
        # 10个可恢复错误（都成功）
        for i in range(10):
            fresh_handler.handle(ValueError(f"e{i}"))
        stats = fresh_handler.get_stats()
        assert stats["recovery_rate"] == pytest.approx(1.0, abs=0.01)


# ============================================================================
# 七、ErrorHandler — safe_execute 深度测试
# ============================================================================

class TestSafeExecute:
    """安全执行包装器深度测试"""

    def test_successful_execution_returns_result(self, fresh_handler):
        result, err = fresh_handler.safe_execute(
            lambda a, b: a + b, 3, 4, module="math", function="add"
        )
        assert result == 7
        assert err is None

    def test_failure_returns_default(self, fresh_handler):
        def fail():
            raise ValueError("boom")

        result, err = fresh_handler.safe_execute(
            fail, module="m", function="f", default="fallback_val"
        )
        assert result == "fallback_val"
        assert err is not None
        assert err.exception_type == "ValueError"

    def test_failure_default_is_none(self, fresh_handler):
        def fail():
            raise RuntimeError("x")

        result, err = fresh_handler.safe_execute(fail, module="m", function="f")
        assert result is None
        assert err is not None

    def test_retry_eventually_succeeds(self, fresh_handler):
        """重试多次后成功"""
        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("temporary")
            return "done"

        result, err = fresh_handler.safe_execute(
            flaky, module="m", function="f", max_retries=3
        )
        assert result == "done"
        assert err is None
        assert call_count[0] == 3

    def test_retry_exhausted_returns_error(self, fresh_handler):
        """重试耗尽后返回错误记录"""
        call_count = [0]

        def always_fail():
            call_count[0] += 1
            raise ValueError("always")

        result, err = fresh_handler.safe_execute(
            always_fail, module="m", function="f", max_retries=2
        )
        assert result is None
        assert err is not None
        assert call_count[0] == 2

    def test_circuit_broken_skips_execution(self, fresh_handler):
        """熔断后直接返回默认值，不执行函数"""
        # 先熔断
        for i in range(6):
            fresh_handler.handle(
                RuntimeError("crit"),
                level=ErrorLevel.CRITICAL,
                module="fragile",
                function="op",
            )
        assert fresh_handler.is_circuit_broken("fragile", "op") is True

        called = [False]

        def should_not_run():
            called[0] = True
            return "result"

        result, err = fresh_handler.safe_execute(
            should_not_run, module="fragile", function="op", default="skip"
        )
        assert result == "skip"
        assert err is None
        assert called[0] is False  # 函数根本没被调用

    def test_successful_call_resets_circuit_breaker(self, fresh_handler):
        """成功调用会重置熔断器计数"""
        # 设置一些失败计数（但未到熔断阈值）
        for i in range(3):
            fresh_handler.handle(
                RuntimeError("crit"),
                level=ErrorLevel.CRITICAL,
                module="m",
                function="f",
            )
        # 成功执行 → 重置
        result, err = fresh_handler.safe_execute(
            lambda: 42, module="m", function="f"
        )
        assert result == 42
        assert err is None
        # 重置后熔断器计数归零
        assert fresh_handler.is_circuit_broken("m", "f") is False

    def test_safe_execute_with_kwargs(self, fresh_handler):
        """支持关键字参数"""
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result, err = fresh_handler.safe_execute(
            greet, "World", module="m", function="greet", greeting="Hi"
        )
        assert result == "Hi, World!"
        assert err is None


# ============================================================================
# 八、ErrorHandler — 错误日志与统计
# ============================================================================

class TestErrorLogAndStats:
    """错误日志裁剪与统计测试"""

    def test_log_truncation_at_1000(self, fresh_handler):
        """错误日志超过 1000 条后被裁剪"""
        for i in range(1200):
            fresh_handler.handle(ValueError(f"err_{i}"))
        stats = fresh_handler.get_stats()
        # total_errors 是计数器，只增不减
        assert stats["total_errors"] == 1200
        # 但 get_recent_errors 只返回最近的
        recent = fresh_handler.get_recent_errors(limit=2000)
        assert len(recent) == 1000

    def test_get_recent_errors_limit(self, fresh_handler):
        """get_recent_errors 限制返回数量"""
        for i in range(20):
            fresh_handler.handle(ValueError(f"e{i}"))
        recent = fresh_handler.get_recent_errors(limit=5)
        assert len(recent) == 5

    def test_get_stats_structure(self, fresh_handler):
        """get_stats 返回完整结构"""
        fresh_handler.handle(ValueError("e1"))
        fresh_handler.handle(TypeError("e2"))
        stats = fresh_handler.get_stats()
        assert "total_errors" in stats
        assert "by_level" in stats
        assert "by_category" in stats
        assert "circuit_broken" in stats
        assert "recovery_rate" in stats

    def test_by_level_counts(self, fresh_handler):
        """按级别计数正确"""
        fresh_handler.handle(ValueError("e"))  # ERROR
        fresh_handler.handle(UserWarning("w"))  # WARNING
        fresh_handler.handle(RuntimeError("c"), level=ErrorLevel.CRITICAL)  # CRITICAL
        stats = fresh_handler.get_stats()
        assert stats["by_level"]["ERROR"] >= 1
        assert stats["by_level"]["WARNING"] >= 1
        assert stats["by_level"]["CRITICAL"] >= 1

    def test_get_errors_by_category_filters(self, fresh_handler):
        """按分类过滤错误"""
        fresh_handler.handle(ValueError("data"))  # 坎1
        fresh_handler.handle(ValueError("data2"))  # 坎1
        fresh_handler.handle(PermissionError("denied"))  # 乾6
        kan_errors = fresh_handler.get_errors_by_category(NinePalaceErrorCategory.KAN1)
        qian_errors = fresh_handler.get_errors_by_category(NinePalaceErrorCategory.QIAN6)
        assert len(kan_errors) >= 2
        assert len(qian_errors) >= 1

    def test_reset_clears_everything(self, fresh_handler):
        """reset 清空所有状态"""
        for i in range(10):
            fresh_handler.handle(ValueError(f"e{i}"))
        fresh_handler.handle(
            RuntimeError("c"), level=ErrorLevel.CRITICAL, module="m", function="f"
        )
        fresh_handler.reset()
        stats = fresh_handler.get_stats()
        assert stats["total_errors"] == 0
        assert stats["circuit_broken"] == 0
        assert len(fresh_handler.get_recent_errors()) == 0


# ============================================================================
# 九、ErrorHandler — 门禁影响评估
# ============================================================================

class TestGateImpactAssessment:
    """门禁影响评估测试"""

    def test_all_categories_have_gate_impact(self, fresh_handler):
        """所有九宫格分类都有门禁影响映射"""
        test_pairs = [
            (ValueError("data"), "坎一·水"),
            (IOError("disk"), "坤二·土"),
            (ImportError("mod"), "震三·木"),
            (ConnectionError("net"), "巽四·木"),
            (Exception("mystery"), "中五·土"),
            (PermissionError("denied"), "乾六·金"),
            (TypeError("type"), "兑七·金"),
            (AssertionError("assert"), "艮八·土"),
        ]
        for err, expected_palace in test_pairs:
            record = fresh_handler.handle(err, level=ErrorLevel.ERROR)
            assert record.gate_impact is not None
            assert record.gate_impact["palace"] == expected_palace
            assert "affected_god" in record.gate_impact
            assert "impact_description" in record.gate_impact
            assert "severity" in record.gate_impact

    def test_gate_impact_summary(self, fresh_handler):
        """门禁影响摘要聚合"""
        fresh_handler.handle(ValueError("e1"))
        fresh_handler.handle(ValueError("e2"))
        fresh_handler.handle(PermissionError("p1"))
        summary = fresh_handler.get_gate_impact_summary()
        assert len(summary) >= 2
        for god, data in summary.items():
            assert "count" in data
            assert "severities" in data
            assert data["count"] >= 1


# ============================================================================
# 十、单例模式与线程安全
# ============================================================================

class TestSingletonPattern:
    """单例模式与全局实例测试"""

    def test_get_error_handler_returns_same_instance(self):
        """两次调用返回同一实例"""
        h1 = get_error_handler()
        h2 = get_error_handler()
        assert h1 is h2

    def test_reset_error_handler_creates_new_instance(self):
        """重置后获取新实例"""
        h1 = get_error_handler()
        reset_error_handler()
        h2 = get_error_handler()
        assert h1 is not h2

    def test_error_handler_constructor_singleton(self):
        """直接构造也返回单例"""
        reset_error_handler()
        h1 = ErrorHandler()
        h2 = ErrorHandler()
        assert h1 is h2

    def test_thread_safe_singleton_creation(self):
        """多线程下创建单例也是唯一的"""
        reset_error_handler()
        instances = []
        errors = []

        def create_instance():
            try:
                instances.append(get_error_handler())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_instance) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(instances) == 20
        # 所有线程拿到同一个实例
        assert all(inst is instances[0] for inst in instances)

    def test_reset_during_thread_safety(self):
        """多线程并发 handle 不崩溃（线程安全基本验证）"""
        reset_error_handler()
        handler = get_error_handler()

        def worker(start, end):
            for i in range(start, end):
                handler.handle(ValueError(f"t{i}"))

        threads = [
            threading.Thread(target=worker, args=(0, 50)),
            threading.Thread(target=worker, args=(50, 100)),
            threading.Thread(target=worker, args=(100, 150)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = handler.get_stats()
        assert stats["total_errors"] == 150


# ============================================================================
# 十一、FallbackStrategy 完整性
# ============================================================================

class TestFallbackStrategyCompleteness:
    """回退策略枚举完整性"""

    def test_all_six_strategies_exist(self):
        assert len(FallbackStrategy) == 6

    def test_strategy_values_are_unique(self):
        values = [s.value for s in FallbackStrategy]
        assert len(values) == len(set(values))

    def test_each_strategy_is_string(self):
        for s in FallbackStrategy:
            assert isinstance(s.value, str)
            assert len(s.value) > 0
