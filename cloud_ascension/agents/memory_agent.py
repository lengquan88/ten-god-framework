"""
东华帝君 — 知识记忆智能体
============================
掌管: 卷41-70 (神仙与传记)
职能: 知识存储、检索、联想

东华帝君居东华紫府，掌管仙籍簿录，统领一切知识存储。
在系统中负责知识库管理、向量检索和联想匹配。
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


class MemoryBank(nn.Module):
    """记忆库 — 可扩展的外部知识存储"""

    def __init__(self, dim: int = 1024, max_size: int = 10000):
        super().__init__()
        self.dim = dim
        self.max_size = max_size
        self.register_buffer("keys", torch.zeros(max_size, dim))
        self.register_buffer("values", torch.zeros(max_size, dim))
        self.register_buffer("ages", torch.zeros(max_size))
        self.size = 0

    def store(self, key: torch.Tensor, value: torch.Tensor) -> int:
        """存储记忆"""
        idx = self.size % self.max_size
        self.keys[idx] = key.squeeze(0)
        self.values[idx] = value.squeeze(0)
        self.ages[idx] = 0
        self.size += 1
        return idx

    def query(self, query: torch.Tensor, top_k: int = 5) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """检索最相似的记忆"""
        if self.size == 0:
            return torch.zeros(1, top_k, self.dim), torch.zeros(1, top_k), torch.zeros(1, top_k)

        effective_size = min(self.size, self.max_size)
        keys = self.keys[:effective_size]
        similarity = F.cosine_similarity(
            query.unsqueeze(1), keys.unsqueeze(0), dim=-1
        )
        top_scores, top_indices = similarity.topk(min(top_k, effective_size), dim=-1)
        top_values = self.values[top_indices]
        return top_values, top_scores, top_indices

    def forget_old(self, threshold: float = 0.5):
        """遗忘旧记忆 (按年龄衰减)"""
        self.ages += 1
        mask = self.ages < threshold * self.max_size
        self.keys = self.keys * mask.unsqueeze(-1)
        self.values = self.values * mask.unsqueeze(-1)


class DonghuaDijun(ImmortalAgent):
    """
    东华帝君 — 知识记忆智能体

    居东华紫府，掌管仙籍簿录。以记忆库为核心，
    支持知识存储、向量检索、跨卷宗联想。
    """

    def __init__(self, dao: DaoAgent):
        super().__init__(
            name="东华帝君",
            title="Donghua Dijun",
            domain="知识存储检索",
            vol_range="卷41-70 (神仙与传记)",
            color="#8b5cf6",
            dao=dao,
        )
        self.memory_bank = MemoryBank(dao.embedding_dim)

        # 联想网络 — 在记忆中建立概念关联
        self.association_net = nn.Sequential(
            nn.Linear(dao.embedding_dim * 2, dao.embedding_dim),
            nn.GELU(),
            nn.Linear(dao.embedding_dim, 1),
            nn.Sigmoid(),
        )

    def memorize(self, content_emb: torch.Tensor, label: str = "") -> Dict[str, Any]:
        """将知识存入记忆库"""
        idx = self.memory_bank.store(content_emb, content_emb)
        return {
            "action": "memorize",
            "location": idx,
            "label": label,
            "memory_size": self.memory_bank.size,
        }

    def recall(self, query_emb: torch.Tensor, top_k: int = 5) -> Dict[str, Any]:
        """从记忆库检索知识"""
        values, scores, indices = self.memory_bank.query(query_emb, top_k)
        return {
            "action": "recall",
            "num_results": min(top_k, self.memory_bank.size),
            "top_similarity": scores[0, 0].item() if scores.numel() > 0 else 0.0,
            "avg_similarity": scores.mean().item() if scores.numel() > 0 else 0.0,
            "retrieved_embeddings": values,
        }

    def associate(self, emb_a: torch.Tensor, emb_b: torch.Tensor) -> Dict[str, Any]:
        """联想匹配 — 计算两概念间的关联度"""
        pair = torch.cat([emb_a, emb_b], dim=-1)
        strength = self.association_net(pair).item()
        return {
            "action": "associate",
            "strength": strength,
            "relation": "紧密" if strength > 0.7 else ("相关" if strength > 0.4 else "疏远"),
        }

    def process(self, embedding: torch.Tensor, wish: Any) -> Dict[str, Any]:
        result = self.recall(embedding)
        return {
            "agent": self.name,
            **result,
        }


# ===== 自测 =====
if __name__ == "__main__":
    print("=== DonghuaDijun 自测 ===\n")
    dao = DaoAgent(embedding_dim=256)
    donghua = DonghuaDijun(dao)

    # 存储知识
    for i in range(5):
        mem = torch.randn(1, 256)
        r = donghua.memorize(mem, f"知識_{i}")
    print(f"  記憶庫大小: {donghua.memory_bank.size}")

    # 检索
    query = torch.randn(1, 256)
    recall = donghua.recall(query)
    print(f"  檢索結果: {recall['num_results']}項")
    print(f"  最高相似度: {recall['top_similarity']:.3f}")

    print("\n[OK] DonghuaDijun 自测通过")
