#!/usr/bin/env python3
"""
test_geju_engine.py — 格局/喜用神/调候引擎单元测试
覆盖：常量、数据类、五行统计、从格判断、普通格局、旺衰、喜用神、调候、综合分析
"""
import os
import sys
from collections import Counter
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

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
    _is_cong_from,
    _judge_normal_geju,
    _judge_wangshuai,
    _ke_wuxing,
    _sheng_wuxing,
    analyze_bazi_comprehensive,
    calc_geju,
    calc_tiaohou,
    calc_yongshen,
    text_report_comprehensive,
    TIANGAN,
    DIZHI,
    TG_YINYANG,
    DZ_YINYANG,
    TG_WUXING,
    DZ_WUXING,
    ZHI_MAIN_GAN,
    YUELING_INDEX,
    YUELING_WUXING,
    TIAOHOU_TABLE,
    ZHISHEN_BY_DAY,
)

# 测试命盘
TEST_PILLARS = {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"}
# 从格案例：庚金日主，火7金1
CONG_FIRE_PILLARS = {"year": "丙午", "month": "丁巳", "day": "庚午", "hour": "丁巳"}
# 从格案例：庚金日主，木7金1（曲直仁寿格）
CONG_WOOD_PILLARS = {"year": "甲寅", "month": "乙卯", "day": "庚寅", "hour": "甲寅"}
# 从格案例：壬水日主，土7水1（从旺格，土金→从旺格）
CONG_EARTH_PILLARS = {"year": "戊辰", "month": "己丑", "day": "壬戌", "hour": "戊辰"}
# 强木普通格局（不触发从格，因日主木占比高）
STRONG_WOOD_NORMAL = {"year": "甲寅", "month": "丙寅", "day": "甲戌", "hour": "甲午"}
# 月令与日主同五行（加分案例）
YUELING_SAME_PILLARS = {"year": "甲子", "month": "丙寅", "day": "甲寅", "hour": "甲子"}


# ════════════════════════════════════════
# 1. 常量测试
# ════════════════════════════════════════

class TestConstants:
    """常量完整性测试"""

    def test_tiangan_count(self):
        assert len(TIANGAN) == 10
        assert set(TIANGAN) == set("甲乙丙丁戊己庚辛壬癸")

    def test_dizhi_count(self):
        assert len(DIZHI) == 12
        assert set(DIZHI) == set("子丑寅卯辰巳午未申酉戌亥")

    def test_tg_yinyang_covers_all(self):
        assert len(TG_YINYANG) == 10
        for tg in TIANGAN:
            assert tg in TG_YINYANG
            assert TG_YINYANG[tg] in (0, 1)

    def test_dz_yinyang_covers_all(self):
        assert len(DZ_YINYANG) == 12
        for dz in DIZHI:
            assert dz in DZ_YINYANG
            assert DZ_YINYANG[dz] in (0, 1)

    def test_tg_wuxing_maps_all_tiangan(self):
        assert len(TG_WUXING) == 10
        for tg in TIANGAN:
            assert tg in TG_WUXING
            assert TG_WUXING[tg] in {"木", "火", "土", "金", "水"}

    def test_dz_wuxing_maps_all_dizhi(self):
        assert len(DZ_WUXING) == 12
        for dz in DIZHI:
            assert dz in DZ_WUXING
            assert DZ_WUXING[dz] in {"木", "火", "土", "金", "水"}

    def test_zhi_main_gan_maps_all_dizhi(self):
        assert len(ZHI_MAIN_GAN) == 12
        for dz in DIZHI:
            assert dz in ZHI_MAIN_GAN
            assert ZHI_MAIN_GAN[dz] in TIANGAN

    def test_yueling_index_complete(self):
        assert len(YUELING_INDEX) == 12
        for dz in DIZHI:
            assert dz in YUELING_INDEX

    def test_yueling_wuxing_complete(self):
        assert len(YUELING_WUXING) == 12
        for dz in DIZHI:
            assert dz in YUELING_WUXING

    def test_tiaohou_table_entries(self):
        """12个月 x 10个日干 = 120条"""
        assert len(TIAOHOU_TABLE) == 120
        for month in DIZHI:
            for day_gan in TIANGAN:
                assert (month, day_gan) in TIAOHOU_TABLE
                assert isinstance(TIAOHOU_TABLE[(month, day_gan)], list)
                assert len(TIAOHOU_TABLE[(month, day_gan)]) == 3

    def test_zhishen_by_day_complete(self):
        """10个日干，每个10个十神关系"""
        assert len(ZHISHEN_BY_DAY) == 10
        for dm in TIANGAN:
            assert dm in ZHISHEN_BY_DAY
            relations = ZHISHEN_BY_DAY[dm]
            assert len(relations) == 10
            for other in TIANGAN:
                assert other in relations
            shishen_set = {"比肩", "劫财", "食神", "伤官", "正财", "偏财", "正官", "七杀", "正印", "偏印"}
            assert set(relations.values()) == shishen_set


# ════════════════════════════════════════
# 2. 数据类测试
# ════════════════════════════════════════

class TestDataclasses:
    """数据类创建测试"""

    def test_geju_result_creation(self):
        result = GejuResult(
            pillars=TEST_PILLARS,
            day_master="辛",
            month_zhi="午",
            month_gan="壬",
            yueling="火",
            geju_type="食伤格",
            geju_name="伤官格",
            geju_desc="测试",
            is_cong=False,
            is_huaqi=False,
            shiyongshen=[],
            jishen=["印绶"],
            fujia_shens=[],
            score=80.0,
            detail={"wuxing_counts": {"金": 2}},
        )
        assert result.day_master == "辛"
        assert result.score == 80.0
        assert isinstance(result.jishen, list)
        assert isinstance(result.detail, dict)

    def test_tiaohou_result_creation(self):
        result = TiaohouResult(
            month_zhi="午",
            day_master="辛",
            yueling="火",
            required_tiaohou=True,
            season="夏",
            tiaohou_shens=["壬", "庚", "癸"],
            bingyao_shens=["水", "壬", "癸"],
            desc="命局偏热",
            detail={"season": "夏"},
        )
        assert result.required_tiaohou is True
        assert result.season == "夏"
        assert len(result.tiaohou_shens) == 3

    def test_yongshen_result_creation(self):
        result = YongshenResult(
            pillars=TEST_PILLARS,
            day_master="辛",
            wang_shuai="弱",
            wang_shuai_level=28.0,
            yong_shen=["壬", "印星"],
            ji_shen=["财星"],
            tiaohou_needed=True,
            tiaohou_shens=["壬"],
            bingyao_shens=["水"],
            yongshen_desc="测试",
            wuxing_balance={"木": 0, "火": 3, "土": 0, "金": 2, "水": 3},
            score=70.0,
        )
        assert result.wang_shuai == "弱"
        assert set(result.wuxing_balance.keys()) == {"木", "火", "土", "金", "水"}

    def test_comprehensive_result_creation(self):
        g = calc_geju(TEST_PILLARS)
        y = calc_yongshen(TEST_PILLARS)
        t = calc_tiaohou(TEST_PILLARS)
        result = ComprehensiveResult(
            pillars=TEST_PILLARS,
            day_master="辛",
            geju=g,
            yongshen=y,
            tiaohou=t,
        )
        assert result.day_master == "辛"
        assert isinstance(result.geju, GejuResult)
        assert isinstance(result.yongshen, YongshenResult)
        assert isinstance(result.tiaohou, TiaohouResult)


# ════════════════════════════════════════
# 3. _count_wuxing 测试
# ════════════════════════════════════════

class TestCountWuxing:
    """五行统计测试"""

    def test_returns_counter(self):
        c = _count_wuxing(TEST_PILLARS)
        assert isinstance(c, Counter)

    def test_total_eight(self):
        """四柱共8个（4天干+4地支本气）"""
        c = _count_wuxing(TEST_PILLARS)
        assert sum(c.values()) == 8

    def test_each_pillar_contributes_two(self):
        """每柱贡献2（1天干+1地支本气），4柱=8"""
        for pillars in [TEST_PILLARS, CONG_FIRE_PILLARS, STRONG_WOOD_NORMAL]:
            c = _count_wuxing(pillars)
            assert sum(c.values()) == 8, f"Expected 8 for {pillars}, got {sum(c.values())}"

    def test_specific_pillars_count(self):
        """验证已知命盘的五行统计"""
        c = _count_wuxing(TEST_PILLARS)
        # 庚午 壬午 辛亥 癸巳
        # 天干: 庚(金) 壬(水) 辛(金) 癸(水) → 金2,水2
        # 地支本气: 午(丁火) 午(丁火) 亥(壬水) 巳(丙火) → 火3,水1
        # 总计: 金2,水3,火3
        assert c["金"] == 2
        assert c["水"] == 3
        assert c["火"] == 3
        assert c["木"] == 0
        assert c["土"] == 0

    def test_cong_fire_count(self):
        c = _count_wuxing(CONG_FIRE_PILLARS)
        # 丙午 丁巳 庚午 丁巳
        # 天干: 丙(火) 丁(火) 庚(金) 丁(火) → 火3,金1
        # 地支本气: 午(丁火) 巳(丙火) 午(丁火) 巳(丙火) → 火4
        # 总计: 火7,金1
        assert c["火"] == 7
        assert c["金"] == 1
        assert sum(c.values()) == 8


# ════════════════════════════════════════
# 4. _is_cong_from 测试
# ════════════════════════════════════════

class TestIsCongFrom:
    """从格判断测试"""

    def test_day_master_ratio_40_or_more_not_cong(self):
        """日主占比>=40%时不从"""
        # 木4个，其他4个 → 4/8=50% >=40%
        c = Counter({"木": 4, "火": 2, "土": 1, "金": 1})
        assert _is_cong_from(c, "甲") is None

    def test_day_master_exactly_40_percent(self):
        """日主刚好40%也不从"""
        # 8个中3.2个是40%，3/8=37.5%<40%, 4/8=50%>40%
        # 构造10个（虽然通常是8）：4/10=40%
        c = Counter({"木": 4, "火": 3, "土": 3})
        assert _is_cong_from(c, "甲") is None

    def test_strongest_wood_returns_quzhi(self):
        """最强五行木 → 曲直仁寿格"""
        # 木7个，金1个（日主庚，金）→ 金占12.5%<40%，木占87.5%>=50%
        c = Counter({"木": 7, "金": 1})
        result = _is_cong_from(c, "庚")
        assert result == "曲直仁寿格"

    def test_strongest_fire_returns_yanshang(self):
        """最强五行火 → 炎上格"""
        c = Counter({"火": 7, "金": 1})
        result = _is_cong_from(c, "庚")
        assert result == "炎上格"

    def test_strongest_water_returns_runxia(self):
        """最强五行水 → 润下格"""
        # 水7个，火1个（日主丁）
        c = Counter({"水": 7, "火": 1})
        result = _is_cong_from(c, "丁")
        assert result == "润下格"

    def test_strongest_earth_returns_congwang(self):
        """最强五行土 → 从旺格"""
        c = Counter({"土": 7, "水": 1})
        result = _is_cong_from(c, "壬")
        assert result == "从旺格"

    def test_strongest_metal_returns_congwang(self):
        """最强五行金 → 从旺格"""
        c = Counter({"金": 7, "木": 1})
        result = _is_cong_from(c, "甲")
        assert result == "从旺格"

    def test_strongest_less_than_50_percent_not_cong(self):
        """最强非日主五行<50%时不从"""
        # 日主甲（木）2个=25%<40%，但最强火3个=37.5%<50%
        c = Counter({"木": 2, "火": 3, "土": 1, "金": 1, "水": 1})
        assert _is_cong_from(c, "甲") is None

    def test_cai_guan_sha_branches_unreachable(self):
        """
        注意：_is_cong_from 检查 strongest=='财'/'官'/'杀'，
        但 wuxing_counts 的键是五行（木火土金水），所以这些分支不可达。
        从财格/从杀格在当前实现中不会被触发。
        此测试验证当前实际行为（传入'财'作为key的counter）。
        """
        # 如果直接构造key为'财'的Counter，会返回'从财格'
        # 但_count_wuxing永远不会产生这样的key
        c = Counter({"财": 6, "木": 2})
        result = _is_cong_from(c, "甲")
        assert result == "从财格"

    def test_cong_sha_ge(self):
        """直接构造key为'官'或'杀'的Counter返回从杀格"""
        c = Counter({"官": 5, "木": 3})
        result = _is_cong_from(c, "甲")
        assert result == "从杀格"
        c2 = Counter({"杀": 6, "木": 2})
        result2 = _is_cong_from(c2, "甲")
        assert result2 == "从杀格"

    def test_other_returns_congshi(self):
        """其他未知最强五行 → 从势格"""
        c = Counter({"未知": 7, "木": 1})
        result = _is_cong_from(c, "甲")
        assert result == "从势格"

    def test_empty_counts(self):
        """空Counter测试（total=0时使用max(total,1)=1）"""
        c = Counter()
        # 日主0/1=0%<40%，找最强非日主五行时会出错（没有非日主五行）
        # 这是edge case，实际不会发生
        with pytest.raises(ValueError):
            _is_cong_from(c, "甲")


# ════════════════════════════════════════
# 5. _judge_normal_geju 测试
# ════════════════════════════════════════

class TestJudgeNormalGeju:
    """普通格局判断测试"""

    def _make_pillars_with_month_gan(self, month_gan: str, month_zhi: str = "丑") -> dict:
        """构造指定月干的四柱，平衡五行避免触发从格"""
        return {
            "year": "甲子",
            "month": month_gan + month_zhi,
            "day": "辛" + "酉",
            "hour": "庚" + "辰",
        }

    def test_zhengguan_returns_guansha(self):
        """正官（丙对辛）→ 官杀格"""
        p = self._make_pillars_with_month_gan("丙")
        c = _count_wuxing(p)
        gtype, gname, gdesc, jishen, score = _judge_normal_geju(p, "辛", "丙", c)
        assert gtype == "官杀格"
        assert "正官格" in gname
        assert "伤官" in jishen

    def test_qisha_returns_guansha(self):
        """七杀（丁对辛）→ 官杀格"""
        p = self._make_pillars_with_month_gan("丁")
        c = _count_wuxing(p)
        gtype, gname, gdesc, jishen, score = _judge_normal_geju(p, "辛", "丁", c)
        assert gtype == "官杀格"
        assert "七杀格" in gname
        assert "伤官" in jishen

    def test_zhengcai_returns_caige(self):
        """正财（甲对辛）→ 财格"""
        p = self._make_pillars_with_month_gan("甲")
        c = _count_wuxing(p)
        gtype, gname, gdesc, jishen, score = _judge_normal_geju(p, "辛", "甲", c)
        assert gtype == "财格"
        assert "正财格" in gname
        assert "劫财" in jishen
        assert "比肩" in jishen

    def test_piancai_returns_caige(self):
        """偏财（乙对辛）→ 财格"""
        p = self._make_pillars_with_month_gan("乙")
        c = _count_wuxing(p)
        gtype, gname, gdesc, jishen, score = _judge_normal_geju(p, "辛", "乙", c)
        assert gtype == "财格"
        assert "偏财格" in gname
        assert "劫财" in jishen

    def test_shishen_returns_shishang(self):
        """食神（癸对辛）→ 食伤格"""
        p = self._make_pillars_with_month_gan("癸")
        c = _count_wuxing(p)
        gtype, gname, gdesc, jishen, score = _judge_normal_geju(p, "辛", "癸", c)
        assert gtype == "食伤格"
        assert "食神格" in gname
        assert "印绶" in jishen

    def test_shangguan_returns_shishang(self):
        """伤官（壬对辛）→ 食伤格"""
        p = self._make_pillars_with_month_gan("壬")
        c = _count_wuxing(p)
        gtype, gname, gdesc, jishen, score = _judge_normal_geju(p, "辛", "壬", c)
        assert gtype == "食伤格"
        assert "伤官格" in gname
        assert "印绶" in jishen

    def test_zhengyin_returns_yinshou(self):
        """正印（戊对辛）→ 印绶格"""
        p = self._make_pillars_with_month_gan("戊")
        c = _count_wuxing(p)
        gtype, gname, gdesc, jishen, score = _judge_normal_geju(p, "辛", "戊", c)
        assert gtype == "印绶格"
        assert "正印格" in gname
        assert "财星" in jishen

    def test_pianyin_returns_yinshou(self):
        """偏印（己对辛）→ 印绶格"""
        p = self._make_pillars_with_month_gan("己")
        c = _count_wuxing(p)
        gtype, gname, gdesc, jishen, score = _judge_normal_geju(p, "辛", "己", c)
        assert gtype == "印绶格"
        assert "偏印格" in gname
        assert "财星" in jishen

    def test_bijian_returns_bijie(self):
        """比肩（辛对辛）→ 比劫格"""
        p = self._make_pillars_with_month_gan("辛")
        c = _count_wuxing(p)
        gtype, gname, gdesc, jishen, score = _judge_normal_geju(p, "辛", "辛", c)
        assert gtype == "比劫格"
        assert "比劫格" in gname
        assert "独立自我" in gname
        assert "财星" in jishen
        assert "官杀" in jishen

    def test_jiecai_returns_bijie(self):
        """劫财（庚对辛）→ 比劫格"""
        p = self._make_pillars_with_month_gan("庚")
        c = _count_wuxing(p)
        gtype, gname, gdesc, jishen, score = _judge_normal_geju(p, "辛", "庚", c)
        assert gtype == "比劫格"
        assert "劫财格" in gname
        assert "财星" in jishen

    def test_yueling_bonus_when_same_as_day_master(self):
        """月令五行与日主相同时score+5"""
        # 甲日主，寅月（木令）
        p = {"year": "甲子", "month": "丙寅", "day": "甲戌", "hour": "甲子"}
        c = _count_wuxing(p)
        gtype, gname, gdesc, jishen, score = _judge_normal_geju(p, "甲", "丙", c)
        assert score == 85.0  # 80 + 5
        assert "月令当令" in gdesc

    def test_yueling_no_bonus_when_different(self):
        """月令五行与日主不同时score=80"""
        p = {"year": "甲子", "month": "丙子", "day": "甲寅", "hour": "甲子"}
        c = _count_wuxing(p)
        gtype, gname, gdesc, jishen, score = _judge_normal_geju(p, "甲", "丙", c)
        # 注意：子月水令，甲木日主，不加分
        assert score == 80.0

    def test_score_capped_at_100(self):
        """score上限100（通过min(score, 100)）"""
        # 当前逻辑初始80+5=85，正常无法达到100，但代码有保护
        p = {"year": "甲子", "month": "丙寅", "day": "甲寅", "hour": "甲子"}
        c = _count_wuxing(p)
        _, _, _, _, score = _judge_normal_geju(p, "甲", "丙", c)
        assert score <= 100


# ════════════════════════════════════════
# 6. calc_geju 测试
# ════════════════════════════════════════

class TestCalcGeju:
    """格局判断主函数测试"""

    def test_returns_geju_result(self):
        result = calc_geju(TEST_PILLARS)
        assert isinstance(result, GejuResult)

    def test_normal_case_not_cong(self):
        """普通命盘非从格"""
        result = calc_geju(TEST_PILLARS)
        assert result.is_cong is False
        assert result.is_huaqi is False

    def test_cong_case_is_cong(self):
        """从格命盘is_cong=True"""
        result = calc_geju(CONG_FIRE_PILLARS)
        assert result.is_cong is True
        assert result.is_huaqi is False
        assert result.geju_type == "从格"

    def test_cong_fire_yanshang(self):
        """火极旺从格 → 炎上格"""
        result = calc_geju(CONG_FIRE_PILLARS)
        assert result.geju_name == "炎上格"

    def test_cong_wood_quzhi(self):
        """木极旺从格 → 曲直仁寿格"""
        result = calc_geju(CONG_WOOD_PILLARS)
        assert result.geju_name == "曲直仁寿格"

    def test_all_fields_populated(self):
        """所有字段都有值"""
        result = calc_geju(TEST_PILLARS)
        assert result.pillars == TEST_PILLARS
        assert result.day_master == "辛"
        assert result.month_zhi == "午"
        assert result.month_gan == "壬"
        assert result.yueling == "火"
        assert result.geju_type
        assert result.geju_name
        assert result.geju_desc
        assert isinstance(result.jishen, list)
        assert isinstance(result.fujia_shens, list)
        assert isinstance(result.shiyongshen, list)
        assert 0 <= result.score <= 100

    def test_detail_dict_has_required_keys(self):
        """detail字典包含必要字段"""
        result = calc_geju(TEST_PILLARS)
        assert "wuxing_counts" in result.detail
        assert "yueling_wuxing" in result.detail
        assert "day_gan_wuxing" in result.detail
        assert "month_shishen" in result.detail

    def test_known_example_from_cli(self):
        """CLI中的测试例子：庚午壬午辛亥癸巳"""
        result = calc_geju(TEST_PILLARS)
        # 月干壬对辛是伤官
        assert result.detail["month_shishen"] == "伤官"
        assert result.geju_type == "食伤格"
        assert result.score == 80.0
        assert result.jishen == ["印绶"]

    def test_cong_case_jishen(self):
        """从格忌神正确"""
        result = calc_geju(CONG_FIRE_PILLARS)
        # 从旺格局（炎上格属于从旺类），忌神为[day_gan_wx]
        assert result.jishen == ["金"]

    def test_cong_earth_congwang(self):
        """土旺从格 → 从旺格"""
        # 壬辰日主，土7水1
        result = calc_geju(CONG_EARTH_PILLARS)
        assert result.is_cong is True
        assert result.geju_name == "从旺格"


# ════════════════════════════════════════
# 7. _get_season 测试
# ════════════════════════════════════════

class TestGetSeason:
    """季节判断测试"""

    def test_yin_mao_spring(self):
        assert _get_season("寅") == "春"
        assert _get_season("卯") == "春"

    def test_si_wu_summer(self):
        assert _get_season("巳") == "夏"
        assert _get_season("午") == "夏"

    def test_shen_you_autumn(self):
        assert _get_season("申") == "秋"
        assert _get_season("酉") == "秋"

    def test_hai_zi_winter(self):
        assert _get_season("亥") == "冬"
        assert _get_season("子") == "冬"

    def test_chen_xu_chou_wei_four_seasons(self):
        assert _get_season("辰") == "四季"
        assert _get_season("戌") == "四季"
        assert _get_season("丑") == "四季"
        assert _get_season("未") == "四季"

    def test_all_twelve_months(self):
        for dz in DIZHI:
            season = _get_season(dz)
            assert season in {"春", "夏", "秋", "冬", "四季"}


# ════════════════════════════════════════
# 8. calc_tiaohou 测试
# ════════════════════════════════════════

class TestCalcTiaohou:
    """调候用神测试"""

    def test_returns_tiaohou_result(self):
        result = calc_tiaohou(TEST_PILLARS)
        assert isinstance(result, TiaohouResult)

    def test_summer_required_tiaohou(self):
        """夏季（巳午月）必须调候"""
        for mz in ["巳", "午"]:
            p = {"year": "甲子", "month": "甲" + mz, "day": "庚" + "子", "hour": "甲子"}
            result = calc_tiaohou(p)
            assert result.required_tiaohou is True
            assert result.season == "夏"

    def test_winter_required_tiaohou(self):
        """冬季（亥子月）必须调候"""
        for mz in ["亥", "子"]:
            p = {"year": "甲子", "month": "甲" + mz, "day": "庚" + "子", "hour": "甲子"}
            result = calc_tiaohou(p)
            assert result.required_tiaohou is True
            assert result.season == "冬"

    def test_spring_autumn_not_required_except_yin_jia_yi(self):
        """春秋一般不需要调候，但寅月甲乙例外"""
        # 卯月甲不需要
        p_mao_jia = {"year": "甲子", "month": "甲" + "卯", "day": "甲" + "子", "hour": "甲子"}
        assert calc_tiaohou(p_mao_jia).required_tiaohou is False
        # 申月庚不需要
        p_shen_geng = {"year": "甲子", "month": "甲" + "申", "day": "庚" + "子", "hour": "甲子"}
        assert calc_tiaohou(p_shen_geng).required_tiaohou is False
        # 酉月庚不需要
        p_you_geng = {"year": "甲子", "month": "甲" + "酉", "day": "庚" + "子", "hour": "甲子"}
        assert calc_tiaohou(p_you_geng).required_tiaohou is False

    def test_yin_month_jia_yi_required(self):
        """寅月甲乙日主需要调候"""
        for dm in ["甲", "乙"]:
            p = {"year": "甲子", "month": "丙" + "寅", "day": dm + "子", "hour": "甲子"}
            result = calc_tiaohou(p)
            assert result.required_tiaohou is True, f"寅月{dm}应该需要调候"

    def test_yin_month_other_gan_not_required(self):
        """寅月非甲乙日主不需要调候"""
        for dm in ["丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]:
            p = {"year": "甲子", "month": "丙" + "寅", "day": dm + "子", "hour": "甲子"}
            result = calc_tiaohou(p)
            assert result.required_tiaohou is False, f"寅月{dm}不应该需要调候"

    def test_tiaohou_shens_from_table(self):
        """调候用神来自TIAOHOU_TABLE"""
        for mz in ["寅", "午", "亥"]:
            for dm in ["甲", "庚", "壬"]:
                p = {"year": "甲子", "month": "丙" + mz, "day": dm + "子", "hour": "甲子"}
                result = calc_tiaohou(p)
                expected = TIAOHOU_TABLE[(mz, dm)]
                assert result.tiaohou_shens == expected

    def test_bingyao_summer(self):
        """夏季病药为水"""
        p = {"year": "甲子", "month": "甲" + "午", "day": "庚" + "子", "hour": "甲子"}
        result = calc_tiaohou(p)
        assert result.bingyao_shens == ["水", "壬", "癸"]

    def test_bingyao_winter(self):
        """冬季病药为火"""
        p = {"year": "甲子", "month": "甲" + "子", "day": "庚" + "子", "hour": "甲子"}
        result = calc_tiaohou(p)
        assert result.bingyao_shens == ["火", "丙", "丁"]

    def test_bingyao_spring(self):
        """春季病药为金"""
        p = {"year": "甲子", "month": "甲" + "卯", "day": "庚" + "子", "hour": "甲子"}
        result = calc_tiaohou(p)
        assert result.bingyao_shens == ["金", "庚", "辛"]

    def test_bingyao_autumn(self):
        """秋季病药为水"""
        p = {"year": "甲子", "month": "甲" + "酉", "day": "庚" + "子", "hour": "甲子"}
        result = calc_tiaohou(p)
        assert result.bingyao_shens == ["水", "壬", "癸"]

    def test_bingyao_four_seasons_empty(self):
        """四季月（辰戌丑未）病药为空（代码未处理）"""
        for mz in ["辰", "戌", "丑", "未"]:
            p = {"year": "甲子", "month": "甲" + mz, "day": "戊" + "子", "hour": "甲子"}
            result = calc_tiaohou(p)
            assert result.bingyao_shens == []

    def test_desc_populated(self):
        """desc字段非空"""
        result = calc_tiaohou(TEST_PILLARS)
        assert len(result.desc) > 0

    def test_all_twelve_months(self):
        """测试所有12个月"""
        for mz in DIZHI:
            p = {"year": "甲子", "month": "甲" + mz, "day": "甲" + "子", "hour": "甲子"}
            result = calc_tiaohou(p)
            assert result.month_zhi == mz
            assert result.season in {"春", "夏", "秋", "冬", "四季"}
            assert isinstance(result.required_tiaohou, bool)


# ════════════════════════════════════════
# 9. _ke_wuxing 测试
# ════════════════════════════════════════

class TestKeWuxing:
    """五行相克测试"""

    def test_mu_ke_tu(self):
        assert _ke_wuxing("木") == ["土"]

    def test_huo_ke_jin(self):
        assert _ke_wuxing("火") == ["金"]

    def test_tu_ke_shui(self):
        assert _ke_wuxing("土") == ["水"]

    def test_jin_ke_mu(self):
        assert _ke_wuxing("金") == ["木"]

    def test_shui_ke_huo(self):
        assert _ke_wuxing("水") == ["火"]

    def test_unknown_wuxing_empty(self):
        assert _ke_wuxing("未知") == []


# ════════════════════════════════════════
# 10. _sheng_wuxing 测试
# ════════════════════════════════════════

class TestShengWuxing:
    """五行相生测试"""

    def test_mu_sheng_huo(self):
        assert _sheng_wuxing("木") == ["火"]

    def test_huo_sheng_tu(self):
        assert _sheng_wuxing("火") == ["土"]

    def test_tu_sheng_jin(self):
        assert _sheng_wuxing("土") == ["金"]

    def test_jin_sheng_shui(self):
        assert _sheng_wuxing("金") == ["水"]

    def test_shui_sheng_mu(self):
        assert _sheng_wuxing("水") == ["木"]

    def test_unknown_wuxing_empty(self):
        assert _sheng_wuxing("未知") == []


# ════════════════════════════════════════
# 11. _judge_wangshuai 测试
# ════════════════════════════════════════

class TestJudgeWangshuai:
    """旺衰判断测试"""

    def test_returns_tuple(self):
        c = _count_wuxing(TEST_PILLARS)
        ws, level = _judge_wangshuai(TEST_PILLARS, c, "辛")
        assert ws in ["旺", "中和", "弱", "从"]
        assert isinstance(level, (int, float))

    def test_wang_threshold_60(self):
        """score>=60为旺"""
        # 强木命盘 score 高
        c = _count_wuxing(STRONG_WOOD_NORMAL)
        ws, level = _judge_wangshuai(STRONG_WOOD_NORMAL, c, "甲")
        assert ws == "旺"
        assert level >= 60

    def test_zhonghe_threshold_40_60(self):
        """score在40-60之间为中和"""
        # 甲子 丙子 甲寅 甲子 → 甲日主中和
        p = {"year": "甲子", "month": "丙子", "day": "甲寅", "hour": "甲子"}
        c = _count_wuxing(p)
        ws, level = _judge_wangshuai(p, c, "甲")
        assert ws == "中和"
        assert 40 <= level < 60

    def test_ruo_threshold_20_40(self):
        """score在20-40之间为弱"""
        c = _count_wuxing(TEST_PILLARS)
        ws, level = _judge_wangshuai(TEST_PILLARS, c, "辛")
        # 庚午壬午辛亥癸巳 → 辛金弱
        assert ws in ["弱", "从"]

    def test_cong_threshold_below_20(self):
        """score<20为从"""
        # 从格命盘日主极弱
        c = _count_wuxing(CONG_FIRE_PILLARS)
        ws, level = _judge_wangshuai(CONG_FIRE_PILLARS, c, "庚")
        assert ws == "从"
        assert level >= 5

    def test_level_clamped_to_0_100(self):
        """level被限制在0-100"""
        # 旺的上限100，从/弱的下限为5/10
        c = _count_wuxing(STRONG_WOOD_NORMAL)
        ws, level = _judge_wangshuai(STRONG_WOOD_NORMAL, c, "甲")
        assert level <= 100
        assert level >= 0

    def test_yueling_bonus_applied(self):
        """月令加分/减分生效"""
        # 当令加分
        p_wang = {"year": "甲寅", "month": "丙寅", "day": "甲寅", "hour": "乙卯"}
        c_wang = _count_wuxing(p_wang)
        _, level_wang = _judge_wangshuai(p_wang, c_wang, "甲")
        # 失令减分
        p_ruo = {"year": "丙午", "month": "丁巳", "day": "庚午", "hour": "丁巳"}
        c_ruo = _count_wuxing(p_ruo)
        _, level_ruo = _judge_wangshuai(p_ruo, c_ruo, "庚")
        assert level_wang > level_ruo


# ════════════════════════════════════════
# 12. calc_yongshen 测试
# ════════════════════════════════════════

class TestCalcYongshen:
    """喜用神判断测试"""

    def test_returns_yongshen_result(self):
        result = calc_yongshen(TEST_PILLARS)
        assert isinstance(result, YongshenResult)

    def test_all_fields_populated(self):
        result = calc_yongshen(TEST_PILLARS)
        assert result.day_master == "辛"
        assert result.wang_shuai in ["旺", "中和", "弱", "从"]
        assert isinstance(result.yong_shen, list)
        assert isinstance(result.ji_shen, list)
        assert isinstance(result.tiaohou_needed, bool)
        assert isinstance(result.tiaohou_shens, list)
        assert isinstance(result.bingyao_shens, list)
        assert isinstance(result.wuxing_balance, dict)
        assert set(result.wuxing_balance.keys()) == {"木", "火", "土", "金", "水"}
        assert 0 <= result.wang_shuai_level <= 100
        assert result.score == 70.0

    def test_wang_case_yong_shen(self):
        """身旺：喜克泄（财、食伤、官杀），忌印比"""
        result = calc_yongshen(STRONG_WOOD_NORMAL)
        assert result.wang_shuai == "旺"
        # 甲木身旺：木克土（财），木生火（食伤），官杀（金克木）
        assert "印星" in result.ji_shen
        assert "比肩" in result.ji_shen or "劫财" in result.ji_shen

    def test_ruo_case_yong_shen(self):
        """身弱：喜生扶（印星、比劫），忌财官食伤"""
        result = calc_yongshen(TEST_PILLARS)
        assert result.wang_shuai in ["弱", "从"]
        if result.wang_shuai == "弱":
            assert "印星" in result.yong_shen
            assert "比肩" in result.yong_shen or "劫财" in result.yong_shen

    def test_cong_case_special_yongshen(self):
        """从格：特殊喜忌"""
        result = calc_yongshen(CONG_FIRE_PILLARS)
        assert result.wang_shuai == "从"

    def test_extreme_weak_not_cong_else_branch(self):
        """极端弱（旺衰从但格局非从格）：else分支扶日主"""
        # 甲子 丙寅 庚子 丙子 → 庚日主，旺衰=从但is_cong=False
        p = {"year": "甲子", "month": "丙寅", "day": "庚子", "hour": "丙子"}
        g = calc_geju(p)
        y = calc_yongshen(p)
        assert g.is_cong is False
        assert y.wang_shuai == "从"
        assert "扶日主" in y.yong_shen
        assert "克泄" in y.ji_shen
        assert "特殊情况" in y.yongshen_desc

    def test_tiaohou_prioritized_when_needed(self):
        """调候优先：需要调候时调候用神加入喜用前面"""
        # 午月夏季，需要调候
        result = calc_yongshen(TEST_PILLARS)
        if result.tiaohou_needed and result.tiaohou_shens:
            # 调候用神应在yong_shen前面
            assert result.tiaohou_shens[0] == result.yong_shen[0]

    def test_wuxing_balance_all_five(self):
        """五行平衡表包含全部五行"""
        result = calc_yongshen(TEST_PILLARS)
        for wx in ["木", "火", "土", "金", "水"]:
            assert wx in result.wuxing_balance
            assert isinstance(result.wuxing_balance[wx], int)

    def test_yongshen_desc_not_empty(self):
        assert len(calc_yongshen(TEST_PILLARS).yongshen_desc) > 0

    def test_known_pillars_yongshen(self):
        """已知命盘喜用神验证"""
        result = calc_yongshen(TEST_PILLARS)
        # 午月辛金，身弱，需调候（壬水）
        assert result.tiaohou_needed is True
        assert result.yong_shen[0] == "壬"  # 调候优先


# ════════════════════════════════════════
# 13. Engine类测试
# ════════════════════════════════════════

class TestEngines:
    """引擎包装类测试"""

    def test_geju_engine_compute(self):
        result = GejuEngine.compute(TEST_PILLARS)
        assert isinstance(result, GejuResult)

    def test_geju_engine_judge_basic(self):
        result = GejuEngine.judge(TEST_PILLARS, detail="basic")
        assert isinstance(result, dict)
        assert "geju_type" in result
        assert "geju_name" in result
        assert "is_cong" in result
        assert "score" in result
        assert "jishen" in result
        assert "month_shishen" in result
        # basic不包含pillars
        assert "pillars" not in result

    def test_geju_engine_judge_full(self):
        result = GejuEngine.judge(TEST_PILLARS, detail="full")
        assert isinstance(result, dict)
        assert "pillars" in result
        assert "day_master" in result
        assert "wuxing_counts" in result
        assert "fujia_shens" in result

    def test_tiaohou_engine_compute(self):
        result = TiaohouEngine.compute(TEST_PILLARS)
        assert isinstance(result, TiaohouResult)
        assert result.season == "夏"

    def test_yongshen_engine_compute(self):
        result = YongshenEngine.compute(TEST_PILLARS)
        assert isinstance(result, YongshenResult)

    def test_yongshen_engine_analyze_basic(self):
        result = YongshenEngine.analyze(TEST_PILLARS, detail="basic")
        assert isinstance(result, dict)
        assert "day_master" in result
        assert "wang_shuai" in result
        assert "yong_shen" in result
        assert "ji_shen" in result
        assert "tiaohou_needed" in result
        assert "yongshen_desc" in result
        # basic不包含wuxing_balance
        assert "wuxing_balance" not in result

    def test_yongshen_engine_analyze_full(self):
        result = YongshenEngine.analyze(TEST_PILLARS, detail="full")
        assert isinstance(result, dict)
        assert "pillars" in result
        assert "wuxing_balance" in result
        assert "bingyao_shens" in result
        assert "score" in result


# ════════════════════════════════════════
# 14. 综合分析测试
# ════════════════════════════════════════

class TestComprehensive:
    """综合分析测试"""

    def test_analyze_returns_comprehensive_result(self):
        result = analyze_bazi_comprehensive(TEST_PILLARS)
        assert isinstance(result, ComprehensiveResult)
        assert result.pillars == TEST_PILLARS
        assert result.day_master == "辛"
        assert isinstance(result.geju, GejuResult)
        assert isinstance(result.yongshen, YongshenResult)
        assert isinstance(result.tiaohou, TiaohouResult)

    def test_text_report_returns_string(self):
        report = text_report_comprehensive(TEST_PILLARS)
        assert isinstance(report, str)
        assert len(report) > 100

    def test_text_report_contains_title(self):
        report = text_report_comprehensive(TEST_PILLARS)
        assert "八字格局与喜用神综合分析报告" in report

    def test_text_report_contains_all_sections(self):
        report = text_report_comprehensive(TEST_PILLARS)
        assert "【格局判断】" in report
        assert "【旺衰判断】" in report
        assert "【喜用神】" in report
        assert "【调候】" in report
        assert "【五行平衡】" in report

    def test_text_report_contains_bars(self):
        report = text_report_comprehensive(TEST_PILLARS)
        assert "█" in report
        assert "░" in report

    def test_text_report_cong_shows_warning(self):
        """从格报告包含⚠️"""
        report = text_report_comprehensive(CONG_FIRE_PILLARS)
        assert "⚠️" in report
        assert "从格" in report

    def test_text_report_normal_no_warning(self):
        """普通格局报告不包含⚠️（当jishen不为空时）"""
        report = text_report_comprehensive(TEST_PILLARS)
        # 普通非从格不应该有⚠️从格警告
        assert "⚠️ 从格" not in report

    def test_text_report_contains_day_master(self):
        report = text_report_comprehensive(TEST_PILLARS)
        assert "日主:" in report
        assert "月令:" in report
        assert "四柱:" in report

    def test_text_report_cong_case(self):
        """从格文本报告完整性"""
        report = text_report_comprehensive(CONG_WOOD_PILLARS)
        assert "曲直仁寿格" in report
        assert "⚠️" in report


# ════════════════════════════════════════
# 15. 边界与一致性测试
# ════════════════════════════════════════

class TestEdgeCases:
    """边界情况测试"""

    def test_all_month_zhi_tiaohou(self):
        """所有12个月支调候计算不出错"""
        for mz in DIZHI:
            for dm in TIANGAN[:3]:  # 测试甲丙戊三个日干即可
                p = {"year": "甲子", "month": "甲" + mz, "day": dm + "子", "hour": "甲子"}
                result = calc_tiaohou(p)
                assert result.season in {"春", "夏", "秋", "冬", "四季"}
                assert isinstance(result.required_tiaohou, bool)

    def test_cong_all_wood(self):
        """全木从格（需要日干不是木，否则日主不弱）"""
        # 庚寅日：庚(金)+寅(甲木)，其他柱全木
        p = {"year": "甲寅", "month": "乙卯", "day": "庚寅", "hour": "甲寅"}
        result = calc_geju(p)
        assert result.is_cong is True

    def test_cong_all_fire(self):
        p = CONG_FIRE_PILLARS
        result = calc_geju(p)
        assert result.is_cong is True
        assert result.geju_name == "炎上格"

    def test_cong_all_water(self):
        """水极旺从格（润下格）"""
        # 丁日主，其他7个水
        # 丁亥日：丁(火)+亥(壬水)，其他柱水
        p = {"year": "壬子", "month": "癸亥", "day": "丁亥", "hour": "壬子"}
        c = _count_wuxing(p)
        assert c["水"] >= 5
        result = calc_geju(p)
        assert result.is_cong is True
        assert result.geju_name == "润下格"

    def test_consistency_multiple_calls(self):
        """多次调用结果一致"""
        r1 = calc_geju(TEST_PILLARS)
        r2 = calc_geju(TEST_PILLARS)
        assert r1.geju_name == r2.geju_name
        assert r1.score == r2.score

        y1 = calc_yongshen(TEST_PILLARS)
        y2 = calc_yongshen(TEST_PILLARS)
        assert y1.yong_shen == y2.yong_shen
        assert y1.wang_shuai == y2.wang_shuai

    def test_score_boundaries(self):
        """score始终在0-100之间"""
        test_pillars_list = [
            TEST_PILLARS, CONG_FIRE_PILLARS, CONG_WOOD_PILLARS,
            STRONG_WOOD_NORMAL, YUELING_SAME_PILLARS,
        ]
        for p in test_pillars_list:
            g = calc_geju(p)
            assert 0 <= g.score <= 100
            y = calc_yongshen(p)
            assert 0 <= y.wang_shuai_level <= 100

    def test_wuxing_balance_sums_to_eight(self):
        """五行平衡表合计为8"""
        result = calc_yongshen(TEST_PILLARS)
        assert sum(result.wuxing_balance.values()) == 8

    def test_comprehensive_integration(self):
        """综合分析与单独计算结果一致"""
        comp = analyze_bazi_comprehensive(TEST_PILLARS)
        g = calc_geju(TEST_PILLARS)
        y = calc_yongshen(TEST_PILLARS)
        t = calc_tiaohou(TEST_PILLARS)
        assert comp.geju.geju_name == g.geju_name
        assert comp.yongshen.wang_shuai == y.wang_shuai
        assert comp.tiaohou.season == t.season

    def test_cong_cai_ge_via_mock(self):
        """从财格分支（mock _is_cong_from）"""
        import tengod.geju_engine as ge
        with patch.object(ge, '_is_cong_from', return_value='从财格'):
            result = ge.calc_geju(TEST_PILLARS)
            assert result.is_cong is True
            assert result.geju_name == "从财格"
            assert result.geju_type == "从格"
            assert "财星" in result.fujia_shens
            assert "比肩" in result.jishen

    def test_cong_sha_ge_via_mock(self):
        """从杀格分支（mock _is_cong_from）"""
        import tengod.geju_engine as ge
        with patch.object(ge, '_is_cong_from', return_value='从杀格'):
            result = ge.calc_geju(TEST_PILLARS)
            assert result.is_cong is True
            assert result.geju_name == "从杀格"
            assert "官杀" in result.fujia_shens
            assert "食神" in result.jishen

    def test_cong_shi_ge_via_mock(self):
        """从势格分支（mock _is_cong_from）"""
        import tengod.geju_engine as ge
        with patch.object(ge, '_is_cong_from', return_value='从势格'):
            result = ge.calc_geju(TEST_PILLARS)
            assert result.is_cong is True
            assert result.geju_name == "从势格"
            assert "从势格" in result.geju_desc

    def test_guansha_geju_yongshen_correction_via_mock(self):
        """官杀格喜用神修正分支（mock geju_name）"""
        import tengod.geju_engine as ge
        # 先正常计算geju，然后mock返回的geju_name
        original_calc_geju = ge.calc_geju
        def mock_calc_geju(p):
            r = original_calc_geju(p)
            r.geju_name = "官杀格"
            return r
        with patch.object(ge, 'calc_geju', side_effect=mock_calc_geju):
            result = ge.calc_yongshen(TEST_PILLARS)
            # 应该添加印星到yong_shen前面，伤官到ji_shen前面
            assert "印星" in result.yong_shen
            assert "伤官" in result.ji_shen
