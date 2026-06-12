#!/usr/bin/env python3
"""
太极_阴阳调和 — 平衡调节/状态切换
太极主理调和，承担系统的阴阳平衡与状态切换职责。
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
import time


class YinYang(Enum):
    """阴阳状态"""
    YIN = "yin"    # 阴态：静止、收敛、保守
    YANG = "yang"  # 阳态：活跃、扩张、进取
    BALANCED = "balanced"  # 平衡态


@dataclass
class StateTransition:
    """状态转换记录"""
    from_state: YinYang
    to_state: YinYang
    reason: str
    timestamp: float = field(default_factory=time.time)


class TaiChiBalancer:
    """太极调和器 — 阴阳之枢

    管理系统的阴阳状态，支持动态切换与平衡调节。
    """

    def __init__(self, initial_state: YinYang = YinYang.BALANCED):
        self._state = initial_state
        self._history: List[StateTransition] = []
        self._yin_threshold = 0.3
        self._yang_threshold = 0.7
        self._balance_callbacks: Dict[YinYang, List[Callable]] = {
            YinYang.YIN: [],
            YinYang.YANG: [],
            YinYang.BALANCED: [],
        }

    def get_state(self) -> YinYang:
        """获取当前状态"""
        return self._state

    def set_state(self, new_state: YinYang, reason: str = "") -> YinYang:
        """设置状态"""
        old_state = self._state
        self._state = new_state
        self._history.append(StateTransition(
            from_state=old_state,
            to_state=new_state,
            reason=reason,
        ))
        # 触发回调
        for callback in self._balance_callbacks[new_state]:
            callback(old_state, new_state)
        return self._state

    def toggle(self, reason: str = "") -> YinYang:
        """切换状态（阴 ↔ 阳）"""
        if self._state == YinYang.YIN:
            return self.set_state(YinYang.YANG, reason)
        elif self._state == YinYang.YANG:
            return self.set_state(YinYang.YIN, reason)
        else:
            return self.set_state(YinYang.YANG, reason)

    def balance(self, reason: str = "") -> YinYang:
        """回归平衡态"""
        return self.set_state(YinYang.BALANCED, reason)

    def evaluate(self, metrics: Dict[str, float]) -> YinYang:
        """基于指标评估状态"""
        total = sum(metrics.values())
        if total < self._yin_threshold:
            return self.set_state(YinYang.YIN, "metrics below threshold")
        elif total > self._yang_threshold:
            return self.set_state(YinYang.YANG, "metrics above threshold")
        else:
            return self.set_state(YinYang.BALANCED, "metrics in balance")

    def register_callback(self, state: YinYang, callback: Callable) -> None:
        """注册状态回调"""
        self._balance_callbacks[state].append(callback)

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取状态转换历史"""
        return [
            {
                "from": t.from_state.value,
                "to": t.to_state.value,
                "reason": t.reason,
                "timestamp": t.timestamp,
            }
            for t in self._history[-limit:]
        ]

    def stats(self) -> Dict[str, Any]:
        """统计信息"""
        yin_count = sum(1 for t in self._history if t.to_state == YinYang.YIN)
        yang_count = sum(1 for t in self._history if t.to_state == YinYang.YANG)
        balanced_count = sum(1 for t in self._history if t.to_state == YinYang.BALANCED)
        return {
            "current_state": self._state.value,
            "transitions": len(self._history),
            "yin_count": yin_count,
            "yang_count": yang_count,
            "balanced_count": balanced_count,
        }


__all__ = ["TaiChiBalancer", "YinYang", "StateTransition"]
__version__ = "1.0.0"