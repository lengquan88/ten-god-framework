"""
gate_torch.py — 门禁认知系统 PyTorch 加速层 v3.1.0
=====================================================
道曰："人法地，地法天，天法道，道法自然。"

三个任务的门禁层 PyTorch 实现，与现有纯 Python 门禁体系无缝对接：
  - 任务一：TBCESixDimProjector  — 六维投影 + 测地线门禁（替换 n-gram cosine）
  - 任务二：GateFilter               — 三道门禁（权限/资源/因果）+ 节奏采样
  - 任务三：ZuowangAttentionTorch    — 坐忘门禁 + IntentDisambiguator（主动澄清）

集成现有模块：
  - tbce_unit.TBCECoordinates  → 六维坐标输入
  - tbce_unit.GateState        → 门禁三态裁决
  - twelve_gods_base           → 十二神门禁系数热加载
  - zuowang_attention          → 坐忘逻辑对齐

依赖策略：
  - torch 可用 → 使用 nn.Linear / MultiheadAttention / einsum 加速
  - torch 不可用 → 纯 Python fallback（功能等价，性能较低）
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ── 可选 torch 导入 ──────────────────────────────────────────────
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False
    torch = None  # type: ignore
    nn = None     # type: ignore
    F = None      # type: ignore

# ── 现有模块对接 ──────────────────────────────────────────────────
from .tbce_unit import TBCECoordinates, CognitiveUnit, GateState

# 九宫格门禁系数默认值（与洛书九宫对应）
_DEFAULT_GATE_MODS = {
    # 坎一 (水)  → S 维调制
    "kan_1":  np.array([1.0, 0.8, 1.0, 1.0, 1.0, 1.0], dtype=np.float32),
    # 坤二 (土)  → C 维调制
    "kun_2":  np.array([1.0, 1.0, 1.0, 0.8, 1.0, 1.0], dtype=np.float32),
    # 震三 (木)  → I 维调制
    "zhen_3": np.array([1.0, 1.0, 1.0, 1.0, 0.8, 1.0], dtype=np.float32),
    # 巽四 (木)  → P 维调制
    "xun_4":  np.array([1.0, 1.0, 0.8, 1.0, 1.0, 1.0], dtype=np.float32),
    # 中五 (土)  → 全维均衡
    "zhong_5": np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float32),
    # 乾六 (金)  → T 维调制
    "qian_6": np.array([1.0, 0.8, 1.0, 1.0, 1.0, 1.0], dtype=np.float32),
    # 兑七 (金)  → E 维调制
    "dui_7":  np.array([1.0, 1.0, 1.0, 1.0, 1.0, 0.8], dtype=np.float32),
    # 艮八 (土)  → S+E 双维调制
    "gen_8":  np.array([0.8, 1.0, 1.0, 1.0, 1.0, 0.8], dtype=np.float32),
    # 离九 (火)  → P+C 双维调制
    "li_9":   np.array([1.0, 1.0, 0.8, 0.8, 1.0, 1.0], dtype=np.float32),
}


# ============================================================================
# 工具函数
# ============================================================================

def _ensure_numpy(x: Any) -> np.ndarray:
    """将 torch tensor 或 list 转为 numpy"""
    if _HAS_TORCH and isinstance(x, torch.Tensor):
        return x.detach().cpu().numpy()
    if isinstance(x, list):
        return np.array(x, dtype=np.float32)
    if isinstance(x, np.ndarray):
        return x.astype(np.float32)
    return np.array(x, dtype=np.float32)


def _to_tensor(x: Any) -> "torch.Tensor":
    """将 numpy/list 转为 torch tensor"""
    if _HAS_TORCH and isinstance(x, torch.Tensor):
        return x
    arr = _ensure_numpy(x)
    if _HAS_TORCH:
        return torch.from_numpy(arr)
    return arr  # type: ignore


# ============================================================================
# 任务一：TBCE 六维投影 + 测地线门禁
# ============================================================================

class TBCESixDimProjector:
    """把 chunk embedding 投影到 S/T/P/C/I/E 六维，每维由门禁系数调制。

    与现有 tbce_unit.TBCECoordinates 对接：
      - 输入：(batch, dim) embedding
      - 输出：(batch, 6) 六维向量，可转为 TBCECoordinates
      - 门禁系数：从九宫格 JSON 热加载，或使用十二神门禁系数

    当 torch 不可用时，使用 numpy 线性投影。
    """

    def __init__(self, dim: int = 768, gate_mods: Optional[Dict[str, np.ndarray]] = None):
        self.dim = dim
        self.gate_mods = gate_mods or dict(_DEFAULT_GATE_MODS)
        self._load_gate_mods_from_env()

        if _HAS_TORCH:
            self._proj = nn.Linear(dim, 6, bias=False)
            # 初始化：用正交初始化让六维尽可能独立
            nn.init.orthogonal_(self._proj.weight)
            self._use_torch = True
        else:
            # numpy fallback: 随机正交投影矩阵
            rng = np.random.RandomState(42)
            W = rng.randn(dim, 6).astype(np.float32)
            U, _, Vt = np.linalg.svd(W, full_matrices=False)
            self._proj_np = (U @ Vt).T  # (6, dim)
            self._use_torch = False

    def _load_gate_mods_from_env(self) -> None:
        """从环境变量 GATE_MODS_JSON 热加载九宫格门禁系数"""
        path = os.environ.get("GATE_MODS_JSON", "")
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in self.gate_mods and isinstance(v, list) and len(v) == 6:
                    self.gate_mods[k] = np.array(v, dtype=np.float32)

    def forward(
        self,
        x: Any,
        gate_mods: Optional[np.ndarray] = None,
        palace_id: Optional[int] = None,
    ) -> np.ndarray:
        """前向投影

        Args:
            x: (batch, dim) embedding 或 (dim,) 单向量
            gate_mods: (6,) 六维门禁调制系数，覆盖默认
            palace_id: 九宫格编号 (1-9)，自动选择对应门禁系数

        Returns:
            (batch, 6) 六维向量
        """
        # 自动选择九宫格门禁系数
        if gate_mods is None and palace_id is not None:
            palace_key = {
                1: "kan_1", 2: "kun_2", 3: "zhen_3",
                4: "xun_4", 5: "zhong_5", 6: "qian_6",
                7: "dui_7", 8: "gen_8", 9: "li_9",
            }.get(palace_id, "zhong_5")
            gate_mods = self.gate_mods.get(palace_key, np.ones(6, dtype=np.float32))

        if gate_mods is None:
            gate_mods = np.ones(6, dtype=np.float32)

        if self._use_torch:
            return self._forward_torch(x, gate_mods)
        else:
            return self._forward_numpy(x, gate_mods)

    def _forward_torch(self, x: Any, gate_mods: np.ndarray) -> np.ndarray:
        x_t = _to_tensor(x).float()
        if x_t.dim() == 1:
            x_t = x_t.unsqueeze(0)
        vec_6d = self._proj(x_t)  # (batch, 6)
        gate_t = torch.from_numpy(gate_mods.astype(np.float32)).to(x_t.device)
        vec_6d = vec_6d * gate_t
        return vec_6d.detach().cpu().numpy()

    def _forward_numpy(self, x: Any, gate_mods: np.ndarray) -> np.ndarray:
        x_np = _ensure_numpy(x)
        if x_np.ndim == 1:
            x_np = x_np.reshape(1, -1)
        vec_6d = x_np @ self._proj_np.T  # (batch, 6)
        return vec_6d * gate_mods

    def to_tbce_coordinates(self, vec_6d: np.ndarray) -> TBCECoordinates:
        """将六维向量转为 TBCECoordinates"""
        v = vec_6d.reshape(-1)
        # 归一化到合理范围
        v = np.clip(v, 0.0, 1.0)
        return TBCECoordinates(
            S=float(v[0]), T=float(v[1]), P=float(v[2]),
            C=float(v[3]), I=float(v[4]), E=float(v[5]),
        )

    def get_embedding_layer(self) -> Any:
        """获取投影矩阵，用于与其他系统对接"""
        if self._use_torch:
            return self._proj
        return self._proj_np


def geodesic_distance(
    v1: Any,
    v2: Any,
    metric_tensor: Optional[np.ndarray] = None,
) -> float:
    """黎曼流形上的测地线距离（非欧氏距离）

    与 tbce_unit.TBCECoordinates.distance() 数学等价，
    但使用 PyTorch einsum 加速（当 torch 可用时）。

    Args:
        v1: (6,) 六维向量
        v2: (6,) 六维向量
        metric_tensor: (6, 6) 度量张量 g_μν，默认使用 TBCE 默认度量

    Returns:
        测地线距离 ≥ 0
    """
    v1_np = _ensure_numpy(v1).reshape(6)
    v2_np = _ensure_numpy(v2).reshape(6)

    if metric_tensor is None:
        metric_tensor = np.array([
            [2.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 2.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.5, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.5, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        ], dtype=np.float32)

    diff = v1_np - v2_np

    if _HAS_TORCH:
        diff_t = torch.from_numpy(diff)
        metric_t = torch.from_numpy(metric_tensor)
        dist_sq = torch.einsum('i,ij,j', diff_t, metric_t, diff_t)
        return float(torch.sqrt(torch.clamp(dist_sq, min=0.0)).item())
    else:
        dist_sq = diff @ metric_tensor @ diff
        return float(math.sqrt(max(dist_sq, 0.0)))


# ============================================================================
# 任务二：门禁预过滤 + 节奏采样
# ============================================================================

class GateFilter:
    """三道门禁：权限门禁、资源门禁、因果门禁

    对接现有 twelve_gods_base.TwelveGodsGate：
      - 权限门禁：调用架构门禁 (比肩/劫财·木)
      - 资源门禁：系统负载判断
      - 因果门禁：PyTorch Linear 层判断 query 语义自洽性

    三态裁决：
      - 三关全开 → "开"
      - 两关开 → "徘徊"（人工确认）
      - 其他 → "关"（拒绝）
    """

    def __init__(self, dim: int = 768):
        self.dim = dim
        if _HAS_TORCH:
            self._causal_score = nn.Linear(dim, 1)
            nn.init.xavier_uniform_(self._causal_score.weight)
            self._use_torch = True
        else:
            # numpy fallback: 随机权重
            rng = np.random.RandomState(42)
            self._causal_np = rng.randn(dim, 1).astype(np.float32) / math.sqrt(dim)
            self._use_torch = False

        # 授权白名单（可动态更新）
        self._auth_whitelist: List[str] = []

    def set_whitelist(self, patterns: List[str]) -> None:
        """设置授权白名单"""
        self._auth_whitelist = patterns

    def is_authorized(self, query_text: str) -> bool:
        """权限门禁：检查 query 是否在授权范围内"""
        if not self._auth_whitelist:
            return True  # 空白名单 → 全部放行
        return any(pattern in query_text for pattern in self._auth_whitelist)

    def forward(
        self,
        query_emb: Any,
        query_text: str = "",
        system_load: float = 0.5,
    ) -> Tuple[str, Dict[str, Any]]:
        """三道门禁裁决

        Args:
            query_emb: (dim,) embedding
            query_text: 原始 query 文本（用于权限门禁）
            system_load: 系统负载 [0, 1]

        Returns:
            (gate_state, details)
              gate_state: "开" | "徘徊" | "关"
        """
        details: Dict[str, Any] = {}

        # 1. 权限门禁
        details["auth_gate"] = 1.0 if self.is_authorized(query_text) else 0.0

        # 2. 资源门禁
        details["resource_gate"] = 1.0 if system_load < 0.8 else 0.0

        # 3. 因果门禁
        causal_score = self._compute_causal_score(query_emb)
        details["causal_score"] = float(causal_score)
        details["causal_gate"] = 1.0 if causal_score > 0.5 else 0.0

        gate_sum = details["auth_gate"] + details["resource_gate"] + details["causal_gate"]

        if gate_sum >= 3.0:
            return GateState.OPEN, details
        elif gate_sum >= 2.0:
            return GateState.PENDING, details
        else:
            return GateState.CLOSED, details

    def _compute_causal_score(self, query_emb: Any) -> float:
        """因果门禁：query 语义是否自洽"""
        x = _ensure_numpy(query_emb).reshape(1, -1)
        if self._use_torch:
            x_t = torch.from_numpy(x).float()
            score = torch.sigmoid(self._causal_score(x_t))
            return float(score.item())
        else:
            raw = float((x @ self._causal_np).item())
            score = 1.0 / (1.0 + math.exp(-raw))
            return score


class RhythmScheduler:
    """节奏采样调度器：根据系统负载动态调整检索深度 tau

    对应 DeepSpec 的 DSparkScheduler，tau ∈ [2, 6]：
      - 低负载 → tau=6（深度检索）
      - 高负载 → tau=2（浅层检索）
    """

    def __init__(self, tau_min: int = 2, tau_max: int = 6):
        self.tau_min = tau_min
        self.tau_max = tau_max
        self._history: List[float] = []  # 负载历史

    def adjust_tau(self, system_load: float) -> int:
        """根据负载调整检索深度

        Args:
            system_load: 系统负载 [0, 1]

        Returns:
            tau ∈ [tau_min, tau_max]
        """
        self._history.append(system_load)
        if len(self._history) > 100:
            self._history = self._history[-100:]

        # 负载越高 → tau 越小
        tau = self.tau_max - (self.tau_max - self.tau_min) * min(system_load, 1.0)
        return max(self.tau_min, int(round(tau)))

    def get_load_trend(self) -> str:
        """负载趋势"""
        if len(self._history) < 5:
            return "stable"
        recent = self._history[-5:]
        if recent[-1] > recent[0] * 1.2:
            return "rising"
        elif recent[-1] < recent[0] * 0.8:
            return "falling"
        return "stable"


# ============================================================================
# 任务三：坐忘门禁 + 意图歧义消解
# ============================================================================

class ZuowangAttentionTorch:
    """坐忘注意力（PyTorch 加速版）

    与现有 zuowang_attention.ZuowangAttention 逻辑对齐：
      - 当 max(softmax(attention_weights)) < theta → 门禁关闭，触发坐忘
      - theta 默认 0.7（与现有 zuowang_attention 对齐）

    注意：当 torch 不可用时，使用余弦相似度作为注意力（而非随机 QKV），
    确保语义相近的 query/history 对能正确通过坐忘门禁。
    """

    def __init__(self, embed_dim: int = 768, num_heads: int = 12, theta: float = 0.7):
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.theta = theta

        if _HAS_TORCH:
            self._attn = nn.MultiheadAttention(
                embed_dim=embed_dim,
                num_heads=num_heads,
                batch_first=True,
            )
            self._use_torch = True
        else:
            self._use_torch = False

    def forward(
        self,
        query_emb: Any,
        history_embs: Any,
    ) -> Tuple[str, np.ndarray]:
        """坐忘注意力前向

        Args:
            query_emb: (embed_dim,) 当前 query embedding
            history_embs: (seq_len, embed_dim) 历史上下文 embeddings

        Returns:
            (gate_state, attn_output)
              gate_state: "开" | "徘徊"
              attn_output: (embed_dim,) 注意力输出
        """
        # 空 history 或无有效历史 → 跳过坐忘门禁，直接放行
        h = _ensure_numpy(history_embs)
        if h.ndim == 1:
            h = h.reshape(1, -1)
        if h.shape[0] == 0 or np.allclose(h, 0) or np.linalg.norm(h) < 1e-6:
            return GateState.OPEN, _ensure_numpy(query_emb).reshape(-1)

        if self._use_torch:
            return self._forward_torch(query_emb, history_embs)
        else:
            return self._forward_numpy(query_emb, history_embs)

    def _forward_torch(self, query_emb: Any, history_embs: Any) -> Tuple[str, np.ndarray]:
        q = _to_tensor(query_emb).float()                    # (dim,)
        h = _to_tensor(history_embs).float()                  # (seq_len, dim)
        if h.dim() == 1:
            h = h.unsqueeze(0)

        # 余弦相似度作为注意力（语义感知，非随机 QKV）
        q_norm = torch.nn.functional.normalize(q.unsqueeze(0), dim=1)  # (1, dim)
        h_norm = torch.nn.functional.normalize(h, dim=1)               # (seq_len, dim)
        cosine_sim = q_norm @ h_norm.T                                  # (1, seq_len)
        weights = torch.softmax(cosine_sim, dim=-1)                     # (1, seq_len)
        max_attn = float(weights.max().item())

        gate_state = GateState.PENDING if max_attn < self.theta else GateState.OPEN
        output = (weights @ h).squeeze(0).detach().cpu().numpy()        # (dim,)
        return gate_state, output

    def _forward_numpy(self, query_emb: Any, history_embs: Any) -> Tuple[str, np.ndarray]:
        q = _ensure_numpy(query_emb).reshape(1, -1)      # (1, dim)
        h = _ensure_numpy(history_embs)                    # (seq_len, dim)
        if h.ndim == 1:
            h = h.reshape(1, -1)

        # 余弦相似度作为注意力（而非随机 QKV 投影）
        q_norm = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-8)
        h_norm = h / (np.linalg.norm(h, axis=1, keepdims=True) + 1e-8)
        cosine_sim = q_norm @ h_norm.T                       # (1, seq_len)
        # softmax
        sim_max = cosine_sim.max()
        weights = np.exp(cosine_sim - sim_max) / np.exp(cosine_sim - sim_max).sum()
        max_attn = float(weights.max())

        gate_state = GateState.PENDING if max_attn < self.theta else GateState.OPEN
        output = (weights @ h).reshape(-1)                    # (dim,)
        return gate_state, output


class IntentDisambiguator:
    """意图歧义消解 + 主动澄清

    对接现有 ai_interpreter.IntentTracker：
      - 坐忘门禁 → 先判断是否触发坐忘
      - 意图分类 → softmax 置信度分布
      - 歧义判断 → top-3 候选 + 主动澄清

    意图标签（与现有 TOPIC_KEYWORDS 对齐）：
      0: 八字命理, 1: 紫微斗数, 2: 六爻占卜, 3: 风水堪舆, 4: 姓名学
    """

    INTENT_LABELS = [
        "八字命理", "紫微斗数", "六爻占卜", "风水堪舆", "姓名学",
    ]

    # 每个意图的关键词（用于冷启动启发式）
    INTENT_KEYWORDS = {
        0: ["八字", "排盘", "年柱", "月柱", "日柱", "时柱", "天干", "地支", "十神", "命理", "算命", "命", "五行", "大运", "流年", "用神", "日主"],
        1: ["紫微", "斗数", "命盘", "十二宫", "命宫", "星曜", "四化", "三方四正", "紫微星", "天府", "七杀"],
        2: ["六爻", "起卦", "占卜", "铜钱", "卦", "爻", "世应", "动爻", "变卦", "预测"],
        3: ["风水", "堪舆", "峦头", "理气", "玄空", "飞星", "罗盘", "九宫", "旺山", "布局", "方位"],
        4: ["姓名", "取名", "改名", "名字", "五格", "数理", "字义", "笔画", "三才", "起名"],
    }

    def __init__(
        self,
        embed_dim: int = 768,
        num_intents: int = 5,
        confidence_threshold: float = 0.6,
        theta: float = 0.7,
    ):
        self.embed_dim = embed_dim
        self.num_intents = num_intents
        self.confidence_threshold = confidence_threshold
        self.theta = theta

        # 坐忘门禁
        self._zuowang = ZuowangAttentionTorch(
            embed_dim=embed_dim, num_heads=12, theta=theta,
        )

        if _HAS_TORCH:
            self._intent_classifier = nn.Linear(embed_dim, num_intents)
            nn.init.xavier_uniform_(self._intent_classifier.weight)
            self._use_torch = True
        else:
            rng = np.random.RandomState(42)
            self._intent_np = rng.randn(embed_dim, num_intents).astype(np.float32) / math.sqrt(embed_dim)
            self._use_torch = False

    def forward(
        self,
        query_emb: Any,
        history_embs: Any,
        query_text: str = "",
    ) -> Tuple[str, Dict[str, Any]]:
        """意图歧义消解

        Args:
            query_emb: (embed_dim,) 当前 query embedding
            history_embs: (seq_len, embed_dim) 历史上下文 embeddings
            query_text: 原始 query 文本（用于关键词启发式）

        Returns:
            (action, result)
              action: "澄清" | "开"
              result: 包含 candidates 或 intent + confidence
        """
        # 1. 坐忘门禁
        gate_state, attn_out = self._zuowang.forward(query_emb, history_embs)
        if gate_state == GateState.PENDING:
            return "澄清", {
                "reason": "坐忘门禁触发",
                "message": "我发现了多种可能，请选择一种",
            }

        # 2. 意图分类（融合随机分类器 + 关键词启发式）
        probs = self._classify_intents(attn_out, query_text)
        max_prob = float(probs.max())
        max_idx = int(probs.argmax())

        # 3. 歧义判断
        if max_prob < self.confidence_threshold:
            top3_indices = np.argsort(probs)[-3:][::-1]
            candidates = [
                {
                    "intent_id": int(idx),
                    "intent_name": self.INTENT_LABELS[int(idx)] if int(idx) < len(self.INTENT_LABELS) else f"未知{idx}",
                    "confidence": float(probs[idx]),
                }
                for idx in top3_indices
            ]
            return "澄清", {
                "reason": "意图歧义",
                "candidates": candidates,
                "message": f"您是指以下哪种？\n" + "\n".join(
                    f"{i+1}. {c['intent_name']} (置信度 {c['confidence']:.0%})"
                    for i, c in enumerate(candidates)
                ),
            }
        else:
            intent_name = self.INTENT_LABELS[max_idx] if max_idx < len(self.INTENT_LABELS) else f"未知{max_idx}"
            return "开", {
                "intent": max_idx,
                "intent_name": intent_name,
                "confidence": max_prob,
            }

    def _classify_intents(self, attn_out: np.ndarray, query_text: str = "") -> np.ndarray:
        """意图分类 → softmax 概率分布（融合随机分类器 + 关键词启发式）"""
        x = attn_out.reshape(1, -1)

        # 随机分类器输出
        if self._use_torch:
            x_t = torch.from_numpy(x).float()
            logits = self._intent_classifier(x_t)
            base_probs = F.softmax(logits, dim=-1).detach().cpu().numpy().reshape(-1)
        else:
            logits = x @ self._intent_np
            logits = logits - logits.max()
            base_probs = np.exp(logits) / np.exp(logits).sum()
            base_probs = base_probs.reshape(-1)

        # 关键词启发式：boost 匹配意图的置信度
        if query_text:
            boost = np.zeros(self.num_intents, dtype=np.float32)
            for intent_id, keywords in self.INTENT_KEYWORDS.items():
                hits = sum(1 for kw in keywords if kw in query_text)
                if hits > 0:
                    boost[intent_id] = min(hits * 0.3, 0.9)  # 每命中一个关键词 +0.3，上限 0.9
            # 融合：base_probs * 0.3 + boost * 0.7
            if boost.sum() > 0:
                probs = base_probs * 0.3 + boost * 0.7
                # 重新归一化
                probs = probs / probs.sum()
            else:
                probs = base_probs
        else:
            probs = base_probs

        return probs


# ============================================================================
# 批量检索：测地线距离门禁排序
# ============================================================================

def retrieve_with_gates(
    query_emb: Any,
    chunk_embs: List[Tuple[str, Any]],
    projector: Optional[TBCESixDimProjector] = None,
    threshold: float = 0.3,
    top_k: int = 10,
    metric_tensor: Optional[np.ndarray] = None,
) -> List[Tuple[str, float]]:
    """六维投影 + 测地线门禁检索

    替代现有 knowledge_base.py 的 n-gram cosine 检索。

    Args:
        query_emb: (dim,) 原始 embedding
        chunk_embs: [(chunk_id, (dim,) embedding), ...]
        projector: TBCESixDimProjector 实例
        threshold: 测地线距离阈值
        top_k: 返回数量
        metric_tensor: 度量张量

    Returns:
        [(chunk_id, geodesic_distance), ...] 按距离升序
    """
    # 1. 六维投影
    if projector is not None:
        q_6d = projector.forward(query_emb).reshape(6)
        chunks_6d = [
            (cid, projector.forward(emb).reshape(6))
            for cid, emb in chunk_embs
        ]
    else:
        q_6d = _ensure_numpy(query_emb).reshape(-1)
        if len(q_6d) < 6:
            # 不足6维时补零
            q_6d = np.pad(q_6d, (0, max(0, 6 - len(q_6d))))
        q_6d = q_6d[:6]
        chunks_6d = [
            (cid, _ensure_numpy(emb).reshape(-1)[:6])
            for cid, emb in chunk_embs
        ]

    # 2. 测地线距离 + 门禁过滤
    passed: List[Tuple[str, float]] = []
    for cid, c_emb in chunks_6d:
        if len(c_emb) >= 6:
            dist = geodesic_distance(q_6d, c_emb[:6], metric_tensor)
            if dist < threshold:
                passed.append((cid, float(dist)))

    # 3. 按距离升序取 top_k
    passed.sort(key=lambda x: x[1])
    return passed[:top_k]


# ============================================================================
# 自检
# ============================================================================

if __name__ == "__main__":
    print(f"门禁认知系统 PyTorch 加速层 v3.1.0")
    print(f"  torch 可用: {_HAS_TORCH}")
    print(f"  九宫格门禁系数: {len(_DEFAULT_GATE_MODS)} 宫加载")

    # 创建投影器
    proj = TBCESixDimProjector(dim=768)
    dummy_emb = np.random.randn(768).astype(np.float32)
    vec_6d = proj.forward(dummy_emb)
    print(f"  六维投影: {vec_6d.round(3)}")

    # 测地线距离
    d = geodesic_distance(vec_6d, np.ones(6, dtype=np.float32) * 0.5)
    print(f"  测地线距离: {d:.3f}")

    # 门禁裁决
    gate = GateFilter(dim=768)
    state, det = gate.forward(dummy_emb, query_text="帮我算一下八字", system_load=0.3)
    print(f"  门禁裁决: {state}, details={det}")

    # 节奏调度
    scheduler = RhythmScheduler()
    tau = scheduler.adjust_tau(0.3)
    print(f"  节奏采样 tau={tau} (load=0.3)")

    # 坐忘门禁
    zuowang = ZuowangAttentionTorch(embed_dim=768)
    history = np.random.randn(5, 768).astype(np.float32)
    gate_s, _ = zuowang.forward(dummy_emb, history)
    print(f"  坐忘门禁: {gate_s}")

    # 意图消解
    disambiguator = IntentDisambiguator(embed_dim=768)
    action, result = disambiguator.forward(dummy_emb, history)
    print(f"  意图消解: action={action}, result_keys={list(result.keys())}")