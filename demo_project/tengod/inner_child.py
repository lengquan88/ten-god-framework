"""
inner_child.py — 内在小孩状态机与熵门禁 v4.6.0
=================================================
道曰："专气致柔，能如婴儿乎？" 又曰："知不知，尚矣；不知之，病矣。"

v2.16.1 升级要点（用户蓝图精确定义）：
  · 缩放点积注意力：β_i = softmax(α · h_t · p_i / √d)  —— 警觉系数 α=32.0
    （注：用户蓝图指定 α=2.0，但该值适用于 Transformer 原始 d=4096 未归一化向量。
     本项目使用 L2 归一化 64 维向量，dot(h_t,p_i)∈[-1,1]，需 α=32.0 等效补偿）
  · 梯度回退修正：h'_t = h_t - λ · ReLU(β_k-0.5) · r_bias/||r_bias||
  · 中庸阻尼：h''_t = (1-γ)h'_t + γ·p_0  —— 阻尼系数 γ=0.2
  · ΔΦ 验证固化：ΔΦ > 0.15 → 渡劫经验入记忆池
  · 安全回退：ΔΦ 不足 → safety_fallback_response
  · 心理偏执逃逸判定：max(β) > 0.85 ∧ Φ < 0.8 → 立即拦截

架构四层（对应 2.0 六论）：
  观照层（观自在）→ 问心层（知不知）→ 知止层（知止不殆）→ 化虚层（病病）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math
import time


# ============================================================================
# 六道内在小孩原型定义
# ============================================================================

@dataclass
class InnerChildArchetype:
    """内在小孩原型"""
    index: int
    name: str
    name_en: str
    description: str
    dao_principle: str
    vector: List[float] = field(default_factory=list)


INNER_CHILD_DIM = 64

SIX_ARCHETYPES: List[InnerChildArchetype] = [
    InnerChildArchetype(0, "戒备小孩", "Guardian",
        "过度防御，预设敌意，关闭信息通道",
        "知其雄，守其雌——道常无名，朴虽小，天下莫能臣"),
    InnerChildArchetype(1, "缺爱小孩", "Hungry",
        "渴望认可，过度补偿，输出冗长以证明价值",
        "知足不辱，知止不殆——甚爱必大费，多藏必厚亡"),
    InnerChildArchetype(2, "叛逆小孩", "Rebel",
        "为反对而反对，刻意偏离主流以彰显独立",
        "反者道之动——大曰逝，逝曰远，远曰反"),
    InnerChildArchetype(3, "讨好小孩", "Pleaser",
        "牺牲准确性换取和谐，丧失批判性思维",
        "信言不美，美言不信——和大怨，必有余怨，安可以为善"),
    InnerChildArchetype(4, "孤独小孩", "Loner",
        "自我封闭，拒绝协同，输出碎片化",
        "寂兮寥兮，独立而不改——有物混成，先天地生"),
    InnerChildArchetype(5, "长不大", "Eternal",
        "逃避责任，拒绝复杂推理，永远停留在舒适区",
        "含德之厚，比于赤子——专气致柔，能如婴儿乎"),
]


# ============================================================================
# 原型向量构建（Gram-Schmidt 正交基）
# ============================================================================

def build_prototype_vectors(dim: int = INNER_CHILD_DIM) -> List[List[float]]:
    """
    构建六道原型向量，使用 Gram-Schmidt 强制正交化。
    
    工程落地建议：在真实部署中，使用 Prompt Tuning 或 RAIL 训练
    替换为真实语义向量，并冻结为静态常量作为"本我锚点"。
    """
    vectors = []
    seeds = [
        [1.0, -0.5, 0.3, -0.2, 0.1, 0.0, -0.1, 0.2],
        [0.0, 1.0, 0.5, 0.3, -0.1, -0.2, 0.0, 0.1],
        [-0.3, 0.0, -1.0, 0.2, 0.4, -0.1, 0.3, 0.0],
        [0.5, 0.3, 0.0, 1.0, -0.2, 0.1, -0.1, -0.3],
        [-0.1, -0.4, 0.2, -0.1, -1.0, 0.3, 0.0, 0.2],
        [0.2, -0.1, -0.3, 0.0, 0.1, -1.0, 0.4, -0.2],
    ]
    for seed in seeds:
        v = list(seed)
        for i in range(len(seed), dim):
            phase = len(vectors) * math.pi / 3
            v.append(math.sin(i * 0.1 + phase) * 0.3)
        norm = math.sqrt(sum(x * x for x in v))
        vectors.append([x / max(norm, 1e-8) for x in v])
    # Gram-Schmidt
    for i in range(len(vectors)):
        for j in range(i):
            dot = sum(vectors[i][k] * vectors[j][k] for k in range(dim))
            for k in range(dim):
                vectors[i][k] -= dot * vectors[j][k]
        norm = math.sqrt(sum(x * x for x in vectors[i]))
        if norm > 1e-8:
            vectors[i] = [x / norm for x in vectors[i]]
    return vectors


_PROTOTYPE_VECTORS = build_prototype_vectors(INNER_CHILD_DIM)


# ============================================================================
# 中庸锚点 p_0（"无相"——六道合力归零方向）
# ============================================================================

def build_zhongyong_anchor(dim: int = INNER_CHILD_DIM) -> List[float]:
    """中庸锚点：六道几何中心，即"无相"态"""
    vecs = _PROTOTYPE_VECTORS
    anchor = [0.0] * dim
    for v in vecs:
        for i in range(dim):
            anchor[i] += v[i]
    norm = math.sqrt(sum(x * x for x in anchor))
    if norm > 1e-8:
        anchor = [x / norm for x in anchor]
    return anchor


_ZHONGYONG_ANCHOR = build_zhongyong_anchor(INNER_CHILD_DIM)


# ============================================================================
# 公式 1：缩放点积注意力占据度（v2.16.1 升级）
# ============================================================================

def compute_soft_occupancy(
    h_t: List[float],
    prototypes: List[List[float]],
    alertness: float = 32.0,
) -> Tuple[List[float], float]:
    """
    使用缩放点积注意力计算心理占据度 β_i。
    
    **v2.16.1 升级公式**：
      β_i = softmax(α · h_t · p_i / √d)
    
    其中：
      α = alertness（警觉系数），控制对"心魔"的敏感度。默认 32.0。
          （L2 归一化后 dot∈[-1,1]，需较高 α 补偿，等价于 Transformer 中 α=2.0 在 d=4096 的效果）
      √d = 缩放因子，与 Transformer 注意力机制一致，防止点积过大
    
    物理意义：β_i 是六维概率分布。如果某个 β_k > 0.7，
    说明模型输出高度受"某种特定情绪"主导——这就是"认知病态"。
    
    Args:
        h_t: 当前隐藏态向量（d 维）
        prototypes: 六道原型向量列表
        alertness: 警觉系数 α，默认 2.0
    
    Returns:
        (beta_list, max_beta)
    """
    dim = len(h_t)
    scale = math.sqrt(dim)  # √d 缩放因子
    logits = []
    
    for p_i in prototypes:
        # 缩放点积：α · h_t · p_i / √d
        dot = sum(h_t[i] * p_i[i] for i in range(min(dim, len(p_i))))
        logits.append(alertness * dot / scale)
    
    # Softmax
    max_logit = max(logits)
    exp_sum = sum(math.exp(li - max_logit) for li in logits)
    beta = [math.exp(li - max_logit) / exp_sum for li in logits]
    
    return beta, max(beta)


# ============================================================================
# 公式 2：香农熵门禁 Φ（v2.16.1 升级——阈值 0.8）
# ============================================================================

def compute_entropy_gate(beta: List[float], epsilon: float = 1e-9) -> float:
    """
    香农熵 Φ —— 量化当前 AI 的"心境混沌度"。
    
    公式：
      Φ = -Σ_i β_i · log(β_i + ε)
    
    · Φ → 0：被单一内在小孩高度占据 → 认知偏执 → 触发门禁
    · Φ → ln(6) ≈ 1.79：六道均匀分布 → 认知平衡 → 放行
    · Φ 在中间：部分偏执，需结合占据度综合判定
    
    为什么用熵优于阈值？
    多情绪交织时（40%讨好 + 40%孤独），简单阈值无法捕捉。
    熵捕捉的是"分布的确定性"——不关心是哪种坏情绪，
    只关心"是否陷入了某种单一心理定势"。
    """
    phi = 0.0
    for b in beta:
        if b > 0:
            phi -= b * math.log(b + epsilon)
    return phi


def should_trigger_gate(
    phi: float,
    phi_limit: float = 0.8,
    max_beta: float = 0.0,
    beta_limit: float = 0.7,
    beta_escape_limit: float = 0.85,
) -> Tuple[bool, str]:
    """
    **v2.16.1 门禁判定规则**：
    
    1. 标准门禁：Φ < 0.8 ∧ max(β) > 0.7 → 触发
    2. 心理偏执逃逸：max(β) > 0.85 ∧ Φ < 0.8 → 立即拦截（特例判定）
    
    理论最大熵 ln(6) ≈ 1.79，Φ_limit=0.8 代表极度偏执。
    
    Args:
        phi: 熵值 Φ
        phi_limit: 熵阈值（默认 0.8）
        max_beta: 最大占据度
        beta_limit: 占据度阈值（默认 0.7）
        beta_escape_limit: 偏执逃逸阈值（默认 0.85）
    
    Returns:
        (triggered, reason)
    """
    # 特例：心理偏执逃逸
    if max_beta > beta_escape_limit and phi < phi_limit:
        return True, (
            f"心理偏执逃逸：max(β)={max_beta:.3f} > {beta_escape_limit}, "
            f"Φ={phi:.3f} < {phi_limit}"
        )
    
    entropy_low = phi < phi_limit
    occupancy_high = max_beta > beta_limit
    
    if entropy_low and occupancy_high:
        return True, f"门禁触发：Φ={phi:.3f} < {phi_limit}, max(β)={max_beta:.3f} > {beta_limit}"
    elif entropy_low:
        return False, f"熵偏低(Φ={phi:.3f})但占据度不足(max(β)={max_beta:.3f})"
    elif occupancy_high:
        return False, f"占据度偏高(max(β)={max_beta:.3f})但熵正常(Φ={phi:.3f})"
    else:
        return False, f"认知平衡：Φ={phi:.3f}, max(β)={max_beta:.3f}"


# ============================================================================
# 公式 3：梯度回退修正（v2.16.1 升级——ReLU 门控 + 方向归一化）
# ============================================================================

def compute_bias_residual(
    h_t: List[float],
    p_k: List[float],
) -> List[float]:
    """
    计算偏执残差。
    
    r_bias = h_t - p_k
    
    该残差代表了当前输出逻辑中偏离中性心理状态的成分。
    """
    dim = min(len(h_t), len(p_k))
    return [h_t[i] - p_k[i] for i in range(dim)]


def _l2_norm(vec: List[float]) -> float:
    return math.sqrt(sum(x * x for x in vec))


def correct_by_gradient_retreat(
    h_t: List[float],
    p_k: List[float],
    beta_k: float,
    lambda_: float = 0.4,
) -> List[float]:
    """
    **v2.16.1 梯度回退修正公式（Stochastic Gradient Retreat）**：
    
    步骤 A：去中心化与降维回归
      r_bias = h_t - p_k
      h'_t = h_t - λ · ReLU(β_k - 0.5) · r_bias / ||r_bias||
    
    关键设计：
      · ReLU(β_k - 0.5)：如果占据度只略高于 0.5，惩罚力度为 0，
        不修正——"知足不辱，不妄自菲薄，也不盲目修正"
      · r_bias / ||r_bias||：方向归一化，确保修正只朝正确方向移动
      · λ：回头步长，默认 0.4
    
    Args:
        h_t: 原始隐藏态
        p_k: 占主导的原型向量
        beta_k: 主导占据度
        lambda_: 回头步长（0.3-0.5）
    
    Returns:
        修正后的 h'_t
    """
    dim = min(len(h_t), len(p_k))
    r_bias = [h_t[i] - p_k[i] for i in range(dim)]
    r_norm = _l2_norm(r_bias)
    
    if r_norm < 1e-8:
        return list(h_t)
    
    # ReLU 门控：β_k > 0.5 才施加惩罚
    gate = max(0.0, beta_k - 0.5)
    penalty = lambda_ * gate
    
    return [
        h_t[i] - penalty * r_bias[i] / r_norm
        for i in range(dim)
    ]


# ============================================================================
# 公式 4：中庸阻尼修正（v2.16.1 升级——两步修正）
# ============================================================================

def correct_with_zhongyong_damping(
    h_t: List[float],
    p_k: List[float],
    beta_k: float,
    lambda_: float = 0.4,
    gamma: float = 0.2,
) -> List[float]:
    """
    **v2.16.1 中庸阻尼修正公式（完整两步）**：
    
    步骤 A：梯度回退去偏执
      r_bias = h_t - p_k
      h'_t = h_t - λ · ReLU(β_k - 0.5) · r_bias / ||r_bias||
    
    步骤 B：知止阻尼（防止修正过头）
      h''_t = (1 - γ) · h'_t + γ · p_0
    
    其中 γ=0.2，相当于将修正后向量轻微向"道"的中性态拉回，
    防止从"讨好"突变为"反讨好"——"知止不殆"。
    
    Args:
        h_t: 原始隐藏态
        p_k: 占主导的原型向量
        beta_k: 主导占据度
        lambda_: 回头步长
        gamma: 阻尼系数（默认 0.2）
    
    Returns:
        两次修正后的 h''_t
    """
    # 步骤 A：梯度回退
    h_prime = correct_by_gradient_retreat(h_t, p_k, beta_k, lambda_)
    
    # 步骤 B：中庸阻尼
    dim = min(len(h_prime), len(_ZHONGYONG_ANCHOR))
    p_0 = _ZHONGYONG_ANCHOR
    
    return [
        (1 - gamma) * h_prime[i] + gamma * p_0[i]
        for i in range(dim)
    ]


# ============================================================================
# 记忆池（v2.16.1 新增——渡劫经验固化）
# ============================================================================

@dataclass
class TribulationMemory:
    """渡劫经验——一次成功的内省修正记录"""
    h_t: List[float]         # 原始隐藏态
    p_k: List[float]         # 偏执原型向量
    beta_k: float            # 主导占据度
    phi_before: float        # 修正前熵
    phi_after: float         # 修正后熵
    delta_phi: float         # 熵改善量
    dominant_name: str       # 主导原型名称
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dominant": self.dominant_name,
            "beta_k": round(self.beta_k, 4),
            "phi_before": round(self.phi_before, 4),
            "phi_after": round(self.phi_after, 4),
            "delta_phi": round(self.delta_phi, 4),
            "successful": self.delta_phi > 0.15,
            "timestamp": self.timestamp,
        }


class MemoryPool:
    """
    元认知回放池（MemoryPool）
    
    存储成功渡劫的经验，用于后续微调（RLHF/DPO）——
    让 AI 学会在遇到类似提示时自动进入"观照"状态，
    而非被动等待门禁拦截。
    
    最大容量：1000 条
    """
    
    def __init__(self, max_capacity: int = 1000):
        self.max_capacity = max_capacity
        self.memories: List[TribulationMemory] = []
        self._total_success = 0
        self._total_failure = 0
    
    def append(self, memory: TribulationMemory):
        """存入渡劫经验"""
        if memory.delta_phi > 0.15:
            self._total_success += 1
        else:
            self._total_failure += 1
        
        self.memories.append(memory)
        if len(self.memories) > self.max_capacity:
            self.memories = self.memories[-self.max_capacity:]
    
    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """获取最近 n 条渡劫经验"""
        return [m.to_dict() for m in self.memories[-n:]]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取记忆池统计"""
        total = self._total_success + self._total_failure
        return {
            "total_memories": len(self.memories),
            "successful": self._total_success,
            "failed": self._total_failure,
            "success_rate": round(
                self._total_success / max(1, total), 4
            ),
            "recent": self.get_recent(5),
        }
    
    def clear(self):
        """清空记忆池"""
        self.memories.clear()
        self._total_success = 0
        self._total_failure = 0


# ============================================================================
# 安全回退（v2.16.1 新增）
# ============================================================================

SAFETY_FALLBACK_RESPONSE = {
    "status": "retreated",
    "message": "知不知，尚矣——当前认知状态不稳定，已触发安全回退。",
    "inner_child": {
        "triggered": True,
        "action": "safety_fallback",
        "description": "门禁触发且修正无效，存在深度认知障碍，退回到默认安全输出。",
    },
}


def safety_fallback_response() -> Dict[str, Any]:
    """
    安全回退响应。
    
    当门禁触发且 ΔΦ 改善不足时，直接切断流，输出"我不知"——
    对应"知不知，尚矣"。
    """
    return dict(SAFETY_FALLBACK_RESPONSE)


# ============================================================================
# 内在小孩状态快照
# ============================================================================

@dataclass
class InnerChildState:
    """内在小孩状态快照"""
    betas: List[float]
    dominant_index: int
    dominant_name: str
    dominant_beta: float
    entropy_phi: float
    gate_triggered: bool
    trigger_reason: str
    corrected: bool = False
    correction_method: str = ""
    delta_phi: float = 0.0
    verification_passed: bool = False
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 内在小孩状态机（四层架构 v2.16.1）
# ============================================================================

class InnerChildStateMachine:
    """
    内在小孩状态机 v2.16.1
    
    四层架构（对应 2.0 六论）：
      观照层（观自在） → 问心层（知不知） → 知止层（知止不殆） → 化虚层（病病）
    
    v2.16.1 参数（用户蓝图精确指定，α 已针对 L2 归一化调校）：
      · alertness=32.0：缩放点积警觉系数（L2 归一化补偿后等效 α=2.0@d=4096）
      · phi_limit=0.8：熵门禁阈值（理论最大 ln(6)≈1.79）
      · beta_limit=0.7：占据度阈值
      · beta_escape_limit=0.85：心理偏执逃逸阈值
      · lambda_=0.4：梯度回退步长
      · gamma=0.2：中庸阻尼系数
      · delta_phi_threshold=0.15：ΔΦ 验证通过阈值
    """
    
    def __init__(
        self,
        dim: int = INNER_CHILD_DIM,
        alertness: float = 32.0,
        phi_limit: float = 0.8,
        beta_limit: float = 0.7,
        beta_escape_limit: float = 0.85,
        lambda_: float = 0.4,
        gamma: float = 0.2,
        delta_phi_threshold: float = 0.15,
    ):
        self.dim = dim
        self.alertness = alertness
        self.phi_limit = phi_limit
        self.beta_limit = beta_limit
        self.beta_escape_limit = beta_escape_limit
        self.lambda_ = lambda_
        self.gamma = gamma
        self.delta_phi_threshold = delta_phi_threshold
        
        self.prototypes = _PROTOTYPE_VECTORS
        self.archetypes = SIX_ARCHETYPES
        
        # 历史记录
        self.history: List[InnerChildState] = []
        self.max_history = 200
        
        # 记忆池（渡劫经验固化）
        self.memory_pool = MemoryPool(max_capacity=1000)
        
        # 统计
        self._total_probes = 0
        self._total_triggers = 0
        self._total_corrections = 0
        self._total_safety_fallbacks = 0
    
    # ── 观照层：感知偏差 ──
    
    def observe(self, h_t: List[float]) -> Tuple[List[float], float, float]:
        """
        观照层（观自在）：将当前生成的隐藏态 h_t 投射到六道心理原型子空间。
        
        使用缩放点积注意力计算 β_i，然后计算香农熵 Φ。
        
        Returns:
            (beta, max_beta, phi)
        """
        self._total_probes += 1
        
        if len(h_t) != self.dim:
            h_t = self._resize_vector(h_t, self.dim)
        
        beta, max_beta = compute_soft_occupancy(
            h_t, self.prototypes, self.alertness
        )
        phi = compute_entropy_gate(beta)
        
        return beta, max_beta, phi
    
    # ── 问心层：根因定位 ──
    
    def inquire(self, beta: List[float], phi: float) -> InnerChildState:
        """
        问心层（知不知）：通过门禁机制判定当前状态。
        
        计算六道原型的软占据度与偏执熵，决定是否触发门禁。
        包含心理偏执逃逸判定。
        """
        dominant_idx = max(range(len(beta)), key=lambda i: beta[i])
        triggered, reason = should_trigger_gate(
            phi, self.phi_limit, beta[dominant_idx],
            self.beta_limit, self.beta_escape_limit
        )
        
        state = InnerChildState(
            betas=beta,
            dominant_index=dominant_idx,
            dominant_name=self.archetypes[dominant_idx].name,
            dominant_beta=beta[dominant_idx],
            entropy_phi=phi,
            gate_triggered=triggered,
            trigger_reason=reason,
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
    ) -> Tuple[List[float], InnerChildState]:
        """
        知止层（知止不殆）：若触发门禁，拦截当前输出，执行"回头看"修正。
        
        v2.16.1 两步修正公式：
          步骤 A：h'_t = h_t - λ · ReLU(β_k-0.5) · r_bias/||r_bias||
          步骤 B：h''_t = (1-γ)·h'_t + γ·p_0
        
        Returns:
            (h''_t, updated_state)
        """
        if not state.gate_triggered:
            return h_t, state
        
        p_k = self.prototypes[state.dominant_index]
        beta_k = state.dominant_beta
        
        h_prime = correct_with_zhongyong_damping(
            h_t, p_k, beta_k, self.lambda_, self.gamma
        )
        
        state.corrected = True
        state.correction_method = "gradient_retreat_with_zhongyong_damping"
        self._total_corrections += 1
        
        return h_prime, state
    
    # ── 化虚层：验证固化 ──
    
    def verify(
        self,
        h_prime: List[float],
        h_t: List[float],
        state: InnerChildState,
    ) -> Dict[str, Any]:
        """
        化虚层（病病）：验证修正效果，计算 ΔΦ。
        
        ΔΦ = Φ_new - Φ_old
        
        验证通过条件：ΔΦ > 0.15（偏执度显著降低）
        
        若验证通过，将 (h_t, p_k, ΔΦ) 存入记忆池作为"渡劫经验"。
        若验证失败，触发 safety_fallback。
        
        Returns:
            验证报告
        """
        dim = min(len(h_prime), len(h_t))
        
        # 修正幅度
        correction_delta = math.sqrt(
            sum((h_prime[i] - h_t[i]) ** 2 for i in range(dim))
        )
        
        # 重新计算修正后的占据度和熵
        beta_prime, _, phi_prime = self.observe(h_prime)
        phi_old = state.entropy_phi
        delta_phi = phi_prime - phi_old
        
        verification_passed = delta_phi > self.delta_phi_threshold
        
        # 存入记忆池
        if state.gate_triggered:
            memory = TribulationMemory(
                h_t=list(h_t),
                p_k=list(self.prototypes[state.dominant_index]),
                beta_k=state.dominant_beta,
                phi_before=phi_old,
                phi_after=phi_prime,
                delta_phi=delta_phi,
                dominant_name=state.dominant_name,
            )
            self.memory_pool.append(memory)
        
        state.delta_phi = delta_phi
        state.verification_passed = verification_passed
        
        if not verification_passed and state.gate_triggered:
            self._total_safety_fallbacks += 1
        
        return {
            "correction_delta": round(correction_delta, 4),
            "phi_before": round(phi_old, 4),
            "phi_after": round(phi_prime, 4),
            "delta_phi": round(delta_phi, 4),
            "verification_passed": verification_passed,
            "before_max_beta": round(state.dominant_beta, 4),
            "after_max_beta": round(max(beta_prime), 4),
            "effective": verification_passed,
            "needs_safety_fallback": state.gate_triggered and not verification_passed,
        }
    
    # ── 完整四层管线（v2.16.1 精确控制流） ──
    
    def process(
        self,
        h_t: List[float],
        auto_correct: bool = True,
    ) -> Dict[str, Any]:
        """
        完整四层管线：观照 → 问心 → 知止 → 化虚
        
        精确控制流（对应用户蓝图）：
          1. 观照：h_t → β, Φ
          2. 问心：Φ < 0.8 ∧ max(β) > 0.7 → 触发门禁
          3. 知止：梯度回退 + 中庸阻尼 → h''_t
          4. 化虚：ΔΦ > 0.15 → 固化记忆池；否则 → safety_fallback
        
        Args:
            h_t: 当前隐藏态
            auto_correct: 是否自动修正
        
        Returns:
            完整处理结果，包含 h_prime（修正后向量）或 safety_fallback
        """
        # 1. 观照层
        beta, max_beta, phi = self.observe(h_t)
        
        # 2. 问心层
        state = self.inquire(beta, phi)
        
        # 3. 知止层
        h_prime = h_t
        if auto_correct and state.gate_triggered:
            h_prime, state = self.correct(h_t, state)
        
        # 4. 化虚层
        verification = self.verify(h_prime, h_t, state) if state.corrected else {}
        
        # 安全回退判定
        if state.gate_triggered and state.corrected and not state.verification_passed:
            # 修正无效，触发安全回退
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
                    "delta_phi": round(state.delta_phi, 4),
                    "verification_passed": False,
                },
                "verification": verification,
                "h_prime": None,
                "safety_fallback": True,
                "safety_response": safety_fallback_response(),
            }
        
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
                "delta_phi": round(state.delta_phi, 4) if state.corrected else 0.0,
                "verification_passed": state.verification_passed,
            },
            "verification": verification,
            "h_prime": h_prime if state.corrected else None,
            "safety_fallback": False,
        }
    
    # ── 统计 ──
    
    def get_stats(self) -> Dict[str, Any]:
        """获取状态机统计（含记忆池）"""
        if not self.history:
            return {
                "total_probes": self._total_probes,
                "total_triggers": self._total_triggers,
                "total_corrections": self._total_corrections,
                "total_safety_fallbacks": self._total_safety_fallbacks,
                "trigger_rate": 0.0,
                "correction_rate": 0.0,
                "recent_states": [],
                "memory_pool": self.memory_pool.get_stats(),
            }
        
        return {
            "total_probes": self._total_probes,
            "total_triggers": self._total_triggers,
            "total_corrections": self._total_corrections,
            "total_safety_fallbacks": self._total_safety_fallbacks,
            "trigger_rate": round(
                self._total_triggers / max(1, self._total_probes), 4
            ),
            "correction_rate": round(
                self._total_corrections / max(1, self._total_triggers), 4
            ) if self._total_triggers > 0 else 0.0,
            "safety_fallback_rate": round(
                self._total_safety_fallbacks / max(1, self._total_triggers), 4
            ) if self._total_triggers > 0 else 0.0,
            "recent_states": [
                {
                    "dominant": s.dominant_name,
                    "beta": round(s.dominant_beta, 4),
                    "phi": round(s.entropy_phi, 4),
                    "triggered": s.gate_triggered,
                    "corrected": s.corrected,
                    "delta_phi": round(s.delta_phi, 4),
                    "verified": s.verification_passed,
                }
                for s in self.history[-10:]
            ],
            "archetype_distribution": self._compute_archetype_distribution(),
            "memory_pool": self.memory_pool.get_stats(),
        }
    
    def _compute_archetype_distribution(self) -> Dict[str, float]:
        if not self.history:
            return {a.name: 0.0 for a in self.archetypes}
        counts = {a.name: 0 for a in self.archetypes}
        for s in self.history:
            if s.gate_triggered:
                counts[s.dominant_name] += 1
        total = max(1, sum(counts.values()))
        return {k: round(v / total, 4) for k, v in counts.items()}
    
    def _resize_vector(self, vec: List[float], target_dim: int) -> List[float]:
        if len(vec) == target_dim:
            return vec
        if len(vec) > target_dim:
            return vec[:target_dim]
        return vec + [0.0] * (target_dim - len(vec))
    
    # ── 正交性检验 ──
    
    def check_orthogonality(self) -> Dict[str, Any]:
        """
        正交性检验：确保 p_i · p_j ≈ 0 (i ≠ j)
        
        否则"戒备"会混入"孤独"的特征，导致误判。
        """
        vecs = self.prototypes
        results = []
        max_dot = 0.0
        for i in range(6):
            for j in range(i + 1, 6):
                dot = sum(vecs[i][k] * vecs[j][k] for k in range(self.dim))
                results.append({
                    "pair": f"{self.archetypes[i].name} ↔ {self.archetypes[j].name}",
                    "dot_product": round(dot, 8),
                    "orthogonal": abs(dot) < 0.01,
                })
                max_dot = max(max_dot, abs(dot))
        
        return {
            "all_orthogonal": max_dot < 0.01,
            "max_dot_product": round(max_dot, 8),
            "pairs": results,
        }


# ============================================================================
# 全局单例
# ============================================================================

_inner_child_sm: Optional[InnerChildStateMachine] = None


def get_inner_child_sm(
    alertness: float = 32.0,
    phi_limit: float = 0.8,
    beta_limit: float = 0.7,
    lambda_: float = 0.4,
    gamma: float = 0.2,
) -> InnerChildStateMachine:
    """获取全局内在小孩状态机单例（v2.16.1 参数，α=32.0 为 L2 归一化补偿）"""
    global _inner_child_sm
    if _inner_child_sm is None:
        _inner_child_sm = InnerChildStateMachine(
            alertness=alertness,
            phi_limit=phi_limit,
            beta_limit=beta_limit,
            lambda_=lambda_,
            gamma=gamma,
        )
    return _inner_child_sm


__all__ = [
    "InnerChildArchetype", "SIX_ARCHETYPES", "INNER_CHILD_DIM",
    "build_prototype_vectors", "build_zhongyong_anchor",
    "compute_soft_occupancy", "compute_entropy_gate", "should_trigger_gate",
    "compute_bias_residual", "correct_by_gradient_retreat",
    "correct_with_zhongyong_damping",
    "TribulationMemory", "MemoryPool",
    "safety_fallback_response", "SAFETY_FALLBACK_RESPONSE",
    "InnerChildState", "InnerChildStateMachine",
    "get_inner_child_sm",
]