#!/usr/bin/env python3
"""
test_shensha_engine.py — 神煞推算引擎全面单元测试
覆盖：常量、枚举、辅助函数、年月日时柱神煞推算、结果合并、摘要统计、文本/JSON报告、引擎类、边缘情况
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.shensha_engine import (
    DIZHI,
    DZ_YINYANG,
    TIANGAN,
    TG_YINYANG,
    ZHIGAN_MAIN,
    Shensha,
    ShenshaCategory,
    ShenshaEngine,
    ShenshaResult,
    _SHENSHA_INFO,
    _calc_day_shensha,
    _calc_hour_shensha,
    _calc_month_shensha,
    _calc_year_shensha,
    _get_dizhi_index,
    _get_tiangan_index,
    _is_yang,
    _is_yang_zhi,
    calc_all_shensha,
)

TEST_PILLARS = {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"}

YANG_GAN = {"甲", "丙", "戊", "庚", "壬"}
YIN_GAN = {"乙", "丁", "己", "辛", "癸"}

YANG_ZHI = {"子", "寅", "辰", "未", "酉", "亥"}
YIN_ZHI = {"丑", "卯", "巳", "午", "申", "戌"}

KUIGANG_DAYS = ["庚辰", "壬辰", "戊戌", "庚戌"]
YIN_CUO_DAYS = ["庚子", "辛丑", "壬寅", "癸卯", "甲辰", "乙巳",
                "丙午", "丁未", "戊申", "己酉"]
YANG_CUO_DAYS = ["甲子", "乙丑", "丙寅", "丁卯", "戊辰", "己巳",
                 "庚午", "辛未", "壬申", "癸酉"]
YANG_REN_COMBOS = {"甲卯", "丙午", "戊午", "庚酉", "壬子"}

REQUIRED_FIELDS = {"name", "pillar", "source", "desc", "cat", "level"}


# ════════════════════════════════════════
# 1. 常量测试
# ════════════════════════════════════════

class TestConstants:
    """测试基础常量"""

    def test_tiangan_count(self):
        assert len(TIANGAN) == 10

    def test_tiangan_values(self):
        assert TIANGAN == ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

    def test_dizhi_count(self):
        assert len(DIZHI) == 12

    def test_dizhi_values(self):
        assert DIZHI == ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    def test_tg_yinyang_length(self):
        assert len(TG_YINYANG) == 10

    def test_dz_yinyang_length(self):
        assert len(DZ_YINYANG) == 12

    def test_zhigan_main_has_all_12(self):
        assert len(ZHIGAN_MAIN) == 12
        for dz in DIZHI:
            assert dz in ZHIGAN_MAIN


# ════════════════════════════════════════
# 2. 枚举测试
# ════════════════════════════════════════

class TestEnums:
    """测试枚举类型"""

    def test_shensha_category_six_values(self):
        cats = list(ShenshaCategory)
        assert len(cats) == 6
        cat_values = {c.value for c in cats}
        assert cat_values == {"吉神", "吉", "平", "凶", "大凶", "吉凶"}

    def test_shensha_key_entries_exist(self):
        expected = {
            Shensha.TIAN_DE, Shensha.YUE_DE, Shensha.TIAN_E,
            Shensha.YI_MA, Shensha.HUA_GAI, Shensha.TAO_HUA,
            Shensha.WEN_CHANG, Shensha.TAI_JI, Shensha.KUI_GANG,
            Shensha.YIN_CHA, Shensha.YANG_CHA, Shensha.JIE_SHA,
            Shensha.WANG_SHEN, Shensha.GE_SHENG, Shensha.GUA_SUI,
            Shensha.WU_QU, Shensha.YANG_MA, Shensha.SHI_CHA,
        }
        for e in expected:
            assert isinstance(e, Shensha)

    def test_shensha_values_are_strings(self):
        for s in Shensha:
            assert isinstance(s.value, str)
            assert len(s.value) > 0


# ════════════════════════════════════════
# 3. _SHENSHA_INFO 测试
# ════════════════════════════════════════

class TestShenshaInfo:
    """测试神煞详情数据表"""

    @pytest.mark.parametrize("name", [
        "天德", "月德", "天乙贵人", "太极贵人", "文昌", "驿马", "华盖",
        "桃花", "魁罡", "阴错", "阳错", "劫煞", "亡神", "孤辰", "寡宿",
        "五鬼", "阳刃", "死亡", "财禄", "时冲",
    ])
    def test_major_shensha_info_exists(self, name):
        assert name in _SHENSHA_INFO, f"{name} 不在 _SHENSHA_INFO 中"

    def test_shensha_info_structure(self):
        for name, info in _SHENSHA_INFO.items():
            assert "cat" in info, f"{name} 缺少 cat"
            assert "level" in info, f"{name} 缺少 level"
            assert "desc" in info, f"{name} 缺少 desc"
            assert isinstance(info["level"], int)

    def test_shensha_info_categories_valid(self):
        valid_cats = {c.value for c in ShenshaCategory}
        for name, info in _SHENSHA_INFO.items():
            assert info["cat"] in valid_cats, f"{name} 的 cat={info['cat']} 非法"


# ════════════════════════════════════════
# 4. 辅助函数测试
# ════════════════════════════════════════

class TestHelperFunctions:
    """测试辅助函数"""

    @pytest.mark.parametrize("tg,idx", [
        ("甲", 0), ("乙", 1), ("丙", 2), ("丁", 3), ("戊", 4),
        ("己", 5), ("庚", 6), ("辛", 7), ("壬", 8), ("癸", 9),
    ])
    def test_get_tiangan_index(self, tg, idx):
        assert _get_tiangan_index(tg) == idx

    @pytest.mark.parametrize("dz,idx", [
        ("子", 0), ("丑", 1), ("寅", 2), ("卯", 3), ("辰", 4),
        ("巳", 5), ("午", 6), ("未", 7), ("申", 8), ("酉", 9),
        ("戌", 10), ("亥", 11),
    ])
    def test_get_dizhi_index(self, dz, idx):
        assert _get_dizhi_index(dz) == idx

    @pytest.mark.parametrize("tg", list(YANG_GAN))
    def test_is_yang_true(self, tg):
        assert _is_yang(tg) is True

    @pytest.mark.parametrize("tg", list(YIN_GAN))
    def test_is_yang_false(self, tg):
        assert _is_yang(tg) is False

    @pytest.mark.parametrize("dz", list(YANG_ZHI))
    def test_is_yang_zhi_true(self, dz):
        assert _is_yang_zhi(dz) is True

    @pytest.mark.parametrize("dz", list(YIN_ZHI))
    def test_is_yang_zhi_false(self, dz):
        assert _is_yang_zhi(dz) is False


# ════════════════════════════════════════
# 5. 年柱神煞测试
# ════════════════════════════════════════

def _check_fields(shen_dict, expected_name):
    """校验单个神煞字典字段完整性"""
    assert REQUIRED_FIELDS.issubset(shen_dict.keys()), \
        f"{expected_name} 缺少字段: {REQUIRED_FIELDS - shen_dict.keys()}"
    assert shen_dict["name"] == expected_name
    assert shen_dict["pillar"] == "年柱"
    assert isinstance(shen_dict["level"], int)


class TestYearShensha:
    """测试 _calc_year_shensha"""

    @pytest.mark.parametrize("zhi", DIZHI)
    def test_tiande_present_for_all_zhi(self, zhi):
        """天德：所有12年支都应出现（修复后行为）"""
        result = _calc_year_shensha("甲", zhi)
        assert "天德" in result, f"年支{zhi} 应带天德"
        _check_fields(result["天德"], "天德")
        assert result["天德"]["cat"] == "吉神"

    @pytest.mark.parametrize("zhi", DIZHI)
    def test_yuede_present_for_all_zhi(self, zhi):
        """月德：所有12年支都应出现（修复后行为）"""
        result = _calc_year_shensha("甲", zhi)
        assert "月德" in result, f"年支{zhi} 应带月德"
        _check_fields(result["月德"], "月德")
        assert result["月德"]["cat"] == "吉神"

    @pytest.mark.parametrize("gan", TIANGAN)
    def test_tianyi_present_for_all_gan(self, gan):
        """天乙贵人：所有10年干都应出现"""
        result = _calc_year_shensha(gan, "子")
        assert "天乙贵人" in result, f"年干{gan} 应带天乙贵人"
        _check_fields(result["天乙贵人"], "天乙贵人")

    @pytest.mark.parametrize("gan,zhi,expected", [
        ("甲", "子", True), ("乙", "丑", True), ("丙", "寅", True),
        ("丁", "卯", True), ("戊", "未", True), ("己", "申", True),
        ("庚", "酉", True), ("辛", "戌", True), ("壬", "亥", True),
        ("癸", "午", True),
        ("甲", "丑", False), ("丙", "子", False), ("庚", "卯", False),
    ])
    def test_taiji_presence(self, gan, zhi, expected):
        """太极贵人：只有年干映射到年支时才出现"""
        result = _calc_year_shensha(gan, zhi)
        if expected:
            assert "太极贵人" in result
            _check_fields(result["太极贵人"], "太极贵人")
        else:
            assert "太极贵人" not in result

    @pytest.mark.parametrize("zhi", DIZHI)
    def test_jiesha_present_for_all_zhi(self, zhi):
        """劫煞：所有12年支都应出现"""
        result = _calc_year_shensha("甲", zhi)
        assert "劫煞" in result
        _check_fields(result["劫煞"], "劫煞")
        assert result["劫煞"]["cat"] == "凶"

    @pytest.mark.parametrize("zhi", DIZHI)
    def test_wangshen_present_for_all_zhi(self, zhi):
        """亡神：所有12年支都应出现"""
        result = _calc_year_shensha("甲", zhi)
        assert "亡神" in result
        _check_fields(result["亡神"], "亡神")

    @pytest.mark.parametrize("zhi", DIZHI)
    def test_guchen_guasu_present_for_all_zhi(self, zhi):
        """孤辰+寡宿：所有12年支都应出现"""
        result = _calc_year_shensha("甲", zhi)
        assert "孤辰" in result, f"年支{zhi} 应带孤辰"
        assert "寡宿" in result, f"年支{zhi} 应带寡宿"
        _check_fields(result["孤辰"], "孤辰")
        _check_fields(result["寡宿"], "寡宿")

    @pytest.mark.parametrize("zhi", DIZHI)
    def test_wugui_present_for_all_zhi(self, zhi):
        """五鬼：所有12年支都应出现"""
        result = _calc_year_shensha("甲", zhi)
        assert "五鬼" in result
        _check_fields(result["五鬼"], "五鬼")

    @pytest.mark.parametrize("ganzhi", ["甲卯", "丙午", "戊午", "庚酉", "壬子"])
    def test_yangren_five_combos(self, ganzhi):
        """阳刃：仅5个特定组合"""
        gan, zhi = ganzhi[0], ganzhi[1]
        result = _calc_year_shensha(gan, zhi)
        assert "阳刃" in result
        _check_fields(result["阳刃"], "阳刃")
        assert result["阳刃"]["cat"] == "凶"

    @pytest.mark.parametrize("gan,zhi", [
        ("甲", "子"), ("乙", "卯"), ("丙", "子"), ("丁", "卯"),
        ("戊", "子"), ("己", "卯"), ("庚", "卯"), ("辛", "午"),
        ("壬", "卯"), ("癸", "子"),
    ])
    def test_yangren_absent_for_non_combos(self, gan, zhi):
        """阳刃：非5个组合不应出现"""
        result = _calc_year_shensha(gan, zhi)
        assert "阳刃" not in result

    def test_all_fields_present_in_each_shensha(self):
        """每个年柱神煞都有完整字段"""
        for zhi in DIZHI:
            result = _calc_year_shensha("甲", zhi)
            for name, info in result.items():
                assert REQUIRED_FIELDS.issubset(info.keys()), \
                    f"{name} (年支{zhi}) 缺少字段: {REQUIRED_FIELDS - info.keys()}"


# ════════════════════════════════════════
# 6. 月柱神煞测试
# ════════════════════════════════════════

class TestMonthShensha:
    """测试 _calc_month_shensha"""

    @pytest.mark.parametrize("zhi", DIZHI)
    def test_yima_present_for_all_zhi(self, zhi):
        """驿马：所有12月支都应出现"""
        result = _calc_month_shensha("甲", zhi)
        assert "驿马" in result
        assert result["驿马"]["pillar"] == "月柱"
        assert result["驿马"]["cat"] == "吉"

    @pytest.mark.parametrize("zhi", DIZHI)
    def test_huagai_present_for_all_zhi(self, zhi):
        """华盖：所有12月支都应出现"""
        result = _calc_month_shensha("甲", zhi)
        assert "华盖" in result
        assert result["华盖"]["pillar"] == "月柱"

    @pytest.mark.parametrize("gan,zhi,expected", [
        ("甲", "巳", True), ("乙", "午", True), ("丙", "申", True),
        ("丁", "酉", True), ("戊", "申", True), ("己", "酉", True),
        ("庚", "亥", True), ("辛", "子", True), ("壬", "寅", True),
        ("癸", "卯", True),
        ("甲", "子", False), ("乙", "巳", False), ("丙", "午", False),
    ])
    def test_wenchang_presence(self, gan, zhi, expected):
        """文昌：只有月干映射到月支时才出现"""
        result = _calc_month_shensha(gan, zhi)
        if expected:
            assert "文昌" in result
            assert result["文昌"]["cat"] == "吉神"
        else:
            assert "文昌" not in result


# ════════════════════════════════════════
# 7. 日柱神煞测试
# ════════════════════════════════════════

class TestDayShensha:
    """测试 _calc_day_shensha"""

    @pytest.mark.parametrize("zhi", DIZHI)
    def test_taohua_present_for_all_zhi(self, zhi):
        """桃花：所有12日支都应出现"""
        result = _calc_day_shensha("甲", zhi)
        assert "桃花" in result
        assert result["桃花"]["pillar"] == "日柱"
        assert result["桃花"]["cat"] == "凶"

    @pytest.mark.parametrize("day", KUIGANG_DAYS)
    def test_kuigang_four_days(self, day):
        """魁罡：恰好4天"""
        gan, zhi = day[0], day[1]
        result = _calc_day_shensha(gan, zhi)
        assert "魁罡" in result
        assert result["魁罡"]["cat"] == "平"

    def test_kuigang_exactly_four(self):
        """魁罡：遍历所有60甲子组合，恰好4天命中"""
        kuigang_count = 0
        for gan in TIANGAN:
            for zhi in DIZHI:
                result = _calc_day_shensha(gan, zhi)
                if "魁罡" in result:
                    kuigang_count += 1
                    assert gan + zhi in KUIGANG_DAYS
        assert kuigang_count == 4

    @pytest.mark.parametrize("day", YIN_CUO_DAYS)
    def test_yin_cuo_ten_days(self, day):
        """阴错：10天"""
        gan, zhi = day[0], day[1]
        result = _calc_day_shensha(gan, zhi)
        assert "阴错" in result
        assert result["阴错"]["cat"] == "凶"

    def test_yin_cuo_exactly_ten(self):
        """阴错：恰好10天命中"""
        count = 0
        for gan in TIANGAN:
            for zhi in DIZHI:
                result = _calc_day_shensha(gan, zhi)
                if "阴错" in result:
                    count += 1
                    assert gan + zhi in YIN_CUO_DAYS
        assert count == 10

    @pytest.mark.parametrize("day", YANG_CUO_DAYS)
    def test_yang_cuo_ten_days(self, day):
        """阳错：10天"""
        gan, zhi = day[0], day[1]
        result = _calc_day_shensha(gan, zhi)
        assert "阳错" in result

    def test_yang_cuo_exactly_ten(self):
        """阳错：恰好10天命中"""
        count = 0
        for gan in TIANGAN:
            for zhi in DIZHI:
                result = _calc_day_shensha(gan, zhi)
                if "阳错" in result:
                    count += 1
                    assert gan + zhi in YANG_CUO_DAYS
        assert count == 10

    @pytest.mark.parametrize("gan,zhi,expected", [
        ("甲", "子", True), ("乙", "丑", True), ("丙", "寅", True),
        ("丁", "卯", True), ("戊", "未", True), ("己", "申", True),
        ("庚", "酉", True), ("辛", "戌", True), ("壬", "亥", True),
        ("癸", "午", True),
        ("甲", "寅", False), ("乙", "子", False),
    ])
    def test_taiji_day_presence(self, gan, zhi, expected):
        """太极贵人（日）：日干映射到日支时才出现"""
        result = _calc_day_shensha(gan, zhi)
        if expected:
            assert "太极贵人" in result
        else:
            assert "太极贵人" not in result

    @pytest.mark.parametrize("gan,zhi,expected", [
        ("甲", "丑", True), ("甲", "未", True), ("甲", "子", False),
        ("戊", "丑", True), ("戊", "未", True),
        ("乙", "子", True), ("乙", "申", True), ("乙", "丑", False),
        ("己", "子", True), ("己", "申", True),
        ("丙", "亥", True), ("丙", "酉", True),
        ("丁", "亥", True), ("丁", "酉", True),
        ("壬", "卯", True), ("壬", "巳", True),
        ("癸", "卯", True), ("癸", "巳", True),
        ("庚", "寅", True), ("庚", "午", True),
        ("辛", "寅", True), ("辛", "午", True),
    ])
    def test_tianyi_day_presence(self, gan, zhi, expected):
        """天乙贵人（日）：日支在贵人对中才出现"""
        result = _calc_day_shensha(gan, zhi)
        if expected:
            assert "天乙贵人" in result
            assert result["天乙贵人"]["cat"] == "吉神"
        else:
            assert "天乙贵人" not in result

    @pytest.mark.parametrize("zhi", ["亥", "子"])
    def test_cailu_present(self, zhi):
        """财禄：日支为亥/子"""
        result = _calc_day_shensha("甲", zhi)
        assert "财禄" in result
        assert result["财禄"]["cat"] == "吉神"

    @pytest.mark.parametrize("zhi", [dz for dz in DIZHI if dz not in {"亥", "子"}])
    def test_cailu_absent(self, zhi):
        """财禄：非亥/子日支不出现"""
        result = _calc_day_shensha("甲", zhi)
        assert "财禄" not in result

    @pytest.mark.parametrize("zhi", ["酉", "戌"])
    def test_siwang_present(self, zhi):
        """死亡：日支为酉/戌"""
        result = _calc_day_shensha("甲", zhi)
        assert "死亡" in result
        assert result["死亡"]["cat"] == "大凶"

    @pytest.mark.parametrize("zhi", [dz for dz in DIZHI if dz not in {"酉", "戌"}])
    def test_siwang_absent(self, zhi):
        """死亡：非酉/戌日支不出现"""
        result = _calc_day_shensha("甲", zhi)
        assert "死亡" not in result


# ════════════════════════════════════════
# 8. 时柱神煞测试
# ════════════════════════════════════════

class TestHourShensha:
    """测试 _calc_hour_shensha"""

    @pytest.mark.parametrize("zhi", ["子", "午"])
    def test_shichong_present(self, zhi):
        """时冲：时支为子或午"""
        result = _calc_hour_shensha("甲", zhi, "甲")
        assert "时冲" in result
        assert result["时冲"]["cat"] == "凶"

    @pytest.mark.parametrize("zhi", [dz for dz in DIZHI if dz not in {"子", "午"}])
    def test_shichong_absent(self, zhi):
        """时冲：非子/午不出现"""
        result = _calc_hour_shensha("甲", zhi, "甲")
        assert "时冲" not in result

    @pytest.mark.parametrize("zhi", DIZHI)
    def test_taohua_hour_present_for_all_zhi(self, zhi):
        """桃花_时：所有12时支都应出现（键名桃花_时，name为桃花）"""
        result = _calc_hour_shensha("甲", zhi, "甲")
        assert "桃花_时" in result
        assert result["桃花_时"]["name"] == "桃花"
        assert result["桃花_时"]["pillar"] == "时柱"


# ════════════════════════════════════════
# 9. ShenshaResult 测试
# ════════════════════════════════════════

class TestShenshaResult:
    """测试 ShenshaResult 数据类"""

    @pytest.fixture
    def result(self):
        return calc_all_shensha(TEST_PILLARS)

    def test_all_shensha_merges_four_pillars(self, result):
        """all_shensha 合并四柱神煞"""
        all_s = result.all_shensha
        for key in result.year_shens:
            assert key in all_s
        for key in result.month_shens:
            assert key in all_s
        for key in result.day_shens:
            assert key in all_s
        for key in result.hour_shens:
            assert key in all_s

    def test_all_shensha_no_duplicate_pillars_lost(self, result):
        """all_shensha 后出现的柱覆盖同名键（预期行为）"""
        all_s = result.all_shensha
        assert isinstance(all_s, dict)
        total_expected = (
            len(result.year_shens) + len(result.month_shens) +
            len(result.day_shens) + len(result.hour_shens)
        )
        # 桃花可能在日/时柱重复，因此 all_shensha 数量可能 <= 四柱之和
        assert len(all_s) <= total_expected

    def test_summary_has_total(self, result):
        s = result.summary
        assert "total" in s
        assert s["total"] == len(result.all_shensha)

    def test_summary_by_category(self, result):
        s = result.summary
        assert "by_category" in s
        assert isinstance(s["by_category"], dict)
        assert sum(s["by_category"].values()) == s["total"]

    def test_summary_top_jixiong(self, result):
        s = result.summary
        assert "top_jixiong" in s
        assert isinstance(s["top_jixiong"], list)
        for item in s["top_jixiong"]:
            assert "name" in item
            assert "pillar" in item

    def test_top_by_cat_sorted_and_limited(self, result):
        """_top_by_cat 返回按 level 降序、最多 limit 条"""
        items = result._top_by_cat("吉神", limit=2)
        assert len(items) <= 2
        levels = []
        for item in items:
            name = item["name"]
            info = result.all_shensha.get(name) or _find_by_name(result, name)
            if info:
                levels.append(info["level"])
        assert levels == sorted(levels, reverse=True)

    def test_text_report_multiline(self, result):
        report = result.text_report()
        assert isinstance(report, str)
        assert "神煞推算报告" in report
        assert "年柱" in report or len(result.year_shens) == 0
        assert "月柱" in report or len(result.month_shens) == 0
        assert "日柱" in report or len(result.day_shens) == 0
        assert "时柱" in report or len(result.hour_shens) == 0
        assert "总计" in report
        lines = report.split("\n")
        assert len(lines) >= 5

    def test_json_report_structure(self, result):
        jr = result.json_report()
        assert isinstance(jr, dict)
        assert "pillars" in jr
        assert "year_shensha" in jr
        assert "month_shensha" in jr
        assert "day_shensha" in jr
        assert "hour_shensha" in jr
        assert "summary" in jr
        assert jr["pillars"] == TEST_PILLARS
        assert jr["summary"]["total"] == len(result.all_shensha)


def _find_by_name(result, name):
    """在四柱神煞中按 name 字段查找（处理桃花在日/时重复的情况）"""
    for collection in [result.year_shens, result.month_shens,
                       result.day_shens, result.hour_shens]:
        for k, v in collection.items():
            if v.get("name") == name:
                return v
    return None


# ════════════════════════════════════════
# 10. calc_all_shensha 测试
# ════════════════════════════════════════

class TestCalcAllShensha:
    """测试 calc_all_shensha 主函数"""

    def test_returns_shensha_result(self):
        result = calc_all_shensha(TEST_PILLARS)
        assert isinstance(result, ShenshaResult)

    def test_known_cli_pillars(self):
        """CLI测试用例：庚午壬午辛亥癸巳"""
        result = calc_all_shensha(TEST_PILLARS)
        assert result.pillars == TEST_PILLARS
        # 年柱：庚年午支
        assert len(result.year_shens) > 0
        # 月柱：壬年午支
        assert len(result.month_shens) > 0
        # 日柱：辛日亥支
        assert len(result.day_shens) > 0
        # 时柱：癸时巳支
        assert len(result.hour_shens) > 0

    def test_pillars_correctly_parsed(self):
        """四柱干支正确拆解"""
        pillars = {"year": "甲子", "month": "乙丑", "day": "丙寅", "hour": "丁卯"}
        result = calc_all_shensha(pillars)
        assert result.pillars == pillars

    def test_year_shens_populated(self):
        result = calc_all_shensha(TEST_PILLARS)
        assert isinstance(result.year_shens, dict)
        assert len(result.year_shens) > 0

    def test_month_shens_populated(self):
        result = calc_all_shensha(TEST_PILLARS)
        assert isinstance(result.month_shens, dict)
        assert len(result.month_shens) > 0

    def test_day_shens_populated(self):
        result = calc_all_shensha(TEST_PILLARS)
        assert isinstance(result.day_shens, dict)
        assert len(result.day_shens) > 0

    def test_hour_shens_populated(self):
        result = calc_all_shensha(TEST_PILLARS)
        assert isinstance(result.hour_shens, dict)
        assert len(result.hour_shens) > 0

    def test_cli_test_case_expected_structure(self):
        """CLI已知命盘输出结构验证"""
        result = calc_all_shensha(TEST_PILLARS)
        all_s = result.all_shensha
        # 庚午年，午为阳刃不在（庚刃在酉），应带劫煞/亡神/孤辰/寡宿/五鬼
        assert "劫煞" in result.year_shens
        assert "亡神" in result.year_shens
        assert "孤辰" in result.year_shens
        assert "寡宿" in result.year_shens
        assert "五鬼" in result.year_shens
        # 壬午月：午支有驿马、华盖
        assert "驿马" in result.month_shens
        assert "华盖" in result.month_shens
        # 辛亥日：亥支有桃花、财禄
        assert "桃花" in result.day_shens
        assert "财禄" in result.day_shens
        # 癸巳时：巳支有桃花_时，无时冲（巳不是子午）
        assert "桃花_时" in result.hour_shens
        assert "时冲" not in result.hour_shens


# ════════════════════════════════════════
# 11. ShenshaEngine 类测试
# ════════════════════════════════════════

class TestShenshaEngineClass:
    """测试 ShenshaEngine 包装类"""

    def test_compute_returns_result(self):
        result = ShenshaEngine.compute(TEST_PILLARS)
        assert isinstance(result, ShenshaResult)
        assert result.pillars == TEST_PILLARS

    def test_compute_matches_calc_all(self):
        r1 = ShenshaEngine.compute(TEST_PILLARS)
        r2 = calc_all_shensha(TEST_PILLARS)
        assert r1.all_shensha == r2.all_shensha

    def test_compute_single_basic(self):
        """detail=basic 返回 JSON 报告"""
        report = ShenshaEngine.compute_single("辛", TEST_PILLARS, detail="basic")
        assert isinstance(report, dict)
        assert "pillars" in report
        assert "summary" in report

    def test_compute_single_summary(self):
        """detail=summary 返回摘要"""
        report = ShenshaEngine.compute_single("辛", TEST_PILLARS, detail="summary")
        assert isinstance(report, dict)
        assert "total" in report
        assert "by_category" in report

    def test_compute_single_full_default(self):
        """detail=full（非basic/summary）返回完整报告"""
        report = ShenshaEngine.compute_single("辛", TEST_PILLARS, detail="full")
        assert isinstance(report, dict)
        assert "year_shensha" in report

    def test_compute_single_default_detail_is_basic(self):
        """默认 detail=basic"""
        report = ShenshaEngine.compute_single("辛", TEST_PILLARS)
        assert isinstance(report, dict)
        assert "pillars" in report


# ════════════════════════════════════════
# 12. 边缘情况测试
# ════════════════════════════════════════

class TestEdgeCases:
    """边缘情况测试"""

    @pytest.mark.parametrize("gan", TIANGAN)
    @pytest.mark.parametrize("zhi", DIZHI)
    def test_all_60_year_combinations_no_crash(self, gan, zhi):
        """所有60个年柱组合不崩溃"""
        result = _calc_year_shensha(gan, zhi)
        assert isinstance(result, dict)
        for name, info in result.items():
            assert "name" in info
            assert "cat" in info

    @pytest.mark.parametrize("day", KUIGANG_DAYS)
    def test_all_kuigang_days(self, day):
        """4个魁罡日逐一验证"""
        gan, zhi = day[0], day[1]
        result = _calc_day_shensha(gan, zhi)
        assert "魁罡" in result
        assert result["魁罡"]["pillar"] == "日柱"

    @pytest.mark.parametrize("day", YIN_CUO_DAYS)
    def test_all_yin_cuo_days(self, day):
        gan, zhi = day[0], day[1]
        result = _calc_day_shensha(gan, zhi)
        assert "阴错" in result

    @pytest.mark.parametrize("day", YANG_CUO_DAYS)
    def test_all_yang_cuo_days(self, day):
        gan, zhi = day[0], day[1]
        result = _calc_day_shensha(gan, zhi)
        assert "阳错" in result

    def test_hour_with_shichong(self):
        """时柱带子/午 → 有时冲"""
        pillars = {"year": "甲子", "month": "丙寅", "day": "甲午", "hour": "甲子"}
        result = calc_all_shensha(pillars)
        assert "时冲" in result.hour_shens

    def test_hour_without_shichong(self):
        """时柱不带子/午 → 无时冲"""
        pillars = {"year": "甲子", "month": "丙寅", "day": "甲午", "hour": "甲寅"}
        result = calc_all_shensha(pillars)
        assert "时冲" not in result.hour_shens

    def test_multiple_test_cases_from_cli(self):
        """CLI中列出的更多测试用例"""
        test_cases = [
            {"year": "甲辰", "month": "丁卯", "day": "庚子", "hour": "丙子"},
            {"year": "乙酉", "month": "辛酉", "day": "戊午", "hour": "壬子"},
            {"year": "丙寅", "month": "壬辰", "day": "癸亥", "hour": "己丑"},
        ]
        for tc in test_cases:
            result = calc_all_shensha(tc)
            assert isinstance(result, ShenshaResult)
            s = result.summary
            assert s["total"] > 0
            assert sum(s["by_category"].values()) == s["total"]

    def test_yangren_exact_five(self):
        """阳刃：遍历60甲子，恰好5个阳干+刃支组合"""
        yangren_count = 0
        for gan in TIANGAN:
            for zhi in DIZHI:
                result = _calc_year_shensha(gan, zhi)
                if "阳刃" in result:
                    yangren_count += 1
                    assert gan + zhi in YANG_REN_COMBOS
        assert yangren_count == 5

    def test_shichong_exact_two_zhi(self):
        """时冲：仅子、午两个时支"""
        shichong_count = 0
        for zhi in DIZHI:
            result = _calc_hour_shensha("甲", zhi, "甲")
            if "时冲" in result:
                shichong_count += 1
                assert zhi in {"子", "午"}
        assert shichong_count == 2

    def test_result_fixture_determinism(self):
        """同一输入多次计算结果一致"""
        r1 = calc_all_shensha(TEST_PILLARS)
        r2 = calc_all_shensha(TEST_PILLARS)
        assert r1.year_shens == r2.year_shens
        assert r1.month_shens == r2.month_shens
        assert r1.day_shens == r2.day_shens
        assert r1.hour_shens == r2.hour_shens

    def test_shangguan_and_other_info_entries(self):
        """验证 _SHENSHA_INFO 中条目的 level 类型"""
        for name, info in _SHENSHA_INFO.items():
            assert isinstance(info["level"], int), f"{name} level 非 int"
            assert 1 <= info["level"] <= 5, f"{name} level={info['level']} 超出范围"

    def test_engine_compute_single_returns_dict(self):
        """compute_single 返回 dict 类型"""
        for detail in ["basic", "summary", "full"]:
            ret = ShenshaEngine.compute_single("甲", TEST_PILLARS, detail=detail)
            assert isinstance(ret, dict)
