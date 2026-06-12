"""
《云笈七签》122卷 AI全模态架构循环智能体操作界面系统
============================================================

YUNJIA OS v1.0 — 以"道"为底层逻辑，以"循环"为运行法则，以"云笈"为知识载体

三洞 (Three Grottoes):
    洞真 (True Grotto)    — 核心教义/哲学     (卷1-4)
    洞玄 (Mysterious Grotto) — 法术/仪式       (卷5-20)
    洞神 (Spiritual Grotto)  — 神仙/谱系       (卷21-40)

四辅 (Four Supplements):
    太玄 (Supreme Mystery)  — 系统底层
    太平 (Great Peace)      — 交互与界面
    太清 (Supreme Clarity)  — 存储与记忆
    正一 (Right Unity)      — 用户与身份

七大神智能体:
    紫微大帝 — 全模态感知 (卷1-4)
    文昌帝君 — 语义分析推理 (卷5-20)
    太上老君 — 内容生成 (卷21-40)
    东华帝君 — 知识存储检索 (卷41-70)
    真武大帝 — 决策规划 (卷71-90)
    太白金星 — 交互界面 (卷91-122)
    道德天尊 — 核心循环引擎 (贯穿全部)
"""

__version__ = "1.0.0"
__codename__ = "混元"

from .core.dao_agent import DaoAgent
from .core.yunjia_system import YunjiaQiqianSystem
from .core.alchemy import AlchemyFurnace
from .core.star_chart import ZhouTianChart
from .core.mission_board import DuRenJing

__all__ = [
    "DaoAgent",
    "YunjiaQiqianSystem",
    "AlchemyFurnace",
    "ZhouTianChart",
    "DuRenJing",
]
