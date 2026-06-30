"""
test_zuowang_attention.py — 坐忘注意力调度器测试
"""
import pytest
import math
import time
from unittest.mock import patch, MagicMock

from tengod.tbce_unit import TBCECoordinates, CognitiveUnit, GateState
from tengod.zuowang_attention import (
    AttentionWeight, AttentionResult, ZuowangAttention,
    get_zuowang_attention, reset_zuowang_attention,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def zuowang():
    reset_zuowang_attention()
    return ZuowangAttention()


@pytest.fixture
def sample_unit():
    return CognitiveUnit(
        unit_id="test.unit1",
        name="测试单元",
        module_path="test.module",
        coordinates=TBCECoordinates.default(),
        cognitive_layer=5,
        psi_operator="ZuowangAttention",
        palace_id=1,
    )


# ── 1. AttentionWeight ────────────────────────────────────

class TestAttentionWeight:
    def test_create(self):
        w = AttentionWeight("S", 0.8)
        assert w.dimension == "S"
        assert w.weight == 0.8
        assert w.retained is True

    def test_not_retained(self):
        w = AttentionWeight("E", 0.2, retained=False)
        assert w.retained is False


# ── 2. AttentionResult ─────────────────────────────────────

class TestAttentionResult:
    def test_create(self):
        original = [AttentionWeight("S", 0.8)]
        pruned = [AttentionWeight("S", 0.8, retained=True)]
        result = AttentionResult(
            unit_id="test",
            original_weights=original,
            pruned_weights=pruned,
            sparsity=0.0,
            retained_count=1,
            total_count=1,
            gate_state=GateState.OPEN,
        )
        assert result.unit_id == "test"
        assert result.sparsity == 0.0
        assert result.retained_count == 1
        assert result.gate_state == GateState.OPEN


# ── 3. allocate_attention ─────────────────────────────────

class TestAllocateAttention:
    def test_returns_six_weights(self, zuowang, sample_unit):
        weights = zuowang.allocate_attention(sample_unit)
        assert len(weights) == 6
        dims = [w.dimension for w in weights]
        assert dims == ["S", "T", "P", "C", "I", "E"]

    def test_weights_normalized(self, zuowang, sample_unit):
        weights = zuowang.allocate_attention(sample_unit)
        total = sum(w.weight for w in weights)
        assert math.isclose(total, 1.0, rel_tol=1e-9)

    def test_high_confidence_unit(self, zuowang):
        """高S可信单元 → S权重低（不需要关注）"""
        unit = CognitiveUnit(
            unit_id="test.high_conf",
            name="高可信",
            module_path="test",
            coordinates=TBCECoordinates(S=0.9, T=0.5, P=0.5, C=0.5, I=0.5, E=0.1),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        weights = zuowang.allocate_attention(unit)
        s_weight = next(w for w in weights if w.dimension == "S")
        assert s_weight.weight < 0.3  # 高S → 低关注

    def test_high_edge_unit(self, zuowang):
        """高E探索单元 → E权重高（需要关注）"""
        unit = CognitiveUnit(
            unit_id="test.high_edge",
            name="高探索",
            module_path="test",
            coordinates=TBCECoordinates(S=0.1, T=0.5, P=0.5, C=0.5, I=0.5, E=0.9),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        weights = zuowang.allocate_attention(unit)
        e_weight = next(w for w in weights if w.dimension == "E")
        assert e_weight.weight > 0.2  # 高E → 高关注

    def test_high_i_mean_low_attention(self, zuowang):
        """高I稳定 → 低关注（已稳定）"""
        unit = CognitiveUnit(
            unit_id="test.stable",
            name="稳定",
            module_path="test",
            coordinates=TBCECoordinates(S=0.5, T=0.5, P=0.5, C=0.5, I=0.9, E=0.5),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        weights = zuowang.allocate_attention(unit)
        i_weight = next(w for w in weights if w.dimension == "I")
        p_weight = next(w for w in weights if w.dimension == "P")
        assert i_weight.weight < p_weight.weight  # 高I 比 高P 更不需要关注


# ── 4. zuowang ─────────────────────────────────────────────

class TestZuowang:
    def test_zuowang_returns_result(self, zuowang, sample_unit):
        result = zuowang.zuowang(sample_unit)
        assert isinstance(result, AttentionResult)
        assert result.unit_id == sample_unit.unit_id
        assert len(result.original_weights) == 6
        assert len(result.pruned_weights) == 6
        assert result.retained_count == len([w for w in result.pruned_weights if w.retained])

    def test_zuowang_prunes_low_weights(self, zuowang):
        """低权重被坐忘"""
        unit = CognitiveUnit(
            unit_id="test.low",
            name="低权重",
            module_path="test",
            # S=0.9 → weight=0.1, P=0.9 → weight=0.1, E=0.1 → weight=0.1
            coordinates=TBCECoordinates(S=0.9, T=0.5, P=0.9, C=0.5, I=0.9, E=0.1),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        result = zuowang.zuowang(unit)
        # 低权重维度应该被坐忘
        forgotten = [w for w in result.pruned_weights if not w.retained]
        assert len(forgotten) > 0

    def test_zuowang_retains_high_weights(self, zuowang):
        """高权重被保留"""
        z = ZuowangAttention(pruning_threshold=0.1)  # 低阈值确保保留
        unit = CognitiveUnit(
            unit_id="test.high",
            name="高权重",
            module_path="test",
            # S=0.1 → weight=0.9, P=0.1 → weight=0.9, E=0.9 → weight=0.9
            coordinates=TBCECoordinates(S=0.1, T=0.5, P=0.1, C=0.5, I=0.1, E=0.9),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        result = z.zuowang(unit)
        retained = [w for w in result.pruned_weights if w.retained]
        assert len(retained) > 0

    def test_sparsity_calculation(self, zuowang, sample_unit):
        result = zuowang.zuowang(sample_unit)
        expected_sparsity = 1.0 - (result.retained_count / result.total_count)
        assert math.isclose(result.sparsity, expected_sparsity, rel_tol=1e-9)

    def test_auto_judge_enabled(self, zuowang, sample_unit):
        result = zuowang.zuowang(sample_unit, auto_judge=True)
        assert result.gate_state in (GateState.OPEN, GateState.PENDING, GateState.CLOSED)

    def test_auto_judge_disabled(self, zuowang, sample_unit):
        result = zuowang.zuowang(sample_unit, auto_judge=False)
        assert result.gate_state == GateState.PENDING


# ── 5. Gate Judging ────────────────────────────────────────

class TestGateJudging:
    def test_open_gate(self, zuowang):
        """刚好目标稀疏度 → 开"""
        s = zuowang._judge_gate(0.5, 3)
        assert s == GateState.OPEN

    def test_pending_gate(self, zuowang):
        """接近目标 → 徘徊"""
        s = zuowang._judge_gate(0.35, 4)
        assert s == GateState.PENDING

    def test_closed_too_low_sparsity(self, zuowang):
        """坐忘太少 → 关"""
        s = zuowang._judge_gate(0.1, 6)
        assert s == GateState.CLOSED

    def test_closed_too_high_sparsity(self, zuowang):
        """坐忘太多 → 关"""
        s = zuowang._judge_gate(0.9, 1)
        assert s == GateState.CLOSED

    def test_closed_too_few_retained(self, zuowang):
        """保留太少 → 关"""
        s = zuowang._judge_gate(0.5, 1)
        assert s == GateState.CLOSED

    def test_closed_too_many_retained(self, zuowang):
        """保留太多 → 关"""
        s = zuowang._judge_gate(0.5, 6)
        assert s == GateState.CLOSED


# ── 6. get_attention_focus / get_attention_blind ────────────

class TestAttentionFocus:
    def test_get_focus(self, zuowang, sample_unit):
        result = zuowang.zuowang(sample_unit)
        focus = zuowang.get_attention_focus(result)
        assert isinstance(focus, list)
        assert len(focus) == result.retained_count

    def test_get_blind(self, zuowang, sample_unit):
        result = zuowang.zuowang(sample_unit)
        blind = zuowang.get_attention_blind(result)
        assert isinstance(blind, list)
        assert len(blind) == result.total_count - result.retained_count

    def test_focus_and_blind_partition(self, zuowang, sample_unit):
        """焦点+盲区 = 全部维度"""
        result = zuowang.zuowang(sample_unit)
        focus = zuowang.get_attention_focus(result)
        blind = zuowang.get_attention_blind(result)
        assert len(focus) + len(blind) == 6


# ── 7. batch_zuowang ────────────────────────────────────────

class TestBatchZuowang:
    def test_batch(self, zuowang):
        units = [
            CognitiveUnit(
                unit_id=f"test.batch{i}",
                name=f"批量{i}",
                module_path="test",
                coordinates=TBCECoordinates.default(),
                cognitive_layer=1, psi_operator="EmbeddingProvider",
            )
            for i in range(3)
        ]
        results = zuowang.batch_zuowang(units)
        assert len(results) == 3
        for r in results:
            assert isinstance(r, AttentionResult)
            assert r.unit_id.startswith("test.batch")


# ── 8. get_statistics ──────────────────────────────────────

class TestStatistics:
    def test_empty_stats(self, zuowang):
        stats = zuowang.get_statistics()
        assert stats == {}

    def test_stats_after_zuowang(self, zuowang, sample_unit):
        zuowang.zuowang(sample_unit)
        zuowang.zuowang(sample_unit)
        stats = zuowang.get_statistics()
        assert stats['total_judgments'] == 2
        assert 'avg_sparsity' in stats
        assert 'gate_stats' in stats
        assert stats['gate_stats']['open'] + stats['gate_stats']['pending'] + stats['gate_stats']['closed'] == 2


# ── 9. Global Singleton ────────────────────────────────────

class TestGlobalSingleton:
    def test_get_zuowang_attention(self):
        reset_zuowang_attention()
        z1 = get_zuowang_attention()
        z2 = get_zuowang_attention()
        assert z1 is z2

    def test_reset_zuowang_attention(self):
        z1 = get_zuowang_attention()
        reset_zuowang_attention()
        z2 = get_zuowang_attention()
        assert z1 is not z2


# ── 10. Custom Config ──────────────────────────────────────

class TestCustomConfig:
    def test_custom_sparsity_target(self):
        z = ZuowangAttention(sparsity_target=0.3)
        assert z.sparsity_target == 0.3

    def test_custom_pruning_threshold(self):
        z = ZuowangAttention(pruning_threshold=0.5)
        unit = CognitiveUnit(
            unit_id="test", name="test", module_path="test",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        result = z.zuowang(unit)
        # higher threshold means more pruning
        assert isinstance(result, AttentionResult)

    def test_low_threshold_retains_more(self, sample_unit):
        """低阈值保留更多维度"""
        z_low = ZuowangAttention(pruning_threshold=0.1)
        z_high = ZuowangAttention(pruning_threshold=0.5)
        r_low = z_low.zuowang(sample_unit)
        r_high = z_high.zuowang(sample_unit)
        assert r_low.retained_count >= r_high.retained_count


# ── 11. Edge Cases ─────────────────────────────────────────

class TestEdgeCases:
    def test_extreme_coordinates(self):
        """极端坐标"""
        unit = CognitiveUnit(
            unit_id="test.extreme",
            name="极端",
            module_path="test",
            coordinates=TBCECoordinates(S=0.0, T=0.0, P=0.0, C=0.0, I=0.0, E=0.0),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        z = ZuowangAttention()
        result = z.zuowang(unit)
        assert isinstance(result, AttentionResult)

    def test_max_coordinates(self):
        """全最大值"""
        unit = CognitiveUnit(
            unit_id="test.max",
            name="最大",
            module_path="test",
            coordinates=TBCECoordinates(S=1.0, T=1.0, P=1.0, C=1.0, I=1.0, E=1.0),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        z = ZuowangAttention()
        result = z.zuowang(unit)
        assert isinstance(result, AttentionResult)