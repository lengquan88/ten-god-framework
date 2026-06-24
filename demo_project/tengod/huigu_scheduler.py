"""
huigu_scheduler.py — 回头看调度器 v2.14.0
=============================================
道曰："强行者，有志也。"

废除动态 LR 调度，改为"回头看"调度器：
  根据过去 N 步梯度投影的夹角，动态决定是否做"静默"（停止梯度下降，启动回忆拟合）。

核心机制：
  1. 梯度轨迹对齐 — 检查当前方向是否偏离了"道"（初始化分布）
  2. 静默模式 — 停止梯度下降，启动回忆拟合
  3. 回溯性对齐 — 确认当前方向与历史轨迹的一致性
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math
import time


# ============================================================================
# 梯度轨迹
# ============================================================================

@dataclass
class GradientSnapshot:
    """梯度快照"""
    step: int
    direction: List[float]           # 梯度方向向量
    magnitude: float                 # 梯度模长
    angle_to_origin: float           # 与初始方向的夹角
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 回头看调度器
# ============================================================================

class HuiguScheduler:
    """
    回头看调度器。

    不是从外部调整学习率，而是从内部审视：当前方向是否违背了"道"？
    """

    def __init__(self, window_size: int = 10, max_angle: float = 45.0):
        """
        Args:
            window_size: 回溯窗口大小
            max_angle: 最大允许偏离角度（度）
        """
        self.window_size = window_size
        self.max_angle = max_angle
        self._history: List[GradientSnapshot] = []
        self._initial_direction: Optional[List[float]] = None
        self._silent_count = 0
        self._recall_count = 0
        self._total_steps = 0

    def register_gradient(
        self, step: int, gradient: List[float]
    ) -> Dict[str, Any]:
        """
        注册梯度并判断是否应该"静默"。

        Returns:
            {
                "action": "continue" | "silent" | "recall",
                "angle": float,  # 与初始方向的夹角
                "trajectory_health": float,  # 轨迹健康度 (0-1)
            }
        """
        self._total_steps += 1

        if not gradient or all(g == 0 for g in gradient):
            return {"action": "continue", "angle": 0, "trajectory_health": 1.0}

        # 记录初始方向
        if self._initial_direction is None:
            self._initial_direction = list(gradient)

        # 计算梯度模长
        magnitude = math.sqrt(sum(g ** 2 for g in gradient))

        # 计算与初始方向的夹角
        angle = self._compute_angle(self._initial_direction, gradient)

        snapshot = GradientSnapshot(
            step=step,
            direction=list(gradient),
            magnitude=magnitude,
            angle_to_origin=angle,
        )
        self._history.append(snapshot)
        if len(self._history) > self.window_size * 2:
            self._history = self._history[-self.window_size * 2:]

        # 判断动作
        action = self._decide_action(angle, magnitude)

        if action == "silent":
            self._silent_count += 1
        elif action == "recall":
            self._recall_count += 1

        return {
            "action": action,
            "angle": round(angle, 2),
            "magnitude": round(magnitude, 4),
            "trajectory_health": round(self._compute_health(), 3),
            "step": step,
        }

    def _compute_angle(self, v1: List[float], v2: List[float]) -> float:
        """计算两个向量的夹角（度）"""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a ** 2 for a in v1))
        norm2 = math.sqrt(sum(b ** 2 for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        cos_angle = max(-1.0, min(1.0, dot / (norm1 * norm2)))
        return math.degrees(math.acos(cos_angle))

    def _decide_action(self, angle: float, magnitude: float) -> str:
        """
        决定动作：
          - continue: 继续梯度下降
          - silent: 静默 — 停止梯度下降，保持当前参数
          - recall: 回忆拟合 — 回溯到历史最佳状态
        """
        if angle > self.max_angle:
            # 偏离过远 → 静默
            return "silent"
        if magnitude < 1e-6:
            # 梯度消失 → 回忆拟合
            return "recall"
        if len(self._history) >= self.window_size:
            # 检测轨迹震荡
            recent = self._history[-self.window_size:]
            angles = [s.angle_to_origin for s in recent]
            if len(angles) >= 4:
                # 连续震荡 → 静默
                oscillations = sum(
                    1 for i in range(1, len(angles))
                    if abs(angles[i] - angles[i - 1]) > 20
                )
                if oscillations > len(angles) * 0.3:
                    return "silent"
        return "continue"

    def _compute_health(self) -> float:
        """计算轨迹健康度"""
        if len(self._history) < 3:
            return 1.0
        recent = self._history[-self.window_size:]
        angles = [s.angle_to_origin for s in recent]
        avg_angle = sum(angles) / len(angles)
        max_angle = max(angles)
        # 健康度 = 1 - 平均偏离/最大偏离
        health = 1.0 - (avg_angle / max(self.max_angle, max_angle))
        return max(0.0, min(1.0, health))

    def get_best_snapshot(self) -> Optional[GradientSnapshot]:
        """获取历史最佳快照（最小偏离角）"""
        if not self._history:
            return None
        return min(self._history, key=lambda s: s.angle_to_origin)

    def reset_origin(self):
        """重置初始方向（重新校准"道"）"""
        if self._history:
            self._initial_direction = list(self._history[-1].direction)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_steps": self._total_steps,
            "silent_count": self._silent_count,
            "recall_count": self._recall_count,
            "silent_rate": round(self._silent_count / max(1, self._total_steps), 3),
            "recall_rate": round(self._recall_count / max(1, self._total_steps), 3),
            "trajectory_health": round(self._compute_health(), 3),
            "history_size": len(self._history),
        }

    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态（含最近历史）"""
        stats = self.get_stats()
        recent = self._history[-5:] if self._history else []
        return {
            **stats,
            "window_size": self.window_size,
            "max_angle": self.max_angle,
            "recent_history": [
                {"step": s.step, "angle": round(s.angle_to_origin, 2),
                 "magnitude": round(s.magnitude, 4)}
                for s in recent
            ],
        }


# 全局调度器
_huigu_scheduler: Optional[HuiguScheduler] = None


def get_huigu_scheduler(window_size: int = 10, max_angle: float = 45.0) -> HuiguScheduler:
    global _huigu_scheduler
    if _huigu_scheduler is None:
        _huigu_scheduler = HuiguScheduler(window_size=window_size, max_angle=max_angle)
    return _huigu_scheduler


def get_scheduler() -> HuiguScheduler:
    """get_huigu_scheduler 的别名"""
    return get_huigu_scheduler()


__all__ = [
    "GradientSnapshot", "HuiguScheduler",
    "get_huigu_scheduler", "get_scheduler",
]