#!/usr/bin/env python3
"""
test_solar_time.py — 真太阳时计算器单元测试
覆盖：经度修正、均时差、时辰映射、节气查询、五行旺衰量化
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.solar_time import (
    SolarTimeCalculator,
    SolarTimeResult,
    JieqiCalculator,
    WuxingStrengthCalculator,
    calculate_solar_time,
    get_jieqi_info,
    calculate_wuxing_strength,
)


# ════════════════════════════════════════
# 1. 真太阳时计算
# ════════════════════════════════════════

class TestSolarTimeCalculator:
    """真太阳时计算器"""

    def test_default_longitude(self):
        calc = SolarTimeCalculator()
        assert calc.longitude == 120.0
        assert calc.STANDARD_LONGITUDE == 120.0

    def test_custom_longitude(self):
        calc = SolarTimeCalculator(longitude=116.4)  # 北京
        assert calc.longitude == 116.4

    def test_calculate_returns_result(self):
        calc = SolarTimeCalculator(longitude=120.0)
        local = datetime(2026, 6, 22, 12, 0)
        result = calc.calculate(local)
        assert isinstance(result, SolarTimeResult)
        assert result.local_time == local
        assert result.longitude == 120.0

    def test_longitude_correction_east(self):
        """东经度数高于标准经度，时间应增加"""
        calc = SolarTimeCalculator(longitude=130.0)
        local = datetime(2026, 6, 22, 12, 0)
        result = calc.calculate(local)
        # 经度差10度 * 4分钟 = 40分钟（加上均时差）
        assert result.time_correction > 30  # 至少30分钟修正

    def test_longitude_correction_west(self):
        """东经度数低于标准经度，时间应减少"""
        calc = SolarTimeCalculator(longitude=110.0)
        local = datetime(2026, 6, 22, 12, 0)
        result = calc.calculate(local)
        # 经度差-10度 * 4分钟 = -40分钟（加上均时差）
        assert result.time_correction < -30

    def test_standard_longitude_no_correction(self):
        """标准经度下，仅有均时差修正"""
        calc = SolarTimeCalculator(longitude=120.0)
        local = datetime(2026, 6, 22, 12, 0)
        result = calc.calculate(local)
        # 仅均时差，应在 ±20 分钟内
        assert abs(result.time_correction) < 20

    def test_true_hour_minute(self):
        calc = SolarTimeCalculator(longitude=120.0)
        local = datetime(2026, 6, 22, 12, 30)
        result = calc.calculate(local)
        assert 0 <= result.true_hour <= 23
        assert 0 <= result.true_minute <= 59

    def test_equation_of_time_range(self):
        """均时差应在 ±20 分钟范围内"""
        calc = SolarTimeCalculator()
        for day in range(1, 366):
            eot = calc._calculate_equation_of_time(day)
            assert -20 < eot < 20, f"day {day} eot={eot} 超出范围"


# ════════════════════════════════════════
# 2. 时辰映射
# ════════════════════════════════════════

class TestShichenMapping:
    """时辰映射功能"""

    def test_get_shichen_zi(self):
        calc = SolarTimeCalculator()
        assert calc.get_shichen(23) == "子"
        assert calc.get_shichen(0) == "子"

    def test_get_shichen_chou(self):
        calc = SolarTimeCalculator()
        assert calc.get_shichen(1) == "丑"
        assert calc.get_shichen(2) == "丑"

    def test_get_shichen_wu(self):
        calc = SolarTimeCalculator()
        assert calc.get_shichen(11) == "午"
        assert calc.get_shichen(12) == "午"

    def test_get_shichen_all_hours(self):
        """每个小时都应映射到时辰"""
        calc = SolarTimeCalculator()
        for h in range(23):
            shichen = calc.get_shichen(h)
            assert shichen != "未知", f"hour {h} 未映射"

    def test_get_shichen_range_zi(self):
        calc = SolarTimeCalculator()
        start, end = calc.get_shichen_range("子")
        assert start == 23 and end == 1

    def test_get_shichen_range_wu(self):
        calc = SolarTimeCalculator()
        start, end = calc.get_shichen_range("午")
        assert start == 11 and end == 13

    def test_get_shichen_range_unknown(self):
        calc = SolarTimeCalculator()
        start, end = calc.get_shichen_range("未知")
        assert start == 0 and end == 0


# ════════════════════════════════════════
# 3. 节气计算器
# ════════════════════════════════════════

class TestJieqiCalculator:
    """节气计算器"""

    def test_lichun(self):
        calc = JieqiCalculator()
        info = calc.get_jieqi(2026, 2, 4)
        assert info["current"] == "立春"

    def test_before_lichun(self):
        calc = JieqiCalculator()
        info = calc.get_jieqi(2026, 2, 3)
        # 立春前应返回上一节气
        assert info["next"] == "立春"

    def test_is_jieqi_day_true(self):
        calc = JieqiCalculator()
        assert calc.is_jieqi_day(2, 4) is True  # 立春
        assert calc.is_jieqi_day(6, 21) is True  # 夏至
        assert calc.is_jieqi_day(12, 22) is True  # 冬至

    def test_is_jieqi_day_false(self):
        calc = JieqiCalculator()
        assert calc.is_jieqi_day(2, 5) is False
        assert calc.is_jieqi_day(6, 22) is False

    def test_jieqi_data_count(self):
        """24节气数据完整性"""
        calc = JieqiCalculator()
        assert len(calc.JIEQI_DATA) == 24

    def test_get_jieqi_returns_dict(self):
        calc = JieqiCalculator()
        info = calc.get_jieqi(2026, 6, 22)
        assert isinstance(info, dict)
        assert "current" in info
        assert "next" in info
        assert "month" in info
        assert "day" in info


# ════════════════════════════════════════
# 4. 五行旺衰量化
# ════════════════════════════════════════

class TestWuxingStrength:
    """五行旺衰量化计算器"""

    def test_get_season_spring(self):
        calc = WuxingStrengthCalculator()
        assert calc.get_season(1) == "春"
        assert calc.get_season(2) == "春"
        assert calc.get_season(3) == "春"

    def test_get_season_summer(self):
        calc = WuxingStrengthCalculator()
        assert calc.get_season(4) == "夏"
        assert calc.get_season(5) == "夏"
        assert calc.get_season(6) == "夏"

    def test_get_season_autumn(self):
        calc = WuxingStrengthCalculator()
        assert calc.get_season(7) == "秋"
        assert calc.get_season(8) == "秋"
        assert calc.get_season(9) == "秋"

    def test_get_season_winter(self):
        calc = WuxingStrengthCalculator()
        assert calc.get_season(10) == "冬"
        assert calc.get_season(11) == "冬"
        assert calc.get_season(12) == "冬"

    def test_calculate_strength_wood_in_spring(self):
        """春季木旺"""
        calc = WuxingStrengthCalculator()
        result = calc.calculate_strength("木", 3)
        assert result["status"] == "旺"
        assert result["strength"] == 100
        assert result["season"] == "春"

    def test_calculate_strength_fire_in_summer(self):
        """夏季火旺"""
        calc = WuxingStrengthCalculator()
        result = calc.calculate_strength("火", 6)
        assert result["status"] == "旺"
        assert result["strength"] == 100

    def test_calculate_strength_metal_in_autumn(self):
        """秋季金旺"""
        calc = WuxingStrengthCalculator()
        result = calc.calculate_strength("金", 9)
        assert result["status"] == "旺"
        assert result["strength"] == 100

    def test_calculate_strength_water_in_winter(self):
        """冬季水旺"""
        calc = WuxingStrengthCalculator()
        result = calc.calculate_strength("水", 12)
        assert result["status"] == "旺"
        assert result["strength"] == 100

    def test_strength_values(self):
        """旺衰量化值正确"""
        calc = WuxingStrengthCalculator()
        assert calc.STRENGTH_VALUES["旺"] == 100
        assert calc.STRENGTH_VALUES["相"] == 80
        assert calc.STRENGTH_VALUES["休"] == 60
        assert calc.STRENGTH_VALUES["囚"] == 40
        assert calc.STRENGTH_VALUES["死"] == 20

    def test_calculate_all_returns_five(self):
        calc = WuxingStrengthCalculator()
        result = calc.calculate_all(3)
        assert len(result) == 5
        assert "木" in result
        assert "火" in result
        assert "土" in result
        assert "金" in result
        assert "水" in result

    def test_calculate_all_strengths_sum(self):
        """所有五行强度之和应为 100+80+60+40+20=300"""
        calc = WuxingStrengthCalculator()
        result = calc.calculate_all(3)
        total = sum(r["strength"] for r in result.values())
        assert total == 300


# ════════════════════════════════════════
# 5. 便捷函数
# ════════════════════════════════════════

class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_calculate_solar_time(self):
        result = calculate_solar_time(2026, 6, 22, 12, 0, 120.0)
        assert isinstance(result, SolarTimeResult)
        assert result.longitude == 120.0

    def test_get_jieqi_info(self):
        info = get_jieqi_info(2026, 2, 4)
        assert info["current"] == "立春"

    def test_calculate_wuxing_strength(self):
        result = calculate_wuxing_strength(3)
        assert len(result) == 5
        assert result["木"]["status"] == "旺"
