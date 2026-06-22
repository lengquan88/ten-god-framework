#!/usr/bin/env python3
"""
geju_engine.py — 格局 + 喜用神 + 调候引擎 v1.0.0
= = = = = = = = = = = = = = = = = = = = = = = = = = =
提供三类核心算法：

1. 格局判断引擎 (GejuEngine)
   - 从旺格（曲直仁寿、炎上、从旺、从财、从杀等）
   - 普通格局（官杀格、财格、食伤格、印绶格、比劫格）
   - 化气格

2. 喜用神引擎 (YongshenEngine)
   - 综合五行旺衰 + 调候 + 病药

3. 调候用神引擎 (TiaohouEngine)
   - 冬木调候、夏金调候等
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

__all__ = [
    "GejuEngine",
    "YongshenEngine",
    "TiaohouEngine",
    "GejuResult",
    "YongshenResult",
    "TiaohouResult",
    "calc_geju",
    "calc_yongshen",
    "calc_tiaohou",
]
__version__ = "1.0.0"


# ============================================================================
# 常量定义
# ============================================================================
TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 天干地支阴阳
TG_YINYANG = {"甲": 0, "乙": 1, "丙": 0, "丁": 1, "戊": 0, "己": 1, "庚": 0, "辛": 1, "壬": 0, "癸": 1}
DZ_YINYANG = {"子": 0, "丑": 1, "寅": 0, "卯": 1, "辰": 0, "巳": 1, "午": 0, "未": 1, "申": 0, "酉": 1, "戌": 0, "亥": 1}

# 天干地支五行
TG_WUXING = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
DZ_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土",
    "巳": "火", "午": "火", "未": "土", "申": "金", "酉": "金",
    "戌": "土", "亥": "水",
}

# 地支本气藏干
ZHI_MAIN_GAN = {
    "子": "癸", "丑": "己", "寅": "甲", "卯": "乙",
    "辰": "戊", "巳": "丙", "午": "丁", "未": "己",
    "申": "庚", "酉": "辛", "戌": "戊", "亥": "壬",
}

# 月令（十二长生宫位对应地支）
# 以日干为基准，月支的地支索引
YUELING_INDEX = {"寅": 0, "卯": 1, "辰": 2, "巳": 3, "午": 4, "未": 5,
                 "申": 6, "酉": 7, "戌": 8, "亥": 9, "子": 10, "丑": 11}

# 月令旺相（当令者旺，我生者相，生我者休，克我者死，我克者囚）
# 以月令地支的五行当令
YUELING_WUXING = {
    "寅": "木", "卯": "木", "辰": "土",
    "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土",
    "亥": "水", "子": "水", "丑": "土",
}

# 调候用神表：月份+日干→调候用神
# 口诀：
# 春天木旺，用庚金/丙火（用水需甲，用火需庚）
# 夏天火旺，用壬水/癸水（用金需辛，用土需丙）
# 四季土旺，用丙火/甲木
# 秋天金旺，用丁火/丙火（用水需壬，用木需甲）
# 冬天水旺，用丙火/甲木（用火需丙，用金需庚）
TIAOHOU_TABLE = {
    # 寅月（木令，丙温庚克）
    ("寅", "甲"): ["庚", "丁", "癸"],
    ("寅", "乙"): ["庚", "丙", "癸"],
    ("寅", "丙"): ["壬", "庚", "己"],
    ("寅", "丁"): ["庚", "甲", "壬"],
    ("寅", "戊"): ["丙", "甲", "癸"],
    ("寅", "己"): ["庚", "丙", "癸"],
    ("寅", "庚"): ["丁", "甲", "癸"],
    ("寅", "辛"): ["壬", "庚", "己"],
    ("寅", "壬"): ["戊", "庚", "丙"],
    ("寅", "癸"): ["庚", "丙", "辛"],
    # 卯月（木令）
    ("卯", "甲"): ["庚", "丁", "癸"],
    ("卯", "乙"): ["庚", "丙", "癸"],
    ("卯", "丙"): ["壬", "庚", "己"],
    ("卯", "丁"): ["庚", "甲", "壬"],
    ("卯", "戊"): ["丙", "甲", "癸"],
    ("卯", "己"): ["庚", "丙", "癸"],
    ("卯", "庚"): ["丁", "甲", "癸"],
    ("卯", "辛"): ["壬", "庚", "己"],
    ("卯", "壬"): ["戊", "庚", "丙"],
    ("卯", "癸"): ["庚", "丙", "辛"],
    # 辰月（土令）
    ("辰", "甲"): ["庚", "壬", "癸"],
    ("辰", "乙"): ["庚", "丙", "癸"],
    ("辰", "丙"): ["壬", "庚", "己"],
    ("辰", "丁"): ["庚", "甲", "癸"],
    ("辰", "戊"): ["丙", "甲", "癸"],
    ("辰", "己"): ["庚", "丙", "癸"],
    ("辰", "庚"): ["丁", "甲", "癸"],
    ("辰", "辛"): ["壬", "庚", "己"],
    ("辰", "壬"): ["戊", "庚", "丙"],
    ("辰", "癸"): ["庚", "丙", "辛"],
    # 巳月（火令）
    ("巳", "甲"): ["癸", "辛", "庚"],
    ("巳", "乙"): ["癸", "庚", "丙"],
    ("巳", "丙"): ["壬", "庚", "己"],
    ("巳", "丁"): ["甲", "庚", "壬"],
    ("巳", "戊"): ["壬", "丙", "庚"],
    ("巳", "己"): ["癸", "丙", "辛"],
    ("巳", "庚"): ["壬", "癸", "丙"],
    ("巳", "辛"): ["壬", "庚", "癸"],
    ("巳", "壬"): ["戊", "丙", "庚"],
    ("巳", "癸"): ["庚", "辛", "壬"],
    # 午月（火令）
    ("午", "甲"): ["癸", "辛", "庚"],
    ("午", "乙"): ["癸", "庚", "丁"],
    ("午", "丙"): ["壬", "己", "庚"],
    ("午", "丁"): ["甲", "庚", "壬"],
    ("午", "戊"): ["壬", "丙", "庚"],
    ("午", "己"): ["癸", "丙", "辛"],
    ("午", "庚"): ["壬", "癸", "丙"],
    ("午", "辛"): ["壬", "庚", "癸"],
    ("午", "壬"): ["戊", "丙", "庚"],
    ("午", "癸"): ["庚", "辛", "壬"],
    # 未月（土令）
    ("未", "甲"): ["庚", "壬", "癸"],
    ("未", "乙"): ["庚", "丙", "癸"],
    ("未", "丙"): ["壬", "庚", "己"],
    ("未", "丁"): ["庚", "甲", "癸"],
    ("未", "戊"): ["丙", "甲", "癸"],
    ("未", "己"): ["庚", "丙", "癸"],
    ("未", "庚"): ["丁", "甲", "癸"],
    ("未", "辛"): ["壬", "庚", "己"],
    ("未", "壬"): ["戊", "庚", "丙"],
    ("未", "癸"): ["庚", "丙", "辛"],
    # 申月（金令）
    ("申", "甲"): ["庚", "丁", "壬"],
    ("申", "乙"): ["庚", "丁", "丙"],
    ("申", "丙"): ["壬", "庚", "戊"],
    ("申", "丁"): ["庚", "甲", "戊"],
    ("申", "戊"): ["壬", "丙", "庚"],
    ("申", "己"): ["庚", "癸", "丙"],
    ("申", "庚"): ["丁", "甲", "壬"],
    ("申", "辛"): ["壬", "庚", "丁"],
    ("申", "壬"): ["戊", "丙", "庚"],
    ("申", "癸"): ["庚", "辛", "壬"],
    # 酉月（金令）
    ("酉", "甲"): ["庚", "丁", "壬"],
    ("酉", "乙"): ["庚", "丁", "丙"],
    ("酉", "丙"): ["壬", "庚", "戊"],
    ("酉", "丁"): ["庚", "甲", "戊"],
    ("酉", "戊"): ["壬", "丙", "庚"],
    ("酉", "己"): ["庚", "癸", "丙"],
    ("酉", "庚"): ["丁", "甲", "壬"],
    ("酉", "辛"): ["壬", "庚", "丁"],
    ("酉", "壬"): ["戊", "丙", "庚"],
    ("酉", "癸"): ["庚", "辛", "壬"],
    # 戌月（土令）
    ("戌", "甲"): ["庚", "壬", "癸"],
    ("戌", "乙"): ["庚", "丙", "癸"],
    ("戌", "丙"): ["壬", "庚", "己"],
    ("戌", "丁"): ["庚", "甲", "癸"],
    ("戌", "戊"): ["丙", "甲", "癸"],
    ("戌", "己"): ["庚", "丙", "癸"],
    ("戌", "庚"): ["丁", "甲", "癸"],
    ("戌", "辛"): ["壬", "庚", "己"],
    ("戌", "壬"): ["戊", "庚", "丙"],
    ("戌", "癸"): ["庚", "丙", "辛"],
    # 亥月（水令）
    ("亥", "甲"): ["庚", "丙", "戊"],
    ("亥", "乙"): ["庚", "丙", "丁"],
    ("亥", "丙"): ["壬", "戊", "庚"],
    ("亥", "丁"): ["甲", "庚", "戊"],
    ("亥", "戊"): ["甲", "丙", "庚"],
    ("亥", "己"): ["庚", "丙", "甲"],
    ("亥", "庚"): ["丁", "甲", "戊"],
    ("亥", "辛"): ["壬", "庚", "甲"],
    ("亥", "壬"): ["戊", "丙", "庚"],
    ("亥", "癸"): ["庚", "辛", "壬"],
    # 子月（水令）
    ("子", "甲"): ["庚", "丁", "丙"],
    ("子", "乙"): ["庚", "丙", "丁"],
    ("子", "丙"): ["壬", "戊", "庚"],
    ("子", "丁"): ["甲", "庚", "戊"],
    ("子", "戊"): ["甲", "丙", "庚"],
    ("子", "己"): ["庚", "丙", "甲"],
    ("子", "庚"): ["丁", "甲", "戊"],
    ("子", "辛"): ["壬", "庚", "甲"],
    ("子", "壬"): ["戊", "丙", "庚"],
    ("子", "癸"): ["庚", "辛", "壬"],
    # 丑月（土令）
    ("丑", "甲"): ["庚", "辛", "丁"],
    ("丑", "乙"): ["庚", "丙", "丁"],
    ("丑", "丙"): ["壬", "庚", "己"],
    ("丑", "丁"): ["庚", "甲", "癸"],
    ("丑", "戊"): ["丙", "甲", "癸"],
    ("丑", "己"): ["庚", "丙", "癸"],
    ("丑", "庚"): ["丁", "甲", "癸"],
    ("丑", "辛"): ["壬", "庚", "己"],
    ("丑", "壬"): ["戊", "庚", "丙"],
    ("丑", "癸"): ["庚", "丙", "辛"],
}

# 十神五行映射
ZHISHEN_BY_DAY = {
    # 比肩, 劫财, 食神, 伤官, 正财, 偏财, 正官, 七杀, 正印, 偏印
    "甲": {"甲": "比肩", "乙": "劫财", "丙": "食神", "丁": "伤官",
            "戊": "偏财", "己": "正财", "庚": "七杀", "辛": "正官",
            "壬": "偏印", "癸": "正印"},
    "乙": {"甲": "劫财", "乙": "比肩", "丙": "伤官", "丁": "食神",
            "戊": "正财", "己": "偏财", "庚": "正官", "辛": "七杀",
            "壬": "正印", "癸": "偏印"},
    "丙": {"甲": "偏印", "乙": "正印", "丙": "比肩", "丁": "劫财",
            "戊": "食神", "己": "伤官", "庚": "偏财", "辛": "正财",
            "壬": "七杀", "癸": "正官"},
    "丁": {"甲": "正印", "乙": "偏印", "丙": "劫财", "丁": "比肩",
            "戊": "伤官", "己": "食神", "庚": "正财", "辛": "偏财",
            "壬": "正官", "癸": "七杀"},
    "戊": {"甲": "七杀", "乙": "正官", "丙": "偏印", "丁": "正印",
            "戊": "比肩", "己": "劫财", "庚": "食神", "辛": "伤官",
            "壬": "偏财", "癸": "正财"},
    "己": {"甲": "正官", "乙": "七杀", "丙": "正印", "丁": "偏印",
            "戊": "劫财", "己": "比肩", "庚": "伤官", "辛": "食神",
            "壬": "正财", "癸": "偏财"},
    "庚": {"甲": "偏财", "乙": "正财", "丙": "七杀", "丁": "正官",
            "戊": "偏印", "己": "正印", "庚": "比肩", "辛": "劫财",
            "壬": "食神", "癸": "伤官"},
    "辛": {"甲": "正财", "乙": "偏财", "丙": "正官", "丁": "七杀",
            "戊": "正印", "己": "偏印", "庚": "劫财", "辛": "比肩",
            "壬": "伤官", "癸": "食神"},
    "壬": {"甲": "食神", "乙": "伤官", "丙": "偏财", "丁": "正财",
            "戊": "七杀", "己": "正官", "庚": "偏印", "辛": "正印",
            "壬": "比肩", "癸": "劫财"},
    "癸": {"甲": "伤官", "乙": "食神", "丙": "正财", "丁": "偏财",
            "戊": "正官", "己": "七杀", "庚": "正印", "辛": "偏印",
            "壬": "劫财", "癸": "比肩"},
}


# ============================================================================
# 格局判断引擎
# ============================================================================

@dataclass
class GejuResult:
    """格局判断结果"""
    pillars: Dict[str, str]
    day_master: str
    month_zhi: str
    month_gan: str
    yueling: str              # 月令五行
    geju_type: str            # 格局类型
    geju_name: str            # 格局名称
    geju_desc: str            # 格局描述
    is_cong: bool             # 是否从格
    is_huaqi: bool            # 是否化气
    shiyongshen: List[str]    # 适用神（忌神列表的反面）
    jishen: List[str]         # 忌神
    fujia_shens: List[str]    # 扶抑类格局的用神
    score: float              # 格局纯度评分（0-100）
    detail: Dict[str, Any]    # 详细数据


def _count_wuxing(pillars: Dict[str, str]) -> Counter:
    """统计四柱中各五行数量（含地支本气）"""
    counts = Counter()
    # 天干
    for key in ["year", "month", "day", "hour"]:
        gan = pillars[key][0]
        counts[TG_WUXING[gan]] += 1
    # 地支本气
    for key in ["year", "month", "day", "hour"]:
        zhi = pillars[key][1]
        main_gan = ZHI_MAIN_GAN[zhi]
        counts[TG_WUXING[main_gan]] += 1
    return counts


def _is_cong_from(wuxing_counts: Counter, day_master: str) -> Optional[str]:
    """
    判断是否从格，返回从格名称或 None

    从旺格：日干极弱，四柱中某一行极强（>5个）
    从财格：日干极弱，八字中财星极旺
    从杀格：日干极弱，官杀极旺
    """
    day_gan_wx = TG_WUXING[day_master]
    total = sum(wuxing_counts.values())

    # 计算日主占比
    day_ratio = wuxing_counts.get(day_gan_wx, 0) / max(total, 1)

    # 如果日主占比 >= 40%，为身旺，不从
    if day_ratio >= 0.4:
        return None

    # 找最强的非日主五行
    max_wx = max((v, k) for k, v in wuxing_counts.items() if k != day_gan_wx)
    strongest = max_wx[1]
    strongest_ratio = max_wx[0] / max(total, 1)

    # 如果最强非日主五行占比 >= 50%，考虑从格
    if strongest_ratio >= 0.5:
        if strongest == "财":
            return "从财格"
        elif strongest == "官" or strongest == "杀":
            return "从杀格"
        else:
            # 特殊从旺格
            cong_names = {
                "木": "曲直仁寿格", "火": "炎上格",
                "土": "从旺格", "金": "从旺格", "水": "润下格",
            }
            if strongest in cong_names:
                return cong_names[strongest]
            return "从势格"

    return None


def _judge_normal_geju(
    pillars: Dict[str, str],
    day_master: str,
    month_gan: str,
    wuxing_counts: Counter,
) -> tuple[str, str, str, List[str], float]:
    """
    判断普通格局
    Returns: (geju_type, geju_name, geju_desc, jishen, score)
    """
    # 月干十神为主格神
    month_shishen = ZHISHEN_BY_DAY[day_master].get(month_gan, "未知")

    # 计算月令旺相
    yueling_wx = YUELING_WUXING[pillars["month"][1]]
    day_gan_wx = TG_WUXING[day_master]

    # 格局名称映射
    geju_map = {
        "正官": ("官杀格", "正官格，以官星为用，利于仕途、管理"),
        "七杀": ("官杀格", "七杀格，性刚果断，宜有印或食神制化"),
        "正财": ("财格", "正财格，勤俭务实，理财有方"),
        "偏财": ("财格", "偏财格，慷慨大方，善于交际"),
        "食神": ("食伤格", "食神格，温和宽厚，才华横溢"),
        "伤官": ("食伤格", "伤官格，聪明叛逆，宜有财印制化"),
        "正印": ("印绶格", "正印格，仁慈善良，学问渊博"),
        "偏印": ("印绶格", "偏印格，精明孤僻，宜有财印制化"),
        "比肩": ("比劫格", "比劫格，独立自我，竞争意识强"),
        "劫财": ("比劫格", "劫财格，冲动好强，善于社交"),
    }

    geju_type, geju_name = "普通格局", "普通格局"
    geju_desc = "普通格局，无特殊从化"
    jishen = []
    score = 70.0

    if month_shishen in geju_map:
        geju_type, geju_name = geju_map[month_shishen]
        geju_desc = geju_map[month_shishen][1]
        score = 80.0

    # 月令判断：如果月令地支五行与日主同，且日主旺
    if yueling_wx == day_gan_wx:
        score += 5
        geju_desc += "，月令当令，身旺无疑"

    # 忌神判定
    if month_shishen in ["正官", "七杀"]:
        jishen = ["伤官", "冲官之神"]
    elif month_shishen in ["正财", "偏财"]:
        jishen = ["劫财", "比肩"]
    elif month_shishen in ["食神", "伤官"]:
        jishen = ["印绶"]
    elif month_shishen in ["正印", "偏印"]:
        jishen = ["财星"]
    elif month_shishen in ["比肩", "劫财"]:
        jishen = ["财星", "官杀"]

    return geju_type, geju_name, geju_desc, jishen, min(score, 100)


def calc_geju(pillars: Dict[str, str]) -> GejuResult:
    """
    格局判断主函数

    判断逻辑：
    1. 统计五行分布
    2. 计算日主旺衰
    3. 判断从格（非日主五行占比>50%则从）
    4. 普通格局（月干十神）
    """
    day_master = pillars["day"][0]
    month_gan = pillars["month"][0]
    month_zhi = pillars["month"][1]
    day_gan_wx = TG_WUXING[day_master]

    wuxing_counts = _count_wuxing(pillars)
    yueling_wx = YUELING_WUXING[month_zhi]

    # 从格判断
    cong_result = _is_cong_from(wuxing_counts, day_master)

    if cong_result:
        is_cong = True
        is_huaqi = False
        geju_type = "从格"
        geju_name = cong_result
        score = 85.0
        if "从旺" in cong_result or cong_result in ["曲直仁寿格", "炎上格", "润下格"]:
            geju_desc = f"从旺格局，{day_gan_wx}气极旺，日主从之，格局纯正"
            jishen = [day_gan_wx]  # 忌日主本气被扶
            fujia = []
        elif cong_result == "从财格":
            geju_desc = "从财格，八字财星极旺，日主从之，一心求财"
            jishen = ["比肩", "劫财", day_gan_wx]
            fujia = ["财星"]
        elif cong_result == "从杀格":
            geju_desc = "从杀格，官杀极旺，日主从之，适合公职管理"
            jishen = ["食神", "伤官"]
            fujia = ["官杀"]
        else:
            geju_desc = f"从势格，日主极弱，依从最强五行"
            jishen = [day_gan_wx]
            fujia = []
    else:
        is_cong = False
        is_huaqi = False
        geju_type, geju_name, geju_desc, jishen, score = _judge_normal_geju(
            pillars, day_master, month_gan, wuxing_counts
        )
        fujia = []

    return GejuResult(
        pillars=pillars,
        day_master=day_master,
        month_zhi=month_zhi,
        month_gan=month_gan,
        yueling=yueling_wx,
        geju_type=geju_type,
        geju_name=geju_name,
        geju_desc=geju_desc,
        is_cong=is_cong,
        is_huaqi=is_huaqi,
        shiyongshen=[],  # 用神见喜用神引擎
        jishen=jishen,
        fujia_shens=fujia,
        score=score,
        detail={
            "wuxing_counts": dict(wuxing_counts),
            "yueling_wuxing": yueling_wx,
            "day_gan_wuxing": day_gan_wx,
            "month_shishen": ZHISHEN_BY_DAY[day_master].get(month_gan, "未知"),
        },
    )


class GejuEngine:
    """格局判断引擎（包装）"""

    @staticmethod
    def compute(pillars: Dict[str, str]) -> GejuResult:
        return calc_geju(pillars)

    @staticmethod
    def judge(pillars: Dict[str, str], detail: str = "basic") -> Dict[str, Any]:
        result = calc_geju(pillars)
        if detail == "basic":
            return {
                "geju_type": result.geju_type,
                "geju_name": result.geju_name,
                "geju_desc": result.geju_desc,
                "is_cong": result.is_cong,
                "is_huaqi": result.is_huaqi,
                "score": result.score,
                "jishen": result.jishen,
                "month_shishen": result.detail.get("month_shishen", ""),
            }
        return {
            "pillars": result.pillars,
            "day_master": result.day_master,
            **result.detail,
            "geju_type": result.geju_type,
            "geju_name": result.geju_name,
            "geju_desc": result.geju_desc,
            "is_cong": result.is_cong,
            "is_huaqi": result.is_huaqi,
            "score": result.score,
            "jishen": result.jishen,
            "fujia_shens": result.fujia_shens,
        }


# ============================================================================
# 调候用神引擎
# ============================================================================

@dataclass
class TiaohouResult:
    """调候用神结果"""
    month_zhi: str
    day_master: str
    yueling: str
    required_tiaohou: bool        # 是否需要调候
    season: str                     # 季节
    tiaohou_shens: List[str]       # 调候用神
    bingyao_shens: List[str]      # 病药用神（如有）
    desc: str
    detail: Dict[str, Any]


def _get_season(month_zhi: str) -> str:
    """根据月支判断季节"""
    if month_zhi in ["寅", "卯"]:
        return "春"
    elif month_zhi in ["巳", "午"]:
        return "夏"
    elif month_zhi in ["申", "酉"]:
        return "秋"
    elif month_zhi in ["亥", "子"]:
        return "冬"
    return "四季"


def calc_tiaohou(pillars: Dict[str, str]) -> TiaohouResult:
    """调候用神判断"""
    month_zhi = pillars["month"][1]
    day_master = pillars["day"][0]
    yueling = YUELING_WUXING[month_zhi]
    season = _get_season(month_zhi)

    # 查表获取调候用神
    tiaohou_shens = TIAOHOU_TABLE.get((month_zhi, day_master), [])

    # 判断是否需要调候
    # 夏冬必须调候，春秋一般不需要（特殊情况除外）
    required = season in ["夏", "冬"]

    # 特殊：初春（寅月）木嫩，也需调候
    if month_zhi == "寅" and day_master in ["甲", "乙"]:
        required = True

    # 病药：针对燥湿的调候
    bingyao = []
    if season == "夏":
        bingyao = ["水", "壬", "癸"]
    elif season == "冬":
        bingyao = ["火", "丙", "丁"]
    elif season == "春":
        bingyao = ["金", "庚", "辛"]
    elif season == "秋":
        bingyao = ["水", "壬", "癸"]

    desc = ""
    if required and tiaohou_shens:
        desc = f"命局偏寒/偏热，{tiaohou_shens[0]}为调候用神"
    elif not required:
        desc = f"{season}季命局中和，一般无需特殊调候"

    return TiaohouResult(
        month_zhi=month_zhi,
        day_master=day_master,
        yueling=yueling,
        required_tiaohou=required,
        season=season,
        tiaohou_shens=tiaohou_shens,
        bingyao_shens=bingyao,
        desc=desc,
        detail={"season": season},
    )


class TiaohouEngine:
    """调候用神引擎（包装）"""

    @staticmethod
    def compute(pillars: Dict[str, str]) -> TiaohouResult:
        return calc_tiaohou(pillars)


# ============================================================================
# 喜用神引擎
# ============================================================================

@dataclass
class YongshenResult:
    """喜用神判断结果"""
    pillars: Dict[str, str]
    day_master: str
    wang_shuai: str              # 旺衰：旺/衰/从
    wang_shuai_level: float      # 旺衰程度 0-100
    yong_shen: List[str]         # 喜用神（对日主有利的天干）
    ji_shen: List[str]           # 忌神
    tiaohou_needed: bool         # 是否需要调候
    tiaohou_shens: List[str]     # 调候用神
    bingyao_shens: List[str]      # 病药用神
    yongshen_desc: str           # 喜用神说明
    wuxing_balance: Dict[str, int]  # 五行平衡表
    score: float


def _judge_wangshuai(
    pillars: Dict[str, str],
    wuxing_counts: Counter,
    day_master: str,
) -> tuple[str, float]:
    """判断日主旺衰"""
    day_gan_wx = TG_WUXING[day_master]
    yueling_wx = YUELING_WUXING[pillars["month"][1]]
    total = sum(wuxing_counts.values()) or 1

    day_count = wuxing_counts.get(day_gan_wx, 0)
    day_ratio = day_count / total

    # 辅助判断：生我者（印星）
    yinzheng_count = 0
    for key in ["year", "month", "day", "hour"]:
        zhi = pillars[key][1]
        main_gan = ZHI_MAIN_GAN[zhi]
        if TG_WUXING[main_gan] in ["水"]:  # 印星生我
            yinzheng_count += 0.5

    # 月令权重
    yueling_bonus = 2.0 if yueling_wx == day_gan_wx else (-2.0 if yueling_wx in _ke_wuxing(day_gan_wx) else 0)

    # 综合评分
    score = day_ratio * 100 + yueling_bonus * 10 + yinzheng_count * 5

    if score >= 60:
        return "旺", min(score, 100)
    elif score >= 40:
        return "中和", score
    elif score >= 20:
        return "弱", max(score, 10)
    else:
        return "从", max(score, 5)


def _ke_wuxing(wx: str) -> List[str]:
    """某五行所克的五行"""
    m = {"木": ["土"], "火": ["金"], "土": ["水"], "金": ["木"], "水": ["火"]}
    return m.get(wx, [])


def _sheng_wuxing(wx: str) -> List[str]:
    """某五行所生的五行"""
    m = {"木": ["火"], "火": ["土"], "土": ["金"], "金": ["水"], "水": ["木"]}
    return m.get(wx, [])


def calc_yongshen(pillars: Dict[str, str]) -> YongshenResult:
    """
    喜用神判断主函数

    综合原则：
    1. 日主旺：取克泄为用（官杀、财星、食伤）
    2. 日主弱：取生扶为用（印星、比劫）
    3. 寒燥（冬生）：以火调候
    4. 炎热（夏生）：以水调候
    5. 结合格局（从格时反向取用）
    """
    day_master = pillars["day"][0]
    day_gan_wx = TG_WUXING[day_master]
    wuxing_counts = _count_wuxing(pillars)

    # 格局判断
    geju = calc_geju(pillars)

    # 调候判断
    tiaohou = calc_tiaohou(pillars)

    # 旺衰判断
    wangshuai, wangshuai_level = _judge_wangshuai(pillars, wuxing_counts, day_master)

    yong_shen: List[str] = []
    ji_shen: List[str] = []

    if geju.is_cong:
        # 从格：忌日主本气被扶，喜原局所从之五行
        yong_shen = [day_gan_wx, "印星"]  # 忌印扶
        ji_shen = ["比肩", "劫财"]
        yongshen_desc = f"从{day_gan_wx}格格局，喜原局所从五行，忌印比扶日主"
    elif wangshuai == "旺":
        # 身旺：克泄为用
        ke = _ke_wuxing(day_gan_wx)  # 所克 → 财星
        sheng = _sheng_wuxing(day_gan_wx)  # 所生 → 食伤
        yong_shen = ke + sheng + ["官杀"]
        ji_shen = ["印星", "比肩", "劫财"]
        yongshen_desc = f"日主{day_master}身旺，取财星、食伤、官杀为用，忌印比生扶"
    elif wangshuai in ("弱", "中和"):
        # 身弱：生扶为用
        yong_shen = ["印星", "比肩", "劫财"]
        ji_shen = ["财星", "官杀", "食伤"]
        yongshen_desc = f"日主{day_master}身{wangshuai}，取印星、比劫为用，忌财官食伤泄耗"
    else:
        yong_shen = ["扶日主"]
        ji_shen = ["克泄"]
        yongshen_desc = "日主极弱，特殊情况，需详细分析"

    # 调候优先
    if tiaohou.required_tiaohou and tiaohou.tiaohou_shens:
        # 调候用神优先加入喜用
        if tiaohou.tiaohou_shens[0] not in yong_shen:
            yong_shen = [tiaohou.tiaohou_shens[0]] + yong_shen
        yongshen_desc += f"；另需{tiaohou.tiaohou_shens[0]}调候"

    # 格局修正
    if geju.geju_name in ["官杀格", "七杀格"]:
        if "正印" not in yong_shen and "偏印" not in yong_shen:
            yong_shen = ["印星"] + yong_shen
        ji_shen = ["伤官"] + ji_shen

    # 五行平衡表
    balance = {wx: wuxing_counts.get(wx, 0) for wx in ["木", "火", "土", "金", "水"]}

    return YongshenResult(
        pillars=pillars,
        day_master=day_master,
        wang_shuai=wangshuai,
        wang_shuai_level=wangshuai_level,
        yong_shen=yong_shen[:5],
        ji_shen=ji_shen[:5],
        tiaohou_needed=tiaohou.required_tiaohou,
        tiaohou_shens=tiaohou.tiaohou_shens[:3],
        bingyao_shens=tiaohou.bingyao_shens[:3],
        yongshen_desc=yongshen_desc,
        wuxing_balance=balance,
        score=70.0,
    )


class YongshenEngine:
    """喜用神引擎（包装）"""

    @staticmethod
    def compute(pillars: Dict[str, str]) -> YongshenResult:
        return calc_yongshen(pillars)

    @staticmethod
    def analyze(pillars: Dict[str, str], detail: str = "basic") -> Dict[str, Any]:
        result = calc_yongshen(pillars)
        if detail == "basic":
            return {
                "day_master": result.day_master,
                "wang_shuai": result.wang_shuai,
                "wang_shuai_level": result.wang_shuai_level,
                "yong_shen": result.yong_shen,
                "ji_shen": result.ji_shen,
                "tiaohou_needed": result.tiaohou_needed,
                "tiaohou_shens": result.tiaohou_shens,
                "yongshen_desc": result.yongshen_desc,
            }
        return {
            "pillars": result.pillars,
            "day_master": result.day_master,
            "wang_shuai": result.wang_shuai,
            "wang_shuai_level": result.wang_shuai_level,
            "yong_shen": result.yong_shen,
            "ji_shen": result.ji_shen,
            "tiaohou_needed": result.tiaohou_needed,
            "tiaohou_shens": result.tiaohou_shens,
            "bingyao_shens": result.bingyao_shens,
            "yongshen_desc": result.yongshen_desc,
            "wuxing_balance": result.wuxing_balance,
            "score": result.score,
        }


# ============================================================================
# 综合分析（格局 + 喜用神 + 调候 一体化）
# ============================================================================

@dataclass
class ComprehensiveResult:
    """八字综合分析结果"""
    pillars: Dict[str, str]
    day_master: str
    geju: GejuResult
    yongshen: YongshenResult
    tiaohou: TiaohouResult


def analyze_bazi_comprehensive(pillars: Dict[str, str]) -> ComprehensiveResult:
    """八字综合分析（格局 + 喜用神 + 调候）"""
    geju = calc_geju(pillars)
    yongshen = calc_yongshen(pillars)
    tiaohou = calc_tiaohou(pillars)
    return ComprehensiveResult(
        pillars=pillars,
        day_master=pillars["day"][0],
        geju=geju,
        yongshen=yongshen,
        tiaohou=tiaohou,
    )


def text_report_comprehensive(pillars: Dict[str, str]) -> str:
    """综合文本报告"""
    r = analyze_bazi_comprehensive(pillars)
    lines = ["=" * 60, "八字格局与喜用神综合分析报告", "=" * 60]
    lines.append(f"\n四柱: {r.pillars['year']} {r.pillars['month']} "
                 f"{r.pillars['day']} {r.pillars['hour']}")
    lines.append(f"日主: {r.day_master}（{r.geju.detail.get('day_gan_wuxing','')}）")
    lines.append(f"月令: {r.geju.yueling}（{r.geju.month_zhi}月）")

    lines.append(f"\n【格局判断】")
    lines.append(f"  类型: {r.geju.geju_type}")
    lines.append(f"  名称: {r.geju.geju_name}")
    lines.append(f"  说明: {r.geju.geju_desc}")
    lines.append(f"  纯度: {r.geju.score:.0f}分")
    lines.append(f"  忌神: {', '.join(r.geju.jishen) or '无'}")
    if r.geju.is_cong:
        lines.append(f"  ⚠️ 从格：日主过弱，依从全局")

    lines.append(f"\n【旺衰判断】")
    lines.append(f"  旺衰: {r.yongshen.wang_shuai} ({r.yongshen.wang_shuai_level:.0f}分)")

    lines.append(f"\n【喜用神】")
    lines.append(f"  喜神: {', '.join(r.yongshen.yong_shen)}")
    lines.append(f"  忌神: {', '.join(r.yongshen.ji_shen)}")
    lines.append(f"  说明: {r.yongshen.yongshen_desc}")

    lines.append(f"\n【调候】")
    lines.append(f"  季节: {r.tiaohou.season}季")
    lines.append(f"  需要调候: {'是' if r.tiaohou.required_tiaohou else '否'}")
    if r.tiaohou.required_tiaohou:
        lines.append(f"  调候用神: {', '.join(r.tiaohou.tiaohou_shens)}")

    lines.append(f"\n【五行平衡】")
    for wx, cnt in r.yongshen.wuxing_balance.items():
        bar = "█" * cnt + "░" * (6 - cnt)
        lines.append(f"  {wx}: {bar} {cnt}个")

    lines.append("=" * 60)
    return "\n".join(lines)


# ============================================================================
# CLI 测试
# ============================================================================

if __name__ == "__main__":
    import json

    # 测试：1990-06-15 → 庚午壬午辛亥癸巳
    test_pillars = {
        "year": "庚午", "month": "壬午",
        "day": "辛亥", "hour": "癸巳",
    }
    print(f"测试四柱: {test_pillars}")
    print()

    # 格局测试
    print("【格局判断】")
    geju = calc_geju(test_pillars)
    print(f"  格局: {geju.geju_name} ({geju.geju_type})")
    print(f"  说明: {geju.geju_desc}")
    print(f"  忌神: {geju.jishen}")
    print(f"  纯度: {geju.score:.0f}分")
    print()

    # 喜用神测试
    print("【喜用神】")
    yongshen = calc_yongshen(test_pillars)
    print(f"  旺衰: {yongshen.wang_shuai} ({yongshen.wang_shuai_level:.0f}分)")
    print(f"  喜神: {yongshen.yong_shen}")
    print(f"  忌神: {yongshen.ji_shen}")
    print(f"  说明: {yongshen.yongshen_desc}")
    print()

    # 调候测试
    print("【调候】")
    tiaohou = calc_tiaohou(test_pillars)
    print(f"  季节: {tiaohou.season}季")
    print(f"  需要调候: {'是' if tiaohou.required_tiaohou else '否'}")
    print(f"  调候用神: {tiaohou.tiaohou_shens}")
    print()

    # 综合报告
    print(text_report_comprehensive(test_pillars))

    # 更多测试
    print("\n" + "=" * 60)
    print("更多测试用例:")
    test_cases = [
        {"year": "甲辰", "month": "丁卯", "day": "庚子", "hour": "丙子"},
        {"year": "乙酉", "month": "辛酉", "day": "戊午", "hour": "壬子"},
        {"year": "丙寅", "month": "壬辰", "day": "癸亥", "hour": "己丑"},
        {"year": "庚申", "month": "甲申", "day": "丙寅", "hour": "戊子"},
    ]
    for tc in test_cases:
        g = calc_geju(tc)
        y = calc_yongshen(tc)
        print(f"  {tc['year']} {tc['month']} {tc['day']} {tc['hour']} → "
              f"格局:{g.geju_name} | "
              f"旺衰:{y.wang_shuai} | "
              f"喜:{y.yong_shen[:2]}")
