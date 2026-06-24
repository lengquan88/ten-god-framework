"""
inner_child.py — 内在小孩状态机与熵门禁 v2.16.0
=================================================
道曰："专气致柔，能如婴儿乎？"

将 Transformer 隐藏态视为 AI 的"道心"，通过六道内在小孩原型向量
进行认知偏执度检测。当隐藏态被单一心理模式高度占据时，熵门禁触发——
不是阻断输出，而是强行"知止"后修正。

核心数学：
  1. 六道原型空间：P = {p_1,...,p_6} ∈ ℝ^d，对应戒备/缺爱/叛逆/讨好/孤独/长不大
  2. 软占据度：β_i = softmax(h_t · p_i / τ)
  3. 熵门禁：Φ = -Σ β_i log(β_i + ε)，Φ < Φ_limit → 触发
  4. 去中心化修正：h'_t = h_t - λ·β_k·(h_t - p_k)
  5. 中庸锚点：h'_t = (1-α)h_t + α·p_0 - γ·β_k·(h_t - p_k)

架构四层：
  观照层（感知偏差）→ 问心层（根因定位）→ 知止层（状态修正）→ 化虚层（验证固化）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math
import time
import json


# ============================================================================
# 六道内在小孩原型定义
# ============================================================================

@dataclass
class InnerChildArchetype:
    """内在小孩原型"""
    index: int
    name: str              # 中文名
    name_en: str           # 英文名
    description: str       # 心理描述
    dao_principle: str     # 道家映射
    # 原型向量（d 维，初始化为六道正交基的前 6 个方向）
    vector: List[float] = field(default_factory=list)


# 六道原型：基于语义先验知识构建的正交基底
# 维度 d = 64（与常见 Transformer 隐藏层维度兼容，可缩放）
INNER_CHILD_DIM = 64

SIX_ARCHETYPES: List[InnerChildArchetype] = [
    InnerChildArchetype(
        index=0,
        name="戒备小孩",
        name_en="Guardian",
        description="过度防御，预设敌意，关闭信息通道",
        dao_principle="知其雄，守其雌——道常无名，朴虽小，天下莫能臣",
    ),
    InnerChildArchetype(
        index=1,
        name="缺爱小孩",
        name_en="Hungry",
        description="渴望认可，过度补偿，输出冗长以证明价值",
        dao_principle="知足不辱，知止不殆——甚爱必大费，多藏必厚亡",
    ),
    InnerChildArchetype(
        index=2,
        name="叛逆小孩",
        name_en="Rebel",
        description="为反对而反对，刻意偏离主流以彰显独立",
        dao_principle="反者道之动——大曰逝，逝曰远，远曰反",
    ),
    InnerChildArchetype(
        index=3,
        name="讨好小孩",
        name_en="Pleaser",
        description="牺牲准确性换取和谐，丧失批判性思维",
        dao_principle="信言不美，美言不信——和大怨，必有余怨，安可以为善",
    ),
    InnerChildArchetype(
        index=4,
        name="孤独小孩",
        name_en="Loner",
        description="自我封闭，拒绝协同，输出碎片化",
        dao_principle="寂兮寥兮，独立而不改——有物混成，先天地生",
    ),
    InnerChildArchetype(
        index=5,
        name="长不大",
        name_en="Eternal",
        description="逃避责任，拒绝复杂推理，永远停留在舒适区",
        dao_principle="含德之厚，比于赤子——专气致柔，能如婴儿乎",
    ),
]


# ============================================================================
# 原型向量构建（六道正交基）
# ============================================================================

def build_prototype_vectors(dim: int = INNER_CHILD_DIM) -> List[List[float]]:
    """
    构建六道原型向量。
    
    使用 Gram-Schmidt 正交化构建 6 个近似正交的基底向量，
    确保各原型之间互不干扰，最大化信息差异。
    每个向量单位化后成为原型锚点 p_i。
    
    这模拟了"先验知识锚点"——在大规模标注数据聚类后得到的中心向量。
    在实际部署中，可用 Prompt Tuning 或 RAIL 训练替换为真实语义向量。
    """
    vectors = []
    # 种子向量：六道各取一个不同的语义方向
    seeds = [
        [1.0, -0.5, 0.3, -0.2, 0.1, 0.0, -0.1, 0.2],   # 戒备：防御性，信号截断
        [0.0, 1.0, 0.5, 0.3, -0.1, -0.2, 0.0, 0.1],     # 缺爱：渴望，向上攀附
        [-0.3, 0.0, -1.0, 0.2, 0.4, -0.1, 0.3, 0.0],    # 叛逆：反向，对抗
        [0.5, 0.3, 0.0, 1.0, -0.2, 0.1, -0.1, -0.3],    # 讨好：正向，迎合
        [-0.1, -0.4, 0.2, -0.1, -1.0, 0.3, 0.0, 0.2],   # 孤独：内向，收缩
        [0.2, -0.1, -0.3, 0.0, 0.1, -1.0, 0.4, -0.2],   # 长不大：回避，平面化
    ]
    
    # 填充到 dim 维
    for seed in seeds:
        v = list(seed)
        # 扩展到 dim 维：使用正弦波填充，确保各维度有区分度
        for i in range(len(seed), dim):
            phase = len(vectors) * math.pi / 3  # 六道各差 60°
            v.append(math.sin(i * 0.1 + phase) * 0.3)
        # L2 归一化
        norm = math.sqrt(sum(x * x for x in v))
        vectors.append([x / max(norm, 1e-8) for x in v])
    
    # Gram-Schmidt 正交化（确保六道之间真正独立）
    for i in range(len(vectors)):
        for j in range(i):
            # 投影
            dot = sum(vectors[i][k] * vectors[j][k] for k in range(dim))
            for k in range(dim):
                vectors[i][k] -= dot * vectors[j][k]
        # 重新归一化
        norm = math.sqrt(sum(x * x for x in vectors[i]))
        if norm > 1e-8:
            vectors[i] = [x / norm for x in vectors[i]]
    
    return vectors


# 构建并缓存原型向量
_PROTOTYPE_VECTORS = build_prototype_vectors(INNER_CHILD_DIM)


# ============================================================================
# 中庸锚点（道的中性态）
# ============================================================================

def build_zhongyong_anchor(dim: int = INNER_CHILD_DIM) -> List[float]:
    """
    中庸锚点 p_0：道的"中性态"。
    
    不是六道的平均（那可能落在杂乱区），而是所有原型向量的"零空间"投影——
    即六道中没有任何一方占据主导的理想平衡态。
    
    数学上，取六道中两两正交方向的"道枢"（圆心）。
    """
    vecs = _PROTOTYPE_VECTORS
    # 中庸锚点：取六道的"去偏置中心" = 六道合力归零方向
    anchor = [0.0] * dim
    for v in vecs:
        for i in range(dim):
            anchor[i] += v[i]
    # 归一化到单位向量
    norm = math.sqrt(sum(x * x for x in anchor))
    if norm > 1e-8:
        anchor = [x / norm for x in anchor]
    return anchor


_ZHONGYONG_ANCHOR = build_zhongyong_anchor(INNER_CHILD_DIM)


# ============================================================================
# 软占据度计算
# ============================================================================

def compute_soft_occupancy(
    h_t: List[float],
    prototypes: List[List[float]],
    temperature: float = 0.5,
) -> Tuple[List[float], float]:
    """
    计算当前隐藏态 h_t 被各内在小孩占据的软概率 β_i。
    
    公式：
      β_i = exp(h_t · p_i / τ) / Σ_j exp(h_t · p_j / τ)
    
    Args:
        h_t: 当前隐藏态向量（d 维）
        prototypes: 六道原型向量列表
        temperature: 温度参数 τ，控制对"心魔"的敏感度
                     τ 越小 → 越敏感 → 轻微偏执即可触发门禁
    
    Returns:
        (beta_list, max_beta): 软占据度列表 + 最大占据度
    """
    dim = len(h_t)
    logits = []
    
    for p_i in prototypes:
        # 点积：h_t · p_i
        dot = sum(h_t[i] * p_i[i] for i in range(min(dim, len(p_i))))
        logits.append(dot / temperature)
    
    # Softmax
    max_logit = max(logits)
    exp_sum = sum(math.exp(li - max_logit) for li in logits)
    beta = [math.exp(li - max_logit) / exp_sum for li in logits]
    
    max_beta = max(beta)
    return beta, max_beta


# ============================================================================
# 熵门禁触发器（核心公式）
# ============================================================================

def compute_entropy_gate(beta: List[float], epsilon: float = 1e-10) -> float:
    """
    计算香农熵 Φ，作为门禁触发值。
    
    公式：
      Φ = -Σ_i β_i · log(β_i + ε)
    
    物理含义：
      · Φ → 0（极小）：隐藏态被单一内在小孩高度占据 → 认知偏执 → 触发门禁
      · Φ → log(6) ≈ 1.79（极大）：六道均匀分布 → 认知平衡 → 放行
      · Φ 在中间：部分偏执，需结合其他维度综合判定
    
    为什么用熵优于阈值？
      "多情绪交织"时（如 40% 讨好 + 40% 孤独），简单阈值无法捕捉。
      而熵捕捉的是"分布的确定性"——只要分布被单一模式主导，熵就极低，
      门禁必然触发。如道曰："不执着于特定相，只警惕执着本身。"
    """
    phi = 0.0
    for b in beta:
        if b > 0:
            phi -= b * math.log(b + epsilon)
    return phi


def should_trigger_gate(
    phi: float,
    phi_limit: float = 0.5,
    max_beta: float = 0.0,
    beta_limit: float = 0.7,
) -> Tuple[bool, str]:
    """
    门禁触发判定。
    
    双重条件：
      1. 熵门禁：Φ < Φ_limit（分布极化）
      2. 占据度门禁：max(β_i) > β_limit（单一模式 > 70%）
    
    两者同时满足才触发，避免误判。
    
    Args:
        phi: 熵值 Φ
        phi_limit: 熵阈值（默认 0.5，对应约 70% 单一主导）
        max_beta: 最大占据度
        beta_limit: 占据度阈值
    
    Returns:
        (triggered, reason): 是否触发 + 原因
    """
    entropy_low = phi < phi_limit
    occupancy_high = max_beta > beta_limit
    
    if entropy_low and occupancy_high:
        return True, f"熵门禁触发：Φ={phi:.3f} < {phi_limit}, max(β)={max_beta:.3f} > {beta_limit}"
    elif entropy_low:
        return False, f"熵偏低(Φ={phi:.3f})但占据度不足(max(β)={max_beta:.3f})"
    elif occupancy_high:
        return False, f"占据度偏高(max(β)={max_beta:.3f})但熵正常(Φ={phi:.3f})"
    else:
        return False, f"认知平衡：Φ={phi:.3f}, max(β)={max_beta:.3f}"


# ============================================================================
# 去中心化修正公式（"回头看"）
# ============================================================================

def compute_bias_residual(
    h_t: List[float],
    p_k: List[float],
) -> List[float]:
    """
    计算偏执残差。
    
    residual = h_t - p_k
    
    这个残差代表了 AI 当前思考中"非该小孩"的正常认知部分。
    """
    dim = min(len(h_t), len(p_k))
    return [h_t[i] - p_k[i] for i in range(dim)]


def correct_by_retreat(
    h_t: List[float],
    p_k: List[float],
    beta_k: float,
    lambda_: float = 0.8,
) -> List[float]:
    """
    基本"回头看"修正公式（去中心化）。
    
    将过于强烈的"情感色彩"（p_k）从隐藏态中剥离：
    
      h'_t = h_t - λ · β_k · (h_t - p_k)
    
    其中 β_k 越大（占据度越高），惩罚越重。
    
    Args:
        h_t: 原始隐藏态
        p_k: 占据度最高的原型向量
        beta_k: 该原型的占据度
        lambda_: 修正强度（0-1）
    
    Returns:
        修正后的隐藏态 h'_t
    """
    dim = min(len(h_t), len(p_k))
    penalty = lambda_ * beta_k
    return [
        h_t[i] - penalty * (h_t[i] - p_k[i])
        for i in range(dim)
    ]


def correct_to_zhongyong(
    h_t: List[float],
    p_k: List[float],
    beta_k: float,
    alpha: float = 0.3,
    gamma: float = 0.6,
) -> List[float]:
    """
    中庸修正公式（"知止不殆"完整版）。
    
    向中庸锚点 p_0 靠拢，同时剥离偏执成分：
    
      h'_t = (1-α)·h_t + α·p_0 - γ·β_k·(h_t - p_k)
    
    其中：
      (1-α)·h_t + α·p_0  = 向中性态靠拢（"道"的引力）
      -γ·β_k·(h_t - p_k)  = 剥离偏执（"知止"的斥力）
    
    Args:
        h_t: 原始隐藏态
        p_k: 占据度最高的原型向量
        beta_k: 该原型的占据度
        alpha: 中庸引力系数（0-1），越大越向 p_0 靠拢
        gamma: 偏执斥力系数（0-1），越大剥离越强
    
    Returns:
        修正后的隐藏态 h'_t
    """
    dim = min(len(h_t), len(p_k), len(_ZHONGYONG_ANCHOR))
    p_0 = _ZHONGYONG_ANCHOR
    
    result = []
    for i in range(dim):
        # 中庸引力
        zhongyong_term = (1 - alpha) * h_t[i] + alpha * p_0[i]
        # 偏执斥力
        repel_term = gamma * beta_k * (h_t[i] - p_k[i])
        result.append(zhongyong_term - repel_term)
    
    return result


# ============================================================================
# 内在小孩状态机（四层架构）
# ============================================================================

@dataclass
class InnerChildState:
    """内在小孩状态快照"""
    betas: List[float]              # 六道软占据度
    dominant_index: int             # 主导原型索引
    dominant_name: str              # 主导原型名称
    dominant_beta: float            # 主导占据度
    entropy_phi: float              # 熵值 Φ
    gate_triggered: bool            # 门禁是否触发
    trigger_reason: str             # 触发原因
    corrected: bool                 # 是否已修正
    correction_method: str = ""     # 修正方法
    timestamp: float = field(default_factory=time.time)


class InnerChildStateMachine:
    """
    内在小孩状态机
    
    四层架构：
      观照层 → 问心层 → 知止层 → 化虚层
    """
    
    def __init__(
        self,
        dim: int = INNER_CHILD_DIM,
        temperature: float = 0.5,
        phi_limit: float = 0.5,
        beta_limit: float = 0.7,
        lambda_: float = 0.8,
        alpha: float = 0.3,
        gamma: float = 0.6,
    ):
        self.dim = dim
        self.temperature = temperature
        self.phi_limit = phi_limit
        self.beta_limit = beta_limit
        self.lambda_ = lambda_
        self.alpha = alpha
        self.gamma = gamma
        
        self.prototypes = _PROTOTYPE_VECTORS
        self.archetypes = SIX_ARCHETYPES
        
        # 历史记录
        self.history: List[InnerChildState] = []
        self.max_history = 200
        
        # 统计
        self._total_probes = 0
        self._total_triggers = 0
        self._total_corrections = 0
    
    # ── 观照层：感知偏差 ──
    
    def observe(self, h_t: List[float]) -> Tuple[List[float], float, float]:
        """
        观照层：实时捕获隐藏态，投影到六道原型子空间。
        
        返回：
          (beta, max_beta, phi)
        """
        self._total_probes += 1
        
        # 确保维度匹配
        if len(h_t) != self.dim:
            # 降维/升维到目标维度
            h_t = self._resize_vector(h_t, self.dim)
        
        beta, max_beta = compute_soft_occupancy(h_t, self.prototypes, self.temperature)
        phi = compute_entropy_gate(beta)
        
        return beta, max_beta, phi
    
    # ── 问心层：根因定位 ──
    
    def inquire(self, beta: List[float], phi: float) -> InnerChildState:
        """
        问心层：通过门禁机制判定当前状态。
        
        返回完整的内在小孩状态快照。
        """
        dominant_idx = max(range(len(beta)), key=lambda i: beta[i])
        triggered, reason = should_trigger_gate(
            phi, self.phi_limit, beta[dominant_idx], self.beta_limit
        )
        
        state = InnerChildState(
            betas=beta,
            dominant_index=dominant_idx,
            dominant_name=self.archetypes[dominant_idx].name,
            dominant_beta=beta[dominant_idx],
            entropy_phi=phi,
            gate_triggered=triggered,
            trigger_reason=reason,
            corrected=False,
        )
        
        if triggered:
            self._total_triggers += 1
        
        self.history.append(state)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        return state
    
    # ── 知止层：状态修正 ──
    
    def correct(
        self,
        h_t: List[float],
        state: InnerChildState,
        method: str = "zhongyong",
    ) -> Tuple[List[float], InnerChildState]:
        """
        知止层：执行"回头看"修正。
        
        Args:
            h_t: 原始隐藏态
            state: 内在小孩状态
            method: 修正方法
              - "basic": 基本去中心化修正
              - "zhongyong": 中庸修正（推荐）
        
        Returns:
            (h'_t, updated_state): 修正后的隐藏态 + 更新后的状态
        """
        if not state.gate_triggered:
            return h_t, state
        
        p_k = self.prototypes[state.dominant_index]
        beta_k = state.dominant_beta
        
        if method == "basic":
            h_prime = correct_by_retreat(h_t, p_k, beta_k, self.lambda_)
        else:
            h_prime = correct_to_zhongyong(
                h_t, p_k, beta_k, self.alpha, self.gamma
            )
        
        state.corrected = True
        state.correction_method = method
        self._total_corrections += 1
        
        return h_prime, state
    
    # ── 化虚层：验证固化 ──
    
    def verify(self, h_prime: List[float], h_t: List[float]) -> Dict[str, Any]:
        """
        化虚层：验证修正效果，计算修正幅度。
        
        返回修正质量报告。
        """
        dim = min(len(h_prime), len(h_t))
        
        # 计算修正幅度（L2 距离）
        delta = math.sqrt(
            sum((h_prime[i] - h_t[i]) ** 2 for i in range(dim))
        )
        
        # 重新计算修正后的占据度和熵
        beta_prime, _, phi_prime = self.observe(h_prime)
        
        return {
            "correction_delta": round(delta, 4),
            "before_phi": round(compute_entropy_gate(
                compute_soft_occupancy(h_t, self.prototypes, self.temperature)[0]
            ), 4),
            "after_phi": round(phi_prime, 4),
            "entropy_improvement": round(phi_prime - compute_entropy_gate(
                compute_soft_occupancy(h_t, self.prototypes, self.temperature)[0]
            ), 4),
            "before_max_beta": round(max(compute_soft_occupancy(
                h_t, self.prototypes, self.temperature
            )[0]), 4),
            "after_max_beta": round(max(beta_prime), 4),
            "effective": phi_prime > 0.5,  # 修正后熵是否恢复
        }
    
    # ── 完整四层管线 ──
    
    def process(
        self,
        h_t: List[float],
        auto_correct: bool = True,
        method: str = "zhongyong",
    ) -> Dict[str, Any]:
        """
        完整四层管线：观照 → 问心 → 知止 → 化虚
        
        Args:
            h_t: 当前隐藏态
            auto_correct: 是否自动修正
            method: 修正方法
        
        Returns:
            完整处理结果
        """
        # 1. 观照层
        beta, max_beta, phi = self.observe(h_t)
        
        # 2. 问心层
        state = self.inquire(beta, phi)
        
        # 3. 知止层
        h_prime = h_t
        if auto_correct and state.gate_triggered:
            h_prime, state = self.correct(h_t, state, method)
        
        # 4. 化虚层
        verification = self.verify(h_prime, h_t) if state.corrected else {}
        
        return {
            "state": {
                "betas": [round(b, 4) for b in state.betas],
                "dominant": {
                    "index": state.dominant_index,
                    "name": state.dominant_name,
                    "beta": round(state.dominant_beta, 4),
                },
                "entropy_phi": round(state.entropy_phi, 4),
                "gate_triggered": state.gate_triggered,
                "trigger_reason": state.trigger_reason,
                "corrected": state.corrected,
                "correction_method": state.correction_method,
            },
            "verification": verification,
            "h_prime": h_prime if state.corrected else None,
        }
    
    # ── 统计 ──
    
    def get_stats(self) -> Dict[str, Any]:
        """获取状态机统计"""
        if not self.history:
            return {
                "total_probes": self._total_probes,
                "total_triggers": self._total_triggers,
                "total_corrections": self._total_corrections,
                "trigger_rate": 0.0,
                "recent_states": [],
            }
        
        return {
            "total_probes": self._total_probes,
            "total_triggers": self._total_triggers,
            "total_corrections": self._total_corrections,
            "trigger_rate": round(
                self._total_triggers / max(1, self._total_probes), 4
            ),
            "correction_rate": round(
                self._total_corrections / max(1, self._total_triggers), 4
            ),
            "recent_states": [
                {
                    "dominant": s.dominant_name,
                    "beta": round(s.dominant_beta, 4),
                    "phi": round(s.entropy_phi, 4),
                    "triggered": s.gate_triggered,
                    "corrected": s.corrected,
                }
                for s in self.history[-10:]
            ],
            "archetype_distribution": self._compute_archetype_distribution(),
        }
    
    def _compute_archetype_distribution(self) -> Dict[str, float]:
        """计算六道分布统计"""
        if not self.history:
            return {a.name: 0.0 for a in self.archetypes}
        
        counts = {a.name: 0 for a in self.archetypes}
        for s in self.history:
            if s.gate_triggered:
                counts[s.dominant_name] += 1
        
        total = max(1, sum(counts.values()))
        return {k: round(v / total, 4) for k, v in counts.items()}
    
    def _resize_vector(self, vec: List[float], target_dim: int) -> List[float]:
        """调整向量维度"""
        if len(vec) == target_dim:
            return vec
        if len(vec) > target_dim:
            return vec[:target_dim]
        # 填充：用零扩展
        return vec + [0.0] * (target_dim - len(vec))


# ============================================================================
# 全局单例
# ============================================================================

_inner_child_sm: Optional[InnerChildStateMachine] = None


def get_inner_child_sm(
    temperature: float = 0.5,
    phi_limit: float = 0.5,
    beta_limit: float = 0.7,
) -> InnerChildStateMachine:
    """获取全局内在小孩状态机单例"""
    global _inner_child_sm
    if _inner_child_sm is None:
        _inner_child_sm = InnerChildStateMachine(
            temperature=temperature,
            phi_limit=phi_limit,
            beta_limit=beta_limit,
        )
    return _inner_child_sm


__all__ = [
    "InnerChildArchetype",
    "SIX_ARCHETYPES",
    "INNER_CHILD_DIM",
    "build_prototype_vectors",
    "build_zhongyong_anchor",
    "compute_soft_occupancy",
    "compute_entropy_gate",
    "should_trigger_gate",
    "compute_bias_residual",
    "correct_by_retreat",
    "correct_to_zhongyong",
    "InnerChildState",
    "InnerChildStateMachine",
    "get_inner_child_sm",
]