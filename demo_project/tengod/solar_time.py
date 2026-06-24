"""
真太阳时计算器 v2.1
===================
中华文明数字永生体 · 精确时间计算

功能：
- 真太阳时计算（根据经度调整）
- 节气交接精确时间
- 时辰边界动态计算
"""

import math
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class SolarTimeResult:
    """真太阳时计算结果"""
    local_time: datetime       # 当地标准时间
    solar_time: datetime       # 真太阳时
    longitude: float           # 经度
    time_correction: float     # 时间修正（分钟）
    true_hour: int             # 真太阳时时辰
    true_minute: int           # 真太阳时分钟


class SolarTimeCalculator:
    """真太阳时计算器"""

    # 标准经度（中国使用东八区，标准经度120°）
    STANDARD_LONGITUDE = 120.0

    # 时辰对应表
    SHICHEN_MAP = {
        23: "子", 0: "子",
        1: "丑", 2: "丑",
        3: "寅", 4: "寅",
        5: "卯", 6: "卯",
        7: "辰", 8: "辰",
        9: "巳", 10: "巳",
        11: "午", 12: "午",
        13: "未", 14: "未",
        15: "申", 16: "申",
        17: "酉", 18: "酉",
        19: "戌", 20: "戌",
        21: "亥", 22: "亥"
    }

    def __init__(self, longitude: float = 120.0):
        """
        初始化计算器

        Args:
            longitude: 当地经度（东经度数）
        """
        self.longitude = longitude

    def calculate(self, local_time: datetime) -> SolarTimeResult:
        """
        计算真太阳时

        Args:
            local_time: 当地标准时间

        Returns:
            SolarTimeResult: 计算结果
        """
        # 1. 计算经度修正
        # 每1度经度差 = 4分钟时间差
        longitude_diff = self.longitude - self.STANDARD_LONGITUDE
        time_correction_minutes = longitude_diff * 4

        # 2. 计算均时差（地球公转轨道椭圆导致）
        # 简化计算：使用经验公式
        day_of_year = local_time.timetuple().tm_yday
        equation_of_time = self._calculate_equation_of_time(day_of_year)

        # 3. 总修正
        total_correction = time_correction_minutes + equation_of_time

        # 4. 计算真太阳时
        solar_time = local_time + timedelta(minutes=total_correction)

        # 5. 计算真太阳时时辰
        true_hour = solar_time.hour
        true_minute = solar_time.minute

        return SolarTimeResult(
            local_time=local_time,
            solar_time=solar_time,
            longitude=self.longitude,
            time_correction=total_correction,
            true_hour=true_hour,
            true_minute=true_minute
        )

    def _calculate_equation_of_time(self, day_of_year: int) -> float:
        """
        计算均时差

        Args:
            day_of_year: 年内天数（1-365）

        Returns:
            float: 均时差（分钟）
        """
        # 简化公式（基于经验数据）
        # 最大约±16分钟
        b = 2 * math.pi * (day_of_year - 81) / 365
        eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
        return eot

    def get_shichen(self, hour: int) -> str:
        """
        获取时辰名称

        Args:
            hour: 小时（0-23）

        Returns:
            str: 时辰名称
        """
        return self.SHICHEN_MAP.get(hour, "未知")

    def get_shichen_range(self, shichen: str) -> Tuple[int, int]:
        """
        获取时辰时间范围

        Args:
            shichen: 时辰名称

        Returns:
            Tuple[int, int]: 开始小时，结束小时
        """
        ranges = {
            "子": (23, 1), "丑": (1, 3), "寅": (3, 5),
            "卯": (5, 7), "辰": (7, 9), "巳": (9, 11),
            "午": (11, 13), "未": (13, 15), "申": (15, 17),
            "酉": (17, 19), "戌": (19, 21), "亥": (21, 23)
        }
        return ranges.get(shichen, (0, 0))


class JieqiCalculator:
    """节气计算器"""

    # 二十四节气数据（简化版）
    # 实际应使用天文算法精确计算
    JIEQI_DATA = {
        "立春": (2, 4), "雨水": (2, 19),
        "惊蛰": (3, 6), "春分": (3, 21),
        "清明": (4, 5), "谷雨": (4, 20),
        "立夏": (5, 6), "小满": (5, 21),
        "芒种": (6, 6), "夏至": (6, 21),
        "小暑": (7, 7), "大暑": (7, 23),
        "立秋": (8, 8), "处暑": (8, 23),
        "白露": (9, 8), "秋分": (9, 23),
        "寒露": (10, 8), "霜降": (10, 24),
        "立冬": (11, 8), "小雪": (11, 22),
        "大雪": (12, 7), "冬至": (12, 22),
        "小寒": (1, 6), "大寒": (1, 20)
    }

    def get_jieqi(self, year: int, month: int, day: int) -> Dict[str, Any]:
        """
        获取当前节气信息

        Args:
            year: 年
            month: 月
            day: 日

        Returns:
            Dict: 节气信息
        """
        # 查找最近的节气
        current_jieqi = None
        next_jieqi = None

        for name, (m, d) in self.JIEQI_DATA.items():
            if (month == m and day >= d) or (month > m):
                current_jieqi = name
            elif month == m and day < d:
                next_jieqi = name
                break

        if next_jieqi is None:
            # 跨年处理
            next_jieqi = "立春"

        return {
            "current": current_jieqi,
            "next": next_jieqi,
            "month": month,
            "day": day
        }

    def is_jieqi_day(self, month: int, day: int) -> bool:
        """
        判断是否为节气日

        Args:
            month: 月
            day: 日

        Returns:
            bool: 是否为节气日
        """
        for name, (m, d) in self.JIEQI_DATA.items():
            if month == m and day == d:
                return True
        return False


class WuxingStrengthCalculator:
    """五行旺衰量化计算器"""

    # 五行季节旺衰表
    # 旺: 最强, 相: 次强, 休: 中等, 囚: 较弱, 死: 最弱
    SEASON_WUXING = {
        "春": {"木": "旺", "火": "相", "水": "休", "金": "囚", "土": "死"},
        "夏": {"火": "旺", "土": "相", "木": "休", "水": "囚", "金": "死"},
        "秋": {"金": "旺", "水": "相", "土": "休", "火": "囚", "木": "死"},
        "冬": {"水": "旺", "木": "相", "金": "休", "土": "囚", "火": "死"},
        "四季": {"土": "旺", "金": "相", "火": "休", "木": "囚", "水": "死"}
    }

    # 旺衰量化值
    STRENGTH_VALUES = {
        "旺": 100, "相": 80, "休": 60, "囚": 40, "死": 20
    }

    def get_season(self, month: int) -> str:
        """
        获取季节

        Args:
            month: 月份（1-12）

        Returns:
            str: 季节名称
        """
        if month in [1, 2, 3]:
            return "春"
        elif month in [4, 5, 6]:
            return "夏"
        elif month in [7, 8, 9]:
            return "秋"
        elif month in [10, 11, 12]:
            return "冬"
        return "四季"

    def calculate_strength(self, wuxing: str, month: int) -> Dict[str, Any]:
        """
        计算五行旺衰强度

        Args:
            wuxing: 五行名称
            month: 月份

        Returns:
            Dict: 强度信息
        """
        season = self.get_season(month)
        status = self.SEASON_WUXING.get(season, {}).get(wuxing, "休")
        strength = self.STRENGTH_VALUES.get(status, 60)

        return {
            "wuxing": wuxing,
            "season": season,
            "status": status,
            "strength": strength
        }

    def calculate_all(self, month: int) -> Dict[str, Dict[str, Any]]:
        """
        计算所有五行旺衰

        Args:
            month: 月份

        Returns:
            Dict: 所有五行强度
        """
        result = {}
        for wuxing in ["木", "火", "土", "金", "水"]:
            result[wuxing] = self.calculate_strength(wuxing, month)
        return result


# ── 便捷函数 ──────────────────────────────────────────────────────────────
def calculate_solar_time(
    year: int, month: int, day: int,
    hour: int, minute: int,
    longitude: float = 120.0
) -> SolarTimeResult:
    """
    计算真太阳时（便捷函数）

    Args:
        year: 年
        month: 月
        day: 日
        hour: 时
        minute: 分
        longitude: 经度

    Returns:
        SolarTimeResult: 计算结果
    """
    calc = SolarTimeCalculator(longitude)
    local_time = datetime(year, month, day, hour, minute)
    return calc.calculate(local_time)


def get_jieqi_info(year: int, month: int, day: int) -> Dict[str, Any]:
    """
    获取节气信息（便捷函数）
    """
    calc = JieqiCalculator()
    return calc.get_jieqi(year, month, day)


def calculate_wuxing_strength(month: int) -> Dict[str, Dict[str, Any]]:
    """
    计算五行旺衰（便捷函数）
    """
    calc = WuxingStrengthCalculator()
    return calc.calculate_all(month)


__all__ = [
    "SolarTimeCalculator",
    "SolarTimeResult",
    "JieqiCalculator",
    "WuxingStrengthCalculator",
    "calculate_solar_time",
    "get_jieqi_info",
    "calculate_wuxing_strength",
]