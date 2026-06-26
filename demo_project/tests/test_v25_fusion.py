"""
test_v25_fusion.py — v2.5.0 新增功能测试
==========================================
测试范围：
  - 融合分析引擎 (FusionAnalyzer)
  - 命运轨迹时间线 (TrajectoryTimeline)
  - AI 上下文解读 (contextual + memory + recommendations)
  - 案例对比分析 (CaseComparator)
  - 向后兼容性 (import + signature)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tengod.fusion_analyzer import (
    FusionAnalyzer, FusionResult, CrossValidationResult,
    SystemAnalysis, quick_fusion, SYSTEM_WEIGHTS,
    AGREEMENT_LEVELS, FORTUNE_LEVELS,
)
from tengod.chart_visualizer import TrajectoryTimeline, visualize_trajectory, visualize_trajectory_svg
from tengod.ai_interpreter import (
    generate_personalized_recommendations,
    init_conversation, add_to_conversation,
    get_conversation_history, clear_conversation,
)
from tengod.case_comparator import CaseComparator, quick_compare, SimilarCase, ComparisonResult


# ============================================================================
# 测试数据
# ============================================================================

@pytest.fixture
def sample_bazi_data():
    return {
        "pillars": {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
        "analysis": {
            "day_master": "辛金",
            "wuxing": {"金": 2, "水": 2, "火": 3, "土": 1, "木": 0},
            "shigan_map": {"year_gan": "劫财", "month_gan": "伤官", "day_gan": "日主", "hour_gan": "食神"},
            "yongshen": ["土", "金"],
            "jishen": ["火", "木"],
            "conclusion": "日主辛金，身弱，喜土金",
            "dayuns": [
                {"age": 4, "pillar": "癸未", "start_year": 1994},
                {"age": 14, "pillar": "甲申", "start_year": 2004},
            ],
            "liunians": [
                {"year": 2024, "pillar": "甲辰", "gan_shigan": "偏印", "score": 75},
                {"year": 2025, "pillar": "乙巳", "gan_shigan": "正印", "score": 60},
                {"year": 2026, "pillar": "丙午", "gan_shigan": "正官", "score": 45},
            ],
        },
        "geju": "伤官格",
        "shensha": ["天乙贵人", "文昌"],
    }


@pytest.fixture
def sample_ziwei_data():
    return {
        "ming_gong": {"name": "寅", "main_stars": ["紫微", "天府"], "gong_zhi": "寅"},
        "shen_gong": {"name": "申", "main_stars": [], "gong_zhi": "申"},
        "gongs": [
            {"name": "命宫", "main_stars": ["紫微", "天府"], "zhi": "寅"},
            {"name": "兄弟", "main_stars": ["天机"], "zhi": "卯"},
        ],
        "sihua": {"化禄": "天机", "化权": "紫微", "化科": "天府"},
        "ming_zhu": "紫微",
        "shen_zhu": "天相",
        "daxian": [
            {"age_range": "4-13", "gong_name": "命宫"},
            {"age_range": "14-23", "gong_name": "兄弟"},
        ],
    }


@pytest.fixture
def sample_qimen_data():
    return {
        "pan_type": "时家奇门",
        "men": "开门",
        "star": "天辅",
        "gan": "甲",
        "shen": "值符",
    }


# ============================================================================
# Test 1: FusionAnalyzer
# ============================================================================

class TestFusionAnalyzer:
    """融合分析引擎测试"""

    def test_init(self, sample_bazi_data, sample_ziwei_data, sample_qimen_data):
        """测试初始化"""
        fa = FusionAnalyzer(sample_bazi_data, sample_ziwei_data, sample_qimen_data)
        assert fa._bazi is not None
        assert fa._ziwei is not None
        assert fa._qimen is not None

    def test_init_empty(self):
        """测试空数据初始化"""
        fa = FusionAnalyzer()
        assert fa._bazi == {}
        assert fa._ziwei == {}
        assert fa._qimen == {}

    def test_analyze_bazi(self, sample_bazi_data):
        """测试八字体系分析"""
        fa = FusionAnalyzer(bazi_data=sample_bazi_data)
        result = fa._analyze_bazi()
        assert result.available is True
        assert result.score >= 10
        assert result.score <= 100
        assert len(result.yongshen) > 0
        assert "辛金" in result.summary or "辛" in result.summary

    def test_analyze_ziwei(self, sample_ziwei_data):
        """测试紫微体系分析"""
        fa = FusionAnalyzer(ziwei_data=sample_ziwei_data)
        result = fa._analyze_ziwei()
        assert result.available is True
        assert result.score >= 10
        assert result.score <= 100
        assert "紫微" in result.summary

    def test_analyze_qimen(self, sample_qimen_data):
        """测试奇门体系分析"""
        fa = FusionAnalyzer(qimen_data=sample_qimen_data)
        result = fa._analyze_qimen()
        assert result.available is True
        assert result.score >= 10
        assert result.score <= 100
        assert "开门" in result.summary

    def test_empty_system(self):
        """测试空系统返回不可用"""
        fa = FusionAnalyzer()
        result = fa._analyze_bazi()
        assert result.available is False
        assert result.error is not None

    def test_full_analysis(self, sample_bazi_data, sample_ziwei_data, sample_qimen_data):
        """测试完整三体系分析"""
        fa = FusionAnalyzer(sample_bazi_data, sample_ziwei_data, sample_qimen_data)
        result = fa.analyze()

        assert isinstance(result, FusionResult)
        assert result.overall_score >= 10
        assert result.overall_score <= 100
        assert result.overall_level in ("大吉", "吉", "平", "凶", "大凶")
        assert len(result.systems) == 3
        assert result.cross_validation.agreement_score >= 0
        assert result.cross_validation.confidence > 0
        assert result.fusion_report != ""
        assert result.fusion_summary != ""

    def test_cross_validation(self, sample_bazi_data, sample_ziwei_data, sample_qimen_data):
        """测试交叉验证"""
        fa = FusionAnalyzer(sample_bazi_data, sample_ziwei_data, sample_qimen_data)
        result = fa.analyze()

        cv = result.cross_validation
        assert cv.agreement_score >= 0
        assert cv.level in ("高度一致", "基本一致", "部分一致", "存在分歧", "严重矛盾", "待观察")
        assert 0 <= cv.confidence <= 1.0

    def test_to_dict(self, sample_bazi_data, sample_ziwei_data, sample_qimen_data):
        """测试序列化"""
        fa = FusionAnalyzer(sample_bazi_data, sample_ziwei_data, sample_qimen_data)
        result = fa.analyze()
        d = result.to_dict()
        assert "systems" in d
        assert "cross_validation" in d
        assert "overall_score" in d
        assert "fusion_report" in d

    def test_to_json(self, sample_bazi_data, sample_ziwei_data, sample_qimen_data):
        """测试JSON序列化"""
        fa = FusionAnalyzer(sample_bazi_data, sample_ziwei_data, sample_qimen_data)
        result = fa.analyze()
        json_str = result.to_json()
        assert isinstance(json_str, str)
        assert "overall_score" in json_str

    def test_quick_fusion(self, sample_bazi_data):
        """测试便捷函数"""
        result = quick_fusion(bazi=sample_bazi_data)
        assert isinstance(result, FusionResult)
        assert result.overall_level in ("大吉", "吉", "平", "凶", "大凶")

    def test_weights(self):
        """测试权重和为1"""
        assert abs(sum(SYSTEM_WEIGHTS.values()) - 1.0) < 0.01

    def test_agreement_levels(self):
        """测试一致性等级完整性"""
        assert len(AGREEMENT_LEVELS) == 5
        all_levels = set(AGREEMENT_LEVELS.values())
        assert "高度一致" in all_levels

    def test_fortune_levels(self):
        """测试运势等级完整性"""
        assert len(FORTUNE_LEVELS) == 5
        all_levels = set(FORTUNE_LEVELS.values())
        assert "大吉" in all_levels


# ============================================================================
# Test 2: TrajectoryTimeline
# ============================================================================

class TestTrajectoryTimeline:
    """命运轨迹时间线测试"""

    @pytest.fixture
    def dayuns(self):
        return [
            {"age": 4, "pillar": "癸未", "start_year": 1994},
            {"age": 14, "pillar": "甲申", "start_year": 2004},
        ]

    @pytest.fixture
    def liunians(self):
        return [
            {"year": 2024, "pillar": "甲辰", "gan_shigan": "偏印", "score": 75},
            {"year": 2025, "pillar": "乙巳", "gan_shigan": "正印", "score": 60},
            {"year": 2026, "pillar": "丙午", "gan_shigan": "正官", "score": 45},
        ]

    def test_init(self):
        """测试初始化"""
        tt = TrajectoryTimeline()
        assert tt is not None

    def test_generate_html(self, dayuns, liunians):
        """测试HTML生成"""
        tt = TrajectoryTimeline()
        html = tt.generate_html(dayuns, liunians, birth_year=1990)
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "timeline-container" in html
        assert "命运轨迹" in html

    def test_html_contains_dayun(self, dayuns, liunians):
        """测试HTML包含大运信息"""
        tt = TrajectoryTimeline()
        html = tt.generate_html(dayuns, liunians)
        assert "大运" in html
        assert "癸未" in html

    def test_html_contains_liunian(self, dayuns, liunians):
        """测试HTML包含流年信息"""
        tt = TrajectoryTimeline()
        html = tt.generate_html(dayuns, liunians)
        assert "2024" in html
        assert "甲辰" in html

    def test_html_contains_score_bar(self, dayuns, liunians):
        """测试HTML包含评分柱状图"""
        tt = TrajectoryTimeline()
        html = tt.generate_html(dayuns, liunians)
        assert "score-bar" in html
        assert "流年运势趋势" in html

    def test_generate_svg(self, dayuns, liunians):
        """测试SVG生成"""
        tt = TrajectoryTimeline()
        svg = tt.generate_svg(dayuns, liunians)
        assert isinstance(svg, str)
        assert "<svg" in svg
        assert "命运轨迹" in svg

    def test_empty_data(self):
        """测试空数据"""
        tt = TrajectoryTimeline()
        html = tt.generate_html([], [])
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html

    def test_visualize_trajectory(self, dayuns, liunians):
        """测试便捷函数"""
        html = visualize_trajectory(dayuns, liunians)
        assert "timeline" in html

    def test_visualize_trajectory_svg(self, dayuns, liunians):
        """测试SVG便捷函数"""
        svg = visualize_trajectory_svg(dayuns, liunians)
        assert "<svg" in svg


# ============================================================================
# Test 3: AI Contextual + Memory + Recommendations
# ============================================================================

class TestAIContextual:
    """AI上下文感知测试"""

    def test_generate_recommendations_basic(self):
        """测试基本建议生成"""
        recs = generate_personalized_recommendations(
            yongshen=["土", "金"], jishen=["火", "木"],
            current_fortune="平", user_goal="综合"
        )
        assert isinstance(recs, list)
        assert len(recs) >= 1
        for r in recs:
            assert "category" in r
            assert "title" in r
            assert "detail" in r
            assert "action" in r

    def test_generate_recommendations_good_fortune(self):
        """测试吉运建议"""
        recs = generate_personalized_recommendations(
            yongshen=["水"], jishen=["土"],
            current_fortune="吉", user_goal="事业"
        )
        assert any("积极进取" in r["title"] or "向上" in r["title"] or "事业" in r["category"]
                   for r in recs)

    def test_generate_recommendations_bad_fortune(self):
        """测试凶运建议"""
        recs = generate_personalized_recommendations(
            yongshen=["金"], jishen=["火"],
            current_fortune="凶", user_goal="财运"
        )
        assert any("风险" in r["category"] or "低迷" in r["title"]
                   for r in recs)

    def test_generate_recommendations_goal_wealth(self):
        """测试财运目标建议"""
        recs = generate_personalized_recommendations(
            yongshen=["木"], jishen=["金"],
            current_fortune="平", user_goal="财运"
        )
        assert any("财富" in r["category"] or "财运" in r["title"]
                   for r in recs)

    def test_conversation_memory(self):
        """测试对话记忆"""
        session_id = "test_session_001"
        init_conversation(session_id)

        add_to_conversation(session_id, "user", "我的事业运如何？")
        add_to_conversation(session_id, "assistant", "您的事业运整体向好...")

        history = get_conversation_history(session_id)
        assert "事业运" in history
        assert "向好" in history

        clear_conversation(session_id)
        history_after = get_conversation_history(session_id)
        assert history_after == ""

    def test_conversation_memory_empty(self):
        """测试空对话记忆"""
        history = get_conversation_history("nonexistent_session")
        assert history == ""

    def test_wuxing_advice_completeness(self):
        """测试五行建议库完整性"""
        for wx in ["木", "火", "土", "金", "水"]:
            recs = generate_personalized_recommendations(
                yongshen=[wx], jishen=[], current_fortune="平"
            )
            assert len(recs) >= 1


# ============================================================================
# Test 4: CaseComparator
# ============================================================================

class TestCaseComparator:
    """案例对比分析测试"""

    @pytest.fixture
    def bazi_data(self):
        return {
            "pillars": {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            "analysis": {
                "day_master": "辛金",
                "wuxing": {"金": 2, "水": 2, "火": 3, "土": 1, "木": 0},
            },
        }

    def test_init(self):
        """测试初始化"""
        cc = CaseComparator(use_vector=False)
        assert cc is not None

    def test_find_similar(self, bazi_data):
        """测试相似案例查找"""
        cc = CaseComparator(use_vector=False)
        similar = cc.find_similar(bazi_data)
        assert isinstance(similar, list)
        for case in similar:
            assert isinstance(case, SimilarCase)
            assert 0 <= case.similarity <= 1.0

    def test_compare(self, bazi_data):
        """测试对比报告"""
        cc = CaseComparator(use_vector=False)
        similar = cc.find_similar(bazi_data)
        result = cc.generate_comparison_report(bazi_data, similar)

        assert isinstance(result, ComparisonResult)
        assert result.comparison_report != ""
        assert "相似度统计" in result.comparison_report
        assert result.similarity_stats["count"] == len(similar)

    def test_quick_compare(self, bazi_data):
        """测试快速对比"""
        result = quick_compare(bazi_data)
        assert isinstance(result, ComparisonResult)
        assert result.similarity_stats["count"] >= 0

    def test_empty_similar(self, bazi_data):
        """测试空相似案例"""
        cc = CaseComparator(use_vector=False)
        result = cc.generate_comparison_report(bazi_data, [])
        assert result.similarity_stats["count"] == 0
        assert result.similarity_stats["avg_similarity"] == 0

    def test_similar_case_serialization(self):
        """测试SimilarCase序列化"""
        sc = SimilarCase(
            case_id="test_001",
            similarity=0.85,
            bazi_summary="测试案例",
            tags=["测试"],
            verified=True,
        )
        d = sc.to_dict()
        assert d["case_id"] == "test_001"
        assert d["similarity"] == 0.85
        assert d["verified"] is True


# ============================================================================
# Test 5: 向后兼容性
# ============================================================================

class TestV25Regression:
    """v2.5 向后兼容性测试"""

    def test_imports(self):
        """测试新模块导入"""
        import tengod.fusion_analyzer
        import tengod.case_comparator
        assert tengod.fusion_analyzer.FusionAnalyzer is not None
        assert tengod.case_comparator.CaseComparator is not None

    def test_chart_visualizer_still_works(self):
        """测试现有可视化器仍可用"""
        from tengod.chart_visualizer import (
            BaziChartVisualizer, ZiweiChartVisualizer,
            visualize_bazi, visualize_ziwei, visualize_ziwei_svg,
        )
        assert BaziChartVisualizer is not None
        assert ZiweiChartVisualizer is not None

    def test_ai_interpreter_still_works(self):
        """测试现有AI解释器仍可用"""
        from tengod.ai_interpreter import (
            interpret_bazi, interpret_ziwei, interpret_liuyao,
            build_bazi_context, build_ziwei_context,
        )
        assert interpret_bazi is not None
        assert interpret_ziwei is not None

    def test_report_generator_still_works(self):
        """测试现有报告生成器仍可用"""
        from tengod.report_generator import (
            BaziReportGenerator, ComprehensiveReportGenerator,
            generate_report, generate_html_report,
        )
        assert BaziReportGenerator is not None
        assert ComprehensiveReportGenerator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])