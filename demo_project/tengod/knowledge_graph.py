#!/usr/bin/env python3
"""
知识图谱模块 · Knowledge Graph
整合五行八卦天干地支十神河图洛书等中华传统文化知识

与 divination_engine.py 协作：
- divination_engine: 推演/计算（动态推理）
- knowledge_graph: 存储/查询（静态知识 + 图遍历）
"""

from collections import OrderedDict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

__all__ = [
    "KnowledgeGraph",
    "get_knowledge_graph",
]
__version__ = "1.0.0"


# ============================================================================
# LRU 缓存实现
# ============================================================================

class LRUCache:
    """最近最少使用(LRU)缓存，用于加速频繁查询"""

    def __init__(self, capacity: int = 256):
        self._cache: OrderedDict = OrderedDict()
        self._capacity = capacity
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def put(self, key: str, value: Any) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._capacity:
                self._cache.popitem(last=False)
            self._cache[key] = value

    @property
    def stats(self) -> Dict[str, int]:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": round(self._hits / total, 4) if total > 0 else 0,
            "size": len(self._cache),
            "capacity": self._capacity,
        }


# ============================================================================
# 卦象数据
# ============================================================================

@dataclass
class Trigram:
    """八卦信息"""
    name: str              # 卦名：乾兑离震巽坎艮坤
    number: int            # 先天数
    symbol: str            # 符号：☰☱☲☳☴☵☶☷
    element: str           # 五行
    direction: str         # 方位
    nature: str            # 象征物：天地火雷风水山泽
    attribute: str         # 卦德
    family_role: str       # 家庭角色
    body_part: str         # 身体部位
    season: str            # 季节


@dataclass
class LiushisiGua:
    """六十四卦信息"""
    index: int             # 序号 1-64
    name: str              # 卦名
    upper_trigram: str     # 上卦
    lower_trigram: str     # 下卦


# ============================================================================
# 知识图谱核心类
# ============================================================================

class KnowledgeGraph:
    """知识图谱 — 中华传统文化知识存储与图谱查询

    整合五行、八卦、天干、地支、十神、河图洛书等知识体系，
    提供统一的知识查询与关系遍历能力。
    """

    def __init__(self):
        self._cache = LRUCache(capacity=512)

        # ── 五行元素 ──
        self._elements: Dict[str, Dict[str, Any]] = {
            "木": {
                "name": "木", "color": "青/绿", "direction": "东",
                "season": "春", "flavor": "酸", "organ": "肝",
                "sensory": "目", "emotion": "怒", "sound": "角",
                "generate": "火", "generated_by": "水",
                "restrict": "土", "restricted_by": "金",
                "description": "木曰曲直，代表生长、升发、条达的特性",
            },
            "火": {
                "name": "火", "color": "赤/红", "direction": "南",
                "season": "夏", "flavor": "苦", "organ": "心",
                "sensory": "舌", "emotion": "喜", "sound": "徵",
                "generate": "土", "generated_by": "木",
                "restrict": "金", "restricted_by": "水",
                "description": "火曰炎上，代表温热、上升、光明的特性",
            },
            "土": {
                "name": "土", "color": "黄", "direction": "中",
                "season": "长夏", "flavor": "甘", "organ": "脾",
                "sensory": "口", "emotion": "思", "sound": "宫",
                "generate": "金", "generated_by": "火",
                "restrict": "水", "restricted_by": "木",
                "description": "土爰稼穑，代表生化、承载、受纳的特性",
            },
            "金": {
                "name": "金", "color": "白", "direction": "西",
                "season": "秋", "flavor": "辛", "organ": "肺",
                "sensory": "鼻", "emotion": "悲", "sound": "商",
                "generate": "水", "generated_by": "土",
                "restrict": "木", "restricted_by": "火",
                "description": "金曰从革，代表收敛、肃降、变革的特性",
            },
            "水": {
                "name": "水", "color": "黑/蓝", "direction": "北",
                "season": "冬", "flavor": "咸", "organ": "肾",
                "sensory": "耳", "emotion": "恐", "sound": "羽",
                "generate": "木", "generated_by": "金",
                "restrict": "火", "restricted_by": "土",
                "description": "水曰润下，代表寒凉、滋润、向下的特性",
            },
        }

        # ── 八卦 ──
        self._trigrams: Dict[str, Trigram] = {
            "乾": Trigram("乾", 1, "☰", "金", "西北", "天", "健", "父", "头", "秋冬"),
            "兑": Trigram("兑", 2, "☱", "金", "西", "泽", "悦", "少女", "口", "秋"),
            "离": Trigram("离", 3, "☲", "火", "南", "火", "丽", "中女", "目", "夏"),
            "震": Trigram("震", 4, "☳", "木", "东", "雷", "动", "长男", "足", "春"),
            "巽": Trigram("巽", 5, "☴", "木", "东南", "风", "入", "长女", "股", "春夏"),
            "坎": Trigram("坎", 6, "☵", "水", "北", "水", "陷", "中男", "耳", "冬"),
            "艮": Trigram("艮", 7, "☶", "土", "东北", "山", "止", "少男", "手", "冬春"),
            "坤": Trigram("坤", 8, "☷", "土", "西南", "地", "顺", "母", "腹", "夏秋"),
        }
        self._trigram_by_number: Dict[int, Trigram] = {
            t.number: t for t in self._trigrams.values()
        }

        # ── 天干 ──
        self._tiangan: Dict[str, Dict[str, Any]] = {
            "甲": {"name": "甲", "wuxing": "木", "yinyang": "阳", "direction": "东",
                   "number": 1, "description": "甲木为阳木，参天大树，栋梁之材"},
            "乙": {"name": "乙", "wuxing": "木", "yinyang": "阴", "direction": "东",
                   "number": 2, "description": "乙木为阴木，藤萝花草，柔韧之象"},
            "丙": {"name": "丙", "wuxing": "火", "yinyang": "阳", "direction": "南",
                   "number": 3, "description": "丙火为阳火，太阳之火，光明普照"},
            "丁": {"name": "丁", "wuxing": "火", "yinyang": "阴", "direction": "南",
                   "number": 4, "description": "丁火为阴火，灯烛之火，内心光明"},
            "戊": {"name": "戊", "wuxing": "土", "yinyang": "阳", "direction": "中",
                   "number": 5, "description": "戊土为阳土，城墙之土，厚重坚固"},
            "己": {"name": "己", "wuxing": "土", "yinyang": "阴", "direction": "中",
                   "number": 6, "description": "己土为阴土，田园之土，滋养万物"},
            "庚": {"name": "庚", "wuxing": "金", "yinyang": "阳", "direction": "西",
                   "number": 7, "description": "庚金为阳金，刀剑之金，刚锐果断"},
            "辛": {"name": "辛", "wuxing": "金", "yinyang": "阴", "direction": "西",
                   "number": 8, "description": "辛金为阴金，珠宝之金，精致华美"},
            "壬": {"name": "壬", "wuxing": "水", "yinyang": "阳", "direction": "北",
                   "number": 9, "description": "壬水为阳水，江河之水，奔流不息"},
            "癸": {"name": "癸", "wuxing": "水", "yinyang": "阴", "direction": "北",
                   "number": 10, "description": "癸水为阴水，雨露之水，润物无声"},
        }
        # 天干五合
        self._tiangan_wuhe: Dict[str, Dict[str, str]] = {
            "甲": {"partner": "己", "wuxing": "土", "desc": "甲己合土"},
            "己": {"partner": "甲", "wuxing": "土", "desc": "甲己合土"},
            "乙": {"partner": "庚", "wuxing": "金", "desc": "乙庚合金"},
            "庚": {"partner": "乙", "wuxing": "金", "desc": "乙庚合金"},
            "丙": {"partner": "辛", "wuxing": "水", "desc": "丙辛合水"},
            "辛": {"partner": "丙", "wuxing": "水", "desc": "丙辛合水"},
            "丁": {"partner": "壬", "wuxing": "木", "desc": "丁壬合木"},
            "壬": {"partner": "丁", "wuxing": "木", "desc": "丁壬合木"},
            "戊": {"partner": "癸", "wuxing": "火", "desc": "戊癸合火"},
            "癸": {"partner": "戊", "wuxing": "火", "desc": "戊癸合火"},
        }

        # ── 地支 ──
        self._dizhi: Dict[str, Dict[str, Any]] = {
            "子": {"name": "子", "wuxing": "水", "yinyang": "阳", "direction": "北",
                   "zodiac": "鼠", "month": 11, "month_name": "十一月",
                   "hour": "23:00-01:00", "hour_name": "子时",
                   "canggan_main": "癸", "number": 1},
            "丑": {"name": "丑", "wuxing": "土", "yinyang": "阴", "direction": "东北",
                   "zodiac": "牛", "month": 12, "month_name": "十二月",
                   "hour": "01:00-03:00", "hour_name": "丑时",
                   "canggan_main": "己", "canggan_mid": "癸", "canggan_residual": "辛",
                   "number": 2},
            "寅": {"name": "寅", "wuxing": "木", "yinyang": "阳", "direction": "东北",
                   "zodiac": "虎", "month": 1, "month_name": "正月",
                   "hour": "03:00-05:00", "hour_name": "寅时",
                   "canggan_main": "甲", "canggan_mid": "丙", "canggan_residual": "戊",
                   "number": 3},
            "卯": {"name": "卯", "wuxing": "木", "yinyang": "阴", "direction": "东",
                   "zodiac": "兔", "month": 2, "month_name": "二月",
                   "hour": "05:00-07:00", "hour_name": "卯时",
                   "canggan_main": "乙", "number": 4},
            "辰": {"name": "辰", "wuxing": "土", "yinyang": "阳", "direction": "东南",
                   "zodiac": "龙", "month": 3, "month_name": "三月",
                   "hour": "07:00-09:00", "hour_name": "辰时",
                   "canggan_main": "戊", "canggan_mid": "乙", "canggan_residual": "癸",
                   "number": 5},
            "巳": {"name": "巳", "wuxing": "火", "yinyang": "阴", "direction": "东南",
                   "zodiac": "蛇", "month": 4, "month_name": "四月",
                   "hour": "09:00-11:00", "hour_name": "巳时",
                   "canggan_main": "丙", "canggan_mid": "庚", "canggan_residual": "戊",
                   "number": 6},
            "午": {"name": "午", "wuxing": "火", "yinyang": "阳", "direction": "南",
                   "zodiac": "马", "month": 5, "month_name": "五月",
                   "hour": "11:00-13:00", "hour_name": "午时",
                   "canggan_main": "丁", "canggan_mid": "己", "number": 7},
            "未": {"name": "未", "wuxing": "土", "yinyang": "阴", "direction": "西南",
                   "zodiac": "羊", "month": 6, "month_name": "六月",
                   "hour": "13:00-15:00", "hour_name": "未时",
                   "canggan_main": "己", "canggan_mid": "丁", "canggan_residual": "乙",
                   "number": 8},
            "申": {"name": "申", "wuxing": "金", "yinyang": "阳", "direction": "西南",
                   "zodiac": "猴", "month": 7, "month_name": "七月",
                   "hour": "15:00-17:00", "hour_name": "申时",
                   "canggan_main": "庚", "canggan_mid": "壬", "canggan_residual": "戊",
                   "number": 9},
            "酉": {"name": "酉", "wuxing": "金", "yinyang": "阴", "direction": "西",
                   "zodiac": "鸡", "month": 8, "month_name": "八月",
                   "hour": "17:00-19:00", "hour_name": "酉时",
                   "canggan_main": "辛", "number": 10},
            "戌": {"name": "戌", "wuxing": "土", "yinyang": "阳", "direction": "西北",
                   "zodiac": "狗", "month": 9, "month_name": "九月",
                   "hour": "19:00-21:00", "hour_name": "戌时",
                   "canggan_main": "戊", "canggan_mid": "辛", "canggan_residual": "丁",
                   "number": 11},
            "亥": {"name": "亥", "wuxing": "水", "yinyang": "阴", "direction": "西北",
                   "zodiac": "猪", "month": 10, "month_name": "十月",
                   "hour": "21:00-23:00", "hour_name": "亥时",
                   "canggan_main": "壬", "canggan_mid": "甲", "number": 12},
        }

        # ── 十神 ──
        self._shigan: Dict[str, Dict[str, Any]] = {
            "比肩": {"name": "比肩", "classification": "中性", "rule": "同我、同性",
                     "description": "比肩为兄弟、朋友、同辈，代表竞争、合作、自我意识。"},
            "劫财": {"name": "劫财", "classification": "凶神", "rule": "同我、异性",
                     "description": "劫财为同辈异性，代表竞争掠夺、冲动冒险。"},
            "食神": {"name": "食神", "classification": "善神", "rule": "我生、同性",
                     "description": "食神为子女、才华、口福，代表创造力与享乐。"},
            "伤官": {"name": "伤官", "classification": "凶神", "rule": "我生、异性",
                     "description": "伤官为才华外露，代表叛逆、创新、不拘一格。"},
            "正财": {"name": "正财", "classification": "善神", "rule": "我克、异性",
                     "description": "正财为妻子、正当收入，代表稳定财富与价值观。"},
            "偏财": {"name": "偏财", "classification": "中性", "rule": "我克、同性",
                     "description": "偏财为父亲、横财，代表投机、慷慨、意外之财。"},
            "正官": {"name": "正官", "classification": "善神", "rule": "克我、异性",
                     "description": "正官为丈夫、上司、法律，代表权威、纪律、名誉。"},
            "七杀": {"name": "七杀", "classification": "凶神", "rule": "克我、同性",
                     "description": "七杀为武将、敌人、压力，代表权威挑战、魄力。"},
            "正印": {"name": "正印", "classification": "善神", "rule": "生我、异性",
                     "description": "正印为母亲、师长、学问，代表慈爱、智慧、庇护。"},
            "偏印": {"name": "偏印", "classification": "凶神", "rule": "生我、同性",
                     "description": "偏印为继母、偏门学问，代表独特思维、孤僻。"},
        }

        # ── 河图洛书 ──
        self._hetu: Dict[str, Any] = {
            "name": "河图",
            "description": "河出图，洛出书，圣人则之。河图为龙马负图出于黄河。",
            "structure": "黑白点数排列，天数25+地数30=天地之数55",
            "orientation": "坐北朝南，天一生水，地六成之",
            "directions": {
                "北": {"number": "1-6", "element": "水"},
                "南": {"number": "2-7", "element": "火"},
                "东": {"number": "3-8", "element": "木"},
                "西": {"number": "4-9", "element": "金"},
                "中": {"number": "5-10", "element": "土"},
            },
            "grid": [
                ["",  "7", ""],
                ["2", "",  ""],
                ["",  "5", "10", "8", "3"],
                ["",  "1", ""],
                ["",  "6", ""],
            ],
            "relation": "对应先天八卦",
        }

        self._luoshu: Dict[str, Any] = {
            "name": "洛书",
            "description": "洛书为神龟负书出于洛水，禹因之以成九畴。",
            "structure": "戴九履一，左三右七，二四为肩，六八为足",
            "grid": [
                [4, 9, 2],
                [3, 5, 7],
                [8, 1, 6],
            ],
            "magic_constant": 15,
            "relation": "对应后天八卦/文王八卦",
        }

        # ── 六十四卦 ──
        self._liushisi_gua = self._build_liushisi_gua()

        # ── 实体索引（用于搜索） ──
        self._entity_index: Dict[str, Dict[str, Any]] = {}
        self._build_entity_index()

        # ── 关系图谱（生成/被生成/克制/被克制） ──
        self._relation_graph: Dict[str, Dict[str, List[str]]] = {}
        self._build_relation_graph()

    # ========================================================================
    # 六十四卦构建
    # ========================================================================

    def _build_liushisi_gua(self) -> List[LiushisiGua]:
        """构建六十四卦索引"""
        upper_order = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]
        lower_order = ["乾", "坤", "震", "坎", "艮", "巽", "离", "兑"]

        gua_names = [
            # 乾宫八卦：乾为天、天风姤、天山遁、天地否、风地观、山地剥、火地晋、火天大有
            "乾为天", "天风姤", "天山遁", "天地否", "风地观", "山地剥", "火地晋", "火天大有",
            # 兑宫八卦
            "兑为泽", "泽水困", "泽地萃", "泽山咸", "水山蹇", "地山谦", "雷山小过", "雷泽归妹",
            # 离宫八卦
            "离为火", "火山旅", "火风鼎", "火水未济", "山水蒙", "风水涣", "天水讼", "天火同人",
            # 震宫八卦
            "震为雷", "雷地豫", "雷水解", "雷风恒", "地风升", "水风井", "泽风大过", "泽雷随",
            # 巽宫八卦
            "巽为风", "风天小畜", "风火家人", "风雷益", "天雷无妄", "火雷噬嗑", "山雷颐", "山风蛊",
            # 坎宫八卦
            "坎为水", "水泽节", "水雷屯", "水火既济", "泽火革", "雷火丰", "地火明夷", "地水师",
            # 艮宫八卦
            "艮为山", "山火贲", "山天大畜", "山泽损", "火泽睽", "天泽履", "风泽中孚", "风山渐",
            # 坤宫八卦
            "坤为地", "地雷复", "地泽临", "地天泰", "雷天大壮", "泽天夬", "水天需", "水地比",
        ]

        # 每宫八卦：本宫卦 + 一世到五世 + 游魂 + 归魂
        result: List[LiushisiGua] = []
        for palace_idx in range(8):
            palace_upper = upper_order[palace_idx]
            # 世爻对应的下卦索引（本宫卦下卦 = 上卦，依次变卦）
            palace_lower_idx = [
                0, 7, 3, 1, 5, 6, 2, 4  # 乾宫下卦变化顺序的近似映射
            ]
            for gua_idx in range(8):
                idx = palace_idx * 8 + gua_idx
                name = gua_names[idx]
                # 近似映射上下卦
                if gua_idx == 0:
                    upper = palace_upper
                    lower = palace_upper
                elif gua_idx <= 5:
                    upper = palace_upper
                    lower = lower_order[(palace_lower_idx[palace_idx] + gua_idx - 1) % 8]
                elif gua_idx == 6:  # 游魂
                    upper = lower_order[(palace_lower_idx[palace_idx] + 4) % 8]
                    lower = lower_order[(palace_lower_idx[palace_idx] + 5) % 8]
                else:  # 归魂
                    upper = lower_order[(palace_lower_idx[palace_idx] + 4) % 8]
                    lower = palace_upper

                result.append(LiushisiGua(
                    index=idx + 1,
                    name=name,
                    upper_trigram=upper,
                    lower_trigram=lower,
                ))

        return result

    # ========================================================================
    # 实体索引构建
    # ========================================================================

    def _build_entity_index(self) -> None:
        """构建全局实体搜索索引"""
        for key, elem in self._elements.items():
            self._entity_index[f"五行·{key}"] = {"type": "element", "name": key, "data": elem}

        for key, tri in self._trigrams.items():
            self._entity_index[f"八卦·{key}"] = {"type": "trigram", "name": key, "data": {
                "name": tri.name, "number": tri.number, "symbol": tri.symbol,
                "element": tri.element, "direction": tri.direction,
                "nature": tri.nature, "attribute": tri.attribute,
                "family_role": tri.family_role, "body_part": tri.body_part,
                "season": tri.season,
            }}

        for key, tg in self._tiangan.items():
            self._entity_index[f"天干·{key}"] = {"type": "tiangan", "name": key, "data": dict(tg)}
            he = self._tiangan_wuhe.get(key)
            if he:
                self._entity_index[f"天干·{key}"]["data"]["wuhe"] = he

        for key, dz in self._dizhi.items():
            self._entity_index[f"地支·{key}"] = {"type": "dizhi", "name": key, "data": dict(dz)}

        for key, sg in self._shigan.items():
            self._entity_index[f"十神·{key}"] = {"type": "shigan", "name": key, "data": dict(sg)}

        self._entity_index["河图"] = {"type": "hetu", "name": "河图", "data": dict(self._hetu)}
        self._entity_index["洛书"] = {"type": "luoshu", "name": "洛书", "data": dict(self._luoshu)}

        for g in self._liushisi_gua:
            self._entity_index[f"六十四卦·{g.name}"] = {
                "type": "liushisi_gua", "name": g.name, "data": {
                    "index": g.index, "name": g.name,
                    "upper_trigram": g.upper_trigram, "lower_trigram": g.lower_trigram,
                }}

    # ========================================================================
    # 关系图谱构建
    # ========================================================================

    def _build_relation_graph(self) -> None:
        """构建五行生克关系图谱"""
        graph: Dict[str, Dict[str, List[str]]] = {}
        for name, elem in self._elements.items():
            graph[name] = {
                "生成": [elem["generate"]],
                "被生成": [elem["generated_by"]],
                "克制": [elem["restrict"]],
                "被克制": [elem["restricted_by"]],
            }
        self._relation_graph = graph

    # ========================================================================
    # 公开查询方法
    # ========================================================================

    def get_element(self, name: str) -> Optional[Dict[str, Any]]:
        """查询五行元素完整信息

        Args:
            name: 五行名称（木/火/土/金/水）

        Returns:
            元素信息字典，含生成/被生成/克制/被克制关系
        """
        cache_key = f"element:{name}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        result = self._elements.get(name)
        if result:
            result = dict(result)
        self._cache.put(cache_key, result)
        return result

    def get_trigram(self, name_or_number: Any) -> Optional[Dict[str, Any]]:
        """查询八卦

        Args:
            name_or_number: 卦名（如"乾"）或先天数（如1）

        Returns:
            八卦信息字典
        """
        if isinstance(name_or_number, int):
            cache_key = f"trigram:n:{name_or_number}"
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
            tri = self._trigram_by_number.get(name_or_number)
        else:
            cache_key = f"trigram:{name_or_number}"
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
            tri = self._trigrams.get(name_or_number)

        if tri is None:
            self._cache.put(cache_key, None)
            return None

        result = {
            "name": tri.name, "number": tri.number, "symbol": tri.symbol,
            "element": tri.element, "direction": tri.direction,
            "nature": tri.nature, "attribute": tri.attribute,
            "family_role": tri.family_role, "body_part": tri.body_part,
            "season": tri.season,
        }
        self._cache.put(cache_key, result)
        return result

    def get_tiangan(self, name: str) -> Optional[Dict[str, Any]]:
        """查询天干信息

        Args:
            name: 天干名称（甲乙丙丁戊己庚辛壬癸）

        Returns:
            天干信息字典，含五行、阴阳、方位、五合等
        """
        cache_key = f"tiangan:{name}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        tg = self._tiangan.get(name)
        if tg is None:
            self._cache.put(cache_key, None)
            return None
        result = dict(tg)
        he = self._tiangan_wuhe.get(name)
        if he:
            result["wuhe"] = he
        self._cache.put(cache_key, result)
        return result

    def get_dizhi(self, name: str) -> Optional[Dict[str, Any]]:
        """查询地支信息

        Args:
            name: 地支名称（子丑寅卯辰巳午未申酉戌亥）

        Returns:
            地支信息字典，含五行、阴阳、生肖、时辰、藏干等
        """
        cache_key = f"dizhi:{name}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        dz = self._dizhi.get(name)
        if dz is None:
            self._cache.put(cache_key, None)
            return None
        result = dict(dz)
        self._cache.put(cache_key, result)
        return result

    def get_shigan(self, name: str) -> Optional[Dict[str, Any]]:
        """查询十神详情

        Args:
            name: 十神名称（比肩/劫财/食神等）

        Returns:
            十神信息字典
        """
        cache_key = f"shigan:{name}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        result = self._shigan.get(name)
        if result:
            result = dict(result)
        self._cache.put(cache_key, result)
        return result

    def get_hetu(self) -> Dict[str, Any]:
        """获取河图布局

        Returns:
            河图完整信息字典
        """
        cache_key = "hetu"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        result = dict(self._hetu)
        self._cache.put(cache_key, result)
        return result

    def get_luoshu(self) -> Dict[str, Any]:
        """获取洛书布局

        Returns:
            洛书完整信息字典
        """
        cache_key = "luoshu"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        result = dict(self._luoshu)
        self._cache.put(cache_key, result)
        return result

    def search(self, keyword: str) -> List[Dict[str, Any]]:
        """模糊搜索所有实体

        Args:
            keyword: 搜索关键词（支持中文字符）

        Returns:
            匹配的实体列表，按相关度排序
        """
        cache_key = f"search:{keyword}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        results: List[Dict[str, Any]] = []
        keyword_lower = keyword.lower()

        for entity_key, entity in self._entity_index.items():
            score = 0
            name = entity["name"]
            # 名称精确匹配
            if name == keyword:
                score = 100
            # 名称包含关键词
            elif keyword in name:
                score = 80
            elif keyword_lower in name.lower():
                score = 70
            else:
                # 搜索数据字段
                data_str = str(entity["data"])
                if keyword in data_str:
                    score = 40
                elif keyword_lower in data_str.lower():
                    score = 30

            # 也搜索类型前缀
            if keyword in entity["type"]:
                score = max(score, 50)

            if score > 0:
                results.append({
                    "entity_key": entity_key,
                    "type": entity["type"],
                    "name": name,
                    "score": score,
                    "data": entity["data"],
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        self._cache.put(cache_key, results)
        return results

    def get_relations(self, entity_name: str) -> Dict[str, Any]:
        """获取实体的所有关系

        返回该实体在五行生克体系中的生成/被生成/克制/被克制关系。
        对于八卦，返回先天方位关系。对于天干，返回五合关系。

        Args:
            entity_name: 实体名称

        Returns:
            关系字典
        """
        cache_key = f"relations:{entity_name}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        result: Dict[str, Any] = {
            "entity": entity_name,
            "relations": {},
        }

        # 五行关系
        if entity_name in self._relation_graph:
            result["relations"]["wuxing"] = dict(self._relation_graph[entity_name])
            elem = self._elements[entity_name]
            result["category"] = "element"
            result["details"] = {
                "color": elem["color"],
                "direction": elem["direction"],
                "season": elem["season"],
                "description": elem["description"],
            }

        # 天干五合
        tg_he = self._tiangan_wuhe.get(entity_name)
        if tg_he:
            if "relations" not in result:
                result["relations"] = {}
            result["relations"]["wuhe"] = tg_he
            if "category" not in result:
                result["category"] = "tiangan"
                tg = self._tiangan.get(entity_name, {})
                result["details"] = {"wuxing": tg.get("wuxing"), "yinyang": tg.get("yinyang")}

        # 八卦先天数关系
        tri = self._trigrams.get(entity_name)
        if tri:
            if "relations" not in result:
                result["relations"] = {}
            result["relations"]["trigram"] = {
                "element": tri.element,
                "direction": tri.direction,
                "nature": tri.nature,
                "attribute": tri.attribute,
                "family_role": tri.family_role,
            }
            if "category" not in result:
                result["category"] = "trigram"

        if not result["relations"]:
            result["relations"] = {"note": "无直接的五行生克关系"}
            result["category"] = "unknown"

        self._cache.put(cache_key, result)
        return result

    def export_for_frontend(self) -> Dict[str, Any]:
        """导出为前端可视化所需的数据格式

        Returns:
            包含 nodes 和 edges 的图数据结构，适合前端知识图谱可视化
        """
        cache_key = "export_frontend"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # 五行节点
        for name, elem in self._elements.items():
            nodes.append({
                "id": f"element:{name}", "label": name,
                "group": "五行", "color": elem["color"],
                "properties": elem,
            })

        # 五行生克边
        for name, elem in self._elements.items():
            source = f"element:{name}"
            # 生成边
            edges.append({
                "source": source, "target": f"element:{elem['generate']}",
                "label": "生", "rel_type": "generate",
            })
            # 克制边
            edges.append({
                "source": source, "target": f"element:{elem['restrict']}",
                "label": "克", "rel_type": "restrict",
            })

        # 八卦节点
        for name, tri in self._trigrams.items():
            nodes.append({
                "id": f"trigram:{name}", "label": f"{tri.symbol} {name}",
                "group": "八卦", "color": self._elements.get(tri.element, {}).get("color", ""),
                "properties": {
                    "name": tri.name, "number": tri.number,
                    "element": tri.element, "direction": tri.direction,
                    "nature": tri.nature, "attribute": tri.attribute,
                },
            })

        # 天干节点
        for name, tg in self._tiangan.items():
            nodes.append({
                "id": f"tiangan:{name}", "label": name,
                "group": "天干",
                "properties": dict(tg),
            })

        # 天干五合边
        seen_he: Set[str] = set()
        for name, he in self._tiangan_wuhe.items():
            pair = tuple(sorted([name, he["partner"]]))
            if pair not in seen_he:
                seen_he.add(pair)
                edges.append({
                    "source": f"tiangan:{pair[0]}", "target": f"tiangan:{pair[1]}",
                    "label": f"合化{he['wuxing']}", "rel_type": "wuhe",
                })

        # 地支节点
        for name, dz in self._dizhi.items():
            nodes.append({
                "id": f"dizhi:{name}", "label": f"{name}({dz['zodiac']})",
                "group": "地支",
                "properties": dict(dz),
            })

        # 十神节点
        for name, sg in self._shigan.items():
            nodes.append({
                "id": f"shigan:{name}", "label": name,
                "group": "十神", "color": {
                    "善神": "#4CAF50", "凶神": "#F44336", "中性": "#FF9800",
                }.get(sg["classification"], "#9E9E9E"),
                "properties": dict(sg),
            })

        # 河图洛书节点
        nodes.append({
            "id": "hetu", "label": "河图",
            "group": "宇宙图式", "properties": self._hetu,
        })
        nodes.append({
            "id": "luoshu", "label": "洛书",
            "group": "宇宙图式", "properties": self._luoshu,
        })

        result = {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "groups": ["五行", "八卦", "天干", "地支", "十神", "宇宙图式"],
            },
        }
        self._cache.put(cache_key, result)
        return result

    def get_liushijiazi(self) -> List[Dict[str, Any]]:
        """获取完整六十甲子列表

        Returns:
            六十甲子列表，每项含序号和干支组合
        """
        cache_key = "liushijiazi"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        tiangan_list = list(self._tiangan.keys())
        dizhi_list = list(self._dizhi.keys())
        result = []
        for i in range(60):
            gan = tiangan_list[i % 10]
            zhi = dizhi_list[i % 12]
            result.append({
                "index": i + 1,
                "ganzhi": gan + zhi,
                "tiangan": gan,
                "dizhi": zhi,
                "tiangan_wuxing": self._tiangan[gan]["wuxing"],
                "dizhi_wuxing": self._dizhi[zhi]["wuxing"],
            })

        self._cache.put(cache_key, result)
        return result

    def get_liushisi_gua(self) -> List[Dict[str, Any]]:
        """获取六十四卦索引

        Returns:
            六十四卦列表，每项含序号、卦名、上下卦
        """
        cache_key = "liushisi_gua"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        result = [
            {
                "index": g.index,
                "name": g.name,
                "upper_trigram": g.upper_trigram,
                "lower_trigram": g.lower_trigram,
            }
            for g in self._liushisi_gua
        ]
        self._cache.put(cache_key, result)
        return result

    def list_all_entities(self) -> Dict[str, List[str]]:
        """列出所有可查询的实体名称

        Returns:
            按类型分组的实体名称字典
        """
        return {
            "elements": list(self._elements.keys()),
            "trigrams": list(self._trigrams.keys()),
            "tiangan": list(self._tiangan.keys()),
            "dizhi": list(self._dizhi.keys()),
            "shigan": list(self._shigan.keys()),
            "diagrams": ["河图", "洛书"],
            "liushijiazi_count": 60,
            "liushisi_gua_count": 64,
        }

    @property
    def cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return self._cache.stats

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache = LRUCache(capacity=512)


# ============================================================================
# 全局懒加载实例
# ============================================================================

_knowledge_graph: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    """获取全局知识图谱单例（懒加载）"""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
    return _knowledge_graph


# ============================================================================
# 主测试入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print(f"  知识图谱 KnowledgeGraph v{__version__} 自测")
    print("=" * 70)

    kg = KnowledgeGraph()

    # ── 1. 五行元素查询 ──
    print("\n" + "─" * 70)
    print("  【一】五行元素查询")
    print("─" * 70)
    for el in ["木", "火", "土", "金", "水"]:
        info = kg.get_element(el)
        if info:
            print(f"  {el}：色{info['color']}｜位{info['direction']}｜"
                  f"生{info['generate']}｜克{info['restrict']}｜"
                  f"被{info['generated_by']}生｜被{info['restricted_by']}克")
            print(f"     {info['description']}")

    # ── 2. 八卦查询 ──
    print("\n" + "─" * 70)
    print("  【二】八卦查询")
    print("─" * 70)
    for name in ["乾", "坤", "震", "巽", "坎", "离", "艮", "兑"]:
        tri = kg.get_trigram(name)
        if tri:
            print(f"  {tri['symbol']} {tri['name']}(数{tri['number']})："
                  f"{tri['element']}｜{tri['direction']}｜象{tri['nature']}｜德{tri['attribute']}")

    print(f"\n  按先天数查询：数3→{kg.get_trigram(3)['name']}｜数8→{kg.get_trigram(8)['name']}")

    # ── 3. 天干查询 ──
    print("\n" + "─" * 70)
    print("  【三】天干查询")
    print("─" * 70)
    for tg_name in ["甲", "乙", "丙", "丁", "戊"]:
        tg = kg.get_tiangan(tg_name)
        if tg:
            he_str = f"｜五合：{tg['wuhe']['desc']}" if "wuhe" in tg else ""
            print(f"  {tg_name}：{tg['yinyang']}{tg['wuxing']}｜方位{tg['direction']}{he_str}")
    print("  ...")

    # ── 4. 地支查询 ──
    print("\n" + "─" * 70)
    print("  【四】地支查询")
    print("─" * 70)
    for dz_name in ["子", "丑", "寅", "卯"]:
        dz = kg.get_dizhi(dz_name)
        if dz:
            cg_parts = [f"本气{dz['canggan_main']}"]
            if dz.get("canggan_mid"):
                cg_parts.append(f"中气{dz['canggan_mid']}")
            if dz.get("canggan_residual"):
                cg_parts.append(f"余气{dz['canggan_residual']}")
            print(f"  {dz_name}({dz['zodiac']})：{dz['yinyang']}{dz['wuxing']}｜"
                  f"方位{dz['direction']}｜{dz['month_name']}｜{dz['hour_name']}｜"
                  f"藏干：{'、'.join(cg_parts)}")
    print("  ...")

    # ── 5. 十神查询 ──
    print("\n" + "─" * 70)
    print("  【五】十神查询")
    print("─" * 70)
    for sg_name in ["比肩", "劫财", "食神", "伤官", "正财", "偏财", "正官", "七杀", "正印", "偏印"]:
        sg = kg.get_shigan(sg_name)
        if sg:
            print(f"  {sg['name']}（{sg['classification']}）：{sg['rule']}｜{sg['description']}")

    # ── 6. 河图洛书 ──
    print("\n" + "─" * 70)
    print("  【六】河图洛书")
    print("─" * 70)
    hetu = kg.get_hetu()
    print(f"  河图：{hetu['description']}")
    print(f"    {hetu['structure']}")
    luoshu = kg.get_luoshu()
    print(f"  洛书：{luoshu['description']}")
    print(f"    {luoshu['structure']}，幻方常数={luoshu['magic_constant']}")

    # ── 7. 搜索 ──
    print("\n" + "─" * 70)
    print("  【七】模糊搜索")
    print("─" * 70)
    for keyword in ["木", "金", "火", "比肩", "河图"]:
        results = kg.search(keyword)
        top = results[:3]
        names = ", ".join(
            f"{r['name']}({r['type']},分{r['score']})" for r in top
        )
        print(f"  搜索「{keyword}」→ {names}")

    # ── 8. 关系图谱 ──
    print("\n" + "─" * 70)
    print("  【八】关系图谱")
    print("─" * 70)
    for entity in ["木", "火", "乾", "甲"]:
        rel = kg.get_relations(entity)
        print(f"  {entity}：{rel['relations']}")

    # ── 9. 六十甲子 ──
    print("\n" + "─" * 70)
    print("  【九】六十甲子")
    print("─" * 70)
    jiazi = kg.get_liushijiazi()
    print(f"  共计 {len(jiazi)} 组")
    for jz in jiazi[:5]:
        print(f"    {jz['index']:2d}. {jz['ganzhi']}（天干{jz['tiangan_wuxing']}·地支{jz['dizhi_wuxing']}）")
    print("  ...")
    for jz in jiazi[-3:]:
        print(f"    {jz['index']:2d}. {jz['ganzhi']}（天干{jz['tiangan_wuxing']}·地支{jz['dizhi_wuxing']}）")

    # ── 10. 六十四卦 ──
    print("\n" + "─" * 70)
    print("  【十】六十四卦索引")
    print("─" * 70)
    gua64 = kg.get_liushisi_gua()
    print(f"  共计 {len(gua64)} 卦")
    for g in gua64[:5]:
        print(f"    {g['index']:2d}. {g['name']}（上{g['upper_trigram']}下{g['lower_trigram']}）")
    print("  ...")
    for g in gua64[-3:]:
        print(f"    {g['index']:2d}. {g['name']}（上{g['upper_trigram']}下{g['lower_trigram']}）")

    # ── 11. 前端导出 ──
    print("\n" + "─" * 70)
    print("  【十一】前端可视化导出")
    print("─" * 70)
    frontend = kg.export_for_frontend()
    print(f"  节点: {frontend['stats']['total_nodes']} 个")
    print(f"  边: {frontend['stats']['total_edges']} 条")
    print(f"  分组: {', '.join(frontend['stats']['groups'])}")

    # ── 12. 缓存统计 ──
    print("\n" + "─" * 70)
    print("  【十二】缓存统计")
    print("─" * 70)
    stats = kg.cache_stats
    print(f"  命中: {stats['hits']}｜缺失: {stats['misses']}｜"
          f"命中率: {stats['hit_rate'] * 100:.1f}%｜大小: {stats['size']}/{stats['capacity']}")

    # ── 13. 实体列表 ──
    print("\n" + "─" * 70)
    print("  【十三】全部实体列表")
    print("─" * 70)
    entities = kg.list_all_entities()
    for cat, names in entities.items():
        if isinstance(names, list):
            print(f"  {cat}: {', '.join(names)}")
        else:
            print(f"  {cat}: {names}")

    print("\n" + "=" * 70)
    print("  知识图谱自测全部完成 ✓")
    print("=" * 70)