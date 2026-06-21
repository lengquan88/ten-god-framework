"""
tengod.fengshui — 阶段二十一 · 玄空飞星风水子模块

导出：
  - XuankongEngine：玄空飞星排盘引擎
  - FlyingStarResult：飞星排盘结果数据类
  - YangzhaiAnalyzer：阳宅分析器
  - compute_fengshui(sitting, facing, year)：便捷函数
  - NINE_STARS / STAR_FORTUNE / STAR_WUXING：九星基础数据
  - get_yun_number / get_yun_name / get_yun_year_range：元运计算
"""

from .xuankong import (
    XuankongEngine,
    FlyingStarResult,
    YangzhaiAnalyzer,
    compute_fengshui,
    NINE_STARS,
    STAR_FORTUNE,
    STAR_WUXING,
    STAR_INFLUENCE,
    EIGHT_DIRECTIONS,
    NINE_PALACES,
    get_yun_number,
    get_yun_name,
    get_yun_year_range,
)

__all__ = [
    "XuankongEngine",
    "FlyingStarResult",
    "YangzhaiAnalyzer",
    "compute_fengshui",
    "NINE_STARS",
    "STAR_FORTUNE",
    "STAR_WUXING",
    "STAR_INFLUENCE",
    "EIGHT_DIRECTIONS",
    "NINE_PALACES",
    "get_yun_number",
    "get_yun_name",
    "get_yun_year_range",
]
