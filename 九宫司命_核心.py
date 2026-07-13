"""
九宫司命_核心.py — 洛书九宫279智能体架构核心
==============================================

九宫格映射:
    坎一(消化) 坤二(留白) 震三(断裂)
    巽四(投影) 中五(呼吸) 乾六(观照)
    兑七(返还) 艮八(归墟) 离九(扮演)

M2.5-B 增强: ZuowangGridInjector — 坐忘状态→九宫格动态重映射
    v2.1 校准: 基于 E2E 实测值 (consciousness=0.78, respiration=1.69→1.82)

作者: 人道 / 版本: v2.1 / 日期: 2026-05-07
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ============================================================================
# v2.1 校准常量（呼吸调制公式更新）
# ============================================================================
ZUOWANG_RESPIRATION_BASE = 1.2         # 呼吸基础值（原1.3→1.2）
ZUOWANG_RESPIRATION_COEFFICIENT = 0.8  # 意识得分系数（原0.5→0.8）
ZUOWANG_RESPIRATION_MAX = 2.2          # 呼吸调制上限（原1.75→2.2）
ZUOWANG_SUPPRESSION_DEPTH = 0.35       # 抑制深度（原0.5→0.35，更深）


# ============================================================================
# 九宫格常量
# ============================================================================

# 九宫格 → 功能映射
PALACE_NAMES = {
    "坎一": "消化",
    "坤二": "留白",
    "震三": "断裂",
    "巽四": "投影",
    "中五": "呼吸",
    "乾六": "观照",
    "兑七": "返还",
    "艮八": "归墟",
    "离九": "扮演",
}

# 坐忘触发时受抑制的宫位
ZUOWANG_SUPPRESSED_PALACES = ["坎一", "巽四", "离九"]

# 坐忘触发时增强的宫位
ZUOWANG_ENHANCED_PALACES = ["坤二", "中五", "艮八"]


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class ZuowangGridState:
    """坐忘九宫格状态"""
    zuowang_triggered: bool = False
    max_relevance: float = 0.0
    threshold: float = 0.3
    consciousness_score: float = 0.0
    respiration_modulation: float = 1.0
    suppressed_palaces: List[str] = field(default_factory=list)
    enhanced_palaces: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zuowang_triggered": self.zuowang_triggered,
            "max_relevance": self.max_relevance,
            "threshold": self.threshold,
            "consciousness_score": self.consciousness_score,
            "respiration_modulation": self.respiration_modulation,
            "suppressed_palaces": self.suppressed_palaces,
            "enhanced_palaces": self.enhanced_palaces,
        }


# ============================================================================
# 九宫司命核心
# ============================================================================

class 九宫司命核心:
    """
    九宫司命核心 — 279智能体调度母版

    九宫格各宫位承载不同的智能体功能，中五(呼吸)是核心调度枢纽。
    """

    def __init__(self):
        # 权重状态：各宫位当前权重（默认为1.0）
        self.权重状态 = {
            "坎一": 1.0, "坤二": 1.0, "震三": 1.0,
            "巽四": 1.0, "中五": 1.0, "乾六": 1.0,
            "兑七": 1.0, "艮八": 1.0, "离九": 1.0,
        }
        self.呼吸计数 = 0
        self.调度日志: List[Dict[str, Any]] = []

    def 获取宫位功能(self, 宫位: str) -> str:
        return PALACE_NAMES.get(宫位, "未知")

    def 获取权重(self, 宫位: str) -> float:
        return self.权重状态.get(宫位, 1.0)

    def 设置权重(self, 宫位: str, 权重: float):
        if 宫位 in self.权重状态:
            self.权重状态[宫位] = round(权重, 4)
            self.调度日志.append({
                "action": "set_weight",
                "palace": 宫位,
                "weight": 权重,
                "function": self.获取宫位功能(宫位),
            })

    def 呼吸(self) -> float:
        """执行一次呼吸调度，返回当前中五权重"""
        self.呼吸计数 += 1
        return self.权重状态.get("中五", 1.0)

    def 重置(self):
        """重置所有宫位权重为默认值"""
        for k in self.权重状态:
            self.权重状态[k] = 1.0
        self.呼吸计数 = 0
        self.调度日志 = []

    def 获取状态摘要(self) -> Dict[str, Any]:
        return {
            "呼吸计数": self.呼吸计数,
            "权重状态": dict(self.权重状态),
            "调度日志条目数": len(self.调度日志),
        }


# ============================================================================
# ZuowangGridInjector — 坐忘九宫格注入器 (M2.5-B)
# ============================================================================

class ZuowangGridInjector:
    """
    坐忘状态 → 九宫格动态重映射

    坐忘触发时:
        坎一(消化) ↓ 抑制深度
        坤二(留白) ↑ 1.3x
        震三(断裂) → 不变
        巽四(投影) ↓ 抑制深度
        中五(呼吸) ↑ 呼吸调制系数
        乾六(观照) ↑ 1.3x
        兑七(返还) ↑ 1.2x
        艮八(归墟) ↑ 1.4x
        离九(扮演) ↓ 抑制深度

    坐忘关闭时: 全部恢复为 1.0

    v2.1 校准: 呼吸公式从 1.3+cs*0.5 改为 1.2+cs*0.8，上限 2.2
    """

    def __init__(self):
        self.current_weights: Dict[str, float] = {
            "坎一": 1.0, "坤二": 1.0, "震三": 1.0,
            "巽四": 1.0, "中五": 1.0, "乾六": 1.0,
            "兑七": 1.0, "艮八": 1.0, "离九": 1.0,
        }
        self._state = ZuowangGridState()

    def update(self,
               zuowang_triggered: bool,
               max_relevance: float = 0.0,
               threshold: float = 0.3,
               consciousness_score: float = 0.0) -> ZuowangGridState:
        """
        更新坐忘九宫格状态

        返回: ZuowangGridState
        """
        if not zuowang_triggered:
            # 恢复默认权重
            for k in self.current_weights:
                self.current_weights[k] = 1.0
            self._state = ZuowangGridState(
                zuowang_triggered=False,
                max_relevance=max_relevance,
                threshold=threshold,
                consciousness_score=consciousness_score,
                respiration_modulation=1.0,
                suppressed_palaces=[],
                enhanced_palaces=[],
            )
            return self._state

        # 坐忘触发：计算呼吸调制系数（v2.1 校准公式）
        respiration = ZUOWANG_RESPIRATION_BASE + consciousness_score * ZUOWANG_RESPIRATION_COEFFICIENT
        respiration = min(respiration, ZUOWANG_RESPIRATION_MAX)

        # 抑制宫位
        for p in ZUOWANG_SUPPRESSED_PALACES:
            if p in self.current_weights:
                self.current_weights[p] = ZUOWANG_SUPPRESSION_DEPTH

        # 增强宫位
        self.current_weights["坤二"] = 1.3
        self.current_weights["中五"] = respiration
        self.current_weights["乾六"] = 1.3
        self.current_weights["兑七"] = 1.2
        self.current_weights["艮八"] = 1.4

        # 不变宫位
        self.current_weights["震三"] = 1.0

        self._state = ZuowangGridState(
            zuowang_triggered=True,
            max_relevance=max_relevance,
            threshold=threshold,
            consciousness_score=consciousness_score,
            respiration_modulation=round(respiration, 4),
            suppressed_palaces=list(ZUOWANG_SUPPRESSED_PALACES),
            enhanced_palaces=list(ZUOWANG_ENHANCED_PALACES),
        )

        logger.info(
            f"[ZuowangGridInjector] 坐忘触发: 呼吸={respiration:.2f}x, "
            f"抑制={ZUOWANG_SUPPRESSED_PALACES}, 增强={ZUOWANG_ENHANCED_PALACES}"
        )
        return self._state

    def get_state(self) -> ZuowangGridState:
        return self._state

    def apply_to_grid_core(self, core: 九宫司命核心) -> str:
        """
        将坐忘调制应用到九宫司命核心

        返回: 操作摘要
        """
        if not self._state.zuowang_triggered:
            return "ZuowangGridInjector: 未触发，无操作"

        for palace, weight in self.current_weights.items():
            core.设置权重(palace, weight)

        # 呼吸计数增加
        for _ in range(int(self._state.respiration_modulation)):
            core.呼吸()

        return (f"ZuowangGridInjector: 已应用, 呼吸={self._state.respiration_modulation:.2f}x, "
                f"抑制={self._state.suppressed_palaces}, 增强={self._state.enhanced_palaces}")

    def reset(self):
        """重置注入器"""
        for k in self.current_weights:
            self.current_weights[k] = 1.0
        self._state = ZuowangGridState()