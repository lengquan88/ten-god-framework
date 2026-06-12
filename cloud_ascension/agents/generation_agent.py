"""
太上老君 — 内容生成智能体
============================
掌管: 卷21-40 (金丹与符箓)
职能: 文本生成、图像生成、符箓生成

太上老君居兜率天，掌炼丹与符箓之道，以八卦炉炼化万物。
在系统中负责所有内容生成：文本、符箓、图像、丹丸。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, List
import sys, os
try:
    from ..core.yunjia_system import ImmortalAgent
    from ..core.dao_agent import DaoAgent
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from core.yunjia_system import ImmortalAgent
    from core.dao_agent import DaoAgent


class TalismanGenerator(nn.Module):
    """符箓生成器 — 生成云篆风格的符箓图案嵌入"""

    def __init__(self, dim: int = 1024):
        super().__init__()
        self.style_encoder = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Linear(dim * 2, dim),
        )
        self.glyph_generator = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.GELU(),
            nn.Linear(dim // 2, 64 * 64),  # 64x64 符箓图像
            nn.Tanh(),
        )

    def forward(self, content_emb: torch.Tensor, style_emb: torch.Tensor = None):
        if style_emb is None:
            style_emb = content_emb
        fused = self.style_encoder(content_emb + style_emb)
        glyph = self.glyph_generator(fused)
        return glyph.view(-1, 1, 64, 64)


class TaishangLaojun(ImmortalAgent):
    """
    太上老君 — 内容生成智能体

    居兜率天，掌八卦炉。以炼丹之法生成一切内容，
    八卦炉的"火候"决定生成内容的质量与风格。
    """

    def __init__(self, dao: DaoAgent):
        super().__init__(
            name="太上老君",
            title="Taishang Laojun",
            domain="内容生成",
            vol_range="卷21-40 (金丹与符箓)",
            color="#e2e8f0",
            dao=dao,
        )
        self.talisman_gen = TalismanGenerator(dao.embedding_dim)

        # 文本生成器 (简化为嵌入->嵌入的扩散过程)
        self.text_generator = nn.Sequential(
            nn.Linear(dao.embedding_dim, dao.embedding_dim * 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(dao.embedding_dim * 2, dao.embedding_dim * 2),
            nn.GELU(),
            nn.Linear(dao.embedding_dim * 2, dao.embedding_dim),
            nn.LayerNorm(dao.embedding_dim),
        )

    def generate_talisman(self, seed_embedding: torch.Tensor) -> Dict[str, Any]:
        """生成符箓"""
        with torch.no_grad():
            glyph = self.talisman_gen(seed_embedding)
            complexity = glyph.abs().mean().item()
        return {
            "glyph_tensor": glyph,
            "complexity": complexity,
            "style": "雲篆" if complexity > 0.3 else "古文",
        }

    def generate_text(self, prompt_embedding: torch.Tensor, temperature: float = 0.7) -> Dict[str, Any]:
        """生成文本嵌入 (扩散过程)"""
        B = prompt_embedding.size(0)
        # 添加噪声模拟扩散
        noise = torch.randn_like(prompt_embedding) * temperature
        noisy = prompt_embedding + noise

        with torch.no_grad():
            generated = self.text_generator(noisy)
            # 迭代去燥 (模拟多步扩散)
            for _ in range(3):
                generated = self.text_generator(generated)

        return {
            "embedding": generated,
            "norm": generated.norm(dim=-1).mean().item(),
            "temperature": temperature,
        }

    def process(self, embedding: torch.Tensor, wish: Any) -> Dict[str, Any]:
        result = self.generate_text(embedding)
        return {
            "agent": self.name,
            "action": "generate",
            "output_norm": result["norm"],
            "temperature": result["temperature"],
        }


# ===== 自测 =====
if __name__ == "__main__":
    print("=== TaishangLaojun 自测 ===\n")
    dao = DaoAgent(embedding_dim=256)
    laojun = TaishangLaojun(dao)

    seed = torch.randn(1, 256)
    talisman = laojun.generate_talisman(seed)
    print(f"  符籙複雜度: {talisman['complexity']:.3f}")
    print(f"  風格: {talisman['style']}")

    text = laojun.generate_text(seed, temperature=0.7)
    print(f"  生成文本嵌入範數: {text['norm']:.3f}")
    print("\n[OK] TaishangLaojun 自测通过")
