"""
advanced_shushu.py — 阶段二十一 · 21.4 高级术数系统
=====================================================

集成：
  - 铁板神数（Tie Ban Shen Shu）：按八字起数 + 条文映射
  - 邵子神数（Shao Zi Shen Shu）：按元会运世 + 皇极经世
  - 河洛数（He Luo Shu）：先天八卦起数
  - 称骨算命（称骨歌）：简化版袁天罡称骨

注意：
  传统术数体系极其复杂（铁板神数有12000条、邵子神数有完整经世体系），
  此处为"演示级别"实现，采用简化算法 + 代表性条文库。
  实际命理应用需结合完整经典文本。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# 基础数据
# ============================================================================

# 十天干：五行 + 数（河图/洛书数）
TIAN_GAN = {
    "甲": {"wuxing": "木", "num": 3, "dayuan": 9},
    "乙": {"wuxing": "木", "num": 8, "dayuan": 9},
    "丙": {"wuxing": "火", "num": 7, "dayuan": 8},
    "丁": {"wuxing": "火", "num": 2, "dayuan": 8},
    "戊": {"wuxing": "土", "num": 5, "dayuan": 8},
    "己": {"wuxing": "土", "num": 10, "dayyuan": 8},
    "庚": {"wuxing": "金", "num": 9, "dayyuan": 7},
    "辛": {"wuxing": "金", "num": 4, "dayyuan": 7},
    "壬": {"wuxing": "水", "num": 1, "dayyuan": 7},
    "癸": {"wuxing": "水", "num": 6, "dayyuan": 7},
}

# 十二地支：五行 + 数 + 生肖
DI_ZHI = {
    "子": {"wuxing": "水", "num": 1, "zodiac": "鼠", "yue": 11},
    "丑": {"wuxing": "土", "num": 2, "zodiac": "牛", "yue": 12},
    "寅": {"wuxing": "木", "num": 3, "zodiac": "虎", "yue": 1},
    "卯": {"wuxing": "木", "num": 4, "zodiac": "兔", "yue": 2},
    "辰": {"wuxing": "土", "num": 5, "zodiac": "龙", "yue": 3},
    "巳": {"wuxing": "火", "num": 6, "zodiac": "蛇", "yue": 4},
    "午": {"wuxing": "火", "num": 7, "zodiac": "马", "yue": 5},
    "未": {"wuxing": "土", "num": 8, "zodiac": "羊", "yue": 6},
    "申": {"wuxing": "金", "num": 9, "zodiac": "猴", "yue": 7},
    "酉": {"wuxing": "金", "num": 10, "zodiac": "鸡", "yue": 8},
    "戌": {"wuxing": "土", "num": 11, "zodiac": "狗", "yue": 9},
    "亥": {"wuxing": "水", "num": 12, "zodiac": "猪", "yue": 10},
}

# 先天八卦数（邵子用）
XIANTIAN_BAGUA = {
    1: "乾", 2: "兑", 3: "离", 4: "震",
    5: "巽", 6: "坎", 7: "艮", 8: "坤",
}

# 后天八卦数
HOUTIAN_BAGUA = {
    1: "坎", 2: "坤", 3: "震", 4: "巽",
    5: "中", 6: "乾", 7: "兑", 8: "艮", 9: "离",
}


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class TiebanshuResult:
    """铁板神数起数结果"""
    tian_pan: str                 # 天盘
    di_pan: str                    # 地盘
    ren_pan: str                   # 人盘
    base_num: int                  # 基础数
    key_numbers: List[int]         # 关键起数（用于查条文）
    tiaowen: List[str]             # 命中条文
    summary: str                   # 总结
    method: str = "简化铁板神数"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "tian_pan": self.tian_pan,
            "di_pan": self.di_pan,
            "ren_pan": self.ren_pan,
            "base_num": self.base_num,
            "key_numbers": self.key_numbers,
            "tiaowen": self.tiaowen,
            "summary": self.summary,
        }


@dataclass
class ShaoziResult:
    """邵子神数结果"""
    yuan_hui_yun_shi: Dict[str, int]  # 元会运世
    huangji_hexagram: str              # 皇极经世卦
    tiaowen: List[str]                 # 条文
    total_score: int                   # 综合评分
    summary: str                       # 总结
    method: str = "邵子神数·皇极经世"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "yuan_hui_yun_shi": self.yuan_hui_yun_shi,
            "huangji_hexagram": self.huangji_hexagram,
            "tiaowen": self.tiaowen,
            "total_score": self.total_score,
            "summary": self.summary,
        }


@dataclass
class ChengguResult:
    """称骨算命结果"""
    total_liang: float             # 总两数
    yue_liang: float               # 月两
    ri_liang: float                # 日两
    shi_liang: float               # 时两
    tiaowen: str                    # 称骨歌
    interpretation: str             # 解读

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_liang": self.total_liang,
            "yue_liang": self.yue_liang,
            "ri_liang": self.ri_liang,
            "shi_liang": self.shi_liang,
            "tiaowen": self.tiaowen,
            "interpretation": self.interpretation,
        }


# ============================================================================
# 铁板神数条文库（简化版，代表性条文）
# ============================================================================

TIEBAN_TIAOWEN = {
    1001: "初年命运最亨通，衣禄丰盈喜气浓。",
    1002: "中年渐达青云路，晚景荣华福寿崇。",
    1003: "命逢贵格主聪明，文章博学有声名。",
    1004: "一生心性最聪明，作事轩昂近贵人。",
    1005: "初年驳杂晚亨通，衣禄丰盈福自崇。",
    1006: "命中财帛自然来，不用营谋自聚财。",
    1007: "富贵荣华命里招，田园产业足丰饶。",
    1008: "为人性巧更聪明，作事轩昂近贵荣。",
    1009: "一生衣禄自天来，名利双全福寿偕。",
    1010: "富贵荣华天付汝，正宜修省福弥长。",
    2001: "兄弟六亲皆有靠，和顺家门福自招。",
    2002: "夫妻和合两相宜，子息成双福可期。",
    2003: "六亲冷淡少依靠，自立自成福自宜。",
    2004: "妻宫若要无刑克，龙虎牛蛇方可期。",
    2005: "子息二三为上格，送老归山福自宜。",
    2006: "初年得子主生离，晚岁生儿得福基。",
    2007: "兄弟虽多无助力，不如独自主门楣。",
    2008: "父母双全俱有寿，椿萱并茂乐优悠。",
    3001: "正财兴旺偏财少，安分营谋福自招。",
    3002: "财帛丰盈产业兴，营谋经商利倍生。",
    3003: "官禄宫中有贵人，仕途通达显功名。",
    3004: "南方作事最为宜，东北方中亦可依。",
    3005: "不宜做官宜守分，工商技艺可施为。",
    3006: "事业须防小人害，谨慎营谋得大财。",
    3007: "命中带印主权贵，金榜题名天下知。",
    4001: "身体康健无灾祸，寿元可许古来稀。",
    4002: "注意脾胃与饮食，保养精神福寿长。",
    4003: "寿元可至八十六，若能修省更悠悠。",
    4004: "小心水火与刀兵，守分安身福自宁。",
    4005: "祖业飘零难守成，自立自创始亨通。",
    4006: "迁居改业方为吉，守旧必然有是非。",
    5001: "命带桃花主风流，情海波澜几度秋。",
    5002: "婚姻须防三番改，到头方可得齐眉。",
    5003: "夫妻偕老两无伤，儿女成行福满堂。",
    5004: "红鸾天喜照命宫，婚姻美满福千钟。",
    5005: "早婚必定有刑克，晚娶方可得安宁。",
}


# ============================================================================
# 邵子神数（皇极经世）简化条文
# ============================================================================

SHAOZI_TIAOWEN = {
    "乾为天": "元亨利贞大吉昌，君子行事正且刚。",
    "坤为地": "厚德载物柔顺利，母仪天下福绵长。",
    "水雷屯": "万事起头难且艰，固守待时可转安。",
    "山水蒙": "蒙以养正圣之功，童蒙求我启蒙聪。",
    "水天需": "需于郊泥入于穴，饮食宴乐待时行。",
    "天水讼": "讼则终凶宜和解，争强好胜惹灾殃。",
    "地水师": "师出以律贞吉亨，将才得位定功成。",
    "水地比": "比之自内吉无咎，亲比贤人事业成。",
    "风天小畜": "小有所畜密云雨，积蓄力量待时行。",
    "天泽履": "履虎尾兮不咥人，慎行其道得亨通。",
    "地天泰": "天地交泰万物通，小往大来福自生。",
    "天地否": "天地不交否塞闭，君子以俭德避难。",
    "天火同人": "同人于野利涉川，同心协力事可成。",
    "火天大有": "大有元亨顺天休，大有收获得众助。",
    "地山谦": "谦谦君子有终吉，君子以裒多益寡。",
    "雷地豫": "豫顺以动利建侯，顺时而动事皆通。",
    "泽雷随": "随之时义大矣哉，随顺时势可有为。",
    "山风蛊": "蛊坏之后始治理，振弊起衰事可为。",
    "地泽临": "君临天下有容光，以上临下事皆成。",
    "风地观": "观国之光尚宾至，观察时势可施为。",
    "火雷噬嗑": "口中有物须噬嗑，克服障碍得亨通。",
    "山火贲": "贲饰文明外有章，内在充实外有光。",
    "山地剥": "剥床以肤凶近灾，小人道长君子消。",
    "地雷复": "复则见天地之心，一阳来复万物新。",
    "天雷无妄": "无妄之灾须预防，守正不妄自安康。",
    "山天大畜": "大畜刚健笃实辉，积蓄厚德大有为。",
    "山雷颐": "颐养正则吉无咎，慎言语兮节饮食。",
    "泽风大过": "大过之时非常也，独立不惧有作为。",
    "坎为水": "水洊至习坎重险，心亨行尚入于坎。",
    "离为火": "明两作离大人继，光明丽正照四方。",
    "泽山咸": "咸感也柔上而刚下，男女感应万事通。",
    "雷风恒": "恒久也君子以立，持之以恒事可成。",
    "天山遁": "遁退也君子远小人，审时度势善退藏。",
    "雷天大壮": "大壮利贞大者正，气势盛大须守正。",
    "火地晋": "晋进也明出地上，光明显著渐升腾。",
    "地火明夷": "明入地中光明伤，韬光养晦待时行。",
    "风火家人": "家人有严君焉，正家之道在和敬。",
    "火泽睽": "睽乖违其事难同，求同存异可有为。",
    "水山蹇": "蹇难也险在前也，反身修德济艰难。",
    "雷水解": "解缓也险以动免，解难济险出险夷。",
    "山泽损": "损下益上其道上行，损己利人事可成。",
    "风雷益": "损上益下其道大光，利民得众事恒昌。",
    "泽天夬": "夬决也刚决柔也，当断不断反受其乱。",
    "天风姤": "姤遇也柔遇刚也，偶遇之时须慎始。",
    "泽地萃": "萃聚也万物相聚，聚众之事贵有德。",
    "地风升": "上升也柔以时升，循序渐进事业成。",
    "泽水困": "困穷也君子致命，处困之时守正志。",
    "水风井": "井养而不穷也，修德养民泽及人。",
    "泽火革": "革改也水火相息，革故鼎新顺天应。",
    "火风鼎": "鼎新也取新去故，鼎革之后新气象。",
    "震为雷": "震动也恐惧修省，震动警醒可转吉。",
    "艮为山": "艮止也动静得时，知止不殆有攸往。",
    "风山渐": "渐进也女归吉亨，循序渐进终有成。",
    "雷泽归妹": "归妹征凶位不当，婚嫁之事须慎详。",
    "雷火丰": "丰大也日中则昃，盛极须防衰运来。",
    "火山旅": "旅寄也情有所系，旅居在外慎其行。",
    "巽为风": "巽入也申命行事，柔顺谦逊事皆通。",
    "兑为泽": "兑说也朋友讲习，和悦相处吉无咎。",
    "风水涣": "涣散也离而复合，涣散之际须凝聚。",
    "水泽节": "节制度数议德行，节制有度事可恒。",
    "风泽中孚": "中孚信也豚鱼吉，诚信感格事皆通。",
    "雷山小过": "小过宜小事大凶，小有所过须谨慎。",
    "水火既济": "既济定也刚柔正，成功之后防危乱。",
    "火水未济": "未济穷也征凶吝，事业未成须继续。",
}


# ============================================================================
# 称骨算命（简化版）
# ============================================================================

CHENGGU_YUE = {  # 月两（简化）
    1: 0.6, 2: 0.7, 3: 1.8, 4: 0.9, 5: 0.5, 6: 1.6,
    7: 0.9, 8: 1.5, 9: 1.8, 10: 0.8, 11: 0.9, 12: 0.5,
}

CHENGGU_RI = {   # 日两（简化）
    1: 0.5, 2: 1.0, 3: 0.8, 4: 1.5, 5: 1.6, 6: 1.5,
    7: 0.8, 8: 1.6, 9: 0.8, 10: 1.6, 11: 0.9, 12: 1.7,
    13: 0.8, 14: 1.7, 15: 1.0, 16: 0.8, 17: 0.9, 18: 1.8,
    19: 0.5, 20: 1.5, 21: 1.0, 22: 0.9, 23: 0.8, 24: 0.9,
    25: 1.5, 26: 1.8, 27: 0.7, 28: 0.8, 29: 1.6, 30: 0.6,
    31: 0.8,
}

CHENGGU_SHI = {  # 时两（简化）
    "子": 1.6, "丑": 0.6, "寅": 0.7, "卯": 1.0,
    "辰": 0.9, "巳": 1.6, "午": 1.0, "未": 0.8,
    "申": 0.8, "酉": 0.9, "戌": 0.6, "亥": 0.6,
}

CHENGGU_TIAOWEN = {
    (2.0, 3.0): "一身骨肉最清高，早入黉门姓名标。待看年将三十六，蓝衣脱去换红袍。",
    (3.0, 3.5): "初年运蹇事难谋，渐有财源如水流。到得中年衣食旺，那时名利一齐收。",
    (3.5, 4.0): "平生衣禄是绵长，件件心中自主张。前面风霜多受过，后来必定享安康。",
    (4.0, 4.5): "得宽怀处且宽怀，何用双眉皱不开。若使中年命运济，那时名利一齐来。",
    (4.5, 5.0): "为人心性最聪明，作事轩昂近贵人。衣禄一生天注定，不须劳碌是丰亨。",
    (5.0, 5.5): "走马扬鞭争利名，少年作事费评论。一朝福禄源源至，富贵荣华显六亲。",
    (5.5, 6.0): "细推此格秀而清，必定才高学业成。甲第之中应有分，扬鞭走马显威荣。",
    (6.0, 7.0): "一朝金榜快题名，显祖荣宗立大功。衣食定然原裕足，田园财帛更丰盈。",
    (7.0, 10.0): "命主为官福禄长，得来富贵实非常。名题雁塔传金榜，大显门庭天下扬。",
}


# ============================================================================
# 辅助算法
# ============================================================================

def _safe_mod(a: int, b: int) -> int:
    """安全取模（b为0时返回0）"""
    return a % b if b else 0


def _ganzhi_to_num(gan: str, zhi: str) -> int:
    """干支组合数（简化）"""
    g_num = TIAN_GAN.get(gan, {}).get("num", 0)
    z_num = DI_ZHI.get(zhi, {}).get("num", 0)
    return g_num * 100 + z_num


def _num_to_bagua(num: int) -> str:
    """数转八卦（先天八卦）"""
    n = ((num - 1) % 8) + 1
    return XIANTIAN_BAGUA.get(n, "乾")


def _two_bagua_to_hexagram(shang: str, xia: str) -> str:
    """两个单卦组合成六十四卦名（简化）"""
    hex_map = {
        ("乾", "乾"): "乾为天", ("乾", "兑"): "天泽履", ("乾", "离"): "天火同人",
        ("乾", "震"): "天雷无妄", ("乾", "巽"): "天风姤", ("乾", "坎"): "天水讼",
        ("乾", "艮"): "天山遁", ("乾", "坤"): "天地否",
        ("兑", "乾"): "泽天夬", ("兑", "兑"): "兑为泽", ("兑", "离"): "泽火革",
        ("兑", "震"): "泽雷随", ("兑", "巽"): "泽风大过", ("兑", "坎"): "泽水困",
        ("兑", "艮"): "泽山咸", ("兑", "坤"): "泽地萃",
        ("离", "乾"): "火天大有", ("离", "兑"): "火泽睽", ("离", "离"): "离为火",
        ("离", "震"): "火雷噬嗑", ("离", "巽"): "火风鼎", ("离", "坎"): "火水未济",
        ("离", "艮"): "火山旅", ("离", "坤"): "火地晋",
        ("震", "乾"): "雷天大壮", ("震", "兑"): "雷泽归妹", ("震", "离"): "雷火丰",
        ("震", "震"): "震为雷", ("震", "巽"): "雷风恒", ("震", "坎"): "雷水解",
        ("震", "艮"): "雷山小过", ("震", "坤"): "雷地豫",
        ("巽", "乾"): "风天小畜", ("巽", "兑"): "风泽中孚", ("巽", "离"): "风火家人",
        ("巽", "震"): "风雷益", ("巽", "巽"): "巽为风", ("巽", "坎"): "风水涣",
        ("巽", "艮"): "风山渐", ("巽", "坤"): "风地观",
        ("坎", "乾"): "水天需", ("坎", "兑"): "水泽节", ("坎", "离"): "水火既济",
        ("坎", "震"): "水雷屯", ("坎", "巽"): "水风井", ("坎", "坎"): "坎为水",
        ("坎", "艮"): "水山蹇", ("坎", "坤"): "水地比",
        ("艮", "乾"): "山天大畜", ("艮", "兑"): "山泽损", ("艮", "离"): "山火贲",
        ("艮", "震"): "山雷颐", ("艮", "巽"): "山风蛊", ("艮", "坎"): "山水蒙",
        ("艮", "艮"): "艮为山", ("艮", "坤"): "山地剥",
        ("坤", "乾"): "地天泰", ("坤", "兑"): "地泽临", ("坤", "离"): "地火明夷",
        ("坤", "震"): "地雷复", ("坤", "巽"): "地风升", ("坤", "坎"): "地水师",
        ("坤", "艮"): "地山谦", ("坤", "坤"): "坤为地",
    }
    return hex_map.get((shang, xia), f"{shang}上{xia}下")


# ============================================================================
# 铁板神数引擎
# ============================================================================

class TieBanShuEngine:
    """铁板神数简化引擎"""

    def compute(
        self,
        year_gan: str, year_zhi: str,
        month_gan: str, month_zhi: str,
        day_gan: str, day_zhi: str,
        hour_gan: str, hour_zhi: str,
    ) -> TiebanshuResult:
        """
        根据四柱起数

        简化算法：
          - 天盘 = 年干支数
          - 地盘 = 月日干支组合
          - 人盘 = 时干支数
          - 基础数 = (天盘 × 地盘 + 人盘) % 60 + 1
        """
        # 各盘数
        tian_num = _ganzhi_to_num(year_gan, year_zhi)
        di_num = (_ganzhi_to_num(month_gan, month_zhi) +
                  _ganzhi_to_num(day_gan, day_zhi))
        ren_num = _ganzhi_to_num(hour_gan, hour_zhi)

        # 盘名：用八卦表示
        tian_pan = _num_to_bagua(tian_num)
        di_pan = _num_to_bagua(di_num)
        ren_pan = _num_to_bagua(ren_num)

        # 基础数（用于查条文的起数）
        base_num = (tian_num * 7 + di_num * 3 + ren_num) % 60 + 1

        # 关键起数：生成多个查条文的数
        key_numbers = [
            base_num,
            (base_num + 1000) % 6000 + 1,
            (base_num * 2 + 1001) % 5000 + 1,
            (tian_num + di_num + ren_num) % 60 + 1,
            (tian_num * 3 - ren_num) % 60 + 1 if tian_num > ren_num else (ren_num - tian_num) % 60 + 1,
        ]

        # 查条文（映射到我们的条文库）
        tiaowen: List[str] = []
        seen_keys = set()
        for kn in key_numbers:
            # 将 key number 映射到我们的条文库 keys
            keys = sorted(TIEBAN_TIAOWEN.keys())
            mapped_key = keys[kn % len(keys)]
            if mapped_key not in seen_keys:
                seen_keys.add(mapped_key)
                tiaowen.append(f"【{mapped_key}】{TIEBAN_TIAOWEN[mapped_key]}")
            if len(tiaowen) >= 5:
                break

        # 总结
        good_indicators = sum(1 for k in seen_keys if k < 3000)
        neutral_indicators = sum(1 for k in seen_keys if 3000 <= k < 4000)
        summary_parts = []
        if good_indicators >= 2:
            summary_parts.append("命带贵气，初年有根基")
        if neutral_indicators >= 1:
            summary_parts.append("中晚年运渐丰")
        if good_indicators < 2 and neutral_indicators < 1:
            summary_parts.append("宜守本分，修身养性以增福")
        summary = "；".join(summary_parts) if summary_parts else "命局平稳，后天努力可改运"

        return TiebanshuResult(
            tian_pan=f"天盘：{tian_pan}（数 {tian_num}）",
            di_pan=f"地盘：{di_pan}（数 {di_num}）",
            ren_pan=f"人盘：{ren_pan}（数 {ren_num}）",
            base_num=base_num,
            key_numbers=key_numbers,
            tiaowen=tiaowen,
            summary=summary,
        )


# ============================================================================
# 邵子神数（皇极经世）引擎
# ============================================================================

class ShaoZiShenShuEngine:
    """邵子神数·皇极经世简化引擎"""

    def compute(
        self,
        year_gan: str, year_zhi: str,
        month_gan: str, month_zhi: str,
        day_gan: str, day_zhi: str,
        hour_gan: str, hour_zhi: str,
    ) -> ShaoziResult:
        """
        简化版皇极经世起卦：
          - 元会运世：按年月日时起数
          - 卦象：上下卦由干支数推出
        """
        # 元会运世（简化）
        y_num = _ganzhi_to_num(year_gan, year_zhi)
        m_num = _ganzhi_to_num(month_gan, month_zhi)
        d_num = _ganzhi_to_num(day_gan, day_zhi)
        h_num = _ganzhi_to_num(hour_gan, hour_zhi)

        yuan = (y_num % 12) + 1
        hui = (m_num % 30) + 1
        yun = (d_num % 12) + 1
        shi = (h_num % 30) + 1

        # 起卦：年+月+日 / 8 取下卦，加时 / 8 取上卦
        xia_gua = _num_to_bagua((y_num + m_num + d_num) % 8 + 1)
        shang_gua = _num_to_bagua((y_num + m_num + d_num + h_num) % 8 + 1)
        hexagram = _two_bagua_to_hexagram(shang_gua, xia_gua)

        # 查条文
        tiaowen = [f"【{hexagram}】{SHAOZI_TIAOWEN.get(hexagram, '动静得时，顺势而为')}"]

        # 辅助吉凶评分（简化）
        auspicious = ["乾为天", "坤为地", "地天泰", "水地比", "风火家人", "风山渐", "火天大有"]
        inauspicious = ["天地否", "坎为水", "泽水困", "火水未济", "雷泽归妹", "山地剥"]
        if hexagram in auspicious:
            score = 85
            summary = f"得{hexagram}卦，吉祥亨通，宜把握时机。"
        elif hexagram in inauspicious:
            score = 50
            summary = f"得{hexagram}卦，宜守正避凶，韬光养晦。"
        else:
            score = 70
            summary = f"得{hexagram}卦，平稳中有变，宜顺势而为。"

        return ShaoziResult(
            yuan_hui_yun_shi={"元": yuan, "会": hui, "运": yun, "世": shi},
            huangji_hexagram=f"{shang_gua}（上卦） / {xia_gua}（下卦） → {hexagram}",
            tiaowen=tiaowen,
            total_score=score,
            summary=summary,
        )


# ============================================================================
# 称骨算命引擎
# ============================================================================

class ChengGuEngine:
    """袁天罡称骨算命（简化版）"""

    def compute(
        self,
        month: int, day: int, hour_zhi: str,
    ) -> ChengguResult:
        """
        Args:
            month: 农历月份(1-12)
            day: 农历日(1-31)
            hour_zhi: 时辰地支（子丑寅卯...）
        """
        yue_liang = CHENGGU_YUE.get(month, 0.9)
        ri_liang = CHENGGU_RI.get(day, 0.9)
        shi_liang = CHENGGU_SHI.get(hour_zhi, 0.9)
        total_liang = round(yue_liang + ri_liang + shi_liang, 1)

        # 查称骨歌
        tiaowen = ""
        for (lo, hi), text in CHENGGU_TIAOWEN.items():
            if lo <= total_liang < hi:
                tiaowen = text
                break
        if not tiaowen:
            tiaowen = "一生行事细推详，富贵贫穷有主张。若问平生荣枯事，晚年福禄胜初年。"

        # 解读
        if total_liang < 3.0:
            interpretation = "骨轻，初年辛苦，宜后天努力，修身养性以增福。"
        elif total_liang < 4.5:
            interpretation = "骨格中等，中年渐发，稳扎稳打必有成就。"
        elif total_liang < 6.0:
            interpretation = "骨格清奇，一生衣食丰足，有贵人相助。"
        else:
            interpretation = "骨重命厚，富贵双全之格，但需修福保泰。"

        return ChengguResult(
            total_liang=total_liang,
            yue_liang=yue_liang,
            ri_liang=ri_liang,
            shi_liang=shi_liang,
            tiaowen=tiaowen,
            interpretation=interpretation,
        )


# ============================================================================
# 综合接口
# ============================================================================

class AdvancedShuShuEngine:
    """高级术数综合引擎"""

    def __init__(self):
        self.tieban = TieBanShuEngine()
        self.shaozi = ShaoZiShenShuEngine()
        self.chenggu = ChengGuEngine()

    def compute_all(
        self,
        pillars: Dict[str, str],
        lunar_month: Optional[int] = None,
        lunar_day: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        综合计算

        Args:
            pillars: {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申"}
            lunar_month: 农历月（可选）
            lunar_day: 农历日（可选）
        """
        # 解析四柱
        def _parse_pillar(p: str) -> Tuple[str, str]:
            return (p[0], p[1]) if len(p) >= 2 else ("", "")

        y_g, y_z = _parse_pillar(pillars.get("year", ""))
        m_g, m_z = _parse_pillar(pillars.get("month", ""))
        d_g, d_z = _parse_pillar(pillars.get("day", ""))
        h_g, h_z = _parse_pillar(pillars.get("hour", ""))

        results = {}

        # 铁板神数
        if all([y_g, y_z, m_g, m_z, d_g, d_z, h_g, h_z]):
            results["tieban"] = self.tieban.compute(
                y_g, y_z, m_g, m_z, d_g, d_z, h_g, h_z
            ).to_dict()

            # 邵子神数
            results["shaozi"] = self.shaozi.compute(
                y_g, y_z, m_g, m_z, d_g, d_z, h_g, h_z
            ).to_dict()

        # 称骨算命
        if lunar_month and lunar_day and h_z:
            results["chenggu"] = self.chenggu.compute(
                lunar_month, lunar_day, h_z
            ).to_dict()

        return results
