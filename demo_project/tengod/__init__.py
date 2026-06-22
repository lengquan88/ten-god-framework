"""
TenGod - Chinese Fortune Telling System v2.1
============================================
中华文明数字永生体 · 命理智能分析系统

核心模块：
- 八字排盘 (bazi_calculator)
- 紫微斗数 (ziwei_engine)
- 六爻预测 (liuyao_engine)
- 奇门遁甲 (qimen_engine)
- AI 智能分析 (deepseek_adapter, intelligent_analysis)
- 真太阳时计算 (solar_time)
- 交互式可视化 (chart_visualizer)

版本: 2.1.0
"""

__version__ = "2.1.0"
__author__ = "TenGod Team"

from .core import get_core, create_app

__all__ = [
    "get_core",
    "create_app",
    "__version__",
]
