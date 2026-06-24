"""
v2.4 测试套件：可视化增强与报告系统升级
==========================================
覆盖：
- 紫微斗数可视化（HTML/SVG）
- 报告多语言集成
- PNG 导出
- 分享卡多语言
- 全量回归
"""

import json
import pytest
from unittest.mock import MagicMock, patch


# ════════════════════════════════════════
# 1. 紫微斗数可视化测试
# ════════════════════════════════════════

class TestZiweiVisualization:
    """紫微斗数可视化器"""

    @pytest.fixture
    def sample_ziwei_data(self):
        return {
            "input": {"solar": "1990-06-15", "lunar": "庚午年五月廿三",
                       "gender": "male", "year_ganzhi": "庚午", "hour_zhi": "巳"},
            "ming_gong": {"name": "命宫", "zhi": "寅", "index": 0},
            "shen_gong": {"name": "迁移", "zhi": "申", "index": 6},
            "wuxing_ju": "木三局",
            "ming_zhu": "禄存",
            "shen_zhu": "文昌",
            "sihua": {"化禄": "贪狼", "化权": "武曲", "化科": "文曲", "化忌": "巨门"},
            "gongs": [
                {"name": "命宫", "ganzhi": "丙寅", "main_stars": ["紫微", "天机"], "aux_stars": ["文昌", "文曲"], "sihua": ""},
                {"name": "兄弟", "ganzhi": "丁卯", "main_stars": [], "aux_stars": ["天魁"], "sihua": ""},
                {"name": "夫妻", "ganzhi": "戊辰", "main_stars": ["太阳"], "aux_stars": [], "sihua": ""},
                {"name": "子女", "ganzhi": "己巳", "main_stars": ["武曲"], "aux_stars": ["天钺"], "sihua": ""},
                {"name": "财帛", "ganzhi": "庚午", "main_stars": ["天同"], "aux_stars": [], "sihua": ""},
                {"name": "疾厄", "ganzhi": "辛未", "main_stars": ["廉贞"], "aux_stars": ["擎羊"], "sihua": ""},
                {"name": "迁移", "ganzhi": "壬申", "main_stars": ["天府"], "aux_stars": ["禄存"], "sihua": ""},
                {"name": "交友", "ganzhi": "癸酉", "main_stars": ["太阴"], "aux_stars": [], "sihua": ""},
                {"name": "官禄", "ganzhi": "甲戌", "main_stars": ["贪狼"], "aux_stars": [], "sihua": "化禄"},
                {"name": "田宅", "ganzhi": "乙亥", "main_stars": ["巨门"], "aux_stars": ["地空"], "sihua": "化忌"},
                {"name": "福德", "ganzhi": "丙子", "main_stars": ["七杀"], "aux_stars": [], "sihua": ""},
                {"name": "父母", "ganzhi": "丁丑", "main_stars": ["破军"], "aux_stars": ["天马"], "sihua": ""},
            ],
            "daxian": [
                {"gong_name": "命宫", "age_range": "4-13"},
                {"gong_name": "父母", "age_range": "14-23"},
                {"gong_name": "福德", "age_range": "24-33"},
            ],
        }

    def test_generate_html_basic(self, sample_ziwei_data):
        """基础 HTML 生成：包含 12 宫位"""
        from tengod.chart_visualizer import ZiweiChartVisualizer
        viz = ZiweiChartVisualizer()
        html = viz.generate_html(sample_ziwei_data)
        assert "紫微斗数命盘" in html
        assert "命宫" in html
        assert "兄弟" in html
        assert "夫妻" in html
        assert "子女" in html
        assert "财帛" in html
        assert "疾厄" in html
        assert "迁移" in html
        assert "交友" in html
        assert "官禄" in html
        assert "田宅" in html
        assert "福德" in html
        assert "父母" in html

    def test_generate_html_stars(self, sample_ziwei_data):
        """HTML 包含主星和辅星"""
        from tengod.chart_visualizer import ZiweiChartVisualizer
        viz = ZiweiChartVisualizer()
        html = viz.generate_html(sample_ziwei_data)
        assert "紫微" in html
        assert "天机" in html
        assert "文昌" in html
        assert "文曲" in html

    def test_generate_html_sihua(self, sample_ziwei_data):
        """HTML 包含四化星标签"""
        from tengod.chart_visualizer import ZiweiChartVisualizer
        viz = ZiweiChartVisualizer()
        html = viz.generate_html(sample_ziwei_data)
        assert "化禄" in html
        assert "化权" in html
        assert "化科" in html
        assert "化忌" in html

    def test_generate_html_dayun(self, sample_ziwei_data):
        """HTML 包含大运叠盘信息"""
        from tengod.chart_visualizer import ZiweiChartVisualizer
        viz = ZiweiChartVisualizer()
        html = viz.generate_html(sample_ziwei_data)
        assert "4-13" in html
        assert "大限" in html

    def test_generate_html_ming_shen(self, sample_ziwei_data):
        """HTML 标记命宫和身宫"""
        from tengod.chart_visualizer import ZiweiChartVisualizer
        viz = ZiweiChartVisualizer()
        html = viz.generate_html(sample_ziwei_data)
        assert "ming-gong" in html
        assert "shen-gong" in html

    def test_generate_svg_basic(self, sample_ziwei_data):
        """SVG 生成：包含命宫信息"""
        from tengod.chart_visualizer import ZiweiChartVisualizer
        viz = ZiweiChartVisualizer()
        svg = viz.generate_svg(sample_ziwei_data)
        assert '<svg' in svg
        assert '紫微斗数' in svg
        assert '命宫' in svg

    def test_empty_data_svg(self):
        """空数据 SVG 回退"""
        from tengod.chart_visualizer import ZiweiChartVisualizer
        viz = ZiweiChartVisualizer()
        svg = viz.generate_svg({"gongs": []})
        assert '<svg' in svg
        assert 'No data' in svg

    def test_visualize_ziwei_convenience(self, sample_ziwei_data):
        """便捷函数 visualize_ziwei"""
        from tengod.chart_visualizer import visualize_ziwei
        html = visualize_ziwei(sample_ziwei_data)
        assert "紫微斗数" in html

    def test_visualize_ziwei_svg_convenience(self, sample_ziwei_data):
        """便捷函数 visualize_ziwei_svg"""
        from tengod.chart_visualizer import visualize_ziwei_svg
        svg = visualize_ziwei_svg(sample_ziwei_data)
        assert '<svg' in svg


# ════════════════════════════════════════
# 2. 报告多语言集成测试
# ════════════════════════════════════════

class TestReportI18n:
    """报告生成器多语言支持"""

    @pytest.fixture
    def mock_analyzer(self):
        """创建模拟的 BaziAnalyzer"""
        mock = MagicMock()
        mock.year = 1990
        mock.month = 6
        mock.day = 15
        mock.hour = 10
        mock.minute = 0
        mock.is_male = True
        mock.longitude = 116.4
        mock.chart = MagicMock()
        mock.chart.true_hour = 10
        mock.chart.true_minute = 0
        mock.analysis = {
            "pillars": {"year": "庚午", "month": "壬午", "day": "丙午", "hour": "癸巳"},
            "day_master": "丙",
            "wuxing": {"木": 0, "火": 4, "土": 2, "金": 1, "水": 1},
            "wuxing_score": {"木": 0, "火": 80, "土": 30, "金": 20, "水": 15},
            "shigan_count": {"正官": 2, "正印": 1, "比肩": 3, "食神": 1, "正财": 1},
            "shigan_map": {"year_gan": "正官", "month_gan": "正官", "day": "日主", "hour_gan": "正财"},
            "dayuns": [
                {"age": 4, "start_year": 1994, "pillar": "癸未"},
                {"age": 14, "start_year": 2004, "pillar": "甲申"},
            ],
            "liunians": [
                {"year": 2024, "pillar": "甲辰", "gan_shigan": "偏印"},
                {"year": 2025, "pillar": "乙巳", "gan_shigan": "正印"},
            ],
            "conclusion": "火旺之命，宜补水调候。",
        }
        mock._is_male = True
        mock._year = 1990
        mock._month = 6
        mock._day = 15
        mock._hour = 10
        mock._minute = 0
        mock._longitude = 116.4
        mock._chart = mock.chart
        return mock

    def test_zh_cn_report(self, mock_analyzer):
        """简体中文报告：默认语言"""
        from tengod.report_generator import BaziReportGenerator
        gen = BaziReportGenerator(mock_analyzer, lang="zh-CN")
        gen._analysis = mock_analyzer.analysis
        gen._year = 1990
        gen._month = 6
        gen._day = 15
        gen._hour = 10
        gen._minute = 0
        gen._is_male = True
        gen._longitude = 116.4
        gen._chart = mock_analyzer.chart
        report = gen.text_report()
        assert "八字命理综合分析报告" in report
        assert "一、基本信息" in report
        assert "二、四柱分析" in report
        assert "庚午" in report

    def test_en_report(self, mock_analyzer):
        """英文报告：lang=en"""
        from tengod.report_generator import BaziReportGenerator
        gen = BaziReportGenerator(mock_analyzer, lang="en")
        gen._analysis = mock_analyzer.analysis
        gen._year = 1990
        gen._month = 6
        gen._day = 15
        gen._hour = 10
        gen._minute = 0
        gen._is_male = True
        gen._longitude = 116.4
        gen._chart = mock_analyzer.chart
        report = gen.text_report()
        # 英文报告中应包含翻译后的术语
        assert "True Solar" in report or "Day Master" in report or "Ten Gods" in report

    def test_markdown_report_i18n(self, mock_analyzer):
        """Markdown 报告多语言"""
        from tengod.report_generator import BaziReportGenerator
        gen = BaziReportGenerator(mock_analyzer, lang="en")
        gen._analysis = mock_analyzer.analysis
        gen._year = 1990
        gen._month = 6
        gen._day = 15
        gen._hour = 10
        gen._minute = 0
        gen._is_male = True
        gen._longitude = 116.4
        gen._chart = mock_analyzer.chart
        md = gen.markdown_report()
        assert "True Solar" in md or "Day Master" in md or "Ten Gods" in md

    def test_json_report_lang_field(self, mock_analyzer):
        """JSON 报告包含 lang 字段"""
        from tengod.report_generator import BaziReportGenerator
        gen = BaziReportGenerator(mock_analyzer, lang="en")
        gen._analysis = mock_analyzer.analysis
        gen._year = 1990
        gen._month = 6
        gen._day = 15
        gen._hour = 10
        gen._minute = 0
        gen._is_male = True
        gen._longitude = 116.4
        gen._chart = mock_analyzer.chart
        jr = gen.json_report()
        assert jr["meta"]["lang"] == "en"

    def test_html_report_lang(self, mock_analyzer):
        """HTML 报告 lang 属性"""
        from tengod.report_generator import BaziReportGenerator
        gen = BaziReportGenerator(mock_analyzer, lang="en")
        gen._analysis = mock_analyzer.analysis
        gen._year = 1990
        gen._month = 6
        gen._day = 15
        gen._hour = 10
        gen._minute = 0
        gen._is_male = True
        gen._longitude = 116.4
        gen._chart = mock_analyzer.chart
        html = gen.html_report()
        assert 'lang="en"' in html


# ════════════════════════════════════════
# 3. PNG 导出测试
# ════════════════════════════════════════

class TestPNGExport:
    """PNG 导出功能"""

    def test_export_to_png_svg_fallback(self):
        """导出 PNG：cairosvg 未安装时回退 SVG"""
        from tengod.visualization import export_to_png
        svg = '<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg"><text x="10" y="30">test</text></svg>'
        result = export_to_png(svg)
        assert result  # 返回内容不为空

    def test_export_to_png_with_path(self, tmp_path):
        """导出 PNG 到文件路径"""
        from tengod.visualization import export_to_png
        svg = '<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg"><text x="10" y="30">test</text></svg>'
        out = str(tmp_path / "test.png")
        result = export_to_png(svg, out)
        assert result == out or "test" in result


# ════════════════════════════════════════
# 4. 分享卡多语言测试
# ════════════════════════════════════════

class TestShareCardI18n:
    """分享卡多语言支持"""

    def test_bazi_share_zh(self):
        """简体中文分享卡"""
        from tengod.miniapp import ShareCardGenerator
        sc = ShareCardGenerator()
        result = sc.generate_bazi_share(
            pillars=[{"gan": "甲", "zhi": "子"}],
            day_master="丙",
            geju="正官格",
            score=85.0,
            lang="zh-CN",
        )
        assert "命盘" in result["title"]
        assert "日主" in result["title"]

    def test_bazi_share_en(self):
        """英文分享卡"""
        from tengod.miniapp import ShareCardGenerator
        sc = ShareCardGenerator()
        result = sc.generate_bazi_share(
            pillars=[{"gan": "甲", "zhi": "子"}],
            day_master="丙",
            geju="正官格",
            score=85.0,
            lang="en",
        )
        assert "Pattern" in result["description"] or "Chart" in result["title"]

    def test_trajectory_share_zh(self):
        """简体中文轨迹分享"""
        from tengod.miniapp import ShareCardGenerator
        sc = ShareCardGenerator()
        result = sc.generate_trajectory_share(
            {"day_master": "丙", "dayun": [{"age_start": 4}]},
            lang="zh-CN",
        )
        assert "命运" in result["title"]

    def test_ai_share_zh(self):
        """简体中文 AI 分享"""
        from tengod.miniapp import ShareCardGenerator
        sc = ShareCardGenerator()
        result = sc.generate_ai_share(
            "今日运势极佳，宜积极进取。",
            "AI 解读",
            lang="zh-CN",
        )
        assert "AI" in result["title"]


# ════════════════════════════════════════
# 5. 全量回归（快速检查编纂）
# ════════════════════════════════════════

class TestV24Regression:
    """v2.4 全量回归"""

    def test_i18n_engine_import(self):
        """i18n 引擎可导入"""
        from tengod.i18n import get_i18n_engine, t
        assert get_i18n_engine() is not None

    def test_chart_visualizer_import(self):
        """可视化器可导入"""
        from tengod.chart_visualizer import (
            BaziChartVisualizer, ZiweiChartVisualizer,
            visualize_bazi, visualize_ziwei, visualize_ziwei_svg,
        )
        assert BaziChartVisualizer is not None
        assert ZiweiChartVisualizer is not None

    def test_report_generator_import(self):
        """报告生成器可导入"""
        from tengod.report_generator import (
            BaziReportGenerator, ComprehensiveReportGenerator,
            generate_report, generate_html_report,
        )
        assert BaziReportGenerator is not None

    def test_visualization_import(self):
        """可视化模块导出"""
        from tengod.visualization import export_to_png, export_to_html
        assert export_to_png is not None

    def test_miniapp_share_card_i18n(self):
        """分享卡支持 lang 参数"""
        from tengod.miniapp import ShareCardGenerator
        import inspect
        sig = inspect.signature(ShareCardGenerator.generate_bazi_share)
        assert "lang" in sig.parameters