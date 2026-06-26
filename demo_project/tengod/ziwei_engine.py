#!/usr/bin/env python3
"""
ziwei_engine.py — 紫微斗数排盘引擎 v1.0.0

紫微斗数是中国传统命理学中最重要的推命术之一，以出生年、月、日、时
配合十二宫位、星曜分布、四化飞星来推断人生吉凶祸福。

核心排盘流程：
  1. 定十二宫（命宫、兄弟、夫妻...）
  2. 定十二宫天干地支
  3. 定五行局
  4. 安紫微星
  5. 安十四主星（紫微系 + 天府系）
  6. 安辅星（左辅、右弼、文昌、文曲...）
  7. 定四化（化禄、化权、化科、化忌）
  8. 起大限
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# 常量定义
# ============================================================================

# 十二地支
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 十天干
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

# 十二宫名称
GONG_NAMES = [
    "命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄",
    "迁移", "交友", "官禄", "田宅", "福德", "父母"
]

# 十二宫英文名
GONG_EN = [
    "ming", "xiongdi", "fuqi", "zinv", "caibo", "jie",
    "qianyi", "jiaoyou", "guanlu", "tianzhai", "fude", "fumu"
]

# 紫微系六星排列顺序（从紫微逆排）
ZIWEI_SERIES = ["紫微", "天机", None, "太阳", "武曲", "天同", None, None, "廉贞"]

# 天府系八星排列顺序（从天府顺排）
TIANFU_SERIES = ["天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", None, None, None, "破军"]

# 五行局表（命宫干支 → 五行局）
# 甲乙锦江烟，丙丁没谷田，戊己营堤柳，庚辛挂杖钱，壬癸林钟满
WUXING_JU_MAP = {
    # 甲子乙丑 → 金四局
    ("甲", "子"): ("金", 4), ("乙", "丑"): ("金", 4),
    # 丙寅丁卯 → 火六局
    ("丙", "寅"): ("火", 6), ("丁", "卯"): ("火", 6),
    # 戊辰己巳 → 木三局
    ("戊", "辰"): ("木", 3), ("己", "巳"): ("木", 3),
    # 庚午辛未 → 土五局
    ("庚", "午"): ("土", 5), ("辛", "未"): ("土", 5),
    # 壬申癸酉 → 金四局
    ("壬", "申"): ("金", 4), ("癸", "酉"): ("金", 4),
    # 甲戌乙亥 → 火六局
    ("甲", "戌"): ("火", 6), ("乙", "亥"): ("火", 6),
    # 丙子丁丑 → 水二局
    ("丙", "子"): ("水", 2), ("丁", "丑"): ("水", 2),
    # 戊寅己卯 → 土五局
    ("戊", "寅"): ("土", 5), ("己", "卯"): ("土", 5),
    # 庚辰辛巳 → 金四局
    ("庚", "辰"): ("金", 4), ("辛", "巳"): ("金", 4),
    # 壬午癸未 → 木三局
    ("壬", "午"): ("木", 3), ("癸", "未"): ("木", 3),
    # 甲申乙酉 → 水二局
    ("甲", "申"): ("水", 2), ("乙", "酉"): ("水", 2),
    # 丙戌丁亥 → 土五局
    ("丙", "戌"): ("土", 5), ("丁", "亥"): ("土", 5),
    # 戊子己丑 → 火六局
    ("戊", "子"): ("火", 6), ("己", "丑"): ("火", 6),
    # 庚寅辛卯 → 木三局
    ("庚", "寅"): ("木", 3), ("辛", "卯"): ("木", 3),
    # 壬辰癸巳 → 水二局
    ("壬", "辰"): ("水", 2), ("癸", "巳"): ("水", 2),
    # 甲午乙未 → 金四局
    ("甲", "午"): ("金", 4), ("乙", "未"): ("金", 4),
    # 丙申丁酉 → 火六局
    ("丙", "申"): ("火", 6), ("丁", "酉"): ("火", 6),
    # 戊戌己亥 → 木三局
    ("戊", "戌"): ("木", 3), ("己", "亥"): ("木", 3),
    # 庚子辛丑 → 土五局
    ("庚", "子"): ("土", 5), ("辛", "丑"): ("土", 5),
    # 壬寅癸卯 → 金四局
    ("壬", "寅"): ("金", 4), ("癸", "卯"): ("金", 4),
    # 甲辰乙巳 → 火六局
    ("甲", "辰"): ("火", 6), ("乙", "巳"): ("火", 6),
    # 丙午丁未 → 水二局
    ("丙", "午"): ("水", 2), ("丁", "未"): ("水", 2),
    # 戊申己酉 → 土五局
    ("戊", "申"): ("土", 5), ("己", "酉"): ("土", 5),
    # 庚戌辛亥 → 金四局
    ("庚", "戌"): ("金", 4), ("辛", "亥"): ("金", 4),
    # 壬子癸丑 → 木三局
    ("壬", "子"): ("木", 3), ("癸", "丑"): ("木", 3),
    # 甲寅乙卯 → 水二局
    ("甲", "寅"): ("水", 2), ("乙", "卯"): ("水", 2),
    # 丙辰丁巳 → 土五局
    ("丙", "辰"): ("土", 5), ("丁", "巳"): ("土", 5),
    # 戊午己未 → 火六局
    ("戊", "午"): ("火", 6), ("己", "未"): ("火", 6),
    # 庚申辛酉 → 木三局
    ("庚", "申"): ("木", 3), ("辛", "酉"): ("木", 3),
    # 壬戌癸亥 → 水二局
    ("壬", "戌"): ("水", 2), ("癸", "亥"): ("水", 2),
}

# 四化表（天干 → 化禄、化权、化科、化忌）
SIHUA_MAP = {
    "甲": ("廉贞", "破军", "武曲", "太阳"),
    "乙": ("天机", "天梁", "紫微", "太阴"),
    "丙": ("天同", "天机", "文昌", "廉贞"),
    "丁": ("太阴", "天同", "天机", "巨门"),
    "戊": ("贪狼", "太阴", "右弼", "天机"),
    "己": ("武曲", "贪狼", "天梁", "文曲"),
    "庚": ("太阳", "武曲", "太阴", "天同"),
    "辛": ("巨门", "太阳", "文曲", "文昌"),
    "壬": ("天梁", "紫微", "左辅", "武曲"),
    "癸": ("破军", "巨门", "太阴", "贪狼"),
}

# 紫微星安放表（五行局 → {农历生日 → 紫微所在宫位}）
# 格式: 局数 → {生日: 地支索引}
ZIWEI_POSITION = {
    2: {  # 水二局
        1: 1, 2: 0, 3: 11, 4: 10, 5: 9, 6: 8, 7: 7, 8: 6, 9: 5, 10: 4,
        11: 3, 12: 2, 13: 1, 14: 0, 15: 11, 16: 10, 17: 9, 18: 8, 19: 7,
        20: 6, 21: 5, 22: 4, 23: 3, 24: 2, 25: 1, 26: 0, 27: 11, 28: 10,
        29: 9, 30: 8,
    },
    3: {  # 木三局
        1: 4, 2: 1, 3: 10, 4: 7, 5: 4, 6: 1, 7: 10, 8: 7, 9: 4, 10: 1,
        11: 10, 12: 7, 13: 4, 14: 1, 15: 10, 16: 7, 17: 4, 18: 1, 19: 10,
        20: 7, 21: 4, 22: 1, 23: 10, 24: 7, 25: 4, 26: 1, 27: 10, 28: 7,
        29: 4, 30: 1,
    },
    4: {  # 金四局
        1: 7, 2: 3, 3: 11, 4: 7, 5: 3, 6: 11, 7: 7, 8: 3, 9: 11, 10: 7,
        11: 3, 12: 11, 13: 7, 14: 3, 15: 11, 16: 7, 17: 3, 18: 11, 19: 7,
        20: 3, 21: 11, 22: 7, 23: 3, 24: 11, 25: 7, 26: 3, 27: 11, 28: 7,
        29: 3, 30: 11,
    },
    5: {  # 土五局
        1: 10, 2: 5, 3: 0, 4: 7, 5: 2, 6: 9, 7: 4, 8: 11, 9: 6, 10: 1,
        11: 8, 12: 3, 13: 10, 14: 5, 15: 0, 16: 7, 17: 2, 18: 9, 19: 4,
        20: 11, 21: 6, 22: 1, 23: 8, 24: 3, 25: 10, 26: 5, 27: 0, 28: 7,
        29: 2, 30: 9,
    },
    6: {  # 火六局
        1: 1, 2: 7, 3: 1, 4: 7, 5: 1, 6: 7, 7: 1, 8: 7, 9: 1, 10: 7,
        11: 1, 12: 7, 13: 1, 14: 7, 15: 1, 16: 7, 17: 1, 18: 7, 19: 1,
        20: 7, 21: 1, 22: 7, 23: 1, 24: 7, 25: 1, 26: 7, 27: 1, 28: 7,
        29: 1, 30: 7,
    },
}


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class StarInfo:
    """星曜信息"""
    name: str          # 星名
    level: str         # 等级: 主星/辅星/四化
    wuxing: str        # 五行属性
    sheng_ke: str = "" # 生克说明
    description: str = ""  # 星曜描述


@dataclass
class GongInfo:
    """宫位信息"""
    name: str              # 宫名
    en_name: str           # 英文名
    zhi: str               # 地支
    gan: str               # 天干
    stars: List[str] = field(default_factory=list)  # 主星
    aux_stars: List[str] = field(default_factory=list)  # 辅星
    sihua: str = ""        # 四化标记
    daxian_range: str = "" # 大限范围


@dataclass
class ZiweiChart:
    """紫微斗数命盘"""
    # 基本信息
    year: int
    month: int
    day: int
    hour: int
    minute: int
    gender: str          # "male" / "female"
    year_gan: str        # 年干
    year_zhi: str        # 年支
    lunar_month: int     # 农历月
    lunar_day: int       # 农历日
    hour_zhi: str        # 时支
    
    # 命宫信息
    ming_gong_index: int     # 命宫地支索引
    shen_gong_index: int     # 身宫地支索引
    wuxing_ju: str           # 五行局
    wuxing_ju_num: int       # 五行局数
    
    # 十二宫
    gongs: List[GongInfo] = field(default_factory=list)
    
    # 四化
    hua_lu: str = ""     # 化禄星
    hua_quan: str = ""   # 化权星
    hua_ke: str = ""     # 化科星
    hua_ji: str = ""     # 化忌星
    
    # 身主
    shen_zhu: str = ""   # 身主星
    ming_zhu: str = ""   # 命主星
    
    # 大限
    daxian: List[Dict[str, Any]] = field(default_factory=list)


# ============================================================================
# 主星属性
# ============================================================================

STAR_PROPERTIES = {
    "紫微": {"level": "主星", "wuxing": "己土", "desc": "帝王星，尊贵权威，统御全局"},
    "天机": {"level": "主星", "wuxing": "乙木", "desc": "智谋星，机变灵活，善谋略"},
    "太阳": {"level": "主星", "wuxing": "丙火", "desc": "光明星，热情博爱，主贵显"},
    "武曲": {"level": "主星", "wuxing": "辛金", "desc": "财帛星，刚毅果断，理财专家"},
    "天同": {"level": "主星", "wuxing": "壬水", "desc": "福寿星，温和善良，享福之人"},
    "廉贞": {"level": "主星", "wuxing": "丁火", "desc": "囚星，亦正亦邪，才华横溢"},
    "天府": {"level": "主星", "wuxing": "戊土", "desc": "库星，包容稳重，财富库藏"},
    "太阴": {"level": "主星", "wuxing": "癸水", "desc": "阴柔星，温柔细腻，母性之光"},
    "贪狼": {"level": "主星", "wuxing": "甲木/癸水", "desc": "桃花星，多才多艺，欲望强烈"},
    "巨门": {"level": "主星", "wuxing": "癸水", "desc": "暗星，口才犀利，是非口舌"},
    "天相": {"level": "主星", "wuxing": "壬水", "desc": "印星，辅佐之才，公正无私"},
    "天梁": {"level": "主星", "wuxing": "戊土", "desc": "荫星，老成持重，庇佑他人"},
    "七杀": {"level": "主星", "wuxing": "庚金", "desc": "将星，勇猛果断，开拓进取"},
    "破军": {"level": "主星", "wuxing": "癸水", "desc": "耗星，破旧立新，敢作敢为"},
}

AUX_STAR_PROPERTIES = {
    "左辅":   {"level": "辅星", "wuxing": "戊土", "desc": "辅佐贵人，左膀右臂"},
    "右弼":   {"level": "辅星", "wuxing": "癸水", "desc": "辅助贵人，暗助之力"},
    "文昌":   {"level": "辅星", "wuxing": "辛金", "desc": "文才星，科甲功名"},
    "文曲":   {"level": "辅星", "wuxing": "癸水", "desc": "文艺星，才艺出众"},
    "天魁":   {"level": "辅星", "wuxing": "丙火", "desc": "天乙贵人，科甲之喜"},
    "天钺":   {"level": "辅星", "wuxing": "丁火", "desc": "玉堂贵人，暗中扶持"},
    "禄存":   {"level": "辅星", "wuxing": "己土", "desc": "财禄星，衣食无忧"},
    "擎羊":   {"level": "辅星", "wuxing": "庚金", "desc": "刑伤星，刚强冲动"},
    "陀罗":   {"level": "辅星", "wuxing": "辛金", "desc": "暗伤星，拖延阻碍"},
    "火星":   {"level": "辅星", "wuxing": "丙火", "desc": "暴烈星，突发急变"},
    "铃星":   {"level": "辅星", "wuxing": "丁火", "desc": "暗火星，阴险算计"},
    "地空":   {"level": "辅星", "wuxing": "丁火", "desc": "空亡星，虚无幻想"},
    "地劫":   {"level": "辅星", "wuxing": "丙火", "desc": "劫煞星，波折损失"},
    "天马":   {"level": "辅星", "wuxing": "丙火", "desc": "驿马星，奔波远行"},
}


# ============================================================================
# 核心引擎
# ============================================================================

class ZiweiEngine:
    """紫微斗数排盘引擎"""

    # ── 农历转换（基于2000-2050年数据） ──
    # 农历闰月表：年 -> 闰月月份（0表示无闰月）
    _LUNAR_LEAP_MONTH = {
        2000: 0, 2001: 4, 2002: 0, 2003: 2, 2004: 0, 2005: 0, 2006: 7,
        2007: 0, 2008: 0, 2009: 5, 2010: 0, 2011: 4, 2012: 0, 2013: 0,
        2014: 9, 2015: 0, 2016: 0, 2017: 6, 2018: 0, 2019: 0, 2020: 4,
        2021: 0, 2022: 0, 2023: 2, 2024: 0, 2025: 6, 2026: 0, 2027: 0,
        2028: 5, 2029: 0, 2030: 3, 2031: 0, 2032: 0, 2033: 11, 2034: 0,
        2035: 0, 2036: 6, 2037: 0, 2038: 0, 2039: 5, 2040: 0, 2041: 4,
        2042: 0, 2043: 0, 2044: 8, 2045: 0, 2046: 0, 2047: 2, 2048: 0,
        2049: 7, 2050: 0,
    }

    # 农历每月天数表：年 -> [1月,2月,...,12月] 天数(29/30)
    _LUNAR_MONTH_DAYS = {
        2000: [29,30,29,30,29,30,29,30,30,29,30,29],
        2001: [30,29,30,29,30,29,30,29,30,29,30,30],
        2002: [29,30,29,30,29,30,29,30,29,30,29,30],
        2003: [30,30,29,30,29,30,29,30,29,30,29,30],
        2004: [29,30,29,30,29,30,29,29,30,29,30,29],
        2005: [30,29,30,29,30,29,30,29,30,29,30,29],
        2006: [30,29,30,29,30,29,30,29,30,29,30,30],
        2007: [29,30,29,30,29,30,29,30,29,30,29,30],
        2008: [29,30,29,30,29,30,29,30,29,30,29,30],
        2009: [30,29,30,29,30,30,29,30,29,30,29,30],
        2010: [29,30,29,30,29,30,29,30,29,30,29,30],
        2011: [30,29,30,29,30,29,30,29,30,29,30,30],
        2012: [29,30,29,30,29,30,29,30,29,30,29,30],
        2013: [29,30,29,30,29,30,29,30,29,30,29,30],
        2014: [30,29,30,29,30,29,30,29,30,29,30,30],
        2015: [29,30,29,30,29,30,29,30,29,30,29,30],
        2016: [30,29,30,29,30,29,30,30,29,30,29,30],
        2017: [29,30,29,30,29,30,29,30,29,30,29,30],
        2018: [29,30,29,30,29,30,29,30,29,30,29,30],
        2019: [30,29,30,29,30,29,30,29,30,30,29,30],
        2020: [29,30,29,30,29,30,29,30,29,30,29,30],
        2021: [29,30,29,30,29,30,29,30,29,30,29,30],
        2022: [30,29,30,29,30,29,30,29,30,29,30,29],
        2023: [29,30,29,30,29,30,29,30,30,29,30,29],
        2024: [29,30,29,30,29,30,29,30,29,30,29,30],
        2025: [30,29,30,29,30,29,30,29,30,29,30,30],
        2026: [29,30,29,30,29,30,29,30,29,30,29,30],
        2027: [29,30,29,30,29,30,29,30,29,30,29,30],
        2028: [30,29,30,29,30,30,29,30,29,30,29,30],
        2029: [29,30,29,30,29,30,29,30,29,30,29,30],
        2030: [30,29,30,30,29,30,29,30,29,30,29,30],
        2031: [29,30,29,30,29,30,29,30,29,30,29,30],
        2032: [30,29,30,29,30,29,30,29,30,29,30,29],
        2033: [30,29,30,29,30,29,30,29,30,29,30,30],
        2034: [29,30,29,30,29,30,29,30,29,30,29,30],
        2035: [29,30,29,30,29,30,29,30,29,30,29,30],
        2036: [30,29,30,29,30,29,30,30,29,30,29,30],
        2037: [29,30,29,30,29,30,29,30,29,30,29,30],
        2038: [29,30,29,30,29,30,29,30,30,29,30,29],
        2039: [30,29,30,29,30,29,30,29,30,29,30,29],
        2040: [30,29,30,29,30,29,30,29,30,29,30,29],
        2041: [30,29,30,30,29,30,29,30,29,30,29,30],
        2042: [29,30,29,30,29,30,29,30,29,30,29,30],
        2043: [29,30,29,30,29,30,29,30,29,30,29,30],
        2044: [30,29,30,29,30,29,30,29,30,30,29,30],
        2045: [29,30,29,30,29,30,29,30,29,30,29,30],
        2046: [29,30,29,30,29,30,29,30,29,30,29,30],
        2047: [30,29,30,29,30,29,30,29,30,29,30,29],
        2048: [30,29,30,29,30,29,30,29,30,29,30,29],
        2049: [30,29,30,29,30,29,30,30,29,30,29,30],
        2050: [29,30,29,30,29,30,29,30,29,30,29,30],
    }

    # 闰月天数表：年 -> 闰月天数（无闰月为0）
    _LUNAR_LEAP_DAYS = {
        2000: 0, 2001: 29, 2002: 0, 2003: 30, 2004: 0, 2005: 0, 2006: 29,
        2007: 0, 2008: 0, 2009: 29, 2010: 0, 2011: 29, 2012: 0, 2013: 0,
        2014: 29, 2015: 0, 2016: 0, 2017: 29, 2018: 0, 2019: 0, 2020: 29,
        2021: 0, 2022: 0, 2023: 29, 2024: 0, 2025: 29, 2026: 0, 2027: 0,
        2028: 29, 2029: 0, 2030: 29, 2031: 0, 2032: 0, 2033: 30, 2034: 0,
        2035: 0, 2036: 29, 2037: 0, 2038: 0, 2039: 29, 2040: 0, 2041: 29,
        2042: 0, 2043: 0, 2044: 29, 2045: 0, 2046: 0, 2047: 29, 2048: 0,
        2049: 29, 2050: 0,
    }

    # 农历正月初一对应的公历日期（年->日序号，1月1日=0）
    _LUNAR_NEW_YEAR_OFFSET = {
        2000: 35, 2001: 23, 2002: 42, 2003: 31, 2004: 21, 2005: 39, 2006: 28,
        2007: 48, 2008: 37, 2009: 25, 2010: 44, 2011: 33, 2012: 22, 2013: 40,
        2014: 30, 2015: 49, 2016: 38, 2017: 27, 2018: 46, 2019: 35, 2020: 24,
        2021: 42, 2022: 31, 2023: 21, 2024: 40, 2025: 28, 2026: 47, 2027: 36,
        2028: 25, 2029: 43, 2030: 33, 2031: 22, 2032: 41, 2033: 30, 2034: 49,
        2035: 38, 2036: 27, 2037: 45, 2038: 34, 2039: 23, 2040: 42, 2041: 31,
        2042: 21, 2043: 40, 2044: 29, 2045: 47, 2046: 36, 2047: 25, 2048: 44,
        2049: 32, 2050: 53,
    }

    @classmethod
    def _is_leap_year(cls, year: int) -> bool:
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

    @classmethod
    def _days_in_month(cls, year: int, month: int) -> int:
        if month in (1, 3, 5, 7, 8, 10, 12):
            return 31
        if month in (4, 6, 9, 11):
            return 30
        return 29 if cls._is_leap_year(year) else 28

    @classmethod
    def _day_of_year(cls, year: int, month: int, day: int) -> int:
        """计算公历日期是当年的第几天"""
        days = day
        for m in range(1, month):
            days += cls._days_in_month(year, m)
        return days

    @classmethod
    def _lunar_year_days(cls, year: int) -> int:
        """计算农历年的总天数"""
        if year not in cls._LUNAR_MONTH_DAYS:
            return 354
        total = sum(cls._LUNAR_MONTH_DAYS[year])
        leap = cls._lunar_leap_month(year)
        if leap > 0:
            total += cls._lunar_leap_days(year)
        return total

    @classmethod
    def _lunar_leap_month(cls, year: int) -> int:
        """获取闰月（0表示无闰月）"""
        return cls._LUNAR_LEAP_MONTH.get(year, 0)

    @classmethod
    def _lunar_month_days(cls, year: int, month: int) -> int:
        """获取农历月的天数（非闰月）"""
        if year not in cls._LUNAR_MONTH_DAYS:
            return 29
        return cls._LUNAR_MONTH_DAYS[year][month - 1]

    @classmethod
    def _lunar_leap_days(cls, year: int) -> int:
        """获取闰月天数，0表示无闰月"""
        return cls._LUNAR_LEAP_DAYS.get(year, 0)

    @classmethod
    def solar_to_lunar(cls, year: int, month: int, day: int) -> Tuple[int, int, int, bool]:
        """
        公历转农历（简化版）
        返回: (农历年, 农历月, 农历日, 是否闰月)
        """
        def date_offset(y, m, d):
            offset = d - 1
            for mm in range(1, m):
                offset += cls._days_in_month(y, mm)
            return offset

        def year_days_total(y):
            return 366 if cls._is_leap_year(y) else 365

        doy = date_offset(year, month, day)
        ny_offset = cls._LUNAR_NEW_YEAR_OFFSET.get(year, 40)

        if doy >= ny_offset:
            lunar_year = year
            days_since_ny = doy - ny_offset
        else:
            lunar_year = year - 1
            prev_ny = cls._LUNAR_NEW_YEAR_OFFSET.get(lunar_year, 40)
            prev_total = year_days_total(lunar_year)
            days_since_ny = (prev_total - prev_ny) + doy

        leap_month = cls._lunar_leap_month(lunar_year)
        leap_days_count = cls._lunar_leap_days(lunar_year)
        
        current = 0
        for m in range(1, 13):
            mdays = cls._lunar_month_days(lunar_year, m)
            if days_since_ny < current + mdays:
                return (lunar_year, m, days_since_ny - current + 1, False)
            current += mdays
            if m == leap_month and leap_days_count > 0:
                if days_since_ny < current + leap_days_count:
                    return (lunar_year, m, days_since_ny - current + 1, True)
                current += leap_days_count

        return (lunar_year, 12, 29, False)

    # ── 排盘核心方法 ──

    @classmethod
    def _get_hour_zhi(cls, hour: int, minute: int = 0) -> str:
        """根据小时获取时辰地支"""
        # 子时: 23:00-01:00, 丑时: 01:00-03:00, ...
        hour_index = ((hour + 1) // 2) % 12
        return DI_ZHI[hour_index]

    @classmethod
    def _get_year_ganzhi(cls, year: int) -> Tuple[str, str]:
        """获取年干支"""
        gan_idx = (year - 4) % 10
        zhi_idx = (year - 4) % 12
        return TIAN_GAN[gan_idx], DI_ZHI[zhi_idx]

    @classmethod
    def _get_month_gan(cls, year_gan: str, month_zhi_idx: int) -> str:
        """五虎遁：根据年干和月支获取月干"""
        base = TIAN_GAN.index(year_gan)
        # 甲己→丙寅(2), 乙庚→戊寅(4), 丙辛→庚寅(6), 丁壬→壬寅(8), 戊癸→甲寅(0)
        start = (2 + base * 2) % 10
        gan_idx = (start + (month_zhi_idx - 2)) % 10  # 寅月为正月
        return TIAN_GAN[gan_idx]

    @classmethod
    def _get_ming_gong(cls, lunar_month: int, hour_zhi: str) -> Tuple[int, int]:
        """
        安命宫/身宫
        从寅宫起正月，顺数至生月；再从该宫起子时，逆数至生时 → 命宫
        从寅宫起正月，顺数至生月；再从该宫起子时，顺数至生时 → 身宫
        返回: (命宫地支索引, 身宫地支索引)
        """
        # 寅宫索引为2
        month_gong = (2 + lunar_month - 1) % 12  # 顺数
        hour_idx = DI_ZHI.index(hour_zhi)
        # 命宫: 逆数
        ming_gong = (month_gong - hour_idx) % 12
        # 身宫: 顺数
        shen_gong = (month_gong + hour_idx) % 12
        return ming_gong, shen_gong

    @classmethod
    def _get_12_gongs_ganzhi(cls, ming_gong_idx: int, year_gan: str) -> List[Tuple[str, str]]:
        """
        定十二宫天干地支
        从命宫开始逆时针排列十二宫
        天干用五虎遁法
        """
        result = []
        for i in range(12):
            # 逆时针：命宫 → 兄弟 → 夫妻 → ...
            gong_zhi_idx = (ming_gong_idx - i) % 12
            gong_zhi = DI_ZHI[gong_zhi_idx]
            # 五虎遁定天干
            gong_gan = cls._get_month_gan(year_gan, gong_zhi_idx)
            result.append((gong_gan, gong_zhi))
        return result

    @classmethod
    def _get_wuxing_ju(cls, gan: str, zhi: str) -> Tuple[str, int]:
        """根据命宫干支获取五行局"""
        key = (gan, zhi)
        return WUXING_JU_MAP.get(key, ("土", 5))

    @classmethod
    def _get_ziwei_pos(cls, wuxing_ju_num: int, lunar_day: int) -> int:
        """根据五行局数和农历生日确定紫微星位置"""
        # 生日超过30取30
        if lunar_day > 30:
            lunar_day = 30
        pos_table = ZIWEI_POSITION.get(wuxing_ju_num, {})
        return pos_table.get(lunar_day, 2)  # 默认寅宫

    @classmethod
    def _place_ziwei_series(cls, ziwei_pos: int) -> Dict[int, str]:
        """安放紫微系六星（逆排）"""
        stars = {}
        # 紫微系列：紫微在ziwei_pos，然后逆排
        for i, star in enumerate(ZIWEI_SERIES):
            if star:
                pos = (ziwei_pos - i) % 12
                stars[pos] = star
        return stars

    @classmethod
    def _place_tianfu_series(cls, ziwei_pos: int) -> Dict[int, str]:
        """安放天府系八星（顺排）"""
        # 天府与紫微的关系：紫微在寅→天府在辰（紫微+2顺排）
        # 通用公式：天府位置 = (紫微位置 + 4 - 2*(紫微位置%3)) % 12
        # 更简单：紫微在A，天府在B，A+B=4(寅+辰=2+4=6→4)
        tianfu_pos = (4 - ziwei_pos) % 12
        
        stars = {}
        for i, star in enumerate(TIANFU_SERIES):
            if star:
                pos = (tianfu_pos + i) % 12
                stars[pos] = star
        return stars

    @classmethod
    def _place_aux_stars(cls, year_zhi: str, hour_zhi: str, lunar_month: int, lunar_day: int,
                         year_gan: str) -> Dict[int, List[str]]:
        """安放辅星"""
        aux = {i: [] for i in range(12)}
        year_zhi_idx = DI_ZHI.index(year_zhi)
        hour_zhi_idx = DI_ZHI.index(hour_zhi)
        
        # 左辅: 辰起正月顺数至生月
        left_pos = (4 + lunar_month - 1) % 12
        aux[left_pos].append("左辅")
        
        # 右弼: 戌起正月逆数至生月
        right_pos = (10 - (lunar_month - 1)) % 12
        aux[right_pos].append("右弼")
        
        # 文昌: 戌起子时逆数至生时
        wenchang_pos = (10 - hour_zhi_idx) % 12
        aux[wenchang_pos].append("文昌")
        
        # 文曲: 辰起子时顺数至生时
        wenqu_pos = (4 + hour_zhi_idx) % 12
        aux[wenqu_pos].append("文曲")
        
        # 天魁/天钺: 根据年干
        # 甲戊庚牛羊, 乙己鼠猴乡, 丙丁猪鸡位, 壬癸兔蛇藏, 六辛逢马虎
        kuiyue_map = {
            "甲": (1, 8), "戊": (1, 8), "庚": (1, 8),  # 丑未
            "乙": (0, 7), "己": (0, 7),               # 子申
            "丙": (11, 9), "丁": (11, 9),              # 亥酉
            "壬": (3, 5), "癸": (3, 5),               # 卯巳
            "辛": (6, 2),                              # 午寅
        }
        if year_gan in kuiyue_map:
            kui, yue = kuiyue_map[year_gan]
            aux[kui].append("天魁")
            aux[yue].append("天钺")
        
        # 禄存: 根据年干
        # 甲禄寅, 乙禄卯, 丙戊禄巳, 丁己禄午, 庚禄申, 辛禄酉, 壬禄亥, 癸禄子
        lucun_map = {"甲": 2, "乙": 3, "丙": 5, "戊": 5, "丁": 6, "己": 6,
                      "庚": 8, "辛": 9, "壬": 11, "癸": 0}
        lucun_pos = lucun_map.get(year_gan, 2)
        aux[lucun_pos].append("禄存")
        
        # 擎羊: 禄存前一位
        qingyang_pos = (lucun_pos + 1) % 12
        aux[qingyang_pos].append("擎羊")
        
        # 陀罗: 禄存后一位
        tuoluo_pos = (lucun_pos - 1) % 12
        aux[tuoluo_pos].append("陀罗")
        
        # 火星/铃星: 根据年支和时支
        # 火星: 寅午戌-丑起, 申子辰-寅起, 巳酉丑-卯起, 亥卯未-酉起
        huo_start = {0: 2, 2: 2, 6: 2, 8: 3, 4: 3, 9: 3, 5: 6, 1: 9, 10: 9}.get(
            year_zhi_idx, 2)
        # 根据三合局
        if year_zhi_idx in (2, 6, 10):  # 寅午戌
            huo_start = 1  # 丑
        elif year_zhi_idx in (8, 0, 4):  # 申子辰
            huo_start = 2  # 寅
        elif year_zhi_idx in (5, 9, 1):  # 巳酉丑
            huo_start = 3  # 卯
        elif year_zhi_idx in (11, 3, 7):  # 亥卯未
            huo_start = 9  # 酉
        huo_pos = (huo_start + hour_zhi_idx) % 12
        aux[huo_pos].append("火星")
        
        # 铃星: 寅午戌-卯起, 申子辰-戌起, 巳酉丑-戌起, 亥卯未-戌起
        if year_zhi_idx in (2, 6, 10):
            ling_start = 3  # 卯
        elif year_zhi_idx in (8, 0, 4):
            ling_start = 10  # 戌
        elif year_zhi_idx in (5, 9, 1):
            ling_start = 10  # 戌
        else:
            ling_start = 10  # 戌
        ling_pos = (ling_start + hour_zhi_idx) % 12
        aux[ling_pos].append("铃星")
        
        # 地空: 亥起子时逆数至生时
        dikong_pos = (11 - hour_zhi_idx) % 12
        aux[dikong_pos].append("地空")
        
        # 地劫: 亥起子时顺数至生时
        dijie_pos = (11 + hour_zhi_idx) % 12
        aux[dijie_pos].append("地劫")
        
        # 天马: 根据年支三合
        tianma_map = {2: 8, 6: 8, 10: 8, 8: 2, 0: 2, 4: 2, 5: 11, 9: 11, 1: 11, 11: 5, 3: 5, 7: 5}
        tianma_pos = tianma_map.get(year_zhi_idx, 8)
        aux[tianma_pos].append("天马")
        
        return aux

    @classmethod
    def _get_sihua(cls, year_gan: str) -> Tuple[str, str, str, str]:
        """根据年干获取四化"""
        return SIHUA_MAP.get(year_gan, ("", "", "", ""))

    @classmethod
    def _get_mingshen_zhu(cls, year_zhi: str, hour_zhi: str) -> Tuple[str, str]:
        """获取命主和身主"""
        # 命主: 根据命宫地支（用年支代替简化）
        ming_zhu_map = {
            "子": "贪狼", "丑": "巨门", "寅": "禄存", "卯": "文曲",
            "辰": "廉贞", "巳": "武曲", "午": "破军", "未": "武曲",
            "申": "廉贞", "酉": "文曲", "戌": "禄存", "亥": "巨门",
        }
        # 身主: 根据年支
        shen_zhu_map = {
            "子": "火星", "丑": "天相", "寅": "天梁", "卯": "天同",
            "辰": "文昌", "巳": "天机", "午": "火星", "未": "天相",
            "申": "天梁", "酉": "天同", "戌": "文昌", "亥": "天机",
        }
        ming_zhu = ming_zhu_map.get(year_zhi, "贪狼")
        shen_zhu = shen_zhu_map.get(year_zhi, "天机")
        return ming_zhu, shen_zhu

    @classmethod
    def _get_daxian(cls, wuxing_ju_num: int, gender: str, year_gan: str,
                    ming_gong_idx: int) -> List[Dict[str, Any]]:
        """
        起大限
        阳男阴女顺行，阴男阳女逆行
        阳干: 甲丙戊庚壬，阴干: 乙丁己辛癸
        """
        yang_gan = set("甲丙戊庚壬")
        is_yang = year_gan in yang_gan
        is_male = gender == "male"
        shun_xing = (is_yang and is_male) or (not is_yang and not is_male)
        
        daxian = []
        # 起始年龄 = 五行局数
        start_age = wuxing_ju_num
        
        for i in range(12):
            if shun_xing:
                gong_idx = (ming_gong_idx + i) % 12
            else:
                gong_idx = (ming_gong_idx - i) % 12
            
            age_start = start_age + i * 10
            age_end = age_start + 9
            
            daxian.append({
                "gong_name": GONG_NAMES[gong_idx],
                "gong_index": gong_idx,
                "age_range": f"{age_start}-{age_end}岁",
                "start_age": age_start,
                "end_age": age_end,
            })
        
        return daxian

    # ── 公开接口 ──

    @classmethod
    def calc_chart(cls, year: int, month: int, day: int, hour: int = 0,
                   minute: int = 0, gender: str = "male") -> ZiweiChart:
        """
        完整紫微斗数排盘
        
        参数:
            year: 公历年
            month: 公历月
            day: 公历日
            hour: 小时 (0-23)
            minute: 分钟 (0-59)
            gender: "male" / "female"
        
        返回:
            ZiweiChart 完整命盘
        """
        # 1. 获取年干支和时支
        year_gan, year_zhi = cls._get_year_ganzhi(year)
        hour_zhi = cls._get_hour_zhi(hour, minute)
        
        # 2. 公历转农历
        lunar_year, lunar_month, lunar_day, is_leap = cls.solar_to_lunar(year, month, day)
        
        # 3. 安命宫/身宫
        ming_gong_idx, shen_gong_idx = cls._get_ming_gong(lunar_month, hour_zhi)
        
        # 4. 定十二宫天干地支
        gong_ganzhi = cls._get_12_gongs_ganzhi(ming_gong_idx, year_gan)
        
        # 5. 定五行局
        wuxing_ju, wuxing_ju_num = cls._get_wuxing_ju(gong_ganzhi[0][0], gong_ganzhi[0][1])
        
        # 6. 安紫微星
        ziwei_pos = cls._get_ziwei_pos(wuxing_ju_num, lunar_day)
        
        # 7. 安主星
        ziwei_stars = cls._place_ziwei_series(ziwei_pos)
        tianfu_stars = cls._place_tianfu_series(ziwei_pos)
        all_main_stars = {}
        for pos, star in ziwei_stars.items():
            all_main_stars.setdefault(pos, []).append(star)
        for pos, star in tianfu_stars.items():
            all_main_stars.setdefault(pos, []).append(star)
        
        # 8. 安辅星
        aux_stars = cls._place_aux_stars(year_zhi, hour_zhi, lunar_month, lunar_day, year_gan)
        
        # 9. 定四化
        hua_lu, hua_quan, hua_ke, hua_ji = cls._get_sihua(year_gan)
        sihua_map = {
            hua_lu: "禄", hua_quan: "权", hua_ke: "科", hua_ji: "忌"
        }
        
        # 10. 命主/身主
        ming_zhu, shen_zhu = cls._get_mingshen_zhu(year_zhi, hour_zhi)
        
        # 11. 构建十二宫
        gongs = []
        for i in range(12):
            gan, zhi = gong_ganzhi[i]
            main = all_main_stars.get(i, [])
            aux = aux_stars.get(i, [])
            
            # 四化标记
            sihua_tags = []
            for star in main + aux:
                if star in sihua_map:
                    sihua_tags.append(f"{star}化{sihua_map[star]}")
            
            gongs.append(GongInfo(
                name=GONG_NAMES[i],
                en_name=GONG_EN[i],
                zhi=zhi,
                gan=gan,
                stars=main,
                aux_stars=aux,
                sihua=", ".join(sihua_tags) if sihua_tags else "",
            ))
        
        # 12. 大限
        daxian = cls._get_daxian(wuxing_ju_num, gender, year_gan, ming_gong_idx)
        
        return ZiweiChart(
            year=year, month=month, day=day, hour=hour, minute=minute,
            gender=gender,
            year_gan=year_gan, year_zhi=year_zhi,
            lunar_month=lunar_month, lunar_day=lunar_day,
            hour_zhi=hour_zhi,
            ming_gong_index=ming_gong_idx,
            shen_gong_index=shen_gong_idx,
            wuxing_ju=wuxing_ju,
            wuxing_ju_num=wuxing_ju_num,
            gongs=gongs,
            hua_lu=hua_lu, hua_quan=hua_quan, hua_ke=hua_ke, hua_ji=hua_ji,
            shen_zhu=shen_zhu, ming_zhu=ming_zhu,
            daxian=daxian,
        )

    @classmethod
    def to_dict(cls, chart: ZiweiChart) -> Dict[str, Any]:
        """将命盘转为字典"""
        return {
            "input": {
                "solar": f"{chart.year}-{chart.month:02d}-{chart.day:02d} {chart.hour:02d}:{chart.minute:02d}",
                "lunar": f"{chart.lunar_month}月{chart.lunar_day}日",
                "gender": "男" if chart.gender == "male" else "女",
                "year_ganzhi": f"{chart.year_gan}{chart.year_zhi}",
                "hour_zhi": chart.hour_zhi,
            },
            "ming_gong": {
                "name": GONG_NAMES[chart.ming_gong_index],
                "index": chart.ming_gong_index,
                "zhi": DI_ZHI[chart.ming_gong_index],
            },
            "shen_gong": {
                "name": GONG_NAMES[chart.shen_gong_index],
                "index": chart.shen_gong_index,
                "zhi": DI_ZHI[chart.shen_gong_index],
            },
            "wuxing_ju": f"{chart.wuxing_ju}{chart.wuxing_ju_num}局",
            "ming_zhu": chart.ming_zhu,
            "shen_zhu": chart.shen_zhu,
            "sihua": {
                "化禄": chart.hua_lu,
                "化权": chart.hua_quan,
                "化科": chart.hua_ke,
                "化忌": chart.hua_ji,
            },
            "gongs": [
                {
                    "name": g.name,
                    "en_name": g.en_name,
                    "ganzhi": f"{g.gan}{g.zhi}",
                    "main_stars": g.stars,
                    "aux_stars": g.aux_stars,
                    "sihua": g.sihua,
                }
                for g in chart.gongs
            ],
            "daxian": chart.daxian,
        }

    @classmethod
    def format_text(cls, chart: ZiweiChart) -> str:
        """生成文本格式的命盘"""
        d = cls.to_dict(chart)
        lines = []
        lines.append("╔══════════════════════════════════════╗")
        lines.append("║           紫微斗数命盘               ║")
        lines.append("╠══════════════════════════════════════╣")
        lines.append(f"║ 公历: {d['input']['solar']}")
        lines.append(f"║ 农历: {d['input']['lunar']}  {d['input']['year_ganzhi']}年")
        lines.append(f"║ 性别: {d['input']['gender']}  时支: {d['input']['hour_zhi']}")
        lines.append(f"║ 命宫: {d['ming_gong']['name']}({d['ming_gong']['zhi']})  身宫: {d['shen_gong']['name']}")
        lines.append(f"║ 五行局: {d['wuxing_ju']}")
        lines.append(f"║ 命主: {d['ming_zhu']}  身主: {d['shen_zhu']}")
        lines.append(f"║ 四化: 禄({d['sihua']['化禄']}) 权({d['sihua']['化权']}) 科({d['sihua']['化科']}) 忌({d['sihua']['化忌']})")
        lines.append("╠══════════════════════════════════════╣")
        
        for g in d["gongs"]:
            stars_str = ", ".join(g["main_stars"]) if g["main_stars"] else "—"
            aux_str = ", ".join(g["aux_stars"]) if g["aux_stars"] else ""
            sihua_str = f" [{g['sihua']}]" if g["sihua"] else ""
            lines.append(f"║ {g['name']:4s} {g['ganzhi']:4s} │ {stars_str}{sihua_str}")
            if aux_str:
                lines.append(f"║      │ 辅: {aux_str}")
        
        lines.append("╠══════════════════════════════════════╣")
        lines.append("║ 大限：")
        for dx in d["daxian"]:
            lines.append(f"║   {dx['gong_name']:4s} → {dx['age_range']}")
        lines.append("╚══════════════════════════════════════╝")
        return "\n".join(lines)


# ============================================================================
# 便捷函数
# ============================================================================

def calc_ziwei(year: int, month: int, day: int, hour: int = 0,
               minute: int = 0, gender: str = "male") -> ZiweiChart:
    """快速排紫微斗数命盘"""
    return ZiweiEngine.calc_chart(year, month, day, hour, minute, gender)


def ziwei_to_dict(chart: ZiweiChart) -> Dict[str, Any]:
    """命盘转字典"""
    return ZiweiEngine.to_dict(chart)


__all__ = [
    "ZiweiEngine", "ZiweiChart", "GongInfo",
    "calc_ziwei", "ziwei_to_dict",
    "GONG_NAMES", "GONG_EN", "STAR_PROPERTIES", "AUX_STAR_PROPERTIES",
]