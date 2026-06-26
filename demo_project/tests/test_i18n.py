#!/usr/bin/env python3
"""
test_i18n.py —— 国际化模块 (tengod/i18n.py) 全面测试
覆盖 I18nEngine、便捷函数、I18nManager、detect_locale_from_text 等。
目标覆盖率：95%+
"""

from __future__ import annotations

import datetime
import sys

import pytest

# ── 重置模块级全局状态（确保测试隔离） ──────────────────────────────────────
import tengod.i18n as i18n_mod


@pytest.fixture(autouse=True)
def _reset_i18n_state():
    """每个测试前重置全局状态"""
    i18n_mod._current_lang = "zh-CN"
    i18n_mod._i18n_engine = None
    yield
    i18n_mod._current_lang = "zh-CN"
    i18n_mod._i18n_engine = None


# ============================================================================
# 1. TRANSLATIONS 字典结构验证
# ============================================================================

class TestTranslationsDict:
    """验证 TRANSLATIONS 字典结构"""

    EXPECTED_CATEGORIES = [
        "天干", "地支", "五行", "五行状态", "十神", "神煞", "格局",
        "二十四节气", "十二时辰", "六爻", "紫微", "八字四柱", "常见术语",
        "UI 文案", "十二长生", "纳音", "神煞扩展", "流年流月",
    ]

    def test_all_expected_categories_present(self):
        """验证所有预期类别都存在（通过代表性条目检查）"""
        trans = i18n_mod.TRANSLATIONS

        # 天干
        for char in ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]:
            assert char in trans

        # 地支
        for char in ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]:
            assert char in trans

        # 五行
        for char in ["木", "火", "土", "金", "水"]:
            assert char in trans

        # 五行状态
        for char in ["旺", "相", "休", "囚"]:
            assert char in trans  # "死" has two entries, checked separately

        # 十神
        for char in ["比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"]:
            assert char in trans

        # 神煞
        for char in ["天乙贵人", "文昌", "驿马", "桃花", "将星", "华盖", "羊刃"]:
            assert char in trans

        # 格局
        for char in ["正官格", "七杀格", "建禄格", "月刃格"]:
            assert char in trans

        # 二十四节气
        for char in ["立春", "雨水", "惊蛰", "春分", "清明", "谷雨"]:
            assert char in trans

        # 十二时辰
        for char in ["子时", "丑时", "寅时", "卯时", "午时", "亥时"]:
            assert char in trans

        # 六爻
        for char in ["乾为天", "坤为地", "震为雷", "巽为风"]:
            assert char in trans

        # 紫微
        for char in ["紫微", "天机", "太阳", "武曲", "天同", "廉贞", "天府", "太阴"]:
            assert char in trans

        # 八字四柱
        for char in ["年柱", "月柱", "日柱", "时柱", "命宫", "身宫", "日主", "大运", "流年"]:
            assert char in trans

        # 常见术语
        for char in ["天干", "地支", "八字", "五行", "十神", "神煞", "格局", "喜用神", "调候"]:
            assert char in trans

        # UI 文案
        for char in ["命盘", "排盘", "分析", "综合", "事业", "财运", "婚姻", "健康", "设置"]:
            assert char in trans

        # 十二长生
        for char in ["长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "墓", "绝", "胎", "养"]:
            assert char in trans

        # 纳音
        for char in ["海中金", "炉中火", "大林木", "路旁土", "剑锋金"]:
            assert char in trans

        # 神煞扩展
        for char in ["太极贵人", "学堂", "词馆", "禄神", "魁罡"]:
            assert char in trans

        # 流年流月
        for char in ["流月", "流日", "流时", "太岁", "值太岁", "冲太岁"]:
            assert char in trans

    def test_translations_count_at_least_200(self):
        """验证 TRANSLATIONS 至少有 200 个条目"""
        assert len(i18n_mod.TRANSLATIONS) >= 200

    def test_zh_CN_always_returns_original(self):
        """zh-CN 键值始终等于原文"""
        for key, trans in i18n_mod.TRANSLATIONS.items():
            assert trans.get("zh-CN") == key, f"zh-CN mismatch for '{key}'"

    def test_zh_TW_has_different_chars_for_some_entries(self):
        """zh-TW 至少有一些条目与原文不同（繁体差异）"""
        diff_count = 0
        for key, trans in i18n_mod.TRANSLATIONS.items():
            if trans.get("zh-TW") != key:
                diff_count += 1
        assert diff_count > 0, "zh-TW should have some entries different from zh-CN"

    def test_zh_TW_specific_differences(self):
        """验证特定条目的 zh-TW 繁体差异"""
        translations = i18n_mod.TRANSLATIONS
        # 丑 → 醜
        assert translations["丑"]["zh-TW"] == "醜"
        # 伤官 → 傷官
        assert translations["伤官"]["zh-TW"] == "傷官"
        # 将星 → 將星
        assert translations["将星"]["zh-TW"] == "將星"
        # 华盖 → 華蓋
        assert translations["华盖"]["zh-TW"] == "華蓋"
        # 财 (偏财) → 財
        assert translations["偏财"]["zh-TW"] == "偏財"
        # 杀 (七杀) → 殺
        assert translations["七杀"]["zh-TW"] == "七殺"
        # 驿马 → 驛馬
        assert translations["驿马"]["zh-TW"] == "驛馬"
        # 灾煞 → 災煞
        assert translations["灾煞"]["zh-TW"] == "災煞"

    def test_all_entries_have_three_languages(self):
        """每个条目都包含 zh-CN, zh-TW, en"""
        for key, trans in i18n_mod.TRANSLATIONS.items():
            for lang in ["zh-CN", "zh-TW", "en"]:
                assert lang in trans, f"'{key}' missing language '{lang}'"


# ============================================================================
# 2. I18nEngine 类测试
# ============================================================================

class TestI18nEngineInit:
    """I18nEngine.__init__ 测试"""

    def test_init_default_lang(self):
        """默认语言为 zh-CN"""
        engine = i18n_mod.I18nEngine()
        assert engine.lang == "zh-CN"
        assert engine.default_lang == "zh-CN"

    def test_init_custom_lang(self):
        """自定义默认语言"""
        engine = i18n_mod.I18nEngine(default_lang="en")
        assert engine.lang == "en"
        assert engine.default_lang == "en"

    def test_init_custom_dict_is_empty(self):
        """初始化时自定义翻译字典为空"""
        engine = i18n_mod.I18nEngine()
        assert engine._custom == {}


class TestI18nEngineSetLang:
    """I18nEngine.set_lang 测试"""

    def test_set_lang_valid_zh_CN(self):
        engine = i18n_mod.I18nEngine(default_lang="en")
        engine.set_lang("zh-CN")
        assert engine.lang == "zh-CN"

    def test_set_lang_valid_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.lang == "zh-TW"

    def test_set_lang_valid_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.lang == "en"

    def test_set_lang_invalid_ja(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("ja")
        assert engine.lang == "zh-CN"  # 回退到默认

    def test_set_lang_invalid_ko(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("ko")
        assert engine.lang == "zh-CN"

    def test_set_lang_invalid_empty(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("")
        assert engine.lang == "zh-CN"

    def test_set_lang_invalid_random(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("xyz")
        assert engine.lang == "zh-CN"


class TestI18nEngineGetLang:
    """I18nEngine.get_lang 测试"""

    def test_get_lang_default(self):
        engine = i18n_mod.I18nEngine()
        assert engine.get_lang() == "zh-CN"

    def test_get_lang_after_set_lang(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.get_lang() == "en"


class TestI18nEngineTranslate:
    """I18nEngine.translate 测试"""

    # ── zh-CN 返回原文 ──────────────────────────────────────────────────

    def test_translate_zh_CN_returns_original(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-CN")
        assert engine.translate("甲") == "甲"
        assert engine.translate("伤官") == "伤官"
        assert engine.translate("天乙贵人") == "天乙贵人"
        assert engine.translate("anything") == "anything"

    # ── 天干 en ─────────────────────────────────────────────────────────

    def test_translate_gan_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        mapping = {
            "甲": "Jia", "乙": "Yi", "丙": "Bing", "丁": "Ding",
            "戊": "Wu", "己": "Ji", "庚": "Geng", "辛": "Xin",
            "壬": "Ren", "癸": "Gui",
        }
        for zh, en in mapping.items():
            assert engine.translate(zh) == en

    def test_translate_gan_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        for char in ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]:
            assert engine.translate(char) == char  # 天干 zh-TW 与 zh-CN 相同

    # ── 地支 en ─────────────────────────────────────────────────────────

    def test_translate_zhi_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        mapping = {
            "子": "Zi", "丑": "Chou", "寅": "Yin", "卯": "Mao",
            "辰": "Chen", "巳": "Si", "午": "Wu", "未": "Wei",
            "申": "Shen", "酉": "You", "戌": "Xu", "亥": "Hai",
        }
        for zh, en in mapping.items():
            assert engine.translate(zh) == en

    def test_translate_chou_zh_TW(self):
        """丑 → 醜 (zh-TW)"""
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("丑") == "醜"

    # ── 五行 en ─────────────────────────────────────────────────────────

    def test_translate_wuxing_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        mapping = {"木": "Wood", "火": "Fire", "土": "Earth", "金": "Metal", "水": "Water"}
        for zh, en in mapping.items():
            assert engine.translate(zh) == en

    def test_translate_wuxing_status_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("旺") == "Prosperous"
        assert engine.translate("相") == "Supporting"
        assert engine.translate("休") == "Resting"
        assert engine.translate("囚") == "Imprisoned"

    # ── 十神 en ─────────────────────────────────────────────────────────

    def test_translate_shishen_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("比肩") == "BiJian (Equal Companion)"
        assert engine.translate("劫财") == "JieCai (Rob Wealth)"
        assert engine.translate("食神") == "ShiShen (Eating God)"
        assert engine.translate("伤官") == "ShangGuan (Hurting Officer)"
        assert engine.translate("偏财") == "PianCai (Indirect Wealth)"
        assert engine.translate("正财") == "ZhengCai (Direct Wealth)"
        assert engine.translate("七杀") == "QiSha (Seven Killings)"
        assert engine.translate("正官") == "ZhengGuan (Direct Officer)"
        assert engine.translate("偏印") == "PianYin (Indirect Resource)"
        assert engine.translate("正印") == "ZhengYin (Direct Resource)"

    def test_translate_shishen_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        # 伤官 → 傷官
        assert engine.translate("伤官") == "傷官"
        # 劫财 → 劫財
        assert engine.translate("劫财") == "劫財"
        # 偏财 → 偏財
        assert engine.translate("偏财") == "偏財"
        # 正财 → 正財
        assert engine.translate("正财") == "正財"
        # 七杀 → 七殺
        assert engine.translate("七杀") == "七殺"

    # ── 神煞 en ─────────────────────────────────────────────────────────

    def test_translate_shensha_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("天乙贵人") == "TianYi Nobleman"
        assert engine.translate("文昌") == "WenChang"
        assert engine.translate("驿马") == "YiMa (Post Horse)"
        assert engine.translate("桃花") == "Peach Blossom"
        assert engine.translate("将星") == "JiangXing (General Star)"
        assert engine.translate("华盖") == "HuaGai (Canopy)"
        assert engine.translate("羊刃") == "YangRen (Yang Blade)"
        assert engine.translate("天德贵人") == "TianDe Nobleman"
        assert engine.translate("月德贵人") == "YueDe Nobleman"
        assert engine.translate("天罗地网") == "Net of Heaven and Earth"
        assert engine.translate("天赦") == "TianShe (Heavenly Pardon)"

    def test_translate_shensha_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("天乙贵人") == "天乙貴人"
        assert engine.translate("驿马") == "驛馬"
        assert engine.translate("将星") == "將星"
        assert engine.translate("华盖") == "華蓋"
        assert engine.translate("红鸾") == "紅鸞"
        assert engine.translate("天德贵人") == "天德貴人"
        assert engine.translate("天罗地网") == "天羅地網"
        assert engine.translate("金舆") == "金輿"
        assert engine.translate("国印") == "國印"
        assert engine.translate("三奇贵人") == "三奇貴人"

    # ── 格局 en ─────────────────────────────────────────────────────────

    def test_translate_geju_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("正官格") == "Direct Officer Pattern"
        assert engine.translate("七杀格") == "Seven Killings Pattern"
        assert engine.translate("正印格") == "Direct Resource Pattern"
        assert engine.translate("偏印格") == "Indirect Resource Pattern"
        assert engine.translate("正财格") == "Direct Wealth Pattern"
        assert engine.translate("偏财格") == "Indirect Wealth Pattern"
        assert engine.translate("食神格") == "Eating God Pattern"
        assert engine.translate("伤官格") == "Hurting Officer Pattern"
        assert engine.translate("建禄格") == "JianLu Pattern"
        assert engine.translate("月刃格") == "YueRen Pattern"
        assert engine.translate("从财格") == "CongCai (Follow Wealth)"
        assert engine.translate("从官格") == "CongGuan (Follow Officer)"
        assert engine.translate("从杀格") == "CongSha (Follow Killings)"
        assert engine.translate("从儿格") == "CongEr (Follow Output)"
        assert engine.translate("从势格") == "CongShi (Follow Momentum)"
        assert engine.translate("化气格") == "HuaQi (Transforming Qi)"

    def test_translate_geju_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("七杀格") == "七殺格"
        assert engine.translate("正财格") == "正財格"
        assert engine.translate("偏财格") == "偏財格"
        assert engine.translate("伤官格") == "傷官格"
        assert engine.translate("建禄格") == "建祿格"
        assert engine.translate("从财格") == "從財格"
        assert engine.translate("从官格") == "從官格"
        assert engine.translate("从杀格") == "從殺格"
        assert engine.translate("从儿格") == "從兒格"
        assert engine.translate("从势格") == "從勢格"
        assert engine.translate("化气格") == "化氣格"

    # ── 二十四节气 en ───────────────────────────────────────────────────

    def test_translate_jieqi_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        mapping = {
            "立春": "Lichun", "雨水": "Yushui", "惊蛰": "Jingzhe",
            "春分": "Chunfen", "清明": "Qingming", "谷雨": "Guyu",
            "立夏": "Lixia", "小满": "Xiaoman", "芒种": "Mangzhong",
            "夏至": "Xiazhi", "小暑": "Xiaoshu", "大暑": "Dashu",
            "立秋": "Liqiu", "处暑": "Chushu", "白露": "Bailu",
            "秋分": "Qiufen", "寒露": "Hanlu", "霜降": "Shuangjiang",
            "立冬": "Lidong", "小雪": "Xiaoxue", "大雪": "Daxue",
            "冬至": "Dongzhi", "小寒": "Xiaohan", "大寒": "Dahan",
        }
        for zh, en in mapping.items():
            assert engine.translate(zh) == en

    def test_translate_jieqi_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("惊蛰") == "驚蟄"
        assert engine.translate("谷雨") == "穀雨"
        assert engine.translate("小满") == "小滿"
        assert engine.translate("芒种") == "芒種"
        assert engine.translate("处暑") == "處暑"

    # ── 十二时辰 en ─────────────────────────────────────────────────────

    def test_translate_shichen_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("子时") == "Zi Hour (23-01)"
        assert engine.translate("丑时") == "Chou Hour (01-03)"
        assert engine.translate("寅时") == "Yin Hour (03-05)"
        assert engine.translate("卯时") == "Mao Hour (05-07)"
        assert engine.translate("午时") == "Wu Hour (11-13)"
        assert engine.translate("亥时") == "Hai Hour (21-23)"

    def test_translate_shichen_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("子时") == "子時"
        assert engine.translate("丑时") == "丑時"
        assert engine.translate("寅时") == "寅時"
        assert engine.translate("时柱") == "時柱"

    # ── 六爻 en ─────────────────────────────────────────────────────────

    def test_translate_liuyao_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("乾为天") == "Qian (Heaven)"
        assert engine.translate("坤为地") == "Kun (Earth)"
        assert engine.translate("震为雷") == "Zhen (Thunder)"
        assert engine.translate("巽为风") == "Xun (Wind)"
        assert engine.translate("坎为水") == "Kan (Water)"
        assert engine.translate("离为火") == "Li (Fire)"
        assert engine.translate("艮为山") == "Gen (Mountain)"
        assert engine.translate("兑为泽") == "Dui (Lake)"

    def test_translate_liuyao_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("乾为天") == "乾為天"
        assert engine.translate("坤为地") == "坤為地"
        assert engine.translate("离为火") == "離為火"
        assert engine.translate("兑为泽") == "兌為澤"

    # ── 紫微斗数 en ─────────────────────────────────────────────────────

    def test_translate_ziwei_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("紫微") == "ZiWei (Purple Star)"
        assert engine.translate("天机") == "TianJi (Heavenly Secret)"
        assert engine.translate("太阳") == "TaiYang (Sun)"
        assert engine.translate("武曲") == "WuQu (Martial Song)"
        assert engine.translate("天同") == "TianTong (Heavenly Union)"
        assert engine.translate("廉贞") == "LianZhen (Integrity)"
        assert engine.translate("天府") == "TianFu (Heavenly Treasury)"
        assert engine.translate("太阴") == "TaiYin (Moon)"
        assert engine.translate("贪狼") == "TanLang (Greedy Wolf)"
        assert engine.translate("巨门") == "JuMen (Huge Gate)"
        assert engine.translate("天相") == "TianXiang (Heavenly Minister)"
        assert engine.translate("天梁") == "TianLiang (Heavenly Ridge)"
        assert engine.translate("破军") == "PoJun (Victory Army)"

    def test_translate_ziwei_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("天机") == "天機"
        assert engine.translate("太阳") == "太陽"
        assert engine.translate("廉贞") == "廉貞"
        assert engine.translate("太阴") == "太陰"
        assert engine.translate("贪狼") == "貪狼"
        assert engine.translate("巨门") == "巨門"

    # ── 八字术语 en ─────────────────────────────────────────────────────

    def test_translate_bazi_terms_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("年柱") == "Year Pillar"
        assert engine.translate("月柱") == "Month Pillar"
        assert engine.translate("日柱") == "Day Pillar"
        assert engine.translate("时柱") == "Hour Pillar"
        assert engine.translate("命宫") == "Life Palace"
        assert engine.translate("身宫") == "Body Palace"
        assert engine.translate("日主") == "Day Master"
        assert engine.translate("大运") == "Major Fortune"
        assert engine.translate("流年") == "Fleeting Year"
        assert engine.translate("小运") == "Minor Fortune"
        assert engine.translate("天干") == "Heavenly Stem"
        assert engine.translate("地支") == "Earthly Branch"
        assert engine.translate("八字") == "Bazi / Four Pillars"
        assert engine.translate("五行") == "Five Elements"
        assert engine.translate("十神") == "Ten Gods"
        assert engine.translate("神煞") == "ShenSha"
        assert engine.translate("格局") == "Pattern"
        assert engine.translate("喜用神") == "Favorable God"
        assert engine.translate("调候") == "Adjustment"
        assert engine.translate("月令") == "Month Commander"
        assert engine.translate("天干地支") == "Stems and Branches"
        assert engine.translate("相生") == "Generates"
        assert engine.translate("相克") == "Overcomes"
        assert engine.translate("相合") == "Combines"
        assert engine.translate("相冲") == "Clashes"
        assert engine.translate("相害") == "Harms"
        assert engine.translate("相刑") == "Punishes"

    def test_translate_bazi_terms_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("大运") == "大運"
        assert engine.translate("小运") == "小運"
        assert engine.translate("调候") == "調候"
        assert engine.translate("相冲") == "相沖"
        assert engine.translate("命宫") == "命宮"
        assert engine.translate("身宫") == "身宮"

    # ── 十二长生 en ─────────────────────────────────────────────────────

    def test_translate_shier_changsheng_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("长生") == "ChangSheng (Birth)"
        assert engine.translate("沐浴") == "MuYu (Bathing)"
        assert engine.translate("冠带") == "GuanDai (Capping)"
        assert engine.translate("临官") == "LinGuan (Official)"
        assert engine.translate("帝旺") == "DiWang (Emperor)"
        assert engine.translate("衰") == "Shuai (Decline)"
        assert engine.translate("病") == "Bing (Sickness)"
        assert engine.translate("墓") == "Mu (Grave)"
        assert engine.translate("绝") == "Jue (Extinction)"
        assert engine.translate("胎") == "Tai (Embryo)"
        assert engine.translate("养") == "Yang (Nurture)"

    def test_translate_shier_changsheng_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("长生") == "長生"
        assert engine.translate("冠带") == "冠帶"
        assert engine.translate("临官") == "臨官"
        assert engine.translate("绝") == "絕"
        assert engine.translate("养") == "養"

    # ── 纳音 en ─────────────────────────────────────────────────────────

    def test_translate_nayin_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("海中金") == "Gold in the Sea"
        assert engine.translate("炉中火") == "Fire in the Furnace"
        assert engine.translate("大林木") == "Wood of the Great Forest"
        assert engine.translate("剑锋金") == "Sword Edge Gold"
        assert engine.translate("山头火") == "Fire on the Mountain"
        assert engine.translate("涧下水") == "Water in the Valley"
        assert engine.translate("城墙土") == "City Wall Earth"
        assert engine.translate("白蜡金") == "White Wax Gold"
        assert engine.translate("杨柳木") == "Willow Wood"
        assert engine.translate("泉中水") == "Water in the Spring"
        assert engine.translate("霹雳火") == "Thunderbolt Fire"
        assert engine.translate("松柏木") == "Pine and Cypress Wood"
        assert engine.translate("长流水") == "Long Flowing Water"
        assert engine.translate("沙中金") == "Gold in the Sand"
        assert engine.translate("大驿土") == "Great Post Earth"
        assert engine.translate("钗钏金") == "Hairpin Gold"
        assert engine.translate("桑柘木") == "Mulberry Wood"
        assert engine.translate("大溪水") == "Great Stream Water"
        assert engine.translate("沙中土") == "Earth in the Sand"
        assert engine.translate("天上火") == "Fire in the Sky"
        assert engine.translate("石榴木") == "Pomegranate Wood"
        assert engine.translate("大海水") == "Ocean Water"

    def test_translate_nayin_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("炉中火") == "爐中火"
        assert engine.translate("剑锋金") == "劍鋒金"
        assert engine.translate("山头火") == "山頭火"
        assert engine.translate("涧下水") == "澗下水"
        assert engine.translate("城墙土") == "城牆土"
        assert engine.translate("白蜡金") == "白蠟金"
        assert engine.translate("杨柳木") == "楊柳木"
        assert engine.translate("霹雳火") == "霹靂火"
        assert engine.translate("长流水") == "長流水"
        assert engine.translate("大驿土") == "大驛土"
        assert engine.translate("钗钏金") == "釵釧金"

    # ── UI 文案 en ──────────────────────────────────────────────────────

    def test_translate_ui_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("命盘") == "Chart"
        assert engine.translate("排盘") == "Calculation"
        assert engine.translate("分析") == "Analysis"
        assert engine.translate("综合") == "Comprehensive"
        assert engine.translate("事业") == "Career"
        assert engine.translate("财运") == "Wealth"
        assert engine.translate("婚姻") == "Marriage"
        assert engine.translate("健康") == "Health"
        assert engine.translate("感情") == "Relationship"
        assert engine.translate("基础") == "Basic"
        assert engine.translate("智能分析") == "AI Analysis"
        assert engine.translate("真太阳时") == "True Solar Time"
        assert engine.translate("总览") == "Dashboard"
        assert engine.translate("任务") == "Tasks"
        assert engine.translate("指标") == "Metrics"
        assert engine.translate("设置") == "Settings"

    def test_translate_ui_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("命盘") == "命盤"
        assert engine.translate("排盘") == "排盤"
        assert engine.translate("综合") == "綜合"
        assert engine.translate("事业") == "事業"
        assert engine.translate("财运") == "財運"
        assert engine.translate("基础") == "基礎"
        assert engine.translate("智能分析") == "智慧分析"
        assert engine.translate("真太阳时") == "真太陽時"
        assert engine.translate("知识图谱") == "知識圖譜"
        assert engine.translate("总览") == "總覽"
        assert engine.translate("任务") == "任務"
        assert engine.translate("指标") == "指標"
        assert engine.translate("设置") == "設定"

    # ── 神煞扩展 en ─────────────────────────────────────────────────────

    def test_translate_shensha_ext_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("太极贵人") == "TaiJi Nobleman"
        assert engine.translate("学堂") == "XueTang (School)"
        assert engine.translate("词馆") == "CiGuan (Academy)"
        assert engine.translate("禄神") == "LuShen (Prosperity God)"
        assert engine.translate("魁罡") == "KuiGang"
        assert engine.translate("天医") == "TianYi (Heavenly Doctor)"
        assert engine.translate("血刃") == "XueRen (Blood Blade)"
        assert engine.translate("流霞") == "LiuXia (Flowing Glow)"

    def test_translate_shensha_ext_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("太极贵人") == "太極貴人"
        assert engine.translate("学堂") == "學堂"
        assert engine.translate("词馆") == "詞館"
        assert engine.translate("禄神") == "祿神"
        assert engine.translate("暗禄") == "暗祿"
        assert engine.translate("天医") == "天醫"
        assert engine.translate("地网") == "地網"
        assert engine.translate("天罗") == "天羅"

    # ── 流年流月术语 en ─────────────────────────────────────────────────

    def test_translate_liunian_en(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("流月") == "Fleeting Month"
        assert engine.translate("流日") == "Fleeting Day"
        assert engine.translate("流时") == "Fleeting Hour"
        assert engine.translate("太岁") == "TaiSui (Grand Duke)"
        assert engine.translate("值太岁") == "Offending TaiSui"
        assert engine.translate("冲太岁") == "Clashing TaiSui"
        assert engine.translate("害太岁") == "Harming TaiSui"
        assert engine.translate("破太岁") == "Breaking TaiSui"
        assert engine.translate("刑太岁") == "Punishing TaiSui"
        assert engine.translate("合太岁") == "Combining TaiSui"

    def test_translate_liunian_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-TW")
        assert engine.translate("流时") == "流時"
        assert engine.translate("太岁") == "太歲"
        assert engine.translate("值太岁") == "值太歲"
        assert engine.translate("冲太岁") == "沖太歲"
        assert engine.translate("害太岁") == "害太歲"
        assert engine.translate("破太岁") == "破太歲"
        assert engine.translate("刑太岁") == "刑太歲"
        assert engine.translate("合太岁") == "合太歲"

    # ── 未知文本 ────────────────────────────────────────────────────────

    def test_translate_unknown_text_returns_original(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("不存在的文本") == "不存在的文本"
        assert engine.translate("∅∅∅") == "∅∅∅"

    def test_translate_empty_text(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("") == ""

    # ── 自定义翻译 ──────────────────────────────────────────────────────

    def test_translate_custom_via_add_custom(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        engine.add_custom("自定义词", {"en": "Custom Word", "zh-TW": "自訂詞"})
        assert engine.translate("自定义词") == "Custom Word"

    def test_translate_custom_overrides_builtin(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        engine.add_custom("甲", {"en": "JIA_OVERRIDE"})
        assert engine.translate("甲") == "JIA_OVERRIDE"

    # ── 显式 lang 参数覆盖引擎语言 ──────────────────────────────────────

    def test_translate_explicit_lang_overrides_engine_lang(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-CN")
        # 引擎是 zh-CN，但显式传入 en
        assert engine.translate("甲", lang="en") == "Jia"
        # 引擎语言未变
        assert engine.get_lang() == "zh-CN"

    def test_translate_explicit_lang_zh_TW(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("伤官", lang="zh-TW") == "傷官"

    def test_translate_explicit_lang_zh_CN(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("甲", lang="zh-CN") == "甲"


class TestI18nEngineTranslateDict:
    """I18nEngine.translate_dict 测试"""

    def test_translate_dict_all_values(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        data = {"element": "木", "direction": "子", "strength": "旺"}
        result = engine.translate_dict(data)
        assert result == {"element": "Wood", "direction": "Zi", "strength": "Prosperous"}

    def test_translate_dict_specific_keys(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        data = {"element": "木", "direction": "子", "strength": "旺"}
        result = engine.translate_dict(data, keys=["element", "strength"])
        assert result == {"element": "Wood", "direction": "子", "strength": "Prosperous"}

    def test_translate_dict_nested_dict(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        data = {"detail": {"element": "木", "status": "旺"}, "name": "甲"}
        result = engine.translate_dict(data)
        assert result["detail"]["element"] == "Wood"
        assert result["detail"]["status"] == "Prosperous"
        assert result["name"] == "Jia"

    def test_translate_dict_nested_list(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        data = {"elements": ["木", "火", "土"], "name": "甲"}
        result = engine.translate_dict(data)
        assert result["elements"] == ["Wood", "Fire", "Earth"]
        assert result["name"] == "Jia"

    def test_translate_dict_nested_list_mixed(self):
        """列表中非字符串项保持不变"""
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        data = {"items": ["木", 42, None, "火"]}
        result = engine.translate_dict(data)
        assert result["items"] == ["Wood", 42, None, "Fire"]

    def test_translate_dict_explicit_lang(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-CN")
        data = {"element": "木"}
        result = engine.translate_dict(data, lang="en")
        assert result == {"element": "Wood"}

    def test_translate_dict_empty(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate_dict({}) == {}


class TestI18nEngineAddCustom:
    """I18nEngine.add_custom 测试"""

    def test_add_custom_adds_translation(self):
        engine = i18n_mod.I18nEngine()
        engine.add_custom("test_key", {"en": "Test Value", "zh-TW": "測試值"})
        assert "test_key" in engine._custom
        assert engine._custom["test_key"]["en"] == "Test Value"

    def test_add_custom_multiple_keys(self):
        engine = i18n_mod.I18nEngine()
        engine.add_custom("k1", {"en": "v1"})
        engine.add_custom("k2", {"en": "v2"})
        assert "k1" in engine._custom
        assert "k2" in engine._custom


class TestI18nEngineHasTranslation:
    """I18nEngine.has_translation 测试"""

    def test_has_translation_true_builtin(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.has_translation("甲") is True

    def test_has_translation_true_custom(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        engine.add_custom("custom_k", {"en": "custom_v"})
        assert engine.has_translation("custom_k") is True

    def test_has_translation_false_unknown(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.has_translation("non_existent_key") is False

    def test_has_translation_explicit_lang(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.has_translation("甲", lang="zh-CN") is True

    def test_has_translation_false_explicit_lang(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        # "甲" exists in en but we check ja
        assert engine.has_translation("甲", lang="ja") is False


class TestI18nEngineGetAvailableLangs:
    """I18nEngine.get_available_langs 测试"""

    def test_get_available_langs_count(self):
        engine = i18n_mod.I18nEngine()
        langs = engine.get_available_langs()
        assert len(langs) == 3

    def test_get_available_langs_structure(self):
        engine = i18n_mod.I18nEngine()
        langs = engine.get_available_langs()
        codes = [l["code"] for l in langs]
        assert "zh-CN" in codes
        assert "zh-TW" in codes
        assert "en" in codes
        for lang in langs:
            assert "code" in lang
            assert "name" in lang


# ============================================================================
# 3. 便捷函数测试
# ============================================================================

class TestConvenienceFunctionT:
    """t() 便捷函数测试"""

    def test_t_returns_translated_text(self):
        i18n_mod.set_lang("en")
        assert i18n_mod.t("甲") == "Jia"
        assert i18n_mod.t("子") == "Zi"

    def test_t_with_explicit_lang(self):
        i18n_mod.set_lang("zh-CN")
        assert i18n_mod.t("甲", lang="en") == "Jia"

    def test_t_unknown_text(self):
        i18n_mod.set_lang("en")
        assert i18n_mod.t("不存在的") == "不存在的"


class TestConvenienceFunctionSetLang:
    """set_lang() 便捷函数测试"""

    def test_set_lang_updates_global(self):
        i18n_mod.set_lang("en")
        assert i18n_mod._current_lang == "en"

    def test_set_lang_updates_engine(self):
        i18n_mod.set_lang("en")
        engine = i18n_mod.get_i18n_engine()
        assert engine.get_lang() == "en"

    def test_set_lang_invalid(self):
        i18n_mod.set_lang("ja")
        assert i18n_mod._current_lang == "ja"  # _current_lang 直接赋值
        engine = i18n_mod.get_i18n_engine()
        assert engine.get_lang() == "zh-CN"  # 引擎拒绝无效语言


class TestConvenienceFunctionGetLang:
    """get_lang() 便捷函数测试"""

    def test_get_lang_default(self):
        assert i18n_mod.get_lang() == "zh-CN"

    def test_get_lang_after_set_lang(self):
        i18n_mod.set_lang("en")
        assert i18n_mod.get_lang() == "en"


class TestConvenienceFunctionGetI18nEngine:
    """get_i18n_engine() 便捷函数测试"""

    def test_get_i18n_engine_returns_singleton(self):
        engine1 = i18n_mod.get_i18n_engine()
        engine2 = i18n_mod.get_i18n_engine()
        assert engine1 is engine2

    def test_get_i18n_engine_is_i18n_engine_instance(self):
        engine = i18n_mod.get_i18n_engine()
        assert isinstance(engine, i18n_mod.I18nEngine)


class TestTranslateBazi:
    """translate_bazi() 函数测试"""

    def test_translate_bazi_2char_pillars(self):
        result = i18n_mod.translate_bazi(
            {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚午"},
            lang="en",
        )
        assert result["year"] == "Jia Zi"
        assert result["month"] == "Bing Yin"
        assert result["day"] == "Wu Chen"
        assert result["hour"] == "Geng Wu"

    def test_translate_bazi_single_char(self):
        result = i18n_mod.translate_bazi({"day": "甲"}, lang="en")
        assert result["day"] == "Jia"

    def test_translate_bazi_mixed(self):
        result = i18n_mod.translate_bazi(
            {"year": "甲子", "day": "丙"}, lang="en"
        )
        assert result["year"] == "Jia Zi"
        assert result["day"] == "Bing"

    def test_translate_bazi_empty(self):
        result = i18n_mod.translate_bazi({}, lang="en")
        assert result == {}

    def test_translate_bazi_zh_CN(self):
        result = i18n_mod.translate_bazi({"year": "甲子"}, lang="zh-CN")
        assert result["year"] == "甲 子"


class TestTranslateWuxing:
    """translate_wuxing() 函数测试"""

    def test_translate_wuxing_simple_dict(self):
        data = {"木": 3, "火": 2, "土": 1, "金": 4, "水": 0}
        result = i18n_mod.translate_wuxing(data, lang="en")
        assert result == {"Wood": 3, "Fire": 2, "Earth": 1, "Metal": 4, "Water": 0}

    def test_translate_wuxing_nested_dict_with_status(self):
        data = {"木": {"status": "旺", "strength": 100}, "火": {"status": "相", "strength": 80}}
        result = i18n_mod.translate_wuxing(data, lang="en")
        assert result["Wood"]["status"] == "Prosperous"
        assert result["Wood"]["strength"] == 100
        assert result["Fire"]["status"] == "Supporting"
        assert result["Fire"]["strength"] == 80

    def test_translate_wuxing_nested_dict_without_status(self):
        data = {"木": {"strength": 100, "count": 3}}
        result = i18n_mod.translate_wuxing(data, lang="en")
        assert result["Wood"]["strength"] == 100
        assert result["Wood"]["count"] == 3

    def test_translate_wuxing_empty(self):
        result = i18n_mod.translate_wuxing({}, lang="en")
        assert result == {}

    def test_translate_wuxing_default_lang(self):
        data = {"木": 3}
        result = i18n_mod.translate_wuxing(data)
        assert result == {"Wood": 3}  # default lang="en"


class TestTranslateShier:
    """translate_shier() 函数测试"""

    def test_translate_shier_single_char(self):
        result = i18n_mod.translate_shier("子", lang="en")
        assert result == "Zi Hour (23-01)"

    def test_translate_shier_with_shi(self):
        result = i18n_mod.translate_shier("子时", lang="en")
        assert result == "Zi Hour (23-01)"

    def test_translate_shier_all(self):
        for char in ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]:
            result = i18n_mod.translate_shier(char, lang="en")
            assert "Hour" in result

    def test_translate_shier_unknown_char(self):
        result = i18n_mod.translate_shier("X", lang="en")
        # "X时" is not in TRANSLATIONS, returns original
        assert result == "X时"

    def test_translate_shier_default_lang(self):
        result = i18n_mod.translate_shier("子")
        assert "Hour" in result  # default lang="en"


# ============================================================================
# 4. I18nManager 兼容性类测试
# ============================================================================

class TestI18nManagerInit:
    """I18nManager.__init__ 测试"""

    def test_init_default_locale(self):
        mgr = i18n_mod.I18nManager()
        assert mgr.get_locale() == "zh-CN"
        assert mgr._locale == "zh-CN"

    def test_init_custom_locale(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        assert mgr.get_locale() == "en"


class TestI18nManagerLocale:
    """I18nManager get_locale / set_locale 测试"""

    def test_get_locale(self):
        mgr = i18n_mod.I18nManager()
        assert mgr.get_locale() == "zh-CN"

    def test_set_locale(self):
        mgr = i18n_mod.I18nManager()
        mgr.set_locale("en")
        assert mgr.get_locale() == "en"

    def test_set_locale_updates_engine(self):
        mgr = i18n_mod.I18nManager()
        mgr.set_locale("en")
        assert mgr._engine.get_lang() == "en"


class TestI18nManagerTranslate:
    """I18nManager.translate 测试"""

    def test_translate_delegates_to_engine(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        assert mgr.translate("甲") == "Jia"

    def test_translate_unknown(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        assert mgr.translate("未知") == "未知"


class TestI18nManagerBulkTranslate:
    """I18nManager.bulk_translate 测试"""

    def test_bulk_translate_multiple(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        result = mgr.bulk_translate(["甲", "乙", "丙", "未知"])
        assert result == ["Jia", "Yi", "Bing", "未知"]

    def test_bulk_translate_empty(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        assert mgr.bulk_translate([]) == []


class TestI18nManagerGetAllLocales:
    """I18nManager.get_all_locales 测试"""

    def test_get_all_locales_returns_6(self):
        mgr = i18n_mod.I18nManager()
        locales = mgr.get_all_locales()
        assert len(locales) == 6
        assert "zh-CN" in locales
        assert "zh-TW" in locales
        assert "en" in locales
        assert "ja" in locales
        assert "ko" in locales
        assert "vi" in locales


class TestI18nManagerTranslateBaziResult:
    """I18nManager.translate_bazi_result 测试"""

    def test_translate_bazi_result_with_strings(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        data = {"year": "甲", "month": "丙", "day": "戊"}
        result = mgr.translate_bazi_result(data)
        assert result["year"] == "Jia"
        assert result["month"] == "Bing"

    def test_translate_bazi_result_with_lists(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        data = {"pillars": ["甲", "乙", "丙"], "count": 3}
        result = mgr.translate_bazi_result(data)
        assert result["pillars"] == ["Jia", "Yi", "Bing"]
        assert result["count"] == 3

    def test_translate_bazi_result_with_non_string(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        data = {"count": 42, "flag": True, "nested": [1, 2, 3]}
        result = mgr.translate_bazi_result(data)
        assert result["count"] == 42
        assert result["flag"] is True
        assert result["nested"] == [1, 2, 3]

    def test_translate_bazi_result_mixed_list(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        data = {"items": ["甲", 42, "乙"]}
        result = mgr.translate_bazi_result(data)
        assert result["items"] == ["Jia", 42, "Yi"]


class TestI18nManagerFormatNumber:
    """I18nManager.format_number 测试"""

    def test_format_number_en_locale(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        result = mgr.format_number(1234.5)
        assert result == "1,234.5"

    def test_format_number_zh_CN(self):
        mgr = i18n_mod.I18nManager(default_locale="zh-CN")
        result = mgr.format_number(1234.5)
        assert result == "1234.5"

    def test_format_number_zh_TW(self):
        mgr = i18n_mod.I18nManager(default_locale="zh-TW")
        result = mgr.format_number(1234.5)
        assert result == "1234.5"


class TestI18nManagerFormatDate:
    """I18nManager.format_date 测试"""

    def test_format_date_with_datetime(self):
        mgr = i18n_mod.I18nManager()
        dt = datetime.datetime(2026, 6, 26, 12, 0, 0)
        result = mgr.format_date(dt)
        assert "2026-06-26" in result

    def test_format_date_with_date(self):
        mgr = i18n_mod.I18nManager()
        d = datetime.date(2026, 6, 26)
        result = mgr.format_date(d)
        assert "2026-06-26" in result

    def test_format_date_with_non_datetime(self):
        mgr = i18n_mod.I18nManager()
        result = mgr.format_date("2026-06-26")
        assert result == "2026-06-26"


class TestI18nManagerMergeCustomTranslations:
    """I18nManager.merge_custom_translations 测试"""

    def test_merge_custom_translations_adds_to_engine(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        mgr.merge_custom_translations("en", {"custom_key": "Custom Value"})
        assert mgr._engine.has_translation("custom_key", lang="en") is True

    def test_merge_custom_translations_multiple(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        mgr.merge_custom_translations("en", {"k1": "v1", "k2": "v2"})
        assert mgr.translate("k1") == "v1"
        assert mgr.translate("k2") == "v2"


class TestI18nManagerGetUiLabel:
    """I18nManager.get_ui_label 测试"""

    def test_get_ui_label_delegates_to_translate(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        assert mgr.get_ui_label("甲") == "Jia"

    def test_get_ui_label_unknown(self):
        mgr = i18n_mod.I18nManager(default_locale="en")
        assert mgr.get_ui_label("未知标签") == "未知标签"


class TestI18nManagerGetLocaleForMarket:
    """I18nManager.get_locale_for_market 测试"""

    def test_get_locale_for_market_CN(self):
        mgr = i18n_mod.I18nManager()
        assert mgr.get_locale_for_market("CN") == "zh-CN"

    def test_get_locale_for_market_TW(self):
        mgr = i18n_mod.I18nManager()
        assert mgr.get_locale_for_market("TW") == "zh-TW"

    def test_get_locale_for_market_HK(self):
        mgr = i18n_mod.I18nManager()
        assert mgr.get_locale_for_market("HK") == "zh-TW"

    def test_get_locale_for_market_US(self):
        mgr = i18n_mod.I18nManager()
        assert mgr.get_locale_for_market("US") == "en"

    def test_get_locale_for_market_GB(self):
        mgr = i18n_mod.I18nManager()
        assert mgr.get_locale_for_market("GB") == "en"

    def test_get_locale_for_market_JP(self):
        mgr = i18n_mod.I18nManager()
        assert mgr.get_locale_for_market("JP") == "ja"

    def test_get_locale_for_market_KR(self):
        mgr = i18n_mod.I18nManager()
        assert mgr.get_locale_for_market("KR") == "ko"

    def test_get_locale_for_market_VN(self):
        mgr = i18n_mod.I18nManager()
        assert mgr.get_locale_for_market("VN") == "vi"

    def test_get_locale_for_market_unknown(self):
        mgr = i18n_mod.I18nManager()
        assert mgr.get_locale_for_market("XX") == "zh-CN"


# ============================================================================
# 5. detect_locale_from_text() 函数测试
# ============================================================================

class TestDetectLocaleFromText:
    """detect_locale_from_text() 测试"""

    def test_detect_japanese_hiragana(self):
        result = i18n_mod.detect_locale_from_text("こんにちは")
        assert result == "ja"

    def test_detect_japanese_katakana(self):
        result = i18n_mod.detect_locale_from_text("コンニチハ")
        assert result == "ja"

    def test_detect_japanese_mixed(self):
        result = i18n_mod.detect_locale_from_text("これは日本語です")
        assert result == "ja"

    def test_detect_korean_hangul(self):
        result = i18n_mod.detect_locale_from_text("안녕하세요")
        assert result == "ko"

    def test_detect_korean_hangul_mixed(self):
        result = i18n_mod.detect_locale_from_text("한국어 테스트")
        assert result == "ko"

    def test_detect_vietnamese_special_chars(self):
        result = i18n_mod.detect_locale_from_text("tiếng Việt")
        assert result == "vi"

    def test_detect_vietnamese_full(self):
        result = i18n_mod.detect_locale_from_text("Xin chào các bạn")
        assert result == "vi"

    def test_detect_chinese_cjk(self):
        result = i18n_mod.detect_locale_from_text("你好世界")
        assert result == "zh-CN"

    def test_detect_chinese_traditional(self):
        result = i18n_mod.detect_locale_from_text("你好世界嗎")
        assert result == "zh-CN"

    def test_detect_english_no_special(self):
        result = i18n_mod.detect_locale_from_text("Hello world")
        assert result == "en"

    def test_detect_english_only(self):
        result = i18n_mod.detect_locale_from_text("abcdefghijklmnop")
        assert result == "en"

    def test_detect_mixed_text(self):
        """日语优先于中文（hiragana/katakana 先检测）"""
        result = i18n_mod.detect_locale_from_text("これは日本語です 你好")
        assert result == "ja"

    def test_detect_korean_priority_over_chinese(self):
        """韩语优先于中文"""
        result = i18n_mod.detect_locale_from_text("안녕 你好")
        assert result == "ko"

    def test_detect_empty_text(self):
        result = i18n_mod.detect_locale_from_text("")
        assert result == "en"


# ============================================================================
# 6. get_i18n_manager() 兼容性函数测试
# ============================================================================

class TestGetI18nManager:
    """get_i18n_manager() 测试"""

    def test_get_i18n_manager_returns_i18n_manager(self):
        mgr = i18n_mod.get_i18n_manager()
        assert isinstance(mgr, i18n_mod.I18nManager)

    def test_get_i18n_manager_new_instance_each_time(self):
        """get_i18n_manager 每次返回新实例（非单例）"""
        mgr1 = i18n_mod.get_i18n_manager()
        mgr2 = i18n_mod.get_i18n_manager()
        assert mgr1 is not mgr2


# ============================================================================
# 7. 边缘情况测试
# ============================================================================

class TestEdgeCases:
    """边缘情况测试"""

    def test_empty_text_translate(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate("") == ""

    def test_translate_dict_empty(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        assert engine.translate_dict({}) == {}

    def test_translate_bazi_empty(self):
        result = i18n_mod.translate_bazi({}, lang="en")
        assert result == {}

    def test_translate_wuxing_empty(self):
        result = i18n_mod.translate_wuxing({}, lang="en")
        assert result == {}

    def test_translate_shier_unknown_char(self):
        result = i18n_mod.translate_shier("X", lang="en")
        assert result == "X时"

    def test_translate_nonexistent_category_entry(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        # 一个完全不在 TRANSLATIONS 中的文本
        assert engine.translate("∅NONEXISTENT∅") == "∅NONEXISTENT∅"

    def test_zh_CN_always_returns_original_engine(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("zh-CN")
        # 任何文本在 zh-CN 下都应返回原文
        assert engine.translate("甲") == "甲"
        assert engine.translate("anything") == "anything"
        assert engine.translate("") == ""

    def test_set_lang_invalid_preserves_previous(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        engine.set_lang("invalid")
        assert engine.get_lang() == "zh-CN"  # 无效值回退

    def test_translate_dict_no_keys_param(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        data = {"a": "木", "b": "火"}
        result = engine.translate_dict(data)
        assert result == {"a": "Wood", "b": "Fire"}

    def test_translate_dict_keys_none(self):
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        data = {"a": "木"}
        result = engine.translate_dict(data, keys=None)
        assert result == {"a": "Wood"}

    def test_translate_dict_original_unmodified(self):
        """translate_dict 不应修改原始字典"""
        engine = i18n_mod.I18nEngine()
        engine.set_lang("en")
        original = {"a": "木", "b": "火"}
        result = engine.translate_dict(original)
        assert original["a"] == "木"
        assert original["b"] == "火"
        assert result["a"] == "Wood"

    def test_translate_shier_all_chars(self):
        for char in ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]:
            result = i18n_mod.translate_shier(char, lang="en")
            assert "Hour" in result, f"translate_shier('{char}') returned '{result}'"

    def test_translate_shier_with_shi_all(self):
        for char in ["子时", "丑时", "寅时", "卯时", "辰时", "巳时",
                     "午时", "未时", "申时", "酉时", "戌时", "亥时"]:
            result = i18n_mod.translate_shier(char, lang="en")
            assert "Hour" in result, f"translate_shier('{char}') returned '{result}'"

    def test_initial_current_lang(self):
        assert i18n_mod._current_lang == "zh-CN"

    def test_i18n_engine_initial_none(self):
        assert i18n_mod._i18n_engine is None