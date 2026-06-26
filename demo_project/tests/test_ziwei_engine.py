#!/usr/bin/env python3
"""Tests for tengod.ziwei_engine module."""

import pytest
from tengod.ziwei_engine import (
    ZiweiEngine, ZiweiChart, GongInfo, StarInfo,
    calc_ziwei, ziwei_to_dict,
    DI_ZHI, TIAN_GAN, GONG_NAMES, GONG_EN,
    ZIWEI_SERIES, TIANFU_SERIES, WUXING_JU_MAP, SIHUA_MAP, ZIWEI_POSITION,
    STAR_PROPERTIES, AUX_STAR_PROPERTIES,
)


# ============================================================================
# 常量测试
# ============================================================================

class TestConstants:
    def test_di_zhi(self):
        assert len(DI_ZHI) == 12
        expected = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        assert DI_ZHI == expected

    def test_tian_gan(self):
        assert len(TIAN_GAN) == 10
        expected = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        assert TIAN_GAN == expected

    def test_gong_names(self):
        assert len(GONG_NAMES) == 12
        assert GONG_NAMES[0] == "命宫"
        assert "夫妻" in GONG_NAMES
        assert "财帛" in GONG_NAMES
        assert "父母" in GONG_NAMES

    def test_gong_en(self):
        assert len(GONG_EN) == 12
        assert GONG_EN[0] == "ming"

    def test_wuxing_ju_map(self):
        assert len(WUXING_JU_MAP) == 60
        wuxing_set = set(v[0] for v in WUXING_JU_MAP.values())
        ju_set = set(v[1] for v in WUXING_JU_MAP.values())
        assert wuxing_set == {"金", "木", "水", "火", "土"}
        assert ju_set == {2, 3, 4, 5, 6}

    def test_sihua_map(self):
        assert len(SIHUA_MAP) == 10
        for gan in TIAN_GAN:
            assert gan in SIHUA_MAP
            assert len(SIHUA_MAP[gan]) == 4

    def test_ziwei_position(self):
        assert len(ZIWEI_POSITION) == 5
        assert set(ZIWEI_POSITION.keys()) == {2, 3, 4, 5, 6}
        for ju_num, table in ZIWEI_POSITION.items():
            assert len(table) == 30
            for day in range(1, 31):
                assert day in table
                assert 0 <= table[day] <= 11

    def test_ziwei_series(self):
        assert "紫微" in ZIWEI_SERIES
        assert "天机" in ZIWEI_SERIES
        assert "太阳" in ZIWEI_SERIES
        assert "武曲" in ZIWEI_SERIES
        assert "天同" in ZIWEI_SERIES
        assert "廉贞" in ZIWEI_SERIES

    def test_tianfu_series(self):
        assert "天府" in TIANFU_SERIES
        assert "太阴" in TIANFU_SERIES
        assert "贪狼" in TIANFU_SERIES
        assert "巨门" in TIANFU_SERIES
        assert "天相" in TIANFU_SERIES
        assert "天梁" in TIANFU_SERIES
        assert "七杀" in TIANFU_SERIES
        assert "破军" in TIANFU_SERIES


# ============================================================================
# 数据类测试
# ============================================================================

class TestDataclasses:
    def test_star_info_creation(self):
        star = StarInfo(
            name="紫微",
            level="主星",
            wuxing="己土",
            sheng_ke="",
            description="帝王星"
        )
        assert star.name == "紫微"
        assert star.level == "主星"
        assert star.wuxing == "己土"
        assert star.description == "帝王星"

    def test_star_info_defaults(self):
        star = StarInfo(name="test", level="test", wuxing="test")
        assert star.sheng_ke == ""
        assert star.description == ""

    def test_gong_info_creation(self):
        gong = GongInfo(
            name="命宫",
            en_name="ming",
            zhi="子",
            gan="甲",
        )
        assert gong.name == "命宫"
        assert gong.en_name == "ming"
        assert gong.zhi == "子"
        assert gong.gan == "甲"
        assert gong.stars == []
        assert gong.aux_stars == []
        assert gong.sihua == ""
        assert gong.daxian_range == ""

    def test_gong_info_with_stars(self):
        gong = GongInfo(
            name="命宫",
            en_name="ming",
            zhi="子",
            gan="甲",
            stars=["紫微"],
            aux_stars=["左辅"],
            sihua="紫微化权",
        )
        assert gong.stars == ["紫微"]
        assert gong.aux_stars == ["左辅"]
        assert gong.sihua == "紫微化权"

    def test_ziwei_chart_minimal(self):
        chart = ZiweiChart(
            year=2024, month=1, day=1, hour=0, minute=0, gender="male",
            year_gan="甲", year_zhi="辰",
            lunar_month=1, lunar_day=1, hour_zhi="子",
            ming_gong_index=0, shen_gong_index=0,
            wuxing_ju="水", wuxing_ju_num=2,
        )
        assert chart.year == 2024
        assert chart.month == 1
        assert chart.gongs == []
        assert chart.hua_lu == ""
        assert chart.daxian == []


# ============================================================================
# 基础日期工具方法测试
# ============================================================================

class TestDateUtils:
    def test_is_leap_year(self):
        assert ZiweiEngine._is_leap_year(2000) is True
        assert ZiweiEngine._is_leap_year(2004) is True
        assert ZiweiEngine._is_leap_year(2024) is True
        assert ZiweiEngine._is_leap_year(1900) is False
        assert ZiweiEngine._is_leap_year(2001) is False
        assert ZiweiEngine._is_leap_year(2023) is False
        assert ZiweiEngine._is_leap_year(2020) is True

    def test_days_in_month(self):
        assert ZiweiEngine._days_in_month(2024, 1) == 31
        assert ZiweiEngine._days_in_month(2024, 3) == 31
        assert ZiweiEngine._days_in_month(2024, 4) == 30
        assert ZiweiEngine._days_in_month(2024, 6) == 30
        assert ZiweiEngine._days_in_month(2024, 2) == 29
        assert ZiweiEngine._days_in_month(2023, 2) == 28
        assert ZiweiEngine._days_in_month(2023, 12) == 31

    def test_day_of_year_jan1(self):
        assert ZiweiEngine._day_of_year(2024, 1, 1) == 1
        assert ZiweiEngine._day_of_year(2023, 1, 1) == 1

    def test_day_of_year_feb1(self):
        assert ZiweiEngine._day_of_year(2024, 2, 1) == 32
        assert ZiweiEngine._day_of_year(2023, 2, 1) == 32

    def test_day_of_year_dec31(self):
        assert ZiweiEngine._day_of_year(2023, 12, 31) == 365
        assert ZiweiEngine._day_of_year(2024, 12, 31) == 366


# ============================================================================
# 农历转换测试
# ============================================================================

class TestLunarConversion:
    def test_lunar_leap_month(self):
        assert ZiweiEngine._lunar_leap_month(2023) == 2
        assert ZiweiEngine._lunar_leap_month(2025) == 6
        assert ZiweiEngine._lunar_leap_month(2028) == 5
        assert ZiweiEngine._lunar_leap_month(2024) == 0
        assert ZiweiEngine._lunar_leap_month(2022) == 0

    def test_lunar_year_days(self):
        days_2023 = ZiweiEngine._lunar_year_days(2023)
        assert days_2023 == 384
        days_2024 = ZiweiEngine._lunar_year_days(2024)
        assert days_2024 == 354
        days_2025 = ZiweiEngine._lunar_year_days(2025)
        assert days_2025 == 384
        days_2022 = ZiweiEngine._lunar_year_days(2022)
        assert days_2022 == 355

    def test_lunar_month_days(self):
        assert ZiweiEngine._lunar_month_days(2024, 1) == 29
        assert ZiweiEngine._lunar_month_days(2024, 2) == 30
        assert ZiweiEngine._lunar_month_days(2024, 3) == 29

    def test_solar_to_lunar_known_dates(self):
        ly, lm, ld, is_leap = ZiweiEngine.solar_to_lunar(2024, 2, 10)
        assert (ly, lm, ld) == (2024, 1, 1)
        assert is_leap is False

        ly, lm, ld, is_leap = ZiweiEngine.solar_to_lunar(2023, 1, 22)
        assert (ly, lm, ld) == (2023, 1, 1)
        assert is_leap is False

        ly, lm, ld, is_leap = ZiweiEngine.solar_to_lunar(2025, 1, 29)
        assert (ly, lm, ld) == (2025, 1, 1)
        assert is_leap is False

    def test_solar_to_lunar_out_of_range(self):
        ly, lm, ld, is_leap = ZiweiEngine.solar_to_lunar(1990, 1, 1)
        assert ly == 1989 or ly == 1990
        assert 1 <= lm <= 12
        assert 1 <= ld <= 30


# ============================================================================
# 干支与时辰测试
# ============================================================================

class TestGanzhi:
    def test_get_hour_zhi_edges(self):
        assert ZiweiEngine._get_hour_zhi(0, 0) == "子"
        assert ZiweiEngine._get_hour_zhi(1, 0) == "丑"
        assert ZiweiEngine._get_hour_zhi(12, 0) == "午"
        assert ZiweiEngine._get_hour_zhi(23, 0) == "子"

    def test_get_hour_zhi_all(self):
        assert ZiweiEngine._get_hour_zhi(23, 30) == "子"
        assert ZiweiEngine._get_hour_zhi(0, 30) == "子"
        assert ZiweiEngine._get_hour_zhi(1, 0) == "丑"
        assert ZiweiEngine._get_hour_zhi(2, 59) == "丑"
        assert ZiweiEngine._get_hour_zhi(3, 0) == "寅"
        assert ZiweiEngine._get_hour_zhi(5, 0) == "卯"
        assert ZiweiEngine._get_hour_zhi(7, 0) == "辰"
        assert ZiweiEngine._get_hour_zhi(9, 0) == "巳"
        assert ZiweiEngine._get_hour_zhi(11, 0) == "午"
        assert ZiweiEngine._get_hour_zhi(13, 0) == "未"
        assert ZiweiEngine._get_hour_zhi(15, 0) == "申"
        assert ZiweiEngine._get_hour_zhi(17, 0) == "酉"
        assert ZiweiEngine._get_hour_zhi(19, 0) == "戌"
        assert ZiweiEngine._get_hour_zhi(21, 0) == "亥"

    def test_get_year_ganzhi(self):
        gan, zhi = ZiweiEngine._get_year_ganzhi(2024)
        assert (gan, zhi) == ("甲", "辰")
        gan, zhi = ZiweiEngine._get_year_ganzhi(2000)
        assert (gan, zhi) == ("庚", "辰")
        gan, zhi = ZiweiEngine._get_year_ganzhi(2023)
        assert (gan, zhi) == ("癸", "卯")
        gan, zhi = ZiweiEngine._get_year_ganzhi(2025)
        assert (gan, zhi) == ("乙", "巳")

    def test_get_month_gan_wuhu_dun(self):
        assert ZiweiEngine._get_month_gan("甲", 2) == "丙"
        assert ZiweiEngine._get_month_gan("己", 2) == "丙"
        assert ZiweiEngine._get_month_gan("乙", 2) == "戊"
        assert ZiweiEngine._get_month_gan("庚", 2) == "戊"
        assert ZiweiEngine._get_month_gan("丙", 2) == "庚"
        assert ZiweiEngine._get_month_gan("辛", 2) == "庚"
        assert ZiweiEngine._get_month_gan("丁", 2) == "壬"
        assert ZiweiEngine._get_month_gan("壬", 2) == "壬"
        assert ZiweiEngine._get_month_gan("戊", 2) == "甲"
        assert ZiweiEngine._get_month_gan("癸", 2) == "甲"

        assert ZiweiEngine._get_month_gan("甲", 3) == "丁"
        assert ZiweiEngine._get_month_gan("甲", 4) == "戊"


# ============================================================================
# 命宫身宫测试
# ============================================================================

class TestMingGong:
    def test_get_ming_gong_returns_valid_indices(self):
        for month in range(1, 13):
            for zhi in DI_ZHI:
                ming_idx, shen_idx = ZiweiEngine._get_ming_gong(month, zhi)
                assert 0 <= ming_idx <= 11
                assert 0 <= shen_idx <= 11

    def test_get_12_gongs_ganzhi(self):
        gongs = ZiweiEngine._get_12_gongs_ganzhi(0, "甲")
        assert len(gongs) == 12
        for gan, zhi in gongs:
            assert gan in TIAN_GAN
            assert zhi in DI_ZHI
        zhis = [g[1] for g in gongs]
        assert len(set(zhis)) == 12


# ============================================================================
# 五行局测试
# ============================================================================

class TestWuxingJu:
    def test_get_wuxing_ju_known(self):
        assert ZiweiEngine._get_wuxing_ju("甲", "子") == ("金", 4)
        assert ZiweiEngine._get_wuxing_ju("丙", "寅") == ("火", 6)
        assert ZiweiEngine._get_wuxing_ju("戊", "辰") == ("木", 3)
        assert ZiweiEngine._get_wuxing_ju("庚", "午") == ("土", 5)
        assert ZiweiEngine._get_wuxing_ju("壬", "申") == ("金", 4)

    def test_get_wuxing_ju_default(self):
        result = ZiweiEngine._get_wuxing_ju("X", "Y")
        assert result == ("土", 5)


# ============================================================================
# 紫微星定位测试
# ============================================================================

class TestZiweiPos:
    def test_get_ziwei_pos_valid_range(self):
        for ju in [2, 3, 4, 5, 6]:
            for day in range(1, 31):
                pos = ZiweiEngine._get_ziwei_pos(ju, day)
                assert 0 <= pos <= 11

    def test_get_ziwei_pos_day_clamped(self):
        for ju in [2, 3, 4, 5, 6]:
            pos_30 = ZiweiEngine._get_ziwei_pos(ju, 30)
            pos_31 = ZiweiEngine._get_ziwei_pos(ju, 31)
            pos_50 = ZiweiEngine._get_ziwei_pos(ju, 50)
            assert pos_30 == pos_31 == pos_50

    def test_get_ziwei_pos_specific(self):
        assert ZiweiEngine._get_ziwei_pos(2, 1) == 1
        assert ZiweiEngine._get_ziwei_pos(2, 2) == 0
        assert ZiweiEngine._get_ziwei_pos(6, 1) == 1
        assert ZiweiEngine._get_ziwei_pos(6, 2) == 7


# ============================================================================
# 安星测试
# ============================================================================

class TestPlaceStars:
    def test_place_ziwei_series(self):
        stars = ZiweiEngine._place_ziwei_series(0)
        assert len(stars) == 6
        assert "紫微" in stars.values()
        assert "天机" in stars.values()
        assert "太阳" in stars.values()
        assert "武曲" in stars.values()
        assert "天同" in stars.values()
        assert "廉贞" in stars.values()
        for pos in stars:
            assert 0 <= pos <= 11

    def test_place_tianfu_series(self):
        stars = ZiweiEngine._place_tianfu_series(0)
        assert len(stars) == 8
        assert "天府" in stars.values()
        assert "太阴" in stars.values()
        assert "贪狼" in stars.values()
        assert "巨门" in stars.values()
        assert "天相" in stars.values()
        assert "天梁" in stars.values()
        assert "七杀" in stars.values()
        assert "破军" in stars.values()
        for pos in stars:
            assert 0 <= pos <= 11

    def test_place_aux_stars_structure(self):
        aux = ZiweiEngine._place_aux_stars("子", "子", 1, 1, "甲")
        assert isinstance(aux, dict)
        assert len(aux) == 12
        for i in range(12):
            assert i in aux
            assert isinstance(aux[i], list)

    def test_place_aux_stars_basic_stars(self):
        aux = ZiweiEngine._place_aux_stars("子", "子", 1, 1, "甲")
        all_stars = []
        for stars in aux.values():
            all_stars.extend(stars)
        assert "左辅" in all_stars
        assert "右弼" in all_stars
        assert "文昌" in all_stars
        assert "文曲" in all_stars
        assert "擎羊" in all_stars
        assert "陀罗" in all_stars
        assert "火星" in all_stars
        assert "铃星" in all_stars
        assert "地空" in all_stars
        assert "地劫" in all_stars
        assert "天马" in all_stars

    def test_place_aux_stars_kuiyue_all_gan(self):
        for gan in TIAN_GAN:
            aux = ZiweiEngine._place_aux_stars("子", "子", 1, 1, gan)
            all_stars = []
            for stars in aux.values():
                all_stars.extend(stars)
            assert "天魁" in all_stars, f"天魁 not found for gan {gan}"
            assert "天钺" in all_stars, f"天钺 not found for gan {gan}"
            assert "禄存" in all_stars, f"禄存 not found for gan {gan}"


# ============================================================================
# 四化测试
# ============================================================================

class TestSihua:
    def test_get_sihua_jia(self):
        lu, quan, ke, ji = ZiweiEngine._get_sihua("甲")
        assert (lu, quan, ke, ji) == ("廉贞", "破军", "武曲", "太阳")

    def test_get_sihua_yi(self):
        lu, quan, ke, ji = ZiweiEngine._get_sihua("乙")
        assert (lu, quan, ke, ji) == ("天机", "天梁", "紫微", "太阴")

    def test_get_sihua_bing(self):
        lu, quan, ke, ji = ZiweiEngine._get_sihua("丙")
        assert (lu, quan, ke, ji) == ("天同", "天机", "文昌", "廉贞")

    def test_get_sihua_unknown(self):
        assert ZiweiEngine._get_sihua("X") == ("", "", "", "")


# ============================================================================
# 命主身主测试
# ============================================================================

class TestMingShenZhu:
    def test_get_mingshen_zhu_all_zhi(self):
        valid_ming = {"贪狼", "巨门", "禄存", "文曲", "廉贞", "武曲", "破军"}
        valid_shen = {"火星", "天相", "天梁", "天同", "文昌", "天机"}
        for zhi in DI_ZHI:
            ming_zhu, shen_zhu = ZiweiEngine._get_mingshen_zhu(zhi, "子")
            assert ming_zhu in valid_ming
            assert shen_zhu in valid_shen


# ============================================================================
# 大限测试
# ============================================================================

class TestDaxian:
    def test_get_daxian_12_periods(self):
        daxian = ZiweiEngine._get_daxian(2, "male", "甲", 0)
        assert len(daxian) == 12
        for i, dx in enumerate(daxian):
            assert "gong_name" in dx
            assert "gong_index" in dx
            assert "age_range" in dx
            assert dx["start_age"] == 2 + i * 10
            assert dx["end_age"] == dx["start_age"] + 9

    def test_daxian_yang_male_shun(self):
        daxian = ZiweiEngine._get_daxian(4, "male", "甲", 2)
        assert daxian[0]["gong_index"] == 2
        assert daxian[1]["gong_index"] == 3
        assert daxian[2]["gong_index"] == 4

    def test_daxian_yin_female_shun(self):
        daxian = ZiweiEngine._get_daxian(4, "female", "乙", 2)
        assert daxian[0]["gong_index"] == 2
        assert daxian[1]["gong_index"] == 3

    def test_daxian_yang_female_ni(self):
        daxian = ZiweiEngine._get_daxian(4, "female", "甲", 2)
        assert daxian[0]["gong_index"] == 2
        assert daxian[1]["gong_index"] == 1
        assert daxian[2]["gong_index"] == 0

    def test_daxian_yin_male_ni(self):
        daxian = ZiweiEngine._get_daxian(4, "male", "乙", 2)
        assert daxian[0]["gong_index"] == 2
        assert daxian[1]["gong_index"] == 1

    def test_daxian_start_age(self):
        for ju in [2, 3, 4, 5, 6]:
            daxian = ZiweiEngine._get_daxian(ju, "male", "甲", 0)
            assert daxian[0]["start_age"] == ju


# ============================================================================
# 完整排盘集成测试
# ============================================================================

class TestCalcChart:
    def test_calc_chart_returns_ziwei_chart(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        assert isinstance(chart, ZiweiChart)

    def test_calc_chart_has_12_gongs(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        assert len(chart.gongs) == 12
        for gong in chart.gongs:
            assert isinstance(gong, GongInfo)
            assert gong.name in GONG_NAMES
            assert gong.zhi in DI_ZHI
            assert gong.gan in TIAN_GAN
            assert gong.en_name in GONG_EN

    def test_calc_chart_has_12_daxian(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        assert len(chart.daxian) == 12

    def test_calc_chart_sihua_set(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        assert chart.hua_lu != ""
        assert chart.hua_quan != ""
        assert chart.hua_ke != ""
        assert chart.hua_ji != ""

    def test_calc_chart_ming_shen_zhu(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        assert chart.ming_zhu != ""
        assert chart.shen_zhu != ""

    def test_calc_chart_male(self):
        chart = ZiweiEngine.calc_chart(1990, 6, 15, 8, 30, "male")
        assert chart.gender == "male"
        assert len(chart.gongs) == 12

    def test_calc_chart_female(self):
        chart = ZiweiEngine.calc_chart(1990, 6, 15, 8, 30, "female")
        assert chart.gender == "female"
        assert len(chart.gongs) == 12

    def test_calc_chart_hour_zero(self):
        chart = ZiweiEngine.calc_chart(2000, 1, 1, 0, 0, "male")
        assert chart.hour_zhi == "子"
        assert len(chart.gongs) == 12

    def test_calc_chart_various_dates(self):
        test_dates = [
            (2000, 1, 1, 0, 0, "male"),
            (2010, 5, 20, 14, 30, "female"),
            (2020, 8, 8, 20, 0, "male"),
            (2030, 12, 25, 6, 15, "female"),
            (2040, 3, 15, 18, 45, "male"),
        ]
        for y, m, d, h, mi, g in test_dates:
            chart = ZiweiEngine.calc_chart(y, m, d, h, mi, g)
            assert len(chart.gongs) == 12
            assert len(chart.daxian) == 12

    def test_gongs_have_en_name(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        for i, gong in enumerate(chart.gongs):
            assert gong.en_name == GONG_EN[i]

    def test_sihua_tags_assigned(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        has_sihua = any(g.sihua for g in chart.gongs)
        assert has_sihua


# ============================================================================
# to_dict 测试
# ============================================================================

class TestToDict:
    def test_to_dict_structure(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        d = ZiweiEngine.to_dict(chart)
        assert "input" in d
        assert "ming_gong" in d
        assert "shen_gong" in d
        assert "wuxing_ju" in d
        assert "ming_zhu" in d
        assert "shen_zhu" in d
        assert "sihua" in d
        assert "gongs" in d
        assert "daxian" in d

    def test_to_dict_gongs_count(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        d = ZiweiEngine.to_dict(chart)
        assert len(d["gongs"]) == 12
        for g in d["gongs"]:
            assert "name" in g
            assert "en_name" in g
            assert "ganzhi" in g
            assert "main_stars" in g
            assert "aux_stars" in g
            assert "sihua" in g

    def test_to_dict_sihua_keys(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        d = ZiweiEngine.to_dict(chart)
        assert "化禄" in d["sihua"]
        assert "化权" in d["sihua"]
        assert "化科" in d["sihua"]
        assert "化忌" in d["sihua"]


# ============================================================================
# format_text 测试
# ============================================================================

class TestFormatText:
    def test_format_text_returns_string(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        text = ZiweiEngine.format_text(chart)
        assert isinstance(text, str)
        assert len(text) > 100

    def test_format_text_contains_title(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        text = ZiweiEngine.format_text(chart)
        assert "紫微斗数命盘" in text

    def test_format_text_contains_gong_names(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        text = ZiweiEngine.format_text(chart)
        for name in GONG_NAMES:
            assert name in text, f"Missing gong name: {name}"

    def test_format_text_multiline(self):
        chart = ZiweiEngine.calc_chart(2024, 2, 10, 12, 0, "male")
        text = ZiweiEngine.format_text(chart)
        lines = text.split("\n")
        assert len(lines) > 20


# ============================================================================
# 便捷函数测试
# ============================================================================

class TestConvenience:
    def test_calc_ziwei(self):
        chart = calc_ziwei(2024, 2, 10, 12, 0, "male")
        assert isinstance(chart, ZiweiChart)
        assert len(chart.gongs) == 12

    def test_ziwei_to_dict(self):
        chart = calc_ziwei(2024, 2, 10, 12, 0, "male")
        d = ziwei_to_dict(chart)
        assert isinstance(d, dict)
        assert "gongs" in d
        assert len(d["gongs"]) == 12


# ============================================================================
# 星曜属性测试
# ============================================================================

class TestStarProperties:
    def test_star_properties_completeness(self):
        main_stars = ["紫微", "天机", "太阳", "武曲", "天同", "廉贞",
                       "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"]
        assert len(STAR_PROPERTIES) == 14
        for star in main_stars:
            assert star in STAR_PROPERTIES
            assert "level" in STAR_PROPERTIES[star]
            assert "wuxing" in STAR_PROPERTIES[star]
            assert "desc" in STAR_PROPERTIES[star]
            assert STAR_PROPERTIES[star]["level"] == "主星"

    def test_aux_star_properties_completeness(self):
        aux_stars = ["左辅", "右弼", "文昌", "文曲", "天魁", "天钺", "禄存",
                      "擎羊", "陀罗", "火星", "铃星", "地空", "地劫", "天马"]
        assert len(AUX_STAR_PROPERTIES) == 14
        for star in aux_stars:
            assert star in AUX_STAR_PROPERTIES
            assert "level" in AUX_STAR_PROPERTIES[star]
            assert "wuxing" in AUX_STAR_PROPERTIES[star]
            assert "desc" in AUX_STAR_PROPERTIES[star]
            assert AUX_STAR_PROPERTIES[star]["level"] == "辅星"
