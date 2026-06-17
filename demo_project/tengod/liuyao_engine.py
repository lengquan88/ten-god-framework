#!/usr/bin/env python3
"""
liuyao_engine.py — 六爻起卦与断卦引擎 v1.0.0

六爻（纳甲筮法）是中国传统占卜术的核心，以三枚铜钱摇卦，
通过六十四卦、六亲、六神、世应等分析吉凶。

核心流程：
  1. 起卦（铜钱摇卦法）
  2. 排卦（本卦、变卦、互卦）
  3. 装卦（安世应、纳甲、定六亲、安六神）
  4. 断卦（用神分析、生克关系、吉凶判断）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import random


# ============================================================================
# 常量定义
# ============================================================================

# 八卦
BAGUA = {
    "乾": {"symbol": "☰", "nature": "天", "wuxing": "金", "num": 1},
    "兑": {"symbol": "☱", "nature": "泽", "wuxing": "金", "num": 2},
    "离": {"symbol": "☲", "nature": "火", "wuxing": "火", "num": 3},
    "震": {"symbol": "☳", "nature": "雷", "wuxing": "木", "num": 4},
    "巽": {"symbol": "☴", "nature": "风", "wuxing": "木", "num": 5},
    "坎": {"symbol": "☵", "nature": "水", "wuxing": "水", "num": 6},
    "艮": {"symbol": "☶", "nature": "山", "wuxing": "土", "num": 7},
    "坤": {"symbol": "☷", "nature": "地", "wuxing": "土", "num": 8},
}

# 八卦卦序（先天八卦）
BAGUA_ORDER = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]

# 八卦爻象（阳爻=1, 阴爻=0，从下往上）
BAGUA_YAO = {
    "乾": [1, 1, 1],
    "兑": [0, 1, 1],
    "离": [1, 0, 1],
    "震": [0, 0, 1],
    "巽": [1, 1, 0],
    "坎": [0, 1, 0],
    "艮": [1, 0, 0],
    "坤": [0, 0, 0],
}

# 八卦纳甲（天干）
BAGUA_NAJIA_GAN = {
    "乾": "甲壬", "坤": "乙癸", "震": "庚", "巽": "辛",
    "坎": "戊", "离": "己", "艮": "丙", "兑": "丁",
}

# 六爻纳支（从初爻到上爻）
BAGUA_NAZHI = {
    "乾": ["子", "寅", "辰", "午", "申", "戌"],
    "震": ["子", "寅", "辰", "午", "申", "戌"],
    "坎": ["寅", "辰", "午", "申", "戌", "子"],
    "艮": ["辰", "午", "申", "戌", "子", "寅"],
    "坤": ["未", "巳", "卯", "丑", "亥", "酉"],
    "巽": ["丑", "亥", "酉", "未", "巳", "卯"],
    "离": ["卯", "丑", "亥", "酉", "未", "巳"],
    "兑": ["巳", "卯", "丑", "亥", "酉", "未"],
}

# 五行生克关系
WUXING_RELATION = {
    "金": {"生": "水", "克": "木", "被生": "土", "被克": "火"},
    "木": {"生": "火", "克": "土", "被生": "水", "被克": "金"},
    "水": {"生": "木", "克": "火", "被生": "金", "被克": "土"},
    "火": {"生": "土", "克": "金", "被生": "木", "被克": "水"},
    "土": {"生": "金", "克": "水", "被生": "火", "被克": "木"},
}

# 六亲：根据卦宫五行和爻支五行确定
# 生我者父母，我生者子孙，克我者官鬼，我克者妻财，同我者兄弟
LIUQIN_RULES = ["父母", "兄弟", "官鬼", "妻财", "子孙"]

# 六神（按日干起）
LIUSHEN_ORDER = ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"]
LIUSHEN_START = {
    "甲": 0, "乙": 0, "丙": 1, "丁": 1, "戊": 2,
    "己": 3, "庚": 4, "辛": 4, "壬": 5, "癸": 5,
}

# 六十四卦数据
# 格式: (上卦, 下卦, 卦名, 世爻位置(1-6), 应爻位置, 卦宫, 卦序)
_64GUA_DATA = [
    ("乾", "乾", "乾为天", 6, 3, "乾", 1),
    ("坤", "坤", "坤为地", 6, 3, "坤", 2),
    ("坎", "震", "水雷屯", 2, 5, "坎", 3),
    ("艮", "坎", "山水蒙", 4, 1, "离", 4),
    ("坎", "乾", "水天需", 5, 2, "坤", 5),
    ("乾", "坎", "天水讼", 4, 1, "离", 6),
    ("坤", "坎", "地水师", 3, 6, "坎", 7),
    ("坎", "坤", "水地比", 3, 6, "坤", 8),
    ("巽", "乾", "风天小畜", 1, 4, "巽", 9),
    ("乾", "兑", "天泽履", 5, 2, "艮", 10),
    ("坤", "乾", "地天泰", 3, 6, "坤", 11),
    ("乾", "坤", "天地否", 3, 6, "乾", 12),
    ("乾", "离", "天火同人", 4, 1, "离", 13),
    ("离", "乾", "火天大有", 1, 4, "乾", 14),
    ("坤", "艮", "地山谦", 5, 2, "兑", 15),
    ("震", "坤", "雷地豫", 1, 4, "震", 16),
    ("兑", "震", "泽雷随", 3, 6, "震", 17),
    ("艮", "巽", "山风蛊", 3, 6, "巽", 18),
    ("坤", "兑", "地泽临", 2, 5, "坤", 19),
    ("巽", "坤", "风地观", 4, 1, "乾", 20),
    ("离", "震", "火雷噬嗑", 5, 2, "巽", 21),
    ("艮", "离", "山火贲", 1, 4, "艮", 22),
    ("艮", "坤", "山地剥", 5, 2, "乾", 23),
    ("坤", "震", "地雷复", 1, 4, "坤", 24),
    ("乾", "震", "天雷无妄", 4, 1, "巽", 25),
    ("艮", "乾", "山天大畜", 2, 5, "艮", 26),
    ("艮", "震", "山雷颐", 4, 1, "巽", 27),
    ("兑", "巽", "泽风大过", 4, 1, "震", 28),
    ("坎", "坎", "坎为水", 6, 3, "坎", 29),
    ("离", "离", "离为火", 6, 3, "离", 30),
    ("兑", "艮", "泽山咸", 3, 6, "兑", 31),
    ("震", "巽", "雷风恒", 3, 6, "震", 32),
    ("乾", "艮", "天山遁", 2, 5, "乾", 33),
    ("震", "乾", "雷天大壮", 4, 1, "坤", 34),
    ("离", "坤", "火地晋", 4, 1, "乾", 35),
    ("坤", "离", "地火明夷", 1, 4, "坎", 36),
    ("巽", "离", "风火家人", 2, 5, "巽", 37),
    ("离", "兑", "火泽睽", 4, 1, "艮", 38),
    ("坎", "艮", "水山蹇", 4, 1, "兑", 39),
    ("震", "坎", "雷水解", 2, 5, "震", 40),
    ("艮", "兑", "山泽损", 3, 6, "艮", 41),
    ("巽", "震", "风雷益", 3, 6, "巽", 42),
    ("兑", "乾", "泽天夬", 5, 2, "坤", 43),
    ("乾", "巽", "天风姤", 1, 4, "乾", 44),
    ("兑", "坤", "泽地萃", 2, 5, "兑", 45),
    ("坤", "巽", "地风升", 1, 4, "震", 46),
    ("兑", "坎", "泽水困", 1, 4, "兑", 47),
    ("坎", "巽", "水风井", 5, 2, "震", 48),
    ("兑", "离", "泽火革", 4, 1, "坎", 49),
    ("离", "巽", "火风鼎", 4, 1, "离", 50),
    ("震", "震", "震为雷", 6, 3, "震", 51),
    ("艮", "艮", "艮为山", 6, 3, "艮", 52),
    ("巽", "艮", "风山渐", 3, 6, "艮", 53),
    ("震", "兑", "雷泽归妹", 5, 2, "兑", 54),
    ("震", "离", "雷火丰", 5, 2, "坎", 55),
    ("离", "艮", "火山旅", 1, 4, "离", 56),
    ("巽", "巽", "巽为风", 6, 3, "巽", 57),
    ("兑", "兑", "兑为泽", 6, 3, "兑", 58),
    ("巽", "坎", "风水涣", 5, 2, "离", 59),
    ("坎", "兑", "水泽节", 1, 4, "坎", 60),
    ("巽", "兑", "风泽中孚", 4, 1, "艮", 61),
    ("震", "艮", "雷山小过", 4, 1, "兑", 62),
    ("坎", "离", "水火既济", 3, 6, "坎", 63),
    ("离", "坎", "火水未济", 3, 6, "离", 64),
]

# 六十四卦名称索引
_GUA_INDEX = {(s, x): (name, shi, ying, gong, num) for s, x, name, shi, ying, gong, num in _64GUA_DATA}

# 卦象简明断辞
GUA_DUANCI = {
    "乾为天": "元亨利贞。自强不息，飞龙在天。",
    "坤为地": "元亨，利牝马之贞。厚德载物。",
    "水雷屯": "元亨利贞。勿用有攸往。初创艰难。",
    "山水蒙": "亨。匪我求童蒙，童蒙求我。启蒙发智。",
    "水天需": "有孚，光亨，贞吉。利涉大川。耐心等待。",
    "天水讼": "有孚窒惕，中吉终凶。争讼不利。",
    "地水师": "贞，丈人吉，无咎。出师有名。",
    "水地比": "吉。原筮元永贞，无咎。亲附团结。",
    "风天小畜": "亨。密云不雨。蓄势待发。",
    "天泽履": "履虎尾，不咥人，亨。谨慎行事。",
    "地天泰": "小往大来，吉亨。通泰顺利。",
    "天地否": "否之匪人，不利君子贞。闭塞不通。",
    "天火同人": "同人于野，亨。利涉大川。团结合作。",
    "火天大有": "元亨。丰收富足。",
    "地山谦": "亨，君子有终。谦虚受益。",
    "雷地豫": "利建侯行师。愉悦安乐。",
    "泽雷随": "元亨利贞，无咎。顺时而动。",
    "山风蛊": "元亨，利涉大川。先甲三日，后甲三日。整治腐败。",
    "地泽临": "元亨利贞。至于八月有凶。居高临下。",
    "风地观": "盥而不荐，有孚颙若。观察审视。",
    "火雷噬嗑": "亨。利用狱。决断是非。",
    "山火贲": "亨。小利有攸往。文饰美化。",
    "山地剥": "不利有攸往。剥落衰败。",
    "地雷复": "亨。出入无疾，朋来无咎。一阳来复。",
    "天雷无妄": "元亨利贞。其匪正有眚。不可妄为。",
    "山天大畜": "利贞。不家食吉。利涉大川。积蓄力量。",
    "山雷颐": "贞吉。观颐，自求口实。养身养德。",
    "泽风大过": "栋桡，利有攸往，亨。过度失衡。",
    "坎为水": "习坎，有孚，维心亨。行有尚。处险不惊。",
    "离为火": "利贞，亨。畜牝牛吉。依附光明。",
    "泽山咸": "亨利贞，取女吉。感应相通。",
    "雷风恒": "亨，无咎，利贞。利有攸往。恒久不变。",
    "天山遁": "亨，小利贞。退隐避世。",
    "雷天大壮": "利贞。强盛壮大。",
    "火地晋": "康侯用锡马蕃庶，昼日三接。晋升发展。",
    "地火明夷": "利艰贞。光明受损。",
    "风火家人": "利女贞。家庭和睦。",
    "火泽睽": "小事吉。乖离不合。",
    "水山蹇": "利西南，不利东北。利见大人。艰难险阻。",
    "雷水解": "利西南。无所往，其来复吉。有攸往，夙吉。解除困难。",
    "山泽损": "有孚，元吉，无咎。可贞，利有攸往。损下益上。",
    "风雷益": "利有攸往，利涉大川。损上益下。",
    "泽天夬": "扬于王庭，孚号有厉。决断果行。",
    "天风姤": "女壮，勿用取女。不期而遇。",
    "泽地萃": "亨。王假有庙。聚集荟萃。",
    "地风升": "元亨，用见大人。勿恤，南征吉。上升发展。",
    "泽水困": "亨，贞，大人吉。困顿受挫。",
    "水风井": "改邑不改井。养人利物。",
    "泽火革": "己日乃孚。元亨利贞，悔亡。变革创新。",
    "火风鼎": "元吉，亨。鼎新革故。",
    "震为雷": "亨。震来虩虩，笑言哑哑。震惊百里。临危不乱。",
    "艮为山": "艮其背，不获其身。行其庭，不见其人。知止不殆。",
    "风山渐": "女归吉，利贞。循序渐进。",
    "雷泽归妹": "征凶，无攸利。婚姻嫁娶。",
    "雷火丰": "亨，王假之。勿忧，宜日中。丰盛盈满。",
    "火山旅": "小亨，旅贞吉。旅行在外。",
    "巽为风": "小亨，利有攸往，利见大人。顺从谦逊。",
    "兑为泽": "亨利贞。喜悦和乐。",
    "风水涣": "亨。王假有庙。涣散离散。",
    "水泽节": "亨。苦节不可贞。节制有度。",
    "风泽中孚": "豚鱼吉，利涉大川，利贞。诚信感化。",
    "雷山小过": "亨利贞。可小事，不可大事。小有过越。",
    "水火既济": "亨小，利贞。初吉终乱。事成圆满。",
    "火水未济": "亨。小狐汔济，濡其尾。事未完成。",
}


# ============================================================================
# 数据模型
# ============================================================================

class YaoType(Enum):
    """爻类型"""
    SHAO_YANG = "少阳"   # 1阳 — 不变
    SHAO_YIN = "少阴"    # 0阴 — 不变
    LAO_YANG = "老阳"    # 0阳→阴 动爻
    LAO_YIN = "老阴"     # 1阴→阳 动爻


@dataclass
class YaoInfo:
    """爻信息"""
    position: int        # 爻位 1-6（初爻到上爻）
    yao_type: YaoType    # 爻类型
    value: int           # 爻值(0/1)
    is_dong: bool        # 是否动爻
    zhi: str = ""        # 地支
    gan: str = ""        # 天干
    liuqin: str = ""     # 六亲
    liushen: str = ""    # 六神
    shi: bool = False    # 是否世爻
    ying: bool = False   # 是否应爻


@dataclass
class LiuyaoResult:
    """六爻卦象结果"""
    # 卦名
    ben_gua_name: str       # 本卦名
    bian_gua_name: str = "" # 变卦名
    hu_gua_name: str = ""   # 互卦名
    
    # 卦象
    ben_gua_symbol: str = ""  # 本卦符号
    bian_gua_symbol: str = "" # 变卦符号
    
    # 八卦
    shang_gua: str = ""     # 上卦
    xia_gua: str = ""       # 下卦
    gua_gong: str = ""      # 卦宫
    
    # 六爻
    yaos: List[YaoInfo] = field(default_factory=list)
    
    # 断辞
    ben_gua_duanci: str = ""
    bian_gua_duanci: str = ""
    overall_judgment: str = ""
    
    # 日期
    day_ganzhi: str = ""
    day_gan: str = ""
    
    # 动爻
    dong_yao_positions: List[int] = field(default_factory=list)


# ============================================================================
# 核心引擎
# ============================================================================

class LiuyaoEngine:
    """六爻起卦与断卦引擎"""

    @classmethod
    def _get_gua_by_yao(cls, yao_values: List[int]) -> Tuple[str, str, str]:
        """根据六爻值获取卦象"""
        # 上卦（上三爻）
        upper_yao = tuple(yao_values[3:])
        shang = None
        for name, yao in BAGUA_YAO.items():
            if tuple(yao) == upper_yao:
                shang = name
                break
        
        # 下卦（下三爻）
        lower_yao = tuple(yao_values[:3])
        xia = None
        for name, yao in BAGUA_YAO.items():
            if tuple(yao) == lower_yao:
                xia = name
                break
        
        return shang or "坤", xia or "坤", ""

    @classmethod
    def _get_gua_info(cls, shang: str, xia: str) -> Tuple[str, int, int, str, int]:
        """获取卦名、世爻、应爻、卦宫、卦序"""
        return _GUA_INDEX.get((shang, xia), ("未知卦", 1, 4, "乾", 0))

    @classmethod
    def _get_hu_gua(cls, yao_values: List[int]) -> Tuple[str, str]:
        """获取互卦（二三四爻为下卦，三四五爻为上卦）"""
        # 互卦下卦：二、三、四爻
        lower_yao = (yao_values[1], yao_values[2], yao_values[3])
        xia = None
        for name, yao in BAGUA_YAO.items():
            if tuple(yao) == lower_yao:
                xia = name
                break
        
        # 互卦上卦：三、四、五爻
        upper_yao = (yao_values[2], yao_values[3], yao_values[4])
        shang = None
        for name, yao in BAGUA_YAO.items():
            if tuple(yao) == upper_yao:
                shang = name
                break
        
        return shang or "坤", xia or "坤"

    @classmethod
    def _yao_to_symbol(cls, value: int, is_dong: bool) -> str:
        """爻值转符号"""
        if value == 1:
            return "⚊" if not is_dong else "◯"
        else:
            return "⚋" if not is_dong else "❌"

    @classmethod
    def _get_liuqin(cls, gua_gong_wuxing: str, yao_zhi: str) -> str:
        """根据卦宫五行和爻支五行确定六亲"""
        # 查爻支五行
        zhi_wuxing = {
            "子": "水", "丑": "土", "寅": "木", "卯": "木",
            "辰": "土", "巳": "火", "午": "火", "未": "土",
            "申": "金", "酉": "金", "戌": "土", "亥": "水",
        }
        yao_wx = zhi_wuxing.get(yao_zhi, "土")
        gong_wx = gua_gong_wuxing
        
        if yao_wx == gong_wx:
            return "兄弟"
        if WUXING_RELATION[yao_wx]["生"] == gong_wx:
            return "父母"
        if WUXING_RELATION[yao_wx]["克"] == gong_wx:
            return "官鬼"
        if WUXING_RELATION[gong_wx]["生"] == yao_wx:
            return "子孙"
        if WUXING_RELATION[gong_wx]["克"] == yao_wx:
            return "妻财"
        return "兄弟"

    @classmethod
    def _get_liushen(cls, day_gan: str, position: int) -> str:
        """根据日干和爻位确定六神"""
        start = LIUSHEN_START.get(day_gan, 0)
        # 初爻起，从初爻到上爻
        idx = (start + 5 - (position - 1)) % 6
        return LIUSHEN_ORDER[idx]

    @classmethod
    def shake_coins(cls, randomize: bool = True, seed: int = None) -> List[YaoType]:
        """
        铜钱摇卦法：模拟摇六次，每次三枚铜钱
        
        三枚铜钱：
          - 三正（老阳, ○）: 阳爻，动爻→变阴
          - 两正一反（少阳, —）: 阳爻，不变
          - 一正两反（少阴, - -）: 阴爻，不变
          - 三反（老阴, ×）: 阴爻，动爻→变阳
        """
        if seed is not None:
            random.seed(seed)
        
        result = []
        for _ in range(6):
            # 三枚铜钱，每枚1为正面（阳），0为反面（阴）
            coins = [random.randint(0, 1) for _ in range(3)]
            yang_count = sum(coins)
            
            if yang_count == 3:
                result.append(YaoType.LAO_YANG)   # 三正→老阳
            elif yang_count == 2:
                result.append(YaoType.SHAO_YANG)  # 两正一反→少阳
            elif yang_count == 1:
                result.append(YaoType.SHAO_YIN)   # 一正两反→少阴
            else:
                result.append(YaoType.LAO_YIN)    # 三反→老阴
        
        return result

    @classmethod
    def calc_gua(cls, yao_types: List[YaoType] = None,
                 day_ganzhi: str = None) -> LiuyaoResult:
        """
        完整六爻排卦
        
        参数:
            yao_types: 六爻类型列表（若为None则自动摇卦）
            day_ganzhi: 日干支，如"甲子"（用于六神）
        """
        if yao_types is None:
            yao_types = cls.shake_coins()
        
        # 本卦爻值
        ben_values = []
        for yt in yao_types:
            if yt in (YaoType.SHAO_YANG, YaoType.LAO_YANG):
                ben_values.append(1)
            else:
                ben_values.append(0)
        
        # 变卦爻值
        bian_values = []
        dong_positions = []
        for i, yt in enumerate(yao_types):
            if yt == YaoType.LAO_YANG:
                bian_values.append(0)  # 老阳变阴
                dong_positions.append(i + 1)
            elif yt == YaoType.LAO_YIN:
                bian_values.append(1)  # 老阴变阳
                dong_positions.append(i + 1)
            else:
                bian_values.append(ben_values[i])
        
        # 获取卦象
        shang_gua, xia_gua, _ = cls._get_gua_by_yao(ben_values)
        ben_name, shi_yao, ying_yao, gua_gong, _ = cls._get_gua_info(shang_gua, xia_gua)
        
        shang_bian, xia_bian, _ = cls._get_gua_by_yao(bian_values)
        bian_name, _, _, _, _ = cls._get_gua_info(shang_bian, xia_bian)
        
        hu_shang, hu_xia = cls._get_hu_gua(ben_values)
        hu_name, _, _, _, _ = cls._get_gua_info(hu_shang, hu_xia)
        
        # 日干支
        if day_ganzhi is None:
            day_ganzhi = "甲子"
        day_gan = day_ganzhi[0]
        
        # 卦宫五行
        gua_gong_wuxing = BAGUA[gua_gong]["wuxing"]
        
        # 构建六爻
        yaos = []
        for i in range(6):
            yt = yao_types[i]
            pos = i + 1  # 初爻=1, 上爻=6
            
            # 纳支
            zhi = BAGUA_NAZHI[gua_gong][i] if gua_gong in BAGUA_NAZHI else BAGUA_NAZHI["乾"][i]
            
            yaos.append(YaoInfo(
                position=pos,
                yao_type=yt,
                value=ben_values[i],
                is_dong=yt in (YaoType.LAO_YANG, YaoType.LAO_YIN),
                zhi=zhi,
                gan="",
                liuqin=cls._get_liuqin(gua_gong_wuxing, zhi),
                liushen=cls._get_liushen(day_gan, pos),
                shi=(pos == shi_yao),
                ying=(pos == ying_yao),
            ))
        
        # 卦象符号
        ben_symbol = "".join(cls._yao_to_symbol(yaos[i].value, yaos[i].is_dong) for i in range(5, -1, -1))
        bian_symbol = "".join("⚊" if bian_values[i] else "⚋" for i in range(5, -1, -1))
        
        # 断辞
        ben_duanci = GUA_DUANCI.get(ben_name, "")
        bian_duanci = GUA_DUANCI.get(bian_name, "")
        
        # 综合判断
        overall = cls._judge(yaos, dong_positions, ben_name, gua_gong)
        
        return LiuyaoResult(
            ben_gua_name=ben_name,
            bian_gua_name=bian_name,
            hu_gua_name=hu_name,
            ben_gua_symbol=ben_symbol,
            bian_gua_symbol=bian_symbol,
            shang_gua=shang_gua,
            xia_gua=xia_gua,
            gua_gong=gua_gong,
            yaos=yaos,
            ben_gua_duanci=ben_duanci,
            bian_gua_duanci=bian_duanci,
            overall_judgment=overall,
            day_ganzhi=day_ganzhi,
            day_gan=day_gan,
            dong_yao_positions=dong_positions,
        )

    @classmethod
    def _judge(cls, yaos: List[YaoInfo], dong_positions: List[int],
               ben_name: str, gua_gong: str) -> str:
        """综合断卦"""
        parts = []
        
        # 动爻分析
        if dong_positions:
            parts.append(f"动爻: {', '.join(f'第{p}爻' for p in dong_positions)}")
            dong_yao = yaos[dong_positions[0] - 1]
            parts.append(f"主爻六亲: {dong_yao.liuqin}, 六神: {dong_yao.liushen}")
        else:
            parts.append("静卦，无动爻。以世爻为主。")
        
        # 世爻分析
        shi_yao = next((y for y in yaos if y.shi), None)
        if shi_yao:
            parts.append(f"世爻: {shi_yao.zhi} {shi_yao.liuqin} {shi_yao.liushen}")
        
        return " ".join(parts)

    @classmethod
    def format_text(cls, result: LiuyaoResult) -> str:
        """格式化输出"""
        lines = []
        lines.append("╔══════════════════════════════════╗")
        lines.append("║       六 爻 卦 象               ║")
        lines.append("╠══════════════════════════════════╣")
        lines.append(f"║ 本卦: {result.ben_gua_name} {result.ben_gua_symbol}")
        lines.append(f"║ 变卦: {result.bian_gua_name} {result.bian_gua_symbol}")
        lines.append(f"║ 互卦: {result.hu_gua_name}")
        lines.append(f"║ 卦宫: {result.gua_gong}  上卦: {result.shang_gua}  下卦: {result.xia_gua}")
        lines.append(f"║ 日辰: {result.day_ganzhi}")
        if result.dong_yao_positions:
            lines.append(f"║ 动爻: {', '.join(str(p) for p in result.dong_yao_positions)}")
        lines.append("╠══════════════════════════════════╣")
        
        # 爻位（从上到下）
        for yao in reversed(result.yaos):
            pos = yao.position
            symbol = LiuyaoEngine._yao_to_symbol(yao.value, yao.is_dong)
            tags = []
            if yao.shi:
                tags.append("世")
            if yao.ying:
                tags.append("应")
            if yao.is_dong:
                tags.append("动")
            tag_str = " ".join(tags)
            lines.append(f"║ {pos}爻 {symbol} {yao.liuqin} {yao.zhi} {yao.liushen} {tag_str}")
        
        lines.append("╠══════════════════════════════════╣")
        lines.append(f"║ 本卦断: {result.ben_gua_duanci[:30]}...")
        if result.bian_gua_name != result.ben_gua_name:
            lines.append(f"║ 变卦断: {result.bian_gua_duanci[:30]}...")
        lines.append(f"║ 综合: {result.overall_judgment[:50]}")
        lines.append("╚══════════════════════════════════╝")
        return "\n".join(lines)


# ============================================================================
# 便捷函数
# ============================================================================

def shake_and_calc(day_ganzhi: str = None) -> LiuyaoResult:
    """摇卦并排盘"""
    return LiuyaoEngine.calc_gua(day_ganzhi=day_ganzhi)


def calc_from_yao(yao_str: str, day_ganzhi: str = None) -> LiuyaoResult:
    """
    从六爻字符串排盘
    
    yao_str: 六爻字符串，每爻一个字符
      1=少阳, 0=少阴, 3=老阳, 2=老阴
      从初爻到上爻
    """
    type_map = {
        "1": YaoType.SHAO_YANG, "0": YaoType.SHAO_YIN,
        "3": YaoType.LAO_YANG, "2": YaoType.LAO_YIN,
    }
    yao_types = [type_map.get(c, YaoType.SHAO_YANG) for c in yao_str[:6]]
    return LiuyaoEngine.calc_gua(yao_types, day_ganzhi=day_ganzhi)


__all__ = [
    "LiuyaoEngine", "LiuyaoResult", "YaoInfo", "YaoType",
    "shake_and_calc", "calc_from_yao",
    "GUA_DUANCI", "BAGUA", "LIUSHEN_ORDER",
]