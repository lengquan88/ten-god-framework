"""
seven_theories_judge.py — 七论裁决器正式版 v4.6.0
=====================================================
道曰："道生一，一生二，二生三，三生万物。"

七论（六论 + 混沌海）：
  1. 本体论 (Ontology)    — 这个模块存在吗？
  2. 认识论 (Epistemology) — 这个模块可以被认知吗？
  3. 实践论 (Praxis)       — 这个模块可以被工程落地吗？
  4. 境界论 (Realm)        — 这个模块提升了系统境界吗？
  5. 未来观论 (Futures)    — 这个模块具有可持续性吗？
  6. 元认知论 (Metacognition) — 系统知道自己正在处理这个模块吗？
  7. 混沌海 (Chaos Sea)    — 是否应该保持为"疑"而非"解"？

七论裁决机制：
- 每论独立裁决，结果为"开/徘徊/关"三态
- 多数投票：开多则开，徘徊多则徘徊，关多则关
- 混沌海有特殊否决权：任何一论判决为"关"，混沌海可将其转为"徘徊"
- 可中断化：任意裁决点都可触发"存疑→混沌海"
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .tbce_unit import CognitiveUnit, GateState, TBCECoordinates
from .object_space import get_object_space


# ============================================================================
# 裁决结果
# ============================================================================

@dataclass
class TheoryVerdict:
    """单论裁决结果"""
    theory_name: str  #: 论名
    theory_index: int  #: 1-7
    state: str  #: open/pending/closed
    score: float  #: 得分 [0, 1]
    reason: str  #: 裁决理由
    interruptible: bool = False  #: 是否可在此中断

@dataclass
class SevenTheoriesVerdict:
    """七论裁决综合结果"""
    unit_id: str
    verdicts: List[TheoryVerdict]
    overall_state: str  #: 多数投票结果
    chaos_sea_override: bool = False  #: 混沌海是否覆盖了某论裁决
    interrupted: bool = False  #: 是否被中断
    interrupted_at: Optional[int] = None  #: 中断在哪一论
    pending_reason: str = ""  #: 存疑原因
    timestamp: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'unit_id': self.unit_id,
            'verdicts': [
                {
                    'theory': v.theory_name,
                    'index': v.theory_index,
                    'state': v.state,
                    'score': round(v.score, 3),
                    'reason': v.reason,
                }
                for v in self.verdicts
            ],
            'overall_state': self.overall_state,
            'chaos_sea_override': self.chaos_sea_override,
            'interrupted': self.interrupted,
            'timestamp': self.timestamp,
        }


# ============================================================================
# 七论裁决器
# ============================================================================

class SevenTheoriesJudge:
    """七论裁决器 —— 六论+混沌海的投票裁决

    裁决流程：
    1. 本体论 → 2. 认识论 → 3. 实践论 → 4. 境界论 → 5. 未来观论 → 6. 元认知论 → 7. 混沌海

    任一步骤都可能触发中断（可中断校准）。
    混沌海有特殊覆盖权：任何一论判决为"关"时，混沌海可以将其转为"徘徊"。
    """

    THEORY_NAMES = [
        "本体论",
        "认识论",
        "实践论",
        "境界论",
        "未来观论",
        "元认知论",
        "混沌海",
    ]

    # 各论阈值
    THRESHOLDS = {
        1: (0.7, 0.4),  # 本体论: open_min=0.7, pending_min=0.4
        2: (0.7, 0.4),  # 认识论
        3: (0.6, 0.3),  # 实践论
        4: (0.6, 0.3),  # 境界论
        5: (0.5, 0.3),  # 未来观论
        6: (0.7, 0.4),  # 元认知论
        7: (0.5, 0.2),  # 混沌海
    }

    def __init__(self, interruptible: bool = True):
        self.interruptible = interruptible
        self._judgment_log: List[SevenTheoriesVerdict] = []

    def judge(
        self,
        unit: CognitiveUnit,
        interruptible: Optional[bool] = None,
    ) -> SevenTheoriesVerdict:
        """对认知单元进行七论裁决

        Args:
            unit: 认知单元
            interruptible: 是否可中断，默认使用实例配置

        Returns:
            七论裁决综合结果
        """
        if interruptible is None:
            interruptible = self.interruptible

        verdicts: List[TheoryVerdict] = []
        interrupted = False
        interrupted_at = None

        # 1. 本体论
        v1 = self._ontology_judge(unit)
        verdicts.append(v1)
        if interruptible and v1.state == GateState.CLOSED and v1.interruptible:
            interrupted = True
            interrupted_at = 1

        # 2. 认识论
        v2 = self._epistemology_judge(unit)
        verdicts.append(v2)
        if interruptible and not interrupted and v2.state == GateState.CLOSED and v2.interruptible:
            interrupted = True
            interrupted_at = 2

        # 3. 实践论
        v3 = self._praxis_judge(unit)
        verdicts.append(v3)
        if interruptible and not interrupted and v3.state == GateState.CLOSED and v3.interruptible:
            interrupted = True
            interrupted_at = 3

        # 4. 境界论
        v4 = self._realm_judge(unit)
        verdicts.append(v4)

        # 5. 未来观论
        v5 = self._futures_judge(unit)
        verdicts.append(v5)

        # 6. 元认知论
        v6 = self._metacognition_judge(unit)
        verdicts.append(v6)
        if interruptible and not interrupted and v6.state == GateState.CLOSED and v6.interruptible:
            interrupted = True
            interrupted_at = 6

        # 7. 混沌海（特殊裁决）
        v7 = self._chaos_sea_judge(unit, verdicts)
        verdicts.append(v7)

        # 投票：多数决
        overall_state = self._majority_vote(verdicts)

        # 混沌海覆盖：如果任何一论是closed，混沌海可以转为pending
        chaos_override = False
        if v7.state == GateState.OPEN:
            has_closed = any(v.state == GateState.CLOSED for v in verdicts[:6])
            if has_closed and overall_state == GateState.CLOSED:
                overall_state = GateState.PENDING
                chaos_override = True

        result = SevenTheoriesVerdict(
            unit_id=unit.unit_id,
            verdicts=verdicts,
            overall_state=overall_state,
            chaos_sea_override=chaos_override,
            interrupted=interrupted,
            interrupted_at=interrupted_at,
        )
        self._judgment_log.append(result)
        return result

    # ── 各论裁决逻辑 ──────────────────────────────────

    def _ontology_judge(self, unit: CognitiveUnit) -> TheoryVerdict:
        """本体论裁决：这个模块存在吗？

        依据：S维度（事实可信度）+ 模块路径合法性
        """
        coord = unit.coordinates
        score = coord.S
        open_min, pending_min = self.THRESHOLDS[1]
        state = GateState.from_threshold(score, open_min, pending_min)

        reason = f"S={coord.S:.2f}"
        if not unit.module_path:
            score = 0.0
            state = GateState.CLOSED
            reason = "缺少module_path"

        return TheoryVerdict(
            theory_name="本体论",
            theory_index=1,
            state=state,
            score=score,
            reason=reason,
            interruptible=True,  # 本体论可中断
        )

    def _epistemology_judge(self, unit: CognitiveUnit) -> TheoryVerdict:
        """认识论裁决：这个模块可以被认知吗？

        依据：P维度（投影保真度）+ E维度（边缘探索度）
        """
        coord = unit.coordinates
        # 认知得分 = P的保真度 * (1 - E的边界惩罚)
        score = coord.P * (1.0 - 0.5 * coord.E)
        open_min, pending_min = self.THRESHOLDS[2]
        state = GateState.from_threshold(score, open_min, pending_min)

        reason = f"P={coord.P:.2f}, E={coord.E:.2f}"
        return TheoryVerdict(
            theory_name="认识论",
            theory_index=2,
            state=state,
            score=score,
            reason=reason,
            interruptible=True,  # 认识论可中断
        )

    def _praxis_judge(self, unit: CognitiveUnit) -> TheoryVerdict:
        """实践论裁决：这个模块可以被工程落地吗？

        依据：I维度（交织稳定性）+ C维度（图层对齐度）
        """
        coord = unit.coordinates
        score = (coord.I + coord.C) / 2.0
        open_min, pending_min = self.THRESHOLDS[3]
        state = GateState.from_threshold(score, open_min, pending_min)

        reason = f"I={coord.I:.2f}, C={coord.C:.2f}"
        return TheoryVerdict(
            theory_name="实践论",
            theory_index=3,
            state=state,
            score=score,
            reason=reason,
            interruptible=False,  # 实践论不可中断（工程必须落地）
        )

    def _realm_judge(self, unit: CognitiveUnit) -> TheoryVerdict:
        """境界论裁决：这个模块提升了系统境界吗？

        依据：认知层 + 门禁宫
        """
        coord = unit.coordinates
        # 高认知层 + 有门禁宫 → 高境界
        layer_score = (unit.cognitive_layer - 1) / 7.0  # L1=0, L8=1
        palace_score = 0.3 if unit.palace_id else 0.0
        score = coord.S * 0.3 + layer_score * 0.4 + palace_score * 0.3
        open_min, pending_min = self.THRESHOLDS[4]
        state = GateState.from_threshold(score, open_min, pending_min)

        reason = f"L{unit.cognitive_layer}, 宫{unit.palace_id or 'N/A'}"
        return TheoryVerdict(
            theory_name="境界论",
            theory_index=4,
            state=state,
            score=score,
            reason=reason,
            interruptible=False,
        )

    def _futures_judge(self, unit: CognitiveUnit) -> TheoryVerdict:
        """未来观论裁决：这个模块具有可持续性吗？

        依据：T维度（时间坐标） + E维度（边缘探索度）
        """
        coord = unit.coordinates
        # 未来观 = 当前时间相关度 + 探索潜力
        score = coord.T * 0.5 + coord.E * 0.5
        open_min, pending_min = self.THRESHOLDS[5]
        state = GateState.from_threshold(score, open_min, pending_min)

        reason = f"T={coord.T:.2f}, E={coord.E:.2f}"
        return TheoryVerdict(
            theory_name="未来观论",
            theory_index=5,
            state=state,
            score=score,
            reason=reason,
            interruptible=False,
        )

    def _metacognition_judge(self, unit: CognitiveUnit) -> TheoryVerdict:
        """元认知论裁决：系统知道自己正在处理这个模块吗？

        依据：综合评分 + 门禁宫（中五=紫微垣=元认知中心）
        """
        coord = unit.coordinates
        score = (coord.S + coord.P + coord.I + coord.C) / 4.0
        # 中五宫（紫微垣）加权
        if unit.palace_id == 5:
            score += 0.1
        open_min, pending_min = self.THRESHOLDS[6]
        state = GateState.from_threshold(score, open_min, pending_min)

        reason = f"综合={score:.2f}"
        if unit.palace_id == 5:
            reason += "（紫微垣）"
        return TheoryVerdict(
            theory_name="元认知论",
            theory_index=6,
            state=state,
            score=score,
            reason=reason,
            interruptible=True,  # 元认知可中断
        )

    def _chaos_sea_judge(
        self,
        unit: CognitiveUnit,
        pre_verdicts: List[TheoryVerdict],
    ) -> TheoryVerdict:
        """混沌海裁决：是否应该保持为"疑"而非"解"？

        混沌海裁决逻辑：
        - 如果前六论都开 → 混沌海也开（不需要存疑）
        - 如果前六论有徘徊 → 混沌海开（支持存疑）
        - 如果前六论有关 → 混沌海开（覆盖为徘徊）
        - 如果E维度极高 → 混沌海开（边界探索需要存疑空间）
        """
        coord = unit.coordinates
        # 检查前六论状态
        all_open = all(v.state == GateState.OPEN for v in pre_verdicts)
        any_closed = any(v.state == GateState.CLOSED for v in pre_verdicts)
        any_pending = any(v.state == GateState.PENDING for v in pre_verdicts)

        if all_open and coord.E < 0.5:
            score = 0.9
            state = GateState.OPEN
            reason = "六论全开，不需要存疑"
        elif any_closed:
            score = 0.8
            state = GateState.OPEN
            reason = "存在裁决关闭，混沌海覆盖为存疑"
        else:
            score = 0.7
            state = GateState.OPEN
            reason = "混沌海保持存疑空间"

        return TheoryVerdict(
            theory_name="混沌海",
            theory_index=7,
            state=state,
            score=score,
            reason=reason,
            interruptible=False,
        )

    # ── 投票机制 ──────────────────────────────────────

    def _majority_vote(self, verdicts: List[TheoryVerdict]) -> str:
        """多数投票"""
        counts = {'open': 0, 'pending': 0, 'closed': 0}
        for v in verdicts:
            counts[v.state] += 1

        # 排除混沌海的投票（第7论），只计前6论
        front_counts = {'open': 0, 'pending': 0, 'closed': 0}
        for v in verdicts[:6]:
            front_counts[v.state] += 1

        # 多数决：开多则开，徘徊多则徘徊，关多则关
        if front_counts['open'] >= front_counts['pending'] and front_counts['open'] >= front_counts['closed']:
            if front_counts['open'] >= 4:
                return GateState.OPEN
            elif front_counts['open'] >= 3:
                return GateState.PENDING
            else:
                return GateState.PENDING

        if front_counts['pending'] >= front_counts['closed']:
            return GateState.PENDING
        else:
            return GateState.CLOSED

    def get_statistics(self) -> Dict[str, Any]:
        """获取裁决统计"""
        if not self._judgment_log:
            return {}
        total = len(self._judgment_log)
        states = {'open': 0, 'pending': 0, 'closed': 0}
        interrupted = 0
        for j in self._judgment_log:
            states[j.overall_state] += 1
            if j.interrupted:
                interrupted += 1
        return {
            'total': total,
            'states': states,
            'interrupted': interrupted,
            'interrupt_ratio': interrupted / total,
        }

    def get_theory_stats(self) -> Dict[str, Dict[str, int]]:
        """获取各论统计"""
        stats = {name: {'open': 0, 'pending': 0, 'closed': 0} for name in self.THEORY_NAMES}
        for j in self._judgment_log:
            for v in j.verdicts:
                stats[v.theory_name][v.state] += 1
        return stats


# ============================================================================
# 全局单例
# ============================================================================

_SEVEN_JUDGE_INSTANCE: Optional[SevenTheoriesJudge] = None


def get_seven_judge() -> SevenTheoriesJudge:
    """获取全局七论裁决器"""
    global _SEVEN_JUDGE_INSTANCE
    if _SEVEN_JUDGE_INSTANCE is None:
        _SEVEN_JUDGE_INSTANCE = SevenTheoriesJudge()
    return _SEVEN_JUDGE_INSTANCE


def reset_seven_judge() -> None:
    """重置全局单例"""
    global _SEVEN_JUDGE_INSTANCE
    _SEVEN_JUDGE_INSTANCE = None