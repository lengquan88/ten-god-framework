#!/usr/bin/env python3
"""
test_chart_visualizer.py — 命盘可视化器单元测试
覆盖：HTML生成、五行图表、格局神煞展示、JSON输出、紫微命盘
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.chart_visualizer import (
    BaziChartVisualizer,
    ZiweiChartVisualizer,
    VisualizationConfig,
    visualize_bazi,
    visualize_ziwei,
)


# ════════════════════════════════════════
# 测试数据
# ════════════════════════════════════════

SAMPLE_BAZI = {
    "pillars": {
        "year": "甲子",
        "month": "丙寅",
        "day": "戊午",
        "hour": "庚申"
    },
    "wuxing": {"木": 2, "火": 1, "土": 1, "金": 1, "水": 3},
    "geju": "正官格",
    "shensha": ["天乙贵人", "文昌", "太极贵人"]
}


# ════════════════════════════════════════
# 1. VisualizationConfig
# ════════════════════════════════════════

class TestVisualizationConfig:
    """可视化配置"""

    def test_default_config(self):
        cfg = VisualizationConfig()
        assert cfg.theme == "classic"
        assert cfg.show_shensha is True
        assert cfg.show_wuxing is True
        assert cfg.show_geju is True
        assert cfg.language == "zh"
        assert cfg.interactive is True

    def test_custom_config(self):
        cfg = VisualizationConfig(
            theme="modern",
            show_shensha=False,
            language="en"
        )
        assert cfg.theme == "modern"
        assert cfg.show_shensha is False
        assert cfg.language == "en"


# ════════════════════════════════════════
# 2. BaziChartVisualizer 八字命盘
# ════════════════════════════════════════

class TestBaziChartVisualizer:
    """八字命盘可视化器"""

    def test_init_default_config(self):
        viz = BaziChartVisualizer()
        assert viz.config is not None
        assert viz.config.theme == "classic"

    def test_init_custom_config(self):
        cfg = VisualizationConfig(theme="modern")
        viz = BaziChartVisualizer(cfg)
        assert viz.config.theme == "modern"

    def test_generate_html_basic_structure(self):
        viz = BaziChartVisualizer()
        html = viz.generate_html(SAMPLE_BAZI)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_generate_html_contains_pillars(self):
        viz = BaziChartVisualizer()
        html = viz.generate_html(SAMPLE_BAZI)
        assert "甲子" in html
        assert "丙寅" in html
        assert "戊午" in html
        assert "庚申" in html

    def test_generate_html_contains_pillar_titles(self):
        viz = BaziChartVisualizer()
        html = viz.generate_html(SAMPLE_BAZI)
        assert "年柱" in html
        assert "月柱" in html
        assert "日柱" in html
        assert "时柱" in html

    def test_generate_html_contains_wuxing(self):
        viz = BaziChartVisualizer()
        html = viz.generate_html(SAMPLE_BAZI)
        assert "木" in html
        assert "火" in html
        assert "土" in html
        assert "金" in html
        assert "水" in html

    def test_generate_html_contains_geju(self):
        viz = BaziChartVisualizer()
        html = viz.generate_html(SAMPLE_BAZI)
        assert "正官格" in html

    def test_generate_html_contains_shensha(self):
        viz = BaziChartVisualizer()
        html = viz.generate_html(SAMPLE_BAZI)
        assert "天乙贵人" in html
        assert "文昌" in html

    def test_generate_html_with_empty_data(self):
        """空数据不应崩溃"""
        viz = BaziChartVisualizer()
        html = viz.generate_html({})
        assert "<!DOCTYPE html>" in html
        assert "--" in html  # 默认占位

    def test_generate_html_hide_wuxing(self):
        cfg = VisualizationConfig(show_wuxing=False)
        viz = BaziChartVisualizer(cfg)
        html = viz.generate_html(SAMPLE_BAZI)
        # 五行图表 div 不应出现（CSS 类定义可存在，但实际渲染的 div 不应存在）
        assert '<div class="wuxing-chart">' not in html
        assert "甲子" not in html.split("wuxing-chart")[0] if "wuxing-chart" in html else True

    def test_generate_html_hide_geju(self):
        cfg = VisualizationConfig(show_geju=False)
        viz = BaziChartVisualizer(cfg)
        html = viz.generate_html(SAMPLE_BAZI)
        assert "格局" not in html

    def test_generate_html_hide_shensha(self):
        cfg = VisualizationConfig(show_shensha=False)
        viz = BaziChartVisualizer(cfg)
        html = viz.generate_html(SAMPLE_BAZI)
        assert "天乙贵人" not in html

    def test_generate_html_contains_title(self):
        viz = BaziChartVisualizer()
        html = viz.generate_html(SAMPLE_BAZI)
        assert "八字命盘" in html
        assert "TenGod" in html

    def test_generate_html_responsive_design(self):
        """响应式设计应包含媒体查询"""
        viz = BaziChartVisualizer()
        html = viz.generate_html(SAMPLE_BAZI)
        assert "@media" in html

    def test_generate_html_interactive(self):
        """交互式应包含 onclick"""
        cfg = VisualizationConfig(interactive=True)
        viz = BaziChartVisualizer(cfg)
        html = viz.generate_html(SAMPLE_BAZI)
        assert "onclick" in html

    def test_generate_wuxing_html(self):
        viz = BaziChartVisualizer()
        wuxing_html = viz._generate_wuxing_html({"木": 2, "火": 1, "土": 1, "金": 1, "水": 3})
        assert "wuxing-chart" in wuxing_html
        assert "木" in wuxing_html

    def test_generate_wuxing_html_empty(self):
        viz = BaziChartVisualizer()
        wuxing_html = viz._generate_wuxing_html({})
        assert "wuxing-chart" in wuxing_html

    def test_generate_geju_html(self):
        viz = BaziChartVisualizer()
        geju_html = viz._generate_geju_html("正官格")
        assert "正官格" in geju_html
        assert "格局" in geju_html

    def test_generate_geju_html_empty(self):
        viz = BaziChartVisualizer()
        geju_html = viz._generate_geju_html("")
        assert "未判断" in geju_html

    def test_generate_shensha_html(self):
        viz = BaziChartVisualizer()
        shensha_html = viz._generate_shensha_html(["天乙贵人", "文昌"])
        assert "天乙贵人" in shensha_html
        assert "文昌" in shensha_html

    def test_generate_shensha_html_empty(self):
        viz = BaziChartVisualizer()
        shensha_html = viz._generate_shensha_html([])
        assert "无特殊神煞" in shensha_html

    def test_generate_json(self):
        viz = BaziChartVisualizer()
        json_str = viz.generate_json(SAMPLE_BAZI)
        data = json.loads(json_str)
        assert data["pillars"]["year"] == "甲子"
        assert data["geju"] == "正官格"

    def test_generate_json_chinese_not_escaped(self):
        """JSON 中文字符不应被转义"""
        viz = BaziChartVisualizer()
        json_str = viz.generate_json(SAMPLE_BAZI)
        assert "甲子" in json_str  # ensure_ascii=False


# ════════════════════════════════════════
# 3. ZiweiChartVisualizer 紫微命盘
# ════════════════════════════════════════

class TestZiweiChartVisualizer:
    """紫微命盘可视化器"""

    def test_generate_html_basic(self):
        viz = ZiweiChartVisualizer()
        html = viz.generate_html({})
        assert "<!DOCTYPE html>" in html
        assert "紫微斗数" in html

    def test_generate_html_contains_grid(self):
        viz = ZiweiChartVisualizer()
        html = viz.generate_html({})
        assert "ziwei-grid" in html


# ════════════════════════════════════════
# 4. 便捷函数
# ════════════════════════════════════════

class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_visualize_bazi_default(self):
        html = visualize_bazi(SAMPLE_BAZI)
        assert "<!DOCTYPE html>" in html
        assert "甲子" in html

    def test_visualize_bazi_modern_theme(self):
        html = visualize_bazi(SAMPLE_BAZI, theme="modern")
        assert "<!DOCTYPE html>" in html

    def test_visualize_ziwei(self):
        html = visualize_ziwei({})
        assert "紫微斗数" in html
