#!/usr/bin/env python3
"""
divination_engine.py — 五行/干支/十神关系推演引擎 v1.0.0
提供完整的五行生克、天干地支、十神推演与八字分析能力。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

__all__ = [
    "WuxingEngine",
    "TianganEngine",
    "DizhiEngine",
    "ShiganEngine",
    "BaziCalculator",
    "ShiganResult",
    "analyze_relations",
    "find_interactions",
]
__version__ = "1.0.0"


# ============================================================================
# 基础枚举定义
# ============================================================================

class Wuxing(Enum):
    """五行枚举"""
    MU = "木"
    HUO = "火"
    TU = "土"
    JIN = "金"
    SHUI = "水"


class Yinyang(Enum):
    """阴阳枚举"""
    YANG = "阳"  # 阳性
    YIN = "阴"   # 阴性


class ShiganType(Enum):
    """十神类型枚举"""
    BIJIAN = "比肩"           # 同我、同性
    JIECAI = "劫财"            # 同我、异性
    SHISHEN = "食神"           # 我生、同性
    SHANGGUAN = "伤官"         # 我生、异性
    ZHENGCAI = "正财"          # 我克、异性
    PIANCAI = "偏财"           # 我克、同性
    ZHENGGUAN = "正官"         # 克我、异性
    QISHA = "七杀"             # 克我、同性
    ZHENGYIN = "正印"          # 生我、异性
    PIANYIN = "偏印"           # 生我、同性


# ============================================================================
# 五行推演引擎
# ============================================================================

class WuxingEngine:
    """五行推演引擎 — 掌握五行生克乘侮之道

    生：木→火→土→金→水→木
    克：木克土，土克水，水克火，火克金，金克木
    """

    # 五行颜色映射
    COLORS: Dict[str, str] = {
        "木": "\033[32m",  # 绿色
        "火": "\033[31m",  # 红色
        "土": "\033[33m",  # 黄色
        "金": "\033[37m",  # 白色/亮灰
        "水": "\033[34m",  # 蓝色
    }
    COLOR_RESET: str = "\033[0m"
    COLOR_NAMES: Dict[str, str] = {
        "木": "青/绿",
        "火": "赤/红",
        "土": "黄",
        "金": "白",
        "水": "黑/蓝",
    }

    # 五行相生次序
    _GENERATE_ORDER: List[str] = ["木", "火", "土", "金", "水"]
    # 五行相克次序（隔一为克：木克土，土克水，水克火，火克金，金克木）
    _RESTRICT_MAP: Dict[str, str] = {
        "木": "土",
        "土": "水",
        "水": "火",
        "火": "金",
        "金": "木",
    }
    # 反向映射
    _GENERATED_BY_MAP: Dict[str, str] = {
        "火": "木",
        "土": "火",
        "金": "土",
        "水": "金",
        "木": "水",
    }
    _RESTRICTED_BY_MAP: Dict[str, str] = {
        "土": "木",
        "水": "土",
        "火": "水",
        "金": "火",
        "木": "金",
    }

    @classmethod
    def colorize(cls, wuxing: str, text: Optional[str] = None) -> str:
        """使用五行颜色包裹文本"""
        color = cls.COLORS.get(wuxing, "")
        if text is None:
            text = wuxing
        return f"{color}{text}{cls.COLOR_RESET}"

    @classmethod
    def validate(cls, wuxing: str) -> str:
        """校验并返回合法五行名称"""
        if wuxing not in cls._GENERATE_ORDER:
            raise ValueError(f"无效的五行：「{wuxing}」，合法值为：{cls._GENERATE_ORDER}")
        return wuxing

    @classmethod
    def generate(cls, origin: str) -> str:
        """给定一个五行，返回它生的五行（生我→我生）

        Args:
            origin: 起始五行，如 "木"

        Returns:
            它所生的五行，如 "火"
        """
        origin = cls.validate(origin)
        idx = cls._GENERATE_ORDER.index(origin)
        return cls._GENERATE_ORDER[(idx + 1) % 5]

    @classmethod
    def restrict(cls, origin: str) -> str:
        """给定一个五行，返回它克的五行（我克）

        Args:
            origin: 起始五行，如 "木"

        Returns:
            它所克的五行，如 "土"
        """
        origin = cls.validate(origin)
        return cls._RESTRICT_MAP[origin]

    @classmethod
    def generated_by(cls, target: str) -> str:
        """给定一个五行，返回生它的五行（生我）

        Args:
            target: 目标五行，如 "火"

        Returns:
            生它的五行，如 "木"
        """
        target = cls.validate(target)
        return cls._GENERATED_BY_MAP[target]

    @classmethod
    def restricted_by(cls, target: str) -> str:
        """给定一个五行，返回克它的五行（克我）

        Args:
            target: 目标五行，如 "土"

        Returns:
            克它的五行，如 "木"
        """
        target = cls.validate(target)
        return cls._RESTRICTED_BY_MAP[target]

    @classmethod
    def over_restrict(cls, origin: str) -> str:
        """相乘 — 过克（克者太强，被克者太弱导致的过度克制）

        相乘的次序与相克相同，但为病理性的过度克制。
        """
        return cls.restrict(origin)

    @classmethod
    def reverse_restrict(cls, origin: str) -> str:
        """相侮 — 反克（被克者反制克者）

        相侮的次序与相克相反，即：
        土侮木，水侮土，火侮水，金侮火，木侮金
        """
        origin = cls.validate(origin)
        reverse_map = {v: k for k, v in cls._RESTRICT_MAP.items()}
        return reverse_map[origin]

    @classmethod
    def chain_generate(cls, origin: str, depth: int) -> List[str]:
        """生链深度遍历 — 从我生开始，连续生到指定深度

        Args:
            origin: 起始五行
            depth: 遍历深度（含起点）

        Returns:
            生链列表，如 chain_generate("木", 5) → ["木","火","土","金","水"]

        Examples:
            >>> WuxingEngine.chain_generate("木", 3)
            ['木', '火', '土']
        """
        origin = cls.validate(origin)
        result = [origin]
        current = origin
        for _ in range(depth - 1):
            current = cls.generate(current)
            result.append(current)
        return result

    @classmethod
    def chain_restrict(cls, origin: str, depth: int) -> List[str]:
        """克链深度遍历 — 从我克开始，连续克到指定深度

        Args:
            origin: 起始五行
            depth: 遍历深度（含起点）

        Returns:
            克链列表

        Examples:
            >>> WuxingEngine.chain_restrict("木", 5)
            ['木', '土', '水', '火', '金']
        """
        origin = cls.validate(origin)
        result = [origin]
        current = origin
        for _ in range(depth - 1):
            current = cls.restrict(current)
            result.append(current)
        return result

    @classmethod
    def summary(cls) -> Dict[str, Any]:
        """返回五行系统摘要"""
        return {
            "elements": cls._GENERATE_ORDER,
            "colors": dict(cls.COLOR_NAMES),
            "generate": "木→火→土→金→水→木",
            "restrict": "木克土→土克水→水克火→火克金→金克木",
        }


# ============================================================================
# 天干推演引擎
# ============================================================================

@dataclass
class _TianganInfo:
    """天干基础信息"""
    name: str
    wuxing: str
    yinyang: Yinyang
    direction: str


class TianganEngine:
    """天干推演引擎 — 十天干之阴阳五行相合相克"""

    # 十天干列表
    TIANGAN: List[str] = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

    # 天干详细信息
    _INFO: Dict[str, _TianganInfo] = {
        "甲": _TianganInfo("甲", "木", Yinyang.YANG, "东"),
        "乙": _TianganInfo("乙", "木", Yinyang.YIN, "东"),
        "丙": _TianganInfo("丙", "火", Yinyang.YANG, "南"),
        "丁": _TianganInfo("丁", "火", Yinyang.YIN, "南"),
        "戊": _TianganInfo("戊", "土", Yinyang.YANG, "中"),
        "己": _TianganInfo("己", "土", Yinyang.YIN, "中"),
        "庚": _TianganInfo("庚", "金", Yinyang.YANG, "西"),
        "辛": _TianganInfo("辛", "金", Yinyang.YIN, "西"),
        "壬": _TianganInfo("壬", "水", Yinyang.YANG, "北"),
        "癸": _TianganInfo("癸", "水", Yinyang.YIN, "北"),
    }

    # 天干五合：合化后的天干五行映射
    _WUHE_MAP: Dict[str, Tuple[str, str, str]] = {
        # 甲己合土：合化后五行→土
        "甲": ("己", "土", "甲己合土"),
        "己": ("甲", "土", "甲己合土"),
        # 乙庚合金
        "乙": ("庚", "金", "乙庚合金"),
        "庚": ("乙", "金", "乙庚合金"),
        # 丙辛合水
        "丙": ("辛", "水", "丙辛合水"),
        "辛": ("丙", "水", "丙辛合水"),
        # 丁壬合木
        "丁": ("壬", "木", "丁壬合木"),
        "壬": ("丁", "木", "丁壬合木"),
        # 戊癸合火
        "戊": ("癸", "火", "戊癸合火"),
        "癸": ("戊", "火", "戊癸合火"),
    }

    # 天干相克：依五行生克而来（同五行再按阴阳论）
    # 阳克阳、阴克阴为重克（同性相克），阳克阴/阴克阳为轻克
    # 木克土：甲乙克戊己 → 甲克戊(阳克阳)，乙克己(阴克阴)
    _RESTRICT_RELATION: Dict[str, List[Tuple[str, str]]] = {
        "甲": [("戊", "阳木克阳土（重克）"), ("己", "阳木克阴土（轻克）")],
        "乙": [("己", "阴木克阴土（重克）"), ("戊", "阴木克阳土（轻克）")],
        "丙": [("庚", "阳火克阳金（重克）"), ("辛", "阳火克阴金（轻克）")],
        "丁": [("辛", "阴火克阴金（重克）"), ("庚", "阴火克阳金（轻克）")],
        "戊": [("壬", "阳土克阳水（重克）"), ("癸", "阳土克阴水（轻克）")],
        "己": [("癸", "阴土克阴水（重克）"), ("壬", "阴土克阳水（轻克）")],
        "庚": [("甲", "阳金克阳木（重克）"), ("乙", "阳金克阴木（轻克）")],
        "辛": [("乙", "阴金克阴木（重克）"), ("甲", "阴金克阳木（轻克）")],
        "壬": [("丙", "阳水克阳火（重克）"), ("丁", "阳水克阴火（轻克）")],
        "癸": [("丁", "阴水克阴火（重克）"), ("丙", "阴水克阳火（轻克）")],
    }

    @classmethod
    def validate(cls, tiangan: str) -> str:
        """校验天干有效性"""
        if tiangan not in cls.TIANGAN:
            raise ValueError(f"无效的天干：「{tiangan}」，合法值为：{cls.TIANGAN}")
        return tiangan

    @classmethod
    def wuxing_of(cls, tiangan: str) -> str:
        """返回天干的五行

        Args:
            tiangan: 天干名称

        Returns:
            五行名称

        Examples:
            >>> TianganEngine.wuxing_of("甲")
            '木'
        """
        return cls._INFO[cls.validate(tiangan)].wuxing

    @classmethod
    def yinyang_of(cls, tiangan: str) -> Yinyang:
        """返回天干的阴阳属性

        Args:
            tiangan: 天干名称

        Returns:
            Yinyang 枚举值
        """
        return cls._INFO[cls.validate(tiangan)].yinyang

    @classmethod
    def wuhe(cls, tiangan: str) -> Optional[Dict[str, str]]:
        """天干五合 — 返回合化的天干和五行

        Args:
            tiangan: 天干名称

        Returns:
            包含 partner（合的对象）、wuxing（合化五行）、description 的字典
            若该天干无合，返回 None

        Examples:
            >>> TianganEngine.wuhe("甲")
            {'partner': '己', 'wuxing': '土', 'description': '甲己合土'}
        """
        cls.validate(tiangan)
        if tiangan not in cls._WUHE_MAP:
            return None
        partner, wuxing, desc = cls._WUHE_MAP[tiangan]
        return {"partner": partner, "wuxing": wuxing, "description": desc}

    @classmethod
    def restrict(cls, tiangan: str) -> List[Dict[str, str]]:
        """天干相克关系 — 返回该天干所克的目标

        Args:
            tiangan: 天干名称

        Returns:
            被克目标列表，每项含 target 和 description
        """
        cls.validate(tiangan)
        return [
            {"target": target, "description": desc}
            for target, desc in cls._RESTRICT_RELATION.get(tiangan, [])
        ]

    @classmethod
    def direction_of(cls, tiangan: str) -> str:
        """天干方位

        Args:
            tiangan: 天干名称

        Returns:
            方位（东/南/中/西/北）
        """
        return cls._INFO[cls.validate(tiangan)].direction

    @classmethod
    def summary(cls) -> Dict[str, Any]:
        """天干系统摘要"""
        return {
            "tiangan": cls.TIANGAN,
            "mapping": {
                tg: {
                    "wuxing": cls.wuxing_of(tg),
                    "yinyang": cls.yinyang_of(tg).value,
                    "direction": cls.direction_of(tg),
                }
                for tg in cls.TIANGAN
            },
            "wuhe": "甲己合土 / 乙庚合金 / 丙辛合水 / 丁壬合木 / 戊癸合火",
        }


# ============================================================================
# 地支推演引擎
# ============================================================================

@dataclass
class _DizhiInfo:
    """地支基础信息"""
    name: str
    wuxing: str
    yinyang: Yinyang
    direction: str
    month: int            # 农历月份序号
    month_name: str       # 月份名称
    hour_range: str       # 时辰范围
    hour_name: str        # 时辰名称
    zodiac: str           # 生肖
    canggan_main: str     # 本气（藏干主气）
    canggan_mid: Optional[str] = None   # 中气
    canggan_residual: Optional[str] = None  # 余气


class DizhiEngine:
    """地支推演引擎 — 十二地支藏干、合冲害破刑之推演"""

    # 十二地支列表
    DIZHI: List[str] = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    # 地支详细信息
    _INFO: Dict[str, _DizhiInfo] = {
        "子": _DizhiInfo(
            "子", "水", Yinyang.YANG, "北", 11, "十一月",
            "23:00-01:00", "子时", "鼠",
            canggan_main="癸",
        ),
        "丑": _DizhiInfo(
            "丑", "土", Yinyang.YIN, "东北", 12, "十二月",
            "01:00-03:00", "丑时", "牛",
            canggan_main="己", canggan_mid="癸", canggan_residual="辛",
        ),
        "寅": _DizhiInfo(
            "寅", "木", Yinyang.YANG, "东北", 1, "正月",
            "03:00-05:00", "寅时", "虎",
            canggan_main="甲", canggan_mid="丙", canggan_residual="戊",
        ),
        "卯": _DizhiInfo(
            "卯", "木", Yinyang.YIN, "东", 2, "二月",
            "05:00-07:00", "卯时", "兔",
            canggan_main="乙",
        ),
        "辰": _DizhiInfo(
            "辰", "土", Yinyang.YANG, "东南", 3, "三月",
            "07:00-09:00", "辰时", "龙",
            canggan_main="戊", canggan_mid="乙", canggan_residual="癸",
        ),
        "巳": _DizhiInfo(
            "巳", "火", Yinyang.YIN, "东南", 4, "四月",
            "09:00-11:00", "巳时", "蛇",
            canggan_main="丙", canggan_mid="庚", canggan_residual="戊",
        ),
        "午": _DizhiInfo(
            "午", "火", Yinyang.YANG, "南", 5, "五月",
            "11:00-13:00", "午时", "马",
            canggan_main="丁", canggan_mid="己",
        ),
        "未": _DizhiInfo(
            "未", "土", Yinyang.YIN, "西南", 6, "六月",
            "13:00-15:00", "未时", "羊",
            canggan_main="己", canggan_mid="丁", canggan_residual="乙",
        ),
        "申": _DizhiInfo(
            "申", "金", Yinyang.YANG, "西南", 7, "七月",
            "15:00-17:00", "申时", "猴",
            canggan_main="庚", canggan_mid="壬", canggan_residual="戊",
        ),
        "酉": _DizhiInfo(
            "酉", "金", Yinyang.YIN, "西", 8, "八月",
            "17:00-19:00", "酉时", "鸡",
            canggan_main="辛",
        ),
        "戌": _DizhiInfo(
            "戌", "土", Yinyang.YANG, "西北", 9, "九月",
            "19:00-21:00", "戌时", "狗",
            canggan_main="戊", canggan_mid="辛", canggan_residual="丁",
        ),
        "亥": _DizhiInfo(
            "亥", "水", Yinyang.YIN, "西北", 10, "十月",
            "21:00-23:00", "亥时", "猪",
            canggan_main="壬", canggan_mid="甲",
        ),
    }

    # 地支六合：合局五行
    _LIUHE_MAP: Dict[str, Tuple[str, str]] = {
        "子": ("丑", "土"),  "丑": ("子", "土"),
        "寅": ("亥", "木"),  "亥": ("寅", "木"),
        "卯": ("戌", "火"),  "戌": ("卯", "火"),
        "辰": ("酉", "金"),  "酉": ("辰", "金"),
        "巳": ("申", "水"),  "申": ("巳", "水"),
        "午": ("未", "火"),  "未": ("午", "火"),
    }

    # 地支三合局
    _SANHE_GROUPS: List[Tuple[str, str, str, str]] = [
        ("申", "子", "辰", "水"),   # 申子辰合水局
        ("亥", "卯", "未", "木"),   # 亥卯未合木局
        ("寅", "午", "戌", "火"),   # 寅午戌合火局
        ("巳", "酉", "丑", "金"),   # 巳酉丑合金局
    ]

    # 地支三会局
    _SANHUI_GROUPS: List[Tuple[str, str, str, str]] = [
        ("寅", "卯", "辰", "木"),   # 寅卯辰会东方木
        ("巳", "午", "未", "火"),   # 巳午未会南方火
        ("申", "酉", "戌", "金"),   # 申酉戌会西方金
        ("亥", "子", "丑", "水"),   # 亥子丑会北方水
    ]

    # 六冲
    _LIUCHONG_MAP: Dict[str, str] = {
        "子": "午", "午": "子",
        "丑": "未", "未": "丑",
        "寅": "申", "申": "寅",
        "卯": "酉", "酉": "卯",
        "辰": "戌", "戌": "辰",
        "巳": "亥", "亥": "巳",
    }

    # 六害
    _LIUHAI_MAP: Dict[str, str] = {
        "子": "未", "未": "子",
        "丑": "午", "午": "丑",
        "寅": "巳", "巳": "寅",
        "卯": "辰", "辰": "卯",
        "申": "亥", "亥": "申",
        "酉": "戌", "戌": "酉",
    }

    # 六破
    _LIUPO_MAP: Dict[str, str] = {
        "子": "酉", "酉": "子",
        "寅": "亥", "亥": "寅",
        "辰": "丑", "丑": "辰",
        "午": "卯", "卯": "午",
        "申": "巳", "巳": "申",
        "戌": "未", "未": "戌",
    }

    # 相刑
    _XIANGXING_GROUPS: Dict[str, str] = {
        # 无恩之刑：寅刑巳，巳刑申，申刑寅
        "寅": "巳", "巳": "申", "申": "寅",
        # 恃势之刑：丑刑戌，戌刑未，未刑丑
        "丑": "戌", "戌": "未", "未": "丑",
        # 无礼之刑：子刑卯，卯刑子
        "子": "卯", "卯": "子",
    }
    # 自刑
    _ZIXING: Set[str] = {"辰", "午", "酉", "亥"}

    @classmethod
    def validate(cls, dizhi: str) -> str:
        """校验地支有效性"""
        if dizhi not in cls.DIZHI:
            raise ValueError(f"无效的地支：「{dizhi}」，合法值为：{cls.DIZHI}")
        return dizhi

    @classmethod
    def wuxing_of(cls, dizhi: str) -> str:
        """返回地支的五行"""
        return cls._INFO[cls.validate(dizhi)].wuxing

    @classmethod
    def yinyang_of(cls, dizhi: str) -> Yinyang:
        """返回地支的阴阳"""
        return cls._INFO[cls.validate(dizhi)].yinyang

    @classmethod
    def canggan(cls, dizhi: str) -> Dict[str, Any]:
        """地支藏干 — 返回本气、中气、余气

        Args:
            dizhi: 地支名称

        Returns:
            藏干字典，含 main/mid/residual/list
        """
        info = cls._INFO[cls.validate(dizhi)]
        result: Dict[str, Any] = {"main": info.canggan_main, "mid": info.canggan_mid,
                                   "residual": info.canggan_residual}
        result["list"] = [g for g in [info.canggan_main, info.canggan_mid, info.canggan_residual] if g is not None]
        return result

    @classmethod
    def liuhe(cls, dizhi: str) -> Optional[Dict[str, str]]:
        """地支六合 — 返回合局对象和所化五行

        Args:
            dizhi: 地支名称

        Returns:
            含 partner 和 wuxing 的字典
        """
        cls.validate(dizhi)
        pair = cls._LIUHE_MAP.get(dizhi)
        if pair is None:
            return None
        return {"partner": pair[0], "wuxing": pair[1],
                "description": f"{dizhi}{pair[0]}合{pair[1]}"}

    @classmethod
    def sanhe(cls, dizhi: str) -> Optional[Dict[str, Any]]:
        """地支三合局

        Args:
            dizhi: 地支名称

        Returns:
            含 members 和 wuxing 的字典，或 None
        """
        cls.validate(dizhi)
        for a, b, c, w in cls._SANHE_GROUPS:
            if dizhi in (a, b, c):
                return {
                    "members": [a, b, c],
                    "wuxing": w,
                    "description": f"{a}{b}{c}合{w}局",
                }
        return None

    @classmethod
    def sanhui(cls, dizhi: str) -> Optional[Dict[str, Any]]:
        """地支三会局

        Args:
            dizhi: 地支名称

        Returns:
            含 members 和 wuxing 的字典，或 None
        """
        cls.validate(dizhi)
        for a, b, c, w in cls._SANHUI_GROUPS:
            if dizhi in (a, b, c):
                direction = {"木": "东方", "火": "南方", "金": "西方", "水": "北方"}.get(w, "")
                return {
                    "members": [a, b, c],
                    "wuxing": w,
                    "description": f"{a}{b}{c}会{direction}{w}",
                }
        return None

    @classmethod
    def liuchong(cls, dizhi: str) -> Optional[Dict[str, str]]:
        """六冲"""
        cls.validate(dizhi)
        target = cls._LIUCHONG_MAP.get(dizhi)
        if target is None:
            return None
        return {
            "target": target,
            "description": f"{dizhi}{target}相冲（{cls._INFO[dizhi].wuxing}冲{cls._INFO[target].wuxing}）",
        }

    @classmethod
    def liuhai(cls, dizhi: str) -> Optional[Dict[str, str]]:
        """六害"""
        cls.validate(dizhi)
        target = cls._LIUHAI_MAP.get(dizhi)
        if target is None:
            return None
        return {
            "target": target,
            "description": f"{dizhi}{target}相害",
        }

    @classmethod
    def liupo(cls, dizhi: str) -> Optional[Dict[str, str]]:
        """六破"""
        cls.validate(dizhi)
        target = cls._LIUPO_MAP.get(dizhi)
        if target is None:
            return None
        return {
            "target": target,
            "description": f"{dizhi}{target}相破",
        }

    @classmethod
    def xiangxing(cls, dizhi: str) -> List[Dict[str, str]]:
        """相刑 — 返回所有相刑关系（含被刑与自刑）

        Returns:
            相刑目标列表，每项含 target 和 description
        """
        cls.validate(dizhi)
        results: List[Dict[str, str]] = []

        # 主动刑
        target = cls._XIANGXING_GROUPS.get(dizhi)
        if target:
            # 确定刑的名称
            if dizhi in ("寅", "巳", "申"):
                xing_name = "无恩之刑"
            elif dizhi in ("丑", "戌", "未"):
                xing_name = "恃势之刑"
            elif dizhi in ("子", "卯"):
                xing_name = "无礼之刑"
            else:
                xing_name = "相刑"
            results.append({
                "target": target,
                "description": f"{dizhi}刑{target}（{xing_name}）",
            })

        # 自刑
        if dizhi in cls._ZIXING:
            results.append({
                "target": dizhi,
                "description": f"{dizhi}{dizhi}自刑",
            })

        # 被刑（别人刑我）
        for k, v in cls._XIANGXING_GROUPS.items():
            if v == dizhi and k != dizhi:
                results.append({
                    "target": k,
                    "description": f"{k}刑{dizhi}（被刑）",
                })

        return results

    @classmethod
    def month_of(cls, dizhi: str) -> Dict[str, Any]:
        """地支对应月份

        Returns:
            含 month（数字序号）和 name（名称）的字典
        """
        info = cls._INFO[cls.validate(dizhi)]
        return {"month": info.month, "name": info.month_name}

    @classmethod
    def hour_of(cls, dizhi: str) -> Dict[str, str]:
        """地支对应时辰

        Returns:
            含 range（时间段）和 name（时辰名称）的字典
        """
        info = cls._INFO[cls.validate(dizhi)]
        return {"range": info.hour_range, "name": info.hour_name}

    @classmethod
    def direction_of(cls, dizhi: str) -> str:
        """地支方位"""
        return cls._INFO[cls.validate(dizhi)].direction

    @classmethod
    def zodiac_of(cls, dizhi: str) -> str:
        """生肖对应"""
        return cls._INFO[cls.validate(dizhi)].zodiac

    @classmethod
    def summary(cls) -> Dict[str, Any]:
        """地支系统摘要"""
        return {
            "dizhi": cls.DIZHI,
            "liuhe": "子丑合土 / 寅亥合木 / 卯戌合火 / 辰酉合金 / 巳申合水 / 午未合火",
            "sanhe": "申子辰水 / 亥卯未木 / 寅午戌火 / 巳酉丑金",
            "sanhui": "寅卯辰东方木 / 巳午未南方火 / 申酉戌西方金 / 亥子丑北方水",
            "liuchong": "子午/丑未/寅申/卯酉/辰戌/巳亥",
            "liuhai": "子未/丑午/寅巳/卯辰/申亥/酉戌",
            "liupo": "子酉/寅亥/辰丑/午卯/申巳/戌未",
            "xiangxing": "寅巳申(无恩) / 丑戌未(恃势) / 子卯(无礼) / 辰午酉亥(自刑)",
        }


# ============================================================================
# 十神推演引擎
# ============================================================================

@dataclass
class ShiganResult:
    """单个十神推演结果"""
    day_gan: str           # 日干
    target_gan: str        # 目标天干
    shigan: ShiganType     # 十神类型
    description: str       # 简要说明
    wuxing_relation: str   # 五行关系


class ShiganEngine:
    """十神推演引擎 — 以日干为核心推演十神关系

    核心规则（以日干「我」为参照）：
    - 克我者为官杀   ── 阴阳异性→正官，同性→七杀
    - 生我者为印绶   ── 阴阳异性→正印，同性→偏印
    - 我克者为财星   ── 阴阳异性→正财，同性→偏财
    - 同我者为比劫   ── 阴阳同性→比肩，异性→劫财
    - 我生者为食伤   ── 阴阳同性→食神，异性→伤官
    """

    # 十神善恶分类
    _CLASSIFICATION: Dict[ShiganType, str] = {
        ShiganType.BIJIAN: "中性",
        ShiganType.JIECAI: "凶神",
        ShiganType.SHISHEN: "善神",
        ShiganType.SHANGGUAN: "凶神",
        ShiganType.ZHENGCAI: "善神",
        ShiganType.PIANCAI: "中性",
        ShiganType.ZHENGGUAN: "善神",
        ShiganType.QISHA: "凶神",
        ShiganType.ZHENGYIN: "善神",
        ShiganType.PIANYIN: "凶神",
    }

    # 十神之间的生克关系
    _INTERACTION_TABLE: Dict[str, Dict[str, Optional[str]]] = {
        # 比肩：生食伤，克财星，被官杀克，被印绶生
        "比肩": {"比肩": None, "劫财": None, "食神": "生", "伤官": "生",
                 "正财": "克", "偏财": "克", "正官": "被克", "七杀": "被克",
                 "正印": "被生", "偏印": "被生"},
        "劫财": {"比肩": None, "劫财": None, "食神": "生", "伤官": "生",
                 "正财": "克", "偏财": "克", "正官": "被克", "七杀": "被克",
                 "正印": "被生", "偏印": "被生"},
        "食神": {"比肩": "被生", "劫财": "被生", "食神": None, "伤官": None,
                 "正财": "生", "偏财": "生", "正官": "被克", "七杀": "被克",
                 "正印": "克", "偏印": "克"},
        "伤官": {"比肩": "被生", "劫财": "被生", "食神": None, "伤官": None,
                 "正财": "生", "偏财": "生", "正官": "被克", "七杀": "被克",
                 "正印": "克", "偏印": "克"},
        "正财": {"比肩": "被克", "劫财": "被克", "食神": "被生", "伤官": "被生",
                 "正财": None, "偏财": None, "正官": "生", "七杀": "生",
                 "正印": "被克", "偏印": "被克"},
        "偏财": {"比肩": "被克", "劫财": "被克", "食神": "被生", "伤官": "被生",
                 "正财": None, "偏财": None, "正官": "生", "七杀": "生",
                 "正印": "被克", "偏印": "被克"},
        "正官": {"比肩": "克", "劫财": "克", "食神": "被生", "伤官": "被生",
                 "正财": "被生", "偏财": "被生", "正官": None, "七杀": None,
                 "正印": "生", "偏印": "生"},
        "七杀": {"比肩": "克", "劫财": "克", "食神": "被生", "伤官": "被生",
                 "正财": "被生", "偏财": "被生", "正官": None, "七杀": None,
                 "正印": "生", "偏印": "生"},
        "正印": {"比肩": "生", "劫财": "生", "食神": "被克", "伤官": "被克",
                 "正财": "克", "偏财": "克", "正官": "被生", "七杀": "被生",
                 "正印": None, "偏印": None},
        "偏印": {"比肩": "生", "劫财": "生", "食神": "被克", "伤官": "被克",
                 "正财": "克", "偏财": "克", "正官": "被生", "七杀": "被生",
                 "正印": None, "偏印": None},
    }

    @classmethod
    def compute(cls, day_gan: str, target_gan: str) -> ShiganResult:
        """根据日干推演指定天干的十神

        Args:
            day_gan: 日干（参照基准，"我"）
            target_gan: 目标天干

        Returns:
            ShiganResult 十神结果
        """
        TianganEngine.validate(day_gan)
        TianganEngine.validate(target_gan)

        my_wx = TianganEngine.wuxing_of(day_gan)
        tg_wx = TianganEngine.wuxing_of(target_gan)
        my_yy = TianganEngine.yinyang_of(day_gan)
        tg_yy = TianganEngine.yinyang_of(target_gan)

        # 同五行 → 比劫（同我为比劫）
        if my_wx == tg_wx:
            if my_yy == tg_yy:
                shigan = ShiganType.BIJIAN
                desc = f"比肩（{day_gan}{target_gan}同五行同性）"
            else:
                shigan = ShiganType.JIECAI
                desc = f"劫财（{day_gan}{target_gan}同五行异性）"
            return ShiganResult(
                day_gan=day_gan, target_gan=target_gan,
                shigan=shigan, description=desc,
                wuxing_relation=f"{my_wx}见{my_wx}（同我）",
            )

        # 生我 → 印绶（生我者为印绶）
        if WuxingEngine.generated_by(my_wx) == tg_wx:
            if my_yy != tg_yy:
                shigan = ShiganType.ZHENGYIN
                desc = f"正印（{target_gan}{tg_wx}生{day_gan}{my_wx}，阴阳异性）"
            else:
                shigan = ShiganType.PIANYIN
                desc = f"偏印（{target_gan}{tg_wx}生{day_gan}{my_wx}，阴阳同性）"
            return ShiganResult(
                day_gan=day_gan, target_gan=target_gan,
                shigan=shigan, description=desc,
                wuxing_relation=f"{tg_wx}生{my_wx}（生我）",
            )

        # 克我 → 官杀（克我者为官杀）
        if WuxingEngine.restricted_by(my_wx) == tg_wx:
            if my_yy != tg_yy:
                shigan = ShiganType.ZHENGGUAN
                desc = f"正官（{target_gan}{tg_wx}克{day_gan}{my_wx}，阴阳异性）"
            else:
                shigan = ShiganType.QISHA
                desc = f"七杀（{target_gan}{tg_wx}克{day_gan}{my_wx}，阴阳同性）"
            return ShiganResult(
                day_gan=day_gan, target_gan=target_gan,
                shigan=shigan, description=desc,
                wuxing_relation=f"{tg_wx}克{my_wx}（克我）",
            )

        # 我生 → 食伤（我生者为食伤）
        if WuxingEngine.generate(my_wx) == tg_wx:
            if my_yy == tg_yy:
                shigan = ShiganType.SHISHEN
                desc = f"食神（{day_gan}{my_wx}生{target_gan}{tg_wx}，阴阳同性）"
            else:
                shigan = ShiganType.SHANGGUAN
                desc = f"伤官（{day_gan}{my_wx}生{target_gan}{tg_wx}，阴阳异性）"
            return ShiganResult(
                day_gan=day_gan, target_gan=target_gan,
                shigan=shigan, description=desc,
                wuxing_relation=f"{my_wx}生{tg_wx}（我生）",
            )

        # 我克 → 财星（我克者为财星）
        if WuxingEngine.restrict(my_wx) == tg_wx:
            if my_yy != tg_yy:
                shigan = ShiganType.ZHENGCAI
                desc = f"正财（{day_gan}{my_wx}克{target_gan}{tg_wx}，阴阳异性）"
            else:
                shigan = ShiganType.PIANCAI
                desc = f"偏财（{day_gan}{my_wx}克{target_gan}{tg_wx}，阴阳同性）"
            return ShiganResult(
                day_gan=day_gan, target_gan=target_gan,
                shigan=shigan, description=desc,
                wuxing_relation=f"{my_wx}克{tg_wx}（我克）",
            )

        # fallback（不应到达此处）
        return ShiganResult(
            day_gan=day_gan, target_gan=target_gan,
            shigan=ShiganType.BIJIAN, description="未知",
            wuxing_relation="未知",
        )

    @classmethod
    def compute_for_bazi(
        cls, day_gan: str, all_gans: List[str]
    ) -> List[ShiganResult]:
        """为八字中所有天干计算十神

        Args:
            day_gan: 日干
            all_gans: 所有相关天干列表（含日干自身）

        Returns:
            十神结果列表
        """
        return [cls.compute(day_gan, tg) for tg in all_gans]

    @classmethod
    def classify(cls, shigan: ShiganType) -> str:
        """分类为善神/凶神/中性

        Args:
            shigan: 十神类型

        Returns:
            分类标签
        """
        return cls._CLASSIFICATION.get(shigan, "未知")

    @classmethod
    def interaction(cls, shigan_a: ShiganType, shigan_b: ShiganType) -> Optional[str]:
        """十神之间的生克关系

        Args:
            shigan_a: 十神A
            shigan_b: 十神B

        Returns:
            关系描述：'生' / '克' / '被生' / '被克' / None（无直接关系）
        """
        name_a = shigan_a.value
        name_b = shigan_b.value
        table = cls._INTERACTION_TABLE.get(name_a, {})
        return table.get(name_b)

    @classmethod
    def summary(cls) -> Dict[str, Any]:
        """十神系统摘要"""
        return {
            "types": [st.value for st in ShiganType],
            "rules": {
                "克我": {"异性→正官": ShiganType.ZHENGGUAN.value, "同性→七杀": ShiganType.QISHA.value},
                "生我": {"异性→正印": ShiganType.ZHENGYIN.value, "同性→偏印": ShiganType.PIANYIN.value},
                "我克": {"异性→正财": ShiganType.ZHENGCAI.value, "同性→偏财": ShiganType.PIANCAI.value},
                "同我": {"同性→比肩": ShiganType.BIJIAN.value, "异性→劫财": ShiganType.JIECAI.value},
                "我生": {"同性→食神": ShiganType.SHISHEN.value, "异性→伤官": ShiganType.SHANGGUAN.value},
            },
            "classification": {st.value: cls.classify(st) for st in ShiganType},
        }


# ============================================================================
# 八字计算器
# ============================================================================

class BaziCalculator:
    """八字计算器 — 六十甲子及相关计算"""

    # 六十甲子表
    _JIAZI_CACHE: Optional[List[Tuple[int, str]]] = None

    @classmethod
    def jiazi_table(cls) -> List[Tuple[int, str]]:
        """返回完整的60甲子编号表

        Returns:
            [(序号, 干支组合), ...] 列表，序号从1开始

        规则：天干循环10次 × 地支循环12次 = 60种组合
        阳配阳、阴配阴（奇数位天干配奇数位地支，偶数位天干配偶数位地支）
        """
        if cls._JIAZI_CACHE is not None:
            return cls._JIAZI_CACHE

        table: List[Tuple[int, str]] = []
        for i in range(60):
            gan = TianganEngine.TIANGAN[i % 10]
            zhi = DizhiEngine.DIZHI[i % 12]
            table.append((i + 1, gan + zhi))
        cls._JIAZI_CACHE = table
        return table

    @classmethod
    def get_jiazi(cls, index: int) -> Optional[str]:
        """根据序号（1-60）获取甲子组合

        Args:
            index: 1-60 的序号

        Returns:
            干支组合字符串，如 "甲子"
        """
        if index < 1 or index > 60:
            return None
        return cls.jiazi_table()[index - 1][1]

    @classmethod
    def get_index(cls, jiazi: str) -> Optional[int]:
        """根据干支组合获取序号

        Args:
            jiazi: 如 "甲子"

        Returns:
            1-60 的序号，未找到返回 None
        """
        for idx, name in cls.jiazi_table():
            if name == jiazi:
                return idx
        return None

    @classmethod
    def is_valid_combination(cls, gan: str, zhi: str) -> bool:
        """验证天干地支组合是否合法（阳配阳、阴配阴）

        甲丙戊庚壬为阳天干，配子寅辰午申戌为阳地支
        乙丁己辛癸为阴天干，配丑卯巳未酉亥为阴地支
        """
        if gan not in TianganEngine.TIANGAN or zhi not in DizhiEngine.DIZHI:
            return False
        gan_idx = TianganEngine.TIANGAN.index(gan)
        zhi_idx = DizhiEngine.DIZHI.index(zhi)
        # 同为偶数或同为奇数即为合法
        return (gan_idx % 2) == (zhi_idx % 2)

    @classmethod
    def summary(cls) -> Dict[str, Any]:
        """八字计算器摘要"""
        table = cls.jiazi_table()
        return {
            "total": 60,
            "cycle": [f"{i}:{name}" for i, name in table[:5]] + ["..."] +
                     [f"{i}:{name}" for i, name in table[-5:]],
            "rule": "天干10 × 地支12 = 60组合，阳配阳、阴配阴",
        }


# ============================================================================
# 综合推理函数
# ============================================================================

def analyze_relations(
    day_gan: str,
    heavenly_stems: List[str],
    earthly_branches: List[str],
) -> Dict[str, Any]:
    """综合分析八字中的十神关系

    Args:
        day_gan: 日干
        heavenly_stems: 四柱天干列表（年干、月干、日干、时干）
        earthly_branches: 四柱地支列表（年支、月支、日支、时支）

    Returns:
        综合分析结果字典
    """
    TianganEngine.validate(day_gan)

    # 计算天干十神
    gan_shigan = ShiganEngine.compute_for_bazi(day_gan, heavenly_stems)

    # 地支藏干十神分析
    branch_shigan: List[Dict[str, Any]] = []
    for zhi in earthly_branches:
        cg = DizhiEngine.canggan(zhi)
        branch_entry: Dict[str, Any] = {
            "branch": zhi,
            "wuxing": DizhiEngine.wuxing_of(zhi),
            "canggan": {},
        }
        for level, gan in [("main", cg["main"]), ("mid", cg["mid"]), ("residual", cg["residual"])]:
            if gan is None:
                continue
            sr = ShiganEngine.compute(day_gan, gan)
            branch_entry["canggan"][level] = {
                "gan": gan,
                "shigan": sr.shigan.value,
                "classification": ShiganEngine.classify(sr.shigan),
                "description": sr.description,
            }
        branch_shigan.append(branch_entry)

    # 地支间互动关系
    interactions = find_interactions(earthly_branches)

    # 统计十神分布
    shigan_counts: Dict[str, int] = {}
    for sr in gan_shigan:
        key = sr.shigan.value
        shigan_counts[key] = shigan_counts.get(key, 0) + 1
    # 也统计藏干中的十神
    for bs in branch_shigan:
        for level_info in bs["canggan"].values():
            key = level_info["shigan"]
            shigan_counts[key] = shigan_counts.get(key, 0) + 1

    # 善恶统计
    good = sum(c for k, c in shigan_counts.items()
               if ShiganEngine.classify(ShiganType(k)) == "善神")
    bad = sum(c for k, c in shigan_counts.items()
              if ShiganEngine.classify(ShiganType(k)) == "凶神")
    neutral = sum(c for k, c in shigan_counts.items()
                  if ShiganEngine.classify(ShiganType(k)) == "中性")

    return {
        "day_gan": day_gan,
        "day_wuxing": TianganEngine.wuxing_of(day_gan),
        "day_yinyang": TianganEngine.yinyang_of(day_gan).value,
        "heavenly_stems": [
            {
                "gan": sr.target_gan,
                "shigan": sr.shigan.value,
                "classification": ShiganEngine.classify(sr.shigan),
                "description": sr.description,
            }
            for sr in gan_shigan
        ],
        "earthly_branches": branch_shigan,
        "interactions": interactions,
        "statistics": {
            "shigan_counts": shigan_counts,
            "good": good,
            "bad": bad,
            "neutral": neutral,
            "balance": f"善神:{good} / 凶神:{bad} / 中性:{neutral}",
        },
    }


def find_interactions(earthly_branches: List[str]) -> Dict[str, Any]:
    """分析地支间的合冲害破刑关系

    Args:
        earthly_branches: 地支列表（如四柱地支）

    Returns:
        互动关系分析结果
    """
    n = len(earthly_branches)
    results: Dict[str, Any] = {
        "branches": earthly_branches,
        "pairs_analyzed": [],
        "he": [],      # 合
        "chong": [],   # 冲
        "hai": [],     # 害
        "po": [],      # 破
        "xing": [],    # 刑
    }

    for i in range(n):
        for j in range(i + 1, n):
            a, b = earthly_branches[i], earthly_branches[j]
            pair_label = f"[{i}]{a} ↔ [{j}]{b}"
            pair_entry = {"pair": pair_label, "relations": []}

            # 六合
            lh = DizhiEngine.liuhe(a)
            if lh and lh["partner"] == b:
                rel = {"type": "合", "detail": lh["description"]}
                pair_entry["relations"].append(rel)
                results["he"].append({**rel, "pair": pair_label})

            # 六冲
            lc = DizhiEngine.liuchong(a)
            if lc and lc["target"] == b:
                rel = {"type": "冲", "detail": lc["description"]}
                pair_entry["relations"].append(rel)
                results["chong"].append({**rel, "pair": pair_label})

            # 六害
            lh2 = DizhiEngine.liuhai(a)
            if lh2 and lh2["target"] == b:
                rel = {"type": "害", "detail": lh2["description"]}
                pair_entry["relations"].append(rel)
                results["hai"].append({**rel, "pair": pair_label})

            # 六破
            lp = DizhiEngine.liupo(a)
            if lp and lp["target"] == b:
                rel = {"type": "破", "detail": lp["description"]}
                pair_entry["relations"].append(rel)
                results["po"].append({**rel, "pair": pair_label})

            # 相刑
            xx = DizhiEngine.xiangxing(a)
            for xr in xx:
                if xr["target"] == b:
                    rel = {"type": "刑", "detail": xr["description"]}
                    pair_entry["relations"].append(rel)
                    results["xing"].append({**rel, "pair": pair_label})

            if pair_entry["relations"]:
                results["pairs_analyzed"].append(pair_entry)

    return results


# ============================================================================
# 主测试入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print(f"  推演引擎 divination_engine v{__version__} 自测")
    print("=" * 70)

    # ---- 1. 五行引擎测试 ----
    print("\n" + "─" * 70)
    print("  【一】五行引擎 WuxingEngine 测试")
    print("─" * 70)

    we = WuxingEngine
    print(f"  木生的：{we.generate('木')}    木克的：{we.restrict('木')}")
    print(f"  生火的是：{we.generated_by('火')}    克土的是：{we.restricted_by('土')}")
    print(f"  相乘（过克）：木相乘 → {we.over_restrict('木')}")
    print(f"  相侮（反克）：木相侮 → {we.reverse_restrict('木')}")
    print(f"  生链：木 → {we.chain_generate('木', 5)}")
    print(f"  克链：木 → {we.chain_restrict('木', 5)}")
    print(f"  颜色映射：{dict(we.COLOR_NAMES)}")

    # ---- 2. 天干引擎测试 ----
    print("\n" + "─" * 70)
    print("  【二】天干引擎 TianganEngine 测试")
    print("─" * 70)

    te = TianganEngine
    for tg in te.TIANGAN:
        wx = te.wuxing_of(tg)
        yy = te.yinyang_of(tg)
        direct = te.direction_of(tg)
        he = te.wuhe(tg)
        ke = te.restrict(tg)
        ke_targets = "、".join(r["target"] for r in ke)
        he_info = f"→合{he['partner']}化{he['wuxing']}" if he else ""
        print(f"  {tg}：{yy.value}{wx}｜方位{direct}｜克{ke_targets} {he_info}")

    # ---- 3. 地支引擎测试 ----
    print("\n" + "─" * 70)
    print("  【三】地支引擎 DizhiEngine 测试")
    print("─" * 70)

    de = DizhiEngine
    for dz in de.DIZHI:
        info = de._INFO[dz]
        cg = de.canggan(dz)
        cg_str = f"本气{cg['main']}"
        if cg['mid']:
            cg_str += f"、中气{cg['mid']}"
        if cg['residual']:
            cg_str += f"、余气{cg['residual']}"
        zc = de.zodiac_of(dz)
        mn = de.month_of(dz)
        hr = de.hour_of(dz)
        print(f"  {dz}({zc})：{info.yinyang.value}{info.wuxing}｜方位{info.direction}｜"
              f"{mn['name']}｜{hr['name']}｜藏干：{cg_str}")

    print("\n  --- 地支关系示例 ---")
    for dz in ["子", "寅", "卯", "辰"]:
        lh = de.liuhe(dz)
        sh = de.sanhe(dz)
        sha = de.sanhui(dz)
        lc = de.liuchong(dz)
        lh2 = de.liuhai(dz)
        lp = de.liupo(dz)
        xx = de.xiangxing(dz)
        print(f"  {dz}：六合={lh['partner'] if lh else '—'}｜"
              f"三合={'+'.join(sh['members']) if sh else '—'}｜"
              f"六冲={lc['target'] if lc else '—'}｜"
              f"刑={'、'.join(x['target'] for x in xx) if xx else '—'}")

    # ---- 4. 十神引擎测试 ----
    print("\n" + "─" * 70)
    print("  【四】十神引擎 ShiganEngine 测试")
    print("─" * 70)

    se = ShiganEngine
    # 以甲木为日干，推演所有天干的十神
    day = "甲"
    print(f"  日干：{day}（{te.wuxing_of(day)}·{te.yinyang_of(day).value}）")
    print(f"  {'目标':<4} {'十神':<6} {'分类':<4} {'说明'}")
    print(f"  {'─' * 40}")
    for tg in te.TIANGAN:
        sr = se.compute(day, tg)
        cls = se.classify(sr.shigan)
        print(f"  {sr.target_gan:<4} {sr.shigan.value:<6} {cls:<4} {sr.description}")

    # 十神交互示例
    print("\n  --- 十神交互示例（以食神为基准）---")
    for st in ShiganType:
        rel = se.interaction(ShiganType.SHISHEN, st)
        if rel:
            print(f"  食神 {rel} {st.value}")

    # 分类概览
    print("\n  --- 十神分类 ---")
    for st in ShiganType:
        print(f"  {st.value}：{se.classify(st)}")

    # ---- 5. 八字计算器测试 ----
    print("\n" + "─" * 70)
    print("  【五】八字计算器 BaziCalculator 测试")
    print("─" * 70)

    bc = BaziCalculator
    table = bc.jiazi_table()
    print(f"  六十甲子共 {len(table)} 组，前5组：")
    for i, name in table[:5]:
        print(f"    {i:2d}. {name}")
    print(f"  ...")
    for i, name in table[-5:]:
        print(f"    {i:2d}. {name}")

    print(f"  甲子序号：{bc.get_index('甲子')}    序号60：{bc.get_jiazi(60)}")
    print(f"  甲子合法：{bc.is_valid_combination('甲', '子')}")
    print(f"  甲乙合法：{bc.is_valid_combination('甲', '乙')}")

    # ---- 6. 综合推理测试 ----
    print("\n" + "─" * 70)
    print("  【六】综合推理函数 测试")
    print("─" * 70)

    # 示例八字：甲子年、丙寅月、庚辰日、壬午时
    example_gans = ["甲", "丙", "庚", "壬"]
    example_branches = ["子", "寅", "辰", "午"]
    print(f"  示例八字：{', '.join(f'{g}{z}' for g, z in zip(example_gans, example_branches))}")

    result = analyze_relations("庚", example_gans, example_branches)
    print(f"\n  日干：{result['day_gan']}（{result['day_wuxing']}·{result['day_yinyang']}）")
    print(f"\n  --- 天干十神 ---")
    for gs in result["heavenly_stems"]:
        print(f"  {gs['gan']} → {gs['shigan']}({gs['classification']}) — {gs['description']}")
    print(f"\n  --- 地支藏干十神 ---")
    for bs in result["earthly_branches"]:
        cg_list = ", ".join(
            f"{v['gan']}({v['shigan']})" for v in bs["canggan"].values()
        )
        print(f"  {bs['branch']}({bs['wuxing']}) → {cg_list}")

    print(f"\n  --- 地支互动 ---")
    if result["interactions"]["he"]:
        print("  【合】")
        for h in result["interactions"]["he"]:
            print(f"    {h['pair']} — {h['detail']}")
    if result["interactions"]["chong"]:
        print("  【冲】")
        for c in result["interactions"]["chong"]:
            print(f"    {c['pair']} — {c['detail']}")
    if result["interactions"]["xing"]:
        print("  【刑】")
        for x in result["interactions"]["xing"]:
            print(f"    {x['pair']} — {x['detail']}")

    print(f"\n  --- 统计 ---")
    stats = result["statistics"]
    print(f"  十神分布：{stats['shigan_counts']}")
    print(f"  善恶平衡：{stats['balance']}")

    print("\n" + "=" * 70)
    print(f"  全部测试完成 ✓")
    print("=" * 70)