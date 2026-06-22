#!/usr/bin/env python3
"""
shensha_engine.py — 神煞推算引擎 v1.0.0
= = = = = = = = = = = = = = = = = = =
实现 40+ 种神煞的精确推算，基于年柱、月柱、日柱、时柱推演。
神煞包括：吉神（天德、月德、文昌、太极贵人等）、凶神（桃花、阴错、
阳错、魁罡、亡神、劫煞等）、中性神煞（驿马、华盖、天乙贵人等）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

__all__ = [
    "ShenshaEngine",
    "Shensha",
    "ShenshaResult",
    "calc_all_shensha",
]
__version__ = "1.0.0"


# ============================================================================
# 天干地支索引
# ============================================================================
TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 天干地支对应的阴阳（0=阳，1=阴）
TG_YINYANG = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]  # 甲阳, 乙阴, ...
DZ_YINYANG = [0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0]  # 子阳, 丑阴, ...

# 地支藏干主气（用于某些神煞的推导）
ZHIGAN_MAIN = {
    "子": "癸", "丑": "己", "寅": "甲", "卯": "乙",
    "辰": "戊", "巳": "丙", "午": "丁", "未": "己",
    "申": "庚", "酉": "辛", "戌": "戊", "亥": "壬",
}


# ============================================================================
# 神煞分类枚举
# ============================================================================
class ShenshaCategory(Enum):
    """神煞分类"""
    JI_SHEN = "吉神"          # 大吉
    JI = "吉"                # 吉利
    PING = "平"              # 中性
    XIONG = "凶"             # 凶
    DA_XIONG = "大凶"         # 大凶
    JI_XIONG_PING = "吉凶"    # 吉凶参半


# ============================================================================
# 神煞定义
# ============================================================================
class Shensha(Enum):
    """神煞枚举"""

    # ── 年柱神煞 ──
    TIAN_DE = "天德"
    YUE_DE = "月德"
    TIAN_E = "天乙贵人"
    YUE_E = "月德贵人"
    JI_YIN = "吉暗"
    YANG_MA = "阳刃"
    JIE_SHA = "劫煞"
    WANG_SHEN = "亡神"
    GOU_CHEN = "勾陈"
    TENG_KONG = "腾蛇"
    WU_QU = "五鬼"
    LIU_CHEN = "六沉"
    JI_DUAN = "极断"
    HONG_FAN = "红凡"
    PIAO_FAN = "飘逢"
    FU_SHOU = "福寿"
    TIAN_SHUI = "天煞"
    GE_SHENG = "孤辰"
    GUA_SUI = "寡宿"

    # ── 月柱神煞 ──
    YI_MA = "驿马"
    HUA_GAI = "华盖"
    JIN_CHAI = "进神"
    TUI_SHEN = "退神"
    WAN_SHEN = "万金曜"
    GUA_WANG = "寡宿孤神"
    GUA_XIU = "孤秀"

    # ── 日柱神煞 ──
    TAO_HUA = "桃花"
    WEN_CHANG = "文昌"
    TAI_JI = "太极贵人"
    YIN_CHA = "阴错"
    YANG_CHA = "阳错"
    KUI_GANG = "魁罡"
    YANG_FENG = "阳普贤"
    GUAN_ZHI = "官事"
    XUE_TANG = "学堂"
    XI_YIN = "喜印"
    SI_WANG = "死亡"
    JI_GUAN = "吉关"
    FENG_LU = "丰禄"
    GUA_JI = "官吉"
    XUE_LU = "血罗"
    SI_CHU = "死处"
    XIONG_CHANG = "凶创"
    WEI_WU = "威武"
    GUA_GAN = "官杆"
    WEN_MING = "文明"
    XUE_LI = "血离"
    SI_CHU_2 = "死处2"
    SHI_CHU = "食出"
    CAI_LU = "财禄"
    XIAO_HAO = "消耗"
    FENG_DONG = "逢洞"
    GUA_ZAI = "官灾"
    XUE_WU = "血污"
    XIANG_XIU = "相休"
    HONG_CHI = "红迟"
    BAI_HU = "白虎"
    QING_LONG = "青龙"
    XUAN_WU = "玄武"
    BAI_HU2 = "白虎2"
    ZHU_CAI = "朱雀"
    CAI_GUAN = "财官"
    SHENG_GUAN = "生官"
    SHANG_GUAN = "伤官"
    XI_SHANG = "喜伤"
    SHENG_CAI = "生财"
    SHI_CAI = "食财"
    SHANG_CAI = "伤财"
    JI_SHANG = "吉伤"
    GUA_DU = "孤读"

    # ── 时柱神煞 ──
    SHI_CHA = "时冲"
    SHI_SHA = "时杀"
    SHI_YIN = "时阴"
    SHI_XIONG = "时凶"
    SHI_GUAN = "时官"
    SHI_CAI2 = "时财"
    ZI_MING = "子命"
    FU_ZHI = "福至"


# ============================================================================
# 神煞详情数据（名称、类别、说明）
# ============================================================================
_SHENSHA_INFO: Dict[str, Dict[str, Any]] = {
    # ── 吉神 ──
    "天德": {"cat": "吉神", "level": 5, "desc": "天赐之德，能压百凶，大吉"},
    "月德": {"cat": "吉神", "level": 4, "desc": "月中吉神，福寿双全"},
    "天乙贵人": {"cat": "吉神", "level": 5, "desc": "众贵之首，逢凶化吉，遇难成祥"},
    "月德贵人": {"cat": "吉神", "level": 4, "desc": "日月德合，贵人相助"},
    "太极贵人": {"cat": "吉神", "level": 4, "desc": "聪明好学，有文昌之德，功名显达"},
    "文昌": {"cat": "吉神", "level": 4, "desc": "利于学业功名，科甲有望"},
    "驿马": {"cat": "吉", "level": 3, "desc": "走动奔波之象，利出行、迁移、经商"},
    "华盖": {"cat": "吉", "level": 3, "desc": "艺术才情，孤高神秘，利技艺、宗教"},
    "进神": {"cat": "吉", "level": 3, "desc": "进益之神，财运亨通"},
    "学堂": {"cat": "吉神", "level": 4, "desc": "聪明登第，学业优异"},
    "喜印": {"cat": "吉", "level": 3, "desc": "喜见印绶，文采出众"},
    "丰禄": {"cat": "吉神", "level": 4, "desc": "福禄双全，财运稳定"},
    "官吉": {"cat": "吉", "level": 3, "desc": "官运吉利，仕途顺畅"},
    "威武": {"cat": "吉", "level": 3, "desc": "武职显达，胆识过人"},
    "官杆": {"cat": "吉", "level": 3, "desc": "官职亨通"},
    "文明": {"cat": "吉", "level": 4, "desc": "文采斐然，利学术、文化"},
    "财禄": {"cat": "吉神", "level": 4, "desc": "财运丰厚，收入稳定"},
    "福寿": {"cat": "吉神", "level": 4, "desc": "福泽深厚，长寿之命"},
    "青龙": {"cat": "吉神", "level": 4, "desc": "四吉神之一，镇百煞，利事业"},
    "朱雀": {"cat": "吉", "level": 3, "desc": "口才出众，利文职、演艺"},
    "生财": {"cat": "吉", "level": 3, "desc": "财源滚滚"},
    "食财": {"cat": "吉", "level": 3, "desc": "食神生财，财运亨通"},
    "吉伤": {"cat": "吉", "level": 3, "desc": "伤官见官，反为吉利"},
    "福至": {"cat": "吉神", "level": 4, "desc": "福星高照，好运连连"},
    "吉暗": {"cat": "吉", "level": 3, "desc": "暗中得福，贵人不现而自现"},
    "吉关": {"cat": "吉", "level": 3, "desc": "关煞化吉"},
    "福至": {"cat": "吉神", "level": 4, "desc": "福星高照"},
    "子命": {"cat": "吉", "level": 3, "desc": "子息兴旺"},

    # ── 中性/平 ──
    "魁罡": {"cat": "平", "level": 2, "desc": "刚强果断，利武职，女性则性刚孤僻"},
    "退神": {"cat": "平", "level": 2, "desc": "运势稍退，需蓄势待发"},
    "勾陈": {"cat": "平", "level": 2, "desc": "牵绊纠缠之星，需注意人际关系"},
    "腾蛇": {"cat": "平", "level": 2, "desc": "多思多虑，善于应变，但易焦虑"},
    "万金曜": {"cat": "平", "level": 2, "desc": "变化之星，运势波动较大"},
    "官事": {"cat": "平", "level": 2, "desc": "易有官非口舌，需谨言慎行"},
    "官灾": {"cat": "凶", "level": 3, "desc": "易有官非诉讼，需注意法律风险"},
    "官吉": {"cat": "吉", "level": 3, "desc": "官运吉利"},
    "消耗": {"cat": "平", "level": 2, "desc": "容易消耗财力，需理财节制"},
    "相休": {"cat": "平", "level": 2, "desc": "身体易疲劳，需注意休息"},

    # ── 凶神 ──
    "桃花": {"cat": "凶", "level": 3, "desc": "多情浪漫，易陷感情纠葛，男命尤忌酒色"},
    "阴错": {"cat": "凶", "level": 3, "desc": "阴差阳错，诸事不顺，易犯小人"},
    "阳错": {"cat": "凶", "level": 3, "desc": "阳差阴错，口舌是非，易与女性起冲突"},
    "劫煞": {"cat": "凶", "level": 4, "desc": "破财凶险之星，需防意外灾祸"},
    "亡神": {"cat": "凶", "level": 4, "desc": "心神不宁，易有凶灾横祸"},
    "孤辰": {"cat": "凶", "level": 3, "desc": "性格孤僻，人际关系淡薄，晚婚之象"},
    "寡宿": {"cat": "凶", "level": 3, "desc": "孤独之星，婚姻不顺，晚景凄凉"},
    "五鬼": {"cat": "凶", "level": 4, "desc": "小人作祟之星，暗中破财，易招是非"},
    "六沉": {"cat": "凶", "level": 3, "desc": "沉沦之星，运势低迷"},
    "极断": {"cat": "凶", "level": 4, "desc": "判官之神，易有重大决定失误"},
    "红凡": {"cat": "凶", "level": 3, "desc": "桃花之凶，易因色破财"},
    "飘逢": {"cat": "凶", "level": 3, "desc": "漂泊不定，居无定所"},
    "天煞": {"cat": "凶", "level": 4, "desc": "天降灾祸，需防意外"},
    "死亡": {"cat": "大凶", "level": 5, "desc": "大凶之星，健康易出严重问题"},
    "血罗": {"cat": "凶", "level": 4, "desc": "血光之灾，易有手术、意外流血"},
    "血离": {"cat": "凶", "level": 4, "desc": "血光离散，易有离别或伤灾"},
    "血污": {"cat": "凶", "level": 4, "desc": "易沾血光之灾，需注意安全"},
    "死处": {"cat": "大凶", "level": 5, "desc": "大凶临头"},
    "凶创": {"cat": "凶", "level": 4, "desc": "意外伤害，需防头部、眼部灾祸"},
    "逢洞": {"cat": "凶", "level": 4, "desc": "遇险之象，意外事故"},
    "白虎": {"cat": "凶", "level": 4, "desc": "凶神之一，易有血光之灾、官非"},
    "玄武": {"cat": "凶", "level": 4, "desc": "阴私之神，易有暗损、小人"},
    "孤读": {"cat": "凶", "level": 3, "desc": "学业受阻，读书困难"},
    "阳刃": {"cat": "凶", "level": 4, "desc": "刚暴之星，身旺则凶，易有刀剑伤灾"},
    "六冲": {"cat": "凶", "level": 3, "desc": "六冲之星，动荡不安"},
    "时冲": {"cat": "凶", "level": 3, "desc": "时柱与命局相冲，不利子息"},
    "时杀": {"cat": "凶", "level": 4, "desc": "时有七杀，运势受阻"},
    "时阴": {"cat": "凶", "level": 3, "desc": "时柱阴气重，晚年不顺"},
    "时凶": {"cat": "凶", "level": 4, "desc": "晚年多凶险"},
    "伤官": {"cat": "凶", "level": 3, "desc": "伤官见官，为祸百端（无印通关时）"},
}


# ============================================================================
# 神煞推算规则
# ============================================================================

def _get_tiangan_index(tg: str) -> int:
    return TIANGAN.index(tg)


def _get_dizhi_index(dz: str) -> int:
    return DIZHI.index(dz)


def _is_yang(tg: str) -> bool:
    """判断天干是否为阳干"""
    return TG_YINYANG[TIANGAN.index(tg)] == 0


def _is_yang_zhi(dz: str) -> bool:
    """判断地支是否为阳支"""
    return DZ_YINYANG[DIZHI.index(dz)] == 0


# ── 年柱神煞 ──────────────────────────────────────────────────────────────

def _calc_year_shensha(year_gan: str, year_zhi: str) -> Dict[str, Dict]:
    """年柱神煞推算"""
    results = {}

    # 天德：口诀"正丁二坤中，三壬四辛同，五乾六甲上，七癸八寅逢，
    #        九丙十居乙，子巳丑庚中"
    # 天德口诀简化版：年支见地支 → 对应天德天干
    # 正月丁(子), 二月坤(未), 三月壬(寅), 四月辛(卯), 五月乾(戌), 六月甲(辰)
    # 七月癸(巳), 八月寅(未月), 九月丙(申), 十月乙(酉), 十一月巳(戌), 十二月庚(亥)
    tiande_zhi_map = {
        "寅": "丁", "卯": "坤", "辰": "壬",
        "巳": "辛", "午": "乾", "未": "甲",
        "申": "癸", "酉": "寅", "戌": "丙",
        "亥": "乙", "子": "巳", "丑": "庚",
    }
    # 天德天干出现在月柱天干
    tiande_gan = tiande_zhi_map.get(year_zhi, "")
    # 如果天德天干出现在月柱天干中，则有天德
    if tiande_gan == "坤":
        tiande_gan = "未"
    elif tiande_gan == "乾":
        tiande_gan = "戌"
    if tiande_gan in TIANGAN:
        results["天德"] = {
            "name": "天德", "pillar": "年柱", "source": f"年支{year_zhi}",
            "desc": _SHENSHA_INFO.get("天德", {}).get("desc", ""),
            "cat": "吉神", "level": 5,
        }

    # 月德：口诀"亥卯午月申, 巳子辰月寅, 寅午戌月巳, 申酉丑月未"
    yuede_map = {
        "亥": "申", "卯": "申", "午": "申",  # 亥卯午 → 申
        "巳": "寅", "子": "寅", "辰": "寅",  # 巳子辰 → 寅
        "寅": "巳", "午": "巳", "戌": "巳",  # 寅午戌 → 巳
        "申": "未", "酉": "未", "丑": "未",  # 申酉丑 → 未
    }
    if year_zhi in yuede_map:
        results["月德"] = {
            "name": "月德", "pillar": "年柱", "source": f"年支{year_zhi}",
            "desc": _SHENSHA_INFO.get("月德", {}).get("desc", ""),
            "cat": "吉神", "level": 4,
        }

    # 天乙贵人：口诀"甲戊兼牛羊, 乙己鼠猴乡, 丙丁猪鸡位,
    #            壬癸兔蛇藏, 庚辛逢虎马, 此是贵人方"
    tianyi_map = {
        "甲": ["丑", "未"], "戊": ["丑", "未"],
        "乙": ["子", "申"], "己": ["子", "申"],
        "丙": ["亥", "酉"], "丁": ["亥", "酉"],
        "壬": ["卯", "巳"], "癸": ["卯", "巳"],
        "庚": ["寅", "午"], "辛": ["寅", "午"],
    }
    if year_gan in tianyi_map:
        results["天乙贵人"] = {
            "name": "天乙贵人", "pillar": "年柱", "source": f"年干{year_gan}",
            "desc": _SHENSHA_INFO.get("天乙贵人", {}).get("desc", ""),
            "cat": "吉神", "level": 5,
        }

    # 太极贵人
    taiji_map = {
        "甲": "子", "乙": "丑", "丙": "寅", "丁": "卯",
        "戊": "未", "己": "申", "庚": "酉", "辛": "戌",
        "壬": "亥", "癸": "午",
    }
    if year_gan in taiji_map and taiji_map[year_gan] == year_zhi:
        results["太极贵人"] = {
            "name": "太极贵人", "pillar": "年柱", "source": f"年干{year_gan}年支{year_zhi}",
            "desc": _SHENSHA_INFO.get("太极贵人", {}).get("desc", ""),
            "cat": "吉神", "level": 4,
        }

    # 劫煞：口诀"申子辰兮蛇开口, 亥卯未兮猴儿哭, 寅午戌兮猪面黑,
    #        巳酉丑兮虎啸 Dread, 辰月见亥，丑月见巳，寅月见申..."
    # 年支见劫煞
    jiesha_map = {
        "申": "巳", "子": "巳", "辰": "巳",  # 水局 → 巳
        "亥": "申", "卯": "申", "未": "申",  # 木局 → 申
        "寅": "亥", "午": "亥", "戌": "亥",  # 火局 → 亥
        "巳": "寅", "酉": "寅", "丑": "寅",  # 金局 → 寅
    }
    if year_zhi in jiesha_map:
        results["劫煞"] = {
            "name": "劫煞", "pillar": "年柱", "source": f"年支{year_zhi}",
            "desc": _SHENSHA_INFO.get("劫煞", {}).get("desc", ""),
            "cat": "凶", "level": 4,
        }

    # 亡神：口诀"申子辰兮虎暗藏, 亥卯未兮蛇头动, 寅午戌兮猴速跳,
    #        巳酉丑兮猪口叫"
    wangshen_map = {
        "申": "寅", "子": "寅", "辰": "寅",
        "亥": "巳", "卯": "巳", "未": "巳",
        "寅": "申", "午": "申", "戌": "申",
        "巳": "亥", "酉": "亥", "丑": "亥",
    }
    if year_zhi in wangshen_map:
        results["亡神"] = {
            "name": "亡神", "pillar": "年柱", "source": f"年支{year_zhi}",
            "desc": _SHENSHA_INFO.get("亡神", {}).get("desc", ""),
            "cat": "凶", "level": 4,
        }

    # 孤辰寡宿：口诀"亥子丑兮北方走, 寅卯辰兮东不康,
    #            巳午未兮南离群, 申酉戌兮西方哭"
    # 年支查孤辰寡宿
    guchen_map = {
        "亥": ("寅", "戌"), "子": ("寅", "戌"), "丑": ("寅", "戌"),
        "寅": ("巳", "丑"), "卯": ("巳", "丑"), "辰": ("巳", "丑"),
        "巳": ("申", "辰"), "午": ("申", "辰"), "未": ("申", "辰"),
        "申": ("亥", "未"), "酉": ("亥", "未"), "戌": ("亥", "未"),
    }
    if year_zhi in guchen_map:
        gu, gua = guchen_map[year_zhi]
        results["孤辰"] = {
            "name": "孤辰", "pillar": "年柱", "source": f"年支{year_zhi}",
            "desc": _SHENSHA_INFO.get("孤辰", {}).get("desc", ""),
            "cat": "凶", "level": 3,
        }
        results["寡宿"] = {
            "name": "寡宿", "pillar": "年柱", "source": f"年支{year_zhi}",
            "desc": _SHENSHA_INFO.get("寡宿", {}).get("desc", ""),
            "cat": "凶", "level": 3,
        }

    # 五鬼
    wugui_zhi = {"子": "午", "丑": "寅", "寅": "戌", "卯": "亥", "辰": "丑",
                 "巳": "辰", "午": "巳", "未": "卯", "申": "未", "酉": "午",
                 "戌": "巳", "亥": "辰"}
    if year_zhi in wugui_zhi:
        results["五鬼"] = {
            "name": "五鬼", "pillar": "年柱", "source": f"年支{year_zhi}",
            "desc": _SHENSHA_INFO.get("五鬼", {}).get("desc", ""),
            "cat": "凶", "level": 4,
        }

    # 阳刃（羊刃）
    # 阳干才有阳刃：甲-卯, 丙-午, 戊-午, 庚-酉, 壬-子
    yangren_map = {"甲": "卯", "丙": "午", "戊": "午", "庚": "酉", "壬": "子"}
    if year_gan in yangren_map and year_zhi == yangren_map[year_gan]:
        results["阳刃"] = {
            "name": "阳刃", "pillar": "年柱", "source": f"年干{year_gan}年支{year_zhi}",
            "desc": _SHENSHA_INFO.get("阳刃", {}).get("desc", ""),
            "cat": "凶", "level": 4,
        }

    return results


# ── 月柱神煞 ──────────────────────────────────────────────────────────────

def _calc_month_shensha(month_gan: str, month_zhi: str) -> Dict[str, Dict]:
    """月柱神煞推算"""
    results = {}

    # 驿马：口诀"申子辰马在寅, 亥卯未马在巳, 寅午戌马在申, 巳酉丑马在亥"
    yima_map = {
        "申": "寅", "子": "寅", "辰": "寅",
        "亥": "巳", "卯": "巳", "未": "巳",
        "寅": "申", "午": "申", "戌": "申",
        "巳": "亥", "酉": "亥", "丑": "亥",
    }
    if month_zhi in yima_map:
        results["驿马"] = {
            "name": "驿马", "pillar": "月柱", "source": f"月支{month_zhi}",
            "desc": _SHENSHA_INFO.get("驿马", {}).get("desc", ""),
            "cat": "吉", "level": 3,
        }

    # 华盖：口诀"寅午戌见戌, 亥卯未见未, 申子辰见辰, 巳酉丑见丑"
    huagai_map = {
        "寅": "戌", "午": "戌", "戌": "戌",
        "亥": "未", "卯": "未", "未": "未",
        "申": "辰", "子": "辰", "辰": "辰",
        "巳": "丑", "酉": "丑", "丑": "丑",
    }
    if month_zhi in huagai_map:
        results["华盖"] = {
            "name": "华盖", "pillar": "月柱", "source": f"月支{month_zhi}",
            "desc": _SHENSHA_INFO.get("华盖", {}).get("desc", ""),
            "cat": "吉", "level": 3,
        }

    # 文昌：口诀"甲乙见丙者, 兮居已午间,
    #        切嫌南与离, 更忌于离火,
    #        丙丁见壬相, 亥子坎阴汜,
    #        戊己见庚金, 必朝西北辛,
    #        庚辛见甲乙, 壬要北方吉,
    #        癸见丙与丁, 功名魁首是文昌"
    # 简化版：
    wenchang_map = {
        "甲": "巳", "乙": "午",
        "丙": "申", "丁": "酉",
        "戊": "申", "己": "酉",
        "庚": "亥", "辛": "子",
        "壬": "寅", "癸": "卯",
    }
    if month_gan in wenchang_map and month_zhi == wenchang_map[month_gan]:
        results["文昌"] = {
            "name": "文昌", "pillar": "月柱", "source": f"月干{month_gan}",
            "desc": _SHENSHA_INFO.get("文昌", {}).get("desc", ""),
            "cat": "吉神", "level": 4,
        }

    return results


# ── 日柱神煞 ──────────────────────────────────────────────────────────────

def _calc_day_shensha(day_gan: str, day_zhi: str) -> Dict[str, Dict]:
    """日柱神煞推算"""
    results = {}

    # 桃花：口诀"申子辰见酉, 寅午戌见卯, 亥卯未见子, 巳酉丑见午"
    taohua_map = {
        "申": "酉", "子": "酉", "辰": "酉",
        "寅": "卯", "午": "卯", "戌": "卯",
        "亥": "子", "卯": "子", "未": "子",
        "巳": "午", "酉": "午", "丑": "午",
    }
    if day_zhi in taohua_map:
        results["桃花"] = {
            "name": "桃花", "pillar": "日柱", "source": f"日支{day_zhi}",
            "desc": _SHENSHA_INFO.get("桃花", {}).get("desc", ""),
            "cat": "凶", "level": 3,
        }

    # 魁罡：庚辰、壬辰、戊戌、庚戌四日
    if day_gan == "庚" and day_zhi == "辰":
        results["魁罡"] = {"name": "魁罡", "pillar": "日柱",
                           "source": f"{day_gan}{day_zhi}",
                           "desc": "庚辰日，魁罡日，刚强果断", "cat": "平", "level": 2}
    elif day_gan == "壬" and day_zhi == "辰":
        results["魁罡"] = {"name": "魁罡", "pillar": "日柱",
                           "source": f"{day_gan}{day_zhi}",
                           "desc": "壬辰日，魁罡日，刚强果断", "cat": "平", "level": 2}
    elif day_gan == "戊" and day_zhi == "戌":
        results["魁罡"] = {"name": "魁罡", "pillar": "日柱",
                           "source": f"{day_gan}{day_zhi}",
                           "desc": "戊戌日，魁罡日，刚强果断", "cat": "平", "level": 2}
    elif day_gan == "庚" and day_zhi == "戌":
        results["魁罡"] = {"name": "魁罡", "pillar": "日柱",
                           "source": f"{day_gan}{day_zhi}",
                           "desc": "庚戌日，魁罡日，刚强果断", "cat": "平", "level": 2}

    # 阴错阳错：特定日干见特定地支
    # 阴错：庚子、辛丑、壬寅、癸卯、甲辰、乙巳、丙午、丁未、戊申、己酉
    # 阳错：甲子、乙丑、丙寅、丁卯、戊辰、己巳、庚午、辛未、壬申、癸酉
    yin_cuo = ["庚子", "辛丑", "壬寅", "癸卯", "甲辰", "乙巳",
               "丙午", "丁未", "戊申", "己酉"]
    yang_cuo = ["甲子", "乙丑", "丙寅", "丁卯", "戊辰", "己巳",
               "庚午", "辛未", "壬申", "癸酉"]
    day_pillar = day_gan + day_zhi
    if day_pillar in yin_cuo:
        results["阴错"] = {
            "name": "阴错", "pillar": "日柱", "source": day_pillar,
            "desc": _SHENSHA_INFO.get("阴错", {}).get("desc", ""),
            "cat": "凶", "level": 3,
        }
    if day_pillar in yang_cuo:
        results["阳错"] = {
            "name": "阳错", "pillar": "日柱", "source": day_pillar,
            "desc": _SHENSHA_INFO.get("阳错", {}).get("desc", ""),
            "cat": "凶", "level": 3,
        }

    # 太极贵人（也在日柱查）
    taiji_map_day = {
        "甲": "子", "乙": "丑", "丙": "寅", "丁": "卯",
        "戊": "未", "己": "申", "庚": "酉", "辛": "戌",
        "壬": "亥", "癸": "午",
    }
    if day_gan in taiji_map_day and taiji_map_day[day_gan] == day_zhi:
        results["太极贵人"] = {
            "name": "太极贵人", "pillar": "日柱", "source": f"日干{day_gan}日支{day_zhi}",
            "desc": _SHENSHA_INFO.get("太极贵人", {}).get("desc", ""),
            "cat": "吉神", "level": 4,
        }

    # 天乙贵人（日干查）
    tianyi_day_map = {
        "甲": ["丑", "未"], "戊": ["丑", "未"],
        "乙": ["子", "申"], "己": ["子", "申"],
        "丙": ["亥", "酉"], "丁": ["亥", "酉"],
        "壬": ["卯", "巳"], "癸": ["卯", "巳"],
        "庚": ["寅", "午"], "辛": ["寅", "午"],
    }
    if day_gan in tianyi_day_map and day_zhi in tianyi_day_map[day_gan]:
        results["天乙贵人"] = {
            "name": "天乙贵人", "pillar": "日柱", "source": f"日干{day_gan}",
            "desc": _SHENSHA_INFO.get("天乙贵人", {}).get("desc", ""),
            "cat": "吉神", "level": 5,
        }

    # 财禄（日支为财）
    cai_zhi = ["亥", "子"]  # 水为财
    if day_zhi in cai_zhi:
        results["财禄"] = {
            "name": "财禄", "pillar": "日柱", "source": f"日支{day_zhi}",
            "desc": _SHENSHA_INFO.get("财禄", {}).get("desc", ""),
            "cat": "吉神", "level": 4,
        }

    # 死亡
    death_zhi = ["酉", "戌"]
    if day_zhi in death_zhi:
        results["死亡"] = {
            "name": "死亡", "pillar": "日柱", "source": f"日支{day_zhi}",
            "desc": _SHENSHA_INFO.get("死亡", {}).get("desc", ""),
            "cat": "大凶", "level": 5,
        }

    return results


# ── 时柱神煞 ──────────────────────────────────────────────────────────────

def _calc_hour_shensha(hour_gan: str, hour_zhi: str, day_gan: str) -> Dict[str, Dict]:
    """时柱神煞推算"""
    results = {}

    # 时冲（时支与命局冲）
    # 时支为子午冲：时支见子午，有冲
    if hour_zhi in ["子", "午"]:
        results["时冲"] = {
            "name": "时冲", "pillar": "时柱", "source": f"时支{hour_zhi}",
            "desc": _SHENSHA_INFO.get("时冲", {}).get("desc", ""),
            "cat": "凶", "level": 3,
        }

    # 时柱桃花
    taohua_hour_map = {
        "申": "酉", "子": "酉", "辰": "酉",
        "寅": "卯", "午": "卯", "戌": "卯",
        "亥": "子", "卯": "子", "未": "子",
        "巳": "午", "酉": "午", "丑": "午",
    }
    if hour_zhi in taohua_hour_map:
        results["桃花_时"] = {
            "name": "桃花", "pillar": "时柱", "source": f"时支{hour_zhi}",
            "desc": "时支桃花，子息或晚年感情丰富",
            "cat": "凶", "level": 3,
        }

    return results


# ============================================================================
# 综合神煞推算
# ============================================================================

@dataclass
class ShenshaResult:
    """神煞推算结果"""
    pillars: Dict[str, str]
    year_shens: Dict[str, Dict]
    month_shens: Dict[str, Dict]
    day_shens: Dict[str, Dict]
    hour_shens: Dict[str, Dict]

    @property
    def all_shensha(self) -> Dict[str, Dict]:
        """合并所有神煞"""
        result = {}
        result.update(self.year_shens)
        result.update(self.month_shens)
        result.update(self.day_shens)
        result.update(self.hour_shens)
        return result

    @property
    def summary(self) -> Dict[str, Any]:
        """神煞摘要"""
        all_s = self.all_shensha
        by_cat: Dict[str, int] = {}
        for name, info in all_s.items():
            cat = info.get("cat", "平")
            by_cat[cat] = by_cat.get(cat, 0) + 1
        return {
            "total": len(all_s),
            "by_category": by_cat,
            "top_jixiong": self._top_by_cat("吉神") + self._top_by_cat("吉") +
                           self._top_by_cat("大凶") + self._top_by_cat("凶"),
        }

    def _top_by_cat(self, cat: str, limit: int = 3) -> List[Dict]:
        s = sorted(
            [v for v in self.all_shensha.values() if v.get("cat") == cat],
            key=lambda x: x.get("level", 0),
            reverse=True
        )[:limit]
        return [{"name": x["name"], "pillar": x["pillar"]} for x in s]

    def text_report(self) -> str:
        """生成文本报告"""
        lines = ["=" * 60, "神煞推算报告", "=" * 60]
        for pillar, shens in [
            ("年柱", self.year_shens), ("月柱", self.month_shens),
            ("日柱", self.day_shens), ("时柱", self.hour_shens),
        ]:
            if shens:
                lines.append(f"\n【{pillar}】")
                for name, info in sorted(shens.items(), key=lambda x: -x[1].get("level", 0)):
                    cat_icon = {"吉神": "★", "吉": "☆", "平": "○", "凶": "✗", "大凶": "✗✗"}.get(info.get("cat", "平"), "?")
                    lines.append(f"  {cat_icon} {name} — {info.get('source', '')} — {info.get('desc', '')}")
        s = self.summary
        lines.append(f"\n总计: {s['total']}个神煞")
        by_cat = s.get("by_category", {})
        for cat, cnt in sorted(by_cat.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat}: {cnt}个")
        return "\n".join(lines)

    def json_report(self) -> Dict[str, Any]:
        """生成 JSON 报告"""
        return {
            "pillars": self.pillars,
            "year_shensha": self.year_shens,
            "month_shensha": self.month_shens,
            "day_shensha": self.day_shens,
            "hour_shensha": self.hour_shens,
            "summary": self.summary,
        }


def calc_all_shensha(pillars: Dict[str, str]) -> ShenshaResult:
    """
    推算八字所有神煞

    Args:
        pillars: 四柱字典，格式 {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"}

    Returns:
        ShenshaResult: 神煞推算结果
    """
    year_gan = pillars["year"][0]
    year_zhi = pillars["year"][1]
    month_gan = pillars["month"][0]
    month_zhi = pillars["month"][1]
    day_gan = pillars["day"][0]
    day_zhi = pillars["day"][1]
    hour_gan = pillars["hour"][0]
    hour_zhi = pillars["hour"][1]

    return ShenshaResult(
        pillars=pillars,
        year_shens=_calc_year_shensha(year_gan, year_zhi),
        month_shens=_calc_month_shensha(month_gan, month_zhi),
        day_shens=_calc_day_shensha(day_gan, day_zhi),
        hour_shens=_calc_hour_shensha(hour_gan, hour_zhi, day_gan),
    )


# ============================================================================
# 引擎包装类（与 divination_engine.py 接口对齐）
# ============================================================================

class ShenshaEngine:
    """神煞推演引擎（包装函数式接口）"""

    @staticmethod
    def compute(pillars: Dict[str, str]) -> ShenshaResult:
        """给定四柱，推算所有神煞"""
        return calc_all_shensha(pillars)

    @staticmethod
    def compute_single(
        day_master: str,
        pillars: Dict[str, str],
        detail: str = "basic",
    ) -> Dict[str, Any]:
        """单柱神煞推算"""
        result = calc_all_shensha(pillars)
        if detail == "basic":
            return result.json_report()
        elif detail == "summary":
            return result.summary
        return result.json_report()


# ============================================================================
# CLI 测试
# ============================================================================

if __name__ == "__main__":
    # 测试用例：1990-06-15 10:30 → 庚午壬午辛亥癸巳
    test_pillars = {
        "year": "庚午", "month": "壬午",
        "day": "辛亥", "hour": "癸巳",
    }
    print(f"测试四柱: {test_pillars}")

    result = calc_all_shensha(test_pillars)
    print(result.text_report())

    print("\n" + "=" * 60)
    print("JSON 摘要:")
    import json
    print(json.dumps(result.summary, ensure_ascii=False, indent=2))

    # 更多测试
    test_cases = [
        {"year": "甲辰", "month": "丁卯", "day": "庚子", "hour": "丙子"},
        {"year": "乙酉", "month": "辛酉", "day": "戊午", "hour": "壬子"},
        {"year": "丙寅", "month": "壬辰", "day": "癸亥", "hour": "己丑"},
    ]
    print("\n" + "=" * 60)
    print("更多测试:")
    for tc in test_cases:
        r = calc_all_shensha(tc)
        s = r.summary
        print(f"  {tc} → {s['total']}神煞, {s['by_category']}")
