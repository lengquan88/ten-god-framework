"""
innovation_gate.py — 创新门禁 (食神·伤官 / 火) v4.6.0
===========================================================
食神·创生输出：生成质量是否达标？
伤官·破界创新：创新是否带来系统性风险？

五行属性：火
火生土（创新驱动知识固化）
火克金（创新挑战法度）
水克火（滋养约束创新）

裁决维度：
  1. 创生质量：生成内容的准确性、完整性、一致性
  2. 破界风险：创新对现有系统的冲击评估
  3. 创造性密度：新增功能 vs 破坏性变更的比例
  4. 规范遵循度：创新是否遵循架构规范

与七论裁决器的集成：
  - 认识论：创新是否可被认知？
  - 实践论：创新是否可落地？
  - 未来观论：创新是否具有可持续性？
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
# 创新度量
# ============================================================================

@dataclass
class InnovationMetrics:
    """创新度量"""
    creativity_score: float = 0.5      # 创造性评分 [0, 1]
    novelty_density: float = 0.5       # 新颖性密度 [0, 1]
    disruption_risk: float = 0.3       # 破坏性风险 [0, 1]
    norm_compliance: float = 0.7       # 规范遵循度 [0, 1]
    quality_score: float = 0.7         # 生成质量 [0, 1]
    coherence_score: float = 0.7       # 一致性评分 [0, 1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "creativity_score": round(self.creativity_score, 3),
            "novelty_density": round(self.novelty_density, 3),
            "disruption_risk": round(self.disruption_risk, 3),
            "norm_compliance": round(self.norm_compliance, 3),
            "quality_score": round(self.quality_score, 3),
            "coherence_score": round(self.coherence_score, 3),
        }


# ============================================================================
# 创新门禁
# ============================================================================

class InnovationGate(TwelveGodsGate):
    """创新门禁 —— 食神·伤官（火）

    食神·创生输出：生成质量是否达标？
    伤官·破界创新：创新是否带来系统性风险？

    裁决逻辑：
    1. 创生质量：内容准确、完整、一致 → 食神开
    2. 破界风险：创新冲击可控 → 伤官开
    3. 创造性平衡：创造性密度 × 规范遵循度 → 综合评分
    4. 高风险创新 → 徘徊（需要人工判断）

    食神与伤官的区别：
    - 食神（创生）：评分主要看质量和一致性
    - 伤官（破界）：评分主要看新颖性和风险
    """

    # 评分阈值
    QUALITY_OPEN = 0.8
    QUALITY_CLOSED = 0.4
    RISK_HIGH_THRESHOLD = 0.6
    RISK_CRITICAL_THRESHOLD = 0.8

    def __init__(self, god: TwelveGods = TwelveGods.SHISHEN):
        super().__init__(god)
        self._metrics_log: List[InnovationMetrics] = []

    def _judge_impl(self, unit: CognitiveUnit) -> GateVerdict:
        """创新门禁裁决"""
        # 从认知单元提取创新度量
        metrics = self._extract_metrics(unit)
        self._metrics_log.append(metrics)

        score = self._compute_score(metrics, unit)
        issues, evidence = self._analyze(metrics, unit)

        if score >= self.QUALITY_OPEN:
            state = GateState.OPEN
        elif score >= self.QUALITY_CLOSED:
            state = GateState.PENDING
        else:
            state = GateState.CLOSED

        reason_parts = []
        if evidence:
            reason_parts.append("; ".join(evidence[:2]))
        if issues:
            reason_parts.append("问题: " + "; ".join(issues[:2]))
        reason = " | ".join(reason_parts) if reason_parts else "创新度量评估"

        return GateVerdict(
            god=self.god,
            state=state,
            score=score,
            reason=reason,
            element=self.element,
        )

    def _extract_metrics(self, unit: CognitiveUnit) -> InnovationMetrics:
        """从认知单元提取创新度量"""
        metrics = InnovationMetrics()

        # 从TBCE坐标推断
        coords = unit.coordinates

        # 创造性：E（边缘探索度）越高 → 创造性越高
        metrics.creativity_score = coords.E

        # 新颖性密度：P（投影保真度）越低 → 越新颖（偏离常规投影）
        metrics.novelty_density = 1.0 - coords.P

        # 破坏性风险：E × (1 - C)
        metrics.disruption_risk = coords.E * (1.0 - coords.C)

        # 规范遵循度：C（图层对齐度）越高 → 越遵循规范
        metrics.norm_compliance = coords.C

        # 生成质量：S（事实可信度）的主要贡献
        metrics.quality_score = coords.S

        # 一致性：I（交织稳定性）的主要贡献
        metrics.coherence_score = coords.I

        return metrics

    def _compute_score(
        self, metrics: InnovationMetrics, unit: CognitiveUnit
    ) -> float:
        """计算创新综合评分"""
        if self.god == TwelveGods.SHISHEN:
            # 食神：创生输出 → 质量优先
            score = (
                metrics.quality_score * 0.35 +
                metrics.coherence_score * 0.25 +
                metrics.norm_compliance * 0.20 +
                metrics.creativity_score * 0.10 +
                (1.0 - metrics.disruption_risk) * 0.10
            )
        elif self.god == TwelveGods.SHANGGUAN:
            # 伤官：破界创新 → 创新优先，但风险必须可控
            base = (
                metrics.creativity_score * 0.30 +
                metrics.novelty_density * 0.25 +
                metrics.quality_score * 0.20 +
                metrics.coherence_score * 0.15 +
                (1.0 - metrics.disruption_risk) * 0.10
            )
            # 高破坏性风险 → 严厉惩罚
            if metrics.disruption_risk > self.RISK_CRITICAL_THRESHOLD:
                score = base * 0.5
            elif metrics.disruption_risk > self.RISK_HIGH_THRESHOLD:
                score = base * 0.7
            else:
                score = base
        else:
            score = metrics.quality_score

        return max(0.0, min(1.0, score))

    def _analyze(
        self, metrics: InnovationMetrics, unit: CognitiveUnit
    ) -> Tuple[List[str], List[str]]:
        """分析创新度量，返回(问题, 证据)"""
        issues = []
        evidence = []

        # 质量检测
        if metrics.quality_score >= 0.8:
            evidence.append(f"生成质量高({metrics.quality_score:.2f})")
        elif metrics.quality_score < 0.4:
            issues.append(f"生成质量低({metrics.quality_score:.2f})")

        # 一致性检测
        if metrics.coherence_score >= 0.7:
            evidence.append(f"一致性良好({metrics.coherence_score:.2f})")
        elif metrics.coherence_score < 0.3:
            issues.append(f"一致性差({metrics.coherence_score:.2f})")

        # 破坏性风险检测
        if metrics.disruption_risk > self.RISK_CRITICAL_THRESHOLD:
            issues.append(f"严重破坏性风险({metrics.disruption_risk:.2f})")
        elif metrics.disruption_risk > self.RISK_HIGH_THRESHOLD:
            issues.append(f"较高破坏性风险({metrics.disruption_risk:.2f})")
        elif metrics.disruption_risk < 0.2:
            evidence.append(f"破坏性风险低({metrics.disruption_risk:.2f})")

        # 规范遵循度
        if metrics.norm_compliance >= 0.7:
            evidence.append(f"规范遵循度高({metrics.norm_compliance:.2f})")
        elif metrics.norm_compliance < 0.3:
            issues.append(f"规范遵循度低({metrics.norm_compliance:.2f})")

        # 创造性密度
        if metrics.creativity_score >= 0.7:
            evidence.append(f"创造性高({metrics.creativity_score:.2f})")

        return issues, evidence

    def get_metrics_history(self) -> List[InnovationMetrics]:
        return self._metrics_log

    def get_avg_metrics(self) -> Optional[InnovationMetrics]:
        if not self._metrics_log:
            return None
        n = len(self._metrics_log)
        return InnovationMetrics(
            creativity_score=sum(m.creativity_score for m in self._metrics_log) / n,
            novelty_density=sum(m.novelty_density for m in self._metrics_log) / n,
            disruption_risk=sum(m.disruption_risk for m in self._metrics_log) / n,
            norm_compliance=sum(m.norm_compliance for m in self._metrics_log) / n,
            quality_score=sum(m.quality_score for m in self._metrics_log) / n,
            coherence_score=sum(m.coherence_score for m in self._metrics_log) / n,
        )


__all__ = [
    "InnovationMetrics", "InnovationGate",
]