"""
天眼门禁模块 (tiangan_gate.py) 综合测试
=========================================
覆盖：ZhizhiVerdict, TianmenGate, ZhizhiEngine, TianmenGuard, get_tianmen()
目标：95%+ 代码覆盖率
"""
import pytest
import math
import time
from unittest.mock import patch

from tengod.tiangan_gate import (
    ZhizhiVerdict,
    TianmenGate,
    ZhizhiEngine,
    TianmenGuard,
    get_tianmen,
)


# ============================================================================
# 1. ZhizhiVerdict 数据类测试
# ============================================================================

class TestZhizhiVerdict:
    """ZhizhiVerdict 数据类测试"""

    def test_create_with_all_fields(self):
        """创建包含所有字段的 ZhizhiVerdict"""
        v = ZhizhiVerdict(
            passed=True,
            confidence=0.85,
            entropies={"dim1": 0.2, "dim2": 0.3},
            variance=0.05,
            threshold_level=0.6,
            should_retreat=False,
            retreat_reason="",
            cultivation_qi=0.72,
            timestamp=1234567890.0,
            inner_child_phi=0.15,
            inner_child_triggered=False,
            inner_child_dominant="",
            inner_child_beta=0.0,
        )
        assert v.passed is True
        assert v.confidence == 0.85
        assert v.entropies == {"dim1": 0.2, "dim2": 0.3}
        assert v.variance == 0.05
        assert v.threshold_level == 0.6
        assert v.should_retreat is False
        assert v.retreat_reason == ""
        assert v.cultivation_qi == 0.72
        assert v.timestamp == 1234567890.0
        assert v.inner_child_phi == 0.15
        assert v.inner_child_triggered is False
        assert v.inner_child_dominant == ""
        assert v.inner_child_beta == 0.0

    def test_default_values(self):
        """测试默认值"""
        v = ZhizhiVerdict(
            passed=False,
            confidence=0.3,
            entropies={},
            variance=0.1,
            threshold_level=0.6,
            should_retreat=True,
        )
        assert v.retreat_reason == ""
        assert v.cultivation_qi == 0.0
        assert v.inner_child_phi is None
        assert v.inner_child_triggered is False
        assert v.inner_child_dominant == ""
        assert v.inner_child_beta == 0.0
        assert isinstance(v.timestamp, float)

    def test_should_retreat_true(self):
        """should_retreat=True 时的判决"""
        v = ZhizhiVerdict(
            passed=False,
            confidence=0.4,
            entropies={"a": 0.9},
            variance=0.35,
            threshold_level=0.6,
            should_retreat=True,
            retreat_reason="置信度过低",
        )
        assert v.should_retreat is True
        assert v.passed is False
        assert v.retreat_reason == "置信度过低"

    def test_should_retreat_false(self):
        """should_retreat=False 时的判决"""
        v = ZhizhiVerdict(
            passed=True,
            confidence=0.9,
            entropies={"a": 0.1},
            variance=0.02,
            threshold_level=0.6,
            should_retreat=False,
        )
        assert v.should_retreat is False
        assert v.passed is True

    def test_inner_child_fields(self):
        """内在小孩字段填充"""
        v = ZhizhiVerdict(
            passed=False,
            confidence=0.5,
            entropies={},
            variance=0.0,
            threshold_level=0.6,
            should_retreat=True,
            retreat_reason="内在小孩门禁触发",
            inner_child_phi=0.87,
            inner_child_triggered=True,
            inner_child_dominant="愤怒小孩",
            inner_child_beta=0.65,
        )
        assert v.inner_child_phi == 0.87
        assert v.inner_child_triggered is True
        assert v.inner_child_dominant == "愤怒小孩"
        assert v.inner_child_beta == 0.65

    def test_timestamp_auto_generated(self):
        """timestamp 自动生成"""
        before = time.time()
        v = ZhizhiVerdict(
            passed=True,
            confidence=0.8,
            entropies={},
            variance=0.0,
            threshold_level=0.6,
            should_retreat=False,
        )
        after = time.time()
        assert before <= v.timestamp <= after + 0.1


# ============================================================================
# 2. TianmenGate 数据类测试
# ============================================================================

class TestTianmenGate:
    """TianmenGate 数据类测试"""

    def test_default_values(self):
        """测试默认配置值"""
        gate = TianmenGate()
        assert gate.min_confidence == 0.6
        assert gate.max_entropy_threshold == 0.8
        assert gate.max_variance_threshold == 0.3
        assert gate.retreat_on_low_confidence is True
        assert gate.retreat_on_high_entropy is True
        assert gate.silent_on_boundary is True
        assert gate.track_cultivation is True
        assert gate.adaptive_threshold is True
        assert gate.history_window == 100

    def test_custom_values(self):
        """测试自定义配置值"""
        gate = TianmenGate(
            min_confidence=0.7,
            max_entropy_threshold=0.5,
            max_variance_threshold=0.2,
            retreat_on_low_confidence=False,
            retreat_on_high_entropy=False,
            silent_on_boundary=False,
            track_cultivation=False,
            adaptive_threshold=False,
            history_window=50,
        )
        assert gate.min_confidence == 0.7
        assert gate.max_entropy_threshold == 0.5
        assert gate.max_variance_threshold == 0.2
        assert gate.retreat_on_low_confidence is False
        assert gate.retreat_on_high_entropy is False
        assert gate.silent_on_boundary is False
        assert gate.track_cultivation is False
        assert gate.adaptive_threshold is False
        assert gate.history_window == 50

    def test_partial_custom_values(self):
        """测试部分自定义值"""
        gate = TianmenGate(min_confidence=0.8, history_window=200)
        assert gate.min_confidence == 0.8
        assert gate.history_window == 200
        # 其余保持默认
        assert gate.max_entropy_threshold == 0.8
        assert gate.retreat_on_low_confidence is True


# ============================================================================
# 3. ZhizhiEngine 测试
# ============================================================================

class TestZhizhiEngineInit:
    """ZhizhiEngine 初始化测试"""

    def test_init_with_default_gate(self):
        """使用默认门禁初始化"""
        engine = ZhizhiEngine()
        assert isinstance(engine.gate, TianmenGate)
        assert engine.gate.min_confidence == 0.6
        assert engine._history == []
        assert engine._adaptive_threshold == 0.6

    def test_init_with_custom_gate(self):
        """使用自定义门禁初始化"""
        gate = TianmenGate(min_confidence=0.8, max_entropy_threshold=0.5)
        engine = ZhizhiEngine(gate)
        assert engine.gate is gate
        assert engine.gate.min_confidence == 0.8
        assert engine._adaptive_threshold == 0.8


class TestZhizhiEngineJudge:
    """ZhizhiEngine.judge() 测试"""

    # ── 基础判定 ──

    def test_judge_high_confidence_passed(self):
        """高置信度输出 → passed=True"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="这是一个高质量的回答，内容详实且逻辑清晰",
            confidence_scores={"accuracy": 0.9, "relevance": 0.95},
        )
        assert verdict.passed is True
        assert verdict.should_retreat is False
        assert verdict.confidence > 0.8

    def test_judge_low_confidence_retreat(self):
        """低置信度 → passed=False, should_retreat=True"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="不确定",
            confidence_scores={"accuracy": 0.3, "relevance": 0.25},
        )
        assert verdict.passed is False
        assert verdict.should_retreat is True
        assert "置信度过低" in verdict.retreat_reason

    def test_judge_high_entropy_retreat(self):
        """高熵 → should_retreat=True"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="test",
            confidence_scores={"accuracy": 0.8, "relevance": 0.85},
            feature_entropies={"dim1": 0.9, "dim2": 0.95},
        )
        assert verdict.should_retreat is True
        assert "熵过高" in verdict.retreat_reason

    def test_judge_high_variance(self):
        """高方差 → passed=False（方差超过阈值，但置信度仍通过）"""
        gate = TianmenGate(max_variance_threshold=0.05)
        engine = ZhizhiEngine(gate)
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.95, "b": 0.1, "c": 0.9},
        )
        # 均值 0.65 > 0.6，置信度通过；方差 ~0.15 > 0.05，触发方差
        assert verdict.passed is False
        assert "方差过大" in verdict.retreat_reason

    def test_judge_boundary_values_silent(self):
        """边界值 → silent 行为"""
        gate = TianmenGate(
            min_confidence=0.6,
            retreat_on_low_confidence=False,
            retreat_on_high_entropy=False,
            silent_on_boundary=True,
        )
        engine = ZhizhiEngine(gate)
        verdict = engine.judge(
            output="short",
            confidence_scores={"a": 0.5},
        )
        assert verdict.passed is False
        assert verdict.should_retreat is False
        assert "天门关闭" in verdict.retreat_reason

    # ── 内在小孩 ──

    def test_judge_with_inner_child_state(self):
        """带 inner_child_state 的判决"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="test output",
            confidence_scores={"a": 0.9},
            inner_child_state={
                "entropy_phi": 0.3,
                "gate_triggered": False,
                "dominant": {"name": "inner_child_1", "beta": 0.1},
            },
        )
        assert verdict.inner_child_phi == 0.3
        assert verdict.inner_child_triggered is False
        assert verdict.inner_child_dominant == "inner_child_1"
        assert verdict.inner_child_beta == 0.1

    def test_judge_inner_child_triggered(self):
        """内在小孩门禁触发"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.9},
            inner_child_state={
                "entropy_phi": 0.9,
                "gate_triggered": True,
                "dominant": {"name": "愤怒小孩", "beta": 0.8},
            },
        )
        assert verdict.passed is False
        assert verdict.should_retreat is True
        assert verdict.inner_child_triggered is True
        assert "内在小孩门禁触发" in verdict.retreat_reason
        assert verdict.inner_child_dominant == "愤怒小孩"

    def test_judge_inner_child_state_no_dominant_key(self):
        """inner_child_state 缺少 dominant 键"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.9},
            inner_child_state={
                "entropy_phi": 0.1,
                "gate_triggered": False,
            },
        )
        assert verdict.inner_child_phi == 0.1
        assert verdict.inner_child_dominant == ""
        assert verdict.inner_child_beta == 0.0

    def test_judge_inner_child_state_empty_dict(self):
        """inner_child_state 为空字典 → 跳过内在小孩门禁"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.9},
            inner_child_state={},
        )
        # 空字典被 if inner_child_state: 判定为 False，跳过内在小孩块
        assert verdict.inner_child_phi is None
        assert verdict.inner_child_triggered is False
        assert verdict.inner_child_dominant == ""
        assert verdict.inner_child_beta == 0.0

    # ── 空数据 ──

    def test_judge_empty_entropies(self):
        """空的 entropies 字典 → 回退到估计"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="test output",
            confidence_scores={"a": 0.9},
            feature_entropies={},
        )
        # 空字典 if feature_entropies: 为 False，走 _estimate_entropies
        assert verdict.entropies == {"output": 0.5}
        assert verdict.passed is True

    def test_judge_no_confidence_scores(self):
        """不提供 confidence_scores，使用估计值"""
        engine = ZhizhiEngine()
        verdict = engine.judge(output="A sufficiently long string for confidence estimation purposes")
        assert isinstance(verdict.confidence, float)
        assert verdict.variance == 0.0

    # ── 策略配置 ──

    def test_retreat_on_low_confidence_false(self):
        """retreat_on_low_confidence=False"""
        gate = TianmenGate(
            min_confidence=0.6,
            retreat_on_low_confidence=False,
            silent_on_boundary=True,
        )
        engine = ZhizhiEngine(gate)
        verdict = engine.judge(
            output="short",
            confidence_scores={"a": 0.4},
        )
        assert verdict.passed is False
        assert verdict.should_retreat is False
        assert "天门关闭" in verdict.retreat_reason

    def test_retreat_on_high_entropy_false(self):
        """retreat_on_high_entropy=False"""
        gate = TianmenGate(
            retreat_on_high_entropy=False,
            silent_on_boundary=True,
        )
        engine = ZhizhiEngine(gate)
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.8},
            feature_entropies={"d1": 0.95},
        )
        assert verdict.passed is False
        assert verdict.should_retreat is False
        assert "天门关闭" in verdict.retreat_reason


class TestZhizhiEngineEstimateEntropies:
    """_estimate_entropies() 测试"""

    def test_estimate_entropies_dict_output(self):
        """字典输出 → 各维度估算"""
        engine = ZhizhiEngine()
        entropies = engine._estimate_entropies({"score": 50, "name": "hello"})
        assert "score" in entropies
        assert "name" in entropies
        assert 0.0 <= entropies["score"] <= 1.0
        assert 0.0 <= entropies["name"] <= 1.0

    def test_estimate_entropies_string_output(self):
        """字符串输出 → 单一 output 键"""
        engine = ZhizhiEngine()
        entropies = engine._estimate_entropies("hello world")
        assert entropies == {"output": 0.5}

    def test_estimate_entropies_list_output(self):
        """列表输出 → 单一 output 键"""
        engine = ZhizhiEngine()
        entropies = engine._estimate_entropies([1, 2, 3])
        assert entropies == {"output": 0.5}

    def test_estimate_entropies_nested_dict(self):
        """嵌套字典 → 非数值/字符串值估算为 0.5"""
        engine = ZhizhiEngine()
        entropies = engine._estimate_entropies({"a": {"nested": 1}, "b": 42})
        assert "a" in entropies
        assert entropies["a"] == 0.5
        assert entropies["b"] == min(1.0, 42 / 100.0)

    def test_estimate_entropies_none_output(self):
        """None 输出"""
        engine = ZhizhiEngine()
        entropies = engine._estimate_entropies(None)
        assert entropies == {"output": 0.5}

    def test_estimate_entropies_float_values(self):
        """浮点数值归一化"""
        engine = ZhizhiEngine()
        entropies = engine._estimate_entropies({"x": 200.0})
        assert entropies["x"] == 1.0  # min(1.0, 200/100)

    def test_estimate_entropies_long_string_value(self):
        """长字符串值"""
        engine = ZhizhiEngine()
        entropies = engine._estimate_entropies({"text": "a" * 1500})
        assert entropies["text"] == 1.0  # min(1.0, 1500/1000)


class TestZhizhiEngineEstimateConfidence:
    """_estimate_confidence() 测试"""

    def test_estimate_confidence_none(self):
        """None 输出 → 0.0"""
        engine = ZhizhiEngine()
        assert engine._estimate_confidence(None) == 0.0

    def test_estimate_confidence_short_string(self):
        """短字符串 (< 20) → 0.4"""
        engine = ZhizhiEngine()
        assert engine._estimate_confidence("hi") == 0.4

    def test_estimate_confidence_medium_string(self):
        """中等字符串 (20-99) → 0.6"""
        engine = ZhizhiEngine()
        assert engine._estimate_confidence("a" * 50) == 0.6

    def test_estimate_confidence_long_string(self):
        """长字符串 (>= 100) → 0.7"""
        engine = ZhizhiEngine()
        assert engine._estimate_confidence("a" * 200) == 0.7

    def test_estimate_confidence_dict(self):
        """字典输出 → 基于字段完整性"""
        engine = ZhizhiEngine()
        result = engine._estimate_confidence({"a": 1, "b": None, "c": "hello"})
        assert result == min(0.9, 2 / 3)  # 2 filled / 3 total

    def test_estimate_confidence_empty_dict(self):
        """空字典"""
        engine = ZhizhiEngine()
        result = engine._estimate_confidence({})
        assert result == 0.0  # 0 filled / 1 = 0.0

    def test_estimate_confidence_dict_all_filled(self):
        """字典全部有值"""
        engine = ZhizhiEngine()
        result = engine._estimate_confidence({"a": 1, "b": 2})
        assert result == 0.9  # min(0.9, 2/2) = min(0.9, 1.0)

    def test_estimate_confidence_non_empty_list(self):
        """非空列表 → 0.6"""
        engine = ZhizhiEngine()
        assert engine._estimate_confidence([1, 2, 3]) == 0.6

    def test_estimate_confidence_empty_list(self):
        """空列表 → 0.3"""
        engine = ZhizhiEngine()
        assert engine._estimate_confidence([]) == 0.3

    def test_estimate_confidence_other_type(self):
        """其他类型 → 0.5"""
        engine = ZhizhiEngine()
        assert engine._estimate_confidence(42) == 0.5


class TestZhizhiEngineComputeVariance:
    """_compute_variance() 测试"""

    def test_compute_variance_normal(self):
        """正常方差计算"""
        engine = ZhizhiEngine()
        values = [0.0, 0.5, 1.0]
        result = engine._compute_variance(values)
        mean = 0.5
        expected = ((0.0 - 0.5) ** 2 + (0.5 - 0.5) ** 2 + (1.0 - 0.5) ** 2) / 3
        assert math.isclose(result, expected)

    def test_compute_variance_single_value(self):
        """单值 → 0.0"""
        engine = ZhizhiEngine()
        assert engine._compute_variance([0.5]) == 0.0

    def test_compute_variance_empty_list(self):
        """空列表 → 0.0"""
        engine = ZhizhiEngine()
        assert engine._compute_variance([]) == 0.0

    def test_compute_variance_all_same(self):
        """所有值相同 → 0.0"""
        engine = ZhizhiEngine()
        assert engine._compute_variance([0.7, 0.7, 0.7, 0.7]) == 0.0

    def test_compute_variance_high_variance(self):
        """高方差"""
        engine = ZhizhiEngine()
        result = engine._compute_variance([0.0, 1.0, 0.0, 1.0])
        assert result == 0.25  # mean=0.5, variance = (0.25*4)/4 = 0.25

    def test_compute_variance_all_zeros(self):
        """全零值"""
        engine = ZhizhiEngine()
        assert engine._compute_variance([0.0, 0.0, 0.0]) == 0.0

    def test_compute_variance_all_ones(self):
        """全1值"""
        engine = ZhizhiEngine()
        assert engine._compute_variance([1.0, 1.0, 1.0]) == 0.0


class TestZhizhiEngineComputeCultivationQi:
    """_compute_cultivation_qi() 测试"""

    def test_high_qi(self):
        """高置信度+低熵+低方差 → 高元气"""
        engine = ZhizhiEngine()
        qi = engine._compute_cultivation_qi(0.95, 0.1, 0.05)
        expected = 0.95 * 0.9 * 0.95
        assert math.isclose(qi, expected)

    def test_low_qi(self):
        """低置信度+高熵+高方差 → 低元气"""
        engine = ZhizhiEngine()
        qi = engine._compute_cultivation_qi(0.3, 0.9, 0.5)
        expected = max(0.0, 0.3 * 0.1 * 0.5)
        assert math.isclose(qi, expected)

    def test_qi_clamped_to_zero(self):
        """元气被 clamp 到 0"""
        engine = ZhizhiEngine()
        qi = engine._compute_cultivation_qi(0.0, 1.0, 1.0)
        assert qi == 0.0

    def test_qi_clamped_to_one(self):
        """元气被 clamp 到 1"""
        engine = ZhizhiEngine()
        qi = engine._compute_cultivation_qi(1.0, 0.0, 0.0)
        assert qi == 1.0

    def test_qi_perfect_conditions(self):
        """完美条件：最高元气"""
        engine = ZhizhiEngine()
        qi = engine._compute_cultivation_qi(1.0, 0.0, 0.0)
        assert qi == 1.0

    def test_qi_worst_conditions(self):
        """最差条件：最低元气"""
        engine = ZhizhiEngine()
        qi = engine._compute_cultivation_qi(0.0, 1.0, 1.0)
        assert qi == 0.0


class TestZhizhiEngineStats:
    """get_stats() 测试"""

    def test_get_stats_empty(self):
        """空历史统计"""
        engine = ZhizhiEngine()
        stats = engine.get_stats()
        assert stats == {"total": 0, "pass_rate": 0, "avg_qi": 0}

    def test_get_stats_structure(self):
        """统计结构完整性"""
        engine = ZhizhiEngine()
        engine.judge(output="test", confidence_scores={"a": 0.9})
        stats = engine.get_stats()
        assert "total" in stats
        assert "passed" in stats
        assert "retreated" in stats
        assert "pass_rate" in stats
        assert "retreat_rate" in stats
        assert "avg_qi" in stats
        assert "adaptive_threshold" in stats
        assert stats["total"] == 1

    def test_get_stats_after_multiple_judges(self):
        """多次判决后统计"""
        engine = ZhizhiEngine()
        # 高置信度
        engine.judge(output="good output", confidence_scores={"a": 0.9, "b": 0.95})
        # 低置信度
        engine.judge(output="bad", confidence_scores={"a": 0.2, "b": 0.3})
        # 另一个高置信度
        engine.judge(output="good", confidence_scores={"a": 0.85, "b": 0.9})

        stats = engine.get_stats()
        assert stats["total"] == 3
        assert stats["passed"] >= 2
        assert stats["retreated"] >= 1
        assert 0.0 <= stats["pass_rate"] <= 1.0


class TestZhizhiEngineHistory:
    """历史记录测试"""

    def test_reset_history_by_clearing(self):
        """直接清空 _history 重置"""
        engine = ZhizhiEngine()
        engine.judge(output="test", confidence_scores={"a": 0.9})
        assert len(engine._history) == 1
        engine._history.clear()
        assert len(engine._history) == 0
        stats = engine.get_stats()
        assert stats["total"] == 0

    def test_set_adaptive_threshold_directly(self):
        """直接设置 _adaptive_threshold"""
        engine = ZhizhiEngine()
        engine._adaptive_threshold = 0.75
        assert engine._adaptive_threshold == 0.75

    def test_get_history_copy(self):
        """获取 _history 副本"""
        engine = ZhizhiEngine()
        engine.judge(output="a", confidence_scores={"x": 0.9})
        engine.judge(output="b", confidence_scores={"x": 0.8})
        history = list(engine._history)
        assert len(history) == 2
        # 修改副本不影响原始
        history.clear()
        assert len(engine._history) == 2

    def test_get_history_with_limit(self):
        """获取限制数量的历史"""
        engine = ZhizhiEngine()
        for i in range(10):
            engine.judge(output=f"test_{i}", confidence_scores={"a": 0.8})
        recent = engine._history[-5:]
        assert len(recent) == 5

    def test_history_window_limit(self):
        """历史窗口限制"""
        gate = TianmenGate(history_window=5)
        engine = ZhizhiEngine(gate)
        for i in range(10):
            engine.judge(output=f"test_{i}", confidence_scores={"a": 0.8})
        assert len(engine._history) <= 5


class TestZhizhiEngineAdaptiveThreshold:
    """自适应阈值测试"""

    def test_adaptive_threshold_enabled(self):
        """adaptive_threshold=True 时使用自适应阈值"""
        gate = TianmenGate(adaptive_threshold=True, min_confidence=0.6)
        engine = ZhizhiEngine(gate)
        # 初始自适应阈值等于 min_confidence
        assert engine._adaptive_threshold == 0.6

    def test_adaptive_threshold_disabled(self):
        """adaptive_threshold=False 时使用 gate.min_confidence"""
        gate = TianmenGate(adaptive_threshold=False, min_confidence=0.6)
        engine = ZhizhiEngine(gate)
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.55},
        )
        # 即使 _adaptive_threshold 可能不同，实际使用的是 gate.min_confidence
        assert verdict.threshold_level == 0.6

    def test_adaptive_threshold_increases(self):
        """通过率 > 90% 时阈值提高"""
        gate = TianmenGate(adaptive_threshold=True, min_confidence=0.6)
        engine = ZhizhiEngine(gate)
        # 先积累足够的高置信度判决
        for i in range(10):
            engine.judge(output=f"good_{i}", confidence_scores={"a": 0.95})
        # 阈值应已更新
        # 注意：_update_adaptive_threshold 在 >=10 条历史时触发
        stats = engine.get_stats()
        assert stats["adaptive_threshold"] >= 0.6

    def test_adaptive_threshold_decreases(self):
        """通过率 < 30% 时阈值降低"""
        gate = TianmenGate(adaptive_threshold=True, min_confidence=0.6)
        engine = ZhizhiEngine(gate)
        # 先设一个高阈值，然后大量低置信度判决
        engine._adaptive_threshold = 0.8
        for i in range(10):
            engine.judge(output=f"bad_{i}", confidence_scores={"a": 0.1})
        # 阈值应降低
        assert engine._adaptive_threshold < 0.8

    def test_adaptive_threshold_moderate_decrease(self):
        """通过率 30%-60% 时阈值小幅降低"""
        gate = TianmenGate(adaptive_threshold=True, min_confidence=0.6)
        engine = ZhizhiEngine(gate)
        engine._adaptive_threshold = 0.8
        # 混合判决：一半通过一半不通过
        for i in range(10):
            conf = 0.95 if i % 2 == 0 else 0.1
            engine.judge(output=f"mixed_{i}", confidence_scores={"a": conf})
        # 阈值应降低 -0.01
        assert engine._adaptive_threshold < 0.8


class TestZhizhiEngineTrackCultivation:
    """track_cultivation 测试"""

    def test_cultivation_qi_computed(self):
        """元气利用率始终被计算"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.9},
        )
        assert 0.0 <= verdict.cultivation_qi <= 1.0

    def test_cultivation_qi_in_stats(self):
        """元气利用率在统计中"""
        engine = ZhizhiEngine()
        engine.judge(output="test", confidence_scores={"a": 0.9})
        stats = engine.get_stats()
        assert "avg_qi" in stats
        assert stats["avg_qi"] > 0


# ============================================================================
# 4. TianmenGuard 测试
# ============================================================================

class TestTianmenGuard:
    """TianmenGuard 测试"""

    def test_init_default(self):
        """默认初始化"""
        guard = TianmenGuard()
        assert isinstance(guard.engine, ZhizhiEngine)
        assert guard.blocked_count == 0
        assert guard.passed_count == 0

    def test_init_custom_gate(self):
        """自定义门禁初始化"""
        gate = TianmenGate(min_confidence=0.9)
        guard = TianmenGuard(gate)
        assert guard.engine.gate.min_confidence == 0.9

    def test_guard_passed(self):
        """门禁通过 → 返回原输出"""
        guard = TianmenGuard()
        output, verdict = guard.guard(
            output="valid output",
            confidence_scores={"a": 0.95},
        )
        assert output == "valid output"
        assert verdict.passed is True
        assert guard.passed_count == 1
        assert guard.blocked_count == 0

    def test_guard_retreat(self):
        """门禁回退 → 返回退守标记"""
        guard = TianmenGuard()
        output, verdict = guard.guard(
            output="bad",
            confidence_scores={"a": 0.2},
        )
        assert isinstance(output, dict)
        assert output["_gate"] == "retreat"
        assert output["status"] == "天门退守，回头再审"
        assert verdict.should_retreat is True
        assert guard.blocked_count == 1
        assert guard.passed_count == 0

    def test_guard_silent(self):
        """门禁静默 → 返回静默标记"""
        gate = TianmenGate(
            retreat_on_low_confidence=False,
            retreat_on_high_entropy=False,
            silent_on_boundary=True,
        )
        guard = TianmenGuard(gate)
        output, verdict = guard.guard(
            output="bad",
            confidence_scores={"a": 0.2},
        )
        assert isinstance(output, dict)
        assert output["_gate"] == "silent"
        assert output["status"] == "知止不殆，天门未开"
        assert guard.blocked_count == 1

    def test_guard_high_entropy_retreat(self):
        """高熵触发回退（通过 engine.judge 直接测试）"""
        guard = TianmenGuard()
        output, verdict = guard.guard(
            output="test",
            confidence_scores={"a": 0.8},
        )
        # 注意：guard() 不直接支持 feature_entropies 参数
        # 高熵可通过 engine 直接测试
        engine = ZhizhiEngine()
        verdict2 = engine.judge(
            output="test",
            confidence_scores={"a": 0.8},
            feature_entropies={"d1": 0.95},
        )
        assert verdict2.should_retreat is True
        assert "熵过高" in verdict2.retreat_reason

    def test_guard_stats(self):
        """guard 统计"""
        guard = TianmenGuard()
        guard.guard(output="good", confidence_scores={"a": 0.9})
        guard.guard(output="bad", confidence_scores={"a": 0.2})

        stats = guard.get_stats()
        assert "total_guarded" in stats
        assert stats["total_guarded"] == 2
        assert stats["blocked"] == 1
        assert stats["passed"] == 1
        assert "total" in stats  # 来自 engine.get_stats()

    def test_guard_multiple_mixed(self):
        """多次混合判决"""
        guard = TianmenGuard()
        for i in range(5):
            conf = 0.95 if i % 2 == 0 else 0.1
            guard.guard(output=f"test_{i}", confidence_scores={"a": conf})
        stats = guard.get_stats()
        assert stats["total_guarded"] == 5
        assert stats["passed"] >= 2
        assert stats["blocked"] >= 2


# ============================================================================
# 5. get_tianmen() 单例测试
# ============================================================================

class TestGetTianmen:
    """get_tianmen() 单例测试"""

    def test_returns_same_instance(self):
        """返回同一实例"""
        import tengod.tiangan_gate as tg
        tg._tianmen_guard = None
        t1 = get_tianmen()
        t2 = get_tianmen()
        assert t1 is t2
        tg._tianmen_guard = None

    def test_returns_tianmen_guard(self):
        """返回 TianmenGuard 实例"""
        import tengod.tiangan_gate as tg
        tg._tianmen_guard = None
        result = get_tianmen()
        assert isinstance(result, TianmenGuard)
        tg._tianmen_guard = None

    def test_engine_accessible(self):
        """通过 guard 可访问 engine"""
        import tengod.tiangan_gate as tg
        tg._tianmen_guard = None
        guard = get_tianmen()
        assert isinstance(guard.engine, ZhizhiEngine)
        tg._tianmen_guard = None


# ============================================================================
# 6. 边界情况测试
# ============================================================================

class TestEdgeCases:
    """边界情况测试"""

    def test_judge_none_output(self):
        """None 输出"""
        engine = ZhizhiEngine()
        verdict = engine.judge(output=None)
        assert verdict.confidence == 0.0
        assert verdict.passed is False
        assert verdict.should_retreat is True

    def test_judge_empty_dict_output(self):
        """空字典输出"""
        engine = ZhizhiEngine()
        verdict = engine.judge(output={}, confidence_scores={})
        assert verdict.confidence == 0.0  # _estimate_confidence({}) = 0/1 = 0
        assert verdict.entropies == {}

    def test_judge_very_large_output(self):
        """超大输出"""
        engine = ZhizhiEngine()
        large_string = "x" * 10000
        verdict = engine.judge(
            output=large_string,
            confidence_scores={"a": 0.95},
        )
        assert verdict.confidence == 0.95
        assert verdict.passed is True

    def test_all_confidence_scores_at_one(self):
        """所有置信度 1.0"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="perfect",
            confidence_scores={"a": 1.0, "b": 1.0, "c": 1.0},
        )
        assert verdict.confidence == 1.0
        assert verdict.variance == 0.0
        assert verdict.passed is True

    def test_all_confidence_scores_at_zero(self):
        """所有置信度 0.0"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="terrible",
            confidence_scores={"a": 0.0, "b": 0.0},
        )
        assert verdict.confidence == 0.0
        assert verdict.variance == 0.0
        assert verdict.passed is False
        assert verdict.should_retreat is True

    def test_mixed_confidence_scores(self):
        """混合置信度"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="mixed",
            confidence_scores={"a": 0.9, "b": 0.1, "c": 0.5, "d": 0.3},
        )
        assert 0.0 < verdict.confidence < 1.0
        assert verdict.variance > 0.0

    def test_judge_with_context(self):
        """带上下文信息"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.9},
            context={"user_id": "123", "session": "abc"},
        )
        assert verdict.passed is True

    def test_judge_with_context_none(self):
        """context=None"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.9},
            context=None,
        )
        assert verdict.passed is True

    def test_judge_string_output_length_variants(self):
        """不同长度字符串输出的置信度估计"""
        engine = ZhizhiEngine()
        # 短字符串
        v1 = engine.judge(output="hi")
        assert v1.confidence == 0.4
        # 中等字符串
        v2 = engine.judge(output="a" * 50)
        assert v2.confidence == 0.6
        # 长字符串
        v3 = engine.judge(output="a" * 200)
        assert v3.confidence == 0.7

    def test_judge_list_output(self):
        """列表输出"""
        engine = ZhizhiEngine()
        verdict = engine.judge(output=[1, 2, 3])
        assert verdict.confidence == 0.6

    def test_judge_empty_list_output(self):
        """空列表输出"""
        engine = ZhizhiEngine()
        verdict = engine.judge(output=[])
        assert verdict.confidence == 0.3

    def test_judge_tuple_output(self):
        """元组输出"""
        engine = ZhizhiEngine()
        verdict = engine.judge(output=(1, 2))
        assert verdict.confidence == 0.6

    def test_judge_int_output(self):
        """整数输出 → 其他类型 → 0.5"""
        engine = ZhizhiEngine()
        verdict = engine.judge(output=42)
        assert verdict.confidence == 0.5

    def test_judge_float_output(self):
        """浮点数输出 → 其他类型 → 0.5"""
        engine = ZhizhiEngine()
        verdict = engine.judge(output=3.14)
        assert verdict.confidence == 0.5

    def test_confidence_scores_single_entry(self):
        """单条置信度"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="test",
            confidence_scores={"accuracy": 0.85},
        )
        assert verdict.confidence == 0.85
        assert verdict.variance == 0.0  # 单值方差为 0

    def test_feature_entropies_single_entry(self):
        """单条特征熵"""
        engine = ZhizhiEngine()
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.9},
            feature_entropies={"dim1": 0.3},
        )
        assert verdict.entropies == {"dim1": 0.3}
        assert verdict.passed is True

    def test_variance_exceeds_threshold(self):
        """方差刚好超过阈值"""
        gate = TianmenGate(max_variance_threshold=0.1)
        engine = ZhizhiEngine(gate)
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.0, "b": 0.5, "c": 1.0},
        )
        # variance = ((0-0.5)^2 + (0.5-0.5)^2 + (1-0.5)^2)/3 = 0.5/3 ≈ 0.167
        assert verdict.variance > 0.1
        assert verdict.passed is False

    def test_entropy_exactly_at_threshold(self):
        """熵刚好等于阈值（不超过）"""
        gate = TianmenGate(max_entropy_threshold=0.8)
        engine = ZhizhiEngine(gate)
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.9},
            feature_entropies={"d1": 0.8},
        )
        # max_entropy == 0.8，不大于 threshold，不触发
        assert verdict.passed is True

    def test_entropy_just_above_threshold(self):
        """熵刚好超过阈值"""
        gate = TianmenGate(max_entropy_threshold=0.8)
        engine = ZhizhiEngine(gate)
        verdict = engine.judge(
            output="test",
            confidence_scores={"a": 0.9},
            feature_entropies={"d1": 0.8001},
        )
        assert verdict.passed is False
        assert "熵过高" in verdict.retreat_reason

    def test_adaptive_threshold_not_triggered_below_10(self):
        """历史少于 10 条时不触发自适应更新"""
        gate = TianmenGate(adaptive_threshold=True, min_confidence=0.6)
        engine = ZhizhiEngine(gate)
        initial_threshold = engine._adaptive_threshold
        for i in range(5):
            engine.judge(output=f"test_{i}", confidence_scores={"a": 0.95})
        # 少于 10 条，阈值不变
        assert engine._adaptive_threshold == initial_threshold

    def test_retreat_reason_priority(self):
        """回退原因优先级：置信度 > 熵 > 方差"""
        gate = TianmenGate(
            min_confidence=0.6,
            retreat_on_low_confidence=True,
            retreat_on_high_entropy=True,
        )
        engine = ZhizhiEngine(gate)
        # 同时触发低置信度和高熵
        verdict = engine.judge(
            output="bad",
            confidence_scores={"a": 0.3},
            feature_entropies={"d1": 0.95},
        )
        assert "置信度过低" in verdict.retreat_reason
        # 熵过高不会覆盖（因为 should_retreat 已经是 True）
        assert "熵过高" not in verdict.retreat_reason

    def test_dict_entropy_with_none_value(self):
        """dict 熵估计中 None 值"""
        engine = ZhizhiEngine()
        entropies = engine._estimate_entropies({"a": None, "b": 50})
        assert entropies["a"] == 0.5
        assert entropies["b"] == 0.5

    def test_dict_entropy_with_bool_value(self):
        """dict 熵估计中 bool 值"""
        engine = ZhizhiEngine()
        entropies = engine._estimate_entropies({"flag": True})
        # bool 是 int 的子类，True == 1
        assert entropies["flag"] == min(1.0, 1 / 100.0)


# ============================================================================
# 7. 综合场景测试
# ============================================================================

class TestIntegrationScenarios:
    """综合场景测试"""

    def test_full_pipeline_normal(self):
        """完整正常流程"""
        guard = TianmenGuard()
        output, verdict = guard.guard(
            output="经过深思熟虑的高质量回答",
            confidence_scores={"accuracy": 0.92, "completeness": 0.88, "relevance": 0.95},
        )
        assert output == "经过深思熟虑的高质量回答"
        assert verdict.passed is True
        assert guard.passed_count == 1

    def test_full_pipeline_blocked(self):
        """完整阻断流程"""
        guard = TianmenGuard()
        output, verdict = guard.guard(
            output="不确定的猜测",
            confidence_scores={"accuracy": 0.25, "completeness": 0.3},
        )
        assert isinstance(output, dict)
        assert output["_gate"] == "retreat"
        assert verdict.should_retreat is True

    def test_multiple_engines_independent(self):
        """多个引擎独立"""
        engine1 = ZhizhiEngine(TianmenGate(min_confidence=0.7))
        engine2 = ZhizhiEngine(TianmenGate(min_confidence=0.5))

        v1 = engine1.judge(output="test", confidence_scores={"a": 0.6})
        v2 = engine2.judge(output="test", confidence_scores={"a": 0.6})

        # engine1 阈值 0.7，0.6 不通过
        assert v1.passed is False
        # engine2 阈值 0.5，0.6 通过
        assert v2.passed is True

    def test_guard_qi_in_output(self):
        """元气值在输出中"""
        guard = TianmenGuard()
        output, verdict = guard.guard(
            output="bad",
            confidence_scores={"a": 0.2},
        )
        assert "_qi" in output
        assert 0.0 <= output["_qi"] <= 1.0
        assert output["_qi"] == verdict.cultivation_qi

    def test_guard_reason_in_output(self):
        """回退原因在输出中"""
        guard = TianmenGuard()
        output, verdict = guard.guard(
            output="bad",
            confidence_scores={"a": 0.2},
        )
        assert "_reason" in output
        assert output["_reason"] == verdict.retreat_reason