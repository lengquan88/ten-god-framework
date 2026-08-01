"""
test_architecture_gate.py — ArchitectureGate 回归加固测试

覆盖：
  1. DependencyGraph（循环依赖/孤立节点/深度检测/健康度评分）
  2. ArchitectureGate（门禁裁决：阈值分级、证据/问题收集、模块路径加成）
  3. TwelveGodsGateManager（多数投票、太极否决、按五行过滤）

选择理由：architecture_gate.py 是十二神门禁体系中的"架构协同/攻防边界"
核心模块，实现了非平凡的 DFS 环检测、带记忆化的深度递归、分段评分与
多数投票逻辑，但当前仓库无任何测试覆盖。本文件聚焦解析/算法/边界分支，
避免快照式断言。
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.architecture_gate import (
    ArchitectureGate,
    DependencyGraph,
    TwelveGodsGateManager,
)
from tengod.tbce_unit import CognitiveUnit, GateState, TBCECoordinates
from tengod.twelve_gods_base import (
    FiveElements,
    GateVerdict,
    TwelveGods,
    TwelveGodsGate,
)


# ============================================================================
# 辅助
# ============================================================================


def _make_unit(
    unit_id="mod.a",
    module_path="tengod.mod_a",
    cognitive_layer=3,
    palace_id=5,
) -> CognitiveUnit:
    return CognitiveUnit(
        unit_id=unit_id,
        name="mod_a",
        module_path=module_path,
        coordinates=TBCECoordinates(
            S=0.9, T=0.5, P=0.8, C=0.7, I=0.6, E=0.4
        ),
        cognitive_layer=cognitive_layer,
        psi_operator="EmbeddingProvider",
        palace_id=palace_id,
    )


class _DummyGate(TwelveGodsGate):
    """用于测试管理器的最小门禁实现。"""

    def __init__(self, god: TwelveGods, verdict_state: str = GateState.OPEN,
                 score: float = 0.9):
        super().__init__(god)
        self._verdict_state = verdict_state
        self._score = score

    def _judge_impl(self, unit: CognitiveUnit) -> GateVerdict:
        return GateVerdict(
            god=self.god,
            state=self._verdict_state,
            score=self._score,
            reason="dummy",
            element=self.element,
        )


# ============================================================================
# 1. DependencyGraph
# ============================================================================


class TestDependencyGraphStructure:
    def test_add_node_initializes_both_maps(self):
        g = DependencyGraph()
        g.add_node("a")
        g.add_node("b")
        assert g.nodes["a"] == set()
        assert g.dependents["a"] == set()
        assert g.nodes["b"] == set()

    def test_add_edge_updates_directional_maps(self):
        g = DependencyGraph()
        g.add_edge("a", "b")
        assert "b" in g.nodes["a"]
        assert "a" in g.dependents["b"]
        # 反向不成立
        assert "a" not in g.nodes.get("b", set())

    def test_duplicate_edges_are_setlike(self):
        g = DependencyGraph()
        g.add_edge("a", "b")
        g.add_edge("a", "b")
        assert g.nodes["a"] == {"b"}


class TestDependencyIsolated:
    def test_all_nodes_isolated_when_no_edges(self):
        g = DependencyGraph()
        g.add_node("a")
        g.add_node("b")
        g.analyze()
        assert set(g.isolated) == {"a", "b"}

    def test_connected_nodes_not_isolated(self):
        g = DependencyGraph()
        g.add_edge("a", "b")
        g.analyze()
        assert g.isolated == []

    def test_partially_connected(self):
        g = DependencyGraph()
        g.add_edge("a", "b")
        g.add_node("c")
        g.analyze()
        assert g.isolated == ["c"]


class TestDependencyCycles:
    def test_self_loop_is_a_cycle(self):
        g = DependencyGraph()
        g.add_edge("a", "a")
        g.analyze()
        # 自身环应为一个 cycle
        assert any(set(c) == {"a"} for c in g.cycles)

    def test_two_node_cycle_detected(self):
        g = DependencyGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "a")
        g.analyze()
        assert len(g.cycles) >= 1
        flat = {n for c in g.cycles for n in c}
        assert "a" in flat and "b" in flat

    def test_three_node_cycle_detected(self):
        g = DependencyGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("c", "a")
        g.analyze()
        assert len(g.cycles) >= 1

    def test_no_cycle_in_dag(self):
        g = DependencyGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("a", "c")
        g.analyze()
        assert g.cycles == []

    def test_cycle_with_shared_prefix_reports_at_least_one(self):
        g = DependencyGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("c", "b")  # b-c-b 构成环
        g.analyze()
        assert len(g.cycles) >= 1


class TestDependencyMaxDepth:
    def test_empty_graph_depth_zero(self):
        g = DependencyGraph()
        g.analyze()
        assert g.max_depth == 0

    def test_single_node_no_deps_depth_zero(self):
        g = DependencyGraph()
        g.add_node("a")
        g.analyze()
        assert g.max_depth == 0

    def test_linear_chain_depth(self):
        g = DependencyGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("c", "d")
        g.analyze()
        # a->b->c->d => 深度 3
        assert g.max_depth == 3

    def test_fanout_depth_equals_max_branch(self):
        g = DependencyGraph()
        g.add_edge("root", "a")
        g.add_edge("root", "b")
        g.add_edge("a", "leaf")
        g.analyze()
        # root->a->leaf 深度 2，root->b 深度 1
        assert g.max_depth == 2

    def test_cycle_depth_does_not_infinite_loop(self):
        """回归：当图含环时 depth() 不应无限递归，应稳定落在有限值。"""
        g = DependencyGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "a")
        g.analyze()
        # 实现使用 memo + visiting 防环，执行必然在有限步内结束，
        # 深度值应为正整数（实现中按环长记为深度），且不会是 0 或负数
        assert g.max_depth >= 1
        assert isinstance(g.max_depth, int)


class TestDependencyHealthScore:
    def test_empty_graph_perfect_score(self):
        g = DependencyGraph()
        assert g.health_score() == 1.0

    def test_no_issues_near_perfect(self):
        g = DependencyGraph()
        g.add_edge("a", "b")
        g.analyze()
        assert g.health_score() == 1.0

    def test_isolated_penalty(self):
        g = DependencyGraph()
        g.add_node("a")
        g.add_node("b")
        g.analyze()
        # 2 个孤立节点，扣 2 * 0.05
        assert g.health_score() == 0.90

    def test_cycle_penalty(self):
        g = DependencyGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "a")
        g.analyze()
        # 1 个环扣 0.15
        assert g.health_score() == pytest.approx(0.85)

    def test_depth_penalty_over_5(self):
        g = DependencyGraph()
        # 6 层链式依赖
        for i in range(6):
            g.add_edge(f"n{i}", f"n{i+1}")
        g.analyze()
        # max_depth=6，超出 5 的部分扣 (6-5)*0.05
        assert g.health_score() == pytest.approx(0.95)

    def test_score_clamped_to_zero_one(self):
        g = DependencyGraph()
        # 刻意制造大量孤立节点与环，确认分数被钳制
        for i in range(30):
            g.add_node(f"n{i}")
        g.add_edge("c1", "c2")
        g.add_edge("c2", "c1")
        g.analyze()
        assert 0.0 <= g.health_score() <= 1.0


# ============================================================================
# 2. ArchitectureGate
# ============================================================================


class TestArchitectureGateBasic:
    def test_default_construction(self):
        gate = ArchitectureGate()
        assert gate.god == TwelveGods.BIJIAN
        assert gate.dependency_graph is not None

    def test_register_module_adds_node(self):
        gate = ArchitectureGate()
        gate.register_module("m1", dependencies=["m2", "m3"])
        assert "m1" in gate.dependency_graph.nodes
        assert "m2" in gate.dependency_graph.nodes
        assert "m3" in gate.dependency_graph.nodes
        assert "m2" in gate.dependency_graph.nodes["m1"]

    def test_register_module_no_deps(self):
        gate = ArchitectureGate()
        gate.register_module("m1")
        assert gate.dependency_graph.nodes["m1"] == set()


class TestArchitectureGateJudge:
    def test_gate_opens_for_healthy_graph_with_complete_unit(self):
        gate = ArchitectureGate()
        gate.register_module("a", dependencies=["b"])
        gate.register_module("b")
        unit = _make_unit(unit_id="a", module_path="tengod.a",
                          cognitive_layer=3, palace_id=5)
        verdict = gate.judge(unit)
        assert verdict.state == GateState.OPEN
        assert verdict.score >= ArchitectureGate.DEPS_HEALTH_OPEN
        assert "无循环依赖" in verdict.reason
        assert "所有模块已连接" in verdict.reason

    def test_gate_closes_when_cycle_and_missing_metadata(self):
        gate = ArchitectureGate()
        gate.register_module("a", dependencies=["b"])
        gate.register_module("b", dependencies=["a"])
        # 故意缺失 palace_id 与 cognitive_layer
        unit = _make_unit(unit_id="a", module_path="",
                          cognitive_layer=0, palace_id=None)
        verdict = gate.judge(unit)
        # 多条问题导致分数被大幅扣除，必然进入 closed 或 pending，
        # 本用例验证：至少识别出了环与缺失元数据
        assert "循环依赖" in verdict.reason
        # 分数低于 DEPS_HEALTH_OPEN
        assert verdict.score < ArchitectureGate.DEPS_HEALTH_OPEN

    def test_gate_pending_for_borderline_score(self):
        """当健康分在 [CLOSED, OPEN) 区间时应返回 PENDING。"""
        gate = ArchitectureGate()
        # 8 个孤立节点 -> 扣 0.40 -> 健康分 0.60
        # 再加上 gate 的问题惩罚，可落在 [0.40, 0.80) 的 PENDING 区间
        for i in range(8):
            gate.register_module(f"m{i}")
        unit = _make_unit(unit_id="m0", module_path="tengod.m0",
                          cognitive_layer=3, palace_id=5)
        verdict = gate.judge(unit)
        assert ArchitectureGate.DEPS_HEALTH_CLOSED <= verdict.score < ArchitectureGate.DEPS_HEALTH_OPEN
        assert verdict.state == GateState.PENDING

    def test_missing_palace_id_flagged(self):
        gate = ArchitectureGate()
        unit = _make_unit(palace_id=None, module_path="tengod.m")
        verdict = gate.judge(unit)
        assert "缺少门禁宫定位" in verdict.reason

    def test_missing_cognitive_layer_flagged(self):
        gate = ArchitectureGate()
        unit = _make_unit(cognitive_layer=0, palace_id=5,
                          module_path="tengod.m")
        verdict = gate.judge(unit)
        assert "认知层未定义" in verdict.reason

    def test_module_path_provides_small_boost(self):
        gate_no_path = ArchitectureGate()
        gate_no_path.register_module("m")
        u1 = _make_unit(module_path="", cognitive_layer=3, palace_id=5)
        v1 = gate_no_path.judge(u1)

        gate_with_path = ArchitectureGate()
        gate_with_path.register_module("m")
        u2 = _make_unit(module_path="tengod.m", cognitive_layer=3, palace_id=5)
        v2 = gate_with_path.judge(u2)

        assert v2.score == pytest.approx(v1.score + 0.05)


class TestArchitectureGateBuildGraph:
    def test_build_graph_from_module_list(self):
        gate = ArchitectureGate()
        modules = [
            {"module_path": "a", "dependencies": ["b"]},
            {"module_path": "b", "dependencies": ["c"]},
            {"module_path": "c", "dependencies": []},
        ]
        g = gate.build_dependency_graph(modules)
        assert set(g.nodes.keys()) == {"a", "b", "c"}
        assert g.max_depth == 2
        assert g.cycles == []

    def test_build_graph_handles_missing_keys(self):
        gate = ArchitectureGate()
        modules = [{"name": "only_name"}, {"module_path": "m1"}]
        g = gate.build_dependency_graph(modules)
        assert "only_name" in g.nodes
        assert "m1" in g.nodes


class TestArchitectureGateHealthReport:
    def test_get_dependency_health_returns_expected_keys(self):
        gate = ArchitectureGate()
        gate.register_module("a", dependencies=["b"])
        gate.register_module("b")
        report = gate.get_dependency_health()
        for key in ("total_nodes", "total_edges", "isolated",
                    "cycles", "max_depth", "health_score"):
            assert key in report
        assert report["total_nodes"] == 2
        assert report["total_edges"] == 1
        assert report["health_score"] == 1.0


# ============================================================================
# 3. TwelveGodsGateManager
# ============================================================================


class TestGateManagerRegistrationAndLookup:
    def test_register_and_get_gate(self):
        mgr = TwelveGodsGateManager()
        g = _DummyGate(TwelveGods.BIJIAN)
        mgr.register_gate(g)
        assert mgr.get_gate(TwelveGods.BIJIAN) is g
        # 未注册的神位返回 None
        assert mgr.get_gate(TwelveGods.SHANGGUAN) is None

    def test_get_all_gates_returns_copy(self):
        mgr = TwelveGodsGateManager()
        mgr.register_gate(_DummyGate(TwelveGods.BIJIAN))
        mgr.register_gate(_DummyGate(TwelveGods.JIECAI))
        all_gates = mgr.get_all_gates()
        assert len(all_gates) == 2
        all_gates.pop(TwelveGods.BIJIAN)
        # 不影响内部状态
        assert TwelveGods.BIJIAN in mgr.get_all_gates()

    def test_statistics_aggregates(self):
        mgr = TwelveGodsGateManager()
        g1 = _DummyGate(TwelveGods.BIJIAN)
        mgr.register_gate(g1)
        stats = mgr.get_statistics()
        # 至少包含已注册神位
        assert TwelveGods.BIJIAN.value in stats


class TestGateManagerJudgment:
    def test_judge_all_invokes_every_gate(self):
        mgr = TwelveGodsGateManager()
        mgr.register_gate(_DummyGate(TwelveGods.BIJIAN))
        mgr.register_gate(_DummyGate(TwelveGods.JIECAI))
        unit = _make_unit()
        results = mgr.judge_all(unit)
        assert set(results.keys()) == {TwelveGods.BIJIAN, TwelveGods.JIECAI}
        for v in results.values():
            assert v.state == GateState.OPEN

    def test_judge_by_element_filters_by_element(self):
        mgr = TwelveGodsGateManager()
        # 木
        mgr.register_gate(_DummyGate(TwelveGods.BIJIAN))
        mgr.register_gate(_DummyGate(TwelveGods.JIECAI))
        # 火
        mgr.register_gate(_DummyGate(TwelveGods.SHISHEN))
        unit = _make_unit()
        wood = mgr.judge_by_element(unit, FiveElements.WOOD)
        fire = mgr.judge_by_element(unit, FiveElements.FIRE)
        metal = mgr.judge_by_element(unit, FiveElements.METAL)
        assert set(wood.keys()) == {TwelveGods.BIJIAN, TwelveGods.JIECAI}
        assert set(fire.keys()) == {TwelveGods.SHISHEN}
        assert metal == {}


class TestGateManagerOverallState:
    def test_empty_verdicts_is_pending(self):
        mgr = TwelveGodsGateManager()
        assert mgr.get_overall_state({}) == GateState.PENDING

    def test_majority_open(self):
        mgr = TwelveGodsGateManager()
        verdicts = {
            TwelveGods.BIJIAN: GateVerdict(
                god=TwelveGods.BIJIAN, state=GateState.OPEN,
                score=0.9, reason="", element=FiveElements.WOOD,
            ),
            TwelveGods.JIECAI: GateVerdict(
                god=TwelveGods.JIECAI, state=GateState.OPEN,
                score=0.9, reason="", element=FiveElements.WOOD,
            ),
            TwelveGods.SHISHEN: GateVerdict(
                god=TwelveGods.SHISHEN, state=GateState.CLOSED,
                score=0.2, reason="", element=FiveElements.FIRE,
            ),
        }
        assert mgr.get_overall_state(verdicts) == GateState.OPEN

    def test_majority_closed(self):
        mgr = TwelveGodsGateManager()
        verdicts = {
            TwelveGods.BIJIAN: GateVerdict(
                god=TwelveGods.BIJIAN, state=GateState.CLOSED,
                score=0.2, reason="", element=FiveElements.WOOD,
            ),
            TwelveGods.JIECAI: GateVerdict(
                god=TwelveGods.JIECAI, state=GateState.CLOSED,
                score=0.2, reason="", element=FiveElements.WOOD,
            ),
            TwelveGods.SHISHEN: GateVerdict(
                god=TwelveGods.SHISHEN, state=GateState.OPEN,
                score=0.9, reason="", element=FiveElements.FIRE,
            ),
        }
        assert mgr.get_overall_state(verdicts) == GateState.CLOSED

    def test_taiji_veto_overrides_open_majority(self):
        """太极·元辰拥有否决权：即便多数 open，只要太极 CLOSED 则整体 CLOSED。"""
        mgr = TwelveGodsGateManager()
        verdicts = {
            TwelveGods.BIJIAN: GateVerdict(
                god=TwelveGods.BIJIAN, state=GateState.OPEN,
                score=0.9, reason="", element=FiveElements.WOOD,
            ),
            TwelveGods.JIECAI: GateVerdict(
                god=TwelveGods.JIECAI, state=GateState.OPEN,
                score=0.9, reason="", element=FiveElements.WOOD,
            ),
            TwelveGods.TAIJI: GateVerdict(
                god=TwelveGods.TAIJI, state=GateState.CLOSED,
                score=0.0, reason="", element=FiveElements.TRANSCENDENT,
            ),
        }
        assert mgr.get_overall_state(verdicts) == GateState.CLOSED

    def test_taiji_not_closed_does_not_veto(self):
        mgr = TwelveGodsGateManager()
        verdicts = {
            TwelveGods.BIJIAN: GateVerdict(
                god=TwelveGods.BIJIAN, state=GateState.OPEN,
                score=0.9, reason="", element=FiveElements.WOOD,
            ),
            TwelveGods.JIECAI: GateVerdict(
                god=TwelveGods.JIECAI, state=GateState.OPEN,
                score=0.9, reason="", element=FiveElements.WOOD,
            ),
            TwelveGods.TAIJI: GateVerdict(
                god=TwelveGods.TAIJI, state=GateState.PENDING,
                score=0.5, reason="", element=FiveElements.TRANSCENDENT,
            ),
        }
        assert mgr.get_overall_state(verdicts) == GateState.OPEN

    def test_tie_leads_to_pending(self):
        mgr = TwelveGodsGateManager()
        verdicts = {
            TwelveGods.BIJIAN: GateVerdict(
                god=TwelveGods.BIJIAN, state=GateState.OPEN,
                score=0.9, reason="", element=FiveElements.WOOD,
            ),
            TwelveGods.JIECAI: GateVerdict(
                god=TwelveGods.JIECAI, state=GateState.CLOSED,
                score=0.2, reason="", element=FiveElements.WOOD,
            ),
        }
        assert mgr.get_overall_state(verdicts) == GateState.PENDING
