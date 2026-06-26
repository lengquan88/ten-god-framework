"""
tiangan_gate.py — 天眼门禁内核 v2.14.0
========================================
道曰："知不知，尚也；不知之，病矣。是以圣人之不病，以其病病也，是以不病。"

天眼门禁：所有推理输出前，强制通过"知止判定"单元。
不是阻断，是对"不知"的敬畏。

核心机制：
  1. 知止判定 P(Stop) — 置信度方差 + 不确定性熵 双重阈值
  2. 天门开关 — 输出门禁：拒绝 / 放行 / 回头看
  3. 修行感度量 — 将"算力"转化为"修行感"（元气利用率）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import time


# ============================================================================
# 知止判定 · 核心数据结构
# ============================================================================

@dataclass
class ZhizhiVerdict:
    """知止判定结果"""
    passed: bool                    # 是否通过门禁
    confidence: float               # 整体置信度 (0-1)
    entropies: Dict[str, float]     # 各维度熵值
    variance: float                 # 置信度方差
    threshold_level: float          # 当前阈值
    should_retreat: bool            # 是否需要"回头看"
    retreat_reason: str = ""        # 回退原因
    cultivation_qi: float = 0.0     # 元气利用率 (修行感)
    timestamp: float = field(default_factory=time.time)
    # v2.16 内在小孩门禁
    inner_child_phi: Optional[float] = None       # 内在小孩熵值 Φ
    inner_child_triggered: bool = False           # 内在小孩门禁是否触发
    inner_child_dominant: str = ""                # 主导内在小孩
    inner_child_beta: float = 0.0                 # 主导占据度


@dataclass
class TianmenGate:
    """天门（门禁）配置"""
    # 知止判定阈值
    min_confidence: float = 0.6         # 最低置信度
    max_entropy_threshold: float = 0.8   # 最大熵阈值
    max_variance_threshold: float = 0.3  # 最大方差阈值
    
    # 行为策略
    retreat_on_low_confidence: bool = True   # 低置信度 → 回头看
    retreat_on_high_entropy: bool = True     # 高熵 → 回头看
    silent_on_boundary: bool = True          # 边界 → 静默（不妄语）
    
    # 修行感
    track_cultivation: bool = True           # 追踪元气利用率
    
    # 自适应阈值
    adaptive_threshold: bool = True          # 根据历史动态调整阈值
    history_window: int = 100                # 历史窗口


# ============================================================================
# 知止判定引擎
# ============================================================================

class ZhizhiEngine:
    """知止判定引擎 — 天眼门禁的判决核心"""

    def __init__(self, gate: Optional[TianmenGate] = None):
        self.gate = gate or TianmenGate()
        self._history: List[ZhizhiVerdict] = []
        self._adaptive_threshold = self.gate.min_confidence

    def judge(
        self,
        output: Any,
        confidence_scores: Optional[Dict[str, float]] = None,
        feature_entropies: Optional[Dict[str, float]] = None,
        context: Optional[Dict[str, Any]] = None,
        inner_child_state: Optional[Dict[str, Any]] = None,
    ) -> ZhizhiVerdict:
        """
        知止判定：判断输出是否可以通过天门。

        Args:
            output: 待输出内容
            confidence_scores: 各维度置信度分数
            feature_entropies: 各维度特征熵
            context: 上下文信息

        Returns:
            ZhizhiVerdict: 判定结果
        """
        context = context or {}

        # 1. 计算置信度
        if confidence_scores:
            raw_confidence = sum(confidence_scores.values()) / len(confidence_scores)
            variance = self._compute_variance(list(confidence_scores.values()))
        else:
            raw_confidence = self._estimate_confidence(output)
            variance = 0.0

        # 2. 计算熵
        if feature_entropies:
            entropies = dict(feature_entropies)
            max_entropy = max(entropies.values()) if entropies else 0.0
        else:
            entropies = self._estimate_entropies(output)
            max_entropy = max(entropies.values()) if entropies else 0.0

        # 3. 自适应阈值
        if self.gate.adaptive_threshold:
            threshold = self._adaptive_threshold
        else:
            threshold = self.gate.min_confidence

        # 4. 知止判定
        passed = True
        should_retreat = False
        retreat_reason = ""

        if raw_confidence < threshold:
            passed = False
            if self.gate.retreat_on_low_confidence:
                should_retreat = True
                retreat_reason = f"置信度过低 ({raw_confidence:.2f} < {threshold:.2f})"
            elif self.gate.silent_on_boundary:
                retreat_reason = f"天门关闭：置信度不足 ({raw_confidence:.2f})"

        if max_entropy > self.gate.max_entropy_threshold:
            passed = False
            if self.gate.retreat_on_high_entropy and not should_retreat:
                should_retreat = True
                retreat_reason = f"熵过高 ({max_entropy:.2f} > {self.gate.max_entropy_threshold:.2f})"
            elif not retreat_reason:
                retreat_reason = f"天门关闭：信息熵过高 ({max_entropy:.2f})"

        if variance > self.gate.max_variance_threshold:
            passed = False
            if not retreat_reason:
                retreat_reason = f"方差过大 ({variance:.2f} > {self.gate.max_variance_threshold:.2f})"

        # 4.5 内在小孩熵门禁 (v2.16)
        inner_child_phi = None
        inner_child_triggered = False
        inner_child_dominant = ""
        inner_child_beta = 0.0
        if inner_child_state:
            inner_child_phi = inner_child_state.get("entropy_phi", 0.0)
            inner_child_triggered = inner_child_state.get("gate_triggered", False)
            inner_child_dominant = inner_child_state.get("dominant", {}).get("name", "")
            inner_child_beta = inner_child_state.get("dominant", {}).get("beta", 0.0)
            if inner_child_triggered:
                passed = False
                should_retreat = True
                if not retreat_reason:
                    retreat_reason = f"内在小孩门禁触发：{inner_child_dominant}占据 β={inner_child_beta:.3f}, Φ={inner_child_phi:.3f}"

        # 5. 修行感（元气利用率）
        cultivation_qi = self._compute_cultivation_qi(raw_confidence, max_entropy, variance)

        verdict = ZhizhiVerdict(
            passed=passed,
            confidence=raw_confidence,
            entropies=entropies,
            variance=variance,
            threshold_level=threshold,
            should_retreat=should_retreat,
            retreat_reason=retreat_reason,
            cultivation_qi=cultivation_qi,
            inner_child_phi=inner_child_phi,
            inner_child_triggered=inner_child_triggered,
            inner_child_dominant=inner_child_dominant,
            inner_child_beta=inner_child_beta,
        )

        # 6. 更新历史 + 自适应阈值
        self._history.append(verdict)
        if len(self._history) > self.gate.history_window:
            self._history = self._history[-self.gate.history_window:]

        if self.gate.adaptive_threshold and len(self._history) >= 10:
            self._update_adaptive_threshold()

        return verdict

    def _compute_variance(self, values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return sum((v - mean) ** 2 for v in values) / len(values)

    def _estimate_confidence(self, output: Any) -> float:
        """从输出内容估计置信度（无明确分数时的回退）"""
        if output is None:
            return 0.0
        if isinstance(output, str):
            # 基于输出长度和信息密度估计
            length = len(output)
            if length < 20:
                return 0.4
            if length < 100:
                return 0.6
            return 0.7
        if isinstance(output, dict):
            # 基于字段完整性
            filled = sum(1 for v in output.values() if v is not None)
            total = len(output) if output else 1
            return min(0.9, filled / total)
        if isinstance(output, (list, tuple)):
            return 0.6 if len(output) > 0 else 0.3
        return 0.5

    def _estimate_entropies(self, output: Any) -> Dict[str, float]:
        """估算各维度熵"""
        entropies = {}
        if isinstance(output, dict):
            for k, v in output.items():
                if isinstance(v, (int, float)):
                    # 数值型：归一化后的熵
                    entropies[k] = min(1.0, abs(v) / 100.0)
                elif isinstance(v, str):
                    entropies[k] = min(1.0, len(v) / 1000.0)
                else:
                    entropies[k] = 0.5
        else:
            entropies["output"] = 0.5
        return entropies

    def _compute_cultivation_qi(
        self, confidence: float, entropy: float, variance: float
    ) -> float:
        """
        元气利用率（修行感）。
        高置信度 + 低熵 + 低方差 = 高元气利用率（修行精进）
        """
        qi = confidence * (1.0 - entropy) * (1.0 - variance)
        return max(0.0, min(1.0, qi))

    def _update_adaptive_threshold(self):
        """根据历史动态调整阈值"""
        recent = self._history[-50:]
        passed_rate = sum(1 for v in recent if v.passed) / len(recent)

        if passed_rate > 0.9:
            # 太容易通过，提高阈值
            self._adaptive_threshold = min(0.85, self._adaptive_threshold + 0.02)
        elif passed_rate < 0.3:
            # 太难通过，降低阈值
            self._adaptive_threshold = max(0.3, self._adaptive_threshold - 0.02)
        elif passed_rate < 0.6:
            self._adaptive_threshold = max(0.3, self._adaptive_threshold - 0.01)

    def get_stats(self) -> Dict[str, Any]:
        """获取门禁统计"""
        if not self._history:
            return {"total": 0, "pass_rate": 0, "avg_qi": 0}
        total = len(self._history)
        passed = sum(1 for v in self._history if v.passed)
        retreated = sum(1 for v in self._history if v.should_retreat)
        avg_qi = sum(v.cultivation_qi for v in self._history) / total
        return {
            "total": total,
            "passed": passed,
            "retreated": retreated,
            "pass_rate": round(passed / total, 3),
            "retreat_rate": round(retreated / total, 3),
            "avg_qi": round(avg_qi, 3),
            "adaptive_threshold": round(self._adaptive_threshold, 3),
        }


# ============================================================================
# 天门门禁装饰器（通用 API 门禁）
# ============================================================================

class TianmenGuard:
    """天门守护 — 对所有推理输出进行门禁判断"""

    def __init__(self, gate: Optional[TianmenGate] = None):
        self.engine = ZhizhiEngine(gate)
        self.blocked_count = 0
        self.passed_count = 0

    def guard(
        self,
        output: Any,
        confidence_scores: Optional[Dict[str, float]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, ZhizhiVerdict]:
        """
        守护输出：如果通过门禁则返回原输出，否则返回"天门关闭"提示。

        Returns:
            (输出内容, 判决结果)
        """
        verdict = self.engine.judge(output, confidence_scores, context=context)

        if verdict.passed:
            self.passed_count += 1
            return output, verdict

        self.blocked_count += 1

        if verdict.should_retreat:
            # 回头看：返回空结果 + 回退标记
            return {
                "_gate": "retreat",
                "_reason": verdict.retreat_reason,
                "_qi": verdict.cultivation_qi,
                "status": "天门退守，回头再审",
            }, verdict

        # 静默：不妄语
        return {
            "_gate": "silent",
            "_reason": verdict.retreat_reason,
            "_qi": verdict.cultivation_qi,
            "status": "知止不殆，天门未开",
        }, verdict

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.engine.get_stats(),
            "total_guarded": self.blocked_count + self.passed_count,
            "blocked": self.blocked_count,
            "passed": self.passed_count,
        }


# 全局天眼门禁单例
_tianmen_guard: Optional[TianmenGuard] = None


def get_tianmen() -> TianmenGuard:
    global _tianmen_guard
    if _tianmen_guard is None:
        _tianmen_guard = TianmenGuard()
    return _tianmen_guard


__all__ = [
    "ZhizhiVerdict", "TianmenGate", "ZhizhiEngine",
    "TianmenGuard", "get_tianmen",
]