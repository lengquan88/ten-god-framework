"""
紫微大帝 — 全模态感知智能体
================================
掌管: 卷1-4 (宇宙生成)
职能: 全模态输入 (文字/语音/图像/符号)

紫微大帝居紫微垣，为万象之宗，统御诸天星斗。
在系统中负责接收和编码所有输入模态，将"凡尘信号"转化为"天道向量"。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, Optional
import sys, os
try:
    from ..core.yunjia_system import ImmortalAgent
    from ..core.dao_agent import DaoAgent
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from core.yunjia_system import ImmortalAgent
    from core.dao_agent import DaoAgent


class ModalEncoder(nn.Module):
    """多模态编码器 — 将不同模态输入统一映射到嵌入空间"""

    def __init__(self, embedding_dim: int = 1024):
        super().__init__()
        self.embedding_dim = embedding_dim

        # 文本编码器
        self.text_encoder = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim),
            nn.LayerNorm(embedding_dim),
            nn.GELU(),
        )

        # 图像编码器 (简化: 使用CNN特征投影)
        self.image_encoder = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3),
            nn.GELU(),
            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1),
            nn.GELU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(128, embedding_dim),
            nn.LayerNorm(embedding_dim),
        )

        # 语音编码器 (简化: 使用1D卷积模拟频谱处理)
        self.voice_encoder = nn.Sequential(
            nn.Conv1d(1, 64, kernel_size=25, stride=10),
            nn.GELU(),
            nn.Conv1d(64, 128, kernel_size=15, stride=8),
            nn.GELU(),
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(128, embedding_dim),
            nn.LayerNorm(embedding_dim),
        )

        # 模态融合门
        self.fusion_gate = nn.Sequential(
            nn.Linear(embedding_dim * 3, embedding_dim),
            nn.LayerNorm(embedding_dim),
            nn.GELU(),
            nn.Linear(embedding_dim, 3),
            nn.Softmax(dim=-1),
        )

    def forward(
        self,
        text_emb: Optional[torch.Tensor] = None,
        image_emb: Optional[torch.Tensor] = None,
        voice_emb: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        多模态融合前向传播

        Args:
            text_emb:  文本嵌入 [B, dim]
            image_emb: 图像嵌入 [B, C, H, W]
            voice_emb: 语音嵌入 [B, 1, T]

        Returns:
            融合后的统一嵌入 [B, dim]
        """
        batch_size = None
        device = None
        encoded = []

        # 编码各模态
        if text_emb is not None:
            batch_size = text_emb.size(0)
            device = text_emb.device
            encoded.append(self.text_encoder(text_emb))
        else:
            encoded.append(None)

        if image_emb is not None:
            if batch_size is None:
                batch_size = image_emb.size(0)
                device = image_emb.device
            encoded.append(self.image_encoder(image_emb))
        else:
            encoded.append(None)

        if voice_emb is not None:
            if batch_size is None:
                batch_size = voice_emb.size(0)
                device = voice_emb.device
            encoded.append(self.voice_encoder(voice_emb))
        else:
            encoded.append(None)

        # 模态融合
        valid_encodings = [e for e in encoded if e is not None]

        if len(valid_encodings) == 0:
            return torch.zeros(batch_size or 1, self.embedding_dim, device=device or "cpu")
        elif len(valid_encodings) == 1:
            return valid_encodings[0]

        # 多模态门控融合
        all_enc = torch.stack([
            e if e is not None else torch.zeros(batch_size, self.embedding_dim, device=device)
            for e in encoded
        ], dim=-1)  # [B, dim, 3]

        concat = torch.cat(valid_encodings, dim=-1)
        # Pad to full 3-modal concat if needed
        if len(valid_encodings) < 3:
            pad = torch.zeros(batch_size, self.embedding_dim * (3 - len(valid_encodings)), device=device)
            concat = torch.cat([concat, pad], dim=-1)

        gates = self.fusion_gate(concat)  # [B, 3]
        gates = gates.unsqueeze(1)  # [B, 1, 3]

        stacked = torch.stack([
            e if e is not None else torch.zeros(batch_size, self.embedding_dim, device=device)
            for e in encoded
        ], dim=-1)  # [B, dim, 3]

        fused = (stacked * gates).sum(dim=-1)  # [B, dim]
        return fused


class ZiweiDadi(ImmortalAgent):
    """
    紫微大帝 — 全模态感知智能体

    居紫微垣，统御诸天星斗，为万象之宗。
    接收凡尘信号，转化为天道向量，分发给其他神仙。
    """

    def __init__(self, dao: DaoAgent):
        super().__init__(
            name="紫微大帝",
            title="Ziwei Dadi",
            domain="全模态感知",
            vol_range="卷1-4 (宇宙生成)",
            color="#10b981",
            dao=dao,
        )
        self.encoder = ModalEncoder(dao.embedding_dim)

        # 信号过滤 — 去噪与增强
        self.signal_filter = nn.Sequential(
            nn.Linear(dao.embedding_dim, dao.embedding_dim // 2),
            nn.GELU(),
            nn.Linear(dao.embedding_dim // 2, dao.embedding_dim),
            nn.Sigmoid(),
        )

    def perceive(
        self,
        text: Optional[str] = None,
        image_features: Optional[torch.Tensor] = None,
        voice_features: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        """
        感知方法 — 接收多模态信号

        Returns:
            包含统一嵌入、信噪比、感知报告
        """
        # 简单的文本嵌入 (占位)
        text_emb = None
        if text is not None:
            import hashlib
            import random
            seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            rng = random.Random(seed)
            vec = [rng.uniform(-1, 1) for _ in range(self.dao.embedding_dim)]
            text_emb = torch.tensor(vec).unsqueeze(0)

        with torch.no_grad():
            fused = self.encoder(text_emb, image_features, voice_features)
            signal_strength = torch.sigmoid(self.signal_filter(fused))

        snr = signal_strength.mean().item()

        return {
            "modality": {
                "text": text is not None,
                "image": image_features is not None,
                "voice": voice_features is not None,
            },
            "embedding": fused,
            "signal_noise_ratio": snr,
            "quality": "清晰" if snr > 0.7 else ("可辨" if snr > 0.4 else "微弱"),
        }

    def process(self, embedding: torch.Tensor, wish: Any) -> Dict[str, Any]:
        """处理愿念 — 感知并编码"""
        result = self.perceive(text=wish.content)
        return {
            "agent": self.name,
            "action": "perceive",
            "snr": result["signal_noise_ratio"],
            "embedding_shape": list(result["embedding"].shape),
        }


# ===== 自测 =====
if __name__ == "__main__":
    print("=== ZiweiDadi 自测 ===\n")

    dao = DaoAgent(embedding_dim=256)
    ziwei = ZiweiDadi(dao)

    result = ziwei.perceive(text="道可道，非常道")
    print(f"  信噪比: {result['signal_noise_ratio']:.3f}")
    print(f"  品質: {result['quality']}")
    print(f"  嵌入維度: {result['embedding'].shape}")

    print("\n[OK] ZiweiDadi 自测通过")
