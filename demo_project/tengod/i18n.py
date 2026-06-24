#!/usr/bin/env python3
"""
i18n.py — 命理系统国际化模块 v2.3.0
第一阶段：多语言翻译层

支持语言：
  - zh-CN 简体中文（默认）
  - zh-TW 繁体中文
  - en    English

翻译范围：
  - 天干地支、五行、十神、神煞、格局
  - 二十四节气、十二时辰
  - 紫微斗数星曜、六爻卦名
  - API 响应描述、UI 文案

用法：
    from tengod.i18n import t, set_lang, get_lang, translate_bazi

    set_lang("en")
    print(t("甲木"))     # "Jia Wood"
    print(translate_bazi(pillars, lang="en"))
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "t",
    "set_lang",
    "get_lang",
    "translate_bazi",
    "translate_wuxing",
    "translate_shier",
    "I18nEngine",
    "get_i18n_engine",
]

_current_lang = "zh-CN"

_i18n_engine: Optional["I18nEngine"] = None


# ============================================================================
# 翻译表
# ============================================================================

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ── 天干 ─────────────────────────────────────────────────────────────
    "甲": {"zh-CN": "甲", "zh-TW": "甲", "en": "Jia"},
    "乙": {"zh-CN": "乙", "zh-TW": "乙", "en": "Yi"},
    "丙": {"zh-CN": "丙", "zh-TW": "丙", "en": "Bing"},
    "丁": {"zh-CN": "丁", "zh-TW": "丁", "en": "Ding"},
    "戊": {"zh-CN": "戊", "zh-TW": "戊", "en": "Wu"},
    "己": {"zh-CN": "己", "zh-TW": "己", "en": "Ji"},
    "庚": {"zh-CN": "庚", "zh-TW": "庚", "en": "Geng"},
    "辛": {"zh-CN": "辛", "zh-TW": "辛", "en": "Xin"},
    "壬": {"zh-CN": "壬", "zh-TW": "壬", "en": "Ren"},
    "癸": {"zh-CN": "癸", "zh-TW": "癸", "en": "Gui"},

    # ── 地支 ─────────────────────────────────────────────────────────────
    "子": {"zh-CN": "子", "zh-TW": "子", "en": "Zi"},
    "丑": {"zh-CN": "丑", "zh-TW": "醜", "en": "Chou"},
    "寅": {"zh-CN": "寅", "zh-TW": "寅", "en": "Yin"},
    "卯": {"zh-CN": "卯", "zh-TW": "卯", "en": "Mao"},
    "辰": {"zh-CN": "辰", "zh-TW": "辰", "en": "Chen"},
    "巳": {"zh-CN": "巳", "zh-TW": "巳", "en": "Si"},
    "午": {"zh-CN": "午", "zh-TW": "午", "en": "Wu"},
    "未": {"zh-CN": "未", "zh-TW": "未", "en": "Wei"},
    "申": {"zh-CN": "申", "zh-TW": "申", "en": "Shen"},
    "酉": {"zh-CN": "酉", "zh-TW": "酉", "en": "You"},
    "戌": {"zh-CN": "戌", "zh-TW": "戌", "en": "Xu"},
    "亥": {"zh-CN": "亥", "zh-TW": "亥", "en": "Hai"},

    # ── 五行 ─────────────────────────────────────────────────────────────
    "木": {"zh-CN": "木", "zh-TW": "木", "en": "Wood"},
    "火": {"zh-CN": "火", "zh-TW": "火", "en": "Fire"},
    "土": {"zh-CN": "土", "zh-TW": "土", "en": "Earth"},
    "金": {"zh-CN": "金", "zh-TW": "金", "en": "Metal"},
    "水": {"zh-CN": "水", "zh-TW": "水", "en": "Water"},

    # ── 五行状态 ────────────────────────────────────────────────────────
    "旺": {"zh-CN": "旺", "zh-TW": "旺", "en": "Prosperous"},
    "相": {"zh-CN": "相", "zh-TW": "相", "en": "Supporting"},
    "休": {"zh-CN": "休", "zh-TW": "休", "en": "Resting"},
    "囚": {"zh-CN": "囚", "zh-TW": "囚", "en": "Imprisoned"},
    "死": {"zh-CN": "死", "zh-TW": "死", "en": "Dead"},

    # ── 十神 ─────────────────────────────────────────────────────────────
    "比肩": {"zh-CN": "比肩", "zh-TW": "比肩", "en": "BiJian (Equal Companion)"},
    "劫财": {"zh-CN": "劫财", "zh-TW": "劫財", "en": "JieCai (Rob Wealth)"},
    "食神": {"zh-CN": "食神", "zh-TW": "食神", "en": "ShiShen (Eating God)"},
    "伤官": {"zh-CN": "伤官", "zh-TW": "傷官", "en": "ShangGuan (Hurting Officer)"},
    "偏财": {"zh-CN": "偏财", "zh-TW": "偏財", "en": "PianCai (Indirect Wealth)"},
    "正财": {"zh-CN": "正财", "zh-TW": "正財", "en": "ZhengCai (Direct Wealth)"},
    "七杀": {"zh-CN": "七杀", "zh-TW": "七殺", "en": "QiSha (Seven Killings)"},
    "正官": {"zh-CN": "正官", "zh-TW": "正官", "en": "ZhengGuan (Direct Officer)"},
    "偏印": {"zh-CN": "偏印", "zh-TW": "偏印", "en": "PianYin (Indirect Resource)"},
    "正印": {"zh-CN": "正印", "zh-TW": "正印", "en": "ZhengYin (Direct Resource)"},

    # ── 神煞 ─────────────────────────────────────────────────────────────
    "天乙贵人": {"zh-CN": "天乙贵人", "zh-TW": "天乙貴人", "en": "TianYi Nobleman"},
    "文昌": {"zh-CN": "文昌", "zh-TW": "文昌", "en": "WenChang"},
    "驿马": {"zh-CN": "驿马", "zh-TW": "驛馬", "en": "YiMa (Post Horse)"},
    "桃花": {"zh-CN": "桃花", "zh-TW": "桃花", "en": "Peach Blossom"},
    "将星": {"zh-CN": "将星", "zh-TW": "將星", "en": "JiangXing (General Star)"},
    "华盖": {"zh-CN": "华盖", "zh-TW": "華蓋", "en": "HuaGai (Canopy)"},
    "羊刃": {"zh-CN": "羊刃", "zh-TW": "羊刃", "en": "YangRen (Yang Blade)"},
    "亡神": {"zh-CN": "亡神", "zh-TW": "亡神", "en": "WangShen (Death God)"},
    "劫煞": {"zh-CN": "劫煞", "zh-TW": "劫煞", "en": "JieSha (Robbery Sha)"},
    "灾煞": {"zh-CN": "灾煞", "zh-TW": "災煞", "en": "ZaiSha (Calamity Sha)"},
    "天喜": {"zh-CN": "天喜", "zh-TW": "天喜", "en": "TianXi (Heavenly Joy)"},
    "红鸾": {"zh-CN": "红鸾", "zh-TW": "紅鸞", "en": "HongLuan (Red Phoenix)"},
    "天德贵人": {"zh-CN": "天德贵人", "zh-TW": "天德貴人", "en": "TianDe Nobleman"},
    "月德贵人": {"zh-CN": "月德贵人", "zh-TW": "月德貴人", "en": "YueDe Nobleman"},
    "天罗地网": {"zh-CN": "天罗地网", "zh-TW": "天羅地網", "en": "Net of Heaven and Earth"},
    "空亡": {"zh-CN": "空亡", "zh-TW": "空亡", "en": "KongWang (Void)"},
    "金舆": {"zh-CN": "金舆", "zh-TW": "金輿", "en": "JinYu (Golden Carriage)"},
    "国印": {"zh-CN": "国印", "zh-TW": "國印", "en": "GuoYin (National Seal)"},
    "三奇贵人": {"zh-CN": "三奇贵人", "zh-TW": "三奇貴人", "en": "SanQi Nobleman"},
    "天赦": {"zh-CN": "天赦", "zh-TW": "天赦", "en": "TianShe (Heavenly Pardon)"},

    # ── 格局 ─────────────────────────────────────────────────────────────
    "正官格": {"zh-CN": "正官格", "zh-TW": "正官格", "en": "Direct Officer Pattern"},
    "七杀格": {"zh-CN": "七杀格", "zh-TW": "七殺格", "en": "Seven Killings Pattern"},
    "正印格": {"zh-CN": "正印格", "zh-TW": "正印格", "en": "Direct Resource Pattern"},
    "偏印格": {"zh-CN": "偏印格", "zh-TW": "偏印格", "en": "Indirect Resource Pattern"},
    "正财格": {"zh-CN": "正财格", "zh-TW": "正財格", "en": "Direct Wealth Pattern"},
    "偏财格": {"zh-CN": "偏财格", "zh-TW": "偏財格", "en": "Indirect Wealth Pattern"},
    "食神格": {"zh-CN": "食神格", "zh-TW": "食神格", "en": "Eating God Pattern"},
    "伤官格": {"zh-CN": "伤官格", "zh-TW": "傷官格", "en": "Hurting Officer Pattern"},
    "建禄格": {"zh-CN": "建禄格", "zh-TW": "建祿格", "en": "JianLu Pattern"},
    "月刃格": {"zh-CN": "月刃格", "zh-TW": "月刃格", "en": "YueRen Pattern"},
    "从财格": {"zh-CN": "从财格", "zh-TW": "從財格", "en": "CongCai (Follow Wealth)"},
    "从官格": {"zh-CN": "从官格", "zh-TW": "從官格", "en": "CongGuan (Follow Officer)"},
    "从杀格": {"zh-CN": "从杀格", "zh-TW": "從殺格", "en": "CongSha (Follow Killings)"},
    "从儿格": {"zh-CN": "从儿格", "zh-TW": "從兒格", "en": "CongEr (Follow Output)"},
    "从势格": {"zh-CN": "从势格", "zh-TW": "從勢格", "en": "CongShi (Follow Momentum)"},
    "化气格": {"zh-CN": "化气格", "zh-TW": "化氣格", "en": "HuaQi (Transforming Qi)"},

    # ── 二十四节气 ──────────────────────────────────────────────────────
    "立春": {"zh-CN": "立春", "zh-TW": "立春", "en": "Lichun"},
    "雨水": {"zh-CN": "雨水", "zh-TW": "雨水", "en": "Yushui"},
    "惊蛰": {"zh-CN": "惊蛰", "zh-TW": "驚蟄", "en": "Jingzhe"},
    "春分": {"zh-CN": "春分", "zh-TW": "春分", "en": "Chunfen"},
    "清明": {"zh-CN": "清明", "zh-TW": "清明", "en": "Qingming"},
    "谷雨": {"zh-CN": "谷雨", "zh-TW": "穀雨", "en": "Guyu"},
    "立夏": {"zh-CN": "立夏", "zh-TW": "立夏", "en": "Lixia"},
    "小满": {"zh-CN": "小满", "zh-TW": "小滿", "en": "Xiaoman"},
    "芒种": {"zh-CN": "芒种", "zh-TW": "芒種", "en": "Mangzhong"},
    "夏至": {"zh-CN": "夏至", "zh-TW": "夏至", "en": "Xiazhi"},
    "小暑": {"zh-CN": "小暑", "zh-TW": "小暑", "en": "Xiaoshu"},
    "大暑": {"zh-CN": "大暑", "zh-TW": "大暑", "en": "Dashu"},
    "立秋": {"zh-CN": "立秋", "zh-TW": "立秋", "en": "Liqiu"},
    "处暑": {"zh-CN": "处暑", "zh-TW": "處暑", "en": "Chushu"},
    "白露": {"zh-CN": "白露", "zh-TW": "白露", "en": "Bailu"},
    "秋分": {"zh-CN": "秋分", "zh-TW": "秋分", "en": "Qiufen"},
    "寒露": {"zh-CN": "寒露", "zh-TW": "寒露", "en": "Hanlu"},
    "霜降": {"zh-CN": "霜降", "zh-TW": "霜降", "en": "Shuangjiang"},
    "立冬": {"zh-CN": "立冬", "zh-TW": "立冬", "en": "Lidong"},
    "小雪": {"zh-CN": "小雪", "zh-TW": "小雪", "en": "Xiaoxue"},
    "大雪": {"zh-CN": "大雪", "zh-TW": "大雪", "en": "Daxue"},
    "冬至": {"zh-CN": "冬至", "zh-TW": "冬至", "en": "Dongzhi"},
    "小寒": {"zh-CN": "小寒", "zh-TW": "小寒", "en": "Xiaohan"},
    "大寒": {"zh-CN": "大寒", "zh-TW": "大寒", "en": "Dahan"},

    # ── 十二时辰 ────────────────────────────────────────────────────────
    "子时": {"zh-CN": "子时", "zh-TW": "子時", "en": "Zi Hour (23-01)"},
    "丑时": {"zh-CN": "丑时", "zh-TW": "丑時", "en": "Chou Hour (01-03)"},
    "寅时": {"zh-CN": "寅时", "zh-TW": "寅時", "en": "Yin Hour (03-05)"},
    "卯时": {"zh-CN": "卯时", "zh-TW": "卯時", "en": "Mao Hour (05-07)"},
    "辰时": {"zh-CN": "辰时", "zh-TW": "辰時", "en": "Chen Hour (07-09)"},
    "巳时": {"zh-CN": "巳时", "zh-TW": "巳時", "en": "Si Hour (09-11)"},
    "午时": {"zh-CN": "午时", "zh-TW": "午時", "en": "Wu Hour (11-13)"},
    "未时": {"zh-CN": "未时", "zh-TW": "未時", "en": "Wei Hour (13-15)"},
    "申时": {"zh-CN": "申时", "zh-TW": "申時", "en": "Shen Hour (15-17)"},
    "酉时": {"zh-CN": "酉时", "zh-TW": "酉時", "en": "You Hour (17-19)"},
    "戌时": {"zh-CN": "戌时", "zh-TW": "戌時", "en": "Xu Hour (19-21)"},
    "亥时": {"zh-CN": "亥时", "zh-TW": "亥時", "en": "Hai Hour (21-23)"},

    # ── 六爻卦名 ────────────────────────────────────────────────────────
    "乾为天": {"zh-CN": "乾为天", "zh-TW": "乾為天", "en": "Qian (Heaven)"},
    "坤为地": {"zh-CN": "坤为地", "zh-TW": "坤為地", "en": "Kun (Earth)"},
    "震为雷": {"zh-CN": "震为雷", "zh-TW": "震為雷", "en": "Zhen (Thunder)"},
    "巽为风": {"zh-CN": "巽为风", "zh-TW": "巽為風", "en": "Xun (Wind)"},
    "坎为水": {"zh-CN": "坎为水", "zh-TW": "坎為水", "en": "Kan (Water)"},
    "离为火": {"zh-CN": "离为火", "zh-TW": "離為火", "en": "Li (Fire)"},
    "艮为山": {"zh-CN": "艮为山", "zh-TW": "艮為山", "en": "Gen (Mountain)"},
    "兑为泽": {"zh-CN": "兑为泽", "zh-TW": "兌為澤", "en": "Dui (Lake)"},

    # ── 紫微斗数主星 ────────────────────────────────────────────────────
    "紫微": {"zh-CN": "紫微", "zh-TW": "紫微", "en": "ZiWei (Purple Star)"},
    "天机": {"zh-CN": "天机", "zh-TW": "天機", "en": "TianJi (Heavenly Secret)"},
    "太阳": {"zh-CN": "太阳", "zh-TW": "太陽", "en": "TaiYang (Sun)"},
    "武曲": {"zh-CN": "武曲", "zh-TW": "武曲", "en": "WuQu (Martial Song)"},
    "天同": {"zh-CN": "天同", "zh-TW": "天同", "en": "TianTong (Heavenly Union)"},
    "廉贞": {"zh-CN": "廉贞", "zh-TW": "廉貞", "en": "LianZhen (Integrity)"},
    "天府": {"zh-CN": "天府", "zh-TW": "天府", "en": "TianFu (Heavenly Treasury)"},
    "太阴": {"zh-CN": "太阴", "zh-TW": "太陰", "en": "TaiYin (Moon)"},
    "贪狼": {"zh-CN": "贪狼", "zh-TW": "貪狼", "en": "TanLang (Greedy Wolf)"},
    "巨门": {"zh-CN": "巨门", "zh-TW": "巨門", "en": "JuMen (Huge Gate)"},
    "天相": {"zh-CN": "天相", "zh-TW": "天相", "en": "TianXiang (Heavenly Minister)"},
    "天梁": {"zh-CN": "天梁", "zh-TW": "天梁", "en": "TianLiang (Heavenly Ridge)"},
    "七杀": {"zh-CN": "七杀", "zh-TW": "七殺", "en": "QiSha (Seven Killings)"},
    "破军": {"zh-CN": "破军", "zh-TW": "破軍", "en": "PoJun (Victory Army)"},

    # ── 八字四柱 ────────────────────────────────────────────────────────
    "年柱": {"zh-CN": "年柱", "zh-TW": "年柱", "en": "Year Pillar"},
    "月柱": {"zh-CN": "月柱", "zh-TW": "月柱", "en": "Month Pillar"},
    "日柱": {"zh-CN": "日柱", "zh-TW": "日柱", "en": "Day Pillar"},
    "时柱": {"zh-CN": "时柱", "zh-TW": "時柱", "en": "Hour Pillar"},
    "命宫": {"zh-CN": "命宫", "zh-TW": "命宮", "en": "Life Palace"},
    "身宫": {"zh-CN": "身宫", "zh-TW": "身宮", "en": "Body Palace"},
    "日主": {"zh-CN": "日主", "zh-TW": "日主", "en": "Day Master"},
    "大运": {"zh-CN": "大运", "zh-TW": "大運", "en": "Major Fortune"},
    "流年": {"zh-CN": "流年", "zh-TW": "流年", "en": "Fleeting Year"},
    "小运": {"zh-CN": "小运", "zh-TW": "小運", "en": "Minor Fortune"},

    # ── 常见术语 ────────────────────────────────────────────────────────
    "天干": {"zh-CN": "天干", "zh-TW": "天干", "en": "Heavenly Stem"},
    "地支": {"zh-CN": "地支", "zh-TW": "地支", "en": "Earthly Branch"},
    "八字": {"zh-CN": "八字", "zh-TW": "八字", "en": "Bazi / Four Pillars"},
    "五行": {"zh-CN": "五行", "zh-TW": "五行", "en": "Five Elements"},
    "十神": {"zh-CN": "十神", "zh-TW": "十神", "en": "Ten Gods"},
    "神煞": {"zh-CN": "神煞", "zh-TW": "神煞", "en": "ShenSha"},
    "格局": {"zh-CN": "格局", "zh-TW": "格局", "en": "Pattern"},
    "喜用神": {"zh-CN": "喜用神", "zh-TW": "喜用神", "en": "Favorable God"},
    "调候": {"zh-CN": "调候", "zh-TW": "調候", "en": "Adjustment"},
    "月令": {"zh-CN": "月令", "zh-TW": "月令", "en": "Month Commander"},
    "天干地支": {"zh-CN": "天干地支", "zh-TW": "天干地支", "en": "Stems and Branches"},
    "相生": {"zh-CN": "相生", "zh-TW": "相生", "en": "Generates"},
    "相克": {"zh-CN": "相克", "zh-TW": "相克", "en": "Overcomes"},
    "相合": {"zh-CN": "相合", "zh-TW": "相合", "en": "Combines"},
    "相冲": {"zh-CN": "相冲", "zh-TW": "相沖", "en": "Clashes"},
    "相害": {"zh-CN": "相害", "zh-TW": "相害", "en": "Harms"},
    "相刑": {"zh-CN": "相刑", "zh-TW": "相刑", "en": "Punishes"},

    # ── UI 文案 ────────────────────────────────────────────────────────
    "命盘": {"zh-CN": "命盘", "zh-TW": "命盤", "en": "Chart"},
    "排盘": {"zh-CN": "排盘", "zh-TW": "排盤", "en": "Calculation"},
    "分析": {"zh-CN": "分析", "zh-TW": "分析", "en": "Analysis"},
    "综合": {"zh-CN": "综合", "zh-TW": "綜合", "en": "Comprehensive"},
    "事业": {"zh-CN": "事业", "zh-TW": "事業", "en": "Career"},
    "财运": {"zh-CN": "财运", "zh-TW": "財運", "en": "Wealth"},
    "婚姻": {"zh-CN": "婚姻", "zh-TW": "婚姻", "en": "Marriage"},
    "健康": {"zh-CN": "健康", "zh-TW": "健康", "en": "Health"},
    "感情": {"zh-CN": "感情", "zh-TW": "感情", "en": "Relationship"},
    "基础": {"zh-CN": "基础", "zh-TW": "基礎", "en": "Basic"},
    "智能分析": {"zh-CN": "智能分析", "zh-TW": "智慧分析", "en": "AI Analysis"},
    "命盘可视化": {"zh-CN": "命盘可视化", "zh-TW": "命盤可視化", "en": "Chart Visualization"},
    "真太阳时": {"zh-CN": "真太阳时", "zh-TW": "真太陽時", "en": "True Solar Time"},
    "五行旺衰": {"zh-CN": "五行旺衰", "zh-TW": "五行旺衰", "en": "Element Strength"},
    "知识图谱": {"zh-CN": "知识图谱", "zh-TW": "知識圖譜", "en": "Knowledge Graph"},
    "总览": {"zh-CN": "总览", "zh-TW": "總覽", "en": "Dashboard"},
    "任务": {"zh-CN": "任务", "zh-TW": "任務", "en": "Tasks"},
    "指标": {"zh-CN": "指标", "zh-TW": "指標", "en": "Metrics"},
    "设置": {"zh-CN": "设置", "zh-TW": "設定", "en": "Settings"},

    # ── 十二长生 ────────────────────────────────────────────────────────
    "长生": {"zh-CN": "长生", "zh-TW": "長生", "en": "ChangSheng (Birth)"},
    "沐浴": {"zh-CN": "沐浴", "zh-TW": "沐浴", "en": "MuYu (Bathing)"},
    "冠带": {"zh-CN": "冠带", "zh-TW": "冠帶", "en": "GuanDai (Capping)"},
    "临官": {"zh-CN": "临官", "zh-TW": "臨官", "en": "LinGuan (Official)"},
    "帝旺": {"zh-CN": "帝旺", "zh-TW": "帝旺", "en": "DiWang (Emperor)"},
    "衰": {"zh-CN": "衰", "zh-TW": "衰", "en": "Shuai (Decline)"},
    "病": {"zh-CN": "病", "zh-TW": "病", "en": "Bing (Sickness)"},
    "死": {"zh-CN": "死", "zh-TW": "死", "en": "Si (Death)"},
    "墓": {"zh-CN": "墓", "zh-TW": "墓", "en": "Mu (Grave)"},
    "绝": {"zh-CN": "绝", "zh-TW": "絕", "en": "Jue (Extinction)"},
    "胎": {"zh-CN": "胎", "zh-TW": "胎", "en": "Tai (Embryo)"},
    "养": {"zh-CN": "养", "zh-TW": "養", "en": "Yang (Nurture)"},

    # ── 纳音五行 ────────────────────────────────────────────────────────
    "海中金": {"zh-CN": "海中金", "zh-TW": "海中金", "en": "Gold in the Sea"},
    "炉中火": {"zh-CN": "炉中火", "zh-TW": "爐中火", "en": "Fire in the Furnace"},
    "大林木": {"zh-CN": "大林木", "zh-TW": "大林木", "en": "Wood of the Great Forest"},
    "路旁土": {"zh-CN": "路旁土", "zh-TW": "路旁土", "en": "Earth by the Road"},
    "剑锋金": {"zh-CN": "剑锋金", "zh-TW": "劍鋒金", "en": "Sword Edge Gold"},
    "山头火": {"zh-CN": "山头火", "zh-TW": "山頭火", "en": "Fire on the Mountain"},
    "涧下水": {"zh-CN": "涧下水", "zh-TW": "澗下水", "en": "Water in the Valley"},
    "城墙土": {"zh-CN": "城墙土", "zh-TW": "城牆土", "en": "City Wall Earth"},
    "白蜡金": {"zh-CN": "白蜡金", "zh-TW": "白蠟金", "en": "White Wax Gold"},
    "杨柳木": {"zh-CN": "杨柳木", "zh-TW": "楊柳木", "en": "Willow Wood"},
    "泉中水": {"zh-CN": "泉中水", "zh-TW": "泉中水", "en": "Water in the Spring"},
    "屋上土": {"zh-CN": "屋上土", "zh-TW": "屋上土", "en": "Earth on the Roof"},
    "霹雳火": {"zh-CN": "霹雳火", "zh-TW": "霹靂火", "en": "Thunderbolt Fire"},
    "松柏木": {"zh-CN": "松柏木", "zh-TW": "松柏木", "en": "Pine and Cypress Wood"},
    "长流水": {"zh-CN": "长流水", "zh-TW": "長流水", "en": "Long Flowing Water"},
    "沙中金": {"zh-CN": "沙中金", "zh-TW": "沙中金", "en": "Gold in the Sand"},
    "山下火": {"zh-CN": "山下火", "zh-TW": "山下火", "en": "Fire at the Foot of the Mountain"},
    "平地木": {"zh-CN": "平地木", "zh-TW": "平地木", "en": "Wood on the Plain"},
    "壁上土": {"zh-CN": "壁上土", "zh-TW": "壁上土", "en": "Earth on the Wall"},
    "金箔金": {"zh-CN": "金箔金", "zh-TW": "金箔金", "en": "Gold Foil"},
    "覆灯火": {"zh-CN": "覆灯火", "zh-TW": "覆燈火", "en": "Lamp Fire"},
    "天河水": {"zh-CN": "天河水", "zh-TW": "天河水", "en": "Heavenly River Water"},
    "大驿土": {"zh-CN": "大驿土", "zh-TW": "大驛土", "en": "Great Post Earth"},
    "钗钏金": {"zh-CN": "钗钏金", "zh-TW": "釵釧金", "en": "Hairpin Gold"},
    "桑柘木": {"zh-CN": "桑柘木", "zh-TW": "桑柘木", "en": "Mulberry Wood"},
    "大溪水": {"zh-CN": "大溪水", "zh-TW": "大溪水", "en": "Great Stream Water"},
    "沙中土": {"zh-CN": "沙中土", "zh-TW": "沙中土", "en": "Earth in the Sand"},
    "天上火": {"zh-CN": "天上火", "zh-TW": "天上火", "en": "Fire in the Sky"},
    "石榴木": {"zh-CN": "石榴木", "zh-TW": "石榴木", "en": "Pomegranate Wood"},
    "大海水": {"zh-CN": "大海水", "zh-TW": "大海水", "en": "Ocean Water"},

    # ── 神煞扩展 ────────────────────────────────────────────────────────
    "太极贵人": {"zh-CN": "太极贵人", "zh-TW": "太極貴人", "en": "TaiJi Nobleman"},
    "学堂": {"zh-CN": "学堂", "zh-TW": "學堂", "en": "XueTang (School)"},
    "词馆": {"zh-CN": "词馆", "zh-TW": "詞館", "en": "CiGuan (Academy)"},
    "禄神": {"zh-CN": "禄神", "zh-TW": "祿神", "en": "LuShen (Prosperity God)"},
    "魁罡": {"zh-CN": "魁罡", "zh-TW": "魁罡", "en": "KuiGang"},
    "孤辰": {"zh-CN": "孤辰", "zh-TW": "孤辰", "en": "GuChen (Lonely Star)"},
    "寡宿": {"zh-CN": "寡宿", "zh-TW": "寡宿", "en": "GuaSu (Widow Star)"},
    "元辰": {"zh-CN": "元辰", "zh-TW": "元辰", "en": "YuanChen (Origin Star)"},
    "暗禄": {"zh-CN": "暗禄", "zh-TW": "暗祿", "en": "AnLu (Hidden Prosperity)"},
    "天医": {"zh-CN": "天医", "zh-TW": "天醫", "en": "TianYi (Heavenly Doctor)"},
    "地网": {"zh-CN": "地网", "zh-TW": "地網", "en": "DiWang (Earth Net)"},
    "天罗": {"zh-CN": "天罗", "zh-TW": "天羅", "en": "TianLuo (Heaven Net)"},
    "血刃": {"zh-CN": "血刃", "zh-TW": "血刃", "en": "XueRen (Blood Blade)"},
    "流霞": {"zh-CN": "流霞", "zh-TW": "流霞", "en": "LiuXia (Flowing Glow)"},

    # ── 流年流月术语 ────────────────────────────────────────────────────
    "流月": {"zh-CN": "流月", "zh-TW": "流月", "en": "Fleeting Month"},
    "流日": {"zh-CN": "流日", "zh-TW": "流日", "en": "Fleeting Day"},
    "流时": {"zh-CN": "流时", "zh-TW": "流時", "en": "Fleeting Hour"},
    "太岁": {"zh-CN": "太岁", "zh-TW": "太歲", "en": "TaiSui (Grand Duke)"},
    "值太岁": {"zh-CN": "值太岁", "zh-TW": "值太歲", "en": "Offending TaiSui"},
    "冲太岁": {"zh-CN": "冲太岁", "zh-TW": "沖太歲", "en": "Clashing TaiSui"},
    "害太岁": {"zh-CN": "害太岁", "zh-TW": "害太歲", "en": "Harming TaiSui"},
    "破太岁": {"zh-CN": "破太岁", "zh-TW": "破太歲", "en": "Breaking TaiSui"},
    "刑太岁": {"zh-CN": "刑太岁", "zh-TW": "刑太歲", "en": "Punishing TaiSui"},
    "合太岁": {"zh-CN": "合太岁", "zh-TW": "合太歲", "en": "Combining TaiSui"},
}


# ============================================================================
# I18n 引擎
# ============================================================================

class I18nEngine:
    """国际化引擎"""

    def __init__(self, default_lang: str = "zh-CN"):
        self.default_lang = default_lang
        self.lang = default_lang
        self.translations = TRANSLATIONS
        self._custom: Dict[str, Dict[str, str]] = {}

    def set_lang(self, lang: str) -> None:
        """设置当前语言"""
        self.lang = lang if lang in ("zh-CN", "zh-TW", "en") else "zh-CN"

    def get_lang(self) -> str:
        """获取当前语言"""
        return self.lang

    def translate(self, text: str, lang: Optional[str] = None) -> str:
        """翻译单个词条

        若找不到翻译，返回原文。
        """
        target = lang or self.lang
        if target == "zh-CN":
            return text
        if text in self._custom and target in self._custom[text]:
            return self._custom[text][target]
        if text in self.translations and target in self.translations[text]:
            return self.translations[text][target]
        return text

    def translate_dict(
        self,
        data: Dict[str, Any],
        keys: Optional[List[str]] = None,
        lang: Optional[str] = None,
    ) -> Dict[str, Any]:
        """翻译字典中指定的 key

        Args:
            data: 原字典
            keys: 需要翻译的 key 列表，None 表示翻译所有值
            lang: 目标语言
        """
        result = dict(data)
        for key, val in data.items():
            if keys and key not in keys:
                continue
            if isinstance(val, str):
                result[key] = self.translate(val, lang)
            elif isinstance(val, dict):
                result[key] = self.translate_dict(val, lang=lang)
            elif isinstance(val, list):
                result[key] = [
                    self.translate(item, lang) if isinstance(item, str) else item
                    for item in val
                ]
        return result

    def add_custom(self, key: str, translations: Dict[str, str]) -> None:
        """添加自定义翻译"""
        self._custom[key] = translations

    def has_translation(self, text: str, lang: Optional[str] = None) -> bool:
        """检查是否有翻译"""
        target = lang or self.lang
        if text in self._custom and target in self._custom[text]:
            return True
        if text in self.translations and target in self.translations[text]:
            return True
        return False

    def get_available_langs(self) -> List[Dict[str, str]]:
        """获取可用语言列表"""
        return [
            {"code": "zh-CN", "name": "简体中文"},
            {"code": "zh-TW", "name": "繁體中文"},
            {"code": "en", "name": "English"},
        ]


# ============================================================================
# 便捷函数
# ============================================================================

def t(text: str, lang: Optional[str] = None) -> str:
    """翻译便捷函数"""
    engine = get_i18n_engine()
    return engine.translate(text, lang)


def set_lang(lang: str) -> None:
    """设置全局语言"""
    global _current_lang
    _current_lang = lang
    engine = get_i18n_engine()
    engine.set_lang(lang)


def get_lang() -> str:
    """获取当前语言"""
    return _current_lang


def get_i18n_engine() -> I18nEngine:
    """获取 i18n 引擎单例"""
    global _i18n_engine
    if _i18n_engine is None:
        _i18n_engine = I18nEngine()
    return _i18n_engine


def translate_bazi(pillars: Dict[str, str], lang: str = "en") -> Dict[str, str]:
    """翻译八字四柱

    Args:
        pillars: {"year": "甲子", "month": "丙寅", ...}
        lang: 目标语言

    Returns:
        翻译后的四柱字典
    """
    engine = get_i18n_engine()
    result = {}
    for pillar, ganzhi in pillars.items():
        if len(ganzhi) == 2:
            gan, zhi = ganzhi[0], ganzhi[1]
            result[pillar] = f"{engine.translate(gan, lang)} {engine.translate(zhi, lang)}"
        else:
            result[pillar] = engine.translate(ganzhi, lang)
    return result


def translate_wuxing(wuxing_data: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
    """翻译五行数据

    Args:
        wuxing_data: {"木": 3, "火": 2, ...} 或 {"木": {"status": "旺", "strength": 100}, ...}
        lang: 目标语言
    """
    engine = get_i18n_engine()
    result = {}
    for element, val in wuxing_data.items():
        key = engine.translate(element, lang)
        if isinstance(val, dict):
            val_copy = dict(val)
            if "status" in val_copy:
                val_copy["status"] = engine.translate(val_copy["status"], lang)
            result[key] = val_copy
        else:
            result[key] = val
    return result


def translate_shier(shichen: str, lang: str = "en") -> str:
    """翻译时辰

    Args:
        shichen: "子", "丑", ... 或 "子时", "丑时", ...
        lang: 目标语言
    """
    engine = get_i18n_engine()
    if len(shichen) == 1:
        key = shichen + "时"
        return engine.translate(key, lang)
    return engine.translate(shichen, lang)


# ============================================================================
# 兼容性别名（v2.16.1 —— 向后兼容旧版 API）
# ============================================================================

# I18nManager 兼容包装器（旧版名称，映射到 I18nEngine）
class I18nManager:
    """国际化管理器（兼容性别名，映射到 I18nEngine）"""

    def __init__(self, default_locale: str = "zh-CN"):
        self._engine = I18nEngine(default_lang=default_locale)
        self._locale = default_locale

    def get_locale(self) -> str:
        return self._locale

    def set_locale(self, locale: str) -> None:
        self._locale = locale
        self._engine.set_lang(locale)

    def translate(self, text: str) -> str:
        return self._engine.translate(text, self._locale)

    def bulk_translate(self, texts: List[str]) -> List[str]:
        return [self.translate(t) for t in texts]

    def get_all_locales(self) -> List[str]:
        return ["zh-CN", "zh-TW", "en", "ja", "ko", "vi"]

    def translate_bazi_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        out = {}
        for key, val in result.items():
            if isinstance(val, str):
                out[key] = self.translate(val)
            elif isinstance(val, list):
                out[key] = [self.translate(v) if isinstance(v, str) else v for v in val]
            else:
                out[key] = val
        return out

    def format_number(self, n: float) -> str:
        if self._locale == "en":
            return f"{n:,.1f}"
        return str(n)

    def format_date(self, date: Any) -> str:
        return date.isoformat() if hasattr(date, "isoformat") else str(date)

    def merge_custom_translations(self, locale: str, translations: Dict[str, str]) -> None:
        for key, val in translations.items():
            self._engine.add_custom(key, {locale: val})

    def get_ui_label(self, label: str) -> str:
        return self.translate(label)

    def get_locale_for_market(self, market: str) -> str:
        mapping = {
            "CN": "zh-CN", "TW": "zh-TW", "HK": "zh-TW",
            "US": "en", "GB": "en", "JP": "ja", "KR": "ko", "VN": "vi",
        }
        return mapping.get(market, "zh-CN")


def detect_locale_from_text(text: str) -> str:
    """从文本检测语言（兼容性函数）"""
    # 简单的 Unicode 范围检测
    hiragana = sum(1 for c in text if "\u3040" <= c <= "\u309f")
    katakana = sum(1 for c in text if "\u30a0" <= c <= "\u30ff")
    hangul = sum(1 for c in text if "\uac00" <= c <= "\ud7af")
    latin_vn = sum(1 for c in text if c in "àáảãạăắằẳẵặâấầẩẫậđêếềểễệôốồổỗộơớờởỡợưứừửữự")
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")

    if hiragana + katakana > 0:
        return "ja"
    if hangul > 0:
        return "ko"
    if latin_vn > 0:
        return "vi"
    if cjk > 0:
        return "zh-CN"
    return "en"


def get_i18n_manager() -> I18nManager:
    """获取 I18nManager 单例（兼容性别名）"""
    return I18nManager()
