"""
tengod.fengshui — 阶段二十一 · 21.2 玄空飞星风水排盘

玄空飞星核心：
  1. 三元九运：每 20 年一运，1864 起计
     上元：1运(1864-1883), 2运(1884-1903), 3运(1904-1923)
     中元：4运(1924-1943), 5运(1944-1963), 6运(1964-1983)
     下元：7运(1984-2003), 8运(2004-2023), 9运(2024-2043)
  2. 元旦盘：根据所属运程，将该运星入中宫顺飞九宫
  3. 山盘 / 向盘：根据坐向确定山向，根据阴/阳顺逆飞
  4. 流年飞星：根据流年太岁，将年支星入中宫顺飞

九宫方位（洛书）：
  4 巽 | 9 离 | 2 坤
  -----------------
  3 震 | 5 中 | 7 兑
  -----------------
  8 艮 | 1 坎 | 6 乾

  坎(北)1, 坤(西南)2, 震(东)3, 巽(东南)4,
  中宫5, 乾(西北)6, 兑(西)7, 艮(东北)8, 离(南)9

八宫五行：
  1 坎宫(北) - 水
  2 坤宫(西南) - 土
  3 震宫(东) - 木
  4 巽宫(东南) - 木
  5 中宫 - 土
  6 乾宫(西北) - 金
  7 兑宫(西) - 金
  8 艮宫(东北) - 土
  9 离宫(南) - 火

九星吉凶（三元九运体系）：
  1白 贪狼 - 吉（旺丁财，利文书）
  2黑 巨门 - 凶（病符星，主疾病）
  3碧 禄存 - 凶（主是非争斗）
  4绿 文曲 - 吉（文昌，利学业）
  5黄 廉贞 - 凶（五黄大煞，最凶）
  6白 武曲 - 吉（主贵气，利官贵）
  7赤 破军 - 吉（主财运，利商业）
  8白 左辅 - 吉（主小贵，利不动产）
  9紫 右弼 - 吉（主喜庆，利感情）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# 基础数据
# ============================================================================

# 九星名称
NINE_STARS = {
    1: "一白贪狼",
    2: "二黑巨门",
    3: "三碧禄存",
    4: "四绿文曲",
    5: "五黄廉贞",
    6: "六白武曲",
    7: "七赤破军",
    8: "八白左辅",
    9: "九紫右弼",
}

# 九星吉凶
STAR_FORTUNE = {
    1: "吉", 2: "凶", 3: "凶", 4: "吉", 5: "大凶",
    6: "吉", 7: "吉", 8: "吉", 9: "吉",
}

# 九星五行
STAR_WUXING = {
    1: "水", 2: "土", 3: "木", 4: "木", 5: "土",
    6: "金", 7: "金", 8: "土", 9: "火",
}

# 九星影响领域
STAR_INFLUENCE = {
    1: "旺丁财，利文书、谈判、学习",
    2: "主疾病、瘟疫，健康需注意",
    3: "主是非争斗，官非口舌",
    4: "利学业、文昌，有助名誉",
    5: "五黄大煞，主大灾大病，需特别化解",
    6: "主贵气，利官位、上司缘",
    7: "主财运，利商业、投资",
    8: "主小贵，利不动产、稳定事业",
    9: "主喜庆，利感情、姻缘、桃花",
}

# 二十四山坐向（简化版：每宫三山，取24向）
# 这里用常见八向简化：坎(北)、艮(东北)、震(东)、巽(东南)、
# 离(南)、坤(西南)、兑(西)、乾(西北)
EIGHT_DIRECTIONS = [
    ("坎", "北", 1),
    ("艮", "东北", 8),
    ("震", "东", 3),
    ("巽", "东南", 4),
    ("离", "南", 9),
    ("坤", "西南", 2),
    ("兑", "西", 7),
    ("乾", "西北", 6),
]

# 洛书九宫数（位置 → 数字）
LUOSHU_POSITION_NUMBER = {
    # (行, 列) → 数字，行0=北，列0=西
    (0, 1): 9,  # 南中 (注：下面输出时方位已调整)
}

# 九宫位置
NINE_PALACES = {
    "坎": {"位置": "北", "数字": 1, "五行": "水"},
    "坤": {"位置": "西南", "数字": 2, "五行": "土"},
    "震": {"位置": "东", "数字": 3, "五行": "木"},
    "巽": {"位置": "东南", "数字": 4, "五行": "木"},
    "中宫": {"位置": "中", "数字": 5, "五行": "土"},
    "乾": {"位置": "西北", "数字": 6, "五行": "金"},
    "兑": {"位置": "西", "数字": 7, "五行": "金"},
    "艮": {"位置": "东北", "数字": 8, "五行": "土"},
    "离": {"位置": "南", "数字": 9, "五行": "火"},
}


# ============================================================================
# 元运计算
# ============================================================================

def get_yun_number(year: int) -> int:
    """
    根据公历年份计算属于第几运。
    1864起为下元第1运，每20年转一运。
    """
    yun_start = 1864
    if year < yun_start:
        # 简化：1864前按60循环推
        diff = yun_start - year
        cycles = diff // 180 + 1
        year = year + cycles * 180
    offset = year - yun_start
    yun_idx = offset // 20
    return (yun_idx % 9) + 1  # 1~9循环


def get_yun_name(yun: int) -> str:
    """第几运的中文名称"""
    yuans = {1: "上元", 2: "上元", 3: "上元",
             4: "中元", 5: "中元", 6: "中元",
             7: "下元", 8: "下元", 9: "下元"}
    return f"{yuans.get(yun, '下元')}{yun}运"


def get_yun_year_range(yun: int) -> Tuple[int, int]:
    """获取某运的年份范围（基于1864起点计算）"""
    start = 1864 + (yun - 1) * 20
    return start, start + 19


# ============================================================================
# 飞星核心算法
# ============================================================================

def _shun_fly(center_star: int) -> Dict[int, int]:
    """
    顺飞：从中心数字出发，按 1→2→3→4→5→6→7→8→9 的顺序分配到洛书九宫
    洛书顺序（入中宫后飞九宫）：中5 → 乾6 → 兑7 → 艮8 → 离9 → 坎1 → 坤2 → 震3 → 巽4
    简化实现：返回 {palace_number: star_number}

    简化版飞星：按数字 1-9 顺序对应九宫位置
    """
    # 九宫基础位置(数字1..9对应九宫位置编号)
    # 洛书: 戴九履一，左三右七，二四为肩，六八为足，五居中央
    # 位置映射（方位→数字）：
    #   北1 南9 东3 西7
    #   东北8 西北6 东南4 西南2 中5

    # 入中宫顺飞：某星入中，顺次飞布九宫
    # 例如：5入中 → 1→坎, 2→坤, 3→震, 4→巽, 5→中, 6→乾, 7→兑, 8→艮, 9→离
    # 实际：6入中 → 1→乾, 2→兑, 3→艮, 4→离, 5→坎, 6→中, 7→坤, 8→震, 9→巽

    # 简化实现：按 (star_number - center_number + 5) mod 9 → 得到新位置
    result = {}
    for star in range(1, 10):
        offset = (star - center_star + 9) % 9
        # offset 0=中宫, 1=乾, 2=兑, 3=艮, 4=离, 5=坎, 6=坤, 7=震, 8=巽
        palace_map = {0: 5, 1: 6, 2: 7, 3: 8, 4: 9, 5: 1, 6: 2, 7: 3, 8: 4}
        palace = palace_map[offset]
        result[palace] = star
    return result


def _ni_fly(center_star: int) -> Dict[int, int]:
    """
    逆飞：入中宫后逆布，用于阴干/特殊情况
    简化版：按9→8→7→6→5→4→3→2→1 顺序
    """
    result = {}
    for star in range(1, 10):
        offset = (center_star - star + 9) % 9
        palace_map = {0: 5, 1: 6, 2: 7, 3: 8, 4: 9, 5: 1, 6: 2, 7: 3, 8: 4}
        palace = palace_map[offset]
        result[palace] = star
    return result


# ============================================================================
# 玄空飞星排盘引擎
# ============================================================================

@dataclass
class FlyingStarResult:
    """玄空飞星排盘结果"""
    year: int
    yun: int
    yun_name: str
    direction: str              # 坐向：如"坐北向南"
    sitting_palace: str         # 坐宫
    facing_palace: str          # 向宫

    # 各盘：{palace_number: star_number}
    yuandan_pan: Dict[int, int]  # 元旦盘
    yun_pan: Dict[int, int]      # 运盘
    shan_pan: Dict[int, int]     # 山盘
    xiang_pan: Dict[int, int]    # 向盘
    liunian_pan: Optional[Dict[int, int]] = None  # 流年飞星盘

    # 分析
    analysis: Dict[str, Any] = field(default_factory=dict)
    judgments: List[str] = field(default_factory=list)
    wealth_palaces: List[str] = field(default_factory=list)
    health_palaces: List[str] = field(default_factory=list)
    relationship_palaces: List[str] = field(default_factory=list)
    career_palaces: List[str] = field(default_factory=list)
    danger_palaces: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        def _pan_to_labels(pan: Dict[int, int]) -> Dict[str, str]:
            labels = {}
            palace_map = {1: "坎(北)", 2: "坤(西南)", 3: "震(东)", 4: "巽(东南)",
                         5: "中宫", 6: "乾(西北)", 7: "兑(西)", 8: "艮(东北)", 9: "离(南)"}
            for p, s in pan.items():
                labels[palace_map.get(p, str(p))] = NINE_STARS.get(s, str(s))
            return labels

        result = {
            "year": self.year,
            "yun": self.yun,
            "yun_name": self.yun_name,
            "yun_year_range": list(get_yun_year_range(self.yun)),
            "direction": self.direction,
            "sitting_palace": self.sitting_palace,
            "facing_palace": self.facing_palace,
            "yuandan_pan": _pan_to_labels(self.yuandan_pan),
            "yun_pan": _pan_to_labels(self.yun_pan),
            "shan_pan": _pan_to_labels(self.shan_pan),
            "xiang_pan": _pan_to_labels(self.xiang_pan),
        }
        if self.liunian_pan:
            result["liunian_pan"] = _pan_to_labels(self.liunian_pan)
        result.update({
            "analysis": self.analysis,
            "judgments": self.judgments,
            "wealth_palaces": self.wealth_palaces,
            "health_palaces": self.health_palaces,
            "relationship_palaces": self.relationship_palaces,
            "career_palaces": self.career_palaces,
            "danger_palaces": self.danger_palaces,
        })
        return result


class XuankongEngine:
    """玄空飞星排盘引擎"""

    # 方位到宫位的映射（简化八向版）
    DIRECTION_PALACE = {
        "北": ("坎", 1), "东北": ("艮", 8), "东": ("震", 3), "东南": ("巽", 4),
        "南": ("离", 9), "西南": ("坤", 2), "西": ("兑", 7), "西北": ("乾", 6),
    }

    # 八宫数字 → 名称
    NUMBER_PALACE = {v[1]: v[0] for v in DIRECTION_PALACE.values()}
    NUMBER_PALACE[5] = "中宫"

    def __init__(self):
        pass

    def compute(
        self,
        sitting: str = "北",
        facing: str = "南",
        year: int = 2026,
    ) -> FlyingStarResult:
        """
        完整玄空飞星排盘

        Args:
            sitting: 坐向（"北"/"东北"/"东"/"东南"/"南"/"西南"/"西"/"西北"）
            facing: 朝向（通常是 sitting 的对面）
            year: 年份（用于计算元运与流年飞星）
        """
        yun = get_yun_number(year)
        yun_name = get_yun_name(yun)

        sit_name, sit_num = self.DIRECTION_PALACE.get(sitting, ("坎", 1))
        face_name, face_num = self.DIRECTION_PALACE.get(facing, ("离", 9))

        # 元旦盘：运星入中宫顺飞
        yuandan = _shun_fly(yun)

        # 运盘：同元旦盘（简化版，实际还有更细致算法）
        yun_pan = _shun_fly(yun)

        # 山盘：坐宫的运星数入中宫，顺飞或逆飞（简化版：坐宫星数入中顺飞）
        shan_pan = _shun_fly(yuandan.get(sit_num, 5))

        # 向盘：向宫的运星数入中宫，顺飞或逆飞（简化版：向宫星数入中逆飞）
        xiang_pan = _ni_fly(yuandan.get(face_num, 5))

        # 流年飞星：根据流年干支计算流年星入中宫
        # 简化版：(year - 4) % 9 + 1 入中宫顺飞
        liunian_center = ((year - 4) % 9)
        if liunian_center == 0:
            liunian_center = 9
        liunian_pan = _shun_fly(liunian_center)

        result = FlyingStarResult(
            year=year, yun=yun, yun_name=yun_name,
            direction=f"坐{sitting}向{facing}",
            sitting_palace=f"{sit_name}宫({sitting}, 数字{sit_num})",
            facing_palace=f"{face_name}宫({facing}, 数字{face_num})",
            yuandan_pan=yuandan, yun_pan=yun_pan,
            shan_pan=shan_pan, xiang_pan=xiang_pan, liunian_pan=liunian_pan,
        )

        # 分析：按各宫飞星组合，给出判断
        self._analyze(result, sitting, facing)
        return result

    def _analyze(self, result: FlyingStarResult, sitting: str, facing: str) -> None:
        """分析各宫飞星组合，给出判断"""
        # 分析运盘（主运）
        wealth_candidates = []
        health_warnings = []
        relationship_candidates = []
        career_candidates = []
        danger_candidates = []

        # 各宫综合：取流年盘 + 运盘 + 山/向盘组合
        palace_names = {
            1: "坎宫(北)", 2: "坤宫(西南)", 3: "震宫(东)", 4: "巽宫(东南)",
            5: "中宫", 6: "乾宫(西北)", 7: "兑宫(西)", 8: "艮宫(东北)", 9: "离宫(南)"
        }

        overall_scores = {}
        for palace in range(1, 10):
            yun_star = result.yun_pan.get(palace, 5)
            liunian_star = (result.liunian_pan or {}).get(palace, 5)
            shan_star = result.shan_pan.get(palace, 5)
            xiang_star = result.xiang_pan.get(palace, 5)

            # 简化评分：吉星+3, 凶星-3
            score = 0
            for s in (yun_star, liunian_star, shan_star, xiang_star):
                if STAR_FORTUNE.get(s) == "吉": score += 3
                elif STAR_FORTUNE.get(s) == "凶": score -= 3
                elif STAR_FORTUNE.get(s) == "大凶": score -= 5
            overall_scores[palace] = score

            palace_name = palace_names.get(palace, str(palace))

            # 具体领域判断（简化）
            if palace == 8:  # 艮宫-东北 主小贵、不动产
                wealth_candidates.append(f"{palace_name}: {NINE_STARS.get(yun_star, str(yun_star))}")
            if palace == 7:  # 兑宫-西 主商业
                wealth_candidates.append(f"{palace_name}: {NINE_STARS.get(yun_star, str(yun_star))}")
            if palace == 9:  # 离宫-南 主喜庆感情
                relationship_candidates.append(f"{palace_name}: {NINE_STARS.get(liunian_star, str(liunian_star))}")
            if palace == 1:  # 坎宫-北 主健康
                health_warnings.append(f"{palace_name}: {NINE_STARS.get(liunian_star, str(liunian_star))}")
            if palace == 6:  # 乾宫-西北 主官贵事业
                career_candidates.append(f"{palace_name}: {NINE_STARS.get(yun_star, str(yun_star))}")
            if palace == 5:  # 中宫 五黄所在最凶
                if liunian_star == 5 or yun_star == 5:
                    danger_candidates.append(f"{palace_name}: 五黄临位，需化解")
            if shan_star == 5 or xiang_star == 5:
                danger_candidates.append(f"{palace_name}: 五黄/山向交会")

        # 综合判断
        best_palace = max(overall_scores, key=overall_scores.get)
        worst_palace = min(overall_scores, key=overall_scores.get)

        result.analysis = {
            "overall_best": palace_names.get(best_palace, str(best_palace)),
            "overall_worst": palace_names.get(worst_palace, str(worst_palace)),
            "best_score": overall_scores[best_palace],
            "worst_score": overall_scores[worst_palace],
        }

        # 断语
        result.wealth_palaces = wealth_candidates[:3]
        result.health_palaces = health_warnings[:3]
        result.relationship_palaces = relationship_candidates[:3]
        result.career_palaces = career_candidates[:3]
        result.danger_palaces = danger_candidates

        result.judgments = [
            f"{result.yun_name}，本宅坐{sitting}向{facing}，",
            f"最佳方位：{result.analysis['overall_best']}（综合分 {result.analysis['best_score']}）",
            f"需要化解：{result.analysis['overall_worst']}（综合分 {result.analysis['worst_score']}）",
        ]

        if wealth_candidates:
            result.judgments.append(f"财运相关：{', '.join(wealth_candidates[:2])}")
        if danger_candidates:
            result.judgments.append(f"注意：{', '.join(danger_candidates[:2])}")

        # 根据流年盘加断语
        if result.liunian_pan:
            for palace in (1, 5, 7):
                star = result.liunian_pan.get(palace)
                if star and STAR_FORTUNE.get(star) in ("凶", "大凶"):
                    result.judgments.append(
                        f"流年{NINE_STARS.get(star, str(star))}临{palace_names.get(palace, str(palace))}，"
                        f"主{STAR_INFLUENCE.get(star, '注意事项')}"
                    )


# ============================================================================
# 阳宅分析（简化版）
# ============================================================================

class YangzhaiAnalyzer:
    """阳宅分析：针对住宅的风水综合分析"""

    def analyze(self, fengshui_result: FlyingStarResult, house_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        分析住宅：
          - 大门方位吉凶
          - 厨房位置
          - 卧室位置
          - 卫生间位置
        """
        house_info = house_info or {}
        door_dir = house_info.get("门位", "南")
        kitchen_dir = house_info.get("厨房", "西南")
        bedroom_dir = house_info.get("主卧", "东北")

        # 简化版：判断各主要功能区是否在吉位
        door_palace = XuankongEngine.DIRECTION_PALACE.get(door_dir, ("离", 9))
        kitchen_palace = XuankongEngine.DIRECTION_PALACE.get(kitchen_dir, ("坤", 2))
        bedroom_palace = XuankongEngine.DIRECTION_PALACE.get(bedroom_dir, ("艮", 8))

        def _dir_judgment(dir_name: str, palace_num: int, key: str) -> str:
            liunian_star = (fengshui_result.liunian_pan or {}).get(palace_num, 5)
            yun_star = fengshui_result.yun_pan.get(palace_num, 5)
            fortune = STAR_FORTUNE.get(liunian_star, "吉")
            star_name = NINE_STARS.get(liunian_star, str(liunian_star))
            if fortune == "吉":
                return f"{dir_name}位于吉位（{star_name}），{key}运昌隆"
            else:
                return f"{dir_name}位于凶位（{star_name}），需注意化解，不利{key}"

        return {
            "house_basic": f"坐{fengshui_result.direction.split('向')[0][1:] if '向' in fengshui_result.direction else '北'}向{facing if (facing:=fengshui_result.direction.split('向')[-1]) else '南'}",
            "door_analysis": _dir_judgment(f"{door_dir}门", door_palace[1], "事业与出入"),
            "kitchen_analysis": _dir_judgment(f"{kitchen_dir}厨房", kitchen_palace[1], "健康与饮食"),
            "bedroom_analysis": _dir_judgment(f"{bedroom_dir}卧室", bedroom_palace[1], "感情与休息"),
            "suggestions": [
                "保持阳宅整洁通风，尤其凶位不宜堆放杂物",
                "五黄/二黑临位，可放置金属/铜铃化解",
                "财位（八白/七赤所在）可放置聚宝盆或绿植",
                "大门不可直冲卫生间或厨房",
            ],
            "base_result": fengshui_result.to_dict(),
        }


# ============================================================================
# 便捷函数
# ============================================================================

def compute_fengshui(sitting: str, facing: str, year: int) -> FlyingStarResult:
    return XuankongEngine().compute(sitting=sitting, facing=facing, year=year)


if __name__ == "__main__":
    # 自测：2026 坐北朝南
    print("=" * 60)
    print("玄空飞星自测：2026年 坐北向南")
    print("=" * 60)
    engine = XuankongEngine()
    result = engine.compute(sitting="北", facing="南", year=2026)
    print(f"元运: {result.yun_name} ({result.yun}运)")
    print(f"坐向: {result.direction}")
    print(f"坐宫: {result.sitting_palace} / 向宫: {result.facing_palace}")
    print()
    print("运盘 (各宫飞星):")
    for p in sorted(result.yun_pan.keys()):
        print(f"  {p}宫 → {result.yun_pan[p]} ({NINE_STARS.get(result.yun_pan[p], '')})")
    print()
    print("流年飞星:")
    if result.liunian_pan:
        for p in sorted(result.liunian_pan.keys()):
            star = result.liunian_pan[p]
            print(f"  {p}宫 → {star} ({NINE_STARS.get(star, '')}, {STAR_FORTUNE.get(star, '')})")
    print()
    print("断语:")
    for j in result.judgments:
        print(f"  · {j}")
    print()
    print(f"财运位: {result.wealth_palaces}")
    print(f"感情位: {result.relationship_palaces}")
    print(f"事业位: {result.career_palaces}")
    print(f"注意位: {result.danger_palaces}")
