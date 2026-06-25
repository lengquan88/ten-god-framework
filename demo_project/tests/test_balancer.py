"""
太极_阴阳调和 balancer 模块测试
"""

import time
from unittest.mock import MagicMock

import pytest

from tengod.太极_阴阳调和.balancer import StateTransition, TaiChiBalancer, YinYang


# ── YinYang 枚举 ──────────────────────────────────────────────────────────


class TestYinYang:
    """YinYang 枚举测试"""

    def test_yin_value(self):
        assert YinYang.YIN.value == "yin"

    def test_yang_value(self):
        assert YinYang.YANG.value == "yang"

    def test_balanced_value(self):
        assert YinYang.BALANCED.value == "balanced"

    def test_enum_members(self):
        members = list(YinYang)
        assert len(members) == 3
        assert YinYang.YIN in members
        assert YinYang.YANG in members
        assert YinYang.BALANCED in members

    def test_enum_comparison(self):
        assert YinYang.YIN == YinYang.YIN
        assert YinYang.YIN != YinYang.YANG
        assert YinYang.YIN != YinYang.BALANCED


# ── StateTransition dataclass ──────────────────────────────────────────────


class TestStateTransition:
    """StateTransition 数据类测试"""

    def test_creation(self):
        st = StateTransition(
            from_state=YinYang.YIN,
            to_state=YinYang.YANG,
            reason="toggle",
        )
        assert st.from_state == YinYang.YIN
        assert st.to_state == YinYang.YANG
        assert st.reason == "toggle"
        assert isinstance(st.timestamp, float)

    def test_timestamp_default(self):
        st = StateTransition(
            from_state=YinYang.BALANCED,
            to_state=YinYang.YIN,
            reason="test",
        )
        assert st.timestamp > 0
        assert abs(st.timestamp - time.time()) < 1.0

    def test_timestamp_custom(self):
        custom_ts = 1234567890.0
        st = StateTransition(
            from_state=YinYang.YANG,
            to_state=YinYang.BALANCED,
            reason="balance",
            timestamp=custom_ts,
        )
        assert st.timestamp == custom_ts

    def test_equality(self):
        ts = time.time()
        st1 = StateTransition(YinYang.YIN, YinYang.YANG, "r", ts)
        st2 = StateTransition(YinYang.YIN, YinYang.YANG, "r", ts)
        assert st1 == st2

    def test_inequality(self):
        st1 = StateTransition(YinYang.YIN, YinYang.YANG, "r1")
        st2 = StateTransition(YinYang.YIN, YinYang.BALANCED, "r2")
        assert st1 != st2


# ── TaiChiBalancer ─────────────────────────────────────────────────────────


class TestTaiChiBalancerInit:
    """TaiChiBalancer 初始化测试"""

    def test_default_initial_state(self):
        balancer = TaiChiBalancer()
        assert balancer.get_state() == YinYang.BALANCED

    def test_custom_initial_state_yin(self):
        balancer = TaiChiBalancer(initial_state=YinYang.YIN)
        assert balancer.get_state() == YinYang.YIN

    def test_custom_initial_state_yang(self):
        balancer = TaiChiBalancer(initial_state=YinYang.YANG)
        assert balancer.get_state() == YinYang.YANG


class TestTaiChiBalancerGetSetState:
    """get_state / set_state 测试"""

    def test_get_state_after_init(self):
        balancer = TaiChiBalancer()
        assert balancer.get_state() == YinYang.BALANCED

    def test_set_state_changes_state(self):
        balancer = TaiChiBalancer()
        result = balancer.set_state(YinYang.YIN, "test")
        assert result == YinYang.YIN
        assert balancer.get_state() == YinYang.YIN

    def test_set_state_records_history(self):
        balancer = TaiChiBalancer()
        balancer.set_state(YinYang.YANG, "go active")
        history = balancer.get_history()
        assert len(history) == 1
        assert history[0]["from"] == "balanced"
        assert history[0]["to"] == "yang"
        assert history[0]["reason"] == "go active"

    def test_set_state_fires_callback(self):
        balancer = TaiChiBalancer()
        callback = MagicMock()
        balancer.register_callback(YinYang.YIN, callback)
        balancer.set_state(YinYang.YIN, "test")
        callback.assert_called_once_with(YinYang.BALANCED, YinYang.YIN)

    def test_set_state_returns_new_state(self):
        balancer = TaiChiBalancer()
        result = balancer.set_state(YinYang.BALANCED, "stay")
        assert result == YinYang.BALANCED


class TestTaiChiBalancerToggle:
    """toggle() 测试"""

    def test_toggle_from_yin_to_yang(self):
        balancer = TaiChiBalancer(initial_state=YinYang.YIN)
        result = balancer.toggle("flip")
        assert result == YinYang.YANG
        assert balancer.get_state() == YinYang.YANG

    def test_toggle_from_yang_to_yin(self):
        balancer = TaiChiBalancer(initial_state=YinYang.YANG)
        result = balancer.toggle("flip")
        assert result == YinYang.YIN
        assert balancer.get_state() == YinYang.YIN

    def test_toggle_from_balanced_to_yang(self):
        balancer = TaiChiBalancer(initial_state=YinYang.BALANCED)
        result = balancer.toggle("flip")
        assert result == YinYang.YANG
        assert balancer.get_state() == YinYang.YANG

    def test_toggle_records_history(self):
        balancer = TaiChiBalancer(initial_state=YinYang.YIN)
        balancer.toggle("flip")
        history = balancer.get_history()
        assert len(history) == 1
        assert history[0]["from"] == "yin"
        assert history[0]["to"] == "yang"


class TestTaiChiBalancerBalance:
    """balance() 测试"""

    def test_balance_from_yin(self):
        balancer = TaiChiBalancer(initial_state=YinYang.YIN)
        result = balancer.balance("calm down")
        assert result == YinYang.BALANCED
        assert balancer.get_state() == YinYang.BALANCED

    def test_balance_from_yang(self):
        balancer = TaiChiBalancer(initial_state=YinYang.YANG)
        result = balancer.balance("calm down")
        assert result == YinYang.BALANCED

    def test_balance_from_balanced(self):
        balancer = TaiChiBalancer(initial_state=YinYang.BALANCED)
        result = balancer.balance("stay")
        assert result == YinYang.BALANCED

    def test_balance_records_history(self):
        balancer = TaiChiBalancer(initial_state=YinYang.YANG)
        balancer.balance("restore")
        history = balancer.get_history()
        assert len(history) == 1
        assert history[0]["to"] == "balanced"


class TestTaiChiBalancerEvaluate:
    """evaluate() 测试"""

    def test_evaluate_low_metrics_to_yin(self):
        balancer = TaiChiBalancer()
        result = balancer.evaluate({"cpu": 0.1})
        assert result == YinYang.YIN
        assert balancer.get_state() == YinYang.YIN

    def test_evaluate_high_metrics_to_yang(self):
        balancer = TaiChiBalancer()
        result = balancer.evaluate({"cpu": 0.9})
        assert result == YinYang.YANG
        assert balancer.get_state() == YinYang.YANG

    def test_evaluate_balanced_metrics(self):
        balancer = TaiChiBalancer()
        result = balancer.evaluate({"cpu": 0.5})
        assert result == YinYang.BALANCED
        assert balancer.get_state() == YinYang.BALANCED

    def test_evaluate_empty_metrics(self):
        balancer = TaiChiBalancer()
        result = balancer.evaluate({})
        assert result == YinYang.YIN
        assert balancer.get_state() == YinYang.YIN

    def test_evaluate_multiple_metrics(self):
        balancer = TaiChiBalancer()
        result = balancer.evaluate({"cpu": 0.5, "memory": 0.4})
        assert result == YinYang.YANG  # 0.5+0.4=0.9 > 0.7
        assert balancer.get_state() == YinYang.YANG

    def test_evaluate_at_yang_threshold(self):
        """sum = 0.7 — 不 > 0.7，落入 balanced 分支"""
        balancer = TaiChiBalancer()
        result = balancer.evaluate({"cpu": 0.7})
        assert result == YinYang.BALANCED

    def test_evaluate_at_yin_threshold(self):
        """sum = 0.3 — 不 < 0.3，落入 balanced 分支"""
        balancer = TaiChiBalancer()
        result = balancer.evaluate({"cpu": 0.3})
        assert result == YinYang.BALANCED


class TestTaiChiBalancerRegisterCallback:
    """register_callback() 测试"""

    def test_register_callback_called_on_state_change(self):
        balancer = TaiChiBalancer()
        callback = MagicMock()
        balancer.register_callback(YinYang.YANG, callback)
        balancer.set_state(YinYang.YANG, "go")
        callback.assert_called_once_with(YinYang.BALANCED, YinYang.YANG)

    def test_register_callback_for_yin(self):
        balancer = TaiChiBalancer()
        callback = MagicMock()
        balancer.register_callback(YinYang.YIN, callback)
        balancer.set_state(YinYang.YIN, "to yin")
        callback.assert_called_once()

    def test_register_callback_for_balanced(self):
        balancer = TaiChiBalancer(initial_state=YinYang.YIN)
        callback = MagicMock()
        balancer.register_callback(YinYang.BALANCED, callback)
        balancer.set_state(YinYang.BALANCED, "to balanced")
        callback.assert_called_once()

    def test_register_multiple_callbacks(self):
        balancer = TaiChiBalancer()
        cb1 = MagicMock()
        cb2 = MagicMock()
        balancer.register_callback(YinYang.YANG, cb1)
        balancer.register_callback(YinYang.YANG, cb2)
        balancer.set_state(YinYang.YANG, "go")
        cb1.assert_called_once()
        cb2.assert_called_once()

    def test_callback_not_called_for_other_state(self):
        balancer = TaiChiBalancer()
        callback = MagicMock()
        balancer.register_callback(YinYang.YIN, callback)
        balancer.set_state(YinYang.YANG, "go")
        callback.assert_not_called()


class TestTaiChiBalancerGetHistory:
    """get_history() 测试"""

    def test_get_history_default_limit(self):
        balancer = TaiChiBalancer()
        for i in range(12):
            balancer.toggle(f"toggle {i}")
        history = balancer.get_history()
        assert len(history) == 10  # default limit

    def test_get_history_custom_limit(self):
        balancer = TaiChiBalancer()
        for i in range(10):
            balancer.toggle(f"toggle {i}")
        history = balancer.get_history(limit=5)
        assert len(history) == 5

    def test_get_history_limit_larger_than_history(self):
        balancer = TaiChiBalancer()
        balancer.toggle("t1")
        balancer.toggle("t2")
        history = balancer.get_history(limit=100)
        assert len(history) == 2

    def test_get_history_empty(self):
        balancer = TaiChiBalancer()
        history = balancer.get_history()
        assert len(history) == 0
        assert isinstance(history, list)

    def test_get_history_returns_latest_entries(self):
        balancer = TaiChiBalancer()
        balancer.set_state(YinYang.YIN, "first")
        balancer.set_state(YinYang.YANG, "second")
        balancer.set_state(YinYang.BALANCED, "third")
        history = balancer.get_history(limit=2)
        assert len(history) == 2
        assert history[0]["reason"] == "second"
        assert history[1]["reason"] == "third"

    def test_get_history_format(self):
        balancer = TaiChiBalancer()
        balancer.set_state(YinYang.YANG, "test")
        history = balancer.get_history()
        assert "from" in history[0]
        assert "to" in history[0]
        assert "reason" in history[0]
        assert "timestamp" in history[0]
        assert history[0]["from"] == "balanced"
        assert history[0]["to"] == "yang"


class TestTaiChiBalancerStats:
    """stats() 测试"""

    def test_stats_initial(self):
        balancer = TaiChiBalancer()
        stats = balancer.stats()
        assert stats["current_state"] == "balanced"
        assert stats["state"] == YinYang.BALANCED
        assert stats["transitions"] == 0
        assert stats["yin_count"] == 0
        assert stats["yang_count"] == 0
        assert stats["balanced_count"] == 0

    def test_stats_after_state_changes(self):
        balancer = TaiChiBalancer()
        balancer.set_state(YinYang.YIN, "to yin")
        balancer.set_state(YinYang.YANG, "to yang")
        balancer.set_state(YinYang.BALANCED, "to balanced")
        stats = balancer.stats()
        assert stats["transitions"] == 3
        assert stats["yin_count"] == 1
        assert stats["yang_count"] == 1
        assert stats["balanced_count"] == 1
        assert stats["current_state"] == "balanced"

    def test_stats_counts_yin_correctly(self):
        balancer = TaiChiBalancer()
        balancer.set_state(YinYang.YIN, "1")
        balancer.set_state(YinYang.YIN, "2")
        balancer.set_state(YinYang.YIN, "3")
        stats = balancer.stats()
        assert stats["yin_count"] == 3
        assert stats["yang_count"] == 0
        assert stats["balanced_count"] == 0

    def test_stats_counts_yang_correctly(self):
        balancer = TaiChiBalancer()
        balancer.set_state(YinYang.YANG, "1")
        balancer.set_state(YinYang.YANG, "2")
        stats = balancer.stats()
        assert stats["yang_count"] == 2
        assert stats["yin_count"] == 0

    def test_stats_counts_balanced_correctly(self):
        balancer = TaiChiBalancer()
        balancer.set_state(YinYang.BALANCED, "1")
        balancer.set_state(YinYang.BALANCED, "2")
        balancer.set_state(YinYang.BALANCED, "3")
        balancer.set_state(YinYang.BALANCED, "4")
        stats = balancer.stats()
        assert stats["balanced_count"] == 4
        assert stats["transitions"] == 4


class TestTaiChiBalancerAutoBalance:
    """auto_balance() 测试"""

    def test_auto_balance_cpu_over_threshold(self):
        balancer = TaiChiBalancer()
        result = balancer.auto_balance({"cpu": 0.9})
        assert result["degraded"] is True
        assert "cpu过高" in result["reason"]
        assert any("cpu" in r for r in result["recommendations"])

    def test_auto_balance_memory_over_threshold(self):
        balancer = TaiChiBalancer()
        result = balancer.auto_balance({"memory": 0.95})
        assert result["degraded"] is True
        assert "memory过高" in result["reason"]

    def test_auto_balance_error_rate_over_threshold(self):
        balancer = TaiChiBalancer()
        result = balancer.auto_balance({"error_rate": 0.5})
        assert result["degraded"] is True
        assert "error_rate过高" in result["reason"]

    def test_auto_balance_normal_metrics(self):
        balancer = TaiChiBalancer()
        result = balancer.auto_balance({"cpu": 0.3, "memory": 0.4})
        assert result["degraded"] is False
        assert "系统运行平稳" in result["reason"] or "保持当前状态" in result["recommendations"]

    def test_auto_balance_triggers_degradation_handler(self):
        balancer = TaiChiBalancer()
        handler = MagicMock()
        balancer.set_degradation_handler(handler)
        balancer.auto_balance({"cpu": 0.9})
        handler.assert_called_once()

    def test_auto_balance_degradation_handler_exception(self):
        balancer = TaiChiBalancer()

        def failing_handler(result):
            raise RuntimeError("handler crash")

        balancer.set_degradation_handler(failing_handler)
        # Should not raise — caught gracefully
        result = balancer.auto_balance({"cpu": 0.9})
        assert result["degraded"] is True

    def test_auto_balance_empty_metrics(self):
        balancer = TaiChiBalancer()
        result = balancer.auto_balance({})
        assert result["degraded"] is False
        assert "state" in result
        assert "score" in result
        assert "recommendations" in result

    def test_auto_balance_all_metrics_at_threshold(self):
        """cpu=0.85, memory=0.9, error_rate=0.1 — 刚好在阈值，不触发降级"""
        balancer = TaiChiBalancer()
        result = balancer.auto_balance({"cpu": 0.85, "memory": 0.9, "error_rate": 0.1})
        assert result["degraded"] is False

    def test_auto_balance_multiple_degraded(self):
        balancer = TaiChiBalancer()
        result = balancer.auto_balance({"cpu": 0.95, "memory": 0.95, "error_rate": 0.5})
        assert result["degraded"] is True
        assert len(result["recommendations"]) >= 1

    def test_auto_balance_no_handler_set(self):
        """auto_balance 在未设置 degradation_handler 时不崩溃"""
        balancer = TaiChiBalancer()
        result = balancer.auto_balance({"cpu": 0.95})
        assert result["degraded"] is True

    def test_auto_balance_return_structure(self):
        balancer = TaiChiBalancer()
        result = balancer.auto_balance({"cpu": 0.5})
        assert "state" in result
        assert "score" in result
        assert "degraded" in result
        assert "reason" in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)


class TestTaiChiBalancerDegradationHandler:
    """降级处理器相关测试"""

    def test_set_degradation_handler(self):
        balancer = TaiChiBalancer()
        handler = MagicMock()
        balancer.set_degradation_handler(handler)
        assert balancer._degradation_handler is handler

    def test_set_degradation_handler_none(self):
        balancer = TaiChiBalancer()
        balancer.set_degradation_handler(None)
        assert balancer._degradation_handler is None


class TestTaiChiBalancerDegradedMode:
    """降级模式 进入/退出 测试"""

    def test_enter_degraded_mode_sets_yin(self):
        balancer = TaiChiBalancer()
        balancer.enter_degraded_mode("CPU过载")
        assert balancer.get_state() == YinYang.YIN

    def test_enter_degraded_mode_with_reason(self):
        balancer = TaiChiBalancer()
        balancer.enter_degraded_mode("CPU过载")
        history = balancer.get_history()
        assert len(history) == 1
        assert "[降级]CPU过载" in history[0]["reason"]

    def test_enter_degraded_mode_default_reason(self):
        balancer = TaiChiBalancer()
        balancer.enter_degraded_mode()
        history = balancer.get_history()
        assert "[降级]系统负载过高" in history[0]["reason"]

    def test_exit_degraded_mode_sets_yang(self):
        balancer = TaiChiBalancer()
        balancer.exit_degraded_mode("系统恢复")
        assert balancer.get_state() == YinYang.YANG

    def test_exit_degraded_mode_with_reason(self):
        balancer = TaiChiBalancer()
        balancer.exit_degraded_mode("系统恢复")
        history = balancer.get_history()
        assert "[恢复]系统恢复" in history[0]["reason"]

    def test_exit_degraded_mode_default_reason(self):
        balancer = TaiChiBalancer()
        balancer.exit_degraded_mode()
        history = balancer.get_history()
        assert "[恢复]系统已稳定" in history[0]["reason"]


class TestTaiChiBalancerEdgeCases:
    """边界情况测试"""

    def test_multiple_rapid_state_changes(self):
        balancer = TaiChiBalancer()
        for i in range(100):
            balancer.toggle(f"rapid {i}")
        history = balancer.get_history(limit=200)
        assert len(history) == 100
        # 最终状态：BALANCED→YANG(1)→YIN(2)→YANG(3)... 偶数次 toggle 后为 YIN
        # 从 BALANCED 开始 toggle: BALANCED→YANG(1), YANG→YIN(2), YIN→YANG(3)...
        # 100 次 toggle: 100%2=0 余 0, so 100 is even → YIN
        assert balancer.get_state() == YinYang.YIN

    def test_callback_modifies_state(self):
        """回调函数修改状态不会导致崩溃"""
        balancer = TaiChiBalancer()

        def callback(old_state, new_state):
            # 回调中再次修改状态（设置不同状态避免递归）
            if new_state == YinYang.YANG:
                balancer.set_state(YinYang.BALANCED, "callback override")

        balancer.register_callback(YinYang.YANG, callback)
        balancer.set_state(YinYang.YANG, "test")
        # 不应崩溃；最终状态取决于回调执行顺序
        # 无论如何，不应有异常
        assert balancer.get_state() in (YinYang.YANG, YinYang.BALANCED)

    def test_set_state_empty_reason(self):
        balancer = TaiChiBalancer()
        balancer.set_state(YinYang.YIN, "")
        history = balancer.get_history()
        assert history[0]["reason"] == ""

    def test_toggle_empty_reason(self):
        balancer = TaiChiBalancer()
        balancer.toggle()
        history = balancer.get_history()
        assert history[0]["reason"] == ""

    def test_balance_empty_reason(self):
        balancer = TaiChiBalancer()
        balancer.balance()
        history = balancer.get_history()
        assert history[0]["reason"] == ""

    def test_get_history_zero_limit(self):
        """limit=0 时 Python list[-0:] 等同于 list[0:]，返回全部"""
        balancer = TaiChiBalancer()
        balancer.toggle("t1")
        balancer.toggle("t2")
        history = balancer.get_history(limit=0)
        assert len(history) == 2

    def test_auto_balance_with_yin_state(self):
        """auto_balance 在阴态下的行为"""
        balancer = TaiChiBalancer()
        result = balancer.auto_balance({"cpu": 0.1})
        assert "当前为阴态" in result["reason"]

    def test_auto_balance_with_yang_state(self):
        """auto_balance 在阳态下的行为"""
        balancer = TaiChiBalancer()
        result = balancer.auto_balance({"cpu": 0.9, "memory": 0.5})
        # cpu=0.9 > 0.85 → degraded
        assert result["degraded"] is True
        assert "当前为阳态" in result["reason"] or "当前为阴态" in result["reason"]

    def test_degradation_handler_receives_result(self):
        balancer = TaiChiBalancer()
        received = []

        def handler(result):
            received.append(result)

        balancer.set_degradation_handler(handler)
        result = balancer.auto_balance({"cpu": 0.95})
        assert len(received) == 1
        assert received[0] is result
        assert received[0]["degraded"] is True