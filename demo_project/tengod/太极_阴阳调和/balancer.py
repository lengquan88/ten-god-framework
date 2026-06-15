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
            "state": self._state,
            "transitions": len(self._history),
            "yin_count": yin_count,
            "yang_count": yang_count,
            "balanced_count": balanced_count,
        }

    def auto_balance(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """根据系统指标自动评估阴阳状态并决定是否降级。
        metrics 形如：{"cpu": 0.9, "memory": 0.8, "error_rate": 0.3, "throughput": 50}
        返回 {"state": YinYang, "degraded": bool, "reason": str, "recommendations": List[str]}
        """
        score = self.evaluate(metrics)
        stats = self.stats()
        degraded = False
        reasons = []
        recommendations = []

        if stats.get("state") == YinYang.YIN:
            reasons.append("当前为阴态（低负载）")
        elif stats.get("state") == YinYang.YANG:
            reasons.append("当前为阳态（高负载）")

        # 异常指标检测
        for key, threshold in [("cpu", 0.85), ("memory", 0.9), ("error_rate", 0.1)]:
            if key in metrics and metrics[key] > threshold:
                degraded = True
                reasons.append(f"{key}过高({metrics[key]:.0%})")
                recommendations.append(f"建议降级 {key} 相关服务")

        if not reasons:
            reasons.append("系统运行平稳")
        if not recommendations:
            recommendations.append("保持当前状态")

        return {
            "state": stats.get("state"),
            "score": score,
            "degraded": degraded,
            "reason": "; ".join(reasons),
            "recommendations": recommendations,
        }

    def enter_degraded_mode(self, reason: str = "") -> None:
        """进入降级模式（阴态）：减少计算资源占用"""
        self.set_state(YinYang.YIN, reason=f"[降级]{reason}" if reason else "[降级]系统负载过高")

    def exit_degraded_mode(self, reason: str = "") -> None:
        """退出降级模式：恢复正常（阳态）"""
        self.set_state(YinYang.YANG, reason=f"[恢复]{reason}" if reason else "[恢复]系统已稳定")


__all__ = ["TaiChiBalancer", "YinYang", "StateTransition"]
__version__ = "1.4.0"