"""
炼丹炉 AlchemyFurnace
=====================
知识蒸馏与生成模块 — 模拟道教炼丹过程

以"炉火"为驱动，以"药材"(经典文献)为输入，
经过"九转"蒸馏过程，产出"丹丸"(精炼知识成果)。

数学建模:
    炼丹 = 知识蒸馏 = Teacher-Student + 温度缩放
    炉火温度 T 控制蒸馏的"精纯度"：
        T → 0: 硬蒸馏 (保留核心结构)
        T → 1: 软蒸馏 (保留细节分布)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math


class FireType(Enum):
    """炉火类型及其特性"""
    TIAN_HUO = ("tianhuo", 0.3, "天火 — 高温精炼，保留核心结构")
    DI_HUO = ("dihuo", 0.5, "地火 — 中温平衡，兼顾结构与细节")
    REN_HUO = ("renhuo", 0.7, "人火 — 低温慢炼，保留丰富细节")
    SAN_MEI = ("sanmei", 0.15, "三昧真火 — 极致高温，至纯至精")

    def __new__(cls, code, temperature, description):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.temperature = temperature
        obj.description = description
        return obj


@dataclass
class Ingredient:
    """药材 — 一本经典文献的向量表示"""
    name: str
    embedding: Optional[torch.Tensor] = None
    grotto: str = "dong_zhen"
    weight: float = 1.0


@dataclass
class Pill:
    """丹丸 — 知识蒸馏的最终产物"""
    name: str
    ingredients: List[str]
    fire: FireType
    content_embedding: torch.Tensor
    quality_score: float
    grotto: str
    cycles: int = 49  # 默认七七四十九转


class AlchemyFurnace(nn.Module):
    """
    炼丹炉神经网络模块

    结构:
        1. 药材编码器 (Ingredient Encoder)  — 将文本转为嵌入
        2. 九转蒸馏塔 (9-Cycle Distillation Tower) — 多轮知识蒸馏
        3. 炉火温度控制器 (Temperature Controller) — 调节蒸馏强度
        4. 丹丸凝聚器 (Pill Condenser) — 将蒸馏结果凝聚为丹丸
        5. 品质评估器 (Quality Evaluator) — 评估丹丸品质
    """

    # 九转对应的炼丹阶段
    NINE_CYCLES = [
        "一轉·築基", "二轉·煉精", "三轉·化氣",
        "四轉·凝神", "五轉·還虛", "六轉·合道",
        "七轉·出竅", "八轉·飛升", "九轉·歸元",
    ]

    def __init__(
        self,
        input_dim: int = 768,
        hidden_dim: int = 512,
        num_cycles: int = 9,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_cycles = num_cycles

        # 药材编码器
        self.ingredient_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim * 2),
            nn.LayerNorm(hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.LayerNorm(hidden_dim),
        )

        # 九转蒸馏塔 — 使用共享权重的递归模块
        self.distill_cell = nn.GRUCell(hidden_dim, hidden_dim)

        # 每转的"火候"调节
        self.fire_modulators = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 4),
                nn.GELU(),
                nn.Linear(hidden_dim // 4, hidden_dim),
                nn.Sigmoid(),
            )
            for _ in range(num_cycles)
        ])

        # 丹丸凝聚器
        self.condenser = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
        )

        # 品质评估器
        self.quality_evaluator = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 4),
            nn.GELU(),
            nn.Linear(hidden_dim // 4, 1),
            nn.Sigmoid(),
        )

    def forward(
        self,
        ingredients: torch.Tensor,       # [batch, num_ingredients, input_dim]
        fire: FireType = FireType.TIAN_HUO,
        return_history: bool = False,
    ) -> Dict[str, torch.Tensor]:
        """
        炼丹前向传播

        Args:
            ingredients:    药材嵌入张量
            fire:           炉火类型 (控制蒸馏温度)
            return_history: 是否返回每转的中间状态

        Returns:
            包含丹丸嵌入、品质评分、蒸馏历史
        """
        batch_size = ingredients.size(0)
        device = ingredients.device

        # === 1. 药材编码 ===
        # 将多种药材融合为初始"药液"
        encoded = self.ingredient_encoder(ingredients)  # [B, N, hidden]
        elixir = encoded.mean(dim=1)  # [B, hidden]

        # === 2. 九转蒸馏 ===
        temperature = fire.temperature
        history = [] if return_history else None
        hidden = torch.zeros(batch_size, self.hidden_dim, device=device)

        for cycle_idx in range(self.num_cycles):
            # 将当前"药液"送入蒸馏塔
            hidden = self.distill_cell(elixir, hidden)

            # 火候调节 — 模拟每转的火候变化
            modulation = self.fire_modulators[cycle_idx](hidden)
            hidden = hidden * modulation * (1.0 - temperature) + hidden * temperature

            # 添加微小的"炉火噪声"模拟真实炼丹过程的不确定性
            fire_noise = torch.randn_like(hidden) * 0.02 * (1.0 - temperature)
            hidden = hidden + fire_noise

            if return_history:
                history.append({
                    "cycle": cycle_idx + 1,
                    "stage": self.NINE_CYCLES[cycle_idx],
                    "hidden_norm": hidden.norm(dim=-1).mean().item(),
                })

        # === 3. 丹丸凝聚 ===
        pill_embedding = self.condenser(hidden)

        # === 4. 品质评估 ===
        quality = self.quality_evaluator(hidden).squeeze(-1)

        result = {
            "pill_embedding": pill_embedding,
            "quality": quality,
            "final_state": hidden,
        }
        if return_history:
            result["history"] = history

        return result

    def distill_knowledge(
        self,
        source_texts: List[str],
        target_dim: int = 768,
        fire: FireType = FireType.SAN_MEI,
    ) -> Pill:
        """
        高级API：从文本列表中进行知识蒸馏

        Args:
            source_texts: 源文本列表 (经典文献名)
            target_dim:   嵌入维度
            fire:         炉火类型
        """
        # 占位：实际使用时替换为 BGE/RoBERTa 嵌入
        import hashlib
        import random

        embeddings = []
        for text in source_texts:
            seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            rng = random.Random(seed)
            emb = torch.tensor([rng.uniform(-1, 1) for _ in range(target_dim)])
            embeddings.append(emb)

        ingredients = torch.stack(embeddings).unsqueeze(0)  # [1, N, dim]

        with torch.no_grad():
            result = self(ingredients, fire=fire)

        return Pill(
            name=self._generate_pill_name(),
            ingredients=source_texts,
            fire=fire,
            content_embedding=result["pill_embedding"].squeeze(0),
            quality_score=result["quality"].item(),
            grotto=self._determine_grotto(source_texts),
        )

    @staticmethod
    def _generate_pill_name() -> str:
        """生成丹丸名称"""
        import random
        pre = random.choice([
            "太極", "混元", "九轉", "紫府", "金丹",
            "玉液", "玄珠", "大還", "小還", "八卦",
        ])
        suf = random.choice(["丹", "丸", "散", "膏", "液", "符", "寶", "珠"])
        return pre + suf

    @staticmethod
    def _determine_grotto(texts: List[str]) -> str:
        for text in texts:
            if any(k in text for k in ["道", "德", "自然"]):
                return "dong_zhen"
            if any(k in text for k in ["法", "丹", "符"]):
                return "dong_xuan"
            if any(k in text for k in ["神", "仙", "傳"]):
                return "dong_shen"
        return "dong_zhen"


# ===== 自测 =====
if __name__ == "__main__":
    print("=== AlchemyFurnace 自测 ===\n")

    furnace = AlchemyFurnace(input_dim=768, hidden_dim=512)
    furnace.eval()

    # 模拟药材嵌入
    ingredients = torch.randn(1, 3, 768)  # 3种药材

    for fire in FireType:
        with torch.no_grad():
            result = furnace(ingredients, fire=fire)
        print(f"{fire.description}")
        print(f"  品質: {result['quality'].item():.3f}")
        print(f"  丹丸維度: {result['pill_embedding'].shape}")

    # 完整蒸馏
    print("\n--- 蒸馏測試 ---")
    pill = furnace.distill_knowledge(
        ["道德經", "莊子", "悟真篇"],
        target_dim=768,
        fire=FireType.SAN_MEI,
    )
    print(f"  丹名: {pill.name}")
    print(f"  品質: {pill.quality_score:.3f}")
    print(f"  洞: {pill.grotto}")

    print("\n[OK] AlchemyFurnace 自测通过")
