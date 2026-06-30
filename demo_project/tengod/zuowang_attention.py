"""
zuowang_attention.py — 坐忘注意力调度器 v2.23.0
===================================================
道曰："为道日损，损之又损，以至于无为。"

坐忘（Zuowang）注意力机制：
- 不是"关注什么"，而是"忘记什么"
- 为道日损：注意力稀疏化，只保留最重要的特征
- 坐忘门禁：防止注意力过度集中，导致认知偏见

核心Ψ算子：ZuowangAttention（L5 注意力调度层）
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .tbce_unit import TBCECoordinates, CognitiveUnit, GateState


# ============================================================================
# 注意力权重
# ============================================================================

@dataclass
class AttentionWeight:
    """注意力权重向量"""
    dimension: str  #: S/T/P/C/I/E
    weight: float  #: 注意力权重 [0, 1]
    retained: bool = True  #: 是否保留（坐忘判断）

@dataclass
class AttentionResult:
    """注意力分配结果"""
    unit_id: str
    original_weights: List[AttentionWeight]
    pruned_weights: List[AttentionWeight]
    sparsity: float  #: 注意力稀疏度
    retained_count: int
    total_count: int
    gate_state: str  #: 坐忘门禁裁决
    timestamp: float = field(default_factory=lambda: time.time())


# ============================================================================
# 坐忘注意力调度器
# ============================================================================

class ZuowangAttention:
    """坐忘注意力调度器 —— 为道日损

    传统注意力机制：关注重要特征
    坐忘注意力机制：忘记不重要特征

    核心思想：
    1. 先分配注意力（全量权重）
    2. 坐忘（忘记不重要部分）
    3. 只保留最重要的特征

    门禁：
    - 坐忘太少（注意力太分散）：注意力不足，需要聚焦 → 关
    - 坐忘适中（刚好保留关键特征）：坐忘成功 → 开
    - 坐忘太多（连关键特征都忘了）：注意力过度稀疏 → 徘徊
    """

    # 默认配置
    DEFAULT_SPARSITY_TARGET = 0.5  # 目标稀疏度：保留50%
    MAX_SPARSITY = 0.8  # 最大稀疏度
    MIN_SPARSITY = 0.2  # 最小稀疏度（至少保留20%）
    PRUNING_THRESHOLD = 0.3  # 权重低于此 → 被坐忘

    def __init__(
        self,
        sparsity_target: float = DEFAULT_SPARSITY_TARGET,
        pruning_threshold: float = PRUNING_THRESHOLD,
    ):
        self.sparsity_target = sparsity_target
        self.pruning_threshold = pruning_threshold
        self._attention_log: List[AttentionResult] = []

    def allocate_attention(
        self,
        unit: CognitiveUnit,
    ) -> List[AttentionWeight]:
        """分配注意力 —— 基于TBCE坐标自动生成权重

        权重分配逻辑：
        - S（事实可信度）：高S → 低注意（已验证，不需要额外关注）
        - E（边缘探索度）：高E → 高注意（接近边界，需要关注）
        - P（投影保真度）：高P → 低注意（投影清晰，不需要关注）
        - I（交织稳定性）：低I → 高注意（不稳定，需要关注）
        """
        coord = unit.coordinates

        weights = [
            AttentionWeight("S", 1.0 - coord.S),  # 可信 → 少关注
            AttentionWeight("T", 0.5),  # 时间平权
            AttentionWeight("P", 1.0 - coord.P),  # 清晰 → 少关注
            AttentionWeight("C", 0.5 + 0.5 * (1.0 - coord.C)),  # 对齐差 → 多关注
            AttentionWeight("I", 1.0 - coord.I),  # 不稳定 → 多关注
            AttentionWeight("E", coord.E),  # 边界 → 多关注
        ]

        # 归一化到[0, 1]
        total = sum(w.weight for w in weights)
        if total > 0:
            for w in weights:
                w.weight /= total

        return weights

    def zuowang(
        self,
        unit: CognitiveUnit,
        auto_judge: bool = True,
    ) -> AttentionResult:
        """坐忘 —— 忘记不重要特征

        Args:
            unit: 认知单元
            auto_judge: 是否自动门禁裁决

        Returns:
            注意力分配结果
        """
        # Step 1: 分配注意力
        original = self.allocate_attention(unit)

        # Step 2: 坐忘（忘记不重要特征）
        pruned = []
        for w in original:
            # 门禁第一步：权重低于阈值 → 坐忘
            if w.weight >= self.pruning_threshold:
                pruned.append(AttentionWeight(
                    dimension=w.dimension,
                    weight=w.weight,
                    retained=True,
                ))
            else:
                # 坐忘不保留
                pruned.append(AttentionWeight(
                    dimension=w.dimension,
                    weight=0.0,
                    retained=False,
                ))

        # Step 3: 计算稀疏度
        retained_count = sum(1 for w in pruned if w.retained)
        total_count = len(pruned)
        sparsity = 1.0 - (retained_count / total_count)

        # Step 4: 坐忘门禁裁决
        if auto_judge:
            gate_state = self._judge_gate(sparsity, retained_count)
        else:
            gate_state = GateState.PENDING

        result = AttentionResult(
            unit_id=unit.unit_id,
            original_weights=original,
            pruned_weights=pruned,
            sparsity=sparsity,
            retained_count=retained_count,
            total_count=total_count,
            gate_state=gate_state,
        )
        self._attention_log.append(result)
        return result

    def _judge_gate(self, sparsity: float, retained_count: int) -> str:
        """坐忘门禁裁决

        三态：
        - 开：坐忘成功，注意力聚焦在关键特征上
        - 徘徊：坐忘过渡态，处于临界区域
        - 关：坐忘失败，注意力分配不当
        """
        # 坐忘太少 → 注意力分散 → 关
        if sparsity < self.MIN_SPARSITY:
            return GateState.CLOSED
        # 坐忘太多 → 连关键特征都忘了 → 关
        if sparsity > self.MAX_SPARSITY:
            return GateState.CLOSED
        # 保留太少 → 注意力不足
        if retained_count < 2:
            return GateState.CLOSED
        # 保留太多 → 注意力分散
        if retained_count > 5:
            return GateState.CLOSED
        # 刚好 → 坐忘成功
        if abs(sparsity - self.sparsity_target) <= 0.15:
            return GateState.OPEN
        # 接近 → 徘徊
        return GateState.PENDING

    def get_attention_focus(self, result: AttentionResult) -> List[str]:
        """获取注意力焦点（保留的维度）"""
        return [w.dimension for w in result.pruned_weights if w.retained]

    def get_attention_blind(self, result: AttentionResult) -> List[str]:
        """获取注意力盲区（被坐忘的维度）"""
        return [w.dimension for w in result.pruned_weights if not w.retained]

    def batch_zuowang(
        self,
        units: List[CognitiveUnit],
        auto_judge: bool = True,
    ) -> List[AttentionResult]:
        """批量坐忘"""
        return [self.zuowang(u, auto_judge) for u in units]

    def get_statistics(self) -> Dict[str, Any]:
        """获取坐忘统计"""
        if not self._attention_log:
            return {}
        total = len(self._attention_log)
        avg_sparsity = sum(r.sparsity for r in self._attention_log) / total
        gate_stats = {'open': 0, 'pending': 0, 'closed': 0}
        for r in self._attention_log:
            gate_stats[r.gate_state] += 1
        return {
            'total_judgments': total,
            'avg_sparsity': avg_sparsity,
            'gate_stats': gate_stats,
        }


# ============================================================================
# 全局单例
# ============================================================================

_ZUOWANG_INSTANCE: Optional[ZuowangAttention] = None


def get_zuowang_attention() -> ZuowangAttention:
    """获取全局坐忘注意力调度器"""
    global _ZUOWANG_INSTANCE
    if _ZUOWANG_INSTANCE is None:
        _ZUOWANG_INSTANCE = ZuowangAttention()
    return _ZUOWANG_INSTANCE


def reset_zuowang_attention() -> None:
    """重置全局单例"""
    global _ZUOWANG_INSTANCE
    _ZUOWANG_INSTANCE = None