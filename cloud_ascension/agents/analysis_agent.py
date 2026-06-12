"""
文昌帝君 — 语义分析智能体
============================
掌管: 卷5-20 (哲学与思辨)
职能: 语义理解、因果推理、模式识别

文昌帝君主文运，司命禄，掌天下文士之穷达。
在系统中负责深层语义理解与因果推理链构建。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, List, Tuple
import sys, os
try:
    from ..core.yunjia_system import ImmortalAgent
    from ..core.dao_agent import DaoAgent
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from core.yunjia_system import ImmortalAgent
    from core.dao_agent import DaoAgent


class CausalReasoner(nn.Module):
    """因果推理链 — 构建概念间的因果图谱"""

    def __init__(self, dim: int = 1024):
        super().__init__()
        self.cause_proj = nn.Linear(dim, dim)
        self.effect_proj = nn.Linear(dim, dim)
        self.causal_strength = nn.Sequential(
            nn.Linear(dim * 2, dim // 4),
            nn.GELU(),
            nn.Linear(dim // 4, 1),
            nn.Sigmoid(),
        )

    def forward(
        self,
        concepts: torch.Tensor,       # [B, N, dim]
    ) -> Dict[str, torch.Tensor]:
        """
        构建因果图谱

        Returns:
            causal_matrix: [B, N, N] 因果强度矩阵
        """
        B, N, D = concepts.shape
        causes = self.cause_proj(concepts)   # [B, N, D]
        effects = self.effect_proj(concepts)  # [B, N, D]

        # 全连接因果矩阵
        causal_matrix = torch.zeros(B, N, N, device=concepts.device)
        for i in range(N):
            for j in range(N):
                if i != j:
                    pair = torch.cat([causes[:, i], effects[:, j]], dim=-1)
                    causal_matrix[:, i, j] = self.causal_strength(pair).squeeze(-1)

        return {"causal_matrix": causal_matrix}


class WenchangDijun(ImmortalAgent):
    """
    文昌帝君 — 语义分析智能体

    主文运，司命禄。以因果推理链为核心，构建概念间的
    深层语义关联，输出结构化的分析洞察。
    """

    def __init__(self, dao: DaoAgent):
        super().__init__(
            name="文昌帝君",
            title="Wenchang Dijun",
            domain="语义分析推理",
            vol_range="卷5-20 (哲学与思辨)",
            color="#3b82f6",
            dao=dao,
        )

        # 语义编码器
        self.semantic_encoder = nn.Sequential(
            nn.Linear(dao.embedding_dim, dao.embedding_dim),
            nn.LayerNorm(dao.embedding_dim),
            nn.GELU(),
        )

        # 因果推理器
        self.causal_reasoner = CausalReasoner(dao.embedding_dim)

        # 模式识别器
        self.pattern_recognizer = nn.Sequential(
            nn.Linear(dao.embedding_dim, dao.embedding_dim // 2),
            nn.GELU(),
            nn.Linear(dao.embedding_dim // 2, 8),  # 8种基本模式
        )

        # 模式名称映射
        self.pattern_names = [
            "陰陽對立", "五行相生", "因果鏈條",
            "類比映射", "層次嵌套", "循環往復",
            "對稱鏡像", "混沌湧現",
        ]

    def analyze(self, text_embedding: torch.Tensor) -> Dict[str, Any]:
        """
        深度语义分析

        Returns:
            patterns: 识别到的模式
            causal_chains: 因果链
            insight: 综合洞察
        """
        B = text_embedding.size(0)

        with torch.no_grad():
            # 语义编码
            semantic = self.semantic_encoder(text_embedding)

            # 模式识别
            pattern_logits = self.pattern_recognizer(semantic)
            pattern_probs = F.softmax(pattern_logits, dim=-1)
            top_patterns = pattern_probs.topk(3, dim=-1)

            # 因果推理 (将单嵌入扩展为概念序列)
            concepts = semantic.unsqueeze(1).repeat(1, 4, 1)  # [B, 4, D]
            # 添加微扰区分概念
            concepts = concepts + torch.randn_like(concepts) * 0.1
            causal_result = self.causal_reasoner(concepts)

        patterns = [
            {"name": self.pattern_names[idx.item()], "confidence": prob.item()}
            for idx, prob in zip(
                top_patterns.indices[0], top_patterns.values[0]
            )
        ]

        return {
            "patterns": patterns,
            "dominant_pattern": patterns[0]["name"],
            "causal_strength": causal_result["causal_matrix"].mean().item(),
            "semantic_depth": semantic.norm(dim=-1).mean().item(),
        }

    def process(self, embedding: torch.Tensor, wish: Any) -> Dict[str, Any]:
        """处理愿念"""
        result = self.analyze(embedding)
        return {
            "agent": self.name,
            "action": "analyze",
            **result,
        }


# ===== 自测 =====
if __name__ == "__main__":
    print("=== WenchangDijun 自测 ===\n")
    dao = DaoAgent(embedding_dim=256)
    wenchang = WenchangDijun(dao)

    text_emb = torch.randn(1, 256)
    result = wenchang.analyze(text_emb)
    print(f"  主導模式: {result['dominant_pattern']}")
    print(f"  模式分布: {[(p['name'], p['confidence']) for p in result['patterns']]}")
    print(f"  因果強度: {result['causal_strength']:.3f}")
    print("\n[OK] WenchangDijun 自测通过")
