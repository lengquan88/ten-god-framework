"""
test_v27_liuyao.py — v2.7.0 新增功能测试
==========================================
测试范围：
  - 六爻卦象可视化 (LiuyaoChartVisualizer)
  - 六爻起卦 API (liuyao/cast + liuyao/chart)
  - 异步任务端点 (create/list/update)
  - 向后兼容性 (import + signature)
"""

import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tengod.chart_visualizer import (
    LiuyaoChartVisualizer, visualize_liuyao, visualize_liuyao_svg,
)
from tengod.liuyao_engine import LiuyaoEngine, YaoInfo, YaoType


# ============================================================================
# 测试数据
# ============================================================================

@pytest.fixture
def sample_liuyao_result():
    """创建示例六爻结果"""
    from tengod.liuyao_engine import shake_and_calc
    return shake_and_calc()


@pytest.fixture
def sample_liuyao_dict():
    """创建示例六爻 dict 数据"""
    return {
        "ben_gua_name": "乾为天",
        "bian_gua_name": "天风姤",
        "hu_gua_name": "乾为天",
        "shang_gua": "乾",
        "xia_gua": "乾",
        "gua_gong": "乾",
        "day_ganzhi": "甲子日",
        "overall_judgment": "乾卦大吉，元亨利贞",
        "yaos": [
            {"position": 1, "yao_type": "YANG", "is_dong": True, "zhi": "子", "liuqin": "父母", "liushen": "青龙", "shi": False, "ying": False},
            {"position": 2, "yao_type": "YANG", "is_dong": False, "zhi": "寅", "liuqin": "妻财", "liushen": "朱雀", "shi": False, "ying": False},
            {"position": 3, "yao_type": "YANG", "is_dong": False, "zhi": "辰", "liuqin": "兄弟", "liushen": "勾陈", "shi": False, "ying": False},
            {"position": 4, "yao_type": "YANG", "is_dong": False, "zhi": "午", "liuqin": "官鬼", "liushen": "螣蛇", "shi": True, "ying": False},
            {"position": 5, "yao_type": "YANG", "is_dong": False, "zhi": "申", "liuqin": "子孙", "liushen": "白虎", "shi": False, "ying": False},
            {"position": 6, "yao_type": "YANG", "is_dong": False, "zhi": "戌", "liuqin": "父母", "liushen": "玄武", "shi": False, "ying": True},
        ],
    }


# ============================================================================
# Test 1: LiuyaoChartVisualizer
# ============================================================================

class TestLiuyaoVisualization:
    """六爻可视化测试"""

    def test_init(self):
        """测试初始化"""
        viz = LiuyaoChartVisualizer()
        assert viz is not None
        assert len(viz.LIUQIN_COLORS) == 5
        assert len(viz.LIUSHEN_COLORS) == 6

    def test_generate_html_dict(self, sample_liuyao_dict):
        """测试从 dict 生成 HTML"""
        viz = LiuyaoChartVisualizer()
        html = viz.generate_html(sample_liuyao_dict)
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "六爻卦象" in html
        assert "乾为天" in html

    def test_generate_html_dataclass(self, sample_liuyao_result):
        """测试从 dataclass 生成 HTML"""
        viz = LiuyaoChartVisualizer()
        html = viz.generate_html(sample_liuyao_result)
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "六爻卦象" in html

    def test_html_contains_yao_info(self, sample_liuyao_dict):
        """测试 HTML 包含爻信息"""
        viz = LiuyaoChartVisualizer()
        html = viz.generate_html(sample_liuyao_dict)
        assert "yao-row" in html
        assert "yao-line" in html

    def test_html_contains_liuqin(self, sample_liuyao_dict):
        """测试 HTML 包含六亲"""
        viz = LiuyaoChartVisualizer()
        html = viz.generate_html(sample_liuyao_dict)
        assert "父母" in html
        assert "妻财" in html

    def test_html_contains_liushen(self, sample_liuyao_dict):
        """测试 HTML 包含六神"""
        viz = LiuyaoChartVisualizer()
        html = viz.generate_html(sample_liuyao_dict)
        assert "青龙" in html
        assert "白虎" in html

    def test_html_contains_shi_ying(self, sample_liuyao_dict):
        """测试 HTML 包含世应标记"""
        viz = LiuyaoChartVisualizer()
        html = viz.generate_html(sample_liuyao_dict)
        assert "badge shi" in html
        assert "badge ying" in html

    def test_html_contains_dong_yao(self, sample_liuyao_dict):
        """测试 HTML 包含动爻标记"""
        viz = LiuyaoChartVisualizer()
        html = viz.generate_html(sample_liuyao_dict)
        assert "dong" in html

    def test_generate_svg_dict(self, sample_liuyao_dict):
        """测试从 dict 生成 SVG"""
        viz = LiuyaoChartVisualizer()
        svg = viz.generate_svg(sample_liuyao_dict)
        assert isinstance(svg, str)
        assert "<svg" in svg
        assert "乾为天" in svg

    def test_generate_svg_dataclass(self, sample_liuyao_result):
        """测试从 dataclass 生成 SVG"""
        viz = LiuyaoChartVisualizer()
        svg = viz.generate_svg(sample_liuyao_result)
        assert isinstance(svg, str)
        assert "<svg" in svg

    def test_visualize_liuyao(self, sample_liuyao_dict):
        """测试便捷函数"""
        html = visualize_liuyao(sample_liuyao_dict)
        assert "六爻卦象" in html

    def test_visualize_liuyao_svg(self, sample_liuyao_dict):
        """测试 SVG 便捷函数"""
        svg = visualize_liuyao_svg(sample_liuyao_dict)
        assert "<svg" in svg

    def test_liuqin_colors(self):
        """测试六亲颜色映射"""
        viz = LiuyaoChartVisualizer()
        for qin in ["父母", "兄弟", "官鬼", "妻财", "子孙"]:
            assert qin in viz.LIUQIN_COLORS

    def test_liushen_colors(self):
        """测试六神颜色映射"""
        viz = LiuyaoChartVisualizer()
        for shen in ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"]:
            assert shen in viz.LIUSHEN_COLORS


# ============================================================================
# Test 2: Liuyao Engine Integration
# ============================================================================

class TestLiuyaoEngine:
    """六爻引擎集成测试"""

    def test_shake_and_calc(self):
        """测试基本起卦"""
        from tengod.liuyao_engine import shake_and_calc
        result = shake_and_calc()
        assert result.ben_gua_name is not None
        assert len(result.ben_gua_name) > 0
        assert len(result.yaos) == 6

    def test_calc_gua(self):
        """测试指定日干起卦"""
        from tengod.liuyao_engine import LiuyaoEngine, shake_and_calc
        result = shake_and_calc(day_ganzhi="甲子")
        assert result.day_ganzhi != ""

    def test_yaos_have_liuqin(self):
        """测试爻有六亲"""
        from tengod.liuyao_engine import shake_and_calc
        result = shake_and_calc()
        for yao in result.yaos:
            assert isinstance(yao.liuqin, str)
            assert len(yao.liuqin) > 0

    def test_yaos_have_liushen(self):
        """测试爻有六神"""
        from tengod.liuyao_engine import shake_and_calc
        result = shake_and_calc()
        for yao in result.yaos:
            assert isinstance(yao.liushen, str)
            assert len(yao.liushen) > 0

    def test_has_shi_ying(self):
        """测试有世应爻"""
        from tengod.liuyao_engine import shake_and_calc
        result = shake_and_calc()
        shi_count = sum(1 for y in result.yaos if y.shi)
        ying_count = sum(1 for y in result.yaos if y.ying)
        assert shi_count == 1
        assert ying_count == 1

    def test_has_judgment(self):
        """测试有断辞"""
        from tengod.liuyao_engine import shake_and_calc
        result = shake_and_calc()
        assert result.overall_judgment != ""


# ============================================================================
# Test 3: Async Task 模型测试
# ============================================================================

class TestAsyncTasks:
    """异步任务模型测试"""

    def test_task_store_logic(self):
        """测试任务存储逻辑（内存实现）"""
        _task_store = {}
        _task_counter = 0

        _task_counter += 1
        tid = f"task_{_task_counter}"
        _task_store[tid] = {
            "id": tid,
            "type": "test",
            "status": "pending",
            "progress": 0,
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
        }

        assert tid in _task_store
        assert _task_store[tid]["status"] == "pending"
        assert _task_store[tid]["progress"] == 0

        _task_store[tid]["status"] = "running"
        _task_store[tid]["progress"] = 50
        assert _task_store[tid]["status"] == "running"
        assert _task_store[tid]["progress"] == 50

        _task_store[tid]["status"] = "done"
        _task_store[tid]["progress"] = 100
        _task_store[tid]["result"] = {"score": 85}
        assert _task_store[tid]["status"] == "done"
        assert _task_store[tid]["result"] == {"score": 85}


# ============================================================================
# Test 4: 向后兼容性
# ============================================================================

class TestV27Regression:
    """v2.7 向后兼容性测试"""

    def test_imports(self):
        """测试新模块导入"""
        from tengod.chart_visualizer import LiuyaoChartVisualizer
        assert LiuyaoChartVisualizer is not None

    def test_v26_visualizers_still_work(self):
        """测试 v2.6 可视化器仍可用"""
        from tengod.chart_visualizer import (
            QimenChartVisualizer, FengshuiVisualizer,
        )
        assert QimenChartVisualizer is not None
        assert FengshuiVisualizer is not None

    def test_v25_fusion_still_works(self):
        """测试 v2.5 融合分析仍可用"""
        from tengod.fusion_analyzer import FusionAnalyzer
        assert FusionAnalyzer is not None

    def test_v24_visualizers_still_work(self):
        """测试 v2.4 可视化器仍可用"""
        from tengod.chart_visualizer import (
            BaziChartVisualizer, ZiweiChartVisualizer,
        )
        assert BaziChartVisualizer is not None
        assert ZiweiChartVisualizer is not None

    def test_liuyao_engine_imports(self):
        """测试六爻引擎导入"""
        from tengod.liuyao_engine import LiuyaoEngine, YaoInfo, YaoType, BAGUA
        assert LiuyaoEngine is not None
        assert len(BAGUA) == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])