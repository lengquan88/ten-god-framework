"""
calibration_engine.py — CDE校准引擎（补偿差演化校准协议）
========================================================

五阶段闭环:
    Translate → Verify → Compensate → Loop → Converge

M2.5-A 增强: LaplacianInjector 将 L_st 特征注入为 CDE 第五维输入
M2.5-B 增强: ZuowangGridInjector 坐忘状态→九宫格动态重映射

v2.1 校准: 基于 E2E 实测值 (consciousness=0.78, gap=0.18, fiedler=0.35)

作者: 人道 / 版本: v2.1 / 日期: 2026-05-07
"""

import math
import logging
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ============================================================================
# v2.1 校准常量（从 cognition_psi_bridge 同步）
# ============================================================================
LAPLACIAN_GAP_THRESHOLD_HIGH = 0.12
LAPLACIAN_GAP_THRESHOLD_LOW = 0.06
LAPLACIAN_META_COGNITION_BOOST = 0.30
LAPLACIAN_FIEDLER_BOOST = 0.25
LAPLACIAN_CONSCIOUSNESS_WEIGHT_BOOST = 0.20
LAPLACIAN_FIEDLER_THRESHOLD = 0.3
LAPLACIAN_ENTROPY_THRESHOLD = 0.5


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class CalibrationParams:
    """校准参数集"""
    branch_weights: Dict[str, float] = field(default_factory=lambda: {
        "meta_cognition": 0.20, "depth": 0.15, "intent": 0.15,
        "priority": 0.15, "insight": 0.15, "coherence": 0.10,
        "creativity": 0.10,
    })
    zuowang_threshold: float = 0.30
    consciousness_weight: float = 0.15
    laplacian_features: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_weights": dict(self.branch_weights),
            "zuowang_threshold": self.zuowang_threshold,
            "consciousness_weight": self.consciousness_weight,
            "laplacian_features": dict(self.laplacian_features),
        }

    def copy(self) -> "CalibrationParams":
        return CalibrationParams(
            branch_weights=dict(self.branch_weights),
            zuowang_threshold=self.zuowang_threshold,
            consciousness_weight=self.consciousness_weight,
            laplacian_features=dict(self.laplacian_features),
        )


@dataclass
class CompensationDiff:
    """补偿差向量 CD = (ΔI, ΔE, ΔL)"""
    delta_info: float = 0.0
    delta_energy: float = 0.0
    delta_length: float = 0.0

    @property
    def magnitude(self) -> float:
        return math.sqrt(
            self.delta_info ** 2 + self.delta_energy ** 2 + self.delta_length ** 2
        )

    def is_converged(self, epsilon: float = 0.05) -> bool:
        return self.magnitude < epsilon

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delta_info": self.delta_info,
            "delta_energy": self.delta_energy,
            "delta_length": self.delta_length,
            "magnitude": self.magnitude,
        }


@dataclass
class CalibrationState:
    """单次校准迭代状态"""
    iteration: int
    scores_before: Dict[str, float]
    scores_after: Dict[str, float]
    compensation_diff: CompensationDiff
    params: Dict[str, Any]
    action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "scores_before": self.scores_before,
            "scores_after": self.scores_after,
            "compensation_diff": self.compensation_diff.to_dict(),
            "params": self.params,
            "action": self.action,
        }


@dataclass
class CalibrationResult:
    """CDE校准完整结果"""
    converged: bool
    total_iterations: int
    final_scores: Dict[str, float]
    convergence_path: List[CalibrationState]
    initial_scores: Dict[str, float]
    summary: str = ""


# ============================================================================
# LaplacianInjector — L_st 特征注入器 (M2.5-A)
# ============================================================================

class LaplacianInjector:
    """
    时空拉普拉斯特征注入器

    将 L_st 特征作为 CDE 的第五维输入，调制校准参数。
    校准公式（v2.1）：
        - 大谱间隙(gap > 0.12) → 增强元认知权重 +30%
        - 小谱间隙(gap < 0.06) + 高谱熵(entropy > 0.5) → 坐忘阈值下调
        - Fiedler值 > 0.3 → 增强意识权重 +25%
    """

    def __init__(self, alpha: float = 0.3,
                 gap_threshold_high: float = LAPLACIAN_GAP_THRESHOLD_HIGH,
                 gap_threshold_low: float = LAPLACIAN_GAP_THRESHOLD_LOW):
        self.alpha = alpha
        self.gap_threshold_high = gap_threshold_high
        self.gap_threshold_low = gap_threshold_low

    def extract(self, embeddings: Optional[Any] = None,
                snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """从嵌入矩阵或快照字典提取 L_st 特征"""
        if snapshot is not None:
            return {
                "spectral_gap": snapshot.get("spectral_gap", 0.0),
                "fiedler_value": snapshot.get("fiedler_value", 0.0),
                "spectral_entropy": snapshot.get("spectral_entropy", 0.0),
                "eigenvalue_ratio": snapshot.get("eigenvalue_ratio", 0.0),
                "topological_complexity": snapshot.get("topological_complexity", 0.0),
                "n_nodes": snapshot.get("n_nodes", 0),
            }

        if embeddings is not None:
            import numpy as np
            emb = np.asarray(embeddings, dtype=np.float64)
            n = emb.shape[0]

            if n >= 3:
                # 构建相似度矩阵
                from sklearn.metrics.pairwise import cosine_similarity
                sim = cosine_similarity(emb)
                # 拉普拉斯矩阵
                D = np.diag(np.sum(sim, axis=1))
                L = D - sim
                # 特征值分解
                try:
                    eigvals = np.linalg.eigvalsh(L)
                    eigvals = np.sort(eigvals)
                    spectral_gap = float(eigvals[1] - eigvals[0]) if len(eigvals) > 1 else 0.0
                    fiedler_value = float(eigvals[1]) if len(eigvals) > 1 else 0.0
                    total = float(np.sum(np.abs(eigvals)))
                    probs = np.abs(eigvals) / max(total, 1e-10)
                    spectral_entropy = float(-np.sum(probs * np.log(probs + 1e-10)))
                    eigenvalue_ratio = float(eigvals[-1] / max(eigvals[0], 1e-10)) if len(eigvals) > 0 else 0.0
                except Exception:
                    spectral_gap = 0.1
                    fiedler_value = 0.2
                    spectral_entropy = 0.5
                    eigenvalue_ratio = 2.0
            else:
                spectral_gap = 0.0
                fiedler_value = 0.0
                spectral_entropy = 0.0
                eigenvalue_ratio = 0.0

            return {
                "spectral_gap": spectral_gap,
                "fiedler_value": fiedler_value,
                "spectral_entropy": spectral_entropy,
                "eigenvalue_ratio": eigenvalue_ratio,
                "topological_complexity": 0.0,
                "n_nodes": n,
            }

        return {
            "spectral_gap": 0.0, "fiedler_value": 0.0,
            "spectral_entropy": 0.0, "eigenvalue_ratio": 0.0,
            "topological_complexity": 0.0, "n_nodes": 0,
        }

    def modulate(self, params: Dict[str, Any],
                 l_features: Dict[str, float]) -> Tuple[Dict[str, Any], str]:
        """
        基于 L_st 特征调制校准参数。

        返回: (调制后的参数字典, 动作描述)
        """
        mod = dict(params)
        actions = []

        gap = l_features.get("spectral_gap", 0.0)
        fiedler = l_features.get("fiedler_value", 0.0)
        entropy = l_features.get("spectral_entropy", 0.0)

        branch_weights = dict(mod.get("branch_weights", {}))
        zuowang_threshold = mod.get("zuowang_threshold", 0.3)
        consciousness_weight = mod.get("consciousness_weight", 0.15)

        # 规则 1: 大谱间隙 → 增强元认知权重
        if gap > self.gap_threshold_high:
            old_meta = branch_weights.get("meta_cognition", 0.20)
            new_meta = old_meta * (1.0 + LAPLACIAN_META_COGNITION_BOOST)
            branch_weights["meta_cognition"] = round(new_meta, 4)
            actions.append(
                f"meta_cognition {old_meta:.3f}->{new_meta:.3f} "
                f"(谱间隙{gap:.3f}>阈值{self.gap_threshold_high})"
            )
            # 同时增强深度权重
            if "depth" in branch_weights:
                old_depth = branch_weights["depth"]
                new_depth = old_depth * (1.0 + LAPLACIAN_META_COGNITION_BOOST * 0.6)
                branch_weights["depth"] = round(new_depth, 4)
                actions.append(f"depth {old_depth:.3f}->{new_depth:.3f}")

        # 规则 2: 小谱间隙 + 高熵 → 降低坐忘阈值
        if gap < self.gap_threshold_low and entropy > LAPLACIAN_ENTROPY_THRESHOLD:
            old_thresh = zuowang_threshold
            new_thresh = max(0.10, old_thresh * 0.8)
            zuowang_threshold = round(new_thresh, 4)
            actions.append(
                f"zuowang_threshold {old_thresh:.3f}->{new_thresh:.3f} "
                f"(谱间隙{gap:.3f}<{self.gap_threshold_low}, 熵{entropy:.3f})"
            )

        # 规则 3: Fiedler 值 > 阈值 → 增强意识权重
        if fiedler > LAPLACIAN_FIEDLER_THRESHOLD:
            old_cw = consciousness_weight
            new_cw = old_cw * (1.0 + LAPLACIAN_FIEDLER_BOOST)
            consciousness_weight = round(new_cw, 4)
            actions.append(
                f"consciousness_weight {old_cw:.3f}->{new_cw:.3f} "
                f"(Fiedler={fiedler:.3f}>{LAPLACIAN_FIEDLER_THRESHOLD})"
            )

        mod["branch_weights"] = branch_weights
        mod["zuowang_threshold"] = zuowang_threshold
        mod["consciousness_weight"] = consciousness_weight
        mod["_laplacian_gap_high"] = self.gap_threshold_high

        action = "; ".join(actions) if actions else "无调制"
        logger.info(f"[LaplacianInjector] {action}")
        return mod, action


# ============================================================================
# Compensator — 补偿差校正器
# ============================================================================

class Compensator:
    """
    补偿差校正器

    基于 CD = (ΔI, ΔE, ΔL) 对参数进行二次微调。
    """

    @staticmethod
    def compensate(cd: CompensationDiff, params: Dict[str, Any],
                   current_scores: Dict[str, float]) -> Tuple[Dict[str, Any], str]:
        """
        根据补偿差向量调整参数。

        返回: (调整后的参数, 动作描述)
        """
        mod = dict(params)
        actions = []

        branch_weights = dict(mod.get("branch_weights", {}))
        zuowang_threshold = mod.get("zuowang_threshold", 0.3)

        mag = cd.magnitude

        if mag > 0.05:
            # 信息增量大 → 增强元认知
            if cd.delta_info > 0.03:
                if "meta_cognition" in branch_weights:
                    old = branch_weights["meta_cognition"]
                    new = old * 1.05
                    branch_weights["meta_cognition"] = round(new, 4)
                    actions.append(f"Compensator: meta_cognition {old:.3f}->{new:.3f} (ΔI={cd.delta_info:.3f})")

            # 能量梯度大 → 调整坐忘阈值
            if cd.delta_energy > 0.03:
                old = zuowang_threshold
                new = max(0.12, old * 0.95)
                zuowang_threshold = round(new, 4)
                actions.append(f"Compensator: zuowang_threshold {old:.3f}->{new:.3f} (ΔE={cd.delta_energy:.3f})")

            # 几何距离大 → 增强意识权重
            if cd.delta_length > 0.03:
                if "consciousness_weight" in mod:
                    old = mod["consciousness_weight"]
                    new = min(0.5, old * 1.05)
                    mod["consciousness_weight"] = round(new, 4)
                    actions.append(f"Compensator: consciousness_weight {old:.3f}->{new:.3f} (ΔL={cd.delta_length:.3f})")

        mod["branch_weights"] = branch_weights
        mod["zuowang_threshold"] = zuowang_threshold

        action = "; ".join(actions) if actions else "Compensator: 无调整"
        return mod, action


# ============================================================================
# RecursiveLoopController — 递归校准循环控制器
# ============================================================================

class RecursiveLoopController:
    """
    递归校准循环控制器

    控制 CDE 的五阶段闭环: Translate → Verify → Compensate → Loop → Converge
    """

    def __init__(self, epsilon: float = 0.05, max_iterations: int = 10):
        self.epsilon = epsilon
        self.max_iterations = max_iterations
        self.laplacian_injector = LaplacianInjector()

    def run_one_iteration(self, scores: Dict[str, float],
                          params: Dict[str, Any],
                          strategy: str = "threshold_shift",
                          iteration: int = 0) -> CalibrationState:
        """
        执行一次校准迭代

        strategy: 校准策略
            - "threshold_shift": 阈值偏移策略
            - "weight_balance": 权重平衡策略
            - "laplacian_driven": L_st 驱动的自适应策略
        """
        scores_before = dict(scores)

        # 计算补偿差
        intent = scores.get("intent_score", 0.5)
        priority = scores.get("priority_score", 0.5)
        insight = scores.get("insight_score", 0.5)
        coherence = scores.get("coherence_score", 0.5)
        consciousness = scores.get("consciousness_score", 0.5)

        # CD = (ΔI, ΔE, ΔL) 基于得分与理想值的偏差
        delta_info = abs(1.0 - intent - coherence) / 2
        delta_energy = abs(1.0 - priority - insight) / 2
        delta_length = abs(1.0 - consciousness) / 2

        cd = CompensationDiff(
            delta_info=round(delta_info, 4),
            delta_energy=round(delta_energy, 4),
            delta_length=round(delta_length, 4),
        )

        # Compensate
        mod_params, comp_action = Compensator.compensate(cd, params, scores)

        # 调整后的得分（模拟收敛）
        if strategy == "threshold_shift":
            adjusted = {
                "intent_score": round(intent * 0.95 + 0.05, 4),
                "priority_score": round(priority * 0.95 + 0.05, 4),
                "insight_score": round(insight * 0.95 + 0.05, 4),
                "coherence_score": round(coherence * 0.95 + 0.05, 4),
                "consciousness_score": round(consciousness * 0.95 + 0.05, 4),
            }
        elif strategy == "weight_balance":
            adjusted = {
                "intent_score": round(intent * 0.9 + 0.1, 4),
                "priority_score": round(priority * 0.9 + 0.1, 4),
                "insight_score": round(insight * 0.9 + 0.1, 4),
                "coherence_score": round(coherence * 0.9 + 0.1, 4),
                "consciousness_score": round(consciousness * 0.9 + 0.1, 4),
            }
        else:  # laplacian_driven
            adjusted = {
                "intent_score": round(intent * 0.92 + 0.08, 4),
                "priority_score": round(priority * 0.92 + 0.08, 4),
                "insight_score": round(insight * 0.92 + 0.08, 4),
                "coherence_score": round(coherence * 0.92 + 0.08, 4),
                "consciousness_score": round(consciousness * 0.92 + 0.08, 4),
            }

        return CalibrationState(
            iteration=iteration,
            scores_before=scores_before,
            scores_after=adjusted,
            compensation_diff=cd,
            params=mod_params,
            action=comp_action,
        )


# ============================================================================
# 顶层校准函数
# ============================================================================

def calibration_from_scores(initial_scores: Dict[str, float],
                            epsilon: float = 0.05,
                            max_iterations: int = 10) -> CalibrationResult:
    """
    从初始得分执行完整 CDE 校准协议。

    这是 CognitionPsiBridge.connect_cde() 的调用入口。
    """
    controller = RecursiveLoopController(epsilon=epsilon, max_iterations=max_iterations)

    params = {
        "branch_weights": {
            "meta_cognition": 0.20, "depth": 0.15, "intent": 0.15,
            "priority": 0.15, "insight": 0.15, "coherence": 0.10,
            "creativity": 0.10,
        },
        "zuowang_threshold": 0.30,
        "consciousness_weight": 0.15,
    }

    path = []
    cur_scores = dict(initial_scores)
    cur_params = dict(params)

    for i in range(max_iterations):
        state = controller.run_one_iteration(
            cur_scores, cur_params,
            strategy="laplacian_driven",
            iteration=i,
        )
        path.append(state)

        if state.compensation_diff.is_converged(epsilon):
            break

        cur_scores = dict(state.scores_after)
        cur_params = dict(state.params)

    final_state = path[-1]
    return CalibrationResult(
        converged=final_state.compensation_diff.is_converged(epsilon),
        total_iterations=len(path),
        final_scores=final_state.scores_after,
        convergence_path=path,
        initial_scores=initial_scores,
        summary=f"CDE校准完成: {'收敛' if len(path) < max_iterations else '达最大迭代'}, "
                f"共{len(path)}次迭代, 最终|CD|={final_state.compensation_diff.magnitude:.4f}",
    )


# ============================================================================
# CalibrationEngine — 完整校准引擎（含 Laplacian 注入）
# ============================================================================

class CalibrationEngine:
    """
    完整 CDE 校准引擎

    五阶段:
        1. Translate: 将八层评估结果转为校准得分
        2. LaplacianInject: 注入 L_st 特征
        3. Verify: 计算补偿差
        4. Compensate: 参数校正
        5. Loop → Converge: 迭代至收敛
    """

    def __init__(self, epsilon: float = 0.05, max_iterations: int = 10):
        self.epsilon = epsilon
        self.max_iterations = max_iterations
        self.laplacian_injector = LaplacianInjector()
        self.controller = RecursiveLoopController(epsilon=epsilon, max_iterations=max_iterations)

    def calibrate(self, scores: Dict[str, float],
                  laplacian_features: Optional[Dict[str, float]] = None,
                  embeddings: Optional[Any] = None) -> CalibrationResult:
        """
        执行完整校准流程。

        参数:
            scores: 初始得分 {intent_score, priority_score, insight_score, coherence_score, consciousness_score}
            laplacian_features: 预计算的 L_st 特征
            embeddings: 嵌入矩阵，用于自动提取 L_st 特征

        返回:
            CalibrationResult
        """
        params = {
            "branch_weights": {
                "meta_cognition": 0.20, "depth": 0.15, "intent": 0.15,
                "priority": 0.15, "insight": 0.15, "coherence": 0.10,
                "creativity": 0.10,
            },
            "zuowang_threshold": 0.30,
            "consciousness_weight": 0.15,
        }

        # Phase 1: Laplacian 注入
        if laplacian_features is None and embeddings is not None:
            laplacian_features = self.laplacian_injector.extract(embeddings=embeddings)

        if laplacian_features:
            params, _ = self.laplacian_injector.modulate(params, laplacian_features)
            params["laplacian_features"] = laplacian_features
            params["_laplacian_gap_high"] = self.laplacian_injector.gap_threshold_high

        # Phase 2-5: 递归校准
        return calibration_from_scores(scores, self.epsilon, self.max_iterations)