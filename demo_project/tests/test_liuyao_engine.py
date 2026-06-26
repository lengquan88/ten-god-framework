#!/usr/bin/env python3
"""Tests for liuyao_engine module — comprehensive coverage."""

import pytest
from tengod.liuyao_engine import (
    BAGUA, BAGUA_ORDER, BAGUA_YAO, BAGUA_NAJIA_GAN, BAGUA_NAZHI,
    WUXING_RELATION, LIUQIN_RULES, LIUSHEN_ORDER, LIUSHEN_START,
    _64GUA_DATA, _GUA_INDEX, GUA_DUANCI,
    YaoType, YaoInfo, LiuyaoResult, LiuyaoEngine,
    shake_and_calc, calc_from_yao,
)


class TestConstants:
    def test_bagua_has_eight_trigrams(self):
        assert len(BAGUA) == 8
        for name in ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]:
            assert name in BAGUA
            entry = BAGUA[name]
            assert "symbol" in entry
            assert "nature" in entry
            assert "wuxing" in entry
            assert "num" in entry
            assert isinstance(entry["num"], int)

    def test_bagua_order_eight_entries(self):
        assert len(BAGUA_ORDER) == 8
        assert set(BAGUA_ORDER) == set(BAGUA.keys())

    def test_bagua_yao_maps_eight_trigrams(self):
        assert len(BAGUA_YAO) == 8
        for name in BAGUA_ORDER:
            assert name in BAGUA_YAO
            yao = BAGUA_YAO[name]
            assert len(yao) == 3
            assert all(v in (0, 1) for v in yao)

    def test_bagua_najia_gan_maps_eight(self):
        assert len(BAGUA_NAJIA_GAN) == 8
        for name in BAGUA_ORDER:
            assert name in BAGUA_NAJIA_GAN
            assert isinstance(BAGUA_NAJIA_GAN[name], str)

    def test_bagua_nazhi_six_elements_each(self):
        assert len(BAGUA_NAZHI) == 8
        for name in BAGUA_ORDER:
            assert name in BAGUA_NAZHI
            zhi_list = BAGUA_NAZHI[name]
            assert len(zhi_list) == 6
            for z in zhi_list:
                assert z in "子丑寅卯辰巳午未申酉戌亥"

    def test_wuxing_relation_completeness(self):
        assert len(WUXING_RELATION) == 5
        for wx in ["金", "木", "水", "火", "土"]:
            assert wx in WUXING_RELATION
            rel = WUXING_RELATION[wx]
            assert "生" in rel
            assert "克" in rel
            assert "被生" in rel
            assert "被克" in rel

    def test_liuqin_rules_five_relatives(self):
        assert len(LIUQIN_RULES) == 5
        for qin in ["父母", "兄弟", "官鬼", "妻财", "子孙"]:
            assert qin in LIUQIN_RULES

    def test_liushen_order_six_spirits(self):
        assert len(LIUSHEN_ORDER) == 6
        for spirit in ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"]:
            assert spirit in LIUSHEN_ORDER

    def test_liushen_start_ten_tiangan(self):
        assert len(LIUSHEN_START) == 10
        for gan in "甲乙丙丁戊己庚辛壬癸":
            assert gan in LIUSHEN_START
            assert 0 <= LIUSHEN_START[gan] < 6

    def test_64gua_data_exactly_64(self):
        assert len(_64GUA_DATA) == 64
        for entry in _64GUA_DATA:
            assert len(entry) == 7
            s, x, name, shi, ying, gong, num = entry
            assert s in BAGUA
            assert x in BAGUA
            assert isinstance(name, str)
            assert 1 <= shi <= 6
            assert 1 <= ying <= 6
            assert gong in BAGUA
            assert 1 <= num <= 64

    def test_gua_index_64_entries(self):
        assert len(_GUA_INDEX) == 64
        for entry in _64GUA_DATA:
            s, x, name, shi, ying, gong, num = entry
            assert (s, x) in _GUA_INDEX
            assert _GUA_INDEX[(s, x)] == (name, shi, ying, gong, num)

    def test_gua_duanci_64_entries(self):
        assert len(GUA_DUANCI) == 64
        for entry in _64GUA_DATA:
            name = entry[2]
            assert name in GUA_DUANCI
            assert isinstance(GUA_DUANCI[name], str)
            assert len(GUA_DUANCI[name]) > 0


class TestEnumAndDataclasses:
    def test_yao_type_all_four(self):
        assert YaoType.SHAO_YANG.value == "少阳"
        assert YaoType.SHAO_YIN.value == "少阴"
        assert YaoType.LAO_YANG.value == "老阳"
        assert YaoType.LAO_YIN.value == "老阴"
        assert len(YaoType) == 4

    def test_yao_info_required_fields(self):
        yao = YaoInfo(
            position=1, yao_type=YaoType.SHAO_YANG,
            value=1, is_dong=False,
        )
        assert yao.position == 1
        assert yao.yao_type == YaoType.SHAO_YANG
        assert yao.value == 1
        assert yao.is_dong is False
        assert yao.zhi == ""
        assert yao.gan == ""
        assert yao.liuqin == ""
        assert yao.liushen == ""
        assert yao.shi is False
        assert yao.ying is False

    def test_yao_info_optional_fields(self):
        yao = YaoInfo(
            position=3, yao_type=YaoType.LAO_YIN,
            value=0, is_dong=True,
            zhi="卯", gan="乙", liuqin="父母", liushen="青龙",
            shi=True, ying=False,
        )
        assert yao.zhi == "卯"
        assert yao.gan == "乙"
        assert yao.liuqin == "父母"
        assert yao.liushen == "青龙"
        assert yao.shi is True
        assert yao.ying is False

    def test_liuyao_result_required_and_defaults(self):
        r = LiuyaoResult(ben_gua_name="乾为天")
        assert r.ben_gua_name == "乾为天"
        assert r.bian_gua_name == ""
        assert r.hu_gua_name == ""
        assert r.ben_gua_symbol == ""
        assert r.bian_gua_symbol == ""
        assert r.shang_gua == ""
        assert r.xia_gua == ""
        assert r.gua_gong == ""
        assert r.yaos == []
        assert r.ben_gua_duanci == ""
        assert r.bian_gua_duanci == ""
        assert r.overall_judgment == ""
        assert r.day_ganzhi == ""
        assert r.day_gan == ""
        assert r.dong_yao_positions == []

    def test_liuyao_result_all_fields(self):
        r = LiuyaoResult(
            ben_gua_name="坤为地", bian_gua_name="乾为天", hu_gua_name="坤为地",
            ben_gua_symbol="⚋⚋⚋⚋⚋⚋", bian_gua_symbol="⚊⚊⚊⚊⚊⚊",
            shang_gua="坤", xia_gua="坤", gua_gong="坤",
            yaos=[], ben_gua_duanci="元亨", bian_gua_duanci="元亨利贞",
            overall_judgment="吉", day_ganzhi="甲子", day_gan="甲",
            dong_yao_positions=[1, 3, 5],
        )
        assert r.bian_gua_name == "乾为天"
        assert r.dong_yao_positions == [1, 3, 5]


class TestGetGuaByYao:
    def test_all_eight_upper_trigrams(self):
        trigram_values = {
            "乾": [1, 1, 1], "兑": [0, 1, 1], "离": [1, 0, 1], "震": [0, 0, 1],
            "巽": [1, 1, 0], "坎": [0, 1, 0], "艮": [1, 0, 0], "坤": [0, 0, 0],
        }
        for name, upper in trigram_values.items():
            yao_values = [1, 1, 1] + upper
            shang, xia, _ = LiuyaoEngine._get_gua_by_yao(yao_values)
            assert shang == name, f"Expected upper {name}, got {shang}"

    def test_all_eight_lower_trigrams(self):
        trigram_values = {
            "乾": [1, 1, 1], "兑": [0, 1, 1], "离": [1, 0, 1], "震": [0, 0, 1],
            "巽": [1, 1, 0], "坎": [0, 1, 0], "艮": [1, 0, 0], "坤": [0, 0, 0],
        }
        for name, lower in trigram_values.items():
            yao_values = lower + [0, 0, 0]
            shang, xia, _ = LiuyaoEngine._get_gua_by_yao(yao_values)
            assert xia == name, f"Expected lower {name}, got {xia}"

    def test_qian_wei_tian(self):
        shang, xia, _ = LiuyaoEngine._get_gua_by_yao([1, 1, 1, 1, 1, 1])
        assert shang == "乾" and xia == "乾"

    def test_kun_wei_di(self):
        shang, xia, _ = LiuyaoEngine._get_gua_by_yao([0, 0, 0, 0, 0, 0])
        assert shang == "坤" and xia == "坤"

    def test_huo_tian_da_you(self):
        shang, xia, _ = LiuyaoEngine._get_gua_by_yao([1, 1, 1, 1, 0, 1])
        assert shang == "离" and xia == "乾"

    def test_invalid_defaults_to_kun(self):
        shang, xia, _ = LiuyaoEngine._get_gua_by_yao([2, 2, 2, 2, 2, 2])
        assert shang == "坤" and xia == "坤"


class TestGetGuaInfo:
    def test_all_64_pairs_return_valid(self):
        for s, x, name, shi, ying, gong, num in _64GUA_DATA:
            rn, rs, ry, rg, rnum = LiuyaoEngine._get_gua_info(s, x)
            assert rn == name
            assert rs == shi
            assert ry == ying
            assert rg == gong
            assert rnum == num

    def test_qian_wei_tian_info(self):
        name, shi, ying, gong, num = LiuyaoEngine._get_gua_info("乾", "乾")
        assert name == "乾为天" and shi == 6 and ying == 3
        assert gong == "乾" and num == 1

    def test_kun_wei_di_info(self):
        name, shi, ying, gong, num = LiuyaoEngine._get_gua_info("坤", "坤")
        assert name == "坤为地" and shi == 6 and ying == 3
        assert gong == "坤" and num == 2

    def test_unknown_pair_default(self):
        name, shi, ying, gong, num = LiuyaoEngine._get_gua_info("X", "Y")
        assert name == "未知卦" and shi == 1 and ying == 4
        assert gong == "乾" and num == 0


class TestGetHuGua:
    def test_hu_gua_qian_all_yang(self):
        shang, xia = LiuyaoEngine._get_hu_gua([1, 1, 1, 1, 1, 1])
        assert xia == "乾" and shang == "乾"

    def test_hu_gua_uses_positions_234_345(self):
        shang, xia = LiuyaoEngine._get_hu_gua([1, 0, 1, 0, 1, 0])
        assert xia == "坎" and shang == "离"

    def test_hu_gua_kun_all_yin(self):
        shang, xia = LiuyaoEngine._get_hu_gua([0, 0, 0, 0, 0, 0])
        assert xia == "坤" and shang == "坤"


class TestYaoToSymbol:
    def test_yang_not_dong(self):
        assert LiuyaoEngine._yao_to_symbol(1, False) == "⚊"

    def test_yin_not_dong(self):
        assert LiuyaoEngine._yao_to_symbol(0, False) == "⚋"

    def test_yang_dong_lao_yang(self):
        assert LiuyaoEngine._yao_to_symbol(1, True) == "◯"

    def test_yin_dong_lao_yin(self):
        assert LiuyaoEngine._yao_to_symbol(0, True) == "❌"


class TestGetLiuqin:
    def test_same_wuxing_xiongdi(self):
        assert LiuyaoEngine._get_liuqin("金", "申") == "兄弟"
        assert LiuyaoEngine._get_liuqin("木", "寅") == "兄弟"
        assert LiuyaoEngine._get_liuqin("水", "子") == "兄弟"
        assert LiuyaoEngine._get_liuqin("火", "午") == "兄弟"
        assert LiuyaoEngine._get_liuqin("土", "辰") == "兄弟"

    def test_yao_sheng_gong_fumu(self):
        assert LiuyaoEngine._get_liuqin("水", "申") == "父母"
        assert LiuyaoEngine._get_liuqin("火", "寅") == "父母"
        assert LiuyaoEngine._get_liuqin("木", "子") == "父母"
        assert LiuyaoEngine._get_liuqin("土", "午") == "父母"
        assert LiuyaoEngine._get_liuqin("金", "辰") == "父母"

    def test_yao_ke_gong_guangui(self):
        assert LiuyaoEngine._get_liuqin("木", "申") == "官鬼"
        assert LiuyaoEngine._get_liuqin("土", "寅") == "官鬼"
        assert LiuyaoEngine._get_liuqin("火", "子") == "官鬼"
        assert LiuyaoEngine._get_liuqin("金", "午") == "官鬼"
        assert LiuyaoEngine._get_liuqin("水", "辰") == "官鬼"

    def test_gong_sheng_yao_zisun(self):
        assert LiuyaoEngine._get_liuqin("金", "子") == "子孙"
        assert LiuyaoEngine._get_liuqin("木", "午") == "子孙"
        assert LiuyaoEngine._get_liuqin("水", "寅") == "子孙"
        assert LiuyaoEngine._get_liuqin("火", "辰") == "子孙"
        assert LiuyaoEngine._get_liuqin("土", "申") == "子孙"

    def test_gong_ke_yao_qicai(self):
        assert LiuyaoEngine._get_liuqin("金", "寅") == "妻财"
        assert LiuyaoEngine._get_liuqin("木", "辰") == "妻财"
        assert LiuyaoEngine._get_liuqin("水", "午") == "妻财"
        assert LiuyaoEngine._get_liuqin("火", "申") == "妻财"
        assert LiuyaoEngine._get_liuqin("土", "子") == "妻财"

    def test_unknown_zhi_defaults_to_tu(self):
        assert LiuyaoEngine._get_liuqin("土", "XYZ") == "兄弟"
        assert LiuyaoEngine._get_liuqin("水", "") == "官鬼"

    def test_all_twelve_zhi_for_jin_gong(self):
        for zhi in ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]:
            result = LiuyaoEngine._get_liuqin("金", zhi)
            assert result in LIUQIN_RULES


class TestGetLiushen:
    def test_jiayi_qinglong_at_shang_yao(self):
        assert LiuyaoEngine._get_liushen("甲", 6) == "青龙"
        assert LiuyaoEngine._get_liushen("乙", 6) == "青龙"
        assert LiuyaoEngine._get_liushen("甲", 5) == "朱雀"
        assert LiuyaoEngine._get_liushen("甲", 4) == "勾陈"
        assert LiuyaoEngine._get_liushen("甲", 3) == "螣蛇"
        assert LiuyaoEngine._get_liushen("甲", 2) == "白虎"
        assert LiuyaoEngine._get_liushen("甲", 1) == "玄武"

    def test_bingding_zhuque_at_shang_yao(self):
        assert LiuyaoEngine._get_liushen("丙", 6) == "朱雀"
        assert LiuyaoEngine._get_liushen("丁", 6) == "朱雀"
        assert LiuyaoEngine._get_liushen("丙", 5) == "勾陈"

    def test_wu_gouchen_at_shang_yao(self):
        assert LiuyaoEngine._get_liushen("戊", 6) == "勾陈"
        assert LiuyaoEngine._get_liushen("戊", 5) == "螣蛇"

    def test_ji_tengshe_at_shang_yao(self):
        assert LiuyaoEngine._get_liushen("己", 6) == "螣蛇"
        assert LiuyaoEngine._get_liushen("己", 5) == "白虎"

    def test_gengxin_baihu_at_shang_yao(self):
        assert LiuyaoEngine._get_liushen("庚", 6) == "白虎"
        assert LiuyaoEngine._get_liushen("辛", 6) == "白虎"
        assert LiuyaoEngine._get_liushen("庚", 5) == "玄武"

    def test_rengui_xuanwu_at_shang_yao(self):
        assert LiuyaoEngine._get_liushen("壬", 6) == "玄武"
        assert LiuyaoEngine._get_liushen("癸", 6) == "玄武"
        assert LiuyaoEngine._get_liushen("壬", 5) == "青龙"

    def test_all_positions_return_spirit(self):
        for gan in "甲乙丙丁戊己庚辛壬癸":
            for pos in range(1, 7):
                spirit = LiuyaoEngine._get_liushen(gan, pos)
                assert spirit in LIUSHEN_ORDER

    def test_all_six_spirits_present_for_any_gan(self):
        for gan in "甲乙丙丁戊己庚辛壬癸":
            spirits = [LiuyaoEngine._get_liushen(gan, p) for p in range(1, 7)]
            assert set(spirits) == set(LIUSHEN_ORDER)


class TestShakeCoins:
    def test_seed_deterministic(self):
        r1 = LiuyaoEngine.shake_coins(seed=42)
        r2 = LiuyaoEngine.shake_coins(seed=42)
        assert r1 == r2
        assert len(r1) == 6
        for yt in r1:
            assert isinstance(yt, YaoType)

    def test_returns_six_yao_types(self):
        result = LiuyaoEngine.shake_coins(seed=123)
        assert len(result) == 6
        for yt in result:
            assert isinstance(yt, YaoType)

    def test_randomize_returns_six(self):
        result = LiuyaoEngine.shake_coins(randomize=True)
        assert len(result) == 6

    def test_different_seeds(self):
        r1 = LiuyaoEngine.shake_coins(seed=1)
        r2 = LiuyaoEngine.shake_coins(seed=2)
        assert len(r1) == 6 and len(r2) == 6


class TestCalcGua:
    def test_explicit_yao_types_returns_result(self):
        yao_types = [YaoType.SHAO_YANG] * 6
        r = LiuyaoEngine.calc_gua(yao_types=yao_types)
        assert isinstance(r, LiuyaoResult)
        assert r.ben_gua_name == "乾为天"

    def test_none_yao_types_auto_shake(self):
        r = LiuyaoEngine.calc_gua(yao_types=None, day_ganzhi="甲子")
        assert isinstance(r, LiuyaoResult)
        assert len(r.yaos) == 6

    def test_ben_gua_name_qian_kun(self):
        assert calc_from_yao("111111").ben_gua_name == "乾为天"
        assert calc_from_yao("000000").ben_gua_name == "坤为地"

    def test_yaos_have_six_entries(self):
        r = calc_from_yao("101010")
        assert len(r.yaos) == 6

    def test_yao_positions_1_to_6(self):
        r = calc_from_yao("111111")
        assert [y.position for y in r.yaos] == [1, 2, 3, 4, 5, 6]

    def test_yao_zhi_from_nazhi(self):
        r = calc_from_yao("111111")
        assert r.gua_gong == "乾"
        for i, yao in enumerate(r.yaos):
            assert yao.zhi == BAGUA_NAZHI["乾"][i]

    def test_yao_liuqin_present(self):
        r = calc_from_yao("111111")
        for yao in r.yaos:
            assert yao.liuqin in LIUQIN_RULES

    def test_yao_liushen_present(self):
        r = calc_from_yao("111111", day_ganzhi="甲子")
        for yao in r.yaos:
            assert yao.liushen in LIUSHEN_ORDER

    def test_exactly_one_shi_ying(self):
        r = calc_from_yao("111111")
        assert sum(1 for y in r.yaos if y.shi) == 1
        assert sum(1 for y in r.yaos if y.ying) == 1

    def test_dong_positions_lao_yang(self):
        r = calc_from_yao("131111")
        assert 2 in r.dong_yao_positions
        assert r.yaos[1].is_dong is True

    def test_dong_positions_lao_yin(self):
        r = calc_from_yao("112111")
        assert 3 in r.dong_yao_positions
        assert r.yaos[2].is_dong is True

    def test_no_dong_yiao_jing_gua(self):
        r = calc_from_yao("101010")
        assert r.dong_yao_positions == []
        for y in r.yaos:
            assert y.is_dong is False

    def test_all_lao_yang_all_dong(self):
        r = calc_from_yao("333333")
        assert len(r.dong_yao_positions) == 6
        assert r.dong_yao_positions == [1, 2, 3, 4, 5, 6]
        assert r.bian_gua_name == "坤为地"

    def test_ben_gua_duanci_present(self):
        r = calc_from_yao("111111")
        assert r.ben_gua_duanci == GUA_DUANCI["乾为天"]

    def test_default_day_ganzhi_jiazi(self):
        r = LiuyaoEngine.calc_gua(yao_types=[YaoType.SHAO_YANG] * 6)
        assert r.day_ganzhi == "甲子"
        assert r.day_gan == "甲"

    def test_gua_gong_wuxing_from_bagua(self):
        r = calc_from_yao("111111")
        assert r.gua_gong == "乾"
        assert BAGUA[r.gua_gong]["wuxing"] == "金"

    def test_bian_gua_from_dong(self):
        r = calc_from_yao("111113")
        assert r.ben_gua_name == "乾为天"
        assert r.bian_gua_name != "乾为天"

    def test_hu_gua_computed(self):
        r = calc_from_yao("111111")
        assert r.hu_gua_name != ""

    def test_jing_gua_bian_same_as_ben(self):
        r = calc_from_yao("111111")
        assert r.bian_gua_name == "乾为天"

    def test_custom_day_ganzhi(self):
        r = calc_from_yao("111111", day_ganzhi="丙子")
        assert r.day_ganzhi == "丙子"
        assert r.day_gan == "丙"

    def test_bian_gua_duanci_when_different(self):
        r = calc_from_yao("333333")
        assert r.bian_gua_duanci == GUA_DUANCI["坤为地"]


class TestJudge:
    def test_with_dong_yao_mentions_dong(self):
        r = calc_from_yao("131111")
        assert "动爻" in r.overall_judgment
        assert "第2爻" in r.overall_judgment

    def test_without_dong_yao_jing_gua(self):
        r = calc_from_yao("111111")
        assert "静卦" in r.overall_judgment

    def test_includes_shi_yao(self):
        r = calc_from_yao("111111")
        assert "世爻" in r.overall_judgment

    def test_mentions_liuqin_liushen_for_dong(self):
        r = calc_from_yao("111113", day_ganzhi="甲子")
        j = r.overall_judgment
        assert "六亲" in j
        assert "六神" in j


class TestFormatText:
    def test_returns_multiline_string(self):
        r = calc_from_yao("111111")
        text = LiuyaoEngine.format_text(r)
        assert isinstance(text, str)
        assert "\n" in text

    def test_contains_title(self):
        r = calc_from_yao("111111")
        text = LiuyaoEngine.format_text(r)
        assert "六 爻 卦 象" in text

    def test_contains_ben_bian_hu_names(self):
        r = calc_from_yao("111311")
        text = LiuyaoEngine.format_text(r)
        assert r.ben_gua_name in text
        assert r.hu_gua_name in text
        assert r.bian_gua_name in text

    def test_contains_six_yao_lines(self):
        r = calc_from_yao("111111")
        text = LiuyaoEngine.format_text(r)
        for pos in range(1, 7):
            assert f"{pos}爻" in text

    def test_shows_shi_ying_tags(self):
        r = calc_from_yao("111111")
        text = LiuyaoEngine.format_text(r)
        assert "世" in text
        assert "应" in text

    def test_shows_dong_tag(self):
        r = calc_from_yao("131111")
        text = LiuyaoEngine.format_text(r)
        assert "动" in text

    def test_contains_richua_info(self):
        r = calc_from_yao("111111", day_ganzhi="丙寅")
        text = LiuyaoEngine.format_text(r)
        assert "日辰" in text
        assert "丙寅" in text


class TestConvenience:
    def test_shake_and_calc(self):
        r = shake_and_calc(day_ganzhi="甲子")
        assert isinstance(r, LiuyaoResult)
        assert len(r.yaos) == 6

    def test_calc_from_yao_qian(self):
        assert calc_from_yao("111111").ben_gua_name == "乾为天"

    def test_calc_from_yao_kun(self):
        assert calc_from_yao("000000").ben_gua_name == "坤为地"

    def test_calc_from_yao_dong_fourth(self):
        r = calc_from_yao("111311")
        assert r.ben_gua_name == "乾为天"
        assert 4 in r.dong_yao_positions

    def test_calc_from_yao_invalid_chars_default_shaoyang(self):
        r = calc_from_yao("abcdef")
        assert r.ben_gua_name == "乾为天"
        assert r.dong_yao_positions == []

    def test_calc_from_yao_day_ganzhi(self):
        r = calc_from_yao("111111", day_ganzhi="丙寅")
        assert r.day_ganzhi == "丙寅"
        assert r.day_gan == "丙"

    def test_calc_from_yao_lao_yin(self):
        r = calc_from_yao("222222")
        assert r.ben_gua_name == "坤为地"
        assert r.bian_gua_name == "乾为天"


@pytest.mark.parametrize("shang,xia,name,shi,ying,gong,num", _64GUA_DATA)
def test_all_64_hexagrams(shang, xia, name, shi, ying, gong, num):
    lower = BAGUA_YAO[xia]
    upper = BAGUA_YAO[shang]
    yao_values = lower + upper
    yao_str = "".join("1" if v else "0" for v in yao_values)
    r = calc_from_yao(yao_str)
    assert r.ben_gua_name == name, f"Expected {name}, got {r.ben_gua_name}"
    assert r.shang_gua == shang
    assert r.xia_gua == xia
    assert r.gua_gong == gong


class TestEdgeCases:
    def test_all_shao_yang_qian_jing_gua(self):
        r = calc_from_yao("111111")
        assert r.ben_gua_name == "乾为天"
        assert r.dong_yao_positions == []
        assert r.bian_gua_name == "乾为天"
        for y in r.yaos:
            assert y.is_dong is False

    def test_all_shao_yin_kun_jing_gua(self):
        r = calc_from_yao("000000")
        assert r.ben_gua_name == "坤为地"
        assert r.dong_yao_positions == []

    def test_all_lao_yin_all_become_yang(self):
        r = calc_from_yao("222222")
        assert len(r.dong_yao_positions) == 6
        assert r.bian_gua_name == "乾为天"

    def test_single_dong_yao(self):
        r = calc_from_yao("111131")
        assert r.dong_yao_positions == [5]

    def test_different_day_gan_liushen(self):
        r_jia = calc_from_yao("111111", day_ganzhi="甲子")
        r_bing = calc_from_yao("111111", day_ganzhi="丙子")
        spirits_jia = [y.liushen for y in r_jia.yaos]
        spirits_bing = [y.liushen for y in r_bing.yaos]
        assert spirits_jia != spirits_bing

    def test_symbols_for_dong_yao(self):
        r = calc_from_yao("300000")
        assert "◯" in r.ben_gua_symbol or "❌" in r.ben_gua_symbol or \
               any(LiuyaoEngine._yao_to_symbol(y.value, y.is_dong) in ("◯", "❌") for y in r.yaos)
        assert r.yaos[0].is_dong is True

    def test_short_yao_string_uses_only_first_six_chars(self):
        r = calc_from_yao("111111extra")
        assert len(r.yaos) == 6
        assert r.ben_gua_name == "乾为天"

    def test_empty_or_invalid_defaults_yao_types(self):
        r = calc_from_yao("1x1x1x")
        assert len(r.yaos) == 6

    def test_bagua_symbol_fields(self):
        for name, info in BAGUA.items():
            assert len(info["symbol"]) == 1
