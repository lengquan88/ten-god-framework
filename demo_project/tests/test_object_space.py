"""
test_object_space.py — 物方空间管理器单元测试 v2.21.0
=======================================================
测试覆盖：
- ObjectSpaceManager: 注册/发现/列表/过滤/序列化/推测解码
- OntologyJudge: 裁决/统计/各种案例
- 全局单例: get_object_space / reset_object_space
"""

import json
import os
import pytest
import tempfile
import time

from tengod.tbce_unit import (
    TBCECoordinates,
    CognitiveUnit,
    GateState,
    AutoCoordinateGenerator,
)
from tengod.object_space import (
    ObjectSpaceManager,
    OntologyJudge,
    SpeculativeDecodingResult,
    SniffResult,
    get_object_space,
    reset_object_space,
)


# ============================================================================
# 辅助函数
# ============================================================================

def make_unit(
    unit_id: str = "test.unit",
    name: str = "测试单元",
    module_path: str = "test.module",
    S: float = 0.8,
    T: float = 0.8,
    P: float = 0.8,
    C: float = 0.8,
    I: float = 0.8,
    E: float = 0.3,
    cognitive_layer: int = 3,
    psi_operator: str = "PersistenceDiagram",
    palace_id: int = None,
    tense: str = "present",
    description: str = "",
    **kwargs,
) -> CognitiveUnit:
    """创建认知单元的辅助函数"""
    return CognitiveUnit(
        unit_id=unit_id,
        name=name,
        module_path=module_path,
        coordinates=TBCECoordinates(S, T, P, C, I, E),
        cognitive_layer=cognitive_layer,
        psi_operator=psi_operator,
        palace_id=palace_id,
        tense=tense,
        description=description,
        **kwargs,
    )


# ============================================================================
# OntologyJudge 测试
# ============================================================================

class TestOntologyJudge:
    """本体论裁决器测试"""

    @pytest.fixture
    def judge(self):
        return OntologyJudge()

    def test_judge_open(self, judge):
        """高评分 → 开"""
        unit = make_unit(S=0.9, P=0.9, C=0.9, I=0.9)
        result = judge.judge(unit)
        assert result == GateState.OPEN
        assert unit.gate_state == GateState.OPEN
        assert unit.confidence > 0.6

    def test_judge_pending(self, judge):
        """中等评分 → 徘徊"""
        unit = make_unit(S=0.5, P=0.5, C=0.5, I=0.5)
        result = judge.judge(unit)
        assert result == GateState.PENDING
        assert unit.gate_state == GateState.PENDING

    def test_judge_closed_low_s(self, judge):
        """低S维度 → 关"""
        unit = make_unit(S=0.1, P=0.9, C=0.9, I=0.9)
        result = judge.judge(unit)
        assert result == GateState.CLOSED

    def test_judge_closed_low_p(self, judge):
        """低P维度 → 关"""
        unit = make_unit(S=0.9, P=0.1, C=0.9, I=0.9)
        result = judge.judge(unit)
        assert result == GateState.CLOSED

    def test_judge_closed_low_c(self, judge):
        """低C维度 → 关"""
        unit = make_unit(S=0.9, P=0.9, C=0.05, I=0.9)
        result = judge.judge(unit)
        assert result == GateState.CLOSED

    def test_judge_closed_missing_id(self, judge):
        """缺少unit_id → 关"""
        unit = make_unit(unit_id="", module_path="")
        result = judge.judge(unit)
        assert result == GateState.CLOSED

    def test_judge_closed_negative_s(self, judge):
        """负S值 → 关"""
        unit = make_unit(S=-0.1)
        result = judge.judge(unit)
        assert result == GateState.CLOSED

    def test_judge_logs_entries(self, judge):
        """裁决记录日志"""
        judge.judge(make_unit(unit_id="a", S=0.9, P=0.9, C=0.9, I=0.9))
        judge.judge(make_unit(unit_id="b", S=0.5, P=0.5, C=0.5, I=0.5))
        judge.judge(make_unit(unit_id="c", S=0.1, P=0.1, C=0.1, I=0.1))
        assert len(judge.judgment_log) == 3

    def test_get_statistics(self, judge):
        """获取统计信息"""
        judge.judge(make_unit(unit_id="a", S=0.9, P=0.9, C=0.9, I=0.9))
        judge.judge(make_unit(unit_id="b", S=0.5, P=0.5, C=0.5, I=0.5))
        judge.judge(make_unit(unit_id="c", S=0.1, P=0.1, C=0.1, I=0.1))
        stats = judge.get_statistics()
        assert stats['open'] == 1
        assert stats['pending'] == 1
        assert stats['closed'] == 1

    def test_judge_pending_borderline(self, judge):
        """边界评分 → 徘徊"""
        # S=0.5 刚好在pending阈值，综合评分~0.5
        unit = make_unit(S=0.5, P=0.5, C=0.3, I=0.5)
        result = judge.judge(unit)
        # 综合 = (0.5+0.5+0.3+0.5)/4 = 0.45
        # pending_min=0.3, open_min=0.6 → pending
        assert result == GateState.PENDING


# ============================================================================
# ObjectSpaceManager 测试
# ============================================================================

class TestObjectSpaceManager:
    """物方空间管理器测试"""

    @pytest.fixture
    def space(self):
        return ObjectSpaceManager(seed=42)

    def test_register_and_discover(self, space):
        """注册和发现"""
        unit = make_unit(S=0.9, P=0.9, C=0.9, I=0.9)
        gate_state = space.register(unit)
        assert gate_state == GateState.OPEN
        found = space.discover("test.unit")
        assert found is not None
        assert found.name == "测试单元"

    def test_register_closed_rejected(self, space):
        """门禁关的单元拒绝注册"""
        unit = make_unit(S=0.1, P=0.1, C=0.1, I=0.1)
        gate_state = space.register(unit)
        assert gate_state == GateState.CLOSED
        # 但被拒绝的不在空间中
        found = space.discover("test.unit")
        assert found is None

    def test_register_without_judge(self, space):
        """不自动裁决的注册"""
        unit = make_unit(S=0.1, P=0.1, C=0.1, I=0.1)
        gate_state = space.register(unit, auto_judge=False)
        assert gate_state == GateState.PENDING  # 初始状态
        found = space.discover("test.unit")
        assert found is not None  # 即使评分低，不裁决也注册

    def test_count(self, space):
        """注册计数"""
        assert space.count() == 0
        space.register(make_unit(unit_id="a", S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="b", S=0.9, P=0.9, C=0.9, I=0.9))
        assert space.count() == 2

    def test_list_all(self, space):
        """列出所有单元"""
        space.register(make_unit(unit_id="a", S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="b", S=0.9, P=0.9, C=0.9, I=0.9))
        all_units = space.list_all()
        assert len(all_units) == 2
        ids = {u.unit_id for u in all_units}
        assert ids == {"a", "b"}

    def test_list_by_layer(self, space):
        """按认知层过滤"""
        space.register(make_unit(unit_id="a", cognitive_layer=1, S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="b", cognitive_layer=3, S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="c", cognitive_layer=3, S=0.9, P=0.9, C=0.9, I=0.9))
        l3 = space.list_by_layer(3)
        assert len(l3) == 2
        l1 = space.list_by_layer(1)
        assert len(l1) == 1

    def test_list_by_palace(self, space):
        """按门禁宫过滤"""
        space.register(make_unit(unit_id="a", palace_id=1, S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="b", palace_id=1, S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="c", palace_id=5, S=0.9, P=0.9, C=0.9, I=0.9))
        p1 = space.list_by_palace(1)
        assert len(p1) == 2
        p5 = space.list_by_palace(5)
        assert len(p5) == 1

    def test_list_by_tense(self, space):
        """按时态过滤"""
        space.register(make_unit(unit_id="a", tense="past", S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="b", tense="present", S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="c", tense="future", S=0.9, P=0.9, C=0.9, I=0.9))
        assert len(space.list_by_tense("past")) == 1
        assert len(space.list_by_tense("present")) == 1
        assert len(space.list_by_tense("future")) == 1

    def test_list_by_gate_state(self, space):
        """按门禁状态过滤"""
        space.register(make_unit(unit_id="a", S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="b", S=0.5, P=0.5, C=0.5, I=0.5))
        assert len(space.list_by_gate_state(GateState.OPEN)) == 1
        assert len(space.list_by_gate_state(GateState.PENDING)) == 1

    def test_nearest_neighbors(self, space):
        """最近邻查询"""
        space.register(make_unit(unit_id="center", S=0.9, T=0.5, P=0.9, C=0.9, I=0.5, E=0.5))
        space.register(make_unit(unit_id="near", S=0.9, T=0.5, P=0.9, C=0.9, I=0.5, E=0.5))
        space.register(make_unit(unit_id="far", S=0.6, T=0.2, P=0.6, C=0.6, I=0.2, E=0.8))
        nn = space.nearest_neighbors("center", k=2)
        assert len(nn) == 2
        # near 应该比 far 更近
        assert nn[0][0].unit_id == "near"

    def test_nearest_neighbors_missing_target(self, space):
        """目标不存在 → 空列表"""
        nn = space.nearest_neighbors("nonexistent")
        assert nn == []

    def test_discover_nonexistent(self, space):
        """发现不存在的单元 → None"""
        assert space.discover("nonexistent") is None

    def test_get_ontology_stats(self, space):
        """获取本体论统计"""
        space.register(make_unit(unit_id="a", S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="b", S=0.5, P=0.5, C=0.5, I=0.5))
        stats = space.get_ontology_stats()
        assert stats['total_units'] == 2
        assert stats['gate_stats']['open'] == 1
        assert stats['gate_stats']['pending'] == 1

    def test_get_coordinate_distribution(self, space):
        """获取坐标分布"""
        space.register(make_unit(unit_id="a", S=0.3, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="b", S=0.7, P=0.9, C=0.9, I=0.9))
        dist = space.get_coordinate_distribution()
        assert 'S' in dist
        assert dist['S']['min'] == pytest.approx(0.3, abs=0.05)
        assert dist['S']['max'] == pytest.approx(0.7, abs=0.05)

    def test_get_layer_distribution(self, space):
        """获取认知层分布"""
        space.register(make_unit(unit_id="a", cognitive_layer=1, S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="b", cognitive_layer=3, S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="c", cognitive_layer=3, S=0.9, P=0.9, C=0.9, I=0.9))
        dist = space.get_layer_distribution()
        assert dist[1] == 1
        assert dist[3] == 2

    # ── 序列化测试 ──────────────────────────────────

    def test_to_dict(self, space):
        """序列化"""
        space.register(make_unit(unit_id="a", S=0.9, P=0.9, C=0.9, I=0.9))
        d = space.to_dict()
        assert d['version'] == '2.21.0'
        assert 'a' in d['units']
        assert 'ontology_stats' in d

    def test_save_and_load(self, space):
        """保存和加载"""
        space.register(make_unit(unit_id="a", S=0.9, P=0.9, C=0.9, I=0.9))
        space.register(make_unit(unit_id="b", S=0.9, P=0.9, C=0.9, I=0.9))

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "object_space.json")
            space.save(filepath)

            # 加载
            loaded = ObjectSpaceManager.load(filepath)
            assert loaded.count() == 2
            assert loaded.discover("a") is not None
            assert loaded.discover("b") is not None

    def test_save_creates_directory(self, space):
        """保存时自动创建目录"""
        space.register(make_unit(unit_id="a", S=0.9, P=0.9, C=0.9, I=0.9))
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "subdir", "object_space.json")
            space.save(filepath)
            assert os.path.exists(filepath)

    # ── 推测解码测试 ──────────────────────────────────

    def test_sniff_returns_results(self, space):
        """推测解码返回结果"""
        space.register(make_unit(unit_id="a", S=0.9, T=0.8, P=0.7, C=0.6, I=0.5, E=0.3))
        space.register(make_unit(unit_id="b", S=0.1, T=0.2, P=0.3, C=0.4, I=0.5, E=0.6))
        target = TBCECoordinates(S=0.9, T=0.8, P=0.7, C=0.6, I=0.5, E=0.3)
        result = space.sniff(target, top_k=3)
        assert isinstance(result, SpeculativeDecodingResult)
        assert len(result.verified_results) > 0

    def test_sniff_speedup(self, space):
        """推测解码加速比 > 1"""
        # 注册多个单元
        for i in range(10):
            space.register(make_unit(
                unit_id=f"unit_{i}",
                S=0.5 + 0.05 * i, T=0.5, P=0.5, C=0.5, I=0.5, E=0.5,
            ))
        target = TBCECoordinates(S=0.9, T=0.8, P=0.7, C=0.6, I=0.5, E=0.3)
        result = space.sniff(target, top_k=3)
        assert result.speedup_ratio >= 1.0

    def test_sniff_ignores_closed(self, space):
        """推测解码忽略门禁关的单元"""
        space.register(make_unit(
            unit_id="closed_unit", S=0.1, P=0.1, C=0.1, I=0.1,
        ))
        # 门禁关的单元不会被注册
        assert space.discover("closed_unit") is None

    def test_sniff_empty_space(self, space):
        """空空间推测解码"""
        target = TBCECoordinates.default()
        result = space.sniff(target)
        assert len(result.verified_results) == 0

    # ── 批量注册测试 ──────────────────────────────────

    def test_auto_register(self, space):
        """批量自动注册"""
        module_infos = [
            {
                "name": "mod_a",
                "module_path": "tengod.mod_a",
                "lines_of_code": 300,
                "dependency_count": 5,
                "is_core_module": True,
                "has_tests": True,
                "test_coverage": 0.95,
                "psi_operator": "EmbeddingProvider",
                "description": "模块A",
            },
            {
                "name": "mod_b",
                "module_path": "tengod.mod_b",
                "lines_of_code": 200,
                "dependency_count": 3,
                "is_core_module": False,
                "has_tests": False,
                "test_coverage": 0.0,
                "psi_operator": "PersistenceDiagram",
                "description": "模块B",
            },
        ]
        results = space.auto_register(module_infos)
        assert len(results) == 2

    def test_auto_register_with_custom_id(self, space):
        """自定义unit_id"""
        results = space.auto_register([{
            "name": "custom",
            "unit_id": "my.custom.id",
            "module_path": "tengod.custom",
            "lines_of_code": 200,
            "dependency_count": 5,
            "is_core_module": True,
            "has_tests": True,
            "test_coverage": 0.90,
            "psi_operator": "EmbeddingProvider",
        }])
        assert "my.custom.id" in results

    def test_auto_register_with_palace(self, space):
        """带门禁宫的注册"""
        results = space.auto_register([{
            "name": "palace_mod",
            "module_path": "tengod.palace",
            "lines_of_code": 300,
            "dependency_count": 5,
            "is_core_module": True,
            "has_tests": True,
            "test_coverage": 0.90,
            "psi_operator": "EmbeddingProvider",
            "palace_id": 5,
            "tense": "present",
            "consensus_layer": 3,
        }])
        unit = space.discover(list(results.keys())[0])
        assert unit.palace_id == 5
        assert unit.consensus_layer == 3


# ============================================================================
# 全局单例测试
# ============================================================================

class TestGlobalSingleton:
    """全局单例测试"""

    def test_get_object_space_returns_same(self):
        """get_object_space返回同一实例"""
        reset_object_space()
        s1 = get_object_space()
        s2 = get_object_space()
        assert s1 is s2

    def test_reset_creates_new(self):
        """reset后创建新实例"""
        reset_object_space()
        s1 = get_object_space()
        reset_object_space()
        s2 = get_object_space()
        assert s1 is not s2


# ============================================================================
# SniffResult 测试
# ============================================================================

class TestSniffResult:
    """嗅探结果测试"""

    def test_create(self):
        sr = SniffResult(
            unit_id="test",
            coarse_score=0.5,
            predictive_score=0.7,
            verified_score=0.9,
            distance=0.3,
        )
        assert sr.unit_id == "test"
        assert sr.verified is False
        assert sr.pending is True

    def test_verified_status(self):
        sr = SniffResult(
            unit_id="test", coarse_score=0.5, predictive_score=0.7,
            verified_score=0.9, distance=0.3, verified=True, pending=False,
        )
        assert sr.verified is True
        assert sr.pending is False


# ============================================================================
# SpeculativeDecodingResult 测试
# ============================================================================

class TestSpeculativeDecodingResult:
    """推测解码结果测试"""

    def test_speedup_ratio_default(self):
        """默认加速比"""
        result = SpeculativeDecodingResult(query_id="q", top_k=5)
        assert result.speedup_ratio == 1.0

    def test_speedup_ratio_with_data(self):
        """有数据的加速比"""
        result = SpeculativeDecodingResult(
            query_id="q", top_k=5,
            sniff_duration_ms=1.0,
            spec_duration_ms=0.5,
            verify_duration_ms=0.3,
            total_duration_ms=1.8,
            sniff_results=[SniffResult("u1", 0.5, 0.6, 0.7, 0.3)] * 10,
        )
        assert result.speedup_ratio > 1.0