"""
test_lens_zoom.py — 透镜缩放引擎测试 v2.24.0
"""
import pytest
import math
from unittest.mock import patch, MagicMock

from tengod.tbce_unit import TBCECoordinates, CognitiveUnit, GateState
from tengod.lens_zoom import (
    ZoomMode, ZoomState, LensZoomEngine,
    LoadMetric, BalanceResult, LoadBalancer,
    RhythmSlot, RhythmResult, RhythmScheduler,
    ZoomRing, ZoomGate,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def engine():
    return LensZoomEngine()


@pytest.fixture
def lb():
    return LoadBalancer()


@pytest.fixture
def scheduler():
    return RhythmScheduler()


@pytest.fixture
def sample_units():
    return [
        CognitiveUnit(
            unit_id=f"u{i}", name=f"unit{i}", module_path="test",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=i % 8 + 1, psi_operator="EmbeddingProvider",
        )
        for i in range(10)
    ]


# ── 1. ZoomMode ───────────────────────────────────────────

class TestZoomMode:
    def test_wide_mode(self):
        assert ZoomMode.WIDE.precision == 0.4
        assert ZoomMode.WIDE.throughput == 0.95
        assert ZoomMode.WIDE.label == "广角·全并行"

    def test_normal_mode(self):
        assert ZoomMode.NORMAL.precision == 0.7
        assert ZoomMode.NORMAL.throughput == 0.7

    def test_tele_mode(self):
        assert ZoomMode.TELE.precision == 0.95
        assert ZoomMode.TELE.throughput == 0.3

    def test_speculative_mode(self):
        assert ZoomMode.SPECULATIVE.precision == 0.85
        assert ZoomMode.SPECULATIVE.throughput == 0.6


# ── 2. ZoomState ──────────────────────────────────────────

class TestZoomState:
    def test_default_state(self):
        state = ZoomState()
        assert state.mode == ZoomMode.NORMAL
        assert state.focal_length == 0.5
        assert state.burst_size == 2
        assert state.confidence_threshold == 0.7

    def test_to_dict(self):
        state = ZoomState(mode=ZoomMode.WIDE, focal_length=0.3)
        d = state.to_dict()
        assert d["mode"] == "wide"
        assert d["focal_length"] == 0.3


# ── 3. LensZoomEngine ─────────────────────────────────────

class TestLensZoomEngine:
    def test_initial_state(self, engine):
        assert engine.state.mode == ZoomMode.NORMAL
        assert engine.state.focal_length == 0.5

    def test_auto_zoom_high_load(self, engine):
        """高负载 → 推测解码（广角捕获+长焦验证）"""
        state = engine.auto_zoom(load_level=0.85, confidence=0.6)
        assert state.mode == ZoomMode.SPECULATIVE
        assert state.focal_length == 0.5

    def test_auto_zoom_low_load(self, engine):
        """低负载 → 长焦"""
        state = engine.auto_zoom(load_level=0.2, confidence=0.5)
        assert state.mode == ZoomMode.TELE
        assert state.focal_length > 0.5

    def test_auto_zoom_high_confidence(self, engine):
        """高置信度 → 广角"""
        state = engine.auto_zoom(load_level=0.5, confidence=0.9)
        assert state.mode == ZoomMode.WIDE

    def test_auto_zoom_low_confidence(self, engine):
        """低置信度 → 长焦"""
        state = engine.auto_zoom(load_level=0.5, confidence=0.3)
        assert state.mode == ZoomMode.TELE

    def test_zoom_to_wide(self, engine):
        state = engine.zoom_to(ZoomMode.WIDE)
        assert state.mode == ZoomMode.WIDE
        assert state.focal_length == 0.0
        # WIDE: min(8, 1) = 1
        assert state.burst_size == 1

    def test_zoom_to_tele(self, engine):
        state = engine.zoom_to(ZoomMode.TELE)
        assert state.mode == ZoomMode.TELE
        assert state.focal_length == 1.0
        assert state.burst_size == 1

    def test_zoom_to_speculative(self, engine):
        state = engine.zoom_to(ZoomMode.SPECULATIVE)
        assert state.mode == ZoomMode.SPECULATIVE
        assert state.focal_length == 0.5

    def test_zoom_history(self, engine):
        engine.zoom_to(ZoomMode.WIDE)
        engine.zoom_to(ZoomMode.NORMAL)
        history = engine.get_zoom_history()
        assert len(history) == 2

    def test_statistics(self, engine):
        engine.zoom_to(ZoomMode.WIDE)
        engine.zoom_to(ZoomMode.TELE)
        stats = engine.get_statistics()
        assert stats["transitions"] == 2

    def test_burst_size_calculation(self, engine):
        assert engine._calc_burst_size(ZoomMode.WIDE, 10) == 8
        assert engine._calc_burst_size(ZoomMode.NORMAL, 10) == 2
        assert engine._calc_burst_size(ZoomMode.TELE, 10) == 1
        assert engine._calc_burst_size(ZoomMode.SPECULATIVE, 2) == 2
        assert engine._calc_burst_size(ZoomMode.SPECULATIVE, 4) == 4
        assert engine._calc_burst_size(ZoomMode.SPECULATIVE, 6) == 6

    def test_confidence_threshold_calculation(self, engine):
        assert engine._calc_confidence_threshold(ZoomMode.TELE) == 0.9
        assert engine._calc_confidence_threshold(ZoomMode.WIDE) == 0.5
        assert engine._calc_confidence_threshold(ZoomMode.SPECULATIVE) == 0.7


# ── 4. LoadBalancer ───────────────────────────────────────

class TestLoadBalancer:
    def test_register_node(self, lb):
        lb.register_node("node_a", capacity=1.0)
        assert "node_a" in lb._nodes
        assert lb._nodes["node_a"].capacity == 1.0

    def test_update_node_load(self, lb):
        lb.register_node("node_a")
        lb.update_node_load("node_a", 0.5, 3)
        assert lb._nodes["node_a"].load == 0.5
        assert lb._nodes["node_a"].queue_depth == 3

    def test_update_nonexistent_node(self, lb):
        lb.update_node_load("nonexistent", 0.5)
        # 不应该报错

    def test_balance_weighted_least(self, lb, sample_units):
        lb.register_node("a", capacity=1.0)
        lb.register_node("b", capacity=0.5)
        result = lb.balance(sample_units, "weighted_least_connections")
        assert result.total_units == 10
        assert sum(result.assignments.values()) == 10
        assert result.imbalance >= 0

    def test_balance_round_robin(self, lb, sample_units):
        lb.register_node("a", capacity=1.0)
        lb.register_node("b", capacity=1.0)
        lb.register_node("c", capacity=1.0)
        result = lb.balance(sample_units, "round_robin")
        assert result.total_units == 10
        # 轮询应该接近均衡
        assert result.imbalance <= 0.3

    def test_balance_capacity_aware(self, lb, sample_units):
        lb.register_node("a", capacity=1.0)
        lb.register_node("b", capacity=0.5)
        result = lb.balance(sample_units, "capacity_aware")
        assert result.total_units == 10
        assert result.assignments["a"] > result.assignments["b"]

    def test_balance_cognitive_layer(self, lb, sample_units):
        lb.register_node("high_cap", capacity=1.0)
        lb.register_node("low_cap", capacity=0.3)
        result = lb.balance(sample_units, "cognitive_layer")
        assert result.total_units == 10

    def test_balance_no_nodes(self, lb, sample_units):
        result = lb.balance(sample_units)
        assert result.total_units == 10
        assert result.imbalance == 1.0
        assert result.assignments == {}

    def test_node_stats(self, lb):
        lb.register_node("a", capacity=1.0)
        lb.update_node_load("a", 0.5)
        stats = lb.get_node_stats()
        assert "a" in stats
        assert stats["a"]["load"] == 0.5
        assert stats["a"]["utilization"] == 0.5

    def test_balance_history(self, lb, sample_units):
        lb.register_node("a")
        lb.balance(sample_units[:3])
        lb.balance(sample_units[3:6])
        assert len(lb.get_balance_history()) == 2

    def test_imbalance_zero(self, lb):
        """完美均衡"""
        assert lb._calc_imbalance({"a": 5, "b": 5}) == 0.0

    def test_imbalance_max(self, lb):
        """完全失衡"""
        assert lb._calc_imbalance({"a": 10, "b": 0}) == 1.0


# ── 5. RhythmScheduler ────────────────────────────────────

class TestRhythmScheduler:
    def test_schedule(self, scheduler):
        candidates = [
            {"confidence": 0.9},
            {"confidence": 0.8},
            {"confidence": 0.3},
            {"confidence": 0.95},
        ]
        result = scheduler.schedule(candidates)
        assert result.total_slots == 4
        assert result.accepted_slots == 3
        assert result.acceptance_rate == 0.75

    def test_schedule_with_scores(self, scheduler):
        candidates = [{"val": "a"}, {"val": "b"}, {"val": "c"}]
        scores = [0.9, 0.5, 0.8]
        result = scheduler.schedule(candidates, confidence_scores=scores)
        assert result.accepted_slots == 2

    def test_schedule_empty(self, scheduler):
        result = scheduler.schedule([])
        assert result.total_slots == 0
        assert result.accepted_slots == 0

    def test_speedup_calculation(self, scheduler):
        # 100% acceptance → speedup = burst_size
        speedup = scheduler._calc_speedup(1.0, 4)
        assert speedup == 4.0

        # 75% acceptance → speedup = 4 / (1 + 0.25*4) = 4/2 = 2
        speedup = scheduler._calc_speedup(0.75, 4)
        assert speedup == 2.0

        # 0% acceptance → speedup = 1
        speedup = scheduler._calc_speedup(0.0, 4)
        assert speedup == 1.0

        # 50% acceptance → speedup = 4 / (1 + 0.5*4) = 4/3 ≈ 1.33
        speedup = scheduler._calc_speedup(0.5, 4)
        assert math.isclose(speedup, 1.333, rel_tol=0.01)

    def test_adjust_burst_size_high_conf(self, scheduler):
        new_size = scheduler._adjust_burst_size([0.9, 0.95, 0.88, 0.92])
        assert new_size == 6

    def test_adjust_burst_size_low_conf(self, scheduler):
        new_size = scheduler._adjust_burst_size([0.3, 0.4, 0.35])
        assert new_size == 3  # burst_size - 1

    def test_set_burst_size(self, scheduler):
        scheduler.set_burst_size(5)
        assert scheduler.burst_size == 5
        scheduler.set_burst_size(10)  # 超过最大值
        assert scheduler.burst_size == 6
        scheduler.set_burst_size(1)   # 低于最小值
        assert scheduler.burst_size == 2

    def test_statistics(self, scheduler):
        candidates = [{"confidence": 0.9}]
        scheduler.schedule(candidates)
        stats = scheduler.get_statistics()
        assert stats["total_schedules"] == 1
        assert stats["avg_speedup"] > 0

    def test_estimate_confidence(self, scheduler):
        candidates = [
            {"confidence": 0.8},
            {"score": 0.6},
            {"probability": 0.4},
            {"unknown": 0.9},
        ]
        scores = scheduler._estimate_confidence(candidates)
        assert scores == [0.8, 0.6, 0.4, 0.5]


# ── 6. ZoomRing ───────────────────────────────────────────

class TestZoomRing:
    def test_initial_state(self):
        ring = ZoomRing()
        assert ring.get_state().mode == ZoomMode.NORMAL

    def test_legal_transition(self):
        ring = ZoomRing()
        result = ring.transition(ZoomMode.WIDE)
        assert result is not None
        assert result.mode == ZoomMode.WIDE

    def test_illegal_transition(self):
        ring = ZoomRing()
        ring.transition(ZoomMode.WIDE)
        # WIDE → TELE 非法
        result = ring.transition(ZoomMode.TELE)
        assert result is None

    def test_auto(self):
        ring = ZoomRing()
        state = ring.auto(load_level=0.85, confidence=0.6)
        assert state.mode == ZoomMode.SPECULATIVE

    def test_transition_count(self):
        ring = ZoomRing()
        ring.transition(ZoomMode.WIDE)
        ring.transition(ZoomMode.NORMAL)
        assert ring.get_transition_count() == 2


# ── 7. ZoomGate ───────────────────────────────────────────

class TestZoomGate:
    def test_optimal_focal_open(self):
        gate = ZoomGate()
        state = ZoomState(focal_length=0.5)
        assert gate.judge(state) == GateState.OPEN

    def test_acceptable_focal_pending(self):
        gate = ZoomGate()
        state = ZoomState(focal_length=0.15)
        assert gate.judge(state) == GateState.PENDING

    def test_extreme_focal_closed(self):
        gate = ZoomGate()
        state = ZoomState(focal_length=0.05)
        assert gate.judge(state) == GateState.CLOSED

    def test_high_focal_pending(self):
        gate = ZoomGate()
        state = ZoomState(focal_length=0.85)
        assert gate.judge(state) == GateState.PENDING

    def test_max_focal_closed(self):
        gate = ZoomGate()
        state = ZoomState(focal_length=0.95)
        assert gate.judge(state) == GateState.CLOSED


# ── 8. Integration ────────────────────────────────────────

class TestIntegration:
    def test_full_pipeline(self):
        """完整变焦管道"""
        engine = LensZoomEngine()

        # 负载均衡
        lb = LoadBalancer()
        lb.register_node("n1", capacity=1.0)
        lb.register_node("n2", capacity=0.8)

        # 节奏调度
        scheduler = RhythmScheduler()

        # 高负载场景
        state = engine.auto_zoom(load_level=0.85, confidence=0.6)
        assert state.mode == ZoomMode.SPECULATIVE

        units = [
            CognitiveUnit(
                unit_id=f"u{i}", name=f"unit{i}", module_path="test",
                coordinates=TBCECoordinates.default(),
                cognitive_layer=i % 8 + 1, psi_operator="EmbeddingProvider",
            )
            for i in range(5)
        ]
        balance = lb.balance(units)
        assert balance.total_units == 5

        candidates = [{"confidence": 0.9} for _ in range(4)]
        rhythm = scheduler.schedule(candidates)
        assert rhythm.speedup_ratio > 1.0

    def test_zoom_ring_full_cycle(self):
        """变焦环完整周期"""
        ring = ZoomRing()

        # NORMAL → WIDE
        ring.transition(ZoomMode.WIDE)
        assert ring.get_state().mode == ZoomMode.WIDE

        # WIDE → NORMAL
        ring.transition(ZoomMode.NORMAL)
        assert ring.get_state().mode == ZoomMode.NORMAL

        # NORMAL → TELE
        ring.transition(ZoomMode.TELE)
        assert ring.get_state().mode == ZoomMode.TELE

        # TELE → NORMAL
        ring.transition(ZoomMode.NORMAL)
        assert ring.get_state().mode == ZoomMode.NORMAL

        assert ring.get_transition_count() == 4