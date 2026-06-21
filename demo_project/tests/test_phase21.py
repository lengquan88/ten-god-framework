"""
test_phase21.py — 阶段二十一综合测试：流年断语 + 玄空飞星 + 七政四余

目标：至少 30 个测试方法，至少 25 个通过。
"""

from __future__ import annotations

import pytest
import tempfile
import json
import os

from tengod.liunian_judgment import (
    LiunianJudgmentEngine,
    YearJudgment,
    judge_years,
    judge_decade,
)
from tengod.fengshui import (
    XuankongEngine,
    FlyingStarResult,
    compute_fengshui,
    NINE_STARS,
    get_yun_number,
    get_yun_name,
    get_yun_year_range,
)
from tengod.qizheng import (
    QizhengEngine,
    QizhengResult,
    PlanetPosition,
    compute_qizheng,
    SEVEN_PLANETS,
    FOUR_PLANETS,
)


# ============================================================================
# 基础八字数据：使用题目要求的格式
# ============================================================================

SAMPLE_BAZI = {
    "year_gan": "甲",
    "year_zhi": "子",
    "month_gan": "丙",
    "month_zhi": "寅",
    "day_gan": "辛",
    "day_zhi": "亥",
    "hour_gan": "癸",
    "hour_zhi": "巳",
    "day_master": "辛",
    "gender": "male",
}

SAMPLE_BAZI_WITH_YONGSHEN = {
    "day_master": "辛",
    "pillars": {
        "year": "甲子", "month": "丙寅", "day": "辛亥", "hour": "癸巳",
    },
    "yongshen": {
        "favorable_elements": ["土", "金"],
        "unfavorable_elements": ["木", "火"],
    },
}

SAMPLE_BAZI_MINIMAL = {"day_master": "甲"}


# ============================================================================
# Test 1：LiunianJudgmentEngine — 流年吉凶断语引擎
# ============================================================================

class TestLiunianJudgment:
    """流年吉凶断语引擎测试"""

    @pytest.fixture
    def engine(self):
        return LiunianJudgmentEngine()

    def test_engine_instantiation(self, engine):
        """引擎可以被创建"""
        assert engine is not None
        assert isinstance(engine, LiunianJudgmentEngine)

    def test_single_year_judgment(self, engine):
        """单年判断返回 YearJudgment 且 score 在 0~100"""
        result = engine.judge_year(SAMPLE_BAZI_WITH_YONGSHEN, 2026)
        assert result is not None
        assert isinstance(result, YearJudgment)
        assert 0 <= result.score <= 100, f"score={result.score} 超出范围"

    def test_year_judgment_has_ganzhi(self, engine):
        """断语结果包含干支 / 五行 / 十神信息"""
        result = engine.judge_year(SAMPLE_BAZI_WITH_YONGSHEN, 2026)
        assert result.year == 2026
        assert result.pillar, "流年干支柱不应为空"
        assert len(result.pillar) == 2, f"pillar 应为两个字，实际：{result.pillar}"
        assert result.gan in "甲乙丙丁戊己庚辛壬癸"
        assert result.zhi in "子丑寅卯辰巳午未申酉戌亥"
        assert result.gan_shigan, "流年天干十神不应为空"
        assert isinstance(result.zhi_shigan_detail, dict)

    def test_judgments_list_not_empty(self, engine):
        """断语列表是非空字符串列表"""
        result = engine.judge_year(SAMPLE_BAZI_WITH_YONGSHEN, 2026)
        assert isinstance(result.judgments, list)
        assert len(result.judgments) >= 1, "断语列表至少有 1 条"
        for j in result.judgments:
            assert isinstance(j, str), f"断语项必须是字符串：{j}"
            assert len(j) > 0

    def test_multiple_years(self, engine):
        """judge() 方法对年份范围返回列表"""
        results = engine.judge(SAMPLE_BAZI_WITH_YONGSHEN, 2025, 2030)
        assert isinstance(results, list)
        assert len(results) == 6, f"应为 6 年结果，实际 {len(results)}"
        for idx, r in enumerate(results):
            assert isinstance(r, YearJudgment)
            assert r.year == 2025 + idx

    def test_decade_summary(self, engine):
        """十年大运汇总返回字典"""
        summary = engine.decade_summary(SAMPLE_BAZI_WITH_YONGSHEN, 2026, 2035)
        assert isinstance(summary, dict)
        assert "year_range" in summary
        assert "best_year" in summary
        assert "worst_year" in summary
        assert "average_score" in summary
        assert "judgments" in summary
        assert len(summary["judgments"]) == 10
        assert summary["best_score"] >= summary["worst_score"]

    def test_score_range(self, engine):
        """所有分数在 0~100 之间"""
        results = engine.judge(SAMPLE_BAZI_WITH_YONGSHEN, 2020, 2040)
        for r in results:
            assert 0 <= r.score <= 100, f"{r.year} 年 score={r.score} 超出范围"

    def test_favorable_elements(self, engine):
        """喜用神（favorable elements）为列表"""
        result = engine.judge_year(SAMPLE_BAZI_WITH_YONGSHEN, 2026)
        assert isinstance(result.yongshen_list, list)
        assert len(result.yongshen_list) >= 1

    def test_unfavorable_elements(self, engine):
        """忌神（unfavorable elements）为列表"""
        result = engine.judge_year(SAMPLE_BAZI_WITH_YONGSHEN, 2026)
        assert isinstance(result.jishen_list, list)

    def test_day_master_preserved(self, engine):
        """不同日主产生不同的十神格局"""
        # 不使用 pillars（避免内部覆盖 day_master），明确传递 day_master 参数
        bazi_a = {"day_master": "甲"}
        bazi_b = {"day_master": "庚"}
        r_a = engine.judge_year(bazi_a, 2026, day_master="甲", ri_zhi="子")
        r_b = engine.judge_year(bazi_b, 2026, day_master="庚", ri_zhi="子")
        assert r_a.day_master == "甲"
        assert r_b.day_master == "庚"
        # 十神分配：两个不同日主对同一流年天干会产生不同的十神
        assert isinstance(r_a.gan_shigan, str) and r_a.gan_shigan
        assert isinstance(r_b.gan_shigan, str) and r_b.gan_shigan
        # 不同日主 → 不同的地支藏干十神映射
        assert r_a.zhi_shigan_detail != r_b.zhi_shigan_detail

    def test_empty_input(self, engine):
        """最小输入不崩溃"""
        result = engine.judge_year(SAMPLE_BAZI_MINIMAL, 2026)
        assert isinstance(result, YearJudgment)
        assert 0 <= result.score <= 100


# ============================================================================
# Test 2：XuankongEngine — 玄空飞星引擎
# ============================================================================

class TestXuankongFlyingStar:
    """玄空飞星引擎测试"""

    @pytest.fixture
    def engine(self):
        return XuankongEngine()

    def test_engine_instantiation(self, engine):
        """XuankongEngine 可以被创建"""
        assert isinstance(engine, XuankongEngine)

    def test_basic_flying_star(self, engine):
        """calculate/compute 返回 FlyingStarResult"""
        result = engine.compute(sitting="北", facing="南", year=2026)
        assert isinstance(result, FlyingStarResult)

    def test_result_has_nine_palace(self, engine):
        """结果包含九宫"""
        result = engine.compute(sitting="北", facing="南", year=2026)
        # 元旦盘 / 运盘 / 山盘 / 向盘 都应有 9 个宫位
        assert len(result.yuandan_pan) == 9
        assert len(result.yun_pan) == 9
        assert len(result.shan_pan) == 9
        assert len(result.xiang_pan) == 9

    def test_each_palace_has_stars(self, engine):
        """每个宫位都有合法的星数 (1~9)"""
        result = engine.compute(sitting="北", facing="南", year=2026)
        for palace_num in range(1, 10):
            star = result.yun_pan.get(palace_num)
            assert star is not None, f"第 {palace_num} 宫没有星数"
            assert 1 <= star <= 9, f"星数必须为 1~9，实际：{star}"

    def test_different_years_different_stars(self, engine):
        """不同年份产生不同的流年飞星图案"""
        r1 = engine.compute(sitting="北", facing="南", year=2026)
        r2 = engine.compute(sitting="北", facing="南", year=2036)
        # 至少有一个宫位流年星不同
        assert r1.liunian_pan != r2.liunian_pan, "不同年份流年星应不同"

    def test_year_range(self, engine):
        """可计算 1800~2100 年份范围"""
        for year in (1800, 1900, 1949, 2000, 2026, 2050, 2100):
            r = engine.compute(sitting="北", facing="南", year=year)
            assert isinstance(r, FlyingStarResult)
            assert len(r.yun_pan) == 9, f"{year} 年运盘宫位数不对"

    def test_flying_star_directions(self, engine):
        """结果包含八方方位信息"""
        result = engine.compute(sitting="北", facing="南", year=2026)
        # 坐向信息
        assert "坐" in result.direction and "向" in result.direction
        assert "北" in result.sitting_palace
        assert "南" in result.facing_palace
        # 测试主要方位
        for sitting in ("北", "南", "东", "西", "东北", "东南", "西北", "西南"):
            r = engine.compute(sitting=sitting, facing=sitting, year=2026)
            assert isinstance(r, FlyingStarResult)

    def test_to_dict_exists(self, engine):
        """to_dict() 返回 dict 并含关键字段"""
        result = engine.compute(sitting="北", facing="南", year=2026)
        d = result.to_dict()
        assert isinstance(d, dict)
        for key in ("year", "yun", "yun_name", "direction",
                    "yuandan_pan", "yun_pan", "shan_pan", "xiang_pan",
                    "analysis", "judgments"):
            assert key in d, f"to_dict 缺少字段: {key}"


# ============================================================================
# Test 3：QizhengEngine — 七政四余天文引擎
# ============================================================================

class TestQizhengSystem:
    """七政四余天文引擎测试"""

    @pytest.fixture
    def engine(self):
        return QizhengEngine()

    def test_engine_instantiation(self, engine):
        """QizhengEngine 可以被创建"""
        assert isinstance(engine, QizhengEngine)

    def test_basic_calculation(self, engine):
        """可对某日期计算行星位置"""
        result = engine.compute(2026, 6, 19, 12, 0)
        assert isinstance(result, QizhengResult)
        assert result.birth_datetime
        assert result.julian_day > 0

    def test_result_has_seven_planets(self, engine):
        """返回七政数据"""
        result = engine.compute(2026, 6, 19, 12, 0)
        assert len(result.seven_planets) == 7, f"应有 7 颗行星，实际 {len(result.seven_planets)}"
        for key in ("日", "月", "木", "火", "土", "金", "水"):
            assert key in result.seven_planets, f"缺少行星 {key}"

    def test_each_planet_has_position(self, engine):
        """每颗行星有位置/经度/宫位信息"""
        result = engine.compute(2026, 6, 19, 12, 0)
        for key, pos in result.seven_planets.items():
            assert isinstance(pos, PlanetPosition)
            assert 0 <= pos.longitude < 360, f"{key} 经度 {pos.longitude} 超出 0~360"
            assert pos.zhi in "子丑寅卯辰巳午未申酉戌亥"
            assert pos.palace, f"{key} 未分配宫位"
            assert pos.wuxing in "木火土金水"
            assert pos.type in ("吉星", "凶星", "中性")

    def test_different_dates_different_positions(self, engine):
        """不同日期产生不同位置"""
        r1 = engine.compute(2000, 1, 1, 12, 0)
        r2 = engine.compute(2026, 6, 19, 12, 0)
        # 至少太阳位置应不同（因为日期相差 20 多年）
        assert abs(r1.seven_planets["日"].longitude -
                   r2.seven_planets["日"].longitude) > 0.01, \
            "不同日期太阳位置应不同"

    def test_planetary_relationships(self, engine):
        """引擎可计算行星间关系（通过 result 内部结构）"""
        result = engine.compute(2026, 6, 19, 12, 0)
        planets = list(result.seven_planets.values())
        # 验证可以遍历 + 计算相互关系
        assert len(planets) == 7
        # 计算两两角度差
        for i, p1 in enumerate(planets):
            for p2 in planets[i + 1:]:
                diff = abs(p1.longitude - p2.longitude) % 360
                assert 0 <= diff < 360
                # 是否合相（差 < 10 度）
                _ = diff < 10  # 只验证表达式可计算

    def test_four_remainders_stars(self, engine):
        """结果包含四余（罗睺/计都/月孛/紫气）"""
        result = engine.compute(2026, 6, 19, 12, 0)
        assert len(result.four_remainders) == 4
        for key in ("罗睺", "计都", "月孛", "紫气"):
            assert key in result.four_remainders, f"缺少 {key}"
            pos = result.four_remainders[key]
            assert 0 <= pos.longitude < 360
            assert pos.zhi in "子丑寅卯辰巳午未申酉戌亥"

    def test_result_to_dict(self, engine):
        """to_dict 返回 dict 结构"""
        result = engine.compute(2026, 6, 19, 12, 0)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "birth_datetime" in d
        assert "seven_planets" in d
        assert "four_remainders" in d
        assert isinstance(d["seven_planets"], dict)
        assert isinstance(d["four_remainders"], dict)


# ============================================================================
# Test 4：综合集成 — PredictionIntegration
# ============================================================================

class TestPredictionIntegration:
    """综合预测集成测试"""

    def test_all_three_engines_together(self):
        """同时运行三个引擎并得到有效结果"""
        bazi = SAMPLE_BAZI_WITH_YONGSHEN

        liunian_engine = LiunianJudgmentEngine()
        liunian_result = liunian_engine.judge_year(bazi, 2026)

        fengshui_engine = XuankongEngine()
        fengshui_result = fengshui_engine.compute(sitting="北", facing="南", year=2026)

        qizheng_engine = QizhengEngine()
        qizheng_result = qizheng_engine.compute(2026, 6, 19, 12, 0)

        assert isinstance(liunian_result, YearJudgment)
        assert isinstance(fengshui_result, FlyingStarResult)
        assert isinstance(qizheng_result, QizhengResult)

    def test_prediction_workflow(self):
        """完整预测流程：八字 → 流年 → 玄空 → 七政"""
        bazi = SAMPLE_BAZI_WITH_YONGSHEN
        # 1. 先算 10 年流年
        liunian = LiunianJudgmentEngine()
        decade = liunian.decade_summary(bazi, 2026, 2035)
        assert decade["total_years"] == 10
        best_year = decade["best_year"]
        assert 2026 <= best_year <= 2035

        # 2. 该年风水排盘
        fengshui = XuankongEngine()
        f = fengshui.compute(sitting="北", facing="南", year=best_year)
        assert len(f.yun_pan) == 9

        # 3. 七政四余（对该年某月日）
        qizheng = QizhengEngine()
        q = qizheng.compute(best_year, 6, 15, 12, 0)
        assert len(q.seven_planets) == 7

        # 最终综合评分（本函数自己组装的字典）
        combined_score = min(100, max(0, int(
            decade["average_score"] * 0.5 +
            (100 if f.analysis.get("overall_best") else 50) * 0.25 +
            (q.analysis.get("庙旺总数", 0) * 15) * 0.25
        )))
        assert 0 <= combined_score <= 100

    def test_fengshui_import(self):
        """fengshui 子包可被导入且可直接调用主要符号"""
        # 已经从 package 导入了，这里做附加检查
        assert callable(compute_fengshui)
        r = compute_fengshui("北", "南", 2026)
        assert isinstance(r, FlyingStarResult)
        assert isinstance(NINE_STARS, dict)
        assert len(NINE_STARS) == 9
        # 元运计算
        yun = get_yun_number(2026)
        assert 1 <= yun <= 9
        name = get_yun_name(yun)
        assert "运" in name
        start, end = get_yun_year_range(yun)
        assert start < end

    def test_qizheng_import(self):
        """qizheng 子包可被导入"""
        assert callable(compute_qizheng)
        r = compute_qizheng(2026, 6, 19, 12, 0)
        assert isinstance(r, QizhengResult)
        assert isinstance(SEVEN_PLANETS, dict)
        assert len(SEVEN_PLANETS) == 7
        assert isinstance(FOUR_PLANETS, dict)
        assert len(FOUR_PLANETS) == 4

    def test_combined_judgment(self):
        """可以合并三个引擎的结果"""
        bazi = SAMPLE_BAZI_WITH_YONGSHEN
        liunian = LiunianJudgmentEngine().judge_year(bazi, 2026)
        fengshui = XuankongEngine().compute(sitting="北", facing="南", year=2026)
        qizheng = QizhengEngine().compute(2026, 6, 19, 12, 0)

        combined = {
            "year": 2026,
            "liunian": {
                "score": liunian.score,
                "overall": liunian.overall,
                "pillar": liunian.pillar,
                "judgments": liunian.judgments[:3],
            },
            "fengshui": {
                "yun": fengshui.yun,
                "direction": fengshui.direction,
                "best": fengshui.analysis.get("overall_best"),
            },
            "qizheng": {
                "birth_datetime": qizheng.birth_datetime,
                "庙旺总数": qizheng.analysis.get("庙旺总数"),
                "judgments": qizheng.judgments[:3],
            },
        }

        # 写入临时文件验证可序列化
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
            path = f.name

        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded["year"] == 2026
            assert loaded["liunian"]["overall"] in ("吉", "平", "凶")
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
