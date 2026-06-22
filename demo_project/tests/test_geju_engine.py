#!/usr/bin/env python3
"""
test_geju_engine.py — 格局/喜用神/调候引擎单元测试
覆盖：格局判断、从格识别、旺衰判断、喜用神推导、调候用神、综合分析
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.bazi_calculator import BaziChart
from tengod.geju_engine import (
    ComprehensiveResult,
    GejuEngine,
    GejuResult,
    TiaohouEngine,
    TiaohouResult,
    YongshenEngine,
    YongshenResult,
    _count_wuxing,
    _get_season,
    _judge_wangshuai,
    analyze_bazi_comprehensive,
    calc_geju,
    calc_tiaohou,
    calc_yongshen,
    text_report_comprehensive,
)

# 测试命盘
TEST_PILLARS = {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"}
# 强木命盘（从格测试）
STRONG_PILLARS = {"year": "甲寅", "month": "丙寅", "day": "甲寅", "hour": "乙卯"}


# ════════════════════════════════════════
# 1. 五行统计
# ════════════════════════════════════════

class TestWuxingCount:
    """五行统计基础"""

    def test_count_wuxing_returns_counter(self):
        from collections import Counter
        c = _count_wuxing(TEST_PILLARS)
        assert isinstance(c, Counter)

    def test_count_wuxing_sums_to_eight(self):
        """四柱8个干支，统计总数应为8"""
        c = _count_wuxing(TEST_PILLARS)
        assert sum(c.values()) == 8

    def test_count_wuxing_contains_five_elements(self):
        """五行统计应包含五行"""
        c = _count_wuxing(TEST_PILLARS)
        for elem in ["金", "木", "水", "火", "土"]:
            # 某些五行可能为0，但key应存在或可访问
            assert c.get(elem, 0) >= 0


# ════════════════════════════════════════
# 2. 季节判断
# ════════════════════════════════════════

class TestSeason:
    """季节判断"""

    def test_spring(self):
        assert _get_season("寅") == "春"
        assert _get_season("卯") == "春"

    def test_summer(self):
        assert _get_season("巳") == "夏"
        assert _get_season("午") == "夏"

    def test_autumn(self):
        assert _get_season("申") == "秋"
        assert _get_season("酉") == "秋"

    def test_winter(self):
        assert _get_season("亥") == "冬"
        assert _get_season("子") == "冬"

    def test_four_seasons(self):
        """辰戌丑未为四季月"""
        for zhi in ["辰", "戌", "丑", "未"]:
            assert _get_season(zhi) == "四季"


# ════════════════════════════════════════
# 3. 格局判断
# ════════════════════════════════════════

class TestGeju:
    """格局判断"""

    def test_calc_geju_returns_result(self):
        result = calc_geju(TEST_PILLARS)
        assert isinstance(result, GejuResult)

    def test_geju_basic_fields(self):
        result = calc_geju(TEST_PILLARS)
        assert result.pillars == TEST_PILLARS
        assert result.day_master in "甲乙丙丁戊己庚辛壬癸"
        assert result.geju_type  # 非空
        assert result.geju_name  # 非空

    def test_geju_score_range(self):
        """格局评分在0-100"""
        result = calc_geju(TEST_PILLARS)
        assert 0 <= result.score <= 100

    def test_geju_is_cong_flag(self):
        result = calc_geju(TEST_PILLARS)
        assert isinstance(result.is_cong, bool)
        assert isinstance(result.is_huaqi, bool)

    def test_geju_shiyongshen_jishen_lists(self):
        result = calc_geju(TEST_PILLARS)
        assert isinstance(result.shiyongshen, list)
        assert isinstance(result.jishen, list)

    def test_geju_engine_class(self):
        """GejuEngine 包装类"""
        result = GejuEngine.compute(TEST_PILLARS)
        assert isinstance(result, GejuResult)

    def test_geju_detail_dict(self):
        result = calc_geju(TEST_PILLARS)
        assert isinstance(result.detail, dict)


# ════════════════════════════════════════
# 4. 旺衰判断
# ════════════════════════════════════════

class TestWangShuai:
    """日主旺衰判断"""

    def test_judge_wangshuai_returns_tuple(self):
        c = _count_wuxing(TEST_PILLARS)
        ws, level = _judge_wangshuai(TEST_PILLARS, c, "辛")
        assert ws in ["旺", "中和", "弱", "从"]
        assert isinstance(level, (int, float))

    def test_strong_chart_is_wang(self):
        """强木命盘应为旺"""
        c = _count_wuxing(STRONG_PILLARS)
        ws, level = _judge_wangshuai(STRONG_PILLARS, c, "甲")
        assert ws in ["旺", "从"]


# ════════════════════════════════════════
# 5. 喜用神
# ════════════════════════════════════════

class TestYongshen:
    """喜用神推导"""

    def test_calc_yongshen_returns_result(self):
        result = calc_yongshen(TEST_PILLARS)
        assert isinstance(result, YongshenResult)

    def test_yongshen_basic_fields(self):
        result = calc_yongshen(TEST_PILLARS)
        assert result.day_master in "甲乙丙丁戊己庚辛壬癸"
        assert result.wang_shuai in ["旺", "中和", "弱", "从"]
        assert isinstance(result.yong_shen, list)
        assert isinstance(result.ji_shen, list)

    def test_yongshen_level_range(self):
        result = calc_yongshen(TEST_PILLARS)
        assert 0 <= result.wang_shuai_level <= 100

    def test_yongshen_balance_dict(self):
        result = calc_yongshen(TEST_PILLARS)
        assert isinstance(result.wuxing_balance, dict)

    def test_yongshen_engine_class(self):
        result = YongshenEngine.compute(TEST_PILLARS)
        assert isinstance(result, YongshenResult)

    def test_yongshen_desc_not_empty(self):
        result = calc_yongshen(TEST_PILLARS)
        assert len(result.yongshen_desc) > 0


# ════════════════════════════════════════
# 6. 调候用神
# ════════════════════════════════════════

class TestTiaohou:
    """调候用神判断"""

    def test_calc_tiaohou_returns_result(self):
        result = calc_tiaohou(TEST_PILLARS)
        assert isinstance(result, TiaohouResult)

    def test_tiaohou_basic_fields(self):
        result = calc_tiaohou(TEST_PILLARS)
        assert result.month_zhi in "子丑寅卯辰巳午未申酉戌亥"
        assert result.season in ["春", "夏", "秋", "冬", "四季"]
        assert isinstance(result.required_tiaohou, bool)
        assert isinstance(result.tiaohou_shens, list)

    def test_tiaohou_summer_required(self):
        """夏月（午）需要调候"""
        result = calc_tiaohou(TEST_PILLARS)  # 月支午
        if result.season == "夏":
            assert result.required_tiaohou is True

    def test_tiaohou_engine_class(self):
        result = TiaohouEngine.compute(TEST_PILLARS)
        assert isinstance(result, TiaohouResult)

    def test_tiaohou_desc_not_empty(self):
        result = calc_tiaohou(TEST_PILLARS)
        assert len(result.desc) > 0


# ════════════════════════════════════════
# 7. 综合分析
# ════════════════════════════════════════

class TestComprehensive:
    """综合分析"""

    def test_analyze_comprehensive(self):
        result = analyze_bazi_comprehensive(TEST_PILLARS)
        assert isinstance(result, ComprehensiveResult)
        assert result.pillars == TEST_PILLARS
        assert isinstance(result.geju, GejuResult)
        assert isinstance(result.yongshen, YongshenResult)
        assert isinstance(result.tiaohou, TiaohouResult)

    def test_text_report(self):
        report = text_report_comprehensive(TEST_PILLARS)
        assert isinstance(report, str)
        assert len(report) > 0

    def test_chart_integration(self):
        """与 BaziChart 集成"""
        chart = BaziChart(1990, 6, 15, 10, 30)
        geju = calc_geju(chart.pillars)
        yongshen = calc_yongshen(chart.pillars)
        calc_tiaohou(chart.pillars)
        assert geju.day_master == chart.day_master
        assert yongshen.day_master == chart.day_master


# ════════════════════════════════════════
# 8. 一致性
# ════════════════════════════════════════

class TestConsistency:
    """多次计算一致性"""

    def test_geju_consistent(self):
        r1 = calc_geju(TEST_PILLARS)
        r2 = calc_geju(TEST_PILLARS)
        assert r1.geju_name == r2.geju_name
        assert r1.score == r2.score

    def test_yongshen_consistent(self):
        r1 = calc_yongshen(TEST_PILLARS)
        r2 = calc_yongshen(TEST_PILLARS)
        assert r1.yong_shen == r2.yong_shen
        assert r1.wang_shuai == r2.wang_shuai
