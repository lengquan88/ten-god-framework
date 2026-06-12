"""
真武大帝 — 决策规划智能体
============================
掌管: 卷71-90 (法术与科仪)
职能: 任务规划、行动建议、命运推演

真武大帝镇守北方，踏罡步斗，以七政四馀之法推演。
在系统中负责决策规划、方案评估和行动建议生成。
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


class DivinationEngine(nn.Module):
    """占卜推演引擎 — 基于状态空间的蒙特卡洛推演"""

    def __init__(self, dim: int = 1024, num_scenarios: int = 6):
        super().__init__()
        self.num_scenarios = num_scenarios  # 六爻
        self.state_encoder = nn.Linear(dim, dim)
        self.scenario_generator = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Linear(dim * 2, num_scenarios * dim),
        )
        self.outcome_evaluator = nn.Sequential(
            nn.Linear(dim, dim // 4),
            nn.GELU(),
            nn.Linear(dim // 4, 1),
            nn.Tanh(),  # -1 (凶) to +1 (吉)
        )

    def forward(self, state: torch.Tensor) -> Dict[str, Any]:
        """
        推演六爻 — 生成6种可能的发展路径并评估

        Returns:
            scenarios: 6种推演场景
            auspiciousness: 吉凶评分
            recommendation: 建议
        """
        B, D = state.shape
        encoded = self.state_encoder(state)
        scenarios_raw = self.scenario_generator(encoded)
        scenarios = scenarios_raw.view(B, self.num_scenarios, D)

        auspiciousness = []
        for i in range(self.num_scenarios):
            score = self.outcome_evaluator(scenarios[:, i])
            auspiciousness.append(score)

        scores = torch.stack(auspiciousness, dim=1).squeeze(0).squeeze(-1)  # [6]
        best_idx = scores.argmax().item()

        hexagram_names = [
            "乾·天行健", "坤·地勢坤", "屯·雲雷屯",
            "蒙·山水蒙", "需·水天需", "訟·天水訟",
        ]

        interpretation = [
            "大吉·青龍入宅" if s > 0.5 else
            ("吉·鳳凰來儀" if s > 0 else
             ("平·潛龍勿用" if s > -0.3 else
              ("凶·白虎當道" if s > -0.6 else "大凶·群魔亂舞")))
            for s in scores.tolist()
        ]

        return {
            "hexagrams": [
                {"name": hexagram_names[i], "score": scores[i].item(), "meaning": interpretation[i]}
                for i in range(self.num_scenarios)
            ],
            "best_path": hexagram_names[best_idx],
            "best_score": scores[best_idx].item(),
            "overall_auspiciousness": scores.mean().item(),
        }


class ZhenwuDadi(ImmortalAgent):
    """
    真武大帝 — 决策规划智能体

    镇守北方，踏罡步斗。以六爻推演法为核心，
    评估多种行动路径，输出最优决策建议。
    """

    def __init__(self, dao: DaoAgent):
        super().__init__(
            name="真武大帝",
            title="Zhenwu Dadi",
            domain="决策规划",
            vol_range="卷71-90 (法术与科仪)",
            color="#ef4444",
            dao=dao,
        )
        self.divination = DivinationEngine(dao.embedding_dim)

        # 方案评估器
        self.plan_evaluator = nn.Sequential(
            nn.Linear(dao.embedding_dim, dao.embedding_dim // 2),
            nn.GELU(),
            nn.Linear(dao.embedding_dim // 2, 5),  # 5个评估维度
        )
        self.eval_dimensions = [
            "可行性", "風險度", "效益值",
            "時間成本", "資源需求",
        ]

    def divine(self, state_emb: torch.Tensor) -> Dict[str, Any]:
        """六爻推演"""
        return self.divination(state_emb)

    def evaluate_plan(self, plan_emb: torch.Tensor) -> Dict[str, Any]:
        """评估方案各维度"""
        with torch.no_grad():
            scores = self.plan_evaluator(plan_emb).squeeze(0)
            scores_normalized = torch.sigmoid(scores)

        return {
            "dimensions": [
                {"name": self.eval_dimensions[i], "score": scores_normalized[i].item()}
                for i in range(len(self.eval_dimensions))
            ],
            "overall_score": scores_normalized.mean().item(),
        }

    def process(self, embedding: torch.Tensor, wish: Any) -> Dict[str, Any]:
        result = self.divine(embedding)
        return {
            "agent": self.name,
            "action": "decide",
            "best_path": result["best_path"],
            "auspiciousness": f"{result['overall_auspiciousness']:.2f}",
        }


# ===== 自测 =====
if __name__ == "__main__":
    print("=== ZhenwuDadi 自测 ===\n")
    dao = DaoAgent(embedding_dim=256)
    zhenwu = ZhenwuDadi(dao)

    state = torch.randn(1, 256)
    divination = zhenwu.divine(state)
    print(f"  最佳路徑: {divination['best_path']}")
    print(f"  總體吉凶: {divination['overall_auspiciousness']:.3f}")
    for h in divination["hexagrams"]:
        print(f"    {h['name']}: {h['score']:.3f} ({h['meaning']})")

    print("\n[OK] ZhenwuDadi 自测通过")
