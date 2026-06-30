"""
self_referential_gate.py — 自指涉门禁 (太极·元辰) v2.30.0
=============================================================
太极·阴阳调和：系统整体是否平衡？
元辰·本源定位：系统是否在观察自身？

超越五行：太极超越了五行生克，代表了系统的自指涉能力。

裁决维度：
  1. 自指涉深度：系统是否在观察自身的行为？
  2. 阴阳平衡：系统的开/关/徘徊门禁是否存在单向倾斜？
  3. 本源定位：系统是否知道自己的TBCE坐标？
  4. 全息一致性：局部是否反映了整体的状态？

核心能力：
  - 否决权：太极·元辰可以否决其他门禁
  - 自指涉：系统观察自身，类似于"知道自己不知道"
  - 阴阳调和：保持系统整体平衡

与七论裁决器的集成：
  - 元认知论：系统是否知道自己正在被裁决？
  - 混沌海：是否应该保持存疑？
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import time
import math

from .tbce_unit import CognitiveUnit, GateState, TBCECoordinates
from .twelve_gods_base import (
    TwelveGods, FiveElements, GateVerdict, TwelveGodsGate,
)


# ============================================================================
# 自指涉度量
# ============================================================================

@dataclass
class SelfReferenceMetrics:
    """自指涉度量"""
    self_awareness: float = 0.5      # 自指涉深度 [0, 1]
    yin_yang_balance: float = 0.5    # 阴阳平衡 [0, 1]
    origin_known: bool = False       # 本源是否已知
    holographic_consistency: float = 0.5  # 全息一致性 [0, 1]
    recursion_depth: int = 0         # 递归深度
    blind_spots: List[str] = field(default_factory=list)  # 盲点
    veto_triggered: bool = False     # 是否触发了否决权

    def to_dict(self) -> Dict[str, Any]:
        return {
            "self_awareness": round(self.self_awareness, 3),
            "yin_yang_balance": round(self.yin_yang_balance, 3),
            "origin_known": self.origin_known,
            "holographic_consistency": round(self.holographic_consistency, 3),
            "recursion_depth": self.recursion_depth,
            "blind_spots": self.blind_spots,
            "veto_triggered": self.veto_triggered,
        }


# ============================================================================
# 自指涉门禁
# ============================================================================

class SelfReferentialGate(TwelveGodsGate):
    """自指涉门禁 —— 太极·元辰（超越五行）

    太极·阴阳调和：系统整体是否平衡？
    元辰·本源定位：系统是否在观察自身？

    裁决逻辑：
    1. 自指涉深度：递归深度 > 0 → 系统在观察自身
    2. 阴阳平衡：门禁状态分布不过度倾斜
    3. 本源定位：TBCE坐标完整
    4. 全息一致性：局部 → 整体的映射

    特殊权限：
    - 否决权：太极·元辰可以否决其他门禁
    - 盲点检测：发现系统自己不知道的事
    - 递归自指涉：知道自己不知道什么
    """

    # 评分阈值
    SELF_REF_OPEN = 0.8
    SELF_REF_CLOSED = 0.4
    MIN_RECURSION_DEPTH = 1
    MAX_RECURSION_DEPTH = 3

    def __init__(self, god: TwelveGods = TwelveGods.TAIJI):
        super().__init__(god)
        self._metrics_log: List[SelfReferenceMetrics] = []
        self._veto_log: List[Dict] = []
        self._other_gate_states: Dict[str, str] = {}  # 其他门禁状态

    def feed_gate_states(self, states: Dict[str, str]) -> None:
        """投喂其他门禁状态（用于阴阳平衡判断）"""
        self._other_gate_states = dict(states)

    def _judge_impl(self, unit: CognitiveUnit) -> GateVerdict:
        """自指涉门禁裁决"""
        metrics = self._extract_metrics(unit)
        self._metrics_log.append(metrics)

        score, issues, evidence = self._evaluate(metrics, unit)

        if score >= self.SELF_REF_OPEN:
            state = GateState.OPEN
        elif score >= self.SELF_REF_CLOSED:
            state = GateState.PENDING
        else:
            state = GateState.CLOSED

        reason_parts = []
        if evidence:
            reason_parts.append("; ".join(evidence[:2]))
        if issues:
            reason_parts.append("问题: " + "; ".join(issues[:2]))
        reason = " | ".join(reason_parts) if reason_parts else "自指涉门禁评估"

        # 否决权触发
        if state == GateState.CLOSED and self.god == TwelveGods.TAIJI:
            metrics.veto_triggered = True
            self._veto_log.append({
                "unit_id": unit.unit_id,
                "reason": reason,
                "timestamp": time.time(),
            })

        return GateVerdict(
            god=self.god,
            state=state,
            score=score,
            reason=reason,
            element=self.element,
        )

    def _extract_metrics(self, unit: CognitiveUnit) -> SelfReferenceMetrics:
        """提取自指涉度量"""
        coords = unit.coordinates
        metrics = SelfReferenceMetrics()

        # 自指涉深度：I（交织稳定性）→ 高稳定性意味着深层次自指涉
        metrics.self_awareness = coords.I

        # 阴阳平衡：从其他门禁状态计算
        metrics.yin_yang_balance = self._compute_yin_yang_balance()

        # 本源定位：TBCE坐标是否完整
        metrics.origin_known = all(
            getattr(coords, dim, 0) > 0 for dim in ['S', 'T', 'P', 'C', 'I', 'E']
        )

        # 全息一致性：C（图层对齐度）→ 局部是否一致
        metrics.holographic_consistency = coords.C

        # 递归深度：从metadata获取
        if unit.metadata and "recursion_depth" in unit.metadata:
            metrics.recursion_depth = unit.metadata["recursion_depth"]
        else:
            metrics.recursion_depth = min(
                int(unit.coordinates.I * self.MAX_RECURSION_DEPTH) + 1,
                self.MAX_RECURSION_DEPTH,
            )

        # 盲点检测
        metrics.blind_spots = self._detect_blind_spots(unit)

        return metrics

    def _compute_yin_yang_balance(self) -> float:
        """计算阴阳平衡度

        阳（开）和阴（关）的平衡：
        太多开 → 过于乐观（阳盛阴虚）
        太多关 → 过于悲观（阴盛阳虚）
        徘徊 → 平衡倾向
        """
        if not self._other_gate_states:
            return 0.5

        total = len(self._other_gate_states)
        if total == 0:
            return 0.5

        open_count = sum(1 for s in self._other_gate_states.values() if s == GateState.OPEN)
        closed_count = sum(1 for s in self._other_gate_states.values() if s == GateState.CLOSED)
        pending_count = total - open_count - closed_count

        # 理想比例：40%开 + 30%徘徊 + 30%关
        ideal_open = 0.4
        open_dev = abs(open_count / total - ideal_open)
        closed_dev = abs(closed_count / total - 0.3)

        # 平衡度 = 1 - 偏离度
        balance = 1.0 - (open_dev + closed_dev) * 0.5
        return max(0.0, min(1.0, balance))

    def _detect_blind_spots(self, unit: CognitiveUnit) -> List[str]:
        """检测盲点"""
        blind_spots = []

        # 坐标缺失
        coords = unit.coordinates
        if coords.S < 0.2:
            blind_spots.append("S维度盲点：事实可信度低")
        if coords.E < 0.1:
            blind_spots.append("E维度盲点：缺乏探索")
        if coords.E > 0.9:
            blind_spots.append("E维度盲点：过度探索，缺乏聚焦")

        # 认知层盲点
        if unit.cognitive_layer < 2:
            blind_spots.append("认知层盲点：层次过低，缺乏全局视角")

        # 宫位盲点
        if unit.palace_id is None:
            blind_spots.append("宫位盲点：无门禁宫定位")

        # 自指涉盲点
        if not unit.psi_operator:
            blind_spots.append("算子盲点：缺少Ψ算子")

        return blind_spots

    def _evaluate(
        self, metrics: SelfReferenceMetrics, unit: CognitiveUnit
    ) -> Tuple[float, List[str], List[str]]:
        """评估自指涉门禁"""
        issues = []
        evidence = []

        # 自指涉深度
        if metrics.recursion_depth >= self.MIN_RECURSION_DEPTH:
            evidence.append(f"自指涉深度达标({metrics.recursion_depth})")
        else:
            issues.append(f"自指涉深度不足({metrics.recursion_depth})")

        # 阴阳平衡
        if metrics.yin_yang_balance >= 0.7:
            evidence.append("阴阳平衡良好")
        elif metrics.yin_yang_balance < 0.4:
            issues.append(f"阴阳失衡({metrics.yin_yang_balance:.2f})")

        # 本源定位
        if metrics.origin_known:
            evidence.append("本源定位明确")
        else:
            issues.append("本源定位缺失")

        # 全息一致性
        if metrics.holographic_consistency >= 0.7:
            evidence.append("全息一致性高")
        elif metrics.holographic_consistency < 0.3:
            issues.append(f"全息一致性低({metrics.holographic_consistency:.2f})")

        # 盲点
        if metrics.blind_spots:
            for spot in metrics.blind_spots[:2]:
                issues.append(spot)
        else:
            evidence.append("无盲点")

        if self.god == TwelveGods.TAIJI:
            # 太极：阴阳调和优先
            score = (
                metrics.yin_yang_balance * 0.35 +
                metrics.holographic_consistency * 0.25 +
                metrics.self_awareness * 0.20 +
                (1.0 if metrics.origin_known else 0.3) * 0.15 +
                (1.0 - len(metrics.blind_spots) * 0.1) * 0.05
            )
        elif self.god == TwelveGods.YUANCHEN:
            # 元辰：本源定位优先
            score = (
                (1.0 if metrics.origin_known else 0.2) * 0.35 +
                metrics.self_awareness * 0.25 +
                metrics.holographic_consistency * 0.20 +
                metrics.yin_yang_balance * 0.15 +
                (1.0 - len(metrics.blind_spots) * 0.1) * 0.05
            )
        else:
            score = 0.5

        score = max(0.0, min(1.0, score))

        return score, issues, evidence

    def get_metrics_history(self) -> List[SelfReferenceMetrics]:
        return self._metrics_log

    def get_veto_log(self) -> List[Dict]:
        return self._veto_log

    def get_blind_spots_report(self) -> Dict[str, Any]:
        """获取盲点报告"""
        all_blind_spots = set()
        for m in self._metrics_log:
            for spot in m.blind_spots:
                all_blind_spots.add(spot)
        return {
            "total_blind_spots": len(all_blind_spots),
            "blind_spots": sorted(all_blind_spots),
            "veto_count": len(self._veto_log),
        }


__all__ = [
    "SelfReferenceMetrics", "SelfReferentialGate",
]