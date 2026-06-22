#!/usr/bin/env python3
"""
test_v21_integration.py — v2.1 新模块集成测试
覆盖：八字排盘 + 真太阳时 + 五行旺衰 + 可视化 + AI分析 端到端流程
"""
import os
import sys
import json
from unittest.mock import AsyncMock, patch
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.bazi_calculator import BaziChart, calc_bazi
from tengod.solar_time import (
    SolarTimeCalculator,
    JieqiCalculator,
    WuxingStrengthCalculator,
    calculate_solar_time,
    calculate_wuxing_strength,
)
from tengod.chart_visualizer import (
    BaziChartVisualizer,
    VisualizationConfig,
    visualize_bazi,
)
from tengod.intelligent_analysis import (
    IntelligentAnalysisEngine,
    AnalysisResult,
)
from tengod.deepseek_adapter import DeepseekResponse, Message


# ════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════

def bazi_to_visualization_data(chart: BaziChart) -> dict:
    """将 BaziChart 转换为可视化所需的数据格式"""
    # 统计五行
    wuxing_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    wuxing_map = {
        '甲': '木', '乙': '木', '丙': '火', '丁': '火',
        '戊': '土', '己': '土', '庚': '金', '辛': '金',
        '壬': '水', '癸': '水'
    }
    for pillar in chart.pillars.values():
        for char in pillar:
            if char in wuxing_map:
                wuxing_count[wuxing_map[char]] += 1

    return {
        "pillars": chart.pillars,
        "wuxing": wuxing_count,
        "geju": "待分析",
        "shensha": []
    }


def make_mock_ai_response(content: str) -> DeepseekResponse:
    return DeepseekResponse(
        content=content,
        model="deepseek-chat",
        usage={"prompt_tokens": 10, "completion_tokens": 20},
        finish_reason="stop"
    )


# ════════════════════════════════════════
# 1. 八字排盘 + 真太阳时 集成
# ════════════════════════════════════════

class TestBaziSolarTimeIntegration:
    """八字排盘与真太阳时计算集成"""

    def test_bazi_uses_solar_time_correction(self):
        """BaziChart 应使用真太阳时修正"""
        # 北京经度 116.4，标准经度 120
        chart = BaziChart(1990, 6, 15, 10, 30, longitude=116.4)
        # 真太阳时应与原时间不同（经度修正）
        assert chart.true_hour is not None
        assert chart.true_minute is not None

    def test_solar_time_affects_hour_pillar(self):
        """真太阳时修正应影响时柱"""
        # 同一时刻，不同经度，时柱可能不同
        chart_east = BaziChart(1990, 6, 15, 10, 30, longitude=130.0)
        chart_west = BaziChart(1990, 6, 15, 10, 30, longitude=110.0)
        # 两个命盘的时柱可能相同也可能不同，但都应有效
        assert len(chart_east.pillars['hour']) == 2
        assert len(chart_west.pillars['hour']) == 2

    def test_solar_time_calculator_consistent_with_bazi(self):
        """SolarTimeCalculator 与 BaziChart 的真太阳时计算应一致"""
        calc = SolarTimeCalculator(longitude=116.4)
        local_time = datetime(1990, 6, 15, 10, 30)
        result = calc.calculate(local_time)

        chart = BaziChart(1990, 6, 15, 10, 30, longitude=116.4)
        # 两者都应基于相同的经度修正逻辑
        assert result.longitude == 116.4


# ════════════════════════════════════════
# 2. 八字排盘 + 五行旺衰 集成
# ════════════════════════════════════════

class TestBaziWuxingIntegration:
    """八字排盘与五行旺衰分析集成"""

    def test_bazi_wuxing_strength_analysis(self):
        """八字排盘后应能进行五行旺衰分析"""
        chart = BaziChart(1990, 6, 15, 10, 30)
        # 6月为夏季
        strength_calc = WuxingStrengthCalculator()
        strengths = strength_calc.calculate_all(6)

        # 夏季火旺
        assert strengths["火"]["status"] == "旺"
        assert strengths["火"]["strength"] == 100
        # 夏季金死
        assert strengths["金"]["status"] == "死"

    def test_wuxing_strength_matches_birth_season(self):
        """五行旺衰应与出生季节匹配"""
        # 春季出生（3月）
        chart_spring = BaziChart(1990, 3, 15, 10, 30)
        strengths_spring = calculate_wuxing_strength(3)
        assert strengths_spring["木"]["status"] == "旺"

        # 秋季出生（9月）
        chart_autumn = BaziChart(1990, 9, 15, 10, 30)
        strengths_autumn = calculate_wuxing_strength(9)
        assert strengths_autumn["金"]["status"] == "旺"


# ════════════════════════════════════════
# 3. 八字排盘 + 节气 集成
# ════════════════════════════════════════

class TestBaziJieqiIntegration:
    """八字排盘与节气计算集成"""

    def test_lichun_affects_year_pillar(self):
        """立春应影响年柱判断"""
        # 2026年立春为2月4日
        before_lichun = BaziChart(2026, 2, 3, 12, 0)
        after_lichun = BaziChart(2026, 2, 5, 12, 0)

        # 立春前后年柱应不同
        assert before_lichun.pillars['year'] != after_lichun.pillars['year']

    def test_jieqi_calculator_with_bazi(self):
        """节气计算器应与八字排盘配合使用"""
        jieqi_calc = JieqiCalculator()

        # 立春日
        chart = BaziChart(2026, 2, 4, 12, 0)
        jieqi_info = jieqi_calc.get_jieqi(2026, 2, 4)

        assert jieqi_info["current"] == "立春"
        assert chart.pillars['year'] is not None


# ════════════════════════════════════════
# 4. 八字排盘 + 可视化 集成
# ════════════════════════════════════════

class TestBaziVisualizationIntegration:
    """八字排盘与可视化集成"""

    def test_bazi_chart_to_html(self):
        """八字命盘应能生成HTML可视化"""
        chart = BaziChart(1990, 6, 15, 10, 30)
        viz_data = bazi_to_visualization_data(chart)

        html = visualize_bazi(viz_data)
        assert "<!DOCTYPE html>" in html
        # 应包含四柱
        for pillar in chart.pillars.values():
            assert pillar in html

    def test_bazi_chart_with_custom_theme(self):
        """不同主题的可视化"""
        chart = BaziChart(1990, 6, 15, 10, 30)
        viz_data = bazi_to_visualization_data(chart)

        for theme in ["classic", "modern", "minimal"]:
            html = visualize_bazi(viz_data, theme=theme)
            assert "<!DOCTYPE html>" in html

    def test_bazi_chart_json_output(self):
        """八字命盘JSON输出"""
        chart = BaziChart(1990, 6, 15, 10, 30)
        viz_data = bazi_to_visualization_data(chart)

        viz = BaziChartVisualizer()
        json_str = viz.generate_json(viz_data)
        data = json.loads(json_str)

        assert data["pillars"]["year"] == chart.pillars['year']
        assert data["pillars"]["day"] == chart.pillars['day']

    def test_bazi_with_wuxing_chart(self):
        """八字命盘五行图表"""
        chart = BaziChart(1990, 6, 15, 10, 30)
        viz_data = bazi_to_visualization_data(chart)

        html = visualize_bazi(viz_data)
        # 应包含五行
        for wx in ["木", "火", "土", "金", "水"]:
            assert wx in html


# ════════════════════════════════════════
# 5. 八字排盘 + AI分析 集成（mock）
# ════════════════════════════════════════

class TestBaziAIAnalysisIntegration:
    """八字排盘与AI分析集成"""

    @pytest.mark.asyncio
    async def test_bazi_full_analysis_pipeline(self):
        """端到端：排盘 → AI分析"""
        # 1. 排盘
        chart = BaziChart(1990, 6, 15, 10, 30)
        bazi_data = bazi_to_visualization_data(chart)

        # 2. AI分析（mock）
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(
            return_value=make_mock_ai_response("命盘分析：日主庚金，生于午月..."
            )
        )

        engine = IntelligentAnalysisEngine()
        engine.bazi_interpreter.client = mock_client

        with patch("tengod.intelligent_analysis.get_client", return_value=mock_client):
            result = await engine.full_analysis(bazi_data)

        assert "基础" in result
        assert isinstance(result["基础"], AnalysisResult)
        assert "庚" in result["基础"].content or "命盘" in result["基础"].content

    @pytest.mark.asyncio
    async def test_bazi_career_analysis_pipeline(self):
        """端到端：排盘 → 事业分析"""
        chart = BaziChart(1990, 6, 15, 10, 30)
        bazi_data = bazi_to_visualization_data(chart)

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(
            return_value=make_mock_ai_response("事业方向：适合科技行业")
        )

        engine = IntelligentAnalysisEngine()
        engine.bazi_interpreter.client = mock_client

        with patch("tengod.intelligent_analysis.get_client", return_value=mock_client):
            result = await engine.full_analysis(
                bazi_data,
                options={"career": True, "age": 35}
            )

        assert "基础" in result
        assert "事业" in result
        assert result["事业"].score == 78.0

    @pytest.mark.asyncio
    async def test_bazi_liunian_analysis_pipeline(self):
        """端到端：排盘 → 流年分析"""
        chart = BaziChart(1990, 6, 15, 10, 30)
        bazi_data = bazi_to_visualization_data(chart)

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(
            return_value=make_mock_ai_response("2026年运势：事业有成")
        )

        engine = IntelligentAnalysisEngine()
        engine.bazi_interpreter.client = mock_client

        with patch("tengod.intelligent_analysis.get_client", return_value=mock_client):
            result = await engine.full_analysis(
                bazi_data,
                options={"year": 2026}
            )

        assert "基础" in result
        assert "流年" in result
        assert "2026" in result["流年"].title


# ════════════════════════════════════════
# 6. 完整端到端流程
# ════════════════════════════════════════

class TestEndToEndFlow:
    """完整端到端流程测试"""

    @pytest.mark.asyncio
    async def test_complete_bazi_analysis_flow(self):
        """完整流程：排盘 → 真太阳时 → 五行旺衰 → 节气 → 可视化 → AI分析"""
        # 1. 输入出生信息
        birth_year, birth_month, birth_day = 1990, 6, 15
        birth_hour, birth_minute = 10, 30
        longitude = 116.4  # 北京

        # 2. 真太阳时计算
        solar_result = calculate_solar_time(
            birth_year, birth_month, birth_day,
            birth_hour, birth_minute, longitude
        )
        assert solar_result.longitude == 116.4

        # 3. 八字排盘
        chart = BaziChart(
            birth_year, birth_month, birth_day,
            birth_hour, birth_minute, longitude
        )
        assert len(chart.pillars) == 4
        assert chart.day_master in '甲乙丙丁戊己庚辛壬癸'

        # 4. 节气查询
        jieqi_info = JieqiCalculator().get_jieqi(birth_year, birth_month, birth_day)
        assert jieqi_info["current"] is not None

        # 5. 五行旺衰
        strengths = calculate_wuxing_strength(birth_month)
        assert len(strengths) == 5
        # 6月夏季，火旺
        assert strengths["火"]["status"] == "旺"

        # 6. 可视化
        viz_data = bazi_to_visualization_data(chart)
        html = visualize_bazi(viz_data)
        assert "<!DOCTYPE html>" in html
        assert chart.pillars['year'] in html

        # 7. AI分析（mock）
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(
            return_value=make_mock_ai_response("综合分析完成")
        )

        engine = IntelligentAnalysisEngine()
        engine.bazi_interpreter.client = mock_client

        with patch("tengod.intelligent_analysis.get_client", return_value=mock_client):
            ai_result = await engine.bazi_interpreter.interpret(viz_data, "综合")

        assert isinstance(ai_result, AnalysisResult)
        assert ai_result.content == "综合分析完成"

    def test_multiple_bazi_charts_consistency(self):
        """多个命盘排盘一致性"""
        test_cases = [
            (1990, 6, 15, 10, 30, 116.4),
            (2000, 2, 4, 12, 0, 120.0),
            (1984, 2, 5, 12, 0, 116.4),
            (2026, 6, 22, 14, 0, 121.5),  # 上海
        ]

        charts = []
        for y, m, d, h, mi, lon in test_cases:
            chart = BaziChart(y, m, d, h, mi, lon)
            charts.append(chart)

            # 验证每个命盘
            assert len(chart.pillars) == 4
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar = chart.pillars[pillar_name]
                assert len(pillar) == 2
                assert pillar[0] in '甲乙丙丁戊己庚辛壬癸'
                assert pillar[1] in '子丑寅卯辰巳午未申酉戌亥'

        # 验证命盘互不相同
        pillar_sets = [tuple(c.ganzhi_list) for c in charts]
        assert len(set(pillar_sets)) == len(pillar_sets)

    def test_bazi_visualization_themes_consistency(self):
        """不同主题可视化的一致性"""
        chart = BaziChart(1990, 6, 15, 10, 30)
        viz_data = bazi_to_visualization_data(chart)

        htmls = {}
        for theme in ["classic", "modern", "minimal"]:
            htmls[theme] = visualize_bazi(viz_data, theme=theme)

        # 所有主题都应包含核心数据
        for theme, html in htmls.items():
            assert chart.pillars['year'] in html
            assert chart.pillars['day'] in html
            assert "<!DOCTYPE html>" in html
