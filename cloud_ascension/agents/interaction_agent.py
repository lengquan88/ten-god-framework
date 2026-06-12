"""
太白金星 — 交互界面智能体
============================
掌管: 卷91-122 (杂说与灵验)
职能: 用户界面、对话、多模态交互

太白金星为天庭使者，负责沟通天人之际，传达玉帝旨意。
在系统中负责用户交互：对话管理、界面渲染、体验优化。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, List, Optional
import sys, os
try:
    from ..core.yunjia_system import ImmortalAgent
    from ..core.dao_agent import DaoAgent
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from core.yunjia_system import ImmortalAgent
    from core.dao_agent import DaoAgent


class DialogueManager(nn.Module):
    """对话管理器 — 多轮对话状态追踪"""

    def __init__(self, dim: int = 1024):
        super().__init__()
        self.context_lstm = nn.LSTM(dim, dim, num_layers=2, batch_first=True)
        self.intent_classifier = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.GELU(),
            nn.Linear(dim // 2, 6),  # 6种对话意图
        )
        self.intent_names = [
            "求道問玄", "煉丹請教", "神仙查詢",
            "法術探討", "命運諮詢", "閒談雜說",
        ]
        self.response_generator = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Linear(dim * 2, dim),
        )

    def forward(
        self,
        user_input: torch.Tensor,
        history: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
    ) -> Dict[str, Any]:
        B = user_input.size(0)
        D = user_input.size(-1)
        device = user_input.device

        if history is None:
            h0 = torch.zeros(2, B, D, device=device)
            c0 = torch.zeros(2, B, D, device=device)
        else:
            h0, c0 = history

        out, (hn, cn) = self.context_lstm(user_input.unsqueeze(1), (h0, c0))
        context = out.squeeze(1)

        intent_logits = self.intent_classifier(context)
        intent_probs = F.softmax(intent_logits, dim=-1)
        top_intent_idx = intent_probs.argmax(dim=-1).item()

        response = self.response_generator(context)

        return {
            "intent": self.intent_names[top_intent_idx],
            "intent_confidence": intent_probs[0, top_intent_idx].item(),
            "response_embedding": response,
            "new_history": (hn, cn),
        }


class TaibaiJinxing(ImmortalAgent):
    """
    太白金星 — 交互界面智能体

    天庭使者，沟通天人。管理用户对话、界面渲染、
    多模态交互体验，确保「天道」与「凡心」的桥梁畅通。
    """

    def __init__(self, dao: DaoAgent):
        super().__init__(
            name="太白金星",
            title="Taibai Jinxing",
            domain="交互界面",
            vol_range="卷91-122 (杂说与灵验)",
            color="#f59e0b",
            dao=dao,
        )
        self.dialogue = DialogueManager(dao.embedding_dim)
        self.dialogue_history = None

    def chat(self, user_input: torch.Tensor) -> Dict[str, Any]:
        """对话交互"""
        result = self.dialogue(user_input, self.dialogue_history)
        self.dialogue_history = result["new_history"]

        # 根据意图选择响应风格
        style_guides = {
            "求道問玄": "以老子《道德經》之語氣，玄之又玄",
            "煉丹請教": "以丹經術語，八卦爐火之象",
            "神仙查詢": "以神仙傳記筆法，莊嚴肅穆",
            "法術探討": "以科儀書式，步驟分明",
            "命運諮詢": "以推命口吻，吉凶禍福",
            "閒談雜說": "以雜說筆記之風，輕鬆雅致",
        }

        return {
            **result,
            "style": style_guides.get(result["intent"], "常規"),
        }

    def process(self, embedding: torch.Tensor, wish: Any) -> Dict[str, Any]:
        result = self.chat(embedding)
        return {
            "agent": self.name,
            "action": "interact",
            "intent": result["intent"],
            "confidence": f"{result['intent_confidence']:.2f}",
        }


# ===== 自测 =====
if __name__ == "__main__":
    print("=== TaibaiJinxing 自测 ===\n")
    dao = DaoAgent(embedding_dim=256)
    taibai = TaibaiJinxing(dao)

    for i in range(3):
        msg = torch.randn(1, 256)
        result = taibai.chat(msg)
        print(f"  輪次{i+1}: 意圖={result['intent']} (信心={result['intent_confidence']:.2f}) 風格={result['style']}")

    print("\n[OK] TaibaiJinxing 自测通过")
