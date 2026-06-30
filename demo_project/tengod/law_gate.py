"""
law_gate.py — 法度门禁 (正官·七杀 / 金) v2.29.0
=====================================================
正官·法度调度：调度策略是否合规？
七杀·品质裁决：输出品质是否达标？

五行属性：金
金生水（法度支撑滋养）
金克木（法度约束架构）
火克金（创新挑战法度）

裁决维度：
  1. 调度合规性：DeepSpec推测解码节奏是否合规
  2. 品质阈值：输出品质是否达到最低标准
  3. 规范遵循：是否遵循预设的调度策略
  4. 异常检测：调度中是否存在异常行为

与七论裁决器的集成：
  - 实践论：法度是否可落地？
  - 未来观论：法度是否可持续？
  - 元认知论：系统是否知道自己在遵循法度？
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
# 调度策略
# ============================================================================

@dataclass
class SchedulingPolicy:
    """调度策略"""
    policy_id: str
    max_burst_size: int = 4
    min_confidence_threshold: float = 0.7
    max_queue_depth: int = 10
    target_speedup: float = 5.0
    max_retries: int = 3
    timeout_ms: float = 1000.0

    def is_compliant(self, actual: "SchedulingMetrics") -> Tuple[bool, List[str]]:
        """检查实际调度是否合规"""
        violations = []
        if actual.burst_size > self.max_burst_size:
            violations.append(f"burst_size超标({actual.burst_size}/{self.max_burst_size})")
        if actual.confidence < self.min_confidence_threshold:
            violations.append(f"置信度不足({actual.confidence:.2f}/{self.min_confidence_threshold})")
        if actual.queue_depth > self.max_queue_depth:
            violations.append(f"队列深度超标({actual.queue_depth}/{self.max_queue_depth})")
        if actual.retries > self.max_retries:
            violations.append(f"重试次数超标({actual.retries}/{self.max_retries})")
        return len(violations) == 0, violations


@dataclass
class SchedulingMetrics:
    """调度度量"""
    burst_size: int = 2
    confidence: float = 0.5
    queue_depth: int = 0
    retries: int = 0
    speedup: float = 1.0
    latency_ms: float = 100.0
    throughput: float = 1.0
    anomaly_score: float = 0.0  # 异常分数 [0, 1]
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 法度门禁
# ============================================================================

class LawGate(TwelveGodsGate):
    """法度门禁 —— 正官·七杀（金）

    正官·法度调度：调度策略是否合规？
    七杀·品质裁决：输出品质是否达标？

    裁决逻辑：
    1. 调度合规性：实际调度参数是否在策略范围内
    2. 品质阈值：输出品质是否达到最低标准
    3. 规范遵循：是否遵循DeepSpec推测解码节奏
    4. 异常检测：是否存在调度异常

    正官与七杀的区别：
    - 正官（法度）：评分主要看合规性和规范遵循
    - 七杀（品质）：评分主要看品质和异常检测
    """

    # 评分阈值
    LAW_OPEN = 0.8
    LAW_CLOSED = 0.4
    ANOMALY_HIGH_THRESHOLD = 0.6
    ANOMALY_CRITICAL_THRESHOLD = 0.8

    def __init__(self, god: TwelveGods = TwelveGods.ZHENGGUAN):
        super().__init__(god)
        self.policy = SchedulingPolicy(policy_id="default")
        self._metrics_log: List[SchedulingMetrics] = []

    def set_policy(self, policy: SchedulingPolicy) -> None:
        self.policy = policy

    def record_metrics(self, metrics: SchedulingMetrics) -> None:
        self._metrics_log.append(metrics)

    def _judge_impl(self, unit: CognitiveUnit) -> GateVerdict:
        """法度门禁裁决"""
        metrics = self._extract_metrics(unit)
        self._metrics_log.append(metrics)
        score, issues, evidence = self._evaluate(metrics, unit)

        if score >= self.LAW_OPEN:
            state = GateState.OPEN
        elif score >= self.LAW_CLOSED:
            state = GateState.PENDING
        else:
            state = GateState.CLOSED

        reason_parts = []
        if evidence:
            reason_parts.append("; ".join(evidence[:2]))
        if issues:
            reason_parts.append("问题: " + "; ".join(issues[:2]))
        reason = " | ".join(reason_parts) if reason_parts else "法度门禁评估"

        return GateVerdict(
            god=self.god,
            state=state,
            score=score,
            reason=reason,
            element=self.element,
        )

    def _extract_metrics(self, unit: CognitiveUnit) -> SchedulingMetrics:
        """从认知单元提取调度度量"""
        coords = unit.coordinates
        metrics = SchedulingMetrics()

        # 批大小：基于坐标和认知层
        if unit.metadata and "burst_size" in unit.metadata:
            metrics.burst_size = unit.metadata["burst_size"]
        else:
            metrics.burst_size = max(1, int(unit.cognitive_layer * 0.75))

        # 置信度：S
        metrics.confidence = coords.S

        # 队列深度：基于I（交织稳定性）
        if unit.metadata and "queue_depth" in unit.metadata:
            metrics.queue_depth = unit.metadata["queue_depth"]
        else:
            metrics.queue_depth = int((1.0 - coords.I) * 10)

        # 推测加速比：基于C和I
        metrics.speedup = coords.C * coords.I * 5.0 + 1.0

        # 异常分数：E（边缘探索度）的映射
        metrics.anomaly_score = coords.E

        return metrics

    def _evaluate(
        self, metrics: SchedulingMetrics, unit: CognitiveUnit
    ) -> Tuple[float, List[str], List[str]]:
        """评估法度门禁"""
        issues = []
        evidence = []

        # 合规性检查
        is_compliant, violations = self.policy.is_compliant(metrics)
        if is_compliant:
            evidence.append("调度策略合规")
        else:
            issues.extend(violations)

        # 异常检测
        if metrics.anomaly_score > self.ANOMALY_CRITICAL_THRESHOLD:
            issues.append(f"严重异常({metrics.anomaly_score:.2f})")
        elif metrics.anomaly_score > self.ANOMALY_HIGH_THRESHOLD:
            issues.append(f"中度异常({metrics.anomaly_score:.2f})")
        elif metrics.anomaly_score < 0.2:
            evidence.append(f"调度正常(E={metrics.anomaly_score:.2f})")

        # 加速比验证
        if metrics.speedup >= self.policy.target_speedup:
            evidence.append(f"加速比达标({metrics.speedup:.1f}x)")
        elif metrics.speedup < 2.0:
            issues.append(f"加速比不足({metrics.speedup:.1f}x)")

        if self.god == TwelveGods.ZHENGGUAN:
            # 正官：法度优先
            score = (
                (1.0 if is_compliant else 0.3) * 0.40 +
                (1.0 - metrics.anomaly_score) * 0.25 +
                min(1.0, metrics.speedup / self.policy.target_speedup) * 0.20 +
                unit.coordinates.I * 0.15
            )
        elif self.god == TwelveGods.QISHA:
            # 七杀：品质优先
            score = (
                (1.0 - metrics.anomaly_score) * 0.35 +
                (1.0 if is_compliant else 0.3) * 0.25 +
                min(1.0, metrics.speedup / self.policy.target_speedup) * 0.20 +
                unit.coordinates.S * 0.20
            )
        else:
            score = 0.5

        # 违规惩罚
        score -= len(violations) * 0.08
        score = max(0.0, min(1.0, score))

        return score, issues, evidence

    def get_metrics_history(self) -> List[SchedulingMetrics]:
        return self._metrics_log

    def get_avg_metrics(self) -> Optional[SchedulingMetrics]:
        if not self._metrics_log:
            return None
        n = len(self._metrics_log)
        return SchedulingMetrics(
            burst_size=int(sum(m.burst_size for m in self._metrics_log) / n),
            confidence=sum(m.confidence for m in self._metrics_log) / n,
            queue_depth=int(sum(m.queue_depth for m in self._metrics_log) / n),
            retries=int(sum(m.retries for m in self._metrics_log) / n),
            speedup=sum(m.speedup for m in self._metrics_log) / n,
            anomaly_score=sum(m.anomaly_score for m in self._metrics_log) / n,
        )


__all__ = [
    "SchedulingPolicy", "SchedulingMetrics", "LawGate",
]