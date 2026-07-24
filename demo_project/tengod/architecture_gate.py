"""
architecture_gate.py — 架构门禁 (比肩·劫财 / 木) v4.6.0
=============================================================
比肩·架构协同：模块间依赖是否健康？
劫财·攻防边界：系统边界是否安全？

五行属性：木
木生火（架构支撑创新）
木克土（架构约束知识）
金克木（品质裁决约束架构）

裁决维度：
  1. 依赖图健康度：循环依赖、过度耦合、孤立模块
  2. 模块边界清晰度：接口定义、职责单一
  3. 架构稳定性：core模块变更频率、依赖链深度
  4. 安全边界：模块权限、数据隔离

与七论裁决器的集成：
  - 本体论：架构是否存在？
  - 实践论：架构是否可落地？
  - 境界论：架构是否提升系统层次？
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import time

from .tbce_unit import CognitiveUnit, GateState, TBCECoordinates
from .twelve_gods_base import (
    TwelveGods, FiveElements, GateVerdict, TwelveGodsGate,
)


# ============================================================================
# 依赖图分析
# ============================================================================

@dataclass
class DependencyGraph:
    """模块依赖图"""
    nodes: Dict[str, Set[str]] = field(default_factory=dict)  # node → dependencies
    dependents: Dict[str, Set[str]] = field(default_factory=dict)  # node → dependents
    isolated: List[str] = field(default_factory=list)  # 孤立模块
    cycles: List[List[str]] = field(default_factory=list)  # 循环依赖
    max_depth: int = 0  # 最大依赖深度

    def add_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            self.nodes[node_id] = set()
            self.dependents[node_id] = set()

    def add_edge(self, from_node: str, to_node: str) -> None:
        self.add_node(from_node)
        self.add_node(to_node)
        self.nodes[from_node].add(to_node)
        self.dependents[to_node].add(from_node)

    def analyze(self) -> None:
        """分析依赖图健康度"""
        self._find_isolated()
        self._find_cycles()
        self._calc_max_depth()

    def _find_isolated(self) -> None:
        self.isolated = []
        for node_id in self.nodes:
            deps = self.nodes.get(node_id, set())
            revs = self.dependents.get(node_id, set())
            if not deps and not revs:
                self.isolated.append(node_id)

    def _find_cycles(self) -> None:
        self.cycles = []
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in self.nodes}
        parent = {}

        def dfs_cycle(node: str):
            color[node] = GRAY
            for neighbor in self.nodes.get(node, set()):
                if color.get(neighbor, WHITE) == WHITE:
                    parent[neighbor] = node
                    dfs_cycle(neighbor)
                elif color.get(neighbor, WHITE) == GRAY:
                    # 发现环
                    cycle = [neighbor]
                    cur = node
                    while cur != neighbor:
                        cycle.append(cur)
                        cur = parent.get(cur, neighbor)
                    cycle.append(neighbor)
                    cycle.reverse()
                    self.cycles.append(cycle)
            color[node] = BLACK

        for n in self.nodes:
            if color.get(n, WHITE) == WHITE:
                dfs_cycle(n)

    def _calc_max_depth(self) -> None:
        self.max_depth = 0
        memo = {}
        visiting = set()

        def depth(node: str) -> int:
            if node in memo:
                return memo[node]
            if node in visiting:
                # 遇到环，返回当前深度避免无限递归
                return 0
            visiting.add(node)
            deps = self.nodes.get(node, set())
            if not deps:
                visiting.discard(node)
                memo[node] = 0
                return 0
            d = 1 + max((depth(d) for d in deps), default=0)
            visiting.discard(node)
            memo[node] = d
            return d

        for n in self.nodes:
            self.max_depth = max(self.max_depth, depth(n))

    def health_score(self) -> float:
        """计算依赖图健康度评分 [0, 1]"""
        if not self.nodes:
            return 1.0

        score = 1.0

        # 孤立模块惩罚
        if self.isolated:
            score -= len(self.isolated) * 0.05

        # 循环依赖惩罚
        if self.cycles:
            score -= len(self.cycles) * 0.15

        # 依赖深度惩罚（深度 > 5 → 扣分）
        if self.max_depth > 5:
            score -= (self.max_depth - 5) * 0.05

        return max(0.0, min(1.0, score))


# ============================================================================
# 架构门禁
# ============================================================================

class ArchitectureGate(TwelveGodsGate):
    """架构门禁 —— 比肩·劫财（木）

    比肩·架构协同：模块间依赖是否健康？
    劫财·攻防边界：系统边界是否安全？

    裁决逻辑：
    1. 依赖图健康度：无循环依赖、无过度耦合 → 开
    2. 模块边界清晰：有明确接口定义 → 开
    3. 架构稳定性：依赖深度合理 → 开
    4. 安全边界：模块隔离合理 → 开
    """

    # 评分阈值
    DEPS_HEALTH_OPEN = 0.8
    DEPS_HEALTH_CLOSED = 0.4
    MAX_SAFE_DEPTH = 5

    def __init__(self, god: TwelveGods = TwelveGods.BIJIAN):
        super().__init__(god)
        self.dependency_graph = DependencyGraph()

    def register_module(
        self,
        module_id: str,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        """注册模块到依赖图"""
        self.dependency_graph.add_node(module_id)
        if dependencies:
            for dep in dependencies:
                self.dependency_graph.add_edge(module_id, dep)

    def register_modules_from_registry(self) -> None:
        """从模块注册表批量注册"""
        try:
            from .module_registry import TENGOD_MODULES
            for mod in TENGOD_MODULES:
                module_id = mod["module_path"]
                self.dependency_graph.add_node(module_id)
                # 推断依赖关系：基于依赖计数
                dep_count = mod.get("dependency_count", 0)
                # 依赖关系需要从实际代码中分析，这里用简化模型
                # 依赖计数高的模块可能有更多依赖
        except ImportError:
            pass

    def build_dependency_graph(self, modules: List[Dict[str, Any]]) -> DependencyGraph:
        """从模块列表构建依赖图"""
        self.dependency_graph = DependencyGraph()
        for mod in modules:
            module_id = mod.get("module_path", mod.get("name", "unknown"))
            self.dependency_graph.add_node(module_id)
            # 注册依赖
            deps = mod.get("dependencies", [])
            for dep in deps:
                self.dependency_graph.add_edge(module_id, dep)
        self.dependency_graph.analyze()
        return self.dependency_graph

    def _judge_impl(self, unit: CognitiveUnit) -> GateVerdict:
        """架构门禁裁决"""
        self.dependency_graph.analyze()

        health = self.dependency_graph.health_score()
        issues = []
        evidence = []

        # 循环依赖检测
        if self.dependency_graph.cycles:
            cycle_names = ["→".join(c[:2]) + "..." for c in self.dependency_graph.cycles[:3]]
            issues.append(f"循环依赖({len(self.dependency_graph.cycles)}个): {', '.join(cycle_names)}")
        else:
            evidence.append("无循环依赖")

        # 孤立模块检测
        if self.dependency_graph.isolated:
            issues.append(f"孤立模块({len(self.dependency_graph.isolated)}个)")
        else:
            evidence.append("所有模块已连接")

        # 依赖深度检测
        if self.dependency_graph.max_depth > self.MAX_SAFE_DEPTH:
            issues.append(f"依赖深度过大({self.dependency_graph.max_depth})")
        else:
            evidence.append(f"依赖深度合理({self.dependency_graph.max_depth})")

        # 模块边界检测（基于palace_id和cognitive_layer）
        if unit.palace_id is None:
            issues.append("缺少门禁宫定位")
        else:
            evidence.append(f"门禁宫定位明确(宫{unit.palace_id})")

        if unit.cognitive_layer < 1:
            issues.append("认知层未定义")
        else:
            evidence.append(f"认知层L{unit.cognitive_layer}")

        # 综合评分
        score = health
        if issues:
            score -= len(issues) * 0.1

        # 微调：module_path 存在 → 架构存在
        if unit.module_path:
            score += 0.05

        score = max(0.0, min(1.0, score))

        # 判定状态
        if score >= self.DEPS_HEALTH_OPEN:
            state = GateState.OPEN
        elif score >= self.DEPS_HEALTH_CLOSED:
            state = GateState.PENDING
        else:
            state = GateState.CLOSED

        reason_parts = []
        if evidence:
            reason_parts.append("; ".join(evidence[:2]))
        if issues:
            reason_parts.append("问题: " + "; ".join(issues[:2]))
        reason = " | ".join(reason_parts) if reason_parts else "架构健康度评估"

        return GateVerdict(
            god=self.god,
            state=state,
            score=score,
            reason=reason,
            element=self.element,
        )

    def get_dependency_health(self) -> Dict[str, Any]:
        """获取依赖图健康度报告"""
        self.dependency_graph.analyze()
        return {
            "total_nodes": len(self.dependency_graph.nodes),
            "total_edges": sum(len(deps) for deps in self.dependency_graph.nodes.values()),
            "isolated": self.dependency_graph.isolated,
            "cycles": [[str(n) for n in c] for c in self.dependency_graph.cycles],
            "max_depth": self.dependency_graph.max_depth,
            "health_score": self.dependency_graph.health_score(),
        }


# ============================================================================
# 十二神门禁管理器
# ============================================================================

class TwelveGodsGateManager:
    """十二神门禁统一管理器

    管理所有十二神门禁实例，提供统一裁决接口。
    五行生克在管理器层面统一计算。
    """

    def __init__(self):
        self._gates: Dict[TwelveGods, TwelveGodsGate] = {}

    def register_gate(self, gate: TwelveGodsGate) -> None:
        """注册门禁"""
        self._gates[gate.god] = gate

    def judge_all(self, unit: CognitiveUnit) -> Dict[TwelveGods, GateVerdict]:
        """对所有已注册门禁进行裁决"""
        results = {}
        for god, gate in self._gates.items():
            results[god] = gate.judge(unit)
        return results

    def judge_by_element(
        self, unit: CognitiveUnit, element: FiveElements
    ) -> Dict[TwelveGods, GateVerdict]:
        """按五行裁决"""
        results = {}
        for god, gate in self._gates.items():
            if god.element == element:
                results[god] = gate.judge(unit)
        return results

    def get_overall_state(self, verdicts: Dict[TwelveGods, GateVerdict]) -> str:
        """十二神综合裁决（多数投票）"""
        if not verdicts:
            return GateState.PENDING

        counts = {GateState.OPEN: 0, GateState.PENDING: 0, GateState.CLOSED: 0}
        for v in verdicts.values():
            counts[v.state] += 1

        # 太极·元辰有否决权
        if TwelveGods.TAIJI in verdicts and verdicts[TwelveGods.TAIJI].state == GateState.CLOSED:
            return GateState.CLOSED

        if counts[GateState.CLOSED] > len(verdicts) // 2:
            return GateState.CLOSED
        elif counts[GateState.OPEN] > len(verdicts) // 2:
            return GateState.OPEN
        return GateState.PENDING

    def get_gate(self, god: TwelveGods) -> Optional[TwelveGodsGate]:
        return self._gates.get(god)

    def get_all_gates(self) -> Dict[TwelveGods, TwelveGodsGate]:
        return dict(self._gates)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            god.value: gate.get_statistics()
            for god, gate in self._gates.items()
        }


__all__ = [
    "DependencyGraph", "ArchitectureGate", "TwelveGodsGateManager",
]