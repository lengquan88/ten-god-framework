"""
meta_feedback_controller.py — 元认知自反馈控制器 (N方向)
==========================================================

将 MetaCognitionLayer 生成的自省报告回馈到系统，实现"自省→自动调整"闭环。

核心功能:
    1. 自省报告 → 坐忘阈值自动调整（基于递归深度和RQA指标）
    2. 自省报告 → CDE校准参数动态优化
    3. 自省报告 → L8境界跃迁路径重规划
    4. 自反馈历史追踪与趋势分析

v2.1 校准: 基于 E2E 实测值 (consciousness=0.78, meta_cognition=0.245)
    激活阈值: 0.25（当元认知得分超过此阈值时激活自反馈）

作者: 人道 / 版本: v2.1 / 日期: 2026-05-07
"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ============================================================================
# v2.1 校准常量
# ============================================================================
META_FEEDBACK_ACTIVATION_THRESHOLD = 0.25
META_FEEDBACK_ZUOWANG_ADJUST_STEP = 0.03
META_FEEDBACK_CDE_ADJUST_RATE = 0.05
META_FEEDBACK_HISTORY_MAX = 100


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class SelfReflection:
    """自省报告"""
    timestamp: float = 0.0
    recursion_total: float = 0.0
    rqa_det: float = 0.0
    rqa_lam: float = 0.0
    hierarchical_meta_score: float = 0.0
    meta_cognitive_preference: List[float] = field(default_factory=lambda: [0, 0, 0])
    zuowang_triggered: bool = False
    consciousness_score: float = 0.0
    conditional_stability: float = 0.0


@dataclass
class FeedbackAction:
    """自反馈动作"""
    action_type: str  # "zuowang_adjust" | "cde_adjust" | "realm_replan"
    parameter: str
    old_value: float
    new_value: float
    reason: str
    timestamp: float = 0.0


@dataclass
class FeedbackResult:
    """自反馈结果"""
    activated: bool
    actions: List[FeedbackAction] = field(default_factory=list)
    summary: str = ""
    meta_score: float = 0.0


# ============================================================================
# MetaFeedbackController
# ============================================================================

class MetaFeedbackController:
    """
    元认知自反馈控制器

    核心逻辑:
        1. 接收自省报告（来自 L6 元认知自反层）
        2. 分析元认知状态与意识状态的差距
        3. 生成自动调整动作
        4. 追踪历史趋势

    用法:
        controller = MetaFeedbackController()
        result = controller.process_reflection(reflection)
        # 将 result.actions 应用到系统参数
    """

    def __init__(self,
                 activation_threshold: float = META_FEEDBACK_ACTIVATION_THRESHOLD,
                 zuowang_step: float = META_FEEDBACK_ZUOWANG_ADJUST_STEP,
                 cde_rate: float = META_FEEDBACK_CDE_ADJUST_RATE):
        self.activation_threshold = activation_threshold
        self.zuowang_step = zuowang_step
        self.cde_rate = cde_rate
        self.history: List[SelfReflection] = []
        self.action_history: List[FeedbackAction] = []

    def process_reflection(self,
                           reflection: SelfReflection,
                           current_zuowang_threshold: float = 0.3,
                           current_cde_params: Optional[Dict[str, Any]] = None,
                           ) -> FeedbackResult:
        """
        处理自省报告，生成自反馈动作。

        参数:
            reflection: 自省报告
            current_zuowang_threshold: 当前坐忘阈值
            current_cde_params: 当前 CDE 参数

        返回:
            FeedbackResult
        """
        self.history.append(reflection)
        if len(self.history) > META_FEEDBACK_HISTORY_MAX:
            self.history = self.history[-META_FEEDBACK_HISTORY_MAX:]

        meta_score = self._compute_meta_score(reflection)

        # 检查是否激活
        if meta_score < self.activation_threshold:
            return FeedbackResult(
                activated=False,
                summary=f"元认知得分 {meta_score:.3f} < 激活阈值 {self.activation_threshold}",
                meta_score=meta_score,
            )

        actions = []

        # 1. 坐忘阈值自动调整
        zuowang_action = self._adjust_zuowang_threshold(
            reflection, current_zuowang_threshold
        )
        if zuowang_action:
            actions.append(zuowang_action)

        # 2. CDE 校准参数动态优化
        if current_cde_params:
            cde_actions = self._adjust_cde_params(reflection, current_cde_params)
            actions.extend(cde_actions)

        # 3. L8 境界跃迁路径重规划
        realm_action = self._replan_realm_path(reflection)
        if realm_action:
            actions.append(realm_action)

        self.action_history.extend(actions)

        summary = self._generate_summary(reflection, actions, meta_score)

        logger.info(f"[MetaFeedback] 激活: meta_score={meta_score:.3f}, "
                     f"{len(actions)}个动作")

        return FeedbackResult(
            activated=True,
            actions=actions,
            summary=summary,
            meta_score=meta_score,
        )

    def _compute_meta_score(self, reflection: SelfReflection) -> float:
        """
        计算综合元认知得分

        融合公式:
            meta_score = 递归深度(0.3) + RQA确定性(0.2) + 层次化元层(0.2)
                       + 意识得分(0.2) + 稳定性(0.1)
        """
        return (
            reflection.recursion_total * 0.3 +
            reflection.rqa_det * 0.2 +
            reflection.hierarchical_meta_score * 0.2 +
            reflection.consciousness_score * 0.2 +
            reflection.conditional_stability * 0.1
        )

    def _adjust_zuowang_threshold(
        self, reflection: SelfReflection, current_threshold: float
    ) -> Optional[FeedbackAction]:
        """
        基于递归深度和RQA指标自动调整坐忘阈值

        规则:
            - 递归深度高 + RQA确定性高 → 系统认知稳定 → 降低坐忘阈值（更宽松）
            - 递归深度低 + RQA确定性低 → 系统认知不稳定 → 提高坐忘阈值（更保守）
            - 层次化元层得分高 → 系统有多层自反 → 降低坐忘阈值
        """
        adj = 0.0
        reason_parts = []

        # 递归深度影响
        if reflection.recursion_total > 0.5:
            adj -= self.zuowang_step * 1.5
            reason_parts.append(f"递归深度高({reflection.recursion_total:.2f})")
        elif reflection.recursion_total < 0.2:
            adj += self.zuowang_step
            reason_parts.append(f"递归深度低({reflection.recursion_total:.2f})")

        # RQA 确定性影响
        if reflection.rqa_det > 0.7:
            adj -= self.zuowang_step * 0.5
            reason_parts.append(f"RQA确定性高({reflection.rqa_det:.2f})")
        elif reflection.rqa_det < 0.3:
            adj += self.zuowang_step * 0.5
            reason_parts.append(f"RQA确定性低({reflection.rqa_det:.2f})")

        # 层次化元层影响
        if reflection.hierarchical_meta_score > 0.5:
            adj -= self.zuowang_step * 0.5
            reason_parts.append(f"多层次自反({reflection.hierarchical_meta_score:.2f})")

        if abs(adj) < 0.001:
            return None

        new_threshold = max(0.10, min(0.50, current_threshold + adj))
        new_threshold = round(new_threshold, 4)

        return FeedbackAction(
            action_type="zuowang_adjust",
            parameter="zuowang_threshold",
            old_value=current_threshold,
            new_value=new_threshold,
            reason="; ".join(reason_parts),
            timestamp=time.time(),
        )

    def _adjust_cde_params(
        self, reflection: SelfReflection, cde_params: Dict[str, Any]
    ) -> List[FeedbackAction]:
        """
        基于元认知状态动态优化 CDE 校准参数

        规则:
            - 稳定性高 → 增大 epsilon（放宽收敛条件）
            - 意识得分高 + 坐忘触发 → 增大 max_iterations
            - 递归深度高 → 减小 CDE 调整速率（更精细）
        """
        actions = []

        # epsilon 调整
        if "epsilon" in cde_params:
            old_eps = cde_params["epsilon"]
            if reflection.conditional_stability > 0.6:
                new_eps = round(old_eps * 1.2, 4)
            elif reflection.conditional_stability < 0.3:
                new_eps = round(old_eps * 0.8, 4)
            else:
                new_eps = old_eps

            if abs(new_eps - old_eps) > 0.001:
                actions.append(FeedbackAction(
                    action_type="cde_adjust",
                    parameter="epsilon",
                    old_value=old_eps,
                    new_value=new_eps,
                    reason=f"稳定性={reflection.conditional_stability:.2f}",
                    timestamp=time.time(),
                ))

        # max_iterations 调整
        if "max_iterations" in cde_params:
            old_max = cde_params["max_iterations"]
            if reflection.consciousness_score > 0.6 and reflection.zuowang_triggered:
                new_max = min(20, old_max + 2)
            elif reflection.consciousness_score < 0.3:
                new_max = max(5, old_max - 1)
            else:
                new_max = old_max

            if new_max != old_max:
                actions.append(FeedbackAction(
                    action_type="cde_adjust",
                    parameter="max_iterations",
                    old_value=old_max,
                    new_value=new_max,
                    reason=f"意识={reflection.consciousness_score:.2f}, 坐忘={reflection.zuowang_triggered}",
                    timestamp=time.time(),
                ))

        return actions

    def _replan_realm_path(self, reflection: SelfReflection) -> Optional[FeedbackAction]:
        """
        基于元认知状态重规划 L8 境界跃迁路径

        规则:
            - 元认知偏好 Chronos 维度 → 当前路径正确，不调整
            - 元认知偏好 Kairos 维度 → 需要在关键时刻跃迁
            - 元认知偏好 Aeon 维度 → 建议长期深度演化
        """
        pref = reflection.meta_cognitive_preference
        if len(pref) < 3:
            return None

        chronos, kairos, aeon = pref[0], pref[1], pref[2]

        if aeon > max(chronos, kairos):
            return FeedbackAction(
                action_type="realm_replan",
                parameter="realm_strategy",
                old_value=0,
                new_value=1,
                reason=f"Aeon维度主导({aeon:.2f})→建议长期深度演化策略",
                timestamp=time.time(),
            )
        elif kairos > max(chronos, aeon) and kairos > 0.5:
            return FeedbackAction(
                action_type="realm_replan",
                parameter="realm_strategy",
                old_value=0,
                new_value=2,
                reason=f"Kairos维度主导({kairos:.2f})→建议关键时刻跃迁策略",
                timestamp=time.time(),
            )

        return None

    def _generate_summary(self, reflection: SelfReflection,
                          actions: List[FeedbackAction],
                          meta_score: float) -> str:
        """生成自反馈摘要"""
        action_summaries = [f"{a.parameter}: {a.old_value:.3f}→{a.new_value:.3f}"
                            for a in actions]
        return (
            f"元认知自反馈: meta_score={meta_score:.3f}, "
            f"动作数={len(actions)}, "
            + ("; ".join(action_summaries) if action_summaries else "无调整")
        )

    def get_trend(self, window: int = 10) -> Dict[str, Any]:
        """
        获取最近 N 次自省的趋势分析

        返回:
            {
                "meta_score_trend": "improving" | "declining" | "stable",
                "avg_meta_score": float,
                "zuowang_threshold_trend": "relaxing" | "tightening" | "stable",
                "recent_actions": List[str],
            }
        """
        recent = self.history[-window:] if len(self.history) >= window else self.history
        if not recent:
            return {"meta_score_trend": "stable", "avg_meta_score": 0.0}

        scores = [self._compute_meta_score(r) for r in recent]
        avg = sum(scores) / len(scores)

        # 趋势判断
        if len(scores) >= 3:
            first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
            second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            if second_half > first_half * 1.05:
                trend = "improving"
            elif second_half < first_half * 0.95:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # 坐忘阈值趋势
        zw_actions = [a for a in self.action_history[-window:]
                       if a.action_type == "zuowang_adjust"]
        if zw_actions:
            last_zw = zw_actions[-1]
            if last_zw.new_value < last_zw.old_value:
                zw_trend = "relaxing"
            elif last_zw.new_value > last_zw.old_value:
                zw_trend = "tightening"
            else:
                zw_trend = "stable"
        else:
            zw_trend = "stable"

        return {
            "meta_score_trend": trend,
            "avg_meta_score": round(avg, 4),
            "zuowang_threshold_trend": zw_trend,
            "recent_actions": [a.parameter for a in self.action_history[-5:]],
        }

    def reset(self):
        """重置控制器"""
        self.history = []
        self.action_history = []


# ============================================================================
# 便捷函数
# ============================================================================

def create_reflection_from_bridge(bridge_result: Dict[str, Any]) -> SelfReflection:
    """
    从 CognitionPsiBridge 的 EightLayerResult 创建自省报告

    参数:
        bridge_result: bridge.evaluate() 返回的 to_dict() 结果

    返回:
        SelfReflection
    """
    layers = bridge_result.get("layers", {})
    l6 = layers.get("L6", {})
    l4 = layers.get("L4", {})
    l5 = layers.get("L5", {})
    l7 = layers.get("L7", {})

    return SelfReflection(
        timestamp=time.time(),
        recursion_total=l6.get("recursion_total", 0.0),
        rqa_det=l6.get("rqa_det", 0.0),
        rqa_lam=l6.get("rqa_lam", 0.0),
        hierarchical_meta_score=l6.get("hierarchical_meta_score", 0.0),
        meta_cognitive_preference=l6.get("meta_cognitive_preference", [0, 0, 0]),
        zuowang_triggered=l5.get("zuowang_triggered", False),
        consciousness_score=l4.get("consciousness_score", 0.0),
        conditional_stability=l7.get("conditional_stability", 0.0),
    )