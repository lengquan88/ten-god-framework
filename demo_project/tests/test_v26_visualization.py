"""
test_v26_visualization.py — v2.6.0 新增功能测试
================================================
测试范围：
  - 奇门遁甲可视化 (QimenChartVisualizer)
  - 风水可视化 (FengshuiVisualizer)
  - 引擎缓存 (cached_engine / EngineCacheStats)
  - 向后兼容性 (import + signature)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tengod.chart_visualizer import (
    QimenChartVisualizer, FengshuiVisualizer,
    visualize_qimen, visualize_qimen_svg,
    visualize_fengshui, visualize_fengshui_svg,
)
from tengod.cache_manager import (
    EngineCacheStats, cached_engine, cached_bazi, cached_ziwei,
    cached_qimen, cached_fengshui, cached_fusion,
    get_engine_cache_stats, ENGINE_TTL,
    get_cache_manager,
)


# ============================================================================
# 测试数据
# ============================================================================

@pytest.fixture
def sample_qimen_data():
    return {
        "chart": {
            "yin_yang": "阳",
            "ju_num": 1,
            "sizhu": {"year": "甲辰", "month": "丙寅", "day": "戊戌", "hour": "壬子"},
            "xun_shou": "甲午",
            "zhi_fu": "天蓬",
            "zhi_shi": "休门",
            "gongs": {
                "1": {"name": "坎", "di_gan": "戊", "tian_gan": "甲", "men": "休", "xing": "天蓬", "shen": "值符", "wuxing": "水"},
                "2": {"name": "坤", "di_gan": "己", "tian_gan": "乙", "men": "死", "xing": "天芮", "shen": "塍蛇", "wuxing": "土"},
                "3": {"name": "震", "di_gan": "庚", "tian_gan": "丙", "men": "伤", "xing": "天冲", "shen": "太阴", "wuxing": "木"},
                "4": {"name": "巽", "di_gan": "辛", "tian_gan": "丁", "men": "杜", "xing": "天辅", "shen": "六合", "wuxing": "木"},
                "5": {"name": "中", "di_gan": "戊", "tian_gan": "戊", "men": "中", "xing": "天禽", "shen": "值符", "wuxing": "土"},
                "6": {"name": "乾", "di_gan": "壬", "tian_gan": "己", "men": "开", "xing": "天心", "shen": "白虎", "wuxing": "金"},
                "7": {"name": "兑", "di_gan": "癸", "tian_gan": "庚", "men": "惊", "xing": "天柱", "shen": "玄武", "wuxing": "金"},
                "8": {"name": "艮", "di_gan": "乙", "tian_gan": "辛", "men": "生", "xing": "天任", "shen": "九地", "wuxing": "土"},
                "9": {"name": "离", "di_gan": "丙", "tian_gan": "壬", "men": "景", "xing": "天英", "shen": "九天", "wuxing": "火"},
            },
        }
    }


@pytest.fixture
def sample_fengshui_data():
    return {
        "yun": 9,
        "yun_name": "九运 (2024-2043)",
        "direction": "子山午向",
        "yun_pan": {1: 9, 2: 4, 3: 3, 4: 8, 5: 5, 6: 6, 7: 7, 8: 2, 9: 1},
        "shan_pan": {1: 5, 2: 1, 3: 3, 4: 7, 5: 9, 6: 2, 7: 4, 8: 6, 9: 8},
        "xiang_pan": {1: 1, 2: 6, 3: 8, 4: 4, 5: 9, 6: 7, 7: 3, 8: 2, 9: 5},
        "liunian_pan": {1: 8, 2: 5, 3: 4, 4: 9, 5: 1, 6: 6, 7: 7, 8: 3, 9: 2},
        "judgments": [
            "中宫一白到，旺丁旺财",
            "离宫二黑到，需防病符",
            "坎宫八白到，正财位",
        ],
    }


# ============================================================================
# Test 1: QimenChartVisualizer
# ============================================================================

class TestQimenVisualization:
    """奇门遁甲可视化测试"""

    def test_init(self):
        """测试初始化"""
        viz = QimenChartVisualizer()
        assert viz is not None
        assert len(viz.GONG_LAYOUT) == 9
        assert len(viz.MEN_COLORS) >= 8

    def test_generate_html(self, sample_qimen_data):
        """测试HTML生成"""
        viz = QimenChartVisualizer()
        html = viz.generate_html(sample_qimen_data)
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "奇门遁甲" in html
        assert "qimen-grid" in html

    def test_html_contains_gongs(self, sample_qimen_data):
        """测试HTML包含九宫信息"""
        viz = QimenChartVisualizer()
        html = viz.generate_html(sample_qimen_data)
        assert "坎" in html
        assert "休" in html
        assert "天蓬" in html
        assert "值符" in html

    def test_html_contains_men_colors(self, sample_qimen_data):
        """测试HTML包含八门颜色映射"""
        viz = QimenChartVisualizer()
        html = viz.generate_html(sample_qimen_data)
        assert "gong-men" in html

    def test_generate_svg(self, sample_qimen_data):
        """测试SVG生成"""
        viz = QimenChartVisualizer()
        svg = viz.generate_svg(sample_qimen_data)
        assert isinstance(svg, str)
        assert "<svg" in svg
        assert "奇门遁甲" in svg

    def test_visualize_qimen(self, sample_qimen_data):
        """测试便捷函数"""
        html = visualize_qimen(sample_qimen_data)
        assert "qimen-grid" in html

    def test_visualize_qimen_svg(self, sample_qimen_data):
        """测试SVG便捷函数"""
        svg = visualize_qimen_svg(sample_qimen_data)
        assert "<svg" in svg

    def test_empty_data(self):
        """测试空数据"""
        viz = QimenChartVisualizer()
        html = viz.generate_html({"chart": {"gongs": {}}})
        assert "<!DOCTYPE html>" in html


# ============================================================================
# Test 2: FengshuiVisualizer
# ============================================================================

class TestFengshuiVisualization:
    """风水可视化测试"""

    def test_init(self):
        """测试初始化"""
        viz = FengshuiVisualizer()
        assert viz is not None
        assert len(viz.STAR_NAMES) == 9
        assert len(viz.STAR_COLORS) == 9

    def test_generate_html(self, sample_fengshui_data):
        """测试HTML生成"""
        viz = FengshuiVisualizer()
        html = viz.generate_html(sample_fengshui_data)
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "玄空飞星" in html
        assert "fs-grid" in html

    def test_html_contains_stars(self, sample_fengshui_data):
        """测试HTML包含九星信息"""
        viz = FengshuiVisualizer()
        html = viz.generate_html(sample_fengshui_data)
        assert "一白" in html or "八白" in html or "九紫" in html

    def test_html_contains_judgments(self, sample_fengshui_data):
        """测试HTML包含风水断语"""
        viz = FengshuiVisualizer()
        html = viz.generate_html(sample_fengshui_data)
        assert "旺丁旺财" in html or "风水断语" in html

    def test_html_contains_direction(self, sample_fengshui_data):
        """测试HTML包含山向信息"""
        viz = FengshuiVisualizer()
        html = viz.generate_html(sample_fengshui_data)
        assert "子山午向" in html

    def test_generate_svg(self, sample_fengshui_data):
        """测试SVG生成"""
        viz = FengshuiVisualizer()
        svg = viz.generate_svg(sample_fengshui_data)
        assert isinstance(svg, str)
        assert "<svg" in svg
        assert "玄空飞星" in svg

    def test_visualize_fengshui(self, sample_fengshui_data):
        """测试便捷函数"""
        html = visualize_fengshui(sample_fengshui_data)
        assert "fs-grid" in html

    def test_visualize_fengshui_svg(self, sample_fengshui_data):
        """测试SVG便捷函数"""
        svg = visualize_fengshui_svg(sample_fengshui_data)
        assert "<svg" in svg

    def test_empty_data(self):
        """测试空数据"""
        viz = FengshuiVisualizer()
        html = viz.generate_html({})
        assert "<!DOCTYPE html>" in html


# ============================================================================
# Test 3: Engine Cache
# ============================================================================

class TestEngineCache:
    """引擎缓存测试"""

    def test_engine_ttl_defaults(self):
        """测试引擎TTL默认值"""
        assert ENGINE_TTL["bazi"] == 86400
        assert ENGINE_TTL["ziwei"] == 86400
        assert ENGINE_TTL["qimen"] == 3600
        assert ENGINE_TTL["fengshui"] == 3600
        assert ENGINE_TTL["fusion"] == 1800
        assert ENGINE_TTL["report"] == 600

    def test_cache_stats_init(self):
        """测试缓存统计初始化"""
        stats = EngineCacheStats()
        s = stats.get_stats()
        assert isinstance(s, dict)
        assert s == {}

    def test_cache_stats_record(self):
        """测试缓存统计记录"""
        stats = EngineCacheStats()
        stats.record_hit("bazi")
        stats.record_hit("bazi")
        stats.record_miss("bazi")
        s = stats.get_stats()
        assert s["bazi"]["hits"] == 2
        assert s["bazi"]["misses"] == 1
        assert s["bazi"]["total"] == 3
        assert s["bazi"]["hit_rate"] == pytest.approx(0.667, abs=0.001)

    def test_cache_stats_reset(self):
        """测试缓存统计重置"""
        stats = EngineCacheStats()
        stats.record_hit("bazi")
        stats.reset()
        s = stats.get_stats()
        assert s == {}

    def test_cached_engine_decorator(self):
        """测试引擎缓存装饰器"""
        call_count = [0]

        @cached_engine("bazi", ttl=60)
        def calc(x):
            call_count[0] += 1
            return {"result": x * x}

        r1 = calc(5)
        r2 = calc(5)  # 缓存命中
        r3 = calc(3)

        assert r1 == {"result": 25}
        assert r2 == {"result": 25}
        assert r3 == {"result": 9}
        assert call_count[0] == 2  # 5调一次，3调一次

    def test_cached_bazi_decorator(self):
        """测试八字缓存装饰器"""
        @cached_bazi(ttl=60)
        def calc_bazi(date):
            return {"pillar": date}

        r = calc_bazi("2000-01-01")
        assert r == {"pillar": "2000-01-01"}

    def test_cached_ziwei_decorator(self):
        """测试紫微缓存装饰器"""
        @cached_ziwei(ttl=60)
        def calc_ziwei(date):
            return {"ziwei": date}

        r = calc_ziwei("2000-01-01")
        assert r == {"ziwei": "2000-01-01"}

    def test_cached_qimen_decorator(self):
        """测试奇门缓存装饰器"""
        @cached_qimen(ttl=60)
        def calc_qimen(date):
            return {"qimen": date}

        r = calc_qimen("2000-01-01")
        assert r == {"qimen": "2000-01-01"}

    def test_get_engine_cache_stats(self):
        """测试全局缓存统计"""
        stats = get_engine_cache_stats()
        assert isinstance(stats, dict)


# ============================================================================
# Test 4: 向后兼容性
# ============================================================================

class TestV26Regression:
    """v2.6 向后兼容性测试"""

    def test_imports(self):
        """测试新模块导入"""
        from tengod.chart_visualizer import QimenChartVisualizer, FengshuiVisualizer
        from tengod.cache_manager import cached_engine, get_engine_cache_stats
        assert QimenChartVisualizer is not None
        assert FengshuiVisualizer is not None
        assert cached_engine is not None
        assert get_engine_cache_stats is not None

    def test_v25_visualizers_still_work(self):
        """测试 v2.5 可视化器仍可用"""
        from tengod.chart_visualizer import (
            BaziChartVisualizer, ZiweiChartVisualizer, TrajectoryTimeline,
        )
        assert BaziChartVisualizer is not None
        assert ZiweiChartVisualizer is not None
        assert TrajectoryTimeline is not None

    def test_v25_fusion_still_works(self):
        """测试 v2.5 融合分析仍可用"""
        from tengod.fusion_analyzer import FusionAnalyzer, quick_fusion
        assert FusionAnalyzer is not None
        assert quick_fusion is not None

    def test_cache_manager_still_works(self):
        """测试现有缓存管理器仍可用"""
        cm = get_cache_manager()
        assert cm is not None
        assert cm.health_check()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])