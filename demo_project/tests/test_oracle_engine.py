"""
test_oracle_engine.py — 推背图Oracle引擎 + 拓扑发现 + 认识论裁决器测试 v2.22.0
===========================================================================
"""
import math
import pytest
import time

from tengod.tbce_unit import (
    TBCECoordinates,
    CognitiveUnit,
    GateState,
    AutoCoordinateGenerator,
)
from tengod.object_space import (
    ObjectSpaceManager,
    reset_object_space,
    get_object_space,
)
from tengod.oracle_engine import (
    Tense,
    OracleImage,
    OracleText,
    OracleProphecy,
    FullOracle,
    IsomorphismCalculator,
    TuibeiOracle,
    TopologyFeature,
    TopologyDiscovery,
    EpistemologyJudge,
    get_oracle_engine,
    get_topology_discovery,
    get_epistemology_judge,
    reset_oracle_engine,
)
from tengod.module_registry import register_all_modules


def make_unit(
    unit_id: str = "test.unit",
    S: float = 0.8, T: float = 0.8, P: float = 0.8, C: float = 0.8, I: float = 0.8, E: float = 0.3,
    cognitive_layer: int = 3, psi_operator: str = "PersistenceDiagram",
    palace_id: int = None, tense: str = "present",
    **kwargs,
) -> CognitiveUnit:
    return CognitiveUnit(
        unit_id=unit_id, name=unit_id, module_path=f"tengod.{unit_id}",
        coordinates=TBCECoordinates(S, T, P, C, I, E),
        cognitive_layer=cognitive_layer, psi_operator=psi_operator,
        palace_id=palace_id, tense=tense,
    )


# ============================================================================
# Tense 测试
# ============================================================================

class TestTense:
    def test_all(self):
        assert Tense.all() == ["past", "present", "future"]


# ============================================================================
# OracleImage / OracleText / OracleProphecy 测试
# ============================================================================

class TestOracleStructures:
    def test_image_create(self):
        img = OracleImage("测试结构", 0.85, "tree")
        assert img.description == "测试结构"
        assert img.isomorphism == 0.85
        assert img.structure_type == "tree"

    def test_text_create(self):
        text = OracleText("测试箴言", 0.75, ["要点1", "要点2"])
        assert text.content == "测试箴言"
        assert text.confidence == 0.75
        assert len(text.key_points) == 2

    def test_prophecy_create(self):
        prop = OracleProphecy("测试预言", 0.65, "注意风险")
        assert prop.prediction == "测试预言"
        assert prop.probability == 0.65
        assert prop.warning == "注意风险"

    def test_prophecy_no_warning(self):
        prop = OracleProphecy("测试预言", 0.65, None)
        assert prop.warning is None


# ============================================================================
# FullOracle 测试
# ============================================================================

class TestFullOracle:
    def test_create(self):
        oracle = FullOracle(
            unit_id="test", tense="present",
            image=OracleImage("结构", 0.8, "tree"),
            text=OracleText("箴言", 0.7, []),
            prophecy=OracleProphecy("预言", 0.6, None),
        )
        assert oracle.unit_id == "test"
        assert oracle.tense == "present"
        assert oracle.pending is False

    def test_calculate_confidence(self):
        oracle = FullOracle(
            unit_id="test", tense="present",
            image=OracleImage("结构", 0.8, "tree"),
            text=OracleText("箴言", 0.7, []),
            prophecy=OracleProphecy("预言", 0.6, None),
        )
        conf = oracle.calculate_confidence()
        expected = 0.8 * 0.3 + 0.7 * 0.3 + 0.6 * 0.4
        assert abs(conf - expected) < 1e-6

    def test_to_dict(self):
        oracle = FullOracle(
            unit_id="test", tense="present",
            image=OracleImage("结构", 0.8, "tree"),
            text=OracleText("箴言", 0.7, ["要点"]),
            prophecy=OracleProphecy("预言", 0.6, "注意"),
        )
        oracle.calculate_confidence()
        d = oracle.to_dict()
        assert d['unit_id'] == "test"
        assert d['image']['isomorphism'] == 0.8
        assert d['text']['key_points'] == ["要点"]
        assert d['prophecy']['warning'] == "注意"


# ============================================================================
# IsomorphismCalculator 测试
# ============================================================================

class TestIsomorphismCalculator:
    @pytest.fixture
    def calc(self):
        return IsomorphismCalculator()

    def test_same_unit(self, calc):
        unit = make_unit(S=0.8, P=0.8, C=0.8, I=0.8)
        iso = calc.calculate(unit, unit)
        assert iso == 0.985  # 同单元 → 同构度 = 深泉常数

    def test_different_units(self, calc):
        u1 = make_unit(unit_id="a", S=0.8, P=0.8, C=0.8, I=0.8)
        u2 = make_unit(unit_id="b", S=0.2, P=0.2, C=0.2, I=0.2)
        iso = calc.calculate(u1, u2)
        assert 0 < iso < 0.985

    def test_batch_calculate(self, calc):
        units = [make_unit(unit_id=f"u{i}", S=0.5, P=0.5, C=0.5, I=0.5) for i in range(3)]
        target = make_unit(unit_id="t", S=0.5, P=0.5, C=0.5, I=0.5)
        results = calc.batch_calculate(units, target)
        assert len(results) == 3
        # 排序：同构度从高到低
        assert results[0][1] >= results[1][1] >= results[2][1]


# ============================================================================
# TuibeiOracle 测试
# ============================================================================

class TestTuibeiOracle:
    @pytest.fixture
    def space(self):
        reset_object_space()
        reset_oracle_engine()
        s = ObjectSpaceManager(seed=42)
        # 注册几个测试单元
        for i in range(5):
            u = make_unit(
                unit_id=f"test_mod_{i}",
                S=0.7 + 0.05 * i, T=0.5, P=0.7, C=0.7, I=0.7, E=0.3,
                tense="present" if i < 3 else "past",
            )
            s.register(u, auto_judge=False)
        return s

    @pytest.fixture
    def oracle(self, space):
        return TuibeiOracle(space)

    def test_project_single_tense(self, oracle):
        result = oracle.project_single_tense("test_mod_0", "present")
        assert result.unit_id == "test_mod_0"
        assert result.tense == "present"
        assert result.image is not None
        assert result.text is not None
        assert result.prophecy is not None
        assert 0 <= result.confidence <= 1

    def test_project_nonexistent(self, oracle):
        result = oracle.project_single_tense("nonexistent", "present")
        assert result.confidence == 0.0
        assert result.image.isomorphism == 0.0

    def test_project_three_tense(self, oracle):
        results = oracle.project_three_tense("test_mod_0")
        assert "past" in results
        assert "present" in results
        assert "future" in results
        assert results["present"].confidence > 0

    def test_three_tense_confidence_range(self, oracle):
        results = oracle.project_three_tense("test_mod_0")
        for tense, o in results.items():
            assert 0 <= o.confidence <= 1

    def test_find_high_confidence(self, oracle):
        # 先投影
        oracle.project_three_tense("test_mod_0")
        oracle.project_three_tense("test_mod_1")
        high = oracle.find_high_confidence(min_confidence=0.0)
        # 所有投影都应被找到
        assert len(high) >= 2

    def test_find_pending(self, oracle):
        oracle.project_three_tense("test_mod_0")
        oracle.project_three_tense("test_mod_1")
        pending = oracle.find_pending()
        assert isinstance(pending, list)

    def test_get_statistics(self, oracle):
        oracle.project_three_tense("test_mod_0")
        stats = oracle.get_statistics()
        assert stats['total_oracles'] == 3
        assert stats['by_tense']['past'] == 1
        assert stats['by_tense']['present'] == 1
        assert stats['by_tense']['future'] == 1


# ============================================================================
# TopologyFeature / TopologyDiscovery 测试
# ============================================================================

class TestTopologyFeature:
    def test_create(self):
        f = TopologyFeature(
            dimension=0, birth=0.5, death=1.0, persistence=0.5,
            connected_units=["a", "b", "c"],
        )
        assert f.dimension == 0
        assert f.connected_units == ["a", "b", "c"]


class TestTopologyDiscovery:
    @pytest.fixture
    def space(self):
        reset_object_space()
        s = ObjectSpaceManager(seed=42)
        # 注册几个单元，确保它们通过门禁
        for i in range(10):
            u = make_unit(
                unit_id=f"topo_{i}",
                S=0.8, T=0.5 + 0.05 * i, P=0.8, C=0.8, I=0.8, E=0.3,
            )
            s.register(u, auto_judge=False)
        return s

    def test_discover_h0(self, space):
        topo = TopologyDiscovery(space, distance_threshold=1.5)
        h0 = topo.discover_h0()
        assert isinstance(h0, list)

    def test_discover_h1(self, space):
        topo = TopologyDiscovery(space, distance_threshold=1.5)
        h1 = topo.discover_h1()
        assert isinstance(h1, list)

    def test_get_all_features(self, space):
        topo = TopologyDiscovery(space, distance_threshold=1.5)
        feats = topo.get_all_features()
        assert 0 in feats
        assert 1 in feats

    def test_h0_with_tight_threshold(self, space):
        topo = TopologyDiscovery(space, distance_threshold=0.1)
        h0 = topo.discover_h0()
        # 紧密阈值 → 几乎无连通分量
        assert all(len(f.connected_units) >= 2 for f in h0)

    def test_print_summary(self, space):
        topo = TopologyDiscovery(space)
        # 不抛异常
        topo.print_summary()


# ============================================================================
# EpistemologyJudge 测试
# ============================================================================

class TestEpistemologyJudge:
    @pytest.fixture
    def judge(self):
        return EpistemologyJudge()

    def test_judge_open(self, judge):
        unit = make_unit(S=0.9, P=0.9, C=0.9, I=0.9, E=0.1)
        state = judge.judge(unit)
        assert state == GateState.OPEN

    def test_judge_pending(self, judge):
        unit = make_unit(S=0.5, P=0.5, C=0.5, I=0.5, E=0.5)
        state = judge.judge(unit)
        assert state == GateState.PENDING

    def test_judge_closed(self, judge):
        unit = make_unit(S=0.2, P=0.2, C=0.2, I=0.2, E=0.9)
        state = judge.judge(unit)
        assert state == GateState.CLOSED

    def test_edge_penalty(self, judge):
        # 高E值时，得分降低
        unit_high_e = make_unit(S=0.8, P=0.8, C=0.8, I=0.8, E=0.9)
        unit_low_e = make_unit(S=0.8, P=0.8, C=0.8, I=0.8, E=0.1)
        # 高E的得分应该更低（因为边界惩罚）
        state_high = judge.judge(unit_high_e)
        state_low = judge.judge(unit_low_e)
        # 至少高E不应该比低E更好
        # 注意：都是open是可能的，但高E不应该是closed而低E是open
        if state_high == GateState.CLOSED:
            assert state_low == GateState.CLOSED

    def test_adaptive_scale(self, judge):
        unit = make_unit(E=0.8)
        scale = judge.adaptive_scale(unit)
        assert scale > 1.0

    def test_adaptive_scale_low_edge(self, judge):
        unit = make_unit(E=0.0)
        scale = judge.adaptive_scale(unit)
        assert scale == 1.0

    def test_get_statistics(self, judge):
        judge.judge(make_unit(unit_id="a", S=0.9, P=0.9, C=0.9, I=0.9, E=0.1))
        judge.judge(make_unit(unit_id="b", S=0.5, P=0.5, C=0.5, I=0.5, E=0.5))
        judge.judge(make_unit(unit_id="c", S=0.2, P=0.2, C=0.2, I=0.2, E=0.9))
        stats = judge.get_statistics()
        assert stats['open'] == 1
        assert stats['pending'] == 1
        assert stats['closed'] == 1


# ============================================================================
# 全局单例测试
# ============================================================================

class TestGlobalInstances:
    @pytest.fixture(autouse=True)
    def reset(self):
        reset_object_space()
        reset_oracle_engine()
        yield
        reset_object_space()
        reset_oracle_engine()

    def test_oracle_singleton(self):
        o1 = get_oracle_engine()
        o2 = get_oracle_engine()
        assert o1 is o2

    def test_topology_singleton(self):
        t1 = get_topology_discovery()
        t2 = get_topology_discovery()
        assert t1 is t2

    def test_epistemology_singleton(self):
        e1 = get_epistemology_judge()
        e2 = get_epistemology_judge()
        assert e1 is e2

    def test_reset_oracle(self):
        o1 = get_oracle_engine()
        reset_oracle_engine()
        o2 = get_oracle_engine()
        assert o1 is not o2


# ============================================================================
# 集成测试：Oracle + 全量注册表
# ============================================================================

class TestOracleIntegration:
    @pytest.fixture(autouse=True)
    def reset(self):
        reset_object_space()
        reset_oracle_engine()
        yield
        reset_object_space()
        reset_oracle_engine()

    def test_oracle_on_full_registry(self):
        """全量注册表上的Oracle投影"""
        space = get_object_space()
        register_all_modules(space)
        oracle = TuibeiOracle(space)

        # 找第一个注册的单元
        units = space.list_all()
        if units:
            results = oracle.project_three_tense(units[0].unit_id)
            assert len(results) == 3
            for tense, o in results.items():
                assert 0 <= o.confidence <= 1

    def test_topology_on_full_registry(self):
        """全量注册表上的拓扑发现"""
        space = get_object_space()
        register_all_modules(space)
        topo = TopologyDiscovery(space, distance_threshold=1.5)
        feats = topo.get_all_features()
        assert 0 in feats
        assert 1 in feats

    def test_epistemology_on_full_registry(self):
        """全量注册表上的认识论裁决"""
        space = get_object_space()
        register_all_modules(space)
        judge = EpistemologyJudge()

        for unit in space.list_all()[:5]:
            state = judge.judge(unit)
            assert state in [GateState.OPEN, GateState.PENDING, GateState.CLOSED]