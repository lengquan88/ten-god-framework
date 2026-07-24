"""
test_twelve_gods.py — 十二神门禁完整测试 Phase 1
"""
import pytest
import math
from unittest.mock import patch, MagicMock

from tengod.tbce_unit import TBCECoordinates, CognitiveUnit, GateState
from tengod.twelve_gods_base import (
    FiveElements, TwelveGods, GOD_ELEMENT_MAP, GOD_GATE_MAP,
    GateVerdict, TwelveGodsGate,
)
from tengod.architecture_gate import (
    DependencyGraph, ArchitectureGate, TwelveGodsGateManager,
)
from tengod.innovation_gate import InnovationMetrics, InnovationGate
from tengod.knowledge_gate import KnowledgeEntry, KnowledgeGate
from tengod.law_gate import SchedulingPolicy, SchedulingMetrics, LawGate
from tengod.nourish_gate import ConfigHealth, NourishGate
from tengod.self_referential_gate import SelfReferenceMetrics, SelfReferentialGate


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def sample_unit():
    return CognitiveUnit(
        unit_id="test.unit", name="test", module_path="test.module",
        coordinates=TBCECoordinates(S=0.9, T=0.5, P=0.8, C=0.8, I=0.8, E=0.2),
        cognitive_layer=5, psi_operator="ZuowangAttention", palace_id=5,
    )


@pytest.fixture
def low_unit():
    return CognitiveUnit(
        unit_id="test.low", name="low", module_path="test.low",
        coordinates=TBCECoordinates(S=0.2, T=0.3, P=0.2, C=0.2, I=0.2, E=0.9),
        cognitive_layer=1, psi_operator="EmbeddingProvider",
    )


# ── 1. FiveElements 五行生克 ───────────────────────────────

class TestFiveElements:
    def test_generates_cycle(self):
        assert FiveElements.WOOD.generates == FiveElements.FIRE
        assert FiveElements.FIRE.generates == FiveElements.EARTH
        assert FiveElements.EARTH.generates == FiveElements.METAL
        assert FiveElements.METAL.generates == FiveElements.WATER
        assert FiveElements.WATER.generates == FiveElements.WOOD

    def test_overcomes_cycle(self):
        assert FiveElements.WOOD.overcomes == FiveElements.EARTH
        assert FiveElements.FIRE.overcomes == FiveElements.METAL
        assert FiveElements.EARTH.overcomes == FiveElements.WATER
        assert FiveElements.METAL.overcomes == FiveElements.WOOD
        assert FiveElements.WATER.overcomes == FiveElements.FIRE

    def test_transcendent_no_generates(self):
        assert FiveElements.TRANSCENDENT.generates == FiveElements.TRANSCENDENT


# ── 2. TwelveGods 十二神映射 ───────────────────────────────

class TestTwelveGods:
    def test_all_gods_mapped(self):
        assert len(GOD_ELEMENT_MAP) == 12
        assert len(GOD_GATE_MAP) == 12

    def test_wood_gods(self):
        assert TwelveGods.BIJIAN.element == FiveElements.WOOD
        assert TwelveGods.JIECAI.element == FiveElements.WOOD
        assert TwelveGods.BIJIAN.gate_type == "architecture"

    def test_fire_gods(self):
        assert TwelveGods.SHISHEN.element == FiveElements.FIRE
        assert TwelveGods.SHANGGUAN.element == FiveElements.FIRE

    def test_earth_gods(self):
        assert TwelveGods.ZHENGCAI.element == FiveElements.EARTH
        assert TwelveGods.PIANCAI.element == FiveElements.EARTH

    def test_metal_gods(self):
        assert TwelveGods.ZHENGGUAN.element == FiveElements.METAL
        assert TwelveGods.QISHA.element == FiveElements.METAL

    def test_water_gods(self):
        assert TwelveGods.ZHENGYIN.element == FiveElements.WATER
        assert TwelveGods.PIANYIN.element == FiveElements.WATER

    def test_transcendent_gods(self):
        assert TwelveGods.TAIJI.element == FiveElements.TRANSCENDENT
        assert TwelveGods.YUANCHEN.element == FiveElements.TRANSCENDENT


# ── 3. GateVerdict ─────────────────────────────────────────

class TestGateVerdict:
    def test_create(self):
        v = GateVerdict(
            god=TwelveGods.BIJIAN,
            state=GateState.OPEN,
            score=0.9,
            reason="ok",
            element=FiveElements.WOOD,
        )
        assert v.god == TwelveGods.BIJIAN
        assert v.score == 0.9

    def test_to_dict(self):
        v = GateVerdict(
            god=TwelveGods.TAIJI,
            state=GateState.PENDING,
            score=0.5,
            reason="test",
            element=FiveElements.TRANSCENDENT,
        )
        d = v.to_dict()
        assert d["god"] == "太极"
        assert d["state"] == "pending"


# ── 4. DependencyGraph 依赖图 ──────────────────────────────

class TestDependencyGraph:
    def test_empty_graph(self):
        dg = DependencyGraph()
        dg.analyze()
        assert dg.health_score() == 1.0

    def test_isolated_detection(self):
        dg = DependencyGraph()
        dg.add_node("alone")
        dg.analyze()
        assert "alone" in dg.isolated
        assert dg.health_score() < 1.0

    def test_cycle_detection(self):
        dg = DependencyGraph()
        dg.add_edge("a", "b")
        dg.add_edge("b", "a")
        dg.analyze()
        assert len(dg.cycles) == 1

    def test_depth_calculation(self):
        dg = DependencyGraph()
        dg.add_edge("a", "b")
        dg.add_edge("b", "c")
        dg.add_edge("c", "d")
        dg.analyze()
        assert dg.max_depth == 3

    def test_health_with_cycles(self):
        dg = DependencyGraph()
        dg.add_edge("a", "b")
        dg.add_edge("b", "c")
        dg.add_edge("c", "a")
        dg.analyze()
        assert dg.health_score() < 0.9


# ── 5. ArchitectureGate 架构门禁 ───────────────────────────

class TestArchitectureGate:
    def test_judge_healthy(self, sample_unit):
        gate = ArchitectureGate()
        gate.register_module("core", dependencies=["utils"])
        gate.register_module("api", dependencies=["core"])
        gate.register_module("utils")
        v = gate.judge(sample_unit)
        assert v.state in (GateState.OPEN, GateState.PENDING)

    def test_dependency_health_report(self):
        gate = ArchitectureGate()
        gate.register_module("a", dependencies=["b"])
        gate.register_module("b")
        report = gate.get_dependency_health()
        assert report["total_nodes"] == 2
        assert report["health_score"] > 0.8

    def test_build_dependency_graph(self):
        gate = ArchitectureGate()
        modules = [
            {"module_path": "core", "dependencies": ["utils"]},
            {"module_path": "api", "dependencies": ["core"]},
            {"module_path": "utils", "dependencies": []},
        ]
        dg = gate.build_dependency_graph(modules)
        assert len(dg.nodes) == 3


# ── 6. InnovationGate 创新门禁 ─────────────────────────────

class TestInnovationGate:
    def test_shishen_open(self, sample_unit):
        gate = InnovationGate(TwelveGods.SHISHEN)
        v = gate.judge(sample_unit)
        assert v.state == GateState.OPEN

    def test_shangguan_high_risk(self, low_unit):
        gate = InnovationGate(TwelveGods.SHANGGUAN)
        v = gate.judge(low_unit)
        assert v.state in (GateState.PENDING, GateState.CLOSED)

    def test_metrics_extraction(self, sample_unit):
        gate = InnovationGate()
        metrics = gate._extract_metrics(sample_unit)
        assert metrics.creativity_score == sample_unit.coordinates.E
        assert metrics.quality_score == sample_unit.coordinates.S

    def test_avg_metrics(self, sample_unit):
        gate = InnovationGate()
        gate.judge(sample_unit)
        gate.judge(sample_unit)
        avg = gate.get_avg_metrics()
        assert avg is not None
        assert 0 <= avg.quality_score <= 1

    def test_metrics_history(self, sample_unit):
        gate = InnovationGate()
        gate.judge(sample_unit)
        assert len(gate.get_metrics_history()) == 1


# ── 7. KnowledgeGate 知识门禁 ──────────────────────────────

class TestKnowledgeGate:
    def test_store_knowledge(self):
        kg = KnowledgeGate()
        entry = kg.store_knowledge("e1", {"k": "v"}, "test", 0.8)
        assert entry.entry_id == "e1"
        assert entry.version == 1

    def test_conflict_detection(self):
        kg = KnowledgeGate()
        kg.store_knowledge("e1", {"k": "v1"}, "test")
        kg.store_knowledge("e1", {"k": "v2"}, "test")
        assert len(kg.get_conflicts()) == 1

    def test_zhengcai_open(self, sample_unit):
        kg = KnowledgeGate(TwelveGods.ZHENGCAI)
        v = kg.judge(sample_unit)
        assert v.state == GateState.OPEN

    def test_knowledge_stats(self):
        kg = KnowledgeGate()
        kg.store_knowledge("e1", {"k": "v"}, "test")
        stats = kg.get_knowledge_stats()
        assert stats["total_entries"] == 1

    def test_stale_detection(self):
        kg = KnowledgeGate()
        entry = kg.store_knowledge("e1", {"k": "v"}, "test")
        assert not entry.is_stale()


# ── 8. LawGate 法度门禁 ────────────────────────────────────

class TestLawGate:
    def test_policy_compliance(self):
        policy = SchedulingPolicy(policy_id="test", max_burst_size=4)
        metrics = SchedulingMetrics(burst_size=3, confidence=0.8, queue_depth=2)
        compliant, violations = policy.is_compliant(metrics)
        assert compliant is True
        assert len(violations) == 0

    def test_policy_violation(self):
        policy = SchedulingPolicy(policy_id="test", max_burst_size=4, max_queue_depth=10)
        metrics = SchedulingMetrics(burst_size=8, confidence=0.3, queue_depth=15, retries=5)
        compliant, violations = policy.is_compliant(metrics)
        assert compliant is False
        assert len(violations) >= 2

    def test_zhengguan_open(self, sample_unit):
        lg = LawGate(TwelveGods.ZHENGGUAN)
        v = lg.judge(sample_unit)
        assert v.state == GateState.OPEN

    def test_qisha_with_anomaly(self, low_unit):
        lg = LawGate(TwelveGods.QISHA)
        v = lg.judge(low_unit)
        assert v.state in (GateState.PENDING, GateState.CLOSED)

    def test_metrics_history(self, sample_unit):
        lg = LawGate()
        lg.judge(sample_unit)
        assert len(lg.get_metrics_history()) == 1


# ── 9. NourishGate 滋养门禁 ────────────────────────────────

class TestNourishGate:
    def test_zhengyin_open(self, sample_unit):
        ng = NourishGate(TwelveGods.ZHENGYIN)
        v = ng.judge(sample_unit)
        assert v.state == GateState.OPEN

    def test_pianyin_open(self, sample_unit):
        ng = NourishGate(TwelveGods.PIANYIN)
        v = ng.judge(sample_unit)
        assert v.state == GateState.OPEN

    def test_config_health(self, sample_unit):
        ng = NourishGate()
        health = ng._extract_health(sample_unit)
        assert health.completeness == sample_unit.coordinates.S
        assert 0 <= health.security_score <= 1

    def test_health_history(self, sample_unit):
        ng = NourishGate()
        ng.judge(sample_unit)
        assert len(ng.get_health_history()) == 1


# ── 10. SelfReferentialGate 自指涉门禁 ─────────────────────

class TestSelfReferentialGate:
    def test_taiji_open(self, sample_unit):
        srg = SelfReferentialGate(TwelveGods.TAIJI)
        srg.feed_gate_states({
            "arch": GateState.OPEN,
            "innov": GateState.PENDING,
            "know": GateState.OPEN,
        })
        v = srg.judge(sample_unit)
        assert v.state == GateState.OPEN

    def test_yuanchen_open(self, sample_unit):
        srg = SelfReferentialGate(TwelveGods.YUANCHEN)
        v = srg.judge(sample_unit)
        assert v.state == GateState.OPEN

    def test_blind_spot_detection(self, low_unit):
        srg = SelfReferentialGate()
        srg.judge(low_unit)
        metrics = srg.get_metrics_history()[-1]
        assert len(metrics.blind_spots) > 0

    def test_yin_yang_balance(self):
        srg = SelfReferentialGate()
        srg.feed_gate_states({
            "a": GateState.OPEN,
            "b": GateState.OPEN,
            "c": GateState.OPEN,
            "d": GateState.OPEN,
            "e": GateState.OPEN,
        })
        metrics = srg._extract_metrics(CognitiveUnit(
            unit_id="t", name="t", module_path="t",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1, psi_operator="e",
        ))
        # 全开 → 阴阳失衡
        assert metrics.yin_yang_balance < 0.7

    def test_balanced_yin_yang(self):
        srg = SelfReferentialGate()
        srg.feed_gate_states({
            "a": GateState.OPEN,
            "b": GateState.OPEN,
            "c": GateState.PENDING,
            "d": GateState.CLOSED,
            "e": GateState.CLOSED,
        })
        metrics = srg._extract_metrics(CognitiveUnit(
            unit_id="t", name="t", module_path="t",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1, psi_operator="e",
        ))
        assert metrics.yin_yang_balance > 0.5

    def test_origin_known(self, sample_unit):
        srg = SelfReferentialGate()
        metrics = srg._extract_metrics(sample_unit)
        assert metrics.origin_known is True

    def test_recursion_depth(self, sample_unit):
        srg = SelfReferentialGate()
        metrics = srg._extract_metrics(sample_unit)
        assert metrics.recursion_depth >= 1

    def test_blind_spots_report(self, sample_unit):
        srg = SelfReferentialGate()
        srg.judge(sample_unit)
        report = srg.get_blind_spots_report()
        assert "total_blind_spots" in report

    def test_veto_log(self, low_unit):
        srg = SelfReferentialGate(TwelveGods.TAIJI)
        srg.judge(low_unit)
        # 低质量单元可能触发否决
        vetos = srg.get_veto_log()
        assert isinstance(vetos, list)


# ── 11. TwelveGodsGateManager 十二神管理器 ─────────────────

class TestTwelveGodsGateManager:
    def test_register_and_judge(self, sample_unit):
        mgr = TwelveGodsGateManager()
        mgr.register_gate(ArchitectureGate(TwelveGods.BIJIAN))
        mgr.register_gate(InnovationGate(TwelveGods.SHISHEN))
        results = mgr.judge_all(sample_unit)
        assert len(results) == 2

    def test_overall_state_open(self, sample_unit):
        mgr = TwelveGodsGateManager()
        mgr.register_gate(ArchitectureGate(TwelveGods.BIJIAN))
        mgr.register_gate(InnovationGate(TwelveGods.SHISHEN))
        results = mgr.judge_all(sample_unit)
        overall = mgr.get_overall_state(results)
        assert overall == GateState.OPEN

    def test_judge_by_element(self, sample_unit):
        mgr = TwelveGodsGateManager()
        mgr.register_gate(ArchitectureGate(TwelveGods.BIJIAN))
        mgr.register_gate(InnovationGate(TwelveGods.SHISHEN))
        results = mgr.judge_by_element(sample_unit, FiveElements.WOOD)
        assert len(results) == 1
        assert TwelveGods.BIJIAN in results

    def test_get_gate(self):
        mgr = TwelveGodsGateManager()
        gate = ArchitectureGate()
        mgr.register_gate(gate)
        assert mgr.get_gate(TwelveGods.BIJIAN) is gate
        assert mgr.get_gate(TwelveGods.SHISHEN) is None

    def test_statistics(self):
        mgr = TwelveGodsGateManager()
        mgr.register_gate(ArchitectureGate(TwelveGods.BIJIAN))
        mgr.register_gate(InnovationGate(TwelveGods.SHISHEN))
        stats = mgr.get_statistics()
        assert "比肩" in stats
        assert "食神" in stats


# ── 12. 全十二神集成测试 ───────────────────────────────────

class TestFullTwelveGods:
    def test_all_twelve_gates_registered(self, sample_unit):
        mgr = TwelveGodsGateManager()
        mgr.register_gate(ArchitectureGate(TwelveGods.BIJIAN))
        mgr.register_gate(ArchitectureGate(TwelveGods.JIECAI))
        mgr.register_gate(InnovationGate(TwelveGods.SHISHEN))
        mgr.register_gate(InnovationGate(TwelveGods.SHANGGUAN))
        mgr.register_gate(KnowledgeGate(TwelveGods.ZHENGCAI))
        mgr.register_gate(KnowledgeGate(TwelveGods.PIANCAI))
        mgr.register_gate(LawGate(TwelveGods.ZHENGGUAN))
        mgr.register_gate(LawGate(TwelveGods.QISHA))
        mgr.register_gate(NourishGate(TwelveGods.ZHENGYIN))
        mgr.register_gate(NourishGate(TwelveGods.PIANYIN))
        mgr.register_gate(SelfReferentialGate(TwelveGods.TAIJI))
        mgr.register_gate(SelfReferentialGate(TwelveGods.YUANCHEN))

        results = mgr.judge_all(sample_unit)
        assert len(results) == 12

        overall = mgr.get_overall_state(results)
        assert overall == GateState.OPEN

    def test_element_boost_applied(self, sample_unit):
        gate = ArchitectureGate(TwelveGods.BIJIAN)
        v = gate.judge(sample_unit)
        # 五行生克加成应该被应用
        assert v.element_boost != 0.0 or v.element == FiveElements.TRANSCENDENT

    def test_base_gate_raises_not_implemented(self):
        base = TwelveGodsGate(TwelveGods.BIJIAN)
        unit = CognitiveUnit(
            unit_id="t", name="t", module_path="t",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1, psi_operator="e",
        )
        with pytest.raises(NotImplementedError):
            base._judge_impl(unit)

    def test_element_boost_wood_in_wood(self):
        """同五行 → 加成"""
        gate = ArchitectureGate(TwelveGods.BIJIAN)  # 木
        unit = CognitiveUnit(
            unit_id="t", name="t", module_path="t",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1, psi_operator="e",
            palace_id=3,  # 震三=木
        )
        boost = gate._compute_element_boost(unit)
        assert boost == 0.05  # 同五行

    def test_element_boost_fire_overcomes_metal(self):
        """火克金 → 克我"""
        gate = LawGate(TwelveGods.ZHENGGUAN)  # 金
        unit = CognitiveUnit(
            unit_id="t", name="t", module_path="t",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1, psi_operator="e",
            palace_id=9,  # 离九=火
        )
        boost = gate._compute_element_boost(unit)
        assert boost == -0.05  # 火克金 → 克我 → 削弱