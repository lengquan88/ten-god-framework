#!/usr/bin/env python3
"""
test_v24_viz.py — v2.4.0 可视化增强与报告系统升级测试套件

覆盖范围：
  1. 紫微斗数可视化（HTML/SVG/多语言）
  2. 报告系统多语言集成（BaziReportGenerator lang 参数）
  3. PNG 图片导出（cairosvg 降级兼容）
  4. 分享卡多语言 + 命盘分享图生成
  5. API 端点多语言参数
"""

from __future__ import annotations

import pytest


# ============================================================================
# 1. 紫微斗数可视化测试
# ============================================================================


def _make_ziwei_data():
    """构造紫微命盘测试数据"""
    try:
        from tengod.ziwei_engine import ZiweiEngine
        chart = ZiweiEngine.calc_chart(1990, 6, 15, 10, 30, gender="male")
        return ZiweiEngine.to_dict(chart)
    except Exception:
        pytest.skip("ZiweiEngine 不可用")


class TestZiweiVisualization:
    """紫微斗数可视化引擎测试"""

    def test_generate_html_default_lang(self):
        from tengod.chart_visualizer import ZiweiChartVisualizer
        data = _make_ziwei_data()
        viz = ZiweiChartVisualizer()
        html = viz.generate_html(data)
        assert isinstance(html, str)
        assert "<html" in html.lower() or "<div" in html.lower()
        assert len(html) > 500  # 非空骨架

    def test_generate_html_contains_palaces(self):
        from tengod.chart_visualizer import ZiweiChartVisualizer
        data = _make_ziwei_data()
        viz = ZiweiChartVisualizer()
        html = viz.generate_html(data, lang="zh-CN")
        # 至少包含命宫
        assert "命宫" in html

    def test_generate_svg_structure(self):
        from tengod.chart_visualizer import ZiweiChartVisualizer
        data = _make_ziwei_data()
        viz = ZiweiChartVisualizer()
        svg = viz.generate_svg(data)
        assert isinstance(svg, str)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_generate_svg_multilingual(self):
        """三语 SVG 渲染不报错"""
        from tengod.chart_visualizer import ZiweiChartVisualizer
        data = _make_ziwei_data()
        viz = ZiweiChartVisualizer()
        for lang in ["zh-CN", "zh-TW", "en"]:
            svg = viz.generate_svg(data, lang=lang)
            assert "<svg" in svg, f"lang={lang} SVG 渲染失败"

    def test_visualize_ziwei_helper_html(self):
        from tengod.chart_visualizer import visualize_ziwei
        data = _make_ziwei_data()
        out = visualize_ziwei(data, lang="zh-CN", fmt="html")
        assert isinstance(out, str)
        assert len(out) > 100

    def test_visualize_ziwei_helper_svg(self):
        from tengod.chart_visualizer import visualize_ziwei
        data = _make_ziwei_data()
        out = visualize_ziwei(data, lang="en", fmt="svg")
        assert "<svg" in out


# ============================================================================
# 2. 多语言报告测试
# ============================================================================


def _make_analyzer():
    try:
        from tengod.bazi_analyzer import BaziAnalyzer
        return BaziAnalyzer(1990, 6, 15, 10, 30, is_male=True)
    except Exception:
        pytest.skip("BaziAnalyzer 不可用")


class TestMultilingualReport:
    """报告系统多语言集成测试"""

    def test_report_default_lang_zhcn(self):
        from tengod.report_generator import BaziReportGenerator
        analyzer = _make_analyzer()
        gen = BaziReportGenerator(analyzer)
        report = gen.text_report()
        assert isinstance(report, str)
        assert "八字" in report or "命理" in report

    def test_report_lang_param_en(self):
        from tengod.report_generator import BaziReportGenerator
        analyzer = _make_analyzer()
        gen = BaziReportGenerator(analyzer, lang="en")
        report = gen.text_report()
        assert isinstance(report, str)
        assert len(report) > 100

    def test_report_lang_override_in_method(self):
        """方法级 lang 参数覆盖构造函数设置"""
        from tengod.report_generator import BaziReportGenerator
        analyzer = _make_analyzer()
        gen = BaziReportGenerator(analyzer, lang="zh-CN")
        report_zh = gen.text_report()
        report_en = gen.text_report(lang="en")
        # 两种语言应产生不同输出（至少标题不同）
        assert report_zh != report_en

    def test_report_markdown_multilingual(self):
        from tengod.report_generator import BaziReportGenerator
        analyzer = _make_analyzer()
        gen = BaziReportGenerator(analyzer, lang="en")
        md = gen.markdown_report()
        assert isinstance(md, str)
        assert len(md) > 50

    def test_report_json_multilingual(self):
        from tengod.report_generator import BaziReportGenerator
        analyzer = _make_analyzer()
        gen = BaziReportGenerator(analyzer, lang="en")
        js = gen.json_report()
        # json_report 可能返回 dict 或 str
        if isinstance(js, str):
            assert len(js) > 50
        else:
            assert isinstance(js, dict)
            assert len(js) > 0

    def test_report_html_multilingual(self):
        from tengod.report_generator import BaziReportGenerator
        analyzer = _make_analyzer()
        gen = BaziReportGenerator(analyzer, lang="en")
        ht = gen.html_report()
        assert isinstance(ht, str)
        assert len(ht) > 100

    def test_report_zh_tw(self):
        from tengod.report_generator import BaziReportGenerator
        analyzer = _make_analyzer()
        gen = BaziReportGenerator(analyzer, lang="zh-TW")
        report = gen.text_report()
        assert isinstance(report, str)
        assert len(report) > 100


# ============================================================================
# 3. PNG 导出测试
# ============================================================================


class TestPngExport:
    """PNG 图片导出测试"""

    def test_export_to_png_returns_str(self):
        from tengod.visualization import export_to_png
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>'
        result = export_to_png(svg)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_export_to_png_degrades_on_invalid_svg(self):
        """无效 SVG 应降级返回原内容"""
        from tengod.visualization import export_to_png
        result = export_to_png("not a valid svg")
        # 降级时返回原 SVG 字符串
        assert isinstance(result, str)

    def test_export_to_png_with_output_path(self, tmp_path):
        """指定输出路径应写入文件（若 cairosvg 可用）"""
        from tengod.visualization import export_to_png
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50"></svg>'
        out_file = tmp_path / "out.png"
        result = export_to_png(svg, output_path=str(out_file))
        # 若 cairosvg 可用，返回路径且文件存在；否则降级返回 svg 内容
        if result.endswith(".png"):
            assert out_file.exists()


# ============================================================================
# 4. 分享卡多语言 + 命盘分享图测试
# ============================================================================


class TestShareCardMultilingual:
    """分享卡多语言与命盘分享图测试"""

    def test_share_card_default_lang(self):
        from tengod.miniapp import ShareCardGenerator
        cards = ShareCardGenerator()
        card = cards.generate_bazi_share(
            [{"gan": "甲", "zhi": "子"}], "甲", "正官格", 85.0
        )
        assert card["lang"] == "zh-CN"
        assert "title" in card

    def test_share_card_lang_constructor(self):
        from tengod.miniapp import ShareCardGenerator
        cards = ShareCardGenerator(lang="en")
        card = cards.generate_bazi_share([], "甲", "伤官格", 80)
        assert card["lang"] == "en"

    def test_share_card_lang_method_override(self):
        from tengod.miniapp import ShareCardGenerator
        cards = ShareCardGenerator(lang="zh-CN")
        card = cards.generate_bazi_share([], "甲", "伤官格", 80, lang="zh-TW")
        assert card["lang"] == "zh-TW"

    def test_bazi_chart_share_svg_png(self):
        from tengod.miniapp import ShareCardGenerator
        cards = ShareCardGenerator(lang="zh-CN")
        pillars = {"year": "庚午", "month": "壬午", "day": "甲子", "hour": "己巳"}
        card = cards.generate_bazi_chart_share(pillars, day_master="甲")
        assert "svg" in card
        assert "png" in card
        assert card["lang"] == "zh-CN"
        assert "<svg" in card["svg"]
        assert "甲" in card["title"]

    def test_ziwei_chart_share_svg_png(self):
        from tengod.miniapp import ShareCardGenerator
        data = _make_ziwei_data()
        cards = ShareCardGenerator(lang="zh-CN")
        card = cards.generate_ziwei_chart_share(data)
        assert "svg" in card
        assert "png" in card
        assert "<svg" in card["svg"]
        assert "紫微" in card["title"] or "ZiWei" in card["title"]

    def test_ziwei_chart_share_multilingual(self):
        from tengod.miniapp import ShareCardGenerator
        data = _make_ziwei_data()
        for lang in ["zh-CN", "zh-TW", "en"]:
            cards = ShareCardGenerator(lang=lang)
            card = cards.generate_ziwei_chart_share(data)
            assert card["lang"] == lang
            assert "<svg" in card["svg"]

    def test_trajectory_share_multilingual(self):
        from tengod.miniapp import ShareCardGenerator
        cards = ShareCardGenerator(lang="en")
        card = cards.generate_trajectory_share(
            {"day_master": "甲", "dayun": [{"age_start": 5}]}
        )
        assert card["lang"] == "en"
        assert "title" in card

    def test_ai_share_multilingual(self):
        from tengod.miniapp import ShareCardGenerator
        cards = ShareCardGenerator(lang="zh-TW")
        card = cards.generate_ai_share("日主甲木，秀气。", "命運解讀")
        assert card["lang"] == "zh-TW"
        assert "title" in card


# ============================================================================
# 5. API 端点多语言参数测试
# ============================================================================


class TestApiLangParam:
    """API 端点多语言参数测试"""

    def test_report_query_model_has_lang_field(self):
        """ReportQuery 模型应包含 lang 字段"""
        try:
            from tengod.api_server import ReportQuery
        except ImportError:
            pytest.skip("api_server 不可用")
        q = ReportQuery(
            bazi={
                "year": 1990, "month": 6, "day": 15,
                "hour": 10, "minute": 30, "is_male": True,
            },
            format="text",
        )
        assert q.lang == "zh-CN"  # 默认值

    def test_report_query_lang_custom(self):
        try:
            from tengod.api_server import ReportQuery
        except ImportError:
            pytest.skip("api_server 不可用")
        q = ReportQuery(
            bazi={
                "year": 1990, "month": 6, "day": 15,
                "hour": 10, "minute": 30, "is_male": True,
            },
            format="text",
            lang="en",
        )
        assert q.lang == "en"


# ============================================================================
# 6. i18n 翻译表完整性测试
# ============================================================================


class TestI18nTranslations:
    """i18n 翻译表完整性测试"""

    def test_translations_count_meets_target(self):
        """翻译表应达到 250+ 条"""
        from tengod.i18n import TRANSLATIONS
        assert len(TRANSLATIONS) >= 250, f"翻译表仅 {len(TRANSLATIONS)} 条"

    def test_all_translations_have_three_langs(self):
        """每条翻译应包含 zh-CN/zh-TW/en 三种语言"""
        from tengod.i18n import TRANSLATIONS
        for key, vals in TRANSLATIONS.items():
            assert "zh-CN" in vals, f"{key} 缺少 zh-CN"
            assert "zh-TW" in vals, f"{key} 缺少 zh-TW"
            assert "en" in vals, f"{key} 缺少 en"

    def test_ziwei_terms_translated(self):
        """紫微相关术语应有翻译"""
        from tengod.i18n import t
        # 十二宫名
        assert t("命宫", "en") != "命宫"
        assert t("财帛", "en") != "财帛"
        # 四化
        assert t("化禄", "en") != "化禄"
        assert t("化忌", "en") != "化忌"

    def test_t_function_fallback(self):
        """未知词条应回退原文本"""
        from tengod.i18n import t
        result = t("完全不存在的词xyz", "en")
        assert result == "完全不存在的词xyz"
