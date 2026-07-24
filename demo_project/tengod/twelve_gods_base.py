"""
twelve_gods_base.py — 十二神门禁基础框架 v4.6.0
=====================================================
道曰："道生一，一生二，二生三，三生万物。"

十二神门禁体系将门禁认知系统从九宫格（9维）升级为十二神（12维非线性纠缠）：

五行生克：
  木生火 → 火生土 → 土生金 → 金生水 → 水生木
  木克土 → 土克水 → 水克火 → 火克金 → 金克木

十二神位映射：
  木·比肩 (Peer)        — 架构协同：模块间依赖是否健康？
  木·劫财 (Rob Wealth)   — 攻防边界：系统边界是否安全？
  火·食神 (Eating God)   — 创生输出：生成质量是否达标？
  火·伤官 (Hurting Officer) — 破界创新：创新是否带来系统性风险？
  土·正财 (Direct Wealth) — 知识固化：知识存储是否可靠？
  土·偏财 (Indirect Wealth) — 奇招演化：知识演化是否健康？
  金·正官 (Direct Officer) — 法度调度：调度策略是否合规？
  金·七杀 (Seven Killings) — 品质裁决：输出品质是否达标？
  水·正印 (Direct Resource) — 滋养守护：配置与文档是否健康？
  水·偏印 (Indirect Resource) — 桥接通变：微调与外挂是否安全？
  太极 (Tai Chi)          — 阴阳调和：系统整体是否平衡？
  元辰 (Yuan Chen)        — 本源定位：系统是否在观察自身？

门禁裁决通用接口：
  - judge(unit) → (GateState, reason)
  - 与七论裁决器集成
  - 支持生克关系影响
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import time

from .tbce_unit import CognitiveUnit, GateState, TBCECoordinates


# ============================================================================
# 五行与十二神枚举
# ============================================================================

class FiveElements(Enum):
    """五行"""
    WOOD = "木"
    FIRE = "火"
    EARTH = "土"
    METAL = "金"
    WATER = "水"
    TRANSCENDENT = "太极"  # 超越五行

    @property
    def generates(self) -> "FiveElements":
        """五行相生"""
        cycle = {
            FiveElements.WOOD: FiveElements.FIRE,
            FiveElements.FIRE: FiveElements.EARTH,
            FiveElements.EARTH: FiveElements.METAL,
            FiveElements.METAL: FiveElements.WATER,
            FiveElements.WATER: FiveElements.WOOD,
        }
        return cycle.get(self, FiveElements.TRANSCENDENT)

    @property
    def overcomes(self) -> "FiveElements":
        """五行相克"""
        cycle = {
            FiveElements.WOOD: FiveElements.EARTH,
            FiveElements.EARTH: FiveElements.WATER,
            FiveElements.WATER: FiveElements.FIRE,
            FiveElements.FIRE: FiveElements.METAL,
            FiveElements.METAL: FiveElements.WOOD,
        }
        return cycle.get(self, FiveElements.TRANSCENDENT)


class TwelveGods(Enum):
    """十二神位"""
    # 木
    BIJIAN = "比肩"       # 架构协同
    JIECAI = "劫财"       # 攻防边界
    # 火
    SHISHEN = "食神"      # 创生输出
    SHANGGUAN = "伤官"    # 破界创新
    # 土
    ZHENGCAI = "正财"     # 知识固化
    PIANCAI = "偏财"      # 奇招演化
    # 金
    ZHENGGUAN = "正官"    # 法度调度
    QISHA = "七杀"        # 品质裁决
    # 水
    ZHENGYIN = "正印"     # 滋养守护
    PIANYIN = "偏印"      # 桥接通变
    # 太极
    TAIJI = "太极"        # 阴阳调和
    YUANCHEN = "元辰"     # 本源定位

    @property
    def element(self) -> FiveElements:
        return GOD_ELEMENT_MAP[self]

    @property
    def gate_type(self) -> str:
        return GOD_GATE_MAP[self]


# 神位 → 五行
GOD_ELEMENT_MAP = {
    TwelveGods.BIJIAN: FiveElements.WOOD,
    TwelveGods.JIECAI: FiveElements.WOOD,
    TwelveGods.SHISHEN: FiveElements.FIRE,
    TwelveGods.SHANGGUAN: FiveElements.FIRE,
    TwelveGods.ZHENGCAI: FiveElements.EARTH,
    TwelveGods.PIANCAI: FiveElements.EARTH,
    TwelveGods.ZHENGGUAN: FiveElements.METAL,
    TwelveGods.QISHA: FiveElements.METAL,
    TwelveGods.ZHENGYIN: FiveElements.WATER,
    TwelveGods.PIANYIN: FiveElements.WATER,
    TwelveGods.TAIJI: FiveElements.TRANSCENDENT,
    TwelveGods.YUANCHEN: FiveElements.TRANSCENDENT,
}

# 神位 → 门禁类型
GOD_GATE_MAP = {
    TwelveGods.BIJIAN: "architecture",
    TwelveGods.JIECAI: "architecture",
    TwelveGods.SHISHEN: "innovation",
    TwelveGods.SHANGGUAN: "innovation",
    TwelveGods.ZHENGCAI: "knowledge",
    TwelveGods.PIANCAI: "knowledge",
    TwelveGods.ZHENGGUAN: "law",
    TwelveGods.QISHA: "law",
    TwelveGods.ZHENGYIN: "nourish",
    TwelveGods.PIANYIN: "nourish",
    TwelveGods.TAIJI: "self_referential",
    TwelveGods.YUANCHEN: "self_referential",
}


# ============================================================================
# 门禁裁决基类
# ============================================================================

@dataclass
class GateVerdict:
    """门禁裁决结果"""
    god: TwelveGods
    state: str               # open/pending/closed
    score: float             # 得分 [0, 1]
    reason: str              # 裁决理由
    element: FiveElements
    element_boost: float = 0.0  # 五行生克加成
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "god": self.god.value,
            "god_name": self.god.name,
            "state": self.state,
            "score": round(self.score, 3),
            "reason": self.reason,
            "element": self.element.value,
            "element_boost": round(self.element_boost, 3),
        }


class TwelveGodsGate:
    """十二神门禁基类

    每个具体门禁继承此类，实现 _judge_impl 方法。
    基类提供五行生克加成计算。
    """

    def __init__(self, god: TwelveGods):
        self.god = god
        self.element = god.element
        self.gate_type = god.gate_type
        self._verdict_log: List[GateVerdict] = []

    def judge(self, unit: CognitiveUnit) -> GateVerdict:
        """门禁裁决（模板方法）"""
        verdict = self._judge_impl(unit)

        # 五行生克加成
        verdict.element_boost = self._compute_element_boost(unit)

        # 应用生克加成到得分
        adjusted_score = max(0.0, min(1.0, verdict.score + verdict.element_boost))
        if adjusted_score != verdict.score:
            verdict.score = adjusted_score
            # 重新判定状态
            if verdict.score >= 0.7:
                verdict.state = GateState.OPEN
            elif verdict.score >= 0.4:
                verdict.state = GateState.PENDING
            else:
                verdict.state = GateState.CLOSED

        self._verdict_log.append(verdict)
        return verdict

    def _judge_impl(self, unit: CognitiveUnit) -> GateVerdict:
        """子类实现具体裁决逻辑"""
        raise NotImplementedError

    def _compute_element_boost(self, unit: CognitiveUnit) -> float:
        """计算五行生克加成

        基于模块的palace_id和cognitive_layer推算五行属性，
        与本门禁的五行进行生克计算。
        """
        if self.element == FiveElements.TRANSCENDENT:
            return 0.0

        # 从 palace_id 推算模块五行
        # 九宫 → 五行: 坎1(水), 坤2(土), 震3(木), 巽4(木),
        #   中5(土), 乾6(金), 兑7(金), 艮8(土), 离9(火)
        palace_element_map = {
            1: FiveElements.WATER, 2: FiveElements.EARTH,
            3: FiveElements.WOOD, 4: FiveElements.WOOD,
            5: FiveElements.EARTH, 6: FiveElements.METAL,
            7: FiveElements.METAL, 8: FiveElements.EARTH,
            9: FiveElements.FIRE,
        }

        unit_element = FiveElements.EARTH  # 默认
        if unit.palace_id and unit.palace_id in palace_element_map:
            unit_element = palace_element_map[unit.palace_id]

        # 生克计算
        if unit_element == self.element:
            return 0.05  # 同五行：轻微加成
        if unit_element.generates == self.element:
            return 0.08  # 生我：加成
        if self.element.generates == unit_element:
            return -0.03  # 我生：轻微削弱
        if self.element.overcomes == unit_element:
            return 0.03  # 我克：微小加成
        if unit_element.overcomes == self.element:
            return -0.05  # 克我：削弱

        return 0.0

    def get_verdict_history(self) -> List[GateVerdict]:
        return self._verdict_log

    def get_statistics(self) -> Dict[str, Any]:
        if not self._verdict_log:
            return {}
        total = len(self._verdict_log)
        states = {'open': 0, 'pending': 0, 'closed': 0}
        for v in self._verdict_log:
            states[v.state] += 1
        return {
            'god': self.god.value,
            'total': total,
            'states': states,
            'avg_score': sum(v.score for v in self._verdict_log) / total,
        }


__all__ = [
    "FiveElements", "TwelveGods", "GOD_ELEMENT_MAP", "GOD_GATE_MAP",
    "GateVerdict", "TwelveGodsGate",
]