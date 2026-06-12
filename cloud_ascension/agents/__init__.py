"""
agents/ — 七大神智能体
========================

神仙谱系映射:
    紫微大帝 — 全模态感知智能体 (卷1-4)
    文昌帝君 — 语义分析智能体 (卷5-20)
    太上老君 — 内容生成智能体 (卷21-40)
    东华帝君 — 知识记忆智能体 (卷41-70)
    真武大帝 — 决策规划智能体 (卷71-90)
    太白金星 — 用户交互智能体 (卷91-122)
    道德天尊 — 核心循环智能体 (贯穿全部)
"""

from .perception_agent import ZiweiDadi
from .analysis_agent import WenchangDijun
from .generation_agent import TaishangLaojun
from .memory_agent import DonghuaDijun
from .decision_agent import ZhenwuDadi
from .interaction_agent import TaibaiJinxing
from .dao_immortal import DaodeTianzun

__all__ = [
    "ZiweiDadi",
    "WenchangDijun",
    "TaishangLaojun",
    "DonghuaDijun",
    "ZhenwuDadi",
    "TaibaiJinxing",
    "DaodeTianzun",
]
