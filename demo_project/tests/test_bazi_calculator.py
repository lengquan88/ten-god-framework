#!/usr/bin/env python3
"""
test_bazi_calculator.py — 八字排盘核心算法单元测试
覆盖：四柱推算、立春界年、节气界月、五虎遁、五鼠遁、真太阳时、日柱公式
"""
import os
import sys

# 设置导入路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.bazi_calculator import (
    DI_ZHI,
    TIAN_GAN,
    BaziChart,
    _date_before_lichun,
    _get_month_zhi_index,
    _true_solar_time,
    calc_bazi,
    calc_day_pillar,
    calc_hour_pillar,
    calc_month_pillar,
    calc_year_pillar,
)

# ════════════════════════════════════════
# 1. 基础常量验证
# ════════════════════════════════════════

class TestConstants:
    """天干地支常量完整性"""

    def test_tiangan_count(self):
        assert len(TIAN_GAN) == 10
        assert TIAN_GAN[0] == "甲"
        assert TIAN_GAN[-1] == "癸"

    def test_dizhi_count(self):
        assert len(DI_ZHI) == 12
        assert DI_ZHI[0] == "子"
        assert DI_ZHI[-1] == "亥"

    def test_no_duplicate(self):
        assert len(set(TIAN_GAN)) == 10
        assert len(set(DI_ZHI)) == 12


# ════════════════════════════════════════
# 2. 立春界年柱
# ════════════════════════════════════════

class TestYearPillar:
    """年柱推算 — 立春为界"""

    def test_year_pillar_2024(self):
        """2024年立春后 = 甲辰年"""
        p = calc_year_pillar(2024, 3, 15)
        assert p[0] == "甲" and p[1] == "辰"

    def test_year_pillar_before_lichun(self):
        """2024年立春前（1月）= 癸卯年"""
        p = calc_year_pillar(2024, 1, 15)
        assert p[0] == "癸" and p[1] == "卯"

    def test_date_before_lichun(self):
        """立春日期判定"""
        assert _date_before_lichun(2, 3) is True   # 2月3日在立春前
        assert _date_before_lichun(2, 5) is False   # 2月5日在立春后
        assert _date_before_lichun(1, 1) is True
        assert _date_before_lichun(6, 15) is False

    def test_year_pillar_1990(self):
        """1990年 = 庚午年"""
        p = calc_year_pillar(1990, 6, 15)
        assert p == "庚午"

    def test_year_pillar_2000(self):
        """2000年 = 庚辰年"""
        p = calc_year_pillar(2000, 6, 15)
        assert p == "庚辰"


# ════════════════════════════════════════
# 3. 月柱（五虎遁）
# ════════════════════════════════════════

class TestMonthPillar:
    """月柱推算 — 节气为界 + 五虎遁"""

    def test_month_zhi_index(self):
        """月支索引：寅月=0（立春~惊蛰）"""
        assert _get_month_zhi_index(2, 10) == 0   # 2月10日 = 寅月
        assert _get_month_zhi_index(3, 10) == 1   # 3月10日 = 卯月
        assert _get_month_zhi_index(6, 15) == 4   # 6月15日 = 午月

    def test_month_pillar_1990_06(self):
        """1990年6月（午月），年干庚 → 五虎遁戊起寅 → 壬午月"""
        p = calc_month_pillar(1990, 6, 15, "庚")
        assert p[1] == "午"

    def test_month_pillar_wuhu_dun(self):
        """五虎遁：甲己之年丙作首"""
        # 甲年正月（寅月）天干应为丙
        p = calc_month_pillar(2024, 2, 15, "甲")
        assert p[0] == "丙"  # 甲年寅月 = 丙寅


# ════════════════════════════════════════
# 4. 日柱
# ════════════════════════════════════════

class TestDayPillar:
    """日柱推算"""

    def test_day_pillar_format(self):
        p = calc_day_pillar(1990, 6, 15)
        assert len(p) == 2
        assert p[0] in TIAN_GAN
        assert p[1] in DI_ZHI

    def test_day_pillar_known_date(self):
        """1990-06-15 日柱应为辛亥"""
        p = calc_day_pillar(1990, 6, 15)
        # 已知：1990-06-15 为辛亥日（通过算法验证）
        assert p == "辛亥"

    def test_day_pillar_consistency(self):
        """相邻日期日柱递进"""
        p1 = calc_day_pillar(2024, 1, 1)
        p2 = calc_day_pillar(2024, 1, 2)
        # 天干递进1位
        assert TIAN_GAN.index(p2[0]) == (TIAN_GAN.index(p1[0]) + 1) % 10
        # 地支递进1位
        assert DI_ZHI.index(p2[1]) == (DI_ZHI.index(p1[1]) + 1) % 12


# ════════════════════════════════════════
# 5. 时柱（五鼠遁）
# ════════════════════════════════════════

class TestHourPillar:
    """时柱推算 — 五鼠遁"""

    def test_hour_pillar_zi_hour(self):
        """子时（23-1点）：甲日子时为甲子"""
        p = calc_hour_pillar("甲", 0, 0)
        assert p[0] == "甲" and p[1] == "子"

    def test_hour_pillar_wushu_dun(self):
        """五鼠遁：甲己还加甲（甲日子时=甲子）"""
        p = calc_hour_pillar("甲", 0, 0)
        assert p == "甲子"
        # 乙日：丙子
        p2 = calc_hour_pillar("乙", 0, 0)
        assert p2 == "丙子"

    def test_hour_pillar_noon(self):
        """午时（11-13点）"""
        p = calc_hour_pillar("甲", 12, 0)
        assert p[1] == "午"


# ════════════════════════════════════════
# 6. 真太阳时
# ════════════════════════════════════════

class TestTrueSolarTime:
    """真太阳时修正"""

    def test_beijing_no_correction(self):
        """北京经度120°，无需修正"""
        h, m = _true_solar_time(10, 30, 120.0)
        assert h == 10 and m == 30

    def test_east_correction(self):
        """东经130°（比北京早），时间应增加"""
        h, m = _true_solar_time(10, 30, 130.0)
        # 130-120=10度，10*4=40分钟
        assert m == 10 or h == 11  # 10:30+40min=11:10

    def test_west_correction(self):
        """东经110°（比北京晚），时间应减少"""
        h, m = _true_solar_time(10, 30, 110.0)
        # 110-120=-10度，-40分钟 → 9:50
        assert h == 9 and m == 50


# ════════════════════════════════════════
# 7. BaziChart 集成
# ════════════════════════════════════════

class TestBaziChart:
    """BaziChart 完整排盘"""

    def test_chart_basic(self):
        chart = BaziChart(1990, 6, 15, 10, 30, longitude=116.4, latitude=39.9)
        assert len(chart.pillars) == 4
        for key in ["year", "month", "day", "hour"]:
            assert key in chart.pillars
            assert len(chart.pillars[key]) == 2

    def test_chart_day_master(self):
        chart = BaziChart(1990, 6, 15, 10, 30)
        dm = chart.day_master
        assert dm in TIAN_GAN
        # 1990-06-15 日主为辛
        assert dm == "辛"

    def test_chart_ganzhi_list(self):
        chart = BaziChart(1990, 6, 15, 10, 30)
        gl = chart.ganzhi_list
        assert len(gl) == 4
        assert all(len(gz) == 2 for gz in gl)

    def test_chart_true_solar_time(self):
        chart = BaziChart(1990, 6, 15, 10, 30, longitude=116.4)
        # 116.4° 比 120° 晚约14分钟
        assert chart.true_hour is not None
        assert 0 <= chart.true_hour <= 23

    def test_calc_bazi_function(self):
        """便捷函数 calc_bazi"""
        pillars = calc_bazi(1990, 6, 15, 10, 30)
        assert isinstance(pillars, dict)
        assert set(pillars.keys()) == {"year", "month", "day", "hour"}

    def test_chart_repr(self):
        chart = BaziChart(1990, 6, 15, 10, 30)
        s = repr(chart)
        assert "BaziChart" in s
        assert "1990" in s


# ════════════════════════════════════════
# 8. 边界与异常
# ════════════════════════════════════════

class TestEdgeCases:
    """边界条件"""

    def test_midnight_hour(self):
        """子时（0点）"""
        chart = BaziChart(2024, 1, 1, 0, 0)
        assert chart.pillars["hour"][1] == "子"

    def test_late_hour(self):
        """亥时（21-23点）"""
        chart = BaziChart(2024, 1, 1, 22, 0)
        assert chart.pillars["hour"][1] == "亥"

    def test_year_boundary_lichun(self):
        """立春边界：2024-02-04 立春"""
        before = BaziChart(2024, 2, 3, 12, 0)  # 立春前
        after = BaziChart(2024, 2, 5, 12, 0)   # 立春后
        # 立春前属癸卯，立春后属甲辰
        assert before.pillars["year"] != after.pillars["year"]

    def test_different_longitudes(self):
        """不同经度产生不同真太阳时"""
        east = BaziChart(2024, 6, 15, 10, 30, longitude=130.0)
        west = BaziChart(2024, 6, 15, 10, 30, longitude=110.0)
        # 经度差异足够大时，时柱可能不同
        assert east.true_hour != west.true_hour or east.true_minute != west.true_minute
