#!/usr/bin/env python3
"""
test_shensha_engine.py — 神煞推算引擎单元测试
覆盖：四柱神煞推算、分类统计、结果合并、文本报告
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.bazi_calculator import BaziChart
from tengod.shensha_engine import (
    ShenshaCategory,
    ShenshaEngine,
    ShenshaResult,
    calc_all_shensha,
)

# 标准测试命盘：1990-06-15 10:30 北京时间
TEST_PILLARS = {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"}


# ════════════════════════════════════════
# 1. 基础推算
# ════════════════════════════════════════

class TestShenshaBasic:
    """神煞基础推算"""

    def test_calc_all_shensha_returns_result(self):
        result = calc_all_shensha(TEST_PILLARS)
        assert isinstance(result, ShenshaResult)

    def test_pillars_preserved(self):
        result = calc_all_shensha(TEST_PILLARS)
        assert result.pillars == TEST_PILLARS

    def test_four_pillars_all_computed(self):
        """四柱神煞均被推算"""
        result = calc_all_shensha(TEST_PILLARS)
        assert isinstance(result.year_shens, dict)
        assert isinstance(result.month_shens, dict)
        assert isinstance(result.day_shens, dict)
        assert isinstance(result.hour_shens, dict)

    def test_shensha_engine_class(self):
        """ShenshaEngine 包装类"""
        result = ShenshaEngine.compute(TEST_PILLARS)
        assert isinstance(result, ShenshaResult)
        assert result.pillars == TEST_PILLARS


# ════════════════════════════════════════
# 2. 神煞内容验证
# ════════════════════════════════════════

class TestShenshaContent:
    """神煞内容结构验证"""

    def test_shensha_info_structure(self):
        """每个神煞信息结构完整"""
        result = calc_all_shensha(TEST_PILLARS)
        all_s = result.all_shensha
        for name, info in all_s.items():
            assert "name" in info, f"{name} 缺少 name 字段"
            assert "cat" in info, f"{name} 缺少 cat 字段"
            assert "pillar" in info, f"{name} 缺少 pillar 字段"
            assert "desc" in info, f"{name} 缺少 desc 字段"

    def test_shensha_category_valid(self):
        """神煞分类合法"""
        valid_cats = {c.value for c in ShenshaCategory}
        result = calc_all_shensha(TEST_PILLARS)
        for name, info in result.all_shensha.items():
            assert info["cat"] in valid_cats, f"{name} 分类非法: {info['cat']}"

    def test_shensha_pillar_label(self):
        """神煞柱标识合法"""
        valid_pillars = {"年柱", "月柱", "日柱", "时柱", "年", "月", "日", "时"}
        result = calc_all_shensha(TEST_PILLARS)
        for name, info in result.all_shensha.items():
            # 柱标识应包含柱名
            assert any(p in info["pillar"] for p in valid_pillars) or info["pillar"] == ""


# ════════════════════════════════════════
# 3. 摘要与统计
# ════════════════════════════════════════

class TestShenshaSummary:
    """神煞摘要统计"""

    def test_summary_structure(self):
        result = calc_all_shensha(TEST_PILLARS)
        s = result.summary
        assert "total" in s
        assert "by_category" in s
        assert "top_jixiong" in s

    def test_summary_total_matches(self):
        """摘要总数与实际神煞数一致"""
        result = calc_all_shensha(TEST_PILLARS)
        s = result.summary
        assert s["total"] == len(result.all_shensha)

    def test_summary_by_category_sums(self):
        """分类统计总和等于总数"""
        result = calc_all_shensha(TEST_PILLARS)
        s = result.summary
        total_by_cat = sum(s["by_category"].values())
        assert total_by_cat == s["total"]

    def test_summary_top_jixiong_is_list(self):
        result = calc_all_shensha(TEST_PILLARS)
        s = result.summary
        assert isinstance(s["top_jixiong"], list)


# ════════════════════════════════════════
# 4. 文本报告
# ════════════════════════════════════════

class TestShenshaReport:
    """文本报告生成"""

    def test_text_report_not_empty(self):
        result = calc_all_shensha(TEST_PILLARS)
        report = result.text_report()
        assert isinstance(report, str)
        assert len(report) > 0

    def test_text_report_contains_header(self):
        result = calc_all_shensha(TEST_PILLARS)
        report = result.text_report()
        assert "神煞" in report

    def test_text_report_contains_total(self):
        result = calc_all_shensha(TEST_PILLARS)
        report = result.text_report()
        assert "总计" in report


# ════════════════════════════════════════
# 5. 不同命盘对比
# ════════════════════════════════════════

class TestShenshaDifferentCharts:
    """不同命盘神煞差异"""

    def test_different_charts_different_shensha(self):
        """不同命盘应有不同神煞组合"""
        pillars1 = {"year": "甲子", "month": "丙寅", "day": "甲午", "hour": "甲子"}
        pillars2 = {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"}
        r1 = calc_all_shensha(pillars1)
        r2 = calc_all_shensha(pillars2)
        # 神煞集合应有差异
        assert set(r1.all_shensha.keys()) != set(r2.all_shensha.keys()) or \
               r1.all_shensha != r2.all_shensha

    def test_chart_integration(self):
        """与 BaziChart 集成"""
        chart = BaziChart(1990, 6, 15, 10, 30)
        result = calc_all_shensha(chart.pillars)
        assert result.pillars == chart.pillars
        assert len(result.all_shensha) > 0

    def test_multiple_dates_consistency(self):
        """多次推算同一命盘结果一致"""
        r1 = calc_all_shensha(TEST_PILLARS)
        r2 = calc_all_shensha(TEST_PILLARS)
        assert r1.all_shensha == r2.all_shensha
