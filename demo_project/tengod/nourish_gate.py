"""
nourish_gate.py — 滋养门禁 (正印·偏印 / 水) v4.6.0
=========================================================
正印·滋养守护：配置与文档是否健康？
偏印·桥接通变：微调与外挂是否安全？

五行属性：水
水生木（滋养支撑架构）
水克火（滋养约束创新）
土克水（知识约束滋养）

裁决维度：
  1. 配置健康度：配置完整性、合法性、一致性
  2. 文档完整性：是否有足够的文档覆盖
  3. 桥接安全性：微调模块是否安全可靠
  4. 资源健康度：计算资源、内存使用是否合理

与七论裁决器的集成：
  - 本体论：配置是否存在？
  - 实践论：配置是否可落地？
  - 境界论：配置是否提升了系统境界？
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
# 配置健康度
# ============================================================================

@dataclass
class ConfigHealth:
    """配置健康度"""
    completeness: float = 0.5   # 完整性 [0, 1]
    validity: float = 0.5       # 合法性 [0, 1]
    consistency: float = 0.5    # 一致性 [0, 1]
    documentation: float = 0.5  # 文档覆盖度 [0, 1]
    resource_usage: float = 0.5 # 资源使用率 [0, 1]（越低越好）
    security_score: float = 0.5 # 安全评分 [0, 1]

    def overall_score(self) -> float:
        return (
            self.completeness * 0.20 +
            self.validity * 0.20 +
            self.consistency * 0.20 +
            self.documentation * 0.20 +
            (1.0 - self.resource_usage) * 0.10 +
            self.security_score * 0.10
        )


# ============================================================================
# 滋养门禁
# ============================================================================

class NourishGate(TwelveGodsGate):
    """滋养门禁 —— 正印·偏印（水）

    正印·滋养守护：配置与文档是否健康？
    偏印·桥接通变：微调与外挂是否安全？

    裁决逻辑：
    1. 配置健康度：完整、合法、一致
    2. 文档完整性：覆盖度达标
    3. 桥接安全性：微调模块安全
    4. 资源健康度：计算资源合理

    正印与偏印的区别：
    - 正印（守护）：评分主要看配置和文档健康度
    - 偏印（通变）：评分主要看桥接安全性和资源使用
    """

    # 评分阈值
    NOURISH_OPEN = 0.8
    NOURISH_CLOSED = 0.4

    def __init__(self, god: TwelveGods = TwelveGods.ZHENGYIN):
        super().__init__(god)
        self._config_log: List[ConfigHealth] = []

    def _judge_impl(self, unit: CognitiveUnit) -> GateVerdict:
        """滋养门禁裁决"""
        health = self._extract_health(unit)
        self._config_log.append(health)
        score, issues, evidence = self._evaluate(health, unit)

        if score >= self.NOURISH_OPEN:
            state = GateState.OPEN
        elif score >= self.NOURISH_CLOSED:
            state = GateState.PENDING
        else:
            state = GateState.CLOSED

        reason_parts = []
        if evidence:
            reason_parts.append("; ".join(evidence[:2]))
        if issues:
            reason_parts.append("问题: " + "; ".join(issues[:2]))
        reason = " | ".join(reason_parts) if reason_parts else "滋养门禁评估"

        return GateVerdict(
            god=self.god,
            state=state,
            score=score,
            reason=reason,
            element=self.element,
        )

    def _extract_health(self, unit: CognitiveUnit) -> ConfigHealth:
        """从认知单元提取配置健康度"""
        coords = unit.coordinates
        health = ConfigHealth()

        # 完整性：S（事实可信度）
        health.completeness = coords.S

        # 合法性：C（图层对齐度）
        health.validity = coords.C

        # 一致性：I（交织稳定性）
        health.consistency = coords.I

        # 文档覆盖度：P（投影保真度）→ 高P意味着好的文档
        health.documentation = coords.P

        # 资源使用率：E（边缘探索度）→ 高E意味着需要更多资源
        health.resource_usage = coords.E * 0.7 + 0.1

        # 安全评分：基于认知层和palace_id
        layer_bonus = unit.cognitive_layer / 8.0 * 0.3
        palace_bonus = 0.2 if unit.palace_id else 0.0
        health.security_score = 0.5 + layer_bonus + palace_bonus

        return health

    def _evaluate(
        self, health: ConfigHealth, unit: CognitiveUnit
    ) -> Tuple[float, List[str], List[str]]:
        """评估滋养门禁"""
        issues = []
        evidence = []

        # 完整性
        if health.completeness >= 0.8:
            evidence.append("配置完整")
        elif health.completeness < 0.4:
            issues.append(f"配置不完整(S={health.completeness:.2f})")

        # 合法性
        if health.validity >= 0.7:
            evidence.append("配置合法")
        elif health.validity < 0.3:
            issues.append(f"配置非法(C={health.validity:.2f})")

        # 一致性
        if health.consistency >= 0.7:
            evidence.append("配置一致")
        elif health.consistency < 0.3:
            issues.append(f"配置不一致(I={health.consistency:.2f})")

        # 文档覆盖度
        if health.documentation >= 0.7:
            evidence.append("文档覆盖充分")
        elif health.documentation < 0.3:
            issues.append(f"文档不足(P={health.documentation:.2f})")

        # 资源使用率
        if health.resource_usage > 0.8:
            issues.append(f"资源使用过高({health.resource_usage:.2f})")
        elif health.resource_usage < 0.3:
            evidence.append("资源使用合理")

        # 安全评分
        if health.security_score >= 0.7:
            evidence.append("安全评分合格")
        elif health.security_score < 0.4:
            issues.append(f"安全评分低({health.security_score:.2f})")

        if self.god == TwelveGods.ZHENGYIN:
            # 正印：守护优先
            score = (
                health.completeness * 0.25 +
                health.validity * 0.25 +
                health.consistency * 0.20 +
                health.documentation * 0.15 +
                health.security_score * 0.10 +
                (1.0 - health.resource_usage) * 0.05
            )
        elif self.god == TwelveGods.PIANYIN:
            # 偏印：通变优先
            score = (
                health.security_score * 0.25 +
                (1.0 - health.resource_usage) * 0.25 +
                health.consistency * 0.20 +
                health.validity * 0.15 +
                health.completeness * 0.15
            )
        else:
            score = health.overall_score()

        # 缺少palace_id → 无门禁宫定位 → 扣分
        if unit.palace_id is None:
            score -= 0.05

        score = max(0.0, min(1.0, score))

        return score, issues, evidence

    def get_health_history(self) -> List[ConfigHealth]:
        return self._config_log


__all__ = [
    "ConfigHealth", "NourishGate",
]