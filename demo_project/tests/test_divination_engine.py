"""divination_engine.py 完整测试套件 — 覆盖五行/天干/地支/十神/八字及综合推理函数。"""

import pytest
from tengod.divination_engine import (
    WuxingEngine,
    TianganEngine,
    DizhiEngine,
    ShiganEngine,
    BaziCalculator,
    ShiganResult,
    ShiganType,
    Wuxing,
    Yinyang,
    analyze_relations,
    find_interactions,
)


# ============================================================================
# 一、五行引擎 WuxingEngine 测试
# ============================================================================

class TestWuxingValidate:
    """五行校验"""

    def test_validate_valid(self):
        for wx in ["木", "火", "土", "金", "水"]:
            assert WuxingEngine.validate(wx) == wx

    def test_validate_invalid(self):
        with pytest.raises(ValueError, match="无效的五行"):
            WuxingEngine.validate("天")
        with pytest.raises(ValueError, match="无效的五行"):
            WuxingEngine.validate("")


class TestWuxingGenerate:
    """五行相生：木→火→土→金→水→木"""

    def test_mu_generates_huo(self):
        assert WuxingEngine.generate("木") == "火"

    def test_huo_generates_tu(self):
        assert WuxingEngine.generate("火") == "土"

    def test_tu_generates_jin(self):
        assert WuxingEngine.generate("土") == "金"

    def test_jin_generates_shui(self):
        assert WuxingEngine.generate("金") == "水"

    def test_shui_generates_mu(self):
        assert WuxingEngine.generate("水") == "木"


class TestWuxingRestrict:
    """五行相克：木克土→土克水→水克火→火克金→金克木"""

    def test_mu_restricts_tu(self):
        assert WuxingEngine.restrict("木") == "土"

    def test_tu_restricts_shui(self):
        assert WuxingEngine.restrict("土") == "水"

    def test_shui_restricts_huo(self):
        assert WuxingEngine.restrict("水") == "火"

    def test_huo_restricts_jin(self):
        assert WuxingEngine.restrict("火") == "金"

    def test_jin_restricts_mu(self):
        assert WuxingEngine.restrict("金") == "木"


class TestWuxingGeneratedBy:
    """生我关系"""

    def test_huo_generated_by_mu(self):
        assert WuxingEngine.generated_by("火") == "木"

    def test_tu_generated_by_huo(self):
        assert WuxingEngine.generated_by("土") == "火"

    def test_jin_generated_by_tu(self):
        assert WuxingEngine.generated_by("金") == "土"

    def test_shui_generated_by_jin(self):
        assert WuxingEngine.generated_by("水") == "金"

    def test_mu_generated_by_shui(self):
        assert WuxingEngine.generated_by("木") == "水"


class TestWuxingRestrictedBy:
    """克我关系"""

    def test_tu_restricted_by_mu(self):
        assert WuxingEngine.restricted_by("土") == "木"

    def test_shui_restricted_by_tu(self):
        assert WuxingEngine.restricted_by("水") == "土"

    def test_huo_restricted_by_shui(self):
        assert WuxingEngine.restricted_by("火") == "水"

    def test_jin_restricted_by_huo(self):
        assert WuxingEngine.restricted_by("金") == "火"

    def test_mu_restricted_by_jin(self):
        assert WuxingEngine.restricted_by("木") == "金"


class TestWuxingOverRestrict:
    """相乘 — 过克"""

    def test_over_restrict_same_as_restrict(self):
        for wx in ["木", "火", "土", "金", "水"]:
            assert WuxingEngine.over_restrict(wx) == WuxingEngine.restrict(wx)


class TestWuxingReverseRestrict:
    """相侮 — 反克"""

    def test_mu_reverse_restricts_jin(self):
        # 木侮金（金克木，木反侮金）
        assert WuxingEngine.reverse_restrict("木") == "金"

    def test_tu_reverse_restricts_mu(self):
        # 土侮木（木克土，土反侮木）
        assert WuxingEngine.reverse_restrict("土") == "木"

    def test_shui_reverse_restricts_tu(self):
        assert WuxingEngine.reverse_restrict("水") == "土"

    def test_huo_reverse_restricts_shui(self):
        assert WuxingEngine.reverse_restrict("火") == "水"

    def test_jin_reverse_restricts_huo(self):
        assert WuxingEngine.reverse_restrict("金") == "火"


class TestWuxingChainGenerate:
    """生链遍历"""

    def test_chain_generate_depth_5_from_mu(self):
        assert WuxingEngine.chain_generate("木", 5) == ["木", "火", "土", "金", "水"]

    def test_chain_generate_depth_3(self):
        assert WuxingEngine.chain_generate("木", 3) == ["木", "火", "土"]

    def test_chain_generate_depth_1(self):
        assert WuxingEngine.chain_generate("火", 1) == ["火"]

    def test_chain_generate_depth_6_wraps(self):
        # 6个元素会循环回到起点
        assert WuxingEngine.chain_generate("木", 6) == ["木", "火", "土", "金", "水", "木"]


class TestWuxingChainRestrict:
    """克链遍历"""

    def test_chain_restrict_depth_5_from_mu(self):
        assert WuxingEngine.chain_restrict("木", 5) == ["木", "土", "水", "火", "金"]

    def test_chain_restrict_depth_3(self):
        assert WuxingEngine.chain_restrict("木", 3) == ["木", "土", "水"]

    def test_chain_restrict_depth_1(self):
        assert WuxingEngine.chain_restrict("金", 1) == ["金"]

    def test_chain_restrict_depth_6_wraps(self):
        assert WuxingEngine.chain_restrict("木", 6) == ["木", "土", "水", "火", "金", "木"]


class TestWuxingColorize:
    """颜色化"""

    def test_colorize_default_text(self):
        result = WuxingEngine.colorize("木")
        assert "\033[32m" in result
        assert "木" in result
        assert "\033[0m" in result

    def test_colorize_custom_text(self):
        result = WuxingEngine.colorize("火", "text")
        assert "\033[31m" in result
        assert "text" in result
        assert "\033[0m" in result

    def test_colorize_unknown(self):
        # 未知五行：不添加颜色前缀，但仍有 COLOR_RESET 后缀
        result = WuxingEngine.colorize("天")
        # 不包含颜色开头（如 \033[32m），但包含 RESET
        assert not result.startswith("\033[")
        assert result == "天\033[0m"


class TestWuxingSummary:
    """摘要"""

    def test_summary_has_elements(self):
        s = WuxingEngine.summary()
        assert s["elements"] == ["木", "火", "土", "金", "水"]
        assert "colors" in s
        assert "generate" in s
        assert "restrict" in s


# ============================================================================
# 二、天干引擎 TianganEngine 测试
# ============================================================================

class TestTianganValidate:
    """天干校验"""

    def test_validate_all_valid(self):
        for tg in TianganEngine.TIANGAN:
            assert TianganEngine.validate(tg) == tg

    def test_validate_invalid(self):
        with pytest.raises(ValueError, match="无效的天干"):
            TianganEngine.validate("子")
        with pytest.raises(ValueError, match="无效的天干"):
            TianganEngine.validate("X")


class TestTianganWuxing:
    """天干五行"""

    def test_jiayi_wuxing_mu(self):
        assert TianganEngine.wuxing_of("甲") == "木"
        assert TianganEngine.wuxing_of("乙") == "木"

    def test_bingding_wuxing_huo(self):
        assert TianganEngine.wuxing_of("丙") == "火"
        assert TianganEngine.wuxing_of("丁") == "火"

    def test_wuji_wuxing_tu(self):
        assert TianganEngine.wuxing_of("戊") == "土"
        assert TianganEngine.wuxing_of("己") == "土"

    def test_gengxin_wuxing_jin(self):
        assert TianganEngine.wuxing_of("庚") == "金"
        assert TianganEngine.wuxing_of("辛") == "金"

    def test_rengui_wuxing_shui(self):
        assert TianganEngine.wuxing_of("壬") == "水"
        assert TianganEngine.wuxing_of("癸") == "水"


class TestTianganYinyang:
    """天干阴阳"""

    def test_yang_gan(self):
        for tg in ["甲", "丙", "戊", "庚", "壬"]:
            assert TianganEngine.yinyang_of(tg) == Yinyang.YANG

    def test_yin_gan(self):
        for tg in ["乙", "丁", "己", "辛", "癸"]:
            assert TianganEngine.yinyang_of(tg) == Yinyang.YIN


class TestTianganDirection:
    """天干方位"""

    def test_direction_east(self):
        assert TianganEngine.direction_of("甲") == "东"
        assert TianganEngine.direction_of("乙") == "东"

    def test_direction_south(self):
        assert TianganEngine.direction_of("丙") == "南"
        assert TianganEngine.direction_of("丁") == "南"

    def test_direction_center(self):
        assert TianganEngine.direction_of("戊") == "中"
        assert TianganEngine.direction_of("己") == "中"

    def test_direction_west(self):
        assert TianganEngine.direction_of("庚") == "西"
        assert TianganEngine.direction_of("辛") == "西"

    def test_direction_north(self):
        assert TianganEngine.direction_of("壬") == "北"
        assert TianganEngine.direction_of("癸") == "北"


class TestTianganWuhe:
    """天干五合"""

    def test_wuhe_jiaji(self):
        result = TianganEngine.wuhe("甲")
        assert result["partner"] == "己"
        assert result["wuxing"] == "土"
        assert result["description"] == "甲己合土"

    def test_wuhe_yigeng(self):
        result = TianganEngine.wuhe("乙")
        assert result["partner"] == "庚"
        assert result["wuxing"] == "金"

    def test_wuhe_bingxin(self):
        result = TianganEngine.wuhe("丙")
        assert result["partner"] == "辛"
        assert result["wuxing"] == "水"

    def test_wuhe_dingren(self):
        result = TianganEngine.wuhe("丁")
        assert result["partner"] == "壬"
        assert result["wuxing"] == "木"

    def test_wuhe_wugui(self):
        result = TianganEngine.wuhe("戊")
        assert result["partner"] == "癸"
        assert result["wuxing"] == "火"

    def test_wuhe_reverse(self):
        # 己合甲
        assert TianganEngine.wuhe("己")["partner"] == "甲"
        assert TianganEngine.wuhe("己")["wuxing"] == "土"


class TestTianganRestrict:
    """天干相克"""

    def test_jia_restricts_wu_ji(self):
        targets = [r["target"] for r in TianganEngine.restrict("甲")]
        assert "戊" in targets
        assert "己" in targets

    def test_geng_restricts_jia_yi(self):
        targets = [r["target"] for r in TianganEngine.restrict("庚")]
        assert "甲" in targets
        assert "乙" in targets

    def test_restrict_has_description(self):
        for r in TianganEngine.restrict("甲"):
            assert "description" in r
            assert "target" in r


class TestTianganSummary:
    def test_summary(self):
        s = TianganEngine.summary()
        assert s["tiangan"] == TianganEngine.TIANGAN
        assert "mapping" in s
        assert "wuhe" in s
        assert len(s["mapping"]) == 10


# ============================================================================
# 三、地支引擎 DizhiEngine 测试
# ============================================================================

class TestDizhiValidate:
    def test_validate_valid(self):
        for dz in DizhiEngine.DIZHI:
            assert DizhiEngine.validate(dz) == dz

    def test_validate_invalid(self):
        with pytest.raises(ValueError, match="无效的地支"):
            DizhiEngine.validate("甲")
        with pytest.raises(ValueError, match="无效的地支"):
            DizhiEngine.validate("猫")


class TestDizhiWuxing:
    def test_zi_hai_shui(self):
        assert DizhiEngine.wuxing_of("子") == "水"
        assert DizhiEngine.wuxing_of("亥") == "水"

    def test_yin_mao_mu(self):
        assert DizhiEngine.wuxing_of("寅") == "木"
        assert DizhiEngine.wuxing_of("卯") == "木"

    def test_si_wu_huo(self):
        assert DizhiEngine.wuxing_of("巳") == "火"
        assert DizhiEngine.wuxing_of("午") == "火"

    def test_shen_you_jin(self):
        assert DizhiEngine.wuxing_of("申") == "金"
        assert DizhiEngine.wuxing_of("酉") == "金"

    def test_chen_xu_chou_wei_tu(self):
        for dz in ["辰", "戌", "丑", "未"]:
            assert DizhiEngine.wuxing_of(dz) == "土"


class TestDizhiYinyang:
    def test_yang_dizhi(self):
        for dz in ["子", "寅", "辰", "午", "申", "戌"]:
            assert DizhiEngine.yinyang_of(dz) == Yinyang.YANG

    def test_yin_dizhi(self):
        for dz in ["丑", "卯", "巳", "未", "酉", "亥"]:
            assert DizhiEngine.yinyang_of(dz) == Yinyang.YIN


class TestDizhiCanggan:
    def test_canggan_zi(self):
        cg = DizhiEngine.canggan("子")
        assert cg["main"] == "癸"
        assert cg["mid"] is None
        assert cg["residual"] is None
        assert cg["list"] == ["癸"]

    def test_canggan_chou(self):
        cg = DizhiEngine.canggan("丑")
        assert cg["main"] == "己"
        assert cg["mid"] == "癸"
        assert cg["residual"] == "辛"
        assert len(cg["list"]) == 3

    def test_canggan_yin(self):
        cg = DizhiEngine.canggan("寅")
        assert cg["main"] == "甲"
        assert cg["mid"] == "丙"
        assert cg["residual"] == "戊"

    def test_canggan_wu_has_mid_no_residual(self):
        cg = DizhiEngine.canggan("午")
        assert cg["main"] == "丁"
        assert cg["mid"] == "己"
        assert cg["residual"] is None
        assert cg["list"] == ["丁", "己"]


class TestDizhiLiuhe:
    def test_liuhe_zichou(self):
        r = DizhiEngine.liuhe("子")
        assert r["partner"] == "丑"
        assert r["wuxing"] == "土"

    def test_liuhe_yinhai(self):
        r = DizhiEngine.liuhe("寅")
        assert r["partner"] == "亥"
        assert r["wuxing"] == "木"

    def test_liuhe_maoxu(self):
        r = DizhiEngine.liuhe("卯")
        assert r["partner"] == "戌"
        assert r["wuxing"] == "火"

    def test_liuhe_chenyou(self):
        r = DizhiEngine.liuhe("辰")
        assert r["partner"] == "酉"
        assert r["wuxing"] == "金"

    def test_liuhe_sishen(self):
        r = DizhiEngine.liuhe("巳")
        assert r["partner"] == "申"
        assert r["wuxing"] == "水"

    def test_liuhe_wuwei(self):
        r = DizhiEngine.liuhe("午")
        assert r["partner"] == "未"
        assert r["wuxing"] == "火"


class TestDizhiSanhe:
    def test_sanhe_shenzichen(self):
        r = DizhiEngine.sanhe("申")
        assert set(r["members"]) == {"申", "子", "辰"}
        assert r["wuxing"] == "水"

    def test_sanhe_haimaowei(self):
        r = DizhiEngine.sanhe("亥")
        assert set(r["members"]) == {"亥", "卯", "未"}
        assert r["wuxing"] == "木"

    def test_sanhe_yinwuxu(self):
        r = DizhiEngine.sanhe("寅")
        assert set(r["members"]) == {"寅", "午", "戌"}
        assert r["wuxing"] == "火"

    def test_sanhe_siyouchou(self):
        r = DizhiEngine.sanhe("巳")
        assert set(r["members"]) == {"巳", "酉", "丑"}
        assert r["wuxing"] == "金"


class TestDizhiSanhui:
    def test_sanhui_yinmaochen(self):
        r = DizhiEngine.sanhui("寅")
        assert set(r["members"]) == {"寅", "卯", "辰"}
        assert r["wuxing"] == "木"

    def test_sanhui_siwuwei(self):
        r = DizhiEngine.sanhui("巳")
        assert set(r["members"]) == {"巳", "午", "未"}
        assert r["wuxing"] == "火"

    def test_sanhui_shenyouxu(self):
        r = DizhiEngine.sanhui("申")
        assert set(r["members"]) == {"申", "酉", "戌"}
        assert r["wuxing"] == "金"

    def test_sanhui_haizichou(self):
        r = DizhiEngine.sanhui("亥")
        assert set(r["members"]) == {"亥", "子", "丑"}
        assert r["wuxing"] == "水"


class TestDizhiLiuchong:
    def test_liuchong_ziwu(self):
        assert DizhiEngine.liuchong("子")["target"] == "午"
        assert DizhiEngine.liuchong("午")["target"] == "子"

    def test_liuchong_chouwei(self):
        assert DizhiEngine.liuchong("丑")["target"] == "未"

    def test_liuchong_yinshen(self):
        assert DizhiEngine.liuchong("寅")["target"] == "申"

    def test_liuchong_maoyou(self):
        assert DizhiEngine.liuchong("卯")["target"] == "酉"

    def test_liuchong_chenxu(self):
        assert DizhiEngine.liuchong("辰")["target"] == "戌"

    def test_liuchong_sihai(self):
        assert DizhiEngine.liuchong("巳")["target"] == "亥"


class TestDizhiLiuhai:
    def test_liuhai_ziwei(self):
        assert DizhiEngine.liuhai("子")["target"] == "未"

    def test_liuhai_chouwu(self):
        assert DizhiEngine.liuhai("丑")["target"] == "午"

    def test_liuhai_yinsi(self):
        assert DizhiEngine.liuhai("寅")["target"] == "巳"

    def test_liuhai_maochen(self):
        assert DizhiEngine.liuhai("卯")["target"] == "辰"

    def test_liuhai_shenhai(self):
        assert DizhiEngine.liuhai("申")["target"] == "亥"

    def test_liuhai_youxu(self):
        assert DizhiEngine.liuhai("酉")["target"] == "戌"


class TestDizhiLiupo:
    def test_liupo_ziyou(self):
        assert DizhiEngine.liupo("子")["target"] == "酉"

    def test_liupo_yinhai(self):
        assert DizhiEngine.liupo("寅")["target"] == "亥"

    def test_liupo_chenchou(self):
        assert DizhiEngine.liupo("辰")["target"] == "丑"

    def test_liupo_wumao(self):
        assert DizhiEngine.liupo("午")["target"] == "卯"

    def test_liupo_shensi(self):
        assert DizhiEngine.liupo("申")["target"] == "巳"

    def test_liupo_xuwei(self):
        assert DizhiEngine.liupo("戌")["target"] == "未"


class TestDizhiXiangxing:
    def test_xiangxing_wuen(self):
        # 无恩之刑：寅刑巳→巳刑申→申刑寅
        results = DizhiEngine.xiangxing("寅")
        targets = [r["target"] for r in results]
        assert "巳" in targets  # 寅刑巳
        assert "申" in targets  # 申刑寅（被刑）

    def test_xiangxing_shishi(self):
        # 恃势之刑：丑刑戌→戌刑未→未刑丑
        results = DizhiEngine.xiangxing("丑")
        targets = [r["target"] for r in results]
        assert "戌" in targets  # 丑刑戌
        assert "未" in targets  # 未刑丑（被刑）

    def test_xiangxing_wuli(self):
        # 无礼之刑：子刑卯，卯刑子
        results = DizhiEngine.xiangxing("子")
        targets = [r["target"] for r in results]
        assert "卯" in targets

    def test_zixing_chen(self):
        results = DizhiEngine.xiangxing("辰")
        descriptions = [r["description"] for r in results]
        assert any("自刑" in d for d in descriptions)

    def test_zixing_wu(self):
        results = DizhiEngine.xiangxing("午")
        descriptions = [r["description"] for r in results]
        assert any("自刑" in d for d in descriptions)

    def test_zixing_you(self):
        results = DizhiEngine.xiangxing("酉")
        descriptions = [r["description"] for r in results]
        assert any("自刑" in d for d in descriptions)

    def test_zixing_hai(self):
        results = DizhiEngine.xiangxing("亥")
        descriptions = [r["description"] for r in results]
        assert any("自刑" in d for d in descriptions)


class TestDizhiMonth:
    def test_month_of_yin(self):
        m = DizhiEngine.month_of("寅")
        assert m["month"] == 1
        assert m["name"] == "正月"

    def test_month_of_zi(self):
        m = DizhiEngine.month_of("子")
        assert m["month"] == 11
        assert m["name"] == "十一月"


class TestDizhiHour:
    def test_hour_of_zi(self):
        h = DizhiEngine.hour_of("子")
        assert h["range"] == "23:00-01:00"
        assert h["name"] == "子时"

    def test_hour_of_wu(self):
        h = DizhiEngine.hour_of("午")
        assert h["range"] == "11:00-13:00"
        assert h["name"] == "午时"


class TestDizhiDirection:
    def test_direction_of_zi(self):
        assert DizhiEngine.direction_of("子") == "北"

    def test_direction_of_mao(self):
        assert DizhiEngine.direction_of("卯") == "东"

    def test_direction_of_wu(self):
        assert DizhiEngine.direction_of("午") == "南"

    def test_direction_of_you(self):
        assert DizhiEngine.direction_of("酉") == "西"


class TestDizhiZodiac:
    def test_zodiac_mapping(self):
        expected = {
            "子": "鼠", "丑": "牛", "寅": "虎", "卯": "兔",
            "辰": "龙", "巳": "蛇", "午": "马", "未": "羊",
            "申": "猴", "酉": "鸡", "戌": "狗", "亥": "猪",
        }
        for dz, zodiac in expected.items():
            assert DizhiEngine.zodiac_of(dz) == zodiac


class TestDizhiSummary:
    def test_summary(self):
        s = DizhiEngine.summary()
        assert s["dizhi"] == DizhiEngine.DIZHI
        assert "liuhe" in s
        assert "sanhe" in s
        assert "sanhui" in s
        assert "liuchong" in s
        assert "liuhai" in s
        assert "liupo" in s
        assert "xiangxing" in s


# ============================================================================
# 四、十神引擎 ShiganEngine 测试
# ============================================================================

class TestShiganCompute:
    """日干为甲，推演所有天干十神"""

    def test_jia_is_rijian(self):
        # 甲见甲 → 比肩
        sr = ShiganEngine.compute("甲", "甲")
        assert sr.shigan == ShiganType.BIJIAN
        assert sr.day_gan == "甲"
        assert sr.target_gan == "甲"

    def test_yi_is_jiecai(self):
        # 甲见乙 → 劫财（同五行异性）
        sr = ShiganEngine.compute("甲", "乙")
        assert sr.shigan == ShiganType.JIECAI

    def test_bing_is_shishen(self):
        # 甲生丙，同性 → 食神
        sr = ShiganEngine.compute("甲", "丙")
        assert sr.shigan == ShiganType.SHISHEN

    def test_ding_is_shangguan(self):
        # 甲生丁，异性 → 伤官
        sr = ShiganEngine.compute("甲", "丁")
        assert sr.shigan == ShiganType.SHANGGUAN

    def test_wu_is_piancai(self):
        # 甲克戊，同性 → 偏财
        sr = ShiganEngine.compute("甲", "戊")
        assert sr.shigan == ShiganType.PIANCAI

    def test_ji_is_zhengcai(self):
        # 甲克己，异性 → 正财
        sr = ShiganEngine.compute("甲", "己")
        assert sr.shigan == ShiganType.ZHENGCAI

    def test_geng_is_qisha(self):
        # 庚克甲，同性 → 七杀
        sr = ShiganEngine.compute("甲", "庚")
        assert sr.shigan == ShiganType.QISHA

    def test_xin_is_zhengguan(self):
        # 辛克甲，异性 → 正官
        sr = ShiganEngine.compute("甲", "辛")
        assert sr.shigan == ShiganType.ZHENGGUAN

    def test_ren_is_pianyin(self):
        # 壬生甲，同性 → 偏印
        sr = ShiganEngine.compute("甲", "壬")
        assert sr.shigan == ShiganType.PIANYIN

    def test_gui_is_zhengyin(self):
        # 癸生甲，异性 → 正印
        sr = ShiganEngine.compute("甲", "癸")
        assert sr.shigan == ShiganType.ZHENGYIN


class TestShiganComputeForBazi:
    def test_compute_for_bazi(self):
        results = ShiganEngine.compute_for_bazi("甲", ["甲", "丙", "戊", "庚"])
        assert len(results) == 4
        assert results[0].shigan == ShiganType.BIJIAN
        assert results[1].shigan == ShiganType.SHISHEN
        assert results[2].shigan == ShiganType.PIANCAI
        assert results[3].shigan == ShiganType.QISHA


class TestShiganClassify:
    def test_classify_shan_shen(self):
        assert ShiganEngine.classify(ShiganType.SHISHEN) == "善神"
        assert ShiganEngine.classify(ShiganType.ZHENGCAI) == "善神"
        assert ShiganEngine.classify(ShiganType.ZHENGGUAN) == "善神"
        assert ShiganEngine.classify(ShiganType.ZHENGYIN) == "善神"

    def test_classify_xiong_shen(self):
        assert ShiganEngine.classify(ShiganType.JIECAI) == "凶神"
        assert ShiganEngine.classify(ShiganType.SHANGGUAN) == "凶神"
        assert ShiganEngine.classify(ShiganType.QISHA) == "凶神"
        assert ShiganEngine.classify(ShiganType.PIANYIN) == "凶神"

    def test_classify_neutral(self):
        assert ShiganEngine.classify(ShiganType.BIJIAN) == "中性"
        assert ShiganEngine.classify(ShiganType.PIANCAI) == "中性"

    def test_classify_by_string(self):
        assert ShiganEngine.classify("正官") == "善神"
        assert ShiganEngine.classify("七杀") == "凶神"
        assert ShiganEngine.classify("比肩") == "中性"

    def test_classify_unknown(self):
        assert ShiganEngine.classify("未知") == "未知"


class TestShiganInteraction:
    def test_shishen_sheng_zhengcai(self):
        assert ShiganEngine.interaction("食神", "正财") == "生"

    def test_shishen_ke_pianyin(self):
        assert ShiganEngine.interaction("食神", "偏印") == "克"

    def test_shishen_bei_zhengguan_ke(self):
        assert ShiganEngine.interaction("食神", "正官") == "被克"

    def test_shishen_bei_bijian_sheng(self):
        assert ShiganEngine.interaction("食神", "比肩") == "被生"

    def test_shishen_no_relation_with_shishen(self):
        assert ShiganEngine.interaction("食神", "食神") is None

    def test_interaction_with_enum(self):
        assert ShiganEngine.interaction(ShiganType.SHISHEN, ShiganType.ZHENGCAI) == "生"

    def test_zhengyin_sheng_bijian(self):
        assert ShiganEngine.interaction("正印", "比肩") == "生"


class TestShiganSummary:
    def test_summary(self):
        s = ShiganEngine.summary()
        assert "types" in s
        assert "rules" in s
        assert "classification" in s
        assert len(s["types"]) == 10


# ============================================================================
# 五、八字计算器 BaziCalculator 测试
# ============================================================================

class TestBaziJiaziTable:
    def test_table_has_60_entries(self):
        table = BaziCalculator.jiazi_table()
        assert len(table) == 60

    def test_first_entry_is_jiazi(self):
        table = BaziCalculator.jiazi_table()
        assert table[0] == (1, "甲子")

    def test_last_entry_is_guihai(self):
        table = BaziCalculator.jiazi_table()
        assert table[59] == (60, "癸亥")


class TestBaziGetJiazi:
    def test_get_jiazi_1(self):
        assert BaziCalculator.get_jiazi(1) == "甲子"

    def test_get_jiazi_60(self):
        assert BaziCalculator.get_jiazi(60) == "癸亥"

    def test_get_jiazi_out_of_range(self):
        assert BaziCalculator.get_jiazi(0) is None
        assert BaziCalculator.get_jiazi(61) is None
        assert BaziCalculator.get_jiazi(-1) is None


class TestBaziGetIndex:
    def test_get_index_jiazi(self):
        assert BaziCalculator.get_index("甲子") == 1

    def test_get_index_guihai(self):
        assert BaziCalculator.get_index("癸亥") == 60

    def test_get_index_not_found(self):
        assert BaziCalculator.get_index("甲乙") is None
        assert BaziCalculator.get_index("") is None


class TestBaziIsValidCombination:
    def test_valid_yang_yang(self):
        # 甲（阳）配子（阳）→ 合法
        assert BaziCalculator.is_valid_combination("甲", "子") is True

    def test_valid_yin_yin(self):
        # 乙（阴）配丑（阴）→ 合法
        assert BaziCalculator.is_valid_combination("乙", "丑") is True

    def test_invalid_yang_yin(self):
        # 甲（阳）配丑（阴）→ 不合法
        assert BaziCalculator.is_valid_combination("甲", "丑") is False

    def test_invalid_yin_yang(self):
        # 乙（阴）配子（阳）→ 不合法
        assert BaziCalculator.is_valid_combination("乙", "子") is False

    def test_invalid_unknown(self):
        assert BaziCalculator.is_valid_combination("X", "子") is False
        assert BaziCalculator.is_valid_combination("甲", "Y") is False


class TestBaziSummary:
    def test_summary(self):
        s = BaziCalculator.summary()
        assert s["total"] == 60
        assert "cycle" in s
        assert "rule" in s


# ============================================================================
# 六、综合推理函数 测试
# ============================================================================

class TestAnalyzeRelations:
    def test_full_analysis(self):
        # 示例八字：甲子年、丙寅月、庚辰日、壬午时
        result = analyze_relations(
            day_gan="庚",
            heavenly_stems=["甲", "丙", "庚", "壬"],
            earthly_branches=["子", "寅", "辰", "午"],
        )
        assert result["day_gan"] == "庚"
        assert result["day_wuxing"] == "金"
        assert result["day_yinyang"] == "阳"
        assert len(result["heavenly_stems"]) == 4
        assert len(result["earthly_branches"]) == 4

        # 天干十神：庚日干见甲→偏财，见丙→七杀，见庚→比肩，见壬→食神
        gan_shigans = [gs["shigan"] for gs in result["heavenly_stems"]]
        assert "偏财" in gan_shigans
        assert "七杀" in gan_shigans
        assert "比肩" in gan_shigans
        assert "食神" in gan_shigans

        # 统计
        stats = result["statistics"]
        assert "shigan_counts" in stats
        assert "good" in stats
        assert "bad" in stats
        assert "neutral" in stats
        assert "balance" in stats

        # 互动
        assert "interactions" in result

    def test_analyze_relations_with_interactions(self):
        # 子午冲：子年、午日
        result = analyze_relations(
            day_gan="甲",
            heavenly_stems=["甲", "丙", "甲", "壬"],
            earthly_branches=["子", "寅", "午", "辰"],
        )
        interactions = result["interactions"]
        # 子午相冲
        assert len(interactions["chong"]) >= 1
        assert any("子午相冲" in c["detail"] for c in interactions["chong"])


class TestFindInteractions:
    def test_find_interactions_liuhe(self):
        # 子丑合
        result = find_interactions(["子", "丑", "寅", "卯"])
        assert len(result["he"]) >= 1
        assert any("子丑合" in h["detail"] for h in result["he"])

    def test_find_interactions_liuchong(self):
        # 子午冲
        result = find_interactions(["子", "午", "寅", "卯"])
        assert len(result["chong"]) >= 1
        assert any("子午相冲" in c["detail"] for c in result["chong"])

    def test_find_interactions_liuhai(self):
        # 子未害
        result = find_interactions(["子", "未", "寅", "卯"])
        assert len(result["hai"]) >= 1
        assert any("子未相害" in h["detail"] for h in result["hai"])

    def test_find_interactions_liupo(self):
        # 子酉破
        result = find_interactions(["子", "酉", "寅", "卯"])
        assert len(result["po"]) >= 1
        assert any("子酉相破" in p["detail"] for p in result["po"])

    def test_find_interactions_xiangxing(self):
        # 寅巳刑
        result = find_interactions(["寅", "巳", "辰", "戌"])
        assert len(result["xing"]) >= 1
        assert any("寅刑巳" in x["detail"] for x in result["xing"])

    def test_find_interactions_no_relations(self):
        result = find_interactions(["子", "寅", "辰", "午"])
        # 子-辰 = 三合水局成员，但 find_interactions 只检查六合/冲/害/破/刑，不检查三合
        # 子-寅 无直接关系，寅-辰 无直接关系，子-辰 无直接关系（三合不在此函数范围内）
        # 子-午 = 冲
        assert len(result["chong"]) >= 1  # 子午冲

    def test_find_interactions_multiple(self):
        # 多种关系同时存在
        result = find_interactions(["子", "丑", "午", "未"])
        # 子丑合，子午冲，子未害，丑午害，午未合
        assert len(result["he"]) >= 2  # 子丑合 + 午未合
        assert len(result["chong"]) >= 1  # 子午冲
        assert len(result["hai"]) >= 2  # 子未害 + 丑午害

    def test_find_interactions_pairs_analyzed(self):
        result = find_interactions(["子", "丑", "午", "未"])
        assert len(result["pairs_analyzed"]) > 0


# ============================================================================
# 七、枚举与数据类 测试
# ============================================================================

class TestEnums:
    def test_wuxing_values(self):
        assert Wuxing.MU.value == "木"
        assert Wuxing.HUO.value == "火"
        assert Wuxing.TU.value == "土"
        assert Wuxing.JIN.value == "金"
        assert Wuxing.SHUI.value == "水"

    def test_yinyang_values(self):
        assert Yinyang.YANG.value == "阳"
        assert Yinyang.YIN.value == "阴"

    def test_shigan_type_count(self):
        assert len(ShiganType) == 10


class TestShiganResultDataclass:
    def test_create_shigan_result(self):
        sr = ShiganResult(
            day_gan="甲",
            target_gan="丙",
            shigan=ShiganType.SHISHEN,
            description="test",
            wuxing_relation="木生火",
        )
        assert sr.day_gan == "甲"
        assert sr.target_gan == "丙"
        assert sr.shigan == ShiganType.SHISHEN
        assert sr.description == "test"
        assert sr.wuxing_relation == "木生火"