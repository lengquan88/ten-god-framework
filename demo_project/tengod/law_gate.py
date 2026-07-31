"""
law_gate.py — 法度门禁 (正官·七杀 / 金) v4.6.0
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
    #: 自定义规则：Dict[规则名, 阈值]，会合并/覆盖默认规则
    custom_rules: Dict[str, Any] = field(default_factory=dict)

    def merged_rules(self) -> Dict[str, Any]:
        """返回默认规则与自定义规则合并后的完整规则集"""
        defaults = {
            "max_burst_size": self.max_burst_size,
            "min_confidence_threshold": self.min_confidence_threshold,
            "max_queue_depth": self.max_queue_depth,
            "target_speedup": self.target_speedup,
            "max_retries": self.max_retries,
            "timeout_ms": self.timeout_ms,
            "min_timeliness": 0.5,       # T 维度最低实时性
            "min_parallelism": 0.5,      # P 维度最低并行度
            "min_consistency": 0.5,      # C 维度最低一致性
            "deadline_miss_penalty": 0.1,
            "priority_mismatch_penalty": 0.08,
        }
        merged = {**defaults, **self.custom_rules}
        return merged

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
    deadline_miss: bool = False  # 是否错过截止时间
    priority_mismatch: bool = False  # 优先级是否不匹配
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

        # 截止时间错过：从metadata提取
        if unit.metadata and "deadline_miss" in unit.metadata:
            metrics.deadline_miss = bool(unit.metadata["deadline_miss"])

        # 优先级不匹配：从metadata提取
        if unit.metadata and "priority_mismatch" in unit.metadata:
            metrics.priority_mismatch = bool(unit.metadata["priority_mismatch"])

        return metrics

    def _evaluate_policy(
        self, metrics: SchedulingMetrics, unit: CognitiveUnit
    ) -> Tuple[List[str], List[str], float]:
        """策略评估：检查 T/P/C 三维度 + deadline/priority 惩罚

        返回：(issues, evidence, total_penalty)
        """
        coords = unit.coordinates
        rules = self.policy.merged_rules()
        issues = []
        evidence = []
        total_penalty = 0.0

        # 实时性（T 维度）
        if coords.T < rules["min_timeliness"]:
            issues.append(f"实时性不足(T={coords.T:.2f}<{rules['min_timeliness']})")
            total_penalty += 0.08
        else:
            evidence.append(f"实时性达标(T={coords.T:.2f})")

        # 并行度（P 维度）
        if coords.P < rules["min_parallelism"]:
            issues.append(f"并行度不足(P={coords.P:.2f}<{rules['min_parallelism']})")
            total_penalty += 0.08
        else:
            evidence.append(f"并行度达标(P={coords.P:.2f})")

        # 一致性（C 维度）
        if coords.C < rules["min_consistency"]:
            issues.append(f"一致性不够(C={coords.C:.2f}<{rules['min_consistency']})")
            total_penalty += 0.08
        else:
            evidence.append(f"一致性达标(C={coords.C:.2f})")

        # 截止时间错过惩罚
        if metrics.deadline_miss:
            issues.append("错过截止时间(deadline_miss)")
            total_penalty += rules["deadline_miss_penalty"]

        # 优先级不匹配惩罚
        if metrics.priority_mismatch:
            issues.append("优先级不匹配(priority_mismatch)")
            total_penalty += rules["priority_mismatch_penalty"]

        return issues, evidence, total_penalty

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

    def get_gate_stats(self) -> Dict[str, Any]:
        """获取门禁统计（空/非空）。

        返回：
          - 空门禁：{}
          - 非空：包含裁决数、状态分布、平均得分、门禁神位等字段
        """
        if not self._verdict_log:
            return {}
        total = len(self._verdict_log)
        states = {'open': 0, 'pending': 0, 'closed': 0}
        scores = []
        for v in self._verdict_log:
            states[v.state] += 1
            scores.append(v.score)
        return {
            'god': self.god.value,
            'god_name': self.god.name,
            'element': self.element.value,
            'total_verdicts': total,
            'states': states,
            'avg_score': sum(scores) / total if scores else 0.0,
            'max_score': max(scores) if scores else 0.0,
            'min_score': min(scores) if scores else 0.0,
            'policy_id': self.policy.policy_id,
            'metrics_count': len(self._metrics_log),
        }


__all__ = [
    "SchedulingPolicy", "SchedulingMetrics", "LawGate",
]